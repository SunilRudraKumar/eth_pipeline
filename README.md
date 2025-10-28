# Ethereum Data Pipeline Demo

A reproducible mini-pipeline that pulls Ethereum transaction data from Etherscan into Spark (PySpark), exports a compact JSONL summary, pins it to IPFS to get a CID, and mints an ERC-721 NFT on your local chain with `tokenURI = ipfs://<CID>`.

## 🎯 End Goal

Demonstrate a complete data pipeline:
1. **Etherscan** → **Spark** (PySpark) data ingestion
2. Export compact JSONL summary
3. Pin to **IPFS** to get a **CID**
4. Mint **ERC-721** NFT with `tokenURI = ipfs://<CID>`

## 📋 Proof Artifacts

After running the pipeline, you'll have:
- IPFS CID and gateway URL
- Transaction hash
- Token ID
- Screenshots of IPFS content and on-chain verification

## 🚀 Quick Start

### Prerequisites

1. **Docker** running: `open -a Docker`
2. **IPFS Kubo** container: `docker ps | grep ipfs-kubo`
3. **Foundry** tools: `forge --version && cast --version && anvil --version`
4. **Anvil** running in a terminal (shows funded accounts)
5. **ERC-721** contract deployed (you need the address)

### Environment Setup

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
python3 -m pip install --user pyspark requests
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### 2. Ingest from Etherscan → Parquet

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

### 4. Pin to IPFS → Get CID

```bash
PART=$(ls /tmp/eth_tx_jsonl/ | grep -E '^part-|\.jsonl$' | head -n1)
curl -s -X POST -F "file=@/tmp/eth_tx_jsonl/$PART" \
  "http://127.0.0.1:5002/api/v0/add?pin=true" | tee /tmp/ipfs_add.json
CID=$(jq -r '.Hash' /tmp/ipfs_add.json)
echo "CID=$CID"
open "http://127.0.0.1:8081/ipfs/$CID"
```

### 5. Mint NFT with IPFS URI

```bash
cast send $NFT_ADDR "mintWithTokenURI(address,string)" $RECIPIENT "ipfs://$CID" \
  --rpc-url $RPC_URL --private-key $PRIVATE_KEY
```

### 6. Verify TokenURI

```bash
cast call $NFT_ADDR "tokenURI(uint256)" 1 --rpc-url $RPC_URL
```

## 🛠️ Helper Scripts

The project includes several helper scripts in the `scripts/` directory:

- **`setup.sh`** - Check prerequisites and environment
- **`ingest.sh`** - Run Etherscan ingestion
- **`convert_to_jsonl.sh`** - Convert Parquet to JSONL
- **`pin.sh`** - Pin JSONL to IPFS and get CID
- **`mint.sh`** - Mint NFT with IPFS tokenURI
- **`verify.sh`** - Verify tokenURI on-chain
- **`run_pipeline.sh`** - Run complete pipeline

## 📁 Project Structure

```
pipeline_demo/
├── etherscan_ingest.py          # Main PySpark ingestion script
├── scripts/
│   ├── setup.sh                 # Prerequisites check
│   ├── ingest.sh                # Etherscan ingestion
│   ├── convert_to_jsonl.sh      # Parquet to JSONL conversion
│   ├── pin.sh                   # IPFS pinning
│   ├── mint.sh                  # NFT minting
│   ├── verify.sh                # On-chain verification
│   └── run_pipeline.sh          # Complete pipeline runner
├── data/                        # Data storage directory
└── README.md                    # This file
```

## 🔧 Configuration

### Etherscan API

- Get your API key from [etherscan.io](https://etherscan.io/apis)
- Set rate limits appropriately (default: 5 RPS)
- Adjust page size and max pages based on your needs

### IPFS

- Uses local IPFS Kubo container
- Gateway accessible at `http://127.0.0.1:8081`
- API accessible at `http://127.0.0.1:5002`

### Blockchain

- Uses local Anvil chain by default
- Can be configured for testnets (Sepolia, etc.)
- Requires deployed ERC-721 contract

## 🐛 Troubleshooting

### Common Issues

1. **`ModuleNotFoundError: pyspark`**
   ```bash
   python3 -m pip install --user pyspark requests
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

### Health Checks

```bash
# Check Docker
docker ps

# Check IPFS
curl -s -X POST http://127.0.0.1:5002/api/v0/version

# Check Foundry
forge --version && cast --version && anvil --version

# Check Anvil
curl -s -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545
```

## 🎯 Expected Output

After successful completion, you should see:

1. **Ingestion**: Row count and Parquet files in `/tmp/eth_tx/`
2. **JSONL**: Converted files in `/tmp/eth_tx_jsonl/`
3. **IPFS**: CID and gateway URL (e.g., `http://127.0.0.1:8081/ipfs/Qm...`)
4. **NFT**: Transaction hash and tokenURI verification
5. **Verification**: Confirmed `ipfs://<CID>` on-chain

## 📸 Screenshots to Take

1. IPFS gateway showing the JSONL content
2. TokenURI verification output showing `ipfs://<CID>`
3. Transaction details from Anvil or explorer

## 🔄 Stretch Goals

- Swap local IPFS for Pinata pinning (persistent CID)
- Point to testnet RPC (Sepolia) with explorer links
- Add Spark transformations (group-by KPIs) before JSONL export
- Implement data validation and error handling
- Add monitoring and logging

## 📄 License

This project is for demonstration purposes. Please ensure you comply with Etherscan's API terms of service and any applicable regulations when using this code.
