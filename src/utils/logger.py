"""
Logging Configuration
Provides structured logging with colors and multiple outputs
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorlog


class BotLogger:
    """Centralized logger for the arbitrage bot"""
    
    def __init__(self, name: str = "ArbitrageBot", log_level: str = "INFO", log_dir: str = "logs"):
        self.name = name
        self.log_level = log_level.upper()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with console and file handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.log_level))
        
        # Remove existing handlers
        logger.handlers = []
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler for all logs
        log_file = self.log_dir / f"arbitrage_bot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Separate file handler for errors
        error_log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        # Separate file handler for trades
        trade_log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        self.trade_handler = logging.FileHandler(trade_log_file, encoding='utf-8')
        self.trade_handler.setLevel(logging.INFO)
        self.trade_handler.setFormatter(file_formatter)
        
        return logger
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance"""
        return self.logger
    
    def log_trade(self, message: str):
        """Log trade-specific information"""
        trade_logger = logging.getLogger(f"{self.name}.trades")
        trade_logger.addHandler(self.trade_handler)
        trade_logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = True):
        """Log critical message"""
        self.logger.critical(message, exc_info=exc_info)


# Global logger instance
_logger: Optional[BotLogger] = None


def get_logger(name: str = "ArbitrageBot", log_level: str = "INFO") -> BotLogger:
    """Get or create global logger instance"""
    global _logger
    if _logger is None:
        _logger = BotLogger(name, log_level)
    return _logger

