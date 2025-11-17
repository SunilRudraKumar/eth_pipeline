#!/bin/bash
# Deploy Simple721 NFT contract
# Usage: ./scripts/deploy_nft.sh

set -e

echo "🚀 Deploying Simple721 NFT contract..."
echo "================================================"

# Load .env file if it exists
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
fi

# Check if RPC_URL is set
if [ -z "$RPC_URL" ]; then
    echo "❌ Error: RPC_URL environment variable not set"
    echo ""
    echo "💡 Set it with one of:"
    echo "   export RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YABzDqdTAdlNkJW3xg9NrBuWstqb5Jjs
   # Sepolia testnet"
    exit 1
fi

# Check if PRIVATE_KEY is set
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: PRIVATE_KEY environment variable not set"
    echo ""
    echo "💡 Set it with:"
    echo "   export PRIVATE_KEY=0x..."
    echo ""
    echo "⚠️  WARNING: Never commit private keys to version control!"
    exit 1
fi

# Validate PRIVATE_KEY format
if [[ ! "$PRIVATE_KEY" =~ ^0x[a-fA-F0-9]{64}$ ]]; then
    echo "❌ Error: PRIVATE_KEY has invalid format"
    echo "   Expected: 0x followed by 64 hexadecimal characters"
    echo "   Got: ${PRIVATE_KEY:0:10}... (length: ${#PRIVATE_KEY})"
    exit 1
fi

# Ensure required tools
command -v cast >/dev/null 2>&1 || { 
    echo "❌ Error: 'cast' not found. Install Foundry toolkit."
    echo ""
    echo "💡 Install with:"
    echo "   curl -L https://foundry.paradigm.xyz | bash"
    echo "   foundryup"
    exit 1
}

command -v jq >/dev/null 2>&1 || { 
    echo "❌ Error: 'jq' not found. Install JSON processor."
    echo ""
    echo "💡 Install with:"
    echo "   brew install jq  # macOS"
    echo "   apt-get install jq  # Ubuntu/Debian"
    exit 1
}

# Test RPC connection
echo "🔍 Testing RPC connection..."
BLOCK_NUMBER=$(cast block-number --rpc-url "$RPC_URL" 2>&1 || echo "FAILED")
if [ "$BLOCK_NUMBER" = "FAILED" ] || [ -z "$BLOCK_NUMBER" ]; then
    echo "❌ Error: Cannot connect to RPC endpoint"
    echo "   RPC URL: $RPC_URL"
    echo ""
    echo "💡 Possible causes:"
    echo "   - RPC endpoint is down or unreachable"
    echo "   - Invalid RPC URL format"
    echo "   - Network connectivity issues"
    echo "   - Firewall blocking the connection"
    exit 1
fi
echo "✅ Connected to RPC (block: $BLOCK_NUMBER)"

# Check account balance
echo "🔍 Checking account balance..."
ACCOUNT=$(cast wallet address --private-key "$PRIVATE_KEY" 2>/dev/null || echo "INVALID")
if [ "$ACCOUNT" = "INVALID" ]; then
    echo "❌ Error: Invalid private key"
    exit 1
fi

