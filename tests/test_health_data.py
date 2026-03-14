"""Tests for JunctionUser health data fetch handlers and typed models."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import JunctionState, JunctionUser
from reflex_junction.models import (
    ActivitySummary,
    BodyMeasurement,
    MealSummary,
    ProfileData,
    SleepSummary,
    SourceInfo,
    WorkoutSummary,
)

# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------


class TestSourceInfo:
    def test_defaults(self):
        s = SourceInfo()
        assert s.provider == ""
        assert s.type == ""
        assert s.app_id == ""

    def test_custom_values(self):
        s = SourceInfo(provider="oura", type="wearable", app_id="app-1")
        assert s.provider == "oura"
        assert s.type == "wearable"
        assert s.app_id == "app-1"


class TestSleepSummary:
    def test_defaults(self):
        s = SleepSummary()
        assert s.id == ""
        assert s.duration == 0
        assert s.score is None
        assert isinstance(s.source, SourceInfo)

    def test_with_data(self):
        s = SleepSummary(
            id="sleep-1",
            calendar_date="2024-01-15",
            total=28800,
            score=85,
            hr_average=55,
            source=SourceInfo(provider="oura"),
        )
        assert s.id == "sleep-1"
        assert s.total == 28800
        assert s.score == 85
        assert s.source.provider == "oura"


class TestActivitySummary:
    def test_defaults(self):
        a = ActivitySummary()
        assert a.steps is None
        assert a.calories_total is None

    def test_with_data(self):
        a = ActivitySummary(id="act-1", steps=10000, calories_active=450.5)
        assert a.steps == 10000
        assert a.calories_active == 450.5


class TestWorkoutSummary:
    def test_defaults(self):
        w = WorkoutSummary()
        assert w.sport_name == ""
        assert w.duration == 0

    def test_with_data(self):
        w = WorkoutSummary(
            id="w-1", sport_name="Running", duration=3600, calories=500.0
        )
        assert w.sport_name == "Running"
        assert w.calories == 500.0


class TestBodyMeasurement:
    def test_defaults(self):
        b = BodyMeasurement()
        assert b.weight is None
        assert b.fat is None

    def test_with_data(self):
        b = BodyMeasurement(weight=75.5, fat=18.2, body_mass_index=24.1)
        assert b.weight == 75.5
        assert b.body_mass_index == 24.1


class TestProfileData:
    def test_defaults(self):
        p = ProfileData()
        assert p.height is None
        assert p.birth_date is None

    def test_with_data(self):
        p = ProfileData(id="p-1", height=180, gender="male")
        assert p.height == 180
        assert p.gender == "male"


class TestMealSummary:
    def test_defaults(self):
        m = MealSummary()
        assert m.calories is None
        assert m.protein is None

    def test_with_data(self):
        m = MealSummary(name="Lunch", calories=650.0, protein=35.0, carbs=80.0)
        assert m.name == "Lunch"
        assert m.protein == 35.0


# ---------------------------------------------------------------------------
# Fetch handler tests
# ---------------------------------------------------------------------------


def _make_sdk_source(provider="oura", type_="wearable"):
    src = MagicMock()
    src.provider = provider
    src.type = type_
    src.app_id = ""
    return src


def _make_sleep_item(**overrides):
    item = MagicMock()
    defaults = {
        "id": "sleep-1",
        "calendar_date": "2024-01-15",
        "bedtime_start": "2024-01-14T23:00:00",
        "bedtime_stop": "2024-01-15T07:00:00",
        "duration": 28800,
        "total": 27000,
        "awake": 1800,
        "light": 10000,
        "rem": 7000,
        "deep": 10000,
        "score": 85,
        "efficiency": 0.94,
        "hr_lowest": 48,
        "hr_average": 55,
        "average_hrv": 45.2,
        "respiratory_rate": 15.5,
        "temperature_delta": -0.1,
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


def _make_activity_item(**overrides):
    item = MagicMock()
    defaults = {
        "id": "act-1",
        "calendar_date": "2024-01-15",
        "calories_total": 2200.0,
        "calories_active": 450.0,
        "steps": 10000,
        "distance": 8000.0,
        "low": 120.0,
        "medium": 45.0,
        "high": 15.0,
        "floors_climbed": 10,
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


def _make_workout_item(**overrides):
    item = MagicMock()
    sport = MagicMock()
    sport.name = "Running"
    sport.slug = "running"
    defaults = {
        "id": "w-1",
        "calendar_date": "2024-01-15",
        "title": "Morning Run",
        "sport": sport,
        "time_start": "2024-01-15T07:00:00",
        "time_end": "2024-01-15T08:00:00",
        "moving_time": 3600,
        "calories": 500.0,
        "distance": 10000.0,
        "average_hr": 145,
        "max_hr": 175,
        "average_speed": 2.78,
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


def _make_body_item(**overrides):
    item = MagicMock()
    defaults = {
        "id": "b-1",
        "calendar_date": "2024-01-15",
        "weight": 75.5,
        "fat": 18.2,
        "body_mass_index": 24.1,
        "muscle_mass_percentage": None,
        "water_percentage": None,
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


def _make_profile(**overrides):
    item = MagicMock()
    defaults = {
        "id": "p-1",
        "height": 180,
        "birth_date": "1990-05-15",
        "gender": "male",
        "sex": "male",
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


def _make_meal_item(**overrides):
    item = MagicMock()
    energy = MagicMock()
    energy.value = 650.0
    macros = MagicMock()
    macros.protein = 35.0
    macros.carbs = 80.0
    macros.fat = 25.0
    macros.fiber = 8.0
    macros.sugar = 12.0
    defaults = {
        "id": "m-1",
        "name": "Lunch",
        "timestamp": "2024-01-15T12:00:00",
        "energy": energy,
        "macros": macros,
        "source": _make_sdk_source(),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(item, k, v)
    return item


class TestFetchHandlers:
    """Tests for all fetch_* event handlers on JunctionUser."""

    @pytest.fixture()
    def mock_client(self):
        """Create a mock AsyncVital client with all health data endpoints."""
        client = MagicMock()
        # User endpoints (inherited from JunctionState)
        client.user.create = AsyncMock(
            return_value=MagicMock(user_id="vital-user-123")
        )
        client.user.get_connected_providers = AsyncMock(return_value={})

        # Sleep
        sleep_resp = MagicMock()
        sleep_resp.sleep = [_make_sleep_item()]
        client.sleep.get = AsyncMock(return_value=sleep_resp)

        # Activity
        activity_resp = MagicMock()
        activity_resp.activity = [_make_activity_item()]
        client.activity.get = AsyncMock(return_value=activity_resp)

        # Workouts
        workout_resp = MagicMock()
        workout_resp.workouts = [_make_workout_item()]
        client.workouts.get = AsyncMock(return_value=workout_resp)

        # Body
        body_resp = MagicMock()
        body_resp.body = [_make_body_item()]
        client.body.get = AsyncMock(return_value=body_resp)

        # Profile
        client.profile.get = AsyncMock(return_value=_make_profile())

        # Meals
        meal_resp = MagicMock()
        meal_resp.meals = [_make_meal_item()]
        client.meal.get = AsyncMock(return_value=meal_resp)

        return client

    @pytest.fixture()
    def state(self, mock_client):
        """Create a JunctionUser instance with a mocked client."""
        JunctionState._api_key = "sk_test_123"
        JunctionState._client = mock_client
        s = JunctionUser()  # type: ignore[call-arg]
        # Bypass Reflex __setattr__ for inherited vars (parent_state is None in tests)
        object.__setattr__(s, "junction_user_id", "vital-user-123")
        return s

    # --- fetch_sleep ---

    @pytest.mark.asyncio()
    async def test_fetch_sleep_populates_data(self, state, mock_client):
        await JunctionUser.fetch_sleep.fn(state, "2024-01-01", "2024-01-31")
        mock_client.sleep.get.assert_called_once_with(
            user_id="vital-user-123",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        assert len(state.sleep_data) == 1
        assert isinstance(state.sleep_data[0], SleepSummary)
        assert state.sleep_data[0].score == 85
        assert state.sleep_data[0].source.provider == "oura"

    @pytest.mark.asyncio()
    async def test_fetch_sleep_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_sleep.fn(state, "2024-01-01")
        mock_client.sleep.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_sleep_empty_response(self, state, mock_client):
        mock_client.sleep.get = AsyncMock(
            return_value=MagicMock(sleep=[])
        )
        await JunctionUser.fetch_sleep.fn(state, "2024-01-01")
        assert state.sleep_data == []

    @pytest.mark.asyncio()
    async def test_fetch_sleep_no_end_date(self, state, mock_client):
        await JunctionUser.fetch_sleep.fn(state, "2024-01-01")
        mock_client.sleep.get.assert_called_once_with(
            user_id="vital-user-123",
            start_date="2024-01-01",
        )

    # --- fetch_activity ---

    @pytest.mark.asyncio()
    async def test_fetch_activity_populates_data(self, state, mock_client):
        await JunctionUser.fetch_activity.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.activity_data) == 1
        assert isinstance(state.activity_data[0], ActivitySummary)
        assert state.activity_data[0].steps == 10000

    @pytest.mark.asyncio()
    async def test_fetch_activity_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_activity.fn(state, "2024-01-01")
        mock_client.activity.get.assert_not_called()

    # --- fetch_workouts ---

    @pytest.mark.asyncio()
    async def test_fetch_workouts_populates_data(self, state, mock_client):
        await JunctionUser.fetch_workouts.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.workout_data) == 1
        assert isinstance(state.workout_data[0], WorkoutSummary)
        assert state.workout_data[0].sport_name == "Running"
        assert state.workout_data[0].duration == 3600

    @pytest.mark.asyncio()
    async def test_fetch_workouts_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_workouts.fn(state, "2024-01-01")
        mock_client.workouts.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_workouts_no_sport(self, state, mock_client):
        """Workout with None sport should use empty strings."""
        workout_resp = MagicMock()
        workout_resp.workouts = [_make_workout_item(sport=None)]
        mock_client.workouts.get = AsyncMock(return_value=workout_resp)
        await JunctionUser.fetch_workouts.fn(state, "2024-01-01")
        assert state.workout_data[0].sport_name == ""
        assert state.workout_data[0].sport_slug == ""

    # --- fetch_body ---

    @pytest.mark.asyncio()
    async def test_fetch_body_populates_data(self, state, mock_client):
        await JunctionUser.fetch_body.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.body_data) == 1
        assert isinstance(state.body_data[0], BodyMeasurement)
        assert state.body_data[0].weight == 75.5

    @pytest.mark.asyncio()
    async def test_fetch_body_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_body.fn(state, "2024-01-01")
        mock_client.body.get.assert_not_called()

    # --- fetch_profile ---

    @pytest.mark.asyncio()
    async def test_fetch_profile_populates_data(self, state, mock_client):
        await JunctionUser.fetch_profile.fn(state)
        mock_client.profile.get.assert_called_once_with(
            user_id="vital-user-123"
        )
        assert isinstance(state.user_profile, ProfileData)
        assert state.user_profile.height == 180
        assert state.user_profile.gender == "male"

    @pytest.mark.asyncio()
    async def test_fetch_profile_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_profile.fn(state)
        mock_client.profile.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_profile_none_optional_fields(self, state, mock_client):
        mock_client.profile.get = AsyncMock(
            return_value=_make_profile(birth_date=None, gender=None, sex=None)
        )
        await JunctionUser.fetch_profile.fn(state)
        assert state.user_profile.birth_date is None
        assert state.user_profile.gender is None
        assert state.user_profile.sex is None

    # --- fetch_meals ---

    @pytest.mark.asyncio()
    async def test_fetch_meals_populates_data(self, state, mock_client):
        await JunctionUser.fetch_meals.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.meal_data) == 1
        assert isinstance(state.meal_data[0], MealSummary)
        assert state.meal_data[0].calories == 650.0
        assert state.meal_data[0].protein == 35.0

    @pytest.mark.asyncio()
    async def test_fetch_meals_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_meals.fn(state, "2024-01-01")
        mock_client.meal.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_meals_none_macros(self, state, mock_client):
        """Meal with None energy/macros should handle gracefully."""
        meal_resp = MagicMock()
        meal_resp.meals = [_make_meal_item(energy=None, macros=None)]
        mock_client.meal.get = AsyncMock(return_value=meal_resp)
        await JunctionUser.fetch_meals.fn(state, "2024-01-01")
        assert state.meal_data[0].calories is None
        assert state.meal_data[0].protein is None


class TestLoadUser:
    """Tests for JunctionUser.load_user integration."""

    @pytest.fixture()
    def mock_client(self):
        client = MagicMock()
        client.user.get_connected_providers = AsyncMock(return_value={})
        client.sleep.get = AsyncMock(return_value=MagicMock(sleep=[]))
        client.activity.get = AsyncMock(return_value=MagicMock(activity=[]))
        client.workouts.get = AsyncMock(return_value=MagicMock(workouts=[]))
        client.body.get = AsyncMock(return_value=MagicMock(body=[]))
        client.profile.get = AsyncMock(return_value=_make_profile())
        client.meal.get = AsyncMock(return_value=MagicMock(meals=[]))
        return client

    @pytest.fixture()
    def state(self, mock_client):
        JunctionState._api_key = "sk_test_123"
        JunctionState._client = mock_client
        s = JunctionUser()  # type: ignore[call-arg]
        # Bypass Reflex __setattr__ for inherited vars (parent_state is None in tests)
        object.__setattr__(s, "junction_user_id", "vital-user-123")
        return s

    @pytest.mark.asyncio()
    async def test_load_user_calls_all_fetches(self, state, mock_client):
        await JunctionUser.load_user.fn(state)
        mock_client.user.get_connected_providers.assert_called_once()
        mock_client.sleep.get.assert_called_once()
        mock_client.activity.get.assert_called_once()
        mock_client.workouts.get.assert_called_once()
        mock_client.body.get.assert_called_once()
        mock_client.profile.get.assert_called_once()
        mock_client.meal.get.assert_called_once()

    @pytest.mark.asyncio()
    async def test_load_user_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.load_user.fn(state)
        mock_client.user.get_connected_providers.assert_not_called()

    @pytest.mark.asyncio()
    async def test_load_user_error_isolation(self, state, mock_client):
        """Error in one fetch should not prevent other fetches."""
        mock_client.sleep.get = AsyncMock(side_effect=RuntimeError("API down"))
        await JunctionUser.load_user.fn(state)
        # Sleep failed but others should still be called
        mock_client.activity.get.assert_called_once()
        mock_client.workouts.get.assert_called_once()
        mock_client.body.get.assert_called_once()
        mock_client.profile.get.assert_called_once()
        mock_client.meal.get.assert_called_once()

    @pytest.mark.asyncio()
    async def test_load_user_providers_error_isolation(self, state, mock_client):
        """Error in get_connected_providers should not prevent health data fetches."""
        mock_client.user.get_connected_providers = AsyncMock(
            side_effect=RuntimeError("API down")
        )
        await JunctionUser.load_user.fn(state)
        # Health data fetches should still proceed
        mock_client.sleep.get.assert_called_once()


class TestChartComputedVars:
    """Tests for chart-ready computed vars."""

    @pytest.fixture()
    def mock_client(self):
        client = MagicMock()
        return client

    @pytest.fixture()
    def state(self, mock_client):
        JunctionState._api_key = "sk_test_123"
        JunctionState._client = mock_client
        s = JunctionUser()  # type: ignore[call-arg]
        return s

    def test_chart_sleep_scores(self, state):
        state.sleep_data = [
            SleepSummary(calendar_date="2024-01-15", total=27000, score=85),
            SleepSummary(calendar_date="2024-01-16", total=25200, score=None),
            SleepSummary(calendar_date="2024-01-17", total=28800, score=90),
        ]
        result = JunctionUser.chart_sleep_scores.fget(state)
        assert len(result) == 2  # score=None entry filtered out
        assert result[0]["date"] == "2024-01-15"
        assert result[0]["score"] == 85
        assert result[0]["duration_hrs"] == 7.5

    def test_chart_sleep_scores_empty(self, state):
        state.sleep_data = []
        result = JunctionUser.chart_sleep_scores.fget(state)
        assert result == []

    def test_chart_activity_steps(self, state):
        state.activity_data = [
            ActivitySummary(calendar_date="2024-01-15", steps=10000, calories_active=500.0),
        ]
        result = JunctionUser.chart_activity_steps.fget(state)
        assert len(result) == 1
        assert result[0]["steps"] == 10000
        assert result[0]["calories"] == 500

    def test_chart_activity_steps_none_values(self, state):
        state.activity_data = [
            ActivitySummary(calendar_date="2024-01-15", steps=None, calories_active=None),
        ]
        result = JunctionUser.chart_activity_steps.fget(state)
        assert result[0]["steps"] == 0
        assert result[0]["calories"] == 0

    def test_latest_body_with_data(self, state):
        state.body_data = [
            BodyMeasurement(calendar_date="2024-01-14", weight=76.0),
            BodyMeasurement(calendar_date="2024-01-15", weight=75.5),
        ]
        # Access raw ComputedVar from class dict (descriptor protocol wraps in ObjectVar)
        result = vars(JunctionUser)["latest_body"].fget(state)
        assert result.weight == 75.5

    def test_latest_body_empty(self, state):
        state.body_data = []
        result = vars(JunctionUser)["latest_body"].fget(state)
        assert result is None
