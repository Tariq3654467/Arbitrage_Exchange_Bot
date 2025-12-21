# GalaSwap API Endpoints Reference

## Base URL

**Current (Updated)**: `https://dex-backend-prod1.defi.gala.com`  
**Previous**: `https://api-galaswap.gala.com` (deprecated)

Can be overridden via environment variable:
```bash
GALASWAP_API_BASE_URL=https://dex-backend-prod1.defi.gala.com
```

## Official Documentation

- **Trading Endpoints**: https://swap.gala.com/doc/trading-endpoints
- **Main Website**: https://swap.gala.com/

## Important: API Migration

**GalaSwap has migrated from a swap-based API to a V3 DEX (Uniswap V3-style) with concentrated liquidity.**

### Key Changes:
1. **Token Format**: Now uses composite key format: `"GALA$Unit$none$none"` instead of dict objects
2. **Architecture**: V3 DEX with liquidity pools (not peer-to-peer swaps)
3. **Fee Tiers**: 0.05%, 0.30%, 1.00% (500, 3000, 10000 in API)
4. **Price Ranges**: Tick-based system for concentrated liquidity

### Token Format

**New Format (Composite Key)**: `"collection$category$type$additionalKey"`

Examples:
- `"GALA$Unit$none$none"` - GALA token
- `"GUSDC$Unit$none$none"` - GUSDC token
- `"Token$Unit$TUSA$eth:Af379b455fBa98197437260Be2b57E620373Ee89"` - Custom token

**Old Format (Deprecated)**: 
```json
{
  "collection": "GALA",
  "category": "Unit",
  "type": "none",
  "additionalKey": "none"
}
```

## Endpoints

### Trading Endpoints (v1) - NEW DEX API

**Note**: These are the new V3 DEX endpoints. The old swap-based endpoints may no longer work.

1. **Get Trading Quote** ⭐ NEW
   - **Endpoint**: `GET /v1/trade/quote`
   - **Purpose**: Get a quote for trading between two tokens (before swapping)
   - **Query Parameters**:
     - `tokenIn`: Token identifier (e.g., `"GALA$Unit$none$none"`)
     - `tokenOut`: Token identifier (e.g., `"ETIME$Unit$none$none"`)
     - `amountIn`: (optional) Amount of input token (string format)
     - `amountOut`: (optional) Amount you want to receive (string format)
     - `fee`: (optional) Pool fee tier (500 = 0.05%, 3000 = 0.30%, 10000 = 1.00%)
   - **Example**:
     ```
     GET /v1/trade/quote?tokenIn=GALA$Unit$none$none&tokenOut=ETIME$Unit$none$none&amountOut=1&fee=500
     ```
   - **Response**:
     ```json
     {
       "status": 200,
       "message": "Quoted value retrieved successfully.",
       "error": false,
       "data": {
         "currentSqrtPrice": "1.414213562373095048",
         "newSqrtPrice": "2.552346116953373414",
         "fee": 500,
         "amountIn": "6.50106744",
         "amountOut": "1"
       }
     }
     ```

2. **Get Token Price** ⭐ NEW
   - **Endpoint**: `GET /v1/trade/price`
   - **Purpose**: Get current price of a token
   - **Query Parameters**:
     - `token`: Token identifier (e.g., `"GALA$Unit$none$none"`)
   - **Example**:
     ```
     GET /v1/trade/price?token=GALA$Unit$none$none
     ```
   - **Response**:
     ```json
     {
       "price": "0.041954",
       "timestamp": "2024-12-21T09:00:00Z"
     }
     ```

3. **Get Multiple Token Prices** ⭐ NEW
   - **Endpoint**: `POST /v1/trade/price-multiple`
   - **Purpose**: Get prices for multiple tokens at once
   - **Request Body**:
     ```json
     {
       "tokens": [
         "GALA$Unit$none$none",
         "GUSDC$Unit$none$none",
         "ETIME$Unit$none$none"
       ]
     }
     ```

4. **Get Pool Details** ⭐ NEW
   - **Endpoint**: `GET /v1/trade/pool`
   - **Purpose**: Get details of a specific liquidity pool
   - **Query Parameters**:
     - `token0`: First token identifier
     - `token1`: Second token identifier
     - `fee`: Pool fee tier
   - **Example**:
     ```
     GET /v1/trade/pool?token0=GALA$Unit$none$none&token1=GUSDC$Unit$none$none&fee=3000
     ```

### Price Oracle Endpoints ⭐ NEW

1. **Subscribe to Token Price Updates**
   - **Endpoint**: `POST /price-oracle/subscribe-token`
   - **Purpose**: Subscribe/unsubscribe from price updates
   - **Request Body**:
     ```json
     {
       "subscribe": true,
       "token": {
         "collection": "GALA",
         "category": "Unit",
         "type": "none",
         "additionalKey": "none"
       }
     }
     ```

2. **Fetch Historical Price Data**
   - **Endpoint**: `GET /price-oracle/fetch-price`
   - **Purpose**: Get historical price data with pagination
   - **Query Parameters**:
     - `token`: Token identifier (e.g., `"GALA$Unit$none$none"`)
     - `page`: Page number (default: 1)
     - `limit`: Records per page (default: 10)
     - `order`: Sort order (`asc` or `desc`)
   - **Example**:
     ```
     GET /price-oracle/fetch-price?token=GALA$Unit$none$none&page=1&limit=10&order=asc
     ```

