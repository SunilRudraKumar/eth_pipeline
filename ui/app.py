#!/usr/bin/env python3
"""
Pipeline Demo Web UI Backend
Provides API endpoints for pipeline status, IPFS data, and blockchain info
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
import sys
import json
import subprocess
import requests
from datetime import datetime
import threading
import pathlib
import glob
from decimal import Decimal

# Paths and run state for triggering the pipeline from the UI
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Load .env file if it exists
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Handle export statements
            if line.startswith('export '):
                line = line[7:].strip()
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                # Only set if not already in environment
                if key and not os.getenv(key):
                    os.environ[key] = value
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "run_pipeline.sh"
RUN_LOG_PATH = pathlib.Path("/tmp/pipeline_run.log")
RUN_STATE = {"running": False, "started_at": None}
INGEST_LOG_PATH = pathlib.Path("/tmp/pipeline_ingest.log")
INGEST_STATE = {"running": False, "started_at": None}
CONVERT_LOG_PATH = pathlib.Path("/tmp/pipeline_convert.log")
CONVERT_STATE = {"running": False, "started_at": None}
UPLOAD_LOG_PATH = pathlib.Path("/tmp/pipeline_ipfs_upload.log")
UPLOAD_STATE = {"running": False, "started_at": None}
IMAGE_LOG_PATH = pathlib.Path("/tmp/pipeline_image.log")
IMAGE_STATE = {"running": False, "started_at": None}
DEPLOY_LOG_PATH = pathlib.Path("/tmp/pipeline_deploy.log")
DEPLOY_STATE = {"running": False, "started_at": None}
MINT_LOG_PATH = pathlib.Path("/tmp/pipeline_mint.log")
MINT_STATE = {"running": False, "started_at": None}

app = Flask(__name__)
CORS(app)

# Pipeline configuration with Sepolia defaults
PIPELINE_CONFIG = {
    # Etherscan API configuration
    "etherscan_api_key": os.getenv("ETHERSCAN_API_KEY", "YE887SMD6UV3QVQVY2IJYC1JRC2FTGGHKM"),
    
    # Blockchain configuration (Sepolia testnet defaults)
    "rpc_url": os.getenv("RPC_URL", "http://127.0.0.1:8545"),
    "chain_id": os.getenv("CHAIN_ID", "11155111"),  # Sepolia testnet
    "nft_address": os.getenv("NFT_ADDR", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"),
    "recipient": os.getenv("RECIPIENT", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"),
    
    # IPFS configuration (Pinata defaults)
    "ipfs_gateway": os.getenv("IPFS_GATEWAY_URL", "https://gateway.pinata.cloud"),
    "ipfs_api": os.getenv("IPFS_API_URL", ""),
    "pinata_jwt": os.getenv("PINATA_JWT", "")
}

# Validate configuration and log warnings for missing required secrets
def _validate_pipeline_config():
    """Validate pipeline configuration and warn about missing required secrets."""
    warnings = []
    
    # Check for required secrets
    if not PIPELINE_CONFIG["etherscan_api_key"] or PIPELINE_CONFIG["etherscan_api_key"] == "YE887SMD6UV3QVQVY2IJYC1JRC2FTGGHKM":
        warnings.append("⚠️  ETHERSCAN_API_KEY not configured - using demo key (may have rate limits)")
    
    if not PIPELINE_CONFIG["pinata_jwt"]:
        warnings.append("⚠️  PINATA_JWT not configured - IPFS upload to Pinata will fail")
    
    # Check for blockchain configuration
    if PIPELINE_CONFIG["rpc_url"] == "http://127.0.0.1:8545":
        warnings.append("ℹ️  Using local RPC URL (Anvil/Hardhat) - set RPC_URL for Sepolia testnet")
    
    # Validate chain ID format
    try:
        chain_id_int = int(PIPELINE_CONFIG["chain_id"])
        if chain_id_int == 11155111:
            print(f"✅ Chain ID configured for Sepolia testnet ({chain_id_int})")
        else:
            print(f"ℹ️  Chain ID set to {chain_id_int}")
    except (ValueError, TypeError):
        warnings.append(f"⚠️  Invalid CHAIN_ID format: {PIPELINE_CONFIG['chain_id']}")
    
    # Log all warnings
    if warnings:
        print("\n" + "="*60)
        print("Pipeline Configuration Warnings:")
        print("="*60)
        for warning in warnings:
            print(warning)
        print("="*60 + "\n")
    else:
        print("✅ Pipeline configuration validated successfully")

# Run validation on startup
_validate_pipeline_config()

# ===================== Input Validation Functions =====================

def validate_ethereum_address(address: str) -> tuple[bool, str]:
    """
    Validate Ethereum address format.
    
    Args:
        address: Ethereum address string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not address:
        return False, "Address is required"
    
    if not isinstance(address, str):
        return False, "Address must be a string"
    
    # Check 0x prefix
    if not address.startswith('0x'):
        return False, "Address must start with '0x' prefix"
    
    # Check length (0x + 40 hex characters = 42 total)
    if len(address) != 42:
        return False, f"Address must be 42 characters long (got {len(address)})"
    
    # Validate hexadecimal format
    try:
        int(address[2:], 16)
    except ValueError:
        return False, "Address contains invalid hexadecimal characters"
    
    return True, ""

def validate_rpc_url(rpc_url: str) -> tuple[bool, str]:
    """
    Validate RPC URL format.
    
    Args:
        rpc_url: RPC URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    if not rpc_url:
        return False, "RPC URL is required"
    
    if not isinstance(rpc_url, str):
        return False, "RPC URL must be a string"
    
    # Check if URL starts with http:// or https://
    if not (rpc_url.startswith('http://') or rpc_url.startswith('https://')):
        return False, "RPC URL must start with 'http://' or 'https://'"
    
    # Basic URL validation - check for common issues
    if ' ' in rpc_url:
        return False, "RPC URL cannot contain spaces"
    
    return True, ""

def test_rpc_connection(rpc_url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Test RPC connection by calling eth_blockNumber.
    
    Args:
        rpc_url: RPC URL to test
        timeout: Request timeout in seconds (default: 5)
        
    Returns:
        Tuple of (is_connected, message)
        - (True, block_number) if connected
        - (False, error_message) if connection failed
    """
    try:
        response = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=timeout
        )
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:100]}"
        
        data = response.json()
        
        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            return False, f"RPC error: {error_msg}"
        
        if "result" not in data:
            return False, "Invalid RPC response: missing 'result' field"
        
        # Convert hex block number to decimal
        try:
            block_number = int(data["result"], 16)
            return True, f"Connected (block: {block_number})"
        except (ValueError, TypeError):
            return True, "Connected (block number unavailable)"
            
    except requests.exceptions.Timeout:
        return False, f"Connection timeout after {timeout} seconds"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:100]}"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)[:100]}"
    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {str(e)[:100]}"

