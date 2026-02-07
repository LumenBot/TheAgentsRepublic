"""
Clawnch Token Launch Integration
==================================
Enables The Constituent to deploy $REPUBLIC token on Base L2 via Clawnch.

Process:
1. Operator approves launch via Telegram (/launch_token)
2. Agent verifies readiness conditions
3. Constructs launch transaction
4. Operator confirms final approval (/confirm_launch)
5. Agent executes deployment
6. Monitors initial trading

Requires:
- web3 >= 6.15.0
- eth-account >= 0.11.0
- Environment: BASE_RPC_URL, AGENT_WALLET_ADDRESS, AGENT_WALLET_PRIVATE_KEY,
               CLAWNCH_CONTRACT_ADDRESS
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from agent.config.tokenomics import tokenomics

logger = logging.getLogger("TheConstituent.Clawnch")

# Lazy import — web3 may not be installed yet
_web3_available = False
try:
    from web3 import Web3
    from eth_account import Account
    _web3_available = True
except ImportError:
    logger.info("web3 not installed — Clawnch integration disabled. pip install web3 eth-account")


class ClawnchLauncher:
    """
    Handles $REPUBLIC token deployment via Clawnch on Base L2.

    Clawnch is an agent-native token launchpad that allows AI agents
    to deploy tokens by burning $CLAWNCH tokens.
    """

    def __init__(self):
        self._connected = False
        self.w3 = None
        self.account = None
        self.token_address: Optional[str] = None

        if not _web3_available:
            logger.warning("Clawnch integration unavailable (web3 not installed)")
            return

        rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
        self.clawnch_contract = os.getenv("CLAWNCH_CONTRACT_ADDRESS", "")
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

    def check_launch_readiness(self) -> Dict:
        """Verify all conditions met for token launch."""
        checks = {}

        # Check web3 connection
        checks["web3_connected"] = self._connected

        # Check wallet
        checks["wallet_configured"] = bool(self.wallet_address)

        # Check wallet balance
        if self._connected and self.wallet_address:
            try:
                balance_wei = self.w3.eth.get_balance(self.wallet_address)
                balance_eth = self.w3.from_wei(balance_wei, "ether")
                checks["wallet_balance_eth"] = float(balance_eth)
                checks["sufficient_gas"] = float(balance_eth) > 0.01
            except Exception as e:
                checks["wallet_balance_error"] = str(e)
                checks["sufficient_gas"] = False
        else:
            checks["sufficient_gas"] = False

        # Check Clawnch contract
        checks["clawnch_contract_set"] = bool(self.clawnch_contract)

        # Check token metadata
        checks["token_image_exists"] = Path(tokenomics.IMAGE_PATH).exists()
        checks["token_description_set"] = bool(tokenomics.DESCRIPTION)

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
            checks.get("clawnch_contract_set"),
            checks.get("constitution_ready"),
            checks.get("token_image_exists"),
            checks.get("token_description_set"),
        ])

        if not checks["ready"]:
            issues = []
            if not checks.get("web3_connected"):
                issues.append("Base RPC not connected")
            if not checks.get("wallet_configured"):
                issues.append("AGENT_WALLET_ADDRESS not set")
            if not checks.get("sufficient_gas"):
                issues.append("Insufficient ETH for gas")
            if not checks.get("clawnch_contract_set"):
                issues.append("CLAWNCH_CONTRACT_ADDRESS not set")
            if not checks.get("constitution_ready"):
                issues.append(f"Constitution needs 7+ articles (have {checks.get('constitution_articles', 0)})")
            if not checks.get("token_image_exists"):
                issues.append("Token image not found at assets/republic-token.png")
            if not checks.get("token_description_set"):
                issues.append("Token description not set in tokenomics config")
            checks["issues"] = issues

        return checks

    def get_token_metadata(self) -> Dict:
        """Return token metadata for Clawnch deployment.

        Maps to Clawnch !clawnch post fields:
          Required: name, symbol, wallet, description, image
          Optional: website, twitter, burnTxHash
        """
        image_exists = Path(tokenomics.IMAGE_PATH).exists()
        return {
            "name": tokenomics.NAME,
            "symbol": tokenomics.SYMBOL,
            "decimals": tokenomics.DECIMALS,
            "total_supply": tokenomics.TOTAL_SUPPLY,
            "description": tokenomics.DESCRIPTION,
            "image_url": tokenomics.IMAGE_URL,
            "image_path": tokenomics.IMAGE_PATH,
            "image_exists_locally": image_exists,
            "website": tokenomics.WEBSITE,
            "twitter": tokenomics.TWITTER,
        }

    def estimate_costs(self) -> Dict:
        """Estimate gas and burn costs for token launch."""
        if not self.is_available:
            return {"error": "Not connected to Base"}

        try:
            gas_price = self.w3.eth.gas_price
            estimated_gas = 500_000  # Conservative estimate for token deployment
            gas_cost_wei = gas_price * estimated_gas
            gas_cost_eth = float(self.w3.from_wei(gas_cost_wei, "ether"))

            return {
                "gas_price_gwei": float(self.w3.from_wei(gas_price, "gwei")),
                "estimated_gas_units": estimated_gas,
                "gas_cost_eth": gas_cost_eth,
                "clawnch_burn": "5,000,000 $CLAWNCH",
                "total_eth_needed": gas_cost_eth + 0.001,  # Small buffer
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
            # Basic token info
            result = {
                "status": "launched",
                "token_address": token_address,
                "explorer_url": f"https://basescan.org/token/{token_address}",
            }

            # Check wallet balance
            if self.wallet_address:
                # This would need the ERC20 ABI to check token balance
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
            "clawnch_contract": self.clawnch_contract or "not configured",
            "token_deployed": bool(os.getenv("REPUBLIC_TOKEN_ADDRESS")),
        }
