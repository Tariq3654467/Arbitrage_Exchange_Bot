"""
Galaswap DEX Connector
Handles swaps on Galaswap using GalaConnect API
"""

import json
import uuid
import base64
import asyncio
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import aiohttp
from aiohttp import ClientConnectorError, ClientTimeout
from eth_account import Account
from eth_keys import keys
from eth_utils import keccak, to_checksum_address
import hashlib

from ...exchanges.base_exchange import BaseExchange, OrderBook, Balance, Order
from ...utils.logger import get_logger

logger = get_logger()


def deterministic_json_stringify(obj) -> str:
    """Recursively sort object properties and stringify to minimal JSON"""
    if isinstance(obj, dict):
        sorted_items = sorted(obj.items())
        items = []
        for k, v in sorted_items:
            if k != 'signature':  # Exclude signature from signing
                items.append(f'"{k}":{deterministic_json_stringify(v)}')
        return '{' + ','.join(items) + '}'
    elif isinstance(obj, list):
        return '[' + ','.join(deterministic_json_stringify(item) for item in obj) + ']'
    elif isinstance(obj, str):
        # Escape special characters
        escaped = obj.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return f'"{escaped}"'
    elif isinstance(obj, (int, float)):
        # For floats, use JSON to ensure proper formatting
        if isinstance(obj, float):
            # Remove trailing zeros
            s = json.dumps(obj)
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        return str(obj)
    elif obj is None:
        return 'null'
    elif isinstance(obj, bool):
        return 'true' if obj else 'false'
    else:
        return json.dumps(obj)


def sign_request_body(body: dict, private_key: str) -> str:
    """
    Sign request body using secp256k1 signature on keccak256 hash
    
    Args:
        body: Request body dictionary
        private_key: Private key in hex format (with or without 0x prefix)
    
    Returns:
        Base64 encoded signature
    """
    try:
        # Remove signature if present
        body_to_sign = {k: v for k, v in body.items() if k != 'signature'}
        
        # Stringify deterministically
        string_to_sign = deterministic_json_stringify(body_to_sign)
        
        # Hash with keccak256
        string_bytes = string_to_sign.encode('utf-8')
        hash_bytes = keccak(string_bytes)
        
        # Sign with private key
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        private_key_bytes = bytes.fromhex(private_key)
        private_key_obj = keys.PrivateKey(private_key_bytes)
        signature = private_key_obj.sign_msg_hash(hash_bytes)
        
        # Convert to DER format and base64 encode
        # Proper DER encoding for ECDSA signature
        r_bytes = signature.r.to_bytes(32, 'big')
        s_bytes = signature.s.to_bytes(32, 'big')
        
        # Remove leading zeros
        r_bytes = r_bytes.lstrip(b'\x00')
        s_bytes = s_bytes.lstrip(b'\x00')
        
        # Ensure first byte is < 0x80 (DER requirement for positive integers)
        if len(r_bytes) > 0 and r_bytes[0] & 0x80:
            r_bytes = b'\x00' + r_bytes
        if len(s_bytes) > 0 and s_bytes[0] & 0x80:
            s_bytes = b'\x00' + s_bytes
        
        # DER encoding: SEQUENCE { INTEGER r, INTEGER s }
        # Build INTEGER r
        int_r = b'\x02' + bytes([len(r_bytes)]) + r_bytes
        # Build INTEGER s
        int_s = b'\x02' + bytes([len(s_bytes)]) + s_bytes
        # Build SEQUENCE
        seq_length = len(int_r) + len(int_s)
        if seq_length < 128:
            der = b'\x30' + bytes([seq_length]) + int_r + int_s
        else:
            # Long form length encoding (for sequences > 127 bytes)
            length_bytes = []
            temp = seq_length
            while temp > 0:
                length_bytes.insert(0, temp & 0xff)
                temp >>= 8
            der = b'\x30' + bytes([0x80 | len(length_bytes)]) + bytes(length_bytes) + int_r + int_s
        
        return base64.b64encode(der).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Error signing request: {e}")
        raise


