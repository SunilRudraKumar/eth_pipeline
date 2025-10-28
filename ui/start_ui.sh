#!/bin/bash
# Start the Pipeline Demo Web UI

echo "🚀 Starting Ethereum Data Pipeline Demo Web UI..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Please run this script from the ui/ directory"
    exit 1
fi

# Install Python dependencies if needed
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Set environment variables
# Use an existing ETHERSCAN_API_KEY if provided; otherwise fall back to demo key
if [ -z "$ETHERSCAN_API_KEY" ]; then
    export ETHERSCAN_API_KEY=YE887SMD6UV3QVQVY2IJYC1JRC2FTGGHKM
fi
export RPC_URL=http://127.0.0.1:8545

# Prefer deployed NFT address if available
if [ -f "/tmp/nft_address.env" ]; then
    # shellcheck disable=SC1091
    source /tmp/nft_address.env
else
    export NFT_ADDR=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
fi

export RECIPIENT=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# Provide default Anvil private key for local minting if not set
if [ -z "$PRIVATE_KEY" ]; then
    export PRIVATE_KEY=0xac0974beef8f3bfa0f6baf6b9a3cbe1ac9a5a7d3edb6c6c8f7c6a5a2d7f6a5b9
fi

echo "✅ Environment variables set"
echo "🌐 Starting web server..."
echo ""
echo "📋 Access your pipeline dashboard at:"
echo "   http://localhost:5001"
echo ""
echo "🔗 Key URLs:"
echo "   - Dashboard: http://localhost:5001"
echo "   - IPFS Gateway: http://127.0.0.1:8081/ipfs/QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL"
echo "   - Anvil RPC: http://127.0.0.1:8545"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask app on port 5001 (direct execution avoids reload path issues)
python3 app.py
