"""
PancakeSwap (BSC) Connector
Handles swaps on PancakeSwap V2
"""

from typing import Optional
from datetime import datetime, timedelta
from web3 import Web3
from .base_dex import BaseDEX
from ...utils.logger import get_logger

logger = get_logger()


class PancakeSwapConnector(BaseDEX):
    """PancakeSwap exchange connector for Binance Smart Chain"""
    
    # PancakeSwap V2 Router on BSC
    DEFAULT_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
    DEFAULT_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
    WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        router_address: Optional[str] = None,
        factory_address: Optional[str] = None
    ):
        super().__init__(
            dex_name="PancakeSwap",
            chain_name="BSC",
            rpc_url=rpc_url,
            private_key=private_key,
            router_address=router_address or self.DEFAULT_ROUTER,
            factory_address=factory_address or self.DEFAULT_FACTORY
        )
    
    def get_native_token(self) -> str:
        """Get native token symbol"""
        return "BNB"
    
    def get_wrapped_native_address(self) -> str:
        """Get wrapped BNB address"""
        return self.WBNB_ADDRESS
    
    async def swap_tokens(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """
        Execute token swap on PancakeSwap
        
        Args:
            token_in_address: Input token address
            token_out_address: Output token address
            amount_in: Amount of input token
            min_amount_out: Minimum acceptable output amount
            slippage_percent: Slippage tolerance
        
        Returns:
            Transaction hash
        """
        try:
            logger.info(f"Swapping {amount_in} tokens on PancakeSwap")
            
            # Get token contracts and decimals
            token_in = self.get_token_contract(token_in_address)
            token_out = self.get_token_contract(token_out_address)
            
            decimals_in = token_in.functions.decimals().call()
            decimals_out = token_out.functions.decimals().call()
            
            # Convert amounts to wei
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            min_amount_out_wei = int(min_amount_out * (10 ** decimals_out))
            
            # Apply slippage to min_amount_out
            min_amount_out_wei = int(min_amount_out_wei * (1 - slippage_percent / 100))
            
            # Ensure token is approved
            await self.approve_token(token_in_address, self.router_address, amount_in_wei)
            
            # Build swap path
            path = [
                Web3.to_checksum_address(token_in_address),
                Web3.to_checksum_address(token_out_address)
            ]
            
            # Set deadline (10 minutes from now)
            deadline = int((datetime.now() + timedelta(minutes=10)).timestamp())
            
            # Build swap transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            swap_txn = self.router.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_amount_out_wei,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(swap_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"PancakeSwap swap transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"PancakeSwap swap successful!")
                return tx_hash.hex()
            else:
                logger.error(f"PancakeSwap swap failed")
                raise Exception("Swap transaction failed")
        
        except Exception as e:
            logger.error(f"Error executing PancakeSwap swap: {e}")
            raise
    
    async def swap_bnb_for_tokens(
        self,
        token_out_address: str,
        amount_bnb: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """Swap BNB for tokens"""
        try:
            logger.info(f"Swapping {amount_bnb} BNB for tokens on PancakeSwap")
            
            # Get output token decimals
            token_out = self.get_token_contract(token_out_address)
            decimals_out = token_out.functions.decimals().call()
            
            # Convert amounts
            amount_bnb_wei = self.w3.to_wei(amount_bnb, 'ether')
            min_amount_out_wei = int(min_amount_out * (10 ** decimals_out))
            min_amount_out_wei = int(min_amount_out_wei * (1 - slippage_percent / 100))
            
            # Build path (BNB -> WBNB -> Token)
            path = [
                self.WBNB_ADDRESS,
                Web3.to_checksum_address(token_out_address)
            ]
            
            # Set deadline
            deadline = int((datetime.now() + timedelta(minutes=10)).timestamp())
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            swap_txn = self.router.functions.swapExactETHForTokens(
                min_amount_out_wei,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'value': amount_bnb_wei,
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send
            signed_txn = self.account.sign_transaction(swap_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"BNB swap transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"BNB swap successful!")
                return tx_hash.hex()
            else:
                raise Exception("BNB swap failed")
        
        except Exception as e:
            logger.error(f"Error swapping BNB: {e}")
            raise
    
    async def get_price_impact(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float
    ) -> float:
        """Calculate price impact for a swap"""
        try:
            # Small reference amount (1 token)
            reference_amount = 1.0
            
            # Get price for reference amount
            reference_price = await self.get_token_price(
                token_in_address,
                token_out_address,
                reference_amount
            )
            
            # Get price for actual amount
            actual_price = await self.get_token_price(
                token_in_address,
                token_out_address,
                amount_in
            )
            
            # Calculate price impact
            expected_out = reference_price * amount_in
            actual_out = actual_price
            
            if expected_out > 0:
                impact = ((expected_out - actual_out) / expected_out) * 100
                return impact
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Error calculating price impact: {e}")
            return 0.0

