# Cloud Connector Services

This directory contains cloud connector services for wearable integrations.

## 🏗️ Architecture

### Unified Service (Recommended)

**Location**: `synheart-wear-service/`

A single Lambda function that handles all vendors with path-based routing:

- `/v1/whoop-cloud/*` - WHOOP endpoints
- `/v1/garmin-cloud/*` - Garmin endpoints
- `/health` - Health check

**Benefits**:
- ✅ Single deployment
- ✅ Shared environment configuration
- ✅ Reduced cold starts
- ✅ Simplified routing
- ✅ One API Gateway endpoint

### Individual Services (Legacy)

For per-vendor deployments (if needed):

- `whoop-cloud/` - WHOOP-only service
- `garmin-cloud/` - Garmin-only service

## 🚀 Quick Start

### Local Development

```bash
# Start unified service with CLI (auto-starts ngrok)
wear start dev --port 8000

# The CLI will automatically:
# - Start the local API server
# - Start ngrok tunnel
# - Show ngrok URL for SDK configuration
```

### Routes

#### WHOOP
- `GET /v1/whoop-cloud/oauth/authorize`
- `GET /v1/whoop-cloud/oauth/callback`
- `POST /v1/whoop-cloud/oauth/callback`
- `POST /v1/whoop-cloud/webhooks/whoop`
- `DELETE /v1/whoop-cloud/oauth/disconnect`

#### Garmin
- `GET /v1/garmin-cloud/oauth/authorize`
- `GET /v1/garmin-cloud/oauth/callback`
- `POST /v1/garmin-cloud/oauth/callback`
- `POST /v1/garmin-cloud/webhooks/garmin`
- `DELETE /v1/garmin-cloud/oauth/disconnect`

## 📋 Environment Variables

### Shared Resources
- `DYNAMODB_TABLE` - Shared table name
- `KMS_KEY_ID` - Shared encryption key

### Vendor Queues
- `WHOOP_SQS_QUEUE_URL` - WHOOP event queue
- `GARMIN_SQS_QUEUE_URL` - Garmin event queue

### Vendor Secrets
- `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_WEBHOOK_SECRET`, `WHOOP_REDIRECT_URI`
- `GARMIN_CLIENT_ID`, `GARMIN_CLIENT_SECRET`, `GARMIN_WEBHOOK_SECRET`, `GARMIN_REDIRECT_URI`

## 📚 Documentation

- [Synheart Wear Service README](./synheart-wear-service/README.md)
- [CLI README](../cli/README.md) - Local development guide

---

**Made with ❤️ by Synheart Team**
