#!/bin/bash
# Prepare JSONL data (limit + sort) for downstream IPFS upload
# Usage: ./scripts/convert_to_jsonl.sh [input_dir] [output_dir] [limit]

set -e

PY_BIN=${PYTHON_BIN:-python3}

INPUT_DIR=${1:-"/tmp/eth_tx"}
OUTPUT_DIR=${2:-"/tmp/eth_tx_jsonl"}
LIMIT=${3:-200}

echo "🔄 Preparing JSONL dataset..."
echo "Input: $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "Limit: $LIMIT rows"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Convert using pandas
"$PY_BIN" - <<EOF
import json
import os
import shutil
from pathlib import Path

import pandas as pd

input_path = Path(r"$INPUT_DIR")
output_path = Path(r"$OUTPUT_DIR")
limit = int(r"$LIMIT")

if output_path.exists():
    shutil.rmtree(output_path)
output_path.mkdir(parents=True, exist_ok=True)

json_files = []
if input_path.is_file():
    json_files = [input_path]
elif input_path.is_dir():
    json_files = sorted([p for p in input_path.glob("*.json*") if p.is_file()])
    if not json_files:
        json_files = sorted([p for p in input_path.glob("part-*") if p.is_file()])

if not json_files:
    print(f"❌ Error: No JSON files found in {input_path}")
    raise SystemExit(1)

dataframes = []
for file in json_files:
    try:
        dataframes.append(pd.read_json(file, lines=True))
    except ValueError:
        dataframes.append(pd.read_json(file))
    except Exception as exc:
        print(f"⚠️  Skipping {file}: {exc}")

if not dataframes:
    print("❌ Error: Failed to read any JSON files")
    raise SystemExit(1)

df = pd.concat(dataframes, ignore_index=True)
if "timeStamp" in df.columns:
    df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce").fillna(0)
    df = df.sort_values("timeStamp", ascending=False)

df = df.head(limit)
print(f"📊 Total rows in dataset: {len(df)}")
print(f"📝 Writing {len(df)} rows to JSONL...")

output_file = output_path / "part-00000"
with output_file.open("w", encoding="utf-8") as fh:
    for record in df.to_dict(orient="records"):
        fh.write(json.dumps(record, default=str) + "\n")

print("✅ JSONL conversion complete!")
EOF

# Show the created files
echo "📁 JSONL files created:"
ls -la "$OUTPUT_DIR"
