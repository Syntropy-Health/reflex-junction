"""Core Junction state management and app integration for Reflex."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, ClassVar

import reflex as rx
from reflex.event import EventCallback, EventType

logger = logging.getLogger(__name__)

# Environment mapping: string name -> VitalEnvironment enum value
_ENVIRONMENT_MAP: dict[str, str] = {
    "sandbox": "sandbox",
    "production": "production",
    "sandbox_eu": "sandbox_eu",
    "production_eu": "production_eu",
}


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

    activity_summary: list[dict[str, Any]] = []
    sleep_summary: list[dict[str, Any]] = []
    body_summary: list[dict[str, Any]] = []
    profile: dict[str, Any] = {}
    meal_summary: list[dict[str, Any]] = []
    workout_summary: list[dict[str, Any]] = []

    @rx.event
    async def load_user(self) -> None:
        """Load the current user's connected providers and profile.

        This is typically registered as a dependent handler via
        register_on_auth_change_handler(JunctionUser.load_user).
        """
        if not self.junction_user_id:
            return
        try:
            await self.get_connected_providers()
        except Exception:
            logger.exception("Failed to load connected providers")


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
