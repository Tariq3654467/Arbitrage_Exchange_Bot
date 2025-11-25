# Web Dashboard Guide

## Overview

The Arbitrage Bot includes a comprehensive web dashboard that allows you to:
- **Configure** exchange API keys and trading parameters
- **Control** the bot (start/stop/emergency stop)
- **Monitor** real-time market data and prices
- **View** arbitrage opportunities as they're detected
- **Track** trade execution and portfolio performance
- **Manage** risk parameters and balances

## Quick Start

### 1. Start the Dashboard

#### Using Docker (Recommended)
```bash
# Start all services including dashboard
docker-compose up -d

# View dashboard logs
docker-compose logs -f dashboard

# Access dashboard
# Open browser: http://localhost:8000
```

#### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Start dashboard server
python run_dashboard.py

# Access dashboard
# Open browser: http://localhost:8000
```

### 2. Login

Default credentials:
- **Username**: `admin`
- **Password**: `admin`

**⚠️ IMPORTANT**: Change these credentials in production!

To change credentials, edit `src/api/main.py`:
```python
correct_username = "your_username"
correct_password = "your_secure_password"
```

### 3. Configure Exchanges

1. Click **⚙️ Configuration** tab
2. Select exchange (Binance, OKX, or Bybit)
3. Enter API credentials:
   - API Key
   - API Secret
   - Passphrase (OKX only)
4. Click **Save Exchange Config**

Repeat for each exchange you want to use.

### 4. Configure Trading Parameters

In the **Trading Parameters** section:
- **Min Profit Threshold**: Minimum profit % to execute trade (default: 0.5%)
- **Max Trade Size**: Maximum % of capital per trade (default: 10%)
- **Max Slippage**: Maximum acceptable slippage % (default: 1.0%)

Click **Save Trading Config**

### 5. Configure Risk Management

In the **Risk Management** section:
- **Max Drawdown**: Maximum portfolio drawdown before emergency stop (default: 20%)
- **Max Daily Loss**: Maximum daily loss % before disabling trading (default: 5%)
- **Max Position Size**: Maximum USD value per trade (default: $10,000)

Click **Save Risk Config**

### 6. Start the Bot

Click **▶️ Start Bot** button

The bot will:
1. Connect to all configured exchanges
2. Initialize databases
3. Start monitoring prices
4. Begin detecting arbitrage opportunities
5. Execute profitable trades (if not in paper trading mode)

## Dashboard Features

### Control Panel

**Start Bot**: Initialize and start the trading bot
**Stop Bot**: Gracefully stop the bot
**🚨 Emergency Stop**: Immediately halt all trading (use in emergencies)
**⚙️ Configuration**: Access configuration panel

### Status Indicators

- **Green Dot**: Bot is running
- **Red Dot**: Bot is stopped
- **Uptime**: How long the bot has been running
- **Exchanges**: Number of connected exchanges

### Portfolio Metrics

**Total Value**: Current portfolio value in USD
**Daily P&L**: Today's profit/loss
**Drawdown**: Current drawdown from peak

### Trading Statistics

**Total Trades**: Number of trades executed
**Win Rate**: Percentage of profitable trades
**Total Profit**: Cumulative profit/loss

### System Status

**Uptime**: Bot runtime
**Exchanges**: Connected exchanges
**Opportunities**: Number of opportunities found

## Dashboard Tabs

### 📈 Market Data

Shows real-time prices across all exchanges:
- **Bid/Ask prices** for each trading pair
- **Price by exchange** for comparison
- **Updated every 5 seconds**

**Use this to**:
- Monitor price spreads between exchanges
- Identify manual arbitrage opportunities
- Verify exchange connections

### 💰 Opportunities

Displays recent arbitrage opportunities detected:
- Symbol
- Buy/Sell exchanges
- Prices
- Profit percentage
- Timestamp

**Use this to**:
- See what opportunities the bot is finding
- Verify profit calculations
- Understand market conditions

### 📋 Trade History

Shows executed trades:
- Time, symbol, exchanges
- Trade amount
- Actual profit (USD and %)
- Execution status

**Use this to**:
- Review past performance
- Identify successful strategies
- Debug failed trades

### 💵 Balances

Displays account balances across all exchanges:
- Asset name
- Total amount
- USD value
- Distribution across exchanges

**Use this to**:
- Monitor capital allocation
- Identify rebalancing needs
- Track asset holdings

### ⚙️ Configuration

**Exchange API Keys**: Configure CEX credentials

**Trading Parameters**: Set profit thresholds and trade sizes

**Risk Management**: Configure risk limits and safety measures

## Real-Time Updates

The dashboard uses WebSocket for real-time updates:
- **Status changes** are pushed immediately
- **Metrics update** every 5 seconds
- **Trade alerts** appear instantly
- **Errors** are shown in real-time

## Monitoring & Alerts

### On-Screen Alerts

Alerts appear at the top of the control panel:
- **Green** (Success): Successful operations
- **Yellow** (Info): Informational messages
- **Red** (Error): Errors or critical events

### Alert Types

**Bot Started**: Bot successfully initialized
**Bot Stopped**: Bot shut down normally
**Trade Executed**: Trade completed successfully
**Emergency Stop**: Emergency stop triggered
**Configuration Saved**: Settings updated
**Connection Error**: Exchange connection lost

## API Endpoints

The dashboard provides a REST API at `http://localhost:8000/api/`

