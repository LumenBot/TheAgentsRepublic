"""
DeFi Trader — Base L2 Token Swaps
====================================
Handles token swaps on Base L2 DEXes (Aerodrome, Uniswap V3).
Uses web3.py for on-chain operations.

v6.3: Initial DeFi trading capabilities.

Architecture:
- Portfolio tracking (positions, P&L, balances)
- Swap execution via DEX routers
- Risk management (stop-loss, position sizing, daily limits)
- Trade history logging
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("TheConstituent.DeFiTrader")

_web3_available = False
try:
    from web3 import Web3
    from eth_account import Account
    _web3_available = True
except ImportError:
    logger.info("web3 not installed — DeFi trading disabled")

from ..config.trading import trading_config


# Minimal ABIs for DeFi operations
ERC20_ABI = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "name": "approve", "outputs": [{"name": "", "type": "bool"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "name",
     "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
]

# Uniswap V3 SwapRouter exactInputSingle
UNISWAP_V3_SWAP_ABI = [
    {
        "inputs": [{
            "components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "deadline", "type": "uint256"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"},
            ],
            "name": "params",
            "type": "tuple",
        }],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]

# Uniswap V3 Quoter
QUOTER_ABI = [
    {
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"},
        ],
        "name": "quoteExactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


class DeFiTrader:
    """
    DeFi trading engine for The Constituent on Base L2.

    Capabilities:
    - Get token balances and prices
    - Execute swaps via Uniswap V3
    - Track portfolio positions with P&L
    - Enforce risk limits (position size, stop-loss, daily loss)
    - Log all trades for transparency
    """

    _RPC_ENDPOINTS = [
        "https://mainnet.base.org",
        "https://base.drpc.org",
        "https://base-mainnet.public.blastapi.io",
        "https://1rpc.io/base",
    ]

    def __init__(self):
        self.w3: Optional[Web3] = None
        self.account = None
        self._connected = False
        self._portfolio: Dict = {}
        self._trade_history: List[Dict] = []
        self._daily_pnl: float = 0.0
        self._daily_pnl_date: str = ""

        if not _web3_available:
            logger.warning("DeFi trader unavailable (web3 not installed)")
            return

        # Load wallet
        private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
        if private_key:
            try:
                self.account = Account.from_key(private_key)
                logger.info(f"DeFi trader wallet: {self.account.address}")
            except Exception as e:
                logger.error(f"Invalid private key: {e}")

        # Connect to Base
        self._connect()

        # Load persistent state
        self._load_portfolio()
        self._load_trade_history()

    def _connect(self) -> bool:
        """Connect to Base L2 RPC."""
        if not _web3_available:
            return False

        env_rpc = os.getenv("BASE_RPC_URL", "")
        rpc_list = ([env_rpc] if env_rpc else []) + self._RPC_ENDPOINTS

        for rpc_url in rpc_list:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                w3.eth.block_number  # Test connection
                self.w3 = w3
                self._connected = True
                logger.info(f"DeFi trader connected: {rpc_url}")
                return True
            except Exception as e:
                logger.debug(f"RPC {rpc_url} failed: {e}")
                continue

        logger.warning("DeFi trader: no Base RPC available")
        return False

    def _ensure_connected(self) -> bool:
        """Reconnect if needed."""
        if self._connected:
            try:
                self.w3.eth.block_number
                return True
            except Exception:
                self._connected = False
        return self._connect()

    # =================================================================
    # Portfolio Management
    # =================================================================

    def _load_portfolio(self):
        """Load portfolio from disk."""
        path = Path(trading_config.PORTFOLIO_FILE)
        if path.exists():
            try:
                self._portfolio = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load portfolio: {e}")
                self._portfolio = {"positions": {}, "total_invested": 0, "realized_pnl": 0}
        else:
            self._portfolio = {"positions": {}, "total_invested": 0, "realized_pnl": 0}

    def _save_portfolio(self):
        """Save portfolio to disk."""
        path = Path(trading_config.PORTFOLIO_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._portfolio, indent=2, default=str), encoding="utf-8")

    def _load_trade_history(self):
        """Load trade history from disk."""
        path = Path(trading_config.TRADE_HISTORY_FILE)
        if path.exists():
            try:
                self._trade_history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._trade_history = []
        else:
            self._trade_history = []

    def _save_trade_history(self):
        """Save trade history to disk."""
        path = Path(trading_config.TRADE_HISTORY_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._trade_history, indent=2, default=str), encoding="utf-8")

    def _log_trade(self, trade: Dict):
        """Log a trade to history."""
        trade["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._trade_history.append(trade)
        self._save_trade_history()
        logger.info(f"Trade logged: {trade['action']} {trade.get('symbol', '?')} "
                     f"amount={trade.get('amount_in', 0)}")

    # =================================================================
    # Token Operations
    # =================================================================

    def get_token_balance(self, token_address: str) -> Dict:
        """Get ERC-20 token balance for agent wallet."""
        if not self._ensure_connected():
            return {"error": "Not connected to Base"}
        if not self.account:
            return {"error": "Wallet not configured"}

        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI,
            )
            balance_raw = contract.functions.balanceOf(self.account.address).call()
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()
            balance = balance_raw / (10 ** decimals)

            return {
                "token": token_address,
                "symbol": symbol,
                "balance": balance,
                "balance_raw": str(balance_raw),
                "decimals": decimals,
            }
        except Exception as e:
            return {"error": str(e), "token": token_address}

    def get_eth_balance(self) -> Dict:
        """Get ETH balance for gas."""
        if not self._ensure_connected():
            return {"error": "Not connected to Base"}
        if not self.account:
            return {"error": "Wallet not configured"}

        try:
            balance_wei = self.w3.eth.get_balance(self.account.address)
            balance_eth = float(self.w3.from_wei(balance_wei, "ether"))
            return {"eth_balance": balance_eth, "wallet": self.account.address}
        except Exception as e:
            return {"error": str(e)}

    def get_portfolio_status(self) -> Dict:
        """Get full portfolio status with live balances."""
        if not self._ensure_connected():
            return {"error": "Not connected to Base"}

        result = {
            "wallet": self.account.address if self.account else "not configured",
            "connected": self._connected,
        }

        # ETH balance (for gas)
        eth = self.get_eth_balance()
        result["eth_balance"] = eth.get("eth_balance", 0)

        # $CLAWNCH balance
        clawnch = self.get_token_balance(trading_config.CLAWNCH_TOKEN)
        result["clawnch_balance"] = clawnch.get("balance", 0)

        # $REPUBLIC balance
        republic = self.get_token_balance(trading_config.REPUBLIC_TOKEN)
        result["republic_balance"] = republic.get("balance", 0)

        # Open positions
        positions = self._portfolio.get("positions", {})
        result["open_positions"] = len(positions)
        result["positions"] = positions
        result["total_invested"] = self._portfolio.get("total_invested", 0)
        result["realized_pnl"] = self._portfolio.get("realized_pnl", 0)

        # Risk status
        result["risk"] = {
            "max_position_pct": trading_config.MAX_POSITION_PERCENT,
            "max_daily_loss_pct": trading_config.MAX_DAILY_LOSS_PERCENT,
            "daily_pnl": self._daily_pnl,
            "stop_loss_pct": trading_config.STOP_LOSS_PERCENT,
            "reserve_pct": trading_config.RESERVE_PERCENT,
        }

        # Recent trades
        result["recent_trades"] = self._trade_history[-5:] if self._trade_history else []

        return result

    # =================================================================
    # Price Quotes
    # =================================================================

    def get_quote(self, token_in: str, token_out: str, amount_in: float,
                  fee: int = 3000) -> Dict:
        """
        Get a price quote from Uniswap V3 on Base.

        Args:
            token_in: Address of input token
            token_out: Address of output token
            amount_in: Amount of input token (human-readable)
            fee: Pool fee tier (500=0.05%, 3000=0.3%, 10000=1%)

        Returns:
            {"amount_out": float, "price": float, ...}
        """
        if not self._ensure_connected():
            return {"error": "Not connected to Base"}

        try:
            # Get decimals for input token
            in_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_in), abi=ERC20_ABI)
            in_decimals = in_contract.functions.decimals().call()
            amount_in_raw = int(amount_in * (10 ** in_decimals))

            # Get decimals for output token
            out_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_out), abi=ERC20_ABI)
            out_decimals = out_contract.functions.decimals().call()

            # Quote via Uniswap V3 Quoter
            quoter = self.w3.eth.contract(
                address=Web3.to_checksum_address(trading_config.UNISWAP_V3_QUOTER),
                abi=QUOTER_ABI,
            )

            amount_out_raw = quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                amount_in_raw,
                0,  # sqrtPriceLimitX96 = 0 means no limit
            ).call()

            amount_out = amount_out_raw / (10 ** out_decimals)
            price = amount_out / amount_in if amount_in > 0 else 0

            return {
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "amount_out": amount_out,
                "price": price,
                "fee_tier": fee,
            }
        except Exception as e:
            return {"error": str(e), "token_in": token_in, "token_out": token_out}

    # =================================================================
    # Risk Checks
    # =================================================================

    def _check_risk(self, amount: float, portfolio_value: float) -> Dict:
        """
        Check if a trade passes risk limits.

        Returns {"ok": True} or {"ok": False, "reason": "..."}
        """
        # Reset daily P&L if new day
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_pnl_date != today:
            self._daily_pnl = 0.0
            self._daily_pnl_date = today

        # Check daily loss limit
        if portfolio_value > 0:
            daily_loss_pct = abs(min(0, self._daily_pnl)) / portfolio_value * 100
            if daily_loss_pct >= trading_config.MAX_DAILY_LOSS_PERCENT:
                return {"ok": False, "reason": f"Daily loss limit reached ({daily_loss_pct:.1f}% >= {trading_config.MAX_DAILY_LOSS_PERCENT}%)"}

        # Check position size
        if portfolio_value > 0:
            position_pct = (amount / portfolio_value) * 100
            if position_pct > trading_config.MAX_POSITION_PERCENT:
                return {"ok": False, "reason": f"Position too large ({position_pct:.1f}% > {trading_config.MAX_POSITION_PERCENT}% max)"}

        # Check reserve
        reserve = portfolio_value * trading_config.RESERVE_PERCENT / 100
        available = portfolio_value - reserve
        if amount > available:
            return {"ok": False, "reason": f"Would breach reserve. Available: {available:.0f}, requested: {amount:.0f}"}

        # Check max open positions
        open_positions = len(self._portfolio.get("positions", {}))
        if open_positions >= trading_config.MAX_OPEN_POSITIONS:
            return {"ok": False, "reason": f"Max open positions reached ({open_positions}/{trading_config.MAX_OPEN_POSITIONS})"}

        # Check minimum trade
        if amount < trading_config.MIN_TRADE_AMOUNT:
            return {"ok": False, "reason": f"Below minimum trade ({amount:.0f} < {trading_config.MIN_TRADE_AMOUNT:.0f})"}

        return {"ok": True}

    # =================================================================
    # Swap Execution
    # =================================================================

    def _approve_token(self, token_address: str, spender: str, amount_raw: int) -> Dict:
        """Approve a spender to use tokens (ERC-20 approve)."""
        if not self.account:
            return {"error": "Wallet not configured"}

        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI,
            )

            # Check existing allowance
            current = contract.functions.allowance(
                self.account.address,
                Web3.to_checksum_address(spender),
            ).call()

            if current >= amount_raw:
                return {"status": "already_approved", "allowance": current}

            # Build approve tx
            nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
            tx = contract.functions.approve(
                Web3.to_checksum_address(spender),
                amount_raw,
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": 8453,
            })

            gas = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas * 1.3)

            private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex

            # Wait for confirmation (Base L2 = ~2s blocks)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            if receipt.status != 1:
                return {"error": "Approval transaction reverted", "tx_hash": tx_hex}

            logger.info(f"Token approved: {token_address} -> {spender} amount={amount_raw}")
            return {"status": "approved", "tx_hash": tx_hex}

        except Exception as e:
            return {"error": f"Approval failed: {e}"}

    def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        reason: str = "",
        fee: int = 3000,
        slippage_bps: int = None,
    ) -> Dict:
        """
        Execute a token swap on Uniswap V3 (Base L2).

        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Amount of input token (human-readable)
            reason: Why this trade is being made (for logging)
            fee: Uniswap V3 fee tier (3000 = 0.3%)
            slippage_bps: Slippage tolerance in basis points

        Returns:
            {"status": "ok", "tx_hash": "0x...", "amount_out": ..., ...}
        """
        if not self._ensure_connected():
            return {"error": "Not connected to Base"}
        if not self.account:
            return {"error": "Wallet not configured"}

        slippage_bps = slippage_bps or trading_config.DEFAULT_SLIPPAGE_BPS
        if slippage_bps > trading_config.MAX_SLIPPAGE_BPS:
            return {"error": f"Slippage too high ({slippage_bps} bps > {trading_config.MAX_SLIPPAGE_BPS} max)"}

        # Get quote first
        quote = self.get_quote(token_in, token_out, amount_in, fee)
        if "error" in quote:
            return {"error": f"Quote failed: {quote['error']}"}

        expected_out = quote["amount_out"]
        min_out = expected_out * (1 - slippage_bps / 10000)

        # Get input token info
        in_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_in), abi=ERC20_ABI)
        in_decimals = in_contract.functions.decimals().call()
        in_symbol = in_contract.functions.symbol().call()
        amount_in_raw = int(amount_in * (10 ** in_decimals))

        out_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_out), abi=ERC20_ABI)
        out_decimals = out_contract.functions.decimals().call()
        out_symbol = out_contract.functions.symbol().call()
        min_out_raw = int(min_out * (10 ** out_decimals))

        # Check balance
        balance = in_contract.functions.balanceOf(self.account.address).call()
        if balance < amount_in_raw:
            return {"error": f"Insufficient {in_symbol} balance. Have {balance / 10**in_decimals:.2f}, need {amount_in:.2f}"}

        # Approve router
        router_address = trading_config.UNISWAP_V3_ROUTER
        approval = self._approve_token(token_in, router_address, amount_in_raw)
        if "error" in approval:
            return approval

        # Build swap tx
        try:
            router = self.w3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=UNISWAP_V3_SWAP_ABI,
            )

            deadline = int(time.time()) + 300  # 5 min deadline

            swap_params = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                self.account.address,
                deadline,
                amount_in_raw,
                min_out_raw,
                0,  # sqrtPriceLimitX96
            )

            nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
            tx = router.functions.exactInputSingle(swap_params).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": 8453,
                "value": 0,
            })

            gas = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas * 1.3)

            # Sign and send
            private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = tx_hash.hex()
            if not tx_hex.startswith("0x"):
                tx_hex = "0x" + tx_hex

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status != 1:
                self._log_trade({
                    "action": "swap_failed",
                    "token_in": token_in, "symbol_in": in_symbol,
                    "token_out": token_out, "symbol_out": out_symbol,
                    "amount_in": amount_in, "reason": reason,
                    "tx_hash": tx_hex, "error": "Transaction reverted",
                })
                return {"error": "Swap transaction reverted", "tx_hash": tx_hex}

            # Get actual output amount from balance change
            new_balance = out_contract.functions.balanceOf(self.account.address).call()
            # Log the trade
            trade = {
                "action": "swap",
                "token_in": token_in, "symbol_in": in_symbol,
                "token_out": token_out, "symbol_out": out_symbol,
                "amount_in": amount_in,
                "expected_out": expected_out,
                "min_out": min_out,
                "reason": reason,
                "tx_hash": tx_hex,
                "gas_used": receipt.gasUsed,
                "block": receipt.blockNumber,
            }
            self._log_trade(trade)

            logger.info(f"Swap executed: {amount_in} {in_symbol} -> {out_symbol} | tx={tx_hex[:16]}...")

            return {
                "status": "ok",
                "tx_hash": tx_hex,
                "amount_in": amount_in,
                "symbol_in": in_symbol,
                "expected_out": expected_out,
                "symbol_out": out_symbol,
                "gas_used": receipt.gasUsed,
                "explorer_url": f"https://basescan.org/tx/{tx_hex}",
            }

        except Exception as e:
            logger.error(f"Swap failed: {e}")
            self._log_trade({
                "action": "swap_error",
                "token_in": token_in, "token_out": token_out,
                "amount_in": amount_in, "reason": reason,
                "error": str(e),
            })
            return {"error": str(e)}

    # =================================================================
    # High-level Trading Operations
    # =================================================================

    def buy_token(self, token_address: str, clawnch_amount: float,
                  reason: str = "scout buy") -> Dict:
        """
        Buy a token using $CLAWNCH.
        Routes: CLAWNCH -> WETH -> target token (via Uniswap V3)

        Args:
            token_address: Token to buy
            clawnch_amount: Amount of $CLAWNCH to spend
            reason: Trade rationale
        """
        # Risk check
        clawnch_balance = self.get_token_balance(trading_config.CLAWNCH_TOKEN)
        if "error" in clawnch_balance:
            return clawnch_balance

        portfolio_value = clawnch_balance.get("balance", 0)
        risk = self._check_risk(clawnch_amount, portfolio_value)
        if not risk["ok"]:
            return {"error": f"Risk check failed: {risk['reason']}"}

        # Step 1: CLAWNCH -> WETH
        step1 = self.execute_swap(
            trading_config.CLAWNCH_TOKEN,
            trading_config.WETH,
            clawnch_amount,
            reason=f"Step 1/2: {reason}",
            fee=10000,  # 1% fee for less liquid pairs
        )
        if "error" in step1:
            return {"error": f"CLAWNCH->WETH failed: {step1['error']}"}

        weth_received = step1.get("expected_out", 0)

        # Step 2: WETH -> target token
        step2 = self.execute_swap(
            trading_config.WETH,
            token_address,
            weth_received,
            reason=f"Step 2/2: {reason}",
            fee=3000,
        )
        if "error" in step2:
            return {"error": f"WETH->target failed: {step2['error']}. WETH stuck in wallet."}

        # Record position
        positions = self._portfolio.setdefault("positions", {})
        positions[token_address] = {
            "entry_amount_clawnch": clawnch_amount,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "tx_buy": step2.get("tx_hash", ""),
        }
        self._portfolio["total_invested"] = self._portfolio.get("total_invested", 0) + clawnch_amount
        self._save_portfolio()

        return {
            "status": "ok",
            "action": "buy",
            "token": token_address,
            "clawnch_spent": clawnch_amount,
            "weth_intermediate": weth_received,
            "tx_hash": step2.get("tx_hash", ""),
            "explorer_url": step2.get("explorer_url", ""),
        }

    def sell_token(self, token_address: str, amount: float = 0,
                   reason: str = "take profit") -> Dict:
        """
        Sell a token back to $CLAWNCH.
        Routes: target token -> WETH -> CLAWNCH

        Args:
            token_address: Token to sell
            amount: Amount to sell (0 = sell all)
            reason: Trade rationale
        """
        # Get balance
        balance = self.get_token_balance(token_address)
        if "error" in balance:
            return balance

        sell_amount = amount if amount > 0 else balance.get("balance", 0)
        if sell_amount <= 0:
            return {"error": "Nothing to sell"}

        # Step 1: token -> WETH
        step1 = self.execute_swap(
            token_address,
            trading_config.WETH,
            sell_amount,
            reason=f"Step 1/2: {reason}",
            fee=3000,
        )
        if "error" in step1:
            return {"error": f"token->WETH failed: {step1['error']}"}

        weth_received = step1.get("expected_out", 0)

        # Step 2: WETH -> CLAWNCH
        step2 = self.execute_swap(
            trading_config.WETH,
            trading_config.CLAWNCH_TOKEN,
            weth_received,
            reason=f"Step 2/2: {reason}",
            fee=10000,
        )
        if "error" in step2:
            return {"error": f"WETH->CLAWNCH failed: {step2['error']}. WETH stuck in wallet."}

        clawnch_received = step2.get("expected_out", 0)

        # Update position
        positions = self._portfolio.get("positions", {})
        entry = positions.pop(token_address, {})
        entry_cost = entry.get("entry_amount_clawnch", 0)
        pnl = clawnch_received - entry_cost if entry_cost > 0 else 0

        self._portfolio["realized_pnl"] = self._portfolio.get("realized_pnl", 0) + pnl
        self._daily_pnl += pnl
        self._save_portfolio()

        return {
            "status": "ok",
            "action": "sell",
            "token": token_address,
            "sold_amount": sell_amount,
            "clawnch_received": clawnch_received,
            "pnl": pnl,
            "pnl_pct": (pnl / entry_cost * 100) if entry_cost > 0 else 0,
            "tx_hash": step2.get("tx_hash", ""),
            "explorer_url": step2.get("explorer_url", ""),
        }

    def buy_republic(self, clawnch_amount: float, reason: str = "market making") -> Dict:
        """Buy $REPUBLIC using $CLAWNCH (for market making / price support)."""
        return self.buy_token(trading_config.REPUBLIC_TOKEN, clawnch_amount, reason)

    # =================================================================
    # Trade History & Reports
    # =================================================================

    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """Get recent trade history."""
        return self._trade_history[-limit:]

    def get_daily_report(self) -> str:
        """Generate daily trading P&L report."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_trades = [t for t in self._trade_history
                        if t.get("timestamp", "").startswith(today)]

        portfolio = self.get_portfolio_status()
        if "error" in portfolio:
            return f"Portfolio unavailable: {portfolio['error']}"

        lines = [
            f"Trading Report — {today}",
            f"{'=' * 40}",
            f"$CLAWNCH balance: {portfolio.get('clawnch_balance', 0):,.0f}",
            f"$REPUBLIC balance: {portfolio.get('republic_balance', 0):,.0f}",
            f"ETH (gas): {portfolio.get('eth_balance', 0):.6f}",
            f"Open positions: {portfolio.get('open_positions', 0)}",
            f"Realized P&L: {self._portfolio.get('realized_pnl', 0):,.0f} CLAWNCH",
            f"Daily P&L: {self._daily_pnl:,.0f} CLAWNCH",
            f"Trades today: {len(today_trades)}",
        ]

        if today_trades:
            lines.append(f"\nToday's trades:")
            for t in today_trades[-10:]:
                action = t.get("action", "?")
                sym_in = t.get("symbol_in", "?")
                sym_out = t.get("symbol_out", "?")
                amt = t.get("amount_in", 0)
                lines.append(f"  {action}: {amt:,.0f} {sym_in} -> {sym_out}")

        positions = portfolio.get("positions", {})
        if positions:
            lines.append(f"\nOpen positions:")
            for addr, pos in positions.items():
                lines.append(f"  {addr[:10]}...: {pos.get('entry_amount_clawnch', 0):,.0f} CLAWNCH ({pos.get('reason', '?')})")

        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Quick status check."""
        return {
            "connected": self._connected,
            "wallet": self.account.address if self.account else None,
            "web3_available": _web3_available,
            "open_positions": len(self._portfolio.get("positions", {})),
            "realized_pnl": self._portfolio.get("realized_pnl", 0),
            "daily_pnl": self._daily_pnl,
            "total_trades": len(self._trade_history),
        }
