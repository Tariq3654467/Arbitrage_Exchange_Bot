# GalaSwap Bot Integration Guide

This guide explains how to configure GalaSwap functionality from the `galaswap-bot` into your arbitrage bot.

## Overview

The arbitrage bot already includes a GalaSwap connector (`galaswap_connector.py`) that implements the BaseExchange interface. This guide shows you how to configure it using the same settings and patterns from the `galaswap-bot` project.

## Configuration Steps

### 1. Environment Variables

Create a `.env` file in the `Arbitrage_Exchange_Bot` root directory (or add to existing `.env`):

```bash
# GalaSwap Configuration (from galaswap-bot)
GALA_WALLET_ADDRESS=your_gala_wallet_address
GALA_PRIVATE_KEY=your_gala_private_key_hex
GALA_PUBLIC_KEY=your_gala_public_key_base64  # Optional, will be fetched if not provided
GALA_RPC_URL=https://jsonrpc.gala.games  # Gala Chain RPC endpoint

# Optional: GalaSwap API Base URL (defaults to https://api-galaswap.gala.com)
GALASWAP_API_BASE_URI=https://api-galaswap.gala.com
```

**Getting Your Gala Wallet Credentials:**

1. Visit https://galaswap.gala.com/info/api.html
2. Follow the "Getting your Private Key" section
3. Your wallet address format is typically: `client|...` or an Ethereum-style address
4. Your private key should be 64 hex characters (with or without `0x` prefix)

### 2. Token Configuration

The arbitrage bot uses trading pairs defined in `config/config.yaml`. For GalaSwap-specific tokens, you can reference the token configurations from `galaswap-bot/config/token_config.json`.

**Common GalaSwap Token Pairs:**
- `GALA/GUSDC` - Gala token to Gala USD Coin
- `GUSDC/GALA` - Gala USD Coin to Gala token
- `GALA/GUSDT` - Gala token to Gala Tether USD
- `GUSDT/GALA` - Gala Tether USD to Gala token

**Token Class Format:**
GalaSwap uses a token class format: `collection|category|type|additionalKey`

Example:
- GALA: `{"collection": "GALA", "category": "Unit", "type": "none", "additionalKey": "none"}`
- GUSDC: `{"collection": "GUSDC", "category": "Unit", "type": "none", "additionalKey": "none"}`

### 3. Update config.yaml

Ensure GalaSwap is enabled in your `config/config.yaml`:

```yaml
exchanges:
  dex:
    - name: galaswap
      enabled: true
      chain: gala
      router_address: "0x0000000000000000000000000000000000000000"  # Not used for API
      factory_address: "0x0000000000000000000000000000000000000000"  # Not used for API

trading_pairs:
  # GalaSwap pairs
  - symbol: GALA/GUSDC
    min_trade_amount: 1.0
    enabled: true
    
  - symbol: GUSDC/GALA
    min_trade_amount: 1.0
    enabled: true
    
  - symbol: GALA/GUSDT
    min_trade_amount: 1.0
    enabled: true
    
  - symbol: GUSDT/GALA
    min_trade_amount: 1.0
    enabled: true
```

### 4. Database Configuration (Optional)

If you want to store swap history like the galaswap-bot does with MongoDB, you can configure PostgreSQL in your `.env`:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arbitrage_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

The arbitrage bot already uses PostgreSQL for storing trade history and API keys.

### 5. API Keys Management (Recommended Method)

**You can configure GalaSwap credentials directly through the dashboard!**

#### Dashboard Configuration (Easiest Method):

1. Start the bot: `python main.py`
2. Open the dashboard at `http://localhost:3000`
3. Navigate to **Config** → **Exchange Keys**
4. In the **DEX Exchanges** section:
   - Select **"galaswap"** from the dropdown
   - Enter your **Private Key** (64 hex characters, with or without 0x prefix)
   - Enter your **Wallet Address** (required for Galaswap)
   - Enter **RPC URL**: `https://jsonrpc.gala.games` (or leave default)
   - Check **Enable** to activate
5. Click **"Save Exchange"**

✅ Your credentials are automatically encrypted and stored securely in the database.

**Benefits of Dashboard Configuration:**
- ✅ Credentials are encrypted in the database
- ✅ No need to edit `.env` file manually
- ✅ Easy to update or change credentials
- ✅ Can enable/disable without restarting bot
- ✅ Visual interface for managing all exchanges

#### Alternative: Environment Variables

If you prefer using `.env` file:
1. Add credentials to `.env` (see Step 1 above)
2. The bot will automatically load them on startup