### Bot Control
- `POST /api/bot/start` - Start the bot
- `POST /api/bot/stop` - Stop the bot
- `POST /api/bot/emergency-stop` - Trigger emergency stop
- `GET /api/bot/status` - Get bot status

### Configuration
- `GET /api/config/exchanges` - Get exchange config
- `POST /api/config/exchange` - Update exchange config
- `GET /api/config/trading` - Get trading config
- `POST /api/config/trading` - Update trading config
- `GET /api/config/risk` - Get risk config
- `POST /api/config/risk` - Update risk config

### Market Data
- `GET /api/market/prices` - Current prices
- `GET /api/market/opportunities` - Recent opportunities
- `GET /api/market/spreads` - Current spreads

### Portfolio
- `GET /api/portfolio/summary` - Portfolio summary
- `GET /api/portfolio/balances` - Account balances

### Trading
- `GET /api/trades/history` - Trade history
- `GET /api/trades/statistics` - Trading statistics

### Risk
- `GET /api/risk/metrics` - Current risk metrics
- `GET /api/performance/statistics` - Performance stats

## Security

### Authentication

The dashboard uses HTTP Basic Authentication:
```
Username: admin
Password: admin (CHANGE THIS!)
```

### HTTPS

For production, use HTTPS:
1. Obtain SSL certificate
2. Configure reverse proxy (nginx/Apache)
3. Or use Uvicorn with SSL:
```python
uvicorn.run(
    "src.api.main:app",
    host="0.0.0.0",
    port=8000,
    ssl_keyfile="./key.pem",
    ssl_certfile="./cert.pem"
)
```

### IP Restriction

Restrict dashboard access to specific IPs:

**Using nginx**:
```nginx
location / {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://localhost:8000;
}
```

**Using firewall**:
```bash
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw deny 8000
```

## Troubleshooting

### Dashboard won't start

**Check logs**:
```bash
docker-compose logs dashboard
```

**Common issues**:
- Port 8000 already in use
- Missing dependencies
- Database not accessible

### Can't connect to dashboard

**Verify it's running**:
```bash
curl http://localhost:8000/health
```

**Check firewall**:
```bash
sudo ufw status
```

### Real-time updates not working

**Check WebSocket connection**:
- Open browser console (F12)
- Look for WebSocket errors
- Verify no proxy blocking WebSocket

### API returns errors

**Check authentication**:
- Verify credentials are correct
- Check Authorization header

**Check bot status**:
- Bot must be running for some endpoints
- Start bot first, then query data

## Advanced Usage

### Custom Scripts

Use the API in your own scripts:

```python
import requests

# Authentication
auth = ('admin', 'admin')

# Start bot
response = requests.post(
    'http://localhost:8000/api/bot/start',
    auth=auth
)
print(response.json())

# Get status
response = requests.get(
    'http://localhost:8000/api/bot/status'
)
print(response.json())
```

### Automated Monitoring

Create monitoring scripts:

```bash
#!/bin/bash
# Check if bot is running
STATUS=$(curl -s http://localhost:8000/api/bot/status | jq -r '.is_running')

if [ "$STATUS" != "true" ]; then
    echo "Bot is not running! Sending alert..."
    # Send alert (Telegram, email, etc.)
fi
```

### Integration

Integrate with other systems:
- Trading algorithms
- Risk management systems
- Portfolio trackers
- Notification services

## Best Practices

1. **Always use paper trading mode** initially
2. **Monitor the dashboard** during first trades
3. **Set conservative risk limits** at first
4. **Start with small trade sizes**
5. **Review trade history** regularly
6. **Check balances** frequently
7. **Monitor for errors** in the logs
8. **Keep credentials secure**
9. **Use HTTPS in production**
10. **Regular backups** of configuration

## Support

For dashboard issues:
- Check logs: `docker-compose logs dashboard`
- Review API errors in browser console (F12)
- Verify database connections
- Check network/firewall settings
- Consult main documentation

## Next Steps

- Review [Operations Manual](OPERATIONS_MANUAL.md)
- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Read [Configuration Guide](CONFIGURATION_GUIDE.md)

