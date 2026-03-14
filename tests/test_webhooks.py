"""Tests for webhook handling: signature verification, event parsing, routing (Phase 4)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import pytest
from reflex_junction.fastapi_helpers import (
    ConnectionEvent,
    DataEvent,
    WebhookEvent,
    WebhookVerificationError,
    _parse_event,
    _verify_svix_signature,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestWebhookEvent:
    def test_defaults(self):
        e = WebhookEvent()
        assert e.event_type == ""
        assert e.user_id == ""
        assert e.data == {}

    def test_custom_values(self):
        e = WebhookEvent(
            event_type="connection.created",
            user_id="user-123",
            client_user_id="client-456",
            data={"provider": "oura"},
        )
        assert e.event_type == "connection.created"
        assert e.user_id == "user-123"


class TestConnectionEvent:
    def test_inherits_webhook_event(self):
        e = ConnectionEvent(
            event_type="connection.created",
            provider="oura",
            status="connected",
        )
        assert isinstance(e, WebhookEvent)
        assert e.provider == "oura"
        assert e.status == "connected"


class TestDataEvent:
    def test_inherits_webhook_event(self):
        e = DataEvent(
            event_type="daily.data.sleep.created",
            provider="oura",
            data_type="sleep",
            start_date="2024-01-01",
            end_date="2024-01-02",
        )
        assert isinstance(e, WebhookEvent)
        assert e.data_type == "sleep"


# ---------------------------------------------------------------------------
# Event parsing tests
# ---------------------------------------------------------------------------


class TestParseEvent:
    def test_connection_event(self):
        body = {
            "event_type": "connection.created",
            "client_user_id": "client-1",
            "user_id": "user-1",
            "data": {"provider": "oura", "status": "connected"},
        }
        event = _parse_event(body)
        assert isinstance(event, ConnectionEvent)
        assert event.provider == "oura"
        assert event.status == "connected"

    def test_historical_data_event(self):
        body = {
            "event_type": "historical.data.sleep.created",
            "client_user_id": "client-1",
            "user_id": "user-1",
            "data": {
                "provider": "oura",
                "data_type": "sleep",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        }
        event = _parse_event(body)
        assert isinstance(event, DataEvent)
        assert event.data_type == "sleep"
        assert event.start_date == "2024-01-01"

    def test_daily_data_event(self):
        body = {
            "event_type": "daily.data.activity.created",
            "client_user_id": "client-1",
            "user_id": "user-1",
            "data": {"provider": "fitbit", "data_type": "activity"},
        }
        event = _parse_event(body)
        assert isinstance(event, DataEvent)

    def test_unknown_event_type(self):
        body = {
            "event_type": "unknown.event",
            "user_id": "user-1",
        }
        event = _parse_event(body)
        assert isinstance(event, WebhookEvent)
        assert not isinstance(event, ConnectionEvent)
        assert not isinstance(event, DataEvent)

    def test_empty_body(self):
        event = _parse_event({})
        assert isinstance(event, WebhookEvent)
        assert event.event_type == ""

    def test_raw_preserved(self):
        body = {"event_type": "test", "extra_field": "value"}
        event = _parse_event(body)
        assert event.raw == body


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------


def _make_signed_headers(
    payload: bytes,
    secret: str,
    msg_id: str = "msg_test123",
    timestamp: int | None = None,
) -> dict[str, str]:
    """Create valid Svix-signed headers for testing."""
    ts = timestamp or int(time.time())
    key_material = secret.removeprefix("whsec_")
    signing_key = base64.b64decode(key_material)
    to_sign = f"{msg_id}.{ts}.".encode() + payload
    sig = base64.b64encode(
        hmac.new(signing_key, to_sign, hashlib.sha256).digest()
    ).decode()
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(ts),
        "svix-signature": f"v1,{sig}",
    }


# A valid base64-encoded secret with whsec_ prefix
TEST_SECRET = "whsec_" + base64.b64encode(b"test-signing-key-32bytes!!!!!!!!").decode()


class TestVerifySvixSignature:
    def test_valid_signature(self):
        payload = b'{"event_type": "test"}'
        headers = _make_signed_headers(payload, TEST_SECRET)
        # Should not raise
        _verify_svix_signature(payload, headers, TEST_SECRET)

    def test_invalid_signature(self):
        payload = b'{"event_type": "test"}'
        headers = _make_signed_headers(payload, TEST_SECRET)
        headers["svix-signature"] = "v1,invalidsignature"
        with pytest.raises(WebhookVerificationError, match="No matching"):
            _verify_svix_signature(payload, headers, TEST_SECRET)

    def test_missing_headers(self):
        with pytest.raises(WebhookVerificationError, match="Missing required"):
            _verify_svix_signature(b"body", {}, TEST_SECRET)

    def test_missing_id_header(self):
        headers = {
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,sig",
        }
        with pytest.raises(WebhookVerificationError, match="Missing required"):
            _verify_svix_signature(b"body", headers, TEST_SECRET)

    def test_timestamp_too_old(self):
        payload = b'{"event_type": "test"}'
        old_ts = int(time.time()) - 600  # 10 minutes ago
        headers = _make_signed_headers(payload, TEST_SECRET, timestamp=old_ts)
        with pytest.raises(WebhookVerificationError, match="too old"):
            _verify_svix_signature(payload, headers, TEST_SECRET)

    def test_invalid_timestamp(self):
        headers = {
            "svix-id": "msg_1",
            "svix-timestamp": "not-a-number",
            "svix-signature": "v1,sig",
        }
        with pytest.raises(WebhookVerificationError, match="Invalid"):
            _verify_svix_signature(b"body", headers, TEST_SECRET)

    def test_tampered_payload(self):
        payload = b'{"event_type": "test"}'
        headers = _make_signed_headers(payload, TEST_SECRET)
        tampered = b'{"event_type": "tampered"}'
        with pytest.raises(WebhookVerificationError, match="No matching"):
            _verify_svix_signature(tampered, headers, TEST_SECRET)

    def test_secret_without_prefix(self):
        """Secrets without whsec_ prefix should also work."""
        raw_secret = base64.b64encode(b"another-key-32bytes!!!!!!!!!!!!!").decode()
        payload = b'{"event_type": "test"}'
        headers = _make_signed_headers(payload, raw_secret)
        _verify_svix_signature(payload, headers, raw_secret)

    def test_multiple_signatures_in_header(self):
        """Should accept if any v1 signature matches."""
        payload = b'{"event_type": "test"}'
        headers = _make_signed_headers(payload, TEST_SECRET)
        # Prepend an invalid signature
        headers["svix-signature"] = (
            "v1,invalidfirst " + headers["svix-signature"]
        )
        _verify_svix_signature(payload, headers, TEST_SECRET)

    def test_webhook_id_fallback_headers(self):
        """Should accept webhook-id/webhook-timestamp/webhook-signature headers."""
        payload = b'{"event_type": "test"}'
        svix_headers = _make_signed_headers(payload, TEST_SECRET)
        # Use webhook-* prefix instead of svix-*
        fallback_headers = {
            "webhook-id": svix_headers["svix-id"],
            "webhook-timestamp": svix_headers["svix-timestamp"],
            "webhook-signature": svix_headers["svix-signature"],
        }
        _verify_svix_signature(payload, fallback_headers, TEST_SECRET)
