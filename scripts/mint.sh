#!/bin/bash
# Mint NFT with IPFS tokenURI
# Usage: ./scripts/mint.sh [recipient] [token_uri]

set -e

RECIPIENT=${1:-"$RECIPIENT"}
TOKEN_URI=${2:-"ipfs://$CID"}

echo "🎨 Minting NFT..."

# Check required environment variables
if [ -z "$RPC_URL" ]; then
    echo "❌ Error: RPC_URL environment variable not set"
    echo "Please set it with: export RPC_URL=http://127.0.0.1:8545"
    exit 1
fi

if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: PRIVATE_KEY environment variable not set"
    echo "Please set it with: export PRIVATE_KEY=your_private_key"
    exit 1
fi

if [ -z "$NFT_ADDR" ]; then
    echo "❌ Error: NFT_ADDR environment variable not set"
    echo "Please set it with: export NFT_ADDR=your_nft_contract_address"
    exit 1
fi

if [ -z "$RECIPIENT" ]; then
    echo "❌ Error: RECIPIENT environment variable not set"
    echo "Please set it with: export RECIPIENT=recipient_address"
    exit 1
fi

# Load CID if available
if [ -f "/tmp/ipfs_cid.env" ]; then
    source /tmp/ipfs_cid.env
    TOKEN_URI="ipfs://$CID"
fi

echo "📋 Minting details:"
echo "  Contract: $NFT_ADDR"
echo "  Recipient: $RECIPIENT"
echo "  Token URI: $TOKEN_URI"
echo "  RPC URL: $RPC_URL"

# Ensure contract code exists before proceeding
CODE=$(cast code "$NFT_ADDR" --rpc-url "$RPC_URL" 2>/dev/null || echo "0x")
if [ -z "$CODE" ] || [ "$CODE" = "0x" ]; then
  echo "❌ Error: No contract code found at $NFT_ADDR. Check deployment or RPC network."
  exit 1
fi

# Mint the NFT
echo "🔄 Sending mint transaction..."

TX_OUTPUT=""
TX_HASH=""

# Primary path: sign with PRIVATE_KEY
TX_OUTPUT=$(cast send "$NFT_ADDR" "mintWithTokenURI(address,string)" "$RECIPIENT" "$TOKEN_URI" \
  --rpc-url "$RPC_URL" --private-key "$PRIVATE_KEY" --gas-limit 500000 2>&1 || true)
TX_HASH=$(echo "$TX_OUTPUT" | grep -o '0x[a-fA-F0-9]\{64\}' | head -n1)

# Fallback: unlocked account via JSON-RPC
if [ -z "$TX_HASH" ]; then
  echo "ℹ️ Falling back to unlocked account via JSON-RPC"
  DATA=$(cast calldata "mintWithTokenURI(address,string)" "$RECIPIENT" "$TOKEN_URI")
  TX_HASH=$(cast rpc eth_sendTransaction '{"from":"'"$RECIPIENT"'","to":"'"$NFT_ADDR"'","data":"'"$DATA"'","gas":"0x7a120"}' --rpc-url "$RPC_URL" | tr -d '"')
fi

# Validate we have a tx hash
if [ -z "$TX_HASH" ] || [ "$TX_HASH" = "null" ]; then
    echo "❌ Error: Failed to send mint transaction"
    echo "Transaction output:"
    echo "$TX_OUTPUT"
    exit 1
fi

echo "✅ NFT minted successfully!"
echo "🔗 Transaction hash: $TX_HASH"
echo "📋 Token URI: $TOKEN_URI"

# Save transaction details
echo "export TX_HASH=$TX_HASH" > /tmp/mint_tx.env
echo "export TOKEN_URI=$TOKEN_URI" >> /tmp/mint_tx.env

echo ""
echo "🎯 Next steps:"
echo "1. Verify the tokenURI: ./scripts/verify.sh"
echo "2. Check transaction on explorer (if on testnet)"
