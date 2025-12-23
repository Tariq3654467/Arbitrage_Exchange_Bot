"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class BotStatus(BaseModel):
    """Bot status response"""
    is_running: bool
    uptime_seconds: float
    paper_trading: bool
    exchanges_connected: int
    message: Optional[str] = None


class ExchangeConfig(BaseModel):
    """Exchange configuration"""
    exchange_name: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    testnet: bool = False
    enabled: bool = True


class DEXConfig(BaseModel):
    """DEX exchange configuration"""
    exchange_name: str
    private_key: str
    wallet_address: Optional[str] = None  # For Galaswap
    rpc_url: Optional[str] = None
    router_address: Optional[str] = None
    factory_address: Optional[str] = None
    chain: Optional[str] = None  # 'bsc', 'ethereum', 'polygon', 'gala'
    enabled: bool = True


class StartBotRequest(BaseModel):
    """Optional API keys passed directly from dashboard (non-persistent)"""
    exchanges: Optional[List[ExchangeConfig]] = None


class TradingConfig(BaseModel):
    """Trading configuration"""
    min_profit_threshold: float = Field(gt=0, le=100)
    max_trade_size_percent: float = Field(gt=0, le=100)
    max_slippage_percent: float = Field(gt=0, le=100)
    order_timeout_seconds: int = Field(gt=0)
    paper_trading: Optional[bool] = None  # Optional, can be updated separately


class RiskConfig(BaseModel):
    """Risk management configuration"""
    max_drawdown_percent: float = Field(gt=0, le=100)
    max_daily_loss_percent: float = Field(gt=0, le=100)
    max_position_size_usd: float = Field(gt=0)
    emergency_stop_enabled: bool = True


class TradeHistory(BaseModel):
    """Trade history item"""
    timestamp: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    amount: float
    profit_usd: float
    profit_percent: float
    status: str


class OpportunityData(BaseModel):
    """Arbitrage opportunity data"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percent: float
    timestamp: datetime


class PortfolioData(BaseModel):
    """Portfolio data"""
    total_value_usd: float
    allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalance_needed: bool


class TestTradeRequest(BaseModel):
    """Manual test trade request (single execution)"""
    symbol: str  # e.g. "GALA/USDT"
    buy_exchange: str  # e.g. "galaswap" or "binance"
    sell_exchange: str  # e.g. "binance" or "galaswap"
    trade_amount_usd: float = Field(gt=0, description="Notional USD amount to trade")
    force_execute: Optional[bool] = Field(default=False, description="If True, bypass risk checks and execute even if unprofitable (for testing)")
    """Manual test trade request (single execution)"""
    symbol: str  # e.g. "GALA/USDT"
    buy_exchange: str  # e.g. "galaswap" or "binance"
    sell_exchange: str  # e.g. "binance" or "galaswap"
    trade_amount_usd: float = Field(gt=0, description="Notional USD amount to trade")
