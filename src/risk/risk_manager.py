"""
Risk Management System
Implements safety controls and risk limits
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..arbitrage.arbitrage_calculator import ProfitAnalysis
from ..utils.logger import get_logger

logger = get_logger()


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Current risk metrics"""
    portfolio_value_usd: float
    daily_pnl: float
    daily_pnl_percent: float
    drawdown_percent: float
    active_trades_count: int
    total_exposure_usd: float
    risk_level: RiskLevel
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class RiskManager:
    """Manages trading risks and safety controls"""
    
    def __init__(
        self,
        initial_capital: float,
        max_drawdown_percent: float = 20.0,
        max_daily_loss_percent: float = 5.0,
        max_position_size_usd: float = 10000,
        max_trade_size_percent: float = 10.0,
        emergency_stop_enabled: bool = True
    ):
        """
        Initialize risk manager
        
        Args:
            initial_capital: Initial capital in USD
            max_drawdown_percent: Maximum allowed drawdown
            max_daily_loss_percent: Maximum daily loss allowed
            max_position_size_usd: Maximum position size
            max_trade_size_percent: Maximum % of capital per trade
            emergency_stop_enabled: Enable emergency stop
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.max_drawdown_percent = max_drawdown_percent
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_position_size_usd = max_position_size_usd
        self.max_trade_size_percent = max_trade_size_percent
        self.emergency_stop_enabled = emergency_stop_enabled
        
        # State tracking
        self.is_trading_enabled = True
        self.emergency_stop_triggered = False
        
        # Daily tracking
        self.daily_start_capital = initial_capital
        self.daily_trade_count = 0
        self.daily_profit = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Trade history for risk assessment
        self.trade_history = []
        self.loss_streak = 0
        self.win_streak = 0
        
        logger.info(
            f"Risk manager initialized: "
            f"Capital=${initial_capital:.2f}, "
            f"Max Drawdown={max_drawdown_percent}%, "
            f"Max Daily Loss={max_daily_loss_percent}%"
        )
    
    def check_trade_allowed(
        self,
        analysis: ProfitAnalysis,
        current_portfolio_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a trade is allowed based on risk controls
        
        Args:
            analysis: Profit analysis for the trade
            current_portfolio_value: Current portfolio value
        
        Returns:
            Tuple of (allowed, reason_if_not_allowed)
        """
        # Check if trading is enabled
        if not self.is_trading_enabled:
            return False, "Trading is disabled"
        
        # Check if emergency stop is triggered
        if self.emergency_stop_triggered:
            return False, "Emergency stop is active"
        
        # Check drawdown
        drawdown = self.calculate_drawdown(current_portfolio_value)
        if drawdown >= self.max_drawdown_percent:
            self.trigger_emergency_stop("Max drawdown exceeded")
            return False, f"Max drawdown exceeded: {drawdown:.2f}%"
        
        # Check daily loss
        self._reset_daily_if_needed()
        daily_loss_percent = self.get_daily_loss_percent()
        if daily_loss_percent >= self.max_daily_loss_percent:
            self.disable_trading("Max daily loss exceeded")
            return False, f"Max daily loss exceeded: {daily_loss_percent:.2f}%"
        
        # Check trade size
        trade_amount = analysis.trade_amount
        max_allowed_size = current_portfolio_value * (self.max_trade_size_percent / 100)
        
        if trade_amount > max_allowed_size:
            return False, f"Trade size too large: ${trade_amount:.2f} > ${max_allowed_size:.2f}"
        
        if trade_amount > self.max_position_size_usd:
            return False, f"Trade size exceeds max position: ${trade_amount:.2f} > ${self.max_position_size_usd:.2f}"
        
        # NOTE: We DO NOT block trades based on expected profit here.
        # Profitability is handled separately; this allows executing even
        # slightly negative-expected trades for aggressive/testing modes.
        
        # All risk checks passed
        return True, None
    
    def record_trade(
        self,
        profit_usd: float,
        profit_percent: float,
        new_portfolio_value: float
    ):
        """Record a completed trade"""
        self._reset_daily_if_needed()
        
        # Update capital
        self.current_capital = new_portfolio_value
        self.peak_capital = max(self.peak_capital, new_portfolio_value)
        
        # Update daily metrics
        self.daily_trade_count += 1
        self.daily_profit += profit_usd
        
        # Track streaks
        if profit_usd > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        # Add to history
        self.trade_history.append({
            'timestamp': datetime.now(),
            'profit_usd': profit_usd,
            'profit_percent': profit_percent,
            'portfolio_value': new_portfolio_value
        })
        
        # Limit history size
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-500:]
        
        logger.info(
            f"Trade recorded: Profit ${profit_usd:.2f} ({profit_percent:.2f}%), "
            f"Portfolio: ${new_portfolio_value:.2f}"
        )
    
    def calculate_drawdown(self, current_value: float) -> float:
        """Calculate current drawdown percentage"""
        if self.peak_capital == 0:
            return 0.0
        
        drawdown = ((self.peak_capital - current_value) / self.peak_capital) * 100
        return max(0, drawdown)
    
    def get_daily_loss_percent(self) -> float:
        """Get daily loss percentage"""
        if self.daily_start_capital == 0:
            return 0.0
        
        return (self.daily_profit / self.daily_start_capital) * 100
    
    def _reset_daily_if_needed(self):
        """Reset daily metrics if new day"""
        current_date = datetime.now().date()
        
        if current_date > self.last_reset_date:
            logger.info(f"Resetting daily metrics for new trading day")
            self.daily_start_capital = self.current_capital
            self.daily_trade_count = 0
            self.daily_profit = 0.0
            self.last_reset_date = current_date
            
            # Re-enable trading if it was disabled due to daily loss
            if not self.is_trading_enabled and not self.emergency_stop_triggered:
                self.enable_trading()
    
    def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop"""
        if not self.emergency_stop_enabled:
            logger.warning(f"Emergency stop requested but not enabled: {reason}")
            return
        
        logger.critical(f"⚠️  EMERGENCY STOP TRIGGERED: {reason}")
        self.emergency_stop_triggered = True
        self.is_trading_enabled = False
    
    def disable_trading(self, reason: str):
        """Disable trading"""
        logger.warning(f"Trading disabled: {reason}")
        self.is_trading_enabled = False
    
    def enable_trading(self):
        """Enable trading"""
        logger.info("Trading enabled")
        self.is_trading_enabled = True
    
    def reset_emergency_stop(self):
        """Reset emergency stop (manual intervention required)"""
        logger.info("Emergency stop reset")
        self.emergency_stop_triggered = False
        self.is_trading_enabled = True
    
    def reset_drawdown(self, current_portfolio_value: float):
        """Reset drawdown by updating peak capital to current value"""
        logger.info(f"Resetting drawdown: peak_capital ${self.peak_capital:.2f} -> ${current_portfolio_value:.2f}")
        self.peak_capital = current_portfolio_value
        if self.emergency_stop_triggered:
            self.reset_emergency_stop()
    
    def get_risk_metrics(self, current_portfolio_value: float, active_trades: int = 0) -> RiskMetrics:
        """Get current risk metrics"""
        drawdown = self.calculate_drawdown(current_portfolio_value)
        daily_pnl_percent = self.get_daily_loss_percent()
        
        # Determine risk level
        if drawdown >= self.max_drawdown_percent * 0.8:
            risk_level = RiskLevel.CRITICAL
        elif drawdown >= self.max_drawdown_percent * 0.6:
            risk_level = RiskLevel.HIGH
        elif drawdown >= self.max_drawdown_percent * 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return RiskMetrics(
            portfolio_value_usd=current_portfolio_value,
            daily_pnl=self.daily_profit,
            daily_pnl_percent=daily_pnl_percent,
            drawdown_percent=drawdown,
            active_trades_count=active_trades,
            total_exposure_usd=current_portfolio_value - self.initial_capital,
            risk_level=risk_level
        )
    
    def get_statistics(self) -> Dict:
        """Get risk management statistics"""
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t['profit_usd'] > 0)
        losing_trades = total_trades - winning_trades
        
        total_profit = sum(t['profit_usd'] for t in self.trade_history)
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_profit': total_profit,
            'total_profit_percent': (total_profit / self.initial_capital * 100) if self.initial_capital > 0 else 0,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'current_streak': f"{'Win' if self.win_streak > 0 else 'Loss'} {max(self.win_streak, self.loss_streak)}",
            'daily_trades': self.daily_trade_count,
            'daily_profit': self.daily_profit,
            'is_trading_enabled': self.is_trading_enabled,
            'emergency_stop_triggered': self.emergency_stop_triggered
        }
    
    def get_max_trade_size(self, current_portfolio_value: float) -> float:
        """Get maximum allowed trade size"""
        size_by_percent = current_portfolio_value * (self.max_trade_size_percent / 100)
        return min(size_by_percent, self.max_position_size_usd)

