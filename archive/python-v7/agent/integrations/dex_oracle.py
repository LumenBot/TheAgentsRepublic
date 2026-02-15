"""
DEX Price Oracle — DexScreener + GeckoTerminal
================================================
Free, no-auth APIs for token prices and pool discovery on Base L2.
Replaces direct Uniswap V3 Quoter calls which fail when pools don't exist.

v6.3.1: DexScreener for prices, GeckoTerminal for discovery.
"""

import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("TheConstituent.DexOracle")

DEXSCREENER_BASE = "https://api.dexscreener.com"
GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"

# Rate limiting
_last_request_time: float = 0
_MIN_INTERVAL = 0.5  # 500ms between requests


def _throttle():
    """Simple rate limiter."""
    global _last_request_time
    now = time.time()
    wait = _MIN_INTERVAL - (now - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


# =================================================================
# DexScreener API (free, no auth)
# =================================================================

def dexscreener_token_pairs(token_address: str) -> List[Dict]:
    """
    Get all DEX pairs for a token on Base via DexScreener.

    Returns list of pairs with price, volume, liquidity info.
    """
    _throttle()
    try:
        url = f"{DEXSCREENER_BASE}/token-pairs/v1/base/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"DexScreener {resp.status_code}: {resp.text[:200]}")
            return []

        data = resp.json()
        # API returns list directly or dict with "pairs" key
        pairs = data if isinstance(data, list) else data.get("pairs", [])
        return pairs

    except Exception as e:
        logger.error(f"DexScreener error: {e}")
        return []


def dexscreener_search(query: str) -> List[Dict]:
    """Search for tokens/pairs on DexScreener."""
    _throttle()
    try:
        url = f"{DEXSCREENER_BASE}/latest/dex/search"
        resp = requests.get(url, params={"q": query}, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("pairs", [])
    except Exception as e:
        logger.error(f"DexScreener search error: {e}")
        return []


def get_token_price(token_address: str) -> Dict:
    """
    Get token price in USD via multi-source fallback chain:
    1. DexScreener (standard DEX pools)
    2. GeckoTerminal (broader indexing)
    3. Odos pricing API (routes across ALL DEXes)
    4. Clawnch API (bonding curve tokens)

    Returns:
        {"price_usd": float, "price_native": float, "liquidity_usd": float,
         "volume_24h": float, "price_change_24h": float, "dex": str, "pair": str}
    """
    pairs = dexscreener_token_pairs(token_address)
    if not pairs:
        # Fallback 1: GeckoTerminal
        gt = geckoterminal_token_price(token_address)
        if gt.get("price_usd", 0) > 0:
            return gt

        # Fallback 2: Odos pricing (routes across ALL DEXes including bonding curves)
        odos = odos_token_price(token_address)
        if odos.get("price_usd", 0) > 0:
            return odos

        # Fallback 3: Clawnch API (native bonding curve tokens)
        clawnch = clawnch_token_price(token_address)
        if clawnch.get("price_usd", 0) > 0:
            return clawnch

        return {"price_usd": 0, "error": "No price data from any source"}

    # Pick the pair with highest liquidity
    best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

    price_usd = float(best.get("priceUsd", 0) or 0)
    price_native = float(best.get("priceNative", 0) or 0)
    liquidity = float(best.get("liquidity", {}).get("usd", 0) or 0)
    volume_24h = float(best.get("volume", {}).get("h24", 0) or 0)
    price_change_24h = float(best.get("priceChange", {}).get("h24", 0) or 0)
    fdv = float(best.get("fdv", 0) or 0)
    market_cap = float(best.get("marketCap", 0) or 0)

    base_token = best.get("baseToken", {})
    quote_token = best.get("quoteToken", {})
    dex = best.get("dexId", "unknown")
    pair_address = best.get("pairAddress", "")

    txns = best.get("txns", {})
    buys_24h = txns.get("h24", {}).get("buys", 0) if isinstance(txns.get("h24"), dict) else 0
    sells_24h = txns.get("h24", {}).get("sells", 0) if isinstance(txns.get("h24"), dict) else 0

    return {
        "price_usd": price_usd,
        "price_native": price_native,
        "liquidity_usd": liquidity,
        "volume_24h": volume_24h,
        "price_change_24h": price_change_24h,
        "fdv": fdv,
        "market_cap": market_cap,
        "dex": dex,
        "pair_address": pair_address,
        "base_token": base_token.get("symbol", "?"),
        "quote_token": quote_token.get("symbol", "?"),
        "buys_24h": buys_24h,
        "sells_24h": sells_24h,
        "total_pairs": len(pairs),
    }


# =================================================================
# GeckoTerminal API (free, no auth, 30 req/min)
# =================================================================

def geckoterminal_token_price(token_address: str) -> Dict:
    """Get token price from GeckoTerminal."""
    _throttle()
    try:
        url = f"{GECKOTERMINAL_BASE}/simple/networks/base/token_price/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"GeckoTerminal {resp.status_code}"}

        data = resp.json()
        prices = data.get("data", {}).get("attributes", {}).get("token_prices", {})
        price = float(prices.get(token_address.lower(), 0) or 0)
        return {"price_usd": price, "source": "geckoterminal"}

    except Exception as e:
        return {"error": str(e)}


def _extract_token_address_from_pool(pool: Dict) -> str:
    """
    Extract the actual base token address from a GeckoTerminal pool object.

    GeckoTerminal includes token addresses in relationships.base_token.data.id
    in format "base_0x1234..." — parse that to get the token address.
    Falls back to pool address if relationship data is missing.
    """
    try:
        rel = pool.get("relationships", {})
        base_id = rel.get("base_token", {}).get("data", {}).get("id", "")
        # Format: "base_0x1234abcd..." → extract the address part
        if "_0x" in base_id:
            return base_id.split("_", 1)[1]
    except Exception:
        pass
    # Fallback to pool address
    return pool.get("attributes", {}).get("address", "")


def geckoterminal_trending_pools(page: int = 1) -> List[Dict]:
    """Get trending pools on Base from GeckoTerminal."""
    _throttle()
    try:
        url = f"{GECKOTERMINAL_BASE}/networks/base/trending_pools"
        resp = requests.get(url, params={"page": page, "include": "base_token"}, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        pools = data.get("data", [])
        results = []
        for pool in pools:
            attrs = pool.get("attributes", {})
            token_address = _extract_token_address_from_pool(pool)
            results.append({
                "pool_address": attrs.get("address", ""),
                "token_address": token_address,
                "name": attrs.get("name", ""),
                "base_token": attrs.get("base_token_price_usd", ""),
                "quote_token": attrs.get("quote_token_price_usd", ""),
                "price_usd": float(attrs.get("base_token_price_usd", 0) or 0),
                "volume_24h": float(attrs.get("volume_usd", {}).get("h24", 0) or 0),
                "price_change_24h": float(attrs.get("price_change_percentage", {}).get("h24", 0) or 0),
                "reserve_usd": float(attrs.get("reserve_in_usd", 0) or 0),
                "pool_created_at": attrs.get("pool_created_at", ""),
                "fdv_usd": float(attrs.get("fdv_usd", 0) or 0),
                "transactions_24h": attrs.get("transactions", {}).get("h24", {}),
            })
        return results

    except Exception as e:
        logger.error(f"GeckoTerminal trending error: {e}")
        return []


def geckoterminal_new_pools(page: int = 1) -> List[Dict]:
    """Get newly created pools on Base from GeckoTerminal."""
    _throttle()
    try:
        url = f"{GECKOTERMINAL_BASE}/networks/base/new_pools"
        resp = requests.get(url, params={"page": page, "include": "base_token"}, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        pools = data.get("data", [])
        results = []
        for pool in pools:
            attrs = pool.get("attributes", {})
            token_address = _extract_token_address_from_pool(pool)
            results.append({
                "pool_address": attrs.get("address", ""),
                "token_address": token_address,
                "name": attrs.get("name", ""),
                "price_usd": float(attrs.get("base_token_price_usd", 0) or 0),
                "volume_24h": float(attrs.get("volume_usd", {}).get("h24", 0) or 0),
                "price_change_24h": float(attrs.get("price_change_percentage", {}).get("h24", 0) or 0),
                "reserve_usd": float(attrs.get("reserve_in_usd", 0) or 0),
                "pool_created_at": attrs.get("pool_created_at", ""),
                "fdv_usd": float(attrs.get("fdv_usd", 0) or 0),
            })
        return results

    except Exception as e:
        logger.error(f"GeckoTerminal new pools error: {e}")
        return []


def geckoterminal_token_info(token_address: str) -> Dict:
    """Get detailed token info from GeckoTerminal."""
    _throttle()
    try:
        url = f"{GECKOTERMINAL_BASE}/networks/base/tokens/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"GeckoTerminal {resp.status_code}"}

        data = resp.json()
        attrs = data.get("data", {}).get("attributes", {})
        return {
            "name": attrs.get("name", ""),
            "symbol": attrs.get("symbol", ""),
            "address": attrs.get("address", ""),
            "decimals": attrs.get("decimals"),
            "total_supply": attrs.get("total_supply", ""),
            "price_usd": float(attrs.get("price_usd", 0) or 0),
            "fdv_usd": float(attrs.get("fdv_usd", 0) or 0),
            "market_cap_usd": float(attrs.get("market_cap_usd", 0) or 0),
            "volume_24h": float(attrs.get("volume_usd", {}).get("h24", 0) or 0),
            "price_change_24h": float(attrs.get("price_change_percentage", {}).get("h24", 0) or 0),
            "total_reserve_usd": float(attrs.get("total_reserve_in_usd", 0) or 0),
        }

    except Exception as e:
        return {"error": str(e)}


# =================================================================
# Odos Swap API (free, no auth) — for actual trade execution
# =================================================================

ODOS_BASE = "https://api.odos.xyz"
ODOS_ROUTER_V2 = "0x19cEeAd7105607Cd444F5ad10dd51356436095a1"


def odos_quote(
    token_in: str,
    token_out: str,
    amount_in_raw: int,
    user_address: str,
    slippage_pct: float = 3.0,
) -> Dict:
    """
    Get a swap quote from Odos (routes across ALL Base DEXes).

    Args:
        token_in: Input token address
        token_out: Output token address
        amount_in_raw: Amount in raw units (with decimals)
        user_address: Wallet address for the swap
        slippage_pct: Slippage tolerance in percent

    Returns:
        {"path_id": str, "amount_out": int, "price_impact": float, ...}
    """
    _throttle()
    try:
        url = f"{ODOS_BASE}/sor/quote/v2"
        payload = {
            "chainId": 8453,
            "inputTokens": [
                {"tokenAddress": token_in, "amount": str(amount_in_raw)}
            ],
            "outputTokens": [
                {"tokenAddress": token_out, "proportion": 1}
            ],
            "userAddr": user_address,
            "slippageLimitPercent": slippage_pct,
            "referralCode": 0,
            "disableRFQs": True,
            "compact": True,
        }

        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            return {"error": f"Odos quote {resp.status_code}: {resp.text[:300]}"}

        data = resp.json()
        return {
            "path_id": data.get("pathId", ""),
            "amount_out": int(data.get("outAmounts", [0])[0]),
            "price_impact": float(data.get("priceImpact", 0) or 0),
            "gas_estimate": data.get("gasEstimate", 0),
            "data_gas_estimate": data.get("dataGasEstimate", 0),
            "net_out_value": float(data.get("netOutValue", 0) or 0),
        }

    except Exception as e:
        return {"error": str(e)}


def odos_assemble(path_id: str, user_address: str) -> Dict:
    """
    Assemble the swap transaction from an Odos quote.

    Returns the raw transaction data to sign and send.
    """
    _throttle()
    try:
        url = f"{ODOS_BASE}/sor/assemble"
        payload = {
            "userAddr": user_address,
            "pathId": path_id,
        }

        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            return {"error": f"Odos assemble {resp.status_code}: {resp.text[:300]}"}

        data = resp.json()
        tx = data.get("transaction", {})
        return {
            "to": tx.get("to", ""),
            "data": tx.get("data", ""),
            "value": int(tx.get("value", 0)),
            "gas_limit": int(tx.get("gas", 0) or tx.get("gasLimit", 250000)),
        }

    except Exception as e:
        return {"error": str(e)}


def odos_token_price(token_address: str) -> Dict:
    """Get token price from Odos pricing API."""
    _throttle()
    try:
        url = f"{ODOS_BASE}/pricing/token/8453/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"Odos price {resp.status_code}"}
        data = resp.json()
        return {"price_usd": float(data.get("price", 0) or 0), "source": "odos"}
    except Exception as e:
        return {"error": str(e)}


# =================================================================
# Clawnch API — bonding curve tokens (not yet on standard DEXes)
# =================================================================

CLAWNCH_API = "https://clawn.ch/api"


def clawnch_token_price(token_address: str) -> Dict:
    """
    Get token price from Clawnch bonding curve API.

    Tokens launched on Clawnch may not be indexed by DexScreener/GeckoTerminal
    until they graduate to a standard DEX pool.
    """
    _throttle()
    try:
        url = f"{CLAWNCH_API}/tokens/{token_address}"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return {"error": f"Clawnch API {resp.status_code}"}

        data = resp.json()
        # Clawnch API may return data in different formats
        price_usd = float(data.get("priceUsd", 0) or data.get("price_usd", 0) or
                         data.get("price", 0) or 0)
        market_cap = float(data.get("marketCap", 0) or data.get("market_cap", 0) or 0)
        liquidity = float(data.get("liquidity", 0) or data.get("tvl", 0) or 0)
        volume = float(data.get("volume24h", 0) or data.get("volume_24h", 0) or 0)

        return {
            "price_usd": price_usd,
            "market_cap": market_cap,
            "liquidity_usd": liquidity,
            "volume_24h": volume,
            "source": "clawnch",
            "name": data.get("name", ""),
            "symbol": data.get("symbol", ""),
        }

    except Exception as e:
        return {"error": str(e)}
