# Synheart Wear CLI (`wear`)

Command-line tool for local development, testing, and operations of the Synheart Wear cloud connector.

## 🚀 Installation

### Quick Install

```bash
cd /Users/izzy/Desktop/synheart/synheart-wear/cli

# Install dependencies
pip3 install --break-system-packages -r requirements.txt

# Install CLI tool
pip3 install --break-system-packages -e .

# Verify installation
wear --help
```

### Alternative: Run Directly

```bash
cd /Users/izzy/Desktop/synheart/synheart-wear/cli
python3 wear.py --help
```

## 📖 Commands

### `wear start` - Start Development Server

Start local development server for testing.

```bash
# Start WHOOP connector
wear start dev --vendor whoop --port 8000

# Start with auto-open browser for OAuth
wear start dev --vendor whoop --port 8000 --open-browser

# Start Garmin connector
wear start dev --vendor garmin --port 8001

# Start unified service (all vendors)
wear start dev --port 8000

# Use specific environment file
wear start dev --vendor whoop --env .env.production

# Disable auto-reload
wear start dev --vendor whoop --no-reload
```

**Options:**
- `--vendor, -v` - Vendor to run (whoop, garmin, all)
- `--port, -p` - Port to run on (default: 8000)
- `--reload/--no-reload` - Auto-reload on code changes (default: enabled)
- `--env` - Environment file to load (.env.production, .env.test)
- `--open-browser` - Automatically open OAuth authorization URL in browser
- `--webhook-record/--no-webhook-record` - Enable webhook recording (dev mode only, default: enabled)
- `--verbose` - Enable verbose logging

**What it does:**
- Sets up PYTHONPATH automatically
- Starts uvicorn server
- Enables auto-reload for development
- **Automatically starts ngrok** (required for dev mode)
- Shows ngrok URL for SDK configuration
- Shows API docs URL

---

### `wear webhook` - Webhook Testing

#### `wear webhook dev` - Development Server with Recording

Start webhook receiver that saves incoming webhooks for inspection.

```bash
# Start webhook dev server
wear webhook dev --port 8000

# Specific vendor
wear webhook dev --vendor whoop --port 8000

# Don't save webhooks
wear webhook dev --no-save
```

**Options:**
- `--port, -p` - Port to run on (default: 8000)
- `--vendor, -v` - Vendor to receive from (default: all)
- `--save/--no-save` - Save webhooks to file (default: enabled)

**What it does:**
- Starts server with webhook recording enabled
- Saves webhooks to `__dev__/webhooks_recent.jsonl`
- Useful for debugging webhook payloads

#### `wear webhook inspect` - View Recent Webhooks

Inspect webhooks recorded in dev mode.

```bash
# Show last 50 webhooks
wear webhook inspect

# Show last 100 webhooks
wear webhook inspect --limit 100

# Filter by vendor
wear webhook inspect --vendor whoop --limit 50

# Filter by event type
wear webhook inspect --vendor whoop --type recovery.updated
```

**Options:**
- `--limit, -n` - Number of webhooks to show (default: 50)
- `--vendor, -v` - Filter by vendor
- `--type, -t` - Filter by event type

**What it does:**
- Reads from `__dev__/webhooks_recent.jsonl`
- Displays webhooks in a formatted table
- Shows timestamp, vendor, event type, user ID, resource ID

---

### `wear pull` - Manual Data Sync

Trigger manual data pull (backfill) from vendor APIs.

```bash
# Pull WHOOP data from last 2 days
wear pull once --vendor whoop --since 2d

# Pull for specific user
wear pull once --vendor whoop --user-id abc123 --since 1w

# Pull with limit
wear pull once --vendor garmin --since 2024-01-01 --limit 500
```

**Options:**
- `--vendor, -v` - Vendor to pull from (required)
- `--user-id, -u` - Specific user ID (optional, defaults to all users)
- `--since, -s` - Time range (e.g., 2d, 1w, 2024-01-01)
- `--limit, -n` - Max records to fetch (default: 100)

