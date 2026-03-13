# Getting Started

## Installation

```bash
uv add reflex-junction

# or
pip install reflex-junction
```

## Configuration

### API Key

Get your API key from the [Junction/Vital dashboard](https://app.tryvital.io/).

Set it as an environment variable:

```bash
export JUNCTION_API_KEY="sk_sandbox_..."
```

### Basic Usage

```python
import os
import reflex as rx
import reflex_junction as junction

app = rx.App()

junction.wrap_app(
    app,
    api_key=os.environ["JUNCTION_API_KEY"],
    environment="sandbox",  # or "production"
)
```

### Using junction_provider directly

If you prefer to wrap specific pages instead of the entire app:

```python
import reflex_junction as junction

def my_page() -> rx.Component:
    return junction.junction_provider(
        rx.text("Health data integration active"),
        api_key=os.environ["JUNCTION_API_KEY"],
        environment="sandbox",
    )
```

### Registering Webhooks

To receive webhook events from Junction:

```python
junction.wrap_app(
    app,
    api_key=os.environ["JUNCTION_API_KEY"],
    register_webhooks=True,
    webhook_secret=os.environ["JUNCTION_WEBHOOK_SECRET"],
    webhook_prefix="/junction",
)
```

This registers a POST endpoint at `/junction/webhooks`.

### Environment Options

| Environment      | Description                  |
|------------------|------------------------------|
| `sandbox`        | US sandbox (default)         |
| `production`     | US production                |
| `sandbox_eu`     | EU sandbox                   |
| `production_eu`  | EU production                |
