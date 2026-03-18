"""Tests for wait_for_init, on_load event storage, and initialization flow."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from reflex_junction.junction_provider import JunctionState


class TestWaitForInitUuidValidation:
    """Tests for UUID parsing in wait_for_init."""

    @pytest.mark.asyncio()
    async def test_valid_uuid_string(self):
        uid = uuid.uuid4()
        JunctionState._on_load_events[uid] = ["event1"]  # type: ignore[list-item]
        state = JunctionState()  # type: ignore[call-arg]
        state.is_initialized = True

        # Mock async context manager for background task state lock
        state.__aenter__ = AsyncMock(return_value=state)
        state.__aexit__ = AsyncMock(return_value=False)

        result = await JunctionState.wait_for_init.fn(state, str(uid))
        assert result == ["event1"]

    @pytest.mark.asyncio()
    async def test_invalid_uuid_returns_empty(self):
        state = JunctionState()  # type: ignore[call-arg]
        result = await JunctionState.wait_for_init.fn(state, "not-a-uuid")
        assert result == []

    @pytest.mark.asyncio()
    async def test_empty_string_returns_empty(self):
        state = JunctionState()  # type: ignore[call-arg]
        result = await JunctionState.wait_for_init.fn(state, "")
        assert result == []


class TestOnLoadEventConsumption:
    """Tests for _on_load_events pop (memory leak fix)."""

    @pytest.mark.asyncio()
    async def test_events_removed_after_consumption(self):
        uid = uuid.uuid4()
        JunctionState._on_load_events[uid] = ["event1"]  # type: ignore[list-item]
        state = JunctionState()  # type: ignore[call-arg]
        state.is_initialized = True

        state.__aenter__ = AsyncMock(return_value=state)
        state.__aexit__ = AsyncMock(return_value=False)

        await JunctionState.wait_for_init.fn(state, str(uid))
        # After consumption, the uid should be gone from the dict
        assert uid not in JunctionState._on_load_events

    @pytest.mark.asyncio()
    async def test_missing_uid_returns_empty(self):
        uid = uuid.uuid4()
        state = JunctionState()  # type: ignore[call-arg]
        state.is_initialized = True

        state.__aenter__ = AsyncMock(return_value=state)
        state.__aexit__ = AsyncMock(return_value=False)

        result = await JunctionState.wait_for_init.fn(state, str(uid))
        assert result == []


class TestWaitForInitTimeout:
    """Tests for timeout behavior."""

    @pytest.mark.asyncio()
    async def test_timeout_returns_on_loads_anyway(self):
        uid = uuid.uuid4()
        JunctionState._on_load_events[uid] = ["deferred_event"]  # type: ignore[list-item]
        JunctionState._init_wait_timeout_seconds = 0.1

        state = JunctionState()  # type: ignore[call-arg]
        state.is_initialized = False

        state.__aenter__ = AsyncMock(return_value=state)
        state.__aexit__ = AsyncMock(return_value=False)

        result = await JunctionState.wait_for_init.fn(state, str(uid))
        assert result == ["deferred_event"]

    @pytest.mark.asyncio()
    async def test_immediate_return_when_initialized(self):
        uid = uuid.uuid4()
        JunctionState._on_load_events[uid] = ["event1"]  # type: ignore[list-item]

        state = JunctionState()  # type: ignore[call-arg]
        state.is_initialized = True

        state.__aenter__ = AsyncMock(return_value=state)
        state.__aexit__ = AsyncMock(return_value=False)

        # Should return immediately without hitting timeout
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await JunctionState.wait_for_init.fn(state, str(uid))
            assert result == ["event1"]
            mock_sleep.assert_not_called()


class TestSetOnLoadEvents:
    """Tests for _set_on_load_events class method."""

    def test_stores_events_by_uid(self):
        uid = uuid.uuid4()
        events = ["e1", "e2"]
        JunctionState._set_on_load_events(uid, events)  # type: ignore[arg-type]
        assert JunctionState._on_load_events[uid] == events

    def test_overwrites_existing_uid(self):
        uid = uuid.uuid4()
        JunctionState._set_on_load_events(uid, ["old"])  # type: ignore[list-item]
        JunctionState._set_on_load_events(uid, ["new"])  # type: ignore[list-item]
        assert JunctionState._on_load_events[uid] == ["new"]

    def test_multiple_uids_independent(self):
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()
        JunctionState._set_on_load_events(uid1, ["a"])  # type: ignore[list-item]
        JunctionState._set_on_load_events(uid2, ["b"])  # type: ignore[list-item]
        assert JunctionState._on_load_events[uid1] == ["a"]
        assert JunctionState._on_load_events[uid2] == ["b"]
