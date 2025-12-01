# Testnet Setup Guide

This guide explains how to enable and configure testnet mode for testing the arbitrage bot safely.

## Quick Start

Testnet mode is **already enabled** in `config/config.yaml` for all exchanges. The bot is configured to use:
- **Paper Trading**: Enabled (no real trades executed)
- **Testnet Mode**: Enabled for all CEX exchanges

## Configuration

### Option 1: Using config.yaml (Recommended)

The testnet settings are already configured in `config/config.yaml`:

```yaml
bot:
  paper_trading: true
  testnet_mode: true

exchanges:
  cex:
    - name: binance
      testnet: true  # ✅ Testnet enabled
    - name: okx
      testnet: true  # ✅ Testnet enabled
    - name: bybit
      testnet: true  # ✅ Testnet enabled
```

### Option 2: Using Environment Variables

You can also set testnet mode via environment variables in a `.env` file:

```bash
BINANCE_TESTNET=true
OKX_TESTNET=true
BYBIT_TESTNET=true
```

## Getting Testnet API Keys

### Binance Testnet
1. Visit: https://testnet.binance.vision/
2. Create an account and generate API keys
3. Add keys to dashboard or `.env` file

### OKX Testnet
1. Visit: https://www.okx.com/
2. Go to API settings
3. Enable "Demo Trading" mode
4. Generate testnet API keys

### Bybit Testnet
1. Visit: https://testnet.bybit.com/
2. Create account and generate API keys
3. Add keys to dashboard or `.env` file

## DEX Testnet Configuration

For DEX exchanges, use testnet RPC endpoints:

### Ethereum Testnet (Goerli/Sepolia)
```yaml
# In config.yaml, update RPC URL for testnet
ETH_RPC_URL=https://goerli.infura.io/v3/YOUR_INFURA_KEY
```

### BSC Testnet
```yaml
BSC_RPC_URL=https://data-seed-prebsc-1-s1.binance.org:8545/
```

### Polygon Testnet (Mumbai)
```yaml
POLYGON_RPC_URL=https://matic-mumbai.chainstacklabs.com
```

## Verifying Testnet Mode

When the bot starts, you should see log messages like:
```
Binance connector initialized in TESTNET mode
OKX connector initialized in TESTNET mode
Bybit connector initialized in TESTNET mode
```

## Switching to Mainnet

To switch to mainnet (live trading):

1. **Set paper_trading to false** (if you want real trades):
   ```yaml
   bot:
     paper_trading: false
   ```

2. **Set testnet to false for each exchange**:
   ```yaml
   exchanges:
     cex:
       - name: binance
         testnet: false  # Mainnet
   ```

3. **Use mainnet API keys** (different from testnet keys)

4. **Use mainnet RPC URLs** for DEX exchanges

## Important Notes

⚠️ **Safety Features:**
- `paper_trading: true` means NO real trades will be executed, even with mainnet keys
- Testnet mode uses fake/test funds
- Always test thoroughly in testnet before going live

🔒 **Security:**
- Never use mainnet private keys in testnet mode
- Keep testnet and mainnet keys separate
- Testnet keys can be shared (they're for testing only)

## Troubleshooting

**Issue**: "Authentication failed"
- **Solution**: Make sure you're using testnet API keys, not mainnet keys

**Issue**: "Cannot connect to exchange"
- **Solution**: Check if testnet endpoints are accessible from your network

**Issue**: "No balance available"
- **Solution**: Get testnet tokens from faucets:
  - Binance: https://testnet.binance.vision/faucet-smart
  - Ethereum Goerli: https://goerlifaucet.com/
  - BSC Testnet: https://testnet.binance.org/faucet-smart

## Next Steps

1. ✅ Testnet is already enabled in config
2. Add your testnet API keys via dashboard or `.env` file
3. Start the bot and verify testnet mode in logs
4. Test arbitrage detection and execution
5. Switch to mainnet only after thorough testing

