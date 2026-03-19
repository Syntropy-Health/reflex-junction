# reflex-junction: Full Platform Coverage & Visual Demo

## Problem Statement

Health app developers using Reflex who want wearable/lab data integration have no good option. reflex-junction v0.1.0 wraps ~5% of the Vital SDK — it creates users and checks connections but never fetches any actual health data. The 6 health data fields on JunctionUser (`sleep_summary`, `activity_summary`, etc.) are declared but never populated. The demo shows three text lines. Developers can't evaluate the component's value without building everything themselves.

## Evidence

- JunctionUser.load_user() only calls get_connected_providers() — no health data fetch (junction_provider.py:263-274)
- All 6 health data fields remain at empty defaults permanently
- Vital SDK has 20+ namespaces, 100+ methods — reflex-junction uses 5
- Webhook handler is a no-op: logs event_type and returns {"status": "ok"}
- Link widget base class exists (base.py) but renders no UI component
- Demo app renders 3 static text lines with no user interaction possible
- Vital SDK provides sleep, activity, workouts, body, profile, meals, 50+ vitals timeseries, ECG, menstrual cycle, lab testing — none accessible through reflex-junction

## Proposed Solution

Wrap the complete Vital SDK surface into reflex-junction state classes with typed Reflex state vars and event handlers, then build a visual demo app that serves as both showcase and reference implementation. Every data type gets a dedicated state mixin, typed models (replacing `dict[str, Any]`), and a corresponding demo page with charts/visualizations.

## Key Hypothesis

We believe a complete Vital SDK wrapper with a visual demo will make reflex-junction the default choice for health data in Reflex apps.
We'll know we're right when developers install the package and use it in production apps (PyPI downloads > 100/month within 3 months, GitHub stars > 50).

## What We're NOT Building

- Mobile SDKs (Apple HealthKit / Android Health Connect) — these require native platform code, not a Python/Reflex concern
- Custom OAuth BYOO credential management — advanced enterprise feature, defer
- Junction Sense aggregate queries — closed beta, not production-accessible
- ETL pipeline management (Pub/Sub, RabbitMQ destinations) — org-level admin, not per-app
- Production deployment infrastructure — demo runs locally

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| SDK namespace coverage | 15+ of 20 namespaces wrapped | Code audit |
| Demo pages | 8+ interactive pages with visualizations | Manual review |
| PyPI downloads | >100/month within 3 months | PyPI stats |
| Demo startup time | <30 seconds from `reflex run` to interactive UI | Manual test |
| Test coverage | All new state methods have unit tests | pytest |

## Open Questions

- [ ] Vital sandbox — does the sandbox API key return meaningful synthetic data for all data types (sleep, activity, workouts, etc.), or only for connected demo providers?
- [ ] Link widget React component — is `@tryvital/vital-link` still the correct npm package, or has Vital migrated to a new package under the Junction rebrand?
- [ ] Lab testing in sandbox — can we simulate the full order lifecycle with the sandbox key?
- [ ] Rate limits — the refresh endpoint is limited to 8/hr/user; how does this affect demo UX?

---

## Users & Context

**Primary User**
- **Who**: Python developer building a health/wellness app with Reflex, needs wearable data integration
- **Current behavior**: Calls Vital SDK directly, manages state manually, builds their own UI from scratch
- **Trigger**: Discovers reflex-junction, wants to evaluate if it saves time vs. raw SDK usage
- **Success state**: Runs demo, sees their Oura/Fitbit data visualized, copies the pattern into their app

**Job to Be Done**
When building a health app with Reflex, I want to integrate wearable and lab data without managing API clients and state manually, so I can focus on my app's unique value instead of plumbing.

