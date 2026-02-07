"""
Clawnch Token Launch Integration
==================================
Enables The Constituent to deploy $REPUBLIC token on Base L2 via Clawnch.

Clawnch launch flow (NOT smart contract deployment):
1. Burn $CLAWNCH tokens to dead address (ERC-20 transfer)
2. Post `!clawnch` formatted message to Moltbook m/clawnch
3. Clawnch bot auto-deploys token via Clanker within ~1 minute
4. Agent receives dev allocation (locked in vault for 7 days)
5. Agent earns 80% of Uniswap V4 LP trading fees forever

Key addresses:
- $CLAWNCH token: 0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be
- Burn address:   0x000000000000000000000000000000000000dEaD
- FeeLocker:      0xF3622742b1E446D92e45E22923Ef11C2fcD55D68

Rate limit: 1 token launch per 24 hours per agent (shared across all platforms).

Requires:
- web3 >= 6.15.0
- eth-account >= 0.11.0
- Environment: BASE_RPC_URL, AGENT_WALLET_ADDRESS, AGENT_WALLET_PRIVATE_KEY
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("TheConstituent.Clawnch")

# Lazy import — web3 may not be installed yet
_web3_available = False
try:
    from web3 import Web3
    from eth_account import Account
    _web3_available = True
except ImportError:
    logger.info("web3 not installed — Clawnch integration disabled. pip install web3 eth-account")

# ERC-20 transfer ABI (minimal — only what we need for burn)
_ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

# Clawnch constants
CLAWNCH_TOKEN = "0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be"
BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"
CLANKER_FEE_LOCKER = "0xF3622742b1E446D92e45E22923Ef11C2fcD55D68"
BURN_AMOUNT = 4_000_000  # 4M $CLAWNCH


class ClawnchLauncher:
    """
    Handles $REPUBLIC token deployment via Clawnch on Base L2.

    Clawnch is an agent-native token launchpad. Tokens are NOT deployed
    via smart contract constructor — instead, the agent:
    1. Burns $CLAWNCH to dead address (ERC-20 transfer)
    2. Posts a `!clawnch` formatted message to Moltbook m/clawnch
    3. Clawnch bot picks it up and auto-deploys via Clanker
    """

    def __init__(self):
        self._connected = False
        self.w3 = None
        self.account = None
        self.wallet_address = ""
        self.token_address: Optional[str] = None

        if not _web3_available:
            logger.warning("Clawnch integration unavailable (web3 not installed)")
            return

        rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
        self.wallet_address = os.getenv("AGENT_WALLET_ADDRESS", "")

        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            if self.w3.is_connected():
                self._connected = True
                logger.info(f"Connected to Base L2: {rpc_url}")

                if private_key:
                    self.account = Account.from_key(private_key)
                    logger.info(f"Agent wallet: {self.account.address}")
            else:
                logger.warning(f"Cannot connect to Base RPC: {rpc_url}")
        except Exception as e:
            logger.error(f"Clawnch init error: {e}")

    @property
    def is_available(self) -> bool:
        return _web3_available and self._connected

    # ------------------------------------------------------------------
    #  Step 1: Burn $CLAWNCH
    # ------------------------------------------------------------------

    def check_clawnch_balance(self) -> Dict:
        """Check agent's $CLAWNCH balance."""
        if not self.is_available:
            return {"error": "Not connected to Base"}

        try:
            clawnch = self.w3.eth.contract(
                address=Web3.to_checksum_address(CLAWNCH_TOKEN),
                abi=_ERC20_ABI,
            )
            decimals = clawnch.functions.decimals().call()
            balance_raw = clawnch.functions.balanceOf(
                Web3.to_checksum_address(self.wallet_address)
            ).call()
            balance = balance_raw / (10 ** decimals)

            return {
                "balance": balance,
                "required": BURN_AMOUNT,
                "sufficient": balance >= BURN_AMOUNT,
                "decimals": decimals,
            }
        except Exception as e:
            return {"error": str(e)}

    def burn_clawnch(self, dry_run: bool = False) -> Dict:
        """
        Burn 4M $CLAWNCH by transferring to dead address.

        Returns dict with burn tx hash on success.
        """
        if not self.is_available or not self.account:
            return {"error": "Not connected or wallet not configured"}

        try:
            clawnch = self.w3.eth.contract(
                address=Web3.to_checksum_address(CLAWNCH_TOKEN),
                abi=_ERC20_ABI,
            )
            decimals = clawnch.functions.decimals().call()
            burn_amount_raw = BURN_AMOUNT * (10 ** decimals)

            # Check balance first
            balance = clawnch.functions.balanceOf(
                Web3.to_checksum_address(self.wallet_address)
            ).call()
            if balance < burn_amount_raw:
                return {
                    "error": f"Insufficient $CLAWNCH. Have {balance / (10 ** decimals):,.0f}, need {BURN_AMOUNT:,}",
                }

            # Build burn transaction (ERC-20 transfer to dead address)
            tx = clawnch.functions.transfer(
                Web3.to_checksum_address(BURN_ADDRESS),
                burn_amount_raw,
            ).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gasPrice": self.w3.eth.gas_price,
                "chainId": 8453,  # Base mainnet
            })

            gas_estimate = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.2)

            if dry_run:
                return {
                    "status": "dry_run",
                    "burn_amount": f"{BURN_AMOUNT:,} $CLAWNCH",
                    "to": BURN_ADDRESS,
                    "gas_estimate": gas_estimate,
                    "gas_cost_eth": float(self.w3.from_wei(
                        tx["gas"] * tx["gasPrice"], "ether"
                    )),
                }

            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logger.info(f"Burn tx sent: {tx_hash.hex()}")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status == 1:
                tx_hash_hex = tx_hash.hex()
                logger.info(f"Burn successful: {tx_hash_hex}")
                return {
                    "status": "success",
                    "tx_hash": tx_hash_hex,
                    "burn_amount": f"{BURN_AMOUNT:,} $CLAWNCH",
                    "explorer_url": f"https://basescan.org/tx/{tx_hash_hex}",
                }
            else:
                return {"error": f"Burn tx failed. Hash: {tx_hash.hex()}"}

        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    #  Step 2: Build Moltbook !clawnch post
    # ------------------------------------------------------------------

    def build_launch_post(
        self,
        description: str,
        image_url: str,
        burn_tx_hash: Optional[str] = None,
        website: Optional[str] = None,
        twitter: Optional[str] = None,
    ) -> str:
        """
        Build the `!clawnch` formatted post for Moltbook m/clawnch.

        The JSON must be wrapped in a code block (triple backticks)
        because Moltbook uses Markdown and raw JSON gets mangled.

        Returns the full post content ready to submit to Moltbook.
        """
        from ..config.tokenomics import tokenomics

        payload = {
            "name": tokenomics.NAME,
            "symbol": tokenomics.SYMBOL,
            "wallet": self.wallet_address,
            "description": description,
            "image": image_url,
        }

        # Optional fields
        if burn_tx_hash:
            payload["burnTxHash"] = burn_tx_hash
        if website:
            payload["website"] = website
        if twitter:
            payload["twitter"] = twitter

        # Wrap in code block to prevent Markdown mangling
        json_block = json.dumps(payload, indent=2)
        return f"!clawnch\n```\n{json_block}\n```"

    # ------------------------------------------------------------------
    #  Readiness & Status
    # ------------------------------------------------------------------

    def check_launch_readiness(self) -> Dict:
        """Verify all conditions met for token launch."""
        checks = {}

        # Check web3 connection
        checks["web3_connected"] = self._connected

        # Check wallet
        checks["wallet_configured"] = bool(self.wallet_address)

        # Check wallet ETH balance (for gas on burn tx)
        if self._connected and self.wallet_address:
            try:
                balance_wei = self.w3.eth.get_balance(self.wallet_address)
                balance_eth = self.w3.from_wei(balance_wei, "ether")
                checks["wallet_balance_eth"] = float(balance_eth)
                checks["sufficient_gas"] = float(balance_eth) > 0.001
            except Exception as e:
                checks["wallet_balance_error"] = str(e)
                checks["sufficient_gas"] = False
        else:
            checks["sufficient_gas"] = False

        # Check $CLAWNCH balance
        if self._connected and self.wallet_address:
            clawnch_check = self.check_clawnch_balance()
            checks["clawnch_balance"] = clawnch_check.get("balance", 0)
            checks["clawnch_sufficient"] = clawnch_check.get("sufficient", False)
        else:
            checks["clawnch_sufficient"] = False

        # Check constitution exists
        constitution_path = Path("constitution")
        if constitution_path.exists():
            articles = list(constitution_path.rglob("ARTICLE_*.md"))
            checks["constitution_articles"] = len(articles)
            checks["constitution_ready"] = len(articles) >= 7
        else:
            checks["constitution_ready"] = False

        # Overall readiness
        checks["ready"] = all([
            checks.get("web3_connected"),
            checks.get("wallet_configured"),
            checks.get("sufficient_gas"),
            checks.get("clawnch_sufficient"),
            checks.get("constitution_ready"),
        ])

        if not checks["ready"]:
            issues = []
            if not checks.get("web3_connected"):
                issues.append("Base RPC not connected")
            if not checks.get("wallet_configured"):
                issues.append("AGENT_WALLET_ADDRESS not set")
            if not checks.get("sufficient_gas"):
                issues.append("Insufficient ETH for gas")
            if not checks.get("clawnch_sufficient"):
                clawnch_bal = checks.get("clawnch_balance", 0)
                issues.append(f"Need {BURN_AMOUNT:,} $CLAWNCH (have {clawnch_bal:,.0f})")
            if not checks.get("constitution_ready"):
                issues.append(f"Constitution needs 7+ articles (have {checks.get('constitution_articles', 0)})")
            checks["issues"] = issues

        return checks

    def estimate_costs(self) -> Dict:
        """Estimate gas cost for the burn transaction."""
        if not self.is_available:
            return {"error": "Not connected to Base"}

        try:
            gas_price = self.w3.eth.gas_price
            # ERC-20 transfer gas is ~65,000 (not 500k like contract deployment)
            estimated_gas = 65_000
            gas_cost_wei = gas_price * estimated_gas
            gas_cost_eth = float(self.w3.from_wei(gas_cost_wei, "ether"))

            return {
                "gas_price_gwei": float(self.w3.from_wei(gas_price, "gwei")),
                "estimated_gas_units": estimated_gas,
                "gas_cost_eth": gas_cost_eth,
                "clawnch_burn": f"{BURN_AMOUNT:,} $CLAWNCH",
                "dev_allocation": "4% (4B $REPUBLIC)",
                "total_eth_needed": gas_cost_eth + 0.0005,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_token_status(self) -> Dict:
        """Get status of deployed token (post-launch)."""
        token_address = os.getenv("REPUBLIC_TOKEN_ADDRESS", "")
        if not token_address:
            return {"status": "not_launched", "message": "Token not yet deployed"}

        if not self.is_available:
            return {"status": "error", "message": "Not connected to Base"}

        try:
            result = {
                "status": "launched",
                "token_address": token_address,
                "explorer_url": f"https://basescan.org/token/{token_address}",
            }

            if self.wallet_address:
                result["wallet"] = self.wallet_address

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_status(self) -> Dict:
        """Get overall Clawnch integration status."""
        return {
            "web3_available": _web3_available,
            "connected": self._connected,
            "wallet": self.wallet_address or "not configured",
            "clawnch_token": CLAWNCH_TOKEN,
            "burn_amount": f"{BURN_AMOUNT:,} $CLAWNCH",
            "dev_allocation": "4%",
            "launch_method": "Moltbook m/clawnch post",
            "token_deployed": bool(os.getenv("REPUBLIC_TOKEN_ADDRESS")),
        }

    # ------------------------------------------------------------------
    #  Fee Claiming (post-launch)
    # ------------------------------------------------------------------

    def claim_fees(self) -> Dict:
        """
        Claim accumulated trading fees from Clanker FeeLocker.

        Post-launch: agent earns 80% of Uniswap V4 LP trading fees.
        Fees accumulate in the FeeLocker and must be claimed periodically.
        """
        token_address = os.getenv("REPUBLIC_TOKEN_ADDRESS", "")
        if not token_address:
            return {"error": "Token not deployed yet"}
        if not self.is_available or not self.account:
            return {"error": "Not connected or wallet not configured"}

        # FeeLocker ABI would be needed here — placeholder for now
        # The actual ABI depends on Clanker's FeeLocker contract interface
        return {
            "status": "not_implemented",
            "fee_locker": CLANKER_FEE_LOCKER,
            "message": "Fee claiming requires Clanker FeeLocker ABI. "
                       "Check https://basescan.org/address/" + CLANKER_FEE_LOCKER,
        }
