"""
Uniswap V2 Connector
Handles swaps on Uniswap V2 (Ethereum, Polygon)
"""

from typing import Optional
from datetime import datetime, timedelta
from web3 import Web3
from .base_dex import BaseDEX
from ...utils.logger import get_logger

logger = get_logger()


class UniswapConnector(BaseDEX):
    """Uniswap V2 exchange connector"""
    
    # Uniswap V2 Router addresses
    ETH_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    ETH_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
    ETH_WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    
    # QuickSwap (Uniswap fork on Polygon)
    POLYGON_ROUTER = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
    POLYGON_FACTORY = "0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32"
    POLYGON_WMATIC = "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
    
    def __init__(
        self,
        chain: str,  # 'ethereum' or 'polygon'
        rpc_url: str,
        private_key: str,
        router_address: Optional[str] = None,
        factory_address: Optional[str] = None
    ):
        self.chain = chain.lower()
        
        # Set default addresses based on chain
        if self.chain == "ethereum":
            default_router = self.ETH_ROUTER
            default_factory = self.ETH_FACTORY
            self.wrapped_native = self.ETH_WETH
            self.native_symbol = "ETH"
            chain_name = "Ethereum"
        elif self.chain == "polygon":
            default_router = self.POLYGON_ROUTER
            default_factory = self.POLYGON_FACTORY
            self.wrapped_native = self.POLYGON_WMATIC
            self.native_symbol = "MATIC"
            chain_name = "Polygon"
        else:
            raise ValueError(f"Unsupported chain: {chain}")
        
        super().__init__(
            dex_name=f"Uniswap-{chain_name}",
            chain_name=chain_name,
            rpc_url=rpc_url,
            private_key=private_key,
            router_address=router_address or default_router,
            factory_address=factory_address or default_factory
        )
    
    def get_native_token(self) -> str:
        """Get native token symbol"""
        return self.native_symbol
    
    def get_wrapped_native_address(self) -> str:
        """Get wrapped native token address"""
        return self.wrapped_native
    
    async def swap_tokens(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """
        Execute token swap on Uniswap
        
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
            logger.info(f"Swapping {amount_in} tokens on {self.dex_name}")
            
            # Get token contracts and decimals
            token_in = self.get_token_contract(token_in_address)
            token_out = self.get_token_contract(token_out_address)
            
            decimals_in = token_in.functions.decimals().call()
            decimals_out = token_out.functions.decimals().call()
            
            # Convert amounts to wei
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            min_amount_out_wei = int(min_amount_out * (10 ** decimals_out))
            
            # Apply slippage
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
            gas_price = await self.estimate_gas_price()
            
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
                'gasPrice': gas_price
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(swap_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"{self.dex_name} swap transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info(f"{self.dex_name} swap successful!")
                return tx_hash.hex()
            else:
                logger.error(f"{self.dex_name} swap failed")
                raise Exception("Swap transaction failed")
        
        except Exception as e:
            logger.error(f"Error executing {self.dex_name} swap: {e}")
            raise
    
    async def swap_native_for_tokens(
        self,
        token_out_address: str,
        amount_native: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """Swap native token (ETH/MATIC) for tokens"""
        try:
            logger.info(f"Swapping {amount_native} {self.native_symbol} for tokens on {self.dex_name}")
            
            # Get output token decimals
            token_out = self.get_token_contract(token_out_address)
            decimals_out = token_out.functions.decimals().call()
            
            # Convert amounts
            amount_native_wei = self.w3.to_wei(amount_native, 'ether')
            min_amount_out_wei = int(min_amount_out * (10 ** decimals_out))
            min_amount_out_wei = int(min_amount_out_wei * (1 - slippage_percent / 100))
            
            # Build path
            path = [
                self.wrapped_native,
                Web3.to_checksum_address(token_out_address)
            ]
            
            # Set deadline
            deadline = int((datetime.now() + timedelta(minutes=10)).timestamp())
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            gas_price = await self.estimate_gas_price()
            
            swap_txn = self.router.functions.swapExactETHForTokens(
                min_amount_out_wei,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'value': amount_native_wei,
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': gas_price
            })
            
            # Sign and send
            signed_txn = self.account.sign_transaction(swap_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"{self.native_symbol} swap transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info(f"{self.native_symbol} swap successful!")
                return tx_hash.hex()
            else:
                raise Exception(f"{self.native_symbol} swap failed")
        
        except Exception as e:
            logger.error(f"Error swapping {self.native_symbol}: {e}")
            raise
    
    async def get_price_impact(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float
    ) -> float:
        """Calculate price impact for a swap"""
        try:
            # Small reference amount
            reference_amount = 1.0
            
            # Get prices
            reference_price = await self.get_token_price(
                token_in_address,
                token_out_address,
                reference_amount
            )
            
            actual_price = await self.get_token_price(
                token_in_address,
                token_out_address,
                amount_in
            )
            
            # Calculate impact
            expected_out = reference_price * amount_in
            actual_out = actual_price
            
            if expected_out > 0:
                impact = ((expected_out - actual_out) / expected_out) * 100
                return impact
            
            return 0.0
        
        except Exception as e:
            logger.error(f"Error calculating price impact: {e}")
            return 0.0

