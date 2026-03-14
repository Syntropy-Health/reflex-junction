"""Tests for lab testing models and fetch handlers (Phase 5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import JunctionState, JunctionUser
from reflex_junction.models import (
    BiomarkerResult,
    LabOrder,
    LabTest,
    LabTestMarker,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestLabTestMarker:
    def test_defaults(self):
        m = LabTestMarker()
        assert m.id == 0
        assert m.name == ""
        assert m.slug == ""

    def test_custom_values(self):
        m = LabTestMarker(id=1, name="TSH", slug="tsh", description="Thyroid")
        assert m.name == "TSH"


class TestLabTest:
    def test_defaults(self):
        t = LabTest()
        assert t.markers == []
        assert t.is_active is True

    def test_with_markers(self):
        t = LabTest(
            id=1,
            name="Basic Panel",
            markers=[LabTestMarker(id=1, name="TSH")],
        )
        assert len(t.markers) == 1
        assert t.markers[0].name == "TSH"


class TestLabOrder:
    def test_defaults(self):
        o = LabOrder()
        assert o.status == ""
        assert o.patient_details == {}

    def test_custom_values(self):
        o = LabOrder(id="ord-1", status="completed", lab_test_id=5)
        assert o.id == "ord-1"
        assert o.lab_test_id == 5


class TestBiomarkerResult:
    def test_defaults(self):
        r = BiomarkerResult()
        assert r.value == 0.0
        assert r.is_above_range is False

    def test_out_of_range(self):
        r = BiomarkerResult(
            name="TSH",
            value=8.5,
            unit="mIU/L",
            min_range=0.4,
            max_range=4.0,
            is_above_range=True,
        )
        assert r.is_above_range is True
        assert r.value == 8.5


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.lab_tests = MagicMock()
    client.lab_tests.get_markers = AsyncMock()
    client.lab_tests.get_orders = AsyncMock()
    client.lab_tests.get_result_metadata = AsyncMock()
    return client


@pytest.fixture
def state(mock_client):
    JunctionState._api_key = "sk_test_123"
    JunctionState._client = mock_client
    s = JunctionUser()  # type: ignore[call-arg]
    object.__setattr__(s, "junction_user_id", "vital-user-123")
    return s


# ---------------------------------------------------------------------------
# Fetch handler tests
# ---------------------------------------------------------------------------


class TestFetchLabTests:
    @pytest.mark.asyncio()
    async def test_populates_lab_tests(self, state, mock_client):
        marker_mock = MagicMock()
        marker_mock.id = 1
        marker_mock.name = "TSH"
        marker_mock.slug = "tsh"
        marker_mock.description = "Thyroid Stimulating Hormone"

        test_mock = MagicMock()
        test_mock.id = 10
        test_mock.name = "Thyroid Panel"
        test_mock.slug = "thyroid-panel"
        test_mock.description = "Comprehensive thyroid test"
        test_mock.method = "blood_draw"
        test_mock.sample_type = "serum"
        test_mock.is_active = True
        test_mock.markers = [marker_mock]

        result = MagicMock()
        result.markers = [test_mock]
        mock_client.lab_tests.get_markers.return_value = result

        await JunctionUser.fetch_lab_tests.fn(state)
        assert len(state.lab_tests) == 1
        assert state.lab_tests[0].name == "Thyroid Panel"
        assert len(state.lab_tests[0].markers) == 1
        assert state.lab_tests[0].markers[0].name == "TSH"

    @pytest.mark.asyncio()
    async def test_empty_markers(self, state, mock_client):
        result = MagicMock()
        result.markers = []
        mock_client.lab_tests.get_markers.return_value = result

        await JunctionUser.fetch_lab_tests.fn(state)
        assert state.lab_tests == []


class TestFetchLabOrders:
    @pytest.mark.asyncio()
    async def test_populates_lab_orders(self, state, mock_client):
        order_mock = MagicMock()
        order_mock.id = "ord-1"
        order_mock.user_id = "vital-user-123"
        order_mock.patient_details = {"first_name": "Test"}
        order_mock.lab_test_id = 10
        order_mock.status = "completed"
        order_mock.created_at = "2024-01-15T10:00:00"
        order_mock.updated_at = "2024-01-16T10:00:00"

        result = MagicMock()
        result.orders = [order_mock]
        mock_client.lab_tests.get_orders.return_value = result

        await JunctionUser.fetch_lab_orders.fn(state)
        assert len(state.lab_orders) == 1
        assert state.lab_orders[0].id == "ord-1"
        assert state.lab_orders[0].status == "completed"

    @pytest.mark.asyncio()
    async def test_no_user_id(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_lab_orders.fn(state)
        assert state.lab_orders == []
        mock_client.lab_tests.get_orders.assert_not_called()


class TestFetchLabResults:
    @pytest.mark.asyncio()
    async def test_populates_lab_results(self, state, mock_client):
        result_mock = MagicMock()
        result_mock.name = "TSH"
        result_mock.slug = "tsh"
        result_mock.value = 2.5
        result_mock.unit = "mIU/L"
        result_mock.min_range = 0.4
        result_mock.max_range = 4.0
        result_mock.is_above_range = False
        result_mock.is_below_range = False
        result_mock.result_text = "Normal"

        result = MagicMock()
        result.results = [result_mock]
        mock_client.lab_tests.get_result_metadata.return_value = result

        await JunctionUser.fetch_lab_results.fn(state, "ord-1")
        assert len(state.lab_results) == 1
        assert state.lab_results[0].name == "TSH"
        assert state.lab_results[0].value == 2.5
        assert state.lab_results[0].is_above_range is False

    @pytest.mark.asyncio()
    async def test_out_of_range_result(self, state, mock_client):
        result_mock = MagicMock()
        result_mock.name = "TSH"
        result_mock.slug = "tsh"
        result_mock.value = 8.5
        result_mock.unit = "mIU/L"
        result_mock.min_range = 0.4
        result_mock.max_range = 4.0
        result_mock.is_above_range = True
        result_mock.is_below_range = False
        result_mock.result_text = "High"

        result = MagicMock()
        result.results = [result_mock]
        mock_client.lab_tests.get_result_metadata.return_value = result

        await JunctionUser.fetch_lab_results.fn(state, "ord-1")
        assert state.lab_results[0].is_above_range is True
