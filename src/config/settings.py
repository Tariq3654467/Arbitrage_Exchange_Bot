"""
Configuration Settings Manager
Handles loading and validation of all bot configuration
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BotConfig(BaseModel):
    """General bot configuration"""
    name: str
    version: str
    paper_trading: bool = True


class TradingConfig(BaseModel):
    """Trading parameters configuration"""
    min_profit_threshold: float = Field(gt=0, description="Minimum profit % to execute")
    max_trade_size_percent: float = Field(gt=0, le=100)
    max_slippage_percent: float = Field(gt=0, le=100)
    order_timeout_seconds: int = Field(gt=0)
    retry_attempts: int = Field(ge=1)
    auto_discover_pairs: bool = Field(default=True, description="Automatically discover trading pairs from exchanges")
    max_discovered_pairs: int = Field(default=200, ge=1, le=1000, description="Maximum number of pairs to auto-discover")
    preferred_quote_currencies: List[str] = Field(default_factory=lambda: ['USDT', 'FDUSD', 'BTC', 'ETH', 'BUSD', 'USDC'], description="Prioritize pairs with these quote currencies")


class RiskConfig(BaseModel):
    """Risk management configuration"""
    max_drawdown_percent: float = Field(gt=0)
    max_daily_loss_percent: float = Field(gt=0)
    max_position_size_usd: float = Field(gt=0)
    emergency_stop_enabled: bool = True


class ExchangeConfig(BaseModel):
    """Individual exchange configuration"""
    name: str
    enabled: bool = True
    testnet: bool = False  # Use testnet/sandbox mode
    order_type: str = "market"
    max_latency_ms: int = 50
    websocket_enabled: bool = False


class DEXConfig(BaseModel):
    """DEX specific configuration"""
    name: str
    enabled: bool = True
    chain: str
    router_address: Optional[str] = None
    factory_address: Optional[str] = None


class NetworkConfig(BaseModel):
    """Blockchain network configuration"""
    chain_id: int
    gas_price_strategy: str = "fast"
    max_gas_price_gwei: float


class TradingPair(BaseModel):
    """Trading pair configuration"""
    symbol: str
    min_trade_amount: float
    enabled: bool = True


class RebalancingConfig(BaseModel):
    """Rebalancing configuration"""
    enabled: bool = True
    check_interval_minutes: int = 60
    target_allocation: Dict[str, float]
    rebalance_threshold_percent: float = 10


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration"""
    dashboard_enabled: bool = True
    dashboard_port: int = 3000
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    alerts: Dict[str, Any]


