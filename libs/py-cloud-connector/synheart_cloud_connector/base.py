"""Base class for all cloud wearable connectors."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from .exceptions import OAuthError, RateLimitError
from .jobs import JobQueue
from .oauth import OAuthHandler
from .rate_limit import RateLimiter
from .tokens import TokenStore
from .vendor_types import (
    OAuthTokens,
    RateLimitConfig,
    VendorConfig,
    VendorType,
    WebhookEvent,
)
from .webhooks import WebhookVerifier


class CloudConnectorBase(ABC):
    """
    Abstract base class for cloud wearable connectors.

    Each vendor connector extends this class and implements vendor-specific methods.

    Required implementations:
    - auth_base_url() - OAuth authorization URL
    - token_url() - Token exchange endpoint
    - scopes() - Required OAuth scopes
    - verify_webhook() - Webhook signature validation
    - parse_event() - Parse vendor webhook payload

    Inherited functionality:
    - OAuth token exchange and refresh
    - Token storage with KMS encryption
    - Webhook verification and enqueueing
    - Rate limiting
    """

    def __init__(
        self,
        config: VendorConfig,
        token_store: TokenStore,
        queue: JobQueue,
        rate_limiter: RateLimiter,
    ):
        self.config = config
        self.token_store = token_store
        self.queue = queue
        self.rate_limiter = rate_limiter

        # Initialize OAuth handler
        self.oauth_handler = OAuthHandler(
            client_id=config.client_id,
            client_secret=config.client_secret,
            auth_url=config.auth_url,
            token_url=config.token_url,
        )

        # Initialize webhook verifier if secret provided
        self.webhook_verifier = (
            WebhookVerifier(config.webhook_secret)
            if config.webhook_secret
            else None
        )

        # Configure rate limiting if provided
        if config.rate_limit:
            self.rate_limiter.configure(config.rate_limit)

    # ============================================================================
    # Abstract Methods - MUST be implemented by vendor connectors
    # ============================================================================

    @property
    @abstractmethod
    def vendor(self) -> VendorType:
        """Return the vendor type."""
        ...

    @abstractmethod
    async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        """
        Verify webhook signature and authenticity.

        Args:
            headers: HTTP headers from webhook request
            raw_body: Raw request body (before parsing)

        Returns:
            True if webhook is valid

        Raises:
            WebhookError: If verification fails
        """
        ...

    @abstractmethod
    async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
        """
        Parse vendor webhook payload into standard format.

        Args:
            raw_body: Raw request body

        Returns:
            Parsed event data
        """
        ...

    @abstractmethod
    async def fetch_data(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch data from vendor API.

        Args:
            user_id: User identifier
            resource_type: Type of data to fetch (e.g., 'sleep', 'recovery')
            resource_id: Optional specific resource ID

        Returns:
            Raw vendor data
        """
        ...

    # ============================================================================
    # OAuth Methods - Inherited by all connectors
    # ============================================================================

    def build_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        **extra_params: Any,
    ) -> str:
        """
        Build OAuth authorization URL for user consent.

        Args:
            redirect_uri: Callback URL after authorization
            state: Optional state parameter for CSRF protection
            **extra_params: Additional vendor-specific parameters

        Returns:
            Full authorization URL
        """
        return self.oauth_handler.build_authorization_url(
            redirect_uri=redirect_uri,
            scopes=self.config.scopes,
            state=state,
            **extra_params,
        )

    async def exchange_code(
        self,
        user_id: str,
        code: str,
        redirect_uri: str,
        vendor_meta: dict[str, Any] | None = None,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access tokens.

        Args:
            user_id: User identifier
            code: Authorization code from vendor
            redirect_uri: Must match authorization URL
            vendor_meta: Optional vendor-specific metadata

        Returns:
            OAuthTokens

        Raises:
            OAuthError: If exchange fails
        """
        # Exchange code for tokens
        tokens = await self.oauth_handler.exchange_code(code, redirect_uri)

        # Store encrypted tokens
        self.token_store.save_tokens(
            vendor=self.vendor,
            user_id=user_id,
            tokens=tokens,
            vendor_meta=vendor_meta,
        )

        return tokens

    async def refresh_if_needed(self, user_id: str) -> OAuthTokens:
        """
        Refresh access token if expired.

        Args:
            user_id: User identifier

        Returns:
            Valid OAuthTokens (refreshed if needed)

        Raises:
            OAuthError: If refresh fails
        """
        tokens = self.token_store.get_tokens(self.vendor, user_id)

        if not tokens:
            raise OAuthError(
                f"No tokens found for {self.vendor.value}:{user_id}",
                vendor=self.vendor.value,
            )

        # Check if token is expired
        if tokens.is_expired():
            if not tokens.refresh_token:
                raise OAuthError(
                    "Access token expired and no refresh token available",
                    vendor=self.vendor.value,
                )

            # Refresh token
            new_tokens = await self.oauth_handler.refresh_token(tokens.refresh_token)

            # Store new tokens
            self.token_store.save_tokens(
                vendor=self.vendor,
                user_id=user_id,
                tokens=new_tokens,
            )

            return new_tokens

        return tokens

    async def revoke_tokens(self, user_id: str) -> bool:
        """
        Revoke user tokens and mark as disconnected.

        Args:
            user_id: User identifier

        Returns:
            True if revocation succeeded
        """
        tokens = self.token_store.get_tokens(self.vendor, user_id)

        if tokens:
            # Try to revoke with vendor
            try:
                await self.oauth_handler.revoke_token(tokens.access_token)
            except Exception:
                # Log but don't fail - we'll still mark as revoked locally
                pass

        # Mark as revoked in our database
        self.token_store.revoke_tokens(self.vendor, user_id)

        return True

    # ============================================================================
    # Webhook Methods - Inherited by all connectors
    # ============================================================================

    async def process_webhook(
        self,
        headers: dict[str, Any],
        raw_body: bytes,
    ) -> str:
        """
        Process incoming webhook event.

        Args:
            headers: HTTP headers
            raw_body: Raw request body

        Returns:
            Message ID from SQS

        Raises:
            WebhookError: If verification fails
        """
        # Verify webhook signature
        await self.verify_webhook(headers, raw_body)

        # Parse event
        event_data = await self.parse_event(raw_body)

        # Create webhook event
        event = WebhookEvent(
            vendor=self.vendor,
            event_type=event_data.get("type", "unknown"),
            user_id=str(event_data.get("user_id")),
            resource_id=event_data.get("id"),
            trace_id=event_data.get("trace_id", str(uuid.uuid4())),
            received_at=datetime.now(timezone.utc),
            payload=event_data,
        )

        # Enqueue for processing
        message_id = self.queue.enqueue_event(event)

        # Update last webhook timestamp
        self.token_store.update_last_webhook(self.vendor, event.user_id)

        return message_id

    # ============================================================================
    # Rate Limiting - Inherited by all connectors
    # ============================================================================

    def check_rate_limit(self, user_id: str | None = None, tokens: float = 1.0) -> None:
        """
        Check if request is within rate limits.

        Args:
            user_id: Optional user identifier
            tokens: Number of tokens to consume

        Raises:
            RateLimitError: If rate limit exceeded
        """
        self.rate_limiter.check_limit(self.vendor, user_id, tokens)

    def get_rate_limit_status(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get remaining rate limit tokens.

        Args:
            user_id: Optional user identifier

        Returns:
            Dict with remaining tokens
        """
        return self.rate_limiter.get_remaining(self.vendor, user_id)

    # ============================================================================
    # Utility Methods
    # ============================================================================

    async def close(self) -> None:
        """Close HTTP connections."""
        await self.oauth_handler.close()

    async def __aenter__(self) -> "CloudConnectorBase":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        await self.close()
