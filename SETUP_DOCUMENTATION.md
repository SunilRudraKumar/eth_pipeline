## Setup Documentation

This document provides a formal, step‑by‑step guide to set up and run the Ethereum Data Pipeline Demo from a clean macOS environment.

### Scope
- Ingest Ethereum data from Etherscan using PySpark (supports Sepolia testnet)
- Export compact JSONL
- Generate visual chart from transaction data
- Pin content to IPFS (Pinata or local Kubo)
- Deploy and mint ERC‑721 NFT with tokenURI = ipfs://<CID> on Sepolia testnet or local chain (Anvil)
- Web UI to orchestrate and visualize pipeline stages

## Supported Platform
- macOS: 14 (Sonoma) and 15 (Sequoia) verified
- Apple Silicon and Intel supported

## Version Requirements and Recommendations

| Component | Version (verified) | Notes |
|---|---|---|
| Python | 3.11.x (3.7+ supported) | Recommend 3.10–3.12 |
| Java (JDK) | OpenJDK 17.x | Required by PySpark |
| PySpark | 3.5.x | Installed via pip |
| requests (Py) | 2.31.0 | Installed via pip |
| matplotlib (Py) | 3.8.x | For chart generation |
| pandas (Py) | 2.1.x | For data processing |
| Docker Desktop | 4.x | Optional (only for local IPFS) |
| IPFS Kubo (container) | ipfs/kubo:latest (v0.29.x tested) | Optional (Pinata recommended) |
| Foundry (forge/cast/anvil) | Latest stable | Install via foundryup |
| Flask (UI) | 2.3.3 | In `ui/requirements.txt` |
| Flask‑CORS (UI) | 4.0.0 | In `ui/requirements.txt` |

## Network Ports

| Service | Host Port | Container/Internal | Notes |
|---|---:|---|---|
| Anvil RPC | 8545 | N/A | Local development only |
| IPFS API (Kubo) | 5002 | 5001 (container) | Optional (if not using Pinata) |
| IPFS Gateway (Kubo) | 8081 | 8080 (container) | Optional (if not using Pinata) |
| IPFS Swarm (Kubo) | 4002 | 4001 (container) | Optional (if not using Pinata) |
| UI (Flask) | 5001 | N/A | Web interface for pipeline |
| Sepolia RPC | 443 (HTTPS) | N/A | External (Infura/Alchemy) |
| Pinata API | 443 (HTTPS) | N/A | External (api.pinata.cloud) |

## Environment Variables

Create `.env` in the repository root (copy from `env.example`) and set values as needed:

| Variable | Required | Example | Purpose |
|---|---|---|---|
| ETHERSCAN_API_KEY | Yes | AAAAA... | Etherscan API authentication |
| CHAIN_ID | Optional | 11155111 | Chain ID for Etherscan v2 API (default: 1 for mainnet, use 11155111 for Sepolia) |
| RPC_URL | Yes | http://127.0.0.1:8545 or https://sepolia.infura.io/v3/... | JSON‑RPC endpoint (Anvil/Sepolia/Testnet) |
| PRIVATE_KEY | Yes | 0x… | Signer for mint/deploy (use Anvil key locally or funded Sepolia key) |
| NFT_ADDR | Yes (post‑deploy) | 0x… | Deployed ERC‑721 contract address |
| RECIPIENT | Yes | 0x… | Recipient address to mint the token |
| PINATA_JWT | Optional | eyJ... | Pinata JWT token for IPFS pinning (recommended for Sepolia) |
| IPFS_API_URL | Optional | http://127.0.0.1:5002 | IPFS API endpoint (local Kubo only) |
| IPFS_GATEWAY_URL | Optional | https://gateway.pinata.cloud | IPFS Gateway endpoint |

Notes
- `env.example` includes placeholders; replace with your values before use.
- UI startup (`ui/start_ui.sh`) falls back to a demo Etherscan key if none is provided; use your own key for real runs.

## Pinata Configuration

Pinata is the recommended IPFS provider for Sepolia deployments as it doesn't require Docker or local infrastructure.

### Setting Up Pinata

