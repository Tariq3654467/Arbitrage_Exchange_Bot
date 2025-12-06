"""
Price Monitoring System
Continuously monitors prices across all exchanges
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict

from ..exchanges.base_exchange import BaseExchange, OrderBook
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class PriceData:
    """Price data structure"""
    exchange: str
    symbol: str
    bid: float
    ask: float
    mid: float
    spread: float
    spread_percent: float
    timestamp: datetime
    order_book: Optional[OrderBook] = None


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity data"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    gross_profit_percent: float
    timestamp: datetime
    buy_order_book: Optional[OrderBook] = None
    sell_order_book: Optional[OrderBook] = None
    
    @property
    def price_difference(self) -> float:
        """Calculate absolute price difference"""
        return self.sell_price - self.buy_price
    
    def __repr__(self) -> str:
        return (f"ArbitrageOpportunity(symbol={self.symbol}, "
                f"buy={self.buy_exchange}@{self.buy_price:.4f}, "
                f"sell={self.sell_exchange}@{self.sell_price:.4f}, "
                f"profit={self.gross_profit_percent:.2f}%)")


class PriceMonitor:
    """Monitors prices across multiple exchanges"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        trading_pairs: List[str],
        update_interval: float = 0.1,  # 100ms
        min_profit_threshold: float = 0.5,
        min_display_threshold: float = 0.01,  # Show all opportunities >= 0.01% in dashboard
        symbol_exchange_map: Optional[Dict[str, List[str]]] = None  # Map of symbol -> list of exchanges that support it
    ):
        """
        Initialize price monitor
        
        Args:
            exchanges: Dictionary of exchange_name -> exchange_connector
            trading_pairs: List of trading pairs to monitor
            update_interval: Price update interval in seconds
            min_profit_threshold: Minimum profit % to execute trades (for callbacks)
            min_display_threshold: Minimum profit % to show in dashboard (lower threshold)
            symbol_exchange_map: Optional map of symbol -> list of exchanges that support it
        """
        self.exchanges = exchanges
        self.trading_pairs = trading_pairs
        self.update_interval = update_interval
        self.min_profit_threshold = min_profit_threshold  # For trade execution
        self.min_display_threshold = min_display_threshold  # For dashboard display
        self.symbol_exchange_map = symbol_exchange_map or {}  # Track which exchanges support which pairs
        
        # Price storage
        self.current_prices: Dict[str, Dict[str, PriceData]] = defaultdict(dict)
        self.price_history: List[PriceData] = []
        
        # Arbitrage opportunities
        self.opportunities: List[ArbitrageOpportunity] = []
        self.opportunity_callbacks = []
        
        # Monitoring state
        self.is_running = False
        self.monitor_tasks = []
        
        # Rate limiting: semaphore to limit concurrent requests per exchange
        # Binance allows ~20 requests/second, so limit to 10 concurrent per exchange
        self.exchange_semaphores = {
            exchange_name: asyncio.Semaphore(10) 
            for exchange_name in exchanges.keys()
        }
        
        logger.info(f"Price monitor initialized for {len(trading_pairs)} pairs across {len(exchanges)} exchanges")
    
    def add_opportunity_callback(self, callback):
        """Add callback function to be called when opportunity is found"""
        self.opportunity_callbacks.append(callback)
    
    async def start(self):
        """Start price monitoring"""
        if self.is_running:
            logger.warning("Price monitor is already running")
            return
        
        self.is_running = True
        logger.info("Starting price monitor...")
        
        # Start monitoring tasks for each exchange-pair combination
        # Only monitor pairs on exchanges that support them
        # Stagger startup to avoid rate limits (delay between each task creation)
        task_count = 0
        for exchange_name, exchange in self.exchanges.items():
            for symbol in self.trading_pairs:
                # Check if this exchange supports this symbol
                # If symbol_exchange_map is provided, only monitor on listed exchanges
                if self.symbol_exchange_map:
                    supported_exchanges = self.symbol_exchange_map.get(symbol, [])
                    # If symbol is in map but exchange not listed, skip
                    if symbol in self.symbol_exchange_map and exchange_name not in supported_exchanges:
                        continue
                    # If symbol not in map, monitor on all exchanges (backward compatibility)
                
                # Filter Galaswap-specific tokens (GALA, GUSDT, GUSDC, GWETH) to only Galaswap
                if symbol.startswith(('GALA/', 'GUSDT/', 'GUSDC/', 'GWETH/', 'USDT/GALA', 'USDC/GALA', 'BTC/GALA', 'ETH/GALA', 'FDUSD/GALA', 'BUSD/GALA',
                                     'USDT/GUSDT', 'USDC/GUSDT', 'BTC/GUSDT', 'ETH/GUSDT', 'FDUSD/GUSDT', 'BUSD/GUSDT',
                                     'USDT/GUSDC', 'USDC/GUSDC', 'BTC/GUSDC', 'ETH/GUSDC', 'FDUSD/GUSDC', 'BUSD/GUSDC',
                                     'USDT/GWETH', 'USDC/GWETH', 'BTC/GWETH', 'ETH/GWETH', 'FDUSD/GWETH', 'BUSD/GWETH')) or \
                   symbol.endswith(('/GALA', '/GUSDT', '/GUSDC', '/GWETH')) or \
                   '/UNKNOWN' in symbol:
                    if exchange_name != 'galaswap':
                        continue  # Skip Galaswap tokens on other exchanges
                
                task = asyncio.create_task(
                    self._monitor_price(exchange_name, exchange, symbol)
                )
                self.monitor_tasks.append(task)
                task_count += 1
                
                # Stagger task creation to avoid overwhelming API on startup
                # Add small delay every 10 tasks to prevent rate limits
                if task_count % 10 == 0:
                    await asyncio.sleep(0.1)  # 100ms delay every 10 tasks
        
        # Start opportunity detection task
        detect_task = asyncio.create_task(self._detect_opportunities())
        self.monitor_tasks.append(detect_task)
        
        logger.info(f"Price monitor started with {len(self.monitor_tasks)} tasks")
    
    async def stop(self):
        """Stop price monitoring"""
        if not self.is_running:
            return
        
        logger.info("Stopping price monitor...")
        self.is_running = False
        
        # Cancel all monitoring tasks
        for task in self.monitor_tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.monitor_tasks, return_exceptions=True)
        
        self.monitor_tasks = []
        logger.info("Price monitor stopped")
    
    async def _monitor_price(
        self, 
        exchange_name: str, 
        exchange: BaseExchange, 
        symbol: str
    ):
        """Monitor price for a specific exchange and symbol"""
        # Get semaphore for this exchange to limit concurrent requests
        semaphore = self.exchange_semaphores.get(exchange_name, asyncio.Semaphore(10))
        
        while self.is_running:
            try:
                # Use semaphore to limit concurrent API requests
                async with semaphore:
                    # Fetch order book
                    order_book = await exchange.get_order_book(symbol, depth=10)
                
                # Extract price data
                if order_book.best_bid and order_book.best_ask:
                    price_data = PriceData(
                        exchange=exchange_name,
                        symbol=symbol,
                        bid=order_book.best_bid[0],
                        ask=order_book.best_ask[0],
                        mid=(order_book.best_bid[0] + order_book.best_ask[0]) / 2,
                        spread=order_book.spread or 0,
                        spread_percent=order_book.spread_percent or 0,
                        timestamp=order_book.timestamp,
                        order_book=order_book
                    )
                    
                    # Store current price
                    self.current_prices[symbol][exchange_name] = price_data
                    
                    # Add to history
                    self.price_history.append(price_data)
                    
                    # Limit history size
                    if len(self.price_history) > 10000:
                        self.price_history = self.price_history[-5000:]
                
                await asyncio.sleep(self.update_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Check if this is a known invalid pair error
                error_msg = str(e)
                if 'does not have market symbol' in error_msg or 'Invalid symbol' in error_msg:
                    # Invalid pair - stop monitoring this symbol on this exchange
                    logger.debug(f"Invalid pair {symbol} on {exchange_name}, stopping monitoring")
                    break
                
                # Log detailed error information (but reduce frequency)
                error_type = type(e).__name__
                
                # Handle rate limiting with longer backoff
                if 'rate limit' in error_msg.lower() or 'RateLimitExceeded' in error_type or '429' in error_msg:
                    logger.warning(
                        f"Rate limit hit for {exchange_name} {symbol}. "
                        f"Waiting 10 seconds before retry. Error: {error_msg}"
                    )
                    await asyncio.sleep(10)  # Longer wait for rate limits (Binance 429 errors)
                    # Also increase update interval temporarily to reduce load
                    await asyncio.sleep(self.update_interval * 2)
                # Handle timeout errors with exponential backoff
                elif 'timeout' in error_msg.lower() or 'RequestTimeout' in error_type:
                    logger.warning(
                        f"Request timeout for {exchange_name} {symbol}. "
                        f"This may be due to network issues or API slowness. "
                        f"Waiting 3 seconds before retry."
                    )
                    await asyncio.sleep(3)  # Wait before retrying timeout
                else:
                    # Only log unexpected errors, not common network issues
                    if 'network' not in error_msg.lower() and 'connection' not in error_msg.lower():
                        logger.debug(
                            f"Error monitoring price for {exchange_name} {symbol}. "
                            f"Error type: {error_type}, Message: {error_msg}"
                        )
                    await asyncio.sleep(1)  # Normal retry wait
    
    async def _detect_opportunities(self):
        """Continuously detect arbitrage opportunities"""
        while self.is_running:
            try:
                # Check each trading pair
                for symbol in self.trading_pairs:
                    if symbol not in self.current_prices:
                        continue
                    
                    prices = self.current_prices[symbol]
                    
                    # Need at least 1 exchange with price data to find arbitrage
                    # (Same-exchange arbitrage only needs 1 exchange with both bid/ask)
                    if len(prices) < 1:
                        continue
                    
                    # Find best buy and sell prices
                    best_buy_exchange = None
                    best_buy_price = float('inf')
                    best_buy_data = None
                    
                    best_sell_exchange = None
                    best_sell_price = 0
                    best_sell_data = None
                    
                    for exchange_name, price_data in prices.items():
                        # Best buy (lowest ask)
                        if price_data.ask < best_buy_price:
                            best_buy_price = price_data.ask
                            best_buy_exchange = exchange_name
                            best_buy_data = price_data
                        
                        # Best sell (highest bid)
                        if price_data.bid > best_sell_price:
                            best_sell_price = price_data.bid
                            best_sell_exchange = exchange_name
                            best_sell_data = price_data
                    
                    # Check if there's an opportunity
                    # Allow both cross-exchange and same-exchange arbitrage
                    if best_buy_exchange and best_sell_exchange:
                        # For same-exchange arbitrage, check if spread is profitable
                        # (bid > ask would indicate a market inefficiency, but normally bid < ask)
                        # So we check if the spread is large enough to be profitable after fees
                        if best_buy_exchange == best_sell_exchange:
                            # Same-exchange arbitrage: check if spread is profitable
                            # This could be triangular arbitrage or exploiting order book depth
                            spread = best_sell_price - best_buy_price
                            spread_percent = (spread / best_buy_price) * 100 if best_buy_price > 0 else 0
                            
                            # For same-exchange, we need a larger spread to account for fees
                            # Typically need at least 0.2-0.3% more than cross-exchange
                            min_spread_threshold = self.min_profit_threshold + 0.2
                            
                            if spread_percent >= min_spread_threshold:
                                gross_profit_percent = spread_percent
                            else:
                                continue
                        else:
                            # Cross-exchange arbitrage (original logic)
                            gross_profit_percent = ((best_sell_price - best_buy_price) / best_buy_price) * 100
                        
                        # Show all opportunities above display threshold in dashboard
                        if gross_profit_percent >= self.min_display_threshold:
                            opportunity = ArbitrageOpportunity(
                                symbol=symbol,
                                buy_exchange=best_buy_exchange,
                                sell_exchange=best_sell_exchange,
                                buy_price=best_buy_price,
                                sell_price=best_sell_price,
                                gross_profit_percent=gross_profit_percent,
                                timestamp=datetime.now(),
                                buy_order_book=best_buy_data.order_book if best_buy_data else None,
                                sell_order_book=best_sell_data.order_book if best_sell_data else None
                            )
                            
                            # Add to opportunities list (for dashboard display)
                            self.opportunities.append(opportunity)
                            
                            # Limit opportunities list size
                            if len(self.opportunities) > 1000:
                                self.opportunities = self.opportunities[-500:]
                            
                            # Notify callbacks only for opportunities above execution threshold
                            # (This triggers trade execution analysis)
                            if gross_profit_percent >= self.min_profit_threshold:
                                for callback in self.opportunity_callbacks:
                                    try:
                                        await callback(opportunity)
                                    except Exception as e:
                                        logger.error(f"Error in opportunity callback: {e}")
                
                await asyncio.sleep(self.update_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error detecting opportunities: {e}")
                await asyncio.sleep(1)
    
    def get_current_price(self, symbol: str, exchange: str) -> Optional[PriceData]:
        """Get current price for symbol on exchange"""
        return self.current_prices.get(symbol, {}).get(exchange)
    
    def get_all_prices(self, symbol: str) -> Dict[str, PriceData]:
        """Get all current prices for a symbol"""
        return self.current_prices.get(symbol, {})
    
    def get_recent_opportunities(self, limit: int = 10) -> List[ArbitrageOpportunity]:
        """Get recent arbitrage opportunities"""
        return self.opportunities[-limit:]
    
    def get_opportunity_count(self) -> int:
        """Get total number of opportunities found"""
        return len(self.opportunities)
    
    def get_statistics(self) -> Dict:
        """Get monitoring statistics"""
        total_updates = len(self.price_history)
        
        symbol_counts = defaultdict(int)
        exchange_counts = defaultdict(int)
        
        for price in self.price_history:
            symbol_counts[price.symbol] += 1
            exchange_counts[price.exchange] += 1
        
        return {
            'total_price_updates': total_updates,
            'symbols_monitored': len(self.trading_pairs),
            'exchanges_monitored': len(self.exchanges),
            'opportunities_found': len(self.opportunities),
            'symbol_update_counts': dict(symbol_counts),
            'exchange_update_counts': dict(exchange_counts),
            'is_running': self.is_running
        }

