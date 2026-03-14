"""Multi-page demo app for reflex-junction — visual showcase of all capabilities."""

from __future__ import annotations

import logging
import os

import reflex as rx
import reflex_junction as junction

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


# ---------------------------------------------------------------------------
# Demo state — auto-provisions sandbox user with demo provider
# ---------------------------------------------------------------------------


class DemoState(junction.JunctionUser):
    """Extended state that auto-creates a sandbox user and connects a demo provider."""

    demo_status: str = "Not initialized"
    demo_ready: bool = False

    @rx.event
    async def setup_demo(self) -> None:
        """Create a sandbox user, connect Oura demo provider, and load data."""
        if self.demo_ready:
            return
        if self._api_key is None:
            self.demo_status = "No API key — set JUNCTION_API_KEY env var"
            return

        self.demo_status = "Creating sandbox user..."
        try:
            import uuid as _uuid

            client_id = f"demo-{_uuid.uuid4().hex[:8]}"
            await junction.JunctionUser.create_user.fn(self, client_id)
        except Exception as e:
            self.demo_status = f"Failed to create user: {e}"
            return

        self.demo_status = "Connecting Oura demo provider (30 days of synthetic data)..."
        try:
            await junction.JunctionUser.connect_demo_provider.fn(self, "oura")
        except Exception as e:
            self.demo_status = f"Failed to connect demo: {e}"
            return

        self.demo_status = "Loading health data..."
        try:
            await junction.JunctionUser.load_user.fn(self)
        except Exception as e:
            self.demo_status = f"Failed to load data: {e}"
            return

        self.demo_ready = True
        self.demo_status = "Demo ready — showing real sandbox data"


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def nav_link(text: str, href: str) -> rx.Component:
    return rx.link(text, href=href, padding="8px 16px", border_radius="6px")


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Junction Demo", size="5"),
            rx.divider(),
            nav_link("Overview", "/"),
            nav_link("Sleep", "/sleep"),
            nav_link("Activity", "/activity"),
            nav_link("Workouts", "/workouts"),
            nav_link("Body", "/body"),
            nav_link("Vitals", "/vitals"),
            nav_link("Labs", "/labs"),
            nav_link("Providers", "/providers"),
            nav_link("Settings", "/settings"),
            spacing="2",
            padding="16px",
            width="200px",
        ),
        min_width="200px",
        border_right="1px solid var(--gray-6)",
        height="100vh",
    )


def page_layout(*children: rx.Component, title: str = "") -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.vstack(
                rx.heading(title, size="7") if title else rx.fragment(),
                *children,
                spacing="4",
                padding="24px",
                width="100%",
            ),
            flex="1",
            overflow_y="auto",
            height="100vh",
        ),
        spacing="0",
        height="100vh",
    )


def stat_card(label: str, value: rx.Var | str, unit: str = "") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color="gray"),
            rx.hstack(
                rx.heading(value, size="6"),
                rx.text(unit, size="2", color="gray") if unit else rx.fragment(),
                align="end",
                spacing="1",
            ),
            spacing="1",
        ),
        width="200px",
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def index() -> rx.Component:
    """Overview dashboard with summary cards."""
    return page_layout(
        rx.callout(
            DemoState.demo_status,
            icon="info",
            color_scheme=rx.cond(DemoState.demo_ready, "green", "blue"),
        ),
        rx.cond(
            ~DemoState.demo_ready,
            rx.button(
                "Setup Demo (connect Oura sandbox)",
                on_click=DemoState.setup_demo,
                size="3",
                color_scheme="blue",
            ),
            rx.fragment(),
        ),
        rx.hstack(
            stat_card("Version", junction.__version__),
            stat_card(
                "Providers",
                junction.JunctionState.connected_sources.length(),  # type: ignore[attr-defined]
            ),
            stat_card("State", junction.JunctionState.is_initialized),
            spacing="4",
        ),
        rx.divider(),
        rx.heading("Sleep Scores", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.line_chart(
                rx.recharts.line(
                    data_key="score", stroke="#8884d8", name="Score"
                ),
                rx.recharts.x_axis(data_key="date"),
                rx.recharts.y_axis(),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.tooltip(),
                data=DemoState.chart_sleep_scores,
            ),
            width="100%",
            height=300,
        ),
        rx.heading("Daily Steps", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.bar_chart(
                rx.recharts.bar(data_key="steps", fill="#82ca9d", name="Steps"),
                rx.recharts.x_axis(data_key="date"),
                rx.recharts.y_axis(),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.tooltip(),
                data=DemoState.chart_activity_steps,
            ),
            width="100%",
            height=300,
        ),
        title="Dashboard",
    )


