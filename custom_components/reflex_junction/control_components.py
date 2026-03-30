"""Guard components for conditional rendering based on Junction state."""

from __future__ import annotations

import reflex as rx

from .junction_provider import JunctionState


def connected(*children: rx.Component) -> rx.Component:
    """Render children only when the user has connected providers.

    Usage::

        junction.connected(
            rx.text("Your connected devices:"),
            device_list(),
        )
    """
    return rx.cond(JunctionState.has_connections, rx.fragment(*children))


def disconnected(*children: rx.Component) -> rx.Component:
    """Render children only when the user has no connected providers.

    Usage::

        junction.disconnected(
            rx.text("No devices connected yet."),
            junction.junction_link_button("Connect Now", ...),
        )
    """
    return rx.cond(~JunctionState.has_connections, rx.fragment(*children))


def junction_loaded(*children: rx.Component) -> rx.Component:
    """Render children only after Junction state has initialized.

    Usage::

        junction.junction_loaded(
            main_dashboard(),
        )
    """
    return rx.cond(JunctionState.is_initialized, rx.fragment(*children))


def junction_loading(*children: rx.Component) -> rx.Component:
    """Render children only while Junction state is initializing.

    Usage::

        junction.junction_loading(
            rx.spinner(),
            rx.text("Loading health data..."),
        )
    """
    return rx.cond(~JunctionState.is_initialized, rx.fragment(*children))
