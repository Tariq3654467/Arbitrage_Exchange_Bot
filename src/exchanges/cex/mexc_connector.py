"""
MEXC Exchange Connector
Handles all interactions with MEXC API
"""

import ccxt.async_support as ccxt
from typing import Dict, List, Optional
from datetime import datetime
from ...exchanges.base_exchange import BaseExchange, OrderBook, Balance, Order, Trade
from ...utils.logger import get_logger

logger = get_logger()


class MEXCConnector(BaseExchange):
    """MEXC exchange connector using CCXT"""
    
    def __init__(
        self, 
        api_key: str, 
        api_secret: str,
        testnet: bool = False,
        enable_rate_limit: bool = True
    ):
        super().__init__("mexc", testnet)
        
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize CCXT exchange
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': enable_rate_limit,
            'options': {
                'defaultType': 'spot',  # spot, margin, future
                'adjustForTimeDifference': True,
            }
        })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
            logger.info("MEXC connector initialized in TESTNET mode")
        else:
            logger.info("MEXC connector initialized for MAINNET")
    
    async def connect(self):
        """Establish connection and verify credentials"""
        try:
            await self.exchange.load_markets()
            
            # Test connection with balance check
            balance = await self.exchange.fetch_balance()
            
            self.is_connected = True
            logger.info(f"Successfully connected to MEXC ({'testnet' if self.testnet else 'mainnet'})")
            
        except ccxt.AuthenticationError as e:
            logger.error(f"MEXC authentication failed: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"MEXC network error: {e}")
            raise
        except Exception as e:
            logger.error(f"MEXC connection error: {e}")
            raise
    
    async def disconnect(self):
        """Close connection to MEXC"""
        try:
            await self.exchange.close()
            self.is_connected = False
            logger.info("Disconnected from MEXC")
        except Exception as e:
            logger.error(f"Error disconnecting from MEXC: {e}")
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Fetch order book from MEXC
        
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
        
        except Exception as e:
            logger.error(f"Error fetching MEXC order book for {symbol}: {e}")
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
            logger.error(f"Error fetching MEXC ticker for {symbol}: {e}")
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
        
        except Exception as e:
            logger.error(f"Error fetching MEXC balance: {e}")
            raise
    
    async def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Order:
        """Place market order on MEXC"""
        try:
            logger.info(f"Placing MEXC MARKET {side} order: {quantity} {symbol}")
            
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=quantity
            )
            
            return self._parse_order(order)
        
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for MEXC order: {e}")
            raise
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid MEXC order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing MEXC market order: {e}")
            raise
    
    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float
    ) -> Order:
        """Place limit order on MEXC"""
        try:
            logger.info(f"Placing MEXC LIMIT {side} order: {quantity} {symbol} @ {price}")
            
            order = await self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=quantity,
                price=price
            )
            
            return self._parse_order(order)
        
        except Exception as e:
            logger.error(f"Error placing MEXC limit order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled MEXC order {order_id} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling MEXC order {order_id}: {e}")
            return False
    
    async def get_order_status(self, symbol: str, order_id: str) -> Order:
        """Get order status"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"Error fetching MEXC order status: {e}")
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
            
            # Default MEXC fees if not found (typically 0.2% maker, 0.2% taker)
            return {'maker': 0.002, 'taker': 0.002}  # 0.2%
        
        except Exception as e:
            logger.warning(f"Could not fetch MEXC fees, using defaults: {e}")
            return {'maker': 0.002, 'taker': 0.002}
    
    async def get_min_order_size(self, symbol: str) -> float:
        """Get minimum order size"""
        try:
            markets = await self.exchange.load_markets()
            market = markets.get(symbol)
            
            if market:
                return market['limits']['amount']['min']
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Error fetching MEXC min order size: {e}")
            return 0.0
    
    async def get_exchange_info(self, symbol: str) -> Dict:
        """Get exchange information"""
        try:
            markets = await self.exchange.load_markets()
            return markets.get(symbol, {})
        except Exception as e:
            logger.error(f"Error fetching MEXC exchange info: {e}")
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
        """Get MEXC server time"""
        try:
            time_data = await self.exchange.fetch_time()
            return time_data
        except Exception as e:
            logger.error(f"Error fetching MEXC server time: {e}")
            return 0

