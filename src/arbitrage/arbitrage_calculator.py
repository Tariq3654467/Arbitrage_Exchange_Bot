"""
Arbitrage Calculator
Calculates net profit after all fees, slippage, and costs
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .price_monitor import ArbitrageOpportunity
from ..exchanges.base_exchange import BaseExchange
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class FeeEstimate:
    """Fee estimation breakdown"""
    trading_fee_buy: float = 0.0
    trading_fee_sell: float = 0.0
    gas_fee: float = 0.0  # For DEX
    network_fee: float = 0.0  # For CEX withdrawals
    total_fees: float = 0.0
    
    def calculate_total(self):
        """Calculate total fees"""
        self.total_fees = (
            self.trading_fee_buy + 
            self.trading_fee_sell + 
            self.gas_fee + 
            self.network_fee
        )


@dataclass
class ProfitAnalysis:
    """Complete profit analysis for an arbitrage opportunity"""
    opportunity: ArbitrageOpportunity
    trade_amount: float
    gross_profit_usd: float
    gross_profit_percent: float
    
    # Fee breakdown
    fees: FeeEstimate
    total_fees_usd: float
    
    # Net profit
    net_profit_usd: float
    net_profit_percent: float
    
    # Risk factors
    slippage_estimate: float
    price_impact: float
    
    # Trade details
    buy_amount: float
    sell_amount: float
    estimated_execution_time: float  # seconds
    
    is_profitable: bool = False
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ArbitrageCalculator:
    """Calculate profitability of arbitrage opportunities"""
    
    def __init__(
        self,
        exchanges: Dict[str, BaseExchange],
        min_profit_threshold: float = 0.5,
        max_slippage: float = 1.0,
        gas_price_gwei: float = 50
    ):
        """
        Initialize arbitrage calculator
        
        Args:
            exchanges: Dictionary of exchange connectors
            min_profit_threshold: Minimum net profit % required
            max_slippage: Maximum acceptable slippage %
            gas_price_gwei: Estimated gas price for DEX trades
        """
        self.exchanges = exchanges
        self.min_profit_threshold = min_profit_threshold
        self.max_slippage = max_slippage
        self.gas_price_gwei = gas_price_gwei
        
        # Fee cache
        self.fee_cache = {}
        
        logger.info(f"Arbitrage calculator initialized (min profit: {min_profit_threshold}%)")
    
    async def analyze_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        trade_amount_usd: float
    ) -> ProfitAnalysis:
        """
        Analyze an arbitrage opportunity and calculate net profit
        
        Args:
            opportunity: The arbitrage opportunity
            trade_amount_usd: Amount to trade in USD
        
        Returns:
            Complete profit analysis
        """
        try:
            # Get exchanges
            buy_exchange = self.exchanges.get(opportunity.buy_exchange)
            sell_exchange = self.exchanges.get(opportunity.sell_exchange)
            
            if not buy_exchange or not sell_exchange:
                raise ValueError("Exchange not found")
            
            # Calculate trade amounts
            buy_amount = trade_amount_usd / opportunity.buy_price
            expected_sell_amount = buy_amount
            
            # Estimate fees
            fees = await self._estimate_fees(
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                symbol=opportunity.symbol,
                buy_price=opportunity.buy_price,
                sell_price=opportunity.sell_price,
                amount=buy_amount
            )
            
            # Calculate gross profit
            gross_profit_usd = (opportunity.sell_price - opportunity.buy_price) * buy_amount
            gross_profit_percent = opportunity.gross_profit_percent
            
            # Estimate slippage
            slippage_estimate = await self._estimate_slippage(
                opportunity,
                buy_amount
            )
            
            # Calculate price impact
            price_impact = await self._estimate_price_impact(
                opportunity,
                buy_amount
            )
            
            # Adjust for slippage and price impact
            slippage_loss = gross_profit_usd * (slippage_estimate / 100)
            impact_loss = gross_profit_usd * (price_impact / 100)
            
            # Calculate net profit
            total_fees_usd = fees.total_fees
            net_profit_usd = gross_profit_usd - total_fees_usd - slippage_loss - impact_loss
            net_profit_percent = (net_profit_usd / trade_amount_usd) * 100 if trade_amount_usd > 0 else 0
            
            # Estimate execution time
            execution_time = self._estimate_execution_time(
                opportunity.buy_exchange,
                opportunity.sell_exchange
            )
            
            # Determine if profitable
            is_profitable = (
                net_profit_percent >= self.min_profit_threshold and
                slippage_estimate <= self.max_slippage
            )
            
            analysis = ProfitAnalysis(
                opportunity=opportunity,
                trade_amount=trade_amount_usd,
                gross_profit_usd=gross_profit_usd,
                gross_profit_percent=gross_profit_percent,
                fees=fees,
                total_fees_usd=total_fees_usd,
                net_profit_usd=net_profit_usd,
                net_profit_percent=net_profit_percent,
                slippage_estimate=slippage_estimate,
                price_impact=price_impact,
                buy_amount=buy_amount,
                sell_amount=expected_sell_amount,
                estimated_execution_time=execution_time,
                is_profitable=is_profitable
            )
            
            if is_profitable:
                logger.info(
                    f"✓ Profitable opportunity: {opportunity.symbol} "
                    f"Buy@{opportunity.buy_exchange} Sell@{opportunity.sell_exchange} "
                    f"Net: {net_profit_percent:.2f}% (${net_profit_usd:.2f})"
                )
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            raise
    
    async def _estimate_fees(
        self,
        buy_exchange: BaseExchange,
        sell_exchange: BaseExchange,
        symbol: str,
        buy_price: float,
        sell_price: float,
        amount: float
    ) -> FeeEstimate:
        """Estimate all fees for the trade"""
        fees = FeeEstimate()
        
        try:
            # Get trading fees
            buy_fees = await self._get_trading_fees(buy_exchange, symbol)
            sell_fees = await self._get_trading_fees(sell_exchange, symbol)
            
            # Calculate trading fees (using taker fees for market orders)
            fees.trading_fee_buy = buy_price * amount * buy_fees.get('taker', 0.001)
            fees.trading_fee_sell = sell_price * amount * sell_fees.get('taker', 0.001)
            
            # Estimate gas fees for DEX
            if self._is_dex(buy_exchange):
                fees.gas_fee += self._estimate_gas_cost()
            
            if self._is_dex(sell_exchange):
                fees.gas_fee += self._estimate_gas_cost()
            
            # Network fees for cross-exchange transfers (if needed)
            # This would be for moving funds between CEX exchanges
            # For now, we assume instant execution without transfers
            fees.network_fee = 0
            
            fees.calculate_total()
            
        except Exception as e:
            logger.error(f"Error estimating fees: {e}")
        
        return fees
    
    async def _get_trading_fees(self, exchange: BaseExchange, symbol: str) -> Dict[str, float]:
        """Get trading fees from exchange (with caching)"""
        cache_key = f"{exchange.exchange_name}_{symbol}"
        
        if cache_key in self.fee_cache:
            return self.fee_cache[cache_key]
        
        try:
            fees = await exchange.get_trading_fees(symbol)
            self.fee_cache[cache_key] = fees
            return fees
        except Exception as e:
            logger.warning(f"Could not fetch fees for {exchange.exchange_name}: {e}")
            return {'maker': 0.001, 'taker': 0.001}
    
    def _is_dex(self, exchange: BaseExchange) -> bool:
        """Check if exchange is a DEX"""
        dex_names = ['pancakeswap', 'uniswap', 'quickswap', 'galaswap']
        return any(dex in exchange.exchange_name.lower() for dex in dex_names)
    
    def _estimate_gas_cost(self) -> float:
        """Estimate gas cost for DEX trade in USD"""
        # Average gas for a swap: ~200,000 gas
        gas_limit = 200000
        gas_cost_eth = (gas_limit * self.gas_price_gwei) / 1e9
        
        # Convert to USD (simplified - would need real ETH/BNB price)
        # For BSC, gas is much cheaper
        eth_price_usd = 3000  # Estimate
        gas_cost_usd = gas_cost_eth * eth_price_usd
        
        return gas_cost_usd
    
    async def _estimate_slippage(
        self,
        opportunity: ArbitrageOpportunity,
        amount: float
    ) -> float:
        """Estimate slippage based on order book depth"""
        try:
            # Calculate slippage from order books if available
            buy_slippage = 0.0
            sell_slippage = 0.0
            
            if opportunity.buy_order_book and opportunity.buy_order_book.asks:
                buy_slippage = self._calculate_order_book_slippage(
                    opportunity.buy_order_book.asks,
                    amount,
                    opportunity.buy_price
                )
            
            if opportunity.sell_order_book and opportunity.sell_order_book.bids:
                sell_slippage = self._calculate_order_book_slippage(
                    opportunity.sell_order_book.bids,
                    amount,
                    opportunity.sell_price
                )
            
            # Total slippage
            total_slippage = buy_slippage + sell_slippage
            
            return min(total_slippage, self.max_slippage)
        
        except Exception as e:
            logger.error(f"Error estimating slippage: {e}")
            return 0.5  # Default 0.5%
    
    def _calculate_order_book_slippage(
        self,
        orders: list,
        amount: float,
        reference_price: float
    ) -> float:
        """Calculate slippage from order book"""
        if not orders:
            return 0.5  # Default estimate
        
        total_volume = 0
        weighted_price = 0
        
        for price, volume in orders:
            if total_volume >= amount:
                break
            
            fill_volume = min(volume, amount - total_volume)
            weighted_price += price * fill_volume
            total_volume += fill_volume
        
        if total_volume > 0:
            avg_price = weighted_price / total_volume
            slippage = abs((avg_price - reference_price) / reference_price) * 100
            return slippage
        
        return 0.5
    
    async def _estimate_price_impact(
        self,
        opportunity: ArbitrageOpportunity,
        amount: float
    ) -> float:
        """Estimate price impact of the trade"""
        # For CEX, price impact is usually minimal
        # For DEX, it depends on liquidity pool size
        
        buy_impact = 0.1 if self._is_dex_name(opportunity.buy_exchange) else 0.0
        sell_impact = 0.1 if self._is_dex_name(opportunity.sell_exchange) else 0.0
        
        return buy_impact + sell_impact
    
    def _is_dex_name(self, exchange_name: str) -> bool:
        """Check if exchange name indicates DEX"""
        dex_names = ['pancakeswap', 'uniswap', 'quickswap', 'galaswap']
        return any(dex in exchange_name.lower() for dex in dex_names)
    
    def _estimate_execution_time(
        self,
        buy_exchange_name: str,
        sell_exchange_name: str
    ) -> float:
        """Estimate execution time in seconds"""
        # CEX: ~1-2 seconds
        # DEX: ~10-30 seconds (block confirmation)
        
        buy_time = 15 if self._is_dex_name(buy_exchange_name) else 1
        sell_time = 15 if self._is_dex_name(sell_exchange_name) else 1
        
        # Trades can be executed in parallel
        return max(buy_time, sell_time)
    
    def get_fee_summary(self, analysis: ProfitAnalysis) -> str:
        """Get human-readable fee summary"""
        return (
            f"Fee Breakdown:\n"
            f"  Trading Fee (Buy): ${analysis.fees.trading_fee_buy:.2f}\n"
            f"  Trading Fee (Sell): ${analysis.fees.trading_fee_sell:.2f}\n"
            f"  Gas Fees: ${analysis.fees.gas_fee:.2f}\n"
            f"  Network Fees: ${analysis.fees.network_fee:.2f}\n"
            f"  Total Fees: ${analysis.fees.total_fees:.2f}\n"
        )

