# Ethereum Data Pipeline Demo

A reproducible mini-pipeline that pulls Ethereum transaction data from Etherscan into Spark (PySpark), generates visual representations, exports a compact JSONL summary, pins artifacts to IPFS (via Pinata or local Kubo), and mints an ERC-721 NFT on Sepolia testnet or local chain with `tokenURI = ipfs://<CID>`.

## 🎯 End Goal

Demonstrate a complete data pipeline:
1. **Etherscan** → **Spark** (PySpark) data ingestion (supports Sepolia testnet)
2. Export compact JSONL summary
3. **Generate visual chart** from transaction data
4. Pin to **IPFS** via **Pinata** (no Docker required) or local Kubo to get a **CID**
5. Mint **ERC-721** NFT with `tokenURI = ipfs://<CID>` on **Sepolia** or local chain

## 📋 Proof Artifacts

After running the pipeline, you'll have:
- Generated chart image (PNG) visualizing transaction data
- IPFS CID for image and metadata (via Pinata or local IPFS)
- IPFS gateway URLs for all artifacts
- NFT contract address on Sepolia (or local chain)
- Minting transaction hash
- Token ID with tokenURI pointing to IPFS metadata
- Screenshots of IPFS content and on-chain verification

## 🚀 Quick Start

### Prerequisites

**For Sepolia Testnet (Recommended)**:
1. **Foundry** tools: `forge --version && cast --version && anvil --version`
2. **Pinata account** with JWT token (see Pinata Setup below)
3. **Sepolia testnet ETH** (from faucet - see links in SETUP_DOCUMENTATION.md)
4. **Python 3.11+** with matplotlib and pandas

**For Local Development**:
1. **Docker** running: `open -a Docker`
2. **IPFS Kubo** container: `docker ps | grep ipfs-kubo`
3. **Foundry** tools: `forge --version && cast --version && anvil --version`
4. **Anvil** running in a terminal (shows funded accounts)

### Pinata Setup (for Sepolia/Production)

Pinata provides IPFS pinning without requiring Docker or local IPFS nodes:

