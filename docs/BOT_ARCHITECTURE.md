# Arbitrage Bot Architecture

## Overview

The Arbitrage Bot is a multi-agent system where specialized components (agents) work together to identify and execute profitable arbitrage opportunities across multiple exchanges.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARBITRAGE BOT                              │
│                      (Main Orchestrator)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────────────────────────┐
                              │                                     │
        ┌─────────────────────┴─────────────────────┐             │
        │                                             │             │
┌───────▼────────┐                          ┌────────▼────────┐    │
│  EXCHANGE       │                          │  PRICE MONITOR  │    │
│  CONNECTORS     │                          │   (Agent #1)   │    │
│  (Agents)       │                          │                 │    │
│                 │                          │ • Monitors      │    │
│ • Binance       │                          │   prices        │    │
│ • OKX           │                          │ • Detects       │    │
│ • Bybit         │                          │   opportunities │    │
│ • MEXC          │                          │ • Updates       │    │
│ • PancakeSwap   │                          │   every 100ms    │    │
│ • Uniswap       │                          └────────┬────────┘    │
│ • QuickSwap     │                                   │             │
│ • Galaswap      │                                   │             │
└─────────────────┘                                   │             │
        │                                             │             │
        │                                             ▼             │
        │                          ┌─────────────────────────────┐ │
        │                          │  ARBITRAGE CALCULATOR       │ │
        │                          │      (Agent #2)             │ │
        │                          │                              │ │
        │                          │ • Calculates fees            │ │
        │                          │ • Accounts for slippage      │ │
        │                          │ • Estimates gas costs        │ │
        │                          │ • Determines profitability   │ │
        │                          └──────────────┬──────────────┘ │
        │                                         │                 │
        │                                         ▼                 │
        │                          ┌─────────────────────────────┐ │
        │                          │     RISK MANAGER            │ │
        │                          │      (Agent #3)             │ │
        │                          │                              │ │
        │                          │ • Checks drawdown limits    │ │
        │                          │ • Validates daily loss      │ │
        │                          │ • Position size limits      │ │
        │                          │ • Emergency stop control    │ │
        │                          └──────────────┬──────────────┘ │
        │                                         │                 │
        │                                         ▼                 │
        │                          ┌─────────────────────────────┐ │
        │                          │   PORTFOLIO MANAGER         │ │
        │                          │      (Agent #4)             │ │
        │                          │                              │ │
        │                          │ • Tracks balances            │ │
        │                          │ • Manages allocation         │ │
        │                          │ • Handles rebalancing        │ │
        │                          └──────────────┬──────────────┘ │
        │                                         │                 │
        │                                         ▼                 │
        │                          ┌─────────────────────────────┐ │
        │                          │    TRADE EXECUTOR           │ │
        │                          │      (Agent #5)             │ │
        │                          │                              │ │
        │                          │ • Executes buy/sell orders  │ │
        │                          │ • Manages concurrent trades  │ │
        │                          │ • Handles order timeouts     │ │
        │                          │ • Paper/Live trading modes   │ │
        │                          └──────────────┬──────────────┘ │
        │                                         │                 │
        └─────────────────────────────────────────┘                 │
                              │                                     │
        ┌─────────────────────┴─────────────────────┐             │
        │                                             │             │
┌───────▼────────┐                          ┌────────▼────────┐    │
│  ALERT MANAGER │                          │  DATA STORAGE  │    │
│  (Agent #6)    │                          │   (Agents)     │    │
│                │                          │                │    │
│ • Telegram     │                          │ • PostgreSQL   │    │
│ • Email        │                          │   (Trades,     │    │
│ • Notifications│                          │    Opportunities)│    │
│                │                          │ • InfluxDB     │    │
│                │                          │   (Time-series)│    │
└────────────────┘                          └────────────────┘    │
                                                                    │
                              ┌─────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   WEB DASHBOARD   │
                    │   (FastAPI API)  │
                    │                  │
                    │ • REST API       │
                    │ • WebSocket      │
                    │ • Real-time data │
                    └──────────────────┘
```

## Agent Components (Working Together)

### 1. **Price Monitor Agent** (`PriceMonitor`)
**Role:** Continuously monitors prices across all exchanges
- **Frequency:** Updates every 100ms (configurable)
- **Responsibilities:**
  - Fetches real-time prices from all connected exchanges
  - Detects arbitrage opportunities (price differences)
  - Maintains price history
  - Filters opportunities by display threshold (0.01%)
- **Output:** Stream of `ArbitrageOpportunity` objects
- **Location:** `src/arbitrage/price_monitor.py`

### 2. **Arbitrage Calculator Agent** (`ArbitrageCalculator`)
**Role:** Analyzes profitability of opportunities
- **Responsibilities:**
  - Calculates trading fees (maker/taker)
  - Accounts for slippage
  - Estimates gas costs (for DEX trades)
  - Computes net profit after all costs
  - Determines optimal trade size
- **Input:** `ArbitrageOpportunity`
- **Output:** `ProfitAnalysis` (with net profit, fees, etc.)
- **Location:** `src/arbitrage/arbitrage_calculator.py`

### 3. **Risk Manager Agent** (`RiskManager`)
**Role:** Protects capital and manages risk
- **Responsibilities:**
  - Monitors portfolio drawdown
  - Tracks daily P&L
  - Enforces position size limits
  - Controls emergency stop mechanism
  - Validates trade safety before execution
- **Checks:**
  - Max drawdown percentage
  - Daily loss limits
  - Position size constraints
  - Trading enabled/disabled state
- **Location:** `src/risk/risk_manager.py`

### 4. **Portfolio Manager Agent** (`PortfolioManager`)
**Role:** Manages balances and capital allocation
- **Responsibilities:**
  - Tracks balances across all exchanges
  - Calculates total portfolio value (USD)
  - Manages asset allocation percentages
  - Handles automatic rebalancing
  - Provides portfolio snapshots
- **Location:** `src/risk/portfolio_manager.py`

### 5. **Trade Executor Agent** (`TradeExecutor`)
**Role:** Executes trades on exchanges
- **Responsibilities:**
  - Places buy orders on source exchange
  - Places sell orders on destination exchange
  - Manages concurrent trade execution (semaphore)
  - Handles order timeouts
  - Supports paper trading mode
  - Records trade results
- **Concurrency:** Limited by `max_concurrent_trades` setting
- **Location:** `src/arbitrage/trade_executor.py`

### 6. **Alert Manager Agent** (`AlertManager`)
**Role:** Sends notifications and alerts
- **Responsibilities:**
  - Sends Telegram notifications
  - Sends email alerts
  - Alerts on trades executed
  - Alerts on errors
  - Alerts on high-profit opportunities
- **Location:** `src/monitoring/alert_manager.py`

### 7. **Exchange Connector Agents** (Multiple)
**Role:** Interface with individual exchanges
- **CEX Connectors:**
  - `BinanceConnector`
  - `OKXConnector`
  - `BybitConnector`
  - `MEXCConnector`
- **DEX Connectors:**
  - `PancakeSwapConnector` (BSC)
  - `UniswapConnector` (Ethereum/Polygon)
  - `GalaswapConnector` (Gala Chain)
- **Location:** `src/exchanges/`

### 8. **Data Storage Agents**
**Role:** Persist data for analysis
- **PostgreSQL Manager:**
  - Stores trades, opportunities, balances
  - Relational data storage
- **InfluxDB Manager:**
  - Time-series data (prices, metrics)
  - Real-time analytics
- **Location:** `src/database/`

## Data Flow (How Agents Work Together)

```
1. Price Monitor → Detects Opportunity
   ↓
2. Arbitrage Calculator → Analyzes Profitability
   ↓
3. Risk Manager → Validates Trade Safety
   ↓
4. Portfolio Manager → Checks Available Capital
   ↓
5. Trade Executor → Executes Buy/Sell Orders
   ↓
6. Risk Manager → Records Trade Result
   ↓
7. Portfolio Manager → Updates Balances
   ↓
8. Alert Manager → Sends Notifications
   ↓
9. Data Storage → Saves Trade Data
```

## Communication Patterns

### 1. **Callback Pattern**
- Price Monitor uses callbacks to notify when opportunities are found
- `PriceMonitor.add_opportunity_callback()` → `Bot._on_opportunity_found()`

### 2. **Shared State**
- All agents access shared `exchanges` dictionary
- Portfolio state shared between Risk Manager and Portfolio Manager
- Settings object shared across all agents

### 3. **Async/Await Pattern**
- All agents use async/await for non-blocking operations
- Concurrent execution of multiple tasks

### 4. **Event-Driven**
- Price Monitor continuously emits opportunities
- Trade Executor emits trade results
- Alert Manager responds to events

## Configuration

All agents are configured through:
- `config/config.yaml` - Main configuration file
- Environment variables - Override defaults
- Settings class - `src/config/settings.py`

## Key Settings

```yaml
trading:
  min_profit_threshold: 0.5  # Minimum profit % to execute trades
  max_trade_size_percent: 10  # Max % of portfolio per trade
  max_slippage_percent: 1.0  # Max acceptable slippage

risk:
  max_drawdown_percent: 20  # Stop trading if drawdown > 20%
  max_daily_loss_percent: 5  # Stop trading if daily loss > 5%
  emergency_stop_enabled: true

performance:
  price_update_interval_ms: 100  # How often to check prices
  max_concurrent_opportunities: 3  # Max simultaneous trades
```

## Monitoring & Observability

- **Real-time Dashboard:** Web interface showing all agent activities
- **Logging:** Comprehensive logging at all levels
- **Metrics:** Performance metrics tracked in InfluxDB
- **Alerts:** Real-time notifications via Telegram/Email

## Summary

The bot uses a **multi-agent architecture** where specialized components work together:
- **Price Monitor** finds opportunities
- **Calculator** determines profitability
- **Risk Manager** ensures safety
- **Portfolio Manager** manages capital
- **Trade Executor** executes trades
- **Alert Manager** keeps you informed
- **Data Storage** preserves history

All agents run concurrently and communicate through callbacks, shared state, and event-driven patterns.

