"""
Security Utilities
Handles encryption, key management, and secure storage
"""

import os
import base64
from typing import Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend


class SecurityManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize security manager
        
        Args:
            encryption_key: Base64 encoded encryption key, or None to generate
        """
        if encryption_key:
            self.key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key"""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
        """
        Derive an encryption key from a password
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if None)
        
        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data
        
        Args:
            data: Data to encrypt
        
        Returns:
            Base64 encoded encrypted data
        """
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
        
        Returns:
            Decrypted string
        """
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key"""
        return self.encrypt(api_key)
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key"""
        return self.decrypt(encrypted_key)
    
    def encrypt_private_key(self, private_key: str) -> str:
        """Encrypt a private key"""
        return self.encrypt(private_key)
    
    def decrypt_private_key(self, encrypted_key: str) -> str:
        """Decrypt a private key"""
        return self.decrypt(encrypted_key)


def validate_private_key(private_key: str) -> bool:
    """
    Validate if a private key is in correct format
    
    Args:
        private_key: Private key to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Remove 0x prefix if present
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        # Check if it's a valid hex string of 64 characters
        if len(private_key) != 64:
            return False
        
        int(private_key, 16)
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_log_message(message: str, sensitive_words: list = None) -> str:
    """
    Remove sensitive information from log messages
    
    Args:
        message: Log message to sanitize
        sensitive_words: List of sensitive words/patterns to mask
    
    Returns:
        Sanitized message
    """
    if sensitive_words is None:
        sensitive_words = ['api_key', 'secret', 'password', 'private_key', 'passphrase']
    
    sanitized = message
    for word in sensitive_words:
        if word in sanitized.lower():
            # Replace with masked version
            sanitized = sanitized.replace(word, "****")
    
    return sanitized


class IPWhitelist:
    """Manages IP whitelist validation"""
    
    def __init__(self, allowed_ips: str = ""):
        """
        Initialize IP whitelist
        
        Args:
            allowed_ips: Comma-separated list of allowed IPs
        """
        self.allowed_ips = set(ip.strip() for ip in allowed_ips.split(',') if ip.strip())
    
    def is_allowed(self, ip: str) -> bool:
        """
        Check if an IP is allowed
        
        Args:
            ip: IP address to check
        
        Returns:
            True if allowed, False otherwise
        """
        if not self.allowed_ips:
            return True  # If no whitelist, allow all
        
        return ip in self.allowed_ips
    
    def add_ip(self, ip: str):
        """Add an IP to whitelist"""
        self.allowed_ips.add(ip)
    
    def remove_ip(self, ip: str):
        """Remove an IP from whitelist"""
        self.allowed_ips.discard(ip)