## Key Differences from galaswap-bot

### Architecture
- **galaswap-bot**: TypeScript, MongoDB, dedicated swap strategies
- **arbitrage-bot**: Python, PostgreSQL, unified exchange interface for arbitrage

### Trading Strategy
- **galaswap-bot**: Creates and accepts swaps based on profitability thresholds
- **arbitrage-bot**: Finds price differences between exchanges and executes arbitrage

### Configuration
- **galaswap-bot**: JSON config files (`basic_swap_creator.json`, `basic_swap_accepter.json`)
- **arbitrage-bot**: YAML config file (`config.yaml`) + environment variables

## Features from galaswap-bot Already Implemented

✅ **API Integration**: The arbitrage bot's `galaswap_connector.py` implements:
- Fetching available swaps (`FetchAvailableTokenSwaps`)
- Accepting swaps (`BatchFillTokenSwap`)
- Creating swaps (`RequestTokenSwap`)
- Terminating swaps (`TerminateTokenSwap`)
- Fetching balances (`FetchBalances`)
- Fetching swaps by user (`FetchTokenSwapsOfferedByUser`)

✅ **Signing**: Uses the same secp256k1 signature scheme with keccak256 hashing

✅ **Error Handling**: Circuit breaker pattern to handle API failures gracefully

✅ **Token Parsing**: Handles GalaSwap token class format

## Features You Can Add

### 1. Swap Strategy Configuration

You can add configuration similar to `basic_swap_creator.json` and `basic_swap_accepter.json` to your `config.yaml`:

```yaml
galaswap_strategies:
  swap_creator:
    enabled: false  # Set to true if you want to create swaps
    target_active_swaps:
      - giving_token: GUSDC
        receiving_token: GALA
        target_profitability: 1.05  # 5% better than market
        min_profitability: 1.01
        max_profitability: 1.15
        target_giving_size: 10
        max_price_movement_percent: 0.03
        max_price_movement_window_ms: 1800000
  
  swap_accepter:
    enabled: false  # Set to true if you want to accept swaps
    trade_limits:
      - giving_token: GUSDC
        receiving_token: GALA
        rate: 1.01  # Accept swaps 1% better than market
        give_limit_per_reset: 10
        reset_interval_ms: 3600000
        max_price_movement_percent: 0.03
        max_price_movement_window_ms: 1800000
```

### 2. Price Limits

Add price limits similar to `token_config.json`:

```yaml
galaswap_price_limits:
  - token: GALA
    min_price_usd: 0
    max_price_usd: 100
```

## Testing the Integration

1. **Verify Connection**:
   ```bash
   python verify_galaswap_status.sh
   ```

2. **Check Balances**:
   - Start the bot and check the dashboard
   - Navigate to **Balances** to see your GalaSwap balances

3. **Test Order Book**:
   - The bot will automatically fetch order books for enabled trading pairs
   - Check **Market** page in dashboard to see GalaSwap prices

4. **Monitor Logs**:
   ```bash
   tail -f logs/arbitrage_bot_*.log
   ```

## Troubleshooting

### Common Issues

1. **"Wallet address is required"**
   - Ensure `GALA_WALLET_ADDRESS` is set in `.env` or added via dashboard

2. **"Invalid private key format"**
   - Private key must be 64 hex characters (32 bytes)
   - Can include or exclude `0x` prefix
   - Remove any whitespace

3. **"API error 401/403"**
   - Verify wallet address and private key are correct
   - Check that the wallet has been used on Gala Chain (may need initial transaction)

4. **"Circuit breaker OPEN"**
   - API is temporarily disabled due to repeated failures
   - Wait 5 minutes for automatic reset
   - Check network connectivity and API status

5. **"No swaps available"**
   - This is normal if there are no active swaps for the trading pair
   - GalaSwap is a peer-to-peer swap system, so liquidity depends on other users

### API Status

Check GalaSwap API status:
- API Base URL: `https://api-galaswap.gala.com`
- Documentation: https://galaswap.gala.com/info/api.html

## Next Steps

1. ✅ Configure environment variables
2. ✅ Enable GalaSwap in `config.yaml`
3. ✅ Add trading pairs for Gala tokens
4. ✅ Add credentials via dashboard
5. ✅ Test connection and balances
6. ✅ Monitor arbitrage opportunities

## Additional Resources

- **GalaSwap API Documentation**: https://galaswap.gala.com/info/api.html
- **Gala Chain Documentation**: Check Gala Games official documentation
- **galaswap-bot Reference**: See `galaswap-bot/README.md` for original bot documentation

