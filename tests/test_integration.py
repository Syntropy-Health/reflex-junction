"""Integration tests using the real Vital/Junction sandbox API.

These tests require a valid JUNCTION_API_KEY environment variable.
They are skipped automatically in environments without the key (e.g., fork PRs).
They also skip gracefully if the key is expired/invalid (401 from API).

Run with: uv run pytest tests/test_integration.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration

SANDBOX_KEY = os.environ.get("JUNCTION_API_KEY", "")


@pytest.fixture(scope="module")
def api_key() -> str:
    if not SANDBOX_KEY or SANDBOX_KEY == "sk_sandbox_placeholder":
        pytest.skip("JUNCTION_API_KEY not set — skipping integration tests")
    return SANDBOX_KEY


@pytest_asyncio.fixture()
async def vital_client(api_key: str):
    """Create a real AsyncVital client for sandbox testing."""
    from vital import AsyncVital
    from vital.environment import VitalEnvironment

    client = AsyncVital(api_key=api_key, environment=VitalEnvironment.SANDBOX)
    yield client


@pytest_asyncio.fixture()
async def test_user_id(vital_client):
    """Create a test user in sandbox and return the user_id. Cleaned up after test."""
    from vital.core.api_error import ApiError

    client_user_id = f"ci-test-{uuid.uuid4().hex[:12]}"
    try:
        result = await vital_client.user.create(client_user_id=client_user_id)
    except ApiError as e:
        if e.status_code == 401:
            pytest.skip("JUNCTION_API_KEY returned 401 — key may be expired")
        raise
    user_id = result.user_id

    yield user_id

    # Cleanup: deregister test user
    try:
        await vital_client.user.delete(user_id)
    except Exception:
        pass


class TestSandboxUserLifecycle:
    """Test user creation, provider listing, and link token generation against sandbox."""

    @pytest.mark.asyncio()
    async def test_create_user(self, vital_client):
        """Can create a user in the sandbox."""
        from vital.core.api_error import ApiError

        client_user_id = f"ci-test-{uuid.uuid4().hex[:12]}"
        try:
            result = await vital_client.user.create(client_user_id=client_user_id)
        except ApiError as e:
            if e.status_code == 401:
                pytest.skip("JUNCTION_API_KEY returned 401 — key may be expired")
            raise
        assert result.user_id
        # Cleanup
        await vital_client.user.delete(result.user_id)

    @pytest.mark.asyncio()
    async def test_get_connected_providers(self, vital_client, test_user_id):
        """Can query connected providers (expects empty for new sandbox user)."""
        result = await vital_client.user.get_connected_providers(test_user_id)
        # New user has no providers — should not error
        assert result is not None

    @pytest.mark.asyncio()
    async def test_create_link_token(self, vital_client, test_user_id):
        """Can generate a link token for the sandbox user."""
        result = await vital_client.link.token(user_id=test_user_id)
        assert result
        # Link token should be a non-empty string
        token = str(result)
        assert len(token) > 0


class TestSandboxHealthData:
    """Test health data endpoints return without error (data may be empty in sandbox)."""

    @pytest.mark.asyncio()
    async def test_sleep_get(self, vital_client, test_user_id):
        """Sleep endpoint responds without error."""
        result = await vital_client.sleep.get(
            user_id=test_user_id, start_date="2024-01-01"
        )
        assert hasattr(result, "sleep")

    @pytest.mark.asyncio()
    async def test_activity_get(self, vital_client, test_user_id):
        """Activity endpoint responds without error."""
        result = await vital_client.activity.get(
            user_id=test_user_id, start_date="2024-01-01"
        )
        assert hasattr(result, "activity")

    @pytest.mark.asyncio()
    async def test_workouts_get(self, vital_client, test_user_id):
        """Workouts endpoint responds without error."""
        result = await vital_client.workouts.get(
            user_id=test_user_id, start_date="2024-01-01"
        )
        assert hasattr(result, "workouts")

    @pytest.mark.asyncio()
    async def test_body_get(self, vital_client, test_user_id):
        """Body endpoint responds without error."""
        result = await vital_client.body.get(
            user_id=test_user_id, start_date="2024-01-01"
        )
        assert hasattr(result, "body")


class TestSandboxVitals:
    """Test vitals timeseries endpoints."""

    @pytest.mark.asyncio()
    async def test_heartrate(self, vital_client, test_user_id):
        """Heart rate endpoint responds without error."""
        result = await vital_client.vitals.heartrate(
            user_id=test_user_id, start_date="2024-01-01"
        )
        # Result is a list (may be empty for sandbox user without connected provider)
        assert isinstance(result, list)

    @pytest.mark.asyncio()
    async def test_steps_timeseries(self, vital_client, test_user_id):
        """Steps timeseries endpoint responds without error."""
        result = await vital_client.vitals.steps(
            user_id=test_user_id, start_date="2024-01-01"
        )
        assert isinstance(result, list)


class TestSandboxWebhookVerification:
    """Test webhook signature verification logic (no API key needed)."""

    def test_valid_signature_verification(self):
        """Svix signature verification works with known-good inputs."""
        import base64
        import hashlib
        import hmac
        import time

        from reflex_junction.fastapi_helpers import _verify_svix_signature

        secret = "whsec_" + base64.b64encode(b"test-secret-key-1234567890").decode()
        msg_id = "msg_test"
        payload = b'{"event_type": "test"}'
        timestamp = str(int(time.time()))

        # Signature format must match: {msg_id}.{timestamp}.{payload_bytes}
        to_sign = f"{msg_id}.{timestamp}.".encode() + payload
        key_bytes = base64.b64decode(secret.removeprefix("whsec_"))
        sig = base64.b64encode(
            hmac.new(key_bytes, to_sign, hashlib.sha256).digest()
        ).decode()

        headers = {
            "svix-id": msg_id,
            "svix-timestamp": timestamp,
            "svix-signature": f"v1,{sig}",
        }

        # Should not raise
        _verify_svix_signature(payload, headers, secret)

    def test_invalid_signature_rejected(self):
        """Bad signature raises WebhookVerificationError."""
        import time

        from reflex_junction.fastapi_helpers import (
            WebhookVerificationError,
            _verify_svix_signature,
        )

        secret = "whsec_dGVzdC1zZWNyZXQta2V5LTEyMzQ1Njc4OTA="
        headers = {
            "svix-id": "msg_test",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,invalidsignature",
        }

        with pytest.raises(WebhookVerificationError):
            _verify_svix_signature(b'{"event_type": "test"}', headers, secret)
