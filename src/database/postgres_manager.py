"""
PostgreSQL Database Manager
Manages relational data storage
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import contextmanager

from ..utils.logger import get_logger

logger = get_logger()


class PostgresManager:
    """Manages PostgreSQL database operations"""
    
    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL manager
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.conn = None
        
        logger.info("PostgreSQL manager initialized")
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            logger.info("Connected to PostgreSQL database")
            self._initialize_schema()
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from PostgreSQL")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def _initialize_schema(self):
        """Initialize database schema"""
        try:
            with self.get_cursor() as cursor:
                # Trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        buy_exchange VARCHAR(50) NOT NULL,
                        sell_exchange VARCHAR(50) NOT NULL,
                        buy_price NUMERIC(20, 8) NOT NULL,
                        sell_price NUMERIC(20, 8) NOT NULL,
                        amount NUMERIC(20, 8) NOT NULL,
                        gross_profit_usd NUMERIC(20, 2),
                        net_profit_usd NUMERIC(20, 2),
                        net_profit_percent NUMERIC(10, 4),
                        total_fees_usd NUMERIC(20, 2),
                        status VARCHAR(20),
                        buy_order_id VARCHAR(100),
                        sell_order_id VARCHAR(100),
                        execution_time_seconds NUMERIC(10, 2),
                        paper_trade BOOLEAN DEFAULT false
                    )
                """)
                
                # Balances snapshot table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS balance_snapshots (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        exchange VARCHAR(50) NOT NULL,
                        asset VARCHAR(20) NOT NULL,
                        amount NUMERIC(20, 8) NOT NULL,
                        value_usd NUMERIC(20, 2)
                    )
                """)
                
                # Portfolio snapshots table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        total_value_usd NUMERIC(20, 2) NOT NULL,
                        allocation JSONB,
                        rebalance_needed BOOLEAN
                    )
                """)
                
                # Arbitrage opportunities table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        buy_exchange VARCHAR(50) NOT NULL,
                        sell_exchange VARCHAR(50) NOT NULL,
                        buy_price NUMERIC(20, 8) NOT NULL,
                        sell_price NUMERIC(20, 8) NOT NULL,
                        gross_profit_percent NUMERIC(10, 4),
                        net_profit_percent NUMERIC(10, 4),
                        executed BOOLEAN DEFAULT false
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_timestamp ON arbitrage_opportunities(timestamp)")
                
                logger.info("Database schema initialized")
        
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise
    
    def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """Save trade to database"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trades (
                        timestamp, symbol, buy_exchange, sell_exchange,
                        buy_price, sell_price, amount,
                        gross_profit_usd, net_profit_usd, net_profit_percent,
                        total_fees_usd, status, buy_order_id, sell_order_id,
                        execution_time_seconds, paper_trade
                    ) VALUES (
                        %(timestamp)s, %(symbol)s, %(buy_exchange)s, %(sell_exchange)s,
                        %(buy_price)s, %(sell_price)s, %(amount)s,
                        %(gross_profit_usd)s, %(net_profit_usd)s, %(net_profit_percent)s,
                        %(total_fees_usd)s, %(status)s, %(buy_order_id)s, %(sell_order_id)s,
                        %(execution_time_seconds)s, %(paper_trade)s
                    ) RETURNING id
                """, trade_data)
                
                trade_id = cursor.fetchone()['id']
                return trade_id
        
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            raise
    
    def save_opportunity(self, opp_data: Dict[str, Any]) -> int:
        """Save arbitrage opportunity"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO arbitrage_opportunities (
                        timestamp, symbol, buy_exchange, sell_exchange,
                        buy_price, sell_price, gross_profit_percent,
                        net_profit_percent, executed
                    ) VALUES (
                        %(timestamp)s, %(symbol)s, %(buy_exchange)s, %(sell_exchange)s,
                        %(buy_price)s, %(sell_price)s, %(gross_profit_percent)s,
                        %(net_profit_percent)s, %(executed)s
                    ) RETURNING id
                """, opp_data)
                
                opp_id = cursor.fetchone()['id']
                return opp_id
        
        except Exception as e:
            logger.error(f"Error saving opportunity: {e}")
            raise
    
    def save_balance_snapshot(self, balances: List[Dict[str, Any]]):
        """Save balance snapshot"""
        try:
            with self.get_cursor() as cursor:
                for balance in balances:
                    cursor.execute("""
                        INSERT INTO balance_snapshots (
                            timestamp, exchange, asset, amount, value_usd
                        ) VALUES (
                            %(timestamp)s, %(exchange)s, %(asset)s,
                            %(amount)s, %(value_usd)s
                        )
                    """, balance)
        
        except Exception as e:
            logger.error(f"Error saving balance snapshot: {e}")
            raise
    
    def save_portfolio_snapshot(self, snapshot_data: Dict[str, Any]):
        """Save portfolio snapshot"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portfolio_snapshots (
                        timestamp, total_value_usd, allocation, rebalance_needed
                    ) VALUES (
                        %(timestamp)s, %(total_value_usd)s,
                        %(allocation)s::jsonb, %(rebalance_needed)s
                    )
                """, snapshot_data)
        
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
            raise
    
    def get_trades(
        self, 
        limit: int = 100, 
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get trade history"""
        try:
            with self.get_cursor() as cursor:
                query = "SELECT * FROM trades WHERE 1=1"
                params = {}
                
                if symbol:
                    query += " AND symbol = %(symbol)s"
                    params['symbol'] = symbol
                
                if start_date:
                    query += " AND timestamp >= %(start_date)s"
                    params['start_date'] = start_date
                
                query += " ORDER BY timestamp DESC LIMIT %(limit)s"
                params['limit'] = limit
                
                cursor.execute(query, params)
                return cursor.fetchall()
        
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def get_trade_statistics(self) -> Dict:
        """Get trade statistics"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN net_profit_usd > 0 THEN 1 END) as winning_trades,
                        SUM(net_profit_usd) as total_profit,
                        AVG(net_profit_percent) as avg_profit_percent,
                        AVG(execution_time_seconds) as avg_execution_time
                    FROM trades
                    WHERE status = 'completed'
                """)
                
                return dict(cursor.fetchone())
        
        except Exception as e:
            logger.error(f"Error fetching trade statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data"""
        try:
            with self.get_cursor() as cursor:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                cursor.execute("DELETE FROM arbitrage_opportunities WHERE timestamp < %s", (cutoff_date,))
                cursor.execute("DELETE FROM balance_snapshots WHERE timestamp < %s", (cutoff_date,))
                
                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old records")
        
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")

