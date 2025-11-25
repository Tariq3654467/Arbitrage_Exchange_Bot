"""
Main Arbitrage Bot
Orchestrates all components and manages the trading loop
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from .config.settings import get_settings
from .utils.logger import get_logger
from .exchanges.base_exchange import BaseExchange
from .exchanges.cex.binance_connector import BinanceConnector
from .exchanges.cex.okx_connector import OKXConnector
from .exchanges.cex.bybit_connector import BybitConnector
from .exchanges.dex.pancakeswap_connector import PancakeSwapConnector
from .exchanges.dex.uniswap_connector import UniswapConnector
from .arbitrage.price_monitor import PriceMonitor, ArbitrageOpportunity
from .arbitrage.arbitrage_calculator import ArbitrageCalculator
from .arbitrage.trade_executor import TradeExecutor
from .risk.risk_manager import RiskManager
from .risk.portfolio_manager import PortfolioManager
from .database.postgres_manager import PostgresManager
from .database.influxdb_manager import InfluxDBManager
from .monitoring.alert_manager import AlertManager, AlertLevel

logger = get_logger()


class ArbitrageBot:
    """Main arbitrage bot orchestrator"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize arbitrage bot
        
        Args:
            config_path: Path to configuration file
        """
        logger.info("=" * 60)
        logger.info("Initializing Arbitrage Cross-Exchange Bot")
        logger.info("=" * 60)
        
        # Load configuration
        self.settings = get_settings(config_path)
        logger.info(f"Configuration loaded from {config_path}")
        
        # Initialize components
        self.exchanges: Dict[str, BaseExchange] = {}
        self.price_monitor: Optional[PriceMonitor] = None
        self.arbitrage_calculator: Optional[ArbitrageCalculator] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.risk_manager: Optional[RiskManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.postgres_db: Optional[PostgresManager] = None
        self.influxdb: Optional[InfluxDBManager] = None
        self.alert_manager: Optional[AlertManager] = None
        
        # Bot state
        self.is_running = False
        self.start_time = None
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("Initializing bot components...")
            
            # Initialize exchanges
            await self._initialize_exchanges()
            
            # Initialize databases
            self._initialize_databases()
            
            # Initialize alert manager
            self._initialize_alert_manager()
            
            # Initialize risk management
            self._initialize_risk_management()
            
            # Initialize arbitrage components
            self._initialize_arbitrage_components()
            
            logger.info("✓ All components initialized successfully")
            
            # Send startup alert
            await self.alert_manager.send_alert(
                "Bot initialized and ready to start trading",
                level=AlertLevel.INFO
            )
        
        except Exception as e:
            logger.critical(f"Failed to initialize bot: {e}", exc_info=True)
            raise
    
    async def _initialize_exchanges(self):
        """Initialize exchange connectors"""
        logger.info("Connecting to exchanges...")
        
        # CEX exchanges
        for exchange_config in self.settings.get_cex_exchanges():
            try:
                if exchange_config.name == "binance":
                    connector = BinanceConnector(
                        api_key=self.settings.binance_api_key,
                        api_secret=self.settings.binance_api_secret,
                        testnet=self.settings.binance_testnet
                    )
                elif exchange_config.name == "okx":
                    connector = OKXConnector(
                        api_key=self.settings.okx_api_key,
                        api_secret=self.settings.okx_api_secret,
                        passphrase=self.settings.okx_passphrase,
                        testnet=self.settings.okx_testnet
                    )
                elif exchange_config.name == "bybit":
                    connector = BybitConnector(
                        api_key=self.settings.bybit_api_key,
                        api_secret=self.settings.bybit_api_secret,
                        testnet=self.settings.bybit_testnet
                    )
                else:
                    logger.warning(f"Unknown CEX: {exchange_config.name}")
                    continue
                
                await connector.connect()
                self.exchanges[exchange_config.name] = connector
                logger.info(f"✓ Connected to {exchange_config.name}")
            
            except Exception as e:
                logger.error(f"Failed to connect to {exchange_config.name}: {e}")
        
        # DEX exchanges
        for dex_config in self.settings.get_dex_exchanges():
            try:
                if dex_config.name == "pancakeswap":
                    connector = PancakeSwapConnector(
                        rpc_url=self.settings.bsc_rpc_url,
                        private_key=self.settings.bsc_private_key,
                        router_address=dex_config.router_address,
                        factory_address=dex_config.factory_address
                    )
                elif dex_config.name in ["uniswap_v2", "quickswap"]:
                    chain = dex_config.chain
                    if chain == "ethereum":
                        rpc_url = self.settings.eth_rpc_url
                        private_key = self.settings.eth_private_key
                    elif chain == "polygon":
                        rpc_url = self.settings.polygon_rpc_url
                        private_key = self.settings.polygon_private_key
                    else:
                        logger.warning(f"Unsupported chain for {dex_config.name}: {chain}")
                        continue
                    
                    connector = UniswapConnector(
                        chain=chain,
                        rpc_url=rpc_url,
                        private_key=private_key,
                        router_address=dex_config.router_address,
                        factory_address=dex_config.factory_address
                    )
                else:
                    logger.warning(f"Unknown DEX: {dex_config.name}")
                    continue
                
                await connector.connect()
                self.exchanges[dex_config.name] = connector
                logger.info(f"✓ Connected to {dex_config.name}")
            
            except Exception as e:
                logger.error(f"Failed to connect to {dex_config.name}: {e}")
        
        if not self.exchanges:
            raise Exception("No exchanges connected")
        
        logger.info(f"Connected to {len(self.exchanges)} exchanges")
    
    def _initialize_databases(self):
        """Initialize database connections"""
        logger.info("Connecting to databases...")
        
        # PostgreSQL
        try:
            self.postgres_db = PostgresManager(self.settings.postgres_url)
            self.postgres_db.connect()
            logger.info("✓ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
        
        # InfluxDB
        try:
            self.influxdb = InfluxDBManager(
                url=self.settings.influxdb_url,
                token=self.settings.influxdb_token,
                org=self.settings.influxdb_org,
                bucket=self.settings.influxdb_bucket
            )
            self.influxdb.connect()
            logger.info("✓ Connected to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
    
    def _initialize_alert_manager(self):
        """Initialize alert manager"""
        logger.info("Initializing alert manager...")
        
        monitoring_config = self.settings.monitoring
        
        self.alert_manager = AlertManager(
            telegram_enabled=monitoring_config.alerts.get('telegram_enabled', False),
            telegram_bot_token=self.settings.telegram_bot_token,
            telegram_chat_id=self.settings.telegram_chat_id,
            email_enabled=monitoring_config.alerts.get('email_enabled', False),
            sendgrid_api_key=self.settings.sendgrid_api_key,
            from_email=self.settings.alert_email,
            to_email=self.settings.alert_email,
            alert_on_trade=monitoring_config.alerts.get('alert_on_trade', True),
            alert_on_error=monitoring_config.alerts.get('alert_on_error', True),
            alert_on_high_profit=monitoring_config.alerts.get('alert_on_high_profit', True),
            high_profit_threshold=monitoring_config.alerts.get('high_profit_threshold', 2.0)
        )
    
    def _initialize_risk_management(self):
        """Initialize risk management components"""
        logger.info("Initializing risk management...")
        
        # Risk manager
        self.risk_manager = RiskManager(
            initial_capital=100000,  # TODO: Get from config or calculate from balances
            max_drawdown_percent=self.settings.risk.max_drawdown_percent,
            max_daily_loss_percent=self.settings.risk.max_daily_loss_percent,
            max_position_size_usd=self.settings.risk.max_position_size_usd,
            max_trade_size_percent=self.settings.trading.max_trade_size_percent,
            emergency_stop_enabled=self.settings.risk.emergency_stop_enabled
        )
        
        # Portfolio manager
        self.portfolio_manager = PortfolioManager(
            exchanges=self.exchanges,
            target_allocation=self.settings.rebalancing.target_allocation,
            rebalance_threshold_percent=self.settings.rebalancing.rebalance_threshold_percent,
            rebalance_interval_minutes=self.settings.rebalancing.check_interval_minutes
        )
    
    def _initialize_arbitrage_components(self):
        """Initialize arbitrage components"""
        logger.info("Initializing arbitrage components...")
        
        # Get trading pairs
        trading_pairs = [pair.symbol for pair in self.settings.get_enabled_trading_pairs()]
        
        # Price monitor
        self.price_monitor = PriceMonitor(
            exchanges=self.exchanges,
            trading_pairs=trading_pairs,
            update_interval=self.settings.performance['price_update_interval_ms'] / 1000,
            min_profit_threshold=self.settings.trading.min_profit_threshold
        )
        
        # Add opportunity callback
        self.price_monitor.add_opportunity_callback(self._on_opportunity_found)
        
        # Arbitrage calculator
        self.arbitrage_calculator = ArbitrageCalculator(
            exchanges=self.exchanges,
            min_profit_threshold=self.settings.trading.min_profit_threshold,
            max_slippage=self.settings.trading.max_slippage_percent
        )
        
        # Trade executor
        self.trade_executor = TradeExecutor(
            exchanges=self.exchanges,
            paper_trading=self.settings.bot.paper_trading,
            max_concurrent_trades=self.settings.performance['max_concurrent_opportunities'],
            order_timeout=self.settings.trading.order_timeout_seconds
        )
    
    async def _on_opportunity_found(self, opportunity: ArbitrageOpportunity):
        """Callback when arbitrage opportunity is found"""
        try:
            logger.info(f"Opportunity found: {opportunity}")
            
            # Get current portfolio value
            portfolio_value = await self.portfolio_manager.get_total_portfolio_value()
            
            # Calculate trade size
            max_trade_size = self.risk_manager.get_max_trade_size(portfolio_value)
            trade_amount = min(max_trade_size, 1000)  # Use smaller amount for testing
            
            # Analyze opportunity
            analysis = await self.arbitrage_calculator.analyze_opportunity(
                opportunity,
                trade_amount
            )
            
            # Save opportunity to database
            if self.postgres_db:
                try:
                    self.postgres_db.save_opportunity({
                        'timestamp': opportunity.timestamp,
                        'symbol': opportunity.symbol,
                        'buy_exchange': opportunity.buy_exchange,
                        'sell_exchange': opportunity.sell_exchange,
                        'buy_price': opportunity.buy_price,
                        'sell_price': opportunity.sell_price,
                        'gross_profit_percent': opportunity.gross_profit_percent,
                        'net_profit_percent': analysis.net_profit_percent,
                        'executed': False
                    })
                except Exception as e:
                    logger.error(f"Error saving opportunity: {e}")
            
            # Write to InfluxDB
            if self.influxdb:
                try:
                    self.influxdb.write_opportunity(
                        symbol=opportunity.symbol,
                        buy_exchange=opportunity.buy_exchange,
                        sell_exchange=opportunity.sell_exchange,
                        gross_profit_percent=opportunity.gross_profit_percent,
                        net_profit_percent=analysis.net_profit_percent
                    )
                except Exception as e:
                    logger.error(f"Error writing opportunity to InfluxDB: {e}")
            
            # Check if trade is allowed
            allowed, reason = self.risk_manager.check_trade_allowed(analysis, portfolio_value)
            
            if not allowed:
                logger.info(f"Trade not allowed: {reason}")
                return
            
            if not analysis.is_profitable:
                logger.info(f"Trade not profitable enough: {analysis.net_profit_percent:.2f}%")
                return
            
            # Execute trade
            logger.info(f"Executing trade: {analysis.opportunity}")
            result = await self.trade_executor.execute_trade(analysis)
            
            # Process trade result
            if result.is_successful:
                # Record trade in risk manager
                new_portfolio_value = portfolio_value + result.actual_profit_usd
                self.risk_manager.record_trade(
                    result.actual_profit_usd,
                    result.actual_profit_percent,
                    new_portfolio_value
                )
                
                # Send alert
                await self.alert_manager.alert_trade_executed(
                    symbol=opportunity.symbol,
                    buy_exchange=opportunity.buy_exchange,
                    sell_exchange=opportunity.sell_exchange,
                    profit_usd=result.actual_profit_usd,
                    profit_percent=result.actual_profit_percent,
                    amount=analysis.buy_amount
                )
                
                # Save to database
                if self.postgres_db:
                    try:
                        self.postgres_db.save_trade({
                            'timestamp': result.timestamp,
                            'symbol': opportunity.symbol,
                            'buy_exchange': opportunity.buy_exchange,
                            'sell_exchange': opportunity.sell_exchange,
                            'buy_price': opportunity.buy_price,
                            'sell_price': opportunity.sell_price,
                            'amount': analysis.buy_amount,
                            'gross_profit_usd': analysis.gross_profit_usd,
                            'net_profit_usd': result.actual_profit_usd,
                            'net_profit_percent': result.actual_profit_percent,
                            'total_fees_usd': analysis.total_fees_usd,
                            'status': result.status.value,
                            'buy_order_id': result.buy_order.order_id if result.buy_order else None,
                            'sell_order_id': result.sell_order.order_id if result.sell_order else None,
                            'execution_time_seconds': result.execution_time,
                            'paper_trade': self.settings.bot.paper_trading
                        })
                    except Exception as e:
                        logger.error(f"Error saving trade: {e}")
        
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}", exc_info=True)
            await self.alert_manager.alert_error(f"Error processing opportunity: {e}")
    
    async def start(self):
        """Start the bot"""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        mode = "PAPER TRADING" if self.settings.bot.paper_trading else "LIVE TRADING"
        logger.info("=" * 60)
        logger.info(f"STARTING BOT IN {mode} MODE")
        logger.info("=" * 60)
        
        try:
            # Start price monitoring
            await self.price_monitor.start()
            
            logger.info("✓ Bot is now running")
            logger.info("Press Ctrl+C to stop")
            
            # Keep bot running
            while self.is_running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.critical(f"Critical error in bot: {e}", exc_info=True)
            await self.alert_manager.alert_error(f"Critical error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot"""
        if not self.is_running:
            return
        
        logger.info("Stopping bot...")
        self.is_running = False
        
        # Stop price monitoring
        if self.price_monitor:
            await self.price_monitor.stop()
        
        # Disconnect exchanges
        for name, exchange in self.exchanges.items():
            try:
                await exchange.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {name}: {e}")
        
        # Disconnect databases
        if self.postgres_db:
            self.postgres_db.disconnect()
        
        if self.influxdb:
            self.influxdb.disconnect()
        
        # Send shutdown alert
        if self.alert_manager:
            await self.alert_manager.send_alert(
                "Bot stopped",
                level=AlertLevel.INFO
            )
        
        logger.info("Bot stopped")
    
    def get_status(self) -> Dict:
        """Get bot status"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'paper_trading': self.settings.bot.paper_trading,
            'exchanges_connected': len(self.exchanges),
            'price_monitor_stats': self.price_monitor.get_statistics() if self.price_monitor else {},
            'trade_stats': self.trade_executor.get_trade_statistics() if self.trade_executor else {},
            'risk_stats': self.risk_manager.get_statistics() if self.risk_manager else {},
            'portfolio_stats': self.portfolio_manager.get_statistics() if self.portfolio_manager else {}
        }


async def main():
    """Main entry point"""
    bot = ArbitrageBot()
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

