"""
FastAPI Web Dashboard
Provides REST API and web interface for bot management
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import asyncio
import json
from datetime import datetime
from pathlib import Path

from ..bot import ArbitrageBot
from ..utils.logger import get_logger
from .models import (
    BotStatus, ExchangeConfig, DEXConfig, TradingConfig, RiskConfig,
    TradeHistory, OpportunityData, PortfolioData, StartBotRequest
)
from .routes import exchanges as exchanges_router
from .routes import advanced as advanced_router
from .dependencies import verify_credentials
from . import dependencies as deps

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

# Include routers
app.include_router(exchanges_router.router)
app.include_router(advanced_router.router)

# Global bot instance
bot: Optional[ArbitrageBot] = None
bot_task: Optional[asyncio.Task] = None

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    global bot
    
    logger.info("Starting Web Dashboard API...")
    
    # Initialize database connection
    try:
        from ..database.postgres_manager import PostgresManager
        from ..config.settings import get_settings
        
        settings = get_settings()
        # Use individual parameters to avoid connection string parsing issues with special characters
        db_instance = PostgresManager(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        db_instance.connect()
        # Set the global postgres_db in dependencies module
        deps.postgres_db = db_instance
        logger.info("Database connected successfully")
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        logger.warning("API keys will not persist. Configure database to save keys.")
    
    # Bot will be initialized when user clicks "Start"


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global bot, bot_task
    import src.api.dependencies as deps
    
    if bot and bot.is_running:
        await bot.stop()
    if bot_task:
        bot_task.cancel()
    if deps.postgres_db:
        deps.postgres_db.disconnect()
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
async def start_bot(
    payload: Optional[StartBotRequest] = None,
    username: str = Depends(verify_credentials),
):
    """
    Start the trading bot.

    If `payload.exchanges` is provided, API keys are taken directly from the
    request body and NOT persisted to the database. If not provided, the
    previous behaviour is used and keys are loaded from the database.
    """
    global bot, bot_task
    
    try:
        if bot and bot.is_running:
            return {"status": "error", "message": "Bot is already running"}
        
        from ..config.settings import get_settings
        settings = get_settings()

        if payload and payload.exchanges:
            # Use ephemeral keys from request body (non-persistent)
            # and ensure corresponding exchanges are enabled in settings
            for ex in payload.exchanges:
                if not ex.enabled:
                    continue

                # Set API keys in settings (used by connectors)
                if ex.exchange_name == 'binance':
                    settings.binance_api_key = ex.api_key
                    settings.binance_api_secret = ex.api_secret

                # Also flip enabled flag in YAML-based config so get_cex_exchanges() returns it
                if settings.exchanges and 'cex' in settings.exchanges:
                    found = False
                    for cfg in settings.exchanges['cex']:
                        if cfg.get('name') == ex.exchange_name:
                            cfg['enabled'] = True
                            found = True
                            break
                    if not found:
                        settings.exchanges['cex'].append(
                            {
                                'name': ex.exchange_name,
                                'enabled': True,
                                # Default new ephemeral exchanges to testnet for safety
                                'testnet': True,
                                'order_type': 'market',
                                'max_latency_ms': 50,
                                'websocket_enabled': True,
                            }
                        )
        else:
            # Backwards-compatible: load from database
            if not deps.postgres_db:
                return {"status": "error", "message": "Database not available. Cannot load API keys."}

            from ..database.api_keys_manager import APIKeysManager

            keys_manager = APIKeysManager(deps.postgres_db)

            for exchange_name in ['binance', 'mexc']:
                keys = keys_manager.get_exchange_keys(exchange_name)
                if keys and keys['enabled']:
                    if exchange_name == 'binance':
                        settings.binance_api_key = keys.get('api_key', '')
                        settings.binance_api_secret = keys.get('api_secret', '')
                        settings.binance_testnet = keys.get('testnet', False)
                    elif exchange_name == 'mexc':
                        settings.mexc_api_key = keys.get('api_key', '')
                        settings.mexc_api_secret = keys.get('api_secret', '')
                        settings.mexc_testnet = keys.get('testnet', False)
            
            # Load DEX configuration from database
            dex_exchanges = ['galaswap']
            for dex_name in dex_exchanges:
                keys = keys_manager.get_exchange_keys(dex_name)
                if keys and keys.get('enabled') and keys.get('private_key'):
                    chain = keys.get('chain', '')
                    rpc_url = keys.get('rpc_url', '')
                    private_key = keys.get('private_key', '')
                    wallet_address = keys.get('wallet_address', '')
                    router_address = keys.get('router_address', '')
                    factory_address = keys.get('factory_address', '')
                    
                    # Set private keys and RPC URLs in settings
                    if chain == 'gala' or dex_name == 'galaswap':
                        settings.gala_private_key = private_key
                        settings.gala_wallet_address = wallet_address or ''
                        if rpc_url:
                            settings.gala_rpc_url = rpc_url
                    
                    # Update DEX config in settings to include router/factory addresses
                    if settings.exchanges and 'dex' in settings.exchanges:
                        for dex_cfg in settings.exchanges['dex']:
                            if dex_cfg.get('name') == dex_name:
                                dex_cfg['enabled'] = True
                                if router_address:
                                    dex_cfg['router_address'] = router_address
                                if factory_address:
                                    dex_cfg['factory_address'] = factory_address
                                if chain:
                                    dex_cfg['chain'] = chain
                                break
        
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
            {"name": "mexc", "display_name": "MEXC", "supports_testnet": False}
        ]
        
        available_dex = [
            {"name": "galaswap", "display_name": "Galaswap", "chain": "Gala Chain"}
        ]
        
        if not deps.postgres_db:
            return {
                "available_cex": available_cex,
                "available_dex": available_dex,
                "configured_exchanges": []
            }
        
        # Get configured exchanges from database
        from ..database.api_keys_manager import APIKeysManager
        keys_manager = APIKeysManager(deps.postgres_db)
        
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
        if not deps.postgres_db:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Import API keys manager
        from ..database.api_keys_manager import APIKeysManager
        
        # Initialize keys manager
        keys_manager = APIKeysManager(deps.postgres_db)
        
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


@app.post("/api/config/dex")
async def update_dex_config(
    config: DEXConfig,
    username: str = Depends(verify_credentials)
):
    """Update DEX exchange configuration"""
    try:
        # Initialize database if needed
        if not deps.postgres_db:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Import API keys manager
        from ..database.api_keys_manager import APIKeysManager
        
        # Initialize keys manager
        keys_manager = APIKeysManager(deps.postgres_db)
        
        # Determine chain if not provided
        chain = config.chain
        if not chain:
            # Auto-detect chain based on exchange name
            if config.exchange_name == 'galaswap':
                chain = 'gala'
        
        # Get default RPC URLs if not provided
        rpc_url = config.rpc_url
        if not rpc_url:
            from ..config.settings import get_settings
            settings = get_settings()
            if chain == 'gala':
                rpc_url = settings.gala_rpc_url or "https://jsonrpc.gala.games"
        
        # Get default router/factory addresses if not provided
        router_address = config.router_address
        factory_address = config.factory_address
        
        if not router_address or not factory_address:
            # Use defaults from config.yaml
            defaults = {}
            if config.exchange_name in defaults:
                router_address = router_address or defaults[config.exchange_name]['router']
                factory_address = factory_address or defaults[config.exchange_name]['factory']
        
        # Save DEX configuration to database
        success = keys_manager.save_dex_keys(
            exchange_name=config.exchange_name,
            private_key=config.private_key,
            wallet_address=config.wallet_address,
            rpc_url=rpc_url,
            router_address=router_address,
            factory_address=factory_address,
            chain=chain,
            enabled=config.enabled
        )
        
        if success:
            return {
                "status": "success", 
                "message": f"{config.exchange_name} DEX configured and saved to database"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save DEX configuration")
    
    except Exception as e:
        logger.error(f"Error updating DEX config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/trading")
async def get_trading_config():
    """Get trading configuration"""
    from ..config.settings import get_settings
    settings = get_settings()
    
    # Handle case where trading config might be None
    if settings.trading is None:
        # Return default values
        return {
            "min_profit_threshold": 0.001,
            "max_trade_size_percent": 10.0,
            "max_slippage_percent": 1.0,
                "order_timeout_seconds": 120,
            "paper_trading": settings.bot.paper_trading if settings.bot else False
        }
    
    return {
        "min_profit_threshold": settings.trading.min_profit_threshold,
        "max_trade_size_percent": settings.trading.max_trade_size_percent,
        "max_slippage_percent": settings.trading.max_slippage_percent,
        "order_timeout_seconds": settings.trading.order_timeout_seconds,
        "paper_trading": settings.bot.paper_trading if settings.bot else False
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
        
        # Update paper trading mode if provided
        if config.paper_trading is not None:
            settings.bot.paper_trading = config.paper_trading
            logger.info(f"Paper trading mode set to: {config.paper_trading}")
        
        # Save to config file
        try:
            import yaml
            from pathlib import Path
            config_path = Path("config/config.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # Update trading section
                if 'trading' not in config_data:
                    config_data['trading'] = {}
                config_data['trading']['min_profit_threshold'] = config.min_profit_threshold
                config_data['trading']['max_trade_size_percent'] = config.max_trade_size_percent
                config_data['trading']['max_slippage_percent'] = config.max_slippage_percent
                
                # Update bot section for paper_trading
                if 'bot' not in config_data:
                    config_data['bot'] = {}
                if config.paper_trading is not None:
                    config_data['bot']['paper_trading'] = config.paper_trading
                
                # Write back to file
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                logger.info("Trading configuration saved to config file")
            else:
                logger.warning(f"Config file not found at {config_path}, skipping save")
        except Exception as e:
            logger.warning(f"Could not save trading config to file: {e}")
        
        return {"status": "success", "message": "Trading config updated"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/trading/mode")
async def set_trading_mode(
    paper_trading: bool = Body(..., embed=True),
    username: str = Depends(verify_credentials)
):
    """Set paper trading mode (True) or live trading mode (False)"""
    try:
        from ..config.settings import get_settings
        
        settings = get_settings()
        
        old_mode = settings.bot.paper_trading
        settings.bot.paper_trading = paper_trading
        
        mode_name = "PAPER TRADING" if paper_trading else "LIVE TRADING"
        logger.warning(f"Trading mode changed from {'PAPER' if old_mode else 'LIVE'} to {mode_name}")
        
        await broadcast_message({
            "type": "alert",
            "level": "warning" if not paper_trading else "info",
            "message": f"Trading mode set to {mode_name}. Bot restart required for changes to take effect."
        })
        
        return {
            "status": "success",
            "message": f"Trading mode set to {mode_name}",
            "paper_trading": paper_trading,
            "requires_restart": True
        }
    except Exception as e:
        logger.error(f"Error setting trading mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/risk")
async def get_risk_config():
    """Get risk management configuration"""
    from ..config.settings import get_settings
    settings = get_settings()
    
    # Handle case where risk config might be None
    if settings.risk is None:
        # Return default values
        return {
            "max_drawdown_percent": 20.0,
            "max_daily_loss_percent": 5.0,
            "max_position_size_usd": 10000.0,
            "emergency_stop_enabled": True
        }
    
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
        
        # Save to config file
        try:
            import yaml
            from pathlib import Path
            config_path = Path("config/config.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # Update risk section
                if 'risk' not in config_data:
                    config_data['risk'] = {}
                config_data['risk']['max_drawdown_percent'] = config.max_drawdown_percent
                config_data['risk']['max_daily_loss_percent'] = config.max_daily_loss_percent
                config_data['risk']['max_position_size_usd'] = config.max_position_size_usd
                config_data['risk']['emergency_stop_enabled'] = config.emergency_stop_enabled
                
                # Write back to file
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                logger.info("Risk configuration saved to config file")
            else:
                logger.warning(f"Config file not found at {config_path}, skipping save")
        except Exception as e:
            logger.warning(f"Could not save risk config to file: {e}")
        
        return {"status": "success", "message": "Risk config updated"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Market Data Routes ====================

@app.get("/api/market/prices")
async def get_current_prices(all_pairs: bool = False):
    """
    Get current prices across all exchanges
    
    Args:
        all_pairs: If True, fetch prices for all available pairs from exchanges.
                   If False, only show configured trading pairs.
    """
    global bot
    
    if not bot:
        return {"error": "Bot not running. Please start the bot first.", "prices": {}}
    
    if not bot.exchanges:
        return {"error": "No exchanges connected. Please configure and connect exchanges.", "prices": {}}
    
    prices = {}
    
    if all_pairs:
        # Fetch prices for all available pairs from each exchange
        # Use batch fetching (fetch_tickers) for much better performance
        # Create a snapshot to avoid RuntimeError if dictionary changes during iteration
        exchanges_snapshot = list(bot.exchanges.items())
        for exchange_name, exchange in exchanges_snapshot:
            try:
                # For CEX exchanges using CCXT
                if hasattr(exchange, 'exchange') and hasattr(exchange.exchange, 'load_markets'):
                    markets = await exchange.exchange.load_markets()
                    
                    # Try to fetch all tickers at once (much faster than individual calls)
                    try:
                        all_tickers = await exchange.exchange.fetch_tickers()
                    except Exception as e:
                        logger.warning(f"Batch ticker fetch failed for {exchange_name}, falling back to individual: {e}")
                        all_tickers = {}
                    
                    # Filter to active spot markets and process
                    processed_count = 0
                    max_pairs_per_exchange = 1000  # Limit to avoid overwhelming response
                    
                    for symbol, market in markets.items():
                        if processed_count >= max_pairs_per_exchange:
                            break
                            
                        if not (market.get('active') and market.get('type') == 'spot'):
                            continue
                        
                        # Get ticker from batch fetch or fetch individually
                        ticker = all_tickers.get(symbol)
                        if not ticker:
                            # Fallback: fetch individual ticker if not in batch
                            try:
                                ticker = await exchange.get_ticker(symbol)
                            except Exception:
                                continue
                        
                        if ticker and ticker.get('bid') and ticker.get('ask'):
                            if symbol not in prices:
                                prices[symbol] = {}
                            prices[symbol][exchange_name] = {
                                "bid": ticker.get('bid'),
                                "ask": ticker.get('ask'),
                                "mid": (ticker.get('bid') + ticker.get('ask')) / 2,
                                "spread": ticker.get('ask') - ticker.get('bid'),
                                "timestamp": ticker.get('timestamp', datetime.now()).isoformat() if hasattr(ticker.get('timestamp'), 'isoformat') else datetime.now().isoformat()
                            }
                            processed_count += 1
                            
                # For DEX exchanges (like Galaswap), try to get available pairs
                elif exchange_name == 'galaswap':
                    # Galaswap uses a different API structure
                    # Try to get prices for configured trading pairs and common Gala Chain pairs
                    try:
                        # Collect symbols to fetch
                        symbols_to_fetch = set()
                        
                        # Get trading pairs from price monitor if available
                        if bot.price_monitor:
                            symbols_to_fetch.update(bot.price_monitor.trading_pairs)
                        
                        # Also try common Gala Chain pairs if we have balances
                        if hasattr(exchange, 'get_balance'):
                            try:
                                balances = await exchange.get_balance()
                                # Extract symbols from balances (GALA, GUSDT, GUSDC, GWETH, etc.)
                                for balance_symbol in balances.keys():
                                    # Try common pair combinations
                                    common_quotes = ['GUSDT', 'GUSDC', 'GALA', 'GWETH']
                                    for quote in common_quotes:
                                        if balance_symbol != quote:
                                            # Try both directions
                                            symbols_to_fetch.add(f"{balance_symbol}/{quote}")
                                            symbols_to_fetch.add(f"{quote}/{balance_symbol}")
                            except Exception as e:
                                logger.debug(f"Could not get balances for Galaswap pair discovery: {e}")
                        
                        # If no symbols found, try some default Gala Chain pairs
                        if not symbols_to_fetch:
                            default_pairs = ['GALA/GUSDT', 'GUSDT/GALA', 'GALA/GUSDC', 'GUSDC/GALA', 
                                           'GALA/GWETH', 'GWETH/GALA', 'GUSDT/GUSDC', 'GUSDC/GUSDT']
                            symbols_to_fetch.update(default_pairs)
                        
                        # Fetch prices for discovered symbols
                        processed_count = 0
                        max_pairs_per_exchange = 1000
                        for symbol in symbols_to_fetch:
                            if processed_count >= max_pairs_per_exchange:
                                break
                            try:
                                ticker = await exchange.get_ticker(symbol)
                                if ticker and ticker.get('bid') and ticker.get('ask'):
                                    if symbol not in prices:
                                        prices[symbol] = {}
                                    prices[symbol][exchange_name] = {
                                        "bid": ticker.get('bid'),
                                        "ask": ticker.get('ask'),
                                        "mid": (ticker.get('bid') + ticker.get('ask')) / 2,
                                        "spread": ticker.get('ask') - ticker.get('bid'),
                                        "timestamp": ticker.get('timestamp', datetime.now()).isoformat() if hasattr(ticker.get('timestamp'), 'isoformat') else datetime.now().isoformat()
                                    }
                                    processed_count += 1
                            except Exception as e:
                                logger.debug(f"Could not fetch {symbol} from {exchange_name}: {e}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error fetching Galaswap market data: {e}")
            except Exception as e:
                logger.error(f"Error fetching markets from {exchange_name}: {e}")
                continue
    else:
        # Original behavior: only configured trading pairs
        # First try to get from price monitor (fast, cached)
        if bot.price_monitor:
            for symbol in bot.price_monitor.trading_pairs:
                symbol_prices = bot.price_monitor.get_all_prices(symbol)
                if symbol_prices:  # Only add if we have data
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
        
        # Fallback: If price monitor has no data or missing exchanges, fetch directly from exchanges
        # This ensures data is shown even if price monitor hasn't started yet or is missing data
        if bot.exchanges:
            # Get trading pairs from config or price monitor
            trading_pairs = []
            if bot.price_monitor:
                trading_pairs = bot.price_monitor.trading_pairs
            else:
                # Fallback to config
                from ..config.settings import get_settings
                settings = get_settings()
                trading_pairs = [pair.symbol for pair in settings.get_enabled_trading_pairs()]
            
            # Fetch prices directly from exchanges for missing data
            exchanges_snapshot = list(bot.exchanges.items())
            for symbol in trading_pairs:
                if symbol not in prices:
                    prices[symbol] = {}
                
                # Check if we need to fetch for any exchange
                need_fallback = False
                if not prices[symbol]:  # No data at all for this symbol
                    need_fallback = True
                else:
                    # Check if we're missing data for any connected exchange
                    for exchange_name, exchange in exchanges_snapshot:
                        if exchange.is_connected and exchange_name not in prices[symbol]:
                            need_fallback = True
                            break
                
                if need_fallback:
                    for exchange_name, exchange in exchanges_snapshot:
                        if not exchange.is_connected:
                            continue
                        if exchange_name in prices[symbol] and prices[symbol][exchange_name]:
                            continue  # Already have data from price monitor
                        
                        try:
                            # Try to get ticker data
                            if hasattr(exchange, 'get_ticker'):
                                ticker = await exchange.get_ticker(symbol)
                                if ticker and ticker.get('bid') and ticker.get('ask'):
                                    prices[symbol][exchange_name] = {
                                        "bid": ticker.get('bid'),
                                        "ask": ticker.get('ask'),
                                        "mid": (ticker.get('bid') + ticker.get('ask')) / 2,
                                        "spread": ticker.get('ask') - ticker.get('bid'),
                                        "timestamp": ticker.get('timestamp', datetime.now()).isoformat() if hasattr(ticker.get('timestamp'), 'isoformat') else datetime.now().isoformat()
                                    }
                        except Exception as e:
                            error_msg = str(e)
                            # Don't log errors for invalid pairs - they're expected
                            # Also don't log for Galaswap API errors as they're common when pairs don't exist
                            if ('does not have market symbol' not in error_msg and 
                                'Invalid symbol' not in error_msg and
                                exchange_name != 'galaswap'):
                                logger.debug(f"Could not fetch {symbol} from {exchange_name} (fallback): {e}")
                            continue
    
    return prices


@app.get("/api/market/available-pairs")
async def get_available_pairs():
    """Get all available trading pairs from connected exchanges"""
    global bot
    
    if not bot or not bot.exchanges:
        return {"pairs": []}
    
    all_pairs = set()
    
    # Create a snapshot to avoid RuntimeError if dictionary changes during iteration
    exchanges_snapshot = list(bot.exchanges.items())
    for exchange_name, exchange in exchanges_snapshot:
        try:
            # For CEX exchanges using CCXT
            if hasattr(exchange, 'exchange') and hasattr(exchange.exchange, 'load_markets'):
                markets = await exchange.exchange.load_markets()
                # Get all active spot markets
                for symbol, market in markets.items():
                    if market.get('active') and market.get('type') == 'spot':
                        all_pairs.add(symbol)
        except Exception as e:
            logger.error(f"Error fetching available pairs from {exchange_name}: {e}")
            continue
    
    return {
        "pairs": sorted(list(all_pairs)),
        "count": len(all_pairs)
    }


@app.get("/api/market/opportunities")
async def get_opportunities(min_profit: Optional[float] = None, limit: int = 100):
    """
    Get recent arbitrage opportunities
    
    Args:
        min_profit: Optional minimum profit % filter (default: show all >= 0.01%)
        limit: Maximum number of opportunities to return
    """
    global bot
    
    if not bot or not bot.price_monitor:
        return {"opportunities": []}
    
    opportunities = bot.price_monitor.get_recent_opportunities(limit=limit * 2)  # Get more to filter
    
    # Filter by minimum profit if specified, otherwise show all
    if min_profit is not None:
        opportunities = [opp for opp in opportunities if opp.gross_profit_percent >= min_profit]
    
    # Sort by profit (highest first) and limit
    opportunities = sorted(opportunities, key=lambda x: x.gross_profit_percent, reverse=True)[:limit]
    
    return {
        "opportunities": [
            {
                "symbol": opp.symbol,
                "buy_exchange": opp.buy_exchange,
                "sell_exchange": opp.sell_exchange,
                "buy_price": opp.buy_price,
                "sell_price": opp.sell_price,
                "profit_percent": round(opp.gross_profit_percent, 4),  # Show 4 decimal places for small profits
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
        
        # Log if Galaswap is connected but has no balances
        if bot.exchanges.get('galaswap') and bot.exchanges['galaswap'].is_connected:
            galaswap_has_balance = any(
                'galaswap' in bal.balances_by_exchange 
                for bal in balances.values()
            )
            if not galaswap_has_balance:
                logger.debug("Galaswap is connected but no balances found. This may be normal if wallet is empty.")
        
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
        logger.error(f"Error getting balances: {e}", exc_info=True)
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


@app.post("/api/bot/trading/enable")
async def enable_trading(username: str = Depends(verify_credentials)):
    """Enable automatic trading"""
    global bot
    
    if not bot or not bot.risk_manager:
        raise HTTPException(status_code=400, detail="Bot not running")
    
    try:
        bot.risk_manager.enable_trading()
        logger.info("Trading enabled by user")
        
        await broadcast_message({
            "type": "alert",
            "level": "info",
            "message": "Automatic trading has been enabled"
        })
        
        return {"status": "success", "message": "Trading enabled", "trading_enabled": True}
    except Exception as e:
        logger.error(f"Error enabling trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/trading/disable")
async def disable_trading(username: str = Depends(verify_credentials)):
    """Disable automatic trading"""
    global bot
    
    if not bot or not bot.risk_manager:
        raise HTTPException(status_code=400, detail="Bot not running")
    
    try:
        bot.risk_manager.disable_trading("Disabled by user")
        logger.info("Trading disabled by user")
        
        await broadcast_message({
            "type": "alert",
            "level": "info",
            "message": "Automatic trading has been disabled"
        })
        
        return {"status": "success", "message": "Trading disabled", "trading_enabled": False}
    except Exception as e:
        logger.error(f"Error disabling trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    logger.debug(f"WebSocket client connected. Total connections: {len(websocket_connections)}")
    
    try:
        while True:
            try:
                # Send periodic updates
                if bot and bot.is_running:
                    # Send status update
                    try:
                        status = bot.get_status()
                        await websocket.send_json({
                            "type": "status_update",
                            "data": status,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as status_error:
                        # Bot status might fail if bot is initializing
                        logger.debug(f"Could not get bot status: {status_error}")
                        await websocket.send_json({
                            "type": "status_update",
                            "data": {"is_running": False},
                            "timestamp": datetime.now().isoformat()
                        })
                else:
                    # Bot not running - send empty status
                    await websocket.send_json({
                        "type": "status_update",
                        "data": {"is_running": False},
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as send_error:
                # Connection might be closed
                error_type = type(send_error).__name__
                error_msg = str(send_error)
                # Check if it's a connection error (expected when client disconnects)
                if 'connection' in error_msg.lower() or 'closed' in error_msg.lower() or 'disconnect' in error_type:
                    logger.debug(f"WebSocket client disconnected: {error_msg}")
                    break
                else:
                    logger.debug(f"WebSocket send error: {error_type}: {error_msg}")
                    # Try to continue, but if it keeps failing, break
                    await asyncio.sleep(1)
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected normally")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type}"
        # Only log unexpected errors, not normal disconnections
        if 'disconnect' not in error_type.lower() and 'connection' not in error_msg.lower():
            logger.debug(f"WebSocket error: {error_type}: {error_msg}")
    finally:
        # Clean up connection
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
            logger.debug(f"WebSocket client removed. Remaining connections: {len(websocket_connections)}")


async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    disconnected = []
    # Create a copy to avoid modification during iteration
    connections_copy = list(websocket_connections)
    
    for connection in connections_copy:
        try:
            await connection.send_json(message)
        except (WebSocketDisconnect, Exception) as e:
            # Client disconnected or error sending - remove it
            disconnected.append(connection)
            logger.debug(f"WebSocket broadcast failed for client: {type(e).__name__}")
    
    # Remove disconnected clients
    for conn in disconnected:
        if conn in websocket_connections:
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

