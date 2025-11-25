# 🔄 Exchange Selection Guide

## Overview

Your arbitrage bot now has a **dynamic exchange selection system** where you can:
- Choose which CEX/DEX exchanges to use
- Enable/disable exchanges on-the-fly
- Configure API keys directly in the dashboard
- See which exchanges are ready to trade

## 🎯 Quick Start

### 1. **All Exchanges Start DISABLED**
   - By default, NO exchanges are enabled in `config/config.yaml`
   - This prevents connection errors when API keys are not configured

### 2. **Add Exchange via Dashboard**
   1. Open dashboard: http://localhost:8001
   2. Go to **"Configuration"** tab
   3. Under **"Exchange API Keys"** section:
      - Select exchange type: CEX or DEX
      - Choose the exchange
      - Enter API credentials
      - Click "Save Exchange Config"

### 3. **Enable/Disable Exchanges**
   - After saving, you'll see a list of configured exchanges
   - Use the **Enable/Disable** button to toggle each exchange
   - Bot will only connect to ENABLED exchanges

---

## 📋 Available Exchanges

### Centralized Exchanges (CEX)
| Exchange | Testnet | Passphrase Required |
|----------|---------|---------------------|
| Binance  | ✅      | ❌                  |
| OKX      | ✅      | ✅ Yes              |
| Bybit    | ✅      | ❌                  |

### Decentralized Exchanges (DEX)
| Exchange    | Blockchain | Router Required |
|-------------|------------|-----------------|
| PancakeSwap | BSC        | ✅              |
| Uniswap V2  | Ethereum   | ✅              |
| QuickSwap   | Polygon    | ✅              |

---

## 🔑 Configuring Exchanges

### **CEX Configuration**

1. **Select Exchange Type**: CEX
2. **Choose Exchange**: Binance, OKX, or Bybit
3. **Enter Credentials**:
   ```
   API Key:    [Your API Key]
   API Secret: [Your API Secret]
   Passphrase: [Only for OKX]
   ```
4. **Enable Exchange**: Check the box
5. **Click Save**

### **DEX Configuration**

1. **Select Exchange Type**: DEX
2. **Choose DEX**: PancakeSwap, Uniswap V2, or QuickSwap
3. **Enter Credentials**:
   ```
   Private Key: [Your wallet private key starting with 0x...]
   ```
   ⚠️ **Warning**: Never share your private key!
4. **Enable DEX**: Check the box
5. **Click Save**

---

## ✅ Exchange Status Indicators

| Status | Meaning |
|--------|---------|
| ✅ **Enabled** | Exchange has valid keys and is actively trading |
| ⏸️ **Disabled** | Exchange has keys but is temporarily disabled |
| ❌ **No Keys** | Exchange needs API keys configured |

---

## 🔧 Troubleshooting

### Problem: "Failed to connect to [exchange]"

**Solution**:
1. Check if exchange is enabled in config
2. Verify API keys are correct
3. For Binance: Sync your system clock
   ```cmd
   w32tm /resync
   ```
4. Check exchange status page for outages

### Problem: "No exchanges connected"

**Solution**:
1. At least ONE exchange must be configured AND enabled
2. Go to dashboard → Configuration
3. Add API keys for at least one exchange
4. Enable the exchange
5. Restart the bot

### Problem: DEX shows "Private key must be exactly 32 bytes"

**Solution**:
- Either disable the DEX in dashboard
- Or add a valid private key (64 hex characters)
- Format: `0x` + 64 hex digits

---

## 📊 Monitoring Exchanges

### Dashboard Shows:
- **Configured Exchanges**: List of all added exchanges
- **Status**: Whether they're enabled/disabled
- **Last Updated**: When keys were last modified

### Logs Show:
```
2025-11-25 23:19:56 - ArbitrageBot - INFO - Binance connector initialized
2025-11-25 23:19:56 - ArbitrageBot - ERROR - Failed to connect to okx
```

---

## 🎨 Best Practices

### 1. **Start with One Exchange**
   - Configure and test ONE exchange first
   - Verify it connects successfully
   - Then add more exchanges

### 2. **Use Testnet First**
   - Enable testnet mode when configuring
   - Test with fake funds first
   - Switch to mainnet when ready

### 3. **Monitor Regularly**
   - Check dashboard for connection status
   - Watch for API rate limits
   - Review trade execution logs

### 4. **Disable Unused Exchanges**
   - Don't leave exchanges enabled if not trading
   - Reduces API calls and rate limit issues
   - Improves bot performance

---

## 🔐 Security Tips

1. **API Key Permissions**:
   - Only enable "Read" and "Trade" permissions
   - NEVER enable "Withdraw" permission
   - Use IP whitelist if available

2. **Private Keys**:
   - Never commit private keys to git
   - Store securely in dashboard only
   - Use separate wallet for bot trading

3. **Encryption**:
   - All keys are encrypted in database
   - Encryption key stored in `.env`
   - Keep `.env` file secure

---

## 🚀 Quick Commands

### Check Configured Exchanges
```bash
# In PostgreSQL
SELECT exchange_name, exchange_type, enabled FROM api_keys;
```

### Enable All Configured Exchanges
```bash
# In PostgreSQL
UPDATE api_keys SET enabled = true WHERE exchange_name IN ('binance', 'okx');
```

### Disable Specific Exchange
```bash
# In PostgreSQL
UPDATE api_keys SET enabled = false WHERE exchange_name = 'bybit';
```

---

## 📝 Example Workflow

### Starting Fresh:

1. **Install & Setup**
   ```cmd
   setup_local.bat
   ```

2. **Start Dashboard**
   ```cmd
   python run_dashboard.py
   ```

3. **Open Browser**
   - Go to: http://localhost:8001

4. **Configure Binance**
   - Exchange Type: CEX
   - Exchange: Binance
   - Add API Key & Secret
   - Enable: ✅
   - Save

5. **Start Bot**
   - Click "Start Bot" in dashboard
   - Check logs for "Binance connector initialized"

6. **Add More Exchanges**
   - Repeat for OKX, Bybit, etc.
   - Bot will use all enabled exchanges

---

## 🆘 Need Help?

- Check `logs/arbitrage_bot.log` for detailed errors
- Review `QUICK_FIX.md` for common issues
- Ensure PostgreSQL is running
- Verify API keys are correct on exchange website

---

**🎉 You're Ready!** Configure your exchanges and start trading!

