# Why Is My Bot Not Executing Trades?

This guide helps you diagnose why the bot isn't executing trades even when market gaps exist.

## Quick Checklist

Run through these checks in order:

### 1. ✅ Is the Bot Running?

**Check via Dashboard:**
- Open: `http://YOUR_EC2_IP:3001`
- Look at the top status bar
- Should show: **"Running"** (green) with uptime

**Check via API:**
```bash
curl http://localhost:8000/api/bot/status
# Should return: {"is_running": true, ...}
```

**Check via Logs:**
```bash
docker compose logs dashboard | grep -i "bot.*start\|running"
```

**If NOT running:**
- Go to Dashboard → Click **"Start Bot"** button
- Or via API: `curl -X POST -u admin:admin http://localhost:8000/api/bot/start`

---

### 2. ✅ Is Paper Trading Mode DISABLED?

**Paper trading = simulated trades only (no real money)**

**Check via Dashboard:**
- Dashboard → Settings/Config
- Look for **"Paper Trading"** toggle
- Must be **OFF** for real trades

**Check via API:**
```bash
curl http://localhost:8000/api/bot/status | grep paper_trading
# Should return: "paper_trading": false
```

**Check via Config:**
```bash
grep paper_trading config/config.yaml
# Should show: paper_trading: false
```

**If paper trading is ON:**
- Dashboard → Toggle OFF
- Or via API: `curl -X POST -u admin:admin http://localhost:8000/api/bot/trading/mode -H "Content-Type: application/json" -d '{"paper_trading": false}'`

---

### 3. ✅ Are Exchanges Configured with API Keys?

**Check via Dashboard:**
- Dashboard → Exchanges
- Each exchange should show:
  - ✅ **Connected** (green)
  - ✅ **API Keys Added** (not "Not Configured")
  - ✅ **Enabled** (toggle ON)

**Check via API:**
```bash
curl http://localhost:8000/api/exchanges/status
# Should show exchanges with "connected": true
```

**If exchanges are NOT configured:**
1. Dashboard → Exchanges
2. Click on exchange (e.g., Binance)
3. Enter:
   - **API Key**
   - **API Secret**
   - **Enable** the exchange
4. Click **Save**

**Important:**
- API keys must have **Trading permissions** enabled
- For Binance: Enable "Enable Spot & Margin Trading"
- Keys must NOT have IP restrictions (or add EC2 IP to whitelist)

---

### 4. ✅ Are Trading Pairs Configured?

**Check via Dashboard:**
- Dashboard → Tokens/Pairs
- Should show list of trading pairs (e.g., BTC/USDT, ETH/USDT)
- Pairs should be **Enabled** (toggle ON)

**Check via API:**
```bash
curl http://localhost:8000/api/tokens/pairs
# Should return array of trading pairs
```

**If no pairs configured:**
1. Dashboard → Tokens
2. Click **"Auto Discover"** or **"Add Pair"**
3. Add pairs like: `BTC/USDT`, `ETH/USDT`, `BNB/USDT`
4. **Enable** each pair

**Minimum requirement:**
- Need at least **2 exchanges** with the **same trading pair** to find arbitrage
- Example: BTC/USDT on Binance AND BTC/USDT on OKX

---

### 5. ✅ Is the Bot Detecting Opportunities?

**Check via Dashboard:**
- Dashboard → Opportunities tab
- Should show opportunities with profit percentages
- Opportunities should appear in real-time

**Check via Logs:**
```bash
docker compose logs dashboard | grep -i "opportunity\|arbitrage"
# Should show: "Opportunity found: ..."
```

**Check via API:**
```bash
curl http://localhost:8000/api/market/opportunities
# Should return opportunities array
```

**If NO opportunities detected:**
- Check if exchanges are connected (Step 3)
- Check if trading pairs are configured (Step 4)
- Check if prices are being fetched:
  ```bash
  curl http://localhost:8000/api/market/prices
  ```

---

### 6. ✅ Are Opportunities Profitable Enough?

**The bot only trades if profit > minimum threshold**

**Check minimum profit threshold:**
```bash
grep min_profit_threshold config/config.yaml
# Default: 0.001% (very low)
```

**Check if opportunities meet threshold:**
- Dashboard → Opportunities
- Look at **"Net Profit %"** column
- Must be **≥ minimum threshold** (default 0.001%)

**Why opportunities might be rejected:**
- **Fees too high**: After fees, profit becomes negative
- **Slippage too high**: Price moves before execution
- **Below threshold**: Profit % < min_profit_threshold

**Check logs for rejections:**
```bash
docker compose logs dashboard | grep -i "not profitable\|trade not allowed"
# Example: "Trade not profitable enough: 0.0005%"
```

---

### 7. ✅ Is Risk Manager Allowing Trades?

**Risk manager can block trades for safety**

**Check risk status:**
```bash
curl http://localhost:8000/api/risk/metrics
# Check: "trading_enabled", "emergency_stop", "drawdown", etc.
```

**Common blocks:**
- ❌ **Trading disabled**: `"trading_enabled": false`
- ❌ **Emergency stop**: `"emergency_stop": true`
- ❌ **Max drawdown exceeded**: Portfolio down > 20% (default)
- ❌ **Max daily loss exceeded**: Lost > 5% today (default)
- ❌ **Trade size too large**: Exceeds position limits

**Check logs:**
```bash
docker compose logs dashboard | grep -i "trade not allowed"
# Example: "Trade not allowed: Max drawdown exceeded"
```

**If blocked:**
- Dashboard → Risk Management
- Review risk limits
- Reset emergency stop if needed
- Adjust limits if too restrictive

---

### 8. ✅ Do Exchanges Have Sufficient Balance?

