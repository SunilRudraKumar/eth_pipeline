#!/usr/bin/env python3
"""
Simplified Pipeline Demo Web UI Backend
Single-button pipeline execution with real-time logs
"""

from flask import Flask, jsonify, render_template, send_file
from flask_cors import CORS
import os
import subprocess
import threading
import pathlib
from datetime import datetime

# Paths
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Log paths
INGEST_LOG = pathlib.Path("/tmp/pipeline_ingest.log")
CONVERT_LOG = pathlib.Path("/tmp/pipeline_convert.log")
IMAGE_LOG = pathlib.Path("/tmp/pipeline_image.log")
IPFS_LOG = pathlib.Path("/tmp/pipeline_ipfs_upload.log")
DEPLOY_LOG = pathlib.Path("/tmp/pipeline_deploy.log")
MINT_LOG = pathlib.Path("/tmp/pipeline_mint.log")

# State tracking
STATES = {
    'ingest': {"running": False, "started_at": None},
    'convert': {"running": False, "started_at": None},
    'image': {"running": False, "started_at": None},
    'ipfs': {"running": False, "started_at": None},
    'deploy': {"running": False, "started_at": None},
    'mint': {"running": False, "started_at": None},
}

app = Flask(__name__)
CORS(app)

# Configuration
CONFIG = {
    "chain_id": os.getenv("CHAIN_ID", "11155111"),
    "network": "Sepolia Testnet" if os.getenv("CHAIN_ID", "11155111") == "11155111" else "Unknown",
    "rpc_url": os.getenv("RPC_URL", ""),
    "recipient": os.getenv("RECIPIENT", ""),
    "nft_addr": os.getenv("NFT_ADDR", ""),
}


def run_command_async(command, log_path, state_key, cwd=None):
    """Run a command asynchronously and log output"""
    def run():
        STATES[state_key]["running"] = True
        STATES[state_key]["started_at"] = datetime.now().isoformat()
        
        # Clear log file
        log_path.write_text(f"[{datetime.now().isoformat()}] Starting {state_key}...\n")
        
        try:
            # Set up environment
            env = os.environ.copy()
            
            # Run command
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd or PROJECT_ROOT,
                env=env
            )
            
            # Stream output to log file
            with log_path.open("a") as f:
                for line in process.stdout:
                    f.write(line)
                    f.flush()
            
            process.wait()
            
            # Log completion
            with log_path.open("a") as f:
                f.write(f"\n[{datetime.now().isoformat()}] {state_key.capitalize()} finished with code {process.returncode}\n")
            
        except Exception as e:
            with log_path.open("a") as f:
                f.write(f"\n[{datetime.now().isoformat()}] Error: {str(e)}\n")
        finally:
            STATES[state_key]["running"] = False
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()


@app.route('/')
def index():
    """Serve the main page"""
    nft_addr = os.getenv('NFT_ADDR', 'Not deployed yet')
    return render_template('index.html', chain_id=CONFIG['chain_id'], nft_addr=nft_addr)


@app.route('/api/config')
def get_config():
    """Get pipeline configuration"""
    return jsonify(CONFIG)


@app.route('/api/run/ingest', methods=['POST'])
def run_ingest():
    """Start data ingestion"""
    from flask import request
    data = request.get_json() or {}
    address = data.get('address', '0x742d35Cc6634C0532925a3b844Bc454e4438f44e')
    pages = data.get('pages', '2')
    
    command = ['bash', 'scripts/ingest.sh', address, str(pages)]
    run_command_async(command, INGEST_LOG, 'ingest')
    
    return jsonify({"status": "started", "started_at": STATES['ingest']["started_at"]}), 202


@app.route('/api/run/ingest/status')
def ingest_status():
    """Get ingestion status"""
    logs = INGEST_LOG.read_text() if INGEST_LOG.exists() else ""
    return jsonify({
        "running": STATES['ingest']["running"],
        "started_at": STATES['ingest']["started_at"],
        "logs": logs
    })