### Old Swap-Based Endpoints (May be Deprecated)

1. **Fetch Available Token Swaps** ⚠️ OLD API
   - **Endpoint**: `POST /v1/FetchAvailableTokenSwaps`
   - **Status**: May no longer work - replaced by DEX pools

2. **Request Token Swap** (Create Swap)
   - **Endpoint**: `POST /v1/RequestTokenSwap`
   - **Purpose**: Create a new swap offer
   - **Requires**: Signed request with `X-Wallet-Address` header
   - **Request Body**:
     ```json
     {
       "offered": [{
         "quantity": "100.0",
         "tokenInstance": {
           "collection": "GALA",
           "category": "Unit",
           "type": "none",
           "additionalKey": "none",
           "instance": "0"
         }
       }],
       "wanted": [{
         "quantity": "50.0",
         "tokenInstance": {
           "collection": "GUSDT",
           "category": "Unit",
           "type": "none",
           "additionalKey": "none",
           "instance": "0"
         }
       }],
       "uses": "1",
       "signerPublicKey": "...",
       "signature": "...",
       "uniqueKey": "..."
     }
     ```

3. **Batch Fill Token Swap** (Accept Swap)
   - **Endpoint**: `POST /v1/BatchFillTokenSwap`
   - **Purpose**: Accept/fill an existing swap
   - **Requires**: Signed request with `X-Wallet-Address` header
   - **Request Body**:
     ```json
     {
       "swapDtos": [{
         "swapRequestId": "...",
         "uses": "1",
         "expectedTokenSwap": {
           "wanted": [...],
           "offered": [...]
         }
       }],
       "signerPublicKey": "...",
       "signature": "...",
       "uniqueKey": "..."
     }
     ```

4. **Terminate Token Swap** (Cancel Swap)
   - **Endpoint**: `POST /v1/TerminateTokenSwap`
   - **Purpose**: Cancel a swap you created
   - **Requires**: Signed request with `X-Wallet-Address` header

### GalaChain API Endpoints

1. **Get Public Key**
   - **Endpoint**: `POST /galachain/api/asset/public-key-contract/GetPublicKey`
   - **Purpose**: Fetch public key for a wallet address
   - **Request Body**:
     ```json
     {
       "user": "eth|a7027114A40d21382951b03e3067429106e6e806"
     }
     ```

2. **Fetch Balances**
   - **Endpoint**: `POST /galachain/api/asset/token-contract/FetchBalances`
   - **Purpose**: Get token balances for a wallet
   - **Request Body**:
     ```json
     {
       "owner": "eth|a7027114A40d21382951b03e3067429106e6e806"
     }
     ```

3. **Fetch Token Swaps Offered By User**
   - **Endpoint**: `POST /galachain/api/asset/token-contract/FetchTokenSwapsOfferedByUser`
   - **Purpose**: Get swaps created by a specific user
   - **Request Body**:
     ```json
     {
       "user": "eth|a7027114A40d21382951b03e3067429106e6e806",
       "limit": 100
     }
     ```

## Request Headers

All signed requests require:
- `Content-Type: application/json`
- `X-Wallet-Address: eth|...` or `client|...` (GalaChain address format)

## Authentication

Signed requests require:
- `signerPublicKey`: Base64 encoded compressed public key (fetched from API)
- `signature`: Base64 encoded DER signature of request body
- `uniqueKey`: Unique identifier for the request

## Execution Endpoints (Missing)

**⚠️ IMPORTANT**: The documentation provided shows read-only endpoints (GET requests) for:
- Getting quotes
- Checking prices
- Viewing positions
- Pool details

**We still need the POST endpoints for actually executing trades/swaps.** These are likely:
- `/v1/trade/swap` or similar
- May require signed requests with wallet address and signature

Please check the full API documentation for execution endpoints.

## Core Concepts

### 1. Concentrated Liquidity (V3 DEX)
- Liquidity providers can concentrate capital within specific price ranges
- More efficient use of capital
- Better price execution for traders

### 2. Price Ranges and Ticks
- Each tick represents a 0.01% price movement
- Liquidity can be provided between any two ticks
- Current price always sits on a tick

### 3. Fee Tiers
- **500** = 0.05% (stable pairs like USDC/USDT)
- **3000** = 0.30% (standard pairs like ETH/USDC)
- **10000** = 1.00% (exotic pairs)

### 4. Token Format
Tokens use composite key: `"collection$category$type$additionalKey"`
- Example: `"GALA$Unit$none$none"`
- Collection: Token name (GALA, GUSDC, etc.)
- Category: Usually "Unit" for fungible tokens
- Type: Token type or contract identifier
- AdditionalKey: Additional identifying information

## Best Practices

1. **Always get a quote before swapping** to understand expected output
2. **Consider the fee tier** when choosing a pool
3. **Monitor positions regularly** using `/v1/trade/positions`
4. **Use appropriate slippage protection**
5. **Keep track of token identifiers** in composite key format

## Verification

Please verify these endpoints match the official documentation at:
- https://swap.gala.com/doc/trading-endpoints

**We need to find the execution endpoints (POST) for placing trades!**

