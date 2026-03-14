"""Tests for Junction Link widget components (Phase 3)."""

from __future__ import annotations

from reflex_junction.base import JunctionLink, JunctionLinkButton


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
