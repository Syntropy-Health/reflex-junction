"""FastAPI helpers for Junction webhook handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import reflex as rx
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Webhook event models (Phase 4)
# ---------------------------------------------------------------------------


@dataclass
class WebhookEvent:
    """Parsed Junction webhook event."""

    event_type: str = ""
    client_user_id: str = ""
    user_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionEvent(WebhookEvent):
    """Provider connection state change event."""

    provider: str = ""
    status: str = ""


@dataclass
class DataEvent(WebhookEvent):
    """Health data update event (historical or daily)."""

    provider: str = ""
    data_type: str = ""
    start_date: str = ""
    end_date: str = ""


# ---------------------------------------------------------------------------
# Svix-compatible signature verification
# ---------------------------------------------------------------------------


class WebhookVerificationError(ValueError):
    """Raised when webhook signature verification fails."""


def _verify_svix_signature(
    payload: bytes,
    headers: dict[str, str],
    secret: str,
    tolerance_seconds: int = 300,
) -> None:
    """Verify a Svix webhook signature.

    Svix uses the ``whsec_`` prefix on secrets, base64-encodes the
    signing key, and signs ``{msg_id}.{timestamp}.{body}`` with
    HMAC-SHA256.  The signature header may contain multiple
    space-separated ``v1,<base64sig>`` entries.

    Args:
        payload: Raw request body bytes.
        headers: Request headers (case-insensitive lookup).
        secret: Svix webhook secret (with or without ``whsec_`` prefix).
        tolerance_seconds: Max age of the timestamp in seconds.

    Raises:
        WebhookVerificationError: If verification fails.
    """
    import time as _time

    # Normalise header key casing
    norm = {k.lower(): v for k, v in headers.items()}

    msg_id = norm.get("svix-id") or norm.get("webhook-id", "")
    timestamp_str = norm.get("svix-timestamp") or norm.get(
        "webhook-timestamp", ""
    )
    signature_header = norm.get("svix-signature") or norm.get(
        "webhook-signature", ""
    )

    if not msg_id or not timestamp_str or not signature_header:
        raise WebhookVerificationError(
            "Missing required Svix headers (svix-id, svix-timestamp, svix-signature)"
        )

    # Timestamp tolerance check
    try:
        ts = int(timestamp_str)
    except ValueError:
        raise WebhookVerificationError("Invalid svix-timestamp header")

    now = int(_time.time())
    if abs(now - ts) > tolerance_seconds:
        raise WebhookVerificationError(
            f"Webhook timestamp too old or too new (delta={abs(now - ts)}s)"
        )

    # Decode the signing key
    key_material = secret.removeprefix("whsec_")
    try:
        signing_key = base64.b64decode(key_material)
    except Exception:
        raise WebhookVerificationError("Invalid webhook secret encoding")

    # Compute expected signature
    to_sign = f"{msg_id}.{timestamp_str}.".encode() + payload
    expected = base64.b64encode(
        hmac.new(signing_key, to_sign, hashlib.sha256).digest()
    ).decode()

    # Compare against each candidate in the header
    for entry in signature_header.split(" "):
        parts = entry.split(",", 1)
        if len(parts) == 2 and parts[0] == "v1":
            if hmac.compare_digest(parts[1], expected):
                return

    raise WebhookVerificationError("No matching v1 signature found")


# ---------------------------------------------------------------------------
# Event routing
# ---------------------------------------------------------------------------

# Handler type: async callback receiving a parsed WebhookEvent
WebhookHandler = Callable[[WebhookEvent], Any]

# Default prefix-based routing table
_PREFIX_MAP: dict[str, type[WebhookEvent]] = {
    "connection": ConnectionEvent,
    "provider": ConnectionEvent,
    "historical": DataEvent,
    "daily": DataEvent,
    "data": DataEvent,
}


def _parse_event(body: dict[str, Any]) -> WebhookEvent:
    """Parse a raw webhook body into a typed event model."""
    event_type = body.get("event_type", "")
    prefix = event_type.split(".")[0] if event_type else ""
    cls = _PREFIX_MAP.get(prefix, WebhookEvent)

    base_kwargs: dict[str, Any] = {
        "event_type": event_type,
        "client_user_id": str(body.get("client_user_id", "")),
        "user_id": str(body.get("user_id", "")),
        "data": body.get("data", {}),
        "raw": body,
    }

    if cls is ConnectionEvent:
        base_kwargs["provider"] = str(
            body.get("data", {}).get("provider", "")
        )
        base_kwargs["status"] = str(body.get("data", {}).get("status", ""))
    elif cls is DataEvent:
        base_kwargs["provider"] = str(
            body.get("data", {}).get("provider", "")
        )
        base_kwargs["data_type"] = str(
            body.get("data", {}).get("data_type", "")
        )
        base_kwargs["start_date"] = str(
            body.get("data", {}).get("start_date", "")
        )
        base_kwargs["end_date"] = str(
            body.get("data", {}).get("end_date", "")
        )

    return cls(**base_kwargs)


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_webhook_router(
    prefix: str = "/junction",
    secret: str | None = None,
    tags: Sequence[str] | None = None,
    on_event: WebhookHandler | None = None,
) -> APIRouter:
    """Create a FastAPI router for Junction webhook handling.

    Args:
        prefix: URL prefix for webhook endpoints.
        secret: Svix webhook signing secret for signature verification.
        tags: OpenAPI tags for the router.
        on_event: Optional async callback invoked for every verified event.

    Returns:
        A FastAPI APIRouter with webhook endpoints.
    """
    _webhook_secret = secret or ""
    if not _webhook_secret:
        logger.warning(
            "Junction webhook secret not set. "
            "Signature verification is DISABLED for %s/webhooks.",
            prefix,
        )
    if tags is None:
        tags = ["junction"]
    router = APIRouter(prefix=prefix, tags=list(tags))

    @router.post("/webhooks")
    async def junction_webhook_handler(request: Request) -> JSONResponse:
        """Handle incoming Junction webhook events."""
        body_bytes = await request.body()

        # Signature verification (if secret is set)
        if _webhook_secret:
            headers = dict(request.headers)
            try:
                _verify_svix_signature(body_bytes, headers, _webhook_secret)
            except WebhookVerificationError as exc:
                logger.warning("Webhook signature verification failed: %s", exc)
                return JSONResponse(
                    content={"error": "signature_verification_failed"},
                    status_code=401,
                )

        try:
            body: dict[str, Any] = await request.json()
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("Webhook request has malformed JSON body: %s", exc)
            return JSONResponse(
                content={"error": "malformed_json"},
                status_code=400,
            )
        event = _parse_event(body)
        logger.info(
            "Received Junction webhook: %s (user=%s)",
            event.event_type,
            event.user_id,
        )

        if on_event is not None:
            try:
                result = on_event(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                logger.exception("Webhook on_event handler failed")

        return JSONResponse(content={"status": "ok"}, status_code=200)

    return router


def register_webhook_api(
    app: rx.App,
    secret: str,
    prefix: str = "/junction",
    tags: list[str] | None = None,
    on_event: WebhookHandler | None = None,
) -> APIRouter:
    """Register the Junction webhook API on a Reflex app.

    Args:
        app: The Reflex app to register webhooks on.
        secret: Svix webhook signing secret.
        prefix: URL prefix for webhook endpoints.
        tags: OpenAPI tags.
        on_event: Optional async callback for each verified event.

    Returns:
        The registered APIRouter.
    """
    router = create_webhook_router(
        prefix=prefix, secret=secret, tags=tags, on_event=on_event
    )

    if isinstance(app.api_transformer, FastAPI):
        app.api_transformer.include_router(router)
    else:
        fastapi_app = FastAPI()
        fastapi_app.include_router(router)
        app.api_transformer = fastapi_app

    return router
