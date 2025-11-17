# End-to-End Test Documentation

## Overview

This document describes the end-to-end test suite for the Sepolia NFT Pipeline. The test suite validates the complete pipeline functionality, error handling, and stage independence as specified in task 13 of the implementation plan.

## Test Files

- **`test_e2e_sepolia.py`**: Main test suite implementation
- **`scripts/run_e2e_tests.sh`**: Test runner script with environment validation
- **`test_pinata_integration.py`**: Unit tests for Pinata integration functions

## Test Structure

The test suite is organized into three main sub-tasks:

### Sub-task 13.1: Full Pipeline Test on Sepolia

Tests the complete end-to-end pipeline flow on Sepolia testnet:

1. **Deploy Contract to Sepolia**
   - Compiles and deploys ERC-721 contract
   - Verifies contract address is saved
   - Validates deployment transaction

2. **Ingest Sepolia Transaction Data**
   - Fetches transaction data via Etherscan API v2
   - Validates Parquet file creation
   - Verifies data format and content

3. **Convert to JSONL**
   - Converts Parquet to JSONL format
   - Validates JSONL structure
   - Verifies transaction count

4. **Generate Image Visualization**
   - Creates chart from transaction data
   - Validates PNG file creation
   - Checks file size and format

5. **Upload to IPFS (Pinata)**
   - Uploads image and metadata to Pinata
   - Validates CID generation
   - Verifies gateway accessibility

6. **Mint NFT with IPFS tokenURI**
   - Mints NFT with metadata CID
   - Validates token ID generation
   - Verifies tokenURI is set correctly

7. **Verify on Sepolia Etherscan**
   - Constructs Etherscan URL
   - Validates contract existence
   - Checks verification status

### Sub-task 13.2: Error Scenario Testing

Tests various error conditions and validates error messages:

1. **Invalid Ethereum Address**
   - Tests multiple invalid address formats
   - Verifies rejection of malformed addresses
   - Validates error messages

2. **Missing API Keys**
   - Tests behavior without ETHERSCAN_API_KEY
   - Validates clear error messaging
   - Ensures graceful failure

3. **Invalid RPC URL**
   - Tests with unreachable RPC endpoint
   - Validates connection error handling
   - Checks error message clarity

4. **Insufficient Testnet ETH**
   - Tests deployment with unfunded account
   - Validates balance error detection
   - Verifies helpful error messages

### Sub-task 13.3: Stage Independence Testing

Tests that stages can run independently and idempotently:

1. **Out-of-Order Stage Execution**
   - Runs stages with pre-existing files
   - Validates stages don't require sequential execution
   - Tests file-based state management

2. **Stage Re-run**
   - Executes same stage multiple times
   - Validates file overwriting behavior
   - Checks for conflicts or errors

3. **Stage Idempotency**
   - Runs stages twice with same input
   - Compares output consistency
   - Validates deterministic behavior

## Prerequisites

### Required Environment Variables

```bash
ETHERSCAN_API_KEY=your_etherscan_api_key
RPC_URL=https://eth-sepolia.g.alchemy.com/v2/your_project_id
CHAIN_ID=11155111
PRIVATE_KEY=your_private_key_here
RECIPIENT=your_wallet_address
PINATA_JWT=your_pinata_jwt_token  # Optional for some tests
```

### Required Tools

- Python 3.11+
- Foundry (forge, cast, anvil)
- PySpark (for conversion tests)
- Requests library

### Required Testnet Resources

- Sepolia testnet ETH (get from faucet)
- Etherscan API key (free tier sufficient)
- Pinata account with JWT token (for IPFS tests)

## Running the Tests

### Full Test Suite

Run all tests including full pipeline execution:

```bash
./scripts/run_e2e_tests.sh
```

### Quick Tests

Run only error scenarios and stage independence tests (skips full pipeline):

```bash
./scripts/run_e2e_tests.sh --quick
```

### Direct Python Execution

Run the test suite directly:

```bash
cd pipeline_demo
python3 test_e2e_sepolia.py
```

## Test Output

### Success Output

```
======================================================================
Sepolia NFT Pipeline - End-to-End Test Suite
======================================================================

✅ PASS: Deploy Contract to Sepolia
✅ PASS: Ingest Sepolia Transaction Data
✅ PASS: Convert to JSONL
...

======================================================================
Test Summary: 15 total, 15 passed, 0 failed, 0 skipped
======================================================================

🎉 All tests passed!
```

### Failure Output

```
❌ FAIL: Deploy Contract to Sepolia
   Error: Deployment failed: insufficient funds

======================================================================
Test Summary: 15 total, 10 passed, 3 failed, 2 skipped
======================================================================

Failed Tests:
  • Deploy Contract to Sepolia: insufficient funds
  • Mint NFT with IPFS tokenURI: contract not deployed
  • Verify on Sepolia Etherscan: token ID not available
```

## Test Coverage

### Requirements Coverage

The test suite validates all requirements from the specification:

