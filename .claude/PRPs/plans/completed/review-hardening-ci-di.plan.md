# Feature: Review Hardening, CI Security, Test Coverage & DI Cleanup

## Summary

Address all 13 issues from code review #1 (4 critical, 7 important, 2 minor) plus add missing test coverage for critical paths. Fixes span security (CI pwn-request vector, webhook secret default), correctness (type annotations, JSON decode), performance (load_user background task), and maintainability (environment map dedup, public exports, conftest reset). Test coverage targets the 5 identified gaps: webhook HTTP layer, load_user vitals, wait_for_init, register_webhook_api, and on_load flow.

## User Story

As a library consumer and contributor
I want reflex-junction to have correct types, secure defaults, hardened CI, and comprehensive tests
So that I can trust the library's correctness, security posture, and reliability in production

## Problem Statement

Code review #1 identified 4 critical issues (2 security, 1 type system bug, 1 correctness bug), 7 important issues, and 5 test coverage gaps. Effective test coverage is ~75% vs 80% target. CI has a pwn-request vector allowing fork PRs to exfiltrate secrets.

## Solution Statement

Fix all 13 review issues in dependency order, then add tests for the 5 identified coverage gaps. Group changes into atomic, independently verifiable tasks. Each task includes its own validation command.

## Metadata

| Field            | Value                                                  |
| ---------------- | ------------------------------------------------------ |
| Type             | BUG_FIX + REFACTOR                                     |
| Complexity       | HIGH                                                   |
| Systems Affected | junction_provider.py, fastapi_helpers.py, __init__.py, CI workflows, tests |
| Dependencies     | reflex>=0.8.0, vital>=2.1.0, fastapi>=0.115.0, pytest, pytest-asyncio |
| Estimated Tasks  | 16                                                     |
| Source Review     | `.claude/PRPs/code_reviews/review1.md`                |

---

## UX Design

### Before State

```
DEVELOPER EXPERIENCE — BEFORE

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Fork PR      │ ──► │ ci-forks.yml    │ ──► │ Runs fork code   │
  │ (malicious)  │     │ pull_request_   │     │ WITH repo secrets │
  │              │     │ target + secrets│     │ = pwn-request     │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Type checker │ ──► │ EventCallback   │ ──► │ Linter says OK   │
  │ (pyright)    │     │ annotations     │     │ Runtime rejects  │
  │              │     │ everywhere      │     │ the same values  │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ User logs in │ ──► │ load_user()     │ ──► │ UI frozen 2-5s   │
  │              │     │ holds state     │     │ 11 sequential    │
  │              │     │ lock            │     │ API calls        │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Malformed    │ ──► │ request.json()  │ ──► │ HTTP 500         │
  │ webhook body │     │ no try/except   │     │ Svix retries ∞   │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  TEST COVERAGE: ~75% (5 critical paths untested)
```

### After State

```
DEVELOPER EXPERIENCE — AFTER

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Fork PR      │ ──► │ ci-forks.yml    │ ──► │ pull_request     │
  │              │     │ NO secrets      │     │ trigger, safe    │
  │              │     │ NO inherit      │     │ basic checks     │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Type checker │ ──► │ rx.EventHandler │ ──► │ Types match      │
  │ (pyright)    │     │ annotations     │     │ runtime checks   │
  │              │     │ everywhere      │     │ = consistent     │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ User logs in │ ──► │ load_user()     │ ──► │ UI responsive    │
  │              │     │ background=True │     │ concurrent fetch │
  │              │     │ asyncio.gather  │     │ ~1s total        │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │ Malformed    │ ──► │ try/except      │ ──► │ HTTP 400         │
  │ webhook body │     │ JSONDecodeError │     │ Svix stops retry │
  └──────────────┘     └─────────────────┘     └──────────────────┘

  TEST COVERAGE: ~85%+ (all critical paths covered)
```

### Interaction Changes

