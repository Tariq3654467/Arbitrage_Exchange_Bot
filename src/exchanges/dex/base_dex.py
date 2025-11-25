"""
Base DEX Interface
Common functionality for all DEX connectors
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from web3 import Web3
from eth_account import Account
from decimal import Decimal
import json

from ...utils.logger import get_logger
from ...exchanges.base_exchange import OrderBook, Balance

logger = get_logger()


# Standard Uniswap V2 Router ABI (minimal)
ROUTER_ABI = json.loads('''[
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}], "name": "getAmountsOut", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactETHForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForETH", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]''')

# ERC20 Token ABI (minimal)
ERC20_ABI = json.loads('''[
    {"constant": true, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": true, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": true, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": true, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": false, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": true, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]''')


class BaseDEX(ABC):
    """Base class for DEX connectors"""
    
    def __init__(
        self,
        dex_name: str,
        chain_name: str,
        rpc_url: str,
        private_key: str,
        router_address: str,
        factory_address: Optional[str] = None
    ):
        self.dex_name = dex_name
        self.chain_name = chain_name
        self.router_address = Web3.to_checksum_address(router_address)
        self.factory_address = Web3.to_checksum_address(factory_address) if factory_address else None
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Initialize account from private key
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address
        
        # Initialize router contract
        self.router = self.w3.eth.contract(
            address=self.router_address,
            abi=ROUTER_ABI
        )
        
        self.is_connected = False
        
        logger.info(f"Initialized {dex_name} on {chain_name}")
        logger.info(f"Wallet address: {self.wallet_address}")
    
    async def connect(self):
        """Check connection to blockchain"""
        try:
            # Check if connected
            if not self.w3.is_connected():
                raise ConnectionError(f"Cannot connect to {self.chain_name} RPC")
            
            # Get chain ID
            chain_id = self.w3.eth.chain_id
            logger.info(f"Connected to {self.chain_name} (Chain ID: {chain_id})")
            
            # Get wallet balance
            balance = self.w3.eth.get_balance(self.wallet_address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            logger.info(f"Wallet native balance: {balance_eth} {self.get_native_token()}")
            
            self.is_connected = True
            
        except Exception as e:
            logger.error(f"Error connecting to {self.dex_name}: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from blockchain"""
        self.is_connected = False
        logger.info(f"Disconnected from {self.dex_name}")
    
    @abstractmethod
    def get_native_token(self) -> str:
        """Get native token symbol (ETH, BNB, MATIC, etc.)"""
        pass
    
    @abstractmethod
    def get_wrapped_native_address(self) -> str:
        """Get wrapped native token address (WETH, WBNB, WMATIC, etc.)"""
        pass
    
    def get_token_contract(self, token_address: str):
        """Get ERC20 token contract instance"""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
    
    async def get_token_balance(self, token_address: str) -> float:
        """Get token balance for wallet"""
        try:
            token_contract = self.get_token_contract(token_address)
            balance = token_contract.functions.balanceOf(self.wallet_address).call()
            decimals = token_contract.functions.decimals().call()
            
            return balance / (10 ** decimals)
        
        except Exception as e:
            logger.error(f"Error fetching token balance: {e}")
            return 0.0
    
    async def get_native_balance(self) -> float:
        """Get native token balance"""
        try:
            balance = self.w3.eth.get_balance(self.wallet_address)
            return float(self.w3.from_wei(balance, 'ether'))
        except Exception as e:
            logger.error(f"Error fetching native balance: {e}")
            return 0.0
    
    async def get_token_price(
        self, 
        token_in_address: str, 
        token_out_address: str, 
        amount_in: float
    ) -> float:
        """Get token price (amount out for given amount in)"""
        try:
            # Get token decimals
            token_in = self.get_token_contract(token_in_address)
            token_out = self.get_token_contract(token_out_address)
            
            decimals_in = token_in.functions.decimals().call()
            decimals_out = token_out.functions.decimals().call()
            
            # Convert amount to wei
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            
            # Get amounts out
            path = [
                Web3.to_checksum_address(token_in_address),
                Web3.to_checksum_address(token_out_address)
            ]
            
            amounts = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            amount_out_wei = amounts[-1]
            
            # Convert back to decimal
            amount_out = amount_out_wei / (10 ** decimals_out)
            
            return amount_out
        
        except Exception as e:
            logger.error(f"Error fetching token price: {e}")
            return 0.0
    
    async def approve_token(
        self, 
        token_address: str, 
        spender_address: str, 
        amount: Optional[int] = None
    ) -> str:
        """Approve token spending"""
        try:
            token_contract = self.get_token_contract(token_address)
            
            # Use max approval if amount not specified
            if amount is None:
                amount = 2**256 - 1
            
            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                self.wallet_address,
                spender_address
            ).call()
            
            if current_allowance >= amount:
                logger.info(f"Token already approved with sufficient allowance")
                return ""
            
            # Build approval transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            approve_txn = token_contract.functions.approve(
                spender_address,
                amount
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(approve_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Approval transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] == 1:
                logger.info(f"Token approval successful")
                return tx_hash.hex()
            else:
                logger.error(f"Token approval failed")
                return ""
        
        except Exception as e:
            logger.error(f"Error approving token: {e}")
            raise
    
    async def estimate_gas_price(self) -> int:
        """Estimate current gas price"""
        try:
            gas_price = self.w3.eth.gas_price
            return gas_price
        except Exception as e:
            logger.error(f"Error estimating gas price: {e}")
            return 0
    
    async def get_transaction_receipt(self, tx_hash: str) -> Dict:
        """Get transaction receipt"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            return dict(receipt)
        except Exception as e:
            logger.error(f"Error fetching transaction receipt: {e}")
            return {}
    
    def is_operational(self) -> bool:
        """Check if DEX connection is operational"""
        return self.is_connected and self.w3.is_connected()
    
    @abstractmethod
    async def swap_tokens(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float,
        min_amount_out: float,
        slippage_percent: float = 1.0
    ) -> str:
        """Execute token swap"""
        pass

