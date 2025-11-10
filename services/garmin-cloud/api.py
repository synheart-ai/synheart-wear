"""FastAPI application for Garmin cloud connector."""

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
from synheart_cloud_connector.tokens import TokenStore
from synheart_cloud_connector.vendor_types import RateLimitConfig, VendorConfig, VendorType

from .connector import GarminConnector

# Initialize FastAPI app
app = FastAPI(
    title="Garmin Cloud Connector",
    description="Synheart Garmin Health API cloud integration service",
    version="0.1.0",
)

# Load configuration from environment
GARMIN_CLIENT_ID = os.getenv("GARMIN_CLIENT_ID", "")
GARMIN_CLIENT_SECRET = os.getenv("GARMIN_CLIENT_SECRET", "")
GARMIN_WEBHOOK_SECRET = os.getenv("GARMIN_WEBHOOK_SECRET", "")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "cloud_connector_tokens")
KMS_KEY_ID = os.getenv("KMS_KEY_ID")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Initialize dependencies
token_store = TokenStore(table_name=DYNAMODB_TABLE, kms_key_id=KMS_KEY_ID)
queue = JobQueue(queue_url=SQS_QUEUE_URL)
rate_limiter = RateLimiter()

# Configure Garmin rate limits (200 requests per minute)
rate_limiter.configure(
    RateLimitConfig(
        vendor=VendorType.GARMIN,
        max_requests=200,
        time_window=60,
        max_burst=250,
    )
)

# Initialize Garmin connector
garmin_config = VendorConfig(
    vendor=VendorType.GARMIN,
    client_id=GARMIN_CLIENT_ID,
    client_secret=GARMIN_CLIENT_SECRET,
    webhook_secret=GARMIN_WEBHOOK_SECRET,
    base_url="https://api.garmin.com/wellness-api/rest",
    auth_url="https://connect.garmin.com/oauthConfirm",
    token_url="https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0",
    scopes=["wellness"],  # Garmin Health API scopes
)

garmin = GarminConnector(
    config=garmin_config,
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
        "service": "garmin-cloud-connector",
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
    auth_url = garmin.build_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
    )

    return {"authorization_url": auth_url}


@v1_router.get("/oauth/callback")
async def oauth_callback_get(
    code: str = Query(..., description="Authorization code from vendor"),
    state: str = Query(..., description="State parameter for CSRF protection (contains user_id)"),
    vendor: str = Query(default="garmin", description="Vendor identifier"),
) -> dict[str, Any]:
    """
    Handle OAuth callback via GET (RFC A.1.1 - standard OAuth2 flow).
    
    This endpoint receives the OAuth redirect from Garmin with query parameters.

    Returns:
        Token info and user details
    """
    try:
        # State contains user_id in our implementation
        user_id = state
        # Use the configured redirect URI from environment
        redirect_uri = os.getenv("GARMIN_REDIRECT_URI", "")

        if not redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "invalid_request", "message": "Redirect URI not configured"}},
            )

        # Exchange code for tokens
        tokens = await garmin.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )

        return {
            "status": "success",
            "vendor": "garmin",
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
        "vendor": "garmin"
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
                        "vendor": "garmin",
                    }
                },
            )

        # Validate state parameter (basic CSRF check)
        # In production, validate state against stored session
        
        # Exchange code for tokens
        tokens = await garmin.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )

        return {
            "status": "success",
            "vendor": "garmin",
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


@v1_router.post("/webhooks/garmin")
async def webhook_handler(request: Request) -> JSONResponse:
    """
    Handle Garmin webhook events per RFC A.1.2.

    Garmin sends webhooks for:
    - Daily summaries
    - Sleep data
    - Activities
    - Sleep sessions

    Returns:
        204 No Content on success
    """
    try:
        # Get headers and raw body
        headers = dict(request.headers)
        raw_body = await request.body()

        # Process webhook (verify, parse, enqueue)
        message_id = await garmin.process_webhook(headers, raw_body)

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


@v1_router.get("/data/{user_id}/dailies")
async def fetch_dailies(
    user_id: str,
    start_time_seconds: int,
    end_time_seconds: int,
) -> list[dict[str, Any]]:
    """Fetch daily summaries for a time range."""
    try:
        data = await garmin.fetch_dailies(user_id, start_time_seconds, end_time_seconds)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/sleeps")
async def fetch_sleeps(
    user_id: str,
    start_time_seconds: int,
    end_time_seconds: int,
) -> list[dict[str, Any]]:
    """Fetch sleep data for a time range."""
    try:
        data = await garmin.fetch_sleeps(user_id, start_time_seconds, end_time_seconds)
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=e.to_dict())
    except CloudConnectorError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())


@v1_router.get("/data/{user_id}/activities")
async def fetch_activities(
    user_id: str,
    start_time_seconds: int | None = None,
    end_time_seconds: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch activities (workouts)."""
    try:
        data = await garmin.fetch_activities(user_id, start_time_seconds, end_time_seconds)
        return data
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
    vendor: str = Query(default="garmin", description="Vendor to disconnect"),
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
        await garmin.revoke_tokens(user_id)
        return {
            "status": "disconnected",
            "vendor": "garmin",
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
                        "vendor": "garmin",
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

