# Troubleshooting Guide

## Galaswap Connection Issues

### Error: "Non-hexadecimal digit found"

**Symptoms:**
```
ERROR - Failed to connect to galaswap: Non-hexadecimal digit found
```

**Cause:**
The Gala private key is not in the correct hexadecimal format. Private keys for Ethereum-compatible chains (including Gala Chain) must be:
- Exactly 64 hexadecimal characters (32 bytes)
- Can optionally start with `0x` prefix
- Must only contain characters: 0-9, a-f, A-F

**Common Issues:**
1. **Empty or missing private key** - Private key not configured
2. **Invalid characters** - Contains non-hex characters (e.g., spaces, special characters)
3. **Wrong length** - Not exactly 64 hex characters
4. **Wrong format** - Not a hex string (e.g., base64, mnemonic phrase)

**Solution:**

1. **Check your private key format:**
   ```bash
   # Valid formats:
   0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
   1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
   
   # Invalid formats:
   # - Too short: 0x1234...
   # - Too long: 0x1234... (more than 66 chars with 0x)
   # - Contains spaces: "0x 1234..."
   # - Base64: not hex format
   # - Mnemonic: "word1 word2 word3..."
   ```

2. **Verify in configuration:**
   - Check `config/config.yaml` for `gala_private_key`
   - Check environment variable `GALA_PRIVATE_KEY`
   - Check database if using dashboard configuration

3. **Format requirements:**
   - Remove any whitespace
   - Ensure it's exactly 64 hex characters (after removing `0x` if present)
   - Only use: 0-9, a-f, A-F

4. **Example of correct format:**
   ```yaml
   # In config.yaml or environment
   gala_private_key: "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
   # OR without 0x prefix:
   gala_private_key: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
   ```

5. **If using dashboard:**
   - Go to Configuration page
   - Select "Galaswap" DEX
   - Enter private key in "Wallet Private Key" field
   - Ensure no extra spaces or characters
   - Must be 64 hex characters (with or without 0x)

**Validation:**
The bot now validates private keys before attempting connection and will show clear error messages:
- "Invalid private key length: expected 64 hex characters, got X"
- "Invalid private key format: contains non-hexadecimal characters"

### Error: "Failed to fetch public key: 400"

**Symptoms:**
```
ERROR - Error connecting to Galaswap: Failed to fetch public key: 400
ERROR - Failed to connect to galaswap: Failed to fetch public key: 400
```

**Cause:**
The GalaConnect API is returning a 400 Bad Request when trying to fetch the public key. This can happen if:
1. **Invalid wallet address format** - The wallet address doesn't match expected format
2. **Wallet doesn't exist** - The wallet hasn't been created on Gala Chain yet
3. **API endpoint changed** - The GalaConnect API endpoint or format may have changed
4. **Network/API issues** - Temporary API problems

**Solution:**

1. **Check wallet address format:**
   - Gala wallet addresses typically have format: `"client|123456789abcdef012345678"`
   - Or Ethereum-style: `"0x1234567890abcdef..."`
   - Ensure no extra spaces or characters

2. **Verify wallet exists:**
   - The wallet must exist on Gala Chain
   - If it's a new wallet, it may need to be initialized first
   - Check Gala Games documentation for wallet creation

3. **Provide public key manually:**
   - If you have the public key, provide it in configuration:
   ```yaml
   gala_public_key: "your_base64_public_key_here"
   ```
   - This will skip the API fetch and use the provided key

4. **Connection will still work:**
   - The bot now handles this gracefully
   - Connection will proceed with a warning if public key fetch fails
   - Some operations may require the public key, but basic connection will work
   - Balances and market data should still function

5. **Check logs for details:**
   - The improved error handling will show the API's error message
   - Look for: `"Failed to fetch public key from API (status 400): [error message]"`

**Note:** The bot will now connect even if public key fetch fails, but some advanced operations may require it.

## Other Common Issues

### Binance: Order Book Fetch Errors

**Symptoms:**
```
ERROR - Error fetching Binance order book for ETH/USDT: binance GET https://api.binance.com/api/v3/depth?symbol=ETHUSDT&limit=10
ERROR - Error monitoring price for binance ETH/USDT: ...
```

**Causes:**
1. **Rate Limiting** - Too many requests to Binance API
2. **Network Issues** - Connection problems or timeouts
3. **Invalid Symbol** - Symbol format mismatch (e.g., using wrong separator)
4. **API Key Issues** - Invalid or restricted API key
5. **Binance API Downtime** - Temporary service issues

**Solutions:**

1. **Check Rate Limits:**
   - Binance has strict rate limits (1200 requests per minute for order book)
   - Reduce `price_update_interval_ms` in config (default: 100ms = 600 requests/min per symbol)
   - If monitoring multiple symbols, reduce update frequency
   - Example: Set to 200ms for 300 requests/min per symbol

2. **Verify Symbol Format:**
   - Binance uses format: `ETHUSDT` (no separator)
   - Bot uses format: `ETH/USDT` (with separator)
   - CCXT handles conversion automatically, but verify in config

3. **Check API Key:**
   - Ensure API key is valid and not expired
   - Check API key permissions (read-only should work)
   - Verify IP whitelist if enabled

4. **Network/API Status:**
   - Check internet connection
   - Visit https://www.binance.com/en/support/announcement for API status
   - Check if Binance is accessible from your location

5. **Error Details:**
   - The bot now logs detailed error messages
   - Check logs for specific error type (RateLimitExceeded, NetworkError, etc.)
   - Rate limit errors will show "Rate limit exceeded" message
   - Network errors will show connection issues

**Configuration:**
```yaml
performance:
  price_update_interval_ms: 200  # Increase to reduce API calls (default: 100)
```

### Binance: "Batch ticker fetch failed"

**Symptoms:**
```
WARNING - Batch ticker fetch failed for binance, falling back to individual
```

**Cause:**
Binance API rate limiting or temporary API issue. The bot automatically falls back to individual ticker fetches.

**Solution:**
- This is usually temporary and handled automatically
- If persistent, check Binance API status
- Consider reducing `price_update_interval_ms` in config

### Exchange Connection Timeouts

**Symptoms:**
```
ERROR - Failed to connect to [exchange]
```

**Causes:**
1. Invalid API keys
2. Network connectivity issues
3. Exchange API downtime
4. Rate limiting

**Solution:**
1. Verify API keys are correct
2. Check network connection
3. Check exchange API status
4. Wait and retry

## Getting Help

If issues persist:
1. Check logs for detailed error messages
2. Verify all configuration values
3. Ensure API keys are valid and have correct permissions
4. Check exchange API documentation for requirements

