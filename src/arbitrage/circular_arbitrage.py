"""
Circular Arbitrage Path Finder
Finds multi-step arbitrage opportunities that return to the starting asset
Example: GALA → ETH → USDT → GALA (with profit)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .price_monitor import PriceData
from ..exchanges.base_exchange import BaseExchange
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class CircularPath:
    """Represents a circular arbitrage path"""
    start_asset: str
    path: List[Tuple[str, str, str]]  # List of (exchange, symbol, side) tuples
    # Example: [('galaswap', 'GALA/ETH', 'sell'), ('binance', 'ETH/USDT', 'sell'), ('galaswap', 'USDT/GALA', 'buy')]
    expected_profit_percent: float
    expected_profit_amount: float
    start_amount: float
    end_amount: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self):
        path_str = " → ".join([f"{ex}({sym})" for ex, sym, _ in self.path])
        return f"{self.start_asset} → {path_str} → {self.start_asset} | Profit: {self.expected_profit_percent:.2f}%"


class CircularArbitrageFinder:
    """Finds circular arbitrage opportunities"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        price_data: Dict[str, Dict[str, PriceData]],
        min_profit_threshold: float = 0.5
    ):
        """
        Initialize circular arbitrage finder
        
        Args:
            exchanges: Dictionary of exchange connectors
            price_data: Current price data from price monitor {symbol: {exchange: PriceData}}
            min_profit_threshold: Minimum profit % required
        """
        self.exchanges = exchanges
        self.price_data = price_data
        self.min_profit_threshold = min_profit_threshold
        
        # Define circular arbitrage paths to search
        self.defined_paths = [
            {
                'name': 'GALA_ETH_USDT_CIRCLE',
                'start_asset': 'GALA',
                'steps': [
                    {'exchange': 'galaswap', 'symbol': 'GALA/ETH', 'side': 'sell', 'get': 'ETH'},
                    {'exchange': 'binance', 'symbol': 'ETH/USDT', 'side': 'sell', 'get': 'USDT'},
                    {'exchange': 'galaswap', 'symbol': 'USDT/GALA', 'side': 'buy', 'get': 'GALA'},
                ]
            },
            {
                'name': 'GALA_ETH_USDT_CIRCLE_REVERSE',
                'start_asset': 'GALA',
                'steps': [
                    {'exchange': 'galaswap', 'symbol': 'GALA/USDT', 'side': 'sell', 'get': 'USDT'},
                    {'exchange': 'binance', 'symbol': 'USDT/ETH', 'side': 'buy', 'get': 'ETH'},
                    {'exchange': 'galaswap', 'symbol': 'ETH/GALA', 'side': 'buy', 'get': 'GALA'},
                ]
            },
        ]
        
        logger.info(f"Circular arbitrage finder initialized with {len(self.defined_paths)} defined paths")
    
    async def find_opportunities(
        self,
        start_amount: float = 1000.0  # Start with $1000 worth
    ) -> List[CircularPath]:
        """
        Find circular arbitrage opportunities
        
        Args:
            start_amount: Starting amount in USD (or base asset)
        
        Returns:
            List of profitable circular paths
        """
        opportunities = []
        
        for path_def in self.defined_paths:
            try:
                path = await self._evaluate_path(path_def, start_amount)
                if path and path.expected_profit_percent >= self.min_profit_threshold:
                    opportunities.append(path)
                    logger.info(f"Found circular arbitrage: {path}")
            except Exception as e:
                logger.debug(f"Error evaluating path {path_def['name']}: {e}")
                continue
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.expected_profit_percent, reverse=True)
        
        return opportunities
    
    async def _evaluate_path(
        self,
        path_def: Dict,
        start_amount: float
    ) -> Optional[CircularPath]:
        """Evaluate a specific circular path"""
        start_asset = path_def['start_asset']
        steps = path_def['steps']
        
        current_amount = start_amount
        current_asset = start_asset
        path_tuples = []
        
        # Execute each step in the path
        for step in steps:
            exchange_name = step['exchange']
            symbol = step['symbol']
            side = step['side']
            target_asset = step['get']
            
            # Get price data for this symbol on this exchange
            price_info = self.price_data.get(symbol, {}).get(exchange_name)
            
            if not price_info:
                # Try to find price on this exchange
                exchange = self.exchanges.get(exchange_name)
                if not exchange or not exchange.is_connected:
                    return None
                
                try:
                    # Fetch current price
                    order_book = await exchange.get_order_book(symbol, depth=5)
                    if not order_book or not order_book.best_bid or not order_book.best_ask:
                        return None
                    
                    # Create price data
                    price_info = PriceData(
                        exchange=exchange_name,
                        symbol=symbol,
                        bid=order_book.best_bid[0],
                        ask=order_book.best_ask[0],
                        mid=(order_book.best_bid[0] + order_book.best_ask[0]) / 2,
                        spread=order_book.spread or 0,
                        spread_percent=order_book.spread_percent or 0,
                        timestamp=datetime.now(),
                        order_book=order_book
                    )
                except Exception as e:
                    logger.debug(f"Could not get price for {symbol} on {exchange_name}: {e}")
                    return None
            
            # Parse symbol
            base_asset, quote_asset = symbol.split('/')
            
            # Calculate trade based on side and current asset
            if side == 'sell':
                # Selling current_asset to get target_asset
                price = price_info.bid  # We're selling, so we get the bid price
                
                if current_asset == base_asset:
                    # Selling base asset, getting quote asset
                    amount_received = current_amount * price
                    current_amount = amount_received
                    current_asset = quote_asset
                elif current_asset == quote_asset:
                    # Selling quote asset, getting base asset
                    amount_received = current_amount / price
                    current_amount = amount_received
                    current_asset = base_asset
                else:
                    logger.debug(f"Current asset {current_asset} not in symbol {symbol}")
                    return None
            else:  # buy
                # Buying target_asset with current_asset
                price = price_info.ask  # We're buying, so we pay the ask price
                
                if current_asset == base_asset:
                    # Using base to buy quote
                    amount_received = current_amount * price
                    current_amount = amount_received
                    current_asset = quote_asset
                elif current_asset == quote_asset:
                    # Using quote to buy base
                    amount_received = current_amount / price
                    current_amount = amount_received
                    current_asset = base_asset
                else:
                    logger.debug(f"Current asset {current_asset} not in symbol {symbol}")
                    return None
            
            # Apply trading fee (estimate 0.1% per trade)
            fee_rate = 0.001
            current_amount *= (1 - fee_rate)
            
            path_tuples.append((exchange_name, symbol, side))
        
        # Check if we ended with the same asset
        if current_asset != start_asset:
            logger.debug(f"Path did not return to {start_asset}, ended with {current_asset}")
            return None
        
        # Calculate profit
        end_amount = current_amount
        profit_amount = end_amount - start_amount
        profit_percent = (profit_amount / start_amount) * 100 if start_amount > 0 else 0
        
        if profit_percent < self.min_profit_threshold:
            return None
        
        return CircularPath(
            start_asset=start_asset,
            path=path_tuples,
            expected_profit_percent=profit_percent,
            expected_profit_amount=profit_amount,
            start_amount=start_amount,
            end_amount=end_amount
        )
    
    def get_path_summary(self, path: CircularPath) -> str:
        """Get human-readable path summary"""
        steps = []
        for exchange, symbol, side in path.path:
            steps.append(f"{side.upper()} {symbol} on {exchange}")
        
        return (
            f"Circular Path: {path.start_asset} → ... → {path.start_asset}\n"
            f"Steps: {' → '.join(steps)}\n"
            f"Start: {path.start_amount:.6f} {path.start_asset}\n"
            f"End: {path.end_amount:.6f} {path.start_asset}\n"
            f"Profit: {path.expected_profit_amount:.6f} {path.start_asset} ({path.expected_profit_percent:.2f}%)"
        )

