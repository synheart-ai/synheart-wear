"""Tests for rate limiting functionality."""

import time

import pytest

from synheart_cloud_connector.exceptions import RateLimitError
from synheart_cloud_connector.rate_limit import RateLimiter, TokenBucket
from synheart_cloud_connector.vendor_types import RateLimitConfig, VendorType


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_consume_within_limit(self):
        """Test consuming tokens within limit."""
        bucket = TokenBucket(
            max_tokens=10.0,
            refill_rate=1.0,
            tokens=10.0,
            last_refill=time.time(),
        )

        assert bucket.consume(5.0) is True
        assert bucket.tokens == 5.0

    def test_consume_exceeds_limit(self):
        """Test consuming more tokens than available."""
        bucket = TokenBucket(
            max_tokens=10.0,
            refill_rate=1.0,
            tokens=3.0,
            last_refill=time.time(),
        )

        assert bucket.consume(5.0) is False
        assert bucket.tokens == 3.0  # Unchanged

    def test_refill_over_time(self):
        """Test token refill over time."""
        bucket = TokenBucket(
            max_tokens=10.0,
            refill_rate=2.0,  # 2 tokens per second
            tokens=0.0,
            last_refill=time.time() - 3.0,  # 3 seconds ago
        )

        bucket._refill()

        # Should have refilled 6 tokens (2 * 3)
        assert bucket.tokens >= 5.0
        assert bucket.tokens <= 7.0  # Allow some timing variance

    def test_refill_does_not_exceed_max(self):
        """Test refill stops at max tokens."""
        bucket = TokenBucket(
            max_tokens=10.0,
            refill_rate=5.0,
            tokens=8.0,
            last_refill=time.time() - 5.0,
        )

        bucket._refill()

        # Should cap at 10, not go above
        assert bucket.tokens == 10.0

    def test_time_until_available(self):
        """Test calculating wait time."""
        bucket = TokenBucket(
            max_tokens=10.0,
            refill_rate=1.0,
            tokens=2.0,
            last_refill=time.time(),
        )

        # Need 5 tokens, have 2, so need 3 more
        wait_time = bucket.time_until_available(5.0)
        assert wait_time >= 2.5
        assert wait_time <= 3.5


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_configure_vendor(self):
        """Test configuring rate limit for vendor."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=100,
            time_window=60,
        )

        limiter.configure(config)

        assert VendorType.WHOOP in limiter.configs
        assert "whoop" in limiter.vendor_buckets

    def test_check_limit_within_quota(self):
        """Test request within rate limit."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=10,
            time_window=60,
        )
        limiter.configure(config)

        # Should not raise
        limiter.check_limit(VendorType.WHOOP)

    def test_check_limit_exceeds_quota(self):
        """Test request exceeding rate limit."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=3,
            time_window=60,
        )
        limiter.configure(config)

        # First 3 requests should succeed
        limiter.check_limit(VendorType.WHOOP)
        limiter.check_limit(VendorType.WHOOP)
        limiter.check_limit(VendorType.WHOOP)

        # 4th request should fail
        with pytest.raises(RateLimitError) as exc_info:
            limiter.check_limit(VendorType.WHOOP)

        assert exc_info.value.vendor == "whoop"
        assert exc_info.value.retry_after is not None

    def test_check_limit_no_config(self):
        """Test request with no rate limit configured."""
        limiter = RateLimiter()

        # Should allow all requests without config
        for _ in range(100):
            limiter.check_limit(VendorType.GARMIN)

    def test_per_user_rate_limiting(self):
        """Test per-user rate limits."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=2,
            time_window=60,
        )
        limiter.configure(config)

        # User1 makes 2 requests
        limiter.check_limit(VendorType.WHOOP, user_id="user1")
        limiter.check_limit(VendorType.WHOOP, user_id="user1")

        # User1's 3rd request should fail
        with pytest.raises(RateLimitError):
            limiter.check_limit(VendorType.WHOOP, user_id="user1")

        # User2 should still be able to make requests
        limiter.check_limit(VendorType.WHOOP, user_id="user2")

    def test_get_remaining(self):
        """Test getting remaining tokens."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=10,
            time_window=60,
        )
        limiter.configure(config)

        # Make some requests
        limiter.check_limit(VendorType.WHOOP, user_id="user1")
        limiter.check_limit(VendorType.WHOOP, user_id="user1")
        limiter.check_limit(VendorType.WHOOP, user_id="user1")

        remaining = limiter.get_remaining(VendorType.WHOOP, user_id="user1")

        assert "vendor" in remaining
        assert "user" in remaining
        assert remaining["user"]["remaining"] <= 7

    def test_reset_vendor(self):
        """Test resetting vendor rate limit."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=2,
            time_window=60,
        )
        limiter.configure(config)

        # Exhaust limit
        limiter.check_limit(VendorType.WHOOP)
        limiter.check_limit(VendorType.WHOOP)

        # Should fail
        with pytest.raises(RateLimitError):
            limiter.check_limit(VendorType.WHOOP)

        # Reset
        limiter.reset(VendorType.WHOOP)

        # Should now succeed
        limiter.check_limit(VendorType.WHOOP)

    def test_reset_all(self):
        """Test resetting all rate limits."""
        limiter = RateLimiter()

        config = RateLimitConfig(
            vendor=VendorType.WHOOP,
            max_requests=1,
            time_window=60,
        )
        limiter.configure(config)

        # Exhaust limit
        limiter.check_limit(VendorType.WHOOP)

        with pytest.raises(RateLimitError):
            limiter.check_limit(VendorType.WHOOP)

        # Reset all
        limiter.reset()

        # Should succeed
        limiter.check_limit(VendorType.WHOOP)