def sleep_page() -> rx.Component:
    """Sleep data visualization."""
    return page_layout(
        rx.recharts.responsive_container(
            rx.recharts.composed_chart(
                rx.recharts.bar(
                    data_key="duration_hrs", fill="#6366f1", name="Hours"
                ),
                rx.recharts.line(
                    data_key="score", stroke="#f59e0b", name="Score"
                ),
                rx.recharts.x_axis(data_key="date"),
                rx.recharts.y_axis(),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.tooltip(),
                rx.recharts.legend(),
                data=DemoState.chart_sleep_scores,
            ),
            width="100%",
            height=400,
        ),
        rx.heading("Sleep Sessions", size="5"),
        rx.foreach(
            DemoState.sleep_data,
            lambda s: rx.card(
                rx.hstack(
                    rx.text(s.calendar_date, weight="bold"),
                    rx.text("Score: ", rx.text.strong(s.score)),
                    rx.text(f"Duration: {s.total}s"),
                    spacing="4",
                ),
            ),
        ),
        title="Sleep",
    )


def activity_page() -> rx.Component:
    """Activity data visualization."""
    return page_layout(
        rx.recharts.responsive_container(
            rx.recharts.bar_chart(
                rx.recharts.bar(data_key="steps", fill="#10b981", name="Steps"),
                rx.recharts.x_axis(data_key="date"),
                rx.recharts.y_axis(),
                rx.recharts.tooltip(),
                data=DemoState.chart_activity_steps,
            ),
            width="100%",
            height=400,
        ),
        rx.heading("Activity Data", size="5"),
        rx.foreach(
            DemoState.activity_data,
            lambda a: rx.card(
                rx.hstack(
                    rx.text(a.calendar_date, weight="bold"),
                    rx.text("Steps: ", rx.text.strong(a.steps)),
                    rx.text("Calories: ", rx.text.strong(a.calories_active)),
                    spacing="4",
                ),
            ),
        ),
        title="Activity",
    )