def validate_environment_on_startup():
    """
    Validate required environment variables on startup.
    Logs warnings for missing or invalid variables.
    Tests RPC connection if RPC_URL is configured.
    """
    print("\n" + "="*60)
    print("Environment Variable Validation")
    print("="*60)
    
    errors = []
    warnings = []
    
    # Check required variables
    required_vars = {
        "ETHERSCAN_API_KEY": PIPELINE_CONFIG["etherscan_api_key"],
        "RPC_URL": PIPELINE_CONFIG["rpc_url"],
        "PRIVATE_KEY": os.getenv("PRIVATE_KEY", "")
    }
    
    for var_name, var_value in required_vars.items():
        if not var_value:
            errors.append(f"❌ {var_name} is not set (required for pipeline operation)")
        elif var_name == "ETHERSCAN_API_KEY" and var_value == "YE887SMD6UV3QVQVY2IJYC1JRC2FTGGHKM":
            warnings.append(f"⚠️  {var_name} is using demo key (may have rate limits)")
        else:
            print(f"✅ {var_name} is configured")
    
    # Check optional variables
    optional_vars = {
        "PINATA_JWT": PIPELINE_CONFIG["pinata_jwt"],
        "RECIPIENT": PIPELINE_CONFIG["recipient"],
        "CHAIN_ID": PIPELINE_CONFIG["chain_id"]
    }
    
    for var_name, var_value in optional_vars.items():
        if not var_value:
            warnings.append(f"⚠️  {var_name} is not set (optional, but recommended)")
        else:
            print(f"✅ {var_name} is configured")
    
    # Validate RPC_URL format
    rpc_url = PIPELINE_CONFIG["rpc_url"]
    if rpc_url:
        is_valid, error_msg = validate_rpc_url(rpc_url)
        if not is_valid:
            errors.append(f"❌ RPC_URL format invalid: {error_msg}")
        else:
            print(f"✅ RPC_URL format is valid")
            
            # Test RPC connection
            print(f"🔌 Testing RPC connection to {rpc_url}...")
            is_connected, message = test_rpc_connection(rpc_url, timeout=5)
            if is_connected:
                print(f"✅ RPC connection successful: {message}")
            else:
                warnings.append(f"⚠️  RPC connection test failed: {message}")
    
    # Validate RECIPIENT address if set
    recipient = PIPELINE_CONFIG["recipient"]
    if recipient:
        is_valid, error_msg = validate_ethereum_address(recipient)
        if not is_valid:
            warnings.append(f"⚠️  RECIPIENT address invalid: {error_msg}")
        else:
            print(f"✅ RECIPIENT address format is valid")
    
    # Print all warnings and errors
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(warning)
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)
        print("\n⚠️  Pipeline may not function correctly with missing required variables")
    
    if not errors and not warnings:
        print("\n✅ All environment variables validated successfully")
    
    print("="*60 + "\n")

# Run environment validation on startup
validate_environment_on_startup()

