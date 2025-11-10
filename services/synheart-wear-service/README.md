# Synheart Wear Service

Unified cloud connector service for all wearable vendors (WHOOP, Garmin, etc.).

## Architecture

- **Single Lambda Function**: All vendors handled in one service
- **Path-Based Routing**: `/v1/whoop-cloud/...`, `/v1/garmin-cloud/...`
- **Shared Infrastructure**: DynamoDB table and KMS key shared across vendors
- **Vendor-Specific Queues**: Separate SQS queues per vendor for isolation

## Routes

### WHOOP
- `GET /v1/whoop-cloud/oauth/authorize` - OAuth authorization
- `GET /v1/whoop-cloud/oauth/callback` - OAuth callback (GET)
- `POST /v1/whoop-cloud/oauth/callback` - OAuth callback (POST, mobile)
- `POST /v1/whoop-cloud/webhooks/whoop` - Webhook handler
- `DELETE /v1/whoop-cloud/oauth/disconnect` - Disconnect

### Garmin
- `GET /v1/garmin-cloud/oauth/authorize` - OAuth authorization
- `GET /v1/garmin-cloud/oauth/callback` - OAuth callback (GET)
- `POST /v1/garmin-cloud/oauth/callback` - OAuth callback (POST, mobile)
- `POST /v1/garmin-cloud/webhooks/garmin` - Webhook handler
- `DELETE /v1/garmin-cloud/oauth/disconnect` - Disconnect

### Health
- `GET /health` - Health check

## Local Development

```bash
# Start unified service with CLI (auto-starts ngrok)
wear start dev --port 8000

# The CLI will automatically:
# - Start the local API server
# - Start ngrok tunnel
# - Show ngrok URL for SDK configuration
```

## Environment Variables

### Shared Resources
- `DYNAMODB_TABLE` - Shared DynamoDB table name
- `KMS_KEY_ID` - Shared KMS key ID

### Vendor-Specific Queues
- `WHOOP_SQS_QUEUE_URL` - WHOOP event queue URL
- `GARMIN_SQS_QUEUE_URL` - Garmin event queue URL

### Vendor Secrets
- `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_WEBHOOK_SECRET`, `WHOOP_REDIRECT_URI`
- `GARMIN_CLIENT_ID`, `GARMIN_CLIENT_SECRET`, `GARMIN_WEBHOOK_SECRET`, `GARMIN_REDIRECT_URI`