- **Requirement 1**: Sepolia network support (tests 13.1.1, 13.1.7)
- **Requirement 2**: Data ingestion (test 13.1.2)
- **Requirement 3**: Format conversion (test 13.1.3)
- **Requirement 4**: Visual representation (test 13.1.4)
- **Requirement 5**: IPFS upload (test 13.1.5)
- **Requirement 6**: NFT metadata (test 13.1.5)
- **Requirement 7**: Contract deployment (test 13.1.1)
- **Requirement 8**: NFT minting (test 13.1.6)
- **Requirement 9-10**: Web UI (manual testing required)
- **Requirement 11**: Result display (manual testing required)
- **Requirement 12**: Environment configuration (test 13.2.2)
- **Requirement 13**: Error handling (all 13.2 tests)
- **Requirement 14**: Idempotency (all 13.3 tests)

### Code Coverage

The test suite exercises:

- All shell scripts in `scripts/` directory
- Python ingestion script (`etherscan_ingest.py`)
- Python image generation script (`generate_image.py`)
- Solidity contract deployment
- NFT minting functionality
- IPFS upload integration
- Error handling paths

## Troubleshooting

### Test Failures

#### "Missing prerequisites"

**Cause**: Required environment variables not set

**Solution**: 
```bash
cp env.example .env
# Edit .env with your actual values
```

#### "Insufficient funds"

**Cause**: Test wallet has no Sepolia ETH

**Solution**: Get testnet ETH from Sepolia faucet:
- https://sepoliafaucet.com/
- https://www.alchemy.com/faucets/ethereum-sepolia

#### "API rate limit exceeded"

**Cause**: Too many Etherscan API requests

**Solution**: Wait a few minutes and retry, or use a different API key

#### "IPFS upload failed"

**Cause**: Invalid Pinata credentials or network issue

**Solution**: 
- Verify PINATA_JWT is correct
- Check Pinata account status
- Test with smaller files

### Test Skips

Tests may be skipped for valid reasons:

- **"Missing prerequisites"**: Environment not configured for full pipeline test
- **"No pre-existing JSONL files"**: Stage independence test requires prior execution
- **"PINATA_JWT not configured"**: IPFS tests require Pinata credentials
- **"Missing Python dependencies"**: pandas/matplotlib not installed

## Manual Testing

Some aspects require manual verification:

### Web UI Testing

1. Start the UI: `cd ui && ./start_ui.sh`
2. Open browser: http://localhost:5001
3. Test each stage button
4. Verify real-time log updates
5. Check result panels display correctly

### NFT Verification

1. Open Sepolia Etherscan
2. Navigate to contract address
3. Verify token exists
4. Check tokenURI points to IPFS
5. Test metadata accessibility via gateway

### Visual Quality

1. Open generated image: `/tmp/eth_tx_chart.png`
2. Verify chart is readable
3. Check labels and title
4. Validate data accuracy

## Continuous Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r ui/requirements.txt
      - name: Run tests
        env:
          ETHERSCAN_API_KEY: ${{ secrets.ETHERSCAN_API_KEY }}
          RPC_URL: ${{ secrets.SEPOLIA_RPC_URL }}
          PRIVATE_KEY: ${{ secrets.TEST_PRIVATE_KEY }}
          RECIPIENT: ${{ secrets.TEST_RECIPIENT }}
          CHAIN_ID: 11155111
        run: ./scripts/run_e2e_tests.sh --quick
```

## Test Maintenance

### Adding New Tests

1. Add test method to `SepoliaPipelineTest` class
2. Follow naming convention: `_test_<feature_name>`
3. Use `self.result.add_pass()` / `add_fail()` / `add_skip()`
4. Update this documentation

### Updating Tests

When pipeline changes:

1. Review affected test methods
2. Update assertions and validations
3. Update expected outputs
4. Re-run full test suite
5. Update documentation

## Performance Benchmarks

Expected test execution times:

- **Full Pipeline Test**: 5-10 minutes (depends on network)
- **Error Scenarios**: 1-2 minutes
- **Stage Independence**: 1-2 minutes
- **Total Suite**: 7-14 minutes

## Known Limitations

1. **Network Dependency**: Tests require internet access for Etherscan and Pinata APIs
2. **Testnet Availability**: Sepolia network must be operational
3. **Rate Limits**: Etherscan API has rate limits (5 requests/second)
4. **Gas Costs**: Tests consume testnet ETH for transactions
5. **Timing Sensitivity**: Some tests may fail due to network latency

## Future Enhancements

Potential test improvements:

- [ ] Mock Etherscan API for offline testing
- [ ] Add performance benchmarking
- [ ] Implement parallel test execution
- [ ] Add load testing for UI endpoints
- [ ] Create test data fixtures
- [ ] Add contract verification tests
- [ ] Implement automated visual regression testing
- [ ] Add security testing (input validation, injection attacks)

## References

- [Sepolia Testnet Documentation](https://ethereum.org/en/developers/docs/networks/#sepolia)
- [Etherscan API Documentation](https://docs.etherscan.io/)
- [Pinata API Documentation](https://docs.pinata.cloud/)
- [Foundry Book](https://book.getfoundry.sh/)
- [ERC-721 Standard](https://eips.ethereum.org/EIPS/eip-721)
