"""Synheart Cloud Connector - Shared base library for cloud wearable integrations."""

from .base import CloudConnectorBase
from .exceptions import (
    CloudConnectorError,
    OAuthError,
    TokenError,
    WebhookError,
    RateLimitError,
)
from .vendor_types import (
    VendorType,
    TokenStatus,
    EventType,
    OAuthTokens,
    WebhookEvent,
)
from .sync_state import SyncState, SyncCursor

__version__ = "0.1.0"

__all__ = [
    "CloudConnectorBase",
    "CloudConnectorError",
    "OAuthError",
    "TokenError",
    "WebhookError",
    "RateLimitError",
    "VendorType",
    "TokenStatus",
    "EventType",
    "OAuthTokens",
    "WebhookEvent",
    "SyncState",
    "SyncCursor",
]
