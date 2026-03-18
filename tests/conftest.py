"""Shared fixtures and pytest configuration for reflex-junction tests."""

from __future__ import annotations

import pytest
from reflex_junction.junction_provider import JunctionState


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset JunctionState ClassVars between tests."""
    JunctionState._api_key = None
    JunctionState._environment = "sandbox"
    JunctionState._client = None
    JunctionState._on_load_events = {}
    JunctionState._dependent_handlers = {}
    JunctionState._init_wait_timeout_seconds = 1.0
    yield
    JunctionState._api_key = None
    JunctionState._environment = "sandbox"
    JunctionState._client = None
    JunctionState._on_load_events = {}
    JunctionState._dependent_handlers = {}
    JunctionState._init_wait_timeout_seconds = 1.0