def workouts_page() -> rx.Component:
    """Workouts list."""
    return page_layout(
        rx.foreach(
            DemoState.workout_data,
            lambda w: rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading(w.title, size="4"),
                        rx.badge(w.sport_name),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text(w.calendar_date),
                        rx.text(f"Duration: {w.duration}s"),
                        rx.text("Calories: ", rx.text.strong(w.calories)),
                        rx.text("Avg HR: ", rx.text.strong(w.average_hr)),
                        spacing="4",
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        title="Workouts",
    )


def body_page() -> rx.Component:
    """Body measurements."""
    return page_layout(
        rx.foreach(
            DemoState.body_data,
            lambda b: rx.card(
                rx.hstack(
                    rx.text(b.calendar_date, weight="bold"),
                    rx.text("Weight: ", rx.text.strong(b.weight), " kg"),
                    rx.text("BMI: ", rx.text.strong(b.body_mass_index)),
                    rx.text("Fat: ", rx.text.strong(b.fat), "%"),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        title="Body",
    )


def vitals_page() -> rx.Component:
    """Vitals timeseries charts."""
    return page_layout(
        rx.heading("Heart Rate", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.line_chart(
                rx.recharts.line(data_key="bpm", stroke="#ef4444", name="BPM"),
                rx.recharts.x_axis(data_key="timestamp"),
                rx.recharts.y_axis(),
                rx.recharts.tooltip(),
                data=DemoState.chart_heartrate,
            ),
            width="100%",
            height=300,
        ),
        rx.heading("HRV", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.line_chart(
                rx.recharts.line(data_key="hrv", stroke="#8b5cf6", name="HRV"),
                rx.recharts.x_axis(data_key="timestamp"),
                rx.recharts.y_axis(),
                rx.recharts.tooltip(),
                data=DemoState.chart_hrv,
            ),
            width="100%",
            height=300,
        ),
        rx.heading("Blood Pressure", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.line_chart(
                rx.recharts.line(
                    data_key="systolic", stroke="#ef4444", name="Systolic"
                ),
                rx.recharts.line(
                    data_key="diastolic", stroke="#3b82f6", name="Diastolic"
                ),
                rx.recharts.x_axis(data_key="timestamp"),
                rx.recharts.y_axis(),
                rx.recharts.tooltip(),
                rx.recharts.legend(),
                data=DemoState.chart_blood_pressure,
            ),
            width="100%",
            height=300,
        ),
        rx.heading("Glucose", size="5"),
        rx.recharts.responsive_container(
            rx.recharts.line_chart(
                rx.recharts.line(
                    data_key="glucose", stroke="#f59e0b", name="Glucose"
                ),
                rx.recharts.x_axis(data_key="timestamp"),
                rx.recharts.y_axis(),
                rx.recharts.tooltip(),
                data=DemoState.chart_glucose,
            ),
            width="100%",
            height=300,
        ),
        title="Vitals",
    )


def labs_page() -> rx.Component:
    """Lab test orders and results."""
    return page_layout(
        rx.button(
            "Load Lab Tests",
            on_click=DemoState.fetch_lab_tests,
        ),
        rx.heading("Available Tests", size="5"),
        rx.foreach(
            DemoState.lab_tests,
            lambda t: rx.card(
                rx.vstack(
                    rx.heading(t.name, size="4"),
                    rx.text(t.description),
                    rx.text("Method: ", t.method, " | Sample: ", t.sample_type),
                    spacing="1",
                ),
                width="100%",
            ),
        ),
        rx.heading("Orders", size="5"),
        rx.foreach(
            DemoState.lab_orders,
            lambda o: rx.card(
                rx.hstack(
                    rx.text("Order: ", rx.text.strong(o.id)),
                    rx.badge(o.status),
                    rx.text(o.created_at),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        rx.heading("Results", size="5"),
        rx.foreach(
            DemoState.lab_results,
            lambda r: rx.card(
                rx.hstack(
                    rx.text(r.name, weight="bold"),
                    rx.text(r.value, " ", r.unit),
                    rx.cond(
                        r.is_above_range,
                        rx.badge("HIGH", color_scheme="red"),
                        rx.cond(
                            r.is_below_range,
                            rx.badge("LOW", color_scheme="blue"),
                            rx.badge("NORMAL", color_scheme="green"),
                        ),
                    ),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        title="Lab Testing",
    )


def providers_page() -> rx.Component:
    """Available and connected providers."""
    return page_layout(
        rx.button(
            "Load Providers",
            on_click=DemoState.fetch_providers,
        ),
        rx.heading("Available Providers", size="5"),
        rx.foreach(
            DemoState.available_providers,
            lambda p: rx.card(
                rx.hstack(
                    rx.text(p["name"], weight="bold"),
                    rx.badge(p["auth_type"]),
                    rx.text(p["slug"], color="gray"),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        title="Providers",
    )


def settings_page() -> rx.Component:
    """Connection management and settings."""
    return page_layout(
        rx.heading("Connected Providers", size="5"),
        rx.foreach(
            junction.JunctionState.connected_sources,
            lambda src: rx.card(
                rx.hstack(
                    rx.text(src["name"], weight="bold"),
                    rx.badge(src["status"]),
                    rx.button(
                        "Disconnect",
                        on_click=junction.JunctionState.disconnect_provider(
                            src["slug"]
                        ),
                        color_scheme="red",
                        size="1",
                    ),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        rx.divider(),
        rx.heading("Introspection", size="5"),
        rx.button(
            "Load Resource Status",
            on_click=DemoState.fetch_introspection,
        ),
        rx.foreach(
            DemoState.introspection_data,
            lambda r: rx.card(
                rx.hstack(
                    rx.text(r["resource"], weight="bold"),
                    rx.text(r["provider"]),
                    rx.badge(r["status"]),
                    spacing="4",
                ),
                width="100%",
            ),
        ),
        title="Settings",
    )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = rx.App(
    theme=rx.theme(appearance="dark"),
)

junction.wrap_app(
    app,
    api_key=os.environ.get("JUNCTION_API_KEY", "sk_sandbox_placeholder"),
    environment=os.environ.get("JUNCTION_ENVIRONMENT", "sandbox"),
    register_user_state=True,
)

app.add_page(index, route="/")
app.add_page(sleep_page, route="/sleep")
app.add_page(activity_page, route="/activity")
app.add_page(workouts_page, route="/workouts")
app.add_page(body_page, route="/body")
app.add_page(vitals_page, route="/vitals")
app.add_page(labs_page, route="/labs")
app.add_page(providers_page, route="/providers")
app.add_page(settings_page, route="/settings")
