"""
Clawnch Scout — Token Launch Monitor & Opportunity Finder
==========================================================
Monitors Base L2 ecosystem for trading opportunities:
1. GeckoTerminal trending/new pools (high-quality data)
2. DexScreener token discovery
3. Clawnch API for new launches
4. Moltbook feed for !clawnch posts

v6.3.1: Multi-source scanning with real metrics (volume, liquidity, price change).
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

from ..config.trading import trading_config

logger = logging.getLogger("TheConstituent.ClawnchScout")


class ClawnchScout:
    """
    Multi-source token opportunity scanner for Base L2.

    Scoring factors (v6.3.1 — based on real on-chain data):
    - Liquidity (0-25): Higher TVL = safer to trade
    - Volume (0-25): Active trading = real interest
    - Price momentum (0-20): Rising price + healthy ratio
    - Freshness (0-15): New tokens with early traction
    - Social signals (0-15): Website, Moltbook activity, etc.
    """

    CLAWNCH_API = "https://clawn.ch/api"
    MOLTBOOK_API = "https://www.moltbook.com/api/v1"

    def __init__(self):
        self._cache: List[Dict] = []
        self._scored: Dict[str, Dict] = {}
        self._last_scan: float = 0
        self._load_cache()

    def _load_cache(self):
        path = Path(trading_config.SCOUT_CACHE_FILE)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._cache = data.get("tokens", [])
                self._scored = data.get("scored", {})
            except Exception as e:
                logger.error(f"Failed to load scout cache: {e}")

    def _save_cache(self):
        path = Path(trading_config.SCOUT_CACHE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "tokens": self._cache[-200:],
            "scored": {k: v for k, v in sorted(
                self._scored.items(), key=lambda x: x[1].get("score", 0), reverse=True
            )[:100]},
            "last_scan": self._last_scan,
        }, indent=2, default=str), encoding="utf-8")

    # =================================================================
    # Scanning — Multi-Source
    # =================================================================

    def scan_new_launches(self) -> List[Dict]:
        """
        Scan multiple sources for trading opportunities on Base L2.

        Sources (in order of data quality):
        1. GeckoTerminal trending pools
        2. GeckoTerminal new pools
        3. DexScreener search for Base tokens
        4. Clawnch API
        """
        all_tokens = []

        # Source 1: GeckoTerminal trending pools on Base (best data)
        try:
            trending = self._scan_geckoterminal_trending()
            all_tokens.extend(trending)
            logger.info(f"GeckoTerminal trending: {len(trending)} pools")
        except Exception as e:
            logger.warning(f"GeckoTerminal trending scan failed: {e}")

        # Source 2: GeckoTerminal new pools (fresh launches)
        try:
            new_pools = self._scan_geckoterminal_new()
            all_tokens.extend(new_pools)
            logger.info(f"GeckoTerminal new: {len(new_pools)} pools")
        except Exception as e:
            logger.warning(f"GeckoTerminal new scan failed: {e}")

        # Source 3: DexScreener search for hot Base tokens
        try:
            dex_tokens = self._scan_dexscreener()
            all_tokens.extend(dex_tokens)
            logger.info(f"DexScreener: {len(dex_tokens)} tokens")
        except Exception as e:
            logger.warning(f"DexScreener scan failed: {e}")

        # Source 4: Clawnch API (limited data but native to our ecosystem)
        try:
            clawnch = self._scan_clawnch_api()
            all_tokens.extend(clawnch)
        except Exception as e:
            logger.debug(f"Clawnch API scan: {e}")

        # Deduplicate by token address, keeping highest-data entry
        seen_addrs = set()
        seen_names = set()
        unique = []
        for token in all_tokens:
            addr = token.get("token_address", "").lower()
            name_key = token.get("symbol", "").lower() or token.get("name", "").lower()

            # Skip if we've seen this exact address
            if addr and addr in seen_addrs:
                continue
            # Skip if same symbol from different pool (dedup by name for GT pools)
            if name_key and name_key in seen_names:
                continue

            if addr:
                seen_addrs.add(addr)
            if name_key:
                seen_names.add(name_key)
            unique.append(token)

        # Filter: skip our own tokens and major stablecoins
        # Check both token_address and pool_address against skip list
        skip = {
            trading_config.REPUBLIC_TOKEN.lower(),
            trading_config.CLAWNCH_TOKEN.lower(),
            trading_config.WETH.lower(),
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC on Base
            "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",  # DAI on Base
        }
        skip_names = {"weth", "usdc", "dai", "clawnch", "republic"}
        unique = [
            t for t in unique
            if t.get("token_address", "").lower() not in skip
            and t.get("pool_address", "").lower() not in skip
            and t.get("symbol", "").lower() not in skip_names
        ]

        # Score each token
        scored = []
        for token in unique:
            score = self._score_token(token)
            token["score"] = score
            scored.append(token)
            self._scored[token.get("token_address", "")] = token

        scored.sort(key=lambda t: t.get("score", 0), reverse=True)

        self._cache = scored[:200]
        self._last_scan = time.time()
        self._save_cache()

        logger.info(f"Scout scan complete: {len(scored)} tokens, "
                     f"top score: {scored[0]['score'] if scored else 0}")

        return scored

    def _scan_geckoterminal_trending(self) -> List[Dict]:
        """Get trending pools on Base from GeckoTerminal."""
        from .dex_oracle import geckoterminal_trending_pools
        pools = geckoterminal_trending_pools()
        tokens = []
        for pool in pools:
            name = pool.get("name", "")
            # Parse "TOKEN / WETH" style names
            parts = name.split(" / ") if " / " in name else name.split("/")
            token_name = parts[0].strip() if parts else name
            # Use actual token address (extracted from relationships), fallback to pool address
            token_addr = pool.get("token_address", "") or pool.get("pool_address", "")

            tokens.append({
                "token_address": token_addr,
                "pool_address": pool.get("pool_address", ""),
                "name": token_name,
                "symbol": token_name,
                "source": "geckoterminal_trending",
                "price_usd": pool.get("price_usd", 0),
                "volume_24h": pool.get("volume_24h", 0),
                "price_change_24h": pool.get("price_change_24h", 0),
                "liquidity_usd": pool.get("reserve_usd", 0),
                "fdv_usd": pool.get("fdv_usd", 0),
                "pool_created_at": pool.get("pool_created_at", ""),
                "transactions_24h": pool.get("transactions_24h", {}),
            })
        return tokens

    def _scan_geckoterminal_new(self) -> List[Dict]:
        """Get newly created pools on Base from GeckoTerminal."""
        from .dex_oracle import geckoterminal_new_pools
        pools = geckoterminal_new_pools()
        tokens = []
        for pool in pools:
            name = pool.get("name", "")
            parts = name.split(" / ") if " / " in name else name.split("/")
            token_name = parts[0].strip() if parts else name
            # Use actual token address (extracted from relationships), fallback to pool address
            token_addr = pool.get("token_address", "") or pool.get("pool_address", "")

            tokens.append({
                "token_address": token_addr,
                "pool_address": pool.get("pool_address", ""),
                "name": token_name,
                "symbol": token_name,
                "source": "geckoterminal_new",
                "price_usd": pool.get("price_usd", 0),
                "volume_24h": pool.get("volume_24h", 0),
                "price_change_24h": pool.get("price_change_24h", 0),
                "liquidity_usd": pool.get("reserve_usd", 0),
                "fdv_usd": pool.get("fdv_usd", 0),
                "pool_created_at": pool.get("pool_created_at", ""),
            })
        return tokens

    def _scan_dexscreener(self) -> List[Dict]:
        """Search DexScreener for active Base tokens."""
        from .dex_oracle import dexscreener_search
        tokens = []
        queries = ["base new token", "base agent", "clawnch"]
        for q in queries:
            pairs = dexscreener_search(q)
            for pair in pairs[:20]:
                if pair.get("chainId") != "base":
                    continue
                base_token = pair.get("baseToken", {})
                tokens.append({
                    "token_address": base_token.get("address", ""),
                    "name": base_token.get("name", ""),
                    "symbol": base_token.get("symbol", ""),
                    "source": "dexscreener",
                    "price_usd": float(pair.get("priceUsd", 0) or 0),
                    "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
                    "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                    "fdv_usd": float(pair.get("fdv", 0) or 0),
                    "dex": pair.get("dexId", ""),
                    "pair_address": pair.get("pairAddress", ""),
                })
            time.sleep(0.5)  # Rate limiting
        return tokens

    def _scan_clawnch_api(self) -> List[Dict]:
        """Check Clawnch API for recent launches."""
        tokens = []
        try:
            resp = requests.get(
                f"{self.CLAWNCH_API}/tokens",
                params={"sort": "recent", "limit": 20},
                timeout=15,
            )
            if resp.status_code != 200:
                return tokens

            data = resp.json()
            items = data if isinstance(data, list) else data.get("tokens", [])
            for token in items[:20]:
                addr = token.get("address", token.get("tokenAddress", ""))
                if not addr:
                    continue
                tokens.append({
                    "token_address": addr,
                    "name": token.get("name", ""),
                    "symbol": token.get("symbol", ""),
                    "source": "clawnch",
                    "burn_amount": token.get("burnAmount", 0),
                    "created_at": token.get("createdAt", ""),
                    "market_cap": float(token.get("marketCap", 0) or 0),
                    "holders": int(token.get("holders", 0) or 0),
                })
        except Exception as e:
            logger.debug(f"Clawnch API: {e}")
        return tokens

    # =================================================================
    # Scoring (v6.3.1 — based on real on-chain metrics)
    # =================================================================

    def _score_token(self, token: Dict) -> float:
        """
        Score a token opportunity (0-100) using real metrics.

        Factors:
        - Liquidity (0-25): Higher TVL = safer to trade
        - Volume (0-25): Active trading = real interest
        - Price momentum (0-20): Rising price with healthy volume
        - Freshness (0-15): New pools with early traction
        - Social/metadata (0-15): Source quality, name, etc.
        """
        score = 0.0

        # === Liquidity (0-25) ===
        liq = float(token.get("liquidity_usd", 0) or 0)
        if liq >= 100_000:
            score += 25
        elif liq >= 50_000:
            score += 20
        elif liq >= 10_000:
            score += 15
        elif liq >= 5_000:
            score += 10
        elif liq >= 1_000:
            score += 5

        # === Volume (0-25) ===
        vol = float(token.get("volume_24h", 0) or 0)
        if vol >= 500_000:
            score += 25
        elif vol >= 100_000:
            score += 20
        elif vol >= 50_000:
            score += 15
        elif vol >= 10_000:
            score += 10
        elif vol >= 1_000:
            score += 5

        # === Price momentum (0-20) ===
        change = float(token.get("price_change_24h", 0) or 0)
        if 10 <= change <= 100:
            score += 20  # Healthy growth (not pump-and-dump)
        elif 5 <= change <= 200:
            score += 15
        elif 0 < change < 500:
            score += 10
        elif change > 500:
            score += 5  # Probably a pump, risky
        # Negative change = no momentum points

        # === Freshness (0-15) ===
        created = token.get("pool_created_at") or token.get("created_at", "")
        if created:
            try:
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt = datetime.strptime(created, fmt)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
                else:
                    dt = None

                if dt:
                    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    if age_hours < 2:
                        score += 15
                    elif age_hours < 6:
                        score += 12
                    elif age_hours < 24:
                        score += 8
                    elif age_hours < 72:
                        score += 4
            except Exception:
                pass

        # === Source quality / metadata (0-15) ===
        source = token.get("source", "")
        if source == "geckoterminal_trending":
            score += 10  # Already curated as trending
        elif source == "geckoterminal_new":
            score += 5
        elif source == "dexscreener":
            score += 5
        elif source == "clawnch":
            score += 3  # Native ecosystem

        # Bonus for having a name and symbol
        if token.get("name") and token.get("symbol"):
            score += 3

        # Bonus for FDV in sweet spot ($100K - $10M)
        fdv = float(token.get("fdv_usd", 0) or 0)
        if 100_000 <= fdv <= 10_000_000:
            score += 2

        return round(min(100, score), 1)

    # =================================================================
    # Opportunity Filtering
    # =================================================================

    def get_opportunities(self, min_score: float = 40.0) -> List[Dict]:
        """Get tokens that meet minimum score threshold."""
        if time.time() - self._last_scan > trading_config.SCOUT_INTERVAL:
            self.scan_new_launches()

        opportunities = [
            t for t in self._scored.values()
            if t.get("score", 0) >= min_score
        ]
        opportunities.sort(key=lambda t: t.get("score", 0), reverse=True)
        return opportunities

    def get_top_picks(self, n: int = 3) -> List[Dict]:
        """Get top N highest-scored tokens."""
        opps = self.get_opportunities(min_score=30.0)
        return opps[:n]

    def get_scout_report(self) -> str:
        """Generate human-readable scout report."""
        opps = self.get_opportunities(min_score=20.0)
        all_tokens = list(self._scored.values())
        all_tokens.sort(key=lambda t: t.get("score", 0), reverse=True)

        last = (datetime.fromtimestamp(self._last_scan, tz=timezone.utc).strftime("%H:%M UTC")
                if self._last_scan else "never")

        lines = [
            "Clawnch Scout Report",
            "=" * 40,
            f"Tokens scanned: {len(all_tokens)}",
            f"Opportunities (score >= 20): {len(opps)}",
            f"Last scan: {last}",
            "",
        ]

        display = all_tokens[:10]
        if not display:
            lines.append("No tokens found. Check API connectivity.")
            return "\n".join(lines)

        for i, token in enumerate(display, 1):
            name = token.get("name", "?")[:20]
            symbol = token.get("symbol", "?")[:10]
            score = token.get("score", 0)
            vol = token.get("volume_24h", 0)
            liq = token.get("liquidity_usd", 0)
            change = token.get("price_change_24h", 0)
            source = token.get("source", "?")

            indicator = "🔥" if score >= 60 else "⚡" if score >= 40 else "📊"
            lines.append(f"{indicator} #{i} {name} (${symbol}) — Score: {score}/100")
            lines.append(f"   Vol: ${vol:,.0f} | Liq: ${liq:,.0f} | 24h: {change:+.1f}%")
            lines.append(f"   Source: {source}")
            addr = token.get("token_address", "")
            if addr:
                lines.append(f"   {addr[:20]}...")
            lines.append("")

        return "\n".join(lines)

    def get_status(self) -> Dict:
        return {
            "tokens_tracked": len(self._cache),
            "scored_tokens": len(self._scored),
            "last_scan": self._last_scan,
            "opportunities": len(self.get_opportunities()),
        }