1. **Create Account**
   - Visit [pinata.cloud](https://pinata.cloud)
   - Sign up for a free account
   - Verify your email address

2. **Generate JWT Token**
   - Log in to Pinata dashboard
   - Navigate to "API Keys" section
   - Click "New Key" button
   - Configure permissions:
     - Enable `pinFileToIPFS` (required)
     - Optionally enable `pinJSONToIPFS`
     - Set a descriptive name (e.g., "Sepolia NFT Pipeline")
   - Click "Create Key"
   - **Important**: Copy the JWT token immediately (starts with `eyJ...`)
   - Store it securely - you won't be able to see it again

3. **Configure Environment**
   ```bash
   export PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   export IPFS_GATEWAY_URL=https://gateway.pinata.cloud
   ```

4. **Test Authentication**
   ```bash
   curl -s -H "Authorization: Bearer $PINATA_JWT" \
     https://api.pinata.cloud/data/testAuthentication
   ```
   
   Expected response:
   ```json
   {"message":"Congratulations! You are communicating with the Pinata API!"}
   ```

### Pinata Free Tier Limits

- **Storage**: 1 GB
- **Bandwidth**: 100 GB/month
- **Requests**: 180 requests/minute
- **File Size**: 100 MB per file

These limits are sufficient for most development and testing scenarios.

### Alternative: Local IPFS

If you prefer not to use Pinata, you can run local IPFS Kubo:

```bash
docker run -d --name ipfs-kubo \
  -p 4002:4001 -p 5002:5001 -p 8081:8080 \
  ipfs/kubo:latest

export IPFS_API_URL=http://127.0.0.1:5002
export IPFS_GATEWAY_URL=http://127.0.0.1:8081
```

Note: Local IPFS pins are not persistent across container restarts unless you mount a volume.

## Prerequisites Installation (macOS)

1) Command Line Tools and Homebrew
```bash
xcode-select --install || true
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2) Python 3.11 and virtual environment (recommended)
```bash
brew install python@3.11
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

3) Java JDK 17 (for PySpark)
```bash
brew install openjdk@17
sudo ln -sfn $(brew --prefix openjdk@17)/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
```
Add to your shell profile (`~/.zshrc`):
```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export PATH="$HOME/.local/bin:$PATH"
```

4) Docker Desktop
- Install from Docker website and start the Docker engine
- Validate: `docker ps`