**Bot needs funds to execute trades**

**Check balances:**
```bash
curl http://localhost:8000/api/portfolio/balances
# Should show balances for each exchange
```

**Check via Dashboard:**
- Dashboard → Portfolio
- Should show balances for each exchange
- Need sufficient balance for trading pairs

**Minimum requirements:**
- **Buy exchange**: Need quote currency (e.g., USDT to buy BTC)
- **Sell exchange**: Need base currency (e.g., BTC to sell)
- Balance must cover: Trade amount + fees

---

### 9. ✅ Are API Keys Valid and Have Permissions?

**Invalid keys = no trading**

**Test API keys:**
```bash
# Check if exchanges can fetch balances
curl http://localhost:8000/api/portfolio/balances
# If returns error, API keys might be invalid
```

**Check logs for API errors:**
```bash
docker compose logs dashboard | grep -i "api.*error\|invalid.*key\|permission"
# Example: "Invalid API key" or "Insufficient permissions"
```

**Common issues:**
- ❌ **Wrong API key/secret**: Double-check credentials
- ❌ **No trading permission**: Enable "Spot Trading" in exchange settings
- ❌ **IP restriction**: Add EC2 IP to exchange whitelist
- ❌ **Key expired/revoked**: Generate new API keys

---

### 10. ✅ Check Real-Time Logs

**Watch logs while market gap exists:**

```bash
# Follow all logs
docker compose logs -f dashboard

# Filter for trading activity
docker compose logs -f dashboard | grep -E "opportunity|trade|execute|profit"
```

**What to look for:**
- ✅ `"Opportunity found: BTC/USDT ..."`
- ✅ `"Executing trade: ..."`
- ✅ `"Trade completed successfully"`
- ❌ `"Trade not allowed: ..."`
- ❌ `"Trade not profitable enough: ..."`
- ❌ `"Error executing trade: ..."`

---

## Common Issues and Solutions

### Issue 1: "Bot is running but no opportunities detected"

**Causes:**
- Exchanges not connected
- No trading pairs configured
- Price monitoring not working

**Solution:**
1. Verify exchanges are connected (Step 3)
2. Add trading pairs (Step 4)
3. Check price feed: `curl http://localhost:8000/api/market/prices`

---

### Issue 2: "Opportunities detected but no trades executed"

**Causes:**
- Paper trading mode ON
- Profit below threshold
- Risk manager blocking
- Insufficient balance

**Solution:**
1. Disable paper trading (Step 2)
2. Lower profit threshold (if needed)
3. Check risk manager (Step 7)
4. Check balances (Step 8)

---

### Issue 3: "Trades fail immediately"

**Causes:**
- Invalid API keys
- Insufficient permissions
- Insufficient balance
- Exchange API errors

**Solution:**
1. Verify API keys (Step 9)
2. Check exchange permissions
3. Check balances (Step 8)
4. Review error logs: `docker compose logs dashboard | grep -i error`

---

### Issue 4: "Bot was working but stopped trading"

**Causes:**
- Emergency stop triggered
- Daily loss limit reached
- Drawdown limit reached
- Bot crashed/stopped

**Solution:**
1. Check bot status: `curl http://localhost:8000/api/bot/status`
2. Check risk metrics: `curl http://localhost:8000/api/risk/metrics`
3. Restart bot if needed
4. Reset emergency stop if triggered

---

## Debugging Commands

**Quick health check:**
```bash
# Bot status
curl http://localhost:8000/api/bot/status

# System health
curl http://localhost:8000/api/system/health

# Exchanges status
curl http://localhost:8000/api/exchanges/status

# Opportunities
curl http://localhost:8000/api/market/opportunities

# Risk metrics
curl http://localhost:8000/api/risk/metrics

# Balances
curl http://localhost:8000/api/portfolio/balances
```

**Check recent logs:**
```bash
# Last 50 lines
docker compose logs dashboard --tail 50

# Filter for errors
docker compose logs dashboard | grep -i error | tail -20

# Filter for trades
docker compose logs dashboard | grep -i "trade\|execute" | tail -20
```

---

## Still Not Working?

If you've checked all steps and trades still aren't executing:

1. **Share logs:**
   ```bash
   docker compose logs dashboard --tail 100 > bot_logs.txt
   ```

2. **Share system health:**
   ```bash
   curl http://localhost:8000/api/system/health > system_health.json
   ```

3. **Check configuration:**
   ```bash
   cat config/config.yaml
   cat .env | grep -v PASSWORD | grep -v KEY
   ```

4. **Verify market conditions:**
   - Are there ACTUALLY profitable opportunities?
   - After fees, slippage, and price impact?
   - Check manually: Compare prices on exchanges

---

## Expected Behavior

**When everything is working:**
1. Bot starts and connects to exchanges
2. Price monitor fetches prices every few seconds
3. Opportunities appear in dashboard when gaps exist
4. Bot analyzes profit (fees, slippage, etc.)
5. Risk manager checks if trade is allowed
6. If profitable and allowed → **Trade executes**
7. Trade result logged and displayed

**Typical trade flow in logs:**
```
INFO: Opportunity found: BTC/USDT Buy@Binance Sell@OKX profit=0.15%
INFO: Analyzing opportunity: BTC/USDT ...
INFO: ✓ Profitable opportunity: BTC/USDT ... Net: 0.12% ($1.20)
INFO: Executing trade: ...
INFO: ✓ Trade completed successfully! Profit: $1.20 (0.12%) Time: 2.5s
```

---

## Need Help?

If you're still stuck:
1. Check all 10 steps above
2. Review logs for specific error messages
3. Verify market conditions manually
4. Test with paper trading first to verify setup

