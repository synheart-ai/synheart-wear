# Cloud Connector Interface Documentation

This document defines the interface that all vendor connectors **MUST** implement when extending `CloudConnectorBase`.

## Overview

Each vendor connector extends `CloudConnectorBase` and implements vendor-specific methods while inheriting common functionality for OAuth, token management, webhooks, and rate limiting.

---

## Required Implementations

### 1. Vendor Property

```python
@property
@abstractmethod
def vendor(self) -> VendorType:
    """Return the vendor type."""
    ...
```

**Purpose:** Identify the vendor for logging, metrics, and storage.

**Example:**
```python
@property
def vendor(self) -> VendorType:
    return VendorType.WHOOP
```

---

### 2. Webhook Verification

```python
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
```

**Purpose:** Validate that webhooks are genuinely from the vendor, preventing spoofing and replay attacks.

**Implementation Guide:**
- Extract signature and timestamp from headers
- Use `self.webhook_verifier.verify_hmac_sha256()` or similar
- Raise `WebhookError` if invalid

**Example (WHOOP):**
```python
async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
    signature, timestamp = extract_signature_from_headers(
        headers,
        signature_key="X-WHOOP-Signature",
        timestamp_key="X-WHOOP-Signature-Timestamp",
    )

    return self.webhook_verifier.verify_hmac_sha256(
        timestamp=timestamp,
        body=raw_body,
        signature=signature,
        vendor=self.vendor.value,
    )
```

---

### 3. Event Parsing

```python
@abstractmethod
async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
    """
    Parse vendor webhook payload into standard format.

    Args:
        raw_body: Raw request body

    Returns:
        Parsed event data with at minimum:
        - user_id: User identifier
        - type: Event type (e.g., "sleep.updated")
        - id: Resource ID (optional)
        - trace_id: Unique event ID for idempotency

    Raises:
        WebhookError: If payload is malformed
    """
    ...
```

**Purpose:** Convert vendor-specific webhook format to a normalized structure.

**Required Fields:**
- `user_id` (str): User identifier
- `type` (str): Event type
- `trace_id` (str): Unique event ID

**Optional Fields:**
- `id` (str): Resource ID
- Any vendor-specific data

**Example (WHOOP):**
```python
async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
    data = json.loads(raw_body)

    # Validate required fields
    if "user_id" not in data or "type" not in data:
        raise WebhookError("Missing required fields")

    return data
```

---

### 4. Data Fetching

```python
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

    Raises:
        RateLimitError: If vendor API rate limit exceeded
        VendorAPIError: If vendor API returns error
        OAuthError: If token is invalid/expired
    """
    ...
```

**Purpose:** Retrieve data from vendor API for backfills or webhook processing.

**Implementation Guide:**
1. Check rate limit: `self.check_rate_limit(user_id)`
2. Get valid token: `tokens = await self.refresh_if_needed(user_id)`
3. Make API request with `tokens.access_token`
4. Handle errors:
   - 429 → Raise `RateLimitError`
   - 401/403 → Raise `OAuthError`
   - 5xx → Raise `VendorAPIError`
5. Update timestamp: `self.token_store.update_last_pull(self.vendor, user_id)`

**Example (WHOOP):**
```python
async def fetch_data(
    self,
    user_id: str,
    resource_type: str,
    resource_id: str | None = None,
) -> dict[str, Any]:
    # Check rate limit
    self.check_rate_limit(user_id)

    # Get valid token
    tokens = await self.refresh_if_needed(user_id)

    # Build URL
    url = f"{self.config.base_url}/v1/{resource_type}"
    if resource_id:
        url += f"/{resource_id}"

    # Make request
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )

        if response.status_code == 429:
            raise RateLimitError(...)

        if response.status_code != 200:
            raise VendorAPIError(...)

        # Update timestamp
        self.token_store.update_last_pull(self.vendor, user_id)

        return response.json()
```

---

## Inherited Methods (DO NOT Override)

These methods are provided by `CloudConnectorBase` and should **NOT** be overridden:

### OAuth Methods

| Method | Purpose |
|--------|---------|
| `build_authorization_url()` | Generate OAuth consent URL |
| `exchange_code()` | Exchange authorization code for tokens |
| `refresh_if_needed()` | Refresh expired access token |
| `revoke_tokens()` | Revoke and delete user tokens |

### Webhook Methods

| Method | Purpose |
|--------|---------|
| `process_webhook()` | Verify, parse, and enqueue webhook event |

### Rate Limiting Methods

| Method | Purpose |
|--------|---------|
| `check_rate_limit()` | Check if request is within rate limits |
| `get_rate_limit_status()` | Get remaining rate limit tokens |

---

## Configuration

Each connector requires a `VendorConfig` with:

```python
VendorConfig(
    vendor=VendorType.WHOOP,
    client_id="your_client_id",
    client_secret="your_client_secret",
    webhook_secret="your_webhook_secret",
    base_url="https://api.prod.whoop.com",
    auth_url="https://api.prod.whoop.com/oauth/authorize",
    token_url="https://api.prod.whoop.com/oauth/token",
    scopes=["read:recovery", "read:sleep", "read:workout"],
    rate_limit=RateLimitConfig(
        vendor=VendorType.WHOOP,
        max_requests=100,
        time_window=60,
    ),
)
```

---

## Testing Requirements

Each connector **MUST** have unit tests for:

1. **Webhook Verification**
   - Valid signature
   - Invalid signature
   - Expired timestamp
   - Missing headers

2. **Event Parsing**
   - Valid payload
   - Malformed JSON
   - Missing required fields

3. **Data Fetching**
   - Successful fetch
   - Rate limit handling
   - Token refresh
   - Error responses (4xx, 5xx)

**Example Test:**
```python
@pytest.mark.asyncio
async def test_verify_webhook_valid():
    connector = WhoopConnector(config, token_store, queue, rate_limiter)

    headers = {
        "X-WHOOP-Signature": "valid_signature",
        "X-WHOOP-Signature-Timestamp": "1234567890",
    }
    body = b'{"user_id": 123, "type": "recovery.updated"}'

    assert await connector.verify_webhook(headers, body) is True
```

---

## Error Handling

Use these standard exceptions:

| Exception | When to Use |
|-----------|-------------|
| `WebhookError` | Webhook verification or parsing fails |
| `OAuthError` | OAuth exchange or refresh fails |
| `RateLimitError` | Vendor API rate limit exceeded (include `retry_after`) |
| `VendorAPIError` | Vendor API returns error (include `status_code`) |
| `TokenError` | Token storage/retrieval fails |

---

## Observability

Each connector should log:

- **INFO**: Successful operations (token exchange, webhook received, data fetched)
- **WARN**: Rate limits hit, retries triggered
- **ERROR**: Failures (verification failed, API errors)

**Log Format:**
```python
logger.info(
    "Webhook processed",
    extra={
        "vendor": self.vendor.value,
        "user_id": user_id,
        "event_type": event_type,
        "trace_id": trace_id,
    }
)
```

---

## Checklist for New Connectors

- [ ] Extend `CloudConnectorBase`
- [ ] Implement `vendor` property
- [ ] Implement `verify_webhook()` with vendor's signature scheme
- [ ] Implement `parse_event()` to extract required fields
- [ ] Implement `fetch_data()` with rate limiting and error handling
- [ ] Create `VendorConfig` with correct URLs and scopes
- [ ] Write unit tests for all abstract methods
- [ ] Add vendor to `VendorType` enum
- [ ] Document vendor-specific quirks in connector docstring

---

## Reference Implementation

See `services/whoop-cloud/connector.py` for a complete reference implementation.