5) Foundry (forge, cast, anvil)
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
source ~/.zshrc
forge --version && cast --version && anvil --version
```

## Repository Setup

1) Clone repository and enter directory
```bash
git clone <your_fork_or_repo_url> pipeline_demo
cd pipeline_demo
```

2) Configure environment
```bash
cp env.example .env
# Edit .env with your values or export into the current shell
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
```

3) Initial setup checks and IPFS container
```bash
chmod +x scripts/*.sh
./scripts/setup.sh
```
- Ensures Python deps (PySpark, requests)
- Starts `ipfs/kubo:latest` if not running and maps ports (4002, 5002, 8081)
- Verifies Foundry tooling
- Validates required environment variables

## Local Blockchain

1) Start Anvil in a separate terminal
```bash
anvil
```
2) Note the funded accounts and private keys printed by Anvil (you can use one as `PRIVATE_KEY`).

## Deploy ERC‑721 Contract (if needed)

If you do not already have `NFT_ADDR`, deploy the included `Simple721.sol` locally:
```bash
export RPC_URL=http://127.0.0.1:8545
export PRIVATE_KEY=<anvil_private_key>
./scripts/deploy_nft.sh
```
- The script stores the deployed address in `/tmp/nft_address.env` and appends an export to `~/.zshrc`.
- Set `RECIPIENT` to an address you control (e.g., the first Anvil account):
```bash
export RECIPIENT=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

## Run the Complete Pipeline

With prerequisites satisfied and `NFT_ADDR` available, run:
```bash
./scripts/run_pipeline.sh                    # default address & 5 pages
./scripts/run_pipeline.sh <address> <pages>  # custom parameters
```
This executes:
- Etherscan ingestion → Parquet (`/tmp/eth_tx`)
- Convert Parquet → JSONL (`/tmp/eth_tx_jsonl`)
- Pin JSONL to IPFS → capture CID
- Mint NFT with `tokenURI = ipfs://<CID>`
- Verify on‑chain tokenURI

## Manual Execution (Advanced)

1) Ingest with PySpark
```bash
python3 etherscan_ingest.py \
  --address 0x742d35Cc6634C0532925a3b844Bc454e4438f44e \
  --action txlist --page-size 100 --max-pages 5 --rps 5 \
  --output parquet:/tmp/eth_tx
```

2) Convert Parquet → JSONL
```bash
./scripts/convert_to_jsonl.sh /tmp/eth_tx /tmp/eth_tx_jsonl 200
```

3) Pin to IPFS and capture CID
```bash
./scripts/pin.sh /tmp/eth_tx_jsonl
# CID is exported to /tmp/ipfs_cid.env and printed as gateway URL
```

4) Mint NFT using CID
```bash
./scripts/mint.sh
```

5) Verify tokenURI
```bash
./scripts/verify.sh            # auto‑detects latest token id
./scripts/verify.sh 1          # or specify a token id
```

## Start the Web UI (Optional)

1) Install UI dependencies and start server
```bash
cd ui
./start_ui.sh
# Access: http://localhost:5001
```
2) The script sets reasonable defaults (RPC, demo key, recipient). For production/demo integrity, provide your own `ETHERSCAN_API_KEY`, `PRIVATE_KEY`, and `NFT_ADDR` before starting.

## Validation Checklist

### Local Development Checklist

- [ ] Docker is running: `docker ps`
- [ ] IPFS API: `curl -s -X POST http://127.0.0.1:5002/api/v0/version`
- [ ] Foundry tools available: `forge --version && cast --version && anvil --version`
- [ ] Anvil reachable: `curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545`
- [ ] Pipeline created:
  - Parquet in `/tmp/eth_tx/`
  - JSONL in `/tmp/eth_tx_jsonl/`
  - Chart image in `/tmp/eth_tx_chart.png`
  - CID printed and accessible via `http://127.0.0.1:8081/ipfs/<CID>`
  - Mint transaction hash printed
  - `tokenURI` matches `ipfs://<CID>`

### Sepolia Deployment Checklist

- [ ] Environment variables configured:
  - `ETHERSCAN_API_KEY` set
  - `CHAIN_ID=11155111` set
  - `RPC_URL` points to Sepolia endpoint
  - `PRIVATE_KEY` set (wallet with testnet ETH)
  - `RECIPIENT` set to your wallet address
  - `PINATA_JWT` set (if using Pinata)
- [ ] Foundry tools installed: `forge --version && cast --version`
- [ ] Sepolia RPC accessible: `cast block-number --rpc-url $RPC_URL`
- [ ] Wallet has sufficient balance: `cast balance $RECIPIENT --rpc-url $RPC_URL`
  - Should show at least 100000000000000000 Wei (0.1 ETH)
- [ ] Pinata authentication works: `curl -s -H "Authorization: Bearer $PINATA_JWT" https://api.pinata.cloud/data/testAuthentication`
- [ ] Contract deployed successfully:
  - Address saved in `/tmp/nft_address.env`
  - Visible on Sepolia Etherscan
- [ ] Pipeline execution completed:
  - Parquet data ingested from Sepolia addresses
  - JSONL conversion successful
  - Chart image generated
  - Image uploaded to Pinata (CID received)
  - Metadata uploaded to Pinata (CID received)
  - NFT minted successfully
  - Transaction confirmed on Sepolia
- [ ] NFT verification:
  - `tokenURI` returns `ipfs://<metadata_CID>`
  - Metadata accessible via IPFS gateway
  - Image accessible via IPFS gateway
  - NFT visible on OpenSea testnet (may take a few minutes)

## Troubleshooting

### Python and Dependencies

- **PySpark not found**
  ```bash
  python -m pip install --user pyspark requests matplotlib pandas
  ```

- **matplotlib or pandas not found**
  ```bash
  python -m pip install --user matplotlib pandas
  ```

- **Java errors / Spark failing to start**
  - Ensure `JAVA_HOME` points to JDK 17: `export JAVA_HOME="$(/usr/libexec/java_home -v 17)"`
  - Verify Java version: `java -version` (should show 17.x)

### IPFS Issues

- **IPFS API 405/Connection refused (Local Kubo)**
  - Ensure the Kubo container is running: `docker ps | grep ipfs-kubo`
  - Start: `docker run -d --name ipfs-kubo -p 4002:4001 -p 5002:5001 -p 8081:8080 ipfs/kubo:latest`

- **Pinata authentication failed**
  - Verify JWT token is correct: `echo $PINATA_JWT`
  - Test authentication: `curl -s -H "Authorization: Bearer $PINATA_JWT" https://api.pinata.cloud/data/testAuthentication`
  - Ensure token has `pinFileToIPFS` permission
  - Check for extra spaces or quotes in the token

- **Pinata rate limit exceeded**
  - Free tier: 180 requests/minute
  - Wait 60 seconds before retrying
  - Consider upgrading Pinata plan

- **File too large for Pinata**
  - Free tier limit: 100 MB per file
  - Reduce `--max-pages` to limit data size
  - Use `--limit` parameter in conversion step

- **IPFS gateway timeout**
  - Content may take a few seconds to propagate
  - Try alternative gateway: `https://ipfs.io/ipfs/<CID>`
  - Check Pinata dashboard for pin status

### Blockchain Issues

- **`cast`/`forge`/`anvil` not found**
  - Run `foundryup` then `source ~/.zshrc`
  - Verify installation: `forge --version && cast --version`

- **Sepolia RPC connection failed**
  - Verify RPC URL is correct
  - Test connection: `cast block-number --rpc-url $RPC_URL`
  - Check Infura/Alchemy dashboard for API key status
  - Ensure no firewall blocking the connection

- **Insufficient funds on Sepolia**
  - Check balance: `cast balance $RECIPIENT --rpc-url $RPC_URL`
  - Get testnet ETH from faucets (see Sepolia Testnet Setup section)
  - Need at least 0.1 SepoliaETH for deployment and minting

- **Transaction not confirming**
  - Sepolia can be slow during high usage
  - Wait 30-60 seconds for confirmation
  - Check transaction on Sepolia Etherscan
  - Verify gas price is sufficient

- **Mint fails due to signing**
  - Verify `PRIVATE_KEY`, `RPC_URL`, `NFT_ADDR`, `RECIPIENT` are exported in the same shell
  - Ensure private key has `0x` prefix
  - Check wallet has sufficient balance

### Data Issues

- **Empty dataset / few transactions**
  - Increase `--max-pages` or choose a more active address
  - For Sepolia, use addresses with known activity
  - Verify `CHAIN_ID=11155111` is set for Sepolia ingestion

- **Image generation failed**
  - Ensure JSONL file exists and is not empty
  - Check matplotlib is installed: `python -c "import matplotlib"`
  - Verify file permissions on `/tmp/` directory

### Environment Issues

- **Environment variables not persisting**
  - Use `.env` file and source it: `export $(grep -v '^#' .env | xargs)`
  - Add exports to `~/.zshrc` for persistence
  - Verify in current shell: `echo $VARIABLE_NAME`

- **CHAIN_ID not recognized**
  - Ensure `CHAIN_ID=11155111` for Sepolia
  - Pass explicitly to ingestion script: `--chain-id 11155111`
  - Verify Etherscan API supports the chain ID

## Security and Operational Notes

- Do not commit real secrets. `.env` should remain local.
- Keys printed by Anvil are for local development only; never reuse in production.
- If targeting testnets, set `RPC_URL` accordingly and consider using a funded test key.

## Sepolia Testnet Setup

The pipeline fully supports Sepolia testnet for production-like NFT minting without local blockchain setup.

### Prerequisites for Sepolia

1. **Sepolia RPC Endpoint**
   - Get a free RPC URL from [Infura](https://infura.io), [Alchemy](https://alchemy.com), or [Ankr](https://ankr.com)
   - Example: `https://sepolia.infura.io/v3/YOUR_PROJECT_ID`

2. **Sepolia Testnet ETH**
   
   Get free testnet ETH from these faucets:
   - [Alchemy Sepolia Faucet](https://sepoliafaucet.com/)
   - [Infura Sepolia Faucet](https://www.infura.io/faucet/sepolia)
   - [QuickNode Sepolia Faucet](https://faucet.quicknode.com/ethereum/sepolia)
   - [Chainlink Sepolia Faucet](https://faucets.chain.link/sepolia)
   
   You'll need approximately 0.1 SepoliaETH for contract deployment and minting.

3. **Pinata Account** (Recommended)
   
   Pinata provides persistent IPFS pinning without Docker:
   - Sign up at [pinata.cloud](https://pinata.cloud)
   - Navigate to API Keys → New Key
   - Enable `pinFileToIPFS` permission
   - Copy the JWT token (starts with `eyJ...`)
   - Free tier includes 1GB storage and 100GB bandwidth

### Sepolia Environment Configuration

1) Prepare environment file
```bash
cp env.example .env
# Edit .env to set:
#   ETHERSCAN_API_KEY=your_etherscan_api_key
#   CHAIN_ID=11155111
#   RPC_URL=https://sepolia.infura.io/v3/<PROJECT_ID>
#   PRIVATE_KEY=<your_sepolia_private_key_with_test_ETH>
#   RECIPIENT=<your_wallet_address>
#   PINATA_JWT=<your_pinata_jwt_token>
#   IPFS_GATEWAY_URL=https://gateway.pinata.cloud
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
```

2) Verify Sepolia connection
```bash
cast block-number --rpc-url $RPC_URL
# Should return current Sepolia block number
```

3) Check wallet balance
```bash
cast balance $RECIPIENT --rpc-url $RPC_URL
# Should show balance in Wei (need at least 100000000000000000 Wei = 0.1 ETH)
```

### Deploy ERC‑721 to Sepolia

```bash
./scripts/deploy_nft.sh
# This compiles the contract, deploys to Sepolia, and saves the address
# Contract address is saved to /tmp/nft_address.env
```

Expected output:
```
Deploying Simple721 to Sepolia...
Deployed to: 0x1234567890abcdef1234567890abcdef12345678
Transaction hash: 0xabcdef...
Saved to /tmp/nft_address.env
```

### Run Pipeline on Sepolia

```bash
# Ingestion will target Sepolia by passing CHAIN_ID=11155111 to Etherscan v2
export CHAIN_ID=11155111
./scripts/run_pipeline.sh                    # default address & 5 pages
./scripts/run_pipeline.sh <address> <pages>  # custom parameters
```

The pipeline will:
1. Ingest Sepolia transaction data via Etherscan API v2
2. Convert to JSONL and generate chart image
3. Upload image and metadata to Pinata IPFS
4. Mint NFT on Sepolia with IPFS metadata URI

### Verify on Sepolia

After minting, verify your NFT:

1. **Check transaction on Sepolia Etherscan**:
   ```
   https://sepolia.etherscan.io/tx/<transaction_hash>
   ```

2. **View contract on Sepolia Etherscan**:
   ```
   https://sepolia.etherscan.io/address/<contract_address>
   ```

3. **View NFT on OpenSea Testnet**:
   ```
   https://testnets.opensea.io/assets/sepolia/<contract_address>/<token_id>
   ```

4. **Verify tokenURI on-chain**:
   ```bash
   cast call $NFT_ADDR "tokenURI(uint256)" <token_id> --rpc-url $RPC_URL
   ```

### Notes

- Ensure `ETHERSCAN_API_KEY` is set; the ingestion uses Etherscan v2 with `chainid=11155111`
- All on‑chain actions (deploy/mint/verify tokenURI) use `RPC_URL` and your `PRIVATE_KEY` on Sepolia
- Sepolia transactions may take 15-30 seconds to confirm
- IPFS content may take a few seconds to propagate to gateways

## Appendix

- Data directories used by scripts:
  - Parquet: `/tmp/eth_tx/`
  - JSONL: `/tmp/eth_tx_jsonl/`
  - IPFS add response: `/tmp/ipfs_add.json`
  - Exported variables: `/tmp/ipfs_cid.env`, `/tmp/mint_tx.env`, `/tmp/nft_address.env`

- Useful commands
```bash
# Export all variables from .env into current shell
export $(grep -v '^#' .env | xargs)

# Show Anvil accounts again
anvil --accounts 10 --balance 1000
```
