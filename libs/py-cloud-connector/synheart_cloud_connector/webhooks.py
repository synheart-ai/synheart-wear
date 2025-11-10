"""Webhook verification utilities for HMAC signatures and replay protection."""

import hashlib
import hmac
import time
from typing import Any

from .exceptions import WebhookError


class WebhookVerifier:
    """
    Verifies webhook signatures and prevents replay attacks.

    Supports:
    - HMAC-SHA256 signature verification
    - Timestamp-based replay protection
    - Multiple signature schemes (header-based, body-based)
    """

    def __init__(
        self,
        secret: str,
        replay_window_seconds: int = 180,  # 3 minutes
    ):
        self.secret = secret.encode() if isinstance(secret, str) else secret
        self.replay_window_seconds = replay_window_seconds

    def verify_hmac_sha256(
        self,
        timestamp: str | int,
        body: bytes,
        signature: str,
        vendor: str | None = None,
    ) -> bool:
        """
        Verify HMAC-SHA256 signature with timestamp.

        Common pattern used by WHOOP, Stripe, etc.

        Args:
            timestamp: Unix timestamp from webhook headers
            body: Raw request body
            signature: Expected signature from headers
            vendor: Optional vendor name for error messages

        Returns:
            True if signature is valid and within replay window

        Raises:
            WebhookError: If verification fails
        """
        # Check replay window
        try:
            ts = int(timestamp)
        except (ValueError, TypeError) as e:
            raise WebhookError(
                "Invalid timestamp format",
                vendor=vendor,
            ) from e

        now = int(time.time())
        if abs(now - ts) > self.replay_window_seconds:
            raise WebhookError(
                f"Timestamp outside replay window ({self.replay_window_seconds}s)",
                vendor=vendor,
            )

        # Compute signature
        signed_payload = f"{timestamp}.{body.decode()}"
        computed_signature = hmac.new(
            self.secret,
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison
        if not hmac.compare_digest(computed_signature, signature):
            raise WebhookError(
                "HMAC signature mismatch",
                vendor=vendor,
            )

        return True

    def verify_sha256_hash(
        self,
        body: bytes,
        signature: str,
        vendor: str | None = None,
    ) -> bool:
        """
        Verify SHA256 hash (no timestamp).

        Used by some vendors that don't include timestamps.

        Args:
            body: Raw request body
            signature: Expected hash from headers
            vendor: Optional vendor name for error messages

        Returns:
            True if hash matches

        Raises:
            WebhookError: If verification fails
        """
        computed_hash = hmac.new(
            self.secret,
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, signature):
            raise WebhookError(
                "SHA256 hash mismatch",
                vendor=vendor,
            )

        return True

    def verify_signature_header(
        self,
        timestamp: str | int,
        body: bytes,
        signature_header: str,
        vendor: str | None = None,
    ) -> bool:
        """
        Verify signature header with multiple schemes.

        Format: "v1=<signature>,v2=<signature>"

        Args:
            timestamp: Unix timestamp
            body: Raw request body
            signature_header: Signature header value
            vendor: Optional vendor name

        Returns:
            True if any signature scheme matches

        Raises:
            WebhookError: If no valid signatures found
        """
        # Parse signature schemes
        schemes = {}
        for part in signature_header.split(","):
            if "=" in part:
                version, sig = part.split("=", 1)
                schemes[version.strip()] = sig.strip()

        if not schemes:
            raise WebhookError(
                "No signatures found in header",
                vendor=vendor,
            )

        # Try each scheme
        for version, signature in schemes.items():
            if version == "v1":
                try:
                    return self.verify_hmac_sha256(timestamp, body, signature, vendor)
                except WebhookError:
                    continue

        raise WebhookError(
            "No valid signature scheme matched",
            vendor=vendor,
        )

    def verify_basic_auth(
        self,
        username: str,
        password: str,
        expected_username: str,
        expected_password: str,
    ) -> bool:
        """
        Verify HTTP Basic Auth credentials.

        Used by some webhook endpoints.

        Args:
            username: Provided username
            password: Provided password
            expected_username: Expected username
            expected_password: Expected password

        Returns:
            True if credentials match

        Raises:
            WebhookError: If credentials don't match
        """
        if not (
            hmac.compare_digest(username, expected_username)
            and hmac.compare_digest(password, expected_password)
        ):
            raise WebhookError("Basic auth credentials invalid")

        return True


def extract_signature_from_headers(
    headers: dict[str, Any],
    signature_key: str = "X-Signature",
    timestamp_key: str = "X-Timestamp",
) -> tuple[str | None, str | None]:
    """
    Extract signature and timestamp from webhook headers.

    Args:
        headers: Request headers
        signature_key: Header key for signature
        timestamp_key: Header key for timestamp

    Returns:
        Tuple of (signature, timestamp) or (None, None)
    """
    # Case-insensitive header lookup
    headers_lower = {k.lower(): v for k, v in headers.items()}

    signature = headers_lower.get(signature_key.lower())
    timestamp = headers_lower.get(timestamp_key.lower())

    return signature, timestamp
