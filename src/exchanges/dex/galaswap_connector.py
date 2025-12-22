"""
Galaswap DEX Connector
Handles swaps on Galaswap using GalaConnect API
"""

import json
import uuid
import base64
import asyncio
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import aiohttp
from aiohttp import ClientConnectorError, ClientTimeout
from eth_account import Account
from eth_keys import keys
from eth_utils import keccak, to_checksum_address
import hashlib
try:
    import ecdsa
    from ecdsa import SigningKey
    from ecdsa.curves import SECP256k1
    ECDSA_AVAILABLE = True
except (ImportError, AttributeError):
    ECDSA_AVAILABLE = False

from ...exchanges.base_exchange import BaseExchange, OrderBook, Balance, Order
from ...utils.logger import get_logger

logger = get_logger()


class VirtualLedger:
    """
    Virtual Ledger for tracking GalaSwap wallet balances locally.
    
    This addresses API limitations where balance endpoints return 403 errors
    or only show liquidity positions. The ledger tracks balances based on
    executed trades and initial balances from config.
    """
    
    def __init__(self, wallet_address: str, ledger_file: Optional[str] = None):
        """
        Initialize Virtual Ledger
        
        Args:
            wallet_address: Wallet address (used as key for ledger)
            ledger_file: Optional path to JSON file for persistence
        """
        self.wallet_address = wallet_address
        self.ledger_file = ledger_file or f"data/galaswap_ledger_{wallet_address.replace('|', '_').replace(':', '_')}.json"
        self.balances: Dict[str, float] = {}  # Symbol -> balance (free)
        self.locked: Dict[str, float] = {}  # Symbol -> locked balance
        self._initialized = False
        
        # Ensure data directory exists
        if self.ledger_file:
            ledger_dir = os.path.dirname(self.ledger_file)
            if ledger_dir:  # Only create directory if path includes a directory
                os.makedirs(ledger_dir, exist_ok=True)
    
    def load_from_config(self, config: Dict) -> None:
        """
        Load initial balances from config's starting_balances section
        
        Args:
            config: Configuration dictionary (from config.yaml)
        """
        try:
            # Look for starting_balances in galaswap exchange config or root config
            starting_balances = None
            
            # First, try to find galaswap-specific config
            dex_exchanges = config.get("exchanges", {}).get("dex", [])
            for dex_config in dex_exchanges:
                if dex_config.get("name") == "galaswap" and "starting_balances" in dex_config:
                    starting_balances = dex_config.get("starting_balances", {})
                    break
            
            # If not found, try other locations
            if not starting_balances:
                starting_balances = (
                    config.get("galaswap", {}).get("starting_balances", {}) or
                    config.get("starting_balances", {})
                )
            
            if starting_balances:
                logger.info(f"Loading initial balances from config for wallet {self.wallet_address[:30]}...")
                for symbol, balance_value in starting_balances.items():
                    if isinstance(balance_value, (int, float)):
                        self.balances[symbol.upper()] = float(balance_value)
                        self.locked[symbol.upper()] = 0.0
                    elif isinstance(balance_value, dict):
                        self.balances[symbol.upper()] = float(balance_value.get("free", balance_value.get("balance", 0)))
                        self.locked[symbol.upper()] = float(balance_value.get("locked", 0))
                
                logger.info(f"Loaded {len(self.balances)} initial balances from config")
            else:
                logger.debug("No starting_balances found in config, starting with empty ledger")
        except Exception as e:
            logger.warning(f"Error loading starting balances from config: {e}. Starting with empty ledger.")
    
    def load_from_file(self) -> bool:
        """
        Load balances from JSON file if it exists
        
        Returns:
            True if file was loaded, False otherwise
        """
        if not self.ledger_file or not os.path.exists(self.ledger_file):
            return False
        
        try:
            with open(self.ledger_file, 'r') as f:
                data = json.load(f)
                self.balances = data.get("balances", {})
                self.locked = data.get("locked", {})
                logger.info(f"Loaded virtual ledger from {self.ledger_file}: {len(self.balances)} balances")
                return True
        except Exception as e:
            logger.warning(f"Error loading virtual ledger from file: {e}")
            return False
    
    def save_to_file(self) -> None:
        """Save current balances to JSON file"""
        if not self.ledger_file:
            return
        
        try:
            data = {
                "wallet_address": self.wallet_address,
                "last_updated": datetime.now().isoformat(),
                "balances": self.balances,
                "locked": self.locked
            }
            with open(self.ledger_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved virtual ledger to {self.ledger_file}")
        except Exception as e:
            logger.warning(f"Error saving virtual ledger to file: {e}")
    
    def update_balance(self, symbol: str, amount: float, is_locked: bool = False) -> None:
        """
        Update balance for a token
        
        Args:
            symbol: Token symbol (e.g., "GALA", "GUSDC")
            amount: Amount to add (positive) or subtract (negative)
            is_locked: If True, update locked balance; otherwise update free balance
        """
        symbol = symbol.upper()
        if is_locked:
            self.locked[symbol] = self.locked.get(symbol, 0.0) + amount
            if self.locked[symbol] < 0:
                self.locked[symbol] = 0.0
        else:
            self.balances[symbol] = self.balances.get(symbol, 0.0) + amount
            if self.balances[symbol] < 0:
                self.balances[symbol] = 0.0
        
        self.save_to_file()
    
    def record_swap(self, token_in: str, amount_in: float, token_out: str, amount_out: float) -> None:
        """
        Record a swap transaction in the ledger
        
        Args:
            token_in: Token being spent (symbol)
            amount_in: Amount being spent (positive number)
            token_out: Token being received (symbol)
            amount_out: Amount being received (positive number)
        """
        logger.info(
            f"📝 Virtual Ledger: Recording swap - "
            f"Spending {amount_in} {token_in.upper()}, "
            f"Receiving {amount_out} {token_out.upper()}"
        )
        
        # Subtract spent token
        self.update_balance(token_in, -amount_in, is_locked=False)
        
        # Add received token
        self.update_balance(token_out, amount_out, is_locked=False)
        
        logger.debug(
            f"Virtual Ledger updated - "
            f"{token_in.upper()}: {self.balances.get(token_in.upper(), 0.0):.8f}, "
            f"{token_out.upper()}: {self.balances.get(token_out.upper(), 0.0):.8f}"
        )
    
    def get_balance(self, symbol: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get balance(s) from virtual ledger
        
        Args:
            symbol: Optional symbol to get specific balance, or None for all
        
        Returns:
            Dictionary of Balance objects
        """
        balances = {}
        
        if symbol:
            symbol = symbol.upper()
            free = self.balances.get(symbol, 0.0)
            locked = self.locked.get(symbol, 0.0)
            if free > 0 or locked > 0:
                balances[symbol] = Balance(
                    asset=symbol,
                    free=free,
                    locked=locked
                )
        else:
            # Return all balances
            all_symbols = set(self.balances.keys()) | set(self.locked.keys())
            for sym in all_symbols:
                free = self.balances.get(sym, 0.0)
                locked = self.locked.get(sym, 0.0)
                if free > 0 or locked > 0:
                    balances[sym] = Balance(
                        asset=sym,
                        free=free,
                        locked=locked
                    )
        
        return balances
    
    def get_balance_value(self, symbol: str) -> float:
        """Get free balance for a specific symbol"""
        return self.balances.get(symbol.upper(), 0.0)
    
    def initialize(self, config: Optional[Dict] = None) -> None:
        """
        Initialize ledger: load from file first, then from config if needed
        
        Args:
            config: Optional config dictionary to load starting balances
        """
        if self._initialized:
            return
        
        # Try to load from file first
        loaded = self.load_from_file()
        
        # If file doesn't exist or is empty, load from config
        if not loaded and config:
            self.load_from_config(config)
            if self.balances:
                self.save_to_file()  # Save initial balances to file
        
        self._initialized = True
        logger.info(f"Virtual Ledger initialized with {len(self.balances)} token balances")


def derive_compressed_public_key(private_key: str) -> str:
    """
    Derive compressed public key from private key (base64 encoded)
    Same as TypeScript: ethers.SigningKey.computePublicKey(privateKey, true)
    
    Args:
        private_key: Private key in hex format (with or without 0x prefix)
    
    Returns:
        Base64 encoded compressed public key
    """
    # Clean private key
    private_key_clean = private_key[2:] if private_key.startswith('0x') else private_key
    private_key_bytes = bytes.fromhex(private_key_clean)
    
    # Method 1: Try eth_keys with compressed parameter (newer versions)
    try:
        private_key_obj = keys.PrivateKey(private_key_bytes)
        public_key_obj = private_key_obj.public_key
        try:
            public_key_bytes = public_key_obj.to_bytes(compressed=True)
            return base64.b64encode(public_key_bytes).decode('utf-8')
        except (TypeError, AttributeError):
            pass  # Fall through to manual construction
    except Exception as e:
        logger.debug(f"eth_keys method failed: {e}, trying alternatives...")
    
    # Method 2: Try ecdsa library directly (most reliable, if available)
    if ECDSA_AVAILABLE:
        try:
            signing_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            verifying_key = signing_key.get_verifying_key()
            # Get the point coordinates - try different API methods
            try:
                # Try direct point access
                point = verifying_key.pubkey.point
                x = point.x()
                y = point.y()
            except AttributeError:
                # Try alternative API
                try:
                    point = verifying_key.pubkey.point()
                    x = point.x()
                    y = point.y()
                except (AttributeError, TypeError):
                    # Try getting coordinates from the public key bytes
                    pubkey_bytes = verifying_key.to_string("compressed")
                    if len(pubkey_bytes) == 33:
                        # Already compressed, return it
                        return base64.b64encode(pubkey_bytes).decode('utf-8')
                    # Try uncompressed
                    pubkey_bytes = verifying_key.to_string("uncompressed")
                    if len(pubkey_bytes) == 65 and pubkey_bytes[0] == 0x04:
                        x_bytes = pubkey_bytes[1:33]
                        y_bytes = pubkey_bytes[33:65]
                        x = int.from_bytes(x_bytes, 'big')
                        y = int.from_bytes(y_bytes, 'big')
                    else:
                        raise ValueError("Could not extract coordinates from ecdsa public key")
            
            # Convert x to 32-byte big-endian
            x_bytes = x.to_bytes(32, 'big')
            
            # Determine prefix: 0x02 if y is even, 0x03 if y is odd
            y_int = int(y)
            prefix = 0x02 if (y_int % 2 == 0) else 0x03
            
            # Construct compressed public key: prefix + x coordinate
            public_key_bytes = bytes([prefix]) + x_bytes
            return base64.b64encode(public_key_bytes).decode('utf-8')
        except Exception as e:
            logger.debug(f"ecdsa method failed: {e}, trying eth_keys manual method...")
    
    # Method 3: Manual construction using eth_keys (fallback)
    try:
        private_key_obj = keys.PrivateKey(private_key_bytes)
        public_key_obj = private_key_obj.public_key
        
        # Try different methods to get x, y coordinates
        x = None
        y = None
        
        # Method 3a: Try to_point() (some versions)
        try:
            point = public_key_obj.to_point()
            x = point.x()
            y = point.y()
        except AttributeError:
            # Method 3b: Try accessing _key attribute (eth_keys internal)
            try:
                key_obj = public_key_obj._key
                x = key_obj.pubkey.point.x()
                y = key_obj.pubkey.point.y()
            except AttributeError:
                # Method 3c: Use to_bytes() and extract from uncompressed format
                uncompressed = public_key_obj.to_bytes()
                logger.debug(f"Uncompressed public key length: {len(uncompressed)}, first byte: {hex(uncompressed[0]) if len(uncompressed) > 0 else 'N/A'}")
                
                # Handle different formats
                if len(uncompressed) == 65 and uncompressed[0] == 0x04:
                    # Standard uncompressed format: 0x04 + 32 bytes x + 32 bytes y
                    x_bytes = uncompressed[1:33]
                    y_bytes = uncompressed[33:65]
                    x = int.from_bytes(x_bytes, 'big')
                    y = int.from_bytes(y_bytes, 'big')
                elif len(uncompressed) == 64:
                    # Some versions return 64 bytes (x + y without prefix)
                    x_bytes = uncompressed[0:32]
                    y_bytes = uncompressed[32:64]
                    x = int.from_bytes(x_bytes, 'big')
                    y = int.from_bytes(y_bytes, 'big')
                elif len(uncompressed) == 33:
                    # Already compressed format
                    return base64.b64encode(uncompressed).decode('utf-8')
                else:
                    raise ValueError(
                        f"Unexpected public key format: length={len(uncompressed)}, "
                        f"first_byte={hex(uncompressed[0]) if len(uncompressed) > 0 else 'N/A'}"
                    )
        
        if x is None or y is None:
            raise ValueError("Could not extract x, y coordinates from public key")
        
        # Convert x to 32-byte big-endian
        x_bytes = x.to_bytes(32, 'big')
        
        # Determine prefix: 0x02 if y is even, 0x03 if y is odd
        y_int = int(y)
        prefix = 0x02 if (y_int % 2 == 0) else 0x03
        
        # Construct compressed public key: prefix + x coordinate
        public_key_bytes = bytes([prefix]) + x_bytes
        return base64.b64encode(public_key_bytes).decode('utf-8')
    
    except Exception as e:
        error_msg = f"Failed to derive compressed public key: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


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


def sign_payload_for_bundle(payload: dict, private_key: str) -> str:
    """
    Sign payload for bundle API execution.
    Returns hex-encoded signature (r + s concatenated, 64 bytes = 128 hex chars).
    
    Args:
        payload: Payload dictionary to sign
        private_key: Private key in hex format (with or without 0x prefix)
    
    Returns:
        Hex-encoded signature string (128 characters)
    """
    try:
        # Stringify deterministically
        string_to_sign = deterministic_json_stringify(payload)
        
        # Hash with keccak256
        string_bytes = string_to_sign.encode('utf-8')
        hash_bytes = keccak(string_bytes)
        
        # Sign with private key
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        private_key_bytes = bytes.fromhex(private_key)
        private_key_obj = keys.PrivateKey(private_key_bytes)
        signature = private_key_obj.sign_msg_hash(hash_bytes)
        
        # Normalize signature (same as TypeScript version)
        curve_n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        r_value = signature.r
        s_value = signature.s
        
        # Normalize s if needed
        half_n = curve_n // 2
        if s_value > half_n:
            s_value = curve_n - s_value
        
        # Convert to hex format (r + s concatenated, each 32 bytes = 64 hex chars)
        r_hex = format(r_value, '064x')  # 64 hex chars (32 bytes)
        s_hex = format(s_value, '064x')  # 64 hex chars (32 bytes)
        
        return r_hex + s_hex  # 128 hex characters total
        
    except Exception as e:
        logger.error(f"Error signing payload for bundle: {e}")
        raise Exception(f"Failed to sign payload for bundle: {e}")


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
        
        # Normalize signature (same as TypeScript version)
        # If s > n/2, use n - s (this is required for GalaSwap API)
        # secp256k1 curve order n (constant)
        # 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        curve_n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        
        # Normalize s if needed (same logic as TypeScript)
        r_value = signature.r
        s_value = signature.s
        
        # Check if s > n/2 and normalize (same as TypeScript: signature.s.cmp(ecSecp256k1.curve.n.shrn(1)) > 0)
        half_n = curve_n // 2
        if s_value > half_n:
            s_value = curve_n - s_value
            logger.debug(f"Normalized signature s value (was > n/2)")
        
        # Convert to DER format and base64 encode
        # Proper DER encoding for ECDSA signature
        r_bytes = r_value.to_bytes(32, 'big')
        s_bytes = s_value.to_bytes(32, 'big')
        
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


def token_class_to_composite_key(token_class: Dict) -> str:
    """
    Convert token class dict to composite key string format used by new GalaSwap API.
    
    Format: "collection$category$type$additionalKey"
    Example: {"collection": "GALA", "category": "Unit", "type": "none", "additionalKey": "none"}
    -> "GALA$Unit$none$none"
    """
    collection = token_class.get("collection", "")
    category = token_class.get("category", "")
    type_val = token_class.get("type", "none")
    additional_key = token_class.get("additionalKey", "none")
    
    return f"{collection}${category}${type_val}${additional_key}"


def composite_key_to_token_class(composite_key: str) -> Dict:
    """
    Convert composite key string to token class dict.
    
    Format: "collection$category$type$additionalKey"
    Example: "GALA$Unit$none$none"
    -> {"collection": "GALA", "category": "Unit", "type": "none", "additionalKey": "none"}
    """
    parts = composite_key.split("$")
    if len(parts) != 4:
        raise ValueError(f"Invalid composite key format: {composite_key}")
    
    return {
        "collection": parts[0],
        "category": parts[1],
        "type": parts[2],
        "additionalKey": parts[3]
    }


def format_quantity(quantity: float, decimals: int = 8) -> str:
    """
    Format quantity to string with specified decimal places.
    GalaSwap API requires quantities to have at most 8 decimal places.
    
    Args:
        quantity: Quantity value
        decimals: Maximum decimal places (default 8 for GalaSwap)
    
    Returns:
        Formatted quantity string
    """
    # Round to specified decimal places and remove trailing zeros
    rounded = round(quantity, decimals)
    # Format to avoid scientific notation and remove trailing zeros
    formatted = f"{rounded:.{decimals}f}".rstrip('0').rstrip('.')
    return formatted


class GalaswapConnector(BaseExchange):
    """Galaswap exchange connector using GalaConnect API"""
    
    # API Base URL - can be overridden via environment variable GALASWAP_API_BASE_URL
    # Updated to new backend URL: https://dex-backend-prod1.defi.gala.com/
    # Previous URL: https://api-galaswap.gala.com (may still work but new URL is preferred)
    # Note: https://swap.gala.com/ is the frontend website, not the API endpoint
    # Check environment variable first, then use default
    API_BASE_URL = os.getenv("GALASWAP_API_BASE_URL", "https://dex-backend-prod1.defi.gala.com")
    
    # Asset API Base URL - for GalaChain Asset API (separate from DEX API)
    # Used for fetching actual on-chain balances
    ASSET_API_BASE_URL = os.getenv("GALASWAP_ASSET_API_BASE_URL", "https://api-galaswap.gala.com")
    REQUEST_TIMEOUT = 10  # seconds (increased for signed requests)
    SIGNED_REQUEST_TIMEOUT = 30  # seconds (longer timeout for order execution)
    MAX_RETRIES = 3  # Increased retries for better reliability
    RETRY_DELAY_BASE = 2  # seconds (increased delay between retries)
    
    # Circuit breaker: disable after consecutive failures
    _circuit_breaker_threshold = 10  # Disable after 10 consecutive failures (less aggressive)
    _circuit_breaker_reset_time = 180  # Re-enable after 3 minutes (faster recovery)
    
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
        
        # Derive Ethereum address from private key (this is the authoritative address)
        # GalaChain uses Ethereum-compatible addresses, so we derive the Ethereum address
        derived_ethereum_address = self.account.address
        
        # Store both addresses
        self.ethereum_address = derived_ethereum_address  # For reference
        self.gala_address = wallet_address  # Original address (may be different)
        
        # IMPORTANT: GalaChain supports both Ethereum-compatible and native addresses
        # - Ethereum addresses: Use with "eth|" prefix (e.g., "eth|a7027114A40d21382951b03e3067429106e6e806")
        # - GalaChain native: Use with "client|" prefix (e.g., "client|123456789abcdef012345678")
        # The API verifies that the signature matches the address in X-Wallet-Address header
        # We MUST use the address that corresponds to the private key
        
        # Check if provided address matches derived address
        provided_address_clean = wallet_address.replace('eth|', '').replace('client|', '').replace('0x', '').lower()
        derived_address_clean = derived_ethereum_address.replace('0x', '').lower()
        
        if provided_address_clean == derived_address_clean:
            # Addresses match - use provided format (may have eth| or client| prefix)
            if '|' in wallet_address:
                # Already in GalaChain format (eth| or client|)
                self.wallet_address_for_api = wallet_address
                logger.info(f"✓ Using GalaChain address format: {wallet_address[:30]}...")
            elif wallet_address.startswith('0x'):
                # Ethereum address - convert to eth| format for GalaChain API
                self.wallet_address_for_api = f"eth|{wallet_address[2:]}"
                logger.info(f"✓ Converted Ethereum address to GalaChain format: eth|{wallet_address[2:30]}...")
            else:
                # Assume it's already in GalaChain format (without prefix, might be client| format)
                self.wallet_address_for_api = wallet_address
                logger.info(f"✓ Using provided GalaChain address: {wallet_address[:30]}...")
        else:
            # Addresses don't match - CRITICAL: Use derived address to fix signature errors
            # The error message will show which address the API expects
            logger.warning(
                f"⚠️  WARNING: Configured wallet address '{wallet_address[:20]}...' does NOT match "
                f"private key's derived Ethereum address '{derived_ethereum_address[:20]}...'. "
                f"This will cause signature errors! Using derived address instead."
            )
            # Use derived Ethereum address in eth| format (GalaChain API format for Ethereum addresses)
            # This should match the address shown in error messages like:
            # "DTO should be signed by a7027114A40d21382951b03e3067429106e6e806 private key"
            self.wallet_address_for_api = f"eth|{derived_ethereum_address[2:]}"
            logger.info(
                f"✓ Using derived Ethereum address for GalaChain API: eth|{derived_ethereum_address[2:30]}... "
                f"(This should match the address in signature error messages)"
            )
        
        # Store provided public key if given, but we'll always try to fetch from API first
        # The API public key is the authoritative source - it must match what's registered on GalaChain
        self.public_key = public_key  # May be None - will be fetched from API during connect()
        self._public_key_derived = False  # Track if we derived it (vs fetched from API)
        
        self.is_connected = False
        
        # Circuit breaker state (instance-level)
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        
        # Token registry for symbol -> token class mapping
        self.token_registry: Dict[str, Dict] = {}
        
        # Load token registry from config file if available
        self._load_token_registry()
        
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
        
        # Initialize Virtual Ledger for balance tracking
        # This addresses API limitations (403 errors, positions-only data)
        self.virtual_ledger = VirtualLedger(
            wallet_address=self.wallet_address_for_api,
            ledger_file=None  # Will use default path
        )
        self._ledger_initialized = False
        
        logger.info(f"Initialized Galaswap connector for wallet: {wallet_address}")
    
    def _load_token_registry(self):
        """Load token registry from galaswap_tokens.json config file"""
        try:
            import os
            from pathlib import Path
            
            # Try to find config file relative to project root
            config_paths = [
                Path(__file__).parent.parent.parent.parent / "config" / "galaswap_tokens.json",
                Path("config") / "galaswap_tokens.json",
                Path("../config") / "galaswap_tokens.json",
            ]
            
            config_file = None
            for path in config_paths:
                if path.exists():
                    config_file = path
                    break
            
            if config_file:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                # Load token registry
                registry = config.get("token_registry", {})
                for symbol, token_info in registry.items():
                    # Extract token class (collection, category, type, additionalKey)
                    token_class = {
                        "collection": token_info.get("collection", symbol),
                        "category": token_info.get("category", "Unit"),
                        "type": token_info.get("type", "none"),
                        "additionalKey": token_info.get("additionalKey", "none")
                    }
                    self.token_registry[symbol.upper()] = token_class
                    
                    # Also update token names if provided
                    if "name" in token_info:
                        self.token_names[symbol.upper()] = token_info["name"]
                
                logger.info(f"Loaded {len(self.token_registry)} tokens from {config_file}")
        except Exception as e:
            # Don't fail if config file doesn't exist - use defaults
            logger.debug(f"Could not load token registry from config: {e}")
    
    async def connect(self):
        """Connect to GalaConnect API and fetch public key from API (required for GalaChain)"""
        try:
            # ALWAYS fetch public key from API first - this is the authoritative source
            # The public key must match what's registered with your GalaChain wallet address
            try:
                timeout = ClientTimeout(total=self.REQUEST_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # Use GalaChain address format for public key lookup
                    gala_address_for_api = getattr(self, 'wallet_address_for_api', self.wallet_address)
                    # Format Ethereum addresses with eth| prefix for GalaChain API
                    if gala_address_for_api.startswith('0x') and '|' not in gala_address_for_api:
                        gala_address_for_api = f"eth|{gala_address_for_api[2:]}"
                    
                    logger.info(f"Fetching public key from GalaChain API for wallet: {gala_address_for_api[:30]}...")
                    async with session.post(
                        f"{self.API_BASE_URL}/galachain/api/asset/public-key-contract/GetPublicKey",
                        json={"user": gala_address_for_api},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status in [404, 403]:
                            # Endpoint deprecated (404) or forbidden (403) - try to derive public key or use provided one
                            status_msg = "deprecated (404)" if response.status == 404 else "forbidden (403 - rate limiting/access restriction)"
                            logger.warning(
                                f"Public key endpoint {status_msg}. "
                                f"Using derived public key (may cause signature errors if not registered)."
                            )
                            # Derive public key as fallback
                            try:
                                derived_pubkey = derive_compressed_public_key(self.private_key)
                                self.public_key = derived_pubkey
                                self._public_key_derived = True
                                logger.warning(
                                    "⚠️  Using DERIVED public key - this may cause signature errors. "
                                    "Public key should be fetched from API or provided in config."
                                )
                            except Exception as derive_error:
                                logger.error(f"Failed to derive public key: {derive_error}")
                                raise Exception(
                                    "Cannot get public key: API endpoint unavailable and derivation failed. "
                                    "Please provide public key in configuration."
                                )
                            # Skip the rest of the public key fetching logic
                            return
                        elif response.status == 200:
                            data = await response.json()
                            api_public_key = data.get("Data", {}).get("publicKey")
                            if api_public_key:
                                # Use API public key - this is the one registered with your wallet
                                self.public_key = api_public_key
                                self._public_key_derived = False
                                logger.info(
                                    f"✓ Fetched public key from GalaChain API: "
                                    f"length={len(self.public_key)}, "
                                    f"preview={self.public_key[:30]}..."
                                )
                            else:
                                logger.warning("Public key not found in API response Data field")
                                # Try alternative response structure
                                api_public_key = data.get("publicKey") or data.get("PublicKey")
                                if api_public_key:
                                    self.public_key = api_public_key
                                    self._public_key_derived = False
                                    logger.info(f"✓ Found public key in alternative response field")
                                else:
                                    raise Exception("Public key not found in API response")
                        else:
                            # Try to get error message from response
                            try:
                                error_data = await response.json()
                                error_msg = error_data.get("Message", error_data.get("message", error_data.get("error", "Unknown error")))
                            except:
                                error_msg = await response.text()
                            
                            logger.warning(
                                f"Failed to fetch public key from API (status {response.status}): {error_msg}. "
                                f"This is CRITICAL - public key must match what's registered on GalaChain."
                            )
                            raise Exception(f"API returned status {response.status}: {error_msg}")
                            
            except (ClientConnectorError, asyncio.TimeoutError) as fetch_error:
                # Network errors - this is critical, we need the API public key
                logger.error(
                    f"❌ CRITICAL: Cannot connect to GalaChain API to fetch public key: {fetch_error}. "
                    f"Public key MUST be fetched from API to match your registered wallet. "
                    f"Derived public keys will NOT work for GalaChain API."
                )
                raise Exception(
                    f"Cannot fetch public key from GalaChain API. "
                    f"This is required - derived public keys do not match registered keys. "
                    f"Error: {fetch_error}"
                )
            except Exception as fetch_error:
                error_msg = str(fetch_error)
                # Check if it's a 403 error - treat as non-critical (rate limiting)
                if "403" in error_msg or "forbidden" in error_msg.lower():
                    logger.warning(
                        f"Public key endpoint returned 403 (rate limiting/access restriction). "
                        f"Using derived public key as fallback."
                    )
                    # Derive public key as fallback
                    try:
                        derived_pubkey = derive_compressed_public_key(self.private_key)
                        self.public_key = derived_pubkey
                        self._public_key_derived = True
                        logger.warning(
                            "⚠️  Using DERIVED public key due to API access restriction. "
                            "This may cause signature errors if the derived key doesn't match registered key."
                        )
                        return  # Successfully derived, continue
                    except Exception as derive_error:
                        logger.error(f"Failed to derive public key: {derive_error}")
                        raise Exception(
                            "Cannot get public key: API access forbidden and derivation failed. "
                            "Please provide public key in configuration or wait for rate limit to reset."
                        )
                else:
                    # Other errors are still critical
                    logger.error(
                        f"❌ CRITICAL: Failed to fetch public key from GalaChain API: {error_msg}. "
                        f"Public key MUST match what's registered with your wallet address."
                    )
                    raise Exception(
                        f"Failed to fetch public key from GalaChain API: {error_msg}. "
                        f"This is required for GalaChain API authentication."
                    )
            
            # Initialize Virtual Ledger if not already initialized
            if not self._ledger_initialized:
                try:
                    # Try to load config for starting balances
                    config_data = None
                    try:
                        import yaml
                        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
                        if os.path.exists(config_path):
                            with open(config_path, 'r') as f:
                                config_data = yaml.safe_load(f) or {}
                            logger.debug(f"Loaded config from {config_path} for virtual ledger")
                    except ImportError:
                        logger.debug("yaml module not available, skipping config load for virtual ledger")
                    except Exception as config_error:
                        logger.debug(f"Could not load config for virtual ledger: {config_error}")
                    
                    # Initialize ledger (will load from file if exists, or from config)
                    self.virtual_ledger.initialize(config=config_data)
                    self._ledger_initialized = True
                    logger.info(
                        f"✓ Virtual Ledger initialized with {len(self.virtual_ledger.balances)} token balances. "
                        f"Ledger file: {self.virtual_ledger.ledger_file}"
                    )
                except Exception as ledger_error:
                    logger.warning(f"Could not initialize virtual ledger: {ledger_error}. Will continue without it.")
            
            # Test connection by fetching balances (this will fail gracefully if wallet is empty)
            # Use virtual ledger if available, otherwise try API
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
        # Use GalaChain address format for API header (client|... or eth|...)
        # GalaChain API expects the GalaChain address format, not Ethereum address
        wallet_address_for_header = getattr(self, 'wallet_address_for_api', self.wallet_address)
        # Format Ethereum addresses with eth| prefix for GalaChain API
        if wallet_address_for_header.startswith('0x') and '|' not in wallet_address_for_header:
            wallet_address_for_header = f"eth|{wallet_address_for_header[2:]}"
        headers["X-Wallet-Address"] = wallet_address_for_header
        logger.info(
            f"Using wallet address in X-Wallet-Address header: {wallet_address_for_header[:50]}... "
            f"(Derived from private key: {self.ethereum_address[:20]}...)"
        )
        
        # Add public key and unique key if not present
        if "signerPublicKey" not in body:
            # Ensure we have the public key from API (not derived)
            if not self.public_key or self._public_key_derived:
                # Reconnect to fetch public key from API if we don't have it or it was derived
                if not self.is_connected:
                    await self.connect()
                elif self._public_key_derived:
                    # Try to fetch again - derived keys don't work with GalaChain API
                    logger.warning("Public key was derived, attempting to fetch from API again...")
                    try:
                        timeout = ClientTimeout(total=self.REQUEST_TIMEOUT)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            gala_addr = getattr(self, 'wallet_address_for_api', self.wallet_address)
                            if gala_addr.startswith('0x') and '|' not in gala_addr:
                                gala_addr = f"eth|{gala_addr[2:]}"
                            async with session.post(
                                f"{self.API_BASE_URL}/galachain/api/asset/public-key-contract/GetPublicKey",
                                json={"user": gala_addr},
                                headers={"Content-Type": "application/json"}
                            ) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    api_pubkey = data.get("Data", {}).get("publicKey") or data.get("publicKey") or data.get("PublicKey")
                                    if api_pubkey:
                                        self.public_key = api_pubkey
                                        self._public_key_derived = False
                                        logger.info("✓ Re-fetched public key from API")
                    except Exception as e:
                        logger.error(f"Failed to re-fetch public key: {e}")
                        raise Exception(
                            f"Public key must be fetched from GalaChain API. "
                            f"Derived public keys do not match registered keys. Error: {e}"
                        )
            
            if not self.public_key:
                raise Exception(
                    "Public key is required for signed requests but is not available. "
                    "Must be fetched from GalaChain API - derived keys will not work."
                )
            
            if self._public_key_derived:
                logger.error(
                    "⚠️  WARNING: Using derived public key - this will likely cause PUBLIC_KEY_MISMATCH errors. "
                    "Public key must be fetched from GalaChain API."
                )
            
            body["signerPublicKey"] = self.public_key
            logger.info(
                f"Using public key for signed request: "
                f"wallet_address={wallet_address_for_header}, "
                f"public_key_length={len(self.public_key)}, "
                f"public_key_preview={self.public_key[:30]}..., "
                f"source={'API' if not self._public_key_derived else 'DERIVED (WILL FAIL)'}"
            )
        if "uniqueKey" not in body:
            body["uniqueKey"] = self._generate_unique_key()
        
        # Sign the request
        try:
            logger.debug(f"Signing request with wallet: {self.wallet_address[:20]}...")
            signature = sign_request_body(body, self.private_key)
            body["signature"] = signature
            logger.debug("Request signed successfully")
        except Exception as e:
            logger.error(f"Error signing request body: {e}")
            raise Exception(f"Failed to sign request: {e}")
        
        # Use longer timeout for signed requests (order execution)
        timeout = ClientTimeout(total=self.SIGNED_REQUEST_TIMEOUT)
        last_error = None
        
        for attempt in range(self.MAX_RETRIES if retry_on_connection_error else 1):
            try:
                logger.debug(f"Making signed request to {endpoint} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(
                        method,
                        f"{self.API_BASE_URL}{endpoint}",
                        json=body,
                        headers=headers
                    ) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            logger.error(f"API error {response.status} for {endpoint}: {error_text[:200]}")
                            
                            # Don't retry on 4xx errors (client errors)
                            if 400 <= response.status < 500:
                                raise Exception(f"API error {response.status}: {error_text[:200]}")
                            
                            # Retry on 5xx errors (server errors)
                            raise Exception(f"API error {response.status}: {error_text[:200]}")
                        
                        result = await response.json()
                        logger.debug(f"Signed request to {endpoint} succeeded")
                        return result
            
            except (ClientConnectorError, asyncio.TimeoutError) as e:
                last_error = e
                # Log connection errors with full URL for debugging
                logger.warning(
                    f"Connection/timeout error to Galaswap API: "
                    f"URL={self.API_BASE_URL}{endpoint}, "
                    f"Error={type(e).__name__}: {str(e)[:200]}"
                )
                if attempt < (self.MAX_RETRIES - 1) if retry_on_connection_error else 0:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(
                        f"Retrying in {delay}s... (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    error_msg = f"Failed to connect to Galaswap API after {self.MAX_RETRIES} attempts: URL={self.API_BASE_URL}{endpoint}, Error={type(e).__name__}: {e}"
                    logger.error(error_msg)
                    self._record_failure()  # Record failure for circuit breaker
                    raise Exception(error_msg) from e
            
            except Exception as e:
                # For non-connection errors, don't retry unless it's a 5xx error
                error_msg = str(e)
                if "API error 5" in error_msg and attempt < (self.MAX_RETRIES - 1):
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"Server error, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
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
                    # Handle GET vs POST requests differently
                    if method.upper() == "GET":
                        # GET request - query params in URL, no body
                        request_kwargs = {"headers": headers}
                    else:
                        # POST/PUT/etc - JSON body
                        request_kwargs = {"json": body or {}, "headers": headers}
                    
                    async with session.request(
                        method,
                        f"{self.API_BASE_URL}{endpoint}",
                        **request_kwargs
                    ) as response:
                        if response.status >= 400:
                            error_text = await response.text()
                            
                            # Check if this is a deprecated endpoint (404 on old endpoints)
                            deprecated_endpoints = [
                                "/v1/FetchAvailableTokenSwaps",
                                "/galachain/api/asset/token-contract/FetchBalances",
                                "/galachain/api/asset/public-key-contract/GetPublicKey",
                                "/galachain/api/asset/token-contract/FetchTokenSwapsOfferedByUser"
                            ]
                            is_deprecated = any(dep in endpoint for dep in deprecated_endpoints)
                            
                            # Check if this is a "pool not found" or "token ordering" error (400) - not a failure
                            is_pool_not_found = (
                                response.status == 400 and 
                                ("Pool data not found" in error_text or 
                                 "Token0 must be smaller" in error_text or
                                 "pool" in error_text.lower())
                            )
                            
                            # Check if this is a 403 Forbidden (rate limiting or access restriction) - not a failure
                            is_forbidden = response.status == 403
                            
                            if response.status == 404 and is_deprecated:
                                # Deprecated endpoint - don't record as failure, just log and return
                                logger.debug(
                                    f"GalaSwap deprecated endpoint (404): {endpoint}. "
                                    f"Old swap-based API endpoints are no longer available. "
                                    f"New V3 DEX API uses different endpoints."
                                )
                                # Don't record 404 on deprecated endpoints as failure
                                raise Exception(f"Deprecated endpoint (404): {endpoint} - Old API no longer available")
                            
                            if is_pool_not_found:
                                # Pool doesn't exist - this is expected for many pairs, don't record as failure
                                logger.debug(
                                    f"GalaSwap pool not found (400): {endpoint}. "
                                    f"This is expected for pairs that don't have liquidity pools on GalaSwap."
                                )
                                # Don't record 400 "pool not found" as failure
                                raise Exception(f"Pool not found (400): {endpoint} - Pool does not exist")
                            
                            if is_forbidden:
                                # 403 Forbidden - likely rate limiting or access restriction, don't record as failure
                                logger.debug(
                                    f"GalaSwap API access forbidden (403): {endpoint}. "
                                    f"This may be due to rate limiting or API access restrictions."
                                )
                                # Don't record 403 as failure
                                raise Exception(f"API access forbidden (403): {endpoint} - Rate limiting or access restriction")
                            
                            # Log the actual error for debugging (especially important with new API URL)
                            logger.warning(
                                f"Galaswap API error {response.status} for {endpoint}: "
                                f"URL={self.API_BASE_URL}{endpoint}, "
                                f"Error={error_text[:200]}"
                            )
                            
                            # Handle 502 Bad Gateway and 503 Service Unavailable as temporary errors
                            if response.status in [502, 503, 504]:
                                # These are temporary server errors
                                self._record_failure()
                                raise Exception(f"API error {response.status}: Service temporarily unavailable - {error_text[:100]}")
                            else:
                                # Other 4xx/5xx errors - log the actual error
                                # Only record as failure if not a deprecated endpoint 404, pool not found 400, or forbidden 403
                                if not (response.status == 404 and is_deprecated) and not is_pool_not_found and not is_forbidden:
                                    self._record_failure()
                                    raise Exception(f"API error {response.status}: {error_text[:200]}")
                                # If it's a deprecated endpoint, pool not found, or forbidden, don't record failure
                                # These are handled gracefully elsewhere
                        
                        # Success - reset circuit breaker
                        self._record_success()
                        return await response.json()
            
            except (ClientConnectorError, asyncio.TimeoutError) as e:
                last_error = e
                self._record_failure()
                
                # Log connection errors with full URL for debugging (especially important with new API URL)
                error_msg = (
                    f"Galaswap API connection error: "
                    f"URL={self.API_BASE_URL}{endpoint}, "
                    f"Error={type(e).__name__}: {str(e)[:200]}"
                )
                
                if attempt < (self.MAX_RETRIES - 1) if retry_on_connection_error else 0:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    # Log on first attempt to see what's failing
                    if attempt == 0:
                        logger.warning(f"{error_msg} - Retrying in {delay}s... (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"{error_msg} - Failed after {self.MAX_RETRIES} attempts")
                    raise Exception(f"Failed to connect to Galaswap API: {error_msg}") from e
            
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
            
            # NEW API: Use /v1/trade/pool and /v1/trade/quote to build order book
            # V3 DEX uses liquidity pools, not traditional order books
            # We'll simulate an order book using quotes at different amounts
            
            base_token_key = token_class_to_composite_key(base_class)
            quote_token_key = token_class_to_composite_key(quote_class)
            
            # IMPORTANT: GalaSwap API requires token0 to be lexicographically smaller than token1
            # Compare the composite keys to determine correct order
            if base_token_key > quote_token_key:
                # Swap tokens: token0 must be smaller
                token0_key = quote_token_key
                token1_key = base_token_key
                token0_class = quote_class
                token1_class = base_class
                # Note: This means we're querying the reverse pool
            else:
                token0_key = base_token_key
                token1_key = quote_token_key
                token0_class = base_class
                token1_class = quote_class
            
            # Try to get pool details first (need to know fee tier)
            # Common fee tiers: 500 (0.05%), 3000 (0.30%), 10000 (1.00%)
            fee_tiers = [3000, 500, 10000]  # Try standard fee tier first
            
            pool_data = None
            for fee in fee_tiers:
            try:
                response = await self._make_unsigned_request(
                        "GET",
                        f"/v1/trade/pool?token0={token0_key}&token1={token1_key}&fee={fee}",
                        None  # GET request
                    )
                    data = response.get("data", {})
                    pool_data = data.get("Data", {}) if isinstance(data, dict) else {}
                    if pool_data:
                        break
                except Exception as e:
                    error_msg = str(e)
                    # "Pool not found" or "Token0 must be smaller" are expected for many pairs
                    if "Pool not found" in error_msg or "Pool data not found" in error_msg:
                        logger.debug(f"Pool not found for {symbol} with fee tier {fee} - this is expected for pairs without liquidity pools")
                    elif "Token0 must be smaller" in error_msg:
                        # This shouldn't happen now, but log it if it does
                        logger.debug(f"Token ordering issue for {symbol} with fee tier {fee} (should be fixed)")
                    else:
                        logger.debug(f"Pool lookup failed for fee tier {fee}: {e}")
                    continue
            
            if not pool_data:
                # No pool found - return empty order book
                logger.debug(f"No pool found for {symbol} on GalaSwap")
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            # Get current price using quote endpoint
            # We want the price of base in terms of quote (how much quote for 1 base)
            # So we need: tokenIn = quote, tokenOut = base
            try:
                # Determine which token is input/output based on the pool order
                # We want to buy base with quote, so quote is input, base is output
                if token0_key == base_token_key:
                    # Base is token0, quote is token1 - to get base price: quote in, base out
                    quote_response = await self._make_unsigned_request(
                        "GET",
                        f"/v1/trade/quote?tokenIn={token1_key}&tokenOut={token0_key}&amountIn=1",
                        None
                    )
                else:
                    # Base is token1, quote is token0 - to get base price: quote in, base out
                    quote_response = await self._make_unsigned_request(
                        "GET",
                        f"/v1/trade/quote?tokenIn={token0_key}&tokenOut={token1_key}&amountIn=1",
                        None
                    )
                quote_data = quote_response.get("data", {})
                if quote_data:
                    amount_in = float(quote_data.get("amountIn", 0))
                    amount_out = float(quote_data.get("amountOut", 0))
                    if amount_out > 0:
                        current_price = amount_in / amount_out
                    else:
                        current_price = 0
                else:
                    current_price = 0
            except Exception as e:
                logger.debug(f"Could not get quote for {symbol}: {e}")
                current_price = 0
            
            if current_price == 0:
                return OrderBook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    bids=[],
                    asks=[],
                    timestamp=datetime.now()
                )
            
            # Build simulated order book from current price
            # V3 DEX doesn't have traditional order book, so we simulate one
            bids = []
            asks = []
            
            # Create bid levels (buy orders) - slightly below current price
            for i in range(depth):
                price = current_price * (1 - 0.001 * (i + 1))  # 0.1% spread per level
                quantity = 10.0 / (i + 1)  # Decreasing quantity
                bids.append((price, quantity))
            
            # Create ask levels (sell orders) - slightly above current price
            for i in range(depth):
                price = current_price * (1 + 0.001 * (i + 1))  # 0.1% spread per level
                quantity = 10.0 / (i + 1)  # Decreasing quantity
                asks.append((price, quantity))
            
            return OrderBook(
                exchange=self.exchange_name,
                symbol=symbol,
                bids=bids,
                asks=asks,
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
        Get ticker data for a symbol using new GalaSwap DEX API
        
        Uses /v1/trade/price endpoint for base token price, then calculates bid/ask from quotes.
        Returns empty ticker data if API is unreachable to allow bot to continue.
        """
        try:
            base_class, quote_class = self._parse_symbol(symbol)
            
            # Get base token price using new API
            base_token_key = token_class_to_composite_key(base_class)
            
            try:
                # Try new API endpoint: GET /v1/trade/price
                # Alternative: /price-oracle/fetch-price for historical data
                response = await self._make_unsigned_request(
                    "GET",
                    f"/v1/trade/price?token={base_token_key}",
                    None  # GET request, no body
                )
                
                # Response format: {"price": "number", "timestamp": "string"}
                # Or wrapped in data: {"data": {"price": "...", "timestamp": "..."}}
                if isinstance(response, dict):
                    if "data" in response:
                        price_data = response["data"]
                    elif "price" in response:
                        price_data = response
                    else:
                        price_data = response
                else:
                    price_data = response
                
                base_price = float(price_data.get("price", 0))
                
                if base_price > 0:
                    # For DEX, bid and ask are typically close to the current price
                    # Use a small spread estimate (0.1%) or get quotes
                    spread = base_price * 0.001  # 0.1% spread
                    bid = base_price - spread
                    ask = base_price + spread
                    
                    return {
                        'symbol': symbol,
                        'bid': bid,
                        'ask': ask,
                        'last': base_price,
                        'volume': 0.0,  # Volume not available from price endpoint
                        'timestamp': datetime.now()
                    }
                else:
                    logger.debug(f"No price data available for {symbol} on Galaswap")
                    return {
                        'symbol': symbol,
                        'bid': 0.0,
                        'ask': 0.0,
                        'last': 0.0,
                        'volume': 0.0,
                        'timestamp': datetime.now()
                    }
                    
            except Exception as api_error:
                # Fallback to order book method if new API fails
                logger.debug(f"New price API failed for {symbol}, trying order book: {api_error}")
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
                        'volume': 0.0,
                    'timestamp': datetime.now()
                }
            else:
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
        """
        Get account balance using Virtual Ledger (primary) or API (fallback)
        
        Virtual Ledger is used to track balances locally, addressing API limitations.
        Balances are updated when trades execute (201 status from bundle API).
        """
        try:
            # PRIMARY: Use Virtual Ledger if initialized and has balances
            if self._ledger_initialized and self.virtual_ledger.balances:
                ledger_balances = self.virtual_ledger.get_balance(asset)
                if ledger_balances:
                    logger.debug(
                        f"Using Virtual Ledger for balances: {len(ledger_balances)} tokens. "
                        f"This avoids API rate limiting issues."
                    )
                    return ledger_balances
                elif asset:
                    # Specific asset requested but not in ledger - return empty
                    logger.debug(f"Asset {asset} not found in Virtual Ledger")
                    return {}
            
            # FALLBACK: Try API if ledger is empty or not initialized
            # Check circuit breaker first
            if not self._check_circuit_breaker():
                # Circuit breaker is open - try ledger, then return empty
                if self._ledger_initialized:
                    return self.virtual_ledger.get_balance(asset)
                logger.debug("Circuit breaker open, returning empty balances")
                return {}
            
            # Use GalaChain address format for API calls
            gala_address_for_api = getattr(self, 'wallet_address_for_api', self.wallet_address)
            # Format Ethereum addresses with eth| prefix for GalaChain API
            if gala_address_for_api.startswith('0x') and '|' not in gala_address_for_api:
                gala_address_for_api = f"eth|{gala_address_for_api[2:]}"
            
            # NEW: Use GalaChain Asset API endpoint for actual on-chain balances
            # POST https://api-galaswap.gala.com/v1/FetchBalances
            # This endpoint provides real balance data, not just positions
            balance_data = None
            
            # If specific asset requested, we need to parse it to tokenClass format
            token_class = None
            if asset:
                # Try to parse asset symbol to tokenClass
                # Asset might be in format like "GALA", "GUSDC", etc.
                # We'll need to construct a tokenClass object
                # For now, query all balances and filter by asset name
                pass  # Will filter after fetching all balances
            
            try:
                # Use Asset API endpoint (separate from DEX API)
                # Request body: {"owner": "eth|address", "tokenClass": {...}} or just {"owner": "eth|address"} for all
                request_body = {"owner": gala_address_for_api}
                if token_class:
                    request_body["tokenClass"] = token_class
                
                # Make request to Asset API (different base URL)
                async with aiohttp.ClientSession() as session:
                    url = f"{self.ASSET_API_BASE_URL}/v1/FetchBalances"
                    async with session.post(
                        url,
                        json=request_body,
                        timeout=ClientTimeout(total=self.REQUEST_TIMEOUT),
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            # Asset API response format may vary - try common fields
                            balance_data = (
                                response_data.get("Data", []) or
                                response_data.get("data", []) or
                                response_data.get("balances", []) or
                                (response_data if isinstance(response_data, list) else [])
                            )
                            logger.debug(f"Successfully fetched {len(balance_data)} token balances from Asset API")
                        else:
                            error_text = await response.text()
                            raise Exception(f"Asset API error {response.status}: {error_text[:200]}")
                            
            except Exception as e:
                error_msg = str(e)
                logger.debug(f"Asset API endpoint failed: {error_msg}. Trying fallback methods...")
                
                # Fallback 1: Try old endpoint (might still work in some cases)
                try:
            response = await self._make_unsigned_request(
                "POST",
                "/galachain/api/asset/token-contract/FetchBalances",
                {"owner": gala_address_for_api}
            )
                    balance_data = response.get("Data", [])
                    logger.debug("Successfully fetched balances from old endpoint")
                except Exception as old_error:
                    error_msg_old = str(old_error)
                    # If it's a 404 or 403, the endpoint is deprecated or forbidden
                    if "404" in error_msg_old or "403" in error_msg_old or "Cannot POST" in error_msg_old or "forbidden" in error_msg_old.lower():
                        logger.debug(
                            f"Old balance endpoint unavailable (404/403). "
                            f"Trying to infer balances from positions as last resort..."
                        )
                        # Fallback 2: Try to get balances from positions (liquidity positions may have token info)
                        # This is a workaround - positions don't show all balances, only liquidity
                        try:
                            positions_response = await self._make_unsigned_request(
                                "GET",
                                f"/v1/trade/positions?user={gala_address_for_api}&limit=10",
                                None
                            )
                            positions_data = positions_response.get("data", {})
                            positions = positions_data.get("Data", {}).get("positions", []) if isinstance(positions_data, dict) else []
                            
                            # Extract token balances from positions (limited - only shows tokens in positions)
                            # This won't show all balances, but it's better than nothing
                            balance_data = []
                            seen_tokens = set()
                            for position in positions:
                                token0 = position.get("token0ClassKey", {})
                                token1 = position.get("token1ClassKey", {})
                                
                                # Add token0 if not seen
                                token0_key = f"{token0.get('collection', '')}${token0.get('category', '')}${token0.get('type', '')}${token0.get('additionalKey', '')}"
                                if token0_key and token0_key not in seen_tokens:
                                    balance_data.append({
                                        "tokenClass": token0,
                                        "quantity": "0",  # Positions don't show available balance
                                        "lockedHolds": []
                                    })
                                    seen_tokens.add(token0_key)
                                
                                # Add token1 if not seen
                                token1_key = f"{token1.get('collection', '')}${token1.get('category', '')}${token1.get('type', '')}${token1.get('additionalKey', '')}"
                                if token1_key and token1_key not in seen_tokens:
                                    balance_data.append({
                                        "tokenClass": token1,
                                        "quantity": "0",  # Positions don't show available balance
                                        "lockedHolds": []
                                    })
                                    seen_tokens.add(token1_key)
                            
                            if balance_data:
                                logger.debug(f"Inferred {len(balance_data)} tokens from positions (balances will be 0)")
                            else:
                                logger.debug("No positions found, cannot infer balances")
                                return {}
                        except Exception as pos_error:
                            logger.debug(f"Could not get balances from positions: {pos_error}")
                            return {}
                    else:
                        # Other errors from old endpoint - re-raise
                        raise
            
            if not balance_data:
                logger.debug("No token data returned from Galaswap balance API")
                return {}
            
            balances = {}
            data = balance_data
            
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
            
            # Sync Virtual Ledger with API balances if we successfully fetched them
            # This keeps the ledger up-to-date when API is available
            if balance_data and self._ledger_initialized:
                try:
                    # Update ledger with fetched balances
                    for symbol, balance_obj in balances.items():
                        if isinstance(balance_obj, Balance):
                            # Update ledger with API balance (this is authoritative when API works)
                            self.virtual_ledger.balances[symbol] = balance_obj.free
                            self.virtual_ledger.locked[symbol] = balance_obj.locked
                    self.virtual_ledger.save_to_file()
                    logger.debug("Synced Virtual Ledger with API balances")
                except Exception as sync_error:
                    logger.debug(f"Error syncing ledger with API balances: {sync_error}")
            
            # Filter by asset if specified
            if asset:
                return {asset: balances.get(asset)} if asset in balances else {}
            
            return balances
        
        except Exception as e:
            error_msg = (
                f"Error fetching Galaswap balance for wallet {self.wallet_address}. "
                f"Error type: {type(e).__name__}, Message: {str(e)}"
            )
            logger.warning(error_msg)
            
            # FALLBACK: Return Virtual Ledger balances if available
            # This ensures the bot can continue operating even when API fails
            if self._ledger_initialized and self.virtual_ledger.balances:
                ledger_balances = self.virtual_ledger.get_balance(asset)
                if ledger_balances:
                    logger.info(
                        f"Using Virtual Ledger balances as fallback (API failed). "
                        f"Returning {len(ledger_balances)} token balances from ledger."
                    )
                    return ledger_balances
            
            # Return empty balances if ledger is also unavailable
            logger.debug("No Virtual Ledger balances available, returning empty balances")
            return {}
    
    async def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Order:
        """
        Place a market order on GalaSwap V3 DEX
        
        NOTE: Old swap-based API endpoints are deprecated (404).
        Trade execution for V3 DEX is not yet implemented.
        We need the new execution endpoints from the API documentation.
        """
        try:
            # Check circuit breaker first
            if not self._check_circuit_breaker():
                raise Exception(
                    "GalaSwap API circuit breaker is OPEN. "
                    "Too many API failures detected. "
                    "Please wait a few minutes before retrying. "
                    "This may be due to rate limiting or API access restrictions."
                )
            
            # Ensure we're connected and have the public key
            if not self.is_connected or not self.public_key:
                await self.connect()
            
            logger.info(f"Placing {side.upper()} market order for {quantity} {symbol} on GalaSwap")
            base_class, quote_class = self._parse_symbol(symbol)
            
            # NEW API: V3 DEX with payload generation API
            # Flow: 1. Get quote 2. Generate payload 3. Sign payload 4. Execute on bundle API
            
            # Step 1: Get quote to determine amounts and fee tier
            base_token_key = token_class_to_composite_key(base_class)
            quote_token_key = token_class_to_composite_key(quote_class)
            
            # IMPORTANT: For quote endpoint, we need to ensure the underlying pool exists
            # The pool requires token0 < token1 lexicographically
            # But quote endpoint uses tokenIn/tokenOut, which can be in any order
            # However, if the pool doesn't exist, the quote will fail
            
            # Determine tokenIn and tokenOut based on side
            # Track which amount was originally specified (for API: exactly one must be provided)
            use_amount_in = None  # Will be set based on side
            if side.lower() == 'buy':
                # Buying base with quote: tokenIn = quote, tokenOut = base
                token_in = quote_class
                token_out = base_class
                token_in_key = quote_token_key
                token_out_key = base_token_key
                # We want to receive 'quantity' of base
                amount_out = format_quantity(quantity, decimals=8)
                amount_in = None  # Will get from quote
                use_amount_in = False  # Use amountOut for buy orders
            else:  # sell
                # Selling base for quote: tokenIn = base, tokenOut = quote
                token_in = base_class
                token_out = quote_class
                token_in_key = base_token_key
                token_out_key = quote_token_key
                # We want to spend 'quantity' of base
                amount_in = format_quantity(quantity, decimals=8)
                amount_out = None  # Will get from quote
                use_amount_in = True  # Use amountIn for sell orders
            
            # Log the quote request for debugging
            logger.debug(
                f"Getting quote for {symbol} ({side}): "
                f"tokenIn={token_in_key}, tokenOut={token_out_key}, "
                f"amountIn={amount_in}, amountOut={amount_out}"
            )
            
            # Get quote to determine amounts and find available pool
            # Note: Quote endpoint doesn't require token ordering (token0/token1), it uses tokenIn/tokenOut
            # But the underlying pool must exist, and pools require token0 < token1
            # Try without fee first (API will use default), then with specific fee tiers
            fee_options = [None, 3000, 500, 10000]  # Try without fee first, then specific tiers
            quote_data = None
            selected_fee = None
            last_error = None
            retry_count = 0
            max_retries = 3  # Max retries for 403 errors
            all_403_errors = True  # Track if all attempts result in 403
            
            for fee in fee_options:
                try:
                    # Build quote URL
                    if amount_in:
                        if fee is not None:
                            quote_url = f"/v1/trade/quote?tokenIn={token_in_key}&tokenOut={token_out_key}&amountIn={amount_in}&fee={fee}"
                        else:
                            quote_url = f"/v1/trade/quote?tokenIn={token_in_key}&tokenOut={token_out_key}&amountIn={amount_in}"
                    else:
                        if fee is not None:
                            quote_url = f"/v1/trade/quote?tokenIn={token_in_key}&tokenOut={token_out_key}&amountOut={amount_out}&fee={fee}"
                        else:
                            quote_url = f"/v1/trade/quote?tokenIn={token_in_key}&tokenOut={token_out_key}&amountOut={amount_out}"
                    
                    logger.debug(f"Getting quote for {symbol}: {quote_url}")
                    
                    # Retry logic for 403 errors with exponential backoff
                    quote_response = None
                    for attempt in range(max_retries):
                        try:
                            quote_response = await self._make_unsigned_request("GET", quote_url, None)
                            break  # Success, exit retry loop
                        except Exception as retry_error:
                            error_msg_retry = str(retry_error)
                            if "403" in error_msg_retry or "forbidden" in error_msg_retry.lower():
                                if attempt < max_retries - 1:
                                    # Exponential backoff: 2s, 4s, 8s (longer delays for rate limiting)
                                    wait_time = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                                    logger.debug(
                                        f"403 error on quote attempt {attempt + 1}/{max_retries} for {symbol}. "
                                        f"Waiting {wait_time}s before retry (rate limiting)..."
                                    )
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    # Last attempt failed, raise the error
                                    raise
                            else:
                                # Not a 403 error, raise immediately
                                raise
                    
                    if quote_response is None:
                        raise Exception("Failed to get quote after retries")
                    
                    # Check response structure
                    if isinstance(quote_response, dict):
                        quote_data = quote_response.get("data", {})
                        # If no "data" key, check if response itself is the data
                        if not quote_data and ("amountIn" in quote_response or "amountOut" in quote_response):
                            quote_data = quote_response
                    
                    if quote_data and quote_data.get("amountIn") and quote_data.get("amountOut"):
                        selected_fee = fee if fee is not None else 3000  # Default to 3000 if no fee specified
                        all_403_errors = False  # Reset - we got a successful response
                        logger.info(
                            f"Got quote for {symbol} with fee tier {selected_fee}: "
                            f"{quote_data.get('amountIn')} -> {quote_data.get('amountOut')}"
                        )
                        break
                    else:
                        logger.debug(f"Quote response for fee {fee} missing data: {quote_response}")
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    # Log more details about the error
                    if "Pool not found" in error_msg or "Pool data not found" in error_msg:
                        logger.debug(f"Pool not found for {symbol} with fee tier {fee}")
                    elif "Token0 must be smaller" in error_msg:
                        # Quote endpoint shouldn't have this issue, but log it
                        logger.debug(f"Token ordering issue for quote {symbol} with fee tier {fee}: {e}")
                    elif "403" in error_msg or "forbidden" in error_msg.lower():
                        # 403 error - rate limiting, add delay before trying next fee tier
                        all_403_errors = True  # Track that we're getting 403 errors
                        logger.warning(
                            f"Quote failed for {symbol} with fee tier {fee} due to 403 (rate limiting). "
                            f"Will retry with next fee tier after delay..."
                        )
                        # Add longer delay before trying next fee tier to avoid rate limits
                        await asyncio.sleep(2.0)  # 2 second delay to help with rate limiting
                    elif "400" in error_msg or "404" in error_msg:
                        logger.debug(f"Quote endpoint error for {symbol} with fee {fee}: {error_msg[:200]}")
                    else:
                        logger.warning(f"Quote failed for {symbol} with fee tier {fee}: {e}")
                    continue
            
            if not quote_data:
                error_details = f"Last error: {last_error}" if last_error else "No errors logged"
                
                # Check if all errors were 403 (rate limiting)
                if last_error and ("403" in str(last_error) or "forbidden" in str(last_error).lower()):
                    raise ValueError(
                        f"❌ RATE LIMITING: Could not get quote for {symbol} due to API rate limiting (403 Forbidden). "
                        f"All fee tiers returned 403 errors. "
                        f"This indicates the API is blocking requests due to rate limits. "
                        f"Please wait 5-10 minutes before retrying. "
                        f"Tried fee tiers: {fee_options}. "
                        f"Last error: {error_details}"
                    )
                else:
                    raise ValueError(
                        f"Could not get quote for {symbol}. "
                        f"No pool found or insufficient liquidity. "
                        f"Tried fee tiers: {fee_options}. "
                        f"{error_details}"
                    )
            
            # Extract amounts from quote
            if amount_in:
                # We have amountIn, quote gives us amountOut
                quote_amount_in = float(quote_data.get("amountIn", amount_in))
                quote_amount_out = float(quote_data.get("amountOut", 0))
                if quote_amount_out == 0:
                    raise ValueError(f"Quote returned zero output for {symbol}")
                amount_out = format_quantity(quote_amount_out, decimals=8)
            else:
                # We have amountOut, quote gives us amountIn
                quote_amount_out = float(quote_data.get("amountOut", amount_out))
                quote_amount_in = float(quote_data.get("amountIn", 0))
                if quote_amount_in == 0:
                    raise ValueError(f"Quote returned zero input for {symbol}")
                amount_in = format_quantity(quote_amount_in, decimals=8)
            
            # Calculate price
            price = float(amount_in) / float(amount_out) if float(amount_out) > 0 else 0
            
            # Step 2: Generate swap payload
            # Get sqrtPriceLimit from pool data
            # sqrtPriceLimit must be a valid numeric string in decimal format
            # For market orders (no price limit), we use the current sqrtPrice from the pool
            # or a very large/small number depending on direction
            sqrt_price_limit = None
            
            # Try to get current sqrtPrice from pool
            # Determine token0/token1 order for pool lookup
            if base_token_key > quote_token_key:
                pool_token0 = quote_token_key
                pool_token1 = base_token_key
            else:
                pool_token0 = base_token_key
                pool_token1 = quote_token_key
            
            # Try to get pool data to extract sqrtPrice
            try:
                pool_response = await self._make_unsigned_request(
                    "GET",
                    f"/v1/trade/pool?token0={pool_token0}&token1={pool_token1}&fee={selected_fee}",
                    None
                )
                pool_data = pool_response.get("data", {}).get("Data", {})
                if pool_data and pool_data.get("sqrtPrice"):
                    current_sqrt_price = pool_data.get("sqrtPrice")
                    # Convert to string, ensuring it's a valid numeric format
                    if isinstance(current_sqrt_price, (int, float)):
                        current_sqrt_price_str = f"{current_sqrt_price:.18f}"  # Use high precision
                    else:
                        current_sqrt_price_str = str(current_sqrt_price)
                    
                    # For market orders, set sqrtPriceLimit based on direction:
                    # - Buy (tokenIn=quote, tokenOut=base): use very large (no upper limit)
                    # - Sell (tokenIn=base, tokenOut=quote): use very small but not zero (no lower limit)
                    # NOTE: Must be within safe numeric range [-9007199254740991, 9007199254740991]
                    if side.lower() == 'buy':
                        # Buying: allow execution at any price (no upper limit)
                        # Use maximum safe integer (JavaScript Number.MAX_SAFE_INTEGER)
                        sqrt_price_limit = "9007199254740991"
                    else:
                        # Selling: allow execution at any price (no lower limit)
                        # Use a very small positive number (not zero)
                        sqrt_price_limit = "0.000000000000000001"  # Very small but not zero
                    
                    logger.debug(f"Using sqrtPriceLimit for {side} order: {sqrt_price_limit} (current pool sqrtPrice: {current_sqrt_price_str})")
                else:
                    # Fallback: use direction-based defaults
                    if side.lower() == 'buy':
                        sqrt_price_limit = "9007199254740991"  # Max safe integer
                    else:
                        sqrt_price_limit = "0.000000000000000001"
            except Exception as e:
                logger.debug(f"Could not get pool sqrtPrice, using default: {e}")
                # Fallback: use direction-based defaults
                if side.lower() == 'buy':
                    sqrt_price_limit = "9007199254740991"  # Max safe integer
                else:
                    sqrt_price_limit = "0.000000000000000001"
            
            # Ensure sqrtPriceLimit is a valid numeric string (not "0" or empty)
            if not sqrt_price_limit or sqrt_price_limit == "0" or sqrt_price_limit == "0.0":
                if side.lower() == 'buy':
                    sqrt_price_limit = "9007199254740991"  # Max safe integer
                else:
                    sqrt_price_limit = "0.000000000000000001"
            
            # Calculate slippage protection (1% slippage tolerance)
            # amountOutMinimum must be negative (API requirement)
            # It represents the minimum amount of output tokens we want to receive
            
            # Build swap payload request - API requires exactly one of amountIn or amountOut
            swap_payload_request = {
                "tokenIn": token_in,
                "tokenOut": token_out,
                "fee": selected_fee,
                "sqrtPriceLimit": sqrt_price_limit,
            }
            
            # Include exactly one of amountIn or amountOut based on original specification
            if use_amount_in:
                # Sell order: we specified amountIn (spending base), so send only amountIn
                swap_payload_request["amountIn"] = amount_in
                # Calculate slippage protection for sell orders
                amount_in_max = format_quantity(float(amount_in) * 1.01, decimals=8)  # 1% more
                swap_payload_request["amountInMaximum"] = amount_in_max
                # amountOutMinimum must be negative
                amount_out_min = format_quantity(-abs(float(amount_out) * 0.99), decimals=8)  # 1% less, negative
                swap_payload_request["amountOutMinimum"] = amount_out_min
            else:
                # Buy order: we specified amountOut (receiving base), so send only amountOut
                swap_payload_request["amountOut"] = amount_out
                # Calculate slippage protection for buy orders
                amount_in_max = format_quantity(float(amount_in) * 1.01, decimals=8)  # 1% more
                swap_payload_request["amountInMaximum"] = amount_in_max
                # amountOutMinimum must be negative
                amount_out_min = format_quantity(-abs(float(amount_out) * 0.99), decimals=8)  # 1% less, negative
                swap_payload_request["amountOutMinimum"] = amount_out_min
            
            logger.info(f"Generating swap payload: {amount_in} {token_in['collection']} -> {amount_out} {token_out['collection']} (fee: {selected_fee})")
            
            # Generate payload (unsigned request)
            payload_response = await self._make_unsigned_request(
                "POST",
                "/v1/trade/swap",
                swap_payload_request
            )
            
            payload_data = payload_response.get("data", {})
            if not payload_data:
                raise ValueError(f"Failed to generate swap payload: {payload_response}")
            
            unique_key = payload_data.get("uniqueKey")
            if not unique_key:
                raise ValueError("Payload generation did not return uniqueKey")
            
            logger.info(f"Swap payload generated with uniqueKey: {unique_key[:30]}...")
            
            # Step 3: Sign and execute payload on bundle API
            # Bundle API requires: payload, type, signature, user
            # The payload_data from step 2 already contains all swap parameters including uniqueKey
            
            # Sign the payload (sign the payload_data object)
            # Bundle API expects hex signature (r + s concatenated), not base64 DER
            logger.debug("Signing swap payload for bundle execution...")
            
            # Log payload being signed for debugging
            logger.debug(f"Payload to sign: {json.dumps(payload_data, default=str, indent=2)}")
            
            signature = sign_payload_for_bundle(payload_data, self.private_key)
            
            # Verify signature format (should be 128 hex characters)
            if len(signature) != 128:
                raise ValueError(f"Invalid signature length: {len(signature)} (expected 128 hex characters)")
            
            logger.debug(f"Generated signature (first 20 chars): {signature[:20]}... (length: {len(signature)})")
            
            # Get user address in GalaChain format
            user_address = getattr(self, 'wallet_address_for_api', self.wallet_address)
            if user_address.startswith('0x') and '|' not in user_address:
                user_address = f"eth|{user_address[2:]}"
            
            # Verify user address matches the private key's derived address
            derived_address = getattr(self, 'derived_ethereum_address', None)
            if derived_address:
                expected_address = f"eth|{derived_address[2:]}" if derived_address.startswith('0x') else derived_address
                if user_address.lower() != expected_address.lower():
                    logger.warning(
                        f"⚠️ WARNING: User address '{user_address}' does not match derived address '{expected_address}'. "
                        f"This may cause signature verification to fail!"
                    )
            
            # Prepare bundle request
            bundle_request = {
                "payload": payload_data,  # The payload from /v1/trade/swap
                "type": "swap",  # Operation type
                "signature": signature,  # Signature of the payload
                "user": user_address  # User address in eth| format
            }
            
            logger.info(
                f"Executing swap bundle: type=swap, user={user_address}, "
                f"uniqueKey={unique_key[:30]}..., signature_length={len(signature)}"
            )
            
            # Log bundle request (without full signature for security)
            logger.debug(f"Bundle request (signature truncated): {json.dumps({**bundle_request, 'signature': signature[:20] + '...'}, default=str)}")
            
            # Execute on bundle API (unsigned request - signature is in the body)
            execution_result = await self._make_unsigned_request(
                    "POST",
                "/v1/trade/bundle",
                bundle_request
            )
            
            # Log full response for debugging
            logger.debug(f"Bundle API response: {json.dumps(execution_result, default=str)}")
            
            # Check response status - bundle API returns 201 for success
            response_status = execution_result.get("status")
            response_message = execution_result.get("message", "")
            response_error = execution_result.get("error", False)
            
            # CRITICAL: Update Virtual Ledger when bundle API returns 201 (transaction submitted)
            # This ensures balances are tracked locally even if API balance endpoints fail
            if response_status in [200, 201] and not response_error:
                if self._ledger_initialized:
                    try:
                        # Extract token symbols from token_in and token_out
                        token_in_symbol = token_in.get("collection", "").upper()
                        token_out_symbol = token_out.get("collection", "").upper()
                        
                        # Record swap in virtual ledger
                        # When 201 is returned, the transaction is submitted and will execute
                        self.virtual_ledger.record_swap(
                            token_in=token_in_symbol,
                            amount_in=float(amount_in),
                            token_out=token_out_symbol,
                            amount_out=float(amount_out)
                        )
                        logger.info(
                            f"✓ Virtual Ledger updated: Spent {amount_in} {token_in_symbol}, "
                            f"Received {amount_out} {token_out_symbol}"
                        )
                    except Exception as ledger_error:
                        logger.warning(f"Error updating Virtual Ledger: {ledger_error}")
            
            if response_error or (response_status and response_status not in [200, 201]):
                error_details = execution_result.get("data", {})
                error_text = str(error_details) if error_details else response_message
                
                # Check for signature validation errors
                if "signature" in error_text.lower() and "invalid" in error_text.lower():
                    raise ValueError(
                        f"❌ SIGNATURE VALIDATION FAILED: Bundle API rejected transaction due to invalid signature. "
                        f"This means the transaction will NOT execute. "
                        f"Status: {response_status}, Message: {response_message}, "
                        f"Details: {error_text}. "
                        f"Please check: 1) Private key matches wallet address, 2) Signature format is correct, "
                        f"3) Payload is signed correctly."
                    )
                
                # Check for other validation errors
                if "validation" in error_text.lower() or "invalid" in error_text.lower():
                    raise ValueError(
                        f"❌ TRANSACTION VALIDATION FAILED: Bundle API rejected transaction. "
                        f"This means the transaction will NOT execute. "
                        f"Status: {response_status}, Message: {response_message}, "
                        f"Details: {error_text}"
                    )
                
                raise ValueError(
                    f"Bundle API returned error: status={response_status}, "
                    f"message={response_message}, error={response_error}, "
                    f"details={error_details}"
                )
            
            # Extract transaction/order ID from result
            # Bundle API response format: {"status": 201, "data": {"data": "transaction-id", "message": "...", ...}}
            bundle_data = execution_result.get("data", {})
            
            # Check if transaction was actually submitted
            transaction_status = 'pending'  # Default to pending until confirmed
            if isinstance(bundle_data, dict):
                transaction_message = bundle_data.get("message", "")
                transaction_id = (
                    bundle_data.get("data") or  # Transaction ID from bundle
                    bundle_data.get("transactionId") or
                    bundle_data.get("txid") or
                    unique_key  # Fallback to uniqueKey
                )
                
                # Log transaction details
                logger.info(
                    f"Bundle API response - Status: {response_status}, "
                    f"Message: {transaction_message}, "
                    f"Transaction ID: {transaction_id}"
                )
                
                # Check if message indicates actual execution vs just received
                if transaction_message and "received" in transaction_message.lower():
                    logger.warning(
                        f"⚠️ Bundle API returned 'received' status - transaction submitted but NOT confirmed executed. "
                        f"Transaction ID: {transaction_id}. "
                        f"This may indicate the transaction was queued but not yet executed on-chain. "
                        f"Please verify transaction status on-chain or check for errors."
                    )
                    transaction_status = 'pending'  # Not confirmed executed
                elif transaction_message and ("success" in transaction_message.lower() or "executed" in transaction_message.lower()):
                    logger.info(f"✓ Bundle API confirmed transaction execution: {transaction_id}")
                    transaction_status = 'filled'  # Confirmed executed
                else:
                    # Unknown status - default to pending
                    logger.warning(
                        f"⚠️ Bundle API returned unknown status message: '{transaction_message}'. "
                        f"Transaction ID: {transaction_id}. "
                        f"Assuming pending until confirmed."
                    )
                    transaction_status = 'pending'
                
                order_id = transaction_id
            else:
                order_id = unique_key  # Fallback
                logger.warning(f"Bundle API response format unexpected, using uniqueKey: {execution_result}")
                transaction_status = 'pending'
            
            if not order_id:
                order_id = unique_key
            
            # Verify transaction execution by checking balances
            # This helps confirm if the transaction actually executed on-chain
            logger.info(f"Verifying transaction execution for {order_id}...")
            verified_execution = False
            
            try:
                # Get token symbols for balance checking
                token_in_symbol = token_in.get("collection", "").upper()
                token_out_symbol = token_out.get("collection", "").upper()
                
                # Get initial balances
                initial_balances = await self.get_balance()
                initial_token_in = initial_balances.get(token_in_symbol, Balance(asset=token_in_symbol, free=0.0, locked=0.0)).free
                initial_token_out = initial_balances.get(token_out_symbol, Balance(asset=token_out_symbol, free=0.0, locked=0.0)).free
                
                logger.debug(
                    f"Initial balances - {token_in_symbol}: {initial_token_in}, "
                    f"{token_out_symbol}: {initial_token_out}"
                )
                
                # Wait a bit for transaction to process (bundle transactions may take a few seconds)
                await asyncio.sleep(3)
                
                # Poll for balance changes (up to 30 seconds)
                max_poll_attempts = 10
                poll_interval = 3  # seconds
                
                for attempt in range(max_poll_attempts):
                    await asyncio.sleep(poll_interval)
                    
                    # Get current balances
                    current_balances = await self.get_balance()
                    current_token_in = current_balances.get(token_in_symbol, Balance(asset=token_in_symbol, free=0.0, locked=0.0)).free
                    current_token_out = current_balances.get(token_out_symbol, Balance(asset=token_out_symbol, free=0.0, locked=0.0)).free
                    
                    logger.debug(
                        f"Poll attempt {attempt + 1}/{max_poll_attempts} - "
                        f"{token_in_symbol}: {current_token_in}, "
                        f"{token_out_symbol}: {current_token_out}"
                    )
                    
                    # Check if balances changed as expected
                    if side.lower() == 'buy':
                        # Buying: should receive token_out (base), spend token_in (quote)
                        expected_token_out_change = float(amount_out)
                        token_out_change = current_token_out - initial_token_out
                        if token_out_change >= expected_token_out_change * 0.95:  # 95% tolerance for rounding
                            verified_execution = True
                            logger.info(
                                f"✓ Transaction verified! Balance change detected: "
                                f"{token_out_symbol} increased by {token_out_change} "
                                f"(expected ~{expected_token_out_change})"
                            )
                            break
            else:  # sell
                        # Selling: should receive token_out (quote), spend token_in (base)
                        expected_token_in_decrease = float(amount_in)
                        token_in_decrease = initial_token_in - current_token_in
                        if token_in_decrease >= expected_token_in_decrease * 0.95:  # 95% tolerance
                            verified_execution = True
                            logger.info(
                                f"✓ Transaction verified! Balance change detected: "
                                f"{token_in_symbol} decreased by {token_in_decrease} "
                                f"(expected ~{expected_token_in_decrease})"
                            )
                            break
                
                if not verified_execution:
                    logger.warning(
                        f"⚠️ Could not verify transaction execution after {max_poll_attempts * poll_interval} seconds. "
                        f"Transaction ID: {order_id}. "
                        f"Balance changes not detected. Transaction may not have executed."
                    )
            except Exception as verify_error:
                logger.warning(
                    f"Error during transaction verification: {verify_error}. "
                    f"Transaction ID: {order_id}. "
                    f"Cannot confirm execution status."
                )
            
            # Update transaction status based on verification
            if verified_execution:
                transaction_status = 'filled'
                logger.info(f"✓✓ Transaction CONFIRMED executed on-chain. Transaction ID: {order_id}")
            elif transaction_status == 'pending':
                logger.warning(
                    f"⚠️ Swap submitted to bundle API but execution NOT verified. "
                    f"Transaction ID: {order_id}. "
                    f"Status: {response_status}, Message: {response_message}. "
                    f"⚠️ IMPORTANT: Transaction may not have executed. Please verify on-chain!"
                )
            else:
                logger.info(
                    f"✓ Swap executed successfully. Transaction ID: {order_id}. "
                    f"Status: {response_status}, Message: {response_message}."
                )
            
            # Return order with appropriate status
            # Only mark as filled if verified or API confirmed execution
            final_status = 'filled' if (verified_execution or transaction_status == 'filled') else 'pending'
            filled_qty = float(amount_out) if side.lower() == 'buy' else float(amount_in) if final_status == 'filled' else 0.0
                
                return Order(
                    exchange=self.exchange_name,
                order_id=order_id,
                    symbol=symbol,
                    side=side,
                type='market',
                    price=price,
                quantity=float(amount_out) if side.lower() == 'buy' else float(amount_in),
                filled_quantity=filled_qty,
                status=final_status,  # 'pending' or 'filled' based on verification
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
        Place a limit order - OLD API deprecated
        
        NOTE: Old swap-based endpoints return 404.
        Trade execution for V3 DEX is not yet implemented.
        """
        # OLD API (deprecated): Swap-based endpoints return 404
        # V3 DEX limit orders would need to be implemented using the swap payload API
        # with price limits (sqrtPriceLimit parameter)
        raise NotImplementedError(
            f"GalaSwap limit orders not yet implemented for V3 DEX API. "
            f"Old swap-based endpoints are deprecated (404). "
            f"New V3 DEX execution endpoints need to be implemented."
        )
    
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
        """
        Get order status for GalaSwap V3 DEX
        
        For swap transactions executed via bundle API:
        - Bundle API returns transaction IDs (UUID format)
        - Swaps execute immediately, so we return 'filled' status
        
        For liquidity positions:
        - Uses /v1/trade/positions endpoint to check position status
        """
        try:
            # Normalize order_id for comparison
            order_id_normalized = order_id.replace('\x00', '').strip() if isinstance(order_id, str) else str(order_id).replace('\x00', '').strip()
            
            # Check if this is a bundle transaction ID (UUID format)
            # Bundle transaction IDs are UUIDs like: "b960c27e-d3c1-40b2-acf5-45ffa3f7d5e0"
            # or uniqueKeys like: "galaswap-operation-44d5d50a-d2..."
            import re
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            bundle_key_pattern = r'^galaswap-operation-[0-9a-f-]+$'
            
            is_bundle_tx = (
                re.match(uuid_pattern, order_id_normalized, re.IGNORECASE) is not None or
                re.match(bundle_key_pattern, order_id_normalized, re.IGNORECASE) is not None
            )
            
            if is_bundle_tx:
                # This is a bundle transaction ID
                # NOTE: Bundle API returns "Transaction Received" which doesn't guarantee execution
                # We need to verify the transaction actually executed on-chain
                # For now, we can't verify without a transaction status endpoint, so return 'pending'
                # The trade executor should handle this by checking balances or waiting for confirmation
                logger.debug(
                    f"Order {order_id} is a bundle transaction ID. "
                    f"⚠️ Cannot verify execution status without transaction status endpoint. "
                    f"Returning 'pending' status - transaction may or may not have executed."
                )
                return Order(
                    exchange=self.exchange_name,
                    order_id=order_id,
                    symbol=symbol,
                    side='unknown',  # Can't determine from transaction ID alone
                    type='market',  # Bundle swaps are market orders
                    price=0.0,  # Would need to query transaction details
                    quantity=0.0,  # Would need to query transaction details
                    filled_quantity=0.0,  # Cannot confirm without verification
                    status='pending',  # ⚠️ Cannot verify execution - may not have executed
                    timestamp=datetime.now(),
                    commission=None,
                    commission_asset=None
                )
            
            # For non-bundle IDs, check positions (liquidity positions)
            # Use GalaChain address format for API calls
            gala_address_for_api = getattr(self, 'wallet_address_for_api', self.wallet_address)
            # Format Ethereum addresses with eth| prefix for GalaChain API
            if gala_address_for_api.startswith('0x') and '|' not in gala_address_for_api:
                gala_address_for_api = f"eth|{gala_address_for_api[2:]}"
            
            # Use new V3 DEX endpoint: GET /v1/trade/positions
            try:
            response = await self._make_unsigned_request(
                    "GET",
                    f"/v1/trade/positions?user={gala_address_for_api}&limit=10",
                    None  # GET request, no body
                )
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg or "Cannot" in error_msg:
                    logger.debug(f"GalaSwap positions endpoint not available: {e}")
                    # Return unknown status if endpoint unavailable
                    return Order(
                        exchange=self.exchange_name,
                        order_id=order_id,
                        symbol=symbol,
                        side='unknown',
                        type='unknown',
                        price=0.0,
                        quantity=0.0,
                        filled_quantity=0.0,
                        status='unknown',
                        timestamp=datetime.now(),
                        commission=None,
                        commission_asset=None
                    )
                raise
            
            # Parse response: {"status": 200, "data": {"Data": {"positions": [...]}}}
            data = response.get("data", {})
            positions_data = data.get("Data", {}) if isinstance(data, dict) else {}
            positions = positions_data.get("positions", [])
            
            # Search for matching position by positionId
            for position in positions:
                position_id = position.get("positionId", "")
                position_id_normalized = position_id.replace('\x00', '').strip() if isinstance(position_id, str) else str(position_id).replace('\x00', '').strip()
                
                if position_id_normalized == order_id_normalized or position_id == order_id:
                    # Found matching position
                    liquidity = float(position.get("liquidity", 0))
                    
                    # In V3 DEX, positions represent liquidity, not orders
                    # A position with liquidity > 0 is "active", otherwise it's closed
                    if liquidity > 0:
                        status = 'open'  # Position is active
                    else:
                        status = 'closed'  # Position has no liquidity
                    
                    # Extract token info
                    token0_class = position.get("token0ClassKey", {})
                    token1_class = position.get("token1ClassKey", {})
                    
                    # Try to match symbol
                    token0_symbol = token0_class.get("collection", "")
                    token1_symbol = token1_class.get("collection", "")
                    
                    # Get price from position (would need pool data for accurate price)
                    # For now, use liquidity as quantity indicator
                    quantity = liquidity
                    
                    return Order(
                        exchange=self.exchange_name,
                        order_id=position_id,
                        symbol=symbol,
                        side='unknown',  # V3 positions don't have buy/sell side
                        type='position',
                        price=0.0,  # Would need pool data to calculate
                        quantity=quantity,
                        filled_quantity=quantity if status == 'open' else 0.0,
                        status=status,
                        timestamp=datetime.now(),
                        commission=None,
                        commission_asset=None
                    )
            
            # Order not found in positions
            logger.debug(f"Order {order_id} not found in user positions")
            return Order(
                exchange=self.exchange_name,
                order_id=order_id,
                symbol=symbol,
                side='unknown',
                type='unknown',
                price=0.0,
                quantity=0.0,
                filled_quantity=0.0,
                status='not_found',
                timestamp=datetime.now(),
                commission=None,
                commission_asset=None
            )
        
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
