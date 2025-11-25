# 🚀 START HERE - Quick Launch Guide

## For Complete Beginners

Follow these exact steps to get your bot running in **5 minutes**:

### 1️⃣ Install Docker Desktop

**Windows:**
1. Download: https://www.docker.com/products/docker-desktop/
2. Run installer
3. Restart computer
4. Open Docker Desktop (wait for it to start)

**Mac:**
1. Download Docker Desktop for Mac
2. Drag to Applications
3. Launch Docker Desktop

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 2️⃣ Get Your API Keys

**Binance:**
1. Login to Binance.com
2. Go to API Management
3. Create new API key
4. Save the Key and Secret (you'll need these!)
5. Enable "Spot Trading"
6. Set IP restriction (optional but recommended)

**OKX:**
1. Login to OKX.com
2. Go to Account → API
3. Create API key
4. Save Key, Secret, and Passphrase
5. Enable trading permissions

**Bybit:**
1. Login to Bybit.com  
2. Go to API Management
3. Create API key
4. Save Key and Secret
5. Enable spot trading

### 3️⃣ Start the Bot

**Open Command Prompt (Windows) or Terminal (Mac/Linux):**

```bash
# Navigate to bot folder
cd D:\Trading_Bot\Arbitrage_bot

# Start everything
docker-compose up -d

# Wait 30 seconds for services to start...

# Check if running
docker-compose ps
```

You should see:
- ✅ arbitrage_dashboard (running)
- ✅ arbitrage_postgres (healthy)
- ✅ arbitrage_influxdb (healthy)
- ✅ arbitrage_redis (healthy)

### 4️⃣ Access Dashboard

Open your web browser and go to:
```
http://localhost:8000
```

**Login:**
- Username: `admin`
- Password: `admin`

### 5️⃣ Configure the Bot

**In the dashboard:**

1. Click **⚙️ Configuration** tab

2. **Add Exchange API Keys:**
   - Select "binance" from dropdown
   - Paste your API Key
   - Paste your API Secret
   - Click "Save Exchange Config"
   - Repeat for other exchanges

3. **Set Trading Parameters:**
   - Min Profit Threshold: `0.5` (means 0.5% minimum profit)
   - Max Trade Size: `10` (use 10% of capital per trade)
   - Max Slippage: `1.0` (1% max slippage)
   - Click "Save Trading Config"

4. **Set Risk Limits:**
   - Max Drawdown: `20` (stop if losing 20%)
   - Max Daily Loss: `5` (stop if losing 5% in one day)
   - Max Position Size: `10000` (max $10k per trade)
   - Click "Save Risk Config"

### 6️⃣ Start Trading

**IMPORTANT: Test in Paper Trading Mode First!**

Make sure in `config/config.yaml`:
```yaml
bot:
  paper_trading: true  # This simulates trades without real money
```

Then:
1. Click **▶️ Start Bot** button
2. Watch the status indicator turn green
3. Go to **📈 Market Data** tab to see live prices
4. Check **💰 Opportunities** tab to see detected arbitrage
5. View **📋 Trade History** to see executed trades

### 7️⃣ Monitor Your Bot

**What to Watch:**
- ✅ Portfolio value should stay stable or grow
- ✅ Win rate should be > 50%
- ✅ Daily P&L shows today's profit
- ✅ Opportunities should be detected regularly

**Red Flags:**
- ❌ Portfolio value dropping fast
- ❌ Many failed trades
- ❌ High slippage on trades
- ❌ Connection errors

## 🛑 How to Stop

```bash
# Stop the bot (graceful shutdown)
# Click "Stop Bot" in dashboard

# Or stop all services
docker-compose down
```

## 📱 Quick Command Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f dashboard

# Restart
docker-compose restart dashboard

# Check status
docker-compose ps

# Update after code changes
docker-compose up -d --build
```

## ⚠️ Important Safety Tips

1. **Always start with paper trading mode**
2. **Test for at least 1 week before going live**
3. **Start with small amounts** ($100-500)
4. **Monitor closely** the first few days
5. **Set conservative risk limits**
6. **Never invest more than you can afford to lose**

## 🆘 Troubleshooting

**Dashboard won't start:**
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker-compose logs dashboard

# Restart services
docker-compose restart
```

**Can't access http://localhost:8000:**
- Make sure Docker Desktop is running
- Check firewall isn't blocking port 8000
- Try http://127.0.0.1:8000 instead

**"Connection refused" errors:**
```bash
# Restart databases
docker-compose restart postgres influxdb redis

# Wait 30 seconds then retry
```

**API key errors:**
- Double-check you copied the full key (no spaces)
- Verify API key has trading permissions enabled
- Check IP whitelist settings on exchange

## 📚 Next Steps

Once running successfully:
1. ✅ Review [Dashboard Guide](docs/DASHBOARD_GUIDE.md)
2. ✅ Read [Operations Manual](docs/OPERATIONS_MANUAL.md)
3. ✅ Understand [Risk Management](docs/SETUP_GUIDE.md)
4. ✅ Join support channel for questions

## 💬 Need Help?

If you get stuck:
1. Check the logs: `docker-compose logs -f dashboard`
2. Review [Troubleshooting Guide](docs/OPERATIONS_MANUAL.md)
3. Make sure all prerequisites are installed
4. Try restarting: `docker-compose restart`

---

**You're all set! Happy trading! 🚀💰**

Remember: Start small, test thoroughly, and never risk more than you can afford to lose.

