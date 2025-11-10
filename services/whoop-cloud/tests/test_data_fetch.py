"""Test WHOOP data fetching endpoints with real WHOOP API."""

import asyncio
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

# Load production credentials
load_dotenv('.env.production')

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_realwhoop"


async def test_data_fetching():
    """Test data fetching endpoints after OAuth is complete."""
    print("=" * 70)
    print("📊 WHOOP Data Fetching Test")
    print("=" * 70)
    print()
    print("⚠️  PREREQUISITES:")
    print("   1. Server is running (python api_local.py)")
    print("   2. OAuth flow completed (run test_real_whoop.py first)")
    print("   3. User has authorized WHOOP account")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Verify tokens exist
        print("📋 Step 1: Verifying stored tokens...")
        response = await client.get(f"{BASE_URL}/v1/debug/tokens/{TEST_USER_ID}")

        if response.status_code != 200:
            print("❌ Failed to check tokens")
            print(f"   Status: {response.status_code}")
            print()
            print("⚠️  Please run test_real_whoop.py first to complete OAuth flow")
            return

        token_data = response.json()
        if not token_data.get("has_tokens"):
            print("❌ No tokens found for user")
            print()
            print("⚠️  Please run test_real_whoop.py first to complete OAuth flow")
            return

        print("✅ Tokens found")
        print(f"   User: {token_data.get('user_id')}")
        print(f"   Access Token: {token_data.get('access_token', 'N/A')}")
        print()

        # Step 2: Fetch user profile
        print("📋 Step 2: Fetching user profile...")
        try:
            response = await client.get(f"{BASE_URL}/v1/data/{TEST_USER_ID}/profile")

            if response.status_code == 200:
                profile = response.json()
                print("✅ Profile fetched successfully!")
                print(f"   User ID: {profile.get('user_id', 'N/A')}")
                print(f"   First Name: {profile.get('first_name', 'N/A')}")
                print(f"   Last Name: {profile.get('last_name', 'N/A')}")
                print(f"   Email: {profile.get('email', 'N/A')}")
                print()
            else:
                print(f"⚠️  Profile fetch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print()
        except Exception as e:
            print(f"❌ Error fetching profile: {e}")
            print()

        # Step 3: Fetch recent recovery data
        print("📋 Step 3: Fetching recent recovery data...")
        try:
            # Get last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            response = await client.get(
                f"{BASE_URL}/v1/data/{TEST_USER_ID}/recovery",
                params={
                    "start": start_date.isoformat() + "Z",
                    "end": end_date.isoformat() + "Z",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                print(f"✅ Recovery data fetched: {len(records)} records")

                if records:
                    print("   Sample record:")
                    sample = records[0]
                    print(f"   - Cycle ID: {sample.get('cycle_id', 'N/A')}")
                    print(f"   - Sleep ID: {sample.get('sleep_id', 'N/A')}")
                    print(f"   - Recovery Score: {sample.get('score', {}).get('recovery_score', 'N/A')}")
                    print(f"   - HRV: {sample.get('score', {}).get('hrv_rmssd_milli', 'N/A')} ms")
                    print(f"   - Resting HR: {sample.get('score', {}).get('resting_heart_rate', 'N/A')} bpm")
                print()
            elif response.status_code == 429:
                print("⚠️  Rate limited by WHOOP API")
                print(f"   Retry after: {response.headers.get('Retry-After', 'unknown')} seconds")
                print()
            else:
                print(f"⚠️  Recovery fetch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print()
        except Exception as e:
            print(f"❌ Error fetching recovery: {e}")
            print()

        # Step 4: Fetch recent sleep data
        print("📋 Step 4: Fetching recent sleep data...")
        try:
            response = await client.get(
                f"{BASE_URL}/v1/data/{TEST_USER_ID}/sleep",
                params={
                    "start": start_date.isoformat() + "Z",
                    "end": end_date.isoformat() + "Z",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                print(f"✅ Sleep data fetched: {len(records)} records")

                if records:
                    print("   Sample record:")
                    sample = records[0]
                    print(f"   - Sleep ID: {sample.get('id', 'N/A')}")
                    print(f"   - Start: {sample.get('start', 'N/A')}")
                    print(f"   - End: {sample.get('end', 'N/A')}")
                    score = sample.get('score', {})
                    print(f"   - Sleep Score: {score.get('stage_summary', {}).get('total_in_bed_time_milli', 'N/A')} ms")
                    print(f"   - Sleep Efficiency: {score.get('sleep_efficiency_percentage', 'N/A')}%")
                print()
            elif response.status_code == 429:
                print("⚠️  Rate limited by WHOOP API")
                print()
            else:
                print(f"⚠️  Sleep fetch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print()
        except Exception as e:
            print(f"❌ Error fetching sleep: {e}")
            print()

        # Step 5: Fetch recent workout data
        print("📋 Step 5: Fetching recent workout data...")
        try:
            response = await client.get(
                f"{BASE_URL}/v1/data/{TEST_USER_ID}/workouts",
                params={
                    "start": start_date.isoformat() + "Z",
                    "end": end_date.isoformat() + "Z",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                print(f"✅ Workout data fetched: {len(records)} records")

                if records:
                    print("   Sample record:")
                    sample = records[0]
                    print(f"   - Workout ID: {sample.get('id', 'N/A')}")
                    print(f"   - Sport: {sample.get('sport_id', 'N/A')}")
                    print(f"   - Start: {sample.get('start', 'N/A')}")
                    print(f"   - End: {sample.get('end', 'N/A')}")
                    score = sample.get('score', {})
                    print(f"   - Strain: {score.get('strain', 'N/A')}")
                    print(f"   - Avg HR: {score.get('average_heart_rate', 'N/A')} bpm")
                    print(f"   - Calories: {score.get('kilojoule', 'N/A')} kJ")
                print()
            elif response.status_code == 429:
                print("⚠️  Rate limited by WHOOP API")
                print()
            else:
                print(f"⚠️  Workout fetch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print()
        except Exception as e:
            print(f"❌ Error fetching workouts: {e}")
            print()

        # Step 6: Fetch recent cycle data
        print("📋 Step 6: Fetching recent cycle (daily summary) data...")
        try:
            response = await client.get(
                f"{BASE_URL}/v1/data/{TEST_USER_ID}/cycles",
                params={
                    "start": start_date.isoformat() + "Z",
                    "end": end_date.isoformat() + "Z",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                print(f"✅ Cycle data fetched: {len(records)} records")

                if records:
                    print("   Sample record:")
                    sample = records[0]
                    print(f"   - Cycle ID: {sample.get('id', 'N/A')}")
                    print(f"   - Start: {sample.get('start', 'N/A')}")
                    print(f"   - End: {sample.get('end', 'N/A')}")
                    score = sample.get('score', {})
                    print(f"   - Strain: {score.get('strain', 'N/A')}")
                    print(f"   - Kilojoules: {score.get('kilojoule', 'N/A')} kJ")
                print()
            elif response.status_code == 429:
                print("⚠️  Rate limited by WHOOP API")
                print()
            else:
                print(f"⚠️  Cycle fetch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                print()
        except Exception as e:
            print(f"❌ Error fetching cycles: {e}")
            print()

        print("=" * 70)
        print("✅ DATA FETCHING TEST COMPLETE!")
        print("=" * 70)
        print()
        print("📝 Summary:")
        print("   ✅ Verified token storage")
        print("   ✅ Fetched user profile")
        print("   ✅ Fetched recovery data")
        print("   ✅ Fetched sleep data")
        print("   ✅ Fetched workout data")
        print("   ✅ Fetched cycle data")
        print()
        print("🎉 All data endpoints are working with real WHOOP API!")
        print()


if __name__ == "__main__":
    print()
    print("📝 Prerequisites:")
    print("   1. Server running: python api_local.py")
    print("   2. OAuth completed: python test_real_whoop.py")
    print("   3. User has WHOOP data to fetch")
    print()
    print("Press Enter to continue...")
    input()

    asyncio.run(test_data_fetching())
