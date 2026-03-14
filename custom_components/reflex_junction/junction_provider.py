"""Core Junction state management and app integration for Reflex."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, ClassVar

import reflex as rx
from reflex.event import EventCallback, EventType

from .models import (
    ActivitySummary,
    BiomarkerResult,
    BloodPressurePoint,
    BodyMeasurement,
    LabOrder,
    LabTest,
    LabTestMarker,
    MealSummary,
    ProfileData,
    SleepSummary,
    SourceInfo,
    TimeseriesPoint,
    WorkoutSummary,
)

logger = logging.getLogger(__name__)

# Environment mapping: string name -> VitalEnvironment enum value
_ENVIRONMENT_MAP: dict[str, str] = {
    "sandbox": "sandbox",
    "production": "production",
    "sandbox_eu": "sandbox_eu",
    "production_eu": "production_eu",
}


def _source_from_sdk(source: Any) -> SourceInfo:
    """Convert a Vital SDK source object to SourceInfo."""
    if source is None:
        return SourceInfo()
    return SourceInfo(
        provider=str(getattr(source, "provider", "") or ""),
        type=str(getattr(source, "type", "") or ""),
        app_id=str(getattr(source, "app_id", "") or ""),
    )


class MissingApiKeyError(ValueError):
    """Raised when the Junction API key is not set."""


class JunctionState(rx.State):
    """Core state for Junction health data integration.

    Manages the Junction API client, user mapping, and provider connections.
    Configuration is stored as ClassVars (process-level singletons).
    Per-session state tracks the current user's Junction data.
    """

    # Per-session state vars (serialized by Reflex)
    junction_user_id: str = ""
    client_user_id: str = ""
    connected_sources: list[dict[str, Any]] = []
    is_initialized: bool = False
    _link_token: str = ""
    _link_web_url: str = ""

    # ClassVars — process-level singletons, NOT per-session
    _api_key: ClassVar[str | None] = None
    _environment: ClassVar[str] = "sandbox"
    _client: ClassVar[Any | None] = None  # AsyncVital, typed as Any to avoid import at module level
    _on_load_events: ClassVar[dict[uuid.UUID, list[EventType[()]]]] = {}
    _dependent_handlers: ClassVar[dict[int, EventCallback]] = {}
    _init_wait_timeout_seconds: ClassVar[float] = 1.0

    @classmethod
    def _set_api_key(cls, api_key: str) -> None:
        """Set the Junction API key (process-level singleton)."""
        if not api_key:
            raise MissingApiKeyError("api_key must be set (and not empty)")
        cls._api_key = api_key

    @classmethod
    def _set_environment(cls, environment: str) -> None:
        """Set the Junction environment."""
        if environment not in _ENVIRONMENT_MAP:
            logger.warning(
                "Unknown environment '%s', defaulting to 'sandbox'. "
                "Valid options: %s",
                environment,
                list(_ENVIRONMENT_MAP.keys()),
            )
            environment = "sandbox"
        cls._environment = environment

    @classmethod
    def _set_client(cls) -> None:
        """Initialize the AsyncVital client (lazy, called once)."""
        from vital.client import AsyncVital
        from vital.environment import VitalEnvironment

        if cls._api_key is None:
            raise MissingApiKeyError(
                "Junction API key not set. Call wrap_app() or junction_provider() first."
            )

        env_map = {
            "sandbox": VitalEnvironment.SANDBOX,
            "production": VitalEnvironment.PRODUCTION,
            "sandbox_eu": VitalEnvironment.SANDBOX_EU,
            "production_eu": VitalEnvironment.PRODUCTION_EU,
        }
        vital_env = env_map.get(cls._environment, VitalEnvironment.SANDBOX)
        cls._client = AsyncVital(api_key=cls._api_key, environment=vital_env)

    @property
    def client(self) -> Any:
        """Get the AsyncVital client, initializing lazily if needed."""
        if self._client is None:
            self._set_client()
        return self._client

    @classmethod
    def register_dependent_handler(cls, handler: EventCallback) -> None:
        """Register a handler to be called after initialization.

        Uses hash-based dedup to prevent double-registration.
        """
        if not isinstance(handler, rx.EventHandler):
            raise TypeError(f"Expected EventHandler, got {type(handler)}")
        hash_id = hash((handler.state_full_name, handler.fn))
        cls._dependent_handlers[hash_id] = handler

    @classmethod
    def _set_on_load_events(
        cls, uid: uuid.UUID, events: list[EventType[()]]
    ) -> None:
        """Store on_load events by UUID for later retrieval."""
        cls._on_load_events[uid] = events

    @rx.event
    async def initialize(self) -> list[EventCallback]:
        """Initialize the Junction state. Sets is_initialized and fires dependent handlers."""
        self.is_initialized = True
        return list(self._dependent_handlers.values())

    @rx.event(background=True)
    async def wait_for_init(self, uid: str) -> list[EventType[()]]:
        """Wait for Junction state to be initialized, then return stored on_load events.

        Args:
            uid: String UUID identifying the on_load event batch.
        """
        parsed_uid = uuid.UUID(uid) if isinstance(uid, str) else uid
        on_loads = self._on_load_events.get(parsed_uid, [])

        start = time.monotonic()
        while time.monotonic() - start < self._init_wait_timeout_seconds:
            async with self:
                if self.is_initialized:
                    return on_loads
            await asyncio.sleep(0.05)

        logger.warning(
            "Junction init wait timed out after %.1fs. "
            "Proceeding with on_load handlers anyway.",
            self._init_wait_timeout_seconds,
        )
        return on_loads

    @rx.event
    async def create_user(self, client_user_id: str) -> None:
        """Create a Junction user mapped to the given client user ID.

        Args:
            client_user_id: Your application's internal user identifier.
        """
        result = await self.client.user.create(client_user_id=client_user_id)
        self.junction_user_id = str(result.user_id)
        self.client_user_id = client_user_id

    @rx.event
    async def get_connected_providers(self) -> None:
        """Fetch and update the list of connected providers for the current user."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        result = await self.client.user.get_connected_providers(
            user_id=self.junction_user_id
        )
        # Flatten the provider status dict into a list of dicts
        providers = []
        for source_type, source_list in result.items():
            for source in source_list:
                providers.append(
                    {
                        "source_type": source_type,
                        "name": getattr(source, "name", ""),
                        "slug": getattr(source, "slug", ""),
                        "logo": getattr(source, "logo", ""),
                        "status": getattr(source, "status", ""),
                    }
                )
        self.connected_sources = providers

    @rx.event
    async def disconnect_provider(self, provider: str) -> EventCallback | None:
        """Disconnect a specific provider for the current user.

        Args:
            provider: The provider slug to disconnect (e.g., 'oura').
        """
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        await self.client.user.deregister_provider(
            user_id=self.junction_user_id,
            provider=provider,
        )
        # Refresh the connected sources list
        return JunctionState.get_connected_providers  # type: ignore[return-value]

    @rx.event
    async def refresh_data(self) -> None:
        """Trigger a data refresh for the current user from all connected providers."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        await self.client.user.refresh(user_id=self.junction_user_id)

    @rx.event
    async def create_link_token(self, redirect_url: str = "") -> None:
        """Generate a Junction Link token for the current user.

        The token and web URL are stored in state for use by the Link widget.

        Args:
            redirect_url: URL to redirect to after provider connection.
        """
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {"user_id": self.junction_user_id}
        if redirect_url:
            kwargs["redirect_url"] = redirect_url
        result = await self.client.link.token(**kwargs)
        self._link_token = str(result.link_token)
        self._link_web_url = str(result.link_web_url)

    @rx.var
    def has_connections(self) -> bool:
        """Whether the current user has any connected providers."""
        return len(self.connected_sources) > 0

    @rx.var
    def provider_slugs(self) -> list[str]:
        """List of connected provider slugs."""
        return [p.get("slug", "") for p in self.connected_sources]

    @rx.var
    def link_token(self) -> str:
        """The current link token for the Link widget."""
        return self._link_token

    @rx.var
    def link_web_url(self) -> str:
        """The current link web URL for redirect-based flow."""
        return self._link_web_url


class JunctionUser(JunctionState):
    """Extended Junction state with health data summaries.

    Inherits from JunctionState and adds per-user health data fields.
    Register via register_on_auth_change_handler(JunctionUser.load_user).
    """

    sleep_data: list[SleepSummary] = []
    activity_data: list[ActivitySummary] = []
    workout_data: list[WorkoutSummary] = []
    body_data: list[BodyMeasurement] = []
    user_profile: ProfileData | None = None
    meal_data: list[MealSummary] = []

    # Vitals timeseries (Phase 2)
    heartrate_data: list[TimeseriesPoint] = []
    hrv_data: list[TimeseriesPoint] = []
    blood_oxygen_data: list[TimeseriesPoint] = []
    glucose_data: list[TimeseriesPoint] = []
    steps_timeseries: list[TimeseriesPoint] = []
    calories_timeseries: list[TimeseriesPoint] = []
    respiratory_rate_data: list[TimeseriesPoint] = []
    blood_pressure_data: list[BloodPressurePoint] = []

    # Lab testing (Phase 5)
    lab_tests: list[LabTest] = []
    lab_orders: list[LabOrder] = []
    lab_results: list[BiomarkerResult] = []

    # Advanced features (Phase 6)
    available_providers: list[dict[str, Any]] = []
    introspection_data: list[dict[str, Any]] = []
    historical_pulls: list[dict[str, Any]] = []

    @rx.event
    async def fetch_sleep(self, start_date: str, end_date: str = "") -> None:
        """Fetch sleep data for the given date range."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.sleep.get(**kwargs)
        self.sleep_data = [
            SleepSummary(
                id=str(getattr(s, "id", "")),
                calendar_date=str(getattr(s, "calendar_date", "")),
                bedtime_start=str(getattr(s, "bedtime_start", "")),
                bedtime_stop=str(getattr(s, "bedtime_stop", "")),
                duration=getattr(s, "duration", 0) or 0,
                total=getattr(s, "total", 0) or 0,
                awake=getattr(s, "awake", 0) or 0,
                light=getattr(s, "light", 0) or 0,
                rem=getattr(s, "rem", 0) or 0,
                deep=getattr(s, "deep", 0) or 0,
                score=getattr(s, "score", None),
                efficiency=getattr(s, "efficiency", None),
                hr_lowest=getattr(s, "hr_lowest", None),
                hr_average=getattr(s, "hr_average", None),
                average_hrv=getattr(s, "average_hrv", None),
                respiratory_rate=getattr(s, "respiratory_rate", None),
                temperature_delta=getattr(s, "temperature_delta", None),
                source=_source_from_sdk(getattr(s, "source", None)),
            )
            for s in result.sleep
        ]

    @rx.event
    async def fetch_activity(self, start_date: str, end_date: str = "") -> None:
        """Fetch activity data for the given date range."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.activity.get(**kwargs)
        self.activity_data = [
            ActivitySummary(
                id=str(getattr(a, "id", "")),
                calendar_date=str(getattr(a, "calendar_date", "")),
                calories_total=getattr(a, "calories_total", None),
                calories_active=getattr(a, "calories_active", None),
                steps=getattr(a, "steps", None),
                distance=getattr(a, "distance", None),
                low=getattr(a, "low", None),
                medium=getattr(a, "medium", None),
                high=getattr(a, "high", None),
                floors_climbed=getattr(a, "floors_climbed", None),
                source=_source_from_sdk(getattr(a, "source", None)),
            )
            for a in result.activity
        ]

    @rx.event
    async def fetch_workouts(self, start_date: str, end_date: str = "") -> None:
        """Fetch workout data for the given date range."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.workouts.get(**kwargs)
        self.workout_data = [
            WorkoutSummary(
                id=str(getattr(w, "id", "")),
                calendar_date=str(getattr(w, "calendar_date", "")),
                title=str(getattr(w, "title", "") or ""),
                sport_name=str(
                    getattr(getattr(w, "sport", None), "name", "") or ""
                ),
                sport_slug=str(
                    getattr(getattr(w, "sport", None), "slug", "") or ""
                ),
                time_start=str(getattr(w, "time_start", "")),
                time_end=str(getattr(w, "time_end", "")),
                duration=getattr(w, "moving_time", 0) or 0,
                calories=getattr(w, "calories", None),
                distance=getattr(w, "distance", None),
                average_hr=getattr(w, "average_hr", None),
                max_hr=getattr(w, "max_hr", None),
                average_speed=getattr(w, "average_speed", None),
                source=_source_from_sdk(getattr(w, "source", None)),
            )
            for w in result.workouts
        ]

    @rx.event
    async def fetch_body(self, start_date: str, end_date: str = "") -> None:
        """Fetch body measurement data for the given date range."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.body.get(**kwargs)
        self.body_data = [
            BodyMeasurement(
                id=str(getattr(b, "id", "")),
                calendar_date=str(getattr(b, "calendar_date", "")),
                weight=getattr(b, "weight", None),
                fat=getattr(b, "fat", None),
                body_mass_index=getattr(b, "body_mass_index", None),
                muscle_mass_percentage=getattr(b, "muscle_mass_percentage", None),
                water_percentage=getattr(b, "water_percentage", None),
                source=_source_from_sdk(getattr(b, "source", None)),
            )
            for b in result.body
        ]

    @rx.event
    async def fetch_profile(self) -> None:
        """Fetch health profile from connected provider."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        result = await self.client.profile.get(user_id=self.junction_user_id)
        self.user_profile = ProfileData(
            id=str(getattr(result, "id", "")),
            height=getattr(result, "height", None),
            birth_date=(
                str(getattr(result, "birth_date", ""))
                if getattr(result, "birth_date", None)
                else None
            ),
            gender=(
                str(getattr(result, "gender", ""))
                if getattr(result, "gender", None)
                else None
            ),
            sex=(
                str(getattr(result, "sex", ""))
                if getattr(result, "sex", None)
                else None
            ),
            source=_source_from_sdk(getattr(result, "source", None)),
        )

    @rx.event
    async def fetch_meals(self, start_date: str, end_date: str = "") -> None:
        """Fetch meal data for the given date range."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.meal.get(**kwargs)
        self.meal_data = [
            MealSummary(
                id=str(getattr(m, "id", "")),
                name=str(getattr(m, "name", "") or ""),
                timestamp=str(getattr(m, "timestamp", "")),
                calories=getattr(
                    getattr(m, "energy", None), "value", None
                ),
                protein=getattr(
                    getattr(m, "macros", None), "protein", None
                ),
                carbs=getattr(
                    getattr(m, "macros", None), "carbs", None
                ),
                fat=getattr(
                    getattr(m, "macros", None), "fat", None
                ),
                fiber=getattr(
                    getattr(m, "macros", None), "fiber", None
                ),
                sugar=getattr(
                    getattr(m, "macros", None), "sugar", None
                ),
                source=_source_from_sdk(getattr(m, "source", None)),
            )
            for m in result.meals
        ]

    # -----------------------------------------------------------------
    # Vitals timeseries fetch methods (Phase 2)
    # -----------------------------------------------------------------

    @rx.event
    async def fetch_heartrate(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch heart rate timeseries data."""
        self.heartrate_data = await self._fetch_timeseries(
            "heartrate", start_date, end_date
        )

    @rx.event
    async def fetch_hrv(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch heart rate variability timeseries data."""
        self.hrv_data = await self._fetch_timeseries(
            "hrv", start_date, end_date
        )

    @rx.event
    async def fetch_blood_oxygen(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch blood oxygen (SpO2) timeseries data."""
        self.blood_oxygen_data = await self._fetch_timeseries(
            "blood_oxygen", start_date, end_date
        )

    @rx.event
    async def fetch_glucose(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch glucose timeseries data."""
        self.glucose_data = await self._fetch_timeseries(
            "glucose", start_date, end_date
        )

    @rx.event
    async def fetch_steps_timeseries(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch steps timeseries data."""
        self.steps_timeseries = await self._fetch_timeseries(
            "steps", start_date, end_date
        )

    @rx.event
    async def fetch_calories_timeseries(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch calories timeseries data."""
        self.calories_timeseries = await self._fetch_timeseries(
            "calories_active", start_date, end_date
        )

    @rx.event
    async def fetch_respiratory_rate(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch respiratory rate timeseries data."""
        self.respiratory_rate_data = await self._fetch_timeseries(
            "respiratory_rate", start_date, end_date
        )

    @rx.event
    async def fetch_blood_pressure(
        self, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch blood pressure timeseries data."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await self.client.vitals.blood_pressure(**kwargs)
        self.blood_pressure_data = [
            BloodPressurePoint(
                timestamp=str(getattr(p, "timestamp", "")),
                systolic=float(getattr(p, "systolic", 0) or 0),
                diastolic=float(getattr(p, "diastolic", 0) or 0),
                unit=str(getattr(p, "unit", "mmHg") or "mmHg"),
            )
            for p in result
        ]

    @rx.event
    async def fetch_vital(
        self, metric: str, start_date: str, end_date: str = ""
    ) -> None:
        """Fetch any vitals timeseries by metric name.

        Generic escape hatch for the ~50 metrics not covered by
        dedicated helpers. Stores the result in the corresponding
        ``*_data`` state var if one exists, otherwise logs a warning.

        Args:
            metric: Vital SDK method name (e.g. "stress_level").
            start_date: ISO date string for range start.
            end_date: Optional ISO date string for range end.
        """
        # Map metric names to state var names
        _metric_to_var: dict[str, str] = {
            "heartrate": "heartrate_data",
            "hrv": "hrv_data",
            "blood_oxygen": "blood_oxygen_data",
            "glucose": "glucose_data",
            "steps": "steps_timeseries",
            "calories_active": "calories_timeseries",
            "respiratory_rate": "respiratory_rate_data",
        }
        points = await self._fetch_timeseries(metric, start_date, end_date)
        var_name = _metric_to_var.get(metric)
        if var_name:
            setattr(self, var_name, points)
        else:
            logger.info(
                "fetch_vital(%s): %d points (no dedicated state var)",
                metric,
                len(points),
            )

    async def _fetch_timeseries(
        self, metric: str, start_date: str, end_date: str = ""
    ) -> list[TimeseriesPoint]:
        """Internal helper to fetch a vitals timeseries from the SDK.

        Args:
            metric: SDK method name on client.vitals (e.g. "heartrate").
            start_date: ISO date string.
            end_date: Optional ISO date string.

        Returns:
            List of TimeseriesPoint dataclasses.
        """
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return []
        method = getattr(self.client.vitals, metric, None)
        if method is None:
            logger.error("Unknown vitals metric: %s", metric)
            return []
        kwargs: dict[str, Any] = {
            "user_id": self.junction_user_id,
            "start_date": start_date,
        }
        if end_date:
            kwargs["end_date"] = end_date
        result = await method(**kwargs)
        return [
            TimeseriesPoint(
                timestamp=str(getattr(p, "timestamp", "")),
                value=float(getattr(p, "value", 0) or 0),
                unit=str(getattr(p, "unit", "") or ""),
            )
            for p in result
        ]

    # -----------------------------------------------------------------
    # Lab testing methods (Phase 5)
    # -----------------------------------------------------------------

    @rx.event
    async def fetch_lab_tests(self) -> None:
        """Fetch available lab test panels."""
        if self._api_key is None:
            logger.warning("Junction API key not set. Call wrap_app() first.")
            return
        result = await self.client.lab_tests.get_markers()
        self.lab_tests = [
            LabTest(
                id=getattr(t, "id", 0) or 0,
                name=str(getattr(t, "name", "") or ""),
                slug=str(getattr(t, "slug", "") or ""),
                description=str(getattr(t, "description", "") or ""),
                method=str(getattr(t, "method", "") or ""),
                sample_type=str(getattr(t, "sample_type", "") or ""),
                is_active=bool(getattr(t, "is_active", True)),
                markers=[
                    LabTestMarker(
                        id=getattr(m, "id", 0) or 0,
                        name=str(getattr(m, "name", "") or ""),
                        slug=str(getattr(m, "slug", "") or ""),
                        description=str(getattr(m, "description", "") or ""),
                    )
                    for m in getattr(t, "markers", []) or []
                ],
            )
            for t in getattr(result, "markers", []) or []
        ]

    @rx.event
    async def fetch_lab_orders(self) -> None:
        """Fetch lab orders for the current user."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        result = await self.client.lab_tests.get_orders(
            user_id=self.junction_user_id
        )
        orders = getattr(result, "orders", []) or []
        self.lab_orders = [
            LabOrder(
                id=str(getattr(o, "id", "")),
                user_id=str(getattr(o, "user_id", "")),
                patient_details=dict(getattr(o, "patient_details", {}) or {}),
                lab_test_id=getattr(o, "lab_test_id", 0) or 0,
                status=str(getattr(o, "status", "") or ""),
                created_at=str(getattr(o, "created_at", "")),
                updated_at=str(getattr(o, "updated_at", "")),
            )
            for o in orders
        ]

    @rx.event
    async def fetch_lab_results(self, order_id: str) -> None:
        """Fetch biomarker results for a specific lab order.

        Args:
            order_id: The lab order ID to fetch results for.
        """
        if self._api_key is None:
            logger.warning("Junction API key not set. Call wrap_app() first.")
            return
        result = await self.client.lab_tests.get_result_metadata(
            order_id=order_id
        )
        results_data = getattr(result, "results", []) or []
        self.lab_results = [
            BiomarkerResult(
                name=str(getattr(r, "name", "") or ""),
                slug=str(getattr(r, "slug", "") or ""),
                value=float(getattr(r, "value", 0) or 0),
                unit=str(getattr(r, "unit", "") or ""),
                min_range=getattr(r, "min_range", None),
                max_range=getattr(r, "max_range", None),
                is_above_range=bool(getattr(r, "is_above_range", False)),
                is_below_range=bool(getattr(r, "is_below_range", False)),
                result_text=str(getattr(r, "result_text", "") or ""),
            )
            for r in results_data
        ]

    # -----------------------------------------------------------------
    # Advanced features (Phase 6)
    # -----------------------------------------------------------------

    @rx.event
    async def connect_demo_provider(self, provider: str = "oura") -> None:
        """Connect a demo provider in sandbox for synthetic data.

        Only works in sandbox environment. Creates 30 days of backfilled data.

        Args:
            provider: Demo provider slug (oura, fitbit, apple_health_kit, freestyle_libre).
        """
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        try:
            await self.client.link.connect_demo_provider(
                user_id=self.junction_user_id,
                provider=provider,
            )
            logger.info(
                "Connected demo provider '%s' for user %s",
                provider,
                self.junction_user_id,
            )
            # Refresh connected providers list
            await JunctionState.get_connected_providers.fn(self)
        except Exception:
            logger.exception("Failed to connect demo provider '%s'", provider)

    @rx.event
    async def fetch_providers(self) -> None:
        """Fetch the full list of available providers."""
        if self._api_key is None:
            logger.warning("Junction API key not set. Call wrap_app() first.")
            return
        result = await self.client.providers.get_all()
        self.available_providers = [
            {
                "name": str(getattr(p, "name", "") or ""),
                "slug": str(getattr(p, "slug", "") or ""),
                "logo": str(getattr(p, "logo", "") or ""),
                "auth_type": str(getattr(p, "auth_type", "") or ""),
                "status": str(getattr(p, "status", "") or ""),
            }
            for p in result
        ]

    @rx.event
    async def fetch_introspection(self) -> None:
        """Fetch introspection data (resource status) for the current user."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        result = await self.client.introspect.get_user_resources(
            user_id=self.junction_user_id
        )
        self.introspection_data = [
            {
                "resource": str(getattr(r, "resource", "") or ""),
                "provider": str(getattr(r, "provider", "") or ""),
                "status": str(getattr(r, "status", "") or ""),
            }
            for r in getattr(result, "resources", []) or []
        ]

    @rx.event
    async def fetch_historical_pulls(self) -> None:
        """Fetch historical pull status for the current user."""
        if not self.junction_user_id:
            logger.warning("No junction_user_id set. Call create_user() first.")
            return
        result = await self.client.introspect.get_user_historical_pulls(
            user_id=self.junction_user_id
        )
        self.historical_pulls = [
            {
                "resource": str(getattr(p, "resource", "") or ""),
                "provider": str(getattr(p, "provider", "") or ""),
                "status": str(getattr(p, "status", "") or ""),
            }
            for p in getattr(result, "historical_pulls", []) or []
        ]

    @rx.event
    async def load_user(self) -> None:
        """Load the current user's connections and health data.

        Fetches connected providers and all health data types with a
        30-day default date range. Errors in individual fetches do not
        prevent other fetches from completing.
        """
        if not self.junction_user_id:
            return
        from datetime import date, timedelta

        end = date.today()
        start = end - timedelta(days=30)
        start_str = start.isoformat()
        end_str = end.isoformat()

        try:
            await JunctionState.get_connected_providers.fn(self)
        except Exception:
            logger.exception("Failed to load connected providers")

        for method_name, args in [
            ("fetch_sleep", (start_str, end_str)),
            ("fetch_activity", (start_str, end_str)),
            ("fetch_workouts", (start_str, end_str)),
            ("fetch_body", (start_str, end_str)),
            ("fetch_profile", ()),
            ("fetch_meals", (start_str, end_str)),
            ("fetch_heartrate", (start_str, end_str)),
            ("fetch_hrv", (start_str, end_str)),
            ("fetch_blood_oxygen", (start_str, end_str)),
            ("fetch_glucose", (start_str, end_str)),
        ]:
            try:
                handler = getattr(JunctionUser, method_name)
                await handler.fn(self, *args)
            except Exception:
                logger.exception("Failed to fetch %s", method_name)

    @rx.var
    def chart_sleep_scores(self) -> list[dict[str, Any]]:
        """Sleep scores for recharts (date + score)."""
        return [
            {
                "date": s.calendar_date,
                "score": s.score or 0,
                "duration_hrs": round(s.total / 3600, 1),
            }
            for s in self.sleep_data
            if s.score is not None
        ]

    @rx.var
    def chart_activity_steps(self) -> list[dict[str, Any]]:
        """Daily steps for recharts (date + steps)."""
        return [
            {
                "date": a.calendar_date,
                "steps": a.steps or 0,
                "calories": round(a.calories_active or 0),
            }
            for a in self.activity_data
        ]

    @rx.var
    def latest_body(self) -> BodyMeasurement | None:
        """Most recent body measurement."""
        return self.body_data[-1] if self.body_data else None

    @rx.var
    def chart_heartrate(self) -> list[dict[str, Any]]:
        """Heart rate timeseries for recharts."""
        return [
            {"timestamp": p.timestamp, "bpm": p.value}
            for p in self.heartrate_data
        ]

    @rx.var
    def chart_hrv(self) -> list[dict[str, Any]]:
        """HRV timeseries for recharts."""
        return [
            {"timestamp": p.timestamp, "hrv": p.value}
            for p in self.hrv_data
        ]

    @rx.var
    def chart_blood_pressure(self) -> list[dict[str, Any]]:
        """Blood pressure timeseries for recharts."""
        return [
            {
                "timestamp": p.timestamp,
                "systolic": p.systolic,
                "diastolic": p.diastolic,
            }
            for p in self.blood_pressure_data
        ]

    @rx.var
    def chart_glucose(self) -> list[dict[str, Any]]:
        """Glucose timeseries for recharts."""
        return [
            {"timestamp": p.timestamp, "glucose": p.value, "unit": p.unit}
            for p in self.glucose_data
        ]


def junction_provider(
    *children: rx.Component,
    api_key: str,
    environment: str = "sandbox",
    register_user_state: bool = False,
) -> rx.Component:
    """Configure Junction integration and return a component wrapping children.

    Args:
        *children: Child components to wrap.
        api_key: Junction API key.
        environment: Junction environment (sandbox, production, sandbox_eu, production_eu).
        register_user_state: If True, registers JunctionUser.load_user as a dependent handler.

    Returns:
        A Reflex component wrapping the children with Junction configuration.
    """
    JunctionState._set_api_key(api_key)
    JunctionState._set_environment(environment)

    if register_user_state:
        register_on_auth_change_handler(JunctionUser.load_user)

    # In Phase 1, we just return children wrapped in a fragment.
    # Phase 2 will add the actual JunctionLinkProvider React component.
    return rx.fragment(*children)


def wrap_app(
    app: rx.App,
    api_key: str,
    environment: str = "sandbox",
    register_user_state: bool = False,
    register_webhooks: bool = False,
    webhook_secret: str | None = None,
    webhook_prefix: str = "/junction",
) -> rx.App:
    """Wrap a Reflex app with Junction health data integration.

    Args:
        app: The Reflex app to wrap.
        api_key: Junction API key.
        environment: Junction environment (sandbox, production, sandbox_eu, production_eu).
        register_user_state: If True, registers JunctionUser.load_user as dependent handler.
        register_webhooks: If True, registers the webhook API endpoint.
        webhook_secret: Svix webhook secret for signature verification.
        webhook_prefix: URL prefix for the webhook endpoint.

    Returns:
        The wrapped Reflex app.
    """
    # Priority 1 makes this the first wrapper around the content
    app.app_wraps[(1, "JunctionProvider")] = lambda _: junction_provider(
        api_key=api_key,
        environment=environment,
        register_user_state=register_user_state,
    )

    if register_webhooks:
        if not webhook_secret:
            raise ValueError(
                "webhook_secret is required when register_webhooks=True"
            )
        from .fastapi_helpers import register_webhook_api

        register_webhook_api(app, secret=webhook_secret, prefix=webhook_prefix)

    return app


def on_load(
    on_load_list: list[EventType[()]],
) -> list[EventType[()]]:
    """Wrap on_load handlers to ensure Junction state is initialized first.

    Usage:
        app.add_page(
            my_page,
            on_load=[*junction.on_load([MyState.load_data]), ...],
        )

    Args:
        on_load_list: List of event handlers to run after Junction initializes.

    Returns:
        A list containing the wait_for_init event handler.
    """
    uid = uuid.uuid4()
    JunctionState._set_on_load_events(uid, on_load_list)
    return [JunctionState.wait_for_init(str(uid))]  # type: ignore[list-item]


def register_on_auth_change_handler(handler: EventCallback) -> None:
    """Register an event handler to be called after Junction initialization.

    Args:
        handler: An rx.EventHandler to call after initialization.
    """
    JunctionState.register_dependent_handler(handler)