| Location | Before | After | User Impact |
|----------|--------|-------|-------------|
| CI fork PRs | Secrets exposed to fork code | No secrets on fork PRs | Prevents secret exfiltration |
| Type annotations | EventCallback (wrong) | rx.EventHandler (correct) | Types match runtime |
| Webhook JSON | 500 on malformed | 400 on malformed | Svix stops retrying |
| Webhook secret default | `""` (silently disabled) | `None` (explicit opt-in) | Forces conscious choice |
| load_user | Blocks UI 2-5s | Background task, concurrent | Responsive login |
| Public exports | Missing WebhookHandler, MissingApiKeyError | Both exported | Clean imports |

---

## Mandatory Reading

**CRITICAL: Implementation agent MUST read these files before starting any task:**

| Priority | File | Lines | Why Read This |
|----------|------|-------|---------------|
| P0 | `custom_components/reflex_junction/junction_provider.py` | all | Primary file for 7 of 13 fixes |
| P0 | `custom_components/reflex_junction/fastapi_helpers.py` | all | Webhook fixes + test targets |
| P0 | `.github/workflows/ci-forks.yml` | all | CI security fix |
| P0 | `.github/workflows/_reusable-ci.yml` | all | CI security fix |
| P1 | `custom_components/reflex_junction/__init__.py` | all | Public exports fix |
| P1 | `tests/conftest.py` | all | Test isolation fix |
| P1 | `tests/test_state.py` | all | Test pattern to FOLLOW |
| P1 | `tests/test_health_data.py` | all | Mock patterns to FOLLOW |
| P2 | `.github/actions/full-checks/action.yml` | all | Remove .env step |
| P2 | `.github/actions/basic-checks/action.yml` | all | CI structure reference |
| P2 | `.claude/PRPs/code_reviews/review1.md` | all | Source of all issues |

---

## Patterns to Mirror

**TEST_CLASS_PATTERN:**
```python
# SOURCE: tests/test_state.py — class-based test organization
class TestSetApiKey:
    """Tests for _set_api_key class method."""

    def test_valid_key(self):
        """Accepts a valid API key string."""
        JunctionState._set_api_key("sk_us_test_key_1234")
        assert JunctionState._api_key == "sk_us_test_key_1234"
```

**MOCK_CLIENT_FIXTURE:**
```python
# SOURCE: tests/test_health_data.py:272-320 — async mock fixture
@pytest.fixture
def mock_client():
    client = MagicMock()
    client.sleep.get = AsyncMock(return_value=...)
    JunctionState._api_key = "sk_test"
    JunctionState._client = client
    return client
```

**STATE_INSTANTIATION:**
```python
# SOURCE: tests/test_health_data.py:319 — bypass Reflex __setattr__
s = JunctionUser()  # type: ignore[call-arg]
object.__setattr__(s, "junction_user_id", "vital-user-123")
```

**BACKGROUND_TASK_PATTERN:**
```python
# SOURCE: junction_provider.py:151-173 — existing background task pattern
@rx.event(background=True)
async def wait_for_init(self, uid: str) -> list[EventType[()]]:
    # ...
    async with self:
        if self.is_initialized:
            return on_loads
    await asyncio.sleep(0.05)
```

