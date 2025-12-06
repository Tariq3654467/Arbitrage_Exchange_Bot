# Arbitrage Cross-Exchange Bot (CEX/DEX)

A sophisticated cryptocurrency arbitrage trading bot that identifies and executes profitable arbitrage opportunities across multiple Centralized Exchanges (CEXs) and Decentralized Exchanges (DEXs).

## 🎯 Features

### Core Trading
- **Multi-Exchange Support**
  - CEX: Binance, OKX, Bybit
  - DEX: PancakeSwap, Uniswap V2, GalaSwap
- **Real-time Price Monitoring** with sub-second latency
- **Automated Trade Execution** with simultaneous buy/sell
- **Comprehensive Fee Calculation** including trading fees, gas, and slippage
- **Paper Trading Mode** for risk-free testing
- **Token List Management** - Add, edit, and manage trading pairs via web UI

### Risk Management
- **Emergency Stop Mechanism** (Kill Switch) to halt all trading instantly
- **Max Drawdown Protection** with configurable limits
- **Daily Loss Limits** to prevent excessive losses
- **Position Size Controls** based on available capital
- **Automatic Risk Assessment** for each trade
- **Enhanced Risk Controls** via web dashboard

### Portfolio Management
- **Multi-Asset Balance Tracking** across all exchanges
- **Automatic Rebalancing** to maintain target allocation
- **Manual Rebalancing** with one-click trigger
- **Real-time Portfolio Valuation** in USD
- **Capital Allocation Management** per exchange and asset
- **Rebalancing Panel** with visual allocation tracking

### Web Dashboard Features
- **Modern Web UI** - Clean, responsive interface
- **Real-time Market Data** - Live prices, spreads, and opportunities
- **Token Management** - Add/edit/delete trading pairs
- **Rebalancing Control** - Set target allocation and trigger rebalancing
- **Backtesting UI** - Test strategies on historical data
- **System Health Monitoring** - Component status, logs, and diagnostics
- **Enhanced Transaction History** - Filters and CSV export
- **Paper Trading Toggle** - Switch between paper and live trading
- **Emergency Stop Button** - Prominent kill switch in header
- **Risk Control Settings** - Configure all risk parameters via UI

### Monitoring & Alerts
- **Telegram Notifications** for trades and errors
- **Email Alerts** for critical events
- **System Health Dashboard** (without Grafana)
- **Comprehensive Logging** with multiple log levels
- **Performance Metrics** tracking
- **Real-time WebSocket Updates**

### Data & Analytics
- **PostgreSQL** for relational data (trades, balances, opportunities)
- **InfluxDB** for time-series data (prices, metrics)
- **Historical Data** retention and analysis
- **Performance Statistics** and reporting
- **Trade History Export** - CSV export functionality

## 📋 Requirements

### System Requirements
- Python 3.11+
- 4GB RAM minimum (8GB recommended)
- Low-latency internet connection
- Docker and Docker Compose (for deployment)
- Node.js 18+ (for frontend)

### API Keys Required
- Binance API key and secret
- OKX API key, secret, and passphrase
- Bybit API key and secret
- Web3 RPC endpoints (Alchemy, Infura, or similar)
- Private keys for DEX trading (BSC, Ethereum, Polygon, Gala)

### Optional Services
- Telegram Bot Token (for notifications)
- SendGrid API Key (for email alerts)

## 🚀 Quick Start

### Method 1: Web Dashboard (Recommended)

```bash
# 1. Start the dashboard
python run_dashboard.py

# 2. Access web interface
# Open browser: http://localhost:8000
# Login: admin / admin (CHANGE THIS!)

# 3. Configure via web interface:
#    - Add exchange API keys (Settings)
#    - Set trading parameters (Settings)
#    - Configure risk limits (Settings)
#    - Add trading pairs (Token List)
#    - Set portfolio allocation (Rebalancing)
#    - Click "Start Bot" in header
```

### Method 2: Command Line

```bash
# 1. Clone Repository
git clone <repository-url>
cd Arbitrage_bot

# 2. Install Dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. Configure Environment
cp .env.example .env
nano .env  # Add your API keys

# 4. Configure Trading
nano config/config.yaml

# 5. Run Dashboard
python run_dashboard.py
```

## ⚙️ Configuration

