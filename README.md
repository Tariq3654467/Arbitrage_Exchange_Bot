# Arbitrage Cross-Exchange Bot (CEX/DEX)

A sophisticated cryptocurrency arbitrage trading bot that identifies and executes profitable arbitrage opportunities across multiple Centralized Exchanges (CEXs) and Decentralized Exchanges (DEXs).

## 🎯 Features

### Core Trading
- **Multi-Exchange Support**
  - CEX: Binance, OKX, Bybit
  - DEX: PancakeSwap, Uniswap V2, QuickSwap
- **Real-time Price Monitoring** with sub-second latency
- **Automated Trade Execution** with simultaneous buy/sell
- **Comprehensive Fee Calculation** including trading fees, gas, and slippage
- **Paper Trading Mode** for risk-free testing

### Risk Management
- **Emergency Stop Mechanism** to halt all trading instantly
- **Max Drawdown Protection** with configurable limits
- **Daily Loss Limits** to prevent excessive losses
- **Position Size Controls** based on available capital
- **Automatic Risk Assessment** for each trade

### Portfolio Management
- **Multi-Asset Balance Tracking** across all exchanges
- **Automatic Rebalancing** to maintain target allocation
- **Real-time Portfolio Valuation** in USD
- **Capital Allocation Management** per exchange

### Monitoring & Alerts
- **Telegram Notifications** for trades and errors
- **Email Alerts** for critical events
- **Real-time Dashboard** via Grafana
- **Comprehensive Logging** with multiple log levels
- **Performance Metrics** tracking

### Data & Analytics
- **PostgreSQL** for relational data (trades, balances, opportunities)
- **InfluxDB** for time-series data (prices, metrics)
- **Historical Data** retention and analysis
- **Performance Statistics** and reporting

## 📋 Requirements

### System Requirements
- Python 3.11+
- 4GB RAM minimum (8GB recommended)
- Low-latency internet connection
- Docker and Docker Compose (for deployment)

### API Keys Required
- Binance API key and secret
- OKX API key, secret, and passphrase
- Bybit API key and secret
- Web3 RPC endpoints (Alchemy, Infura, or similar)
- Private keys for DEX trading (BSC, Ethereum, Polygon)

### Optional Services
- Telegram Bot Token (for notifications)
- SendGrid API Key (for email alerts)

## 🚀 Quick Start

### Method 1: Web Dashboard (Recommended for Beginners)

```bash
# 1. Start the dashboard
docker-compose up -d

# 2. Access web interface
# Open browser: http://localhost:8000
# Login: admin / admin

# 3. Configure via web interface:
#    - Add exchange API keys
#    - Set trading parameters
#    - Configure risk limits
#    - Click "Start Bot"
```

### Method 2: Command Line

```bash
# 1. Clone Repository
git clone <repository-url>
cd Arbitrage_bot

# 2. Configure Environment
cp .env.example .env
nano .env  # Add your API keys

# 3. Configure Trading
nano config/config.yaml

# 4. Run with Docker
docker-compose up -d

# 5. Or run locally
pip install -r requirements.txt
python main.py
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

# RPC Endpoints
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed1.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com/

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

Features:
- ⚙️ Configure API keys and parameters
- ▶️ Start/stop bot with one click
- 📈 Real-time market data
- 💰 Live arbitrage opportunities
- 📋 Trade history and statistics
- 💵 Account balances across exchanges
- 🚨 Emergency stop button

**Grafana Dashboard** (Advanced Monitoring):
```
http://localhost:3000
Username: admin
Password: (set in docker-compose.yml)
```

Add InfluxDB as data source:
- URL: http://influxdb:8086
- Organization: arbitrage_org
- Token: (from .env)
- Bucket: price_data

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

## 🔧 Troubleshooting

### Bot Won't Start
- Check all API keys are valid
- Verify RPC endpoints are accessible
- Ensure databases are running (`docker-compose ps`)
- Check logs for specific errors

### No Opportunities Found
- Verify exchanges are connected
- Check trading pairs are configured
- Reduce MIN_PROFIT_THRESHOLD temporarily
- Ensure sufficient liquidity on exchanges

### Trades Failing
- Check account balances
- Verify order sizes meet minimum requirements
- Check network congestion (for DEX)
- Review gas price settings

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
   - Add more trading pairs
   - Connect to more exchanges
   - Optimize fee calculations

3. **Scale Up**
   - Increase max_concurrent_opportunities
   - Add more capital
   - Use multiple bot instances

## 🧪 Testing

### Paper Trading Mode
Test the bot without risking capital:
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

## 📚 Documentation Structure

```
docs/
├── SETUP_GUIDE.md          # Detailed setup instructions
├── OPERATIONS_MANUAL.md    # Day-to-day operations
├── DASHBOARD_GUIDE.md      # Web dashboard user guide
├── CONFIGURATION_GUIDE.md  # Configuration reference
├── TROUBLESHOOTING.md      # Common issues and solutions
├── API_REFERENCE.md        # REST API documentation
└── ARCHITECTURE.md         # System architecture
```

## 🤝 Support

For technical support during the 6-month support period:
- Response times as per SLA in specification
- Dedicated support channels
- Regular knowledge transfer sessions

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

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- CCXT library for unified exchange API
- Web3.py for Ethereum interactions
- All open-source contributors

---

**Version:** 1.0.0  
**Last Updated:** 2025-01-01  
**Status:** Production Ready

