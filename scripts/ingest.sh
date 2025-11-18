#!/bin/bash
# Etherscan ingestion script
# Usage: ./scripts/ingest.sh [address] [max-pages]

set -e

PY_BIN=${PYTHON_BIN:-python3}

# Default values
ADDRESS=${1:-"0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}
MAX_PAGES=${2:-5}
OUTPUT_DIR="/tmp/eth_tx"
# Chain ID (1=mainnet, 11155111=sepolia)
CHAIN_ID=${CHAIN_ID:-11155111}

echo "🚀 Starting Etherscan ingestion..."
echo "Address: $ADDRESS"
echo "Max pages: $MAX_PAGES"
echo "Chain ID: $CHAIN_ID"
echo "Output: $OUTPUT_DIR"
echo "Python: $PY_BIN"

# Check if ETHERSCAN_API_KEY is set
if [ -z "$ETHERSCAN_API_KEY" ]; then
    echo "❌ Error: ETHERSCAN_API_KEY environment variable not set"
    echo "Please set it with: export ETHERSCAN_API_KEY=your_key"
    exit 1
fi

# Run the ingestion script (pandas + requests)
"$PY_BIN" etherscan_ingest.py \
  --address "$ADDRESS" \
  --action txlist \
  --page-size 100 \
  --max-pages "$MAX_PAGES" \
  --rps 5 \
  --chain-id "$CHAIN_ID" \
  --output "$OUTPUT_DIR"

echo "✅ Ingestion complete! Data saved to $OUTPUT_DIR"

# Show file count
echo "📊 Files created:"
ls -la "$OUTPUT_DIR" | grep -v "^total"
