"""
API Keys Manager
Securely stores and retrieves API keys from database
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from ..utils.logger import get_logger

logger = get_logger()


def _load_or_create_encryption_key() -> str:
    """
    Load encryption key from ENV or file, or create a new one once.

    Priority:
    1. ENCRYPTION_KEY environment variable
    2. data/.encryption_key file (created if missing)
    """
    # 1) Environment variable (takes precedence)
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        return env_key.strip()

    # 2) Local file in data/.encryption_key
    key_file = Path("data") / ".encryption_key"
    try:
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()

        # Generate once and persist
        key = Fernet.generate_key().decode()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key, encoding="utf-8")
        logger.warning(
            "Generated new encryption key file at data/.encryption_key. "
            "Back this up if you want to keep API keys across machines."
        )
        return key
    except Exception as e:
        # Fallback: generate in-memory key (keys won't be decryptable after restart)
        logger.error(f"Error loading/saving encryption key file: {e}")
        return Fernet.generate_key().decode()


class APIKeysManager:
    """Manages encrypted API keys in database"""
    
    def __init__(self, db_manager, encryption_key: Optional[str] = None):
        """
        Initialize API keys manager
        
        Args:
            db_manager: PostgresManager instance
            encryption_key: Encryption key (generated if not provided)
        """
        self.db = db_manager

        # Initialize encryption with stable key
        if encryption_key:
            key_str = encryption_key
        else:
            key_str = _load_or_create_encryption_key()

        self.encryption_key = key_str
        self.cipher = Fernet(key_str.encode())
        
        self._initialize_table()
    
    def _initialize_table(self):
        """Create API keys table if not exists and add missing columns"""
        try:
            with self.db.get_cursor() as cursor:
                # Create table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id SERIAL PRIMARY KEY,
                        exchange_name VARCHAR(50) UNIQUE NOT NULL,
                        exchange_type VARCHAR(10) NOT NULL,
                        api_key TEXT,
                        api_secret TEXT,
                        passphrase TEXT,
                        private_key TEXT,
                        testnet BOOLEAN DEFAULT false,
                        enabled BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Add new columns if they don't exist (for existing databases)
                new_columns = [
                    ('wallet_address', 'TEXT'),
                    ('rpc_url', 'TEXT'),
                    ('router_address', 'TEXT'),
                    ('factory_address', 'TEXT'),
                    ('chain', 'VARCHAR(50)'),
                ]
                
                for column_name, column_type in new_columns:
                    try:
                        cursor.execute(f"""
                            ALTER TABLE api_keys 
                            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                        """)
                    except Exception as e:
                        # Some PostgreSQL versions don't support IF NOT EXISTS in ALTER TABLE
                        # Check if column exists first
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name='api_keys' AND column_name=%s
                        """, (column_name,))
                        if not cursor.fetchone():
                            cursor.execute(f"""
                                ALTER TABLE api_keys 
                                ADD COLUMN {column_name} {column_type}
                            """)
                
                logger.info("API keys table initialized and migrated")
        except Exception as e:
            logger.error(f"Error initializing API keys table: {e}")
    
    def save_exchange_keys(
        self,
        exchange_name: str,
        exchange_type: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False,
        enabled: bool = True
    ) -> bool:
        """
        Save CEX API keys
        
        Args:
            exchange_name: Exchange name (binance, okx, bybit)
            exchange_type: 'cex' or 'dex'
            api_key: API key
            api_secret: API secret
            passphrase: Passphrase (for OKX)
            testnet: Use testnet
            enabled: Enable this exchange
        
        Returns:
            True if saved successfully
        """
        try:
            # Encrypt sensitive data
            encrypted_key = self._encrypt(api_key) if api_key else None
            encrypted_secret = self._encrypt(api_secret) if api_secret else None
            encrypted_passphrase = self._encrypt(passphrase) if passphrase else None
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_keys (
                        exchange_name, exchange_type, api_key, api_secret, 
                        passphrase, testnet, enabled, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (exchange_name) 
                    DO UPDATE SET
                        api_key = EXCLUDED.api_key,
                        api_secret = EXCLUDED.api_secret,
                        passphrase = EXCLUDED.passphrase,
                        testnet = EXCLUDED.testnet,
                        enabled = EXCLUDED.enabled,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    exchange_name, exchange_type, encrypted_key, 
                    encrypted_secret, encrypted_passphrase, testnet, enabled
                ))
            
            logger.info(f"Saved API keys for {exchange_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving API keys for {exchange_name}: {e}")
            return False
    
    def save_dex_keys(
        self,
        exchange_name: str,
        private_key: str,
        wallet_address: Optional[str] = None,
        rpc_url: Optional[str] = None,
        router_address: Optional[str] = None,
        factory_address: Optional[str] = None,
        chain: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """
        Save DEX configuration (private key, RPC URL, addresses, etc.)
        
        Args:
            exchange_name: DEX name (e.g., 'pancakeswap', 'galaswap')
            private_key: Wallet private key (encrypted)
            wallet_address: Wallet address (for Galaswap)
            rpc_url: Blockchain RPC URL
            router_address: DEX router contract address
            factory_address: DEX factory contract address
            chain: Blockchain chain name (e.g., 'bsc', 'ethereum', 'polygon', 'gala')
            enabled: Enable this DEX
        
        Returns:
            True if saved successfully
        """
        try:
            encrypted_key = self._encrypt(private_key) if private_key else None
            encrypted_wallet = self._encrypt(wallet_address) if wallet_address else None
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_keys (
                        exchange_name, exchange_type, private_key, wallet_address,
                        rpc_url, router_address, factory_address, chain,
                        enabled, updated_at
                    ) VALUES (
                        %s, 'dex', %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (exchange_name) 
                    DO UPDATE SET
                        private_key = COALESCE(EXCLUDED.private_key, api_keys.private_key),
                        wallet_address = COALESCE(EXCLUDED.wallet_address, api_keys.wallet_address),
                        rpc_url = COALESCE(EXCLUDED.rpc_url, api_keys.rpc_url),
                        router_address = COALESCE(EXCLUDED.router_address, api_keys.router_address),
                        factory_address = COALESCE(EXCLUDED.factory_address, api_keys.factory_address),
                        chain = COALESCE(EXCLUDED.chain, api_keys.chain),
                        enabled = EXCLUDED.enabled,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    exchange_name, encrypted_key, encrypted_wallet,
                    rpc_url, router_address, factory_address, chain, enabled
                ))
            
            logger.info(f"Saved DEX configuration for {exchange_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving DEX configuration for {exchange_name}: {e}")
            return False
    
    def get_exchange_keys(self, exchange_name: str) -> Optional[Dict]:
        """
        Get API keys for an exchange
        
        Args:
            exchange_name: Exchange name
        
        Returns:
            Dictionary with decrypted keys or None
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT exchange_type, api_key, api_secret, passphrase, 
                           private_key, wallet_address, rpc_url, router_address,
                           factory_address, chain, testnet, enabled
                    FROM api_keys
                    WHERE exchange_name = %s
                """, (exchange_name,))
                
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                result = {
                    'exchange_name': exchange_name,
                    'exchange_type': row['exchange_type'],
                    'testnet': row.get('testnet', False),
                    'enabled': row['enabled']
                }

                # Decrypt keys – keep InvalidToken inside the cursor context
                try:
                    if row['exchange_type'] == 'cex':
                        result['api_key'] = self._decrypt(row['api_key']) if row['api_key'] else None
                        result['api_secret'] = self._decrypt(row['api_secret']) if row['api_secret'] else None
                        result['passphrase'] = self._decrypt(row['passphrase']) if row['passphrase'] else None
                    else:  # dex
                        result['private_key'] = self._decrypt(row['private_key']) if row['private_key'] else None
                        result['wallet_address'] = self._decrypt(row['wallet_address']) if row.get('wallet_address') else None
                        result['rpc_url'] = row.get('rpc_url')
                        result['router_address'] = row.get('router_address')
                        result['factory_address'] = row.get('factory_address')
                        result['chain'] = row.get('chain')
                except InvalidToken:
                    # Happens if encryption key changed since keys were saved
                    logger.error(
                        "Encryption key mismatch when reading keys for %s. "
                        "You may need to reset stored API keys (truncate api_keys table).",
                        exchange_name,
                    )
                    return None

                return result
        
        except Exception as e:
            logger.error(f"Error getting keys for {exchange_name}: {e}")
            return None
    
    def get_all_exchanges(self) -> List[Dict]:
        """Get all configured exchanges"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT exchange_name, exchange_type, testnet, enabled, updated_at
                    FROM api_keys
                    ORDER BY exchange_name
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Error getting all exchanges: {e}")
            return []
    
    def delete_exchange(self, exchange_name: str) -> bool:
        """Delete exchange API keys"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM api_keys WHERE exchange_name = %s
                """, (exchange_name,))
            
            logger.info(f"Deleted API keys for {exchange_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting keys for {exchange_name}: {e}")
            return False
    
    def toggle_exchange(self, exchange_name: str, enabled: bool) -> bool:
        """Enable or disable an exchange"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE api_keys 
                    SET enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE exchange_name = %s
                """, (enabled, exchange_name))
            
            logger.info(f"{'Enabled' if enabled else 'Disabled'} {exchange_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error toggling {exchange_name}: {e}")
            return False
    
    def _encrypt(self, data: str) -> str:
        """Encrypt string data"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, data: str) -> str:
        """Decrypt string data"""
        if not data:
            return ""
        return self.cipher.decrypt(data.encode()).decode()
    
    def has_valid_keys(self, exchange_name: str) -> bool:
        """Check if exchange has valid keys configured"""
        keys = self.get_exchange_keys(exchange_name)
        if not keys or not keys['enabled']:
            return False
        
        if keys['exchange_type'] == 'cex':
            return bool(keys.get('api_key') and keys.get('api_secret'))
        else:  # dex
            return bool(keys.get('private_key'))

