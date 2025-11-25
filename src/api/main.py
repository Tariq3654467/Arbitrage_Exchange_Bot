"""
FastAPI Web Dashboard
Provides REST API and web interface for bot management
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Dict, Optional
import asyncio
import json
from datetime import datetime
from pathlib import Path

from ..bot import ArbitrageBot
from ..utils.logger import get_logger
from .models import (
    BotStatus, ExchangeConfig, TradingConfig, RiskConfig,
    TradeHistory, OpportunityData, PortfolioData
)

logger = get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    description="Web interface for crypto arbitrage bot management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic authentication
security = HTTPBasic()

# Global bot instance
bot: Optional[ArbitrageBot] = None
bot_task: Optional[asyncio.Task] = None

# Database instances
postgres_db = None

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify basic authentication"""
    # TODO: Load from config or environment
    correct_username = "admin"
    correct_password = "admin"  # Change this!
    
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    global bot, postgres_db
    logger.info("Starting Web Dashboard API...")
    
    # Initialize database connection
    try:
        from ..database.postgres_manager import PostgresManager
        from ..config.settings import get_settings
        
        settings = get_settings()
        postgres_db = PostgresManager(settings.postgres_url)
        postgres_db.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        logger.warning("API keys will not persist. Configure database to save keys.")
    
    # Bot will be initialized when user clicks "Start"


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global bot, bot_task, postgres_db
    if bot and bot.is_running:
        await bot.stop()
    if bot_task:
        bot_task.cancel()
    if postgres_db:
        postgres_db.disconnect()
    logger.info("Web Dashboard API stopped")


