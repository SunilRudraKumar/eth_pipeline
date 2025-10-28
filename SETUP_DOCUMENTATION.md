## Setup Documentation

This document provides a formal, step‑by‑step guide to set up and run the Ethereum Data Pipeline Demo from a clean macOS environment.

### Scope
- Ingest Ethereum data from Etherscan using PySpark
- Export compact JSONL
- Pin content to IPFS (Kubo)
- Mint an ERC‑721 with tokenURI = ipfs://<CID> on a local chain (Anvil)
- Optional: Start a web UI to visualize artifacts

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
| Docker Desktop | 4.x | Ensure Docker Engine is running |
| IPFS Kubo (container) | ipfs/kubo:latest (v0.29.x tested) | Pulled and run by setup script |
| Foundry (forge/cast/anvil) | Latest stable | Install via foundryup |
| Flask (UI) | 2.3.3 | In `ui/requirements.txt` |
| Flask‑CORS (UI) | 4.0.0 | In `ui/requirements.txt` |

## Network Ports

| Service | Host Port | Container/Internal |
|---|---:|---|
| Anvil RPC | 8545 | N/A |
| IPFS API | 5002 | 5001 (container) |
| IPFS Gateway | 8081 | 8080 (container) |
| IPFS Swarm | 4002 | 4001 (container) |
| UI (Flask) | 5001 | N/A |

## Environment Variables

Create `.env` in the repository root (copy from `env.example`) and set values as needed:

| Variable | Required | Example | Purpose |
|---|---|---|---|
| ETHERSCAN_API_KEY | Yes | AAAAA... | Etherscan API authentication |
| RPC_URL | Yes | http://127.0.0.1:8545 | JSON‑RPC endpoint (Anvil/Testnet) |
| PRIVATE_KEY | Yes | 0x… | Signer for mint/deploy (use Anvil key locally) |
| NFT_ADDR | Yes (post‑deploy) | 0x… | Deployed ERC‑721 contract address |
| RECIPIENT | Yes | 0x… | Recipient address to mint the token |
| IPFS_API_URL | Optional | http://127.0.0.1:5002 | IPFS API endpoint |
| IPFS_GATEWAY_URL | Optional | http://127.0.0.1:8081 | IPFS Gateway endpoint |

Notes
- `env.example` includes placeholders; replace with your values before use.
- UI startup (`ui/start_ui.sh`) falls back to a demo Etherscan key if none is provided; use your own key for real runs.

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

- Docker is running: `docker ps`
- IPFS API: `curl -s -X POST http://127.0.0.1:5002/api/v0/version`
- Foundry tools available: `forge --version && cast --version && anvil --version`
- Anvil reachable: `curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://127.0.0.1:8545`
- Pipeline created:
  - Parquet in `/tmp/eth_tx/`
  - JSONL in `/tmp/eth_tx_jsonl/`
  - CID printed and accessible via `http://127.0.0.1:8081/ipfs/<CID>`
  - Mint transaction hash printed
  - `tokenURI` matches `ipfs://<CID>`

## Troubleshooting

- PySpark not found
```bash
python -m pip install --user pyspark requests
```
- Java errors / Spark failing to start
  - Ensure `JAVA_HOME` points to JDK 17: `export JAVA_HOME="$(/usr/libexec/java_home -v 17)"`
- IPFS API 405/Connection refused
  - Ensure the Kubo container is running: `docker ps | grep ipfs-kubo`
  - Start: `docker run -d --name ipfs-kubo -p 4002:4001 -p 5002:5001 -p 8081:8080 ipfs/kubo:latest`
- `cast`/`forge`/`anvil` not found
  - Run `foundryup` then `source ~/.zshrc`
- Empty dataset / few transactions
  - Increase `--max-pages` or choose a more active address
- Mint fails due to signing
  - Verify `PRIVATE_KEY`, `RPC_URL`, `NFT_ADDR`, `RECIPIENT` are exported in the same shell

## Security and Operational Notes

- Do not commit real secrets. `.env` should remain local.
- Keys printed by Anvil are for local development only; never reuse in production.
- If targeting testnets, set `RPC_URL` accordingly and consider using a funded test key.

### Using Sepolia Testnet

To run the full pipeline and deploy/mint on Sepolia instead of a local Anvil chain:

1) Prepare environment
```bash
cp env.example .env
# Edit .env to set:
#   RPC_URL=https://sepolia.infura.io/v3/<PROJECT_ID>
#   CHAIN_ID=11155111
#   PRIVATE_KEY=<your_sepolia_private_key_with_test_ETH>
#   RECIPIENT=<your_wallet_address>
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
```

2) Fund your `PRIVATE_KEY` wallet with Sepolia ETH
- Use an official faucet (search for "Sepolia faucet").

3) Deploy the ERC‑721 to Sepolia
```bash
./scripts/deploy_nft.sh
# This prints the deployed address and exports NFT_ADDR
```

4) Run the pipeline against Sepolia
```bash
# Ingestion will target Sepolia by passing CHAIN_ID=11155111 to Etherscan v2
export CHAIN_ID=11155111
./scripts/run_pipeline.sh                    # default address & 5 pages
./scripts/run_pipeline.sh <address> <pages>  # custom parameters
```

Notes
- Ensure `ETHERSCAN_API_KEY` is set; the ingestion uses Etherscan v2 with `chainid=11155111`.
- All on‑chain actions (deploy/mint/verify tokenURI) use `RPC_URL` and your `PRIVATE_KEY` on Sepolia.

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
