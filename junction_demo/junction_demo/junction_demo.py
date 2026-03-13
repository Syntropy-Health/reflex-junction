"""Minimal demo app for reflex-junction."""

import logging
import os

import reflex as rx
import reflex_junction as junction

# Set up debug logging with a console handler
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


def index() -> rx.Component:
    """Landing page for the Junction demo."""
    return rx.box(
        rx.vstack(
            rx.heading("reflex-junction demo", size="9"),
            rx.text(junction.__version__),
            rx.divider(),
            rx.text(
                "Junction state initialized: ",
                rx.text.strong(junction.JunctionState.is_initialized),
            ),
            rx.text(
                "Connected sources: ",
                rx.text.strong(junction.JunctionState.connected_sources.length()),  # type: ignore[attr-defined]
            ),
            rx.text(
                "Has connections: ",
                rx.text.strong(junction.JunctionState.has_connections),
            ),
            align="center",
            spacing="5",
        ),
        height="100vh",
        max_width="100%",
        overflow_y="auto",
        padding="2em",
    )


app = rx.App()

junction.wrap_app(
    app,
    api_key=os.environ.get("JUNCTION_API_KEY", "sk_sandbox_placeholder"),
    environment=os.environ.get("JUNCTION_ENVIRONMENT", "sandbox"),
)

app.add_page(index)
