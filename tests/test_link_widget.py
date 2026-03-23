"""Tests for Junction Link widget components."""

from __future__ import annotations

from reflex_junction.base import JunctionLink, JunctionLinkButton
from reflex_junction.junction_provider import JunctionLinkSynchronizer


class TestJunctionLink:
    def test_tag(self):
        assert JunctionLink.tag == "VitalLink"

    def test_library(self):
        assert JunctionLink.library == "@tryvital/vital-link"

    def test_create_returns_component(self):
        comp = JunctionLink.create(env="sandbox", public_key="pk_test")
        assert comp is not None


class TestJunctionLinkButton:
    def test_tag(self):
        assert JunctionLinkButton.tag == "JunctionLinkButton"

    def test_add_imports(self):
        comp = JunctionLinkButton()
        imports = comp.add_imports()
        assert "@tryvital/vital-link" in imports
        assert "useVitalLink" in imports["@tryvital/vital-link"]

    def test_add_custom_code(self):
        comp = JunctionLinkButton()
        code = comp.add_custom_code()
        assert len(code) == 1
        assert "function JunctionLinkButton" in code[0]
        assert "useVitalLink" in code[0]
        assert "open(linkToken)" in code[0]

    def test_create_returns_component(self):
        comp = JunctionLinkButton.create(
            link_token="test-token", env="sandbox"
        )
        assert comp is not None


class TestJunctionLinkSynchronizer:
    """Tests for the headless JS bridge component."""

    def test_tag(self):
        assert JunctionLinkSynchronizer.tag == "JunctionLinkSynchronizer"

    def test_add_imports(self):
        comp = JunctionLinkSynchronizer()
        imports = comp.add_imports()
        assert "react" in imports
        assert "useContext" in imports["react"]
        assert "useEffect" in imports["react"]
        assert "$/utils/context" in imports
        assert "EventLoopContext" in imports["$/utils/context"]
        assert "$/utils/state" in imports
        assert "ReflexEvent" in imports["$/utils/state"]

    def test_add_custom_code(self):
        comp = JunctionLinkSynchronizer()
        code = comp.add_custom_code()
        assert len(code) == 1
        js = code[0]
        assert "function JunctionLinkSynchronizer" in js
        assert "useContext(EventLoopContext)" in js
        assert "ReflexEvent" in js
        assert ".initialize" in js
        assert "useEffect" in js

    def test_add_custom_code_contains_state_name(self):
        comp = JunctionLinkSynchronizer()
        code = comp.add_custom_code()
        from reflex_junction.junction_provider import JunctionState

        state_name = JunctionState.get_full_name()
        assert state_name in code[0]

    def test_create_returns_component(self):
        comp = JunctionLinkSynchronizer.create()
        assert comp is not None
