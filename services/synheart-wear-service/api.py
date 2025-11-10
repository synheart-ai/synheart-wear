"""Unified FastAPI application for all cloud connector services."""

import os
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from synheart_cloud_connector import CloudConnectorError
from synheart_cloud_connector.jobs import JobQueue
from synheart_cloud_connector.rate_limit import RateLimiter
from synheart_cloud_connector.tokens import TokenStore
from synheart_cloud_connector.vendor_types import RateLimitConfig, VendorType

# Import vendor connectors using importlib (directory names have hyphens)
import sys
import importlib.util
from pathlib import Path

# Get parent directory
parent_dir = Path(__file__).parent.parent

# Import WHOOP connector
whoop_connector_path = parent_dir / "whoop-cloud" / "connector.py"
whoop_spec = importlib.util.spec_from_file_location(
    "whoop_connector", whoop_connector_path
)
whoop_module = importlib.util.module_from_spec(whoop_spec)
sys.modules["whoop_connector"] = whoop_module  # Register module
whoop_spec.loader.exec_module(whoop_module)
WhoopConnector = whoop_module.WhoopConnector

# Import Garmin connector
garmin_connector_path = parent_dir / "garmin-cloud" / "connector.py"
garmin_spec = importlib.util.spec_from_file_location(
    "garmin_connector", garmin_connector_path
)
garmin_module = importlib.util.module_from_spec(garmin_spec)
sys.modules["garmin_connector"] = garmin_module  # Register module
garmin_spec.loader.exec_module(garmin_module)
GarminConnector = garmin_module.GarminConnector

# Add parent directory to path for synheart_cloud_connector imports in connectors
sys.path.insert(0, str(parent_dir.parent))

# Initialize FastAPI app
app = FastAPI(
    title="Synheart Wear Cloud Connector Service",
    description="Unified cloud integration service for all wearable vendors",
    version="1.0.0",
)

# Check if we're in dev mode (use mocked services)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"
use_mocks = DEV_MODE or LOCAL_MODE

# Load shared configuration from environment
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "cloud_connector_tokens")
KMS_KEY_ID = os.getenv("KMS_KEY_ID")

# Vendor-specific secrets
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID", "")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET", "")
WHOOP_WEBHOOK_SECRET = os.getenv("WHOOP_WEBHOOK_SECRET", "")

GARMIN_CLIENT_ID = os.getenv("GARMIN_CLIENT_ID", "")
GARMIN_CLIENT_SECRET = os.getenv("GARMIN_CLIENT_SECRET", "")
GARMIN_WEBHOOK_SECRET = os.getenv("GARMIN_WEBHOOK_SECRET", "")

