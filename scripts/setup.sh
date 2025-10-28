#!/bin/bash
# Setup script for the pipeline demo
# Usage: ./scripts/setup.sh

set -e

echo "🚀 Setting up Pipeline Demo..."

# Check if we're in the right directory
if [ ! -f "etherscan_ingest.py" ]; then
    echo "❌ Error: Please run this script from the pipeline_demo directory"
    exit 1
fi

# Make scripts executable
echo "📝 Making scripts executable..."
chmod +x scripts/*.sh

# Check Python dependencies
echo "🐍 Checking Python dependencies..."
if ! python3 -c "import pyspark" 2>/dev/null; then
    echo "📦 Installing PySpark..."
    python3 -m pip install --user pyspark requests
else
    echo "✅ PySpark already installed"
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "📦 Installing requests..."
    python3 -m pip install --user requests
else
    echo "✅ requests already installed"
fi

# Check Docker and IPFS
echo "🐳 Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "🔍 Checking IPFS container..."
if ! docker ps | grep -q ipfs-kubo; then
    echo "⚠️  IPFS Kubo container not found. Starting it..."
    docker run -d --name ipfs-kubo -p 4002:4001 -p 5002:5001 -p 8081:8080 ipfs/kubo:latest
    echo "⏳ Waiting for IPFS to start..."
    sleep 10
else
    echo "✅ IPFS Kubo container is running"
fi

# Test IPFS connectivity
echo "🔗 Testing IPFS connectivity..."
if curl -s -X POST http://127.0.0.1:5002/api/v0/version > /dev/null; then
    echo "✅ IPFS is accessible"
else
    echo "❌ Error: IPFS is not accessible"
    echo "Please check if the container is running: docker ps | grep ipfs"
    exit 1
fi

# Check Foundry tools
echo "🔨 Checking Foundry tools..."
if command -v forge > /dev/null && command -v cast > /dev/null && command -v anvil > /dev/null; then
    echo "✅ Foundry tools are installed"
    echo "  Forge: $(forge --version)"
    echo "  Cast: $(cast --version)"
    echo "  Anvil: $(anvil --version)"
else
    echo "❌ Error: Foundry tools not found"
    echo "Please install Foundry: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi

# Check environment variables
echo "🔧 Checking environment variables..."
MISSING_VARS=()

if [ -z "$ETHERSCAN_API_KEY" ]; then
    MISSING_VARS+=("ETHERSCAN_API_KEY")
fi

if [ -z "$RPC_URL" ]; then
    MISSING_VARS+=("RPC_URL")
fi

if [ -z "$PRIVATE_KEY" ]; then
    MISSING_VARS+=("PRIVATE_KEY")
fi

if [ -z "$NFT_ADDR" ]; then
    MISSING_VARS+=("NFT_ADDR")
fi

if [ -z "$RECIPIENT" ]; then
    MISSING_VARS+=("RECIPIENT")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "⚠️  Missing environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set them before running the pipeline:"
    echo "  export ETHERSCAN_API_KEY=your_key"
    echo "  export RPC_URL=http://127.0.0.1:8545"
    echo "  export PRIVATE_KEY=your_private_key"
    echo "  export NFT_ADDR=your_nft_contract_address"
    echo "  export RECIPIENT=recipient_address"
else
    echo "✅ All required environment variables are set"
fi

echo ""
echo "🎯 Setup complete! Next steps:"
echo "1. Set missing environment variables (if any)"
echo "2. Start anvil: anvil"
echo "3. Deploy your NFT contract (if not already deployed)"
echo "4. Run the pipeline: ./scripts/run_pipeline.sh"
