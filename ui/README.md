# Ethereum Data Pipeline Demo - Web UI

A comprehensive web interface to visualize and monitor your Ethereum data pipeline.

## 🎯 Features

- **Real-time Pipeline Status**: Monitor all pipeline steps
- **IPFS Data Viewer**: View your pinned data directly in the browser
- **Blockchain Integration**: Check contract status and NFT information
- **Transaction Explorer**: Browse sample transaction data
- **Interactive Dashboard**: Clean, responsive interface

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Your pipeline components running:
  - Anvil (local blockchain)
  - IPFS Kubo container
  - Pipeline data in `/tmp/eth_tx*`

### Installation & Startup

1. **Navigate to the UI directory**:
   ```bash
   cd ui/
   ```

2. **Start the web interface**:
   ```bash
   ./start_ui.sh
   ```

3. **Open your browser**:
   ```
   http://localhost:5001
   ```

## 📊 Dashboard Components

### Pipeline Status
- Overall pipeline health
- Individual step status (completed/error)
- Real-time updates

### IPFS Data
- **CID**: `QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL`
- **Gateway URL**: Direct link to view your data
- **Sample Data**: Preview of transaction data

### Blockchain Info
- **RPC Status**: Anvil connection status
- **Contract Info**: NFT contract details
- **Block Number**: Current blockchain state

### NFT Information
- **Token ID**: 1
- **Token URI**: `ipfs://QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL`
- **Mint Transaction**: Deployment transaction hash

### Sample Transactions
- Real Ethereum transaction data
- From your Etherscan ingestion
- Formatted for easy reading

## 🔧 API Endpoints

The backend provides several API endpoints:

- `GET /api/status` - Overall pipeline status
- `GET /api/ipfs` - IPFS information and data
- `GET /api/blockchain` - Blockchain connection and contract info
- `GET /api/nft` - NFT token information
- `GET /api/transactions` - Sample transaction data

## 🎨 UI Features

- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Status Indicators**: Color-coded status badges
- **Interactive Links**: Direct access to IPFS gateway
- **Code Blocks**: Easy-to-read technical data

## 🔗 Integration

The UI connects to:
- **Local Anvil**: `http://127.0.0.1:8545`
- **IPFS Gateway**: `http://127.0.0.1:8081`
- **IPFS API**: `http://127.0.0.1:5002`
- **Local Files**: `/tmp/eth_tx*`

## 📋 Proof Artifacts

Your dashboard shows all the key proof artifacts:

1. **IPFS CID**: `QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL`
2. **Gateway URL**: `http://127.0.0.1:8081/ipfs/QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL`
3. **NFT Contract**: `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
4. **Mint Transaction**: `0xb8fa4fb101bb3b008e9c8682329faa796459be4fa4841e5b21101d4f02953293`
5. **Token URI**: `ipfs://QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL`

## 🛠️ Troubleshooting

### UI Not Loading
- Check if Python dependencies are installed: `pip3 install -r requirements.txt`
- Verify port 5000 is available
- Check console for error messages

### API Errors
- Ensure Anvil is running: `anvil`
- Verify IPFS container is up: `docker ps | grep ipfs`
- Check environment variables are set

### Data Not Showing
- Confirm pipeline data exists in `/tmp/eth_tx*`
- Verify IPFS CID is correct
- Check blockchain connection

## 🎯 Demo Flow

1. **Start Services**: Anvil, IPFS, and your pipeline
2. **Launch UI**: `./start_ui.sh`
3. **View Dashboard**: `http://localhost:5000`
4. **Explore Data**: Click links to view IPFS content
5. **Verify Pipeline**: All steps should show "COMPLETED"

## 📸 Screenshots

Take screenshots of:
- Dashboard overview showing all green statuses
- IPFS data viewer showing transaction JSON
- Blockchain info showing contract deployment
- NFT information showing tokenURI

Your complete pipeline demonstration is now fully visualized and interactive!
