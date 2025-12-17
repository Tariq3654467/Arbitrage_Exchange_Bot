#!/usr/bin/env python3
"""
Test script to execute a trade on GalaSwap
This script will:
1. Create a swap on GalaSwap (if needed)
2. Accept a swap on GalaSwap
3. Or execute a simple trade for testing
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.exchanges.dex.galaswap_connector import GalaswapConnector
from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger()

async def test_galaswap_trade():
    """Test executing a trade on GalaSwap"""
    
    # Load settings
    settings = get_settings()
    
    # Get GalaSwap credentials
    wallet_address = settings.gala_wallet_address
    private_key = settings.gala_private_key
    
    if not wallet_address or not private_key:
        print("❌ GalaSwap credentials not configured!")
        print("Please configure via dashboard or .env file:")
        print("  GALA_WALLET_ADDRESS=your_wallet")
        print("  GALA_PRIVATE_KEY=your_key")
        return
    
    print(f"🔗 Connecting to GalaSwap with wallet: {wallet_address[:20]}...")
    
    # Initialize connector
    connector = GalaswapConnector(
        wallet_address=wallet_address,
        private_key=private_key
    )
    
    await connector.connect()
    
    # Check balances
    print("\n📊 Checking balances...")
    balances = await connector.get_balance()
    if balances:
        for symbol, balance in balances.items():
            if balance.free > 0:
                print(f"  {symbol}: {balance.free} (free), {balance.locked} (locked)")
    else:
        print("  No balances found")
    
    # Try to find available swaps
    print("\n🔍 Checking for available swaps...")
    
    # Common pairs to check
    test_pairs = [
        ("GALA", "GUSDC"),
        ("GUSDC", "GALA"),
        ("GALA", "GUSDT"),
        ("GUSDT", "GALA"),
    ]
    
    available_swaps = []
    
    for base, quote in test_pairs:
        try:
            symbol = f"{base}/{quote}"
            print(f"  Checking {symbol}...")
            
            # Try to get order book (this fetches available swaps)
            order_book = await connector.get_order_book(symbol, depth=5)
            
            if order_book.bids:
                print(f"    ✅ Found {len(order_book.bids)} available swaps!")
                for i, (price, qty) in enumerate(order_book.bids[:3], 1):
                    print(f"      {i}. Price: {price:.6f}, Quantity: {qty:.6f}")
                available_swaps.append((symbol, order_book))
            else:
                print(f"    ❌ No swaps available")
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
    if not available_swaps:
        print("\n⚠️  No available swaps found. Creating a test swap...")
        
        # Check what tokens we have
        if not balances:
            print("❌ No balances available. Cannot create swap.")
            return
        
        # Find a token we have
        available_tokens = [s for s, b in balances.items() if b.free > 0]
        if not available_tokens:
            print("❌ No tokens with free balance to create swap.")
            return
        
        print(f"📝 Available tokens: {', '.join(available_tokens)}")
        
        # Try to create a swap (e.g., offer GALA for GUSDC)
        if "GALA" in available_tokens and balances["GALA"].free > 1:
            print("\n🔄 Creating swap: Offering 1 GALA for GUSDC...")
            try:
                # Create a swap offering GALA, wanting GUSDC
                order = await connector.place_market_order(
                    symbol="GALA/GUSDC",
                    side="sell",
                    quantity=1.0
                )
                print(f"✅ Swap created! Order ID: {order.order_id}")
                print(f"   Status: {order.status}")
                print("\n💡 Note: This creates a swap that others can accept.")
                print("   To test accepting, wait for someone to create a swap, or")
                print("   create another swap in the opposite direction.")
                return
            except Exception as e:
                print(f"❌ Failed to create swap: {e}")
        else:
            print(f"❌ Don't have enough GALA to create swap. Need at least 1 GALA.")
            print(f"   Current balance: {balances.get('GALA', 'N/A')}")
    
    else:
        # Execute a trade with available swap
        symbol, order_book = available_swaps[0]
        print(f"\n✅ Found available swaps for {symbol}")
        print(f"   Executing test trade...")
        
        try:
            # Get the best bid (lowest price to buy)
            best_bid = order_book.bids[0]
            price, max_qty = best_bid
            
            # Use small quantity for testing
            quantity = min(0.1, max_qty * 0.1)  # Use 10% of available or 0.1, whichever is smaller
            
            print(f"   Buying {quantity} {symbol.split('/')[0]} at price {price:.6f}")
            
            order = await connector.place_market_order(
                symbol=symbol,
                side="buy",
                quantity=quantity
            )
            
            print(f"\n✅ Trade executed!")
            print(f"   Order ID: {order.order_id}")
            print(f"   Status: {order.status}")
            print(f"   Price: {order.price}")
            print(f"   Quantity: {order.quantity}")
            print(f"   Filled: {order.filled_quantity}")
            
        except Exception as e:
            print(f"❌ Failed to execute trade: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("GalaSwap Trade Test Script")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(test_galaswap_trade())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

