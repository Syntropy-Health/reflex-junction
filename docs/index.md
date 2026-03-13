# reflex-junction

A Reflex custom component for integrating Junction (Vital) health data into a Reflex application.

## Overview

`reflex-junction` wraps the [Junction/Vital](https://tryvital.io/) health data SDK, providing:

- **JunctionState** -- Reflex state management for Junction API integration
- **JunctionUser** -- Extended state with health data summaries
- **Webhook handling** -- FastAPI router for receiving Junction webhook events
- **Link widget support** -- Token generation for the Vital Link provider connection widget

## Quick Start

```python
import reflex_junction as junction

# Wrap your app with Junction integration
junction.wrap_app(
    app,
    api_key="your_junction_api_key",
    environment="sandbox",
)
```

See [Getting Started](getting_started.md) for detailed setup instructions.
