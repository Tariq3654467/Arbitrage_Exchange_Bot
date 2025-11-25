# 🔧 Quick Fix Guide - Connection Errors

## Problem: Bot can't connect to exchanges

You're seeing these errors because:
1. ❌ API keys are missing or invalid
2. ❌ System clock is out of sync (Binance timestamp error)
3. ❌ DEX private keys are empty (only needed if using DEX)

## ✅ Solution: Configure Your .env File

### Step 1: Open .env File

```cmd
notepad .env
```

### Step 2: Add Your API Keys

**For Binance ONLY (easiest start):**

```env
# ===========================================
# BINANCE API (Required)
# ===========================================
BINANCE_API_KEY=paste_your_binance_api_key_here
BINANCE_API_SECRET=paste_your_binance_secret_here
BINANCE_TESTNET=false

# ===========================================
# OTHER EXCHANGES (Optional - leave empty if not using)
# ===========================================
OKX_API_KEY=
OKX_API_SECRET=
OKX_PASSPHRASE=
OKX_TESTNET=false

BYBIT_API_KEY=
BYBIT_API_SECRET=
BYBIT_TESTNET=false

# ===========================================
# DEX (Leave empty if not using)
# ===========================================
ETH_PRIVATE_KEY=
BSC_PRIVATE_KEY=
POLYGON_PRIVATE_KEY=

# ===========================================
# DATABASE (Use these defaults for local)
# ===========================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arbitrage_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=my-token
INFLUXDB_ORG=arbitrage_org
INFLUXDB_BUCKET=price_data

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ===========================================
# GENERAL
# ===========================================
ENVIRONMENT=development
LOG_LEVEL=INFO
MIN_PROFIT_THRESHOLD=0.5
MAX_TRADE_SIZE_PERCENT=10
MAX_SLIPPAGE_PERCENT=1.0
MAX_DRAWDOWN_PERCENT=20.0
```

### Step 3: Disable Unused Exchanges

Edit `config/config.yaml`:

```yaml
exchanges:
  cex:
    - name: binance
      enabled: true      # ✅ Keep this enabled
      
    - name: okx
      enabled: false     # ❌ Disable if not using
      
    - name: bybit
      enabled: false     # ❌ Disable if not using

  dex:
    - name: pancakeswap
      enabled: false     # ❌ Disable DEX
      
    - name: uniswap_v2
      enabled: false     # ❌ Disable DEX
      
    - name: quickswap
      enabled: false     # ❌ Disable DEX
```

### Step 4: Fix Clock Sync (Binance timestamp error)

**Windows:**
```cmd
# Run as Administrator
w32tm /resync
```

**Or manually:**
1. Right-click clock in taskbar
2. Click "Adjust date/time"
3. Turn ON "Set time automatically"
4. Click "Sync now"

### Step 5: Restart the Bot

1. Stop the dashboard (Ctrl+C in terminal)
2. Restart: `python run_dashboard.py`
3. Go to dashboard: http://localhost:8000
4. Click "Start Bot"

## 🎯 How to Get Binance API Keys

1. **Login** to Binance.com
2. Go to **Profile** → **API Management**
3. Click **Create API**
4. Name it: "Arbitrage Bot"
5. Complete 2FA verification
6. **Save the API Key and Secret** (you can't see secret again!)
7. **Enable Permissions**:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ Enable Withdrawals (NOT needed, keep disabled for security)
8. **Optional but Recommended**: Set IP restriction to your server IP

## 🧪 Test with Testnet First (Recommended)

Want to test without real money?

```env
BINANCE_TESTNET=true
```

Get testnet API keys from: https://testnet.binance.vision/

## ⚠️ Security Tips

1. ✅ Never share your API keys
2. ✅ Enable IP whitelist
3. ✅ Disable withdrawal permissions
4. ✅ Start with small amounts
5. ✅ Use paper trading mode first

## 🔄 Complete Restart Process

```cmd
# 1. Stop bot
Ctrl+C

# 2. Sync clock
w32tm /resync

# 3. Edit .env
notepad .env
# Add your API keys, save and close

# 4. Edit config
notepad config/config.yaml
# Disable unused exchanges, save and close

# 5. Restart
python run_dashboard.py

# 6. Open browser
# http://localhost:8000

# 7. Click "Start Bot"
```

## ✅ Success Indicators

When working correctly, you'll see:
```
✓ Connected to Binance (mainnet)
✓ Connected to PostgreSQL
✓ Connected to InfluxDB
✓ Successfully connected to 1 exchanges
✓ Price monitor started
```

## 🆘 Still Having Issues?

**Error: "Invalid API key"**
- Double-check you copied the entire key (no spaces)
- Make sure API key has trading permissions
- Try regenerating the API key

**Error: "IP not whitelisted"**
- Either disable IP restriction on Binance
- Or add your public IP to the whitelist

**Error: "No exchanges connected"**
- Make sure at least one exchange is enabled in config.yaml
- Make sure that exchange has valid API keys in .env

**Error: "Timestamp outside recvWindow"**
- Sync your system clock: `w32tm /resync`
- Check Windows time settings
- Restart computer if needed

## 📊 Minimum Configuration

The absolute minimum to get started:

**Required:**
- ✅ Binance API key & secret
- ✅ Synchronized system clock
- ✅ Binance enabled in config.yaml

**Optional:**
- Other exchanges
- DEX connections
- Telegram alerts
- Email notifications

## 🎓 Next Steps

Once bot starts successfully:
1. Watch the "Market Data" tab for live prices
2. Check "Opportunities" tab for arbitrage detection
3. Monitor "Portfolio" for balance tracking
4. Review "Trade History" for executed trades

Start with paper trading mode first! Set in config.yaml:
```yaml
bot:
  paper_trading: true
```

