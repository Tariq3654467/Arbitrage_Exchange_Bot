#!/usr/bin/env python3
"""
Run Web Dashboard
Starts the FastAPI web server for the dashboard
"""

import uvicorn
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Arbitrage Bot Web Dashboard")
    print("=" * 60)
    print("\n📊 Dashboard will be available at: http://localhost:8000")
    print("🔐 Default credentials: admin / admin (CHANGE THIS!)")
    print("\n Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

