"""
InfluxDB Manager
Manages time-series data storage for prices and metrics
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from ..utils.logger import get_logger

logger = get_logger()


class InfluxDBManager:
    """Manages InfluxDB operations for time-series data"""
    
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str
    ):
        """
        Initialize InfluxDB manager
        
        Args:
            url: InfluxDB URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        self.client = None
        self.write_api = None
        self.query_api = None
        
        logger.info("InfluxDB manager initialized")
    
    def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            logger.info(f"Connected to InfluxDB: {health.status}")
        
        except Exception as e:
            logger.error(f"Error connecting to InfluxDB: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from InfluxDB")
    
    def write_price(
        self,
        exchange: str,
        symbol: str,
        bid: float,
        ask: float,
        mid: float,
        spread: float,
        volume: Optional[float] = None
    ):
        """Write price data point"""
        try:
            point = Point("price") \
                .tag("exchange", exchange) \
                .tag("symbol", symbol) \
                .field("bid", bid) \
                .field("ask", ask) \
                .field("mid", mid) \
                .field("spread", spread) \
                .field("spread_percent", (spread / mid * 100) if mid > 0 else 0)
            
            if volume is not None:
                point = point.field("volume", volume)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
        except Exception as e:
            logger.error(f"Error writing price data: {e}")
    
    def write_opportunity(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        gross_profit_percent: float,
        net_profit_percent: float
    ):
        """Write arbitrage opportunity"""
        try:
            point = Point("arbitrage_opportunity") \
                .tag("symbol", symbol) \
                .tag("buy_exchange", buy_exchange) \
                .tag("sell_exchange", sell_exchange) \
                .field("gross_profit_percent", gross_profit_percent) \
                .field("net_profit_percent", net_profit_percent)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
        except Exception as e:
            logger.error(f"Error writing opportunity data: {e}")
    
    def write_trade_execution(
        self,
        symbol: str,
        profit_usd: float,
        profit_percent: float,
        execution_time: float,
        status: str
    ):
        """Write trade execution metrics"""
        try:
            point = Point("trade_execution") \
                .tag("symbol", symbol) \
                .tag("status", status) \
                .field("profit_usd", profit_usd) \
                .field("profit_percent", profit_percent) \
                .field("execution_time", execution_time)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
        except Exception as e:
            logger.error(f"Error writing trade execution data: {e}")
    
    def write_portfolio_value(self, total_value_usd: float, allocation: Dict[str, float]):
        """Write portfolio value snapshot"""
        try:
            point = Point("portfolio_value") \
                .field("total_value_usd", total_value_usd)
            
            for asset, percent in allocation.items():
                point = point.field(f"allocation_{asset}", percent)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
        except Exception as e:
            logger.error(f"Error writing portfolio data: {e}")
    
    def write_performance_metric(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """Write custom performance metric"""
        try:
            point = Point("performance") \
                .field(metric_name, value)
            
            if tags:
                for key, val in tags.items():
                    point = point.tag(key, val)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
        except Exception as e:
            logger.error(f"Error writing performance metric: {e}")
    
    def query_prices(
        self,
        symbol: str,
        exchange: Optional[str] = None,
        start_time: str = "-1h"
    ) -> List[Dict]:
        """Query price data"""
        try:
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r["_measurement"] == "price")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
            '''
            
            if exchange:
                query += f'|> filter(fn: (r) => r["exchange"] == "{exchange}")'
            
            result = self.query_api.query(org=self.org, query=query)
            
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        'time': record.get_time(),
                        'exchange': record.values.get('exchange'),
                        'symbol': record.values.get('symbol'),
                        'field': record.get_field(),
                        'value': record.get_value()
                    })
            
            return data
        
        except Exception as e:
            logger.error(f"Error querying prices: {e}")
            return []
    
    def query_opportunities_count(self, start_time: str = "-1h") -> int:
        """Query number of opportunities found"""
        try:
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r["_measurement"] == "arbitrage_opportunity")
                |> count()
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            count = 0
            for table in result:
                for record in table.records:
                    count = record.get_value()
                    break
            
            return count
        
        except Exception as e:
            logger.error(f"Error querying opportunities count: {e}")
            return 0
    
    def query_portfolio_performance(self, start_time: str = "-24h") -> List[Dict]:
        """Query portfolio performance over time"""
        try:
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r["_measurement"] == "portfolio_value")
                |> filter(fn: (r) => r["_field"] == "total_value_usd")
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        'time': record.get_time(),
                        'value_usd': record.get_value()
                    })
            
            return data
        
        except Exception as e:
            logger.error(f"Error querying portfolio performance: {e}")
            return []

