#!/bin/bash
# Quick test runner for WHOOP connector

set -e

echo "🧪 WHOOP Connector Test Runner"
echo "=============================="
echo ""

# Check if we're in the right directory
if [ ! -f "api_local.py" ]; then
    echo "❌ Error: Please run this script from services/whoop-cloud directory"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install --user --quiet fastapi uvicorn httpx python-dotenv 2>/dev/null || true
pip3 install --user --quiet -e ../../libs/py-cloud-connector 2>/dev/null || true
pip3 install --user --quiet -e ../../libs/py-normalize 2>/dev/null || true
echo "✓ Dependencies installed"

# Start server in background
echo ""
echo "🚀 Starting WHOOP API server..."
python3 api_local.py > server.log 2>&1 &
SERVER_PID=$!
echo "✓ Server started (PID: $SERVER_PID)"

# Wait for server to be ready
echo ""
echo "⏳ Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ Server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Server failed to start. Check server.log for details."
        cat server.log
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Run tests
echo ""
echo "🧪 Running integration tests..."
echo "=============================="
python3 tests/test_whoop_local.py

# Capture exit code
TEST_EXIT_CODE=$?

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
echo "✓ Server stopped"

# Show result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    echo ""
    echo "📖 Server logs saved to: server.log"
    echo "🔗 To run server manually: python3 api_local.py"
    echo "🧪 To run tests manually: python3 tests/test_whoop_local.py"
else
    echo "❌ TESTS FAILED"
    echo ""
    echo "📖 Check server.log for server output"
    echo "🐛 Debug with: python3 api_local.py (in one terminal)"
    echo "               python3 tests/test_whoop_local.py (in another terminal)"
fi

exit $TEST_EXIT_CODE
