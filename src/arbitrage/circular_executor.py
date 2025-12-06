"""
Circular Arbitrage Trade Executor
Executes multi-step circular arbitrage trades sequentially
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .circular_arbitrage import CircularPath
from ..exchanges.base_exchange import BaseExchange, Order
from ..utils.logger import get_logger

logger = get_logger()


class CircularTradeStatus(Enum):
    """Circular trade execution status"""
    PENDING = "pending"
    EXECUTING = "executing"
    STEP_COMPLETED = "step_completed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CircularTradeResult:
    """Result of a circular arbitrage trade"""
    path: CircularPath
    status: CircularTradeStatus
    orders: List[Order] = None
    actual_start_amount: float = None
    actual_end_amount: float = None
    actual_profit: float = None
    actual_profit_percent: float = None
    execution_time: float = None
    error_message: Optional[str] = None
    step_results: List[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.orders is None:
            self.orders = []
        if self.step_results is None:
            self.step_results = []
    
    @property
    def is_successful(self) -> bool:
        """Check if trade was successful"""
        return self.status == CircularTradeStatus.COMPLETED


class CircularTradeExecutor:
    """Executes circular arbitrage trades sequentially"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        paper_trading: bool = True,
        order_timeout: int = 60
    ):
        """
        Initialize circular trade executor
        
        Args:
            exchanges: Dictionary of exchange connectors
            paper_trading: If True, simulate trades
            order_timeout: Order timeout in seconds per step
        """
        self.exchanges = exchanges
        self.paper_trading = paper_trading
        self.order_timeout = order_timeout
        
        # Trade tracking
        self.active_trades: List[CircularTradeResult] = []
        self.completed_trades: List[CircularTradeResult] = []
        
        mode = "PAPER TRADING" if paper_trading else "LIVE TRADING"
        logger.info(f"Circular trade executor initialized in {mode} mode")
    
    async def execute_circular_trade(
        self,
        path: CircularPath,
        start_amount: Optional[float] = None
    ) -> CircularTradeResult:
        """
        Execute a circular arbitrage trade
        
        Args:
            path: The circular arbitrage path to execute
            start_amount: Starting amount (uses path.start_amount if not provided)
        
        Returns:
            Trade execution result
        """
        start_time = datetime.now()
        
        if start_amount is None:
            start_amount = path.start_amount
        
        result = CircularTradeResult(
            path=path,
            status=CircularTradeStatus.PENDING,
            actual_start_amount=start_amount
        )
        
        self.active_trades.append(result)
        
        try:
            logger.info(f"Executing circular arbitrage: {path}")
            result.status = CircularTradeStatus.EXECUTING
            
            if self.paper_trading:
                result = await self._simulate_circular_trade(path, start_amount, result)
            else:
                result = await self._execute_real_circular_trade(path, start_amount, result)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # Update trade lists
            if result in self.active_trades:
                self.active_trades.remove(result)
            self.completed_trades.append(result)
            
            # Log result
            if result.is_successful:
                logger.info(
                    f"✓ Circular trade completed! "
                    f"Start: {result.actual_start_amount:.6f} {path.start_asset} → "
                    f"End: {result.actual_end_amount:.6f} {path.start_asset} | "
                    f"Profit: {result.actual_profit:.6f} ({result.actual_profit_percent:.2f}%) | "
                    f"Time: {execution_time:.2f}s"
                )
            else:
                logger.error(f"✗ Circular trade failed: {result.error_message}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing circular trade: {e}", exc_info=True)
            result.status = CircularTradeStatus.FAILED
            result.error_message = str(e)
            
            if result in self.active_trades:
                self.active_trades.remove(result)
            self.completed_trades.append(result)
            
            return result
    
    async def _simulate_circular_trade(
        self,
        path: CircularPath,
        start_amount: float,
        result: CircularTradeResult
    ) -> CircularTradeResult:
        """Simulate a circular trade for paper trading"""
        logger.info(f"[PAPER TRADE] Simulating circular trade...")
        
        current_amount = start_amount
        current_asset = path.start_asset
        
        # Simulate each step
        for i, (exchange_name, symbol, side) in enumerate(path.path):
            await asyncio.sleep(0.2)  # Simulate execution delay
            
            # Get exchange
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                result.status = CircularTradeStatus.FAILED
                result.error_message = f"Exchange {exchange_name} not found"
                return result
            
            # Simulate price fetch
            try:
                order_book = await exchange.get_order_book(symbol, depth=5)
                if not order_book:
                    result.status = CircularTradeStatus.FAILED
                    result.error_message = f"Could not get order book for {symbol} on {exchange_name}"
                    return result
                
                # Use appropriate price based on side
                if side == 'sell':
                    price = order_book.best_bid[0] if order_book.best_bid else 0
                else:
                    price = order_book.best_ask[0] if order_book.best_ask else 0
                
                # Parse symbol
                base, quote = symbol.split('/')
                
                # Store asset before trade
                asset_before = current_asset
                amount_in = current_amount
                
                # Calculate trade
                if side == 'sell':
                    # Selling current asset
                    if current_asset == base:
                        amount_received = current_amount * price
                        current_asset = quote
                    elif current_asset == quote:
                        amount_received = current_amount / price
                        current_asset = base
                    else:
                        raise ValueError(f"Current asset {current_asset} not in symbol {symbol}")
                else:
                    # Buying target asset
                    if current_asset == base:
                        amount_received = current_amount * price
                        current_asset = quote
                    elif current_asset == quote:
                        amount_received = current_amount / price
                        current_asset = base
                    else:
                        raise ValueError(f"Current asset {current_asset} not in symbol {symbol}")
                
                # Apply fee (0.1%)
                fee_rate = 0.001
                amount_received *= (1 - fee_rate)
                
                # Update amounts
                current_amount = amount_received
                asset_after = current_asset
                
                # Record step result
                result.step_results.append({
                    'step': i + 1,
                    'exchange': exchange_name,
                    'symbol': symbol,
                    'side': side,
                    'price': price,
                    'amount_in': amount_in,
                    'amount_out': current_amount,
                    'asset_before': asset_before,
                    'asset_after': asset_after
                })
                
                result.status = CircularTradeStatus.STEP_COMPLETED
                
            except Exception as e:
                logger.error(f"Error in step {i+1}: {e}")
                result.status = CircularTradeStatus.FAILED
                result.error_message = f"Step {i+1} failed: {str(e)}"
                return result
        
        # Check if we returned to start asset
        if current_asset != path.start_asset:
            result.status = CircularTradeStatus.FAILED
            result.error_message = f"Did not return to {path.start_asset}, ended with {current_asset}"
            return result
        
        # Calculate final profit
        result.actual_end_amount = current_amount
        result.actual_profit = current_amount - start_amount
        result.actual_profit_percent = (result.actual_profit / start_amount) * 100 if start_amount > 0 else 0
        result.status = CircularTradeStatus.COMPLETED
        
        return result
    
    async def _execute_real_circular_trade(
        self,
        path: CircularPath,
        start_amount: float,
        result: CircularTradeResult
    ) -> CircularTradeResult:
        """Execute a real circular trade"""
        logger.info(f"[LIVE TRADE] Executing real circular trade...")
        
        current_amount = start_amount
        current_asset = path.start_asset
        
        # Execute each step sequentially
        for i, (exchange_name, symbol, side) in enumerate(path.path):
            logger.info(f"Step {i+1}/{len(path.path)}: {side.upper()} {symbol} on {exchange_name}")
            
            exchange = self.exchanges.get(exchange_name)
            if not exchange or not exchange.is_connected:
                result.status = CircularTradeStatus.FAILED
                result.error_message = f"Exchange {exchange_name} not connected"
                return result
            
            try:
                # Place order
                order = await exchange.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=current_amount
                )
                
                # Wait for order to fill
                filled_order = await self._wait_for_order_fill(
                    exchange,
                    symbol,
                    order.order_id
                )
                
                if not filled_order or filled_order.status != 'filled':
                    result.status = CircularTradeStatus.FAILED
                    result.error_message = f"Step {i+1} order not filled"
                    return result
                
                result.orders.append(filled_order)
                
                # Store asset before trade
                asset_before = current_asset
                amount_before = current_amount
                
                # Parse symbol
                base, quote = symbol.split('/')
                
                # Update current amount based on filled order
                if filled_order.filled_quantity:
                    current_amount = filled_order.filled_quantity
                
                # Determine next asset based on trade side
                if side == 'sell':
                    if current_asset == base:
                        current_asset = quote
                    elif current_asset == quote:
                        current_asset = base
                else:  # buy
                    if current_asset == base:
                        current_asset = quote
                    elif current_asset == quote:
                        current_asset = base
                
                asset_after = current_asset
                
                result.step_results.append({
                    'step': i + 1,
                    'exchange': exchange_name,
                    'symbol': symbol,
                    'side': side,
                    'order_id': filled_order.order_id,
                    'filled_quantity': filled_order.filled_quantity,
                    'price': filled_order.price,
                    'amount_in': amount_before,
                    'amount_out': current_amount,
                    'asset_before': asset_before,
                    'asset_after': asset_after
                })
                
                result.status = CircularTradeStatus.STEP_COMPLETED
                
            except Exception as e:
                logger.error(f"Error executing step {i+1}: {e}")
                result.status = CircularTradeStatus.FAILED
                result.error_message = f"Step {i+1} failed: {str(e)}"
                return result
        
        # Verify we returned to start asset
        if current_asset != path.start_asset:
            result.status = CircularTradeStatus.FAILED
            result.error_message = f"Did not return to {path.start_asset}, ended with {current_asset}"
            return result
        
        # Calculate final profit
        result.actual_end_amount = current_amount
        result.actual_profit = current_amount - start_amount
        result.actual_profit_percent = (result.actual_profit / start_amount) * 100 if start_amount > 0 else 0
        result.status = CircularTradeStatus.COMPLETED
        
        return result
    
    async def _wait_for_order_fill(
        self,
        exchange: BaseExchange,
        symbol: str,
        order_id: str
    ) -> Optional[Order]:
        """Wait for order to be filled"""
        start_time = datetime.now()
        
        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.order_timeout:
                raise TimeoutError(f"Order {order_id} timed out after {self.order_timeout}s")
            
            try:
                order = await exchange.get_order_status(symbol, order_id)
                
                if order.status in ['filled', 'closed']:
                    return order
                elif order.status in ['cancelled', 'expired', 'rejected']:
                    raise Exception(f"Order {order_id} was {order.status}")
                
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error checking order status: {e}")
                raise
    
    def get_statistics(self) -> Dict:
        """Get circular trade statistics"""
        total_trades = len(self.completed_trades)
        successful_trades = sum(1 for t in self.completed_trades if t.is_successful)
        
        total_profit = sum(
            t.actual_profit for t in self.completed_trades 
            if t.actual_profit is not None
        )
        
        avg_profit = total_profit / successful_trades if successful_trades > 0 else 0
        
        return {
            'total_circular_trades': total_trades,
            'successful_trades': successful_trades,
            'success_rate': (successful_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_profit': total_profit,
            'average_profit': avg_profit,
            'active_trades': len(self.active_trades),
            'paper_trading': self.paper_trading
        }

