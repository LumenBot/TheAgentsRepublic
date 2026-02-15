"""
BaseScan Integration — $REPUBLIC Token Tracker
================================================
Fetches on-chain data about the $REPUBLIC token from BaseScan API.
Provides holder counts, transfer activity, and token info.
"""

import os
import logging
import time
from typing import Dict, Optional

import requests

from ..config.tokenomics import tokenomics

logger = logging.getLogger("TheConstituent.Integration.BaseScan")

BASESCAN_API_URL = "https://api.basescan.org/api"
BASESCAN_TIMEOUT = 10
# Public rate limit: 5 calls/sec without API key
_last_call_time = 0.0


class BaseScanTracker:
    """Track $REPUBLIC token on-chain activity via BaseScan API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("BASESCAN_API_KEY", "")
        self.token_address = tokenomics.TOKEN_ADDRESS
        self.chain_id = tokenomics.CHAIN_ID

    def _request(self, **params) -> Dict:
        """Make a BaseScan API request with rate limiting."""
        global _last_call_time
        # Rate limit: max 5/sec (be conservative — 1/sec)
        elapsed = time.time() - _last_call_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_call_time = time.time()

        if self.api_key:
            params["apikey"] = self.api_key

        try:
            resp = requests.get(
                BASESCAN_API_URL,
                params=params,
                timeout=BASESCAN_TIMEOUT,
            )
            data = resp.json()
            if data.get("status") == "1" or data.get("message") == "OK":
                return data
            return {"error": data.get("message", data.get("result", "Unknown error"))}
        except requests.exceptions.Timeout:
            return {"error": "BaseScan API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def get_token_info(self) -> Dict:
        """Get basic token info (supply, name, decimals)."""
        result = self._request(
            module="token",
            action="tokeninfo",
            contractaddress=self.token_address,
        )
        if "error" in result:
            # Fallback: use tokenomics config
            return {
                "name": tokenomics.NAME,
                "symbol": tokenomics.SYMBOL,
                "decimals": tokenomics.DECIMALS,
                "totalSupply": str(tokenomics.TOTAL_SUPPLY),
                "address": self.token_address,
                "source": "config_fallback",
            }
        return result.get("result", [{}])[0] if isinstance(result.get("result"), list) else result.get("result", {})

    def get_token_supply(self) -> Dict:
        """Get circulating supply."""
        result = self._request(
            module="stats",
            action="tokensupply",
            contractaddress=self.token_address,
        )
        if "error" in result:
            return {"error": result["error"]}
        raw = int(result.get("result", 0))
        supply = raw / (10 ** tokenomics.DECIMALS)
        return {"total_supply_raw": raw, "total_supply": supply}

    def get_token_holders(self) -> Dict:
        """Get holder count (requires BaseScan Pro API key)."""
        # BaseScan doesn't have a direct holder count endpoint on free tier
        # We use token transfer events to estimate
        result = self._request(
            module="token",
            action="tokenholdercount",
            contractaddress=self.token_address,
        )
        if "error" not in result and result.get("result"):
            return {"holder_count": int(result["result"])}
        # Fallback: estimate from recent transfers
        return {"holder_count": "unavailable (needs API key)", "note": "Upgrade to BaseScan Pro for holder count"}

    def get_recent_transfers(self, limit: int = 20) -> Dict:
        """Get recent ERC-20 token transfers."""
        result = self._request(
            module="account",
            action="tokentx",
            contractaddress=self.token_address,
            page=1,
            offset=limit,
            sort="desc",
        )
        if "error" in result:
            return {"error": result["error"], "transfers": []}

        transfers = result.get("result", [])
        if not isinstance(transfers, list):
            return {"error": "Unexpected response", "transfers": []}

        parsed = []
        for tx in transfers[:limit]:
            value_raw = int(tx.get("value", 0))
            value = value_raw / (10 ** tokenomics.DECIMALS)
            parsed.append({
                "hash": tx.get("hash", ""),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value": value,
                "timestamp": tx.get("timeStamp", ""),
                "block": tx.get("blockNumber", ""),
            })

        return {
            "count": len(parsed),
            "transfers": parsed,
        }

    def get_token_balance(self, address: str) -> Dict:
        """Get $REPUBLIC balance for a specific address."""
        result = self._request(
            module="account",
            action="tokenbalance",
            contractaddress=self.token_address,
            address=address,
            tag="latest",
        )
        if "error" in result:
            return {"error": result["error"]}
        raw = int(result.get("result", 0))
        balance = raw / (10 ** tokenomics.DECIMALS)
        return {"address": address, "balance_raw": raw, "balance": balance}

    def get_eth_balance(self, address: str) -> Dict:
        """Get ETH balance for gas tracking."""
        result = self._request(
            module="account",
            action="balance",
            address=address,
            tag="latest",
        )
        if "error" in result:
            return {"error": result["error"]}
        raw = int(result.get("result", 0))
        balance = raw / (10 ** 18)
        return {"address": address, "eth_balance": balance}

    def get_full_status(self) -> Dict:
        """Get comprehensive token status for briefings."""
        status = {
            "token": tokenomics.SYMBOL,
            "address": self.token_address,
            "chain": "Base",
            "explorer": tokenomics.EXPLORER_URL,
        }

        # Supply
        supply = self.get_token_supply()
        if "error" not in supply:
            status["total_supply"] = supply["total_supply"]

        # Holders
        holders = self.get_token_holders()
        status["holders"] = holders.get("holder_count", "unavailable")

        # Recent transfers
        transfers = self.get_recent_transfers(limit=5)
        status["recent_transfers"] = transfers.get("count", 0)
        if transfers.get("transfers"):
            status["last_transfer"] = transfers["transfers"][0]

        # Agent wallet balance
        wallet = os.environ.get("AGENT_WALLET_ADDRESS", "")
        if wallet:
            bal = self.get_token_balance(wallet)
            if "error" not in bal:
                status["agent_balance"] = bal["balance"]
            eth = self.get_eth_balance(wallet)
            if "error" not in eth:
                status["agent_eth"] = eth["eth_balance"]

        return status
