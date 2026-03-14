"""Tests for vitals timeseries models and fetch handlers (Phase 2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from reflex_junction.junction_provider import JunctionState, JunctionUser
from reflex_junction.models import BloodPressurePoint, TimeseriesPoint

# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------


class TestTimeseriesPoint:
    def test_defaults(self):
        p = TimeseriesPoint()
        assert p.timestamp == ""
        assert p.value == 0.0
        assert p.unit == ""

    def test_custom_values(self):
        p = TimeseriesPoint(
            timestamp="2024-01-15T10:30:00+00:00", value=72.0, unit="bpm"
        )
        assert p.timestamp == "2024-01-15T10:30:00+00:00"
        assert p.value == 72.0
        assert p.unit == "bpm"


class TestBloodPressurePoint:
    def test_defaults(self):
        p = BloodPressurePoint()
        assert p.timestamp == ""
        assert p.systolic == 0.0
        assert p.diastolic == 0.0
        assert p.unit == "mmHg"

    def test_custom_values(self):
        p = BloodPressurePoint(
            timestamp="2024-01-15T10:30:00+00:00",
            systolic=120.0,
            diastolic=80.0,
            unit="mmHg",
        )
        assert p.systolic == 120.0
        assert p.diastolic == 80.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_timeseries_point(
    timestamp="2024-01-15T10:30:00+00:00", value=72.0, unit="bpm"
):
    p = MagicMock()
    p.timestamp = timestamp
    p.value = value
    p.unit = unit
    return p


def _make_bp_point(
    timestamp="2024-01-15T10:30:00+00:00",
    systolic=120.0,
    diastolic=80.0,
    unit="mmHg",
):
    p = MagicMock()
    p.timestamp = timestamp
    p.systolic = systolic
    p.diastolic = diastolic
    p.unit = unit
    return p


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.vitals = MagicMock()
    # Standard timeseries methods
    for method_name in [
        "heartrate",
        "hrv",
        "blood_oxygen",
        "glucose",
        "steps",
        "calories_active",
        "respiratory_rate",
        "stress_level",
    ]:
        setattr(client.vitals, method_name, AsyncMock(return_value=[]))
    # Blood pressure is special
    client.vitals.blood_pressure = AsyncMock(return_value=[])
    return client


@pytest.fixture
def state(mock_client):
    JunctionState._api_key = "sk_test_123"
    JunctionState._client = mock_client
    s = JunctionUser()  # type: ignore[call-arg]
    # Bypass Reflex __setattr__ for inherited vars (parent_state is None in tests)
    object.__setattr__(s, "junction_user_id", "vital-user-123")
    return s


# ---------------------------------------------------------------------------
# Fetch handler tests
# ---------------------------------------------------------------------------


class TestFetchHeartrate:
    @pytest.mark.asyncio()
    async def test_populates_heartrate_data(self, state, mock_client):
        mock_client.vitals.heartrate.return_value = [
            _make_timeseries_point(value=72.0, unit="bpm"),
            _make_timeseries_point(
                timestamp="2024-01-15T10:35:00+00:00", value=75.0, unit="bpm"
            ),
        ]
        await JunctionUser.fetch_heartrate.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.heartrate_data) == 2
        assert state.heartrate_data[0].value == 72.0
        assert state.heartrate_data[0].unit == "bpm"
        assert state.heartrate_data[1].value == 75.0

    @pytest.mark.asyncio()
    async def test_no_user_id_returns_empty(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_heartrate.fn(state, "2024-01-01")
        assert state.heartrate_data == []
        mock_client.vitals.heartrate.assert_not_called()


class TestFetchHRV:
    @pytest.mark.asyncio()
    async def test_populates_hrv_data(self, state, mock_client):
        mock_client.vitals.hrv.return_value = [
            _make_timeseries_point(value=45.2, unit="ms"),
        ]
        await JunctionUser.fetch_hrv.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.hrv_data) == 1
        assert state.hrv_data[0].value == 45.2
        assert state.hrv_data[0].unit == "ms"


class TestFetchBloodOxygen:
    @pytest.mark.asyncio()
    async def test_populates_blood_oxygen_data(self, state, mock_client):
        mock_client.vitals.blood_oxygen.return_value = [
            _make_timeseries_point(value=98.0, unit="%"),
        ]
        await JunctionUser.fetch_blood_oxygen.fn(
            state, "2024-01-01", "2024-01-31"
        )
        assert len(state.blood_oxygen_data) == 1
        assert state.blood_oxygen_data[0].value == 98.0


class TestFetchGlucose:
    @pytest.mark.asyncio()
    async def test_populates_glucose_data(self, state, mock_client):
        mock_client.vitals.glucose.return_value = [
            _make_timeseries_point(value=95.0, unit="mg/dL"),
        ]
        await JunctionUser.fetch_glucose.fn(state, "2024-01-01", "2024-01-31")
        assert len(state.glucose_data) == 1
        assert state.glucose_data[0].value == 95.0
        assert state.glucose_data[0].unit == "mg/dL"


class TestFetchStepsTimeseries:
    @pytest.mark.asyncio()
    async def test_populates_steps_timeseries(self, state, mock_client):
        mock_client.vitals.steps.return_value = [
            _make_timeseries_point(value=500.0, unit="steps"),
            _make_timeseries_point(
                timestamp="2024-01-15T11:00:00+00:00",
                value=750.0,
                unit="steps",
            ),
        ]
        await JunctionUser.fetch_steps_timeseries.fn(
            state, "2024-01-01", "2024-01-31"
        )
        assert len(state.steps_timeseries) == 2
        assert state.steps_timeseries[0].value == 500.0


class TestFetchCaloriesTimeseries:
    @pytest.mark.asyncio()
    async def test_populates_calories_timeseries(self, state, mock_client):
        mock_client.vitals.calories_active.return_value = [
            _make_timeseries_point(value=120.0, unit="kcal"),
        ]
        await JunctionUser.fetch_calories_timeseries.fn(
            state, "2024-01-01", "2024-01-31"
        )
        assert len(state.calories_timeseries) == 1
        assert state.calories_timeseries[0].value == 120.0


class TestFetchRespiratoryRate:
    @pytest.mark.asyncio()
    async def test_populates_respiratory_rate_data(self, state, mock_client):
        mock_client.vitals.respiratory_rate.return_value = [
            _make_timeseries_point(value=15.5, unit="breaths/min"),
        ]
        await JunctionUser.fetch_respiratory_rate.fn(
            state, "2024-01-01", "2024-01-31"
        )
        assert len(state.respiratory_rate_data) == 1
        assert state.respiratory_rate_data[0].value == 15.5


class TestFetchBloodPressure:
    @pytest.mark.asyncio()
    async def test_populates_blood_pressure_data(self, state, mock_client):
        mock_client.vitals.blood_pressure.return_value = [
            _make_bp_point(systolic=120.0, diastolic=80.0),
            _make_bp_point(
                timestamp="2024-01-15T14:00:00+00:00",
                systolic=118.0,
                diastolic=78.0,
            ),
        ]
        await JunctionUser.fetch_blood_pressure.fn(
            state, "2024-01-01", "2024-01-31"
        )
        assert len(state.blood_pressure_data) == 2
        assert state.blood_pressure_data[0].systolic == 120.0
        assert state.blood_pressure_data[0].diastolic == 80.0
        assert state.blood_pressure_data[1].systolic == 118.0

    @pytest.mark.asyncio()
    async def test_no_user_id_returns_empty(self, state, mock_client):
        object.__setattr__(state, "junction_user_id", "")
        await JunctionUser.fetch_blood_pressure.fn(state, "2024-01-01")
        assert state.blood_pressure_data == []


class TestFetchVitalGeneric:
    @pytest.mark.asyncio()
    async def test_known_metric_populates_state_var(self, state, mock_client):
        mock_client.vitals.heartrate.return_value = [
            _make_timeseries_point(value=68.0, unit="bpm"),
        ]
        await JunctionUser.fetch_vital.fn(
            state, "heartrate", "2024-01-01", "2024-01-31"
        )
        assert len(state.heartrate_data) == 1
        assert state.heartrate_data[0].value == 68.0

    @pytest.mark.asyncio()
    async def test_unknown_metric_logs_info(self, state, mock_client):
        mock_client.vitals.stress_level.return_value = [
            _make_timeseries_point(value=3.0, unit="level"),
        ]
        # Should not raise, just log
        await JunctionUser.fetch_vital.fn(
            state, "stress_level", "2024-01-01", "2024-01-31"
        )

    @pytest.mark.asyncio()
    async def test_nonexistent_metric_returns_empty(self, state, mock_client):
        # nonexistent_metric is not on client.vitals
        mock_client.vitals.nonexistent_metric = None
        await JunctionUser.fetch_vital.fn(
            state, "nonexistent_metric", "2024-01-01"
        )
        # No crash — internal _fetch_timeseries handles None method


class TestFetchTimeseriesEndDateOptional:
    @pytest.mark.asyncio()
    async def test_end_date_not_passed_to_sdk(self, state, mock_client):
        mock_client.vitals.heartrate.return_value = []
        await JunctionUser.fetch_heartrate.fn(state, "2024-01-01")
        mock_client.vitals.heartrate.assert_called_once_with(
            user_id="vital-user-123", start_date="2024-01-01"
        )

    @pytest.mark.asyncio()
    async def test_end_date_passed_to_sdk(self, state, mock_client):
        mock_client.vitals.heartrate.return_value = []
        await JunctionUser.fetch_heartrate.fn(
            state, "2024-01-01", "2024-01-31"
        )
        mock_client.vitals.heartrate.assert_called_once_with(
            user_id="vital-user-123",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )


# ---------------------------------------------------------------------------
# Chart computed var tests
# ---------------------------------------------------------------------------


class TestChartHeartrate:
    def test_returns_chart_data(self, state):
        object.__setattr__(
            state,
            "heartrate_data",
            [
                TimeseriesPoint(
                    timestamp="2024-01-15T10:30:00", value=72.0, unit="bpm"
                ),
                TimeseriesPoint(
                    timestamp="2024-01-15T10:35:00", value=75.0, unit="bpm"
                ),
            ],
        )
        result = JunctionUser.chart_heartrate.fget(state)
        assert len(result) == 2
        assert result[0] == {"timestamp": "2024-01-15T10:30:00", "bpm": 72.0}
        assert result[1] == {"timestamp": "2024-01-15T10:35:00", "bpm": 75.0}

    def test_empty_data(self, state):
        result = JunctionUser.chart_heartrate.fget(state)
        assert result == []


class TestChartHRV:
    def test_returns_chart_data(self, state):
        object.__setattr__(
            state,
            "hrv_data",
            [
                TimeseriesPoint(
                    timestamp="2024-01-15T10:30:00", value=45.2, unit="ms"
                ),
            ],
        )
        result = JunctionUser.chart_hrv.fget(state)
        assert len(result) == 1
        assert result[0] == {"timestamp": "2024-01-15T10:30:00", "hrv": 45.2}


class TestChartBloodPressure:
    def test_returns_chart_data(self, state):
        object.__setattr__(
            state,
            "blood_pressure_data",
            [
                BloodPressurePoint(
                    timestamp="2024-01-15T10:30:00",
                    systolic=120.0,
                    diastolic=80.0,
                ),
            ],
        )
        result = JunctionUser.chart_blood_pressure.fget(state)
        assert len(result) == 1
        assert result[0] == {
            "timestamp": "2024-01-15T10:30:00",
            "systolic": 120.0,
            "diastolic": 80.0,
        }


class TestChartGlucose:
    def test_returns_chart_data(self, state):
        object.__setattr__(
            state,
            "glucose_data",
            [
                TimeseriesPoint(
                    timestamp="2024-01-15T10:30:00",
                    value=95.0,
                    unit="mg/dL",
                ),
            ],
        )
        result = JunctionUser.chart_glucose.fget(state)
        assert len(result) == 1
        assert result[0] == {
            "timestamp": "2024-01-15T10:30:00",
            "glucose": 95.0,
            "unit": "mg/dL",
        }