1. **Create a Pinata account** at [pinata.cloud](https://pinata.cloud)
2. **Generate a JWT token**:
   - Go to API Keys section in your Pinata dashboard
   - Click "New Key"
   - Enable "pinFileToIPFS" permission
   - Copy the JWT token (starts with `eyJ...`)
3. **Add to environment**: `export PINATA_JWT=your_jwt_token_here`

### Environment Setup for Sepolia

```bash
export ETHERSCAN_API_KEY=your_etherscan_api_key
export CHAIN_ID=11155111  # Sepolia testnet
export RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
export PRIVATE_KEY=your_sepolia_private_key
export RECIPIENT=your_wallet_address
export PINATA_JWT=your_pinata_jwt_token
export IPFS_GATEWAY_URL=https://gateway.pinata.cloud
```

### Environment Setup for Local Development

```bash
export ETHERSCAN_API_KEY=your_etherscan_api_key
export RPC_URL=http://127.0.0.1:8545
export PRIVATE_KEY=your_private_key_from_anvil
export NFT_ADDR=your_deployed_simple721_address
export RECIPIENT=recipient_address
```

### Automated Setup

```bash
# Run the setup script to check all prerequisites
./scripts/setup.sh
```

### Run Complete Pipeline

```bash
# Run the entire pipeline with default settings
./scripts/run_pipeline.sh

# Or with custom parameters
./scripts/run_pipeline.sh 0x742d35Cc6634C0532925a3b844Bc454e4438f44e 10
```

## 📝 Manual Step-by-Step

### 1. Install Dependencies

```bash
python3 -m pip install --user pyspark requests matplotlib pandas
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### 2. Ingest from Etherscan → Parquet

**For Sepolia**:
```bash
python3 etherscan_ingest.py \
  --address 0x742d35Cc6634C0532925a3b844Bc454e4438f44e \
  --action txlist --page-size 100 --max-pages 5 --rps 5 \
  --chain-id 11155111 \
  --output parquet:/tmp/eth_tx
```

**For Mainnet**:
```bash
python3 etherscan_ingest.py \
  --address 0x742d35Cc6634C0532925a3b844Bc454e4438f44e \
  --action txlist --page-size 100 --max-pages 5 --rps 5 \
  --output parquet:/tmp/eth_tx
```

### 3. Convert to JSONL

```bash
python3 - <<'PY'
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
df = spark.read.parquet("/tmp/eth_tx")
df.orderBy(df.timeStamp.desc()).limit(200).toJSON().write.mode("overwrite").text("/tmp/eth_tx_jsonl")
spark.stop()
PY
```

### 4. Generate Visual Chart

```bash
./scripts/generate_image.sh /tmp/eth_tx_jsonl /tmp/eth_tx_chart.png
```

This creates a bar chart showing the top 10 transactions by value.

### 5. Pin to IPFS → Get CID

**Using Pinata (Recommended for Sepolia)**:
```bash
# The UI handles this automatically, or use the backend API
# Uploads both image and metadata, returns metadata CID
```

**Using Local IPFS**:
```bash
PART=$(ls /tmp/eth_tx_jsonl/ | grep -E '^part-|\.jsonl$' | head -n1)
curl -s -X POST -F "file=@/tmp/eth_tx_jsonl/$PART" \
  "http://127.0.0.1:5002/api/v0/add?pin=true" | tee /tmp/ipfs_add.json
CID=$(jq -r '.Hash' /tmp/ipfs_add.json)
echo "CID=$CID"
open "http://127.0.0.1:8081/ipfs/$CID"
```

### 6. Deploy NFT Contract (Sepolia)

```bash
./scripts/deploy_nft.sh
# Saves contract address to /tmp/nft_address.env
```

### 7. Mint NFT with IPFS URI

```bash
cast send $NFT_ADDR "mintWithTokenURI(address,string)" $RECIPIENT "ipfs://$CID" \
  --rpc-url $RPC_URL --private-key $PRIVATE_KEY
```

### 8. Verify TokenURI

```bash
cast call $NFT_ADDR "tokenURI(uint256)" 1 --rpc-url $RPC_URL
```

## 🛠️ Helper Scripts

The project includes several helper scripts in the `scripts/` directory:

- **`setup.sh`** - Check prerequisites and environment
- **`ingest.sh`** - Run Etherscan ingestion
- **`convert_to_jsonl.sh`** - Convert Parquet to JSONL
- **`generate_image.sh`** - Generate visual chart from JSONL data
- **`pin.sh`** - Pin JSONL to IPFS and get CID
- **`deploy_nft.sh`** - Deploy ERC-721 contract
- **`mint.sh`** - Mint NFT with IPFS tokenURI
- **`verify.sh`** - Verify tokenURI on-chain
- **`run_pipeline.sh`** - Run complete pipeline

## 📁 Project Structure

```
pipeline_demo/
├── etherscan_ingest.py          # Main PySpark ingestion script
├── generate_image.py            # Image generation from JSONL
├── scripts/
│   ├── setup.sh                 # Prerequisites check
│   ├── ingest.sh                # Etherscan ingestion
│   ├── convert_to_jsonl.sh      # Parquet to JSONL conversion
│   ├── generate_image.sh        # Image generation
│   ├── pin.sh                   # IPFS pinning
│   ├── deploy_nft.sh            # Contract deployment
│   ├── mint.sh                  # NFT minting
│   ├── verify.sh                # On-chain verification
│   └── run_pipeline.sh          # Complete pipeline runner
├── ui/                          # Web UI for pipeline orchestration
│   ├── app.py                   # Flask backend
│   ├── templates/               # HTML templates
│   └── start_ui.sh              # UI startup script
├── data/                        # Data storage directory
└── README.md                    # This file
```

## 🔧 Configuration

### Etherscan API

- Get your API key from [etherscan.io](https://etherscan.io/apis)
- Set rate limits appropriately (default: 5 RPS)
- Adjust page size and max pages based on your needs
- For Sepolia, use `--chain-id 11155111` parameter

### IPFS Options

**Pinata (Recommended for Production)**:
- No Docker required
- Persistent pinning
- Gateway: `https://gateway.pinata.cloud`
- Requires JWT token from Pinata dashboard

**Local IPFS Kubo**:
- Requires Docker container
- Gateway accessible at `http://127.0.0.1:8081`
- API accessible at `http://127.0.0.1:5002`

### Blockchain

- **Sepolia Testnet** (Recommended): Chain ID 11155111
- **Local Anvil**: For development and testing
- Requires deployed ERC-721 contract

## 🐛 Troubleshooting

### Common Issues

1. **`ModuleNotFoundError: pyspark` or `matplotlib`**
   ```bash
   python3 -m pip install --user pyspark requests matplotlib pandas
   ```

2. **Empty result set**
   - Increase `--max-pages`
   - Try a more active address
   - Use `--action tokennfttx` for NFT transfers

3. **IPFS "405 Method Not Allowed"**
   - Ensure IPFS Kubo container is running
   - Check container ports: `docker ps | grep ipfs`

4. **`cast: command not found`**
   ```bash
   foundryup
   source ~/.zshrc
   ```

5. **Environment variables not set**
   - Run `./scripts/setup.sh` to check all prerequisites
   - Set missing variables as shown in the setup output

### Pinata-Specific Issues

1. **"Invalid JWT" or Authentication Errors**
   - Verify your JWT token is correct and hasn't expired
   - Ensure the token has `pinFileToIPFS` permission enabled
   - Check that `PINATA_JWT` environment variable is set correctly
   - JWT tokens start with `eyJ` - make sure you copied the full token

2. **"Rate Limit Exceeded"**
   - Pinata free tier has rate limits
   - Wait a few minutes before retrying
   - Consider upgrading your Pinata plan for higher limits

3. **"File Too Large"**
   - Pinata free tier has file size limits (typically 100MB)
   - Reduce the number of transactions in your JSONL file
   - Use `--max-pages` parameter to limit data ingestion

4. **Gateway Timeout or CID Not Accessible**
   - Wait a few seconds after upload for content to propagate
   - Try accessing via different gateway: `https://ipfs.io/ipfs/<CID>`
   - Check Pinata dashboard to verify pin status

5. **Network/Connection Errors**
   - Check your internet connection
   - Verify firewall isn't blocking Pinata API (api.pinata.cloud)
   - Try again - temporary network issues can occur

### Sepolia-Specific Issues

1. **"Insufficient Funds" Error**
   - Get testnet ETH from Sepolia faucets (see SETUP_DOCUMENTATION.md)
   - Verify your wallet has enough ETH for gas fees
   - Check balance: `cast balance $RECIPIENT --rpc-url $RPC_URL`

2. **"Invalid Chain ID"**
   - Ensure `CHAIN_ID=11155111` is set for Sepolia
   - Verify RPC URL points to Sepolia network
   - Check RPC connection: `cast block-number --rpc-url $RPC_URL`

3. **Transaction Not Confirming**
   - Sepolia can be slow during high usage
   - Wait 30-60 seconds for confirmation
   - Check transaction on Sepolia Etherscan

### Health Checks

```bash
# Check Docker
docker ps

# Check IPFS
curl -s -X POST http://127.0.0.1:5002/api/v0/version

# Check Foundry
forge --version && cast --version && anvil --version

# Check Anvil (local)
curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545

# Check Sepolia RPC
cast block-number --rpc-url $RPC_URL

# Check Pinata connectivity
curl -s -H "Authorization: Bearer $PINATA_JWT" \
  https://api.pinata.cloud/data/testAuthentication
```

## 🎯 Expected Output

After successful completion, you should see:

1. **Ingestion**: Row count and Parquet files in `/tmp/eth_tx/`
2. **JSONL**: Converted files in `/tmp/eth_tx_jsonl/`
3. **Image**: Chart PNG at `/tmp/eth_tx_chart.png`
4. **IPFS**: Image CID and metadata CID with gateway URLs
5. **Contract**: Deployed address saved to `/tmp/nft_address.env`
6. **NFT**: Transaction hash and token ID
7. **Verification**: Confirmed `ipfs://<metadata_CID>` on-chain

## 📸 Screenshots to Take

1. IPFS gateway showing the chart image
2. IPFS gateway showing the metadata JSON
3. TokenURI verification output showing `ipfs://<CID>`
4. Transaction details on Sepolia Etherscan
5. NFT details on OpenSea testnet (optional)

## 🧪 Testing

### End-to-End Test Suite

The project includes a comprehensive end-to-end test suite that validates:

- **Full Pipeline Flow**: Complete pipeline execution on Sepolia testnet
- **Error Scenarios**: Invalid addresses, missing API keys, insufficient funds, etc.
- **Stage Independence**: Stages can run independently and idempotently

#### Running Tests

```bash
# Run full test suite
./scripts/run_e2e_tests.sh

# Run quick tests (error scenarios and stage independence only)
./scripts/run_e2e_tests.sh --quick

# Run tests directly with Python
python3 test_e2e_sepolia.py
```

#### Test Prerequisites

- Sepolia testnet ETH in your wallet
- Valid Etherscan API key
- Pinata JWT token (for IPFS tests)
- All environment variables configured in `.env`

For detailed test documentation, see [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md).

### Unit Tests

```bash
# Test Pinata integration functions
python3 test_pinata_integration.py

# Quick component verification
./scripts/quick_test.sh
```

## 🔄 Stretch Goals

- ✅ Swap local IPFS for Pinata pinning (persistent CID)
- ✅ Point to testnet RPC (Sepolia) with explorer links
- ✅ Add visual data representation (chart generation)
- ✅ Comprehensive end-to-end test suite
- Add Spark transformations (group-by KPIs) before JSONL export
- Implement advanced data validation and error handling
- Add monitoring and logging dashboard
- Support multiple chains (Polygon, Arbitrum, etc.)

## 📄 License

This project is for demonstration purposes. Please ensure you comply with Etherscan's API terms of service and any applicable regulations when using this code.
