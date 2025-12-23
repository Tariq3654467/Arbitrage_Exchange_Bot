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
from .exchanges.cex.mexc_connector import MEXCConnector
from .exchanges.dex.galaswap_connector import GalaswapConnector
from .arbitrage.price_monitor import PriceMonitor, ArbitrageOpportunity
from .arbitrage.arbitrage_calculator import ArbitrageCalculator
from .arbitrage.trade_executor import TradeExecutor
from .arbitrage.circular_arbitrage import CircularArbitrageFinder
from .arbitrage.circular_executor import CircularTradeExecutor
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
        self.circular_finder: Optional[CircularArbitrageFinder] = None
        self.circular_executor: Optional[CircularTradeExecutor] = None
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
            await self._initialize_arbitrage_components()
            
            # Update initial capital from actual portfolio balances
            await self._update_initial_capital_from_balances()
            
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
        
        # CEX exchanges from config
        for exchange_config in self.settings.get_cex_exchanges():
            try:
                # Use testnet from config if set, otherwise fall back to environment variable
                if exchange_config.name == "binance":
                    testnet = exchange_config.testnet if hasattr(exchange_config, 'testnet') else self.settings.binance_testnet
                    connector = BinanceConnector(
                        api_key=self.settings.binance_api_key,
                        api_secret=self.settings.binance_api_secret,
                        testnet=testnet
                    )
                elif exchange_config.name == "mexc":
                    testnet = exchange_config.testnet if hasattr(exchange_config, 'testnet') else self.settings.mexc_testnet
                    connector = MEXCConnector(
                        api_key=self.settings.mexc_api_key,
                        api_secret=self.settings.mexc_api_secret,
                        testnet=testnet
                    )
                else:
                    logger.warning(f"Unknown CEX: {exchange_config.name}")
                    continue
                
                await connector.connect()
                self.exchanges[exchange_config.name] = connector
                logger.info(f"✓ Connected to {exchange_config.name}")
            
            except Exception as e:
                logger.error(f"Failed to connect to {exchange_config.name}: {e}")

        # Also support session-only API keys that were injected into settings
        # even if the YAML config has exchanges disabled.
        try:
            if (
                'binance' not in self.exchanges
                and self.settings.binance_api_key
                and self.settings.binance_api_secret
            ):
                connector = BinanceConnector(
                    api_key=self.settings.binance_api_key,
                    api_secret=self.settings.binance_api_secret,
                    testnet=self.settings.binance_testnet,
                )
                await connector.connect()
                self.exchanges['binance'] = connector
                logger.info("✓ Connected to binance (from in-memory API keys)")

            if (
                'mexc' not in self.exchanges
                and self.settings.mexc_api_key
                and self.settings.mexc_api_secret
            ):
                connector = MEXCConnector(
                    api_key=self.settings.mexc_api_key,
                    api_secret=self.settings.mexc_api_secret,
                    testnet=self.settings.mexc_testnet,
                )
                await connector.connect()
                self.exchanges['mexc'] = connector
                logger.info("✓ Connected to mexc (from in-memory API keys)")
        except Exception as e:
            logger.error(f"Failed to connect using in-memory API keys: {e}")
        
        # DEX exchanges
        for dex_config in self.settings.get_dex_exchanges():
            try:
                if dex_config.name == "galaswap":
                    # Galaswap uses GalaConnect API, not Web3
                    # Need wallet address and private key from settings
                    wallet_address = self.settings.gala_wallet_address
                    private_key = self.settings.gala_private_key
                    public_key = self.settings.gala_public_key or None
                    
                    if not wallet_address or not private_key:
                        logger.warning(f"Gala wallet address and private key required for Galaswap")
                        continue
                    
                    # Validate private key format before creating connector
                    private_key_clean = private_key.strip()
                    if private_key_clean.startswith('0x'):
                        private_key_clean = private_key_clean[2:]
                    
                    # Basic validation
                    if len(private_key_clean) != 64:
                        logger.error(
                            f"Invalid Gala private key length: expected 64 hex characters, "
                            f"got {len(private_key_clean)}. Please check your configuration."
                        )
                        continue
                    
                    try:
                        # Validate hex format
                        int(private_key_clean, 16)
                    except ValueError:
                        logger.error(
                            f"Invalid Gala private key format: contains non-hexadecimal characters. "
                            f"Private key must be 64 hex characters (with or without 0x prefix)."
                        )
                        continue
                    
                    try:
                        connector = GalaswapConnector(
                            wallet_address=wallet_address,
                            private_key=private_key,
                            public_key=public_key,
                            rpc_url=self.settings.gala_rpc_url
                        )
                    except ValueError as e:
                        logger.error(f"Failed to initialize Galaswap connector: {e}")
                        continue
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
            # Use individual parameters to avoid connection string parsing issues with special characters
            self.postgres_db = PostgresManager(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                database=self.settings.postgres_db,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password
            )
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
        
        # Portfolio manager (initialize first to calculate initial capital)
        self.portfolio_manager = PortfolioManager(
            exchanges=self.exchanges,
            target_allocation=self.settings.rebalancing.target_allocation,
            rebalance_threshold_percent=self.settings.rebalancing.rebalance_threshold_percent,
            rebalance_interval_minutes=self.settings.rebalancing.check_interval_minutes
        )
        
        # Calculate initial capital from actual balances
        # Use a default value if calculation fails (for initial startup)
        initial_capital = 100000.0  # Default fallback
        
        # Risk manager
        self.risk_manager = RiskManager(
            initial_capital=initial_capital,  # Will be updated after portfolio snapshot
            max_drawdown_percent=self.settings.risk.max_drawdown_percent,
            max_daily_loss_percent=self.settings.risk.max_daily_loss_percent,
            max_position_size_usd=self.settings.risk.max_position_size_usd,
            max_trade_size_percent=self.settings.trading.max_trade_size_percent,
            emergency_stop_enabled=self.settings.risk.emergency_stop_enabled
        )
    
    async def _initialize_arbitrage_components(self):
        """Initialize arbitrage components"""
        logger.info("Initializing arbitrage components...")
        
        # Get configured trading pairs
        configured_pairs = [pair.symbol for pair in self.settings.get_enabled_trading_pairs()]
        
        # Get auto-discovery settings
        auto_discover = getattr(self.settings.trading, 'auto_discover_pairs', True)
        max_pairs = getattr(self.settings.trading, 'max_discovered_pairs', 200)
        preferred_quotes = getattr(self.settings.trading, 'preferred_quote_currencies', ['USDT', 'FDUSD', 'BTC', 'ETH', 'BUSD', 'USDC'])
        
        # Start with configured pairs (always included)
        all_available_pairs = set(configured_pairs)
        discovered_pairs = []
        
        if auto_discover:
            logger.info(f"Discovering available trading pairs from Galaswap only (max total: {max_pairs})...")
            # Collect all candidate pairs from Galaswap only
            all_candidate_pairs = []
            
            for exchange_name, exchange in self.exchanges.items():
                if not exchange.is_connected:
                    continue
                
                # Only auto-discover from Galaswap - skip all other exchanges
                if exchange_name != 'galaswap':
                    logger.info(f"Skipping auto-discovery for {exchange_name} - using only configured pairs")
                    continue
                    
                try:
                    # For Galaswap, discover pairs from balances and common Gala Chain tokens
                    if exchange_name == 'galaswap':
                        try:
                            discovered_symbols = set()
                            
                            # Common Gala Chain tokens that should always be included
                            common_gala_tokens = ['GALA', 'GUSDT', 'GUSDC', 'GWETH']
                            
                            # Try to get balances to discover available tokens
                            try:
                                balances = await exchange.get_balance()
                                # Extract unique tokens from balances (balances is a dict: symbol -> Balance object)
                                for symbol_key, balance_obj in balances.items():
                                    if balance_obj and symbol_key:
                                        # Use the symbol key directly (it's the collection code like "GALA", "GUSDT", etc.)
                                        asset_upper = symbol_key.upper()
                                        
                                        # Add to common tokens if not already there
                                        if asset_upper not in common_gala_tokens:
                                            common_gala_tokens.append(asset_upper)
                            except Exception as e:
                                logger.debug(f"Could not fetch balances for pair discovery: {e}")
                                # Continue with common tokens anyway
                            
                            # Create pairs for all discovered tokens with preferred quote currencies
                            for base_token in common_gala_tokens:
                                for quote in preferred_quotes:
                                    # Skip same token pairs
                                    if base_token == quote:
                                        continue
                                    symbol = f"{base_token}/{quote}"
                                    if symbol not in all_available_pairs:
                                        discovered_symbols.add(symbol)
                            
                            # Also create reverse pairs (quote/base) for liquidity
                            for quote in preferred_quotes:
                                for base_token in common_gala_tokens:
                                    if base_token == quote:
                                        continue
                                    symbol = f"{quote}/{base_token}"
                                    if symbol not in all_available_pairs:
                                        discovered_symbols.add(symbol)
                            
                            # Add discovered pairs with priority
                            for symbol in discovered_symbols:
                                priority = 100  # Higher priority for Galaswap pairs
                                all_candidate_pairs.append((symbol, priority, exchange_name))
                            
                            logger.info(f"Discovered {len(discovered_symbols)} pairs from {exchange_name} (including GALA, GUSDT, GUSDC, GWETH)")
                        except Exception as e:
                            logger.warning(f"Could not discover pairs from {exchange_name}: {e}")
                            logger.info(f"Using configured pairs for {exchange_name}")
                            pass
                except Exception as e:
                    logger.warning(f"Error discovering pairs from {exchange_name}: {e}")
            
            # Sort all candidates by priority and take top N globally
            all_candidate_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Track which exchange each pair came from (for filtering later)
            # symbol -> list of exchanges that support it
            symbol_exchange_map = {}
            
            # Remove duplicates (keep highest priority version) but track all exchanges
            seen_symbols = {}
            for symbol, priority, exchange_name in all_candidate_pairs:
                if symbol not in symbol_exchange_map:
                    symbol_exchange_map[symbol] = []
                if exchange_name not in symbol_exchange_map[symbol]:
                    symbol_exchange_map[symbol].append(exchange_name)
                
                if symbol not in seen_symbols or priority > seen_symbols[symbol][1]:
                    seen_symbols[symbol] = (priority, exchange_name)
            
            # Get top pairs (excluding already configured ones)
            top_pairs = []
            for symbol, (priority, exchange_name) in seen_symbols.items():
                if symbol not in all_available_pairs:
                    top_pairs.append((symbol, priority))
            
            # Sort by priority and take top N
            top_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Add discovered pairs without validation (validation happens during monitoring)
            # This prevents blocking initialization with slow API calls
            for symbol, _ in top_pairs[:max_pairs]:
                if symbol not in all_available_pairs:
                    discovered_pairs.append(symbol)
                    all_available_pairs.add(symbol)
            
            logger.info(f"Added {len(discovered_pairs)} discovered pairs (validation will happen during monitoring)")
            
            # Store symbol-to-exchange mapping for price monitor
            self.symbol_exchange_map = symbol_exchange_map
            
            logger.info(f"Selected {len(discovered_pairs)} top pairs from {len(seen_symbols)} unique candidates")
        else:
            logger.info("Auto-discovery disabled - using only configured pairs")
            # Initialize empty map if auto-discovery is disabled
            self.symbol_exchange_map = {}
        
        # Convert to list and log
        trading_pairs = sorted(list(all_available_pairs))
        logger.info(f"Total trading pairs to monitor: {len(trading_pairs)} (configured: {len(configured_pairs)}, discovered: {len(discovered_pairs)})")
        
        if len(trading_pairs) > 300:
            logger.warning(f"Monitoring {len(trading_pairs)} pairs - this may cause high API usage and file descriptor issues on Windows. Consider reducing max_discovered_pairs in config.")
        
        # Price monitor
        # min_profit_threshold: for trade execution
        # min_display_threshold: for showing opportunities in dashboard (0.01% = show all)
        # Pass symbol_exchange_map to filter pairs by exchange
        symbol_exchange_map = getattr(self, 'symbol_exchange_map', {})
        self.price_monitor = PriceMonitor(
            exchanges=self.exchanges,
            trading_pairs=trading_pairs,
            update_interval=self.settings.performance['price_update_interval_ms'] / 1000,
            min_profit_threshold=self.settings.trading.min_profit_threshold,
            min_display_threshold=0.01,  # Show all opportunities >= 0.01% in dashboard
            symbol_exchange_map=symbol_exchange_map  # Map of symbol -> list of exchanges that support it
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
        
        # Circular arbitrage finder and executor
        self.circular_finder = CircularArbitrageFinder(
            exchanges=self.exchanges,
            price_data={},  # Will be updated from price monitor
            min_profit_threshold=self.settings.trading.min_profit_threshold
        )
        
        self.circular_executor = CircularTradeExecutor(
            exchanges=self.exchanges,
            paper_trading=self.settings.bot.paper_trading,
            order_timeout=self.settings.trading.order_timeout_seconds
        )
        
        logger.info("✓ Arbitrage components initialized successfully")
    
    async def _update_initial_capital_from_balances(self):
        """Update initial capital in risk manager from actual portfolio balances"""
        try:
            if not self.portfolio_manager:
                logger.warning("Portfolio manager not initialized, skipping capital update")
                return
            
            # Get portfolio snapshot to calculate total value
            snapshot = await self.portfolio_manager.get_portfolio_snapshot()
            total_value = snapshot.total_value_usd
            
            if total_value > 0:
                # Update risk manager with actual initial capital
                self.risk_manager.initial_capital = total_value
                self.risk_manager.current_capital = total_value
                self.risk_manager.peak_capital = total_value
                self.risk_manager.daily_start_capital = total_value
                
                logger.info(f"✓ Initial capital updated from balances: ${total_value:,.2f}")
            else:
                logger.warning(
                    f"Portfolio value is ${total_value:.2f}, using default initial capital. "
                    "This may indicate no balances found or price feeds not available."
                )
        except Exception as e:
            logger.error(f"Error updating initial capital from balances: {e}")
            logger.warning("Continuing with default initial capital")
    
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
            
            # Check if trade is allowed (only hard risk limits: size, drawdown, daily loss)
            allowed, reason = self.risk_manager.check_trade_allowed(analysis, portfolio_value)
            
            if not allowed:
                logger.info(f"Trade not allowed by risk manager: {reason}")
                return
            
            # Block trades with negative expected profit (aggressive mode disabled)
            # This prevents losses and reduces unnecessary API calls
            if not analysis.is_profitable:
                logger.info(
                    f"Trade blocked: Negative expected profit "
                    f"({analysis.net_profit_percent:.4f}%, ${analysis.net_profit_usd:.4f}). "
                    f"Not executing to prevent losses and reduce API rate limiting."
                )
                return
            
            # Execute trade (only profitable trades)
            logger.info(f"Executing profitable trade: {analysis.opportunity}")
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
    
    async def _monitor_circular_arbitrage(self):
        """Monitor for circular arbitrage opportunities"""
        check_interval = 10  # Check every 10 seconds
        
        while self.is_running:
            try:
                await asyncio.sleep(check_interval)
                
                # Update price data for circular finder
                if self.price_monitor:
                    self.circular_finder.price_data = self.price_monitor.current_prices
                
                # Find circular opportunities
                opportunities = await self.circular_finder.find_opportunities(
                    start_amount=1000.0  # Start with $1000 worth
                )
                
                if opportunities:
                    # Take the best opportunity
                    best_opportunity = opportunities[0]
                    logger.info(f"Found circular arbitrage opportunity: {best_opportunity}")
                    
                    # Get portfolio value for risk check
                    portfolio_value = await self.portfolio_manager.get_total_portfolio_value()
                    
                    # Calculate trade size (use smaller amount for circular trades)
                    max_trade_size = self.risk_manager.get_max_trade_size(portfolio_value)
                    trade_amount = min(max_trade_size * 0.5, 1000)  # Use 50% of max or $1000, whichever is smaller
                    
                    # Check if trade is allowed
                    # For circular trades, we need to check differently
                    # For now, just check basic risk limits
                    if trade_amount < 100:  # Minimum trade size
                        continue
                    
                    # Execute circular trade
                    logger.info(f"Executing circular arbitrage: {best_opportunity}")
                    result = await self.circular_executor.execute_circular_trade(
                        best_opportunity,
                        start_amount=trade_amount
                    )
                    
                    # Process result
                    if result.is_successful:
                        # Calculate profit in USD (approximate)
                        profit_usd = result.actual_profit * 0.05  # Rough estimate (GALA price)
                        
                        # Record trade
                        new_portfolio_value = portfolio_value + profit_usd
                        self.risk_manager.record_trade(
                            profit_usd,
                            result.actual_profit_percent,
                            new_portfolio_value
                        )
                        
                        # Send alert
                        await self.alert_manager.alert_trade_executed(
                            symbol=f"{best_opportunity.start_asset}_CIRCULAR",
                            buy_exchange="circular",
                            sell_exchange="circular",
                            profit_usd=profit_usd,
                            profit_percent=result.actual_profit_percent,
                            amount=result.actual_start_amount
                        )
                        
                        logger.info(
                            f"✓ Circular trade completed! "
                            f"Profit: {result.actual_profit:.6f} {best_opportunity.start_asset} "
                            f"({result.actual_profit_percent:.2f}%)"
                        )
                    else:
                        logger.warning(f"Circular trade failed: {result.error_message}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in circular arbitrage monitoring: {e}", exc_info=True)
                await asyncio.sleep(check_interval)
    
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
            
            # Start circular arbitrage monitoring
            circular_task = asyncio.create_task(self._monitor_circular_arbitrage())
            
            logger.info("✓ Bot is now running")
            logger.info("Press Ctrl+C to stop")
            
            # Keep bot running
            while self.is_running:
                await asyncio.sleep(1)
            
            # Cancel circular arbitrage task
            circular_task.cancel()
            try:
                await circular_task
            except asyncio.CancelledError:
                pass
        
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