### Environment Variables (.env)
Key environment variables to configure:

```bash
# General
ENVIRONMENT=production
LOG_LEVEL=INFO

# CEX API Keys
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
OKX_API_KEY=your_key
OKX_API_SECRET=your_secret
OKX_PASSPHRASE=your_passphrase
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret

# DEX Private Keys (KEEP SECURE!)
ETH_PRIVATE_KEY=your_private_key
BSC_PRIVATE_KEY=your_private_key
POLYGON_PRIVATE_KEY=your_private_key
GALA_PRIVATE_KEY=your_private_key
GALA_RPC_URL=https://jsonrpc.gala.games

# RPC Endpoints
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed1.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com/

# Database
POSTGRES_URL=postgresql://user:password@localhost:5432/arbitrage_bot
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token
INFLUXDB_ORG=arbitrage_org
INFLUXDB_BUCKET=price_data

# Trading Parameters
MIN_PROFIT_THRESHOLD=0.5
MAX_TRADE_SIZE_PERCENT=10
MAX_SLIPPAGE_PERCENT=1.0
MAX_DRAWDOWN_PERCENT=20.0
```

### Configuration File (config/config.yaml)
Main configuration includes:
- Bot settings (paper_trading mode)
- Trading parameters (profit thresholds, slippage)
- Risk management (drawdown, daily loss limits)
- Exchange configuration (enabled/disabled)
- Trading pairs
- Rebalancing settings
- Monitoring and alerts

## 📊 Web Dashboard

**Primary Dashboard** (Modern Web UI):
```
http://localhost:8000
Username: admin
Password: admin (CHANGE THIS!)
```

### Dashboard Pages

1. **Overview** (`/dashboard`)
   - Key metrics and statistics
   - Bot status and risk metrics
   - Recent activity

2. **Market** (`/dashboard/market`)
   - Live price feeds
   - Market data across exchanges
   - Spread analysis

3. **Opportunities** (`/dashboard/opportunities`)
   - Detected arbitrage opportunities
   - Profit calculations
   - Real-time updates

4. **Trades** (`/dashboard/trades`)
   - Trade history with filters
   - CSV export functionality
   - Trade statistics

5. **Balances** (`/dashboard/balances`)
   - Account balances across exchanges
   - Portfolio valuation
   - Asset distribution

6. **Token List** (`/dashboard/tokens`) ⭐ NEW
   - Add/edit/delete trading pairs
   - Enable/disable pairs
   - Manage token list

7. **Rebalancing** (`/dashboard/rebalance`) ⭐ NEW
   - Current vs target allocation
   - Manual rebalancing trigger
   - Visual allocation tracking

8. **Backtesting** (`/dashboard/backtest`) ⭐ NEW
   - Historical strategy testing
   - Performance metrics
   - Configurable parameters

9. **System Health** (`/dashboard/health`) ⭐ NEW
   - Component status monitoring
   - Database connections
   - System logs viewer

10. **Settings** (`/dashboard/config`)
    - Exchange API configuration
    - Trading parameters
    - Risk management settings
    - Paper trading mode toggle ⭐ NEW

### Key Features
- ⚙️ Configure API keys and parameters
- ▶️ Start/stop bot with one click
- 🚨 Emergency stop button (kill switch)
- 📈 Real-time market data
- 💰 Live arbitrage opportunities
- 📋 Trade history with filters and export
- 💵 Account balances across exchanges
- 🪙 Token list management
- ⚖️ Portfolio rebalancing
- 🧪 Backtesting interface
- 🏥 System health monitoring

## 🔒 Security Best Practices

1. **Never commit sensitive data** (.env, private keys)
2. **Use IP whitelisting** for exchange API keys
3. **Enable 2FA** on all exchange accounts
4. **Use separate API keys** for each bot instance
5. **Limit API permissions** to trading only (no withdrawals)
6. **Encrypt private keys** in production
7. **Use hardware wallets** for significant capital
8. **Regular security audits** of the system
9. **Monitor for unusual activity** via alerts
10. **Keep software updated** to latest versions
11. **Change default dashboard password** immediately
12. **Use HTTPS in production** for dashboard access

## 🔧 Troubleshooting

### Bot Won't Start
- Check all API keys are valid
- Verify RPC endpoints are accessible
- Ensure databases are running (`docker-compose ps`)
- Check logs for specific errors
- Review System Health page

