# NFT Contract Reuse Strategy

## Overview

The pipeline now **reuses the same NFT contract** for multiple mints instead of deploying a new contract every time. This saves gas, time, and makes it easier to manage your NFTs.

## How It Works

### First Time (Deploy Once)

1. **No NFT_ADDR in .env** → Pipeline deploys a new contract
2. Contract address is saved to `/tmp/nft_address.env`
3. **Manually add** the contract address to your `.env` file:
   ```bash
   NFT_ADDR=0xYourContractAddressHere
   ```

### Subsequent Runs (Reuse Contract)

1. **NFT_ADDR exists in .env** → Pipeline skips deployment
2. Shows message: "✅ Using existing NFT contract"
3. Proceeds directly to minting with the existing contract
4. Each mint creates a **new token ID** on the same contract

## Benefits

✅ **Save Gas** - No deployment costs after the first time  
✅ **Faster** - Skip 30-60 second deployment wait  
✅ **Organized** - All your NFTs in one contract  
✅ **Easier Tracking** - Single contract address to monitor  
✅ **Collection** - NFTs appear as a collection on OpenSea  

## Configuration

### Your Current Setup

```bash
# In .env file
NFT_ADDR=0xbb80496c4700beaa34759a6f173e280815d62d34
```

This contract is on **Sepolia testnet** and will be reused for all mints.

### View Your Contract

- **Sepolia Etherscan**: https://sepolia.etherscan.io/address/0xbb80496c4700beaa34759a6f173e280815d62d34
- **Contract Name**: Simple721
- **Network**: Sepolia (Chain ID: 11155111)

## Pipeline Behavior

### With NFT_ADDR Set (Current)

```
Step 1: Data Ingestion ✓
Step 2: Convert to JSONL ✓
Step 3: Generate Image ✓
Step 4: Upload to IPFS ✓
Step 5: Deploy Contract → SKIPPED (using existing)
Step 6: Mint NFT ✓ (creates new token ID)
```

### Without NFT_ADDR

```
Step 1: Data Ingestion ✓
Step 2: Convert to JSONL ✓
Step 3: Generate Image ✓
Step 4: Upload to IPFS ✓
Step 5: Deploy Contract ✓ (deploys new contract)
Step 6: Mint NFT ✓ (token ID: 0)
```

## Token IDs

Each time you mint, a new token ID is created:

- **First mint**: Token ID 0
- **Second mint**: Token ID 1
- **Third mint**: Token ID 2
- And so on...

All tokens share the same contract address but have unique:
- Token IDs
- Token URIs (pointing to different IPFS metadata)
- Images (different transaction data visualizations)

## Viewing Your NFTs

### Individual Token

```
https://sepolia.etherscan.io/token/0xbb80496c4700beaa34759a6f173e280815d62d34?a=<TOKEN_ID>
```

### Entire Collection

```
https://sepolia.etherscan.io/token/0xbb80496c4700beaa34759a6f173e280815d62d34
```

### OpenSea Testnet

```
https://testnets.opensea.io/assets/sepolia/0xbb80496c4700beaa34759a6f173e280815d62d34/<TOKEN_ID>
```

## When to Deploy a New Contract

You might want to deploy a new contract if:

1. **Starting a new collection** - Different theme or purpose
2. **Contract has issues** - Bug or needs upgrade
3. **Different network** - Moving from testnet to mainnet
4. **Testing** - Want to test deployment process

### To Deploy New Contract

1. Remove or comment out `NFT_ADDR` from `.env`:
   ```bash
   # NFT_ADDR=0xbb80496c4700beaa34759a6f173e280815d62d34
   ```

2. Run the pipeline - it will deploy a new contract

3. Add the new address back to `.env` for future mints

## UI Display

The UI now shows:

- **NFT Contract Address** field in configuration panel
- **Deployment step** shows "Using existing contract" when skipped
- **Green checkmark** on deployment step (instant completion)
- **Contract address** in results panel

## Example Flow

### Run 1 (First Time)
```
Address: 0x742d35...
↓
Ingest → Convert → Image → IPFS → Deploy (new) → Mint
                                    ↓
                            Contract: 0xabc123...
                            Token ID: 0
```

### Run 2 (Same Contract)
```
Address: 0x742d35...
↓
Ingest → Convert → Image → IPFS → Deploy (skip) → Mint
                                    ↓
                            Contract: 0xabc123... (same)
                            Token ID: 1 (new)
```

### Run 3 (Different Data)
```
Address: 0x999888...
↓
Ingest → Convert → Image → IPFS → Deploy (skip) → Mint
                                    ↓
                            Contract: 0xabc123... (same)
                            Token ID: 2 (new)
```

## Summary

🎯 **One Contract, Many NFTs**  
Your pipeline now efficiently mints multiple NFTs to the same contract, creating a cohesive collection of transaction data visualizations on Sepolia testnet.

Each run creates a unique NFT with:
- Different transaction data
- Different visualization
- Different IPFS metadata
- Same contract address
- Incremental token ID

This is the standard way NFT collections work! 🚀
