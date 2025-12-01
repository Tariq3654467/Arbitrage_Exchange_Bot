"""
Galaswap DEX Connector
Handles swaps on Galaswap (Gala Games ecosystem DEX)
"""

from typing import Optional
from datetime import datetime, timedelta
from web3 import Web3
from .base_dex import BaseDEX
from ...utils.logger import get_logger

logger = get_logger()


class GalaswapConnector(BaseDEX):
    """Galaswap exchange connector"""
    
    # Galaswap Router and Factory addresses
    # Note: These are placeholder addresses - update with actual Galaswap addresses
    # Galaswap typically runs on Ethereum mainnet or Gala Chain
    ETH_ROUTER = "0x0000000000000000000000000000000000000000"  # Update with actual router
    ETH_FACTORY = "0x0000000000000000000000000000000000000000"  # Update with actual factory
    ETH_WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH on Ethereum
    
    # Gala Chain addresses (if Galaswap runs on Gala Chain)
    GALA_ROUTER = "0x0000000000000000000000000000000000000000"  # Update with actual router
    GALA_FACTORY = "0x0000000000000000000000000000000000000000"  # Update with actual factory
    GALA_WGALA = "0x0000000000000000000000000000000000000000"  # Update with wrapped GALA address
    
    def __init__(
        self,
        chain: str = "ethereum",  # 'ethereum' or 'gala'
        rpc_url: str = None,
        private_key: str = None,
        router_address: Optional[str] = None,
        factory_address: Optional[str] = None
    ):
        """
        Initialize Galaswap connector
        
        Args:
            chain: Blockchain network ('ethereum' or 'gala')
            rpc_url: RPC endpoint URL
            private_key: Private key for wallet
            router_address: Router contract address (optional, uses default if not provided)
            factory_address: Factory contract address (optional, uses default if not provided)
        """
        self.chain = chain.lower()
        
        # Set default addresses based on chain
        if self.chain == "ethereum":
            default_router = router_address or self.ETH_ROUTER
            default_factory = factory_address or self.ETH_FACTORY
            self.wrapped_native = self.ETH_WETH
            self.native_symbol = "ETH"
            chain_name = "Ethereum"
        elif self.chain == "gala":
            default_router = router_address or self.GALA_ROUTER
            default_factory = factory_address or self.GALA_FACTORY
            self.wrapped_native = self.GALA_WGALA
            self.native_symbol = "GALA"
            chain_name = "Gala Chain"
        else:
            raise ValueError(f"Unsupported chain for Galaswap: {chain}")
        
        if not rpc_url:
            raise ValueError(f"RPC URL is required for Galaswap on {chain_name}")
        if not private_key:
            raise ValueError(f"Private key is required for Galaswap on {chain_name}")
        
        super().__init__(
            dex_name="Galaswap",
            chain_name=chain_name,
            rpc_url=rpc_url,
            private_key=private_key,
            router_address=default_router,
            factory_address=default_factory
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
        Execute token swap on Galaswap
        
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
            logger.info(f"Swapping {amount_in} tokens on Galaswap")
            
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
            
            logger.info(f"Galaswap swap transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info(f"Galaswap swap successful!")
                return tx_hash.hex()
            else:
                logger.error(f"Galaswap swap failed")
                raise Exception("Swap transaction failed")
        
        except Exception as e:
            logger.error(f"Error executing Galaswap swap: {e}")
            raise
    
    async def swap_native_for_tokens(
        self,
        token_out_address: str,
        amount_native: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """Swap native token (ETH/GALA) for tokens"""
        try:
            logger.info(f"Swapping {amount_native} {self.native_symbol} for tokens on Galaswap")
            
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

