#!/bin/bash
# Complete pipeline runner
# Usage: ./scripts/run_pipeline.sh [address] [max-pages]

set -e

ADDRESS=${1:-"0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}
MAX_PAGES=${2:-5}

echo "🚀 Starting complete pipeline demo..."
echo "Address: $ADDRESS"
echo "Max pages: $MAX_PAGES"
echo ""

# Step 1: Ingest from Etherscan
echo "📊 Step 1: Ingesting from Etherscan..."
./scripts/ingest.sh "$ADDRESS" "$MAX_PAGES"
echo ""

# Step 2: Convert to JSONL
echo "🔄 Step 2: Converting to JSONL..."
./scripts/convert_to_jsonl.sh
echo ""

# Step 3: Pin to IPFS
echo "📌 Step 3: Pinning to IPFS..."
./scripts/pin.sh
echo ""

# Step 4: Mint NFT
echo "🎨 Step 4: Minting NFT..."
./scripts/mint.sh
echo ""

# Step 5: Verify
echo "🔍 Step 5: Verifying NFT..."
./scripts/verify.sh
echo ""

echo "🎉 Pipeline complete!"
echo ""
echo "📋 Summary:"
if [ -f "/tmp/ipfs_cid.env" ]; then
    source /tmp/ipfs_cid.env
    echo "  IPFS CID: $CID"
    echo "  Gateway URL: http://127.0.0.1:8080/ipfs/$CID"
fi

if [ -f "/tmp/mint_tx.env" ]; then
    source /tmp/mint_tx.env
    echo "  Transaction Hash: $TX_HASH"
    echo "  Token URI: $TOKEN_URI"
fi

echo ""
echo "📸 Don't forget to take screenshots of:"
echo "  1. IPFS gateway content"
echo "  2. TokenURI verification output"
echo "  3. Transaction details"
