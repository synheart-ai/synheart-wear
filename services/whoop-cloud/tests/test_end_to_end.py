"""End-to-end test for WHOOP connector with webhooks."""

import asyncio
import os
import sys
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

# Load production environment
load_dotenv('.env.production')

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_USER_ID = "test_user_realwhoop"


async def check_server_health(client: httpx.AsyncClient) -> bool:
    """Check if server is running and healthy."""
    print("🏥 Checking server health...")
    try:
        response = await client.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Mode: {data.get('mode', 'production')}")
            print()
            return True
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print(f"   Make sure server is running: python3 api_local.py")
        return False


async def check_oauth_tokens(client: httpx.AsyncClient) -> bool:
    """Check if OAuth tokens exist for test user."""
    print("🔑 Checking OAuth tokens...")
    try:
        response = await client.get(f"{BASE_URL}/v1/debug/tokens/{TEST_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            if data.get("has_tokens"):
                print(f"✅ Tokens found for user: {TEST_USER_ID}")
                print(f"   Access Token: {data.get('access_token', 'N/A')}")
                print()
                return True
            else:
                print(f"⚠️  No tokens found for user: {TEST_USER_ID}")
                print(f"   Run: python3 test_real_whoop.py")
                print()
                return False
        else:
            print(f"❌ Failed to check tokens: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking tokens: {e}")
        return False


async def test_user_profile(client: httpx.AsyncClient) -> bool:
    """Test fetching user profile."""
    print("👤 Testing user profile fetch...")
    try:
        response = await client.get(f"{BASE_URL}/v1/data/{TEST_USER_ID}/profile")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profile fetched successfully")
            print(f"   User ID: {data.get('user_id', 'N/A')}")
            print(f"   First Name: {data.get('first_name', 'N/A')}")
            print(f"   Last Name: {data.get('last_name', 'N/A')}")
            print(f"   Email: {data.get('email', 'N/A')}")
            print()
            return True
        elif response.status_code == 429:
            print(f"⚠️  Rate limited - try again later")
            print()
            return False
        else:
            print(f"❌ Profile fetch failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print()
            return False
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        print()
        return False


async def test_recovery_data(client: httpx.AsyncClient) -> bool:
    """Test fetching recovery data."""
    print("💪 Testing recovery data fetch...")
    try:
        # Get last 3 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        response = await client.get(
            f"{BASE_URL}/v1/data/{TEST_USER_ID}/recovery",
            params={
                "start": start_date.isoformat() + "Z",
                "end": end_date.isoformat() + "Z",
                "limit": 3
            }
        )

        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            print(f"✅ Recovery data fetched: {len(records)} records")

            if records:
                sample = records[0]
                print(f"   Latest record:")
                print(f"   - Cycle ID: {sample.get('cycle_id', 'N/A')}")
                print(f"   - Recovery Score: {sample.get('score', {}).get('recovery_score', 'N/A')}")
                print(f"   - HRV: {sample.get('score', {}).get('hrv_rmssd_milli', 'N/A')} ms")
                print(f"   - Resting HR: {sample.get('score', {}).get('resting_heart_rate', 'N/A')} bpm")
            else:
                print(f"   ⚠️  No recovery data found in date range")
            print()
            return True
        elif response.status_code == 429:
            print(f"⚠️  Rate limited")
            print()
            return False
        else:
            print(f"❌ Recovery fetch failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print()
            return False
    except Exception as e:
        print(f"❌ Error fetching recovery: {e}")
        print()
        return False


async def test_sleep_data(client: httpx.AsyncClient) -> bool:
    """Test fetching sleep data."""
    print("😴 Testing sleep data fetch...")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        response = await client.get(
            f"{BASE_URL}/v1/data/{TEST_USER_ID}/sleep",
            params={
                "start": start_date.isoformat() + "Z",
                "end": end_date.isoformat() + "Z",
                "limit": 3
            }
        )

        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            print(f"✅ Sleep data fetched: {len(records)} records")

            if records:
                sample = records[0]
                print(f"   Latest record:")
                print(f"   - Sleep ID: {sample.get('id', 'N/A')}")
                score = sample.get('score', {})
                print(f"   - Sleep Efficiency: {score.get('sleep_efficiency_percentage', 'N/A')}%")
                print(f"   - Sleep Performance: {score.get('sleep_performance_percentage', 'N/A')}%")
            else:
                print(f"   ⚠️  No sleep data found in date range")
            print()
            return True
        elif response.status_code == 429:
            print(f"⚠️  Rate limited")
            print()
            return False
        else:
            print(f"❌ Sleep fetch failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print()
            return False
    except Exception as e:
        print(f"❌ Error fetching sleep: {e}")
        print()
        return False


async def check_webhook_queue(client: httpx.AsyncClient) -> bool:
    """Check webhook event queue."""
    print("📬 Checking webhook queue...")
    try:
        response = await client.get(f"{BASE_URL}/v1/debug/queue")
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_messages', 0)
            print(f"✅ Queue status: {total} messages")

            if total > 0:
                messages = data.get('messages', [])
                print(f"   Recent webhooks:")
                for msg in messages[-3:]:  # Show last 3
                    event = msg.get('event', {})
                    print(f"   - Type: {event.get('event_type')}")
                    print(f"     User: {event.get('user_id')}")
                    print(f"     Resource: {event.get('resource_id')}")
                    print(f"     Trace: {event.get('trace_id')[:20]}...")
            else:
                print(f"   ℹ️  No webhooks received yet")
                print(f"   To receive webhooks:")
                print(f"   1. Start ngrok: ngrok http 8000")
                print(f"   2. Configure webhook URL in WHOOP Developer Portal")
                print(f"   3. Trigger WHOOP data update (workout, sleep, etc.)")
            print()
            return True
        else:
            print(f"⚠️  Queue check failed: {response.status_code}")
            print()
            return False
    except Exception as e:
        print(f"❌ Error checking queue: {e}")
        print()
        return False


async def print_ngrok_instructions():
    """Print instructions for ngrok setup."""
    print()
    print("=" * 70)
    print("📡 WEBHOOK TESTING WITH NGROK")
    print("=" * 70)
    print()
    print("To receive real WHOOP webhooks, you need to expose your local server:")
    print()
    print("1️⃣ Install ngrok:")
    print("   brew install ngrok")
    print()
    print("2️⃣ Start ngrok tunnel (in new terminal):")
    print("   ngrok http 8000")
    print()
    print("3️⃣ Copy the HTTPS URL from ngrok output:")
    print("   Example: https://abc123.ngrok-free.app")
    print()
    print("4️⃣ Configure in WHOOP Developer Portal:")
    print("   - Go to: https://developer.whoop.com/")
    print("   - Navigate to your app")
    print("   - Set webhook URL to: https://YOUR-NGROK-URL/v1/webhooks/whoop")
    print("   - Subscribe to all event types")
    print()
    print("5️⃣ Test by triggering WHOOP data:")
    print("   - Complete a workout in WHOOP app")
    print("   - Wait for processing")
    print("   - Watch this terminal for webhook delivery")
    print()
    print("For detailed instructions, see: NGROK_WEBHOOK_TEST.md")
    print()
    print("=" * 70)
    print()


async def main():
    """Run end-to-end tests."""
    print()
    print("=" * 70)
    print("🧪 WHOOP CONNECTOR - END-TO-END TEST")
    print("=" * 70)
    print()
    print(f"📍 Testing against: {BASE_URL}")
    print(f"👤 Test user: {TEST_USER_ID}")
    print()

    # Check if using ngrok
    if "ngrok" in BASE_URL:
        print("✅ Using ngrok URL - webhooks will work!")
        print()
    elif BASE_URL.startswith("http://localhost"):
        print("⚠️  Using localhost - webhooks won't work from WHOOP")
        print("   Run ngrok for webhook testing (see instructions below)")
        print()

    results = {
        "Server Health": False,
        "OAuth Tokens": False,
        "User Profile": False,
        "Recovery Data": False,
        "Sleep Data": False,
        "Webhook Queue": False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Run tests
        results["Server Health"] = await check_server_health(client)

        if not results["Server Health"]:
            print("❌ Server is not healthy. Cannot continue.")
            return

        results["OAuth Tokens"] = await check_oauth_tokens(client)

        if not results["OAuth Tokens"]:
            print("⚠️  No OAuth tokens found.")
            print("   Run: python3 test_real_whoop.py")
            print("   Then run this test again.")
            return

        # Data fetching tests
        results["User Profile"] = await test_user_profile(client)
        results["Recovery Data"] = await test_recovery_data(client)
        results["Sleep Data"] = await test_sleep_data(client)

        # Webhook tests
        results["Webhook Queue"] = await check_webhook_queue(client)

    # Print summary
    print()
    print("=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print()

    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")

    print()

    # Overall status
    all_critical_passed = all([
        results["Server Health"],
        results["OAuth Tokens"],
        results["User Profile"],
    ])

    if all_critical_passed:
        print("🎉 All critical tests passed!")
        print()

        if not results["Webhook Queue"] or results.get("Webhook Queue") == 0:
            await print_ngrok_instructions()
        else:
            print("✅ Webhooks are being received!")
            print()
    else:
        print("❌ Some critical tests failed. Please fix and retry.")
        print()

    print("=" * 70)
    print()


if __name__ == "__main__":
    # Allow setting BASE_URL via environment or command line
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
        print(f"Using BASE_URL from argument: {BASE_URL}")

    asyncio.run(main())