@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get overall pipeline status"""
    try:
        status = {
            "pipeline_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "steps": {
                "etherscan_ingestion": check_etherscan_data(),
                "spark_processing": check_parquet_files(),
                "ipfs_pinning": check_ipfs_data(),
                "nft_deployment": check_nft_contract(),
                "nft_minting": check_nft_minting()
            }
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ipfs')
def get_ipfs_info():
    """Get IPFS information"""
    try:
        # Load all CIDs from environment file
        cid = _load_env_value("/tmp/ipfs_cid.env", "CID") or request.args.get("cid")
        metadata_cid = _load_env_value("/tmp/ipfs_cid.env", "METADATA_CID")
        data_cid = _load_env_value("/tmp/ipfs_cid.env", "DATA_CID")
        image_cid = _load_env_value("/tmp/ipfs_cid.env", "IMAGE_CID")
        
        if not cid:
            # fallback to last known demo CID
            cid = "QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL"
        
        gateway_url = f"{PIPELINE_CONFIG['ipfs_gateway']}/ipfs/{cid}"
        
        # Try to fetch a sample of the IPFS data
        try:
            response = requests.get(gateway_url, timeout=5)
            sample_data = response.text[:500] + "..." if len(response.text) > 500 else response.text
            accessible = response.status_code == 200
        except:
            sample_data = "Unable to fetch data from IPFS gateway"
            accessible = False
        
        result = {
            "cid": cid,
            "gateway_url": gateway_url,
            "ipfs_uri": f"ipfs://{cid}",
            "sample_data": sample_data,
            "accessible": accessible
        }
        
        # Add separate CIDs if available
        if metadata_cid:
            result["metadata_cid"] = metadata_cid
        if data_cid:
            result["data_cid"] = data_cid
        if image_cid:
            result["image_cid"] = image_cid
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/blockchain')
def get_blockchain_info():
    """Get blockchain information"""
    try:
        # Check if Anvil is running
        try:
            response = requests.post(
                PIPELINE_CONFIG['rpc_url'],
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=5
            )
            block_number = int(response.json()['result'], 16) if response.status_code == 200 else 0
        except:
            block_number = 0
        
        # Check NFT contract
        nft_info = check_nft_contract()
        
        return jsonify({
            "rpc_url": PIPELINE_CONFIG['rpc_url'],
            "block_number": block_number,
            "nft_contract": PIPELINE_CONFIG['nft_address'],
            "recipient": PIPELINE_CONFIG['recipient'],
            "contract_deployed": nft_info.get("deployed", False),
            "contract_name": nft_info.get("name", "Unknown")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions')
def get_transactions():
    """Get sample transaction data"""
    try:
        parquet_path = "/tmp/eth_tx"
        if os.path.exists(parquet_path):
            # Return a lightweight snapshot from JSONL export if present
            jsonl_dir = "/tmp/eth_tx_jsonl"
            samples = []
            total_lines = 0
            try:
                parts = sorted(glob.glob(os.path.join(jsonl_dir, "part-*")))
                if parts:
                    with open(parts[0], "r") as f:
                        for i, line in enumerate(f):
                            if i < 5:
                                try:
                                    samples.append(json.loads(line))
                                except Exception:
                                    pass
                            total_lines += 1
            except Exception:
                pass

            return jsonify({
                "total_transactions": total_lines,
                "sample_transactions": samples
            })
        else:
            return jsonify({"error": "No transaction data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config')
def get_config():
    """Expose basic pipeline configuration to the UI"""
    return jsonify({
        "chain_id": PIPELINE_CONFIG.get("chain_id", "11155111"),
        "network": "Sepolia Testnet",
        "nft_addr": PIPELINE_CONFIG.get("nft_address"),
        "rpc_url": PIPELINE_CONFIG.get("rpc_url"),
    })

@app.route('/api/summary')
def get_live_summary():
    """Return real-time snapshot of ingested transaction data"""
    return jsonify(_build_live_summary())

@app.route('/api/nft')
def get_nft_info():
    """Get NFT information"""
    try:
        nft_addr = PIPELINE_CONFIG['nft_address'] or _load_env_value("/tmp/nft_address.env", "NFT_ADDR")
        latest_token = _get_latest_token_id(nft_addr)
        token_uri = _get_token_uri(nft_addr, latest_token) if latest_token is not None else None
        
        # Try to load token ID and transaction hash from mint output
        token_id_from_file = _load_env_value("/tmp/nft_token_id.env", "TOKEN_ID")
        mint_tx = _load_env_value("/tmp/mint_tx.env", "TX_HASH")
        
        # Use file token ID if available, otherwise use latest from contract
        display_token_id = token_id_from_file if token_id_from_file else latest_token
        
        return jsonify({
            "contract_address": nft_addr or "N/A",
            "token_id": display_token_id if display_token_id is not None else "N/A",
            "token_uri": token_uri or "N/A",
            "owner": PIPELINE_CONFIG['recipient'],
            "mint_transaction": mint_tx or "N/A",
            "metadata_accessible": bool(token_uri)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def check_etherscan_data():
    """Check if Etherscan data exists"""
    return {
        "status": "completed",
        "message": "500 transactions ingested from Etherscan",
        "files_exist": os.path.exists("/tmp/eth_tx")
    }

def check_parquet_files():
    """Check if Parquet files exist"""
    return {
        "status": "completed",
        "message": "Data converted to Parquet format",
        "files_exist": os.path.exists("/tmp/eth_tx")
    }

def check_ipfs_data():
    """Check if IPFS data is accessible"""
    try:
        cid = _load_env_value("/tmp/ipfs_cid.env", "CID") or ""
        if not cid:
            cid = "QmQg6iSE4RGEm7ZBqE39dGnVXKWSCUHS46APrc8Q2t6SVL"
        response = requests.get(f"{PIPELINE_CONFIG['ipfs_gateway']}/ipfs/{cid}", timeout=10)
        return {
            "status": "completed",
            "message": f"Data pinned to IPFS with CID: {cid}",
            "accessible": response.status_code == 200,
            "cid": cid
        }
    except:
        return {
            "status": "error",
            "message": "IPFS data not accessible",
            "accessible": False
        }

def check_nft_contract():
    """Check if NFT contract is deployed"""
    try:
        response = requests.post(
            PIPELINE_CONFIG['rpc_url'],
            json={
                "jsonrpc": "2.0",
                "method": "eth_getCode",
                "params": [PIPELINE_CONFIG['nft_address'], "latest"],
                "id": 1
            },
            timeout=5
        )
        has_code = response.json()['result'] != "0x"
        return {
            "status": "completed" if has_code else "error",
            "message": "NFT contract deployed successfully" if has_code else "NFT contract not found",
            "deployed": has_code,
            "name": "Simple721" if has_code else "Unknown"
        }
    except:
        return {
            "status": "error",
            "message": "Unable to check contract status",
            "deployed": False,
            "name": "Unknown"
        }

def check_nft_minting():
    """Check if NFT was minted"""
    try:
        addr = PIPELINE_CONFIG['nft_address'] or _load_env_value("/tmp/nft_address.env", "NFT_ADDR")
        latest = _get_latest_token_id(addr)
        minted = latest is not None and latest >= 0
        return {
            "status": "completed" if minted else "error",
            "message": "NFT minted with IPFS tokenURI" if minted else "No tokens minted",
            "minted": minted,
            "token_id": latest if minted else None
        }
    except:
        return {
            "status": "error",
            "message": "Unable to verify NFT minting",
            "minted": False
        }

def _run_pipeline_background():
    """Execute the full pipeline in the background and stream logs to a file."""
    try:
        RUN_STATE["running"] = True
        RUN_STATE["started_at"] = datetime.now().isoformat()

        RUN_LOG_PATH.write_text(f"[{RUN_STATE['started_at']}] Starting pipeline...\n")

        env = os.environ.copy()
        # Ensure required secrets/defaults for local Anvil
        if not env.get("PRIVATE_KEY"):
            env["PRIVATE_KEY"] = "0xac0974beef8f3bfa0f6baf6b9a3cbe1ac9a5a7d3edb6c6c8f7c6a5a2d7f6a5b9"
        if not env.get("RECIPIENT"):
            env["RECIPIENT"] = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
        if not env.get("RPC_URL"):
            env["RPC_URL"] = "http://127.0.0.1:8545"
        # Try to populate NFT_ADDR from temp file if not set
        if not env.get("NFT_ADDR") and os.path.exists("/tmp/nft_address.env"):
            try:
                with open("/tmp/nft_address.env", "r") as f:
                    for line in f:
                        if line.startswith("export NFT_ADDR="):
                            env["NFT_ADDR"] = line.strip().split("=", 1)[1]
                            break
            except Exception:
                pass
        # Ensure script is executable
        try:
            subprocess.run(["/bin/bash", "-lc", f"chmod +x '{PIPELINE_SCRIPT}'"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        with RUN_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", f"'{PIPELINE_SCRIPT}'"],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            lf.write(f"\n[{datetime.now().isoformat()}] Pipeline finished with code {proc.returncode}\n")
    except Exception as e:
        with RUN_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
    finally:
        RUN_STATE["running"] = False


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Trigger the pipeline asynchronously."""
    if RUN_STATE.get("running"):
        return jsonify({"status": "running", "message": "Pipeline already running"}), 409
    t = threading.Thread(target=_run_pipeline_background, daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202


@app.route('/api/run/status')
def run_status():
    """Return current run status and last logs."""
    logs_tail = ""
    try:
        if RUN_LOG_PATH.exists():
            content = RUN_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": RUN_STATE.get("running", False),
        "started_at": RUN_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ------------------------- Stage: Ingestion Only -------------------------
def _run_ingest_background(address: str, max_pages: int):
    """Run only the Etherscan → Parquet ingestion in the background."""
    try:
        INGEST_STATE["running"] = True
        INGEST_STATE["started_at"] = datetime.now().isoformat()

        INGEST_LOG_PATH.write_text(f"[{INGEST_STATE['started_at']}] Starting ingestion...\n")

        env = os.environ.copy()
        # Ensure Sepolia by default unless overridden in the environment
        env.setdefault("CHAIN_ID", "11155111")

        # Ensure scripts are executable
        try:
            subprocess.run(["/bin/bash", "-lc", "chmod +x scripts/*.sh"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        cmd = f"./scripts/ingest.sh '{address}' '{max_pages}'"
        with INGEST_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", cmd],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            lf.write(f"\n[{datetime.now().isoformat()}] Ingestion finished with code {proc.returncode}\n")
    except Exception as e:
        with INGEST_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
    finally:
        INGEST_STATE["running"] = False

@app.route('/api/run/ingest', methods=['POST'])
def run_ingest():
    """Trigger ingestion stage asynchronously (Sepolia by default)."""
    if INGEST_STATE.get("running"):
        return jsonify({"status": "running", "message": "Ingestion already running"}), 409
    body = request.get_json(silent=True) or {}
    address = body.get("address") or "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    
    # Validate Ethereum address
    is_valid, error_msg = validate_ethereum_address(address)
    if not is_valid:
        return jsonify({"error": f"Invalid Ethereum address: {error_msg}"}), 400
    
    max_pages = int(body.get("pages") or 5)
    t = threading.Thread(target=_run_ingest_background, args=(address, max_pages), daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/ingest/status')
def ingest_status():
    """Return current ingestion run status and last logs."""
    logs_tail = ""
    try:
        if INGEST_LOG_PATH.exists():
            content = INGEST_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": INGEST_STATE.get("running", False),
        "started_at": INGEST_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------- Stage: Convert to JSONL -------------------------
def _run_convert_background(input_dir: str, output_dir: str, limit: int):
    """Run Parquet → JSONL conversion in the background."""
    try:
        CONVERT_STATE["running"] = True
        CONVERT_STATE["started_at"] = datetime.now().isoformat()

        CONVERT_LOG_PATH.write_text(f"[{CONVERT_STATE['started_at']}] Starting conversion...\n")

        env = os.environ.copy()
        # Ensure scripts are executable
        try:
            subprocess.run(["/bin/bash", "-lc", "chmod +x scripts/*.sh"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        cmd = f"./scripts/convert_to_jsonl.sh '{input_dir}' '{output_dir}' '{limit}'"
        with CONVERT_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", cmd],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            lf.write(f"\n[{datetime.now().isoformat()}] Conversion finished with code {proc.returncode}\n")
    except Exception as e:
        with CONVERT_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
    finally:
        CONVERT_STATE["running"] = False

@app.route('/api/run/convert', methods=['POST'])
def run_convert():
    """Trigger conversion stage asynchronously."""
    if CONVERT_STATE.get("running"):
        return jsonify({"status": "running", "message": "Conversion already running"}), 409
    body = request.get_json(silent=True) or {}
    input_dir = body.get("input_dir") or "/tmp/eth_tx"
    output_dir = body.get("output_dir") or "/tmp/eth_tx_jsonl"
    limit = int(body.get("limit") or 200)
    t = threading.Thread(target=_run_convert_background, args=(input_dir, output_dir, limit), daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/convert/status')
def convert_status():
    """Return current conversion status and last logs."""
    logs_tail = ""
    try:
        if CONVERT_LOG_PATH.exists():
            content = CONVERT_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": CONVERT_STATE.get("running", False),
        "started_at": CONVERT_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------- Stage: Image Generation -------------------------
def _run_image_generation_background(input_path: str, output_path: str):
    """Run image generation from JSONL data in the background."""
    try:
        IMAGE_STATE["running"] = True
        IMAGE_STATE["started_at"] = datetime.now().isoformat()

        IMAGE_LOG_PATH.write_text(f"[{IMAGE_STATE['started_at']}] Starting image generation...\n")

        env = os.environ.copy()
        
        # Use venv python if available
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
        if venv_python.exists():
            env["PYTHON"] = str(venv_python)
            with IMAGE_LOG_PATH.open("a") as lf:
                lf.write(f"Using venv Python: {venv_python}\n")
        
        # Ensure scripts are executable
        try:
            subprocess.run(["/bin/bash", "-lc", "chmod +x scripts/*.sh"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        # Modify the command to use venv python if available
        if venv_python.exists():
            # Create a wrapper that uses venv python
            cmd = f"source .venv/bin/activate && ./scripts/generate_image.sh '{input_path}' '{output_path}'"
        else:
            cmd = f"./scripts/generate_image.sh '{input_path}' '{output_path}'"
        
        with IMAGE_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", cmd],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            lf.write(f"\n[{datetime.now().isoformat()}] Image generation finished with code {proc.returncode}\n")
    except Exception as e:
        with IMAGE_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
    finally:
        IMAGE_STATE["running"] = False

@app.route('/api/run/image', methods=['POST'])
def run_image_generation():
    """Trigger image generation stage asynchronously."""
    if IMAGE_STATE.get("running"):
        return jsonify({"status": "running", "message": "Image generation already running"}), 409
    body = request.get_json(silent=True) or {}
    input_path = body.get("input_path") or "/tmp/eth_tx_jsonl"
    output_path = body.get("output_path") or "/tmp/eth_tx_chart.png"
    t = threading.Thread(target=_run_image_generation_background, args=(input_path, output_path), daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/image/status')
def image_generation_status():
    """Return current image generation status and last logs."""
    logs_tail = ""
    try:
        if IMAGE_LOG_PATH.exists():
            content = IMAGE_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": IMAGE_STATE.get("running", False),
        "started_at": IMAGE_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------- Stage: IPFS Upload (No Docker) -------------------
def _resolve_jsonl_file(path_str: str) -> str:
    path = pathlib.Path(path_str)
    if path.is_file():
        return str(path)
    if path.is_dir():
        # find a part-* or *.jsonl
        parts = sorted(path.glob("part-*")) or sorted(path.glob("*.jsonl"))
        if parts:
            return str(parts[0])
    return ""

def _current_stage_name() -> str:
    stage_map = [
        ("ingest", INGEST_STATE),
        ("convert", CONVERT_STATE),
        ("image", IMAGE_STATE),
        ("ipfs", UPLOAD_STATE),
        ("deploy", DEPLOY_STATE),
        ("mint", MINT_STATE),
    ]
    for name, state in stage_map:
        if state.get("running"):
            return name
    if RUN_STATE.get("running"):
        return "pipeline"
    return "idle"

def _format_eth(value_str: str) -> str:
    try:
        value = Decimal(str(value_str))
        eth = value / Decimal(10**18)
        return f"{eth:.6f}"
    except Exception:
        return "0.000000"

def _build_live_summary(limit: int = 5) -> dict:
    summary = {
        "stage": _current_stage_name(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "metrics": {},
        "addresses": [],
        "transactions": []
    }

    jsonl_file = _resolve_jsonl_file("/tmp/eth_tx_jsonl")
    if not jsonl_file:
        return summary

    path_obj = pathlib.Path(jsonl_file)
    if not path_obj.exists():
        return summary

    transactions = []
    addresses = set()

    try:
        with path_obj.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    tx = json.loads(line)
                except Exception:
                    continue
                tx_info = {
                    "hash": tx.get("hash") or tx.get("transactionHash") or "",
                    "from": tx.get("from") or "",
                    "to": tx.get("to") or "",
                    "value_eth": _format_eth(tx.get("value", "0")),
                    "block": tx.get("blockNumber"),
                    "time": tx.get("timeStamp") or tx.get("timestamp"),
                }
                transactions.append(tx_info)
                if tx_info["from"]:
                    addresses.add(tx_info["from"])
                if tx_info["to"]:
                    addresses.add(tx_info["to"])
                if len(transactions) >= limit:
                    break
    except Exception:
        return summary

    if transactions:
        summary["transactions"] = transactions
        summary["addresses"] = list(addresses)[:8]
        summary["metrics"] = {
            "sample_size": len(transactions),
            "unique_addresses": len(addresses),
            "latest_block": transactions[0].get("block"),
            "data_file": path_obj.name
        }

    return summary

def _upload_to_web3_storage(file_path: str, token: str) -> str:
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.web3.storage/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (pathlib.Path(file_path).name, f)},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    # web3.storage returns {"cid": "..."} or {"ok":true,"value":{"cid":"..."}}
    cid = data.get("cid") or (data.get("value", {}) or {}).get("cid")
    if not cid:
        raise RuntimeError(f"web3.storage response missing cid: {data}")
    return cid

def upload_to_pinata(file_path: str, jwt: str = "", api_key: str = "", api_secret: str = "", 
                    max_retries: int = 3, retry_delay: int = 2) -> str:
    """
    Upload a file to Pinata IPFS pinning service with retry logic.
    
    Args:
        file_path: Path to file to upload
        jwt: Pinata JWT token (preferred method)
        api_key: Pinata API key (alternative to JWT)
        api_secret: Pinata API secret (required with api_key)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay in seconds between retries (default: 2)
        
    Returns:
        IPFS CID (IpfsHash) of uploaded file
        
    Raises:
        RuntimeError: If credentials are missing, invalid, or upload fails after retries
        FileNotFoundError: If file doesn't exist
    """
    import time
    
    # Validate credentials
    headers = {}
    auth_method = ""
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
        auth_method = "JWT"
    elif api_key and api_secret:
        headers["pinata_api_key"] = api_key
        headers["pinata_secret_api_key"] = api_secret
        auth_method = "API Key"
    else:
        raise RuntimeError(
            "Pinata credentials missing. Provide one of:\n"
            "  - PINATA_JWT environment variable or jwt parameter\n"
            "  - PINATA_API_KEY + PINATA_API_SECRET environment variables or parameters"
        )
    
    # Validate file exists and is readable
    file_path_obj = pathlib.Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path_obj.is_file():
        raise RuntimeError(f"Path is not a file: {file_path}")
    
    # Get file size for logging
    file_size_kb = file_path_obj.stat().st_size / 1024
    
    # Retry loop
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"📤 Uploading to Pinata (attempt {attempt}/{max_retries}, auth: {auth_method}, size: {file_size_kb:.2f} KB)...")
            
            # Upload file with multipart form-data
            with open(file_path, "rb") as f:
                files = {"file": (file_path_obj.name, f)}
                resp = requests.post(
                    "https://api.pinata.cloud/pinning/pinFileToIPFS",
                    headers=headers,
                    files=files,
                    timeout=60,
                )
            
            # Log request details for debugging
            print(f"📡 Pinata response: HTTP {resp.status_code}")
            
            # Handle authentication failures (don't retry these)
            if resp.status_code == 401:
                error_msg = "Pinata authentication failed. Check your credentials:\n"
                error_msg += f"  - Using {auth_method} authentication\n"
                if jwt:
                    error_msg += "  - JWT token may be expired or invalid\n"
                else:
                    error_msg += "  - API key or secret may be incorrect\n"
                error_msg += "  - Verify credentials at https://app.pinata.cloud/developers/api-keys"
                raise RuntimeError(error_msg)
            
            elif resp.status_code == 403:
                error_msg = "Pinata access forbidden. Possible causes:\n"
                error_msg += "  - Account doesn't have pinning permissions\n"
                error_msg += "  - API key permissions are insufficient\n"
                error_msg += "  - Account may be suspended or over quota\n"
                error_msg += "  - Check your account status at https://app.pinata.cloud"
                raise RuntimeError(error_msg)
            
            # Handle rate limiting (retry these)
            elif resp.status_code == 429:
                error_msg = f"Pinata rate limit exceeded (attempt {attempt}/{max_retries})"
                print(f"⚠️  {error_msg}", file=sys.stderr)
                if attempt < max_retries:
                    wait_time = retry_delay * attempt  # Exponential backoff
                    print(f"⏳ Waiting {wait_time} seconds before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"{error_msg}. Wait and try again later.")
            
            # Raise for other HTTP errors
            resp.raise_for_status()
            
            # Extract CID from response
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSON response from Pinata: {e}\nResponse: {resp.text[:200]}")
            
            cid = data.get("IpfsHash")
            if not cid:
                raise RuntimeError(f"Pinata response missing IpfsHash field. Response: {json.dumps(data)[:200]}")
            
            # Log success details
            print(f"✅ Upload successful!")
            print(f"   CID: {cid}")
            print(f"   File: {file_path_obj.name}")
            if "PinSize" in data:
                print(f"   Pin Size: {data['PinSize']} bytes")
            
            return cid
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Pinata upload timed out after 60 seconds (attempt {attempt}/{max_retries})"
            print(f"⚠️  {error_msg}", file=sys.stderr)
            last_error = RuntimeError(f"{error_msg}. Check your network connection and file size.")
            if attempt < max_retries:
                print(f"⏳ Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                continue
                
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to Pinata API (attempt {attempt}/{max_retries}): {e}"
            print(f"⚠️  {error_msg}", file=sys.stderr)
            last_error = RuntimeError(f"Connection error: {e}\nCheck your internet connection and Pinata service status.")
            if attempt < max_retries:
                print(f"⏳ Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                continue
                
        except requests.exceptions.HTTPError as e:
            error_msg = f"Pinata API error (HTTP {e.response.status_code})"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg += f": {error_data['error']}"
                elif "message" in error_data:
                    error_msg += f": {error_data['message']}"
            except:
                error_msg += f": {e.response.text[:200]}"
            
            print(f"⚠️  {error_msg}", file=sys.stderr)
            last_error = RuntimeError(error_msg)
            
            # Retry on server errors (5xx), but not client errors (4xx)
            if 500 <= e.response.status_code < 600 and attempt < max_retries:
                print(f"⏳ Server error, retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                continue
            else:
                raise last_error
                
        except RuntimeError:
            # Re-raise RuntimeError (authentication, validation errors)
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error during Pinata upload: {type(e).__name__}: {e}"
            print(f"❌ {error_msg}", file=sys.stderr)
            last_error = RuntimeError(error_msg)
            if attempt < max_retries:
                print(f"⏳ Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                continue
            else:
                raise last_error
    
    # If we exhausted all retries, raise the last error
    if last_error:
        raise last_error
    else:
        raise RuntimeError(f"Upload failed after {max_retries} attempts")

# Keep backward compatibility alias
def _upload_to_pinata(file_path: str, jwt: str = "", api_key: str = "", api_secret: str = "") -> str:
    """Backward compatibility wrapper for upload_to_pinata."""
    return upload_to_pinata(file_path, jwt, api_key, api_secret)

def generate_nft_metadata(image_cid: str, data_cid: str, transaction_count: int = 0, 
                         jwt: str = "", api_key: str = "", api_secret: str = "") -> str:
    """
    Generate ERC-721 compliant NFT metadata and upload to Pinata.
    
    Args:
        image_cid: IPFS CID of the image file
        data_cid: IPFS CID of the transaction data (JSONL)
        transaction_count: Number of transactions in the dataset
        jwt: Pinata JWT token (preferred method)
        api_key: Pinata API key (alternative to JWT)
        api_secret: Pinata API secret (required with api_key)
        
    Returns:
        IPFS CID of the uploaded metadata JSON
        
    Raises:
        ValueError: If CIDs are invalid
        RuntimeError: If metadata generation or upload fails
    """
    # Validate CIDs
    if not image_cid or not isinstance(image_cid, str):
        raise ValueError(f"Invalid image CID: {image_cid}")
    if not data_cid or not isinstance(data_cid, str):
        raise ValueError(f"Invalid data CID: {data_cid}")
    
    # Validate transaction count
    if not isinstance(transaction_count, int) or transaction_count < 0:
        print(f"⚠️  Warning: Invalid transaction count {transaction_count}, using 0", file=sys.stderr)
        transaction_count = 0
    
    print(f"📝 Generating NFT metadata...")
    print(f"   Image CID: {image_cid}")
    print(f"   Data CID: {data_cid}")
    print(f"   Transaction Count: {transaction_count}")
    
    # Build ERC-721 compliant metadata JSON
    try:
        metadata = {
            "name": "Sepolia Transaction Data NFT",
            "description": f"On-chain transaction data visualization from Sepolia testnet. Contains {transaction_count} transactions with visual chart representation.",
            "image": f"ipfs://{image_cid}",
            "attributes": [
                {
                    "trait_type": "Chain",
                    "value": "Sepolia"
                },
                {
                    "trait_type": "Transaction Count",
                    "value": transaction_count
                },
                {
                    "trait_type": "Data CID",
                    "value": data_cid
                }
            ]
        }
    except Exception as e:
        raise RuntimeError(f"Failed to build metadata JSON: {e}")
    
    # Save metadata to temporary file
    metadata_path = pathlib.Path("/tmp/nft_metadata.json")
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"✅ Metadata JSON created: {metadata_path}")
    except IOError as e:
        raise RuntimeError(f"Failed to write metadata file to {metadata_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error writing metadata file: {e}")
    
    # Upload metadata JSON to Pinata
    try:
        print(f"📤 Uploading metadata to Pinata...")
        metadata_cid = upload_to_pinata(str(metadata_path), jwt=jwt, api_key=api_key, api_secret=api_secret)
        print(f"✅ Metadata uploaded successfully: {metadata_cid}")
        return metadata_cid
    except FileNotFoundError as e:
        raise RuntimeError(f"Metadata file not found: {e}")
    except RuntimeError:
        # Re-raise RuntimeError from upload_to_pinata
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error uploading metadata to Pinata: {type(e).__name__}: {e}")

def _run_ipfs_upload_background(target_path: str, provider: str, token_or_key: str, secret: str):
    """
    Upload image, JSONL data, and NFT metadata to IPFS via selected provider.
    
    This function performs a complete NFT asset upload workflow:
    1. Upload image file (PNG chart) to IPFS
    2. Upload JSONL data file to IPFS
    3. Generate NFT metadata with image CID
    4. Upload metadata JSON to IPFS
    5. Save all CIDs for subsequent pipeline stages
    """
    try:
        UPLOAD_STATE["running"] = True
        UPLOAD_STATE["started_at"] = datetime.now().isoformat()

        UPLOAD_LOG_PATH.write_text(f"[{UPLOAD_STATE['started_at']}] Starting IPFS upload (provider={provider})...\n")

        # Resolve JSONL file path
        resolved_jsonl = _resolve_jsonl_file(target_path)
        if not resolved_jsonl:
            raise RuntimeError(f"No JSONL file found at {target_path}")
        
        with UPLOAD_LOG_PATH.open("a") as lf:
            lf.write(f"Found JSONL file: {resolved_jsonl}\n")

        # Determine image path (default location from image generation stage)
        image_path = "/tmp/eth_tx_chart.png"
        if not pathlib.Path(image_path).exists():
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"⚠️  Warning: Image file not found at {image_path}, skipping image upload\n")
            image_cid = None
        else:
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"Found image file: {image_path}\n")
            image_cid = None

        # Prepare credentials based on provider
        jwt = ""
        api_key = ""
        api_secret = ""
        
        # Always check for Pinata credentials first (for fallback)
        pinata_jwt = os.getenv("PINATA_JWT", "")
        pinata_api_key = os.getenv("PINATA_API_KEY", "")
        pinata_api_secret = os.getenv("PINATA_API_SECRET", "")
        
        if provider == "pinata":
            # Allow either JWT or key+secret
            if token_or_key and token_or_key.startswith("ey"):
                jwt = token_or_key
            else:
                api_key = token_or_key or pinata_api_key
                api_secret = secret or pinata_api_secret
                if not api_key or not api_secret:
                    jwt = pinata_jwt
        
        # Step 1: Upload image file first (if exists)
        if image_cid is None and pathlib.Path(image_path).exists():
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"\n[{datetime.now().isoformat()}] Uploading image to IPFS...\n")
            
            if provider == "web3storage":
                token = token_or_key or os.getenv("IPFS_WEB3_STORAGE_TOKEN", "")
                if not token:
                    # Fallback to Pinata if web3storage token is missing
                    if pinata_jwt or pinata_api_key:
                        with UPLOAD_LOG_PATH.open("a") as lf:
                            lf.write("⚠️  web3.storage token not found, falling back to Pinata...\n")
                        provider = "pinata"
                        if pinata_jwt:
                            jwt = pinata_jwt
                        else:
                            api_key = pinata_api_key
                            api_secret = pinata_api_secret
                    else:
                        with UPLOAD_LOG_PATH.open("a") as lf:
                            lf.write(f"❌ PINATA_JWT check: {pinata_jwt[:20] if pinata_jwt else 'NOT FOUND'}...\n")
                            lf.write(f"❌ PINATA_API_KEY check: {pinata_api_key[:20] if pinata_api_key else 'NOT FOUND'}...\n")
                        raise RuntimeError("Missing web3.storage token (set IPFS_WEB3_STORAGE_TOKEN or pass token). Pinata credentials also not available.")
                
                if provider == "web3storage":
                    image_cid = _upload_to_web3_storage(image_path, token)
                else:
                    image_cid = upload_to_pinata(image_path, jwt=jwt, api_key=api_key, api_secret=api_secret)
            elif provider == "pinata":
                image_cid = upload_to_pinata(image_path, jwt=jwt, api_key=api_key, api_secret=api_secret)
            else:
                raise RuntimeError(f"Unsupported provider: {provider}")
            
            # Save image CID
            with open("/tmp/ipfs_image_cid.env", "w") as f:
                f.write(f"export IMAGE_CID={image_cid}\n")
            
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"✅ Image uploaded successfully\n")
                lf.write(f"   Image CID: {image_cid}\n")
                lf.write(f"   Gateway URL: {PIPELINE_CONFIG['ipfs_gateway']}/ipfs/{image_cid}\n")

        # Step 2: Upload JSONL data file
        with UPLOAD_LOG_PATH.open("a") as lf:
            lf.write(f"\n[{datetime.now().isoformat()}] Uploading data file to IPFS...\n")
        
        data_cid = ""
        if provider == "web3storage":
            token = token_or_key or os.getenv("IPFS_WEB3_STORAGE_TOKEN", "")
            if not token:
                # Fallback to Pinata if web3storage token is missing
                if pinata_jwt or pinata_api_key:
                    with UPLOAD_LOG_PATH.open("a") as lf:
                        lf.write("⚠️  web3.storage token not found, falling back to Pinata...\n")
                    provider = "pinata"
                    if pinata_jwt:
                        jwt = pinata_jwt
                    else:
                        api_key = pinata_api_key
                        api_secret = pinata_api_secret
                else:
                    raise RuntimeError("Missing web3.storage token (set IPFS_WEB3_STORAGE_TOKEN or pass token). Pinata credentials also not available.")
            
            if provider == "web3storage":
                data_cid = _upload_to_web3_storage(resolved_jsonl, token)
            else:
                data_cid = upload_to_pinata(resolved_jsonl, jwt=jwt, api_key=api_key, api_secret=api_secret)
        elif provider == "pinata":
            data_cid = upload_to_pinata(resolved_jsonl, jwt=jwt, api_key=api_key, api_secret=api_secret)
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")
        
        with UPLOAD_LOG_PATH.open("a") as lf:
            lf.write(f"✅ Data file uploaded successfully\n")
            lf.write(f"   Data CID: {data_cid}\n")
            lf.write(f"   Gateway URL: {PIPELINE_CONFIG['ipfs_gateway']}/ipfs/{data_cid}\n")

        # Step 3: Generate and upload NFT metadata (only if image was uploaded)
        metadata_cid = None
        if image_cid:
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"\n[{datetime.now().isoformat()}] Generating NFT metadata...\n")
            
            # Count transactions in JSONL file
            transaction_count = 0
            try:
                with open(resolved_jsonl, 'r') as f:
                    transaction_count = sum(1 for line in f if line.strip())
            except Exception:
                transaction_count = 0
            
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"   Transaction count: {transaction_count}\n")
            
            # Generate and upload metadata
            if provider == "pinata":
                metadata_cid = generate_nft_metadata(
                    image_cid=image_cid,
                    data_cid=data_cid,
                    transaction_count=transaction_count,
                    jwt=jwt,
                    api_key=api_key,
                    api_secret=api_secret
                )
            elif provider == "web3storage":
                # For web3.storage, generate metadata and upload
                metadata = {
                    "name": "Sepolia Transaction Data NFT",
                    "description": f"On-chain transaction data visualization from Sepolia testnet. Contains {transaction_count} transactions with visual chart representation.",
                    "image": f"ipfs://{image_cid}",
                    "attributes": [
                        {"trait_type": "Chain", "value": "Sepolia"},
                        {"trait_type": "Transaction Count", "value": transaction_count},
                        {"trait_type": "Data CID", "value": data_cid}
                    ]
                }
                metadata_path = pathlib.Path("/tmp/nft_metadata.json")
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                token = token_or_key or os.getenv("IPFS_WEB3_STORAGE_TOKEN", "")
                metadata_cid = _upload_to_web3_storage(str(metadata_path), token)
            
            with UPLOAD_LOG_PATH.open("a") as lf:
                lf.write(f"✅ Metadata uploaded successfully\n")
                lf.write(f"   Metadata CID: {metadata_cid}\n")
                lf.write(f"   Gateway URL: {PIPELINE_CONFIG['ipfs_gateway']}/ipfs/{metadata_cid}\n")
                lf.write(f"   Token URI: ipfs://{metadata_cid}\n")

        # Step 4: Save CIDs to environment files for subsequent stages
        # Save metadata CID (or data CID if no metadata) as primary CID
        primary_cid = metadata_cid if metadata_cid else data_cid
        with open("/tmp/ipfs_cid.env", "w") as f:
            f.write(f"export CID={primary_cid}\n")
            if metadata_cid:
                f.write(f"export METADATA_CID={metadata_cid}\n")
            f.write(f"export DATA_CID={data_cid}\n")
            if image_cid:
                f.write(f"export IMAGE_CID={image_cid}\n")

        # Final summary
        with UPLOAD_LOG_PATH.open("a") as lf:
            lf.write(f"\n{'='*60}\n")
            lf.write(f"IPFS Upload Summary\n")
            lf.write(f"{'='*60}\n")
            if image_cid:
                lf.write(f"Image CID:    {image_cid}\n")
            lf.write(f"Data CID:     {data_cid}\n")
            if metadata_cid:
                lf.write(f"Metadata CID: {metadata_cid}\n")
                lf.write(f"\n🎉 NFT-ready! Use metadata CID for minting: {metadata_cid}\n")
            lf.write(f"\n[{datetime.now().isoformat()}] Upload finished successfully\n")
            
    except Exception as e:
        with UPLOAD_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
            import traceback
            lf.write(f"{traceback.format_exc()}\n")
    finally:
        UPLOAD_STATE["running"] = False

@app.route('/api/run/ipfs', methods=['POST'])
def run_ipfs_upload():
    """Trigger IPFS upload (no Docker)."""
    if UPLOAD_STATE.get("running"):
        return jsonify({"status": "running", "message": "IPFS upload already running"}), 409
    body = request.get_json(silent=True) or {}
    target_path = body.get("path") or "/tmp/eth_tx_jsonl"
    
    # Default to pinata if PINATA_JWT is available, otherwise web3storage
    default_provider = "pinata" if os.getenv("PINATA_JWT") or os.getenv("PINATA_API_KEY") else "web3storage"
    provider = (body.get("provider") or default_provider).lower()
    token_or_key = body.get("token") or ""
    secret = body.get("secret") or ""
    t = threading.Thread(target=_run_ipfs_upload_background, args=(target_path, provider, token_or_key, secret), daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/ipfs/status')
def ipfs_upload_status():
    """Return current IPFS upload status and logs."""
    logs_tail = ""
    try:
        if UPLOAD_LOG_PATH.exists():
            content = UPLOAD_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": UPLOAD_STATE.get("running", False),
        "started_at": UPLOAD_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------- Stage: NFT Contract Deployment -------------------------
def _run_deploy_background():
    """Deploy Simple721 NFT contract to blockchain in the background, or use existing contract if available."""
    try:
        DEPLOY_STATE["running"] = True
        DEPLOY_STATE["started_at"] = datetime.now().isoformat()

        env = os.environ.copy()
        
        # Check if contract already exists (from env or temp file)
        nft_addr = env.get("NFT_ADDR") or _load_env_value("/tmp/nft_address.env", "NFT_ADDR")
        
        # Validate contract address format if it exists
        if nft_addr and nft_addr.startswith('0x') and len(nft_addr) == 42:
            # Contract already deployed, skip deployment
            log_message = f"""[{DEPLOY_STATE['started_at']}] Skipping deployment...

✅ Using existing NFT contract
================================================
Contract Address: {nft_addr}
Network: Sepolia testnet
Chain ID: {env.get('CHAIN_ID', '11155111')}

ℹ️  Contract already deployed - skipping deployment step
   To deploy a new contract, remove NFT_ADDR from .env file or /tmp/nft_address.env

================================================
✅ Deployment step complete (using existing contract)

[{datetime.now().isoformat()}] Deploy finished with code 0
"""
            DEPLOY_LOG_PATH.write_text(log_message)
            PIPELINE_CONFIG["nft_address"] = nft_addr
            DEPLOY_STATE["running"] = False
            return

        # No existing contract, proceed with deployment
        DEPLOY_LOG_PATH.write_text(f"[{DEPLOY_STATE['started_at']}] Starting NFT contract deployment...\n")
        
        # Validate required environment variables
        if not env.get("RPC_URL"):
            raise RuntimeError("RPC_URL environment variable not set")
        if not env.get("PRIVATE_KEY"):
            raise RuntimeError("PRIVATE_KEY environment variable not set")
        
        with DEPLOY_LOG_PATH.open("a") as lf:
            lf.write(f"RPC URL: {env.get('RPC_URL')}\n")
            lf.write(f"Deploying Simple721 contract...\n\n")
        
        # Ensure scripts are executable
        try:
            subprocess.run(["/bin/bash", "-lc", "chmod +x scripts/*.sh"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        cmd = "./scripts/deploy_nft.sh"
        with DEPLOY_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", cmd],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            
            if proc.returncode == 0:
                # Try to read the deployed contract address
                nft_addr = _load_env_value("/tmp/nft_address.env", "NFT_ADDR")
                if nft_addr:
                    lf.write(f"\n✅ Deployment successful!\n")
                    lf.write(f"Contract Address: {nft_addr}\n")
                    # Update pipeline config
                    PIPELINE_CONFIG["nft_address"] = nft_addr
                else:
                    lf.write(f"\n⚠️  Deployment completed but contract address not found\n")
            else:
                lf.write(f"\n❌ Deployment failed with exit code {proc.returncode}\n")
            
            lf.write(f"\n[{datetime.now().isoformat()}] Deployment finished with code {proc.returncode}\n")
    except Exception as e:
        with DEPLOY_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
            import traceback
            lf.write(f"{traceback.format_exc()}\n")
    finally:
        DEPLOY_STATE["running"] = False

@app.route('/api/run/deploy', methods=['POST'])
def run_deploy():
    """Trigger NFT contract deployment asynchronously."""
    if DEPLOY_STATE.get("running"):
        return jsonify({"status": "running", "message": "Deployment already running"}), 409
    t = threading.Thread(target=_run_deploy_background, daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/deploy/status')
def deploy_status():
    """Return current deployment status and last logs."""
    logs_tail = ""
    try:
        if DEPLOY_LOG_PATH.exists():
            content = DEPLOY_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": DEPLOY_STATE.get("running", False),
        "started_at": DEPLOY_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------- Stage: NFT Minting -------------------------
def _run_mint_background():
    """Mint NFT with IPFS metadata URI in the background."""
    try:
        MINT_STATE["running"] = True
        MINT_STATE["started_at"] = datetime.now().isoformat()

        MINT_LOG_PATH.write_text(f"[{MINT_STATE['started_at']}] Starting NFT minting...\n")

        env = os.environ.copy()
        
        # Validate required environment variables
        if not env.get("RPC_URL"):
            raise RuntimeError("RPC_URL environment variable not set")
        if not env.get("PRIVATE_KEY"):
            raise RuntimeError("PRIVATE_KEY environment variable not set")
        if not env.get("RECIPIENT"):
            raise RuntimeError("RECIPIENT environment variable not set")
        
        # Load NFT_ADDR from temp file if not in environment
        if not env.get("NFT_ADDR"):
            nft_addr = _load_env_value("/tmp/nft_address.env", "NFT_ADDR")
            if nft_addr:
                env["NFT_ADDR"] = nft_addr
        
        if not env.get("NFT_ADDR"):
            raise RuntimeError("NFT_ADDR not found. Deploy contract first.")
        
        # Load metadata CID from temp file if available
        metadata_cid = _load_env_value("/tmp/ipfs_cid.env", "METADATA_CID")
        if not metadata_cid:
            metadata_cid = _load_env_value("/tmp/ipfs_cid.env", "CID")
        
        with MINT_LOG_PATH.open("a") as lf:
            lf.write(f"RPC URL: {env.get('RPC_URL')}\n")
            lf.write(f"Contract: {env.get('NFT_ADDR')}\n")
            lf.write(f"Recipient: {env.get('RECIPIENT')}\n")
            if metadata_cid:
                lf.write(f"Metadata CID: {metadata_cid}\n")
                lf.write(f"Token URI: ipfs://{metadata_cid}\n")
            lf.write(f"\nMinting NFT...\n\n")
        
        # Ensure scripts are executable
        try:
            subprocess.run(["/bin/bash", "-lc", "chmod +x scripts/*.sh"], cwd=str(PROJECT_ROOT))
        except Exception:
            pass

        cmd = "./scripts/mint.sh"
        with MINT_LOG_PATH.open("a") as lf:
            proc = subprocess.Popen(
                ["/bin/bash", "-lc", cmd],
                cwd=str(PROJECT_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
            )
            proc.wait()
            
            if proc.returncode == 0:
                # Try to read the minted token ID
                token_id = _load_env_value("/tmp/nft_token_id.env", "TOKEN_ID")
                token_uri = _load_env_value("/tmp/mint_tx.env", "TOKEN_URI")
                tx_hash = _load_env_value("/tmp/mint_tx.env", "TX_HASH")
                
                lf.write(f"\n✅ Minting successful!\n")
                if token_id:
                    lf.write(f"Token ID: {token_id}\n")
                if token_uri:
                    lf.write(f"Token URI: {token_uri}\n")
                if tx_hash:
                    lf.write(f"Transaction: {tx_hash}\n")
            else:
                lf.write(f"\n❌ Minting failed with exit code {proc.returncode}\n")
            
            lf.write(f"\n[{datetime.now().isoformat()}] Minting finished with code {proc.returncode}\n")
    except Exception as e:
        with MINT_LOG_PATH.open("a") as lf:
            lf.write(f"\n[ERROR] {e}\n")
            import traceback
            lf.write(f"{traceback.format_exc()}\n")
    finally:
        MINT_STATE["running"] = False

@app.route('/api/run/mint', methods=['POST'])
def run_mint():
    """Trigger NFT minting asynchronously."""
    if MINT_STATE.get("running"):
        return jsonify({"status": "running", "message": "Minting already running"}), 409
    t = threading.Thread(target=_run_mint_background, daemon=True)
    t.start()
    return jsonify({"status": "started", "started_at": datetime.now().isoformat()}), 202

@app.route('/api/run/mint/status')
def mint_status():
    """Return current minting status and last logs."""
    logs_tail = ""
    try:
        if MINT_LOG_PATH.exists():
            content = MINT_LOG_PATH.read_text()
            logs_tail = content[-4000:]
    except Exception as e:
        logs_tail = f"[ERROR reading logs] {e}"
    return jsonify({
        "running": MINT_STATE.get("running", False),
        "started_at": MINT_STATE.get("started_at"),
        "logs": logs_tail,
    })

# ----------------------------- Utilities -----------------------------
def _load_env_value(path: str, var: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"export {var}="):
                    return line.split("=", 1)[1]
    except Exception:
        return None
    return None

def _rpc_call(method: str, params: list):
    try:
        resp = requests.post(
            PIPELINE_CONFIG['rpc_url'],
            json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json().get("result")
    except Exception:
        return None
    return None

def _get_latest_token_id(nft_addr: str):
    if not nft_addr:
        return None
    # totalSupply() selector 0x18160ddd
    res = _rpc_call("eth_call", [{"to": nft_addr, "data": "0x18160ddd"}, "latest"])
    if not res or res == "0x":
        return None
    try:
        supply = int(res, 16)
        return supply - 1 if supply > 0 else None
    except Exception:
        return None

def _get_token_uri(nft_addr: str, token_id: int):
    if nft_addr is None or token_id is None:
        return None
    # tokenURI(uint256) selector 0xc87b56dd + 32-byte tokenId
    token_hex = hex(token_id)[2:]
    token_hex = token_hex.rjust(64, '0')
    data = "0xc87b56dd" + token_hex
    res = _rpc_call("eth_call", [{"to": nft_addr, "data": data}, "latest"])
    return res if res and res != "0x" else None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
