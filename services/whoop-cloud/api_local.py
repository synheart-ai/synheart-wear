"""Local development version of WHOOP connector API with mocked AWS services."""

import os
from typing import Any
from unittest.mock import MagicMock

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment - check service directory first, then repo root
# This allows CLI to override via --env flag
if not os.getenv('WHOOP_CLIENT_ID'):  # Only auto-load if not already set
    from pathlib import Path
    repo_root = Path(__file__).parent.parent.parent
    
    env_files_to_try = [
        Path('.env.local'),      # Service directory
        Path('.env.production'),  # Service directory
        Path('.env'),             # Service directory
        repo_root / '.env.local',  # Repo root (shared)
        repo_root / '.env',      # Repo root (shared)
    ]
    
    for env_file in env_files_to_try:
        if env_file.exists():
            load_dotenv(env_file)
            break

from synheart_cloud_connector import (
    CloudConnectorError,
    OAuthError,
    RateLimitError,
    WebhookError,
)
from synheart_cloud_connector.vendor_types import RateLimitConfig, VendorConfig, VendorType

# Import but don't initialize real AWS services
# Note: We avoid importing JobQueue here to prevent boto3 import
# We'll use MockJobQueue instead
from synheart_cloud_connector.rate_limit import RateLimiter
# Import SyncCursor type for type hints, but we'll use MockSyncState
try:
    from synheart_cloud_connector.sync_state import SyncCursor
except ImportError:
    # If boto3 not available, create a simple type for local use
    from pydantic import BaseModel
    from typing import Optional
    class SyncCursor(BaseModel):
        vendor: str
        user_id: str
        last_sync_ts: str
        records_synced: int = 0
        last_resource_id: Optional[str] = None
        created_at: str
        updated_at: str

