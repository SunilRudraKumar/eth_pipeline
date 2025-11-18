#!/bin/bash
# Quick test script to verify the pipeline components
# Usage: ./scripts/quick_test.sh

set -e

PY_BIN=${PYTHON_BIN:-python3}

echo "🧪 Quick Pipeline Test"
echo "====================="

# Test 1: Python dependencies
echo "1️⃣ Testing Python dependencies..."
"$PY_BIN" -c "import pandas, requests; print('✅ Python deps OK')"

# Test 2: IPFS connectivity
echo "2️⃣ Testing IPFS connectivity..."
if curl -s -X POST http://127.0.0.1:5002/api/v0/version > /dev/null; then
    echo "✅ IPFS OK"
else
    echo "❌ IPFS not accessible"
    exit 1
fi

# Test 3: Foundry tools
echo "3️⃣ Testing Foundry tools..."
if command -v forge > /dev/null && command -v cast > /dev/null && command -v anvil > /dev/null; then
    echo "✅ Foundry tools OK"
else
    echo "❌ Foundry tools missing"
    exit 1
fi

# Test 4: Script permissions
echo "4️⃣ Testing script permissions..."
if [ -x "scripts/ingest.sh" ] && [ -x "scripts/pin.sh" ] && [ -x "scripts/mint.sh" ]; then
    echo "✅ Scripts executable"
else
    echo "❌ Scripts not executable"
    exit 1
fi

# Test 5: Main script exists
echo "5️⃣ Testing main script..."
if [ -f "etherscan_ingest.py" ]; then
    echo "✅ Main script exists"
else
    echo "❌ Main script missing"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Pipeline is ready to run."
echo ""
echo "Next steps:"
echo "1. Set environment variables (see README.md)"
echo "2. Start anvil: anvil"
echo "3. Deploy NFT contract"
echo "4. Run: ./scripts/run_pipeline.sh"
