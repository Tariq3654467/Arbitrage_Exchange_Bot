"""
Trade Executor
Executes arbitrage trades across exchanges
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .arbitrage_calculator import ProfitAnalysis
from ..exchanges.base_exchange import BaseExchange, Order
from ..utils.logger import get_logger

logger = get_logger()


class TradeStatus(Enum):
    """Trade execution status"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class TradeResult:
    """Trade execution result"""
    analysis: ProfitAnalysis
    status: TradeStatus
    buy_order: Optional[Order] = None
    sell_order: Optional[Order] = None
    actual_profit_usd: Optional[float] = None
    actual_profit_percent: Optional[float] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def is_successful(self) -> bool:
        """Check if trade was successful"""
        return self.status == TradeStatus.COMPLETED
    
    @property
    def profit_difference(self) -> Optional[float]:
        """Difference between expected and actual profit"""
        if self.actual_profit_usd and self.analysis:
            return self.actual_profit_usd - self.analysis.net_profit_usd
        return None


class TradeExecutor:
    """Executes arbitrage trades"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        paper_trading: bool = True,
        max_concurrent_trades: int = 3,
        order_timeout: int = 120
    ):
        """
        Initialize trade executor
        
        Args:
            exchanges: Dictionary of exchange connectors
            paper_trading: If True, simulate trades without executing
            max_concurrent_trades: Maximum number of concurrent trades
            order_timeout: Order timeout in seconds
        """
        self.exchanges = exchanges
        self.paper_trading = paper_trading
        self.max_concurrent_trades = max_concurrent_trades
        self.order_timeout = order_timeout
        
        # Trade tracking
        self.active_trades: List[TradeResult] = []
        self.completed_trades: List[TradeResult] = []
        self.trade_history: List[TradeResult] = []
        
        # Execution semaphore to limit concurrent trades
        self.execution_semaphore = asyncio.Semaphore(max_concurrent_trades)
        
        mode = "PAPER TRADING" if paper_trading else "LIVE TRADING"
        logger.info(f"Trade executor initialized in {mode} mode")
    
    async def execute_trade(self, analysis: ProfitAnalysis) -> TradeResult:
        """
        Execute an arbitrage trade
        
        Args:
            analysis: Profit analysis for the trade
        
        Returns:
            Trade execution result
        """
        async with self.execution_semaphore:
            return await self._execute_trade_internal(analysis)
    
    async def _execute_trade_internal(self, analysis: ProfitAnalysis) -> TradeResult:
        """Internal trade execution logic"""
        start_time = datetime.now()
        
        result = TradeResult(
            analysis=analysis,
            status=TradeStatus.PENDING
        )
        
        self.active_trades.append(result)
        
        try:
            logger.info(f"Executing arbitrage trade: {analysis.opportunity}")
            
            if self.paper_trading:
                # Simulate trade (mutates existing result instance)
                result = await self._simulate_trade(analysis, result)
            else:
                # Execute real trade (mutates existing result instance)
                result = await self._execute_real_trade(analysis, result)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # Update trade lists
            self.active_trades.remove(result)
            self.completed_trades.append(result)
            self.trade_history.append(result)
            
            # Log result
            if result.is_successful:
                logger.info(
                    f"✓ Trade completed successfully! "
                    f"Profit: ${result.actual_profit_usd:.2f} "
                    f"({result.actual_profit_percent:.2f}%) "
                    f"Time: {execution_time:.2f}s"
                )
            else:
                logger.error(
                    f"✗ Trade failed: {result.error_message}"
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            result.status = TradeStatus.FAILED
            result.error_message = str(e)
            
            if result in self.active_trades:
                self.active_trades.remove(result)
            self.completed_trades.append(result)
            self.trade_history.append(result)
            
            return result
    
    async def _simulate_trade(self, analysis: ProfitAnalysis, result: TradeResult) -> TradeResult:
        """Simulate a trade for paper trading (mutates provided TradeResult)"""
        logger.info(f"[PAPER TRADE] Simulating trade...")
        
        # Simulate execution delay
        await asyncio.sleep(0.5)
        
        # Assume trade executes as expected with slight variance
        import random
        variance = random.uniform(-0.1, 0.1)  # ±0.1% variance
        
        actual_profit_usd = analysis.net_profit_usd * (1 + variance / 100)
        actual_profit_percent = analysis.net_profit_percent * (1 + variance / 100)
        
        # Mutate existing result object so references in active_trades stay valid
        result.status = TradeStatus.COMPLETED
        result.actual_profit_usd = actual_profit_usd
        result.actual_profit_percent = actual_profit_percent
        result.execution_time = 0.5
        
        logger.info(
            f"[PAPER TRADE] Trade simulated: "
            f"Buy {analysis.buy_amount:.6f} @ {analysis.opportunity.buy_exchange} "
            f"Sell {analysis.sell_amount:.6f} @ {analysis.opportunity.sell_exchange} "
            f"Profit: ${actual_profit_usd:.2f}"
        )
        
        return result
    
    async def _execute_real_trade(self, analysis: ProfitAnalysis, result: TradeResult) -> TradeResult:
        """Execute a real trade (mutates provided TradeResult)"""
        logger.info(f"[LIVE TRADE] Executing real trade...")
        
        # Mark as executing on the existing result instance
        result.status = TradeStatus.EXECUTING
        
        # Get exchanges
        buy_exchange = self.exchanges.get(analysis.opportunity.buy_exchange)
        sell_exchange = self.exchanges.get(analysis.opportunity.sell_exchange)
        
        if not buy_exchange or not sell_exchange:
            raise ValueError("Exchange not found")
        
        try:
            # Execute buy and sell orders concurrently
            buy_task = asyncio.create_task(
                self._execute_buy_order(
                    buy_exchange,
                    analysis.opportunity.symbol,
                    analysis.buy_amount
                )
            )
            
            sell_task = asyncio.create_task(
                self._execute_sell_order(
                    sell_exchange,
                    analysis.opportunity.symbol,
                    analysis.sell_amount
                )
            )
            
            # Wait for both orders to complete
            buy_order, sell_order = await asyncio.gather(buy_task, sell_task)
            
            result.buy_order = buy_order
            result.sell_order = sell_order
            
            # Calculate actual profit
            if buy_order and sell_order:
                buy_filled = buy_order.filled_quantity or 0
                sell_filled = sell_order.filled_quantity or 0
                filled_qty = min(buy_filled, sell_filled)

                # Consider both 'filled' and 'closed' as terminal filled states (ccxt may use 'closed')
                buy_filled_status = buy_order.status in ['filled', 'closed']
                sell_filled_status = sell_order.status in ['filled', 'closed']

                if filled_qty > 0 and buy_filled_status and sell_filled_status:
                    actual_buy_price = buy_order.price or analysis.opportunity.buy_price
                    actual_sell_price = sell_order.price or analysis.opportunity.sell_price

                    actual_profit_usd = (actual_sell_price - actual_buy_price) * filled_qty
                    denom = analysis.trade_amount or (filled_qty * actual_buy_price) or 1
                    actual_profit_percent = (actual_profit_usd / denom) * 100

                    result.actual_profit_usd = actual_profit_usd
                    result.actual_profit_percent = actual_profit_percent
                    result.status = TradeStatus.COMPLETED

                    # If not all requested qty filled, note it but still mark completed
                    if (buy_filled < analysis.buy_amount) or (sell_filled < analysis.sell_amount):
                        result.error_message = "Completed with partial fill"
                        logger.warning(
                            f"Trade completed with partial fill: "
                            f"buy_filled={buy_filled} sell_filled={sell_filled} "
                            f"requested_buy={analysis.buy_amount} requested_sell={analysis.sell_amount}"
                        )
                else:
                    result.status = TradeStatus.PARTIAL
                    result.error_message = "One or more orders not fully filled"
            else:
                result.status = TradeStatus.FAILED
                result.error_message = "Order execution failed"
        
        except Exception as e:
            logger.error(f"Error in trade execution: {e}")
            result.status = TradeStatus.FAILED
            result.error_message = str(e)
            
            # Attempt to cancel any open orders
            await self._cancel_open_orders(result)
        
        return result
    
    async def _execute_buy_order(
        self,
        exchange: BaseExchange,
        symbol: str,
        amount: float
    ) -> Optional[Order]:
        """Execute buy order"""
        try:
            logger.info(f"Placing BUY order: {amount} {symbol} on {exchange.exchange_name}")
            
            order = await exchange.place_market_order(
                symbol=symbol,
                side='buy',
                quantity=amount
            )
            
            # Wait for order to fill (with timeout)
            filled_order = await self._wait_for_order_fill(
                exchange,
                symbol,
                order.order_id
            )
            
            return filled_order
        
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            raise
    
    async def _execute_sell_order(
        self,
        exchange: BaseExchange,
        symbol: str,
        amount: float
    ) -> Optional[Order]:
        """Execute sell order"""
        try:
            logger.info(f"Placing SELL order: {amount} {symbol} on {exchange.exchange_name}")
            
            order = await exchange.place_market_order(
                symbol=symbol,
                side='sell',
                quantity=amount
            )
            
            # Wait for order to fill
            filled_order = await self._wait_for_order_fill(
                exchange,
                symbol,
                order.order_id
            )
            
            return filled_order
        
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            raise
    
    async def _wait_for_order_fill(
        self,
        exchange: BaseExchange,
        symbol: str,
        order_id: str
    ) -> Order:
        """Wait for order to be filled"""
        start_time = datetime.now()
        
        while True:
            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.order_timeout:
                raise TimeoutError(f"Order {order_id} timed out after {self.order_timeout}s")
            
            # Check order status
            order = await exchange.get_order_status(symbol, order_id)
            
            if order.status in ['filled', 'closed']:
                return order
            elif order.status in ['cancelled', 'expired', 'rejected']:
                raise Exception(f"Order {order_id} was {order.status}")
            
            # Wait before checking again
            await asyncio.sleep(0.5)
    
    async def _cancel_open_orders(self, result: TradeResult):
        """Cancel any open orders"""
        try:
            if result.buy_order and result.buy_order.status == 'open':
                buy_exchange = self.exchanges.get(result.analysis.opportunity.buy_exchange)
                if buy_exchange:
                    await buy_exchange.cancel_order(
                        result.analysis.opportunity.symbol,
                        result.buy_order.order_id
                    )
            
            if result.sell_order and result.sell_order.status == 'open':
                sell_exchange = self.exchanges.get(result.analysis.opportunity.sell_exchange)
                if sell_exchange:
                    await sell_exchange.cancel_order(
                        result.analysis.opportunity.symbol,
                        result.sell_order.order_id
                    )
        
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    def get_trade_statistics(self) -> Dict:
        """Get trade execution statistics"""
        total_trades = len(self.completed_trades)
        successful_trades = sum(1 for t in self.completed_trades if t.is_successful)
        failed_trades = sum(1 for t in self.completed_trades if t.status == TradeStatus.FAILED)
        
        total_profit = sum(
            t.actual_profit_usd for t in self.completed_trades 
            if t.actual_profit_usd is not None
        )
        
        avg_profit = total_profit / successful_trades if successful_trades > 0 else 0
        
        avg_execution_time = sum(
            t.execution_time for t in self.completed_trades 
            if t.execution_time is not None
        ) / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'successful_trades': successful_trades,
            'failed_trades': failed_trades,
            'success_rate': (successful_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_profit_usd': total_profit,
            'average_profit_usd': avg_profit,
            'average_execution_time': avg_execution_time,
            'active_trades': len(self.active_trades),
            'paper_trading': self.paper_trading
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[TradeResult]:
        """Get recent trade results"""
        return self.trade_history[-limit:]

