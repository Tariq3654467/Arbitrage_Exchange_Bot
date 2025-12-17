# GalaSwap Quick Start Guide

Quick reference for configuring GalaSwap in your arbitrage bot.

## Quick Setup (Choose One Method)

### Method 1: Dashboard Configuration (Recommended - Easiest)

**Step 1:** Start the bot and open the dashboard:
```bash
python main.py
# Open http://localhost:3000 in your browser
```

**Step 2:** Navigate to **Config** → **Exchange Keys** in the dashboard

**Step 3:** Select **"galaswap"** from the DEX exchanges dropdown

**Step 4:** Fill in the form:
- **Private Key**: Your Gala private key (64 hex characters)
- **Wallet Address**: Your Gala wallet address (required for Galaswap)
- **RPC URL**: `https://jsonrpc.gala.games` (or leave default)
- **Enable**: Check the box to enable

**Step 5:** Click **"Save Exchange"**

✅ Done! Your credentials are encrypted and stored securely in the database.

### Method 2: Environment Variables (.env file)

Add to your `.env` file:

```bash
GALA_WALLET_ADDRESS=your_wallet_address
GALA_PRIVATE_KEY=your_private_key_hex
GALA_RPC_URL=https://jsonrpc.gala.games
```

### Method 3: Automated Setup Script

```bash
python setup_galaswap.py
```

## Configuration Check

### Verify in config.yaml

GalaSwap should be enabled:

```yaml
exchanges:
  dex:
    - name: galaswap
      enabled: true
      chain: gala
```

### Trading Pairs (Already Configured)

GalaSwap pairs are already in `config.yaml`:

```yaml
trading_pairs:
  - symbol: GALA/GUSDC
    min_trade_amount: 1.0
    enabled: true
  - symbol: GUSDC/GALA
    min_trade_amount: 1.0
    enabled: true
```

## Automated Setup

Run the setup script to automatically configure:

```bash
python setup_galaswap.py
```

This script will:
- Copy settings from `galaswap-bot/.env` if available
- Update `config.yaml` with GalaSwap settings
- Guide you through missing configuration

## Getting Your Credentials

1. Visit: https://galaswap.gala.com/info/api.html
2. Follow "Getting your Private Key" section
3. Copy your wallet address and private key

## Verification

After setup, verify connection:

1. Start bot: `python main.py`
2. Open dashboard: http://localhost:3000
3. Check **Balances** page for GalaSwap balances
4. Check **Market** page for GalaSwap prices

## Common Token Pairs

- `GALA/GUSDC` - Gala to Gala USD Coin
- `GUSDC/GALA` - Gala USD Coin to Gala
- `GALA/GUSDT` - Gala to Gala Tether USD
- `GUSDT/GALA` - Gala Tether USD to Gala

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Wallet address required" | Set `GALA_WALLET_ADDRESS` in `.env` |
| "Invalid private key" | Ensure 64 hex chars, remove `0x` if needed |
| "Circuit breaker OPEN" | Wait 5 minutes, check API status |
| "No swaps available" | Normal - GalaSwap is peer-to-peer |

## Full Documentation

See `docs/GALASWAP_INTEGRATION.md` for complete details.

