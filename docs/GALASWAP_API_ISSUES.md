# Galaswap API Failure Analysis

## Current API Configuration

The bot is using:
- **Base URL**: `https://api-galaswap.gala.com`
- **Endpoints**:
  - `/v1/FetchAvailableTokenSwaps` - For fetching available swaps
  - `/galachain/api/asset/public-key-contract/GetPublicKey` - For public key
  - `/galachain/api/asset/token-contract/FetchBalances` - For balances
  - `/galachain/api/asset/token-contract/FetchTokenSwapsOfferedByUser` - For user swaps

## Common Error: 502 Bad Gateway

A **502 Bad Gateway** error means:
- The gateway/proxy server received an invalid response from the upstream server
- The Galaswap API server might be down, overloaded, or misconfigured

## Potential Reasons for Failures

### 1. **API Server Issues (Most Likely)**
- **Server Overload**: Galaswap API might be experiencing high traffic
- **Maintenance/Downtime**: The API might be temporarily down for maintenance
- **Rate Limiting**: Too many requests might trigger rate limits
- **Service Unavailable**: The backend service might be offline

**Symptoms:**
- 502 Bad Gateway errors
- 503 Service Unavailable
- Timeout errors
- Connection refused

**Solution:**
- Wait and retry later
- Check Galaswap status page (if available)
- Reduce request frequency
- Use circuit breaker (already implemented)

---

### 2. **Incorrect API Endpoints**
The API endpoints might have changed or be incorrect:
- `/v1/FetchAvailableTokenSwaps` might not exist
- `/galachain/api/asset/...` paths might be wrong
- API version might have changed

**How to Check:**
```bash
# Test if base URL is reachable
curl -v https://api-galaswap.gala.com

# Test specific endpoint
curl -X POST https://api-galaswap.gala.com/v1/FetchAvailableTokenSwaps \
  -H "Content-Type: application/json" \
  -d '{"offeredTokenClass":"GUSDT","wantedTokenClass":"GALA"}'
```

**Solution:**
- Check Gala Games official documentation
- Verify endpoint URLs are correct
- Update endpoints if they've changed

---

### 3. **Authentication/Authorization Issues**
Some endpoints might require:
- API keys
- Authentication tokens
- Signed requests
- Specific headers

**Current Implementation:**
- The code uses unsigned requests for read operations
- Some endpoints might require authentication

**Solution:**
- Check if endpoints require authentication
- Add API keys if needed
- Implement request signing if required

---

### 4. **Network/Firewall Issues**
Your EC2 instance might have:
- Firewall blocking outbound requests
- Network connectivity issues
- DNS resolution problems

**How to Check:**
```bash
# Test connectivity
ping api-galaswap.gala.com

# Test DNS resolution
nslookup api-galaswap.gala.com

# Test HTTPS connection
openssl s_client -connect api-galaswap.gala.com:443
```

**Solution:**
- Check AWS Security Groups (allow outbound HTTPS)
- Check UFW firewall rules
- Verify DNS settings

---

### 5. **API Structure Changes**
Gala Games might have:
- Changed API structure
- Updated response formats
- Modified required fields
- Deprecated endpoints

**How to Check:**
```bash
# Check what the API actually returns
curl -X POST https://api-galaswap.gala.com/v1/FetchAvailableTokenSwaps \
  -H "Content-Type: application/json" \
  -d '{}' -v
```

**Solution:**
- Review Gala Games API documentation
- Check for API changelog/updates
- Update code to match new structure

---

### 6. **CORS or Security Policies**
The API might:
- Block requests from certain origins
- Require specific User-Agent headers
- Have CORS restrictions
- Require referrer headers

**Solution:**
- Add appropriate headers to requests
- Check if User-Agent is required
- Verify CORS settings

---

### 7. **Invalid Request Format**
The request body might be:
- Missing required fields
- Using wrong data types
- Incorrect JSON structure
- Wrong parameter names

**Current Request Format:**
```json
{
  "offeredTokenClass": "GUSDT",
  "wantedTokenClass": "GALA"
}
```

**Solution:**
- Verify request format matches API documentation
- Check required vs optional fields
- Validate parameter names

---

