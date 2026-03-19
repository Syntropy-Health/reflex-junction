# Feature: Typed Models & Core Health Data

## Summary

Replace all `dict[str, Any]` health data fields on `JunctionUser` with Python dataclass models, add `fetch_*` event handlers that call the Vital SDK to populate them, and update `load_user()` to actually fetch health data. This makes the existing placeholder fields functional and type-safe.

## User Story

As a Reflex developer using reflex-junction
I want typed health data (sleep, activity, workouts, body, profile, meals) populated from connected providers
So that I can build health dashboards with real data and IDE autocomplete instead of empty `dict[str, Any]`

## Problem Statement

JunctionUser declares 6 health data fields (`sleep_summary`, `activity_summary`, `body_summary`, `profile`, `meal_summary`, `workout_summary`) but `load_user()` only calls `get_connected_providers()`. The fields remain empty forever. The Vital SDK has all the data — it's just never fetched.

## Solution Statement

1. Create `@dataclass` models mirroring key fields from Vital SDK response types
2. Add `fetch_sleep`, `fetch_activity`, `fetch_workouts`, `fetch_body`, `fetch_profile`, `fetch_meals` event handlers to `JunctionUser`
3. Each handler calls the SDK, converts responses to dataclasses, assigns to state vars
4. Update `load_user()` to call all fetch methods with a sensible default date range
5. Add `chart_*` computed vars that transform typed data into `list[dict]` for `rx.recharts`

## Metadata

| Field | Value |
|-------|-------|
| Type | ENHANCEMENT |
| Complexity | MEDIUM |
| Systems Affected | custom_components/reflex_junction/models.py, junction_provider.py, __init__.py, tests/ |
| Dependencies | vital>=2.1.0, reflex>=0.8.0 |
| Estimated Tasks | 10 |

---

## UX Design

### Before State