# Initialize shared dependencies
if use_mocks:
    # Use mocked services for local development
    # Mock token store for local testing
    class MockTokenStore:
        """Mock token store for local testing without AWS. Persists to disk."""
        def __init__(self, *args, **kwargs):
            import json
            from pathlib import Path
            self.tokens_file = Path(__file__).parent.parent.parent / "__dev__" / "tokens.json"
            self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
            self.tokens = {}
            if self.tokens_file.exists():
                try:
                    with open(self.tokens_file, 'r') as f:
                        data = json.load(f)
                        from synheart_cloud_connector.vendor_types import OAuthTokens
                        from datetime import datetime, timezone
                        for key, token_data in data.items():
                            if token_data.get('expires_at'):
                                if isinstance(token_data['expires_at'], str):
                                    dt = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    token_data['expires_at'] = dt
                            self.tokens[key] = OAuthTokens(**token_data)
                except Exception:
                    self.tokens = {}
        
        def save_tokens(self, vendor, user_id, tokens, vendor_meta=None):
            key = f"{vendor.value}:{user_id}"
            self.tokens[key] = tokens
            self._save_to_disk()
            from synheart_cloud_connector.vendor_types import TokenRecord, TokenStatus
            import datetime
            return TokenRecord(
                pk=key, sk=datetime.datetime.now().isoformat(),
                access_token="encrypted_token", refresh_token="encrypted_refresh",
                expires_at=int(datetime.datetime.now().timestamp()) + 3600,
                scopes=tokens.scopes, status=TokenStatus.ACTIVE,
            )
        
        def get_tokens(self, vendor, user_id):
            key = f"{vendor.value}:{user_id}"
            return self.tokens.get(key)
        
        def update_last_webhook(self, vendor, user_id): pass
        def update_last_pull(self, vendor, user_id): pass
        def revoke_tokens(self, vendor, user_id):
            key = f"{vendor.value}:{user_id}"
            if key in self.tokens:
                del self.tokens[key]
                self._save_to_disk()
        
        def _save_to_disk(self):
            import json
            from datetime import datetime
            from synheart_cloud_connector.vendor_types import OAuthTokens
            data = {}
            for key, tokens in self.tokens.items():
                token_dict = tokens.model_dump(mode='json')
                if token_dict.get('expires_at') and isinstance(token_dict['expires_at'], datetime):
                    token_dict['expires_at'] = token_dict['expires_at'].isoformat()
                data[key] = token_dict
            try:
                with open(self.tokens_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
    
    # Mock job queue for local testing
    class MockJobQueue:
        """Mock job queue for local testing without AWS SQS."""
        def __init__(self, *args, **kwargs):
            self.messages = []
        def enqueue_event(self, event, delay_seconds=0):
            message_id = f"msg_{len(self.messages)}"
            self.messages.append({'id': message_id, 'event': event, 'delay': delay_seconds})
            print(f"✓ Enqueued event: {event.event_type} for {event.user_id} (msg_id: {message_id})")
            return message_id
    
    token_store = MockTokenStore()
    whoop_queue = MockJobQueue()
    garmin_queue = MockJobQueue()
    print("✓ Using mocked AWS services (local dev mode)")
else:
    # Use real AWS services for production
    token_store = TokenStore(table_name=DYNAMODB_TABLE, kms_key_id=KMS_KEY_ID)
    whoop_queue = JobQueue(queue_url=os.getenv("WHOOP_SQS_QUEUE_URL"))
    garmin_queue = JobQueue(queue_url=os.getenv("GARMIN_SQS_QUEUE_URL"))

rate_limiter = RateLimiter()

# Configure rate limits for all vendors
rate_limiter.configure(
    RateLimitConfig(
        vendor=VendorType.WHOOP,
        max_requests=100,
        time_window=60,
        max_burst=120,
    )
)
rate_limiter.configure(
    RateLimitConfig(
        vendor=VendorType.GARMIN,
        max_requests=200,
        time_window=60,
        max_burst=250,
    )
)

from synheart_cloud_connector.vendor_types import VendorConfig

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

garmin_config = VendorConfig(
    vendor=VendorType.GARMIN,
    client_id=GARMIN_CLIENT_ID,
    client_secret=GARMIN_CLIENT_SECRET,
    webhook_secret=GARMIN_WEBHOOK_SECRET,
    base_url="https://api.garmin.com/wellness-api/rest",
    auth_url="https://connect.garmin.com/oauthConfirm",
    token_url="https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0",
    scopes=["wellness"],
)

whoop = WhoopConnector(
    config=whoop_config,
    token_store=token_store,
    queue=whoop_queue,
    rate_limiter=rate_limiter,
)

garmin = GarminConnector(
    config=garmin_config,
    token_store=token_store,
    queue=garmin_queue,
    rate_limiter=rate_limiter,
)

# Create vendor-specific routers with prefixes
v1_whoop_router = APIRouter(prefix="/v1/whoop-cloud", tags=["whoop"])
v1_garmin_router = APIRouter(prefix="/v1/garmin-cloud", tags=["garmin"])

# ============================================================================
# Health Check (unversioned)
# ============================================================================

@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for monitoring."""
    checks = {}
    try:
        checks["dynamodb"] = "ok"
    except Exception:
        checks["dynamodb"] = "error"
    
    try:
        checks["sqs_whoop"] = "ok" if whoop_queue else "error"
        checks["sqs_garmin"] = "ok" if garmin_queue else "error"
    except Exception:
        checks["sqs_whoop"] = "error"
        checks["sqs_garmin"] = "error"
    
    try:
        checks["kms"] = "ok" if KMS_KEY_ID else "error"
    except Exception:
        checks["kms"] = "error"
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "synheart-wear-service",
        "vendors": ["whoop", "garmin"],
        "checks": checks,
    }

# ============================================================================
# WHOOP Routes
# ============================================================================

@v1_whoop_router.get("/oauth/authorize")
async def whoop_authorize(redirect_uri: str, state: str | None = None) -> dict[str, str]:
    """WHOOP OAuth authorization URL endpoint."""
    from fastapi import Query
    
    auth_url = whoop.build_authorization_url(redirect_uri=redirect_uri, state=state)
    return {"authorization_url": auth_url}

@v1_whoop_router.get("/oauth/callback")
async def whoop_oauth_callback_get(
    code: str,
    state: str,
    vendor: str = "whoop",
) -> dict[str, Any]:
    """WHOOP OAuth callback endpoint (GET)."""
    from fastapi import HTTPException, Query
    
    # Extract user_id from state (format: user_id:timestamp:nonce)
    try:
        user_id = state.split(":")[0]
    except (IndexError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_state",
                "message": "Invalid state parameter format",
                "vendor": vendor,
            },
        )
    
    try:
        redirect_uri = os.getenv("WHOOP_REDIRECT_URI", "")
        tokens = await whoop.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )
        return {
            "status": "connected",
            "vendor": vendor,
            "user_id": user_id,
            "scopes": tokens.scopes,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "exchange_failed",
                "message": str(e),
                "vendor": vendor,
            },
        )

@v1_whoop_router.post("/oauth/callback")
async def whoop_oauth_callback_post(request: Request) -> dict[str, Any]:
    """WHOOP OAuth callback endpoint (POST for mobile deep links)."""
    from fastapi import HTTPException
    
    body = await request.json()
    code = body.get("code")
    state = body.get("state")
    redirect_uri = body.get("redirect_uri", os.getenv("WHOOP_REDIRECT_URI", ""))
    vendor = body.get("vendor", "whoop")
    
    try:
        user_id = state.split(":")[0]
    except (IndexError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_state",
                "message": "Invalid state parameter format",
                "vendor": vendor,
            },
        )
    
    try:
        tokens = await whoop.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )
        return {
            "status": "connected",
            "vendor": vendor,
            "user_id": user_id,
            "scopes": tokens.scopes,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "exchange_failed",
                "message": str(e),
                "vendor": vendor,
            },
        )

@v1_whoop_router.post("/webhooks/whoop")
async def whoop_webhook_handler(request: Request) -> JSONResponse:
    """WHOOP webhook handler."""
    from fastapi import HTTPException
    
    headers = dict(request.headers)
    raw_body = await request.body()
    
    try:
        event_id = await whoop.process_webhook(headers, raw_body)
        return JSONResponse(
            content={
                "status": "received",
                "vendor": "whoop",
                "event_id": event_id,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "webhook_error",
                "message": str(e),
                "vendor": "whoop",
            },
        )

@v1_whoop_router.delete("/oauth/disconnect")
async def whoop_disconnect(
    user_id: str,
    vendor: str = "whoop",
) -> dict[str, Any]:
    """WHOOP disconnect endpoint."""
    from fastapi import HTTPException, Query
    
    try:
        success = await whoop.revoke_tokens(user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "not_found",
                    "message": "User-vendor binding not found",
                    "vendor": vendor,
                    "user_id": user_id,
                },
            )
        return {
            "status": "disconnected",
            "vendor": vendor,
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "server_error",
                "message": str(e),
                "vendor": vendor,
            },
        )

# ============================================================================
# Garmin Routes
# ============================================================================

@v1_garmin_router.get("/oauth/authorize")
async def garmin_authorize(redirect_uri: str, state: str | None = None) -> dict[str, str]:
    """Garmin OAuth authorization URL endpoint."""
    auth_url = garmin.build_authorization_url(redirect_uri=redirect_uri, state=state)
    return {"authorization_url": auth_url}

@v1_garmin_router.get("/oauth/callback")
async def garmin_oauth_callback_get(
    code: str,
    state: str,
    vendor: str = "garmin",
) -> dict[str, Any]:
    """Garmin OAuth callback endpoint (GET)."""
    from fastapi import HTTPException, Query
    
    try:
        user_id = state.split(":")[0]
    except (IndexError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_state",
                "message": "Invalid state parameter format",
                "vendor": vendor,
            },
        )
    
    try:
        redirect_uri = os.getenv("GARMIN_REDIRECT_URI", "")
        tokens = await garmin.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )
        return {
            "status": "connected",
            "vendor": vendor,
            "user_id": user_id,
            "scopes": tokens.scopes,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "exchange_failed",
                "message": str(e),
                "vendor": vendor,
            },
        )

@v1_garmin_router.post("/oauth/callback")
async def garmin_oauth_callback_post(request: Request) -> dict[str, Any]:
    """Garmin OAuth callback endpoint (POST for mobile deep links)."""
    from fastapi import HTTPException
    
    body = await request.json()
    code = body.get("code")
    state = body.get("state")
    redirect_uri = body.get("redirect_uri", os.getenv("GARMIN_REDIRECT_URI", ""))
    vendor = body.get("vendor", "garmin")
    
    try:
        user_id = state.split(":")[0]
    except (IndexError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_state",
                "message": "Invalid state parameter format",
                "vendor": vendor,
            },
        )
    
    try:
        tokens = await garmin.exchange_code(
            user_id=user_id,
            code=code,
            redirect_uri=redirect_uri,
        )
        return {
            "status": "connected",
            "vendor": vendor,
            "user_id": user_id,
            "scopes": tokens.scopes,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "exchange_failed",
                "message": str(e),
                "vendor": vendor,
            },
        )

@v1_garmin_router.post("/webhooks/garmin")
async def garmin_webhook_handler(request: Request) -> JSONResponse:
    """Garmin webhook handler."""
    from fastapi import HTTPException
    
    headers = dict(request.headers)
    raw_body = await request.body()
    
    try:
        event_id = await garmin.process_webhook(headers, raw_body)
        return JSONResponse(
            content={
                "status": "received",
                "vendor": "garmin",
                "event_id": event_id,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "webhook_error",
                "message": str(e),
                "vendor": "garmin",
            },
        )

@v1_garmin_router.delete("/oauth/disconnect")
async def garmin_disconnect(
    user_id: str,
    vendor: str = "garmin",
) -> dict[str, Any]:
    """Garmin disconnect endpoint."""
    from fastapi import HTTPException, Query
    
    try:
        success = await garmin.revoke_tokens(user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "not_found",
                    "message": "User-vendor binding not found",
                    "vendor": vendor,
                    "user_id": user_id,
                },
            )
        return {
            "status": "disconnected",
            "vendor": vendor,
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "server_error",
                "message": str(e),
                "vendor": vendor,
            },
        )

# Include routers
app.include_router(v1_whoop_router)
app.include_router(v1_garmin_router)

# Error handler
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

