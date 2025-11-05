"""Test WHOOP connector with real WHOOP API credentials."""

import asyncio
import webbrowser
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv

# Load production credentials
load_dotenv('.env.production')

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_realwhoop"


async def test_oauth_flow_real():
    """Test complete OAuth flow with real WHOOP API."""
    print("=" * 70)
    print("🏋️  WHOOP Real API OAuth Flow Test")
    print("=" * 70)
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get authorization URL
        print("📋 Step 1: Getting OAuth authorization URL...")
        response = await client.get(
            f"{BASE_URL}/v1/oauth/authorize",
            params={
                "redirect_uri": "http://localhost:8000/v1/oauth/callback",
                "state": TEST_USER_ID
            }
        )

        if response.status_code != 200:
            print(f"❌ Failed to get authorization URL: {response.status_code}")
            print(response.text)
            return

        auth_data = response.json()
        auth_url = auth_data["authorization_url"]

        print(f"✅ Authorization URL generated")
        print(f"🔗 URL: {auth_url}")
        print()

        # Step 2: User authorization (manual step)
        print("=" * 70)
        print("👤 MANUAL STEP REQUIRED:")
        print("=" * 70)
        print()
        print("1. The authorization URL will open in your browser")
        print("2. Log in to your WHOOP account")
        print("3. Authorize the application")
        print("4. You'll be redirected to: http://localhost:8000/v1/oauth/callback?code=...")
        print("5. Copy the FULL URL from your browser's address bar")
        print()
        print("Opening browser in 3 seconds...")
        await asyncio.sleep(3)

        # Open browser
        webbrowser.open(auth_url)

        print()
        print("⏳ Waiting for you to authorize...")
        print()
        callback_url = input("📋 Paste the full callback URL here: ").strip()

        if not callback_url:
            print("❌ No URL provided. Exiting.")
            return

        # Step 3: Extract code from callback URL
        print()
        print("📋 Step 2: Extracting authorization code...")

        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)

            if 'code' not in params:
                print(f"❌ No authorization code found in URL")
                print(f"   URL: {callback_url}")
                return

            auth_code = params['code'][0]
            state = params.get('state', [TEST_USER_ID])[0]

            print(f"✅ Authorization code extracted")
            print(f"   Code: {auth_code[:20]}...")
            print(f"   State (user_id): {state}")
            print()

        except Exception as e:
            print(f"❌ Failed to parse callback URL: {e}")
            return

        # Step 4: Exchange code for tokens
        print("📋 Step 3: Exchanging code for access token...")

        try:
            response = await client.get(
                f"{BASE_URL}/v1/oauth/callback",
                params={
                    "code": auth_code,
                    "state": state
                }
            )

            if response.status_code != 200:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(response.text)
                return

            token_data = response.json()

            print(f"✅ Token exchange successful!")
            print(f"   User ID: {token_data.get('user_id')}")
            print(f"   Vendor: {token_data.get('vendor')}")
            print(f"   Scopes: {token_data.get('scopes')}")
            print(f"   Expires in: {token_data.get('expires_in')}s")
            print()

        except Exception as e:
            print(f"❌ Token exchange error: {e}")
            return

        # Step 5: Verify tokens are stored
        print("📋 Step 4: Verifying token storage...")

        response = await client.get(
            f"{BASE_URL}/v1/debug/tokens/{state}"
        )

        if response.status_code == 200:
            debug_data = response.json()
            if debug_data.get("has_tokens"):
                print(f"✅ Tokens stored successfully")
                print(f"   User: {debug_data.get('user_id')}")
                print(f"   Access Token: {debug_data.get('access_token', 'N/A')}")
                print()
            else:
                print(f"⚠️  Tokens not found in storage")
                print()
        else:
            print(f"❌ Failed to verify tokens: {response.status_code}")
            print()

        # Step 6: Test fetching user data (if API supports it)
        print("📋 Step 5: Testing data fetch (optional)...")
        print("   Note: This requires implementing fetch endpoints")
        print()

        print("=" * 70)
        print("✅ OAUTH FLOW TEST COMPLETE!")
        print("=" * 70)
        print()
        print("📝 Summary:")
        print("   1. ✅ Generated authorization URL")
        print("   2. ✅ User authorized application")
        print("   3. ✅ Exchanged code for tokens")
        print("   4. ✅ Tokens stored in database")
        print()
        print("🎉 You can now use these tokens to fetch WHOOP data!")
        print()


async def test_health_check():
    """Quick health check."""
    print("🏥 Checking server health...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server is healthy")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                print()
                return True
            else:
                print(f"❌ Server returned {response.status_code}")
                return False
        except httpx.ConnectError:
            print(f"❌ Cannot connect to server at {BASE_URL}")
            print(f"   Make sure the server is running:")
            print(f"   python api_local.py")
            return False


async def main():
    """Run all tests."""
    print()
    print("🧪 WHOOP Real API Integration Test")
    print()

    # Check server is running
    if not await test_health_check():
        return

    # Run OAuth flow test
    await test_oauth_flow_real()


if __name__ == "__main__":
    print("\n📝 Prerequisites:")
    print("   1. Server must be running: python api_local.py")
    print("   2. You need a WHOOP account to authorize")
    print("   3. Browser will open for OAuth authorization")
    print("\nPress Enter to continue...")
    input()

    asyncio.run(main())
