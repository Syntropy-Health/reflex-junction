"""Tests for Junction configuration models."""

from __future__ import annotations

from reflex_junction.models import JunctionConfig, LinkConfig, ProviderInfo


class TestJunctionConfig:
    """Tests for JunctionConfig defaults and types."""

    def test_defaults(self):
        config = JunctionConfig()
        assert config.environment == "sandbox"
        assert config.region == "us"

    def test_custom_values(self):
        config = JunctionConfig(environment="production", region="eu")
        assert config.environment == "production"
        assert config.region == "eu"

    def test_sandbox_eu(self):
        config = JunctionConfig(environment="sandbox_eu", region="eu")
        assert config.environment == "sandbox_eu"


class TestLinkConfig:
    """Tests for LinkConfig defaults and types."""

    def test_defaults(self):
        config = LinkConfig()
        assert config.redirect_url == ""
        assert config.filter_on_providers is None

    def test_custom_values(self):
        config = LinkConfig(
            redirect_url="https://example.com/callback",
            filter_on_providers=["oura", "fitbit"],
        )
        assert config.redirect_url == "https://example.com/callback"
        assert config.filter_on_providers == ["oura", "fitbit"]

    def test_empty_providers_list(self):
        config = LinkConfig(filter_on_providers=[])
        assert config.filter_on_providers == []


class TestProviderInfo:
    """Tests for ProviderInfo defaults and types."""

    def test_defaults(self):
        info = ProviderInfo()
        assert info.name == ""
        assert info.slug == ""
        assert info.logo == ""
        assert info.auth_type == ""

    def test_oura_provider(self):
        info = ProviderInfo(
            name="Oura",
            slug="oura",
            logo="https://example.com/oura.png",
            auth_type="oauth",
        )
        assert info.name == "Oura"
        assert info.slug == "oura"
        assert info.logo == "https://example.com/oura.png"
        assert info.auth_type == "oauth"

    def test_password_auth_provider(self):
        info = ProviderInfo(
            name="Some Device",
            slug="some_device",
            auth_type="password",
        )
        assert info.auth_type == "password"
