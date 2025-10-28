#!/bin/bash
# Pin JSONL file to IPFS and get CID
# Usage: ./scripts/pin.sh [jsonl_dir]

set -e

JSONL_DIR=${1:-"/tmp/eth_tx_jsonl"}
IPFS_ADD_OUTPUT="/tmp/ipfs_add.json"

echo "📌 Pinning to IPFS..."

# Check if IPFS is running
if ! curl -s -X POST http://127.0.0.1:5002/api/v0/version > /dev/null; then
    echo "❌ Error: IPFS Kubo container is not running"
    echo "Please start it with: docker run -d --name ipfs-kubo -p 4002:4001 -p 5002:5001 -p 8081:8080 ipfs/kubo:latest"
    exit 1
fi

# Find the JSONL file
PART=$(ls "$JSONL_DIR" | grep -E '^part-|\.jsonl$' | head -n1)
if [ -z "$PART" ]; then
    echo "❌ Error: No JSONL files found in $JSONL_DIR"
    exit 1
fi

echo "📄 Found file: $PART"

# Pin to IPFS
echo "🔄 Uploading to IPFS..."
curl -s -X POST -F "file=@$JSONL_DIR/$PART" \
  "http://127.0.0.1:5002/api/v0/add?pin=true" | tee "$IPFS_ADD_OUTPUT"

# Extract CID
CID=$(jq -r '.Hash' "$IPFS_ADD_OUTPUT")
if [ "$CID" = "null" ] || [ -z "$CID" ]; then
    echo "❌ Error: Failed to get CID from IPFS response"
    cat "$IPFS_ADD_OUTPUT"
    exit 1
fi

echo ""
echo "✅ Successfully pinned to IPFS!"
echo "🔗 CID: $CID"
echo "🌐 Gateway URL: http://127.0.0.1:8081/ipfs/$CID"
echo "📋 IPFS URI: ipfs://$CID"

# Export CID for other scripts
export CID
echo "export CID=$CID" > /tmp/ipfs_cid.env

# Open in browser (optional)
if command -v open > /dev/null; then
    echo "🌐 Opening in browser..."
    open "http://127.0.0.1:8081/ipfs/$CID"
fi
