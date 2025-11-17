#!/bin/bash
# Mint NFT with IPFS tokenURI
# Usage: ./scripts/mint.sh [recipient] [token_uri]

set -e

RECIPIENT=${1:-"$RECIPIENT"}
TOKEN_URI=${2:-""}

echo "🎨 Minting NFT..."
echo "================================================"

# Check required environment variables
if [ -z "$RPC_URL" ]; then
    echo "❌ Error: RPC_URL environment variable not set"
    echo ""
    echo "💡 Set it with:"
    echo "   export RPC_URL=http://127.0.0.1:8545  # Local Anvil"
    echo "   export RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID  # Sepolia"
    exit 1
fi

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
    exit 1
fi

# Load NFT_ADDR from /tmp/nft_address.env if not set
if [ -z "$NFT_ADDR" ]; then
    if [ -f "/tmp/nft_address.env" ]; then
        source /tmp/nft_address.env
        echo "✅ Loaded NFT_ADDR from /tmp/nft_address.env"
    fi
fi

if [ -z "$NFT_ADDR" ]; then
    echo "❌ Error: NFT_ADDR environment variable not set"
    echo ""
    echo "💡 Deploy contract first:"
    echo "   ./scripts/deploy_nft.sh"
    echo ""
    echo "Or set manually:"
    echo "   export NFT_ADDR=0x..."
    exit 1
fi

