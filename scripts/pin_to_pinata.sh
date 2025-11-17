#!/bin/bash
# Upload image and metadata to Pinata IPFS (no Docker required)
# Usage: ./scripts/pin_to_pinata.sh

set -e

IMAGE_PATH="/tmp/eth_tx_chart.png"
JSONL_DIR="/tmp/eth_tx_jsonl"
PINATA_JWT="${PINATA_JWT}"

echo "📌 Uploading to Pinata IPFS..."
echo "================================"

# Check if Pinata JWT is configured
if [ -z "$PINATA_JWT" ]; then
    echo "❌ Error: PINATA_JWT environment variable not set"
    echo "Please set your Pinata JWT token in .env file"
    echo "Get one from: https://app.pinata.cloud/developers/api-keys"
    exit 1
fi

# Check if image exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Error: Image not found at $IMAGE_PATH"
    echo "Please run image generation first"
    exit 1
fi

echo "📊 Image found: $IMAGE_PATH"
IMAGE_SIZE=$(du -h "$IMAGE_PATH" | cut -f1)
echo "   Size: $IMAGE_SIZE"

# Count transactions from JSONL
TX_COUNT=0
if [ -d "$JSONL_DIR" ]; then
    JSONL_FILE=$(ls "$JSONL_DIR"/part-* 2>/dev/null | head -n1)
    if [ -n "$JSONL_FILE" ]; then
        TX_COUNT=$(wc -l < "$JSONL_FILE" | tr -d ' ')
        echo "📝 Transaction count: $TX_COUNT"
    fi
fi

echo ""
echo "🔄 Step 1: Uploading image to Pinata..."

# Upload image to Pinata
IMAGE_RESPONSE=$(curl -s -X POST "https://api.pinata.cloud/pinning/pinFileToIPFS" \
    -H "Authorization: Bearer $PINATA_JWT" \
    -F "file=@$IMAGE_PATH" \
    -F "pinataMetadata={\"name\":\"eth-tx-chart.png\"}" \
    -F "pinataOptions={\"cidVersion\":1}")

# Check for errors
if echo "$IMAGE_RESPONSE" | grep -q "error"; then
    echo "❌ Error uploading image to Pinata:"
    echo "$IMAGE_RESPONSE" | jq '.' 2>/dev/null || echo "$IMAGE_RESPONSE"
    exit 1
fi

# Extract image CID
IMAGE_CID=$(echo "$IMAGE_RESPONSE" | jq -r '.IpfsHash')
if [ "$IMAGE_CID" = "null" ] || [ -z "$IMAGE_CID" ]; then
    echo "❌ Error: Failed to get CID from Pinata response"
    echo "$IMAGE_RESPONSE"
    exit 1
fi

echo "✅ Image uploaded successfully!"
echo "   CID: $IMAGE_CID"
echo "   Gateway: https://gateway.pinata.cloud/ipfs/$IMAGE_CID"

# Save image CID
echo "export IMAGE_CID=$IMAGE_CID" > /tmp/ipfs_image_cid.env

echo ""
echo "🔄 Step 2: Creating NFT metadata..."

# Get data CID if available (from previous JSONL upload)
DATA_CID="QmNotAvailable"
if [ -f "/tmp/ipfs_data_cid.env" ]; then
    DATA_CID=$(cat /tmp/ipfs_data_cid.env)
fi

# Create NFT metadata JSON
METADATA_FILE="/tmp/nft_metadata.json"
cat > "$METADATA_FILE" << EOF
{
  "name": "Sepolia Transaction Data NFT",
  "description": "On-chain transaction data visualization from Sepolia testnet. Contains $TX_COUNT transactions with visual chart representation.",
  "image": "ipfs://$IMAGE_CID",
  "attributes": [
    {
      "trait_type": "Chain",
      "value": "Sepolia"
    },
    {
      "trait_type": "Transaction Count",
      "value": $TX_COUNT
    },
    {
      "trait_type": "Data CID",
      "value": "$DATA_CID"
    },
    {
      "trait_type": "Generated",
      "value": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  ]
}
EOF

echo "📄 Metadata created:"
cat "$METADATA_FILE" | jq '.'

echo ""
echo "🔄 Step 3: Uploading metadata to Pinata..."

# Upload metadata to Pinata
METADATA_RESPONSE=$(curl -s -X POST "https://api.pinata.cloud/pinning/pinFileToIPFS" \
    -H "Authorization: Bearer $PINATA_JWT" \
    -F "file=@$METADATA_FILE" \
    -F "pinataMetadata={\"name\":\"nft-metadata.json\"}" \
    -F "pinataOptions={\"cidVersion\":1}")

# Check for errors
if echo "$METADATA_RESPONSE" | grep -q "error"; then
    echo "❌ Error uploading metadata to Pinata:"
    echo "$METADATA_RESPONSE" | jq '.' 2>/dev/null || echo "$METADATA_RESPONSE"
    exit 1
fi

# Extract metadata CID
METADATA_CID=$(echo "$METADATA_RESPONSE" | jq -r '.IpfsHash')
if [ "$METADATA_CID" = "null" ] || [ -z "$METADATA_CID" ]; then
    echo "❌ Error: Failed to get metadata CID from Pinata response"
    echo "$METADATA_RESPONSE"
    exit 1
fi

echo "✅ Metadata uploaded successfully!"
echo "   CID: $METADATA_CID"
echo "   Gateway: https://gateway.pinata.cloud/ipfs/$METADATA_CID"

# Save metadata CID (this is what goes in tokenURI)
echo "export METADATA_CID=$METADATA_CID" > /tmp/ipfs_cid.env

echo ""
echo "================================"
echo "✅ IPFS Upload Complete!"
echo "================================"
echo ""
echo "📊 Summary:"
echo "   Image CID:    $IMAGE_CID"
echo "   Metadata CID: $METADATA_CID"
echo "   Token URI:    ipfs://$METADATA_CID"
echo ""
echo "🌐 View on IPFS:"
echo "   Image:    https://gateway.pinata.cloud/ipfs/$IMAGE_CID"
echo "   Metadata: https://gateway.pinata.cloud/ipfs/$METADATA_CID"
echo ""
echo "💡 The metadata CID will be used as the NFT's tokenURI"
echo ""

# Export for other scripts
export IMAGE_CID
export METADATA_CID
