[![CI](https://github.com/Syntropy-Health/reflex-junction/actions/workflows/ci.yml/badge.svg)](https://github.com/Syntropy-Health/reflex-junction/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reflex-junction.svg)](https://pypi.org/project/reflex-junction/)
[![Python](https://img.shields.io/pypi/pyversions/reflex-junction.svg)](https://pypi.org/project/reflex-junction/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://syntropy-health.github.io/reflex-junction/)

# reflex-junction

A [Reflex](https://reflex.dev) custom component for integrating [Junction (Vital)](https://tryvital.io/) health data into your application. Connect wearables and health platforms (Oura, Fitbit, Apple Health, Garmin, etc.) with a few lines of Python.

## Features

- **JunctionState** — Reflex state management for the Vital API (user creation, provider connections, data refresh)
- **JunctionUser** — Extended state with health data summaries (activity, sleep, body, meals, workouts)
- **wrap_app()** — One-line integration that configures your entire Reflex app
- **junction_provider()** — Component-level integration for wrapping specific pages
- **Webhook support** — FastAPI router for receiving real-time health data events
- **Link widget support** — Token generation for the Vital Link provider connection UI
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
        rx.foreach(
            junction.JunctionState.connected_sources,
            lambda p: rx.badge(p["name"]),
        ),
    )
```

## Usage

### Using `junction_provider` directly

For page-level integration instead of app-wide:

```python
import reflex_junction as junction

def health_page() -> rx.Component:
    return junction.junction_provider(
        rx.container(
            rx.text("Connected providers: "),
            rx.text(junction.JunctionState.connected_sources.length()),
        ),
        api_key=os.environ["JUNCTION_API_KEY"],
    )
```

### Webhook support

Receive real-time events when health data updates:

```python
junction.wrap_app(
    app,
    api_key=os.environ["JUNCTION_API_KEY"],
    register_webhooks=True,
    webhook_secret=os.environ["JUNCTION_WEBHOOK_SECRET"],
    webhook_prefix="/junction",  # POST /junction/webhooks
)
```

### Environment options

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
| `JunctionUser` | Extended state — health data summaries (activity, sleep, body, meals, workouts) |

### Configuration Models

| Class | Description |
|-------|-------------|
| `JunctionConfig` | Environment and region settings |
| `LinkConfig` | Redirect URL and provider filter for the Link widget |
| `ProviderInfo` | Provider metadata (name, slug, logo, auth_type) |

### Functions

| Function | Description |
|----------|-------------|
| `wrap_app(app, api_key, ...)` | One-line app integration with optional webhooks |
| `junction_provider(*children, api_key, ...)` | Component wrapper for page-level integration |
| `on_load(handlers)` | Wrap page on_load handlers to wait for Junction init |
| `register_on_auth_change_handler(handler)` | Register handler to fire after Junction initializes |
| `create_webhook_router(prefix, secret)` | Create a standalone FastAPI webhook router |
| `register_webhook_api(app, secret, prefix)` | Register webhook endpoint on a Reflex app |

### JunctionState Events

| Event | Description |
|-------|-------------|
| `create_user(client_user_id)` | Create a Junction user mapped to your app's user |
| `get_connected_providers()` | Fetch connected health data providers |
| `disconnect_provider(provider)` | Disconnect a specific provider by slug |
| `refresh_data()` | Trigger data sync from all connected providers |
| `create_link_token(redirect_url)` | Generate a Link widget token |

See the [full documentation](https://syntropy-health.github.io/reflex-junction/) for detailed guides.

## Contributing

Contributions welcome! We use [Taskfile](https://taskfile.dev/) for common tasks:

```bash
task install          # Install dev dependencies + pre-commit
task test             # Run lint + typecheck + pytest
task run              # Run the demo app
task run-docs         # Serve docs locally at localhost:9000
task bump-patch       # Bump patch version (bug fix)
task bump-minor       # Bump minor version (new feature)
```

Workflow: Fork → feature branch → add tests → submit PR.

## License

[MIT](LICENSE) — Copyright (c) 2025 Syntropy Health