BALANCE=$(cast balance "$ACCOUNT" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")
BALANCE_ETH=$(echo "scale=6; $BALANCE / 1000000000000000000" | bc 2>/dev/null || echo "0")
echo "   Account: $ACCOUNT"
echo "   Balance: $BALANCE_ETH ETH"

if [ "$BALANCE" = "0" ] || [ -z "$BALANCE" ]; then
    echo "⚠️  WARNING: Account has zero balance"
    echo ""
    echo "💡 For Sepolia testnet, get test ETH from:"
    echo "   - https://sepoliafaucet.com/"
    echo "   - https://www.alchemy.com/faucets/ethereum-sepolia"
    echo ""
    echo "Continuing anyway (deployment will fail if insufficient funds)..."
fi

# Locate compiled artifact
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
ARTIFACT="$ROOT_DIR/out/Simple721.sol/Simple721.json"

echo ""
echo "🔍 Locating compiled contract..."
if [ ! -f "$ARTIFACT" ]; then
  echo "❌ Error: Compiled artifact not found"
  echo "   Expected: $ARTIFACT"
  echo ""
  echo "💡 Compile the contract first:"
  echo "   cd $ROOT_DIR"
  echo "   forge build"
  exit 1
fi
echo "✅ Found artifact: $ARTIFACT"

# Extract bytecode and encode constructor args
echo "🔍 Extracting bytecode..."
BYTECODE=$(jq -r '.bytecode.object' "$ARTIFACT" 2>/dev/null || echo "")
if [ -z "$BYTECODE" ] || [ "$BYTECODE" = "0x" ] || [ "$BYTECODE" = "null" ]; then
  echo "❌ Error: Could not read bytecode from artifact"
  echo "   Artifact may be corrupted or incomplete"
  echo ""
  echo "💡 Try rebuilding:"
  echo "   forge clean && forge build"
  exit 1
fi
echo "✅ Bytecode extracted (${#BYTECODE} bytes)"

echo "🔍 Encoding constructor arguments..."
ARGS_ENC=$(cast abi-encode "constructor(string,string)" "PipelineDemo" "PDEMO" 2>&1 || echo "FAILED")
if [ "$ARGS_ENC" = "FAILED" ] || [ -z "$ARGS_ENC" ]; then
    echo "❌ Error: Failed to encode constructor arguments"
    exit 1
fi
echo "✅ Constructor args encoded"

FULL_DATA="0x${BYTECODE#0x}${ARGS_ENC#0x}"

echo ""
echo "📝 Sending deployment transaction..."
echo "   RPC: $RPC_URL"
echo "   From: $ACCOUNT"
echo "   Gas Limit: 5000000"
echo ""

# Place flags before positional args for compatibility
DEPLOY_OUTPUT=$(cast send --rpc-url "$RPC_URL" --private-key "$PRIVATE_KEY" --gas-limit 5000000 \
  --create "$FULL_DATA" 2>&1 || true)

# Check for common error patterns
if echo "$DEPLOY_OUTPUT" | grep -qi "insufficient funds"; then
    echo "❌ Error: Insufficient funds for deployment"
    echo "   Account: $ACCOUNT"
    echo "   Balance: $BALANCE_ETH ETH"
    echo ""
    echo "💡 Get test ETH from a Sepolia faucet:"
    echo "   - https://sepoliafaucet.com/"
    echo "   - https://www.alchemy.com/faucets/ethereum-sepolia"
    exit 1
fi

if echo "$DEPLOY_OUTPUT" | grep -qi "nonce too low"; then
    echo "❌ Error: Nonce too low (transaction already submitted?)"
    echo ""
    echo "💡 Wait for pending transactions to complete or reset nonce"
    exit 1
fi

if echo "$DEPLOY_OUTPUT" | grep -qi "gas too low\|intrinsic gas"; then
    echo "❌ Error: Gas limit too low for deployment"
    echo ""
    echo "💡 Try increasing gas limit or check contract size"
    exit 1
fi

# Extract tx hash then query receipt for contract address
TX_HASH=$(echo "$DEPLOY_OUTPUT" | grep -o '0x[a-fA-F0-9]\{64\}' | head -n1)
if [ -z "$TX_HASH" ]; then
    echo "❌ Error: Failed to obtain deployment transaction hash"
    echo ""
    echo "Deployment output:"
    echo "================================================"
    echo "$DEPLOY_OUTPUT"
    echo "================================================"
    echo ""
    echo "💡 Possible causes:"
    echo "   - Transaction was rejected by the network"
    echo "   - RPC endpoint returned an error"
    echo "   - Insufficient gas or funds"
    exit 1
fi
echo "✅ Transaction submitted: $TX_HASH"

# Wait for receipt
echo ""
echo "⏳ Waiting for transaction confirmation..."
RECEIPT_JSON=""
WAIT_COUNT=0
MAX_WAIT=30

for i in {1..30}; do
  RECEIPT_JSON=$(cast rpc eth_getTransactionReceipt "$TX_HASH" --rpc-url "$RPC_URL" 2>/dev/null || true)
  if echo "$RECEIPT_JSON" | grep -q 'contractAddress\|result'; then
    break
  fi
  WAIT_COUNT=$((WAIT_COUNT + 1))
  if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
    echo "   Still waiting... ($WAIT_COUNT/${MAX_WAIT}s)"
  fi
  sleep 2
done

if [ -z "$RECEIPT_JSON" ] || [ "$RECEIPT_JSON" = "null" ]; then
    echo "⚠️  Warning: Transaction receipt not available after ${MAX_WAIT}s"
    echo "   Transaction may still be pending"
    echo "   TX Hash: $TX_HASH"
    echo ""
    echo "💡 Check transaction status manually:"
    echo "   cast receipt $TX_HASH --rpc-url $RPC_URL"
    exit 1
fi

# Check transaction status
TX_STATUS=$(echo "$RECEIPT_JSON" | jq -r '.status // .result.status // "0x1"')
if [ "$TX_STATUS" = "0x0" ]; then
    echo "❌ Error: Transaction reverted"
    echo "   TX Hash: $TX_HASH"
    echo ""
    echo "💡 Possible causes:"
    echo "   - Constructor failed (check contract logic)"
    echo "   - Out of gas during deployment"
    echo "   - Contract size exceeds limit"
    echo ""
    echo "Check transaction details:"
    echo "   cast receipt $TX_HASH --rpc-url $RPC_URL"
    exit 1
fi

CONTRACT_ADDR=$(echo "$RECEIPT_JSON" | jq -r '.contractAddress // .result.contractAddress // empty')

if [ -z "$CONTRACT_ADDR" ] || [ "$CONTRACT_ADDR" = "null" ]; then
    echo "⚠️  Warning: Contract address not found in receipt"
    # Fallback: try to grab last 40-hex pattern from output
    CONTRACT_ADDR=$(echo "$DEPLOY_OUTPUT" | grep -o '0x[a-fA-F0-9]\{40\}' | tail -n1)
fi

if [ -z "$CONTRACT_ADDR" ] || [ "$CONTRACT_ADDR" = "null" ]; then
    echo "❌ Error: Failed to extract contract address"
    echo ""
    echo "Deployment output:"
    echo "================================================"
    echo "$DEPLOY_OUTPUT"
    echo "================================================"
    echo ""
    echo "Receipt:"
    echo "================================================"
    echo "$RECEIPT_JSON" | jq '.' 2>/dev/null || echo "$RECEIPT_JSON"
    echo "================================================"
    exit 1
fi

# Sanity check: ensure code exists at the address
echo "🔍 Verifying contract deployment..."
CODE=$(cast code "$CONTRACT_ADDR" --rpc-url "$RPC_URL" 2>/dev/null || echo "0x")
if [ "$CODE" = "0x" ] || [ -z "$CODE" ]; then
  echo "❌ Error: No contract code found at $CONTRACT_ADDR"
  echo "   Transaction: $TX_HASH"
  echo ""
  echo "💡 Possible causes:"
  echo "   - Transaction not yet finalized (wait longer)"
  echo "   - Deployment reverted silently"
  echo "   - Wrong network or RPC endpoint"
  echo ""
  echo "Check transaction:"
  echo "   cast receipt $TX_HASH --rpc-url $RPC_URL"
  exit 1
fi
echo "✅ Contract code verified at address"

echo ""
echo "================================================"
echo "✅ Contract deployed successfully!"
echo "================================================"
echo "📋 Contract Address: $CONTRACT_ADDR"
echo "🔗 Deployment TX: $TX_HASH"
echo "📝 Contract Name: PipelineDemo"
echo "🏷️  Contract Symbol: PDEMO"
echo "👤 Deployer: $ACCOUNT"
echo "⛽ Gas Used: $(echo "$RECEIPT_JSON" | jq -r '.gasUsed // .result.gasUsed // "unknown"')"
echo "================================================"

# Save contract address for other scripts
echo "export NFT_ADDR=$CONTRACT_ADDR" > /tmp/nft_address.env
echo "✅ Contract address saved to /tmp/nft_address.env"

# Optionally save to shell config (commented out to avoid pollution)
# echo "export NFT_ADDR=$CONTRACT_ADDR" >> ~/.zshrc

echo ""
echo "🎯 Next steps:"
echo "1. Set NFT_ADDR: export NFT_ADDR=$CONTRACT_ADDR"
echo "2. Set RECIPIENT: export RECIPIENT=$ACCOUNT"
echo "3. Upload data to IPFS and mint NFT"
echo ""
echo "💡 View on block explorer (if on testnet):"
if echo "$RPC_URL" | grep -qi "sepolia"; then
    echo "   https://sepolia.etherscan.io/address/$CONTRACT_ADDR"
fi
