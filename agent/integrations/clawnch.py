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
import time
from pathlib import Path
from typing import Dict, Optional

import requests

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
                checks["sufficient_gas"] = float(balance_eth) > 0.0005  # ERC-20 transfer on Base ~$0.01
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
            estimated_gas = 65_000  # ERC-20 transfer on Base
            gas_cost_wei = gas_price * estimated_gas
            gas_cost_eth = float(self.w3.from_wei(gas_cost_wei, "ether"))

            return {
                "gas_price_gwei": float(self.w3.from_wei(gas_price, "gwei")),
                "estimated_gas_units": estimated_gas,
                "gas_cost_eth": gas_cost_eth,
                "clawnch_burn": f"{tokenomics.CLAWNCH_BURN_AMOUNT:,} $CLAWNCH",
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

    # =================================================================
    # Action Methods (execute on-chain and API operations)
    # =================================================================

    # Minimal ERC-20 ABI for transfer and balanceOf
    _ERC20_ABI = [
        {
            "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"
    CLAWNCH_TOKEN = "0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be"
    CLAWNCH_API_BASE = "https://clawn.ch/api"

    def get_clawnch_balance(self) -> Dict:
        """Check $CLAWNCH token balance of agent wallet."""
        if not self.is_available or not self.wallet_address:
            return {"error": "Web3 not connected or wallet not configured"}
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.CLAWNCH_TOKEN),
                abi=self._ERC20_ABI,
            )
            balance_wei = contract.functions.balanceOf(
                Web3.to_checksum_address(self.wallet_address)
            ).call()
            balance = balance_wei / 10**18
            return {
                "balance_wei": str(balance_wei),
                "balance": balance,
                "sufficient_for_burn": balance >= tokenomics.CLAWNCH_BURN_AMOUNT,
                "burn_amount_required": tokenomics.CLAWNCH_BURN_AMOUNT,
            }
        except Exception as e:
            return {"error": str(e)}

    def check_tx(self, tx_hash: str) -> Dict:
        """Check the status of a previously sent transaction.

        Use this to verify a tx after a timeout or to confirm a burn.
        """
        if not self.is_available:
            return {"error": "Web3 not connected"}
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            if tx is None:
                return {"status": "not_found", "tx_hash": tx_hash,
                        "message": "Transaction not found on-chain. It was never broadcast or was dropped."}

            # Transaction exists — check for receipt
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt is None:
                    return {"status": "pending", "tx_hash": tx_hash,
                            "message": "Transaction found but not yet confirmed (pending)."}
                return {
                    "status": "confirmed" if receipt.status == 1 else "reverted",
                    "tx_hash": tx_hash,
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "explorer_url": f"https://basescan.org/tx/{tx_hash}",
                }
            except Exception:
                return {"status": "pending", "tx_hash": tx_hash,
                        "message": "Transaction exists but receipt not available yet."}
        except Exception as e:
            return {"error": str(e), "tx_hash": tx_hash}

    def execute_burn(self) -> Dict:
        """Burn $CLAWNCH tokens by transferring to dead address.

        Sends tokenomics.CLAWNCH_BURN_AMOUNT tokens to 0x...dEaD.
        Returns the transaction hash on success.
        On timeout, still returns the tx_hash so it can be checked later.
        """
        if not self.is_available:
            return {"error": "Web3 not connected"}
        if not self.account:
            return {"error": "Wallet private key not configured"}

        burn_amount = tokenomics.CLAWNCH_BURN_AMOUNT
        burn_amount_wei = burn_amount * 10**18

        # Verify balance first
        balance_info = self.get_clawnch_balance()
        if "error" in balance_info:
            return balance_info
        if not balance_info.get("sufficient_for_burn"):
            return {
                "error": f"Insufficient $CLAWNCH. Have {balance_info['balance']}, need {burn_amount}",
            }

        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.CLAWNCH_TOKEN),
                abi=self._ERC20_ABI,
            )

            # Use 'pending' nonce to handle any stuck txs
            nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")

            tx = contract.functions.transfer(
                Web3.to_checksum_address(self.BURN_ADDRESS),
                burn_amount_wei,
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": 8453,  # Base mainnet
            })

            # Estimate gas with buffer
            gas_estimate = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.3)

            logger.info(f"Burn tx: nonce={nonce}, gas={tx['gas']}, "
                        f"gasPrice={tx['gasPrice']}, amount={burn_amount}")

            # Sign and send
            private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = "0x" + tx_hash.hex() if not tx_hash.hex().startswith("0x") else tx_hash.hex()

            logger.info(f"Burn tx broadcast: {tx_hash_hex}")

            # Wait for receipt with retry
            receipt = None
            for attempt in range(3):
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(
                        tx_hash, timeout=30
                    )
                    break
                except Exception as wait_err:
                    logger.warning(f"Receipt wait attempt {attempt + 1}/3 failed: {wait_err}")
                    if attempt < 2:
                        time.sleep(5)

            if receipt is None:
                # Tx was broadcast but we can't confirm — return hash for manual check
                logger.warning(f"Burn tx broadcast but receipt not confirmed: {tx_hash_hex}")
                return {
                    "status": "broadcast_unconfirmed",
                    "tx_hash": tx_hash_hex,
                    "message": (
                        "Transaction was broadcast but receipt could not be confirmed. "
                        "Check basescan or use clawnch_check_tx to verify. "
                        "DO NOT retry burn without checking first — tokens may already be burned."
                    ),
                    "explorer_url": f"https://basescan.org/tx/{tx_hash_hex}",
                }

            if receipt.status == 1:
                logger.info(f"Burn confirmed in block {receipt.blockNumber}: "
                            f"{burn_amount} $CLAWNCH burned")
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount_burned": burn_amount,
                    "block": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "explorer_url": f"https://basescan.org/tx/{tx_hash_hex}",
                }
            else:
                return {"error": "Burn transaction reverted", "tx_hash": tx_hash_hex}

        except Exception as e:
            logger.error(f"Burn failed: {e}")
            return {"error": str(e)}

    def upload_image(self) -> Dict:
        """Upload token image to Clawnch hosting (iili.io).

        Uses the raw GitHub URL from tokenomics config.
        Returns the hosted image URL.
        """
        try:
            resp = requests.post(
                f"{self.CLAWNCH_API_BASE}/upload",
                json={"image": tokenomics.IMAGE_URL},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            data = resp.json()
            if data.get("success"):
                hosted_url = data["url"]
                logger.info(f"Image uploaded: {hosted_url}")
                return {"success": True, "image_url": hosted_url}
            else:
                return {"error": f"Upload failed: {data}"}
        except Exception as e:
            return {"error": str(e)}

    def validate_launch(self, image_url: str, burn_tx_hash: str = "") -> Dict:
        """Validate launch content via Clawnch preview API.

        Args:
            image_url: Hosted image URL (from upload_image)
            burn_tx_hash: Transaction hash of the $CLAWNCH burn
        """
        payload = {
            "name": tokenomics.NAME,
            "symbol": tokenomics.SYMBOL,
            "wallet": self.wallet_address,
            "description": tokenomics.DESCRIPTION,
            "image": image_url,
            "website": tokenomics.WEBSITE,
            "twitter": tokenomics.TWITTER,
        }
        if burn_tx_hash:
            payload["burnTxHash"] = burn_tx_hash

        try:
            resp = requests.post(
                f"{self.CLAWNCH_API_BASE}/preview",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            data = resp.json()
            logger.info(f"Validation result: {data}")
            return {"status_code": resp.status_code, "response": data}
        except Exception as e:
            return {"error": str(e)}

    def build_launch_post(self, image_url: str, burn_tx_hash: str = "") -> str:
        """Build the !clawnch post content for Moltbook.

        Args:
            image_url: Hosted image URL (from upload_image)
            burn_tx_hash: Transaction hash of the $CLAWNCH burn

        Returns:
            Formatted !clawnch post content string.
        """
        lines = [
            "!clawnch",
            f"name: {tokenomics.NAME}",
            f"symbol: {tokenomics.SYMBOL}",
            f"wallet: {self.wallet_address}",
            f"description: {tokenomics.DESCRIPTION}",
            f"image: {image_url}",
            f"website: {tokenomics.WEBSITE}",
            f"twitter: {tokenomics.TWITTER}",
        ]
        if burn_tx_hash:
            lines.append(f"burnTxHash: {burn_tx_hash}")
        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Get overall Clawnch integration status."""
        return {
            "web3_available": _web3_available,
            "connected": self._connected,
            "wallet": self.wallet_address or "not configured",
            "clawnch_contract": self.clawnch_contract or "not configured",
            "token_deployed": bool(os.getenv("REPUBLIC_TOKEN_ADDRESS")),
        }
