"""Type definitions, enums, and Pydantic models for cloud connectors."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VendorType(str, Enum):
    """Supported wearable vendors."""

    WHOOP = "whoop"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    POLAR = "polar"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"


class TokenStatus(str, Enum):
    """Token lifecycle status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class EventType(str, Enum):
    """Webhook event types."""

    SLEEP_UPDATED = "sleep.updated"
    RECOVERY_UPDATED = "recovery.updated"
    WORKOUT_UPDATED = "workout.updated"
    CYCLE_UPDATED = "cycle.updated"
    HR_UPDATED = "hr.updated"
    HRV_UPDATED = "hrv.updated"
    USER_DISCONNECTED = "user.disconnected"


class OAuthTokens(BaseModel):
    """OAuth token set from vendor API."""

    access_token: str
    refresh_token: str | None = None
    expires_in: int  # seconds
    expires_at: datetime | None = None
    token_type: str = "Bearer"
    scopes: list[str] = Field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if access token has expired."""
        if not self.expires_at:
            return False
        # Use timezone-aware datetime for comparison
        from datetime import timezone
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware for comparison
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # If expires_at is naive, assume UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now >= expires_at


class TokenRecord(BaseModel):
    """Token storage record in DynamoDB."""

    pk: str  # vendor:user_id
    sk: str  # timestamp ISO8601
    access_token: str  # encrypted
    refresh_token: str | None = None  # encrypted
    expires_at: int  # epoch timestamp
    scopes: list[str]
    status: TokenStatus
    last_webhook_at: int | None = None  # epoch timestamp
    last_pull_at: int | None = None  # epoch timestamp
    vendor_meta: dict[str, Any] = Field(default_factory=dict)


class WebhookEvent(BaseModel):
    """Parsed webhook event from vendor."""

    vendor: VendorType
    event_type: str
    user_id: str
    resource_id: str | None = None
    trace_id: str
    received_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class SQSMessage(BaseModel):
    """SQS job queue message format."""

    vendor: VendorType
    event_type: str
    user_id: str
    resource_id: str | None = None
    trace_id: str
    received_at: datetime
    retries: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class RateLimitConfig(BaseModel):
    """Rate limiter configuration per vendor."""

    vendor: VendorType
    max_requests: int  # requests per time window
    time_window: int  # seconds
    max_burst: int | None = None  # optional burst allowance


class VendorConfig(BaseModel):
    """Vendor-specific configuration."""

    vendor: VendorType
    client_id: str
    client_secret: str
    webhook_secret: str | None = None
    base_url: str
    auth_url: str
    token_url: str
    scopes: list[str]
    rate_limit: RateLimitConfig | None = None
