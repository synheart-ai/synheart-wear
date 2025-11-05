"""Custom exceptions for cloud connector library."""


class CloudConnectorError(Exception):
    """Base exception for all cloud connector errors."""

    def __init__(self, message: str, vendor: str | None = None, trace_id: str | None = None):
        self.message = message
        self.vendor = vendor
        self.trace_id = trace_id
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert exception to API error response format."""
        return {
            "error": {
                "code": self.__class__.__name__.replace("Error", "").lower(),
                "message": self.message,
                "vendor": self.vendor,
                "trace_id": self.trace_id,
            }
        }


class OAuthError(CloudConnectorError):
    """OAuth-related errors (exchange failed, invalid grant, etc.)."""


class TokenError(CloudConnectorError):
    """Token storage, retrieval, or encryption errors."""


class WebhookError(CloudConnectorError):
    """Webhook verification or parsing errors."""


class RateLimitError(CloudConnectorError):
    """Rate limiting errors (429 from vendor API)."""

    def __init__(
        self,
        message: str,
        vendor: str | None = None,
        trace_id: str | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message, vendor, trace_id)
        self.retry_after = retry_after


class EnqueueError(CloudConnectorError):
    """SQS enqueue failures."""


class VendorAPIError(CloudConnectorError):
    """Vendor API errors (5xx, timeouts, etc.)."""

    def __init__(
        self,
        message: str,
        vendor: str | None = None,
        trace_id: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message, vendor, trace_id)
        self.status_code = status_code
