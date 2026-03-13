from __future__ import annotations

from reflex.components.props import PropsBase


class JunctionConfig(PropsBase):
    """Configuration for the Junction health data integration."""

    environment: str = "sandbox"
    """The Junction environment. One of: sandbox, production, sandbox_eu, production_eu."""

    region: str = "us"
    """The region for data storage. One of: us, eu."""


class LinkConfig(PropsBase):
    """Configuration for the Junction Link widget."""

    redirect_url: str = ""
    """URL to redirect to after a successful provider connection."""

    filter_on_providers: list[str] | None = None
    """Optional list of provider slugs to show in the Link widget."""


class ProviderInfo(PropsBase):
    """Information about a connected health data provider."""

    name: str = ""
    """The display name of the provider (e.g., 'Oura')."""

    slug: str = ""
    """The provider slug identifier (e.g., 'oura')."""

    logo: str = ""
    """URL to the provider's logo image."""

    auth_type: str = ""
    """The authentication type: oauth, password, email, sdk."""
