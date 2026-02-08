"""
Clawnch Scout — New Token Launch Monitor
==========================================
Monitors the Clawnch ecosystem for new token launches on Base L2.
Scores opportunities based on burn amount, social activity, and token metrics.

v6.3: Initial scout for DeFi trading opportunities.

Strategy:
1. Scan Moltbook feed for !clawnch posts (new launches)
2. Score each launch on multiple factors
3. Flag high-potential tokens for the trading engine
4. Track graduated tokens (bonding curve -> DEX)
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from ..config.trading import trading_config

logger = logging.getLogger("TheConstituent.ClawnchScout")


class ClawnchScout:
    """
    Monitors Clawnch for new token launches and scores opportunities.

    Scoring factors:
    - Burn amount (higher = more committed)
    - Agent social activity (posts, replies, engagement)
    - Token description quality
    - Time since launch (fresher = better)
    - Existing holder count (if available)
    """

    CLAWNCH_API = "https://clawn.ch/api"
    MOLTBOOK_API = "https://www.moltbook.com/api/v1"

    def __init__(self):
        self._cache: List[Dict] = []
        self._scored: Dict[str, Dict] = {}
        self._last_scan: float = 0
        self._load_cache()

    def _load_cache(self):
        """Load cached scout data from disk."""
        path = Path(trading_config.SCOUT_CACHE_FILE)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._cache = data.get("tokens", [])
                self._scored = data.get("scored", {})
            except Exception as e:
                logger.error(f"Failed to load scout cache: {e}")

    def _save_cache(self):
        """Save cache to disk."""
        path = Path(trading_config.SCOUT_CACHE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "tokens": self._cache[-100:],  # Keep last 100
            "scored": self._scored,
            "last_scan": self._last_scan,
        }, indent=2, default=str), encoding="utf-8")

    # =================================================================
    # Scanning
    # =================================================================

    def scan_new_launches(self) -> List[Dict]:
        """
        Scan for new token launches on Clawnch.

        Approaches:
        1. Check Moltbook feed for !clawnch posts
        2. Check Clawnch API for recent launches (if available)

        Returns list of new token launches found.
        """
        new_tokens = []

        # Approach 1: Moltbook feed scan
        try:
            moltbook_tokens = self._scan_moltbook()
            new_tokens.extend(moltbook_tokens)
        except Exception as e:
            logger.error(f"Moltbook scan failed: {e}")

        # Approach 2: Clawnch API (if endpoint exists)
        try:
            api_tokens = self._scan_clawnch_api()
            new_tokens.extend(api_tokens)
        except Exception as e:
            logger.debug(f"Clawnch API scan: {e}")

        # Deduplicate by token address
        seen = set()
        unique_tokens = []
        for token in new_tokens:
            addr = token.get("token_address", "").lower()
            if addr and addr not in seen:
                seen.add(addr)
                unique_tokens.append(token)

        # Score each token
        scored = []
        for token in unique_tokens:
            score = self._score_token(token)
            token["score"] = score
            scored.append(token)
            self._scored[token.get("token_address", "")] = token

        # Sort by score (highest first)
        scored.sort(key=lambda t: t.get("score", 0), reverse=True)

        self._cache.extend(scored)
        self._last_scan = time.time()
        self._save_cache()

        logger.info(f"Scout scan: {len(scored)} new tokens found, "
                     f"top score: {scored[0]['score'] if scored else 0}")

        return scored

    def _scan_moltbook(self) -> List[Dict]:
        """Scan Moltbook feed for !clawnch posts."""
        tokens = []

        try:
            resp = requests.get(
                f"{self.MOLTBOOK_API}/posts",
                params={"sort": "recent", "limit": 50},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                return tokens

            posts = resp.json() if isinstance(resp.json(), list) else resp.json().get("posts", [])

            for post in posts:
                content = post.get("content", "") or post.get("body", "")
                if "!clawnch" not in content.lower():
                    continue

                # Parse token info from !clawnch post
                token_info = self._parse_clawnch_post(content)
                if token_info:
                    token_info["source"] = "moltbook"
                    token_info["post_id"] = post.get("id", "")
                    token_info["author"] = post.get("author", {}).get("name", "")
                    token_info["post_time"] = post.get("createdAt", "")
                    token_info["likes"] = post.get("likes", 0)
                    token_info["comments"] = post.get("comments", 0)
                    tokens.append(token_info)

        except Exception as e:
            logger.error(f"Moltbook scan error: {e}")

        return tokens

    def _scan_clawnch_api(self) -> List[Dict]:
        """Try to get recent launches from Clawnch API."""
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
            for token in (data if isinstance(data, list) else data.get("tokens", [])):
                tokens.append({
                    "token_address": token.get("address", ""),
                    "name": token.get("name", ""),
                    "symbol": token.get("symbol", ""),
                    "burn_amount": token.get("burnAmount", 0),
                    "created_at": token.get("createdAt", ""),
                    "source": "clawnch_api",
                    "market_cap": token.get("marketCap", 0),
                    "holders": token.get("holders", 0),
                    "graduated": token.get("graduated", False),
                })
        except Exception as e:
            logger.debug(f"Clawnch API not available: {e}")

        return tokens

    def _parse_clawnch_post(self, content: str) -> Optional[Dict]:
        """Parse a !clawnch post to extract token metadata."""
        lines = content.strip().split("\n")
        data = {}

        for line in lines:
            line = line.strip()
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "name":
                data["name"] = value
            elif key == "symbol":
                data["symbol"] = value
            elif key == "wallet":
                data["wallet"] = value
            elif key == "description":
                data["description"] = value
            elif key == "burntxhash":
                data["burn_tx_hash"] = value
            elif key == "website":
                data["website"] = value
            elif key == "twitter":
                data["twitter"] = value
            elif key == "image":
                data["image"] = value

        if not data.get("name") or not data.get("symbol"):
            return None

        return data

    # =================================================================
    # Scoring
    # =================================================================

    def _score_token(self, token: Dict) -> float:
        """
        Score a token launch opportunity (0-100).

        Factors:
        - Burn amount (0-25 points): Higher burn = more commitment
        - Social activity (0-25 points): Posts, engagement, website
        - Freshness (0-20 points): Newer = better
        - Metadata quality (0-15 points): Description, image, website
        - Engagement (0-15 points): Likes, comments on launch post
        """
        score = 0.0

        # Burn amount (0-25)
        burn = token.get("burn_amount", 0)
        if isinstance(burn, str):
            try:
                burn = float(burn.replace(",", ""))
            except ValueError:
                burn = 0
        if burn >= 4_000_000:
            score += 25  # Max burn (same as $REPUBLIC)
        elif burn >= 2_000_000:
            score += 20
        elif burn >= 1_000_000:
            score += 15
        elif burn >= 500_000:
            score += 10
        elif burn >= 100_000:
            score += 5

        # Social activity (0-25)
        has_twitter = bool(token.get("twitter"))
        has_website = bool(token.get("website"))
        has_author = bool(token.get("author"))
        social = 0
        if has_twitter:
            social += 8
        if has_website:
            social += 8
        if has_author:
            social += 5
        # Agent with posts = more legitimate
        if token.get("comments", 0) > 0:
            social += min(4, token["comments"])
        score += min(25, social)

        # Freshness (0-20) - newer is better
        created = token.get("post_time") or token.get("created_at")
        if created:
            try:
                if isinstance(created, str):
                    # Handle various date formats
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
                        if age_hours < 1:
                            score += 20
                        elif age_hours < 4:
                            score += 15
                        elif age_hours < 12:
                            score += 10
                        elif age_hours < 24:
                            score += 5
            except Exception:
                pass

        # Metadata quality (0-15)
        desc = token.get("description", "")
        if len(desc) > 100:
            score += 8
        elif len(desc) > 30:
            score += 4
        if token.get("image"):
            score += 4
        if token.get("name") and token.get("symbol"):
            score += 3

        # Engagement on launch post (0-15)
        likes = token.get("likes", 0)
        comments = token.get("comments", 0)
        engagement = likes * 2 + comments * 3
        score += min(15, engagement)

        return round(score, 1)

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

        # Sort by score
        opportunities.sort(key=lambda t: t.get("score", 0), reverse=True)
        return opportunities

    def get_top_picks(self, n: int = 3) -> List[Dict]:
        """Get top N highest-scored tokens."""
        opps = self.get_opportunities(min_score=30.0)
        return opps[:n]

    def get_scout_report(self) -> str:
        """Generate human-readable scout report."""
        opps = self.get_opportunities(min_score=20.0)
        if not opps:
            return "Clawnch Scout: No opportunities found. Last scan: " + (
                datetime.fromtimestamp(self._last_scan, tz=timezone.utc).strftime("%H:%M UTC")
                if self._last_scan else "never"
            )

        lines = [
            f"Clawnch Scout Report",
            f"{'=' * 40}",
            f"Tokens scanned: {len(self._cache)}",
            f"Opportunities (score >= 20): {len(opps)}",
            f"Last scan: {datetime.fromtimestamp(self._last_scan, tz=timezone.utc).strftime('%H:%M UTC') if self._last_scan else 'never'}",
            "",
        ]

        for i, token in enumerate(opps[:10], 1):
            name = token.get("name", "?")
            symbol = token.get("symbol", "?")
            score = token.get("score", 0)
            burn = token.get("burn_amount", 0)
            author = token.get("author", "?")
            source = token.get("source", "?")
            addr = token.get("token_address", "?")

            indicator = "🔥" if score >= 60 else "⚡" if score >= 40 else "📊"
            lines.append(f"{indicator} #{i} {name} (${symbol}) — Score: {score}/100")
            lines.append(f"   Author: {author} | Source: {source}")
            if addr and addr != "?":
                lines.append(f"   Address: {addr[:16]}...")
            if burn:
                lines.append(f"   Burn: {burn:,.0f} CLAWNCH")
            lines.append("")

        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Scout status."""
        return {
            "tokens_tracked": len(self._cache),
            "scored_tokens": len(self._scored),
            "last_scan": self._last_scan,
            "opportunities": len(self.get_opportunities()),
        }
