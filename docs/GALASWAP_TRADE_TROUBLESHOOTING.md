# GalaSwap Trade Troubleshooting

## Understanding the Errors

### Error 1: "No ask liquidity for GALA/USDT on galaswap"

**Problem**: GalaSwap uses **GUSDT** (Gala Tether USD), not regular USDT. The symbol format is different.

**Solution**: Use `GALA/GUSDT` instead of `GALA/USDT` for GalaSwap.

### Error 2: "binance does not have market symbol GALA/GUSDC"

**Problem**: GUSDC (Gala USD Coin) is a Gala Chain token that only exists on GalaSwap, not on Binance.

**Solution**: You cannot do cross-exchange arbitrage with GUSDC because Binance doesn't support it.

## Correct Trading Approaches

### Option 1: Cross-Exchange Arbitrage (Binance ↔ GalaSwap)

For cross-exchange arbitrage, you need pairs that exist on **BOTH** exchanges:

**Available Cross-Exchange Pairs:**
- `GALA/USDT` - GALA token traded with USDT
  - Binance: Regular USDT
  - GalaSwap: May need to use GUSDT (Gala Tether USD)

**Try this:**
```bash
# Check if GALA/USDT works (may need GALA/GUSDT on GalaSwap side)
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "galaswap",
    "trade_amount_usd": 10.0
  }'
```

**Note**: GalaSwap might use `GALA/GUSDT` format. The connector should handle this, but if there's no liquidity, it means:
- No one is offering swaps for that pair on GalaSwap
- The pair might not be actively traded

### Option 2: GalaSwap Native Pairs (GalaSwap Only)

For GalaSwap native tokens, you can only trade within GalaSwap:

**Available GalaSwap Native Pairs:**
- `GALA/GUSDC` - Gala to Gala USD Coin
- `GUSDC/GALA` - Gala USD Coin to Gala
- `GALA/GUSDT` - Gala to Gala Tether USD
- `GUSDT/GALA` - Gala Tether USD to Gala

**These pairs CANNOT be used for cross-exchange arbitrage** because Binance doesn't support GUSDC or GUSDT (Gala versions).

## How to Check Available Pairs

### Method 1: Check Market Prices

```bash
curl http://localhost:8000/api/market/prices | jq '.prices | keys'
```

This will show all pairs that have current price data.

### Method 2: Check GalaSwap Balances

```bash
curl http://localhost:8000/api/portfolio/balances | jq '.balances_by_exchange.galaswap'
```

This shows what tokens you have on GalaSwap, which indicates available pairs.

### Method 3: Check Logs

From your logs, the bot discovered 47 pairs from GalaSwap. Check which ones:

```bash
docker compose logs dashboard | grep -i "discovered.*pairs"
```

## Working Trade Examples

### Example 1: Buy on Binance, Sell on GalaSwap (if GALA/USDT has liquidity)

```bash
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GALA/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "galaswap",
    "trade_amount_usd": 10.0
  }'
```

### Example 2: Try Other Common Pairs

If GALA/USDT doesn't work, try pairs that definitely exist on both:

```bash
# BTC/USDT (if available on GalaSwap)
curl -X POST http://localhost:8000/api/trades/test \
  -u admin:admin \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "buy_exchange": "binance",
    "sell_exchange": "galaswap",
    "trade_amount_usd": 10.0
  }'
```

### Example 3: GalaSwap Internal Swap (Not Arbitrage)

If you want to test GalaSwap functionality without cross-exchange arbitrage, you could:

1. Create a swap on GalaSwap (offer GALA, want GUSDC)
2. Accept a swap on GalaSwap (accept someone's offer)

However, the current test trade endpoint requires two different exchanges for arbitrage.

## Understanding GalaSwap Liquidity

GalaSwap is a **peer-to-peer swap system**, not a traditional order book exchange. This means:

1. **No guaranteed liquidity**: Swaps only exist if someone created them
2. **Symbol format**: Uses Gala Chain tokens (GUSDC, GUSDT) not regular USDT/USDC
3. **Swap availability**: You can only trade if:
   - Someone created a swap offering what you want
   - You have the tokens to accept/create swaps

## Solutions

### Solution 1: Check What Pairs Have Liquidity

```bash
# Get all available prices
curl http://localhost:8000/api/market/prices > prices.json

# Check which GalaSwap pairs have data
cat prices.json | jq '.prices | to_entries | map(select(.value.galaswap)) | map(.key)'
```

### Solution 2: Use Pairs That Definitely Exist

Based on your config, these pairs are configured:
- `GALA/USDT` - Should work if GalaSwap has GALA/USDT or GALA/GUSDT
- `GALA/GUSDC` - GalaSwap only (no Binance)
- `GALA/GUSDT` - GalaSwap only (no Binance)

### Solution 3: Check GalaSwap API Directly

The connector fetches available swaps. If there are no swaps available, you'll get "No ask liquidity". This is normal for GalaSwap - it means no one is currently offering swaps for that pair.

## Recommended Approach

1. **First, check available pairs with liquidity:**
   ```bash
   curl http://localhost:8000/api/market/opportunities
   ```
   This shows actual arbitrage opportunities that the bot found.

2. **Use those pairs for test trades:**
   - The opportunities endpoint shows pairs that have:
     - Price data on both exchanges
     - Profit potential
     - Available liquidity

3. **If no opportunities exist:**
   - GalaSwap may not have active swaps for cross-exchange pairs
   - Consider using GalaSwap for internal swaps only
   - Or wait for someone to create swaps on GalaSwap

## Alternative: Check Opportunities First

Before trying to execute a trade, check what opportunities the bot has found:

```bash
curl http://localhost:8000/api/market/opportunities | jq '.opportunities[] | {symbol, buy_exchange, sell_exchange, profit_percent}'
```

This will show you:
- Which pairs have price differences
- Which exchanges to use
- Expected profit

Then use those exact pairs for your test trade.

## Summary

**Key Points:**
1. ✅ GalaSwap uses GUSDT/GUSDC (Gala Chain tokens), not regular USDT/USDC
2. ✅ Cross-exchange arbitrage requires pairs that exist on BOTH exchanges
3. ✅ GalaSwap is peer-to-peer - liquidity depends on available swaps
4. ✅ Check `/api/market/opportunities` first to see what's actually available
5. ✅ Use pairs from the opportunities endpoint for test trades

**Next Steps:**
1. Check available opportunities: `curl http://localhost:8000/api/market/opportunities`
2. Use a pair from the opportunities list
3. Execute test trade with that pair

