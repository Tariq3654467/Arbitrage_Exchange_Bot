#!/usr/bin/env python3
"""
Verify GalaSwap credentials
Derives wallet address from private key to ensure they match
"""

import sys
from eth_account import Account
from eth_keys import keys
import base64

def derive_wallet_info(private_key: str):
    """Derive wallet address and public key from private key"""
    # Clean private key
    private_key_clean = private_key.strip()
    if private_key_clean.startswith('0x'):
        private_key_clean = private_key_clean[2:]
    
    if len(private_key_clean) != 64:
        print(f"❌ Invalid private key length: {len(private_key_clean)} (expected 64)")
        return None
    
    try:
        # Derive Ethereum address
        account = Account.from_key('0x' + private_key_clean)
        ethereum_address = account.address
        
        # Derive compressed public key (same as TypeScript)
        private_key_obj = keys.PrivateKey(bytes.fromhex(private_key_clean))
        public_key_obj = private_key_obj.public_key
        public_key_bytes = public_key_obj.to_bytes(compressed=True)
        public_key_base64 = base64.b64encode(public_key_bytes).decode('utf-8')
        
        return {
            'ethereum_address': ethereum_address,
            'public_key_base64': public_key_base64,
            'private_key': private_key_clean
        }
    except Exception as e:
        print(f"❌ Error deriving wallet info: {e}")
        return None

def main():
    print("=" * 60)
    print("GalaSwap Credentials Verification")
    print("=" * 60)
    print()
    
    # Get private key
    if len(sys.argv) > 1:
        private_key = sys.argv[1]
    else:
        print("Enter your Gala private key (will not be displayed):")
        import getpass
        private_key = getpass.getpass("Private Key: ").strip()
    
    if not private_key:
        print("❌ Private key is required")
        return
    
    print("\n🔍 Deriving wallet information from private key...")
    info = derive_wallet_info(private_key)
    
    if not info:
        return
    
    print("\n✅ Wallet Information:")
    print("-" * 60)
    print(f"Ethereum Address: {info['ethereum_address']}")
    print(f"Public Key (Base64): {info['public_key_base64'][:50]}...")
    print()
    
    print("📝 Configuration:")
    print("-" * 60)
    print("Add to your .env file or dashboard:")
    print()
    print(f"GALA_WALLET_ADDRESS={info['ethereum_address']}")
    print(f"GALA_PRIVATE_KEY={info['private_key']}")
    print()
    
    # Check if user provided a wallet address to verify
    if len(sys.argv) > 2:
        provided_address = sys.argv[2].strip()
        print(f"\n🔍 Verifying provided address: {provided_address}")
        
        if provided_address.lower() == info['ethereum_address'].lower():
            print("✅ Wallet address MATCHES private key!")
        else:
            print(f"❌ Wallet address DOES NOT MATCH private key!")
            print(f"   Expected: {info['ethereum_address']}")
            print(f"   Provided: {provided_address}")
            print()
            print("⚠️  This will cause signature validation errors!")
            print("   Update your wallet address to match the derived address above.")
    else:
        print("\n💡 Tip: To verify an existing wallet address, run:")
        print(f"   python verify_gala_credentials.py <private_key> <wallet_address>")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

