"""FastAPI helpers for Junction webhook handling."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import reflex as rx
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def create_webhook_router(
    prefix: str = "/junction",
    secret: str = "",
    tags: Sequence[str] | None = None,
) -> APIRouter:
    """Create a FastAPI router for Junction webhook handling.

    Args:
        prefix: URL prefix for webhook endpoints.
        secret: Svix webhook signing secret for signature verification.
        tags: OpenAPI tags for the router.

    Returns:
        A FastAPI APIRouter with webhook endpoints.
    """
    # secret stored for Phase 5 Svix signature verification
    _webhook_secret = secret
    logger.warning(
        "Junction webhook signature verification is not yet implemented. "
        "All requests to %s/webhooks will be accepted without verification.",
        prefix,
    )
    if tags is None:
        tags = ["junction"]
    router = APIRouter(prefix=prefix, tags=list(tags))

    @router.post("/webhooks")
    async def junction_webhook_handler(request: Request) -> JSONResponse:
        """Handle incoming Junction webhook events.

        Full implementation with Svix signature verification
        will be added in Phase 5.
        """
        body: dict[str, Any] = await request.json()
        event_type = body.get("event_type", "unknown")
        logger.info("Received Junction webhook: %s", event_type)
        return JSONResponse(content={"status": "ok"}, status_code=200)

    return router


def register_webhook_api(
    app: rx.App,
    secret: str,
    prefix: str = "/junction",
    tags: list[str] | None = None,
) -> APIRouter:
    """Register the Junction webhook API on a Reflex app.

    Args:
        app: The Reflex app to register webhooks on.
        secret: Svix webhook signing secret.
        prefix: URL prefix for webhook endpoints.
        tags: OpenAPI tags.

    Returns:
        The registered APIRouter.
    """
    router = create_webhook_router(prefix=prefix, secret=secret, tags=tags)

    if isinstance(app.api_transformer, FastAPI):
        app.api_transformer.include_router(router)
    else:
        fastapi_app = FastAPI()
        fastapi_app.include_router(router)
        app.api_transformer = fastapi_app

    return router