**Time Range Formats:**
- `2d` - Last 2 days
- `1w` - Last 1 week
- `2024-01-01` - Specific date
- `2024-01-01T00:00:00Z` - Specific datetime

**What it does:**
- Calls `/v1/{vendor}-cloud/pull` endpoint
- Fetches data from vendor API
- Normalizes to SynheartSample format
- Stores in S3/Redshift
- Shows progress and statistics

---

### `wear tokens` - Token Management

Manage OAuth tokens.

#### `wear tokens list` - List Tokens

```bash
# List all tokens
wear tokens list

# Filter by vendor
wear tokens list --vendor whoop

# Filter by status
wear tokens list --status active

# Limit results
wear tokens list --limit 100
```

**Options:**
- `--vendor, -v` - Filter by vendor
- `--status, -s` - Filter by status (active, expired, revoked)
- `--limit, -n` - Max tokens to show (default: 50)

**What it displays:**
- Vendor
- User ID
- Status (active, expired, revoked, reauth_required)
- Expires at
- Last used

#### `wear tokens refresh` - Refresh Token

```bash
# Refresh token for a user
wear tokens refresh --vendor whoop --user-id abc123
```

**Options:**
- `--vendor, -v` - Vendor (required)
- `--user-id, -u` - User ID (required)

**What it does:**
- Gets current tokens from DynamoDB
- Calls vendor's token refresh endpoint
- Saves new tokens back to DynamoDB
- Updates expiry time

#### `wear tokens revoke` - Revoke Token

```bash
# Revoke token (with confirmation)
wear tokens revoke --vendor whoop --user-id abc123

# Revoke without confirmation
wear tokens revoke --vendor whoop --user-id abc123 --yes
```

**Options:**
- `--vendor, -v` - Vendor (required)
- `--user-id, -u` - User ID (required)
- `--yes, -y` - Skip confirmation

**What it does:**
- Calls vendor's revoke endpoint (if supported)
- Marks token as revoked in DynamoDB
- User will need to re-authorize

---

### `wear version` - Version Info

Show version information.

```bash
wear version
```

## 🎯 Common Workflows

### Local Development

```bash
# Terminal 1: Start server
wear start dev --vendor whoop --port 8000

# Terminal 2: Watch logs and test
curl http://localhost:8000/health
```

### Webhook Testing

```bash
# Terminal 1: Start webhook dev server
wear webhook dev --vendor whoop --port 8000

# Terminal 2: Send test webhooks
# (use ngrok or test scripts)

# Terminal 3: Inspect recorded webhooks
wear webhook inspect --limit 10
```

### Manual Data Sync

```bash
# Pull recent data for a user
wear pull once --vendor whoop --user-id abc123 --since 7d

# Check what was fetched
wear tokens list --vendor whoop
```

### Token Management

```bash
# List all active tokens
wear tokens list --status active

# Refresh expiring token
wear tokens refresh --vendor whoop --user-id abc123

# Revoke user's access
wear tokens revoke --vendor whoop --user-id abc123 --yes
```

## 🔧 Configuration

### Environment Variables

Set these in `.env` or export before running commands:

```bash
# API Configuration
API_URL=http://localhost:8000          # API endpoint for pull/tokens commands
DYNAMODB_TABLE=cloud_connector_tokens  # DynamoDB table name
KMS_KEY_ID=your-kms-key-id             # KMS key for encryption

# Vendor Credentials (for start command)
WHOOP_CLIENT_ID=your-client-id
WHOOP_CLIENT_SECRET=your-client-secret
WHOOP_WEBHOOK_SECRET=your-webhook-secret
```

### Using .env Files

```bash
# Start with specific env file
wear start dev --vendor whoop --env .env.production

# Or export before running
export $(cat .env.production | xargs)
wear start dev --vendor whoop
```

## 🐛 Troubleshooting

### Command not found: wear

```bash
# Make sure it's installed
pip3 install --break-system-packages -e /path/to/cli

# Or run directly
python3 /path/to/cli/wear.py --help
```

