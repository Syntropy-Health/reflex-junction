"""Tests for JunctionState ClassVar management and configuration."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import (
    JunctionState,
    MissingApiKeyError,
)


class TestSetApiKey:
    """Tests for JunctionState._set_api_key."""

    def test_set_api_key_stores_value(self):
        JunctionState._set_api_key("sk_test_abc123")
        assert JunctionState._api_key == "sk_test_abc123"

    def test_set_api_key_empty_raises(self):
        with pytest.raises(MissingApiKeyError, match="api_key must be set"):
            JunctionState._set_api_key("")

    def test_set_api_key_overwrites(self):
        JunctionState._set_api_key("first_key")
        JunctionState._set_api_key("second_key")
        assert JunctionState._api_key == "second_key"


class TestSetEnvironment:
    """Tests for JunctionState._set_environment."""

    def test_set_valid_environments(self):
        for env in ("sandbox", "production", "sandbox_eu", "production_eu"):
            JunctionState._set_environment(env)
            assert JunctionState._environment == env

    def test_set_invalid_environment_defaults_to_sandbox(self):
        JunctionState._set_environment("invalid_env")
        assert JunctionState._environment == "sandbox"

    def test_set_empty_environment_defaults_to_sandbox(self):
        JunctionState._set_environment("")
        assert JunctionState._environment == "sandbox"


class TestOnLoadEvents:
    """Tests for on_load event storage."""

    def test_set_on_load_events(self):
        uid = uuid.uuid4()
        events: list = ["event1", "event2"]
        JunctionState._set_on_load_events(uid, events)  # type: ignore[arg-type]
        assert JunctionState._on_load_events[uid] == events

    def test_set_on_load_events_overwrites(self):
        uid = uuid.uuid4()
        JunctionState._set_on_load_events(uid, ["old"])  # type: ignore[list-item]
        JunctionState._set_on_load_events(uid, ["new"])  # type: ignore[list-item]
        assert JunctionState._on_load_events[uid] == ["new"]

    def test_multiple_uids(self):
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()
        JunctionState._set_on_load_events(uid1, ["a"])  # type: ignore[list-item]
        JunctionState._set_on_load_events(uid2, ["b"])  # type: ignore[list-item]
        assert JunctionState._on_load_events[uid1] == ["a"]
        assert JunctionState._on_load_events[uid2] == ["b"]


class TestRegisterDependentHandler:
    """Tests for register_dependent_handler."""

    def test_register_non_event_handler_raises(self):
        with pytest.raises(TypeError, match="Expected EventHandler"):
            JunctionState.register_dependent_handler("not_a_handler")  # type: ignore[arg-type]

    def test_dedup_by_hash(self):
        """Registering the same handler twice should only store one entry."""
        handler = JunctionState.initialize  # type: ignore[arg-type]
        JunctionState.register_dependent_handler(handler)
        JunctionState.register_dependent_handler(handler)
        assert len(JunctionState._dependent_handlers) == 1


class TestAsyncEventHandlers:
    """Tests for async event handlers with mocked Vital SDK."""

    @pytest.fixture()
    def mock_client(self):
        """Create a mock AsyncVital client."""
        client = MagicMock()
        client.user.create = AsyncMock(
            return_value=MagicMock(user_id="vital-user-123")
        )
        client.user.get_connected_providers = AsyncMock(return_value={})
        client.user.deregister_provider = AsyncMock()
        client.user.refresh = AsyncMock()
        client.link.token = AsyncMock(
            return_value=MagicMock(link_token="lnk_abc", link_web_url="https://link.example.com")
        )
        return client

    @pytest.fixture()
    def state(self, mock_client):
        """Create a JunctionState instance with a mocked client."""
        JunctionState._api_key = "sk_test_123"
        JunctionState._client = mock_client
        s = JunctionState()  # type: ignore[call-arg]
        return s

    @pytest.mark.asyncio()
    async def test_create_user_calls_sdk(self, state, mock_client):
        await JunctionState.create_user.fn(state, "app-user-1")
        mock_client.user.create.assert_called_once_with(client_user_id="app-user-1")
        assert state.junction_user_id == "vital-user-123"
        assert state.client_user_id == "app-user-1"

    @pytest.mark.asyncio()
    async def test_get_connected_providers_empty(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        await JunctionState.get_connected_providers.fn(state)
        mock_client.user.get_connected_providers.assert_called_once_with(
            user_id="vital-user-123"
        )
        assert state.connected_sources == []

    @pytest.mark.asyncio()
    async def test_get_connected_providers_with_data(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        mock_source = MagicMock(name="Oura", slug="oura", logo="https://logo.png", status="connected")
        mock_client.user.get_connected_providers = AsyncMock(
            return_value={"wearable": [mock_source]}
        )
        await JunctionState.get_connected_providers.fn(state)
        assert len(state.connected_sources) == 1
        assert state.connected_sources[0]["slug"] == "oura"
        assert state.connected_sources[0]["source_type"] == "wearable"

    @pytest.mark.asyncio()
    async def test_get_connected_providers_no_user_id(self, state, mock_client):
        state.junction_user_id = ""
        await JunctionState.get_connected_providers.fn(state)
        mock_client.user.get_connected_providers.assert_not_called()

    @pytest.mark.asyncio()
    async def test_disconnect_provider_calls_sdk(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        await JunctionState.disconnect_provider.fn(state, "oura")
        mock_client.user.deregister_provider.assert_called_once_with(
            user_id="vital-user-123", provider="oura"
        )

    @pytest.mark.asyncio()
    async def test_disconnect_provider_no_user_id(self, state, mock_client):
        state.junction_user_id = ""
        await JunctionState.disconnect_provider.fn(state, "oura")
        mock_client.user.deregister_provider.assert_not_called()

    @pytest.mark.asyncio()
    async def test_refresh_data_calls_sdk(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        await JunctionState.refresh_data.fn(state)
        mock_client.user.refresh.assert_called_once_with(user_id="vital-user-123")

    @pytest.mark.asyncio()
    async def test_create_link_token_calls_sdk(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        await JunctionState.create_link_token.fn(state)
        mock_client.link.token.assert_called_once_with(user_id="vital-user-123")
        assert state._link_token == "lnk_abc"
        assert state._link_web_url == "https://link.example.com"

    @pytest.mark.asyncio()
    async def test_create_link_token_with_redirect(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        await JunctionState.create_link_token.fn(state, redirect_url="https://app.example.com/callback")
        mock_client.link.token.assert_called_once_with(
            user_id="vital-user-123", redirect_url="https://app.example.com/callback"
        )

    @pytest.mark.asyncio()
    async def test_create_link_token_no_user_id(self, state, mock_client):
        state.junction_user_id = ""
        await JunctionState.create_link_token.fn(state)
        mock_client.link.token.assert_not_called()

    @pytest.mark.asyncio()
    async def test_initialize_sets_flag(self, state):
        assert state.is_initialized is False
        await JunctionState.initialize.fn(state)
        assert state.is_initialized is True

    @pytest.mark.asyncio()
    async def test_on_provider_connected_refreshes(self, state, mock_client):
        state.junction_user_id = "vital-user-123"
        metadata = {"provider": "oura", "status": "connected"}
        result = await JunctionState.on_provider_connected.fn(state, metadata)
        assert result == JunctionState.get_connected_providers

    @pytest.mark.asyncio()
    async def test_on_provider_connected_no_user_id(self, state):
        metadata = {"provider": "oura"}
        result = await JunctionState.on_provider_connected.fn(state, metadata)
        assert result is None

    @pytest.mark.asyncio()
    async def test_on_provider_connected_empty_metadata(self, state):
        state.junction_user_id = "vital-user-123"
        result = await JunctionState.on_provider_connected.fn(state, {})
        assert result == JunctionState.get_connected_providers

    @pytest.mark.asyncio()
    async def test_on_link_exit(self, state):
        metadata = {"reason": "user_closed"}
        await JunctionState.on_link_exit.fn(state, metadata)
        # Should not raise

    @pytest.mark.asyncio()
    async def test_on_link_error(self, state):
        metadata = {"error_type": "auth_failed"}
        await JunctionState.on_link_error.fn(state, metadata)
        # Should not raise
