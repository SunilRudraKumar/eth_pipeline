#!/usr/bin/env python3
"""
Image generation module for Ethereum transaction data visualization.

This module reads JSONL transaction data and generates a bar chart
showing the top 10 transactions by value.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for server environments
    import matplotlib.pyplot as plt
except ImportError as e:
    print(f"❌ Error: Missing required package: {e}", file=sys.stderr)
    print("Install with: pip install pandas matplotlib", file=sys.stderr)
    sys.exit(1)


def read_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    Read JSONL file and return list of transaction dictionaries.
    
    Args:
        file_path: Path to JSONL file
        
    Returns:
        List of transaction dictionaries
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    transactions = []
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    transactions.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Skipping invalid JSON on line {line_num}: {e}", 
                          file=sys.stderr)
                    continue
    
    return transactions


def generate_placeholder_image(output_path: str, message: str = "No Transaction Data Available"):
    """
    Generate a placeholder image when no data is available.
    
    Args:
        output_path: Path where image should be saved
        message: Message to display in placeholder
        
    Raises:
        RuntimeError: If image generation or saving fails
    """
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, message, 
                ha='center', va='center', fontsize=20, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✅ Placeholder image saved to: {output_path}")
    except Exception as e:
        plt.close('all')  # Clean up any open figures
        error_msg = f"Failed to generate placeholder image: {e}"
        print(f"❌ Error: {error_msg}", file=sys.stderr)
        raise RuntimeError(error_msg)


def generate_transaction_chart(transactions: List[Dict[str, Any]], output_path: str):
    """
    Generate bar chart of top 10 transactions by value.
    
    Args:
        transactions: List of transaction dictionaries
        output_path: Path where image should be saved
        
    Raises:
        ValueError: If transaction data is invalid or missing required fields
        RuntimeError: If chart generation or saving fails
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        
        # Ensure 'value' column exists
        if 'value' not in df.columns:
            raise ValueError("Transaction data missing 'value' field")
        
        # Validate we have data
        if len(df) == 0:
            raise ValueError("Transaction DataFrame is empty")
        
        # Convert Wei to ETH (value is typically a string in the JSON)
        try:
            df['value_eth'] = df['value'].astype(float) / 1e18
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to convert transaction values to ETH: {e}")
        
        # Get top 10 transactions by value
        top_10 = df.nlargest(min(10, len(df)), 'value_eth')
        
        print(f"📊 Total transactions: {len(df)}")
        print(f"📈 Top transaction value: {top_10['value_eth'].max():.6f} ETH")
        print(f"📉 {'10th' if len(top_10) >= 10 else 'Lowest'} transaction value: {top_10['value_eth'].min():.6f} ETH")
        
        # Create bar chart with 10x6 inch dimensions
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create bars
        bars = ax.bar(range(len(top_10)), top_10['value_eth'], 
                      color='steelblue', alpha=0.8, edgecolor='navy', linewidth=0.5)
        
        # Add value labels on top of bars
        for i, (idx, row) in enumerate(top_10.iterrows()):
            height = row['value_eth']
            ax.text(i, height, f'{height:.4f}', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Customize chart
        ax.set_xlabel('Transaction Rank', fontsize=12, fontweight='bold')
        ax.set_ylabel('Value (ETH)', fontsize=12, fontweight='bold')
        ax.set_title('Top 10 Transactions by Value', fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(range(len(top_10)))
        ax.set_xticklabels([f'#{i+1}' for i in range(len(top_10))])
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add subtle background color
        ax.set_facecolor('#f8f9fa')
        fig.patch.set_facecolor('white')
        
        plt.tight_layout()
        
        # Save with 150 DPI resolution
        try:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        except Exception as e:
            raise RuntimeError(f"Failed to save chart to {output_path}: {e}")
        finally:
            plt.close()
        
        # Report file size
        try:
            file_size = Path(output_path).stat().st_size / 1024
            print(f"✅ Chart saved to: {output_path}")
            print(f"📏 Image size: {file_size:.2f} KB")
        except Exception as e:
            print(f"⚠️  Warning: Could not read file size: {e}", file=sys.stderr)
            
    except (ValueError, RuntimeError):
        # Re-raise validation and runtime errors
        plt.close('all')  # Clean up any open figures
        raise
    except Exception as e:
        # Catch any unexpected matplotlib or pandas errors
        plt.close('all')  # Clean up any open figures
        error_msg = f"Unexpected error during chart generation: {type(e).__name__}: {e}"
        print(f"❌ Error: {error_msg}", file=sys.stderr)
        raise RuntimeError(error_msg)


def generate_image(jsonl_path: str, output_path: str):
    """
    Main function to generate visualization from JSONL data.
    
    Args:
        jsonl_path: Path to JSONL file or directory containing JSONL files
        output_path: Path where PNG image should be saved
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If data is invalid or missing required fields
        RuntimeError: If image generation fails
    """
    # Validate output path is writable
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created output directory: {output_dir}")
        except Exception as e:
            raise RuntimeError(f"Cannot create output directory {output_dir}: {e}")
    
    if not os.access(output_dir, os.W_OK):
        raise RuntimeError(f"Output directory is not writable: {output_dir}")
    
    # Handle directory input - find JSONL file
    jsonl_file = Path(jsonl_path)
    
    if not jsonl_file.exists():
        raise FileNotFoundError(f"Input path does not exist: {jsonl_path}")
    
    if jsonl_file.is_dir():
        # Look for JSONL files in directory
        jsonl_files = list(jsonl_file.glob("*.jsonl")) + list(jsonl_file.glob("part-*"))
        if not jsonl_files:
            raise FileNotFoundError(f"No JSONL files found in directory: {jsonl_path}")
        jsonl_file = jsonl_files[0]
        print(f"📄 Found JSONL file: {jsonl_file}")
    
    if not jsonl_file.is_file():
        raise FileNotFoundError(f"Not a valid file: {jsonl_file}")
    
    # Validate file is readable
    if not os.access(jsonl_file, os.R_OK):
        raise RuntimeError(f"Input file is not readable: {jsonl_file}")
    
    print(f"🎨 Generating image from: {jsonl_file}")
    
    # Read transactions
    try:
        transactions = read_jsonl(str(jsonl_file))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {jsonl_file}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to read JSONL file: {e}")
    
    # Handle empty dataset
    if not transactions:
        print("⚠️  No transactions found, creating placeholder image")
        generate_placeholder_image(output_path, "No Transaction Data Available")
        return
    
    # Generate chart
    try:
        generate_transaction_chart(transactions, output_path)
    except (ValueError, RuntimeError):
        # Re-raise known errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise RuntimeError(f"Failed to generate transaction chart: {e}")


def main():
    """Command-line interface for image generation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate visualization from Ethereum transaction JSONL data'
    )
    parser.add_argument(
        '--input',
        default='/tmp/eth_tx_jsonl',
        help='Input JSONL file or directory (default: /tmp/eth_tx_jsonl)'
    )
    parser.add_argument(
        '--output',
        default='/tmp/eth_tx_chart.png',
        help='Output PNG file path (default: /tmp/eth_tx_chart.png)'
    )
    
    args = parser.parse_args()
    
    try:
        generate_image(args.input, args.output)
    except FileNotFoundError as e:
        print(f"❌ File Error: {e}", file=sys.stderr)
        print(f"💡 Tip: Ensure the input path exists and contains JSONL data", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Data Error: {e}", file=sys.stderr)
        print(f"💡 Tip: Check that the JSONL file contains valid transaction data with 'value' fields", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        print(f"\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
