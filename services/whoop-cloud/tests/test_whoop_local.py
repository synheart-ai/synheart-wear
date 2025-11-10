"""Local integration tests for WHOOP connector."""

import asyncio
import hashlib
import hmac
import json
import time

import httpx


BASE_URL = "http://localhost:8000"
WEBHOOK_SECRET = "test_webhook_secret_12345"


async def test_health_check():
    """Test health check endpoint."""
    print("\n🔍 Testing health check...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["status"] == "healthy"
        assert data["mode"] == "local_test"

        print(f"✅ Health check passed: {data}")
        return data


async def test_oauth_authorize():
    """Test OAuth authorization URL generation."""
    print("\n🔍 Testing OAuth authorization URL...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/v1/oauth/authorize",
            params={
                "redirect_uri": "http://localhost:8000/v1/oauth/callback",
                "state": "test_user_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "authorization_url" in data
        assert "whoop.com" in data["authorization_url"]
        assert "client_id" in data["authorization_url"]

        print(f"✅ Authorization URL generated:")
        print(f"   {data['authorization_url']}")
        return data


async def test_oauth_callback():
    """Test OAuth callback handling."""
    print("\n🔍 Testing OAuth callback...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/v1/oauth/callback",
            params={
                "code": "test_auth_code_12345",
                "state": "test_user_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["vendor"] == "whoop"
        assert data["user_id"] == "test_user_123"
        assert "scopes" in data

        print(f"✅ OAuth callback successful:")
        print(f"   User: {data['user_id']}")
        print(f"   Scopes: {data['scopes']}")
        return data


async def test_debug_tokens():
    """Test token storage verification."""
    print("\n🔍 Checking stored tokens...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/debug/tokens/test_user_123")

        assert response.status_code == 200
        data = response.json()

        assert data["has_tokens"] is True
        assert "access_token" in data

        print(f"✅ Tokens found:")
        print(f"   User: {data['user_id']}")
        print(f"   Access Token: {data['access_token']}")
        print(f"   Scopes: {data['scopes']}")
        return data


async def test_webhook_valid():
    """Test webhook with valid signature."""
    print("\n🔍 Testing webhook with valid signature...")

    # Create webhook payload
    timestamp = str(int(time.time()))
    payload = {
        "user_id": 456,
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "recovery.updated",
        "trace_id": "e369c784-5100-49e8-8098-75d35c47b31b"
    }
    body = json.dumps(payload).encode()

    # Create valid HMAC signature
    signed_payload = f"{timestamp}.{body.decode()}"
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        signed_payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-WHOOP-Signature": signature,
        "X-WHOOP-Signature-Timestamp": timestamp,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/webhooks/whoop",
            content=body,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "message_id" in data

        print(f"✅ Webhook processed successfully:")
        print(f"   Message ID: {data['message_id']}")
        print(f"   Event type: {payload['type']}")
        return data


async def test_webhook_invalid_signature():
    """Test webhook with invalid signature."""
    print("\n🔍 Testing webhook with invalid signature...")

    timestamp = str(int(time.time()))
    payload = {"user_id": 123, "type": "test.event"}
    body = json.dumps(payload).encode()

    headers = {
        "X-WHOOP-Signature": "invalid_signature_12345",
        "X-WHOOP-Signature-Timestamp": timestamp,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/webhooks/whoop",
            content=body,
            headers=headers
        )

        # Should return 400 for invalid signature
        assert response.status_code == 400
        data = response.json()

        assert "error" in data

        print(f"✅ Invalid signature correctly rejected:")
        print(f"   Error: {data['error']}")
        return data


async def test_debug_queue():
    """Test queue inspection."""
    print("\n🔍 Checking message queue...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/debug/queue")

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Queue status:")
        print(f"   Total messages: {data['total_messages']}")
        if data['messages']:
            print(f"   Recent messages:")
            for msg in data['messages'][-3:]:  # Show last 3
                print(f"     - {msg['event'].event_type} (id: {msg['id']})")
        return data


async def test_disconnect():
    """Test user disconnection."""
    print("\n🔍 Testing user disconnection...")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}/v1/oauth/disconnect",
            params={"user_id": "test_user_123"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "disconnected"
        assert data["user_id"] == "test_user_123"

        print(f"✅ User disconnected:")
        print(f"   User: {data['user_id']}")
        return data


async def test_disconnect_tokens_removed():
    """Verify tokens were removed after disconnect."""
    print("\n🔍 Verifying tokens removed...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/debug/tokens/test_user_123")

        assert response.status_code == 200
        data = response.json()

        assert data["has_tokens"] is False

        print(f"✅ Tokens successfully removed")
        return data


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("🧪 WHOOP Connector Integration Tests")
    print("=" * 60)

    try:
        # Test basic functionality
        await test_health_check()
        await test_oauth_authorize()
        await test_oauth_callback()
        await test_debug_tokens()

        # Test webhook handling
        await test_webhook_valid()
        await test_webhook_invalid_signature()
        await test_debug_queue()

        # Test disconnection
        await test_disconnect()
        await test_disconnect_tokens_removed()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except httpx.ConnectError:
        print("\n❌ Cannot connect to server!")
        print("   Make sure the API server is running:")
        print("   python api_local.py")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    print("\n📝 Note: Make sure the WHOOP API server is running first:")
    print("   cd services/whoop-cloud")
    print("   python api_local.py")
    print("\nStarting tests in 2 seconds...\n")

    time.sleep(2)

    asyncio.run(run_all_tests())
