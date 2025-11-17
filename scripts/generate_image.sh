#!/bin/bash
# Generate visualization image from JSONL transaction data
# Usage: ./scripts/generate_image.sh [input_jsonl_path] [output_image_path]

set -e

INPUT_PATH=${1:-"/tmp/eth_tx_jsonl"}
OUTPUT_PATH=${2:-"/tmp/eth_tx_chart.png"}
LOG_FILE="/tmp/pipeline_image.log"

# Initialize log file
echo "🎨 Starting image generation at $(date)" > "$LOG_FILE"
echo "Input: $INPUT_PATH" >> "$LOG_FILE"
echo "Output: $OUTPUT_PATH" >> "$LOG_FILE"

# Echo to console as well
echo "🎨 Starting image generation..."
echo "Input: $INPUT_PATH"
echo "Output: $OUTPUT_PATH"
echo "Log: $LOG_FILE"

# Find the JSONL file (handle both directory and file input)
if [ -d "$INPUT_PATH" ]; then
    JSONL_FILE=$(find "$INPUT_PATH" -name "*.jsonl" -o -name "part-*" | head -n 1)
    if [ -z "$JSONL_FILE" ]; then
        echo "❌ Error: No JSONL file found in $INPUT_PATH" | tee -a "$LOG_FILE"
        exit 1
    fi
    echo "📄 Found JSONL file: $JSONL_FILE" | tee -a "$LOG_FILE"
else
    JSONL_FILE="$INPUT_PATH"
    if [ ! -f "$JSONL_FILE" ]; then
        echo "❌ Error: File not found: $JSONL_FILE" | tee -a "$LOG_FILE"
        exit 1
    fi
fi

# Run the Python image generation script
echo "🔨 Generating chart..." | tee -a "$LOG_FILE"

# Determine script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use venv python if available, otherwise use system python3
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
    echo "Using venv Python: $PYTHON_CMD" | tee -a "$LOG_FILE"
else
    PYTHON_CMD="python3"
    echo "Using system Python: $PYTHON_CMD" | tee -a "$LOG_FILE"
    echo "⚠️  Warning: venv not found, using system Python. pandas/matplotlib may not be available." | tee -a "$LOG_FILE"
fi

$PYTHON_CMD - <<EOF
import json
import sys
from pathlib import Path

try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"❌ Error: Missing required package: {e}", file=sys.stderr)
    print("Install with: pip install pandas matplotlib", file=sys.stderr)
    sys.exit(1)

def generate_image(jsonl_path, output_path, log_file):
    """Generate bar chart from JSONL transaction data."""
    
    with open(log_file, 'a') as log:
        log.write(f"Reading JSONL file: {jsonl_path}\n")
    
    # Read JSONL file
    transactions = []
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    transactions.append(json.loads(line))
    except Exception as e:
        with open(log_file, 'a') as log:
            log.write(f"❌ Error reading JSONL: {e}\n")
        raise
    
    with open(log_file, 'a') as log:
        log.write(f"📊 Loaded {len(transactions)} transactions\n")
    
    # Handle empty dataset
    if not transactions:
        with open(log_file, 'a') as log:
            log.write("⚠️  No transactions found, creating placeholder image\n")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No Transaction Data Available', 
                ha='center', va='center', fontsize=20, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    
    # Convert Wei to ETH (value is string in the JSON)
    df['value_eth'] = df['value'].astype(float) / 1e18
    
    # Get top 10 transactions by value
    top_10 = df.nlargest(10, 'value_eth')
    
    with open(log_file, 'a') as log:
        log.write(f"📈 Top transaction value: {top_10['value_eth'].max():.6f} ETH\n")
        log.write(f"📉 10th transaction value: {top_10['value_eth'].min():.6f} ETH\n")
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(range(len(top_10)), top_10['value_eth'], color='steelblue', alpha=0.8)
    
    # Add value labels on top of bars
    for i, (idx, row) in enumerate(top_10.iterrows()):
        height = row['value_eth']
        ax.text(i, height, f'{height:.4f}', 
                ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Transaction Rank', fontsize=12)
    ax.set_ylabel('Value (ETH)', fontsize=12)
    ax.set_title('Top 10 Transactions by Value', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(top_10)))
    ax.set_xticklabels([f'#{i+1}' for i in range(len(top_10))])
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    # Save with specified DPI and dimensions
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    with open(log_file, 'a') as log:
        log.write(f"✅ Image saved to: {output_path}\n")
        log.write(f"📏 Image size: {Path(output_path).stat().st_size / 1024:.2f} KB\n")

# Run the generation
try:
    generate_image("$JSONL_FILE", "$OUTPUT_PATH", "$LOG_FILE")
    print("✅ Image generation complete!")
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    with open("$LOG_FILE", 'a') as log:
        log.write(f"❌ Error: {e}\n")
    sys.exit(1)
EOF

# Check if image was created
if [ -f "$OUTPUT_PATH" ]; then
    echo "✅ Image generation complete!" | tee -a "$LOG_FILE"
    echo "📁 Output: $OUTPUT_PATH" | tee -a "$LOG_FILE"
    ls -lh "$OUTPUT_PATH" | tee -a "$LOG_FILE"
else
    echo "❌ Error: Image file was not created" | tee -a "$LOG_FILE"
    exit 1
fi

echo "📋 Full log available at: $LOG_FILE"
