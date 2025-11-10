"""Rate limiting using token bucket algorithm."""

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any

from .exceptions import RateLimitError
from .vendor_types import RateLimitConfig, VendorType


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    max_tokens: float
    refill_rate: float  # tokens per second
    tokens: float
    last_refill: float

    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False otherwise
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

    def time_until_available(self, tokens: float = 1.0) -> float:
        """
        Calculate seconds until enough tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait, or 0 if tokens are available now
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.

    Supports per-vendor and per-user rate limiting.
    """

    def __init__(self) -> None:
        self.vendor_buckets: dict[str, TokenBucket] = {}
        self.user_buckets: dict[str, TokenBucket] = {}
        self.configs: dict[VendorType, RateLimitConfig] = {}
        self._lock = Lock()

    def configure(self, config: RateLimitConfig) -> None:
        """
        Configure rate limiting for a vendor.

        Args:
            config: Rate limit configuration
        """
        with self._lock:
            self.configs[config.vendor] = config

            # Initialize vendor-level bucket
            refill_rate = config.max_requests / config.time_window
            max_tokens = config.max_burst or config.max_requests

            self.vendor_buckets[config.vendor.value] = TokenBucket(
                max_tokens=float(max_tokens),
                refill_rate=refill_rate,
                tokens=float(max_tokens),
                last_refill=time.time(),
            )

    def check_limit(
        self,
        vendor: VendorType,
        user_id: str | None = None,
        tokens: float = 1.0,
    ) -> None:
        """
        Check if request is allowed under rate limits.

        Args:
            vendor: Vendor type
            user_id: Optional user identifier for per-user limiting
            tokens: Number of tokens to consume (default 1.0)

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        config = self.configs.get(vendor)
        if not config:
            # No rate limit configured - allow all requests
            return

        with self._lock:
            # Check vendor-level bucket
            vendor_bucket = self.vendor_buckets.get(vendor.value)
            if vendor_bucket and not vendor_bucket.consume(tokens):
                retry_after = int(vendor_bucket.time_until_available(tokens))
                raise RateLimitError(
                    f"Vendor rate limit exceeded for {vendor.value}",
                    vendor=vendor.value,
                    retry_after=retry_after,
                )

            # Check user-level bucket if user_id provided
            if user_id:
                user_key = f"{vendor.value}:{user_id}"
                if user_key not in self.user_buckets:
                    # Create user bucket with same config
                    refill_rate = config.max_requests / config.time_window
                    max_tokens = config.max_burst or config.max_requests

                    self.user_buckets[user_key] = TokenBucket(
                        max_tokens=float(max_tokens),
                        refill_rate=refill_rate,
                        tokens=float(max_tokens),
                        last_refill=time.time(),
                    )

                user_bucket = self.user_buckets[user_key]
                if not user_bucket.consume(tokens):
                    retry_after = int(user_bucket.time_until_available(tokens))
                    raise RateLimitError(
                        f"User rate limit exceeded for {vendor.value}:{user_id}",
                        vendor=vendor.value,
                        retry_after=retry_after,
                    )

    def get_remaining(self, vendor: VendorType, user_id: str | None = None) -> dict[str, Any]:
        """
        Get remaining tokens for vendor and/or user.

        Args:
            vendor: Vendor type
            user_id: Optional user identifier

        Returns:
            Dictionary with vendor and user token counts
        """
        with self._lock:
            result: dict[str, Any] = {}

            vendor_bucket = self.vendor_buckets.get(vendor.value)
            if vendor_bucket:
                vendor_bucket._refill()
                result["vendor"] = {
                    "remaining": int(vendor_bucket.tokens),
                    "max": int(vendor_bucket.max_tokens),
                }

            if user_id:
                user_key = f"{vendor.value}:{user_id}"
                user_bucket = self.user_buckets.get(user_key)
                if user_bucket:
                    user_bucket._refill()
                    result["user"] = {
                        "remaining": int(user_bucket.tokens),
                        "max": int(user_bucket.max_tokens),
                    }

            return result

    def reset(self, vendor: VendorType | None = None, user_id: str | None = None) -> None:
        """
        Reset rate limit buckets.

        Args:
            vendor: Optional vendor to reset (all if None)
            user_id: Optional user to reset (all if None)
        """
        with self._lock:
            if vendor:
                # Reset specific vendor
                if vendor.value in self.vendor_buckets:
                    bucket = self.vendor_buckets[vendor.value]
                    bucket.tokens = bucket.max_tokens
                    bucket.last_refill = time.time()

                if user_id:
                    # Reset specific user
                    user_key = f"{vendor.value}:{user_id}"
                    if user_key in self.user_buckets:
                        bucket = self.user_buckets[user_key]
                        bucket.tokens = bucket.max_tokens
                        bucket.last_refill = time.time()
            else:
                # Reset all
                for bucket in self.vendor_buckets.values():
                    bucket.tokens = bucket.max_tokens
                    bucket.last_refill = time.time()

                for bucket in self.user_buckets.values():
                    bucket.tokens = bucket.max_tokens
                    bucket.last_refill = time.time()
