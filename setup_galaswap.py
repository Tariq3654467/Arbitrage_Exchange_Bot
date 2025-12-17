#!/usr/bin/env python3
"""
Setup script to configure GalaSwap integration
Helps users configure GalaSwap settings from galaswap-bot into arbitrage-bot
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any

def load_env_file(env_path: str = ".env") -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def save_env_file(env_vars: Dict[str, str], env_path: str = ".env"):
    """Save environment variables to .env file"""
    existing_vars = load_env_file(env_path)
    existing_vars.update(env_vars)
    
    with open(env_path, 'w') as f:
        for key, value in existing_vars.items():
            f.write(f"{key}={value}\n")

def load_galaswap_bot_env(galaswap_bot_path: str = "../galaswap-bot/.env") -> Dict[str, str]:
    """Load environment variables from galaswap-bot .env file"""
    if os.path.exists(galaswap_bot_path):
        return load_env_file(galaswap_bot_path)
    return {}

def update_config_yaml(config_path: str = "config/config.yaml"):
    """Update config.yaml with GalaSwap settings"""
    if not os.path.exists(config_path):
        print(f"Warning: {config_path} not found. Skipping config update.")
        return
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Ensure exchanges section exists
    if 'exchanges' not in config:
        config['exchanges'] = {}
    if 'dex' not in config['exchanges']:
        config['exchanges']['dex'] = []
    
    # Check if galaswap is already configured
    galaswap_exists = False
    for dex in config['exchanges']['dex']:
        if dex.get('name') == 'galaswap':
            galaswap_exists = True
            # Update existing config
            dex['enabled'] = True
            dex['chain'] = 'gala'
            break
    
    # Add galaswap if not exists
    if not galaswap_exists:
        config['exchanges']['dex'].append({
            'name': 'galaswap',
            'enabled': True,
            'chain': 'gala',
            'router_address': '0x0000000000000000000000000000000000000000',
            'factory_address': '0x0000000000000000000000000000000000000000'
        })
    
    # Add GalaSwap trading pairs if not exists
    if 'trading_pairs' not in config:
        config['trading_pairs'] = []
    
    existing_symbols = {pair.get('symbol') for pair in config['trading_pairs']}
    
    gala_pairs = [
        {'symbol': 'GALA/GUSDC', 'min_trade_amount': 1.0, 'enabled': True},
        {'symbol': 'GUSDC/GALA', 'min_trade_amount': 1.0, 'enabled': True},
        {'symbol': 'GALA/GUSDT', 'min_trade_amount': 1.0, 'enabled': True},
        {'symbol': 'GUSDT/GALA', 'min_trade_amount': 1.0, 'enabled': True},
    ]
    
    for pair in gala_pairs:
        if pair['symbol'] not in existing_symbols:
            config['trading_pairs'].append(pair)
    
    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✓ Updated {config_path} with GalaSwap configuration")

def main():
    """Main setup function"""
    print("=" * 60)
    print("GalaSwap Integration Setup")
    print("=" * 60)
    print()
    
    # Check if galaswap-bot directory exists
    galaswap_bot_path = Path("../galaswap-bot")
    if not galaswap_bot_path.exists():
        print("ℹ galaswap-bot directory not found. You'll need to configure manually.")
        print()
    
    # Load existing .env
    env_vars = load_env_file()
    
    # Try to load from galaswap-bot
    galaswap_env = load_galaswap_bot_env()
    
    # Map galaswap-bot env vars to arbitrage-bot env vars
    env_mapping = {
        'GALA_WALLET_ADDRESS': 'GALA_WALLET_ADDRESS',
        'GALA_PRIVATE_KEY': 'GALA_PRIVATE_KEY',
    }
    
    print("Environment Variables Configuration:")
    print("-" * 60)
    
    for galaswap_key, arbitrage_key in env_mapping.items():
        # Check if already set in arbitrage-bot
        if arbitrage_key in env_vars and env_vars[arbitrage_key]:
            print(f"✓ {arbitrage_key} is already configured")
        elif galaswap_key in galaswap_env and galaswap_env[galaswap_key]:
            # Copy from galaswap-bot
            env_vars[arbitrage_key] = galaswap_env[galaswap_key]
            print(f"✓ Copied {arbitrage_key} from galaswap-bot")
        else:
            # Ask user to input
            value = input(f"Enter {arbitrage_key} (or press Enter to skip): ").strip()
            if value:
                env_vars[arbitrage_key] = value
    
    # Add GALA_RPC_URL if not set
    if 'GALA_RPC_URL' not in env_vars or not env_vars.get('GALA_RPC_URL'):
        default_rpc = "https://jsonrpc.gala.games"
        rpc_url = input(f"Enter GALA_RPC_URL (default: {default_rpc}): ").strip()
        env_vars['GALA_RPC_URL'] = rpc_url if rpc_url else default_rpc
    
    # Save .env file
    save_env_file(env_vars)
    print(f"✓ Saved environment variables to .env")
    print()
    
    # Update config.yaml
    print("Updating config.yaml...")
    update_config_yaml()
    print()
    
    # Verify token config exists
    token_config_path = Path("config/galaswap_tokens.json")
    if token_config_path.exists():
        print(f"✓ Token configuration file exists: {token_config_path}")
    else:
        print(f"ℹ Token configuration file not found: {token_config_path}")
        print("  You can create it manually or it will use defaults.")
    print()
    
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify your .env file has correct GALA_WALLET_ADDRESS and GALA_PRIVATE_KEY")
    print("2. Start the bot: python main.py")
    print("3. Add GalaSwap credentials via the dashboard (Config → Exchange Keys)")
    print("4. Check the dashboard to verify GalaSwap connection and balances")
    print()
    print("For more information, see: docs/GALASWAP_INTEGRATION.md")

if __name__ == "__main__":
    main()

