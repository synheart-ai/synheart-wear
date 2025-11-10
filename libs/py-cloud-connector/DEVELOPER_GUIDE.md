# Cloud Connector Developer Guide

Quick start guide for building new vendor connectors using the Synheart Cloud Connector library.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Creating a New Connector](#creating-a-new-connector)
3. [Testing Your Connector](#testing-your-connector)
4. [Deploying](#deploying)
5. [Common Patterns](#common-patterns)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# Install the library
cd libs/py-cloud-connector
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest --cov=synheart_cloud_connector --cov-report=term-missing
```

### Example: Using the WHOOP Connector

```python
from synheart_cloud_connector import CloudConnectorBase
from synheart_cloud_connector.jobs import JobQueue
from synheart_cloud_connector.rate_limit import RateLimiter
from synheart_cloud_connector.tokens import TokenStore
from synheart_cloud_connector.vendor_types import VendorConfig, VendorType

# Initialize dependencies
token_store = TokenStore(table_name="cloud_connector_tokens")
queue = JobQueue(queue_name="cloud-connector-events")
rate_limiter = RateLimiter()

# Configure WHOOP
config = VendorConfig(
    vendor=VendorType.WHOOP,
    client_id="your_client_id",
    client_secret="your_client_secret",
    webhook_secret="your_webhook_secret",
    base_url="https://api.prod.whoop.com",
    auth_url="https://api.prod.whoop.com/oauth/authorize",
    token_url="https://api.prod.whoop.com/oauth/token",
    scopes=["read:recovery", "read:sleep", "read:workout"],
)

# Import and initialize connector
from services.whoop_cloud.connector import WhoopConnector

whoop = WhoopConnector(config, token_store, queue, rate_limiter)

# OAuth flow
auth_url = whoop.build_authorization_url(
    redirect_uri="https://yourapp.com/callback",
    state="user123"
)

# After user authorizes, exchange code
tokens = await whoop.exchange_code(
    user_id="user123",
    code="auth_code_from_callback",
    redirect_uri="https://yourapp.com/callback"
)
```

---

## Creating a New Connector

### Step 1: Add Vendor to Enum

Edit `synheart_cloud_connector/vendor_types.py`:

```python
class VendorType(str, Enum):
    WHOOP = "whoop"
    GARMIN = "garmin"
    FITBIT = "fitbit"     # Add your vendor
    POLAR = "polar"       # Add your vendor
    # ...
```

### Step 2: Create Connector Class

Create `services/<vendor>-cloud/connector.py`:

```python
from typing import Any
from synheart_cloud_connector import CloudConnectorBase
from synheart_cloud_connector.vendor_types import VendorType

class FitbitConnector(CloudConnectorBase):
    @property
    def vendor(self) -> VendorType:
        return VendorType.FITBIT

    async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        # Implement Fitbit webhook verification
        # See Fitbit API docs for signature scheme
        ...

    async def parse_event(self, raw_body: bytes) -> dict[str, Any]:
        # Parse Fitbit webhook payload
        # Must return: user_id, type, trace_id
        ...

    async def fetch_data(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        # Fetch data from Fitbit API
        self.check_rate_limit(user_id)
        tokens = await self.refresh_if_needed(user_id)

        # Make API call...
        ...
```

### Step 3: Create FastAPI Application

Create `services/<vendor>-cloud/api.py`:

```python
from fastapi import FastAPI, Request
from synheart_cloud_connector.vendor_types import VendorConfig, VendorType

from .connector import FitbitConnector

app = FastAPI(title="Fitbit Cloud Connector")

# Initialize connector
config = VendorConfig(
    vendor=VendorType.FITBIT,
    client_id=os.getenv("FITBIT_CLIENT_ID"),
    client_secret=os.getenv("FITBIT_CLIENT_SECRET"),
    webhook_secret=os.getenv("FITBIT_WEBHOOK_SECRET"),
    base_url="https://api.fitbit.com",
    auth_url="https://www.fitbit.com/oauth2/authorize",
    token_url="https://api.fitbit.com/oauth2/token",
    scopes=["heartrate", "activity", "sleep"],
)

fitbit = FitbitConnector(config, token_store, queue, rate_limiter)

@app.post("/webhooks/fitbit")
async def webhook_handler(request: Request):
    headers = dict(request.headers)
    raw_body = await request.body()
    await fitbit.process_webhook(headers, raw_body)
    return {"status": "ok"}
```

### Step 4: Add Normalization

Edit `libs/py-normalize/synheart_normalize/to_synheart.py`:

```python
def normalize_fitbit(vendor_data: dict[str, Any], sample_type: SampleType) -> SynheartSample:
    """Normalize Fitbit data to Synheart schema."""

    if sample_type == SampleType.HEART_RATE:
        return SynheartSample(
            timestamp_utc=vendor_data["dateTime"],
            source=DataSource.FITBIT,
            sample_type=SampleType.HEART_RATE,
            hr_bpm=vendor_data["value"]["bpm"],
            meta={"fitbit_device": vendor_data.get("device")},
        )

    # Add other sample types...
```

---

## Testing Your Connector

### Unit Test Template

Create `tests/test_<vendor>_connector.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from synheart_cloud_connector import WebhookError
from services.fitbit_cloud.connector import FitbitConnector

@pytest.fixture
def fitbit_connector():
    config = MagicMock()
    token_store = MagicMock()
    queue = MagicMock()
    rate_limiter = MagicMock()

    return FitbitConnector(config, token_store, queue, rate_limiter)

@pytest.mark.asyncio
async def test_verify_webhook_valid(fitbit_connector):
    headers = {"X-Fitbit-Signature": "valid_sig"}
    body = b'{"user_id": "123"}'

    result = await fitbit_connector.verify_webhook(headers, body)
    assert result is True

@pytest.mark.asyncio
async def test_verify_webhook_invalid(fitbit_connector):
    headers = {"X-Fitbit-Signature": "invalid_sig"}
    body = b'{"user_id": "123"}'

    with pytest.raises(WebhookError):
        await fitbit_connector.verify_webhook(headers, body)
```

### Integration Test Template

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_oauth_flow(fitbit_connector):
    # Test authorization URL
    url = fitbit_connector.build_authorization_url(
        redirect_uri="http://localhost/callback",
        state="user123"
    )
    assert "client_id" in url
    assert "scope" in url

    # Test code exchange (requires mock or test account)
    # tokens = await fitbit_connector.exchange_code(...)
```

---

## Deploying

### Local Development

```bash
# Set environment variables
export FITBIT_CLIENT_ID=xxx
export FITBIT_CLIENT_SECRET=xxx
export DYNAMODB_TABLE=cloud_connector_tokens_dev
export AWS_REGION=us-east-1

# Run locally
cd services/fitbit-cloud
uvicorn api:app --reload --port 8000
```

### AWS Lambda Deployment

Coming soon with Laminar!

---

## Common Patterns

### Pattern 1: Handling Pagination

```python
async def fetch_all_pages(self, user_id: str, resource_type: str) -> list[dict]:
    results = []
    next_token = None

    while True:
        page = await self.fetch_data(
            user_id,
            resource_type,
            extra_params={"next": next_token} if next_token else {}
        )

        results.extend(page["items"])
        next_token = page.get("next_token")

        if not next_token:
            break

    return results
```

### Pattern 2: Batch Backfills

```python
async def backfill_date_range(
    self,
    user_id: str,
    start_date: datetime,
    end_date: datetime,
):
    current = start_date

    while current <= end_date:
        # Fetch one day at a time
        data = await self.fetch_data(
            user_id,
            "activities",
            extra_params={"date": current.strftime("%Y-%m-%d")}
        )

        # Normalize and store
        for item in data:
            sample = normalize_to_synheart(item, DataSource.FITBIT, SampleType.ACTIVITY)
            # Store sample...

        current += timedelta(days=1)
```

### Pattern 3: Webhook Signature Verification

Most vendors use HMAC-SHA256:

```python
async def verify_webhook(self, headers: dict[str, Any], raw_body: bytes) -> bool:
    signature = headers.get("X-Vendor-Signature")
    timestamp = headers.get("X-Vendor-Timestamp")

    return self.webhook_verifier.verify_hmac_sha256(
        timestamp=timestamp,
        body=raw_body,
        signature=signature,
        vendor=self.vendor.value,
    )
```

---

## Troubleshooting

### Issue: Token Refresh Fails

**Symptoms:** `OAuthError: Token refresh failed`

**Solutions:**
1. Check token hasn't been revoked by user
2. Verify `refresh_token` is being stored
3. Check vendor API status
4. Verify scopes haven't changed

```python
# Debug token status
tokens = token_store.get_tokens(VendorType.FITBIT, user_id)
print(f"Expires at: {tokens.expires_at}")
print(f"Is expired: {tokens.is_expired()}")
```

### Issue: Rate Limit Exceeded

**Symptoms:** `RateLimitError: Vendor rate limit exceeded`

**Solutions:**
1. Check rate limit config matches vendor limits
2. Implement exponential backoff
3. Use webhooks instead of polling

```python
# Check current rate limit status
status = connector.get_rate_limit_status(user_id="user123")
print(f"Vendor remaining: {status['vendor']['remaining']}")
print(f"User remaining: {status['user']['remaining']}")
```

### Issue: Webhook Verification Fails

**Symptoms:** `WebhookError: HMAC signature mismatch`

**Solutions:**
1. Verify webhook secret is correct
2. Check timestamp is being extracted correctly
3. Ensure raw body is used (not parsed)
4. Check replay window (default 3 minutes)

```python
# Debug webhook verification
print(f"Headers: {headers}")
print(f"Raw body: {raw_body}")
print(f"Expected signature: {expected_sig}")
print(f"Received signature: {received_sig}")
```

---

## Reference Documentation

- **Interface Documentation:** `docs/CONNECTOR_INTERFACE.md`
- **Implementation Summary:** `docs/IMPLEMENTATION_SUMMARY.md`
- **RFC-0002:** `docs/RFC-0002.md`
- **WHOOP Reference:** `services/whoop-cloud/connector.py`

---

## Support

For questions or issues:
1. Check `docs/CONNECTOR_INTERFACE.md` for interface requirements
2. Review WHOOP connector for reference implementation
3. Review unit tests for usage examples
4. Open an issue in the repo with details
