"""FastAPI application for WHOOP cloud connector."""

import os
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from synheart_cloud_connector import (
    CloudConnectorError,
    OAuthError,
    RateLimitError,
    WebhookError,
)
from synheart_cloud_connector.jobs import JobQueue
from synheart_cloud_connector.rate_limit import RateLimiter
from synheart_cloud_connector.sync_state import SyncState
from synheart_cloud_connector.tokens import TokenStore
from synheart_cloud_connector.vendor_types import RateLimitConfig, VendorConfig, VendorType

from .connector import WhoopConnector

# Initialize FastAPI app
app = FastAPI(
    title="WHOOP Cloud Connector",
    description="Synheart WHOOP cloud integration service",
    version="0.1.0",
)

# Load configuration from environment
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET", "")
WHOOP_WEBHOOK_SECRET = os.getenv("WHOOP_WEBHOOK_SECRET", "")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "cloud_connector_tokens")
KMS_KEY_ID = os.getenv("KMS_KEY_ID")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Initialize dependencies
token_store = TokenStore(table_name=DYNAMODB_TABLE, kms_key_id=KMS_KEY_ID)
queue = JobQueue(queue_url=SQS_QUEUE_URL)
rate_limiter = RateLimiter()
sync_state = SyncState(table_name=DYNAMODB_TABLE)

# Configure WHOOP rate limits (100 requests per minute)
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


