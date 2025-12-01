"""
Galaswap DEX Connector
Handles swaps on Galaswap using GalaConnect API
"""

import json
import uuid
import base64
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import aiohttp
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
        
        # Normalize signature (s must be <= n/2)
        from eth_keys.datatypes import Signature
        from eth_keys import keys as eth_keys_module
        
        ec = eth_keys_module.ecdsa
        curve_n = ec.secp256k1.curve.n
        
        # Check if s > n/2
        if signature.s > curve_n // 2:
            # Normalize: s = n - s
            new_s = curve_n - signature.s
            # Flip recovery param
            new_v = 1 - signature.v if signature.v in (0, 1) else signature.v
            signature = Signature(signature.r, new_s, new_v)
        
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
        
        self.wallet_address = wallet_address
        self.private_key = private_key
        
        # Initialize account for key operations
        if private_key.startswith('0x'):
            private_key_clean = private_key[2:]
        else:
            private_key_clean = private_key
        
        try:
            self.account = Account.from_key('0x' + private_key_clean)
        except:
            self.account = Account.from_key(private_key)
        
        self.public_key = public_key
        self.is_connected = False
        
        # Token registry for symbol -> token class mapping
        self.token_registry: Dict[str, Dict] = {}
        
        logger.info(f"Initialized Galaswap connector for wallet: {wallet_address}")
    
    async def connect(self):
        """Connect to GalaConnect API and fetch public key if needed"""
        try:
            # Fetch public key if not provided
            if not self.public_key:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.API_BASE_URL}/galachain/api/asset/public-key-contract/GetPublicKey",
                        json={"user": self.wallet_address},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.public_key = data.get("Data", {}).get("publicKey")
                            if not self.public_key:
                                raise ValueError("Could not fetch public key")
                            logger.info("Fetched public key from API")
                        else:
                            raise ConnectionError(f"Failed to fetch public key: {response.status}")
            
            # Test connection by fetching balances
            await self.get_balance()
            
            self.is_connected = True
            logger.info(f"✓ Connected to Galaswap (GalaConnect API)")
        
        except Exception as e:
            logger.error(f"Error connecting to Galaswap: {e}")
            raise
    
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
        base, quote = symbol.split('/')
        
        # Try to get from registry
        base_class = self.token_registry.get(base.upper(), {
            "collection": base.upper(),
            "category": "Unit",
            "type": "none",
            "additionalKey": "none"
        })
        
        quote_class = self.token_registry.get(quote.upper(), {
            "collection": quote.upper(),
            "category": "Unit",
            "type": "none",
            "additionalKey": "none"
        })
        
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
        headers: Optional[Dict] = None
    ) -> dict:
        """Make a signed API request"""
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
        
        async with aiohttp.ClientSession() as session:
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
    
    async def _make_unsigned_request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None
    ) -> dict:
        """Make an unsigned API request (for read operations)"""
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                f"{self.API_BASE_URL}{endpoint}",
                json=body or {},
                headers=headers
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"API error {response.status}: {error_text}")
                    raise Exception(f"API error {response.status}: {error_text}")
                
                return await response.json()
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Get order book for a symbol (from available swaps)
        
        Note: Galaswap doesn't have traditional order books.
        We simulate one from available swaps.
        """
        try:
            base_class, quote_class = self._parse_symbol(symbol)
            
            # Fetch available swaps (we want to buy base with quote)
            # So we offer quote and want base
            response = await self._make_unsigned_request(
                "POST",
                "/v1/FetchAvailableTokenSwaps",
                {
                    "offeredTokenClass": quote_class,  # What we're offering
                    "wantedTokenClass": base_class     # What we want
                }
            )
            
            swaps = response.get("results", [])
            
            # Build order book from swaps
            bids = []  # People offering base (we can buy from them)
            asks = []  # People wanting base (we can sell to them)
            
            for swap in swaps[:depth]:
                try:
                    # Swap perspective: they're offering base, wanting quote
                    offered = swap.get("offered", [])
                    wanted = swap.get("wanted", [])
                    
                    if offered and wanted:
                        # Calculate price: quote per base
                        base_qty = float(offered[0].get("quantity", 0))
                        quote_qty = float(wanted[0].get("quantity", 0))
                        
                        if base_qty > 0:
                            price = quote_qty / base_qty
                            bids.append((price, base_qty))
                except Exception as e:
                    logger.warning(f"Error parsing swap: {e}")
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
        
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data for a symbol"""
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
                raise ValueError(f"No price data available for {symbol}")
        
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
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
            
            for token_data in data:
                try:
                    token_class = token_data.get("tokenClass", {})
                    collection = token_class.get("collection", "")
                    quantity = float(token_data.get("quantity", "0"))
                    locked = float(token_data.get("lockedHolds", "0"))
                    
                    if quantity > 0 or locked > 0:
                        symbol = collection  # Use collection as symbol
                        balances[symbol] = Balance(
                            asset=symbol,
                            free=quantity - locked,
                            locked=locked
                        )
                except Exception as e:
                    logger.warning(f"Error parsing balance: {e}")
                    continue
            
            # Filter by asset if specified
            if asset:
                return {asset: balances.get(asset)} if asset in balances else {}
            
            return balances
        
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
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
