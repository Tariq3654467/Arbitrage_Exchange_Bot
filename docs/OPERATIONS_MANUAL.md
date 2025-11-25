# Arbitrage Bot - Operations Manual

## Table of Contents
1. [Daily Operations](#daily-operations)
2. [Monitoring](#monitoring)
3. [Common Tasks](#common-tasks)
4. [Performance Optimization](#performance-optimization)
5. [Emergency Procedures](#emergency-procedures)

## Daily Operations

### Morning Checklist
```bash
# 1. Check bot status
docker-compose ps

# 2. Check recent logs
docker-compose logs --tail=100 bot

# 3. Verify trades from last 24h
# Access Grafana dashboard or check logs for trade summary

# 4. Check risk metrics
# Review drawdown, daily P&L, portfolio value

# 5. Verify alerts are working
# You should have received daily summary alert
```

### Key Metrics to Monitor

#### Performance Metrics
- **Total Trades**: Number of executed trades
- **Win Rate**: Percentage of profitable trades
- **Average Profit**: Average profit per trade
- **Total P&L**: Cumulative profit/loss
- **Sharpe Ratio**: Risk-adjusted returns

#### Risk Metrics
- **Current Drawdown**: Distance from peak equity
- **Daily P&L**: Today's profit/loss
- **Portfolio Value**: Total capital across exchanges
- **Active Trades**: Number of concurrent trades

#### System Health
- **Bot Uptime**: How long bot has been running
- **Exchange Connections**: All should be "Connected"
- **API Rate Limits**: None should be exceeded
- **Error Rate**: Should be <1%

## Monitoring

### Using Grafana Dashboard

#### Access Dashboard
```
URL: http://your-server:3000
Username: admin
Password: (from docker-compose.yml)
```

#### Key Panels to Watch

**1. Portfolio Value Over Time**
- Shows equity curve
- Look for: Steady upward trend

**2. Opportunities Found**
- Number of arbitrage opportunities detected
- Look for: Consistent detection rate

**3. Trade Execution**
- Successful vs. failed trades
- Execution time
- Look for: >95% success rate, <5s execution

**4. Profit Distribution**
- Histogram of profits per trade
- Look for: Most trades in positive range

**5. Exchange Price Spreads**
- Current spreads between exchanges
- Look for: Opportunities when spread > threshold

### Log Monitoring

#### View Live Logs
```bash
# All logs
docker-compose logs -f

# Bot only
docker-compose logs -f bot

# Last 100 lines
docker-compose logs --tail=100 bot

# Filter for errors
docker-compose logs bot | grep -i error

# Filter for trades
docker-compose logs bot | grep -i trade
```

#### Log Files
```bash
# Application logs
tail -f logs/arbitrage_bot_$(date +%Y%m%d).log

# Error logs
tail -f logs/errors_$(date +%Y%m%d).log

# Trade logs
tail -f logs/trades_$(date +%Y%m%d).log
```

#### Important Log Messages

**Normal Operations**:
```
INFO - Successfully connected to binance
INFO - Price monitor started
INFO - Opportunity found: BTC/USDT
INFO - ✓ Trade completed successfully!
```

**Warnings** (require attention):
```
WARNING - Trading disabled: Max daily loss exceeded
WARNING - High slippage detected
WARNING - Price update delayed
```

**Errors** (require action):
```
ERROR - Exchange connection failed
ERROR - Insufficient funds
ERROR - Order execution failed
```

**Critical** (immediate action required):
```
CRITICAL - ⚠️ EMERGENCY STOP TRIGGERED
CRITICAL - Max drawdown exceeded
```

## Common Tasks

### Starting the Bot
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d bot

# Check startup was successful
docker-compose logs bot | grep -i "initialized"
docker-compose logs bot | grep -i "connected"
```

### Stopping the Bot
```bash
# Stop gracefully (allows orders to complete)
docker-compose stop bot

# Force stop (immediate)
docker-compose kill bot

# Stop all services
docker-compose down
```

### Restarting the Bot
```bash
# Restart bot only
docker-compose restart bot

# Restart with fresh configuration
docker-compose down
docker-compose up -d

# Rebuild and restart (after code changes)
docker-compose up -d --build
```

### Checking Balances
```bash
# View in logs
docker-compose logs bot | grep -i balance

# Check PostgreSQL
docker-compose exec postgres psql -U postgres -d arbitrage_bot \
  -c "SELECT * FROM balance_snapshots ORDER BY timestamp DESC LIMIT 10;"

# Check via Grafana dashboard
```

### Modifying Configuration

#### Change Trading Parameters
```bash
# 1. Stop bot
docker-compose stop bot

# 2. Edit configuration
nano config/config.yaml

# 3. Restart bot
docker-compose start bot

# 4. Verify changes in logs
docker-compose logs bot | tail -20
```

#### Common Parameter Changes

**Increase Profit Threshold**:
```yaml
trading:
  min_profit_threshold: 1.0  # From 0.5% to 1.0%
```

**Adjust Trade Size**:
```yaml
trading:
  max_trade_size_percent: 5.0  # From 10% to 5%
```

**Enable/Disable Exchange**:
```yaml
exchanges:
  cex:
    - name: binance
      enabled: false  # Disable temporarily
```

### Viewing Trade History
```bash
# Last 10 trades from database
docker-compose exec postgres psql -U postgres -d arbitrage_bot \
  -c "SELECT timestamp, symbol, buy_exchange, sell_exchange, 
      net_profit_usd, net_profit_percent 
      FROM trades 
      ORDER BY timestamp DESC 
      LIMIT 10;"

# Export to CSV
docker-compose exec postgres psql -U postgres -d arbitrage_bot \
  -c "COPY (SELECT * FROM trades) TO STDOUT CSV HEADER" > trades.csv
```

### Manual Rebalancing
```bash
# Trigger manual rebalance via bot command
# (Requires implementing CLI interface or API endpoint)

# Or manually transfer funds between exchanges:
# 1. Withdraw from Exchange A
# 2. Deposit to Exchange B
# 3. Update bot's expected balances
```

## Performance Optimization

### Reducing Latency

**1. Use Closer Server Location**
```bash
# Ping exchanges to find best location
ping binance.com
ping okx.com
ping bybit.com
```

**2. Enable WebSocket Connections**
```yaml
exchanges:
  cex:
    - name: binance
      websocket_enabled: true  # Enable WebSocket for faster updates
```

**3. Optimize Update Interval**
```yaml
performance:
  price_update_interval_ms: 50  # Reduce from 100ms to 50ms
```

### Increasing Profit

**1. Add More Trading Pairs**
```yaml
trading_pairs:
  - symbol: MATIC/USDT
    enabled: true
  - symbol: AVAX/USDT
    enabled: true
```

**2. Lower Profit Threshold** (carefully)
```yaml
trading:
  min_profit_threshold: 0.3  # Lower from 0.5% to 0.3%
  # WARNING: Ensure fees are properly calculated
```

**3. Increase Concurrent Trades**
```yaml
performance:
  max_concurrent_opportunities: 10  # From 5 to 10
```

### Optimizing Costs

**1. Use Limit Orders** (when possible)
```yaml
exchanges:
  cex:
    - name: binance
      order_type: limit  # Lower fees than market orders
```

**2. Optimize Gas Settings** (DEX)
```yaml
networks:
  bsc:
    gas_price_strategy: average  # Use 'average' instead of 'fast'
```

**3. Batch Transactions** (if possible)
- Group multiple small trades
- Reduce frequency of rebalancing

## Emergency Procedures

### Emergency Stop Activated

**What Happened**: Bot detected max drawdown or critical error

**Immediate Actions**:
```bash
# 1. Check why it was triggered
docker-compose logs bot | grep -i "emergency"

# 2. Review recent trades
docker-compose logs bot | grep -i "trade executed"

# 3. Check current balances
# (Check exchange accounts directly)

# 4. Review drawdown
# (Check Grafana or logs for portfolio value)
```

**Resolution**:
```python
# Only reset after resolving the issue!
# Reset requires manual intervention for safety

# If issue is resolved and you want to resume:
# 1. Review and fix the underlying problem
# 2. Adjust risk parameters if needed
# 3. Reset emergency stop via admin interface
#    (Implementation depends on your setup)
# 4. Restart bot
```

### Exchange Connection Lost

**Symptoms**: "Exchange connection failed" errors

**Actions**:
```bash
# 1. Check exchange status
# Visit exchange status pages
# - Binance: https://www.binance.com/en/support/announcement
# - OKX: https://www.okx.com/support/hc/en-us
# - Bybit: https://www.bybit.com/en-US/announcement-info

# 2. Check network connectivity
ping binance.com
ping okx.com

# 3. Verify API keys are still valid
# Check exchange API management pages

# 4. Check server firewall
sudo ufw status

# 5. Restart bot if needed
docker-compose restart bot
```

### Unexpected Losses

**If experiencing unexpected losses**:

**Immediate Actions**:
```bash
# 1. STOP THE BOT
docker-compose stop bot

# 2. Review recent trades
docker-compose logs bot | grep -i "trade executed" | tail -50

# 3. Calculate actual vs. expected profit
# Compare with database records

# 4. Check for issues:
# - Slippage higher than expected?
# - Fees miscalculated?
# - Price data incorrect?
# - Trade execution delays?
```

**Investigation Checklist**:
- [ ] Review trade execution logs
- [ ] Compare prices at entry vs. actual fill
- [ ] Verify fee calculations
- [ ] Check for network delays
- [ ] Review slippage on each trade
- [ ] Examine order book depth
- [ ] Check for exchange outages during trades

**Resolution**:
- Fix configuration issues
- Adjust risk parameters
- Increase profit thresholds
- Only restart when confident in fix

### Database Issues

**If database is not responding**:
```bash
# Check database status
docker-compose ps

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres

# Restore from backup if corrupted
# (See backup restoration procedure)
```

### Server Crash

**If server crashed or rebooted**:
```bash
# 1. SSH into server
ssh user@your-server

# 2. Check Docker service
sudo systemctl status docker
sudo systemctl start docker

# 3. Restart all services
cd /home/user/arbitrage_bot
docker-compose up -d

# 4. Monitor startup
docker-compose logs -f bot

# 5. Verify all services are healthy
docker-compose ps
```

## Weekly Tasks

- [ ] Review weekly performance report
- [ ] Analyze profitable vs. unprofitable pairs
- [ ] Review and adjust risk parameters
- [ ] Check for software updates
- [ ] Review and optimize gas/fee settings
- [ ] Verify backup integrity
- [ ] Review security (API keys still valid, no suspicious access)

## Monthly Tasks

- [ ] Full system backup
- [ ] Review and rotate logs
- [ ] Performance analysis and optimization
- [ ] Update dependencies if needed
- [ ] Security audit (check for unauthorized access)
- [ ] Review and rebalance target allocations
- [ ] Assess need for additional capital

## Support Contacts

**During 6-Month Support Period**:
- Critical Issues: [Phone/WhatsApp]
- General Support: [Email/Slack]
- Response Time: As per SLA

**Self-Service Resources**:
- Documentation: `/docs` folder
- Troubleshooting Guide: `TROUBLESHOOTING.md`
- Configuration Reference: `CONFIGURATION_GUIDE.md`