### No Opportunities Found
- Verify exchanges are connected
- Check trading pairs are configured (Token List page)
- Reduce MIN_PROFIT_THRESHOLD temporarily
- Ensure sufficient liquidity on exchanges

### Trades Failing
- Check account balances
- Verify order sizes meet minimum requirements
- Check network congestion (for DEX)
- Review gas price settings

### Dashboard Not Loading
- Check frontend is running (`npm run dev` in frontend/)
- Verify backend API is accessible
- Check browser console for errors
- Review System Health page

### High Gas Fees
- Adjust gas_price_strategy in config
- Set max_gas_price_gwei limits
- Wait for lower network congestion

## 📈 Performance Optimization

1. **Reduce Latency**
   - Deploy near exchange servers
   - Use WebSocket connections
   - Optimize price_update_interval

2. **Increase Profitability**
   - Add more trading pairs (Token List)
   - Connect to more exchanges
   - Optimize fee calculations
   - Use rebalancing for optimal allocation

3. **Scale Up**
   - Increase max_concurrent_opportunities
   - Add more capital
   - Use multiple bot instances

## 🧪 Testing

### Paper Trading Mode
Test the bot without risking capital:
1. Go to Settings → Paper Trading Mode
2. Enable Paper Trading
3. Start the bot
4. Monitor trades in Paper Trading mode

Or via config:
```yaml
# config/config.yaml
bot:
  paper_trading: true
```

### Testnet Mode
Use exchange testnets:
```bash
# .env
BINANCE_TESTNET=true
OKX_TESTNET=true
BYBIT_TESTNET=true
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

```
docs/
├── SETUP_GUIDE.md          # Detailed setup instructions
├── OPERATIONS_MANUAL.md    # Day-to-day operations
├── DASHBOARD_GUIDE.md      # Web dashboard user guide
├── NEW_FEATURES.md         # New features documentation ⭐
├── BOT_ARCHITECTURE.md     # System architecture
├── MARKET_DATA.md          # Market data display guide
└── TROUBLESHOOTING.md      # Common issues and solutions
```

### Quick Links
- **New Features**: See `docs/NEW_FEATURES.md` for all new features
- **Dashboard Guide**: See `docs/DASHBOARD_GUIDE.md` for dashboard usage
- **Setup**: See `docs/SETUP_GUIDE.md` for detailed setup

## 🆕 What's New (v1.1.0)

### New Features
- ✅ **Token List Management** - Add/edit/delete trading pairs via web UI
- ✅ **Rebalancing Panel** - Visual portfolio allocation and manual rebalancing
- ✅ **Backtesting UI** - Historical strategy testing interface
- ✅ **System Health Monitoring** - Component status and system logs
- ✅ **Enhanced Risk Controls** - Emergency stop toggle and improved settings
- ✅ **Paper Trading Toggle** - Switch modes via web UI
- ✅ **Enhanced Transaction History** - Filters and CSV export
- ✅ **Emergency Stop Button** - Prominent kill switch in header
- ✅ **Improved UI/UX** - Modern, responsive design throughout

### Improvements
- Better error handling and logging
- Enhanced API endpoints for advanced features
- Improved navigation and user experience
- Real-time updates via WebSocket
- Comprehensive documentation

## 🤝 Support

For technical support:
1. Check documentation in `docs/` folder
2. Review System Health page in dashboard
3. Check system logs
4. Review troubleshooting section above

## ⚠️ Disclaimer

**USE AT YOUR OWN RISK**

This bot is for educational and research purposes. Cryptocurrency trading carries significant risk. You may lose all your capital. The authors and contributors are not responsible for any financial losses incurred.

- Always start with paper trading
- Test thoroughly on testnets
- Start with small amounts
- Never invest more than you can afford to lose
- Understand the risks of leverage and margin trading
- Be aware of market manipulation and flash crashes
- Monitor the bot constantly, especially initially
- Use emergency stop if needed

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- CCXT library for unified exchange API
- Web3.py for Ethereum interactions
- FastAPI for backend framework
- Next.js for frontend framework
- All open-source contributors

---

**Version:** 1.1.0  
**Last Updated:** December 2024  
**Status:** Production Ready
