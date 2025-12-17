# GalaSwap Dashboard Configuration Guide

Step-by-step guide to configure GalaSwap through the web dashboard.

## Prerequisites

1. Bot is running: `python main.py`
2. Dashboard is accessible: http://localhost:3000
3. You have your Gala wallet credentials:
   - Wallet Address (e.g., `client|...` or Ethereum-style address)
   - Private Key (64 hex characters)

## Step-by-Step Instructions

### Step 1: Access the Dashboard

1. Open your web browser
2. Navigate to: `http://localhost:3000`
3. Log in (if authentication is enabled)

### Step 2: Navigate to Exchange Configuration

1. Click on **"Config"** in the sidebar (or navigate to `/dashboard/config`)
2. You'll see two sections:
   - **CEX Exchanges** (Centralized exchanges like Binance)
   - **DEX Exchanges** (Decentralized exchanges like Galaswap)

### Step 3: Configure GalaSwap

1. In the **DEX Exchanges** section, find the dropdown that says **"Select DEX Exchange"**
2. Select **"galaswap"** from the dropdown

### Step 4: Enter Your Credentials

Fill in the form fields:

#### Private Key (Required)
- **Field**: "Private Key" or "API Key" field
- **Format**: 64 hexadecimal characters
- **Example**: `0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef`
- **Note**: Can include or exclude `0x` prefix

#### Wallet Address (Required for Galaswap)
- **Field**: "Wallet Address"
- **Format**: Gala wallet address
- **Example**: `client|123456789abcdef012345678` or `0x1234...`
- **Note**: This field is specifically required when selecting "galaswap"

#### RPC URL (Optional)
- **Field**: "RPC URL"
- **Default**: `https://jsonrpc.gala.games`
- **Note**: You can leave this as default or use your preferred Gala Chain RPC endpoint

#### Enable Exchange
- **Checkbox**: "Enable"
- **Action**: Check this box to activate GalaSwap
- **Note**: Uncheck to disable without deleting credentials

### Step 5: Save Configuration

1. Click the **"Save Exchange"** button
2. You should see a success notification: "DEX configured successfully!"
3. The form will clear, and GalaSwap will appear in your configured exchanges list

### Step 6: Verify Configuration

1. Check the **"Configured Exchanges"** list
2. You should see **"galaswap"** listed with:
   - Status: Enabled/Disabled
   - Type: DEX
   - Actions: Toggle enable/disable, Delete

### Step 7: Test Connection

1. Navigate to **"Balances"** page in the dashboard
2. You should see your GalaSwap balances if:
   - Credentials are correct
   - Wallet has tokens
   - Connection is successful

## Visual Guide

```
Dashboard → Config → Exchange Keys
├── CEX Exchanges
│   └── [Binance, MEXC, etc.]
│
└── DEX Exchanges
    └── Select: "galaswap"
        ├── Private Key: [Enter your private key]
        ├── Wallet Address: [Enter your wallet address]
        ├── RPC URL: [https://jsonrpc.gala.games]
        └── ☑ Enable
        └── [Save Exchange Button]
```

## Troubleshooting

### "Gala wallet address is required for Galaswap"
- **Solution**: Make sure you've entered the wallet address in the "Wallet Address" field
- The wallet address field is specifically required when selecting "galaswap"

### "Please enter your wallet private key"
- **Solution**: Enter your private key in the "Private Key" field
- Must be 64 hex characters (32 bytes)

### "DEX configured successfully!" but not working
- **Check**: Navigate to Balances page to verify connection
- **Check**: Look at bot logs for connection errors
- **Verify**: Credentials are correct (wallet address and private key match)

### Can't see GalaSwap in dropdown
- **Check**: Ensure `config.yaml` has galaswap enabled:
  ```yaml
  exchanges:
    dex:
      - name: galaswap
        enabled: true
  ```
- **Restart**: Restart the bot to reload configuration

### Credentials saved but bot not connecting
- **Check**: Bot logs for specific error messages
- **Verify**: Private key format (64 hex chars)
- **Verify**: Wallet address format
- **Test**: Try fetching balances manually

## Security Notes

✅ **Credentials are encrypted** before being stored in the database  
✅ **Private keys are never displayed** in the UI after saving  
✅ **Database encryption** protects your credentials at rest  
✅ **HTTPS recommended** for production deployments  

## Updating Credentials

To update your GalaSwap credentials:

1. Go to **Config** → **Exchange Keys**
2. Select **"galaswap"** from the dropdown
3. Enter new credentials
4. Click **"Save Exchange"**
5. The old credentials will be replaced

## Disabling GalaSwap

To temporarily disable without deleting credentials:

1. Go to **Config** → **Exchange Keys**
2. Find **"galaswap"** in the configured exchanges list
3. Click the **toggle switch** to disable
4. Or uncheck **"Enable"** when editing

## Deleting Credentials

To completely remove GalaSwap configuration:

1. Go to **Config** → **Exchange Keys**
2. Find **"galaswap"** in the configured exchanges list
3. Click the **delete/trash icon**
4. Confirm deletion

⚠️ **Warning**: This will permanently delete your credentials. You'll need to re-enter them to use GalaSwap again.

## Next Steps

After configuring GalaSwap:

1. ✅ Verify connection on **Balances** page
2. ✅ Check **Market** page for GalaSwap prices
3. ✅ Monitor **Opportunities** page for arbitrage opportunities
4. ✅ Review **Trades** page for executed trades

## Getting Your Credentials

If you don't have your Gala wallet credentials yet:

1. Visit: https://galaswap.gala.com/info/api.html
2. Follow the **"Getting your Private Key"** section
3. Copy your wallet address and private key
4. Use them in the dashboard configuration

## Support

For issues:
- Check bot logs: `logs/arbitrage_bot_*.log`
- See troubleshooting in `docs/GALASWAP_INTEGRATION.md`
- Verify API status: https://api-galaswap.gala.com

