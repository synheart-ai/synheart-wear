# WHOOP Cloud Connector

Cloud-based connector for WHOOP wearable data integration with Synheart platform.

## Overview

This service implements the WHOOP integration following RFC-0002 architecture:
- **OAuth 2.0** authentication flow
- **Webhook receiving** for real-time data updates
- **Data fetching** from WHOOP API v2
- **Local development** with ngrok for SDK access

## Quick Start

### Prerequisites

- Python 3.11+
- WHOOP Developer Account (https://developer.whoop.com/)
- AWS Account (for production deployment)

### Installation

```bash
cd services/whoop-cloud

# Install dependencies
pip install -r requirements.txt

# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Local Development

```bash
# Start local development server (uses mocked AWS services)
python3 api_local.py
```

Server will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Testing

All integration tests are located in the `tests/` directory:

- `test_whoop_local.py` - Local integration tests (mocked services)
- `test_real_whoop.py` - Real WHOOP API OAuth flow test
- `test_data_fetch.py` - Data fetching endpoint tests
- `test_webhooks.py` - Webhook verification tests
- `test_end_to_end.py` - End-to-end integration tests
- `test_oauth_simple.py` - Simple OAuth tests

### Quick Test Runner

```bash
# Run all local integration tests
./run_tests.sh

# Check service status
./check_status.sh
```

### OAuth Flow Test

Test with your real WHOOP account:

```bash
# Terminal 1: Start server
python3 api_local.py

# Terminal 2: Run OAuth test
python3 tests/test_real_whoop.py
```

The test will open your browser for WHOOP authorization.

### Data Fetching Test

After completing OAuth:

```bash
python3 tests/test_data_fetch.py
```

### Webhook Test

Test webhook verification (no external dependencies):

```bash
python3 tests/test_webhooks.py
```

### Webhook with ngrok (Real WHOOP webhooks)

```bash
# Terminal 1: Start server
python3 api_local.py

# Terminal 2: Start ngrok
ngrok http 8000

# Configure webhook URL in WHOOP Developer Portal:
# https://your-ngrok-url/v1/webhooks/whoop
```

## API Endpoints

### OAuth

```bash
# Get authorization URL
GET /v1/oauth/authorize?redirect_uri={uri}&state={user_id}

# OAuth callback (automatic)
GET /v1/oauth/callback?code={code}&state={user_id}

# Disconnect user
DELETE /v1/oauth/disconnect?user_id={user_id}
```

### Data Fetching

```bash
# User profile
GET /v1/data/{user_id}/profile

# Collections (with optional date filtering and pagination)
GET /v1/data/{user_id}/recovery?start={iso8601}&end={iso8601}&limit={n}
GET /v1/data/{user_id}/sleep?start={iso8601}&end={iso8601}&limit={n}
GET /v1/data/{user_id}/workouts?start={iso8601}&end={iso8601}&limit={n}
GET /v1/data/{user_id}/cycles?start={iso8601}&end={iso8601}&limit={n}

# Individual resources
GET /v1/data/{user_id}/recovery/{id}
GET /v1/data/{user_id}/sleep/{id}
GET /v1/data/{user_id}/workouts/{id}
GET /v1/data/{user_id}/cycles/{id}
```

### Webhooks

```bash
# Receive webhook (HMAC-SHA256 verified)
POST /v1/webhooks/whoop
```

## Configuration

### Environment Variables

Create `.env.production` with your credentials:

```bash
# WHOOP Credentials
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_WEBHOOK_SECRET=your_webhook_secret

# Development (local mode)
LOCAL_MODE=true  # Use mocked AWS services (file-based token storage)
```

## Local Development

### Quick Start with CLI

```bash
# Start local development server (auto-starts ngrok)
wear start dev --vendor whoop --port 8000

# The CLI will automatically:
# - Start the local API server
# - Start ngrok tunnel
# - Show ngrok URL for SDK configuration
```

## Architecture

### Components

- **connector.py** - WhoopConnector implementation (extends CloudConnectorBase)
- **api.py** - FastAPI application with all endpoints
- **api_local.py** - Local development server with mocked AWS

### Data Flow

```
User → OAuth Flow → Access Token → Stored (encrypted)
                         ↓
WHOOP API → Webhooks → SQS Queue → Worker (future)
                         ↓
              Data Fetching → Normalize → Store
```

## Security

- **OAuth 2.0 with PKCE** - Secure authorization
- **Token encryption** - KMS (production) or base64 (local)
- **HMAC-SHA256 webhooks** - Signature verification
- **Replay protection** - 3-minute timestamp window
- **Rate limiting** - Token bucket algorithm

## Supported Data Types

- **Profile** - User information, email
- **Recovery** - HRV, resting heart rate, recovery score
- **Sleep** - Sleep score, efficiency, stages
- **Workouts** - Strain, calories, HR zones
- **Cycles** - Daily summaries

## Troubleshooting

### Server won't start

```bash
# Check port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

### OAuth fails

1. Verify credentials in `.env.production`
2. Check redirect URI registered in WHOOP Developer Portal
3. Ensure server is accessible

### Webhooks not received

1. Check ngrok is running: `curl http://127.0.0.1:4040/api/tunnels`
2. Verify webhook URL in WHOOP Developer Portal
3. Check webhook secret matches
4. Review server logs for errors

## Development Status

**Current (Legacy Service)**

This is the original standalone WHOOP service. For new development, see:
- `/services/synheart-wear-service/` - Unified multi-vendor service (recommended)

**Functionality:**
- ✅ OAuth flow
- ✅ Token management
- ✅ Data fetching (all endpoints)
- ✅ Webhook receiving
- ✅ Local testing
- ✅ Local development with auto ngrok

## References

- [WHOOP Developer Docs](https://developer.whoop.com/)
- [RFC-0002](../../docs/RFC-0002.md) - Unified Cloud Integration Structure
- [Synheart Connector Base](../../libs/py-cloud-connector/)

## License

Copyright © 2024 Synheart AI
