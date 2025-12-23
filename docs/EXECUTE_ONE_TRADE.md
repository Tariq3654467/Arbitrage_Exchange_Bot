# Execute One Trade - Quick Guide

## Step 1: Check Available Opportunities

```bash
curl http://localhost:8000/api/market/opportunities | jq
```

If you see opportunities, use the first one.

## Step 2: Check GalaSwap Liquidity

```bash
curl http://localhost:8000/api/market/galaswap/liquidity | jq
```

This shows which GalaSwap pairs have active pools.

## Step 3: Execute One Trade

### Option A: If Opportunities Exist

Use the first opportunity from Step 1:

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

### Option B: Test with Binance Only (If GalaSwap Has No Liquidity)

If GalaSwap has no liquidity, you can test the execution flow with Binance (this won't be arbitrage, just a test):

**Note:** Same-exchange trades are now blocked. For a real test, you need two different exchanges with liquidity.

### Option C: Use a Pair That Actually Has Liquidity

Check what pairs have prices on both exchanges:

```bash
curl -s http://localhost:8000/api/market/prices | jq '.prices | to_entries[] | select(.value.galaswap != null and .value.binance != null) | .key'
```

Then use one of those pairs.

## Step 4: Verify Trade Executed

```bash
curl http://localhost:8000/api/trades/history | jq '.trades[0]'
```

Check:
- `status`: Should be "completed" or "failed"
- `error_message`: If failed, shows why
- `profit_usd`: Actual profit (if completed)

## Common Issues:

1. **"No liquidity"**: The pair doesn't have an active pool on GalaSwap
2. **"Same exchange"**: Can't buy and sell on the same exchange
3. **"Blocked by risk"**: Risk manager blocked the trade

## Quick Test Command:

Run this to find and execute one trade:

```bash
# 1. Get first opportunity
OPP=$(curl -s http://localhost:8000/api/market/opportunities | jq -r '.opportunities[0]')

# 2. If opportunity exists, extract details and execute
if [ "$OPP" != "null" ] && [ -n "$OPP" ]; then
    SYMBOL=$(echo $OPP | jq -r '.symbol')
    BUY_EX=$(echo $OPP | jq -r '.buy_exchange')
    SELL_EX=$(echo $OPP | jq -r '.sell_exchange')
    
    echo "Executing: $SYMBOL (Buy: $BUY_EX, Sell: $SELL_EX)"
    
    curl -X POST http://localhost:8000/api/trades/test \
      -u admin:admin \
      -H "Content-Type: application/json" \
      -d "{
        \"symbol\": \"$SYMBOL\",
        \"buy_exchange\": \"$BUY_EX\",
        \"sell_exchange\": \"$SELL_EX\",
        \"trade_amount_usd\": 10.0
      }"
else
    echo "No opportunities found. Check liquidity:"
    curl http://localhost:8000/api/market/galaswap/liquidity | jq
fi
```