@app.route('/api/run/convert', methods=['POST'])
def run_convert():
    """Start JSONL conversion"""
    command = ['bash', 'scripts/convert_to_jsonl.sh']
    run_command_async(command, CONVERT_LOG, 'convert')
    
    return jsonify({"status": "started", "started_at": STATES['convert']["started_at"]}), 202


@app.route('/api/run/convert/status')
def convert_status():
    """Get conversion status"""
    logs = CONVERT_LOG.read_text() if CONVERT_LOG.exists() else ""
    return jsonify({
        "running": STATES['convert']["running"],
        "started_at": STATES['convert']["started_at"],
        "logs": logs
    })


@app.route('/api/run/image', methods=['POST'])
def run_image():
    """Start image generation"""
    command = ['bash', 'scripts/generate_image.sh']
    run_command_async(command, IMAGE_LOG, 'image')
    
    return jsonify({"status": "started", "started_at": STATES['image']["started_at"]}), 202


@app.route('/api/run/image/status')
def image_status():
    """Get image generation status"""
    logs = IMAGE_LOG.read_text() if IMAGE_LOG.exists() else ""
    return jsonify({
        "running": STATES['image']["running"],
        "started_at": STATES['image']["started_at"],
        "logs": logs
    })


@app.route('/api/run/ipfs', methods=['POST'])
def run_ipfs():
    """Start IPFS upload via Pinata"""
    command = ['bash', 'scripts/pin_to_pinata.sh']
    run_command_async(command, IPFS_LOG, 'ipfs')
    
    return jsonify({"status": "started", "started_at": STATES['ipfs']["started_at"]}), 202


@app.route('/api/run/ipfs/status')
def ipfs_status():
    """Get IPFS upload status"""
    logs = IPFS_LOG.read_text() if IPFS_LOG.exists() else ""
    return jsonify({
        "running": STATES['ipfs']["running"],
        "started_at": STATES['ipfs']["started_at"],
        "logs": logs
    })


@app.route('/api/run/deploy', methods=['POST'])
def run_deploy():
    """Start contract deployment (or skip if already deployed)"""
    nft_addr = os.getenv('NFT_ADDR', '')
    
    # Check if contract already exists
    if nft_addr and nft_addr.startswith('0x') and len(nft_addr) == 42:
        # Contract already deployed, skip deployment
        STATES['deploy']["running"] = False
        STATES['deploy']["started_at"] = datetime.now().isoformat()
        
        log_message = f"""[{datetime.now().isoformat()}] Skipping deployment...

✅ Using existing NFT contract
================================================
Contract Address: {nft_addr}
Network: {CONFIG['network']}
Chain ID: {CONFIG['chain_id']}

ℹ️  Contract already deployed - skipping deployment step
   To deploy a new contract, remove NFT_ADDR from .env file

================================================
✅ Deployment step complete (using existing contract)

[{datetime.now().isoformat()}] Deploy finished with code 0
"""
        DEPLOY_LOG.write_text(log_message)
        
        return jsonify({
            "status": "skipped", 
            "started_at": STATES['deploy']["started_at"],
            "message": "Using existing contract",
            "contract_address": nft_addr
        }), 200
    
    # No contract address, proceed with deployment
    command = ['bash', 'scripts/deploy_nft.sh']
    run_command_async(command, DEPLOY_LOG, 'deploy')
    
    return jsonify({"status": "started", "started_at": STATES['deploy']["started_at"]}), 202


@app.route('/api/run/deploy/status')
def deploy_status():
    """Get deployment status"""
    logs = DEPLOY_LOG.read_text() if DEPLOY_LOG.exists() else ""
    return jsonify({
        "running": STATES['deploy']["running"],
        "started_at": STATES['deploy']["started_at"],
        "logs": logs
    })


