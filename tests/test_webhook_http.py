"""HTTP-layer tests for webhook router and register_webhook_api."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from reflex_junction.fastapi_helpers import (
    create_webhook_router,
    register_webhook_api,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "whsec_" + base64.b64encode(b"test-signing-key-32bytes!!!!").decode()


def _sign_payload(payload: bytes, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    """Generate valid Svix headers for a given payload."""
    msg_id = "msg_test123"
    timestamp = str(int(time.time()))
    key_material = secret.removeprefix("whsec_")
    signing_key = base64.b64decode(key_material)
    to_sign = f"{msg_id}.{timestamp}.".encode() + payload
    sig = base64.b64encode(
        hmac.new(signing_key, to_sign, hashlib.sha256).digest()
    ).decode()
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{sig}",
    }


def _make_app(secret: str | None = WEBHOOK_SECRET, on_event=None) -> FastAPI:
    """Create a FastAPI test app with the webhook router."""
    app = FastAPI()
    router = create_webhook_router(secret=secret, on_event=on_event)
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Tests: create_webhook_router
# ---------------------------------------------------------------------------


class TestWebhookSignatureVerification:
    """Tests for signature verification in the webhook endpoint."""

    def test_valid_signature_returns_200(self):
        app = _make_app()
        client = TestClient(app)
        payload = json.dumps({"event_type": "data.created", "user_id": "u1"}).encode()
        headers = _sign_payload(payload)
        resp = client.post("/junction/webhooks", content=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_invalid_signature_returns_401(self):
        app = _make_app()
        client = TestClient(app)
        payload = json.dumps({"event_type": "test"}).encode()
        headers = {
            "svix-id": "msg_bad",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,invalid_signature_here",
        }
        resp = client.post("/junction/webhooks", content=payload, headers=headers)
        assert resp.status_code == 401
        assert resp.json()["error"] == "signature_verification_failed"

    def test_no_secret_disables_verification(self):
        app = _make_app(secret=None)
        client = TestClient(app)
        payload = json.dumps({"event_type": "test"}).encode()
        resp = client.post("/junction/webhooks", content=payload)
        assert resp.status_code == 200


class TestWebhookMalformedBody:
    """Tests for malformed JSON body handling."""

    def test_non_json_body_returns_400(self):
        app = _make_app(secret=None)
        client = TestClient(app)
        resp = client.post(
            "/junction/webhooks",
            content=b"this is not json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "malformed_json"

    def test_empty_body_returns_400(self):
        app = _make_app(secret=None)
        client = TestClient(app)
        resp = client.post(
            "/junction/webhooks",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 400


class TestWebhookCallback:
    """Tests for on_event callback invocation."""

    def test_callback_invoked_with_parsed_event(self):
        received = []
        callback = MagicMock(side_effect=lambda event: received.append(event))
        app = _make_app(secret=None, on_event=callback)
        client = TestClient(app)
        payload = json.dumps({
            "event_type": "connection.created",
            "user_id": "u1",
            "client_user_id": "cu1",
            "data": {"provider": "oura", "status": "connected"},
        }).encode()
        resp = client.post("/junction/webhooks", content=payload)
        assert resp.status_code == 200
        assert len(received) == 1
        event = received[0]
        assert event.event_type == "connection.created"
        assert event.user_id == "u1"

    def test_async_callback_invoked(self):
        received = []
        callback = AsyncMock(side_effect=lambda event: received.append(event))
        app = _make_app(secret=None, on_event=callback)
        client = TestClient(app)
        payload = json.dumps({"event_type": "data.created"}).encode()
        resp = client.post("/junction/webhooks", content=payload)
        assert resp.status_code == 200
        callback.assert_called_once()

    def test_callback_error_still_returns_200(self):
        callback = MagicMock(side_effect=RuntimeError("boom"))
        app = _make_app(secret=None, on_event=callback)
        client = TestClient(app)
        payload = json.dumps({"event_type": "test"}).encode()
        resp = client.post("/junction/webhooks", content=payload)
        assert resp.status_code == 200

    def test_no_callback_still_returns_200(self):
        app = _make_app(secret=None, on_event=None)
        client = TestClient(app)
        payload = json.dumps({"event_type": "test"}).encode()
        resp = client.post("/junction/webhooks", content=payload)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: register_webhook_api
# ---------------------------------------------------------------------------


class TestRegisterWebhookApi:
    """Tests for register_webhook_api helper."""

    def test_attaches_router_to_existing_fastapi(self):
        mock_app = MagicMock()
        existing_fastapi = FastAPI()
        mock_app.api_transformer = existing_fastapi
        router = register_webhook_api(mock_app, secret="whsec_test")
        assert router is not None
        # The router should have been included in the existing FastAPI app
        route_paths = [getattr(r, "path", "") for r in existing_fastapi.routes]
        assert "/junction/webhooks" in route_paths

    def test_creates_new_fastapi_when_no_transformer(self):
        mock_app = MagicMock()
        mock_app.api_transformer = None
        router = register_webhook_api(mock_app, secret="whsec_test")
        assert router is not None
        # A new FastAPI instance should have been assigned
        assert isinstance(mock_app.api_transformer, FastAPI)

    def test_custom_prefix(self):
        mock_app = MagicMock()
        existing_fastapi = FastAPI()
        mock_app.api_transformer = existing_fastapi
        register_webhook_api(mock_app, secret="whsec_test", prefix="/custom")
        route_paths = [getattr(r, "path", "") for r in existing_fastapi.routes]
        assert "/custom/webhooks" in route_paths
