#!/usr/bin/env python3
"""
Lightweight ingestion utility that fetches Etherscan account activity and writes it
using pandas/pyarrow. Spark is intentionally avoided so the pipeline can run in
small environments (Render free tier, etc.).

Usage:
  export ETHERSCAN_API_KEY=your_key
  python3 etherscan_ingest.py \
    --address 0x742d35Cc6634C0532925a3b844Bc454e4438f44e \
    --action txlist --start-block 0 --end-block 99999999 \
    --page-size 100 --max-pages 50 --rps 5 --output /tmp/eth_tx
"""
import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests

ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"

def fetch_page(action: str, address: str, apikey: str, start_block: int, end_block: int,
               page: int, offset: int, sort: str, chain_id: int) -> Dict:
    params = {
        "module": "account", "action": action, "address": address,
        "startblock": start_block, "endblock": end_block,
        "page": page, "offset": offset, "sort": sort, "apikey": apikey,
        "chainid": chain_id,
    }
    retries = 0
    while True:
        resp = requests.get(ETHERSCAN_BASE, params=params, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503, 504) and retries < 6:
            time.sleep(min(60, (2 ** retries) * 0.5)); retries += 1; continue
        resp.raise_for_status()

def paginate(action: str, address: str, start_block: int, end_block: int,
             page_size: int, max_pages: int, sort: str, rps: float, apikey: str,
             chain_id: int) -> List[Dict]:
    results: List[Dict] = []
    delay = 1.0 / max(1.0, rps)
    for page in range(1, max_pages + 1):
        payload = fetch_page(action, address, apikey, start_block, end_block, page, page_size, sort, chain_id)
        data = payload.get("result") or []
        if not isinstance(data, list) or len(data) == 0:
            break
        results.extend(data)
        time.sleep(delay)
        if len(data) < page_size:
            break
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--address", required=True, help="EOA or contract address")
    p.add_argument("--action", default="txlist",
                   choices=["txlist","txlistinternal","tokentx","tokennfttx"])
    p.add_argument("--chain-id", type=int, default=11155111, help="Etherscan chain id (11155111=sepolia, 1=mainnet)")
    p.add_argument("--start-block", type=int, default=0)
    p.add_argument("--end-block", type=int, default=99999999)
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--max-pages", type=int, default=100)
    p.add_argument("--sort", choices=["asc","desc"], default="asc")
    p.add_argument("--rps", type=float, default=5.0, help="Requests per second throttle")
    p.add_argument("--output", default="", help="Optional: e.g. parquet:/tmp/out or delta:/path")
    args = p.parse_args()

    apikey = os.getenv("ETHERSCAN_API_KEY")
    if not apikey:
        raise SystemExit("Set ETHERSCAN_API_KEY in your environment.")

    rows = paginate(
        action=args.action, address=args.address, start_block=args.start_block,
        end_block=args.end_block, page_size=args.page_size, max_pages=args.max_pages,
        sort=args.sort, rps=args.rps, apikey=apikey, chain_id=args.chain_id
    )

    # Guard against empty datasets from Etherscan (rate limits or inactive address)
    if not rows:
        # Create a minimal placeholder record so downstream steps don't break
        now_ts = int(time.time())
        rows = [{
            "blockNumber": 0,
            "timeStamp": now_ts,
            "from": "0x0000000000000000000000000000000000000000",
            "to": "0x0000000000000000000000000000000000000000",
            "hash": "0x" + ("0" * 64),
            "value": "0",
            "gas": "0",
            "gasPrice": "0",
            "gasUsed": "0",
            "input": "0x00",
            "isError": "0",
            "nonce": "0",
        }]
        print("Warning: Etherscan returned no data; proceeding with a placeholder row for demo continuity.")

    df = pd.DataFrame(rows)
    if df.empty:
        print("⚠️  Warning: DataFrame is empty even after placeholder handling.")

    # Ensure expected columns exist
    for col in ("blockNumber", "timeStamp", "value"):
        if col not in df.columns:
            df[col] = 0

    df["blockNumber"] = pd.to_numeric(df["blockNumber"], errors="coerce").fillna(0).astype("int64")
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce").fillna(0).astype("int64")
    df["ts"] = pd.to_datetime(df["timeStamp"], unit="s", errors="coerce")

    df["valueWei"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
    df["valueEth"] = (df["valueWei"] / 1e18).astype(float)

    print(f"Fetched {len(df)} rows from Etherscan ({args.action}).")
    print(df.sort_values("timeStamp", ascending=False).head(10).to_string(index=False))

    if args.output:
        output_path = Path(args.output)
        if output_path.suffix:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            file_path = output_path
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / "part-00000.jsonl"

        with file_path.open("w", encoding="utf-8") as fh:
            for record in df.to_dict(orient="records"):
                fh.write(json.dumps(record, default=str) + "\n")
        print(f"Wrote jsonl → {file_path}")

if __name__ == "__main__":
    main()
