"""Tests for advanced features: introspection, providers (Phase 6)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import JunctionState, JunctionUser


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.providers = MagicMock()
    client.providers.get_all = AsyncMock(return_value=[])
    client.introspect = MagicMock()
    client.introspect.get_user_resources = AsyncMock()
    client.introspect.get_user_historical_pulls = AsyncMock()
    return client


@pytest.fixture
def state(mock_client):
    JunctionState._api_key = "sk_test_123"
    JunctionState._client = mock_client
    s = JunctionUser()  # type: ignore[call-arg]
    object.__setattr__(s, "junction_user_id", "vital-user-123")
    return s


class TestFetchProviders:
    @pytest.mark.asyncio()
    async def test_populates_available_providers(self, state, mock_client):
        p = MagicMock()
        p.name = "Oura"
        p.slug = "oura"
        p.logo = "https://logo.example/oura.png"
        p.auth_type = "oauth"
        p.status = "active"
        mock_client.providers.get_all.return_value = [p]

        await JunctionUser.fetch_providers.fn(state)
        assert len(state.available_providers) == 1
        assert state.available_providers[0]["slug"] == "oura"
        assert state.available_providers[0]["auth_type"] == "oauth"

    @pytest.mark.asyncio()
    async def test_empty_providers(self, state, mock_client):
        mock_client.providers.get_all.return_value = []
        await JunctionUser.fetch_providers.fn(state)
        assert state.available_providers == []


class TestFetchIntrospection:
    @pytest.mark.asyncio()
    async def test_populates_introspection_data(self, state, mock_client):
        r = MagicMock()
        r.resource = "sleep"
        r.provider = "oura"
        r.status = "available"
        result = MagicMock()
        result.resources = [r]
        mock_client.introspect.get_user_resources.return_value = result

        await JunctionUser.fetch_introspection.fn(state)
        assert len(state.introspection_data) == 1
        assert state.introspection_data[0]["resource"] == "sleep"

    @pytest.mark.asyncio()
    async def test_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_introspection.fn(state)
        assert state.introspection_data == []
        mock_client.introspect.get_user_resources.assert_not_called()


class TestFetchHistoricalPulls:
    @pytest.mark.asyncio()
    async def test_populates_historical_pulls(self, state, mock_client):
        p = MagicMock()
        p.resource = "activity"
        p.provider = "fitbit"
        p.status = "completed"
        result = MagicMock()
        result.historical_pulls = [p]
        mock_client.introspect.get_user_historical_pulls.return_value = result

        await JunctionUser.fetch_historical_pulls.fn(state)
        assert len(state.historical_pulls) == 1
        assert state.historical_pulls[0]["status"] == "completed"

    @pytest.mark.asyncio()
    async def test_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_historical_pulls.fn(state)
        assert state.historical_pulls == []
