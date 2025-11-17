#!/bin/bash
# Run end-to-end tests for Sepolia NFT Pipeline
# Usage: ./scripts/run_e2e_tests.sh [--quick]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧪 Sepolia NFT Pipeline - End-to-End Tests"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with required configuration"
    echo "See env.example for reference"
    exit 1
fi

# Load environment variables
set -a
source "$PROJECT_DIR/.env"
set +a

# Verify required variables
REQUIRED_VARS=("ETHERSCAN_API_KEY" "RPC_URL" "PRIVATE_KEY" "RECIPIENT" "CHAIN_ID")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please set these variables in your .env file"
    exit 1
fi

# Verify Sepolia configuration
if [[ ! "$RPC_URL" =~ "sepolia" ]]; then
    echo "⚠️  Warning: RPC_URL does not contain 'sepolia'"
    echo "   Current RPC_URL: $RPC_URL"
    echo "   These tests are designed for Sepolia testnet"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if [ "$CHAIN_ID" != "11155111" ]; then
    echo "⚠️  Warning: CHAIN_ID is not 11155111 (Sepolia)"
    echo "   Current CHAIN_ID: $CHAIN_ID"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Environment configuration verified"
echo ""
echo "Configuration:"
echo "  - Chain ID: $CHAIN_ID"
echo "  - RPC URL: ${RPC_URL:0:50}..."
echo "  - Recipient: $RECIPIENT"
echo ""

# Check Python dependencies
echo "Checking Python dependencies..."
if ! python3 -c "import requests, json, subprocess, pathlib" 2>/dev/null; then
    echo "❌ Error: Missing required Python packages"
    echo "Please install: pip install requests"
    exit 1
fi
echo "✅ Python dependencies OK"
echo ""

# Check Foundry tools
echo "Checking Foundry tools..."
if ! command -v forge &> /dev/null || ! command -v cast &> /dev/null; then
    echo "❌ Error: Foundry tools not found"
    echo "Please install Foundry: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi
echo "✅ Foundry tools OK"
echo ""

# Run the test suite
echo "Starting test suite..."
echo "======================================"
echo ""

cd "$PROJECT_DIR"

if [ "$1" == "--quick" ]; then
    echo "Running quick tests (error scenarios and stage independence only)..."
    python3 test_e2e_sepolia.py --quick
else
    echo "Running full test suite..."
    python3 test_e2e_sepolia.py
fi

EXIT_CODE=$?

echo ""
echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test suite completed successfully"
else
    echo "❌ Test suite failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
