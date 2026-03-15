[![CI](https://github.com/Syntropy-Health/reflex-junction/actions/workflows/ci.yml/badge.svg)](https://github.com/Syntropy-Health/reflex-junction/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reflex-junction.svg)](https://pypi.org/project/reflex-junction/)
[![Python](https://img.shields.io/pypi/pyversions/reflex-junction.svg)](https://pypi.org/project/reflex-junction/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://syntropy-health.github.io/reflex-junction/)

# reflex-junction

A [Reflex](https://reflex.dev) custom component for integrating [Junction (Vital)](https://tryvital.io/) health data into your application. Connect wearables and health platforms (Oura, Fitbit, Apple Health, Garmin, etc.) with a few lines of Python.

## Features

- **Health Data Summaries** — Sleep, activity, workouts, body composition, meals, profile
- **Vitals Timeseries** — Heart rate, HRV, SpO2, glucose, blood pressure, respiratory rate, steps, calories
- **Lab Testing** — Test panels, orders, biomarker results with range indicators
- **Link Widget** — React component wrapping `@tryvital/vital-link` for provider connection UI
- **Webhooks** — Svix signature verification, typed event models, event routing
- **Introspection** — Resource status, historical pull tracking, provider listing
- **Chart-Ready** — Computed vars formatted for `rx.recharts` (line, bar, composed charts)
- **Visual Demo** — 9-page demo app with sidebar nav, dark theme, and real data visualizations
- **Typed Models** — Python dataclasses for all data types (no `dict[str, Any]`)
- **Multi-region** — US and EU sandbox/production environments

## Installation

```bash
pip install reflex-junction
```

Or with your preferred package manager:

```bash
uv add reflex-junction
poetry add reflex-junction
```

## Quick Start

### 1. Get an API key

Sign up at [tryvital.io](https://tryvital.io/) and grab your API key from the dashboard.

### 2. Wrap your app

```python
import os
import reflex as rx
import reflex_junction as junction

app = rx.App()

junction.wrap_app(
    app,
    api_key=os.environ["JUNCTION_API_KEY"],
    environment="sandbox",  # or "production"
    register_user_state=True,
)
```

### 3. Use Junction state in your pages

```python
def health_dashboard() -> rx.Component:
    return rx.container(
        rx.heading("Health Dashboard"),
        rx.text(f"Connected: {junction.JunctionState.has_connections}"),
        # Sleep scores chart
        rx.recharts.line_chart(
            rx.recharts.line(data_key="score"),
            rx.recharts.x_axis(data_key="date"),
            data=junction.JunctionUser.chart_sleep_scores,
        ),
        # Heart rate timeseries
        rx.recharts.line_chart(
            rx.recharts.line(data_key="bpm", stroke="#ef4444"),
            rx.recharts.x_axis(data_key="timestamp"),
            data=junction.JunctionUser.chart_heartrate,
        ),
    )
```

### 4. Add the Link widget

```python
from reflex_junction import junction_link_button

def connect_page() -> rx.Component:
    return rx.container(
        junction_link_button(
            "Connect a Provider",
            link_token=junction.JunctionState.link_token,
            env="sandbox",
            on_success=junction.JunctionState.get_connected_providers,
        ),
    )
```

## Data Types

### Health Summaries (Phase 1)

| Model | Description | Key Fields |
|-------|-------------|------------|
| `SleepSummary` | Sleep sessions | score, duration, stages, HR, HRV |
| `ActivitySummary` | Daily activity | steps, calories, distance, intensity |
| `WorkoutSummary` | Workout sessions | sport, duration, calories, HR |
| `BodyMeasurement` | Body composition | weight, BMI, fat%, muscle% |
| `ProfileData` | User profile | height, birth_date, gender |
| `MealSummary` | Nutrition entries | calories, protein, carbs, fat |

### Vitals Timeseries (Phase 2)

| Method | Data Key | Unit |
|--------|----------|------|
| `fetch_heartrate()` | bpm | bpm |
| `fetch_hrv()` | hrv | ms |
| `fetch_blood_oxygen()` | SpO2 | % |
| `fetch_glucose()` | glucose | mg/dL |
| `fetch_blood_pressure()` | systolic/diastolic | mmHg |
| `fetch_steps_timeseries()` | steps | steps |
| `fetch_calories_timeseries()` | calories | kcal |
| `fetch_respiratory_rate()` | rate | breaths/min |
| `fetch_vital(metric, ...)` | Generic escape hatch for 50+ metrics |

### Lab Testing (Phase 5)

| Model | Description |
|-------|-------------|
| `LabTest` | Test panel with markers |
| `LabOrder` | Placed order with status |
| `BiomarkerResult` | Result with range indicators |

### Webhook Events (Phase 4)

| Model | Prefix | Example |
|-------|--------|---------|
| `ConnectionEvent` | `connection.*` | Provider connected/disconnected |
| `DataEvent` | `historical.*`, `daily.*` | New health data available |
| `WebhookEvent` | Base class | Any event type |

## Webhook Support

```python
junction.wrap_app(
    app,
    api_key=os.environ["JUNCTION_API_KEY"],
    register_webhooks=True,
    webhook_secret=os.environ["JUNCTION_WEBHOOK_SECRET"],
    webhook_prefix="/junction",  # POST /junction/webhooks
)
```

Webhooks use Svix signature verification. Invalid signatures are rejected with 401.

## Running the Demo

The repo includes a 9-page demo app in `junction_demo/`.

```bash
uv sync --dev
cd junction_demo
export JUNCTION_API_KEY=sk_us_...
uv run reflex init
uv run reflex run
```

Pages: Dashboard, Sleep, Activity, Workouts, Body, Vitals, Labs, Providers, Settings.

## Environment Options

| Environment      | Description        |
|------------------|--------------------|
| `sandbox`        | US sandbox (default) |
| `production`     | US production      |
| `sandbox_eu`     | EU sandbox         |
| `production_eu`  | EU production      |

## API Reference

### State Classes

| Class | Description |
|-------|-------------|
| `JunctionState` | Core state — user creation, provider management, Link tokens |
| `JunctionUser` | Extended state — health data, vitals, labs, introspection |

### Components

| Component | Description |
|-----------|-------------|
| `JunctionLink` / `junction_link` | Declarative VitalLink button (requires public key) |
| `JunctionLinkButton` / `junction_link_button` | Token-based Link widget (uses `useVitalLink` hook) |

### Functions

| Function | Description |
|----------|-------------|
| `wrap_app(app, api_key, ...)` | One-line app integration with optional webhooks |
| `junction_provider(*children, api_key, ...)` | Component wrapper for page-level integration |
| `on_load(handlers)` | Wrap page on_load handlers to wait for Junction init |
| `register_on_auth_change_handler(handler)` | Register handler to fire after Junction initializes |
| `create_webhook_router(prefix, secret)` | Create a standalone FastAPI webhook router |
| `register_webhook_api(app, secret, prefix)` | Register webhook endpoint on a Reflex app |

See the [full documentation](https://syntropy-health.github.io/reflex-junction/) for detailed guides.

## Contributing

```bash
task install          # Install dev dependencies + pre-commit
task test             # Run lint + typecheck + pytest
task run              # Run the demo app
task run-docs         # Serve docs locally at localhost:9000
```

## License

[MIT](LICENSE) — Copyright (c) 2025 Syntropy Health
