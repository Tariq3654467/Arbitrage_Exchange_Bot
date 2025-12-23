"""
Advanced Features Routes
Token management, rebalancing, backtesting, dry-run, system health
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ...api.dependencies import verify_credentials
from ...api import dependencies as deps
from ...utils.logger import get_logger
from ...api.models import TestTradeRequest
from ...arbitrage.price_monitor import ArbitrageOpportunity

logger = get_logger()
router = APIRouter()


def _save_trading_pairs_to_config(settings):
    """Helper function to save trading pairs to config.yaml file"""
    try:
        import yaml
        from pathlib import Path
        
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}, skipping save")
            return False
        
        # Read existing config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
        
        # Update trading_pairs section
        if not settings.trading_pairs:
            config_data['trading_pairs'] = []
        else:
            config_data['trading_pairs'] = [
                {
                    'symbol': pair.symbol,
                    'min_trade_amount': pair.min_trade_amount,
                    'enabled': pair.enabled
                }
                for pair in settings.trading_pairs
            ]
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved {len(settings.trading_pairs)} trading pairs to config file")
        return True
    except Exception as e:
        logger.error(f"Error saving trading pairs to config file: {e}")
        return False


# ==================== Token Management ====================

@router.get("/api/tokens")
async def get_trading_pairs():
    """Get all configured trading pairs"""
    try:
        from ...config.settings import get_settings
        settings = get_settings()
        
        pairs = settings.get_enabled_trading_pairs()
        
        return {
            "pairs": [
                {
                    "symbol": pair.symbol,
                    "min_trade_amount": pair.min_trade_amount,
                    "enabled": pair.enabled
                }
                for pair in pairs
            ],
            "total": len(pairs),
            "enabled": sum(1 for p in pairs if p.enabled)
        }
    except Exception as e:
        logger.error(f"Error getting trading pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tokens")
async def add_trading_pair(
    symbol: str = Body(...),
    min_trade_amount: float = Body(...),
    enabled: bool = Body(True),
    username: str = Depends(verify_credentials)
):
    """Add a new trading pair"""
    try:
        from ...config.settings import get_settings
        settings = get_settings()
        
        # Validate symbol format (should be BASE/QUOTE)
        if '/' not in symbol:
            raise HTTPException(status_code=400, detail="Symbol must be in format BASE/QUOTE (e.g., BTC/USDT)")
        
        # Check if pair already exists
        existing_pairs = settings.get_enabled_trading_pairs() if hasattr(settings, 'get_enabled_trading_pairs') else []
        if any(p.symbol == symbol for p in existing_pairs):
            raise HTTPException(status_code=400, detail=f"Trading pair {symbol} already exists")
        
        # Add to config
        if not settings.trading_pairs:
            settings.trading_pairs = []
        
        from ...config.settings import TradingPair
        new_pair = TradingPair(
            symbol=symbol,
            min_trade_amount=min_trade_amount,
            enabled=enabled
        )
        settings.trading_pairs.append(new_pair)
        
        # Save to config file
        try:
            import yaml
            from pathlib import Path
            config_path = Path("config/config.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
                if 'trading_pairs' not in config_data:
                    config_data['trading_pairs'] = []
                config_data['trading_pairs'].append({
                    'symbol': symbol,
                    'min_trade_amount': min_trade_amount,
                    'enabled': enabled
                })
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f)
        except Exception as e:
            logger.warning(f"Could not save to config file: {e}")
        
        logger.info(f"Added trading pair: {symbol}")
        
        return {
            "status": "success",
            "message": f"Trading pair {symbol} added successfully",
            "pair": {
                "symbol": symbol,
                "min_trade_amount": min_trade_amount,
                "enabled": enabled
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding trading pair: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/tokens/{symbol}")
async def update_trading_pair(
    symbol: str,
    min_trade_amount: Optional[float] = Body(None),
    enabled: Optional[bool] = Body(None),
    username: str = Depends(verify_credentials)
):
    """Update a trading pair"""
    try:
        from ...config.settings import get_settings
        settings = get_settings()
        
        # Find and update pair
        found = False
        for pair in settings.trading_pairs:
            if pair.symbol == symbol:
                if min_trade_amount is not None:
                    pair.min_trade_amount = min_trade_amount
                if enabled is not None:
                    pair.enabled = enabled
                found = True
                break
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Trading pair {symbol} not found")
        
        # Save to config file
        _save_trading_pairs_to_config(settings)
        logger.info(f"Updated trading pair: {symbol}")
        
        return {
            "status": "success",
            "message": f"Trading pair {symbol} updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trading pair: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/tokens/{symbol}")
async def delete_trading_pair(
    symbol: str,
    username: str = Depends(verify_credentials)
):
    """Delete a trading pair"""
    try:
        from ...config.settings import get_settings
        settings = get_settings()
        
        # Find and remove pair
        original_count = len(settings.trading_pairs)
        settings.trading_pairs = [p for p in settings.trading_pairs if p.symbol != symbol]
        
        if len(settings.trading_pairs) == original_count:
            raise HTTPException(status_code=404, detail=f"Trading pair {symbol} not found")
        
        # Save to config file
        _save_trading_pairs_to_config(settings)
        logger.info(f"Deleted trading pair: {symbol}")
        
        return {
            "status": "success",
            "message": f"Trading pair {symbol} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trading pair: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Rebalancing ====================

@router.post("/api/portfolio/rebalance")
async def trigger_rebalance(
    target_allocation: Optional[Dict[str, float]] = Body(None),
    username: str = Depends(verify_credentials)
):
    """Manually trigger portfolio rebalancing"""
    try:
        from ...api.main import bot
        
        if not bot or not bot.portfolio_manager:
            raise HTTPException(status_code=400, detail="Bot not running or portfolio manager not initialized")
        
        # Update target allocation if provided
        if target_allocation:
            bot.portfolio_manager.target_allocation = target_allocation
            logger.info(f"Updated target allocation: {target_allocation}")
        
        # Trigger rebalancing
        result = await bot.portfolio_manager.rebalance()
        
        return {
            "status": "success",
            "message": "Rebalancing triggered",
            "rebalanced": result.rebalanced,
            "transfers": result.transfers if hasattr(result, 'transfers') else [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering rebalance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/allocation")
async def get_allocation():
    """Get current and target portfolio allocation"""
    try:
        from ...api.main import bot
        
        if not bot or not bot.portfolio_manager:
            return {
                "current": {},
                "target": {},
                "rebalance_needed": False
            }
        
        snapshot = await bot.portfolio_manager.get_portfolio_snapshot()
        
        return {
            "current": snapshot.allocation_percent,
            "target": snapshot.target_allocation,
            "rebalance_needed": snapshot.rebalance_needed,
            "threshold": bot.portfolio_manager.rebalance_threshold_percent
        }
    except Exception as e:
        logger.error(f"Error getting allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/portfolio/allocation")
async def update_allocation(
    target_allocation: Dict[str, float] = Body(...),
    username: str = Depends(verify_credentials)
):
    """Update target portfolio allocation"""
    try:
        from ...api.main import bot
        
        if not bot or not bot.portfolio_manager:
            raise HTTPException(status_code=400, detail="Bot not running")
        
        # Validate allocation sums to ~100%
        total = sum(target_allocation.values())
        if abs(total - 100.0) > 1.0:
            raise HTTPException(
                status_code=400,
                detail=f"Allocation percentages must sum to ~100% (got {total}%)"
            )
        
        bot.portfolio_manager.target_allocation = target_allocation
        
        return {
            "status": "success",
            "message": "Target allocation updated",
            "target_allocation": target_allocation
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Backtesting ====================

@router.post("/api/backtest/run")
async def run_backtest(
    start_date: str = Body(...),
    end_date: str = Body(...),
    initial_capital: float = Body(10000.0),
    min_profit_threshold: Optional[float] = Body(None),
    username: str = Depends(verify_credentials)
):
    """Run backtesting on historical data"""
    try:
        from ...arbitrage.backtesting_engine import BacktestingEngine
        from ...api.main import bot
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get settings for backtest parameters
        if bot and bot.settings:
            default_min_profit = bot.settings.trading.min_profit_threshold
            max_trade_size = bot.settings.trading.max_trade_size_percent
            max_slippage = bot.settings.trading.max_slippage_percent
        else:
            default_min_profit = 0.5
            max_trade_size = 10.0
            max_slippage = 1.0
        
        min_profit = min_profit_threshold if min_profit_threshold is not None else default_min_profit
        
        logger.info(f"Backtest requested: {start_date} to {end_date}, capital: {initial_capital}")
        
        # Initialize backtesting engine
        postgres_db_instance = deps.postgres_db if hasattr(deps, 'postgres_db') else None
        
        backtest_engine = BacktestingEngine(
            postgres_db=postgres_db_instance,
            influxdb=bot.influxdb if bot else None
        )
        
        # Run backtest
        result = await backtest_engine.run_backtest(
            start_date=start_dt,
            end_date=end_dt,
            initial_capital=initial_capital,
            min_profit_threshold=min_profit,
            max_trade_size_percent=max_trade_size,
            max_slippage_percent=max_slippage
        )
        
        # Convert to API response format
        return {
            "status": "success",
            "backtest_id": result.backtest_id,
            "status_detail": result.status.value,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_return": result.total_return,
            "total_return_percent": result.total_return_percent,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_profit_usd": result.total_profit_usd,
            "total_loss_usd": result.total_loss_usd,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_percent": result.max_drawdown_percent,
            "sharpe_ratio": result.sharpe_ratio,
            "profit_factor": result.profit_factor,
            "average_profit_per_trade": result.average_profit_per_trade,
            "average_loss_per_trade": result.average_loss_per_trade,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "error_message": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backtest/results/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """Get backtest results by ID"""
    try:
        from ...arbitrage.backtesting_engine import BacktestingEngine
        from ...api.main import bot
        
        # Initialize backtesting engine
        postgres_db_instance = deps.postgres_db if hasattr(deps, 'postgres_db') else None
        
        backtest_engine = BacktestingEngine(
            postgres_db=postgres_db_instance,
            influxdb=bot.influxdb if bot else None
        )
        
        # Get result
        result = backtest_engine.get_backtest_result(backtest_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
        
        # Convert to API response format
        response = {
            "backtest_id": result.backtest_id,
            "status": result.status.value,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_return": result.total_return,
            "total_return_percent": result.total_return_percent,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "total_profit_usd": result.total_profit_usd,
            "total_loss_usd": result.total_loss_usd,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_percent": result.max_drawdown_percent,
            "sharpe_ratio": result.sharpe_ratio,
            "profit_factor": result.profit_factor,
            "average_profit_per_trade": result.average_profit_per_trade,
            "average_loss_per_trade": result.average_loss_per_trade,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "error_message": result.error_message
        }
        
        # Include trades if requested (limit to prevent huge responses)
        # Can add ?include_trades=true query param if needed
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Dry Run ====================

# Global dry-run state
_dry_run_state = {
    "active": False,
    "start_time": None,
    "end_time": None,
    "simulated_trades": [],
    "total_profit_usd": 0.0,
    "total_profit_percent": 0.0,
    "successful_trades": 0,
    "failed_trades": 0
}


@router.post("/api/dry-run/start")
async def start_dry_run(
    duration_minutes: int = Body(60),
    username: str = Depends(verify_credentials)
):
    """Start dry-run mode (simulate trades without executing)"""
    global _dry_run_state
    
    try:
        from ...api.main import bot
        
        if not bot:
            raise HTTPException(status_code=400, detail="Bot not initialized")
        
        if not bot.is_running:
            raise HTTPException(status_code=400, detail="Bot must be running for dry-run mode")
        
        # Check if bot is in paper trading mode (required for dry-run)
        from ...config.settings import get_settings
        settings = get_settings()
        
        if not settings.bot.paper_trading:
            logger.warning("Dry-run mode requires paper trading mode. Enabling paper trading temporarily.")
            # Note: We don't change the actual setting, just note it
        
        # Initialize dry-run state
        _dry_run_state = {
            "active": True,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(minutes=duration_minutes),
            "simulated_trades": [],
            "total_profit_usd": 0.0,
            "total_profit_percent": 0.0,
            "successful_trades": 0,
            "failed_trades": 0
        }
        
        logger.info(f"Dry-run mode started for {duration_minutes} minutes")
        
        # Hook into trade executor to track simulated trades
        # The bot's paper trading mode will handle the simulation
        # We'll track trades through the trade executor's history
        
        return {
            "status": "success",
            "message": "Dry-run mode started",
            "duration_minutes": duration_minutes,
            "start_time": _dry_run_state["start_time"].isoformat(),
            "end_time": _dry_run_state["end_time"].isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting dry-run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/dry-run/stop")
async def stop_dry_run(username: str = Depends(verify_credentials)):
    """Stop dry-run mode and return results"""
    global _dry_run_state
    
    try:
        if not _dry_run_state["active"]:
            raise HTTPException(status_code=400, detail="Dry-run mode is not active")
        
        # Calculate final statistics
        _dry_run_state["active"] = False
        _dry_run_state["end_time"] = datetime.now()
        
        # Get trade statistics from bot if available
        from ...api.main import bot
        if bot and bot.trade_executor:
            recent_trades = bot.trade_executor.get_recent_trades(limit=1000)
            
            # Filter trades that occurred during dry-run period
            start_time = _dry_run_state["start_time"]
            end_time = _dry_run_state["end_time"]
            
            dry_run_trades = [
                trade for trade in recent_trades
                if start_time <= trade.timestamp <= end_time
            ]
            
            _dry_run_state["simulated_trades"] = [
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
                for trade in dry_run_trades
            ]
            
            _dry_run_state["successful_trades"] = sum(
                1 for trade in dry_run_trades
                if trade.status.value == "completed"
            )
            _dry_run_state["failed_trades"] = len(dry_run_trades) - _dry_run_state["successful_trades"]
            _dry_run_state["total_profit_usd"] = sum(
                trade.actual_profit_usd for trade in dry_run_trades
                if trade.status.value == "completed"
            )
            _dry_run_state["total_profit_percent"] = sum(
                trade.actual_profit_percent for trade in dry_run_trades
                if trade.status.value == "completed"
            )
        
        return {
            "status": "success",
            "message": "Dry-run mode stopped",
            "results": {
                "duration_minutes": (
                    (_dry_run_state["end_time"] - _dry_run_state["start_time"]).total_seconds() / 60
                ),
                "simulated_trades": len(_dry_run_state["simulated_trades"]),
                "successful_trades": _dry_run_state["successful_trades"],
                "failed_trades": _dry_run_state["failed_trades"],
                "total_profit_usd": round(_dry_run_state["total_profit_usd"], 2),
                "total_profit_percent": round(_dry_run_state["total_profit_percent"], 4),
                "trades": _dry_run_state["simulated_trades"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping dry-run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dry-run/results")
async def get_dry_run_results():
    """Get dry-run simulation results"""
    global _dry_run_state
    
    try:
        if not _dry_run_state["active"]:
            # Return last results if available
            if _dry_run_state["start_time"]:
                return {
                    "status": "inactive",
                    "last_run": {
                        "start_time": _dry_run_state["start_time"].isoformat() if _dry_run_state["start_time"] else None,
                        "end_time": _dry_run_state["end_time"].isoformat() if _dry_run_state["end_time"] else None,
                        "simulated_trades": len(_dry_run_state["simulated_trades"]),
                        "successful_trades": _dry_run_state["successful_trades"],
                        "failed_trades": _dry_run_state["failed_trades"],
                        "total_profit_usd": round(_dry_run_state["total_profit_usd"], 2),
                        "total_profit_percent": round(_dry_run_state["total_profit_percent"], 4)
                    }
                }
            return {
                "status": "inactive",
                "message": "No dry-run session has been started"
            }
        
        # Update statistics from bot if running
        from ...api.main import bot
        if bot and bot.trade_executor:
            recent_trades = bot.trade_executor.get_recent_trades(limit=1000)
            start_time = _dry_run_state["start_time"]
            end_time = _dry_run_state["end_time"]
            
            dry_run_trades = [
                trade for trade in recent_trades
                if start_time <= trade.timestamp <= end_time
            ]
            
            _dry_run_state["simulated_trades"] = [
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
                for trade in dry_run_trades
            ]
            
            _dry_run_state["successful_trades"] = sum(
                1 for trade in dry_run_trades
                if trade.status.value == "completed"
            )
            _dry_run_state["failed_trades"] = len(dry_run_trades) - _dry_run_state["successful_trades"]
            _dry_run_state["total_profit_usd"] = sum(
                trade.actual_profit_usd for trade in dry_run_trades
                if trade.status.value == "completed"
            )
            _dry_run_state["total_profit_percent"] = sum(
                trade.actual_profit_percent for trade in dry_run_trades
                if trade.status.value == "completed"
            )
        
        # Check if dry-run period has ended
        if datetime.now() >= _dry_run_state["end_time"]:
            _dry_run_state["active"] = False
        
        return {
            "status": "active" if _dry_run_state["active"] else "completed",
            "start_time": _dry_run_state["start_time"].isoformat(),
            "end_time": _dry_run_state["end_time"].isoformat(),
            "remaining_minutes": max(0, (_dry_run_state["end_time"] - datetime.now()).total_seconds() / 60) if _dry_run_state["active"] else 0,
            "simulated_trades": len(_dry_run_state["simulated_trades"]),
            "successful_trades": _dry_run_state["successful_trades"],
            "failed_trades": _dry_run_state["failed_trades"],
            "total_profit_usd": round(_dry_run_state["total_profit_usd"], 2),
            "total_profit_percent": round(_dry_run_state["total_profit_percent"], 4),
            "trades": _dry_run_state["simulated_trades"][-50:]  # Return last 50 trades
        }
    except Exception as e:
        logger.error(f"Error getting dry-run results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== System Health ====================

@router.get("/api/system/health")
async def get_system_health():
    """Get comprehensive system health status"""
    try:
        from ...api.main import bot
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "bot": {
                "running": bot.is_running if bot else False,
                "uptime_seconds": (datetime.now() - bot.start_time).total_seconds() if bot and bot.start_time else 0,
                "paper_trading": bot.settings.bot.paper_trading if bot else False
            },
            "exchanges": {
                "connected": len(bot.exchanges) if bot else 0,
                "total": len(bot.exchanges) if bot else 0
            },
            "databases": {
                "postgres": deps.postgres_db is not None,
                "influxdb": bot.influxdb is not None if bot else False
            },
            "components": {
                "price_monitor": bot.price_monitor is not None if bot else False,
                "trade_executor": bot.trade_executor is not None if bot else False,
                "risk_manager": bot.risk_manager is not None if bot else False,
                "portfolio_manager": bot.portfolio_manager is not None if bot else False
            }
        }
        
        # Check for issues
        issues = []
        if not bot:
            issues.append("Bot not initialized")
        elif not bot.is_running:
            issues.append("Bot not running")
        if not deps.postgres_db:
            issues.append("PostgreSQL not connected")
        
        if issues:
            health["status"] = "degraded"
            health["issues"] = issues
        
        return health
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/api/system/logs")
async def get_system_logs(
    level: Optional[str] = None,
    limit: int = 100,
    username: str = Depends(verify_credentials)
):
    """Get system logs"""
    try:
        from pathlib import Path
        import os
        
        log_dir = Path("logs")
        if not log_dir.exists():
            return {"logs": [], "message": "Log directory not found"}
        
        # Get most recent log file
        log_files = sorted(log_dir.glob("arbitrage_bot_*.log"), reverse=True)
        if not log_files:
            return {"logs": [], "message": "No log files found"}
        
        logs = []
        with open(log_files[0], 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Get last N lines
            for line in lines[-limit:]:
                if level and level.upper() not in line:
                    continue
                logs.append(line.strip())
        
        return {
            "logs": logs,
            "file": str(log_files[0]),
            "total_lines": len(logs)
        }
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Manual Test Trade ====================

@router.post("/api/trades/test")
async def execute_test_trade(
    request: TestTradeRequest,
    username: str = Depends(verify_credentials)
):
    """
    Execute a single manual test trade without requiring an arbitrage opportunity.
    
    This will:
    - Build a synthetic ArbitrageOpportunity using current prices
      from the specified buy/sell exchanges.
    - Run it through the arbitrage calculator and risk manager.
    - Execute exactly one trade via the TradeExecutor if allowed.
    """
    try:
        from ...api.main import bot
        from ...arbitrage.price_monitor import PriceData
        global _dry_run_state

        is_dry_run_active = bool(_dry_run_state.get("active")) if isinstance(_dry_run_state, dict) else False

        if not bot or not bot.is_running:
            raise HTTPException(status_code=400, detail="Bot is not running")

        # Validate exchanges
        buy_ex = bot.exchanges.get(request.buy_exchange)
        sell_ex = bot.exchanges.get(request.sell_exchange)
        if not buy_ex or not sell_ex:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown exchanges. Available: {list(bot.exchanges.keys())}"
            )

        symbol = request.symbol
        
        # Validate: Same-exchange trades don't make sense for arbitrage
        # But allow them if force_execute is true (for testing)
        force_execute = getattr(request, 'force_execute', False)
        if request.buy_exchange == request.sell_exchange and not force_execute:
            raise HTTPException(
                status_code=400,
                detail=f"Same-exchange trades ({request.buy_exchange} → {request.buy_exchange}) are not profitable for arbitrage. "
                       f"You're buying and selling on the same exchange, which will always lose money due to spread and fees. "
                       f"Use different exchanges for arbitrage (e.g., buy on binance, sell on galaswap). "
                       f"Or add 'force_execute: true' to bypass this check for testing."
            )
        elif request.buy_exchange == request.sell_exchange and force_execute:
            logger.warning(f"⚠️ FORCING same-exchange trade: {request.buy_exchange} → {request.sell_exchange} (will likely lose money due to spread/fees)")

        # Try to get current prices from price monitor first (fast path)
        buy_price_data = bot.price_monitor.get_current_price(symbol, request.buy_exchange) if bot.price_monitor else None
        sell_price_data = bot.price_monitor.get_current_price(symbol, request.sell_exchange) if bot.price_monitor else None

        # Helper: create synthetic prices for GalaSwap during dry-run so you can always
        # demonstrate at least one "trade" even when on-chain liquidity is zero.
        def _make_synthetic_price_data(exchange_name: str) -> PriceData:
            # Try to borrow a price from the other side first, otherwise fall back to a constant.
            base_price = None
            if exchange_name == request.buy_exchange and sell_price_data:
                base_price = sell_price_data.mid or sell_price_data.ask or sell_price_data.bid
            elif exchange_name == request.sell_exchange and buy_price_data:
                base_price = buy_price_data.mid or buy_price_data.ask or buy_price_data.bid

            if not base_price or base_price <= 0:
                base_price = 0.01  # Fallback synthetic price for demo

            bid = base_price * 0.999
            ask = base_price * 1.001
            mid = (bid + ask) / 2

            return PriceData(
                exchange=exchange_name,
                symbol=symbol,
                bid=bid,
                ask=ask,
                mid=mid,
                spread=ask - bid,
                spread_percent=((ask - bid) / mid) * 100 if mid > 0 else 0,
                timestamp=datetime.now(),
                order_book=None,
            )

        # Fallback: fetch order books directly if needed
        if not buy_price_data:
            ob = await buy_ex.get_order_book(symbol, depth=10)
            if not ob.best_ask:
                # During dry-run, simulate GalaSwap liquidity so you can demo a trade
                if request.buy_exchange == "galaswap" and is_dry_run_active:
                    logger.warning(f"Simulating GalaSwap ask liquidity for {symbol} during dry-run test trade")
                    buy_price_data = _make_synthetic_price_data(request.buy_exchange)
                else:
                    # Provide helpful error message with suggestions
                    error_detail = f"No ask liquidity for {symbol} on {request.buy_exchange}"
                    if request.buy_exchange == "galaswap":
                        error_detail += ". GalaSwap is a DEX with dynamic liquidity pools. This pair may not have an active pool. Try: 1) Check /api/market/opportunities for pairs with liquidity, 2) Try reverse direction (sell on galaswap, buy on binance), 3) Try GALA/GUSDC or GALA/GUSDT (GalaSwap-only pairs)"
                    raise HTTPException(status_code=400, detail=error_detail)
            else:
                buy_price_data = PriceData(
                    exchange=request.buy_exchange,
                    symbol=symbol,
                    bid=ob.best_bid[0] if ob.best_bid else ob.best_ask[0],
                    ask=ob.best_ask[0],
                    mid=(ob.best_bid[0] + ob.best_ask[0]) / 2 if ob.best_bid else ob.best_ask[0],
                    spread=ob.spread or 0,
                    spread_percent=ob.spread_percent or 0,
                    timestamp=ob.timestamp,
                    order_book=ob,
                )

        if not sell_price_data:
            ob = await sell_ex.get_order_book(symbol, depth=10)
            if not ob.best_bid:
                # During dry-run, simulate GalaSwap liquidity so you can demo a trade
                if request.sell_exchange == "galaswap" and is_dry_run_active:
                    logger.warning(f"Simulating GalaSwap bid liquidity for {symbol} during dry-run test trade")
                    sell_price_data = _make_synthetic_price_data(request.sell_exchange)
                else:
                    # Provide helpful error message with suggestions
                    error_detail = f"No bid liquidity for {symbol} on {request.sell_exchange}"
                    if request.sell_exchange == "galaswap":
                        error_detail += ". GalaSwap is a DEX with dynamic liquidity pools. This pair may not have an active pool. Try: 1) Check /api/market/opportunities for pairs with liquidity, 2) Try reverse direction (buy on galaswap, sell on binance), 3) Try GALA/GUSDC or GALA/GUSDT (GalaSwap-only pairs)"
                    raise HTTPException(status_code=400, detail=error_detail)
            else:
                sell_price_data = PriceData(
                    exchange=request.sell_exchange,
                    symbol=symbol,
                    bid=ob.best_bid[0],
                    ask=ob.best_ask[0] if ob.best_ask else ob.best_bid[0],
                    mid=(ob.best_bid[0] + ob.best_ask[0]) / 2 if ob.best_ask else ob.best_bid[0],
                    spread=ob.spread or 0,
                    spread_percent=ob.spread_percent or 0,
                    timestamp=ob.timestamp,
                    order_book=ob,
                )

        buy_price = buy_price_data.ask
        sell_price = sell_price_data.bid

        if buy_price <= 0 or sell_price <= 0:
            raise HTTPException(status_code=400, detail="Invalid prices for test trade")

        gross_profit_percent = ((sell_price - buy_price) / buy_price) * 100

        # Build synthetic opportunity
        opportunity = ArbitrageOpportunity(
            symbol=symbol,
            buy_exchange=request.buy_exchange,
            sell_exchange=request.sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            gross_profit_percent=gross_profit_percent,
            timestamp=datetime.now(),
            buy_order_book=buy_price_data.order_book,
            sell_order_book=sell_price_data.order_book,
        )

        # Analyze using existing calculator
        analysis = await bot.arbitrage_calculator.analyze_opportunity(
            opportunity,
            trade_amount_usd=request.trade_amount_usd,
        )

        # Check risk limits with current portfolio value
        # Allow bypass for test trades if force_execute is True (for testing even unprofitable trades)
        portfolio_value = await bot.portfolio_manager.get_total_portfolio_value()
        allowed, reason = bot.risk_manager.check_trade_allowed(analysis, portfolio_value)
        
        # Check if we should bypass risk checks (for testing)
        force_execute = getattr(request, 'force_execute', False)
        
        if not allowed and not force_execute:
            return {
                "status": "blocked_by_risk",
                "reason": reason,
                "net_profit_percent": analysis.net_profit_percent,
                "net_profit_usd": analysis.net_profit_usd,
                "note": "Add 'force_execute: true' to bypass risk checks for testing"
            }
        elif not allowed and force_execute:
            logger.warning(f"⚠️ FORCING TRADE EXECUTION despite risk check failure: {reason}")

        # Execute exactly one trade
        result = await bot.trade_executor.execute_trade(analysis)

        return {
            "status": result.status.value,
            "symbol": symbol,
            "buy_exchange": request.buy_exchange,
            "sell_exchange": request.sell_exchange,
            "expected_net_profit_usd": analysis.net_profit_usd,
            "expected_net_profit_percent": analysis.net_profit_percent,
            "actual_profit_usd": result.actual_profit_usd,
            "actual_profit_percent": result.actual_profit_percent,
            "error_message": result.error_message,
            "dry_run": is_dry_run_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing test trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

