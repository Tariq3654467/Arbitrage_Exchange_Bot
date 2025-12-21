# GalaSwap V3 DEX Migration Guide

## Overview

GalaSwap has migrated from a **swap-based peer-to-peer system** to a **V3 DEX (Uniswap V3-style)** with concentrated liquidity pools.

## Key Changes

### 1. Architecture Change
- **Old**: Peer-to-peer swaps (users create/accept swap offers)
- **New**: Liquidity pools with concentrated liquidity (like Uniswap V3)

### 2. Token Format
- **Old Format**: Dict object
  ```json
  {
    "collection": "GALA",
    "category": "Unit",
    "type": "none",
    "additionalKey": "none"
  }
  ```
- **New Format**: Composite key string
  ```
  "GALA$Unit$none$none"
  ```

### 3. API Endpoints

#### New Endpoints (V3 DEX)
- `GET /v1/trade/quote` - Get trading quotes
- `GET /v1/trade/price` - Get token price
- `POST /v1/trade/price-multiple` - Get multiple token prices
- `GET /v1/trade/pool` - Get pool details
- `GET /v1/trade/position` - Get position details
- `GET /v1/trade/positions` - Get all user positions
- `POST /price-oracle/subscribe-token` - Subscribe to price updates
- `GET /price-oracle/fetch-price` - Get historical prices

#### Old Endpoints (May be Deprecated)
- `POST /v1/FetchAvailableTokenSwaps` - Old swap-based API
- `POST /v1/RequestTokenSwap` - Old swap-based API
- `POST /v1/BatchFillTokenSwap` - Old swap-based API

### 4. Fee Tiers
V3 uses fee tiers:
- **500** = 0.05% (stable pairs like USDC/USDT)
- **3000** = 0.30% (standard pairs like ETH/USDC)
- **10000** = 1.00% (exotic pairs)

## Migration Status

### ✅ Completed
- [x] Updated API base URL to `https://dex-backend-prod1.defi.gala.com`
- [x] Added token format conversion functions
- [x] Updated `get_ticker()` to use `/v1/trade/price`
- [x] Updated `_make_unsigned_request()` to handle GET requests
- [x] Improved error logging

### ⚠️ In Progress
- [ ] Update `get_order_book()` to use new DEX endpoints
- [ ] Find and implement execution endpoints (POST for trades)
- [ ] Update `place_market_order()` for V3 DEX
- [ ] Add support for fee tiers
- [ ] Add support for price oracle endpoints

### ❌ Missing
- [ ] **Execution endpoints** - We need POST endpoints for actually placing trades
  - Likely: `/v1/trade/swap` or similar
  - May require signed requests
  - Need to check official documentation

## Current Issues

1. **Circuit Breaker Opening**: The old swap-based endpoints are failing, causing the circuit breaker to open
2. **Missing Execution Endpoints**: We don't have the POST endpoints for executing trades
3. **Token Format Mismatch**: Some code still uses old dict format instead of composite key

## Next Steps

1. **Find Execution Endpoints**: Check the full API documentation for POST endpoints to execute trades
2. **Update Order Book**: Use `/v1/trade/quote` to build order book from pool liquidity
3. **Update Trade Execution**: Implement new trade execution using V3 DEX endpoints
4. **Test New Endpoints**: Verify all new endpoints work correctly

## Resources

- **Official Docs**: https://swap.gala.com/doc/trading-endpoints
- **Base URL**: https://dex-backend-prod1.defi.gala.com
- **Price Oracle**: `/price-oracle/fetch-price` for historical data

## Helper Functions Added

```python
# Convert token class dict to composite key
token_class_to_composite_key({"collection": "GALA", ...})
# Returns: "GALA$Unit$none$none"

# Convert composite key back to dict
composite_key_to_token_class("GALA$Unit$none$none")
# Returns: {"collection": "GALA", "category": "Unit", ...}
```

