# Synheart Cloud Connector

Shared base library for all Synheart cloud-based wearable integrations (WHOOP, Garmin, Fitbit, Polar, etc.).

## Overview

This library provides a unified abstraction for:
- **OAuth 2.0 flows** (authorization code exchange, token refresh)
- **Token storage** (DynamoDB with KMS encryption)
- **Webhook verification** (HMAC signatures, replay protection)
- **Job queue management** (SQS enqueueing and processing)
- **Rate limiting** (token bucket algorithm, vendor API throttling)

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

### Creating a Vendor Connector

```python
from synheart_cloud_connector import CloudConnectorBase

class WhoopConnector(CloudConnectorBase):
    vendor = "whoop"

    def auth_base_url(self) -> str:
        return "https://api.prod.whoop.com/oauth"

    def token_url(self) -> str:
        return "https://api.prod.whoop.com/oauth/token"

    def scopes(self) -> list[str]:
        return ["read:recovery", "read:sleep", "read:workout"]

    def verify_webhook(self, headers: dict, raw_body: bytes) -> bool:
        # WHOOP-specific HMAC validation
        timestamp = headers.get("X-WHOOP-Signature-Timestamp")
        signature = headers.get("X-WHOOP-Signature")
        return self.verify_hmac_sha256(timestamp, raw_body, signature)

    def parse_event(self, raw_body: bytes) -> dict:
        import json
        return json.loads(raw_body)
```

## Architecture

Each vendor connector extends `CloudConnectorBase` and implements:

### Required Methods
- `auth_base_url()` - OAuth authorization URL
- `token_url()` - Token exchange endpoint
- `scopes()` - Required OAuth scopes
- `verify_webhook()` - Webhook signature validation
- `parse_event()` - Parse vendor webhook payload

### Inherited Methods
- `exchange_code()` - Exchange authorization code for tokens
- `refresh_if_needed()` - Refresh expired access tokens
- `enqueue_event()` - Push events to SQS
- `get_user_tokens()` - Retrieve encrypted tokens from DynamoDB
- `revoke_tokens()` - Revoke and delete user tokens

## Testing

```bash
pytest
```

With coverage:

```bash
pytest --cov=synheart_cloud_connector --cov-report=term-missing
```

## Directory Structure

```
synheart_cloud_connector/
├── __init__.py
├── base.py              # CloudConnectorBase abstract class
├── oauth.py             # OAuth utilities
├── tokens.py            # TokenStore (DynamoDB + KMS)
├── webhooks.py          # Webhook verification utilities
├── jobs.py              # JobQueue (SQS)
├── rate_limit.py        # RateLimiter (token bucket)
├── vendor_types.py      # Type definitions and enums
└── exceptions.py        # Custom exceptions
```

## Contributing

See the main [RFC-0002](../../docs/RFC-0002.md) for architecture decisions and design principles.
