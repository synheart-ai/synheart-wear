# Data Flow: WHOOP Cloud → Phone App

This document explains how data flows from WHOOP cloud to the phone app.

## 📊 Overview Flow

```
WHOOP Cloud API
    ↓ (webhook)
AWS Lambda (Backend Service)
    ↓ (enqueue)
SQS Queue
    ↓ (worker processes)
Data Storage (normalized)
    ↓ (API call)
Phone App (Flutter)
```

## 🔄 Detailed Flow

### 1. Initial Connection (OAuth Flow)

```
Phone App                    Backend Service              WHOOP Cloud
    │                               │                           │
    │── connect() ────────────────>│                           │
    │                               │── get auth URL ─────────>│
    │                               │<── auth URL ─────────────│
    │<── auth URL ──────────────────│                           │
    │                               │                           │
    │── open browser ───────────────┼──────────────────────────>│
    │                               │                           │
    │<── OAuth callback (code) ─────┼──────────────────────────│
    │                               │                           │
    │── exchange code ─────────────>│                           │
    │                               │── exchange code ─────────>│
    │                               │<── access token ──────────│
    │                               │                           │
    │                               │── store tokens (DynamoDB) │
    │<── connection success ────────│                           │
```

**Code Location:**
- Phone: `packages/synheart_wear/lib/src/sources/whoop_cloud.dart` - `connect()` method
- Backend: `services/whoop-cloud/api.py` - `/v1/oauth/authorize` and `/v1/oauth/callback`

### 2. Real-Time Updates (Webhook Flow)

When WHOOP data changes (new workout, sleep, recovery, etc.):

```
WHOOP Cloud API              Backend Lambda              SQS Queue              Worker
    │                               │                          │                    │
    │── POST /webhooks/whoop ──────>│                          │                    │
    │    (recovery.updated)         │                          │                    │
    │    (HMAC signed)              │                          │                    │
    │                               │                          │                    │
    │                               │── verify signature ──────│                    │
    │                               │── parse event ───────────│                    │
    │                               │                          │                    │
    │                               │── enqueue event ────────>│                    │
    │                               │                          │                    │
    │<── 204 No Content ────────────│                          │                    │
    │                               │                          │                    │
    │                               │                          │── consume ────────>│
    │                               │                          │                    │
    │                               │                          │                    │── fetch full data
    │                               │                          │                    │── normalize
    │                               │                          │                    │── store
```

**Code Location:**
- Backend: `services/whoop-cloud/api.py` - `/v1/webhooks/whoop`
- Webhook Processing: `services/whoop-cloud/connector.py` - `process_webhook()`
- Queue: `libs/py-cloud-connector/synheart_cloud_connector/jobs.py` - `JobQueue.enqueue_event()`

### 3. Phone App Data Fetching

The phone app **pulls** data from the backend API (not push notifications):

```
Phone App                    Backend API                  Data Storage
    │                               │                           │
    │── fetchRange(start, end) ────>│                           │
    │                               │                           │
    │                               │── query data ────────────>│
    │                               │<── normalized data ───────│
    │                               │                           │
    │<── List<WearMetrics> ─────────│                           │
    │                               │                           │
    │── display in UI ──────────────│                           │
```

**Code Location:**
- Phone: `packages/synheart_wear/lib/src/sources/whoop_cloud.dart` - `fetchRange()` method
- Backend: `services/whoop-cloud/api.py` - `/v1/data/{user_id}/recovery`, `/v1/data/{user_id}/sleep`, etc.

## 🔍 Key Components

### Backend Service (`services/whoop-cloud/`)

**Webhook Endpoint:**
- URL: `POST /v1/webhooks/whoop`
- Verifies HMAC-SHA256 signature
- Parses webhook event (recovery.updated, sleep.updated, workout.updated, cycle.updated)
- Enqueues to SQS for async processing

**Data Endpoints:**
- `GET /v1/data/{user_id}/recovery` - Fetch recovery data
- `GET /v1/data/{user_id}/sleep` - Fetch sleep data
- `GET /v1/data/{user_id}/workouts` - Fetch workout data
- `GET /v1/data/{user_id}/cycles` - Fetch cycle data
- `POST /v1/pull/{user_id}` - Backfill/pull data manually

