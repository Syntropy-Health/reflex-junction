# Changelog

All notable changes to `reflex-junction` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `JunctionLinkSynchronizer` headless component — auto-initializes Junction state on mount via `EventLoopContext` + `ReflexEvent`
- Guard components: `connected()`, `disconnected()`, `junction_loaded()`, `junction_loading()`
- `link_redirect()` helper for URL-based provider connection flow
- Event handler metadata passing — `on_success`, `on_exit`, `on_error` now forward VitalLink callback data to Python handlers
- `JunctionState.on_provider_connected()`, `on_link_exit()`, `on_link_error()` handlers

### Changed
- `junction_provider()` now wraps children in `JunctionLinkSynchronizer` (was `rx.fragment`)
- `JunctionLinkButton` and `JunctionLink` event handlers: `lambda: []` → `lambda metadata: [metadata]`

## [0.2.0] — 2026-03-13

### Added
- **Health data summaries** — `JunctionUser` with `fetch_sleep()`, `fetch_activity()`, `fetch_workouts()`, `fetch_body()`, `fetch_profile()`, `fetch_meals()`
- **Vitals timeseries** — `fetch_heartrate()`, `fetch_hrv()`, `fetch_blood_oxygen()`, `fetch_glucose()`, `fetch_blood_pressure()`, `fetch_steps_timeseries()`, `fetch_calories_timeseries()`, `fetch_respiratory_rate()`, generic `fetch_vital()`
- **Lab testing** — `fetch_lab_tests()`, `fetch_lab_orders()`, `fetch_lab_results()`
- **Advanced features** — `fetch_providers()`, `fetch_introspection()`, `fetch_historical_pulls()`, `connect_demo_provider()`
- **Typed data models** — `SleepSummary`, `ActivitySummary`, `WorkoutSummary`, `BodyMeasurement`, `ProfileData`, `MealSummary`, `TimeseriesPoint`, `BloodPressurePoint`, `LabTest`, `LabOrder`, `BiomarkerResult`, `SourceInfo`
- **Webhook handling** — Svix signature verification, typed `WebhookEvent`, `ConnectionEvent`, `DataEvent`, `WebhookHandler` callback
- **Chart-ready computed vars** — `chart_sleep_scores`, `chart_activity_steps`, `chart_heartrate`, `chart_hrv`, `chart_blood_pressure`, `chart_glucose`
- **Link widget components** — `JunctionLink` (declarative), `JunctionLinkButton` (hook-based with `useVitalLink`)
- **Multi-page demo app** — 9 pages with sidebar nav, dark theme, recharts visualizations
- **171 unit tests** — full coverage for state, models, health data, vitals, webhooks, lab testing, integration

## [0.1.0] — 2026-03-12

### Added
- Initial package scaffold with Hatchling build system
- `JunctionState(rx.State)` — API key management, user creation, provider connections
- `JunctionUser(JunctionState)` — extended state (populated in v0.2.0)
- `JunctionBase(rx.Component)` — base component with `library = "@tryvital/vital-link"`
- `wrap_app()` — one-line app integration via `app.app_wraps`
- `junction_provider()` — component wrapper for page-level integration
- `on_load()` — handler sequencing with `wait_for_init`
- `JunctionConfig`, `LinkConfig`, `ProviderInfo` (PropsBase models)
- FastAPI webhook router scaffold (`create_webhook_router`, `register_webhook_api`)
- GitHub Actions CI/CD (ci.yml, publish.yml, matrix Python 3.11/3.12/3.13)
- MkDocs Material documentation config
- Pre-commit hooks (ruff, pyright, trailing-whitespace)
- MIT License

[Unreleased]: https://github.com/Syntropy-Health/reflex-junction/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Syntropy-Health/reflex-junction/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Syntropy-Health/reflex-junction/releases/tag/v0.1.0
