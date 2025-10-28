#!/bin/bash
# Deploy Simple721 NFT contract
# Usage: ./scripts/deploy_nft.sh

set -e

echo "🚀 Deploying Simple721 NFT contract..."

# Check if RPC_URL is set
if [ -z "$RPC_URL" ]; then
    echo "❌ Error: RPC_URL environment variable not set"
    echo "Please set it with: export RPC_URL=http://127.0.0.1:8545"
    exit 1
fi

# Check if PRIVATE_KEY is set
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: PRIVATE_KEY environment variable not set"
    echo "Please set it with: export PRIVATE_KEY=your_private_key"
    exit 1
fi

# Ensure required tools
command -v cast >/dev/null 2>&1 || { echo "❌ Error: 'cast' not found. Install Foundry (foundryup)."; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ Error: 'jq' not found. Install with: brew install jq"; exit 1; }

# Locate compiled artifact
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
ARTIFACT="$ROOT_DIR/out/Simple721.sol/Simple721.json"
if [ ! -f "$ARTIFACT" ]; then
  echo "❌ Artifact not found at $ARTIFACT"
  echo "Run: forge build (or ensure 'out/Simple721.sol/Simple721.json' exists)"
  exit 1
fi

# Extract bytecode and encode constructor args
BYTECODE=$(jq -r '.bytecode.object' "$ARTIFACT")
if [ -z "$BYTECODE" ] || [ "$BYTECODE" = "0x" ]; then
  echo "❌ Could not read bytecode from artifact"
  exit 1
fi
ARGS_ENC=$(cast abi-encode "constructor(string,string)" "PipelineDemo" "PDEMO")

FULL_DATA="0x${BYTECODE#0x}${ARGS_ENC#0x}"

echo "📝 Sending deployment transaction to $RPC_URL ..."
# Place flags before positional args for compatibility
DEPLOY_OUTPUT=$(cast send --rpc-url "$RPC_URL" --private-key "$PRIVATE_KEY" --gas-limit 5000000 \
  --create "$FULL_DATA" 2>&1 || true)

# Extract tx hash then query receipt for contract address
TX_HASH=$(echo "$DEPLOY_OUTPUT" | grep -o '0x[a-fA-F0-9]\{64\}' | head -n1)
if [ -z "$TX_HASH" ]; then
    echo "❌ Error: Failed to obtain deployment transaction hash"
    echo "Deployment output:"
    echo "$DEPLOY_OUTPUT"
    exit 1
fi

# Wait for receipt
echo "⏳ Waiting for deployment receipt..."
RECEIPT_JSON=""
for i in {1..30}; do
  RECEIPT_JSON=$(cast rpc eth_getTransactionReceipt "$TX_HASH" --rpc-url "$RPC_URL" 2>/dev/null || true)
  if echo "$RECEIPT_JSON" | grep -q 'contractAddress\|result'; then
    break
  fi
  sleep 2
done
CONTRACT_ADDR=$(echo "$RECEIPT_JSON" | jq -r '.contractAddress // .result.contractAddress // empty')

if [ -z "$CONTRACT_ADDR" ] || [ "$CONTRACT_ADDR" = "null" ]; then
    # Fallback: try to grab last 40-hex pattern from output
    CONTRACT_ADDR=$(echo "$DEPLOY_OUTPUT" | grep -o '0x[a-fA-F0-9]\{40\}' | tail -n1)
fi

if [ -z "$CONTRACT_ADDR" ] || [ "$CONTRACT_ADDR" = "null" ]; then
    echo "❌ Error: Failed to extract contract address"
    echo "Deployment output:"
    echo "$DEPLOY_OUTPUT"
    echo "Receipt: $RECEIPT_JSON"
    exit 1
fi

# Sanity check: ensure code exists at the address
CODE=$(cast code "$CONTRACT_ADDR" --rpc-url "$RPC_URL" 2>/dev/null || echo "0x")
if [ "$CODE" = "0x" ] || [ -z "$CODE" ]; then
  echo "❌ Error: No contract code found at $CONTRACT_ADDR (deployment not finalized yet?)"
  echo "Transaction: $TX_HASH"
  exit 1
fi

echo "✅ Contract deployed successfully!"
echo "📋 Contract Address: $CONTRACT_ADDR"
echo "🔗 Deployment TX: $TX_HASH"
echo "📝 Contract Name: PipelineDemo"
echo "🏷️  Contract Symbol: PDEMO"

# Save contract address for other scripts
echo "export NFT_ADDR=$CONTRACT_ADDR" > /tmp/nft_address.env
echo "export NFT_ADDR=$CONTRACT_ADDR" >> ~/.zshrc

echo ""
echo "🎯 Next steps:"
echo "1. Set NFT_ADDR: export NFT_ADDR=$CONTRACT_ADDR"
echo "2. Set RECIPIENT to your wallet: export RECIPIENT=$(cast wallet address --private-key "$PRIVATE_KEY" 2>/dev/null || echo 0xYourAddress)"
echo "3. Run the pipeline: ./scripts/run_pipeline.sh"