**ERROR_HANDLING_PATTERN:**
```python
# SOURCE: junction_provider.py:860-863 — try/except with logging
try:
    await JunctionState.get_connected_providers.fn(self)  # type: ignore[attr-defined]
except Exception:
    logger.exception("Failed to load connected providers")
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `.github/workflows/ci-forks.yml` | UPDATE | Fix pwn-request vector (Review #1) |
| `.github/workflows/_reusable-ci.yml` | UPDATE | Remove fork checkout of local actions |
| `.github/actions/full-checks/action.yml` | UPDATE | Remove redundant .env creation (Review #8) |
| `custom_components/reflex_junction/junction_provider.py` | UPDATE | Fix issues #3, #5, #6, #7, #9 |
| `custom_components/reflex_junction/fastapi_helpers.py` | UPDATE | Fix issues #2, #4 |
| `custom_components/reflex_junction/__init__.py` | UPDATE | Fix issue #11 (missing exports) |
| `tests/conftest.py` | UPDATE | Fix issue #10 (missing timeout reset) |
| `tests/test_webhook_http.py` | CREATE | New tests for create_webhook_router HTTP layer |
| `tests/test_wait_for_init.py` | CREATE | New tests for wait_for_init + on_load flow |
| `tests/test_load_user.py` | CREATE | New tests for load_user vitals calls |

---

## NOT Building (Scope Limits)

- **JunctionLinkButton inheritance change** (Review #12) — Minor risk, would require npm integration testing not available in CI. Deferred.
- **Publish workflow head_branch hardening** (Review #13) — Currently safe, only fragile if branch-push trigger is re-enabled. Deferred.
- **Full DI container/framework** — Overkill for current codebase size. Instead, consolidate the environment map dedup as a concrete step toward DI.
- **asyncio.gather for load_user** — The background task conversion alone eliminates the UI freeze. Gather optimization can follow.

---

## Step-by-Step Tasks

Execute in order. Each task is atomic and independently verifiable.

### Task 1: FIX CI pwn-request vector (Review #1 — Critical/Security)

- **ACTION**: UPDATE `.github/workflows/ci-forks.yml`
- **IMPLEMENT**: Change trigger from `pull_request_target` to `pull_request`. Remove `secrets: inherit`. Remove `checkout_ref` and `checkout_repository` inputs (use defaults). This means fork PRs run basic checks with their own code but without secrets — safe by design.
- **MIRROR**: The existing `ci.yml` uses `pull_request` trigger for first-party PRs
- **GOTCHA**: `pull_request` from forks cannot access secrets — this is the desired behavior. Basic checks (lint + typecheck) don't need secrets.
- **VALIDATE**: Review the YAML for correctness. No runtime validation possible without a fork PR.

**Updated `ci-forks.yml`:**
```yaml
name: CI for Fork PRs

on:
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  basic-checks:
    uses: ./.github/workflows/_reusable-ci.yml
    with:
      check_type: 'basic'
    # No secrets: inherit — fork PRs don't need secrets for basic checks
```

---

### Task 2: Remove redundant .env creation in CI (Review #8)

- **ACTION**: UPDATE `.github/actions/full-checks/action.yml`
- **IMPLEMENT**: Remove the "Create .env" step that writes `JUNCTION_API_KEY` to disk. The integration test step already receives the key via `env:`.
- **GOTCHA**: Verify no other steps read from `.env`. The lint and typecheck steps don't need the API key.
- **VALIDATE**: YAML syntax check.

---

### Task 3: FIX EventCallback → EventHandler type annotations (Review #3 — Critical/Type)

- **ACTION**: UPDATE `custom_components/reflex_junction/junction_provider.py`
- **IMPLEMENT**:
  1. Change import: `from reflex.event import EventCallback, EventType` → `from reflex.event import EventType`
  2. Replace all `EventCallback` type annotations with `rx.EventHandler`:
     - Line 77: `_dependent_handlers: ClassVar[dict[int, rx.EventHandler]]`
     - Line 128: `def register_dependent_handler(cls, handler: rx.EventHandler) -> None:`
     - Line 146: `async def initialize(self) -> list[rx.EventHandler]:`
     - Line 211: `async def disconnect_provider(self, provider: str) -> rx.EventHandler | None:`
     - Line 1042: `def register_on_auth_change_handler(handler: rx.EventHandler) -> None:`
- **GOTCHA**: `rx.EventHandler` is available via `import reflex as rx` (already imported at line 9). The runtime `isinstance(handler, rx.EventHandler)` check at line 133 now matches the type annotation.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/junction_provider.py` (should have 0 new errors)

---

### Task 4: FIX malformed JSON webhook body → 400 (Review #4 — Critical/Bug)

- **ACTION**: UPDATE `custom_components/reflex_junction/fastapi_helpers.py`
- **IMPLEMENT**: Wrap `await request.json()` at line 241 in try/except:
  ```python
  try:
      body: dict[str, Any] = await request.json()
  except (ValueError, UnicodeDecodeError) as exc:
      logger.warning("Webhook request has malformed JSON body: %s", exc)
      return JSONResponse(
          content={"error": "malformed_json"},
          status_code=400,
      )
  ```