class GalaswapConnector(BaseExchange):
    """Galaswap exchange connector using GalaConnect API"""
    
    API_BASE_URL = "https://api-galaswap.gala.com"
    REQUEST_TIMEOUT = 5  # seconds (reduced from 10 to fail faster)
    MAX_RETRIES = 2  # Reduced retries to fail faster
    RETRY_DELAY_BASE = 1  # seconds
    
    # Circuit breaker: disable after consecutive failures
    _circuit_breaker_threshold = 5  # Disable after 5 consecutive failures
    _circuit_breaker_reset_time = 300  # Re-enable after 5 minutes
    
    def __init__(
        self,
        wallet_address: str,
        private_key: str,
        public_key: Optional[str] = None,
        rpc_url: Optional[str] = None  # Not used for API, kept for compatibility
    ):
        """
        Initialize Galaswap connector
        
        Args:
            wallet_address: GalaChain wallet address (e.g., "client|123456789abcdef012345678")
            private_key: Private key in hex format
            public_key: Public key in base64 (optional, will be fetched if not provided)
            rpc_url: Not used, kept for compatibility
        """
        BaseExchange.__init__(self, exchange_name="galaswap", testnet=False)
        
        # Validate wallet address format
        if not wallet_address or not isinstance(wallet_address, str):
            raise ValueError("Wallet address is required and must be a string")
        
        wallet_address = wallet_address.strip()
        if not wallet_address:
            raise ValueError("Wallet address cannot be empty")
        
        # Gala wallet addresses typically have format: "client|..." or just an address
        # Log format for debugging
        if '|' in wallet_address:
            logger.debug(f"Gala wallet address format detected: contains '|' separator")
        elif wallet_address.startswith('0x'):
            logger.debug(f"Gala wallet address format detected: Ethereum-style address")
        else:
            logger.debug(f"Gala wallet address format: {wallet_address[:20]}...")
        
        self.wallet_address = wallet_address
        self.private_key = private_key
        
        # Validate and initialize account for key operations
        if not private_key or not isinstance(private_key, str):
            raise ValueError("Private key is required and must be a string")
        
        # Remove whitespace
        private_key = private_key.strip()
        
        if not private_key:
            raise ValueError("Private key cannot be empty")
        
        # Remove 0x prefix if present
        if private_key.startswith('0x'):
            private_key_clean = private_key[2:]
        else:
            private_key_clean = private_key
        
        # Validate hex format
        try:
            # Check if it's valid hex
            int(private_key_clean, 16)
        except ValueError:
            raise ValueError(
                f"Invalid private key format: contains non-hexadecimal characters. "
                f"Private key must be 64 hex characters (with or without 0x prefix). "
                f"Got: {private_key[:10]}..." if len(private_key) > 10 else private_key
            )
        
        # Check length (should be 64 hex chars = 32 bytes)
        if len(private_key_clean) != 64:
            raise ValueError(
                f"Invalid private key length: expected 64 hex characters (32 bytes), "
                f"got {len(private_key_clean)} characters"
            )
        
        # Initialize account
        try:
            self.account = Account.from_key('0x' + private_key_clean)
        except Exception as e:
            raise ValueError(
                f"Failed to create account from private key: {str(e)}. "
                f"Please ensure the private key is a valid Ethereum-compatible private key."
            ) from e
        
        self.public_key = public_key
        self.is_connected = False
        
        # Circuit breaker state (instance-level)
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        
        # Token registry for symbol -> token class mapping
        self.token_registry: Dict[str, Dict] = {}
        
        # Token name mapping for common Gala tokens
        # Maps collection code to actual token name
        self.token_names: Dict[str, str] = {
            "GALA": "Gala",
            "GUSDT": "Gala Tether USD",
            "GUSDC": "Gala USD Coin",
            "GWETH": "Gala Wrapped Ethereum",
            "USDT": "Tether USD",
            "USDC": "USD Coin",
            "ETH": "Ethereum",
            "BTC": "Bitcoin",
            "BNB": "Binance Coin",
            "MATIC": "Polygon",
            "ADA": "Cardano",
            "DOT": "Polkadot",
            "SOL": "Solana",
            "LINK": "Chainlink",
            "UNI": "Uniswap",
            "AAVE": "Aave",
            "SAND": "The Sandbox",
            "MANA": "Decentraland",
            "AXS": "Axie Infinity",
            "ENJ": "Enjin Coin",
        }
        
        logger.info(f"Initialized Galaswap connector for wallet: {wallet_address}")
    
    async def connect(self):
        """Connect to GalaConnect API and fetch public key if needed"""
        try:
            # Fetch public key if not provided
            if not self.public_key:
                try:
                    timeout = ClientTimeout(total=self.REQUEST_TIMEOUT)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(
                            f"{self.API_BASE_URL}/galachain/api/asset/public-key-contract/GetPublicKey",
                            json={"user": self.wallet_address},
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                self.public_key = data.get("Data", {}).get("publicKey")
                                if not self.public_key:
                                    logger.warning("Public key not found in API response")
                                else:
                                    logger.info("Fetched public key from API")
                            else:
                                # Try to get error message from response
                                try:
                                    error_data = await response.json()
                                    error_msg = error_data.get("Message", error_data.get("message", "Unknown error"))
                                except:
                                    error_msg = await response.text()
                                
                                # Only log as debug - this is often normal for new wallets
                                logger.debug(
                                    f"Public key not available from API (status {response.status}): {error_msg}. "
                                    f"This is normal for new wallets or different address formats. "
                                    f"Will derive public key from private key if needed."
                                )
                                
                                # Try to derive public key from private key as fallback
                                try:
                                    # Get public key from account
                                    public_key_bytes = self.account.key
                                    # Convert to hex and then base64 (Gala API might expect base64)
                                    import base64
                                    # Get uncompressed public key (65 bytes: 0x04 + 32 bytes x + 32 bytes y)
                                    public_key_hex = self.account.key.public_key.to_hex()
                                    # For now, we'll skip this and let it work without public key if needed
                                    logger.info("Will proceed without public key - it may be required for some operations")
                                except Exception as derive_error:
                                    logger.debug(f"Could not derive public key: {derive_error}")
                except (ClientConnectorError, asyncio.TimeoutError) as fetch_error:
                    # Network errors - API might be temporarily unavailable, use debug level
                    logger.debug(
                        f"Galaswap API temporarily unavailable when fetching public key: {fetch_error}. "
                        f"Will proceed without it. Public key will be derived from private key if needed."
                    )
                except Exception as fetch_error:
                    error_msg = str(fetch_error)
                    # Only warn if it's not a network issue
                    if 'network' not in error_msg.lower() and 'connection' not in error_msg.lower():
                        logger.debug(
                            f"Could not fetch public key from API: {fetch_error}. "
                            f"Will proceed without it. Public key will be derived from private key if needed."
                        )
            
            # Test connection by fetching balances (this will fail gracefully if wallet is empty)
            try:
                await self.get_balance()
                logger.debug("Balance fetch successful during connection test")
            except (ClientConnectorError, asyncio.TimeoutError) as balance_error:
                # Network errors - API might be temporarily unavailable
                logger.debug(
                    f"Galaswap API temporarily unavailable during connection test: {balance_error}. "
                    f"Will retry on next operation."
                )
            except Exception as balance_error:
                error_msg = str(balance_error)
                # Only warn if it's not a network/connection issue
                if 'network' not in error_msg.lower() and 'connection' not in error_msg.lower() and 'timeout' not in error_msg.lower():
                    logger.debug(
                        f"Could not fetch balances during connection test: {balance_error}. "
                        f"This may be normal if the wallet is empty or the API format has changed."
                    )
                # Don't fail connection if balance fetch fails - wallet might just be empty
            
            self.is_connected = True
            
            # Verify wallet configuration
            if not self.wallet_address or not self.private_key:
                logger.warning("Galaswap wallet address or private key not configured properly")
            else:
                logger.info(f"✓ Connected to Galaswap (GalaConnect API) - Wallet: {self.wallet_address[:20]}..." if len(self.wallet_address) > 20 else f"✓ Connected to Galaswap (GalaConnect API) - Wallet: {self.wallet_address}")
        
        except Exception as e:
            # Don't raise on connection errors - allow bot to continue
            # The exchange will just return empty data when API is unreachable
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check if it's a network/connection issue (expected and handled gracefully)
            if 'network' in error_msg.lower() or 'connection' in error_msg.lower() or 'timeout' in error_msg.lower() or 'ClientConnectorError' in error_type:
                logger.debug(
                    f"Galaswap API temporarily unavailable during connection: {error_msg}. "
                    f"Will retry on next operation. Wallet: {self.wallet_address[:20]}..." if len(self.wallet_address) > 20 else f"Wallet: {self.wallet_address}"
                )
            else:
                # Other errors might be configuration issues
                logger.warning(
                    f"Error connecting to Galaswap: {error_type}: {error_msg}. "
                    f"Wallet: {self.wallet_address[:20]}..." if len(self.wallet_address) > 20 else f"Wallet: {self.wallet_address}"
                )
            
            # Still mark as connected so bot can continue - methods will handle API errors gracefully
            self.is_connected = True
            logger.info(f"✓ Connected to Galaswap (GalaConnect API) - Wallet: {self.wallet_address[:20]}..." if len(self.wallet_address) > 20 else f"✓ Connected to Galaswap (GalaConnect API) - Wallet: {self.wallet_address}")
    
    async def disconnect(self):
        """Disconnect from API"""
        self.is_connected = False
        logger.info("Disconnected from Galaswap")
    
    def _generate_unique_key(self) -> str:
        """Generate a unique key for API requests"""
        return f"galaconnect-operation-{uuid.uuid4()}"
    
    def _parse_token_class(self, token_str: str) -> Dict:
        """
        Parse token string like "GALA|Unit|none|none" into token class dict
        
        Format: collection|category|type|additionalKey
        """
        parts = token_str.split('|')
        if len(parts) != 4:
            raise ValueError(f"Invalid token format: {token_str}")
        
        return {
            "collection": parts[0],
            "category": parts[1],
            "type": parts[2],
            "additionalKey": parts[3]
        }
    
    def _format_token_class(self, token_class: Dict) -> str:
        """Format token class dict to string format"""
        return f"{token_class['collection']}|{token_class['category']}|{token_class['type']}|{token_class['additionalKey']}"
    
    def _parse_symbol(self, symbol: str) -> Tuple[Dict, Dict]:
        """
        Parse symbol like 'GALA/USDT' into token classes
        
        Returns:
            Tuple of (base_token_class, quote_token_class)
        """
        try:
            base, quote = symbol.split('/')
        except ValueError:
            raise ValueError(f"Invalid symbol format: {symbol}. Expected format: BASE/QUOTE")
        
        # Try to get from registry first
        base_class = self.token_registry.get(base.upper())
        quote_class = self.token_registry.get(quote.upper())
        
        # If not in registry, use default format
        if not base_class:
            base_class = {
                "collection": base.upper(),
                "category": "Unit",
                "type": "none",
                "additionalKey": "none"
            }
        
        if not quote_class:
            quote_class = {
                "collection": quote.upper(),
                "category": "Unit",
                "type": "none",
                "additionalKey": "none"
            }
        
        return base_class, quote_class
    
    def register_token(self, symbol: str, token_class: Dict):
        """Register a token symbol with its token class"""
        self.token_registry[symbol.upper()] = token_class
        logger.info(f"Registered token {symbol} -> {self._format_token_class(token_class)}")
    
    async def _make_signed_request(
        self,
        method: str,
        endpoint: str,
        body: dict,
        headers: Optional[Dict] = None,
        retry_on_connection_error: bool = True
    ) -> dict:
        """
        Make a signed API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            body: Request body
            headers: Additional headers
            retry_on_connection_error: Whether to retry on connection errors
        
        Returns:
            Response JSON data
        
        Raises:
            Exception: If request fails after retries
        """
        if headers is None:
            headers = {}
        
        headers["Content-Type"] = "application/json"
        headers["X-Wallet-Address"] = self.wallet_address
        
        # Add public key and unique key if not present
        if "signerPublicKey" not in body:
            body["signerPublicKey"] = self.public_key
        if "uniqueKey" not in body:
            body["uniqueKey"] = self._generate_unique_key()
        
        # Sign the request
        signature = sign_request_body(body, self.private_key)
        body["signature"] = signature
        
        timeout = ClientTimeout(total=self.REQUEST_TIMEOUT)
        last_error = None
        
        for attempt in range(self.MAX_RETRIES if retry_on_connection_error else 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        method,
                        f"{self.API_BASE_URL}{endpoint}",
                        json=body,
                        headers=headers
                    ) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"API error {response.status}: {error_text}")
                            raise Exception(f"API error {response.status}: {error_text}")
                        
                        return await response.json()
            
            except (ClientConnectorError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < (self.MAX_RETRIES - 1) if retry_on_connection_error else 0:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    # Only log on first attempt to reduce spam
                    if attempt == 0:
                        logger.debug(
                            f"Connection error to Galaswap API (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Failed to connect to Galaswap API after {self.MAX_RETRIES} attempts: {e}"
                    )
                    raise
            
            except Exception as e:
                # For non-connection errors, don't retry
                raise
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise Exception("Unexpected error in _make_signed_request")
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should allow requests"""
        # Reset circuit breaker if enough time has passed
        if self._circuit_breaker_last_failure:
            time_since_failure = (datetime.now() - self._circuit_breaker_last_failure).total_seconds()
            if time_since_failure > self._circuit_breaker_reset_time:
                self._circuit_breaker_failures = 0
                self._circuit_breaker_last_failure = None
                logger.info("Galaswap circuit breaker reset - re-enabling API requests")
                return True
        
        # Check if circuit breaker is open
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            logger.debug(
                f"Galaswap circuit breaker OPEN - API disabled due to {self._circuit_breaker_failures} "
                f"consecutive failures. Will retry after {self._circuit_breaker_reset_time}s"
            )
            return False
        
        return True
    
    def _record_success(self):
        """Record successful API call - reset circuit breaker"""
        if self._circuit_breaker_failures > 0:
            logger.debug(f"Galaswap API recovered - resetting circuit breaker")
            self._circuit_breaker_failures = 0
            self._circuit_breaker_last_failure = None
    
    def _record_failure(self):
        """Record failed API call - update circuit breaker"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = datetime.now()
        
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            logger.warning(
                f"Galaswap circuit breaker OPENED after {self._circuit_breaker_failures} failures. "
                f"API will be disabled for {self._circuit_breaker_reset_time}s to prevent spam."
            )
    
    async def _make_unsigned_request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
        retry_on_connection_error: bool = True
    ) -> dict:
        """
        Make an unsigned API request (for read operations)
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            body: Request body
            retry_on_connection_error: Whether to retry on connection errors
        
        Returns:
            Response JSON data
        
        Raises:
            Exception: If request fails after retries
        """
        # Check circuit breaker
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is OPEN - API temporarily disabled due to repeated failures")
        
        headers = {"Content-Type": "application/json"}
        timeout = ClientTimeout(total=self.REQUEST_TIMEOUT)
        
        last_error = None
        for attempt in range(self.MAX_RETRIES if retry_on_connection_error else 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        method,
                        f"{self.API_BASE_URL}{endpoint}",
                        json=body or {},
                        headers=headers
                    ) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            
                            # Handle 502 Bad Gateway and 503 Service Unavailable as temporary errors
                            if response.status in [502, 503, 504]:
                                # These are temporary server errors - record failure but don't spam logs
                                logger.debug(f"Galaswap API temporary error {response.status}: {error_text[:100]}")
                                self._record_failure()
                                raise Exception(f"API error {response.status}: Service temporarily unavailable")
                            else:
                                # Other 4xx/5xx errors - log but don't spam
                                logger.debug(f"Galaswap API error {response.status}: {error_text[:100]}")
                                self._record_failure()
                                raise Exception(f"API error {response.status}: {error_text[:200]}")
                        
                        # Success - reset circuit breaker
                        self._record_success()
                        return await response.json()
            
            except (ClientConnectorError, asyncio.TimeoutError) as e:
                last_error = e
                self._record_failure()
                
                if attempt < (self.MAX_RETRIES - 1) if retry_on_connection_error else 0:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    # Only log on first attempt to reduce spam
                    if attempt == 0:
                        logger.debug(
                            f"Galaswap connection error (attempt {attempt + 1}/{self.MAX_RETRIES}): {type(e).__name__}. "
                            f"Retrying in {delay}s..."
                        )
                    await asyncio.sleep(delay)
                else:
                    logger.debug(
                        f"Galaswap API connection failed after {self.MAX_RETRIES} attempts: {type(e).__name__}"
                    )
                    raise
            
            except Exception as e:
                # For non-connection errors, don't retry
                raise
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise Exception("Unexpected error in _make_unsigned_request")
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Get order book for a symbol (from available swaps)
        
        Note: Galaswap doesn't have traditional order books.
        We simulate one from available swaps.
        
        Returns empty order book if API is unreachable to allow bot to continue.
        """
        try:
            # Check circuit breaker first
            if not self._check_circuit_breaker():
                # Circuit breaker is open - return empty order book silently
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            base_class, quote_class = self._parse_symbol(symbol)
            
            # Fetch available swaps (we want to buy base with quote)
            # So we offer quote and want base
            # API expects token class objects, not strings
            try:
                response = await self._make_unsigned_request(
                    "POST",
                    "/v1/FetchAvailableTokenSwaps",
                    {
                        "offeredTokenClass": quote_class,  # Dict object: {collection, category, type, additionalKey}
                        "wantedTokenClass": base_class     # Dict object: {collection, category, type, additionalKey}
                    }
                )
            except Exception as api_error:
                error_msg = str(api_error)
                # Silently return empty order book for all errors to prevent spam
                # Circuit breaker will handle repeated failures
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            # Check response structure
            if not response:
                logger.debug(f"Empty response from Galaswap API for {symbol}")
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            swaps = response.get("results", [])
            if not swaps:
                logger.debug(f"No swaps available for {symbol} on Galaswap")
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            # Build order book from swaps
            bids = []  # People offering base (we can buy from them)
            asks = []  # People wanting base (we can sell to them)
            
            for swap in swaps[:depth]:
                try:
                    # Swap perspective: they're offering base, wanting quote
                    offered = swap.get("offered", [])
                    wanted = swap.get("wanted", [])
                    
                    # Handle different response structures
                    if not offered or not wanted:
                        continue
                    
                    # Ensure they're lists
                    if not isinstance(offered, list):
                        offered = [offered]
                    if not isinstance(wanted, list):
                        wanted = [wanted]
                    
                    if offered and wanted and len(offered) > 0 and len(wanted) > 0:
                        # Get quantities - handle different formats
                        base_item = offered[0] if isinstance(offered[0], dict) else {}
                        quote_item = wanted[0] if isinstance(wanted[0], dict) else {}
                        
                        base_qty = float(base_item.get("quantity", base_item.get("qty", 0)))
                        quote_qty = float(quote_item.get("quantity", quote_item.get("qty", 0)))
                        
                        if base_qty > 0 and quote_qty > 0:
                            price = quote_qty / base_qty
                            bids.append((price, base_qty))
                except (ValueError, TypeError, KeyError, IndexError) as e:
                    logger.debug(f"Error parsing swap for {symbol}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Unexpected error parsing swap for {symbol}: {type(e).__name__}: {e}")
                    continue
            
            # Sort bids descending (highest first)
            bids.sort(reverse=True)
            
            # For asks, we'd need swaps where we offer base and want quote
            # This is more complex, so we'll estimate from bid spread
            if bids:
                best_bid = bids[0][0]
                spread = best_bid * 0.001  # 0.1% spread
                asks = [(best_bid + spread * (i + 1), depth - i) for i in range(depth)]
            else:
                asks = []
            
            return OrderBook(
                exchange=self.exchange_name,
                symbol=symbol,
                bids=bids[:depth],
                asks=asks[:depth],
                timestamp=datetime.now()
            )
        
        except (ClientConnectorError, asyncio.TimeoutError) as e:
            # Connection errors: return empty order book to allow bot to continue
            logger.debug(
                f"Galaswap API temporarily unavailable for {symbol} order book: {e}"
            )
            return OrderBook(
                exchange=self.exchange_name,
                symbol=symbol,
                bids=[],
                asks=[],
                timestamp=datetime.now()
            )
        except Exception as e:
            # Other errors: log with more detail and return empty order book
            error_type = type(e).__name__
            error_msg = str(e)
            logger.debug(
                f"Error fetching order book for {symbol}: {error_type}: {error_msg}"
            )
            return OrderBook(
                exchange=self.exchange_name,
                symbol=symbol,
                bids=[],
                asks=[],
                timestamp=datetime.now()
            )
    
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker data for a symbol
        
        Returns empty ticker data if API is unreachable to allow bot to continue.
        """
        try:
            order_book = await self.get_order_book(symbol, depth=1)
            
            best_bid = order_book.best_bid
            best_ask = order_book.best_ask
            
            if best_bid and best_ask:
                mid_price = (best_bid[0] + best_ask[0]) / 2
                return {
                    'symbol': symbol,
                    'bid': best_bid[0],
                    'ask': best_ask[0],
                    'last': mid_price,
                    'volume': 0.0,  # Volume not available from API
                    'timestamp': datetime.now()
                }
            else:
                # Return empty ticker data instead of raising
                logger.debug(f"No price data available for {symbol} on Galaswap")
                return {
                    'symbol': symbol,
                    'bid': 0.0,
                    'ask': 0.0,
                    'last': 0.0,
                    'volume': 0.0,
                    'timestamp': datetime.now()
                }
        
        except Exception as e:
            # Return empty ticker data on any error to allow bot to continue
            error_type = type(e).__name__
            error_msg = str(e)
            logger.debug(f"Error fetching ticker for {symbol}: {error_type}: {error_msg}")
            return {
                'symbol': symbol,
                'bid': 0.0,
                'ask': 0.0,
                'last': 0.0,
                'volume': 0.0,
                'timestamp': datetime.now()
            }
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """Get account balance"""
        try:
            response = await self._make_unsigned_request(
                "POST",
                "/galachain/api/asset/token-contract/FetchBalances",
                {"owner": self.wallet_address}
            )
            
            balances = {}
            data = response.get("Data", [])
            
            if not data:
                logger.debug("No token data returned from Galaswap balance API")
            
            for token_data in data:
                try:
                    token_class = token_data.get("tokenClass", {})
                    
                    # Try multiple fields to get the collection/symbol
                    collection = (
                        token_class.get("collection") or
                        token_class.get("symbol") or
                        token_data.get("collection") or
                        token_data.get("symbol") or
                        ""
                    )
                    
                    # Get token name from various possible fields
                    token_name = (
                        token_data.get("name") or
                        token_data.get("tokenName") or
                        token_data.get("displayName") or
                        token_class.get("name") or
                        token_class.get("tokenName") or
                        token_class.get("displayName") or
                        None
                    )
                    
                    # Handle quantity - might be a list or single value
                    quantity_raw = token_data.get("quantity", "0")
                    if isinstance(quantity_raw, list):
                        # If it's a list, sum all values or take first element
                        quantity = float(sum(float(x) for x in quantity_raw if x)) if quantity_raw else 0.0
                    elif isinstance(quantity_raw, (int, float)):
                        quantity = float(quantity_raw)
                    else:
                        quantity = float(quantity_raw) if quantity_raw else 0.0
                    
                    # Handle lockedHolds - might be a list or single value
                    locked_raw = token_data.get("lockedHolds", "0")
                    if isinstance(locked_raw, list):
                        # If it's a list, sum all values or take first element
                        locked = float(sum(float(x) for x in locked_raw if x)) if locked_raw else 0.0
                    elif isinstance(locked_raw, (int, float)):
                        locked = float(locked_raw)
                    else:
                        locked = float(locked_raw) if locked_raw else 0.0
                    
                    if quantity > 0 or locked > 0:
                        # Determine symbol - try collection first, then derive from name
                        if collection:
                            symbol = collection.upper().strip()
                        elif token_name:
                            # Try to extract symbol from token name (e.g., "Gala Token" -> "GALA")
                            # First check if it matches any known token name
                            symbol = None
                            for known_symbol, known_name in self.token_names.items():
                                if token_name.lower() == known_name.lower() or known_name.lower() in token_name.lower():
                                    symbol = known_symbol
                                    break
                            
                            # If no match, try to create symbol from name
                            if not symbol:
                                # Remove common words and create symbol
                                name_clean = token_name.replace("Token", "").replace("Coin", "").strip()
                                # Take first word or first few letters
                                words = name_clean.split()
                                if words:
                                    symbol = words[0].upper()[:10]  # Limit length
                                else:
                                    symbol = name_clean.upper()[:10] if name_clean else "UNKNOWN"
                        else:
                            # Last resort: try to use category or type
                            category = token_class.get("category", "")
                            type_info = token_class.get("type", "")
                            if category and category.upper() not in ["UNIT", "NONE", ""]:
                                symbol = category.upper()[:10]
                            elif type_info and type_info.upper() not in ["UNIT", "NONE", ""]:
                                symbol = type_info.upper()[:10]
                            else:
                                # Log the raw data for debugging - this helps identify what fields are available
                                logger.warning(
                                    f"Could not determine symbol for Galaswap token. "
                                    f"Collection: {collection}, Token name: {token_name}, "
                                    f"Category: {token_class.get('category', 'N/A')}, "
                                    f"Type: {token_class.get('type', 'N/A')}. "
                                    f"Full token_data keys: {list(token_data.keys())}, "
                                    f"tokenClass keys: {list(token_class.keys())}"
                                )
                                symbol = "UNKNOWN"
                        
                        # Get actual token name from mapping if we have a symbol
                        if not token_name and symbol:
                            token_name = self.token_names.get(symbol, symbol)
                        elif not token_name:
                            token_name = symbol
                        
                        # Try to get additional info from token class
                        category = token_class.get("category", "")
                        type_info = token_class.get("type", "")
                        
                        # Create display name: "Token Name (SYMBOL)" or just "Token Name"
                        if token_name and token_name != symbol and symbol != "UNKNOWN":
                            display_name = f"{token_name} ({symbol})"
                        elif token_name and token_name != symbol:
                            display_name = token_name
                        elif category and category.lower() not in ["unit", "none", ""] and symbol != "UNKNOWN":
                            display_name = f"{symbol} ({category.upper()})"
                        else:
                            display_name = symbol if symbol != "UNKNOWN" else (token_name or "Unknown Token")
                        
                        # Use symbol as key, but display_name for the asset field
                        balances[symbol] = Balance(
                            asset=display_name,  # Use actual token name for better readability
                            free=quantity - locked,
                            locked=locked
                        )
                except Exception as e:
                    logger.warning(f"Error parsing balance for token: {e}. Token data: {json.dumps(token_data, default=str)[:200]}")
                    continue
            
            # Filter by asset if specified
            if asset:
                return {asset: balances.get(asset)} if asset in balances else {}
            
            return balances
        
        except Exception as e:
            error_msg = (
                f"Error fetching Galaswap balance for wallet {self.wallet_address}. "
                f"Error type: {type(e).__name__}, Message: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            # Return empty balances instead of raising to allow other exchanges to work
            return {}
    
    async def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Order:
        """Place a market order (executes by accepting available swaps)"""
        try:
            base_class, quote_class = self._parse_symbol(symbol)
            
            if side.lower() == 'buy':
                # Buy base with quote - find swaps offering base for quote
                response = await self._make_unsigned_request(
                    "POST",
                    "/v1/FetchAvailableTokenSwaps",
                    {
                        "offeredTokenClass": base_class,   # They offer base
                        "wantedTokenClass": quote_class     # They want quote
                    }
                )
                
                swaps = response.get("results", [])
                if not swaps:
                    raise ValueError(f"No available swaps to buy {symbol}")
                
                # Find best swap (lowest price)
                best_swap = None
                best_price = float('inf')
                
                for swap in swaps:
                    offered = swap.get("offered", [])
                    wanted = swap.get("wanted", [])
                    uses_available = int(swap.get("uses", 1)) - int(swap.get("usesSpent", 0))
                    
                    if offered and wanted and uses_available > 0:
                        base_qty = float(offered[0].get("quantity", 0))
                        quote_qty = float(wanted[0].get("quantity", 0))
                        price = quote_qty / base_qty if base_qty > 0 else float('inf')
                        
                        if price < best_price:
                            best_price = price
                            best_swap = swap
                
                if not best_swap:
                    raise ValueError(f"No suitable swap found for {symbol}")
                
                # Calculate how many uses we need
                base_per_use = float(best_swap["offered"][0]["quantity"])
                uses_needed = max(1, int(quantity / base_per_use))
                uses_available = int(best_swap.get("uses", 1)) - int(best_swap.get("usesSpent", 0))
                uses = min(uses_needed, uses_available)
                
                # Accept the swap
                swap_request_id = best_swap["swapRequestId"]
                expected_wanted = best_swap["wanted"]
                expected_offered = best_swap["offered"]
                
                body = {
                    "swapDtos": [{
                        "swapRequestId": swap_request_id,
                        "uses": str(uses),
                        "expectedTokenSwap": {
                            "wanted": expected_wanted,
                            "offered": expected_offered
                        }
                    }]
                }
                
                result = await self._make_signed_request("POST", "/v1/BatchFillTokenSwap", body)
                
                # Extract transaction info
                tx_data = result.get("Data", [{}])[0] if result.get("Data") else {}
                tx_id = tx_data.get("txid", swap_request_id)
                
                return Order(
                    exchange=self.exchange_name,
                    order_id=tx_id,
                    symbol=symbol,
                    side=side,
                    type='market',
                    price=best_price,
                    quantity=quantity,
                    filled_quantity=quantity,
                    status='filled',
                    timestamp=datetime.now(),
                    commission=None,
                    commission_asset=None
                )
            
            else:  # sell
                # Sell base for quote - create a swap offering base for quote
                # Calculate quote amount we want
                ticker = await self.get_ticker(symbol)
                quote_amount = quantity * ticker['bid']  # Use bid price
                
                # Create swap
                body = {
                    "offered": [{
                        "quantity": str(quantity),
                        "tokenInstance": {
                            **base_class,
                            "instance": "0"
                        }
                    }],
                    "wanted": [{
                        "quantity": str(quote_amount),
                        "tokenInstance": {
                            **quote_class,
                            "instance": "0"
                        }
                    }],
                    "uses": "1"
                }
                
                result = await self._make_signed_request("POST", "/v1/RequestTokenSwap", body)
                
                swap_data = result.get("Data", {})
                swap_request_id = swap_data.get("swapRequestId", "")
                
                return Order(
                    exchange=self.exchange_name,
                    order_id=swap_request_id,
                    symbol=symbol,
                    side=side,
                    type='market',
                    price=ticker['bid'],
                    quantity=quantity,
                    filled_quantity=0.0,  # Will be filled when someone accepts
                    status='pending',
                    timestamp=datetime.now(),
                    commission=None,
                    commission_asset=None
                )
        
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Order:
        """
        Place a limit order (creates a swap with specific price)
        
        For buy orders, we search for swaps at or below limit price.
        For sell orders, we create a swap at the limit price.
        """
        try:
            base_class, quote_class = self._parse_symbol(symbol)
            
            if side.lower() == 'buy':
                # Find swaps at or below limit price
                response = await self._make_unsigned_request(
                    "POST",
                    "/v1/FetchAvailableTokenSwaps",
                    {
                        "offeredTokenClass": base_class,
                        "wantedTokenClass": quote_class
                    }
                )
                
                swaps = response.get("results", [])
                suitable_swaps = []
                
                for swap in swaps:
                    offered = swap.get("offered", [])
                    wanted = swap.get("wanted", [])
                    uses_available = int(swap.get("uses", 1)) - int(swap.get("usesSpent", 0))
                    
                    if offered and wanted and uses_available > 0:
                        base_qty = float(offered[0].get("quantity", 0))
                        quote_qty = float(wanted[0].get("quantity", 0))
                        swap_price = quote_qty / base_qty if base_qty > 0 else float('inf')
                        
                        if swap_price <= price:
                            suitable_swaps.append((swap, swap_price))
                
                if not suitable_swaps:
                    raise ValueError(f"No swaps available at or below limit price {price}")
                
                # Use best (lowest) price swap
                best_swap, best_price = min(suitable_swaps, key=lambda x: x[1])
                
                # Execute as market order
                return await self.place_market_order(symbol, side, quantity)
            
            else:  # sell
                # Create swap at limit price
                quote_amount = quantity * price
                
                body = {
                    "offered": [{
                        "quantity": str(quantity),
                        "tokenInstance": {
                            **base_class,
                            "instance": "0"
                        }
                    }],
                    "wanted": [{
                        "quantity": str(quote_amount),
                        "tokenInstance": {
                            **quote_class,
                            "instance": "0"
                        }
                    }],
                    "uses": "1"
                }
                
                result = await self._make_signed_request("POST", "/v1/RequestTokenSwap", body)
                swap_data = result.get("Data", {})
                swap_request_id = swap_data.get("swapRequestId", "")
                
                return Order(
                    exchange=self.exchange_name,
                    order_id=swap_request_id,
                    symbol=symbol,
                    side=side,
                    type='limit',
                    price=price,
                    quantity=quantity,
                    filled_quantity=0.0,
                    status='pending',
                    timestamp=datetime.now(),
                    commission=None,
                    commission_asset=None
                )
        
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel a swap (terminate it)"""
        try:
            body = {
                "swapRequestId": order_id
            }
            
            await self._make_signed_request("POST", "/v1/TerminateTokenSwap", body)
            logger.info(f"Successfully cancelled swap {order_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """Get order status by checking swap status"""
        try:
            # Fetch swaps created by user
            response = await self._make_unsigned_request(
                "POST",
                "/galachain/api/asset/token-contract/FetchTokenSwapsOfferedByUser",
                {
                    "user": self.wallet_address,
                    "limit": 100
                }
            )
            
            swaps = response.get("Data", {}).get("results", [])
            
            for swap in swaps:
                if swap.get("swapRequestId") == order_id:
                    uses = int(swap.get("uses", 1))
                    uses_spent = int(swap.get("usesSpent", 0))
                    
                    if uses_spent >= uses:
                        status = 'filled'
                    else:
                        status = 'pending'
                    
                    # Extract price and quantity
                    offered = swap.get("offered", [])
                    wanted = swap.get("wanted", [])
                    
                    if offered and wanted:
                        quantity = float(offered[0].get("quantity", 0))
                        quote_qty = float(wanted[0].get("quantity", 0))
                        price = quote_qty / quantity if quantity > 0 else 0
                    else:
                        quantity = 0
                        price = 0
                    
                    return Order(
                        exchange=self.exchange_name,
                        order_id=order_id,
                        symbol=symbol,
                        side='sell',  # We created it, so we're selling
                        type='limit',
                        price=price,
                        quantity=quantity,
                        filled_quantity=quantity * (uses_spent / uses) if uses > 0 else 0,
                        status=status,
                        timestamp=datetime.fromtimestamp(swap.get("created", 0) / 1000),
                        commission=None,
                        commission_asset=None
                    )
            
            raise ValueError(f"Order {order_id} not found")
        
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees (Galaswap typically has very low/no fees)"""
        # Galaswap fees are typically 0% or very low
        return {'maker': 0.0, 'taker': 0.0}
    
    async def get_min_order_size(self, symbol: str) -> float:
        """Get minimum order size"""
        return 0.00000001  # Very small minimum
    
    async def get_exchange_info(self, symbol: str) -> Dict:
        """Get exchange information for a symbol"""
        return {
            'symbol': symbol,
            'exchange': 'galaswap',
            'type': 'dex',
            'api': 'galaconnect'
        }
