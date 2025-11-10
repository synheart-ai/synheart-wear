#!/bin/bash
# Quick status check for WHOOP connector

echo ""
echo "🔍 WHOOP Connector Status Check"
echo "================================"
echo ""

# Check if server is running
echo "1️⃣ Server Status:"
if curl -s http://localhost:8000/health 2>/dev/null >/dev/null; then
    SERVER_STATUS=$(curl -s http://localhost:8000/health 2>/dev/null)
    echo "✅ Server is running"
    echo "   $(echo $SERVER_STATUS | grep -o '"service":"[^"]*"' | cut -d'"' -f4)"
    echo "   $(echo $SERVER_STATUS | grep -o '"version":"[^"]*"' | cut -d'"' -f4)"
else
    echo "❌ Server not running"
    echo "   Start with: python3 api_local.py"
fi
echo ""

# Check OAuth tokens
echo "2️⃣ OAuth Tokens:"
TOKENS=$(curl -s http://localhost:8000/v1/debug/tokens/test_user_realwhoop 2>/dev/null)
if echo "$TOKENS" | grep -q '"has_tokens":true'; then
    echo "✅ Tokens stored for test_user_realwhoop"
    ACCESS_TOKEN=$(echo "$TOKENS" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "   Access Token: ${ACCESS_TOKEN:0:30}..."
else
    echo "❌ No tokens found"
    echo "   Run OAuth flow: python3 tests/test_real_whoop.py"
fi
echo ""

# Check webhook queue
echo "3️⃣ Webhook Queue:"
QUEUE=$(curl -s http://localhost:8000/v1/debug/queue 2>/dev/null)
if [ -n "$QUEUE" ]; then
    TOTAL=$(echo "$QUEUE" | grep -o '"total_messages":[0-9]*' | cut -d':' -f2)
    if [ -n "$TOTAL" ]; then
        echo "✅ Queue accessible: $TOTAL messages"
        if [ "$TOTAL" -gt 0 ]; then
            echo "   📨 Webhooks have been received!"
        fi
    fi
else
    echo "⚠️  Cannot check queue (server may be down)"
fi
echo ""

# Check ngrok
echo "4️⃣ ngrok Status:"
if curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | grep -q "public_url"; then
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    if [ -n "$NGROK_URL" ]; then
        echo "✅ ngrok running"
        echo "   Public URL: $NGROK_URL"
        echo "   Webhook URL: $NGROK_URL/v1/webhooks/whoop"
        echo "   Configure this in WHOOP Developer Portal"
    fi
else
    echo "⚠️  ngrok not running"
    echo "   Start with: ngrok http 8000"
    echo "   (Required for webhook testing)"
fi
echo ""

# Check ngrok installation
echo "5️⃣ Tools Installed:"
if command -v ngrok &> /dev/null; then
    echo "✅ ngrok installed"
else
    echo "❌ ngrok not installed"
    echo "   Install with: brew install ngrok"
fi

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "✅ $PYTHON_VERSION"
fi

echo ""

echo "================================"
echo ""
echo "📝 Next Steps:"
echo ""

# Determine what to do next
if ! curl -s http://localhost:8000/health 2>/dev/null >/dev/null; then
    echo "1. Start server: python3 api_local.py"
elif ! echo "$TOKENS" | grep -q '"has_tokens":true'; then
    echo "1. Run OAuth flow: python3 tests/test_real_whoop.py"
else
    echo "✅ OAuth complete! Ready to test:"
    echo ""
    echo "• Test data fetching:"
    echo "  python3 tests/test_data_fetch.py"
    echo ""
    echo "• Test webhooks (requires ngrok):"
    echo "  Terminal 1: ngrok http 8000"
    echo "  Terminal 2: python3 tests/test_webhooks.py"
    echo ""
    echo "• Run complete test:"
    echo "  python3 tests/test_end_to_end.py"
fi
echo ""