# ==================== Dashboard Routes ====================

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve main dashboard HTML"""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return "<h1>Dashboard HTML not found</h1>"


# Mount static files
try:
    static_path = Path(__file__).parent / "static"
    static_path.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


# ==================== Bot Control Routes ====================

@app.post("/api/bot/start")
async def start_bot(username: str = Depends(verify_credentials)):
    """Start the trading bot with database-configured API keys"""
    global bot, bot_task
    
    try:
        if bot and bot.is_running:
            return {"status": "error", "message": "Bot is already running"}
        
        # Check if we have database connection
        if not postgres_db:
            return {"status": "error", "message": "Database not available. Cannot load API keys."}
        
        # Load API keys from database
        from ..database.api_keys_manager import APIKeysManager
        from ..config.settings import get_settings
        
        keys_manager = APIKeysManager(postgres_db)
        settings = get_settings()
        
        # Override settings with database keys
        for exchange_name in ['binance', 'okx', 'bybit']:
            keys = keys_manager.get_exchange_keys(exchange_name)
            if keys and keys['enabled']:
                if exchange_name == 'binance':
                    settings.binance_api_key = keys.get('api_key', '')
                    settings.binance_api_secret = keys.get('api_secret', '')
                    settings.binance_testnet = keys.get('testnet', False)
                elif exchange_name == 'okx':
                    settings.okx_api_key = keys.get('api_key', '')
                    settings.okx_api_secret = keys.get('api_secret', '')
                    settings.okx_passphrase = keys.get('passphrase', '')
                    settings.okx_testnet = keys.get('testnet', False)
                elif exchange_name == 'bybit':
                    settings.bybit_api_key = keys.get('api_key', '')
                    settings.bybit_api_secret = keys.get('api_secret', '')
                    settings.bybit_testnet = keys.get('testnet', False)
        
        # Initialize bot with loaded settings
        bot = ArbitrageBot()
        await bot.initialize()
        
        # Start bot in background task
        bot_task = asyncio.create_task(bot.start())
        
        await broadcast_message({
            "type": "bot_status",
            "status": "running",
            "message": "Bot started successfully"
        })
        
        return {"status": "success", "message": "Bot started successfully with configured API keys"}
    
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/bot/stop")
async def stop_bot(username: str = Depends(verify_credentials)):
    """Stop the trading bot"""
    global bot, bot_task
    
    try:
        if not bot or not bot.is_running:
            return {"status": "error", "message": "Bot is not running"}
        
        await bot.stop()
        
        if bot_task:
            bot_task.cancel()
            bot_task = None
        
        await broadcast_message({
            "type": "bot_status",
            "status": "stopped",
            "message": "Bot stopped successfully"
        })
        
        return {"status": "success", "message": "Bot stopped successfully"}
    
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/bot/status")
async def get_bot_status():
    """Get current bot status"""
    global bot
    
    if not bot:
        return {
            "is_running": False,
            "uptime": 0,
            "message": "Bot not initialized"
        }
    
    status = bot.get_status()
    return status


@app.post("/api/bot/emergency-stop")
async def emergency_stop(username: str = Depends(verify_credentials)):
    """Trigger emergency stop"""
    global bot
    
    if not bot or not bot.risk_manager:
        return {"status": "error", "message": "Bot not initialized"}
    
    bot.risk_manager.trigger_emergency_stop("Manual emergency stop from dashboard")
    
    await broadcast_message({
        "type": "alert",
        "level": "critical",
        "message": "EMERGENCY STOP ACTIVATED"
    })
    
    return {"status": "success", "message": "Emergency stop triggered"}


# ==================== Configuration Routes ====================

@app.get("/api/config/exchanges")
async def get_exchanges_config():
    """Get exchange configuration from database"""
    try:
        # Available exchanges list
        available_cex = [
            {"name": "binance", "display_name": "Binance", "supports_testnet": True},
            {"name": "okx", "display_name": "OKX", "supports_testnet": True, "requires_passphrase": True},
            {"name": "bybit", "display_name": "Bybit", "supports_testnet": True}
        ]
        
        available_dex = [
            {"name": "pancakeswap", "display_name": "PancakeSwap", "chain": "BSC"},
            {"name": "uniswap_v2", "display_name": "Uniswap V2", "chain": "Ethereum"},
            {"name": "quickswap", "display_name": "QuickSwap", "chain": "Polygon"}
        ]
        
        if not postgres_db:
            return {
                "available_cex": available_cex,
                "available_dex": available_dex,
                "configured_exchanges": []
            }
        
        # Get configured exchanges from database
        from ..database.api_keys_manager import APIKeysManager
        keys_manager = APIKeysManager(postgres_db)
        
        configured = keys_manager.get_all_exchanges()
        
        configured_list = []
        for ex in configured:
            # Check if it has valid keys
            has_keys = keys_manager.has_valid_keys(ex['exchange_name'])
            
            configured_list.append({
                "name": ex['exchange_name'],
                "type": ex['exchange_type'],
                "enabled": ex['enabled'],
                "testnet": ex.get('testnet', False),
                "configured": has_keys,
                "last_updated": ex['updated_at'].isoformat() if ex.get('updated_at') else None
            })
        
        return {
            "available_cex": available_cex,
            "available_dex": available_dex,
            "configured_exchanges": configured_list
        }
    
    except Exception as e:
        logger.error(f"Error getting exchanges config: {e}")
        return {
            "available_cex": [],
            "available_dex": [],
            "configured_exchanges": []
        }


@app.post("/api/config/exchange")
async def update_exchange_config(
    config: ExchangeConfig,
    username: str = Depends(verify_credentials)
):
    """Update exchange API credentials - saves to database"""
    try:
        # Initialize database if needed
        if not postgres_db:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Import API keys manager
        from ..database.api_keys_manager import APIKeysManager
        
        # Initialize keys manager
        keys_manager = APIKeysManager(postgres_db)
        
        # Save keys to database
        success = keys_manager.save_exchange_keys(
            exchange_name=config.exchange_name,
            exchange_type='cex',
            api_key=config.api_key,
            api_secret=config.api_secret,
            passphrase=config.passphrase,
            testnet=config.testnet,
            enabled=config.enabled
        )
        
        if success:
            return {
                "status": "success", 
                "message": f"{config.exchange_name} configured and saved to database"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save API keys")
    
    except Exception as e:
        logger.error(f"Error updating exchange config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/trading")
async def get_trading_config():
    """Get trading configuration"""
    from ..config.settings import get_settings
    settings = get_settings()
    
    return {
        "min_profit_threshold": settings.trading.min_profit_threshold,
        "max_trade_size_percent": settings.trading.max_trade_size_percent,
        "max_slippage_percent": settings.trading.max_slippage_percent,
        "order_timeout_seconds": settings.trading.order_timeout_seconds,
        "paper_trading": settings.bot.paper_trading
    }


@app.post("/api/config/trading")
async def update_trading_config(
    config: TradingConfig,
    username: str = Depends(verify_credentials)
):
    """Update trading configuration"""
    try:
        from ..config.settings import get_settings
        settings = get_settings()
        
        settings.trading.min_profit_threshold = config.min_profit_threshold
        settings.trading.max_trade_size_percent = config.max_trade_size_percent
        settings.trading.max_slippage_percent = config.max_slippage_percent
        
        # TODO: Save to config file
        
        return {"status": "success", "message": "Trading config updated"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/risk")
async def get_risk_config():
    """Get risk management configuration"""
    from ..config.settings import get_settings
    settings = get_settings()
    
    return {
        "max_drawdown_percent": settings.risk.max_drawdown_percent,
        "max_daily_loss_percent": settings.risk.max_daily_loss_percent,
        "max_position_size_usd": settings.risk.max_position_size_usd,
        "emergency_stop_enabled": settings.risk.emergency_stop_enabled
    }


@app.post("/api/config/risk")
async def update_risk_config(
    config: RiskConfig,
    username: str = Depends(verify_credentials)
):
    """Update risk management configuration"""
    try:
        from ..config.settings import get_settings
        settings = get_settings()
        
        settings.risk.max_drawdown_percent = config.max_drawdown_percent
        settings.risk.max_daily_loss_percent = config.max_daily_loss_percent
        settings.risk.max_position_size_usd = config.max_position_size_usd
        
        # Update risk manager if bot is running
        global bot
        if bot and bot.risk_manager:
            bot.risk_manager.max_drawdown_percent = config.max_drawdown_percent
            bot.risk_manager.max_daily_loss_percent = config.max_daily_loss_percent
            bot.risk_manager.max_position_size_usd = config.max_position_size_usd
        
        return {"status": "success", "message": "Risk config updated"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Market Data Routes ====================

@app.get("/api/market/prices")
async def get_current_prices():
    """Get current prices across all exchanges"""
    global bot
    
    if not bot or not bot.price_monitor:
        return {"error": "Bot not running"}
    
    prices = {}
    for symbol in bot.price_monitor.trading_pairs:
        symbol_prices = bot.price_monitor.get_all_prices(symbol)
        prices[symbol] = {
            exchange: {
                "bid": data.bid,
                "ask": data.ask,
                "mid": data.mid,
                "spread": data.spread,
                "timestamp": data.timestamp.isoformat()
            }
            for exchange, data in symbol_prices.items()
        }
    
    return prices


@app.get("/api/market/opportunities")
async def get_opportunities():
    """Get recent arbitrage opportunities"""
    global bot
    
    if not bot or not bot.price_monitor:
        return {"opportunities": []}
    
    opportunities = bot.price_monitor.get_recent_opportunities(limit=50)
    
    return {
        "opportunities": [
            {
                "symbol": opp.symbol,
                "buy_exchange": opp.buy_exchange,
                "sell_exchange": opp.sell_exchange,
                "buy_price": opp.buy_price,
                "sell_price": opp.sell_price,
                "profit_percent": opp.gross_profit_percent,
                "timestamp": opp.timestamp.isoformat()
            }
            for opp in opportunities
        ]
    }


@app.get("/api/market/spreads")
async def get_spreads():
    """Get current spreads for all trading pairs"""
    global bot
    
    if not bot or not bot.price_monitor:
        return {"spreads": {}}
    
    spreads = {}
    for symbol in bot.price_monitor.trading_pairs:
        prices = bot.price_monitor.get_all_prices(symbol)
        
        if len(prices) >= 2:
            best_bid = max((p.bid for p in prices.values()))
            best_ask = min((p.ask for p in prices.values()))
            spread = ((best_bid - best_ask) / best_ask) * 100 if best_ask > 0 else 0
            
            spreads[symbol] = {
                "spread_percent": spread,
                "best_bid": best_bid,
                "best_ask": best_ask
            }
    
    return {"spreads": spreads}


# ==================== Portfolio & Balance Routes ====================

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary"""
    global bot
    
    if not bot or not bot.portfolio_manager:
        return {"error": "Bot not running"}
    
    try:
        snapshot = await bot.portfolio_manager.get_portfolio_snapshot()
        
        return {
            "total_value_usd": snapshot.total_value_usd,
            "allocation": snapshot.allocation_percent,
            "target_allocation": snapshot.target_allocation,
            "rebalance_needed": snapshot.rebalance_needed,
            "timestamp": snapshot.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        return {"error": str(e)}


@app.get("/api/portfolio/balances")
async def get_balances():
    """Get balances across all exchanges"""
    global bot
    
    if not bot or not bot.portfolio_manager:
        return {"balances": {}}
    
    try:
        balances = await bot.portfolio_manager.update_balances()
        
        return {
            "balances": {
                asset: {
                    "total_amount": bal.total_amount,
                    "total_value_usd": bal.total_value_usd,
                    "exchanges": bal.balances_by_exchange
                }
                for asset, bal in balances.items()
            }
        }
    except Exception as e:
        logger.error(f"Error getting balances: {e}")
        return {"error": str(e)}


# ==================== Trading History Routes ====================

@app.get("/api/trades/history")
async def get_trade_history(limit: int = 50):
    """Get trade history"""
    global bot
    
    if not bot or not bot.trade_executor:
        return {"trades": []}
    
    trades = bot.trade_executor.get_recent_trades(limit=limit)
    
    return {
        "trades": [
            {
                "symbol": trade.analysis.opportunity.symbol,
                "buy_exchange": trade.analysis.opportunity.buy_exchange,
                "sell_exchange": trade.analysis.opportunity.sell_exchange,
                "amount": trade.analysis.buy_amount,
                "profit_usd": trade.actual_profit_usd,
                "profit_percent": trade.actual_profit_percent,
                "status": trade.status.value,
                "timestamp": trade.timestamp.isoformat()
            }
            for trade in trades
        ]
    }


@app.get("/api/trades/statistics")
async def get_trade_statistics():
    """Get trading statistics"""
    global bot
    
    if not bot or not bot.trade_executor:
        return {"error": "Bot not running"}
    
    stats = bot.trade_executor.get_trade_statistics()
    return stats


# ==================== Risk & Performance Routes ====================

@app.get("/api/risk/metrics")
async def get_risk_metrics():
    """Get current risk metrics"""
    global bot
    
    if not bot or not bot.risk_manager or not bot.portfolio_manager:
        return {"error": "Bot not running"}
    
    try:
        portfolio_value = await bot.portfolio_manager.get_total_portfolio_value()
        risk_metrics = bot.risk_manager.get_risk_metrics(portfolio_value)
        
        return {
            "portfolio_value": risk_metrics.portfolio_value_usd,
            "daily_pnl": risk_metrics.daily_pnl,
            "daily_pnl_percent": risk_metrics.daily_pnl_percent,
            "drawdown_percent": risk_metrics.drawdown_percent,
            "risk_level": risk_metrics.risk_level.value,
            "trading_enabled": bot.risk_manager.is_trading_enabled,
            "emergency_stop": bot.risk_manager.emergency_stop_triggered
        }
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        return {"error": str(e)}


@app.get("/api/performance/statistics")
async def get_performance_statistics():
    """Get overall performance statistics"""
    global bot
    
    if not bot:
        return {"error": "Bot not running"}
    
    stats = {}
    
    if bot.risk_manager:
        stats["risk"] = bot.risk_manager.get_statistics()
    
    if bot.trade_executor:
        stats["trading"] = bot.trade_executor.get_trade_statistics()
    
    if bot.price_monitor:
        stats["monitoring"] = bot.price_monitor.get_statistics()
    
    return stats


# ==================== WebSocket for Real-time Updates ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Send periodic updates
            if bot and bot.is_running:
                # Send status update
                status = bot.get_status()
                await websocket.send_json({
                    "type": "status_update",
                    "data": status,
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    disconnected = []
    for connection in websocket_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        websocket_connections.remove(conn)


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot.is_running if bot else False
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

