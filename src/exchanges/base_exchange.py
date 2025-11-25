"""
Base Exchange Interface
Defines the common interface for all exchange connectors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderBook:
    """Order book data structure"""
    exchange: str
    symbol: str
    bids: List[Tuple[float, float]]  # [(price, quantity), ...]
    asks: List[Tuple[float, float]]  # [(price, quantity), ...]
    timestamp: datetime
    
    @property
    def best_bid(self) -> Optional[Tuple[float, float]]:
        """Get best bid (highest buy price)"""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[Tuple[float, float]]:
        """Get best ask (lowest sell price)"""
        return self.asks[0] if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        """Calculate spread between best bid and ask"""
        if self.best_bid and self.best_ask:
            return self.best_ask[0] - self.best_bid[0]
        return None
    
    @property
    def spread_percent(self) -> Optional[float]:
        """Calculate spread as percentage of midpoint"""
        if self.best_bid and self.best_ask:
            mid_price = (self.best_bid[0] + self.best_ask[0]) / 2
            return (self.spread / mid_price) * 100 if mid_price > 0 else None
        return None


@dataclass
class Balance:
    """Account balance data structure"""
    asset: str
    free: float
    locked: float
    
    @property
    def total(self) -> float:
        """Total balance (free + locked)"""
        return self.free + self.locked


@dataclass
class Order:
    """Order data structure"""
    exchange: str
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market' or 'limit'
    price: Optional[float]
    quantity: float
    filled_quantity: float
    status: str  # 'open', 'filled', 'partially_filled', 'cancelled'
    timestamp: datetime
    commission: Optional[float] = None
    commission_asset: Optional[str] = None


@dataclass
class Trade:
    """Trade execution result"""
    exchange: str
    trade_id: str
    order_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    commission: float
    commission_asset: str
    timestamp: datetime
    is_maker: bool = False


class BaseExchange(ABC):
    """Abstract base class for all exchange connectors"""
    
    def __init__(self, exchange_name: str, testnet: bool = False):
        self.exchange_name = exchange_name
        self.testnet = testnet
        self.is_connected = False
    
    @abstractmethod
    async def connect(self):
        """Establish connection to exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to exchange"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Fetch order book for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            depth: Number of order book levels to fetch
        
        Returns:
            OrderBook object
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Get ticker data for a symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Ticker data dictionary
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance
        
        Args:
            asset: Specific asset to query, or None for all assets
        
        Returns:
            Dictionary of asset -> Balance
        """
        pass
    
    @abstractmethod
    async def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Order:
        """
        Place a market order
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
        
        Returns:
            Order object
        """
        pass
    
    @abstractmethod
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Order:
        """
        Place a limit order
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            price: Limit price
            quantity: Order quantity
        
        Returns:
            Order object
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
        
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """
        Get order status
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
        
        Returns:
            Order object with current status
        """
        pass
    
    @abstractmethod
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """
        Get trading fees for a symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dictionary with 'maker' and 'taker' fees
        """
        pass
    
    @abstractmethod
    async def get_min_order_size(self, symbol: str) -> float:
        """
        Get minimum order size for a symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Minimum order quantity
        """
        pass
    
    async def get_exchange_info(self, symbol: str) -> Dict:
        """
        Get exchange information for a symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Exchange info dictionary
        """
        pass
    
    def is_operational(self) -> bool:
        """Check if exchange connection is operational"""
        return self.is_connected

