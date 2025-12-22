#!/usr/bin/env python3
"""
GalaChain Public Key Derivation Script

This script derives the public key and Ethereum address from a private key
for use with GalaChain/GalaSwap API.

Usage:
    python3 scripts/get_galachain_pubkey.py

Or make it executable:
    chmod +x scripts/get_galachain_pubkey.py
    ./scripts/get_galachain_pubkey.py
"""

from eth_keys import keys
from eth_utils import decode_hex
import base64
import sys
import os

# REPLACE THIS with your 64-character private key (with or without 0x prefix)
# You can also set it via environment variable: export GALASWAP_PRIVATE_KEY="your_key"
PRIVATE_KEY_HEX = os.getenv("GALASWAP_PRIVATE_KEY", "0x2ed261898519a4ba7cf660de9889cc6ccf7bc45bff18c81ead0ed3cf0b015e5a")


def get_galachain_pubkey(private_key_hex: str):
    """
    Derive GalaChain public key and Ethereum address from private key
    
    Args:
        private_key_hex: Private key in hex format (with or without 0x prefix)
    
    Returns:
        tuple: (ethereum_address, base64_public_key)
    """
    try:
        # 1. Clean and validate private key
        if not private_key_hex:
            raise ValueError("Private key cannot be empty")
        
        # Remove 0x prefix if present
        if private_key_hex.startswith('0x') or private_key_hex.startswith('0X'):
            private_key_hex = private_key_hex[2:]
        
        # Validate length (should be 64 hex characters = 32 bytes)
        if len(private_key_hex) != 64:
            raise ValueError(f"Private key must be 64 hex characters (got {len(private_key_hex)})")
        
        # 2. Load the private key
        priv_key_bytes = decode_hex('0x' + private_key_hex)
        priv_key = keys.PrivateKey(priv_key_bytes)
        
        # 3. Get the UNCOMPRESSED public key (65 bytes: 0x04 + 64 bytes)
        pub_key_bytes = priv_key.public_key.to_bytes()
        
        # GalaChain typically expects the raw 64-byte point (without 0x04 prefix)
        # Remove first byte if it's the 0x04 prefix
        if len(pub_key_bytes) == 65 and pub_key_bytes[0] == 0x04:
            pub_key_bytes = pub_key_bytes[1:]
        
        # 4. Encode to Base64
        base64_pubkey = base64.b64encode(pub_key_bytes).decode('utf-8')
        
        # 5. Get Ethereum address
        eth_address = priv_key.public_key.to_checksum_address()
        
        return eth_address, base64_pubkey
    
    except Exception as e:
        print(f"❌ Error deriving public key: {e}", file=sys.stderr)
        raise


def main():
    """Main function"""
    print("=" * 60)
    print("GalaChain Public Key Derivation Tool")
    print("=" * 60)
    print()
    
    # Check if private key is set
    if PRIVATE_KEY_HEX == "0x2ed261898519a4ba7cf660de9889cc6ccf7bc45bff18c81ead0ed3cf0b015e5a":
        print("⚠️  WARNING: Using example private key!")
        print("   Please update PRIVATE_KEY_HEX in this script or set GALASWAP_PRIVATE_KEY environment variable")
        print()
    
    try:
        # Derive public key and address
        eth_address, base64_pubkey = get_galachain_pubkey(PRIVATE_KEY_HEX)
        
        # Display results
        print("✓ Successfully derived GalaChain credentials")
        print()
        print("-" * 60)
        print("YOUR CONFIG VALUES:")
        print("-" * 60)
        print(f"Ethereum Address:     {eth_address}")
        print(f"GalaChain Address:    eth|{eth_address[2:]}")  # Remove 0x prefix for GalaChain format
        print(f"Public Key (Base64):  {base64_pubkey}")
        print("-" * 60)
        print()
        print("📝 Add these to your config.yaml:")
        print()
        print("exchanges:")
        print("  dex:")
        print("    - name: galaswap")
        print(f"      wallet_address: \"eth|{eth_address[2:]}\"")
        print(f"      public_key: \"{base64_pubkey}\"")
        print("      # ... other settings ...")
        print()
        print("Or set environment variables:")
        print(f"export GALASWAP_WALLET_ADDRESS=\"eth|{eth_address[2:]}\"")
        print(f"export GALASWAP_PUBLIC_KEY=\"{base64_pubkey}\"")
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to derive public key: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

