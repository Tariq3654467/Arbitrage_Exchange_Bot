# GalaSwap Signature Error Fix

## Error: "Signature is invalid. DTO should be signed by [address] private key"

### Problem

This error occurs when the **wallet address doesn't match the private key** used for signing.

GalaSwap API validates that:
- The `X-Wallet-Address` header matches the private key used to sign the request
- The signature is valid for that specific wallet address

### Root Cause

The wallet address in your configuration doesn't correspond to the private key you're using.

### Solution

#### Option 1: Use Correct Wallet Address (Recommended)

1. **Get your wallet address from the private key:**
   ```python
   from eth_account import Account
   
   private_key = "your_private_key_here"
   account = Account.from_key(private_key)
   wallet_address = account.address
   print(f"Wallet address: {wallet_address}")
   ```

2. **Update your configuration:**
   - Dashboard: Config → Exchange Keys → Galaswap
   - Update **Wallet Address** to match the derived address
   - Or use the Gala-specific format if your wallet uses that

#### Option 2: Verify Your Credentials

**Check if wallet address matches private key:**

1. **If using Ethereum-style address (0x...):**
   - The address must be derived from your private key
   - Use the script above to get the correct address

2. **If using Gala format (client|...):**
   - This is Gala Chain specific
   - Ensure the wallet address is correct for your Gala account
   - The private key must be the one associated with that Gala wallet

#### Option 3: Get Wallet Address from Gala Games

1. Visit: https://galaswap.gala.com/info/api.html
2. Follow instructions to get your wallet address
3. Ensure it matches the private key you're using

### How to Fix in Dashboard

1. Go to **Config** → **Exchange Keys**
2. Select **galaswap**
3. **Verify:**
   - **Private Key**: Must be 64 hex characters
   - **Wallet Address**: Must match the private key
4. **Update** the wallet address if it doesn't match
5. Click **Save Exchange**

### How to Fix via .env

```bash
# Get wallet address from private key first
# Then set both:
GALA_WALLET_ADDRESS=0x...  # Must match private key
GALA_PRIVATE_KEY=...       # 64 hex characters
```

### Verification Script

Create a file `verify_gala_credentials.py`:

```python
from eth_account import Account

private_key = input("Enter your private key: ").strip()
if private_key.startswith('0x'):
    private_key = private_key[2:]

account = Account.from_key('0x' + private_key)
print(f"\n✅ Derived wallet address: {account.address}")
print(f"\nUse this address in your configuration:")
print(f"GALA_WALLET_ADDRESS={account.address}")
```

### Important Notes

- ✅ **Wallet address and private key MUST match**
- ✅ For Ethereum-style addresses (0x...), derive from private key
- ✅ For Gala format (client|...), use the exact address from Gala Games
- ⚠️ **Mismatched credentials will always fail signature validation**

### After Fixing

1. Restart the bot: `docker compose restart dashboard`
2. Try the trade again
3. The signature error should be resolved