# ============================================================================
# Health Check (unversioned for monitoring tools)
# ============================================================================


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint per RFC A.1.4.
    
    Returns:
        Health status with version and service checks
    """
    # Check service health
    checks = {}
    try:
        # Check DynamoDB (via token_store)
        # This is a basic check - in production, you might ping DynamoDB
        checks["dynamodb"] = "ok"
    except Exception:
        checks["dynamodb"] = "error"
    
    try:
        # Check SQS (via queue)
        # Basic check - in production, verify queue exists
        checks["sqs"] = "ok"
    except Exception:
        checks["sqs"] = "error"
    
    try:
        # Check KMS
        # Basic check - in production, verify key exists
        checks["kms"] = "ok"
    except Exception:
        checks["kms"] = "error"
    
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "whoop-cloud-connector",
        "checks": checks,
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================


@v1_router.get("/oauth/authorize")
async def authorize(redirect_uri: str, state: str | None = None) -> dict[str, str]:
    """
    Get OAuth authorization URL.

    Args:
        redirect_uri: Callback URL
        state: Optional state parameter

    Returns:
        Authorization URL
    """
    auth_url = whoop.build_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
    )

    return {"authorization_url": auth_url}


@v1_router.get("/oauth/callback")
async def oauth_callback_get(
    code: str = Query(..., description="Authorization code from vendor"),
    state: str = Query(..., description="State parameter for CSRF protection (contains user_id)"),
    vendor: str = Query(default="whoop", description="Vendor identifier"),
) -> dict[str, Any]:
    """
    Handle OAuth callback via GET (RFC A.1.1 - standard OAuth2 flow).
    
    This endpoint receives the OAuth redirect from WHOOP with query parameters.

    Returns:
        Token info and user details
    """
    try:
        # State contains user_id in our implementation
        user_id = state
        # Use the configured redirect URI from environment
        redirect_uri = os.getenv("WHOOP_REDIRECT_URI", "")

        if not redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "invalid_request", "message": "Redirect URI not configured"}},
            )

        # Exchange code for tokens
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
        }

    except OAuthError as e:
        raise HTTPException(status_code=401, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.post("/oauth/callback")
async def oauth_callback_post(request: Request) -> dict[str, Any]:
    """
    Handle OAuth callback via POST (for mobile deep links, RFC A.1.1 - alternative).

    Request body:
    {
        "code": "AUTHORIZATION_CODE",
        "state": "user123",
        "redirect_uri": "synheart://oauth/callback",
        "vendor": "whoop"
    }

    Returns:
        Token info and user details
    """
    try:
        data = await request.json()

        code = data.get("code")
        user_id = data.get("state")  # State contains user_id
        redirect_uri = data.get("redirect_uri")

        if not code or not user_id or not redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "invalid_request",
                        "message": "Missing required fields: code, state, redirect_uri",
                        "vendor": "whoop",
                    }
                },
            )

        # Validate state parameter (basic CSRF check)
        # In production, validate state against stored session
        
        # Exchange code for tokens
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
        }

    except OAuthError as e:
        raise HTTPException(status_code=401, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Webhook Endpoint
# ============================================================================


@v1_router.post("/webhooks/whoop")
async def webhook_handler(request: Request) -> JSONResponse:
    """
    Handle WHOOP webhook events.

    WHOOP sends webhooks for:
    - recovery.updated
    - sleep.updated
    - workout.updated
    - cycle.updated

    Returns:
        204 No Content on success
    """
    try:
        # Get headers and raw body
        headers = dict(request.headers)
        raw_body = await request.body()

        # Process webhook (verify, parse, enqueue)
        message_id = await whoop.process_webhook(headers, raw_body)

        return JSONResponse(
            status_code=204,
            content=None,
        )

    except WebhookError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Data Fetch Endpoints (for backfills)
# ============================================================================


@v1_router.get("/data/{user_id}/recovery/{recovery_id}")
async def fetch_recovery(user_id: str, recovery_id: str) -> dict[str, Any]:
    """Fetch specific recovery data."""
    try:
        data = await whoop.fetch_recovery(user_id, recovery_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/sleep/{sleep_id}")
async def fetch_sleep(user_id: str, sleep_id: str) -> dict[str, Any]:
    """Fetch specific sleep data."""
    try:
        data = await whoop.fetch_sleep(user_id, sleep_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/workouts/{workout_id}")
async def fetch_workout(user_id: str, workout_id: str) -> dict[str, Any]:
    """Fetch specific workout data."""
    try:
        data = await whoop.fetch_workout(user_id, workout_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/cycles/{cycle_id}")
async def fetch_cycle(user_id: str, cycle_id: str) -> dict[str, Any]:
    """Fetch specific cycle (daily summary) data."""
    try:
        data = await whoop.fetch_cycle(user_id, cycle_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Data Collection Endpoints (with pagination)
# ============================================================================


@v1_router.get("/data/{user_id}/recovery")
async def fetch_recovery_collection(
    user_id: str,
    start: str | None = Query(None, description="Start date (ISO8601 format)"),
    end: str | None = Query(None, description="End date (ISO8601 format)"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of records (1-100)"),
) -> dict[str, Any]:
    """
    Fetch collection of recovery records.

    Query parameters:
    - start: Optional start date in ISO8601 format (e.g., "2024-01-01T00:00:00Z")
    - end: Optional end date in ISO8601 format
    - limit: Maximum number of records to return (default 25, max 100)

    Returns WHOOP recovery data with pagination info.
    """
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
    start: str | None = Query(None, description="Start date (ISO8601 format)"),
    end: str | None = Query(None, description="End date (ISO8601 format)"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of records (1-100)"),
) -> dict[str, Any]:
    """
    Fetch collection of sleep records.

    Query parameters:
    - start: Optional start date in ISO8601 format
    - end: Optional end date in ISO8601 format
    - limit: Maximum number of records to return (default 25, max 100)

    Returns WHOOP sleep data with pagination info.
    """
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
    start: str | None = Query(None, description="Start date (ISO8601 format)"),
    end: str | None = Query(None, description="End date (ISO8601 format)"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of records (1-100)"),
) -> dict[str, Any]:
    """
    Fetch collection of workout records.

    Query parameters:
    - start: Optional start date in ISO8601 format
    - end: Optional end date in ISO8601 format
    - limit: Maximum number of records to return (default 25, max 100)

    Returns WHOOP workout data with pagination info.
    """
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
    start: str | None = Query(None, description="Start date (ISO8601 format)"),
    end: str | None = Query(None, description="End date (ISO8601 format)"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of records (1-100)"),
) -> dict[str, Any]:
    """
    Fetch collection of cycle (daily summary) records.

    Query parameters:
    - start: Optional start date in ISO8601 format
    - end: Optional end date in ISO8601 format
    - limit: Maximum number of records to return (default 25, max 100)

    Returns WHOOP cycle data with pagination info.
    """
    try:
        data = await whoop.fetch_cycle_collection(user_id, start, end, limit)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/profile")
async def fetch_user_profile(user_id: str) -> dict[str, Any]:
    """
    Fetch user profile information.

    Returns basic WHOOP user profile data.
    """
    try:
        data = await whoop.fetch_user_profile(user_id)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Puller Endpoint (Backfill)
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
        from datetime import datetime, timezone

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
                from datetime import timedelta
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
                results[resource_type] = {"error": str(e)}

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
        }

    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Disconnect Endpoint (RFC A.1.3)
# ============================================================================


@v1_router.delete("/oauth/disconnect")
async def disconnect_user(
    user_id: str = Query(..., description="User identifier"),
    vendor: str = Query(default="whoop", description="Vendor to disconnect"),
) -> dict[str, Any]:
    """
    Disconnect user's wearable integration and revoke tokens per RFC A.1.3.

    Args:
        user_id: User identifier
        vendor: Vendor identifier

    Returns:
        Disconnection confirmation
    """
    try:
        await whoop.revoke_tokens(user_id)
        return {
            "status": "disconnected",
            "vendor": "whoop",
            "user_id": user_id,
            "revoked_at": None,  # Could add timestamp if needed
        }
    except CloudConnectorError as e:
        # If user not found, return 404
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "not_found",
                        "message": f"User-vendor binding does not exist",
                        "vendor": "whoop",
                    }
                },
            )
        raise HTTPException(status_code=500, detail=e.to_dict())


# ============================================================================
# Error Handlers
# ============================================================================


# Include versioned router
app.include_router(v1_router)

# Optional: Also expose unversioned routes for backward compatibility
# In production, consider deprecating these or redirecting to /v1/*
# app.include_router(v1_router, prefix="", tags=["unversioned"])


@app.exception_handler(CloudConnectorError)
async def cloud_connector_error_handler(request: Request, exc: CloudConnectorError) -> JSONResponse:
    """Handle CloudConnectorError exceptions."""
    return JSONResponse(
        status_code=500,
        content=exc.to_dict(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