```
┌────────────────────────────────────────────────────────────────┐
│                         BEFORE                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   wrap_app(app, api_key=...)                                    │
│         │                                                       │
│         ▼                                                       │
│   JunctionState.initialize()                                    │
│         │                                                       │
│         ▼                                                       │
│   JunctionUser.load_user()                                      │
│         │                                                       │
│         ▼                                                       │
│   get_connected_providers() ──► connected_sources = [...]       │
│                                                                 │
│   sleep_summary = []          ◄── NEVER POPULATED               │
│   activity_summary = []       ◄── NEVER POPULATED               │
│   workout_summary = []        ◄── NEVER POPULATED               │
│   body_summary = []           ◄── NEVER POPULATED               │
│   profile = {}                ◄── NEVER POPULATED               │
│   meal_summary = []           ◄── NEVER POPULATED               │
│                                                                 │
│   Developer gets: 3 text lines in demo showing "0" and "false"  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### After State

```
┌────────────────────────────────────────────────────────────────┐
│                          AFTER                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   wrap_app(app, api_key=...)                                    │
│         │                                                       │
│         ▼                                                       │
│   JunctionState.initialize()                                    │
│         │                                                       │
│         ▼                                                       │
│   JunctionUser.load_user()                                      │
│         │                                                       │
│         ├──► get_connected_providers()                          │
│         ├──► fetch_sleep(start, end)      ──► client.sleep.get  │
│         ├──► fetch_activity(start, end)   ──► client.activity   │
│         ├──► fetch_workouts(start, end)   ──► client.workouts   │
│         ├──► fetch_body(start, end)       ──► client.body.get   │
│         ├──► fetch_profile()              ──► client.profile     │
│         └──► fetch_meals(start, end)      ──► client.meal.get   │
│                                                                 │
│   sleep_data: list[SleepSummary]     = [SleepSummary(...), ...]│
│   activity_data: list[ActivitySummary] = [ActivitySummary(...)  │
│   workout_data: list[WorkoutSummary] = [WorkoutSummary(...)     │
│   body_data: list[BodyMeasurement]   = [BodyMeasurement(...)    │
│   user_profile: ProfileData | None   = ProfileData(...)         │
│   meal_data: list[MealSummary]       = [MealSummary(...)        │
│                                                                 │
│   chart_sleep_scores: list[dict]     ──► rx.recharts ready      │
│   chart_activity_steps: list[dict]   ──► rx.recharts ready      │
│                                                                 │
│   Developer gets: typed data + chart-ready computed vars         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Interaction Changes

| Location | Before | After | User Impact |
|----------|--------|-------|-------------|
| `JunctionUser.load_user()` | Only calls `get_connected_providers()` | Calls all 6 `fetch_*` methods | Health data auto-populated on auth |
| `JunctionUser.sleep_summary` | `list[dict[str, Any]] = []` (always empty) | `sleep_data: list[SleepSummary]` (populated) | Type-safe sleep data with IDE autocomplete |
| `JunctionUser.profile` | `dict[str, Any] = {}` (always empty) | `user_profile: ProfileData \| None` (populated) | Typed profile data |
| New: `fetch_sleep(start, end)` | N/A | Fetches sleep data for date range | On-demand data refresh |
| New: `chart_sleep_scores` | N/A | `@rx.var` returning `list[dict]` | Direct recharts integration |

---

## Mandatory Reading

**CRITICAL: Implementation agent MUST read these files before starting any task:**

| Priority | File | Lines | Why Read This |
|----------|------|-------|---------------|
| P0 | `custom_components/reflex_junction/junction_provider.py` | 29-98 | JunctionState class structure, ClassVar pattern, client property |
| P0 | `custom_components/reflex_junction/junction_provider.py` | 148-181 | Event handler pattern to MIRROR (create_user, get_connected_providers) |
| P0 | `custom_components/reflex_junction/junction_provider.py` | 248-274 | JunctionUser — target class for modifications |
| P0 | `custom_components/reflex_junction/models.py` | all | Existing model definitions to extend |
| P1 | `tests/test_state.py` | 15-28 | _reset_state fixture pattern |
| P1 | `tests/test_state.py` | 100-140 | mock_client / state fixture + event handler test pattern |
| P1 | `custom_components/reflex_junction/__init__.py` | all | Export pattern to update |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/client_facing_sleep.py` | all | SDK type fields for SleepSummary |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/client_facing_activity.py` | all | SDK type fields for ActivitySummary |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/client_facing_workout.py` | all | SDK type fields for WorkoutSummary |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/client_facing_body.py` | all | SDK type fields for BodyMeasurement |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/client_facing_profile.py` | all | SDK type fields for ProfileData |
| P2 | `.venv/lib/python3.13/site-packages/vital/types/meal_in_db_base_client_facing_source.py` | all | SDK type fields for MealSummary |

**External Documentation:**

| Source | Section | Why Needed |
|--------|---------|------------|
| [Vital SDK — vital-python](https://github.com/tryVital/vital-python) | reference.md | Method signatures for sleep/activity/workouts/body/profile/meal |
| [Reflex Custom Vars](https://reflex.dev/docs/vars/custom-vars/) | Dataclass support | Confirms `@dataclass` works as state var type |
| [Reflex Recharts](https://reflex.dev/docs/library/graphing/general/) | Data format | `data: Sequence[dict[str, Any]]` — list of dicts with string keys |

---

## Patterns to Mirror

**STATE_VAR_DECLARATION:**
```python
# SOURCE: junction_provider.py:37-43
# COPY THIS PATTERN — per-session state vars with typed defaults:
class JunctionState(rx.State):
    junction_user_id: str = ""
    client_user_id: str = ""
    connected_sources: list[dict[str, Any]] = []
    is_initialized: bool = False
    _link_token: str = ""
```

**EVENT_HANDLER_WITH_SDK_CALL:**
```python
# SOURCE: junction_provider.py:159-181
# COPY THIS PATTERN — guard → SDK call → transform → assign:
@rx.event
async def get_connected_providers(self) -> None:
    if not self.junction_user_id:
        logger.warning("No junction_user_id set. Call create_user() first.")
        return
    result = await self.client.user.get_connected_providers(
        user_id=self.junction_user_id
    )
    providers = []
    for source_type, source_list in result.items():
        for source in source_list:
            providers.append({...})
    self.connected_sources = providers
```

**ERROR_HANDLING_IN_LOAD:**
```python
# SOURCE: junction_provider.py:267-274
# COPY THIS PATTERN — try/except for data fetch in load_user:
try:
    await self.get_connected_providers()
except Exception:
    logger.exception("Failed to load connected providers")
```

**MODEL_DEFINITION:**
```python
# SOURCE: models.py:6-14
# REFERENCE — but we'll use @dataclass instead of PropsBase:
class JunctionConfig(PropsBase):
    """Configuration for the Junction health data integration."""
    environment: str = "sandbox"
    """The Junction environment."""
    region: str = "us"
    """The region for data storage."""
```

**TEST_MOCK_CLIENT:**
```python
# SOURCE: tests/test_state.py:107-128
# COPY THIS PATTERN — mock client fixture:
@pytest.fixture()
def mock_client(self):
    client = MagicMock()
    client.user.create = AsyncMock(return_value=MagicMock(user_id="vital-user-123"))
    client.user.get_connected_providers = AsyncMock(return_value={})
    return client

@pytest.fixture()
def state(self, mock_client):
    JunctionState._api_key = "sk_test_123"
    JunctionState._client = mock_client
    s = JunctionState()
    return s
```

**TEST_EVENT_INVOCATION:**
```python
# SOURCE: tests/test_state.py:131-135
# COPY THIS PATTERN — call .fn() to bypass Reflex dispatch:
@pytest.mark.asyncio()
async def test_create_user_calls_sdk(self, state, mock_client):
    await JunctionState.create_user.fn(state, "app-user-1")
    mock_client.user.create.assert_called_once_with(client_user_id="app-user-1")
    assert state.junction_user_id == "vital-user-123"
```

**EXPORT_PATTERN:**
```python
# SOURCE: __init__.py:1-33
# COPY THIS PATTERN — version, imports, __all__:
from .models import (JunctionConfig, LinkConfig, ProviderInfo)
__all__ = ["JunctionConfig", "LinkConfig", "ProviderInfo", ...]
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `custom_components/reflex_junction/models.py` | UPDATE | Add 6 health data `@dataclass` models + `SourceInfo` |
| `custom_components/reflex_junction/junction_provider.py` | UPDATE | Add fetch methods to JunctionUser, update load_user(), rename state vars |
| `custom_components/reflex_junction/__init__.py` | UPDATE | Export new model classes |
| `tests/test_models.py` | UPDATE | Add tests for new dataclass models |
| `tests/test_health_data.py` | CREATE | Tests for all 6 fetch methods + load_user integration |

---

## NOT Building (Scope Limits)

- **State mixins** — PRD mentions `SleepMixin` etc., but keeping methods directly on `JunctionUser` is simpler and avoids Reflex multi-inheritance risks. Can refactor to mixins in a later phase if the class gets too large.
- **Vitals timeseries** (HR, HRV, SpO2 etc.) — that's Phase 2
- **Link widget component** — that's Phase 3
- **Webhooks** — that's Phase 4
- **Lab testing** — that's Phase 5
- **Demo app changes** — that's Phase 7 (demo will use the new typed data)
- **Chart-ready computed vars** — including a few simple ones for reference, but full chart integration is Phase 7

---

## Step-by-Step Tasks

### Task 1: CREATE health data dataclass models in `models.py`

- **ACTION**: Add `@dataclass` models to the existing `models.py` file
- **IMPLEMENT**: Create these models (all fields optional with defaults, matching Vital SDK response types):

```python
from dataclasses import dataclass, field
from datetime import datetime

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
    duration: int = 0        # seconds
    total: int = 0           # total sleep seconds
    awake: int = 0           # seconds
    light: int = 0           # seconds
    rem: int = 0             # seconds
    deep: int = 0            # seconds
    score: int | None = None # 1-100
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
    distance: float | None = None     # meters
    low: float | None = None          # minutes
    medium: float | None = None       # minutes
    high: float | None = None         # minutes
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
    duration: int = 0         # seconds (moving_time)
    calories: float | None = None
    distance: float | None = None   # meters
    average_hr: int | None = None
    max_hr: int | None = None
    average_speed: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)

@dataclass
class BodyMeasurement:
    """Body composition measurement."""
    id: str = ""
    calendar_date: str = ""
    weight: float | None = None      # kg
    fat: float | None = None         # %
    body_mass_index: float | None = None
    muscle_mass_percentage: float | None = None
    water_percentage: float | None = None
    source: SourceInfo = field(default_factory=SourceInfo)

@dataclass
class ProfileData:
    """User health profile from provider."""
    id: str = ""
    height: int | None = None         # cm
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
```

- **MIRROR**: Follow `models.py` docstring style (class docstring + field docstrings on complex fields)
- **IMPORTS**: Add `from dataclasses import dataclass, field` at top of models.py
- **GOTCHA**: Use `str` for datetime fields (not `datetime`) — Vital SDK returns ISO strings, and str is JSON-serializable without special handling. Use `field(default_factory=SourceInfo)` for mutable defaults.
- **VALIDATE**: `uv run pyright`

### Task 2: ADD `_source_from_sdk()` helper to `junction_provider.py`

- **ACTION**: Add a private helper function that converts a Vital SDK `ClientFacingSource` to our `SourceInfo` dataclass
- **IMPLEMENT**:
```python
def _source_from_sdk(source: Any) -> SourceInfo:
    """Convert a Vital SDK source object to SourceInfo."""
    return SourceInfo(
        provider=getattr(source, "provider", ""),
        type=getattr(source, "type", ""),
        app_id=getattr(source, "app_id", ""),
    )
```
- **LOCATION**: Module-level function in `junction_provider.py`, before the `JunctionState` class
- **IMPORTS**: Add `from .models import (SourceInfo, SleepSummary, ActivitySummary, WorkoutSummary, BodyMeasurement, ProfileData, MealSummary)` at the top of the file
- **MIRROR**: Uses `getattr(obj, field, default)` pattern from `get_connected_providers` (junction_provider.py:174-180)
- **VALIDATE**: `uv run pyright`

### Task 3: ADD `fetch_sleep` event handler to `JunctionUser`

- **ACTION**: Add async event handler that fetches sleep data from Vital SDK
- **IMPLEMENT**:
```python
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
```
- **STATE VAR CHANGE**: Rename `sleep_summary: list[dict[str, Any]] = []` → `sleep_data: list[SleepSummary] = []` on `JunctionUser`
- **MIRROR**: `get_connected_providers` pattern (guard → SDK call → transform → assign)
- **GOTCHA**: SDK returns `ClientSleepResponse` with `.sleep` attribute (list). Use `getattr` with defaults for all optional fields since SDK types may return `None`.
- **VALIDATE**: `uv run pyright`

### Task 4: ADD `fetch_activity` event handler to `JunctionUser`

- **ACTION**: Same pattern as Task 3 for activity data
- **IMPLEMENT**: Same guard → `self.client.activity.get(**kwargs)` → `result.activity` → list comprehension building `ActivitySummary` objects
- **STATE VAR CHANGE**: Rename `activity_summary` → `activity_data: list[ActivitySummary] = []`
- **GOTCHA**: SDK returns `ClientActivityResponse` with `.activity` attribute
- **VALIDATE**: `uv run pyright`

### Task 5: ADD `fetch_workouts` event handler to `JunctionUser`

- **ACTION**: Same pattern for workout data
- **IMPLEMENT**: `self.client.workouts.get(**kwargs)` → `result.workouts` → list of `WorkoutSummary`
- **STATE VAR CHANGE**: Rename `workout_summary` → `workout_data: list[WorkoutSummary] = []`
- **GOTCHA**: `sport` is a nested object with `name` and `slug` — extract as `sport_name=getattr(getattr(s, "sport", None), "name", "")`. The `moving_time` field maps to `duration`.
- **VALIDATE**: `uv run pyright`

### Task 6: ADD `fetch_body` event handler to `JunctionUser`

- **ACTION**: Same pattern for body measurements
- **IMPLEMENT**: `self.client.body.get(**kwargs)` → `result.body` → list of `BodyMeasurement`
- **STATE VAR CHANGE**: Rename `body_summary` → `body_data: list[BodyMeasurement] = []`
- **VALIDATE**: `uv run pyright`

### Task 7: ADD `fetch_profile` event handler to `JunctionUser`

- **ACTION**: Fetch profile data — NOTE: different SDK signature (no start_date/end_date)
- **IMPLEMENT**:
```python
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
        birth_date=str(getattr(result, "birth_date", "")) if getattr(result, "birth_date", None) else None,
        gender=str(getattr(result, "gender", "")) if getattr(result, "gender", None) else None,
        sex=str(getattr(result, "sex", "")) if getattr(result, "sex", None) else None,
        source=_source_from_sdk(getattr(result, "source", None)),
    )
```
- **STATE VAR CHANGE**: Rename `profile: dict[str, Any] = {}` → `user_profile: ProfileData | None = None`
- **GOTCHA**: `client.profile.get()` returns `ClientFacingProfile` directly — NOT a wrapper with a list. It takes `user_id` and optional `provider` only — NO `start_date`/`end_date`.
- **VALIDATE**: `uv run pyright`

### Task 8: ADD `fetch_meals` event handler to `JunctionUser`

- **ACTION**: Same pattern for meal data
- **IMPLEMENT**: `self.client.meal.get(**kwargs)` → `result.meals` → list of `MealSummary`
- **STATE VAR CHANGE**: Rename `meal_summary` → `meal_data: list[MealSummary] = []`
- **GOTCHA**: Meal SDK type is `MealInDbBaseClientFacingSource`. Energy/macros are nested objects — extract `calories=getattr(getattr(m, "energy", None), "value", None)`, `protein=getattr(getattr(m, "macros", None), "protein", None)`, etc.
- **VALIDATE**: `uv run pyright`

### Task 9: UPDATE `load_user()` and add computed vars

- **ACTION**: Update `JunctionUser.load_user()` to fetch all health data, add chart-ready computed vars
- **IMPLEMENT**:
```python
@rx.event
async def load_user(self) -> None:
    """Load the current user's connections and health data."""
    if not self.junction_user_id:
        return
    # Default range: last 30 days
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=30)
    start_str = start.isoformat()
    end_str = end.isoformat()

    try:
        await self.get_connected_providers()
    except Exception:
        logger.exception("Failed to load connected providers")

    for fetch_fn, args in [
        (self.fetch_sleep, (start_str, end_str)),
        (self.fetch_activity, (start_str, end_str)),
        (self.fetch_workouts, (start_str, end_str)),
        (self.fetch_body, (start_str, end_str)),
        (self.fetch_profile, ()),
        (self.fetch_meals, (start_str, end_str)),
    ]:
        try:
            await fetch_fn.fn(self, *args)  # Call .fn() directly for internal chaining
        except Exception:
            logger.exception("Failed to fetch %s", fetch_fn.__name__)
```
- **ADD computed vars** for recharts compatibility:
```python
@rx.var
def chart_sleep_scores(self) -> list[dict[str, Any]]:
    """Sleep scores for recharts (date + score)."""
    return [
        {"date": s.calendar_date, "score": s.score or 0, "duration_hrs": round(s.total / 3600, 1)}
        for s in self.sleep_data if s.score is not None
    ]

@rx.var
def chart_activity_steps(self) -> list[dict[str, Any]]:
    """Daily steps for recharts (date + steps)."""
    return [
        {"date": a.calendar_date, "steps": a.steps or 0, "calories": round(a.calories_active or 0)}
        for a in self.activity_data
    ]

@rx.var
def latest_body(self) -> BodyMeasurement | None:
    """Most recent body measurement."""
    return self.body_data[-1] if self.body_data else None
```
- **GOTCHA**: Call `fetch_fn.fn(self, *args)` (not `await self.fetch_sleep(...)`) to invoke the underlying coroutine directly within `load_user` — avoids going through Reflex event dispatch for internal chaining.
- **VALIDATE**: `uv run pyright && uv run ruff check .`

### Task 10: UPDATE `__init__.py` exports and CREATE tests

- **ACTION**: Export new models + write comprehensive tests
- **IMPLEMENT (exports)**: Add to `__init__.py`:
```python
from .models import (
    ActivitySummary,
    BodyMeasurement,
    JunctionConfig,
    LinkConfig,
    MealSummary,
    ProfileData,
    ProviderInfo,
    SleepSummary,
    SourceInfo,
    WorkoutSummary,
)
```
Update `__all__` to include all new model names.

- **IMPLEMENT (tests)**: Create `tests/test_health_data.py` with:
  - `TestSleepSummary`: default values, custom values, source info
  - `TestActivitySummary`: same pattern
  - `TestWorkoutSummary`, `TestBodyMeasurement`, `TestProfileData`, `TestMealSummary`
  - `TestFetchSleep`: mock `client.sleep.get` → `AsyncMock(return_value=MagicMock(sleep=[...]))` → verify `state.sleep_data` populated with correct types
  - `TestFetchActivity`, `TestFetchWorkouts`, `TestFetchBody`, `TestFetchProfile`, `TestFetchMeals`: same pattern
  - `TestLoadUser`: verify all fetch methods are called, verify error in one fetch doesn't prevent others
  - Use the existing `_reset_state` fixture pattern and `mock_client`/`state` fixture pattern from `test_state.py`
  - Call handlers via `JunctionUser.fetch_sleep.fn(state, start_date, end_date)`

- **MIRROR**: `tests/test_state.py` — class-based tests, `@pytest.mark.asyncio()`, `MagicMock`/`AsyncMock`
- **VALIDATE**: `uv run pytest tests/ -v`

---

## Testing Strategy

### Unit Tests to Write

| Test File | Test Cases | Validates |
|-----------|------------|-----------|
| `tests/test_models.py` (update) | SleepSummary/ActivitySummary/etc. defaults, custom values, SourceInfo | Dataclass models |
| `tests/test_health_data.py` (create) | fetch_sleep, fetch_activity, fetch_workouts, fetch_body, fetch_profile, fetch_meals — happy path + empty response + error | All fetch event handlers |
| `tests/test_health_data.py` | load_user calls all fetches, error isolation, chart computed vars | Integration of load_user |

### Edge Cases Checklist

- [ ] Empty response from SDK (e.g., no sleep data for date range) → `sleep_data = []`
- [ ] SDK returns `None` for optional fields → dataclass defaults handle gracefully
- [ ] Profile fetch returns single object (not list) — different from other endpoints
- [ ] `junction_user_id` not set → early return with warning (no crash)
- [ ] SDK raises exception in one fetch → `load_user` continues with other fetches
- [ ] Nested `source` object is `None` → `_source_from_sdk(None)` returns default `SourceInfo()`
- [ ] Meal energy/macros are nested objects that may be `None`
- [ ] Workout `sport` is nested object that may be `None`
- [ ] Date strings from SDK may have varying formats — store as-is (str)

---

## Validation Commands

### Level 1: STATIC_ANALYSIS

```bash
uv run ruff check . && uv run pyright
```

**EXPECT**: Exit 0, no errors

### Level 2: UNIT_TESTS

```bash
uv run pytest tests/ -v
```

**EXPECT**: All tests pass (existing + new)

### Level 3: FULL_SUITE

```bash
uv run ruff check . && uv run pyright && uv run pytest tests/ -v
```

**EXPECT**: All pass

### Level 6: MANUAL_VALIDATION

1. Start the demo app: `cd junction_demo && uv run reflex run`
2. Verify app starts without import errors
3. Check that `JunctionUser` is importable: `from reflex_junction import JunctionUser, SleepSummary`
4. Verify new model types are accessible: `from reflex_junction import SleepSummary, ActivitySummary, WorkoutSummary, BodyMeasurement, ProfileData, MealSummary`

---

## Acceptance Criteria

- [ ] All 6 health data fields on `JunctionUser` are typed dataclasses (not `dict[str, Any]`)
- [ ] All 6 `fetch_*` event handlers exist and call the correct Vital SDK methods
- [ ] `load_user()` calls all 6 fetch methods with 30-day default range
- [ ] Error in one fetch does not prevent other fetches in `load_user()`
- [ ] At least 2 `@rx.var` computed vars provide recharts-ready data
- [ ] All new models exported from `__init__.py`
- [ ] Level 1-3 validation passes
- [ ] 20+ new test cases covering models + fetch handlers + load_user

---

## Completion Checklist

- [ ] Task 1: Health data dataclass models created in models.py
- [ ] Task 2: `_source_from_sdk` helper added
- [ ] Task 3: `fetch_sleep` + `sleep_data` state var
- [ ] Task 4: `fetch_activity` + `activity_data` state var
- [ ] Task 5: `fetch_workouts` + `workout_data` state var
- [ ] Task 6: `fetch_body` + `body_data` state var
- [ ] Task 7: `fetch_profile` + `user_profile` state var
- [ ] Task 8: `fetch_meals` + `meal_data` state var
- [ ] Task 9: `load_user()` updated + chart computed vars
- [ ] Task 10: Exports updated + tests created
- [ ] Level 1: `ruff check` + `pyright` pass
- [ ] Level 2: All tests pass
- [ ] Level 3: Full suite passes

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dataclass state vars fail to serialize in Reflex | Low | High | Verified: Reflex 0.8.27 has `is_dataclass()` check + fallback serializer. If issues arise, fall back to `list[dict]` with `.model_dump()` |
| Vital SDK response fields differ from docs | Low | Medium | Use `getattr(obj, field, default)` pattern throughout — never direct attribute access |
| Renaming state vars breaks existing consumers | Medium | Medium | Old vars (`sleep_summary`) replaced with new names (`sleep_data`). This is a breaking change but acceptable at v0.1.0 (pre-stable). Document in changelog. |
| Nested SourceInfo dataclass fails proxy tracking | Low | Low | SourceInfo is simple — only primitive fields. If issues arise, replace with flat str fields on parent. |

---

## Notes

**Design Decisions:**
- **Dataclasses over PropsBase**: PropsBase converts field names to camelCase (designed for React prop passing). Health data models are for state storage and Python consumption — snake_case is correct.
- **Dataclasses over Pydantic**: Avoids coupling to Vital SDK's frozen Pydantic models. Simple `@dataclass` is lightest weight and fully supported by Reflex.
- **`getattr` everywhere**: Vital SDK types are auto-generated (Fern) and may add/remove fields. `getattr` with defaults is defensive and won't break on SDK updates.
- **No mixins (yet)**: Keeping all methods on `JunctionUser` directly. If the class exceeds ~500 lines in later phases, refactor to mixins.
- **Renamed state vars**: `sleep_summary` → `sleep_data`, `profile` → `user_profile`, etc. Avoids naming collision with SDK types and is more descriptive.
- **Chart vars as computed**: `chart_sleep_scores` etc. are `@rx.var` computed from typed state — they produce `list[dict]` for recharts without storing duplicate data.
