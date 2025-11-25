"""
API Keys Manager
Securely stores and retrieves API keys from database
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from cryptography.fernet import Fernet
from ..utils.logger import get_logger

logger = get_logger()


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
        
        # Initialize encryption
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate new key if not provided
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            self.encryption_key = key.decode()
            logger.warning(f"Generated new encryption key. Save this securely: {self.encryption_key}")
        
        self._initialize_table()
    
    def _initialize_table(self):
        """Create API keys table if not exists"""
        try:
            with self.db.get_cursor() as cursor:
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
                logger.info("API keys table initialized")
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
        enabled: bool = True
    ) -> bool:
        """
        Save DEX private key
        
        Args:
            exchange_name: DEX name
            private_key: Wallet private key
            enabled: Enable this DEX
        
        Returns:
            True if saved successfully
        """
        try:
            encrypted_key = self._encrypt(private_key)
            
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO api_keys (
                        exchange_name, exchange_type, private_key, 
                        enabled, updated_at
                    ) VALUES (
                        %s, 'dex', %s, %s, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (exchange_name) 
                    DO UPDATE SET
                        private_key = EXCLUDED.private_key,
                        enabled = EXCLUDED.enabled,
                        updated_at = CURRENT_TIMESTAMP
                """, (exchange_name, encrypted_key, enabled))
            
            logger.info(f"Saved private key for {exchange_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving private key for {exchange_name}: {e}")
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
                           private_key, testnet, enabled
                    FROM api_keys
                    WHERE exchange_name = %s
                """, (exchange_name,))
                
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                result = {
                    'exchange_name': exchange_name,
                    'exchange_type': row['exchange_type'],
                    'testnet': row['testnet'],
                    'enabled': row['enabled']
                }
                
                # Decrypt keys
                if row['exchange_type'] == 'cex':
                    result['api_key'] = self._decrypt(row['api_key']) if row['api_key'] else None
                    result['api_secret'] = self._decrypt(row['api_secret']) if row['api_secret'] else None
                    result['passphrase'] = self._decrypt(row['passphrase']) if row['passphrase'] else None
                else:  # dex
                    result['private_key'] = self._decrypt(row['private_key']) if row['private_key'] else None
                
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

