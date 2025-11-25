# 🔄 Restart Instructions

## Your Bot Has Been Updated!

The arbitrage bot now features **dashboard-based exchange selection**. All exchanges start **DISABLED** by default to prevent connection errors.

---

## 🛑 Stop Current Dashboard

Press `Ctrl+C` in your terminal to stop the running dashboard.

---

## ✅ Restart with New Features

### Option 1: Simple Restart
```cmd
python run_dashboard.py
```

### Option 2: Fresh Start (Recommended)
```cmd
# Stop any running services
taskkill /f /im python.exe /t

# Clear any old processes
timeout /t 2

# Start fresh
python run_dashboard.py
```

---

## 🎯 What's New?

### 1. **Exchange Selection**
   - All exchanges disabled by default
   - Enable only the ones you want to use
   - No more "Failed to connect" errors for unused exchanges

### 2. **Dynamic Configuration**
   - Add/remove exchanges without editing files
   - Enable/disable exchanges on-the-fly
   - See which exchanges are ready to trade

### 3. **Better Status Display**
   - ✅ Enabled: Active and trading
   - ⏸️ Disabled: Configured but not active
   - ❌ No Keys: Needs configuration

---

## 📋 Quick Setup Steps

### Step 1: Restart Dashboard
```cmd
python run_dashboard.py
```

Wait for:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 2: Open Browser
```
http://localhost:8001
```

### Step 3: Configure ONE Exchange First

1. Go to **"Configuration"** tab
2. Under **"Exchange API Keys"**:
   - Exchange Type: **CEX**
   - Exchange: **Binance** (or your preferred exchange)
   - Enter your API Key and Secret
   - ✅ Check "Enable this exchange"
   - Click **"Save Exchange Config"**

### Step 4: Verify Configuration

You should see:
```
✅ Binance - CEX - ✅ Enabled
```

### Step 5: Start Bot

Click **"Start Bot"** button in dashboard.

Check logs:
```
2025-11-25 23:19:56 - ArbitrageBot - INFO - Binance connector initialized
```

---

## 🎨 Configure More Exchanges (Optional)

Once first exchange works, add more:

### For OKX:
```
Exchange Type: CEX
Exchange: OKX
API Key: [your key]
API Secret: [your secret]
Passphrase: [your passphrase]  ← OKX requires this!
✅ Enable this exchange
```

### For Bybit:
```
Exchange Type: CEX
Exchange: Bybit
API Key: [your key]
API Secret: [your secret]
✅ Enable this exchange
```

### For DEX (PancakeSwap, Uniswap):
```
Exchange Type: DEX
DEX: PancakeSwap (BSC)
Private Key: 0x... [64 hex characters]
✅ Enable this DEX
```

---

## ⚠️ Important Notes

1. **Don't Enable All at Once**
   - Start with 1-2 exchanges
   - Verify they work
   - Then add more

2. **Check System Clock** (For Binance)
   ```cmd
   w32tm /resync
   ```

3. **Valid API Keys Required**
   - Bot won't start without at least ONE enabled exchange
   - All enabled exchanges must have valid keys

4. **Disable Unused Exchanges**
   - If you don't have keys for an exchange, leave it disabled
   - This prevents connection errors

---

## 🔍 Verify Everything Works

### Check Dashboard Shows:
- ✅ At least one exchange enabled
- ✅ Bot status: "Running"
- ✅ Market prices updating

### Check Logs Show:
```
INFO - Binance connector initialized
INFO - Starting price monitoring...
INFO - Bot started successfully
```

### Should NOT See:
```
❌ ERROR - Failed to connect to okx
❌ ERROR - Failed to connect to bybit
❌ CRITICAL - Failed to initialize bot: No exchanges connected
```

---

## 🆘 If Something Goes Wrong

### Problem: "No exchanges connected"
**Solution**: Configure at least ONE exchange in dashboard

### Problem: Still seeing connection errors
**Solution**: Disable unused exchanges in the configured list

### Problem: Can't access dashboard
**Solution**: 
```cmd
# Check if port is in use
netstat -ano | findstr :8001

# Kill process if needed
taskkill /f /pid [PID]

# Restart
python run_dashboard.py
```

---

## 📚 More Help

- **Exchange Selection Guide**: `EXCHANGE_SELECTION_GUIDE.md`
- **Quick Fix**: `QUICK_FIX.md`
- **Dashboard Guide**: `docs/DASHBOARD_GUIDE.md`

---

**🚀 Ready to Trade!** 

After restarting and configuring your exchanges, your bot will only connect to the exchanges you've enabled. No more errors from unused exchanges!

