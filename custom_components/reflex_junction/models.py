from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reflex.components.props import PropsBase


class JunctionConfig(PropsBase):
    """Configuration for the Junction health data integration."""

    environment: str = "sandbox"
    """The Junction environment. One of: sandbox, production, sandbox_eu, production_eu."""

    region: str = "us"
    """The region for data storage. One of: us, eu."""


class LinkConfig(PropsBase):
    """Configuration for the Junction Link widget."""

    redirect_url: str = ""
    """URL to redirect to after a successful provider connection."""

    filter_on_providers: list[str] | None = None
    """Optional list of provider slugs to show in the Link widget."""


class ProviderInfo(PropsBase):
    """Information about a connected health data provider."""

    name: str = ""
    """The display name of the provider (e.g., 'Oura')."""

    slug: str = ""
    """The provider slug identifier (e.g., 'oura')."""

    logo: str = ""
    """URL to the provider's logo image."""

    auth_type: str = ""
    """The authentication type: oauth, password, email, sdk."""


# ---------------------------------------------------------------------------
# Health data models (populated from Vital SDK responses)
# ---------------------------------------------------------------------------


@dataclass
class SourceInfo:
    """Source/provider information attached to health data."""

    provider: str = ""
    type: str = ""
    app_id: str = ""


@dataclass
class SleepSummary:
    """Sleep session summary."""

    id: str = ""
    calendar_date: str = ""
    bedtime_start: str = ""
    bedtime_stop: str = ""
    duration: int = 0
    total: int = 0
    awake: int = 0
    light: int = 0
    rem: int = 0
    deep: int = 0
    score: int | None = None
    efficiency: float | None = None
    hr_lowest: int | None = None
    hr_average: int | None = None
    average_hrv: float | None = None
    respiratory_rate: float | None = None
    temperature_delta: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


@dataclass
class ActivitySummary:
    """Daily activity summary."""

    id: str = ""
    calendar_date: str = ""
    calories_total: float | None = None
    calories_active: float | None = None
    steps: int | None = None
    distance: float | None = None
    low: float | None = None
    medium: float | None = None
    high: float | None = None
    floors_climbed: int | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


@dataclass
class WorkoutSummary:
    """Workout session summary."""

    id: str = ""
    calendar_date: str = ""
    title: str = ""
    sport_name: str = ""
    sport_slug: str = ""
    time_start: str = ""
    time_end: str = ""
    duration: int = 0
    calories: float | None = None
    distance: float | None = None
    average_hr: int | None = None
    max_hr: int | None = None
    average_speed: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


@dataclass
class BodyMeasurement:
    """Body composition measurement."""

    id: str = ""
    calendar_date: str = ""
    weight: float | None = None
    fat: float | None = None
    body_mass_index: float | None = None
    muscle_mass_percentage: float | None = None
    water_percentage: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


@dataclass
class ProfileData:
    """User health profile from provider."""

    id: str = ""
    height: int | None = None
    birth_date: str | None = None
    gender: str | None = None
    sex: str | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


@dataclass
class MealSummary:
    """Meal/nutrition entry."""

    id: str = ""
    name: str = ""
    timestamp: str = ""
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)


# ---------------------------------------------------------------------------
# Vitals timeseries models (Phase 2)
# ---------------------------------------------------------------------------


@dataclass
class TimeseriesPoint:
    """A single vitals timeseries data point."""

    timestamp: str = ""
    value: float = 0.0
    unit: str = ""


@dataclass
class BloodPressurePoint:
    """A single blood pressure timeseries data point."""

    timestamp: str = ""
    systolic: float = 0.0
    diastolic: float = 0.0
    unit: str = "mmHg"


# ---------------------------------------------------------------------------
# Lab testing models (Phase 5)
# ---------------------------------------------------------------------------


@dataclass
class LabTestMarker:
    """A biomarker in a lab test panel."""

    id: int = 0
    name: str = ""
    slug: str = ""
    description: str = ""


@dataclass
class LabTest:
    """A lab test panel available for ordering."""

    id: int = 0
    name: str = ""
    slug: str = ""
    description: str = ""
    method: str = ""
    sample_type: str = ""
    is_active: bool = True
    markers: list[LabTestMarker] = field(default_factory=list)


@dataclass
class LabOrder:
    """A placed lab test order."""

    id: str = ""
    user_id: str = ""
    patient_details: dict[str, Any] = field(default_factory=dict)
    lab_test_id: int = 0
    status: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class BiomarkerResult:
    """A single biomarker result from a completed lab order."""

    name: str = ""
    slug: str = ""
    value: float = 0.0
    unit: str = ""
    min_range: float | None = None
    max_range: float | None = None
    is_above_range: bool = False
    is_below_range: bool = False
    result_text: str = ""