**Non-Users**
- Developers using React/Next.js directly (they should use Vital's React SDK)
- Mobile-only developers (need native HealthKit/Health Connect SDKs)
- Enterprise admins managing Vital org-level settings (Management API)

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | Populate all JunctionUser health data fields (sleep, activity, workouts, body, profile, meals) | These are declared but broken — core promise |
| Must | Typed Pydantic/dataclass models replacing `dict[str, Any]` | Type safety, IDE support, documentation |
| Must | Link widget React component (not just token generation) | Users need a connection UI, not just a token string |
| Must | Visual demo with 8+ pages showcasing each data type | "Demo is king" — this IS the product for evaluation |
| Must | Vitals timeseries state (HR, HRV, SpO2, glucose, steps, etc.) | Core wearable data that developers actually need |
| Should | Lab testing state (orders, results, appointments) | Full platform coverage differentiator |
| Should | Webhook handler with Svix verification + state updates | Real-time data flow, not just logging |
| Should | Introspection state (resource status, historical pulls) | Developer diagnostics |
| Could | ECG and menstrual cycle data | Niche but complete coverage |
| Could | Demo provider auto-connect (sandbox synthetic data) | Zero-config demo experience |
| Won't | Mobile SDK integration (HealthKit/Health Connect) | Requires native platform, out of scope for Python |
| Won't | Junction Sense aggregate queries | Closed beta, not accessible |
| Won't | ETL pipeline management | Org-level admin, not per-app |

### MVP Scope

All "Must" + "Should" items. The demo must be visually impressive with real data visualizations (charts, timeseries, gauges) — not just text dumps of JSON.

### User Flow (Demo)

```
1. Launch demo → Landing page with "Connect a Provider" CTA
2. Click Connect → Link widget opens → User selects provider (or Demo provider)
3. Provider connected → Dashboard redirects to Overview page
4. Overview → Cards showing: Sleep score, Steps today, Resting HR, Body weight
5. Navigate → Sleep page (hypnogram chart, duration bars, scores over time)
6. Navigate → Activity page (step chart, calorie breakdown, active minutes)
7. Navigate → Workouts page (workout cards with sport icons, HR zones, maps)
8. Navigate → Body page (weight trend, composition breakdown)
9. Navigate → Vitals page (HR timeseries, HRV trend, SpO2, glucose if available)
10. Navigate → Labs page (order status, biomarker results with range indicators)
11. Navigate → Webhooks page (live event log, event type filter)
12. Navigate → Settings page (connection management, disconnect providers)
```

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**
- State mixins pattern: `SleepMixin`, `ActivityMixin`, etc. — composable into `JunctionUser`
- Each mixin owns its SDK calls and typed state vars
- Pydantic models for all data types (replacing `dict[str, Any]`) using `PropsBase` or standalone
- Link widget: wrap `@tryvital/vital-link` React component via `JunctionBase(rx.Component)` with props
- Demo: multi-page Reflex app with sidebar navigation, each page demonstrates one data category
- Charts: use `rx.recharts` (built into Reflex) for timeseries, bar charts, and compositions

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Sandbox returns empty data for some types | Medium | Connect demo provider first; document which types need real providers |
| Vital SDK breaking changes (Junction rebrand) | Low | Pin SDK version, test against CI |
| Link widget npm package renamed/deprecated | Medium | Check package registry, fall back to iframe with link_web_url |
| Reflex recharts limitations for complex charts | Low | Use rx.el for custom SVG if needed |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Typed Models & Core Health Data | Pydantic models for all data types; populate JunctionUser fields (sleep, activity, workouts, body, profile, meals) | complete | - | - | `.claude/PRPs/plans/completed/01-typed-models-core-health-data.plan.md` |
| 2 | Vitals Timeseries | State mixin for 50+ vitals endpoints with typed models; priority: HR, HRV, SpO2, glucose, steps, calories | complete | with 3 | 1 | - |
| 3 | Link Widget Component | Wrap @tryvital/vital-link React component; provider selection UI; connection callbacks | complete | with 2 | 1 | - |
| 4 | Webhooks & Real-time | Svix signature verification; event routing by type; state updates from webhook events; typed event models | complete | with 2,3 | 1 | - |
| 5 | Lab Testing | Orders, results, appointments, biomarker models; PSC/phlebotomy scheduling | complete | - | 1 | - |
| 6 | Advanced Features | Introspection, ECG, menstrual cycle, user demographics, bulk operations | complete | - | 1,2 | - |
| 7 | Demo App — Visual Showcase | Multi-page demo with sidebar nav, charts, real data visualizations; connect flow → dashboard → per-type pages | complete | - | 1,2,3,4,5 | - |
| 8 | Documentation & Release | MkDocs API reference, usage guides per data type, CI badges, PyPI v0.2.0 publish | complete | - | 7 | - |

### Phase Details

**Phase 1: Typed Models & Core Health Data**
- **Goal**: Replace all `dict[str, Any]` with typed models; make JunctionUser.load_user() actually fetch and populate health data
- **Scope**:
  - Pydantic/dataclass models: `SleepSummary`, `ActivitySummary`, `WorkoutSummary`, `BodyMeasurement`, `ProfileData`, `MealSummary` with all fields from Vital SDK
  - State mixins: `SleepMixin`, `ActivityMixin`, `WorkoutMixin`, `BodyMixin`, `ProfileMixin`, `MealMixin`
  - Each mixin: `fetch_X(start_date, end_date)` event handler + typed state vars
  - Update `JunctionUser.load_user()` to populate all fields
  - Unit tests for each mixin with mocked AsyncVital client
- **Success signal**: `JunctionUser.sleep_summary` returns typed SleepSummary objects after `load_user()`; all tests pass

**Phase 2: Vitals Timeseries**
- **Goal**: Expose granular timeseries data (heart rate, HRV, SpO2, glucose, etc.)
- **Scope**:
  - `VitalsMixin` state class with methods for priority vitals: `fetch_heartrate`, `fetch_hrv`, `fetch_blood_oxygen`, `fetch_glucose`, `fetch_steps_timeseries`, `fetch_calories_timeseries`, `fetch_respiratory_rate`, `fetch_stress_level`, `fetch_blood_pressure`
  - Typed timeseries models: `TimeseriesPoint(timestamp, value, unit)`, `GroupedTimeseries`
  - Generic `fetch_vital(metric_name, start_date, end_date)` for the remaining 40+ metrics
  - Tests with mocked data
- **Success signal**: Can fetch and display HR timeseries for a connected provider

**Phase 3: Link Widget Component**
- **Goal**: Render the Vital Link widget as a Reflex component, not just generate tokens
- **Scope**:
  - `JunctionLink(JunctionBase)` React component wrapping `@tryvital/vital-link`
  - Props: `token`, `environment`, `on_success`, `on_error`, `on_close`
  - `JunctionLinkButton` convenience component (generates token + opens Link in one click)
  - Connection success callback that triggers `get_connected_providers` refresh
  - Falls back to `link_web_url` iframe if npm package unavailable
- **Success signal**: Clicking a button in demo opens provider selection, connecting a demo provider updates state

**Phase 4: Webhooks & Real-time**
- **Goal**: Make webhooks functional — verify signatures, route events, update state
- **Scope**:
  - Svix signature verification using `webhook_secret`
  - Typed event models: `WebhookEvent`, `ConnectionEvent`, `DataEvent`
  - Event routing: dispatch by `event_type` prefix (connection, historical, daily)
  - Optional: push webhook events into a Reflex state list for live display
  - Tests for signature verification and event routing
- **Success signal**: Webhook endpoint rejects invalid signatures; provider connection event triggers state refresh

**Phase 5: Lab Testing**
- **Goal**: Wrap lab test ordering, results, and appointment scheduling
- **Scope**:
  - `LabMixin` state class: `get_lab_tests`, `create_order`, `get_order_status`, `get_results`
  - Typed models: `LabTest`, `LabOrder`, `BiomarkerResult`, `Appointment`
  - PSC/phlebotomy appointment methods
  - Result PDF download support
  - Sandbox order simulation (`simulate_order_process`)
- **Success signal**: Can create a test order in sandbox and retrieve simulated results

**Phase 6: Advanced Features**
- **Goal**: Complete coverage of remaining Vital SDK namespaces
- **Scope**:
  - `IntrospectionMixin`: resource status, historical pull tracking
  - `ECGMixin`: electrocardiogram session data
  - `MenstrualMixin`: cycle tracking data
  - User demographics: `upsert_user_info`, `get_latest_user_info`
  - Provider listing: `get_all_providers` with filtering
  - Bulk operations: historical pull triggers
- **Success signal**: All 15+ Vital SDK namespaces have corresponding state methods

**Phase 7: Demo App — Visual Showcase**
- **Goal**: Multi-page interactive demo that wows health app developers
- **Scope**:
  - **Landing page**: Hero section, "Connect a Provider" CTA with Link widget
  - **Overview dashboard**: Summary cards (sleep score, steps, HR, weight) with sparklines
  - **Sleep page**: Hypnogram chart (rx.recharts), duration bars, sleep stages pie, score trend
  - **Activity page**: Steps bar chart, calorie donut, active minutes timeline
  - **Workouts page**: Workout cards with sport icons, HR zone distribution, calendar view
  - **Body page**: Weight trend line chart, composition breakdown
  - **Vitals page**: HR timeseries, HRV trend, SpO2, glucose (if available), blood pressure
  - **Labs page**: Order cards with status badges, biomarker results with range bars (green/yellow/red)
  - **Webhooks page**: Live event log with event type badges, auto-scroll
  - **Settings page**: Connected providers list with disconnect buttons, connection status
  - **Sidebar navigation**: App-wide nav with icons per section
  - Responsive layout, dark theme (Reflex radix-ui)
- **Success signal**: Developer can run demo, connect a provider, and see visualized health data across all pages

**Phase 8: Documentation & Release**
- **Goal**: Publish v0.2.0 with complete docs
- **Scope**:
  - MkDocs pages: one per data type with code examples
  - API reference auto-generated from docstrings (mkdocstrings)
  - Usage guide: wrap_app → connect provider → fetch data → display
  - Migration guide from v0.1.0
  - Update README with new badges and feature list
  - PyPI publish v0.2.0
  - GitHub release with changelog
- **Success signal**: `pip install reflex-junction` gets v0.2.0; docs site has 10+ pages

### Parallelism Notes

Phases 2, 3, and 4 can run in parallel after Phase 1 completes — they touch different concerns (vitals data, React component, FastAPI webhooks) with no shared state. Phase 5 can also start after Phase 1 independently. Phase 7 (demo) depends on all data phases being complete to showcase everything, but individual demo pages can be built incrementally as each phase completes.

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| State architecture | Mixins composing into JunctionUser | Separate state classes per domain | Mixins allow single state tree with modular organization |
| Data models | Pydantic-style dataclasses with PropsBase | Raw dicts, TypedDict | Type safety, IDE autocomplete, documentation |
| Charts in demo | rx.recharts (built-in) | Plotly, custom SVG, Altair | Zero extra dependencies, native Reflex integration |
| Link widget approach | React component wrapper + iframe fallback | Token-only (current), redirect-only | Best UX with graceful degradation |
| Demo theme | Dark mode (Reflex radix-ui default) | Light mode, custom theme | Developer-friendly, modern look |
| Vitals API surface | Priority 10 metrics + generic fallback | All 50+ as individual methods | Manageable API surface with escape hatch |

---

## Research Summary

**Market Context**
- Vital (rebranded Junction) is the leading health data aggregation API, supporting 300+ devices
- No existing Reflex component wraps any health data API
- terra.fyi is the main Vital competitor — also lacks Reflex integration
- reflex-junction could be the first comprehensive health data component for any Python web framework

**Technical Context**
- Vital Python SDK (`vital>=2.1.0`) provides AsyncVital with full async support
- All data endpoints follow consistent patterns: `.get(user_id, start_date, end_date)` → typed response
- Reflex's `rx.recharts` provides line, bar, area, pie, and composed charts out of the box
- Reflex radix-ui theme supports dark mode, responsive layouts, and card-based dashboards
- `@tryvital/vital-link` npm package provides embeddable provider connection widget

---

*Generated: 2026-03-13*
*Status: DRAFT - needs validation*
