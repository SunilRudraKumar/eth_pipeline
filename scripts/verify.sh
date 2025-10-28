#!/bin/bash
# Verify NFT tokenURI on-chain
# Usage: ./scripts/verify.sh [token_id]

set -e

TOKEN_ID_INPUT=${1:-}

echo "🔍 Verifying NFT tokenURI..."

# Check required environment variables
if [ -z "$RPC_URL" ]; then
    echo "❌ Error: RPC_URL environment variable not set"
    echo "Please set it with: export RPC_URL=http://127.0.0.1:8545"
    exit 1
fi

if [ -z "$NFT_ADDR" ]; then
    echo "❌ Error: NFT_ADDR environment variable not set"
    echo "Please set it with: export NFT_ADDR=your_nft_contract_address"
    exit 1
fi

# Auto-detect latest token ID if none provided: totalSupply() - 1
if [ -z "$TOKEN_ID_INPUT" ]; then
  echo "ℹ️ No token ID provided; fetching totalSupply() to determine latest token..."
  SUPPLY_HEX=$(cast call "$NFT_ADDR" "totalSupply()" --rpc-url "$RPC_URL" 2>/dev/null || true)
  if [ -z "$SUPPLY_HEX" ] || [ "$SUPPLY_HEX" = "0x" ]; then
    echo "❌ Error: Failed to fetch totalSupply()"
    exit 1
  fi
  SUPPLY_DEC=$(cast --to-dec "$SUPPLY_HEX")
  if [ "$SUPPLY_DEC" -eq 0 ]; then
    echo "❌ Error: totalSupply() is 0; no tokens exist yet"
    exit 1
  fi
  TOKEN_ID=$((SUPPLY_DEC - 1))
else
  TOKEN_ID=$TOKEN_ID_INPUT
fi

echo "📋 Verification details:"
echo "  Contract: $NFT_ADDR"
echo "  Token ID: $TOKEN_ID"
echo "  RPC URL: $RPC_URL"

# Ensure contract code exists
CODE=$(cast code "$NFT_ADDR" --rpc-url "$RPC_URL" 2>/dev/null || echo "0x")
if [ -z "$CODE" ] || [ "$CODE" = "0x" ]; then
  echo "❌ Error: No contract code found at $NFT_ADDR. Verify network and address."
  exit 1
fi

# Get tokenURI from contract
echo "🔄 Querying tokenURI..."
TOKEN_URI=$(cast call "$NFT_ADDR" "tokenURI(uint256)" "$TOKEN_ID" --rpc-url "$RPC_URL")

if [ -z "$TOKEN_URI" ] || [ "$TOKEN_URI" = "0x" ]; then
    echo "❌ Error: No tokenURI found for token ID $TOKEN_ID"
    echo "Make sure the token exists and the contract address is correct"
    exit 1
fi

echo "✅ TokenURI retrieved successfully!"
echo "🔗 Token URI: $TOKEN_URI"

# If it's an IPFS URI, extract CID and show gateway URL
if [[ "$TOKEN_URI" == ipfs://* ]]; then
    CID=$(echo "$TOKEN_URI" | sed 's/ipfs:\/\///')
    echo "📌 IPFS CID: $CID"
    echo "🌐 Gateway URL: http://127.0.0.1:8081/ipfs/$CID"
    
    # Test if IPFS content is accessible
    echo "🔄 Testing IPFS accessibility..."
    if curl -s -f "http://127.0.0.1:8081/ipfs/$CID" > /dev/null; then
        echo "✅ IPFS content is accessible via gateway"
    else
        echo "⚠️  Warning: IPFS content may not be accessible via gateway"
    fi
fi

# Load transaction details if available
if [ -f "/tmp/mint_tx.env" ]; then
    source /tmp/mint_tx.env
    echo ""
    echo "📋 Transaction details:"
    echo "  TX Hash: $TX_HASH"
    echo "  Expected URI: $TOKEN_URI"
    
    if [ "$TOKEN_URI" = "$TOKEN_URI" ]; then
        echo "✅ TokenURI matches expected value!"
    else
        echo "⚠️  Warning: TokenURI doesn't match expected value"
    fi
fi