## Diagnostic Steps

### Step 1: Test API Connectivity
```bash
# On your EC2 instance
curl -v https://api-galaswap.gala.com
```

**Expected:** Should return HTTP 200 or connection established
**If fails:** Network/firewall issue

---

### Step 2: Test Specific Endpoint
```bash
curl -X POST https://api-galaswap.gala.com/v1/FetchAvailableTokenSwaps \
  -H "Content-Type: application/json" \
  -d '{"offeredTokenClass":"GUSDT","wantedTokenClass":"GALA"}' \
  -v
```

**Check:**
- HTTP status code
- Response body
- Error messages

---

### Step 3: Check Bot Logs
```bash
docker compose logs dashboard | grep -i galaswap | tail -50
```

**Look for:**
- Specific error messages
- HTTP status codes
- Timeout errors
- Connection errors

---

### Step 4: Verify Configuration
```bash
# Check if Gala wallet is configured
grep GALA .env

# Check wallet address format
echo $GALA_WALLET_ADDRESS
```

**Verify:**
- Wallet address is set
- Private key is valid
- Format is correct

---

## Solutions Implemented

### 1. **Circuit Breaker Pattern**
- After 5 consecutive failures, API is disabled for 5 minutes
- Prevents spam and reduces load
- Automatically resets after cooldown

### 2. **Reduced Timeouts**
- Request timeout: 5 seconds (was 10)
- Max retries: 2 (was 3)
- Faster failure detection

### 3. **Graceful Error Handling**
- Returns empty data instead of crashing
- Logs errors at DEBUG level (reduces spam)
- Bot continues with other exchanges

### 4. **Better Error Classification**
- 502/503/504 treated as temporary errors
- Connection errors retried
- Other errors logged but don't block

---

## Recommended Actions

### Immediate (If API is Down)
1. **Disable Galaswap temporarily:**
   ```bash
   curl -X POST -u admin:admin http://localhost:8000/api/exchanges/toggle \
     -H "Content-Type: application/json" \
     -d '{"exchange_name":"galaswap","enabled":false}'
   ```

2. **Focus on Binance same-exchange arbitrage** (already configured)

3. **Monitor Galaswap status** and re-enable when API is stable

---

### Long-term (To Fix API Issues)

1. **Verify API Endpoints:**
   - Check Gala Games official documentation
   - Test endpoints manually
   - Update code if endpoints changed

2. **Check Authentication:**
   - Verify if API requires keys/tokens
   - Add authentication if needed
   - Test with authenticated requests

3. **Monitor API Status:**
   - Set up alerts for API failures
   - Check Gala Games status page
   - Monitor error rates

4. **Alternative Approaches:**
   - Use Gala Chain RPC directly (if available)
   - Use WebSocket connections (if supported)
   - Implement caching to reduce API calls

---

## Testing the Fix

After implementing fixes, test:

```bash
# 1. Restart bot
docker compose restart dashboard

# 2. Check logs
docker compose logs dashboard | grep -i galaswap

# 3. Test API endpoint
curl -X POST https://api-galaswap.gala.com/v1/FetchAvailableTokenSwaps \
  -H "Content-Type: application/json" \
  -d '{"offeredTokenClass":"GUSDT","wantedTokenClass":"GALA"}'

# 4. Check circuit breaker status
# (Will show in logs if circuit breaker is open)
```

---

## Current Status

✅ **Circuit breaker implemented** - Prevents spam and blocking
✅ **Reduced timeouts** - Faster failure detection  
✅ **Graceful degradation** - Bot continues with Binance
✅ **Better error handling** - Logs errors without crashing

⚠️ **API endpoint verification needed** - Confirm endpoints are correct
⚠️ **Authentication check needed** - Verify if auth is required
⚠️ **Network connectivity check** - Ensure EC2 can reach API

---

## Next Steps

1. **Test API connectivity** from EC2 instance
2. **Verify endpoint URLs** with Gala Games documentation
3. **Check if authentication is required**
4. **Monitor logs** for specific error messages
5. **Contact Gala Games support** if API is consistently down

The bot will continue working with Binance even if Galaswap API is down, thanks to the circuit breaker and graceful error handling.

