import asyncio
import os
import ccxt.async_support as ccxt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
        'secret': API_SECRET,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True,
        }
    })
    
    if testnet:
        exchange.set_sandbox_mode(True)
    
    try:
        # await exchange.load_markets()
        balance = await exchange.fetch_balance()
        print(f"SUCCESS: Connected to {name}")
        # print(f"Balance: {balance}")
    except Exception as e:
        print(f"FAILED: {name} - {str(e)}")
    finally:
        await exchange.close()

async def main():
    if not API_KEY or not API_SECRET:
        print("Error: BINANCE_API_KEY or BINANCE_API_SECRET not found in .env")
        return

    # Test 1: Binance Spot (Mainnet)
    await test_connection("Binance Spot (Mainnet)", ccxt.binance, False)

    # Test 2: Binance Spot (Testnet)
    await test_connection("Binance Spot (Testnet)", ccxt.binance, True)

    # Test 3: Binance Futures (Mainnet)
    # await test_connection("Binance Futures (Mainnet)", ccxt.binanceusdm, False)

    # Test 4: Binance Futures (Testnet)
    await test_connection("Binance Futures (Testnet)", ccxt.binanceusdm, True)

if __name__ == "__main__":
    asyncio.run(main())
