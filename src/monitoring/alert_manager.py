"""
Alert Management System
Sends notifications via Telegram and Email
"""

import asyncio
from typing import List, Optional
from datetime import datetime
from enum import Enum

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger()


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(
        self,
        telegram_enabled: bool = False,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        email_enabled: bool = False,
        sendgrid_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        to_email: Optional[str] = None,
        alert_on_trade: bool = True,
        alert_on_error: bool = True,
        alert_on_high_profit: bool = True,
        high_profit_threshold: float = 2.0
    ):
        """
        Initialize alert manager
        
        Args:
            telegram_enabled: Enable Telegram alerts
            telegram_bot_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            email_enabled: Enable email alerts
            sendgrid_api_key: SendGrid API key
            from_email: From email address
            to_email: To email address
            alert_on_trade: Send alerts on trades
            alert_on_error: Send alerts on errors
            alert_on_high_profit: Send alerts on high profit trades
            high_profit_threshold: Profit threshold for high profit alerts
        """
        self.telegram_enabled = telegram_enabled and TELEGRAM_AVAILABLE
        self.email_enabled = email_enabled and SENDGRID_AVAILABLE
        
        self.alert_on_trade = alert_on_trade
        self.alert_on_error = alert_on_error
        self.alert_on_high_profit = alert_on_high_profit
        self.high_profit_threshold = high_profit_threshold
        
        # Telegram setup
        if self.telegram_enabled:
            if not telegram_bot_token or not telegram_chat_id:
                logger.warning("Telegram credentials missing, disabling Telegram alerts")
                self.telegram_enabled = False
            else:
                self.telegram_bot = Bot(token=telegram_bot_token)
                self.telegram_chat_id = telegram_chat_id
                logger.info("Telegram alerts enabled")
        else:
            if not TELEGRAM_AVAILABLE:
                logger.warning("python-telegram-bot not installed, Telegram alerts disabled")
        
        # Email setup
        if self.email_enabled:
            if not sendgrid_api_key or not from_email or not to_email:
                logger.warning("Email credentials missing, disabling email alerts")
                self.email_enabled = False
            else:
                self.sendgrid_client = SendGridAPIClient(sendgrid_api_key)
                self.from_email = from_email
                self.to_email = to_email
                logger.info("Email alerts enabled")
        else:
            if not SENDGRID_AVAILABLE:
                logger.warning("sendgrid not installed, email alerts disabled")
        
        # Alert history
        self.alert_history = []
    
    async def send_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        title: Optional[str] = None
    ):
        """Send an alert via all enabled channels"""
        try:
            # Format message with emoji based on level
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }
            
            emoji = emoji_map.get(level, "")
            formatted_message = f"{emoji} {message}"
            
            # Send via Telegram
            if self.telegram_enabled:
                await self._send_telegram(formatted_message)
            
            # Send via Email
            if self.email_enabled and level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
                await self._send_email(
                    subject=title or f"Arbitrage Bot {level.value.upper()}",
                    message=message
                )
            
            # Store in history
            self.alert_history.append({
                'timestamp': datetime.now(),
                'level': level,
                'message': message
            })
            
            # Limit history size
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-500:]
        
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _send_telegram(self, message: str):
        """Send Telegram message"""
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.debug("Telegram alert sent")
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def _send_email(self, subject: str, message: str):
        """Send email via SendGrid"""
        try:
            mail = Mail(
                from_email=self.from_email,
                to_emails=self.to_email,
                subject=subject,
                plain_text_content=message
            )
            
            # Send in thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.sendgrid_client.send,
                mail
            )
            
            logger.debug("Email alert sent")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    async def alert_trade_executed(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        profit_usd: float,
        profit_percent: float,
        amount: float
    ):
        """Alert when trade is executed"""
        if not self.alert_on_trade:
            return
        
        level = AlertLevel.INFO
        if profit_percent >= self.high_profit_threshold and self.alert_on_high_profit:
            level = AlertLevel.WARNING
        
        message = (
            f"<b>Trade Executed</b>\n"
            f"Symbol: {symbol}\n"
            f"Buy: {buy_exchange}\n"
            f"Sell: {sell_exchange}\n"
            f"Amount: {amount:.6f}\n"
            f"Profit: ${profit_usd:.2f} ({profit_percent:.2f}%)"
        )
        
        await self.send_alert(message, level=level)
    
    async def alert_opportunity_found(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        profit_percent: float
    ):
        """Alert when arbitrage opportunity is found"""
        if profit_percent < self.high_profit_threshold:
            return
        
        message = (
            f"<b>High Profit Opportunity!</b>\n"
            f"Symbol: {symbol}\n"
            f"Buy: {buy_exchange}\n"
            f"Sell: {sell_exchange}\n"
            f"Profit: {profit_percent:.2f}%"
        )
        
        await self.send_alert(message, level=AlertLevel.INFO)
    
    async def alert_error(self, error_message: str, details: Optional[str] = None):
        """Alert on error"""
        if not self.alert_on_error:
            return
        
        message = f"<b>Error Occurred</b>\n{error_message}"
        if details:
            message += f"\n\nDetails: {details}"
        
        await self.send_alert(message, level=AlertLevel.ERROR)
    
    async def alert_emergency_stop(self, reason: str):
        """Alert when emergency stop is triggered"""
        message = (
            f"<b>🚨 EMERGENCY STOP TRIGGERED 🚨</b>\n"
            f"Reason: {reason}\n"
            f"All trading has been halted.\n"
            f"Manual intervention required."
        )
        
        await self.send_alert(message, level=AlertLevel.CRITICAL, title="EMERGENCY STOP")
    
    async def alert_daily_summary(
        self,
        trades_count: int,
        total_profit: float,
        win_rate: float,
        portfolio_value: float
    ):
        """Send daily summary alert"""
        message = (
            f"<b>Daily Summary</b>\n"
            f"Trades: {trades_count}\n"
            f"Total Profit: ${total_profit:.2f}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Portfolio Value: ${portfolio_value:.2f}"
        )
        
        await self.send_alert(message, level=AlertLevel.INFO)
    
    def get_recent_alerts(self, limit: int = 10) -> List[dict]:
        """Get recent alerts"""
        return self.alert_history[-limit:]

