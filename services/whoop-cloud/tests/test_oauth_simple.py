"""Simple OAuth test for WHOOP - Step by step guide."""

import httpx
import asyncio

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_realwhoop"
REDIRECT_URI = "http://localhost:8000/v1/oauth/callback"


async def main():
    print()
    print("=" * 70)
    print("🏋️  WHOOP OAuth Flow - Step by Step")
    print("=" * 70)
    print()

    async with httpx.AsyncClient() as client:
        # Step 1: Get authorization URL
        print("📋 Step 1: Getting OAuth authorization URL...")
        response = await client.get(
            f"{BASE_URL}/v1/oauth/authorize",
            params={
                "redirect_uri": REDIRECT_URI,
                "state": TEST_USER_ID
            }
        )

        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        auth_url = data["authorization_url"]

        print("✅ Authorization URL generated!")
        print()
        print("=" * 70)
        print("👉 NEXT STEPS - DO THIS MANUALLY:")
        print("=" * 70)
        print()
        print("1. Copy this URL and open it in your browser:")
        print()
        print(f"   {auth_url}")
        print()
        print("2. Log in to your WHOOP account")
        print()
        print("3. Click 'Authorize' to grant access")
        print()
        print("4. After authorization, you'll be redirected to:")
        print(f"   {REDIRECT_URI}?code=...&state={TEST_USER_ID}")
        print()
        print("5. The browser will show a JSON response with:")
        print('   {"status": "success", "vendor": "whoop", ...}')
        print()
        print("6. If you see that, OAuth is complete!")
        print()
        print("7. Then run: python3 test_data_fetch.py")
        print()
        print("=" * 70)
        print()


if __name__ == "__main__":
    asyncio.run(main())
