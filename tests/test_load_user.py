"""Tests for JunctionUser.load_user health data orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import JunctionState, JunctionUser


class TestLoadUserOrchestration:
    """Tests for load_user method calling all fetch handlers."""

    @pytest.fixture()
    def mock_client(self):
        """Create a mock AsyncVital client with all required endpoints."""
        client = MagicMock()
        client.user.get_connected_providers = AsyncMock(return_value={})
        client.sleep.get = AsyncMock(return_value=MagicMock(sleep=[]))
        client.activity.get = AsyncMock(return_value=MagicMock(activity=[]))
        client.workouts.get = AsyncMock(return_value=MagicMock(workouts=[]))
        client.body.get = AsyncMock(return_value=MagicMock(body=[]))
        client.profile.get = AsyncMock(return_value=MagicMock())
        client.meal.get = AsyncMock(return_value=MagicMock(meals=[]))
        # Vitals timeseries methods
        client.vitals.heartrate = AsyncMock(return_value=[])
        client.vitals.hrv = AsyncMock(return_value=[])
        client.vitals.blood_oxygen = AsyncMock(return_value=[])
        client.vitals.glucose = AsyncMock(return_value=[])
        JunctionState._api_key = "sk_test_load"
        JunctionState._client = client
        return client

    @pytest.fixture()
    def state(self, mock_client):
        """Create a JunctionUser instance with a mocked client."""
        s = JunctionUser()  # type: ignore[call-arg]
        object.__setattr__(s, "junction_user_id", "vital-user-123")
        return s

    @pytest.mark.asyncio()
    async def test_all_fetch_methods_called(self, state, mock_client):
        await JunctionUser.load_user.fn(state)
        # Connected providers
        mock_client.user.get_connected_providers.assert_called_once()
        # Summary endpoints
        mock_client.sleep.get.assert_called_once()
        mock_client.activity.get.assert_called_once()
        mock_client.workouts.get.assert_called_once()
        mock_client.body.get.assert_called_once()
        mock_client.profile.get.assert_called_once()
        mock_client.meal.get.assert_called_once()
        # Vitals timeseries
        mock_client.vitals.heartrate.assert_called_once()
        mock_client.vitals.hrv.assert_called_once()
        mock_client.vitals.blood_oxygen.assert_called_once()
        mock_client.vitals.glucose.assert_called_once()

    @pytest.mark.asyncio()
    async def test_date_range_is_30_days(self, state, mock_client):
        from datetime import date, timedelta

        await JunctionUser.load_user.fn(state)

        expected_end = date.today().isoformat()
        expected_start = (date.today() - timedelta(days=30)).isoformat()

        # Check sleep call args as representative
        call_kwargs = mock_client.sleep.get.call_args
        assert call_kwargs.kwargs["start_date"] == expected_start
        assert call_kwargs.kwargs["end_date"] == expected_end

    @pytest.mark.asyncio()
    async def test_early_return_on_empty_user_id(self, mock_client):
        s = JunctionUser()  # type: ignore[call-arg]
        object.__setattr__(s, "junction_user_id", "")
        await JunctionUser.load_user.fn(s)
        mock_client.user.get_connected_providers.assert_not_called()
        mock_client.sleep.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_error_isolation_continues_on_failure(self, state, mock_client):
        """If one fetch fails, the rest should still complete."""
        mock_client.sleep.get = AsyncMock(side_effect=RuntimeError("sleep API down"))
        await JunctionUser.load_user.fn(state)
        # Despite sleep failure, other endpoints should be called
        mock_client.activity.get.assert_called_once()
        mock_client.workouts.get.assert_called_once()
        mock_client.body.get.assert_called_once()
        mock_client.profile.get.assert_called_once()
        mock_client.meal.get.assert_called_once()
        mock_client.vitals.heartrate.assert_called_once()

    @pytest.mark.asyncio()
    async def test_connected_providers_failure_continues(self, state, mock_client):
        """If connected providers fails, health data fetches should still run."""
        mock_client.user.get_connected_providers = AsyncMock(
            side_effect=RuntimeError("providers API down")
        )
        await JunctionUser.load_user.fn(state)
        mock_client.sleep.get.assert_called_once()
        mock_client.vitals.glucose.assert_called_once()

    @pytest.mark.asyncio()
    async def test_vitals_timeseries_called_with_date_range(self, state, mock_client):
        from datetime import date, timedelta

        await JunctionUser.load_user.fn(state)

        expected_end = date.today().isoformat()
        expected_start = (date.today() - timedelta(days=30)).isoformat()

        # Check all vitals endpoints receive date range
        for vitals_method in [
            mock_client.vitals.heartrate,
            mock_client.vitals.hrv,
            mock_client.vitals.blood_oxygen,
            mock_client.vitals.glucose,
        ]:
            call_kwargs = vitals_method.call_args
            assert call_kwargs.kwargs["start_date"] == expected_start
            assert call_kwargs.kwargs["end_date"] == expected_end
