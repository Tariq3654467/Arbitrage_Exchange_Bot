# How to Execute a Trade on GalaSwap

This guide shows you how to manually execute a single trade on GalaSwap using the bot's API.

## Method 1: Using the API Endpoint (Recommended)

The bot has a `/api/trades/test` endpoint that allows you to execute a single manual trade.

### Step 1: Check Available Opportunities First (Important!)

**Before executing a trade, check what pairs actually have liquidity and opportunities:**

```bash
curl http://localhost:8000/api/market/opportunities
```

This shows:
- Pairs with price differences
- Available liquidity on both exchanges
- Expected profit

**Use pairs from this list for your test trades!**

### Step 2: Check Available Pairs

From your logs, the bot discovered 47 pairs from GalaSwap. However, **not all pairs have liquidity**.

**Important Notes:**
- GalaSwap uses **GUSDT** (Gala Tether USD) and **GUSDC** (Gala USD Coin), not regular USDT/USDC
- For cross-exchange arbitrage, you need pairs that exist on **BOTH** exchanges
- GalaSwap is peer-to-peer - liquidity depends on available swaps

### Step 3: Execute a Test Trade via API

Use curl or any HTTP client to execute a trade:

```bash
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/GUSDC",
    "buy_exchange": "galaswap",
    "sell_exchange": "galaswap",
    "trade_amount_usd": 5.0
  }'
```

**Parameters:**
- `symbol`: Trading pair (e.g., "GALA/GUSDC", "GUSDC/GALA")
- `buy_exchange`: Exchange to buy from ("galaswap" or "binance")
- `sell_exchange`: Exchange to sell on ("binance" or "galaswap")
- `trade_amount_usd`: Amount in USD to trade (minimum depends on exchange)

### Step 3: Example Trades

#### Example 1: Buy on Binance, Sell on GalaSwap (Recommended)
```bash
# Note: GalaSwap may use GALA/GUSDT format, but connector should handle GALA/USDT
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "binance",
    "trade_amount_usd": 5.0
  }'
```

**If you get "No ask liquidity" error:**
- GalaSwap may not have active swaps for GALA/USDT
- Try checking opportunities first: `curl http://localhost:8000/api/market/opportunities`
- Use a pair that shows up in opportunities

#### Example 2: Buy on Binance, Sell on GalaSwap
```bash
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "galaswap",
    "trade_amount_usd": 15.0
  }'
```

#### Example 3: GalaSwap Native Pairs (Limited)

**Note**: GalaSwap native pairs like `GALA/GUSDC` or `GALA/GUSDT` **cannot be used for cross-exchange arbitrage** because:
- Binance doesn't support GUSDC or GUSDT (Gala Chain tokens)
- These are Gala Chain-only tokens

**For GalaSwap native pairs, you can only:**
- Create swaps on GalaSwap
- Accept swaps on GalaSwap
- But NOT arbitrage with Binance

