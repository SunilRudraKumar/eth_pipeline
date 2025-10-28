#!/bin/bash
# Convert Parquet data to JSONL for IPFS
# Usage: ./scripts/convert_to_jsonl.sh [input_dir] [output_dir] [limit]

set -e

INPUT_DIR=${1:-"/tmp/eth_tx"}
OUTPUT_DIR=${2:-"/tmp/eth_tx_jsonl"}
LIMIT=${3:-200}

echo "🔄 Converting Parquet to JSONL..."
echo "Input: $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "Limit: $LIMIT rows"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Convert using PySpark
python3 - <<EOF
from pyspark.sql import SparkSession
import sys
import os
import shutil

spark = SparkSession.builder.getOrCreate()
try:
    df = spark.read.parquet("$INPUT_DIR")
    print(f"📊 Total rows in dataset: {df.count()}")
    
    # Get the most recent transactions
    df_limited = df.orderBy(df.timeStamp.desc()).limit($LIMIT)
    print(f"📝 Writing $LIMIT rows to JSONL...")
    
    # Overwrite output dir if it exists
    if os.path.exists("$OUTPUT_DIR"):
        shutil.rmtree("$OUTPUT_DIR")

    # toJSON() returns an RDD[String]; write as text files
    df_limited.toJSON().coalesce(1).saveAsTextFile("$OUTPUT_DIR")
    print("✅ JSONL conversion complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    spark.stop()
EOF

# Show the created files
echo "📁 JSONL files created:"
ls -la "$OUTPUT_DIR"