### ModuleNotFoundError

```bash
# Install CLI dependencies
cd /path/to/cli
pip3 install --break-system-packages -r requirements.txt
```

### Server won't start

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Try different port
wear start dev --port 8001
```

### Webhook inspect shows no webhooks

```bash
# Make sure you ran webhook dev mode first
wear webhook dev --port 8000

# Check if file exists
ls -la /path/to/__dev__/webhooks_recent.jsonl
```

## 📚 Examples

### Complete Development Workflow

```bash
# 1. Start WHOOP connector in dev mode
wear start dev --vendor whoop --env .env.production

# 2. In another terminal, test OAuth
curl "http://localhost:8000/v1/oauth/authorize?redirect_uri=http://localhost:8000/v1/oauth/callback&state=test_user"

# 3. After OAuth, pull recent data
wear pull once --vendor whoop --user-id test_user --since 7d

# 4. Check tokens
wear tokens list --vendor whoop
```

### Webhook Development

```bash
# 1. Start webhook dev server
wear webhook dev --vendor whoop

# 2. Use ngrok to expose locally
ngrok http 8000

# 3. Configure ngrok URL in WHOOP Developer Portal

# 4. Trigger WHOOP data (workout, sleep, etc.)

# 5. Inspect received webhooks
wear webhook inspect --vendor whoop --limit 20
```

---

### `wear deploy` - Deployment Commands (Coming Soon)

Deployment features are coming in a future release. For now, focus on local development!

```bash
# All deploy commands show "coming soon" message
wear deploy service whoop-cloud production
```

---

### ngrok Integration (Automatic in Dev Mode)

When running `wear start dev`, ngrok is **automatically started** to expose your local server.

**Prerequisites:**
- `pyngrok` is automatically installed with the CLI (via `requirements.txt`)
- ngrok is **required** for dev mode (CLI will error if pyngrok is not installed)
- First-time setup: You may need to set your ngrok authtoken (free account required):
  ```bash
  ngrok config add-authtoken YOUR_TOKEN
  ```
  Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken

**What happens:**
1. CLI checks if ngrok is installed
2. CLI checks if ngrok tunnel already exists for your port
3. If not running, CLI automatically starts ngrok in background
4. CLI displays the ngrok URL for SDK configuration

**SDK Configuration:**
After starting, you'll see:
```
✅ ngrok tunnel started: https://abc123.ngrok-free.app

📱 SDK Configuration:
   Use this URL in your Flutter app:
   baseUrl: 'https://abc123.ngrok-free.app'
```

Use this URL in your Flutter app's `WhoopProvider` or `GarminProvider`:
```dart
final provider = WhoopProvider(
  baseUrl: 'https://abc123.ngrok-free.app',  // From CLI output
);
```

**Manual ngrok:**
If you prefer to start ngrok manually:
```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Terminal 2: Start server (CLI will detect existing tunnel)
wear start dev --vendor whoop --port 8000
```

---

## 🎨 Output Features

The CLI uses Rich for beautiful terminal output:

- ✅ Color-coded messages
- 📊 Formatted tables for list commands
- ⏳ Progress spinners for long operations
- 🎯 Clear error messages with suggestions

## 🚀 Next Steps

After installing the CLI:

1. **Test the start command:**
   ```bash
   wear start dev --vendor whoop --port 8000
   ```

2. **Explore webhook inspection:**
   ```bash
   wear webhook dev
   wear webhook inspect
   ```

3. **Try token management:**
   ```bash
   wear tokens list
   ```

## 📝 Notes

- The CLI is designed for **local development** only
- **ngrok is required** for dev mode (auto-started by CLI)
- Webhook recording only works in dev mode
- Token commands use local file storage (`__dev__/tokens.json`) by default
- Pull command requires server to be running
- Production deployment coming soon

## 🆘 Support

For issues or questions:
1. Check this README
2. Run command with `--help` flag
3. Check server logs
4. Verify environment variables

## 🎉 You're Ready!

The `wear` CLI is now available. Start with:

```bash
wear --help
```