# Mock token store for local testing
class MockTokenStore:
    """Mock token store for local testing without AWS. Persists to disk."""

    def __init__(self, *args, **kwargs):
        import json
        from pathlib import Path
        
        # Store tokens in __dev__ directory to persist across restarts
        self.tokens_file = Path(__file__).parent.parent.parent / "__dev__" / "tokens.json"
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing tokens from disk
        self.tokens = {}
        if self.tokens_file.exists():
            try:
                with open(self.tokens_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct OAuthTokens objects from dict
                    from synheart_cloud_connector.vendor_types import OAuthTokens
                    from datetime import datetime, timezone
                    for key, token_data in data.items():
                        # Parse ISO datetime string back to datetime if present
                        if token_data.get('expires_at'):
                            if isinstance(token_data['expires_at'], str):
                                dt = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
                                # Ensure timezone-aware
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                token_data['expires_at'] = dt
                        self.tokens[key] = OAuthTokens(**token_data)
                print(f"✓ Loaded {len(self.tokens)} token sets from {self.tokens_file}")
            except Exception as e:
                print(f"⚠️  Failed to load tokens from disk: {e}")
                self.tokens = {}

    def _save_to_disk(self):
        """Save tokens to disk."""
        import json
        from datetime import datetime
        from synheart_cloud_connector.vendor_types import OAuthTokens
        
        # Convert OAuthTokens objects to dict for JSON serialization
        data = {}
        for key, tokens in self.tokens.items():
            # Convert to dict
            token_dict = tokens.model_dump(mode='json')
            # Convert datetime to ISO string if present
            if token_dict.get('expires_at') and isinstance(token_dict['expires_at'], datetime):
                token_dict['expires_at'] = token_dict['expires_at'].isoformat()
            data[key] = token_dict
        
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save tokens to disk: {e}")

    def save_tokens(self, vendor, user_id, tokens, vendor_meta=None):
        key = f"{vendor.value}:{user_id}"
        self.tokens[key] = tokens
        print(f"✓ Saved tokens for {key}")
        self._save_to_disk()
        from synheart_cloud_connector.vendor_types import TokenRecord, TokenStatus
        import datetime
        return TokenRecord(
            pk=key,
            sk=datetime.datetime.now().isoformat(),
            access_token="encrypted_token",
            refresh_token="encrypted_refresh",
            expires_at=int(datetime.datetime.now().timestamp()) + 3600,
            scopes=tokens.scopes,
            status=TokenStatus.ACTIVE,
        )

    def get_tokens(self, vendor, user_id):
        key = f"{vendor.value}:{user_id}"
        return self.tokens.get(key)

    def update_last_webhook(self, vendor, user_id):
        print(f"✓ Updated webhook timestamp for {vendor.value}:{user_id}")

    def update_last_pull(self, vendor, user_id):
        print(f"✓ Updated pull timestamp for {vendor.value}:{user_id}")

    def revoke_tokens(self, vendor, user_id):
        key = f"{vendor.value}:{user_id}"
        if key in self.tokens:
            del self.tokens[key]
            self._save_to_disk()
        print(f"✓ Revoked tokens for {key}")

# Mock job queue for local testing
class MockJobQueue:
    """Mock job queue for local testing without AWS SQS."""

    def __init__(self, *args, **kwargs):
        self.messages = []

    def enqueue_event(self, event, delay_seconds=0):
        message_id = f"msg_{len(self.messages)}"
        self.messages.append({
            'id': message_id,
            'event': event,
            'delay': delay_seconds
        })
        print(f"✓ Enqueued event: {event.event_type} for {event.user_id} (msg_id: {message_id})")
        return message_id

# Mock sync state for local testing
class MockSyncState:
    """Mock sync state for local testing without DynamoDB."""

    def __init__(self, *args, **kwargs):
        self.cursors = {}

    def get_cursor(self, vendor, user_id):
        key = f"{vendor.value}:{user_id}"
        return self.cursors.get(key)

    def update_cursor(self, vendor, user_id, last_sync_ts, records_synced=0, last_resource_id=None):
        from datetime import datetime, timezone
        key = f"{vendor.value}:{user_id}"
        now = datetime.now(timezone.utc).isoformat()

        existing = self.cursors.get(key)
        total_records = (existing.records_synced if existing else 0) + records_synced

        cursor = SyncCursor(
            vendor=vendor.value,
            user_id=user_id,
            last_sync_ts=last_sync_ts,
            records_synced=total_records,
            last_resource_id=last_resource_id,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self.cursors[key] = cursor
        print(f"✓ Updated sync cursor for {key}: {total_records} records, last_sync={last_sync_ts}")
        return cursor

    def reset_cursor(self, vendor, user_id):
        key = f"{vendor.value}:{user_id}"
        if key in self.cursors:
            del self.cursors[key]
        print(f"✓ Reset sync cursor for {key}")

    def list_cursors(self, vendor=None, limit=100):
        cursors = []
        for key, cursor in self.cursors.items():
            if vendor and cursor.vendor != vendor.value:
                continue
            cursors.append(cursor)
            if len(cursors) >= limit:
                break
        return cursors

from connector import WhoopConnector

# Initialize FastAPI app
app = FastAPI(
    title="WHOOP Cloud Connector (Local Dev)",
    description="Local development version with mocked AWS services",
    version="0.1.0-local",
)

# Load configuration from test environment
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET", "")
WHOOP_WEBHOOK_SECRET = os.getenv("WHOOP_WEBHOOK_SECRET", "")

# Initialize mocked dependencies
token_store = MockTokenStore()
queue = MockJobQueue()
rate_limiter = RateLimiter()
sync_state = MockSyncState()

# Configure WHOOP rate limits
rate_limiter.configure(
    RateLimitConfig(
        vendor=VendorType.WHOOP,
        max_requests=100,
        time_window=60,
        max_burst=120,
    )
)

# Initialize WHOOP connector
whoop_config = VendorConfig(
    vendor=VendorType.WHOOP,
    client_id=WHOOP_CLIENT_ID,
    client_secret=WHOOP_CLIENT_SECRET,
    webhook_secret=WHOOP_WEBHOOK_SECRET,
    base_url="https://api.prod.whoop.com",
    auth_url="https://api.prod.whoop.com/oauth/oauth2/auth",
    token_url="https://api.prod.whoop.com/oauth/oauth2/token",
    scopes=["read:recovery", "read:sleep", "read:workout", "read:cycles", "read:profile"],
)

whoop = WhoopConnector(
    config=whoop_config,
    token_store=token_store,
    queue=queue,
    rate_limiter=rate_limiter,
)

# Create versioned API router
v1_router = APIRouter(prefix="/v1", tags=["v1"])


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0-local",
        "service": "whoop-cloud-connector",
        "mode": "local_dev",
        "checks": {
            "token_store": "mocked",
            "queue": "mocked",
            "rate_limiter": "ok",
        }
    }


@v1_router.get("/oauth/authorize")
async def authorize(redirect_uri: str, state: str | None = None) -> dict[str, Any]:
    """
    Get OAuth authorization URL.
    
    This endpoint generates a URL that points to WHOOP's authorization server.
    The user must visit this URL in their browser to authorize the application.
    """
    try:
        auth_url = whoop.build_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
        )
        
        return {
            "authorization_url": auth_url,
            "redirect_uri": redirect_uri,
            "state": state or "",
            "note": "Visit this URL in your browser to authorize. After authorization, you'll be redirected back.",
            "instructions": "\n".join([
                "1. Visit the authorization_url in your browser",
                "2. Log in to your WHOOP account",
                "3. Click 'Authorize' to grant access",
                f"4. You'll be redirected to: {redirect_uri}?code=...&state={state or ''}"
            ])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate authorization URL",
                "message": str(e),
                "vendor": "whoop"
            }
        )