class Settings(BaseSettings):
    """Main settings class combining all configurations"""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # CEX API Keys
    binance_api_key: str = Field(default="", env="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", env="BINANCE_API_SECRET")
    binance_testnet: bool = Field(default=False, env="BINANCE_TESTNET")
    
    okx_api_key: str = Field(default="", env="OKX_API_KEY")
    okx_api_secret: str = Field(default="", env="OKX_API_SECRET")
    okx_passphrase: str = Field(default="", env="OKX_PASSPHRASE")
    okx_testnet: bool = Field(default=False, env="OKX_TESTNET")
    
    bybit_api_key: str = Field(default="", env="BYBIT_API_KEY")
    bybit_api_secret: str = Field(default="", env="BYBIT_API_SECRET")
    bybit_testnet: bool = Field(default=False, env="BYBIT_TESTNET")
    
    mexc_api_key: str = Field(default="", env="MEXC_API_KEY")
    mexc_api_secret: str = Field(default="", env="MEXC_API_SECRET")
    mexc_testnet: bool = Field(default=False, env="MEXC_TESTNET")
    
    # Gala Chain (for Galaswap API)
    gala_wallet_address: str = Field(default="", env="GALA_WALLET_ADDRESS")
    gala_private_key: str = Field(default="", env="GALA_PRIVATE_KEY")
    gala_public_key: str = Field(default="", env="GALA_PUBLIC_KEY")
    
    # Web3 Private Keys
    eth_private_key: str = Field(default="", env="ETH_PRIVATE_KEY")
    bsc_private_key: str = Field(default="", env="BSC_PRIVATE_KEY")
    polygon_private_key: str = Field(default="", env="POLYGON_PRIVATE_KEY")
    
    # RPC Endpoints
    eth_rpc_url: str = Field(default="", env="ETH_RPC_URL")
    bsc_rpc_url: str = Field(default="https://bsc-dataseed1.binance.org/", env="BSC_RPC_URL")
    polygon_rpc_url: str = Field(default="https://polygon-rpc.com/", env="POLYGON_RPC_URL")
    gala_rpc_url: str = Field(default="https://jsonrpc.gala.games", env="GALA_RPC_URL")
    
    # Database
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="arbitrage_bot", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="", env="POSTGRES_PASSWORD")
    
    influxdb_url: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(default="", env="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="arbitrage_org", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="price_data", env="INFLUXDB_BUCKET")
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    
    # Monitoring
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
    sendgrid_api_key: str = Field(default="", env="SENDGRID_API_KEY")
    alert_email: str = Field(default="", env="ALERT_EMAIL")
    
    # Security
    encryption_key: str = Field(default="", env="ENCRYPTION_KEY")
    allowed_ips: str = Field(default="", env="ALLOWED_IPS")
    
    # Trading Parameters from ENV (can override config file)
    min_profit_threshold: Optional[float] = Field(default=None, env="MIN_PROFIT_THRESHOLD")
    max_trade_size_percent: Optional[float] = Field(default=None, env="MAX_TRADE_SIZE_PERCENT")
    max_slippage_percent: Optional[float] = Field(default=None, env="MAX_SLIPPAGE_PERCENT")
    max_drawdown_percent: Optional[float] = Field(default=None, env="MAX_DRAWDOWN_PERCENT")
    
    # Configuration objects (loaded from YAML)
    bot: Optional[BotConfig] = None
    trading: Optional[TradingConfig] = None
    risk: Optional[RiskConfig] = None
    exchanges: Optional[Dict[str, List[Any]]] = None
    networks: Optional[Dict[str, NetworkConfig]] = None
    trading_pairs: Optional[List[TradingPair]] = None
    rebalancing: Optional[RebalancingConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    storage: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def load_yaml_config(self, config_path: str = "config/config.yaml"):
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Parse configuration sections
        if 'bot' in config_data:
            self.bot = BotConfig(**config_data['bot'])
        
        if 'trading' in config_data:
            self.trading = TradingConfig(**config_data['trading'])
            # Override with ENV vars if set
            if self.min_profit_threshold is not None:
                self.trading.min_profit_threshold = self.min_profit_threshold
            if self.max_trade_size_percent is not None:
                self.trading.max_trade_size_percent = self.max_trade_size_percent
            if self.max_slippage_percent is not None:
                self.trading.max_slippage_percent = self.max_slippage_percent
        
        if 'risk' in config_data:
            self.risk = RiskConfig(**config_data['risk'])
            if self.max_drawdown_percent is not None:
                self.risk.max_drawdown_percent = self.max_drawdown_percent
        
        if 'exchanges' in config_data:
            self.exchanges = config_data['exchanges']
        
        if 'networks' in config_data:
            self.networks = {
                name: NetworkConfig(**cfg) 
                for name, cfg in config_data['networks'].items()
            }
        
        if 'trading_pairs' in config_data:
            self.trading_pairs = [TradingPair(**pair) for pair in config_data['trading_pairs']]
        
        if 'rebalancing' in config_data:
            self.rebalancing = RebalancingConfig(**config_data['rebalancing'])
        
        if 'monitoring' in config_data:
            self.monitoring = MonitoringConfig(**config_data['monitoring'])
        
        if 'storage' in config_data:
            self.storage = config_data['storage']
        
        if 'performance' in config_data:
            self.performance = config_data['performance']
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL"""
        from urllib.parse import quote_plus
        # URL-encode password to handle special characters like /, =, +, etc.
        encoded_password = quote_plus(self.postgres_password)
        return f"postgresql://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"
    
    def get_cex_exchanges(self) -> List[ExchangeConfig]:
        """Get enabled CEX exchanges"""
        if not self.exchanges or 'cex' not in self.exchanges:
            return []
        return [ExchangeConfig(**ex) for ex in self.exchanges['cex'] if ex.get('enabled', True)]
    
    def get_dex_exchanges(self) -> List[DEXConfig]:
        """Get enabled DEX exchanges"""
        if not self.exchanges or 'dex' not in self.exchanges:
            return []
        return [DEXConfig(**ex) for ex in self.exchanges['dex'] if ex.get('enabled', True)]
    
    def get_enabled_trading_pairs(self) -> List[TradingPair]:
        """Get list of enabled trading pairs"""
        if not self.trading_pairs:
            return []
        return [pair for pair in self.trading_pairs if pair.enabled]
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"
    
    def validate_required_keys(self):
        """Validate that all required API keys are set"""
        errors = []
        
        # Check CEX exchanges
        for exchange in self.get_cex_exchanges():
            if exchange.name == "binance":
                if not self.binance_api_key or not self.binance_api_secret:
                    errors.append("Binance API keys are required")
            elif exchange.name == "mexc":
                if not self.mexc_api_key or not self.mexc_api_secret:
                    errors.append("MEXC API keys are required")
        
        # Check DEX exchanges
        for dex in self.get_dex_exchanges():
            if dex.chain == "ethereum" and not self.eth_private_key:
                errors.append("Ethereum private key is required")
            elif dex.chain == "bsc" and not self.bsc_private_key:
                errors.append("BSC private key is required")
            elif dex.chain == "polygon" and not self.polygon_private_key:
                errors.append("Polygon private key is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(config_path: str = "config/config.yaml") -> Settings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.load_yaml_config(config_path)
    return _settings


def reload_settings(config_path: str = "config/config.yaml") -> Settings:
    """Reload settings from configuration files"""
    global _settings
    _settings = Settings()
    _settings.load_yaml_config(config_path)
    return _settings