# Validate NFT_ADDR format
if [[ ! "$NFT_ADDR" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    echo "❌ Error: NFT_ADDR has invalid format"
    echo "   Expected: 0x followed by 40 hexadecimal characters"
    echo "   Got: $NFT_ADDR"
    exit 1
fi

if [ -z "$RECIPIENT" ]; then
    echo "❌ Error: RECIPIENT environment variable not set"
    echo ""
    echo "💡 Set it with:"
    echo "   export RECIPIENT=0x..."
    exit 1
fi

# Validate RECIPIENT format
if [[ ! "$RECIPIENT" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    echo "❌ Error: RECIPIENT has invalid format"
    echo "   Expected: 0x followed by 40 hexadecimal characters"
    echo "   Got: $RECIPIENT"
    exit 1
fi

# Load metadata CID from /tmp/ipfs_cid.env if TOKEN_URI not provided
if [ -z "$TOKEN_URI" ]; then
    if [ -f "/tmp/ipfs_cid.env" ]; then
        source /tmp/ipfs_cid.env
        # Prefer METADATA_CID over CID for NFT minting
        if [ -n "$METADATA_CID" ]; then
            TOKEN_URI="ipfs://$METADATA_CID"
            echo "✅ Loaded METADATA_CID from /tmp/ipfs_cid.env"
        elif [ -n "$CID" ]; then
            TOKEN_URI="ipfs://$CID"
            echo "✅ Loaded CID from /tmp/ipfs_cid.env"
        fi
    fi
fi

if [ -z "$TOKEN_URI" ]; then
    echo "❌ Error: TOKEN_URI not provided and no CID found"
    echo ""
    echo "💡 Upload to IPFS first or provide TOKEN_URI:"
    echo "   ./scripts/mint.sh <recipient> ipfs://Qm..."
    exit 1
fi

# Validate TOKEN_URI format
if [[ ! "$TOKEN_URI" =~ ^ipfs:// ]]; then
    echo "⚠️  Warning: TOKEN_URI doesn't start with 'ipfs://'"
    echo "   Got: $TOKEN_URI"
    echo "   Continuing anyway..."
fi

echo ""
echo "📋 Minting Configuration:"
echo "   Contract: $NFT_ADDR"
echo "   Recipient: $RECIPIENT"
echo "   Token URI: $TOKEN_URI"
echo "   RPC URL: $RPC_URL"
echo ""

# Test RPC connection
echo "🔍 Testing RPC connection..."
BLOCK_NUMBER=$(cast block-number --rpc-url "$RPC_URL" 2>&1 || echo "FAILED")
if [ "$BLOCK_NUMBER" = "FAILED" ] || [ -z "$BLOCK_NUMBER" ]; then
    echo "❌ Error: Cannot connect to RPC endpoint"
    echo "   RPC URL: $RPC_URL"
    exit 1
fi
echo "✅ Connected to RPC (block: $BLOCK_NUMBER)"

# Ensure contract code exists before proceeding
echo "🔍 Verifying contract exists..."
CODE=$(cast code "$NFT_ADDR" --rpc-url "$RPC_URL" 2>/dev/null || echo "0x")
if [ -z "$CODE" ] || [ "$CODE" = "0x" ]; then
  echo "❌ Error: No contract code found at $NFT_ADDR"
  echo ""
  echo "💡 Possible causes:"
  echo "   - Contract not deployed at this address"
  echo "   - Wrong network (check RPC_URL)"
  echo "   - Deployment not yet finalized"
  echo ""
  echo "Deploy contract first:"
  echo "   ./scripts/deploy_nft.sh"
  exit 1
fi
echo "✅ Contract verified at address"

# Track total supply before mint to help with fallback detection
PRE_TOTAL_SUPPLY=$(cast call "$NFT_ADDR" "totalSupply()(uint256)" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")
if [ -z "$PRE_TOTAL_SUPPLY" ] || [ "$PRE_TOTAL_SUPPLY" = "null" ]; then
    PRE_TOTAL_SUPPLY=0
fi
echo "   Current total supply: $PRE_TOTAL_SUPPLY"

# Check account balance
ACCOUNT=$(cast wallet address --private-key "$PRIVATE_KEY" 2>/dev/null || echo "INVALID")
if [ "$ACCOUNT" = "INVALID" ]; then
    echo "❌ Error: Invalid private key"
    exit 1
fi

BALANCE=$(cast balance "$ACCOUNT" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")
BALANCE_ETH=$(echo "scale=6; $BALANCE / 1000000000000000000" | bc 2>/dev/null || echo "0")
echo "   Minter: $ACCOUNT"
echo "   Balance: $BALANCE_ETH ETH"

if [ "$BALANCE" = "0" ] || [ -z "$BALANCE" ]; then
    echo "⚠️  WARNING: Account has zero balance"
    echo ""
    echo "💡 Get test ETH from a Sepolia faucet"
    echo "Continuing anyway (minting will fail if insufficient funds)..."
fi

# Mint the NFT
echo ""
echo "🔄 Sending mint transaction..."

TX_OUTPUT=""
TX_HASH=""

# Primary path: sign with PRIVATE_KEY
TX_OUTPUT=$(cast send "$NFT_ADDR" "mintWithTokenURI(address,string)" "$RECIPIENT" "$TOKEN_URI" \
  --rpc-url "$RPC_URL" --private-key "$PRIVATE_KEY" --gas-limit 500000 2>&1 || true)

# Check for common error patterns
if echo "$TX_OUTPUT" | grep -qi "insufficient funds"; then
    echo "❌ Error: Insufficient funds for minting"
    echo "   Account: $ACCOUNT"
    echo "   Balance: $BALANCE_ETH ETH"
    echo ""
    echo "💡 Get test ETH from a Sepolia faucet:"
    echo "   - https://sepoliafaucet.com/"
    echo "   - https://www.alchemy.com/faucets/ethereum-sepolia"
    exit 1
fi

if echo "$TX_OUTPUT" | grep -qi "execution reverted"; then
    echo "❌ Error: Transaction reverted"
    echo ""
    REVERT_REASON=$(echo "$TX_OUTPUT" | grep -o "execution reverted: [^\"]*" | head -n1)
    if [ -n "$REVERT_REASON" ]; then
        echo "Revert reason: $REVERT_REASON"
    fi
    echo ""
    echo "💡 Possible causes:"
    echo "   - Contract doesn't have mintWithTokenURI function"
    echo "   - Minting is paused or restricted"
    echo "   - Invalid recipient address"
    echo "   - Token URI validation failed"
    exit 1
fi

if echo "$TX_OUTPUT" | grep -qi "nonce too low"; then
    echo "❌ Error: Nonce too low (transaction already submitted?)"
    echo ""
    echo "💡 Wait for pending transactions to complete"
    exit 1
fi

TX_HASH=$(echo "$TX_OUTPUT" | grep -o '0x[a-fA-F0-9]\{64\}' | head -n1)

# Fallback: unlocked account via JSON-RPC
if [ -z "$TX_HASH" ]; then
  echo "ℹ️  Trying fallback method (unlocked account)..."
  DATA=$(cast calldata "mintWithTokenURI(address,string)" "$RECIPIENT" "$TOKEN_URI" 2>&1 || echo "FAILED")
  if [ "$DATA" != "FAILED" ]; then
    TX_HASH=$(cast rpc eth_sendTransaction '{"from":"'"$RECIPIENT"'","to":"'"$NFT_ADDR"'","data":"'"$DATA"'","gas":"0x7a120"}' --rpc-url "$RPC_URL" 2>/dev/null | tr -d '"' || echo "")
  fi
fi

# Validate we have a tx hash
if [ -z "$TX_HASH" ] || [ "$TX_HASH" = "null" ]; then
    echo "❌ Error: Failed to send mint transaction"
    echo ""
    echo "Transaction output:"
    echo "================================================"
    echo "$TX_OUTPUT"
    echo "================================================"
    echo ""
    echo "💡 Check that:"
    echo "   - Contract has mintWithTokenURI(address,string) function"
    echo "   - Account has sufficient balance"
    echo "   - RPC endpoint is working correctly"
    exit 1
fi

echo "✅ Transaction submitted: $TX_HASH"

# Extract token ID from transaction receipt
echo ""
echo "⏳ Waiting for transaction confirmation..."
RECEIPT_JSON=""
WAIT_COUNT=0
SLEEP_INTERVAL=3
MAX_WAIT_SECONDS=${MINT_MAX_WAIT:-180}
if [ "$MAX_WAIT_SECONDS" -lt "$SLEEP_INTERVAL" ]; then
    MAX_WAIT_SECONDS=$SLEEP_INTERVAL
fi
MAX_ITERATIONS=$((MAX_WAIT_SECONDS / SLEEP_INTERVAL))
if [ "$MAX_ITERATIONS" -lt 1 ]; then
    MAX_ITERATIONS=1
fi

for ((i=1; i<=MAX_ITERATIONS; i++)); do
  RECEIPT_JSON=$(cast rpc eth_getTransactionReceipt "$TX_HASH" --rpc-url "$RPC_URL" 2>/dev/null || true)
  if echo "$RECEIPT_JSON" | grep -q 'logs\|result'; then
    break
  fi
  WAIT_COUNT=$((WAIT_COUNT + SLEEP_INTERVAL))
  if [ $((WAIT_COUNT % 15)) -eq 0 ]; then
    echo "   Still waiting... (${WAIT_COUNT}s/${MAX_WAIT_SECONDS}s)"
  fi
  sleep $SLEEP_INTERVAL
done

if [ -z "$RECEIPT_JSON" ] || [ "$RECEIPT_JSON" = "null" ]; then
    echo "⚠️  Receipt still pending after ${MAX_WAIT_SECONDS}s. Checking contract state for confirmation..."
    POST_TOTAL_SUPPLY=$(cast call "$NFT_ADDR" "totalSupply()(uint256)" --rpc-url "$RPC_URL" 2>/dev/null || echo "$PRE_TOTAL_SUPPLY")
    if [ -z "$POST_TOTAL_SUPPLY" ] || [ "$POST_TOTAL_SUPPLY" = "null" ]; then
        POST_TOTAL_SUPPLY="$PRE_TOTAL_SUPPLY"
    fi
    if [ "$POST_TOTAL_SUPPLY" -gt "$PRE_TOTAL_SUPPLY" ]; then
        echo "✅ Detected increase in total supply ($PRE_TOTAL_SUPPLY → $POST_TOTAL_SUPPLY). Mint appears successful even though receipt isn't ready."
        RECEIPT_JSON=$(cast rpc eth_getTransactionReceipt "$TX_HASH" --rpc-url "$RPC_URL" 2>/dev/null || echo "{}")
        if [ -z "$RECEIPT_JSON" ] || [ "$RECEIPT_JSON" = "null" ]; then
            RECEIPT_JSON="{}"
        fi
    else
        echo "⚠️  Warning: Transaction receipt not available after ${MAX_WAIT_SECONDS}s"
        echo "   Transaction may still be pending"
        echo "   TX Hash: $TX_HASH"
        echo ""
        echo "💡 Check transaction status manually:"
        echo "   cast receipt $TX_HASH --rpc-url $RPC_URL"
        exit 1
    fi
fi

# Check transaction status
TX_STATUS=$(echo "$RECEIPT_JSON" | jq -r '.status // .result.status // "0x1"')
if [ "$TX_STATUS" = "0x0" ]; then
    echo "❌ Error: Transaction reverted"
    echo "   TX Hash: $TX_HASH"
    echo ""
    echo "💡 Possible causes:"
    echo "   - Minting function reverted (check contract logic)"
    echo "   - Invalid token URI format"
    echo "   - Recipient address validation failed"
    echo "   - Out of gas"
    echo ""
    echo "Check transaction details:"
    echo "   cast receipt $TX_HASH --rpc-url $RPC_URL"
    exit 1
fi

echo "✅ Transaction confirmed!"

# Extract token ID from Transfer event logs
# Transfer event signature: Transfer(address,address,uint256)
# Topic0: 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
echo "🔍 Extracting token ID from logs..."
TOKEN_ID=""
if [ -n "$RECEIPT_JSON" ]; then
    # Extract the third topic (tokenId) from the first Transfer event
    TOKEN_ID=$(echo "$RECEIPT_JSON" | jq -r '.logs[]? // .result.logs[]? | select(.topics[0] == "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef") | .topics[3]' | head -n1)
    if [ -n "$TOKEN_ID" ] && [ "$TOKEN_ID" != "null" ]; then
        # Convert hex to decimal
        TOKEN_ID=$(printf "%d" "$TOKEN_ID" 2>/dev/null || echo "")
    fi
fi

# Fallback: try to get latest token from totalSupply
if [ -z "$TOKEN_ID" ] || [ "$TOKEN_ID" = "null" ]; then
    echo "⚠️  Could not extract token ID from logs, querying totalSupply..."
    TOTAL_SUPPLY=$(cast call "$NFT_ADDR" "totalSupply()(uint256)" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")
    if [ -n "$TOTAL_SUPPLY" ] && [ "$TOTAL_SUPPLY" != "0" ]; then
        TOKEN_ID=$((TOTAL_SUPPLY - 1))
        echo "✅ Token ID from totalSupply: $TOKEN_ID"
    fi
fi

if [ -z "$TOKEN_ID" ] || [ "$TOKEN_ID" = "null" ]; then
    echo "⚠️  Warning: Could not determine token ID"
    echo "   Minting succeeded but token ID extraction failed"
    TOKEN_ID="unknown"
else
    echo "✅ Token ID: $TOKEN_ID"
fi

# Verify tokenURI using cast call
if [ "$TOKEN_ID" != "unknown" ]; then
    echo ""
    echo "🔍 Verifying tokenURI..."
    VERIFIED_URI=$(cast call "$NFT_ADDR" "tokenURI(uint256)(string)" "$TOKEN_ID" --rpc-url "$RPC_URL" 2>/dev/null || echo "")
    if [ -n "$VERIFIED_URI" ] && [ "$VERIFIED_URI" != "0x" ]; then
        echo "✅ Verified tokenURI: $VERIFIED_URI"
        if [ "$VERIFIED_URI" != "$TOKEN_URI" ]; then
            echo "⚠️  Warning: Verified URI differs from expected URI"
            echo "   Expected: $TOKEN_URI"
            echo "   Got: $VERIFIED_URI"
        fi
    else
        echo "⚠️  Could not verify tokenURI"
        echo "   Contract may not support tokenURI function or token doesn't exist"
    fi
    OWNER_ONCHAIN=$(cast call "$NFT_ADDR" "ownerOf(uint256)(address)" "$TOKEN_ID" --rpc-url "$RPC_URL" 2>/dev/null || echo "")
    if [ -n "$OWNER_ONCHAIN" ] && [ "$OWNER_ONCHAIN" != "0x0000000000000000000000000000000000000000" ]; then
        echo "👤 On-chain owner: $OWNER_ONCHAIN"
    fi
fi

# Save transaction details and token ID
echo "export TX_HASH=$TX_HASH" > /tmp/mint_tx.env
echo "export TOKEN_URI=$TOKEN_URI" >> /tmp/mint_tx.env
if [ "$TOKEN_ID" != "unknown" ]; then
    echo "export TOKEN_ID=$TOKEN_ID" >> /tmp/mint_tx.env
fi
echo "✅ Transaction details saved to /tmp/mint_tx.env"

# Save token ID to dedicated file for easy access
if [ "$TOKEN_ID" != "unknown" ]; then
    echo "export TOKEN_ID=$TOKEN_ID" > /tmp/nft_token_id.env
    echo "✅ Token ID saved to /tmp/nft_token_id.env"
fi

# Calculate gas used
GAS_USED=$(echo "$RECEIPT_JSON" | jq -r '.gasUsed // .result.gasUsed // "unknown"')

echo ""
echo "================================================"
echo "✅ NFT Minted Successfully!"
echo "================================================"
echo "🎫 Token ID: $TOKEN_ID"
echo "📋 Token URI: $TOKEN_URI"
echo "👤 Owner: $RECIPIENT"
echo "🔗 TX Hash: $TX_HASH"
echo "⛽ Gas Used: $GAS_USED"
echo "================================================"

echo ""
echo "🎯 Next steps:"
echo "1. Verify the tokenURI: ./scripts/verify.sh"
if echo "$RPC_URL" | grep -qi "sepolia"; then
    echo "2. View on Sepolia Etherscan:"
    echo "   https://sepolia.etherscan.io/tx/$TX_HASH"
    echo "   https://sepolia.etherscan.io/token/$NFT_ADDR?a=$TOKEN_ID"
fi
if [ "$TOKEN_ID" != "unknown" ]; then
    echo "3. View your NFT with token ID: $TOKEN_ID"
fi