@v1_router.get("/oauth/callback")
async def oauth_callback_get(
    code: str = Query(..., description="Authorization code from vendor"),
    state: str = Query(..., description="State parameter (contains user_id)"),
) -> dict[str, Any]:
    """Handle OAuth callback via GET - uses REAL WHOOP API."""
    try:
        user_id = state
        redirect_uri = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:8000/v1/oauth/callback")

        # Exchange code for REAL tokens from WHOOP
        tokens = await whoop.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )

        return {
            "status": "success",
            "vendor": "whoop",
            "user_id": user_id,
            "expires_in": tokens.expires_in,
            "scopes": tokens.scopes,
            "note": "Real WHOOP tokens obtained and saved"
        }

    except OAuthError as e:
        raise HTTPException(status_code=401, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/webhooks/whoop")
async def webhook_handler(request: Request) -> JSONResponse:
    """Handle WHOOP webhook events."""
    try:
        headers = dict(request.headers)
        raw_body = await request.body()

        # Process webhook
        message_id = await whoop.process_webhook(headers, raw_body)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message_id": message_id,
                "note": "Webhook processed and enqueued (local test mode)"
            }
        )

    except WebhookError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/debug/tokens/{user_id}")
async def debug_tokens(user_id: str) -> dict[str, Any]:
    """Debug endpoint to check stored tokens."""
    tokens = token_store.get_tokens(VendorType.WHOOP, user_id)
    if tokens:
        return {
            "user_id": user_id,
            "has_tokens": True,
            "access_token": tokens.access_token[:20] + "...",
            "expires_in": tokens.expires_in,
            "scopes": tokens.scopes,
        }
    else:
        return {
            "user_id": user_id,
            "has_tokens": False,
        }


@v1_router.get("/debug/queue")
async def debug_queue() -> dict[str, Any]:
    """Debug endpoint to check queued messages."""
    return {
        "total_messages": len(queue.messages),
        "messages": queue.messages,
    }