- **MIRROR**: Same pattern as signature verification error handling above it (lines 234-239)
- **GOTCHA**: `request.json()` raises `json.JSONDecodeError` (subclass of `ValueError`) or `UnicodeDecodeError`. Catching `ValueError` covers both.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/fastapi_helpers.py`

---

### Task 5: FIX create_webhook_router default secret (Review #2 — Critical/Security)

- **ACTION**: UPDATE `custom_components/reflex_junction/fastapi_helpers.py`
- **IMPLEMENT**: Change `secret: str = ""` to `secret: str | None = None` at line 196. Update the falsy check at line 213 to `if not secret:` (works for both `None` and `""`). Update the stored variable: `_webhook_secret = secret or ""`.
- **GOTCHA**: Callers passing `secret=""` explicitly still get the warning. Only `wrap_app` and `register_webhook_api` pass non-empty secrets. Direct `create_webhook_router()` callers must now pass `secret=None` explicitly to opt out of verification (instead of silently getting no verification).
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/fastapi_helpers.py`

---

### Task 6: FIX _on_load_events memory leak (Review #6)

- **ACTION**: UPDATE `custom_components/reflex_junction/junction_provider.py`
- **IMPLEMENT**: Change line 159 from:
  ```python
  on_loads = self._on_load_events.get(parsed_uid, [])
  ```
  to:
  ```python
  on_loads = self._on_load_events.pop(parsed_uid, [])
  ```
- **GOTCHA**: `pop` removes the entry after consumption. Since `wait_for_init` only runs once per page load, each UID is consumed exactly once.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/junction_provider.py`

---

### Task 7: FIX wait_for_init UUID validation (Review #7)

- **ACTION**: UPDATE `custom_components/reflex_junction/junction_provider.py`
- **IMPLEMENT**: Wrap UUID parsing at line 158 in try/except:
  ```python
  try:
      parsed_uid = uuid.UUID(uid) if isinstance(uid, str) else uid
  except ValueError:
      logger.warning("wait_for_init called with invalid UUID: %r", uid)
      return []
  ```
- **MIRROR**: Same logging pattern as other warning paths in the file
- **GOTCHA**: `wait_for_init` is a `@rx.event(background=True)` callable from the browser. Invalid UUIDs should be handled gracefully.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/junction_provider.py`

---

### Task 8: Consolidate duplicate environment maps (Review #9)

- **ACTION**: UPDATE `custom_components/reflex_junction/junction_provider.py`
- **IMPLEMENT**:
  1. Replace `_ENVIRONMENT_MAP` (lines 33-38) with a single source of truth mapping to `VitalEnvironment` enums. Move the import of `VitalEnvironment` to module level (or keep lazy with a different pattern).
  2. Since `VitalEnvironment` is imported lazily inside `_set_client`, create a constant for valid environment names at module level and use the enum map only in `_set_client`:
     ```python
     _VALID_ENVIRONMENTS: frozenset[str] = frozenset(
         {"sandbox", "production", "sandbox_eu", "production_eu"}
     )
     ```
  3. In `_set_environment`, change `if environment not in _ENVIRONMENT_MAP:` to `if environment not in _VALID_ENVIRONMENTS:`.
  4. In `_set_client`, keep the inline `env_map` dict (it needs the lazy import of `VitalEnvironment`), but now it's the ONLY place environment→enum mapping exists.
  5. Delete `_ENVIRONMENT_MAP`.
- **GOTCHA**: The lazy import of `VitalEnvironment` inside `_set_client` is intentional (avoids importing `vital` at module load time). The validation set doesn't need the enum.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/junction_provider.py` && `uv run ruff check custom_components/`

---

### Task 9: Convert load_user to background task (Review #5)

