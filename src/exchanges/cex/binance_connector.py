"""
Binance Exchange Connector
Handles all interactions with Binance API
"""

import ccxt.async_support as ccxt
from typing import Dict, List, Optional
from datetime import datetime
from ...exchanges.base_exchange import BaseExchange, OrderBook, Balance, Order, Trade
from ...utils.logger import get_logger

logger = get_logger()


class BinanceConnector(BaseExchange):
    """Binance exchange connector using CCXT"""
    
    def __init__(
        self, 
        api_key: str, 
        api_secret: str,
        testnet: bool = False,
        enable_rate_limit: bool = True
    ):
        super().__init__("binance", testnet)
        
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize CCXT exchange
        exchange_class = ccxt.binanceusdm if testnet else ccxt.binance
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': enable_rate_limit,
            'timeout': 30000,  # 30 seconds timeout (in milliseconds)
            'options': {
                'defaultType': 'spot',  # spot, margin, future
                'adjustForTimeDifference': True,
                'recvWindow': 20000,  # Binance recvWindow: 20 seconds (in milliseconds)
            }
        })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("Binance connector initialized in TESTNET mode")
        else:
            logger.info("Binance connector initialized for MAINNET")
    
    async def connect(self):
        """Establish connection and verify credentials"""
        try:
            await self.exchange.load_markets()
            
            # Test connection with balance check
            balance = await self.exchange.fetch_balance()
            
            self.is_connected = True
            logger.info(f"Successfully connected to Binance ({'testnet' if self.testnet else 'mainnet'})")
            
        except ccxt.AuthenticationError as e:
            logger.error(f"Binance authentication failed: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Binance network error: {e}")
            raise
        except Exception as e:
            logger.error(f"Binance connection error: {e}")
            raise
    
    async def disconnect(self):
        """Close connection to Binance"""
        try:
            await self.exchange.close()
            self.is_connected = False
            logger.info("Disconnected from Binance")
        except Exception as e:
            logger.error(f"Error disconnecting from Binance: {e}")
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Fetch order book from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            depth: Order book depth (5, 10, 20, 50, 100, 500, 1000, 5000)
        
        Returns:
            OrderBook object
        """
        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit=depth)
            
            # Handle missing or None timestamp
            timestamp_value = order_book.get('timestamp')
            if timestamp_value is None:
                timestamp = datetime.now()
            else:
                # Handle both milliseconds and seconds timestamps
                if timestamp_value > 1e10:  # If in milliseconds
                    timestamp = datetime.fromtimestamp(timestamp_value / 1000)
                else:  # If in seconds
                    timestamp = datetime.fromtimestamp(timestamp_value)
            
            # Ensure bids and asks exist
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            return OrderBook(
                exchange=self.exchange_name,
                symbol=symbol,
                bids=[(float(bid[0]), float(bid[1])) for bid in bids if len(bid) >= 2],
                asks=[(float(ask[0]), float(ask[1])) for ask in asks if len(ask) >= 2],
                timestamp=timestamp
            )
        
        except ccxt.RateLimitExceeded as e:
            error_msg = (
                f"Binance rate limit exceeded for {symbol}. "
                f"Message: {str(e)}. "
                f"Please reduce update frequency or wait before retrying."
            )
            logger.warning(error_msg)
            raise
        
        except ccxt.NetworkError as e:
            error_msg = (
                f"Binance network issue for {symbol}. "
                f"Message: {str(e)}. "
                f"Check your internet connection and Binance API status."
            )
            # Check if it's a timeout error
            if 'timeout' in str(e).lower() or 'RequestTimeout' in str(type(e).__name__):
                logger.warning(f"Binance request timeout for {symbol}. This may be temporary. Retrying...")
            else:
                logger.error(error_msg)
            raise
        
        except ccxt.ExchangeError as e:
            error_msg = (
                f"Binance exchange error for {symbol}. "
                f"Error type: {type(e).__name__}, "
                f"Message: {str(e)}. "
                f"Check if symbol {symbol} is valid and trading is enabled."
            )
            logger.error(error_msg)
            raise
        
        except Exception as e:
            error_msg = (
                f"Unexpected error fetching Binance order book for {symbol}. "
                f"Error type: {type(e).__name__}, "
                f"Message: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker data"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            
            # Handle missing or None timestamp
            timestamp_value = ticker.get('timestamp')
            if timestamp_value is None:
                timestamp = datetime.now()
            else:
                # Handle both milliseconds and seconds timestamps
                if timestamp_value > 1e10:  # If in milliseconds
                    timestamp = datetime.fromtimestamp(timestamp_value / 1000)
                else:  # If in seconds
                    timestamp = datetime.fromtimestamp(timestamp_value)
            
            return {
                'symbol': symbol,
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'last': ticker.get('last'),
                'volume': ticker.get('quoteVolume'),
                'timestamp': timestamp
            }
        except Exception as e:
            error_msg = str(e)
            # Don't log errors for invalid symbols - they're expected
            if 'does not have market symbol' not in error_msg and 'Invalid symbol' not in error_msg:
                logger.debug(f"Error fetching Binance ticker for {symbol}: {e}")
            raise
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """Get account balance"""
        try:
            balance_data = await self.exchange.fetch_balance()
            
            balances = {}
            
            if asset:
                # Return specific asset
                if asset in balance_data:
                    balances[asset] = Balance(
                        asset=asset,
                        free=balance_data[asset]['free'],
                        locked=balance_data[asset]['used']
                    )
            else:
                # Return all non-zero balances
                for currency, info in balance_data.items():
                    if isinstance(info, dict) and info.get('total', 0) > 0:
                        balances[currency] = Balance(
                            asset=currency,
                            free=info['free'],
                            locked=info['used']
                        )
            
            return balances
        
        except ccxt.ExchangeNotAvailable as e:
            # Exchange API is temporarily unavailable (maintenance, overload, etc.)
            error_msg = (
                f"Binance API temporarily unavailable. "
                f"This is usually temporary. Error: {str(e)}. "
                f"Check Binance status page or wait a few moments."
            )
            logger.warning(error_msg)
            # Return empty balances instead of raising - allows bot to continue
            return {}
        
        except ccxt.NetworkError as e:
            # Check if it's a timeout error
            if 'timeout' in str(e).lower() or 'RequestTimeout' in str(type(e).__name__):
                logger.warning(f"Binance balance request timeout. This may be temporary. Error: {e}")
            else:
                logger.debug(f"Binance network error fetching balance: {e}")
            raise
        
        except ccxt.AuthenticationError as e:
            error_msg = (
                f"Binance authentication failed. "
                f"Check your API key, secret, and IP restrictions. Error: {str(e)}"
            )
            logger.error(error_msg)
            raise
        
        except ccxt.RateLimitExceeded as e:
            error_msg = (
                f"Binance rate limit exceeded. "
                f"Too many requests. Please reduce request frequency. Error: {str(e)}"
            )
            logger.warning(error_msg)
            raise
        
        except Exception as e:
            error_type = type(e).__name__
            if 'timeout' in str(e).lower() or 'RequestTimeout' in error_type:
                logger.warning(f"Binance balance request timeout. This may be temporary. Error: {e}")
            elif 'ExchangeNotAvailable' in error_type:
                logger.warning(f"Binance API temporarily unavailable: {e}")
                return {}  # Return empty balances
            else:
                logger.error(f"Error fetching balance from binance. Error type: {error_type}, Message: {e}")
            raise
    
    async def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Order:
        """Place market order on Binance"""
        try:
            logger.info(f"Placing Binance MARKET {side} order: {quantity} {symbol}")
            
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=quantity
            )
            
            return self._parse_order(order)
        
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for Binance order: {e}")
            raise
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid Binance order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing Binance market order: {e}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Order:
        """Place limit order on Binance"""
        try:
            logger.info(f"Placing Binance LIMIT {side} order: {quantity} {symbol} @ {price}")
            
            order = await self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=quantity,
                price=price
            )
            
            return self._parse_order(order)
        
        except Exception as e:
            logger.error(f"Error placing Binance limit order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled Binance order {order_id} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling Binance order {order_id}: {e}")
            return False
    
    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """Get order status"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"Error fetching Binance order status: {e}")
            raise
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees"""
        try:
            fees = await self.exchange.fetch_trading_fees()
            
            if symbol in fees:
                return {
                    'maker': fees[symbol]['maker'],
                    'taker': fees[symbol]['taker']
                }
            
            # Default Binance fees if not found
            return {'maker': 0.001, 'taker': 0.001}  # 0.1%
        
        except Exception as e:
            logger.warning(f"Could not fetch Binance fees, using defaults: {e}")
            return {'maker': 0.001, 'taker': 0.001}
    
    async def get_min_order_size(self, symbol: str) -> float:
        """Get minimum order size"""
        try:
            markets = await self.exchange.load_markets()
            market = markets.get(symbol)
            
            if market:
                return market['limits']['amount']['min']
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Error fetching Binance min order size: {e}")
            return 0.0
    
    async def get_exchange_info(self, symbol: str) -> Dict:
        """Get exchange information"""
        try:
            markets = await self.exchange.load_markets()
            return markets.get(symbol, {})
        except Exception as e:
            logger.error(f"Error fetching Binance exchange info: {e}")
            return {}
    
    def _parse_order(self, order_data: Dict) -> Order:
        """Parse CCXT order data to Order object"""
        # Handle missing or None timestamp
        timestamp_value = order_data.get('timestamp')
        if timestamp_value is None:
            timestamp = datetime.now()
        else:
            # Handle both milliseconds and seconds timestamps
            if timestamp_value > 1e10:  # If in milliseconds
                timestamp = datetime.fromtimestamp(timestamp_value / 1000)
            else:  # If in seconds
                timestamp = datetime.fromtimestamp(timestamp_value)
        
        return Order(
            exchange=self.exchange_name,
            order_id=order_data['id'],
            symbol=order_data['symbol'],
            side=order_data['side'],
            type=order_data['type'],
            price=order_data.get('price'),
            quantity=order_data['amount'],
            filled_quantity=order_data['filled'],
            status=order_data['status'],
            timestamp=timestamp,
            commission=order_data.get('fee', {}).get('cost'),
            commission_asset=order_data.get('fee', {}).get('currency')
        )
    
    async def get_server_time(self) -> int:
        """Get Binance server time"""
        try:
            time_data = await self.exchange.fetch_time()
            return time_data
        except Exception as e:
            logger.error(f"Error fetching Binance server time: {e}")
            return 0

