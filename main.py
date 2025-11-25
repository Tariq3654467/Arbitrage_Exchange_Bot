#!/usr/bin/env python3
"""
Arbitrage Cross-Exchange Bot
Main entry point
"""

import asyncio
import sys
from src.bot import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

