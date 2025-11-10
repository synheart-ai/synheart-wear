"""Tests for webhook verification functionality."""

import time

import pytest

from synheart_cloud_connector.exceptions import WebhookError
from synheart_cloud_connector.webhooks import WebhookVerifier, extract_signature_from_headers


class TestWebhookVerifier:
    """Tests for WebhookVerifier class."""

    @pytest.fixture
    def verifier(self):
        """Create webhook verifier with test secret."""
        return WebhookVerifier(secret="test_webhook_secret", replay_window_seconds=180)

    def test_verify_hmac_sha256_valid(self, verifier):
        """Test HMAC-SHA256 verification with valid signature."""
        import hashlib
        import hmac

        timestamp = str(int(time.time()))
        body = b'{"user_id": 123, "type": "test.event"}'

        # Create valid signature
        signed_payload = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            b"test_webhook_secret",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        result = verifier.verify_hmac_sha256(
            timestamp=timestamp,
            body=body,
            signature=signature,
            vendor="test_vendor",
        )

        assert result is True

    def test_verify_hmac_sha256_invalid_signature(self, verifier):
        """Test HMAC-SHA256 verification with invalid signature."""
        timestamp = str(int(time.time()))
        body = b'{"user_id": 123}'
        signature = "invalid_signature"

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_hmac_sha256(timestamp, body, signature, vendor="test")

        assert "HMAC signature mismatch" in str(exc_info.value)
        assert exc_info.value.vendor == "test"

    def test_verify_hmac_sha256_expired_timestamp(self, verifier):
        """Test HMAC-SHA256 verification with expired timestamp."""
        import hashlib
        import hmac

        # Timestamp from 10 minutes ago (outside replay window)
        timestamp = str(int(time.time()) - 600)
        body = b'{"user_id": 123}'

        # Create valid signature
        signed_payload = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            b"test_webhook_secret",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_hmac_sha256(timestamp, body, signature)

        assert "outside replay window" in str(exc_info.value)

    def test_verify_hmac_sha256_future_timestamp(self, verifier):
        """Test HMAC-SHA256 verification with future timestamp."""
        import hashlib
        import hmac

        # Timestamp from 10 minutes in the future
        timestamp = str(int(time.time()) + 600)
        body = b'{"user_id": 123}'

        signed_payload = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            b"test_webhook_secret",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_hmac_sha256(timestamp, body, signature)

        assert "outside replay window" in str(exc_info.value)

    def test_verify_hmac_sha256_invalid_timestamp_format(self, verifier):
        """Test HMAC-SHA256 verification with invalid timestamp format."""
        body = b'{"user_id": 123}'
        signature = "some_signature"

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_hmac_sha256(
                timestamp="not_a_number",
                body=body,
                signature=signature,
            )

        assert "Invalid timestamp format" in str(exc_info.value)

    def test_verify_sha256_hash_valid(self, verifier):
        """Test SHA256 hash verification with valid hash."""
        import hashlib
        import hmac

        body = b'{"user_id": 123}'

        # Create valid hash
        signature = hmac.new(
            b"test_webhook_secret",
            body,
            hashlib.sha256,
        ).hexdigest()

        result = verifier.verify_sha256_hash(body, signature)
        assert result is True

    def test_verify_sha256_hash_invalid(self, verifier):
        """Test SHA256 hash verification with invalid hash."""
        body = b'{"user_id": 123}'
        signature = "invalid_hash"

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_sha256_hash(body, signature, vendor="test")

        assert "SHA256 hash mismatch" in str(exc_info.value)

    def test_verify_signature_header_v1_valid(self, verifier):
        """Test signature header verification with v1 scheme."""
        import hashlib
        import hmac

        timestamp = str(int(time.time()))
        body = b'{"user_id": 123}'

        # Create v1 signature
        signed_payload = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            b"test_webhook_secret",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        signature_header = f"v1={signature}"

        result = verifier.verify_signature_header(
            timestamp=timestamp,
            body=body,
            signature_header=signature_header,
        )

        assert result is True

    def test_verify_signature_header_multiple_schemes(self, verifier):
        """Test signature header with multiple schemes."""
        import hashlib
        import hmac

        timestamp = str(int(time.time()))
        body = b'{"user_id": 123}'

        # Create v1 signature
        signed_payload = f"{timestamp}.{body.decode()}"
        v1_sig = hmac.new(
            b"test_webhook_secret",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Invalid v2 signature
        signature_header = f"v1={v1_sig},v2=invalid_signature"

        # Should succeed because v1 is valid
        result = verifier.verify_signature_header(
            timestamp=timestamp,
            body=body,
            signature_header=signature_header,
        )

        assert result is True

    def test_verify_signature_header_no_valid_schemes(self, verifier):
        """Test signature header with no valid schemes."""
        timestamp = str(int(time.time()))
        body = b'{"user_id": 123}'
        signature_header = "v2=invalid,v3=invalid"

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_signature_header(timestamp, body, signature_header)

        assert "No valid signature scheme matched" in str(exc_info.value)

    def test_verify_signature_header_empty(self, verifier):
        """Test signature header with empty value."""
        timestamp = str(int(time.time()))
        body = b'{"user_id": 123}'
        signature_header = ""

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_signature_header(timestamp, body, signature_header)

        assert "No signatures found" in str(exc_info.value)

    def test_verify_basic_auth_valid(self, verifier):
        """Test basic auth verification with valid credentials."""
        result = verifier.verify_basic_auth(
            username="test_user",
            password="test_pass",
            expected_username="test_user",
            expected_password="test_pass",
        )

        assert result is True

    def test_verify_basic_auth_invalid_username(self, verifier):
        """Test basic auth with invalid username."""
        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_basic_auth(
                username="wrong_user",
                password="test_pass",
                expected_username="test_user",
                expected_password="test_pass",
            )

        assert "Basic auth credentials invalid" in str(exc_info.value)

    def test_verify_basic_auth_invalid_password(self, verifier):
        """Test basic auth with invalid password."""
        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_basic_auth(
                username="test_user",
                password="wrong_pass",
                expected_username="test_user",
                expected_password="test_pass",
            )

        assert "Basic auth credentials invalid" in str(exc_info.value)

    def test_custom_replay_window(self):
        """Test custom replay window setting."""
        verifier = WebhookVerifier(secret="test", replay_window_seconds=60)

        # Timestamp from 90 seconds ago (outside custom window)
        timestamp = str(int(time.time()) - 90)
        body = b'{"test": "data"}'

        import hashlib
        import hmac

        signed_payload = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            b"test",
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        with pytest.raises(WebhookError) as exc_info:
            verifier.verify_hmac_sha256(timestamp, body, signature)

        assert "outside replay window (60s)" in str(exc_info.value)


class TestExtractSignatureFromHeaders:
    """Tests for extract_signature_from_headers function."""

    def test_extract_with_defaults(self):
        """Test extracting with default header keys."""
        headers = {
            "X-Signature": "sig_123",
            "X-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        signature, timestamp = extract_signature_from_headers(headers)

        assert signature == "sig_123"
        assert timestamp == "1234567890"

    def test_extract_case_insensitive(self):
        """Test case-insensitive header extraction."""
        headers = {
            "x-signature": "sig_123",
            "x-timestamp": "1234567890",
        }

        signature, timestamp = extract_signature_from_headers(headers)

        assert signature == "sig_123"
        assert timestamp == "1234567890"

    def test_extract_custom_keys(self):
        """Test extracting with custom header keys."""
        headers = {
            "X-WHOOP-Signature": "whoop_sig",
            "X-WHOOP-Signature-Timestamp": "1234567890",
        }

        signature, timestamp = extract_signature_from_headers(
            headers,
            signature_key="X-WHOOP-Signature",
            timestamp_key="X-WHOOP-Signature-Timestamp",
        )

        assert signature == "whoop_sig"
        assert timestamp == "1234567890"

    def test_extract_missing_signature(self):
        """Test extraction when signature is missing."""
        headers = {
            "X-Timestamp": "1234567890",
        }

        signature, timestamp = extract_signature_from_headers(headers)

        assert signature is None
        assert timestamp == "1234567890"

    def test_extract_missing_timestamp(self):
        """Test extraction when timestamp is missing."""
        headers = {
            "X-Signature": "sig_123",
        }

        signature, timestamp = extract_signature_from_headers(headers)

        assert signature == "sig_123"
        assert timestamp is None

    def test_extract_both_missing(self):
        """Test extraction when both are missing."""
        headers = {
            "Content-Type": "application/json",
        }

        signature, timestamp = extract_signature_from_headers(headers)

        assert signature is None
        assert timestamp is None