@v1_router.delete("/oauth/disconnect")
async def disconnect_user(
    user_id: str = Query(..., description="User identifier"),
) -> dict[str, Any]:
    """Disconnect user and revoke tokens."""
    try:
        await whoop.revoke_tokens(user_id)
        return {
            "status": "disconnected",
            "vendor": "whoop",
            "user_id": user_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Fetch Endpoints
# ============================================================================


@v1_router.get("/data/{user_id}/recovery")
async def fetch_recovery_collection(
    user_id: str,
    start: str | None = Query(None, description="Start date (ISO8601)"),
    end: str | None = Query(None, description="End date (ISO8601)"),
    limit: int = Query(25, ge=1, le=100, description="Max records (1-100)"),
) -> dict[str, Any]:
    """Fetch collection of recovery records from real WHOOP API."""
    try:
        data = await whoop.fetch_recovery_collection(user_id, start, end, limit)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/sleep")
async def fetch_sleep_collection(
    user_id: str,
    start: str | None = Query(None, description="Start date (ISO8601)"),
    end: str | None = Query(None, description="End date (ISO8601)"),
    limit: int = Query(25, ge=1, le=100, description="Max records (1-100)"),
) -> dict[str, Any]:
    """Fetch collection of sleep records from real WHOOP API."""
    try:
        data = await whoop.fetch_sleep_collection(user_id, start, end, limit)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/workouts")
async def fetch_workout_collection(
    user_id: str,
    start: str | None = Query(None, description="Start date (ISO8601)"),
    end: str | None = Query(None, description="End date (ISO8601)"),
    limit: int = Query(25, ge=1, le=100, description="Max records (1-100)"),
) -> dict[str, Any]:
    """Fetch collection of workout records from real WHOOP API."""
    try:
        data = await whoop.fetch_workout_collection(user_id, start, end, limit)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/cycles")
async def fetch_cycle_collection(
    user_id: str,
    start: str | None = Query(None, description="Start date (ISO8601)"),
    end: str | None = Query(None, description="End date (ISO8601)"),
    limit: int = Query(25, ge=1, le=100, description="Max records (1-100)"),
) -> dict[str, Any]:
    """Fetch collection of cycle records from real WHOOP API."""
    try:
        data = await whoop.fetch_cycle_collection(user_id, start, end, limit)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/profile")
async def fetch_user_profile(user_id: str) -> dict[str, Any]:
    """Fetch user profile from real WHOOP API."""
    try:
        data = await whoop.fetch_user_profile(user_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Puller Endpoint (Backfill with Cursor Tracking)
# ============================================================================


@v1_router.post("/pull/{user_id}")
async def pull_data(
    user_id: str,
    resource_types: list[str] | None = Query(None, description="Resource types to pull (recovery, sleep, workout, cycle). Defaults to all."),
    since: str | None = Query(None, description="Start date (ISO8601 format). If not provided, uses last sync cursor."),
    limit: int = Query(25, ge=1, le=100, description="Maximum records per resource type"),
) -> dict[str, Any]:
    """
    Pull (backfill) user data from WHOOP with cursor tracking.

    This endpoint performs incremental data pulls using sync_state cursors
    to track the last sync timestamp. It fetches data from WHOOP and updates
    the cursor after successful pulls.

    Query parameters:
    - resource_types: Optional list of resource types (recovery, sleep, workout, cycle)
      If not provided, pulls all types.
    - since: Optional start date (ISO8601 format, e.g., "2024-01-01T00:00:00Z")
      If not provided, uses the last sync cursor timestamp.
    - limit: Maximum number of records per resource type (default 25, max 100)

    Returns:
        Summary of pulled data with record counts per resource type
    """
    try:
        from datetime import datetime, timezone, timedelta

        # Default to all resource types
        if not resource_types:
            resource_types = ["recovery", "sleep", "workout", "cycle"]

        # Get last sync cursor if since not provided
        if not since:
            cursor = sync_state.get_cursor(VendorType.WHOOP, user_id)
            if cursor:
                since = cursor.last_sync_ts
                pull_type = "incremental"
            else:
                # First sync - default to last 7 days
                since_dt = datetime.now(timezone.utc) - timedelta(days=7)
                since = since_dt.isoformat()
                pull_type = "initial"
        else:
            pull_type = "manual"

        # Pull data from each resource type
        results = {}
        total_records = 0
        now = datetime.now(timezone.utc).isoformat()

        for resource_type in resource_types:
            try:
                if resource_type == "recovery":
                    data = await whoop.fetch_recovery_collection(user_id, start=since, limit=limit)
                elif resource_type == "sleep":
                    data = await whoop.fetch_sleep_collection(user_id, start=since, limit=limit)
                elif resource_type == "workout":
                    data = await whoop.fetch_workout_collection(user_id, start=since, limit=limit)
                elif resource_type == "cycle":
                    data = await whoop.fetch_cycle_collection(user_id, start=since, limit=limit)
                else:
                    results[resource_type] = {"error": "Unknown resource type"}
                    continue

                # Count records
                records = data.get("records", [])
                record_count = len(records)
                total_records += record_count

                results[resource_type] = {
                    "records": record_count,
                    "data": records,  # Include actual data for now (will be stored in S3 later)
                }

            except (RateLimitError, CloudConnectorError) as e:
                results[resource_type] = {"error": str(e), "error_type": type(e).__name__}
            except Exception as e:
                # Catch any other exceptions (e.g., OAuthError, network errors)
                import traceback
                results[resource_type] = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()  # Always include for debugging
                }

        # Update sync cursor with new timestamp
        sync_state.update_cursor(
            VendorType.WHOOP,
            user_id,
            last_sync_ts=now,
            records_synced=total_records,
        )

        return {
            "status": "success",
            "vendor": "whoop",
            "user_id": user_id,
            "pull_type": pull_type,
            "since": since,
            "pulled_at": now,
            "total_records": total_records,
            "results": results,
            "note": "Data pulled from real WHOOP API (local dev mode with mocked cursor tracking)",
        }

    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        # Catch any unexpected errors and return them
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc() if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )


# Include versioned router
app.include_router(v1_router)


@app.exception_handler(CloudConnectorError)
async def cloud_connector_error_handler(request: Request, exc: CloudConnectorError) -> JSONResponse:
    """Handle CloudConnectorError exceptions."""
    return JSONResponse(
        status_code=500,
        content=exc.to_dict(),
    )


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting WHOOP connector in LOCAL DEV mode")
    print("📝 Using mocked AWS services (DynamoDB, SQS, KMS)")
    print("🔗 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
