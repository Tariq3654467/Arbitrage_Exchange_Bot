# Market Data Display

## Overview

The bot can display market data in two modes:

### 1. **Configured Trading Pairs Only** (Default: OFF)
- Shows only the trading pairs configured in `config.yaml`
- Faster loading
- Focused view on pairs you're actively trading
- Access: Uncheck "Show all available pairs" in Market page

### 2. **All Available Market Data** (Default: ON)
- Shows **all available trading pairs** from all connected exchanges
- Up to **1000 pairs per exchange** (to prevent overwhelming the API)
- Comprehensive market view
- Useful for discovering new arbitrage opportunities
- Access: Check "Show all available pairs" in Market page (now default)

## How It Works

### Backend (`/api/market/prices`)

When `all_pairs=true`:
1. For each connected exchange:
   - Loads all available markets
   - Fetches all tickers in batch (much faster)
   - Filters to active spot markets only
   - Returns bid, ask, mid prices, and spread
   - Limited to 1000 pairs per exchange for performance

When `all_pairs=false`:
1. Only shows pairs from `price_monitor.trading_pairs`
2. These are the pairs configured in `config.yaml`
3. Faster response time

### Frontend (Market Page)

- **Default:** Now shows all pairs by default
- **Toggle:** Checkbox to switch between modes
- **Display:** Shows count of loaded pairs
- **Performance:** Updates every 2 seconds

## Market Data Components

### Price Information
- **Bid Price:** Best price to sell
- **Ask Price:** Best price to buy
- **Mid Price:** (Bid + Ask) / 2
- **Spread:** Ask - Bid (difference)
- **Timestamp:** When price was fetched

### Visualizations
- **Price Trend Charts:** Shows price movement over time
- **Price Comparison:** Compare prices across exchanges
- **Spread Charts:** Visualize bid-ask spreads

## Performance Considerations

- **Batch Fetching:** Uses `fetch_tickers()` for better performance
- **Rate Limiting:** Respects exchange API rate limits
- **Caching:** Prices cached in Price Monitor for fast access
- **Update Frequency:** 2 seconds for dashboard, 100ms for bot monitoring

## Finding Opportunities

With "Show all pairs" enabled, you can:
1. Browse all available trading pairs
2. Compare prices across exchanges
3. Identify new arbitrage opportunities
4. Discover pairs with high spreads
5. Monitor market conditions broadly

## Configuration

To add pairs to the bot's trading list:
1. Edit `config/config.yaml`
2. Add pairs to `trading_pairs` section
3. Restart the bot

Example:
```yaml
trading_pairs:
  - symbol: BTC/USDT
    min_trade_amount: 0.001
    enabled: true
  - symbol: ETH/USDT
    min_trade_amount: 0.01
    enabled: true
```

## API Endpoints

- `GET /api/market/prices?all_pairs=true` - Get all market data
- `GET /api/market/prices?all_pairs=false` - Get only configured pairs
- `GET /api/market/available-pairs` - List all available pairs
- `GET /api/market/opportunities` - Get arbitrage opportunities
- `GET /api/market/spreads` - Get current spreads