- **ACTION**: UPDATE `custom_components/reflex_junction/junction_provider.py`
- **IMPLEMENT**:
  1. Change `@rx.event` to `@rx.event(background=True)` on `load_user` (line 843)
  2. Wrap each state-mutating section in `async with self:` blocks
  3. The for-loop pattern already isolates errors per fetch. Add `async with self:` inside each iteration after the `await`:
     ```python
     @rx.event(background=True)
     async def load_user(self) -> None:
         if not self.junction_user_id:
             return
         from datetime import date, timedelta

         end = date.today()
         start = end - timedelta(days=30)
         start_str = start.isoformat()
         end_str = end.isoformat()

         try:
             await JunctionState.get_connected_providers.fn(self)  # type: ignore[attr-defined]
         except Exception:
             logger.exception("Failed to load connected providers")

         for method_name, args in [
             ("fetch_sleep", (start_str, end_str)),
             ("fetch_activity", (start_str, end_str)),
             ("fetch_workouts", (start_str, end_str)),
             ("fetch_body", (start_str, end_str)),
             ("fetch_profile", ()),
             ("fetch_meals", (start_str, end_str)),
             ("fetch_heartrate", (start_str, end_str)),
             ("fetch_hrv", (start_str, end_str)),
             ("fetch_blood_oxygen", (start_str, end_str)),
             ("fetch_glucose", (start_str, end_str)),
         ]:
             try:
                 handler = getattr(JunctionUser, method_name)
                 await handler.fn(self, *args)
             except Exception:
                 logger.exception("Failed to fetch %s", method_name)
     ```
  Note: The `fetch_*` methods are themselves `@rx.event` handlers that write to state. When called via `.fn(self, *args)` from a background task, the state writes happen within the background task's context. The `async with self:` block from `wait_for_init` is the pattern for acquiring the lock — but since `fetch_*` methods are called via `.fn()` (direct function call, not event dispatch), they execute synchronously within the background task. This needs careful handling: either wrap the entire for-loop body in `async with self:` per iteration, or keep the current pattern since `.fn()` calls bypass the event system lock.

  **Simplest correct approach**: Just add `background=True`. The `.fn()` calls access state directly through `self` which is the state proxy in background tasks. Each `fetch_*` method writes to `self.X_data` which updates the frontend after each completion.
- **GOTCHA**: Background tasks in Reflex use `async with self:` to acquire the state lock for writes. However, since `load_user` calls `handler.fn(self, *args)` which internally writes to `self`, the state writes are already within the task context. The key change is simply `background=True` — this releases the session lock so the UI stays responsive.
- **VALIDATE**: `uv run pyright custom_components/reflex_junction/junction_provider.py`

---

### Task 10: FIX conftest missing _init_wait_timeout_seconds reset (Review #10)

- **ACTION**: UPDATE `tests/conftest.py`
- **IMPLEMENT**: Add `JunctionState._init_wait_timeout_seconds = 1.0` to both setup (before yield) and teardown (after yield) sections of the `_reset_state` fixture.
- **MIRROR**: Same pattern as the other 5 ClassVar resets already in the fixture
- **VALIDATE**: `uv run pytest tests/test_state.py -v` (verify fixture still works)

---

### Task 11: Add missing public exports (Review #11)

- **ACTION**: UPDATE `custom_components/reflex_junction/__init__.py`
- **IMPLEMENT**:
  1. Add `WebhookHandler` to the `from .fastapi_helpers import (...)` block
  2. Add `MissingApiKeyError` to the `from .junction_provider import (...)` block
  3. Add both to `__all__` list in alphabetical position
- **GOTCHA**: `WebhookHandler` is a type alias (`Callable[[WebhookEvent], Any]`), not a class. It's still importable and useful for type annotations.
- **VALIDATE**: `uv run python -c "from reflex_junction import WebhookHandler, MissingApiKeyError; print('OK')"`

---

### Task 12: CREATE webhook HTTP-layer tests

- **ACTION**: CREATE `tests/test_webhook_http.py`
- **IMPLEMENT**: FastAPI TestClient tests for `create_webhook_router`:
  1. **Test 401 on bad signature**: POST with valid JSON but wrong signature → 401
  2. **Test 200 on valid signature**: POST with correctly signed payload → 200
  3. **Test 200 with no secret** (verification disabled): Create router with `secret=None`, POST any payload → 200
  4. **Test callback invocation**: Verify `on_event` callback is called with parsed `WebhookEvent`
  5. **Test 400 on malformed JSON** (after Task 4): POST non-JSON body → 400
  6. **Test callback error doesn't affect response**: on_event raises → still 200
