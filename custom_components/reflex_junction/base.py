"""Junction Link widget components for connecting health data providers."""

from __future__ import annotations

from typing import Any

import reflex as rx


class JunctionBase(rx.Component):
    """Base component for Junction health data integration."""

    library = "@tryvital/vital-link"


class JunctionLink(JunctionBase):
    """Declarative wrapper for the VitalLink button component.

    Renders the built-in Vital Link button which opens a provider
    selection modal when clicked. Requires a ``public_key`` prop
    (your Vital publishable key).

    Usage::

        junction_link(
            "Connect your device",
            public_key="pk_...",
            env="sandbox",
            on_success=MyState.handle_success,
        )
    """

    tag = "VitalLink"

    env: rx.Var[str]
    public_key: rx.Var[str]

    on_success: rx.EventHandler[lambda: []]
    on_exit: rx.EventHandler[lambda: []]
    on_error: rx.EventHandler[lambda: []]


junction_link = JunctionLink.create


class JunctionLinkButton(rx.Component):
    """Token-based Link widget using the useVitalLink hook.

    Unlike :class:`JunctionLink`, this component accepts a server-generated
    ``link_token`` and calls ``open(token)`` when clicked.  This is the
    recommended approach when the token is fetched via
    :meth:`JunctionState.create_link_token`.

    Usage::

        junction_link_button(
            "Connect a Provider",
            link_token=JunctionState.link_token,
            env="sandbox",
            on_success=MyState.handle_success,
        )
    """

    tag = "JunctionLinkButton"

    link_token: rx.Var[str]
    env: rx.Var[str]

    on_success: rx.EventHandler[lambda: []]
    on_exit: rx.EventHandler[lambda: []]
    on_error: rx.EventHandler[lambda: []]

    def add_imports(self) -> dict[str, Any]:
        return {"@tryvital/vital-link": ["useVitalLink"]}

    def add_custom_code(self) -> list[str]:
        return [
            """
function JunctionLinkButton({ linkToken, env, onSuccess, onExit, onError, children, ...rest }) {
  const { open, ready, error } = useVitalLink({
    env: env || "sandbox",
    onSuccess: onSuccess,
    onExit: onExit,
    onError: onError,
  });

  return (
    <button
      onClick={() => open(linkToken)}
      disabled={!ready || !linkToken}
      {...rest}
    >
      {children || "Connect a Provider"}
    </button>
  );
}
"""
        ]


junction_link_button = JunctionLinkButton.create