@app.route('/api/run/mint', methods=['POST'])
def run_mint():
    """Start NFT minting"""
    command = ['bash', 'scripts/mint.sh']
    run_command_async(command, MINT_LOG, 'mint')
    
    return jsonify({"status": "started", "started_at": STATES['mint']["started_at"]}), 202


@app.route('/api/run/mint/status')
def mint_status():
    """Get minting status"""
    logs = MINT_LOG.read_text() if MINT_LOG.exists() else ""
    return jsonify({
        "running": STATES['mint']["running"],
        "started_at": STATES['mint']["started_at"],
        "logs": logs
    })


@app.route('/api/results')
def get_results():
    """Get final pipeline results"""
    results = {
        "contract": {},
        "nft": {},
        "ipfs": {},
        "data": {}
    }
    
    # Read contract address
    nft_addr_file = pathlib.Path("/tmp/nft_address.env")
    if nft_addr_file.exists():
        addr = nft_addr_file.read_text().strip()
        if '=' in addr:
            addr = addr.split('=')[1].strip().strip('"').strip("'")
        results["contract"]["address"] = addr
        results["contract"]["name"] = "Simple721"
        results["contract"]["etherscan_url"] = f"https://sepolia.etherscan.io/address/{addr}"
    
    # Read token ID
    token_id_file = pathlib.Path("/tmp/nft_token_id.env")
    if token_id_file.exists():
        token_id = token_id_file.read_text().strip()
        if '=' in token_id:
            token_id = token_id.split('=')[1].strip().strip('"').strip("'")
        results["nft"]["token_id"] = token_id
        results["nft"]["owner"] = CONFIG["recipient"]
    
    # Read IPFS CIDs
    image_cid_file = pathlib.Path("/tmp/ipfs_image_cid.env")
    if image_cid_file.exists():
        cid = image_cid_file.read_text().strip()
        if '=' in cid:
            cid = cid.split('=')[1].strip().strip('"').strip("'")
        results["ipfs"]["image_cid"] = cid
    
    metadata_cid_file = pathlib.Path("/tmp/ipfs_cid.env")
    if metadata_cid_file.exists():
        cid = metadata_cid_file.read_text().strip()
        if '=' in cid:
            cid = cid.split('=')[1].strip().strip('"').strip("'")
        results["ipfs"]["metadata_cid"] = cid
        results["ipfs"]["gateway_url"] = f"https://gateway.pinata.cloud/ipfs/{cid}"
        results["nft"]["token_uri"] = f"ipfs://{cid}"
    
    # Count transactions
    jsonl_dir = pathlib.Path("/tmp/eth_tx_jsonl")
    if jsonl_dir.exists():
        jsonl_files = list(jsonl_dir.glob("part-*"))
        if jsonl_files:
            with open(jsonl_files[0], 'r') as f:
                count = sum(1 for _ in f)
            results["data"]["transaction_count"] = count
    
    # Check for image
    image_path = pathlib.Path("/tmp/eth_tx_chart.png")
    if image_path.exists():
        results["data"]["image_path"] = str(image_path)
    
    return jsonify(results)


@app.route('/api/image')
def get_image():
    """Serve the generated chart image"""
    image_path = pathlib.Path("/tmp/eth_tx_chart.png")
    if image_path.exists():
        return send_file(image_path, mimetype='image/png')
    return jsonify({"error": "Image not found"}), 404


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Sepolia NFT Pipeline - Simplified UI")
    print("=" * 60)
    print(f"Network: {CONFIG['network']}")
    print(f"Chain ID: {CONFIG['chain_id']}")
    print(f"RPC URL: {CONFIG['rpc_url'][:50]}..." if CONFIG['rpc_url'] else "RPC URL: Not configured")
    print("=" * 60)
    print("\n✨ Starting server on http://0.0.0.0:5003")
    print("   Open http://localhost:5003 in your browser\n")
    
    app.run(debug=True, host='0.0.0.0', port=5003)
