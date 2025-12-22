"""
Portfolio Management System
Manages capital allocation, balances, and rebalancing
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from ..exchanges.base_exchange import BaseExchange, Balance
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class AssetBalance:
    """Asset balance across all exchanges"""
    asset: str
    total_amount: float
    total_value_usd: float
    balances_by_exchange: Dict[str, float]
    prices_usd: Dict[str, float]  # Asset prices in USD


@dataclass
class PortfolioSnapshot:
    """Complete portfolio snapshot"""
    timestamp: datetime
    total_value_usd: float
    asset_balances: Dict[str, AssetBalance]
    allocation_percent: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalance_needed: bool


class PortfolioManager:
    """Manages portfolio balances and rebalancing"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        target_allocation: Dict[str, float],
        rebalance_threshold_percent: float = 10.0,
        rebalance_interval_minutes: int = 60,
        price_feeds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize portfolio manager
        
        Args:
            exchanges: Dictionary of exchange connectors
            target_allocation: Target allocation percentages (e.g., {'USDT': 50, 'BTC': 30, 'ETH': 20})
            rebalance_threshold_percent: Trigger rebalance if deviation exceeds this
            rebalance_interval_minutes: Minimum time between rebalances
            price_feeds: Optional price feeds for assets in USD
        """
        self.exchanges = exchanges
        self.target_allocation = target_allocation
        self.rebalance_threshold_percent = rebalance_threshold_percent
        self.rebalance_interval_minutes = rebalance_interval_minutes
        
        # Normalize target allocation to sum to 100
        total = sum(target_allocation.values())
        if total != 100:
            self.target_allocation = {k: (v / total * 100) for k, v in target_allocation.items()}
        
        # Price feeds (simplified - in production would use real-time pricing)
        # If no price feeds are provided, set sensible defaults for major quote assets
        # so portfolio valuation is not zero when you hold common stablecoins.
        self.price_feeds = price_feeds or {}
        default_price_feeds = {
            'USDT': 1.0,
            'FDUSD': 1.0,
            'BUSD': 1.0,
            'USDC': 1.0,
            # Gala ecosystem stable-like tokens
            'GUSDT': 1.0,
            'GUSDC': 1.0,
        }
        for asset, price in default_price_feeds.items():
            self.price_feeds.setdefault(asset, price)
        
        # State tracking
        self.current_balances: Dict[str, AssetBalance] = {}
        self.last_rebalance_time = None
        self.rebalance_history = []
        
        # Portfolio history
        self.portfolio_history: List[PortfolioSnapshot] = []
        
        logger.info(f"Portfolio manager initialized with target allocation: {self.target_allocation}")
    
    async def update_balances(self) -> Dict[str, AssetBalance]:
        """Update balances from all exchanges"""
        try:
            all_balances = defaultdict(lambda: {
                'total_amount': 0.0,
                'balances_by_exchange': {},
                'prices_usd': {}
            })
            
            # Fetch balances from each exchange
            for exchange_name, exchange in self.exchanges.items():
                try:
                    balances = await exchange.get_balance()
                    
                    for asset_key, balance in balances.items():
                        if balance.total > 0:
                            # Use the display name from balance.asset if the key is "UNKNOWN"
                            # This helps with cases where the key might be "UNKNOWN" but balance.asset has the real name
                            if asset_key == "UNKNOWN" and balance.asset and balance.asset != "UNKNOWN" and balance.asset != "Unknown Token":
                                # Extract a clean identifier from the display name (remove parentheses content)
                                import re
                                clean_name = re.sub(r'\s*\([^)]*\)\s*', '', balance.asset).strip()
                                asset_identifier = clean_name if clean_name else balance.asset
                            else:
                                asset_identifier = asset_key
                            
                            all_balances[asset_identifier]['total_amount'] += balance.total
                            all_balances[asset_identifier]['balances_by_exchange'][exchange_name] = balance.total
                            
                            # Get price (simplified - would use real price feeds)
                            # Try both the asset_key and asset_identifier for price lookup
                            price_usd = self.price_feeds.get(asset_identifier, self.price_feeds.get(asset_key, 0.0))
                            all_balances[asset_identifier]['prices_usd'][exchange_name] = price_usd
                
                except Exception as e:
                    error_msg = (
                        f"Error fetching balance from {exchange_name}. "
                        f"Error type: {type(e).__name__}, Message: {str(e)}"
                    )
                    logger.error(error_msg)
                    # Continue with other exchanges even if one fails
            
            # Convert to AssetBalance objects
            self.current_balances = {}
            for asset, data in all_balances.items():
                avg_price = sum(data['prices_usd'].values()) / len(data['prices_usd']) if data['prices_usd'] else 0
                
                self.current_balances[asset] = AssetBalance(
                    asset=asset,
                    total_amount=data['total_amount'],
                    total_value_usd=data['total_amount'] * avg_price,
                    balances_by_exchange=data['balances_by_exchange'],
                    prices_usd=data['prices_usd']
                )
            
            return self.current_balances
        
        except Exception as e:
            logger.error(f"Error updating balances: {e}")
            return {}
    
    async def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Get current portfolio snapshot"""
        await self.update_balances()
        
        # Calculate total portfolio value
        total_value = sum(balance.total_value_usd for balance in self.current_balances.values())
        
        # Calculate current allocation percentages
        allocation_percent = {}
        for asset, balance in self.current_balances.items():
            if total_value > 0:
                allocation_percent[asset] = (balance.total_value_usd / total_value) * 100
            else:
                allocation_percent[asset] = 0.0
        
        # Check if rebalance is needed
        rebalance_needed = self._check_rebalance_needed(allocation_percent)
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value_usd=total_value,
            asset_balances=self.current_balances,
            allocation_percent=allocation_percent,
            target_allocation=self.target_allocation,
            rebalance_needed=rebalance_needed
        )
        
        # Add to history
        self.portfolio_history.append(snapshot)
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-500:]
        
        return snapshot
    
    def _check_rebalance_needed(self, current_allocation: Dict[str, float]) -> bool:
        """Check if rebalancing is needed"""
        for asset, target_percent in self.target_allocation.items():
            current_percent = current_allocation.get(asset, 0.0)
            deviation = abs(current_percent - target_percent)
            
            if deviation > self.rebalance_threshold_percent:
                logger.info(
                    f"Rebalance needed for {asset}: "
                    f"Current {current_percent:.1f}% vs Target {target_percent:.1f}% "
                    f"(Deviation: {deviation:.1f}%)"
                )
                return True
        
        return False
    
    async def execute_rebalance(self) -> bool:
        """Execute portfolio rebalancing"""
        # CRITICAL FIX: Add 5-minute cooldown after rebalance attempts to prevent loops
        # This prevents the bot from repeatedly trying to rebalance when balances haven't updated yet
        if self.last_rebalance_time:
            time_since_last = datetime.now() - self.last_rebalance_time
            # Use shorter cooldown (5 minutes) to prevent rebalance loops
            # The Virtual Ledger updates immediately, but we still want a cooldown
            cooldown_minutes = min(5, self.rebalance_interval_minutes)  # 5 min cooldown
            if time_since_last < timedelta(minutes=cooldown_minutes):
                remaining = (timedelta(minutes=cooldown_minutes) - time_since_last).total_seconds() / 60
                logger.info(
                    f"Rebalance skipped: Cooldown active. "
                    f"Last rebalance was {time_since_last.total_seconds() / 60:.1f} minutes ago. "
                    f"Wait {remaining:.1f} more minutes."
                )
                return False
        
        try:
            logger.info("Starting portfolio rebalance...")
            
            snapshot = await self.get_portfolio_snapshot()
            
            if not snapshot.rebalance_needed:
                logger.info("No rebalance needed")
                return False
            
            # Calculate required trades
            rebalance_trades = self._calculate_rebalance_trades(snapshot)
            
            if not rebalance_trades:
                logger.info("No rebalance trades needed")
                return False
            
            # Execute rebalance trades
            # NOTE: This is a simplified version. In production, you would:
            # 1. Execute trades to rebalance
            # 2. Handle cross-exchange transfers if needed
            # 3. Consider trading fees and slippage
            
            logger.info(f"Rebalance plan: {rebalance_trades}")
            logger.warning("Rebalance execution not fully implemented - would execute trades here")
            
            # Record rebalance
            self.last_rebalance_time = datetime.now()
            self.rebalance_history.append({
                'timestamp': datetime.now(),
                'snapshot': snapshot,
                'trades': rebalance_trades
            })
            
            return True
        
        except Exception as e:
            logger.error(f"Error executing rebalance: {e}")
            return False
    
    def _calculate_rebalance_trades(self, snapshot: PortfolioSnapshot) -> List[Dict]:
        """Calculate required trades to rebalance portfolio"""
        trades = []
        total_value = snapshot.total_value_usd
        
        for asset, target_percent in self.target_allocation.items():
            current_percent = snapshot.allocation_percent.get(asset, 0.0)
            target_value = total_value * (target_percent / 100)
            
            current_balance = snapshot.asset_balances.get(asset)
            current_value = current_balance.total_value_usd if current_balance else 0.0
            
            value_diff = target_value - current_value
            
            if abs(value_diff) > total_value * (self.rebalance_threshold_percent / 100):
                if value_diff > 0:
                    # Need to buy this asset
                    trades.append({
                        'action': 'buy',
                        'asset': asset,
                        'amount_usd': value_diff,
                        'current_percent': current_percent,
                        'target_percent': target_percent
                    })
                else:
                    # Need to sell this asset
                    trades.append({
                        'action': 'sell',
                        'asset': asset,
                        'amount_usd': abs(value_diff),
                        'current_percent': current_percent,
                        'target_percent': target_percent
                    })
        
        return trades
    
    async def get_available_capital(self, asset: str, exchange_name: Optional[str] = None) -> float:
        """Get available capital for an asset"""
        await self.update_balances()
        
        if asset not in self.current_balances:
            return 0.0
        
        balance = self.current_balances[asset]
        
        if exchange_name:
            # Get balance for specific exchange
            return balance.balances_by_exchange.get(exchange_name, 0.0)
        else:
            # Get total balance across all exchanges
            return balance.total_amount
    
    async def get_total_portfolio_value(self) -> float:
        """Get total portfolio value in USD"""
        snapshot = await self.get_portfolio_snapshot()
        return snapshot.total_value_usd
    
    def get_allocation_summary(self) -> Dict:
        """Get allocation summary"""
        if not self.portfolio_history:
            return {}
        
        latest_snapshot = self.portfolio_history[-1]
        
        summary = {
            'total_value_usd': latest_snapshot.total_value_usd,
            'timestamp': latest_snapshot.timestamp,
            'allocations': []
        }
        
        for asset in self.target_allocation.keys():
            current_percent = latest_snapshot.allocation_percent.get(asset, 0.0)
            target_percent = self.target_allocation[asset]
            deviation = current_percent - target_percent
            
            balance = latest_snapshot.asset_balances.get(asset)
            
            summary['allocations'].append({
                'asset': asset,
                'current_percent': current_percent,
                'target_percent': target_percent,
                'deviation': deviation,
                'amount': balance.total_amount if balance else 0.0,
                'value_usd': balance.total_value_usd if balance else 0.0,
                'exchanges': balance.balances_by_exchange if balance else {}
            })
        
        return summary
    
    def get_statistics(self) -> Dict:
        """Get portfolio management statistics"""
        if not self.portfolio_history:
            return {}
        
        latest = self.portfolio_history[-1]
        
        # Calculate portfolio growth
        initial_value = self.portfolio_history[0].total_value_usd if self.portfolio_history else 0
        current_value = latest.total_value_usd
        growth = ((current_value - initial_value) / initial_value * 100) if initial_value > 0 else 0
        
        return {
            'current_portfolio_value': current_value,
            'portfolio_growth_percent': growth,
            'total_rebalances': len(self.rebalance_history),
            'last_rebalance': self.last_rebalance_time,
            'rebalance_needed': latest.rebalance_needed,
            'assets_count': len(latest.asset_balances),
            'exchanges_count': len(self.exchanges)
        }