**If you want to test GalaSwap functionality:**
- Check if there are available swaps: `curl http://localhost:8000/api/market/prices`
- Look for pairs that show GalaSwap prices
- Use those pairs (but they won't work for cross-exchange arbitrage)

## Method 2: Using Python Script

Create a script to execute trades:

```python
import requests
import json

# API endpoint
url = "http://localhost:8000/api/trades/test"

# Authentication
auth = ("admin", "admin")

# Trade request
trade_request = {
    "symbol": "GALA/GUSDC",
    "buy_exchange": "galaswap",
    "sell_exchange": "binance",
    "trade_amount_usd": 10.0
}

# Execute trade
response = requests.post(url, auth=auth, json=trade_request)

print("Status Code:", response.status_code)
print("Response:", json.dumps(response.json(), indent=2))
```

## Method 3: Direct Exchange Call (Advanced)

If you want to execute a trade directly on GalaSwap without arbitrage logic:

```python
# This would require accessing the bot instance directly
# Not recommended for production use
```

## Response Format

The API will return:

```json
{
  "status": "completed",
  "symbol": "GALA/GUSDC",
  "buy_exchange": "galaswap",
  "sell_exchange": "binance",
  "expected_net_profit_usd": 0.15,
  "expected_net_profit_percent": 1.5,
  "actual_profit_usd": 0.12,
  "actual_profit_percent": 1.2,
  "error_message": null
}
```

**Possible Status Values:**
- `"completed"` - Trade executed successfully
- `"failed"` - Trade failed
- `"blocked_by_risk"` - Trade blocked by risk manager
- `"partial"` - Trade partially filled

## Important Notes

### 1. Risk Management
The bot will check:
- ✅ Minimum profit threshold (0.001% by default)
- ✅ Maximum trade size
- ✅ Daily loss limits
- ✅ Portfolio allocation

### 2. Paper Trading Mode
If paper trading is enabled, trades will be simulated only.

**Check paper trading status:**
```bash
curl http://localhost:8000/api/bot/status | grep paper_trading
```

**Disable paper trading (for real trades):**
- Dashboard → Config → Trading Settings
- Or set `paper_trading: false` in `config/config.yaml`

### 3. Balance Requirements
- Ensure you have sufficient balance on both exchanges
- GalaSwap needs GALA or GUSDC/GUSDT tokens
- Binance needs USDT or the base token

**Check balances:**
```bash
curl http://localhost:8000/api/portfolio/balances
```

### 4. Minimum Trade Amounts
- GalaSwap: Very small minimums (can trade fractions)
- Binance: Depends on pair (usually 0.001 BTC equivalent)

### 5. GalaSwap Specific Notes
- GalaSwap uses swaps (peer-to-peer)
- Orders may take time to fill if no matching swaps available
- Swaps are created/accepted, not traditional limit orders

## Common Errors and Solutions

### "No ask liquidity for GALA/USDT on galaswap"

**Problem**: GalaSwap doesn't have active swaps for this pair, OR GalaSwap uses `GALA/GUSDT` format.

**Solutions**:
1. Check available opportunities first: `curl http://localhost:8000/api/market/opportunities`
2. Use a pair that shows up in opportunities
3. GalaSwap is peer-to-peer - liquidity depends on available swaps

### "binance does not have market symbol GALA/GUSDC"

**Problem**: GUSDC is a Gala Chain token that only exists on GalaSwap, not Binance.

**Solution**: You cannot do cross-exchange arbitrage with GUSDC. Use pairs that exist on both exchanges (like GALA/USDT).

### "Bot is not running"
```bash
# Start the bot via API
curl -X POST http://localhost:8000/api/bot/start -u admin:admin
```

### "Unknown exchanges"
- Check available exchanges:
```bash
curl http://localhost:8000/api/config/exchanges
```
- Ensure GalaSwap is connected (check logs)

### "blocked_by_risk"
- Trade doesn't meet profit threshold
- Exceeds maximum trade size
- Daily loss limit reached
- Check risk settings in dashboard

### "Failed to execute"
- Check exchange connection
- Verify balances
- Check logs: `docker compose logs dashboard | grep -i error`

## Monitoring the Trade

After executing, monitor:

1. **Dashboard → Trades**: See trade history
2. **Dashboard → Balances**: Check updated balances
3. **Logs**: `docker compose logs -f dashboard`

## Example: Complete Trade Flow

```bash
# 1. Check bot status
curl http://localhost:8000/api/bot/status

# 2. Check balances
curl http://localhost:8000/api/portfolio/balances

# 3. Execute trade
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/GUSDC",
    "buy_exchange": "galaswap",
    "sell_exchange": "binance",
    "trade_amount_usd": 10.0
  }'

# 4. Check trade result
# Response will show status and profit

# 5. Verify balances again
curl http://localhost:8000/api/portfolio/balances
```

## Safety Reminders

⚠️ **WARNING**: The bot is in **LIVE TRADING MODE** (from your logs)

- ✅ Real funds will be used
- ✅ Trades are irreversible
- ✅ Start with small amounts
- ✅ Test thoroughly before scaling up
- ✅ Monitor closely during first trades

## Next Steps

1. ✅ Execute a small test trade ($5-10)
2. ✅ Verify execution in dashboard
3. ✅ Check balances updated correctly
4. ✅ Review trade logs
5. ✅ Scale up gradually if successful

