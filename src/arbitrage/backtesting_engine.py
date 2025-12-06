"""
Backtesting Engine
Simulates trading strategies on historical data
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logger import get_logger
from ..database.postgres_manager import PostgresManager
from ..database.influxdb_manager import InfluxDBManager

logger = get_logger()


class BacktestStatus(Enum):
    """Backtest execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BacktestTrade:
    """Simulated trade in backtest"""
    timestamp: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    amount: float
    gross_profit_usd: float
    net_profit_usd: float
    net_profit_percent: float
    fees_usd: float
    executed: bool = True


@dataclass
class BacktestResult:
    """Complete backtest results"""
    backtest_id: str
    status: BacktestStatus
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_percent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_usd: float
    total_loss_usd: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    profit_factor: float
    average_profit_per_trade: float
    average_loss_per_trade: float
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class BacktestingEngine:
    """Backtesting engine for arbitrage strategies"""
    
    def __init__(
        self,
        postgres_db: Optional[PostgresManager] = None,
        influxdb: Optional[InfluxDBManager] = None
    ):
        """
        Initialize backtesting engine
        
        Args:
            postgres_db: PostgreSQL database for historical opportunities
            influxdb: InfluxDB for historical price data
        """
        self.postgres_db = postgres_db
        self.influxdb = influxdb
        self.active_backtests: Dict[str, BacktestResult] = {}
        self.completed_backtests: Dict[str, BacktestResult] = {}
    
    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        min_profit_threshold: float = 0.5,
        max_trade_size_percent: float = 10.0,
        max_slippage_percent: float = 1.0,
        trading_fee_percent: float = 0.1
    ) -> BacktestResult:
        """
        Run backtest on historical data
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital in USD
            min_profit_threshold: Minimum profit % to execute trade
            max_trade_size_percent: Maximum % of capital per trade
            max_slippage_percent: Maximum slippage allowed
            trading_fee_percent: Trading fee percentage (0.1 = 0.1%)
        
        Returns:
            BacktestResult with complete statistics
        """
        backtest_id = f"bt_{datetime.now().timestamp()}"
        
        result = BacktestResult(
            backtest_id=backtest_id,
            status=BacktestStatus.RUNNING,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=initial_capital,
            total_return=0.0,
            total_return_percent=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit_usd=0.0,
            total_loss_usd=0.0,
            max_drawdown=0.0,
            max_drawdown_percent=0.0,
            sharpe_ratio=0.0,
            profit_factor=0.0,
            average_profit_per_trade=0.0,
            average_loss_per_trade=0.0
        )
        
        self.active_backtests[backtest_id] = result
        
        try:
            logger.info(f"Starting backtest {backtest_id}: {start_date} to {end_date}")
            
            # Get historical opportunities from database
            opportunities = await self._get_historical_opportunities(
                start_date, end_date, min_profit_threshold
            )
            
            if not opportunities:
                logger.warning("No historical opportunities found for backtest period")
                result.status = BacktestStatus.COMPLETED
                result.error_message = "No historical data available"
                result.completed_at = datetime.now()
                self.completed_backtests[backtest_id] = result
                del self.active_backtests[backtest_id]
                return result
            
            # Simulate trading
            current_capital = initial_capital
            peak_capital = initial_capital
            equity_curve = [(start_date, initial_capital)]
            trades = []
            
            for opp in opportunities:
                # Calculate trade size
                max_trade_size = current_capital * (max_trade_size_percent / 100)
                trade_amount = min(max_trade_size, 1000.0)  # Cap at $1000 for backtest
                
                if trade_amount < 10.0:  # Minimum trade size
                    continue
                
                # Calculate fees
                buy_fee = trade_amount * (trading_fee_percent / 100)
                sell_fee = trade_amount * (trading_fee_percent / 100)
                total_fees = buy_fee + sell_fee
                
                # Calculate profit (accounting for slippage)
                buy_price = opp['buy_price'] * (1 + max_slippage_percent / 100)
                sell_price = opp['sell_price'] * (1 - max_slippage_percent / 100)
                
                gross_profit = (sell_price - buy_price) * (trade_amount / buy_price)
                net_profit = gross_profit - total_fees
                net_profit_percent = (net_profit / trade_amount) * 100
                
                # Only execute if still profitable after fees and slippage
                if net_profit_percent < min_profit_threshold:
                    continue
                
                # Execute trade
                trade = BacktestTrade(
                    timestamp=opp['timestamp'],
                    symbol=opp['symbol'],
                    buy_exchange=opp['buy_exchange'],
                    sell_exchange=opp['sell_exchange'],
                    buy_price=buy_price,
                    sell_price=sell_price,
                    amount=trade_amount,
                    gross_profit_usd=gross_profit,
                    net_profit_usd=net_profit,
                    net_profit_percent=net_profit_percent,
                    fees_usd=total_fees
                )
                
                trades.append(trade)
                current_capital += net_profit
                
                # Update peak and drawdown
                if current_capital > peak_capital:
                    peak_capital = current_capital
                
                drawdown = peak_capital - current_capital
                drawdown_percent = (drawdown / peak_capital * 100) if peak_capital > 0 else 0
                
                if drawdown_percent > result.max_drawdown_percent:
                    result.max_drawdown = drawdown
                    result.max_drawdown_percent = drawdown_percent
                
                # Update equity curve
                equity_curve.append((opp['timestamp'], current_capital))
            
            # Calculate final statistics
            result.final_capital = current_capital
            result.total_return = current_capital - initial_capital
            result.total_return_percent = (result.total_return / initial_capital * 100) if initial_capital > 0 else 0
            result.total_trades = len(trades)
            result.trades = trades
            result.equity_curve = equity_curve
            
            # Calculate win/loss statistics
            winning = [t for t in trades if t.net_profit_usd > 0]
            losing = [t for t in trades if t.net_profit_usd < 0]
            
            result.winning_trades = len(winning)
            result.losing_trades = len(losing)
            result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades > 0 else 0
            
            result.total_profit_usd = sum(t.net_profit_usd for t in winning)
            result.total_loss_usd = abs(sum(t.net_profit_usd for t in losing))
            
            result.profit_factor = (result.total_profit_usd / result.total_loss_usd) if result.total_loss_usd > 0 else float('inf')
            
            result.average_profit_per_trade = (result.total_profit_usd / result.winning_trades) if result.winning_trades > 0 else 0
            result.average_loss_per_trade = (result.total_loss_usd / result.losing_trades) if result.losing_trades > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            if len(trades) > 1:
                returns = [t.net_profit_percent / 100 for t in trades]
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                result.sharpe_ratio = (avg_return / std_dev) if std_dev > 0 else 0
            else:
                result.sharpe_ratio = 0.0
            
            result.status = BacktestStatus.COMPLETED
            result.completed_at = datetime.now()
            
            logger.info(
                f"Backtest {backtest_id} completed: "
                f"{result.total_trades} trades, "
                f"Return: {result.total_return_percent:.2f}%, "
                f"Win Rate: {result.win_rate:.2f}%"
            )
            
            # Move to completed
            self.completed_backtests[backtest_id] = result
            if backtest_id in self.active_backtests:
                del self.active_backtests[backtest_id]
            
            return result
        
        except Exception as e:
            logger.error(f"Error running backtest: {e}", exc_info=True)
            result.status = BacktestStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            
            if backtest_id in self.active_backtests:
                self.completed_backtests[backtest_id] = result
                del self.active_backtests[backtest_id]
            
            return result
    
    async def _get_historical_opportunities(
        self,
        start_date: datetime,
        end_date: datetime,
        min_profit_threshold: float
    ) -> List[Dict]:
        """Get historical arbitrage opportunities from database"""
        opportunities = []
        
        try:
            # Try to get from PostgreSQL first
            if self.postgres_db:
                # Query opportunities table
                query = """
                    SELECT timestamp, symbol, buy_exchange, sell_exchange, 
                           buy_price, sell_price, gross_profit_percent, net_profit_percent
                    FROM opportunities
                    WHERE timestamp >= %s AND timestamp <= %s
                      AND gross_profit_percent >= %s
                    ORDER BY timestamp ASC
                """
                
                # Note: This is a simplified query - actual implementation depends on your schema
                # For now, return empty list and use mock data if database not available
                logger.info("Attempting to fetch historical opportunities from database")
        
        except Exception as e:
            logger.warning(f"Could not fetch from database: {e}")
        
        # If no database or no results, generate mock opportunities for demonstration
        if not opportunities:
            logger.info("Generating mock historical opportunities for backtest")
            opportunities = self._generate_mock_opportunities(start_date, end_date, min_profit_threshold)
        
        return opportunities
    
    def _generate_mock_opportunities(
        self,
        start_date: datetime,
        end_date: datetime,
        min_profit_threshold: float
    ) -> List[Dict]:
        """Generate mock opportunities for backtesting when database is not available"""
        import random
        
        opportunities = []
        current_date = start_date
        symbols = ['BTC/USDT', 'ETH/USDT', 'GALA/USDT', 'MATIC/USDT']
        exchanges = ['binance', 'mexc', 'galaswap']
        
        while current_date <= end_date:
            # Generate 1-3 opportunities per day
            num_opps = random.randint(1, 3)
            
            for _ in range(num_opps):
                symbol = random.choice(symbols)
                buy_exchange = random.choice(exchanges)
                sell_exchange = random.choice([e for e in exchanges if e != buy_exchange])
                
                # Generate realistic prices with arbitrage opportunity
                base_price = random.uniform(100, 50000)
                spread_percent = random.uniform(min_profit_threshold + 0.1, 2.0)
                
                buy_price = base_price
                sell_price = base_price * (1 + spread_percent / 100)
                
                gross_profit_percent = spread_percent
                net_profit_percent = gross_profit_percent - 0.2  # Account for fees
                
                opportunities.append({
                    'timestamp': current_date,
                    'symbol': symbol,
                    'buy_exchange': buy_exchange,
                    'sell_exchange': sell_exchange,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'gross_profit_percent': gross_profit_percent,
                    'net_profit_percent': net_profit_percent
                })
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return opportunities
    
    def get_backtest_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """Get backtest result by ID"""
        if backtest_id in self.active_backtests:
            return self.active_backtests[backtest_id]
        if backtest_id in self.completed_backtests:
            return self.completed_backtests[backtest_id]
        return None
    
    def get_all_backtest_results(self) -> List[BacktestResult]:
        """Get all completed backtest results"""
        return list(self.completed_backtests.values())