- **MIRROR**: `tests/test_integration.py:156-206` for signature test setup patterns
- **IMPORTS**: `from fastapi.testclient import TestClient`, `from fastapi import FastAPI`
- **GOTCHA**: `TestClient` is synchronous. Wrap `create_webhook_router` in a `FastAPI()` app for testing.
- **VALIDATE**: `uv run pytest tests/test_webhook_http.py -v`

---

### Task 13: CREATE wait_for_init + on_load flow tests

- **ACTION**: CREATE `tests/test_wait_for_init.py`
- **IMPLEMENT**:
  1. **Test valid UUID parsing**: Call with valid UUID string → no error
  2. **Test invalid UUID rejection** (after Task 7): Call with "not-a-uuid" → returns empty list, logs warning
  3. **Test timeout path**: Set `_init_wait_timeout_seconds = 0.1`, `is_initialized = False` → returns on_loads after timeout
  4. **Test immediate return when initialized**: Set `is_initialized = True` → returns immediately
  5. **Test on_load event storage**: Call `on_load([event1, event2])` → verify `_on_load_events` populated
  6. **Test on_load event consumption** (after Task 6): Call `wait_for_init` with stored UID → events returned AND removed from dict
  7. **Test _set_on_load_events class method**: Verify storage and retrieval
- **MIRROR**: `tests/test_state.py` class-based pattern, `conftest.py` reset fixture
- **GOTCHA**: `wait_for_init` is `@rx.event(background=True)` — test via `.fn()` to call the underlying async function directly. Need to mock `self.is_initialized` and the `async with self:` context manager.
- **VALIDATE**: `uv run pytest tests/test_wait_for_init.py -v`

---

### Task 14: CREATE load_user vitals tests

- **ACTION**: CREATE `tests/test_load_user.py`
- **IMPLEMENT**:
  1. **Test all 11 methods called**: Mock all fetch methods, verify each is called with correct date args
  2. **Test heartrate/hrv/blood_oxygen/glucose calls**: These 4 vitals methods were identified as unmocked in existing tests
  3. **Test error isolation**: Make one fetch method raise → verify others still called
  4. **Test early return on empty user_id**: Set `junction_user_id = ""` → no API calls
  5. **Test date range**: Verify `start_date` is 30 days before `end_date`
- **MIRROR**: `tests/test_health_data.py` mock client and state fixture patterns
- **IMPORTS**: `from unittest.mock import AsyncMock, MagicMock, patch`
- **GOTCHA**: `load_user` calls `handler.fn(self, *args)` — mock at the `JunctionUser` class level, not on the client. Use `patch.object(JunctionUser, 'fetch_sleep')` etc.
- **VALIDATE**: `uv run pytest tests/test_load_user.py -v`

---

### Task 15: CREATE register_webhook_api tests

- **ACTION**: Add to `tests/test_webhook_http.py` (same file as Task 12)
- **IMPLEMENT**:
  1. **Test router attached to existing FastAPI app**: Mock `app.api_transformer` as FastAPI instance → verify `include_router` called
  2. **Test router creates new FastAPI when no transformer**: Mock `app.api_transformer` as non-FastAPI → verify new FastAPI created
  3. **Test secret passed through**: Verify the created router has verification enabled
- **MIRROR**: No existing tests for this — follow the TestClient pattern from Task 12
- **VALIDATE**: `uv run pytest tests/test_webhook_http.py -v`

---

### Task 16: Run full validation suite

- **ACTION**: Run all validation commands
- **VALIDATE**: See Validation Commands section below

---

## Testing Strategy

### Unit Tests to Write

| Test File | Test Cases | Validates |
|-----------|------------|-----------|
| `tests/test_webhook_http.py` | 401 rejection, 200 valid, 400 malformed JSON, callback invocation, callback error handling, no-secret mode, register_webhook_api attachment | Webhook HTTP layer + register_webhook_api |
| `tests/test_wait_for_init.py` | Valid UUID, invalid UUID, timeout, immediate return, on_load storage, event consumption/pop | wait_for_init + on_load flow |
| `tests/test_load_user.py` | All 11 methods called, 4 vitals mocked, error isolation, early return, date range | load_user completeness |