### Phone App (`packages/synheart_wear/`)

**WhoopProvider Class:**
- `connect()` - Initiates OAuth flow
- `connectWithCode()` - Handles OAuth callback
- `fetchRange()` - Fetches data for date range
- `fetchRecovery()` - Fetches specific recovery record

**Data Fetching:**
```dart
// Example usage in Flutter app
final provider = WhoopProvider(baseUrl: 'https://api.wear.synheart.io');
await provider.connect(context);  // OAuth flow
final data = await provider.fetchRange(startDate, endDate);
```

## 📡 Communication Patterns

### 1. Webhook (Real-Time Updates)

**WHOOP → Backend:**
- WHOOP sends webhook when data changes
- Backend verifies signature and enqueues
- Returns 204 No Content immediately
- Processing happens asynchronously via SQS

**Benefits:**
- Real-time notification of data changes
- No polling needed
- Efficient (only when data changes)

### 2. Polling (Phone App)

**Phone → Backend:**
- Phone app calls API endpoints when needed
- Typically on app open, pull-to-refresh, or periodic refresh
- Backend fetches from WHOOP API if needed (caches tokens)

**Benefits:**
- Simple implementation
- Works offline with cached data
- Full control by app

## 🔐 Security & Authentication

### OAuth Tokens
- Stored securely in DynamoDB (encrypted with KMS)
- Phone app never sees access tokens
- Backend handles all token refresh automatically

### Webhook Verification
- HMAC-SHA256 signature verification
- Timestamp validation (replay protection)
- Webhook secret stored in AWS Secrets Manager

## 📦 Data Storage

### Current Architecture
1. **Tokens**: DynamoDB (encrypted with KMS)
2. **Webhook Events**: SQS Queue (processed asynchronously)
3. **Normalized Data**: (Future - S3 or data warehouse)
4. **Phone Cache**: Local SQLite cache for offline access

### Future Enhancements
- Push notifications to phone when new data arrives
- WebSocket connection for real-time updates
- Cloud sync of local cache

## 🚀 Example Flow

### Complete User Journey

1. **User Opens App:**
   ```
   Phone App → Checks local cache → Shows cached data
   ```

2. **User Connects WHOOP:**
   ```
   Phone App → OAuth flow → Backend stores tokens → Connection success
   ```

3. **User Completes Workout:**
   ```
   WHOOP Device → Syncs to WHOOP Cloud → WHOOP sends webhook
   Webhook → Backend → SQS Queue → Worker processes → Data stored
   ```

4. **User Opens App Again:**
   ```
   Phone App → Fetches from backend API → Gets latest data → Displays
   ```

5. **Manual Refresh:**
   ```
   User pulls to refresh → Phone App → Backend API → WHOOP API → Latest data
   ```

## 🔄 Data Synchronization

### Webhook Events (Real-Time)
- `recovery.updated` - New recovery data available
- `sleep.updated` - New sleep data available
- `workout.updated` - New workout data available
- `cycle.updated` - New cycle (daily summary) available

### Manual Pull (Backfill)
- Used for initial sync
- Used for missed webhooks
- Used for historical data
- Triggered via `wear pull` CLI or `/v1/pull/{user_id}` endpoint

## 📝 Notes

- **No Direct Push**: Phone app doesn't receive push notifications yet. It polls the backend API.
- **Offline Support**: Phone app caches data locally for offline access.
- **Token Management**: All OAuth token management is handled by backend. Phone only stores connection status.
- **Async Processing**: Webhooks are processed asynchronously via SQS to avoid blocking webhook responses.
- **Rate Limiting**: Backend respects WHOOP API rate limits (100 requests/minute).

## 🎯 Future Improvements

1. **Push Notifications**: Send push notifications to phone when new data arrives
2. **WebSocket**: Real-time bidirectional communication
3. **Background Sync**: Automatic periodic sync in background
4. **Conflict Resolution**: Handle offline edits and sync conflicts

