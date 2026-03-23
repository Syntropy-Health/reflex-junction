"""Tests for guard/control flow components."""

from __future__ import annotations

import reflex as rx
from reflex_junction.control_components import (
    connected,
    disconnected,
    junction_loaded,
    junction_loading,
)


class TestConnected:
    def test_returns_component(self):
        comp = connected(rx.text("hello"))
        assert comp is not None

    def test_accepts_multiple_children(self):
        comp = connected(rx.text("a"), rx.text("b"))
        assert comp is not None

    def test_no_children(self):
        comp = connected()
        assert comp is not None


class TestDisconnected:
    def test_returns_component(self):
        comp = disconnected(rx.text("no devices"))
        assert comp is not None

    def test_accepts_multiple_children(self):
        comp = disconnected(rx.text("a"), rx.text("b"))
        assert comp is not None


class TestJunctionLoaded:
    def test_returns_component(self):
        comp = junction_loaded(rx.text("ready"))
        assert comp is not None

    def test_accepts_multiple_children(self):
        comp = junction_loaded(rx.text("a"), rx.text("b"))
        assert comp is not None


class TestJunctionLoading:
    def test_returns_component(self):
        comp = junction_loading(rx.spinner())
        assert comp is not None

    def test_accepts_multiple_children(self):
        comp = junction_loading(rx.spinner(), rx.text("Loading..."))
        assert comp is not None