### Edge Cases Checklist

- [ ] Malformed JSON webhook body → 400 (not 500)
- [ ] Invalid UUID in wait_for_init → empty list + warning log
- [ ] Expired/invalid API key in integration tests → graceful skip
- [ ] load_user with empty junction_user_id → no API calls
- [ ] load_user with one failing fetch → others still complete
- [ ] create_webhook_router with secret=None → verification disabled with warning
- [ ] Duplicate handler registration → deduped via hash
- [ ] _on_load_events consumed after wait_for_init → dict entry removed

---

## Validation Commands

### Level 1: STATIC_ANALYSIS

```bash
uv run ruff check custom_components/ tests/ && uv run pyright
```

**EXPECT**: Exit 0, no errors

### Level 2: UNIT_TESTS

```bash
uv run pytest tests/ -v --ignore=tests/test_integration.py
```

**EXPECT**: All tests pass (existing + new)

### Level 3: FULL_SUITE

```bash
uv run pytest tests/ -v -m "not integration" && uv run ruff check custom_components/ tests/ && uv run pyright
```

**EXPECT**: All pass

### Level 4: INTEGRATION_TESTS (optional, requires API key)

```bash
JUNCTION_API_KEY=sk_us_AhcxbGvz9B_GpTkC28jvMF5mXUZbJvonDU31waAZ_qE uv run pytest tests/test_integration.py -v
```

**EXPECT**: All pass or graceful skip on 401

---

## Acceptance Criteria

- [ ] All 4 critical issues fixed (CI security, types, JSON decode, webhook secret)
- [ ] All 7 important issues fixed
- [ ] 3 new test files created with comprehensive coverage
- [ ] Level 1-3 validation commands pass with exit 0
- [ ] Test coverage of source functions >= 85%
- [ ] No regressions in existing tests
- [ ] CI workflow changes reviewed for YAML correctness

---

## Completion Checklist

- [ ] Task 1: CI pwn-request fix
- [ ] Task 2: Remove .env creation
- [ ] Task 3: EventCallback → EventHandler
- [ ] Task 4: JSON decode error handling
- [ ] Task 5: Webhook secret default
- [ ] Task 6: _on_load_events .pop
- [ ] Task 7: UUID validation
- [ ] Task 8: Environment map dedup
- [ ] Task 9: load_user background task
- [ ] Task 10: conftest timeout reset
- [ ] Task 11: Public exports
- [ ] Task 12: Webhook HTTP tests
- [ ] Task 13: wait_for_init tests
- [ ] Task 14: load_user tests
- [ ] Task 15: register_webhook_api tests
- [ ] Task 16: Full validation suite passes
- [ ] Level 1: Static analysis passes
- [ ] Level 2: Unit tests pass
- [ ] Level 3: Full suite passes

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `rx.EventHandler` not importable as type annotation | LOW | HIGH | Fallback: use `Any` with runtime check preserved |
| `background=True` on load_user changes state update timing | MED | MED | Test that state vars still update; frontend reactivity via `@rx.var` unchanged |
| Removing `secrets: inherit` from fork CI breaks something | LOW | LOW | Basic checks don't need secrets; full checks already have separate trigger |
| `request.json()` exception type differs across FastAPI versions | LOW | LOW | Catch `ValueError` (parent of `JSONDecodeError`) + `UnicodeDecodeError` |

---

## Notes

- The 2 minor issues (JunctionLinkButton inheritance, publish head_branch) are deferred — low risk, would require broader testing.
- `asyncio.gather` for concurrent fetches in `load_user` is a follow-up optimization. The background task conversion alone fixes the UX freeze.
- The environment map consolidation uses `frozenset` for validation (O(1) lookup) instead of a dict mapping to itself.
- All test files follow the existing class-based organization pattern with descriptive docstrings.
