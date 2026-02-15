"""
Farcaster Integration — Neynar API v2
=======================================
Connects The Constituent to Farcaster, the decentralized social protocol
built on OP Mainnet. Uses the Neynar API (https://api.neynar.com/v2/farcaster/)
as the primary interface.

Farcaster is popular with the Base L2 crypto community and supports channels
like "base", "ai-agents", and "governance" that align with the Republic's mission.

v6.3: Initial Farcaster integration via Neynar API.
"""

import os
import logging
import time
from typing import Dict, List, Optional

import requests

from ..integrations.base_integration import BaseIntegration

logger = logging.getLogger("TheConstituent.Integration.Farcaster")

NEYNAR_API_BASE = "https://api.neynar.com/v2/farcaster"
NEYNAR_TIMEOUT = 15

# Rate limiting: 300 reqs/min for paid Neynar tier
_RATE_LIMIT_MAX = 300
_RATE_LIMIT_WINDOW = 60  # seconds
_request_timestamps: List[float] = []


def _enforce_rate_limit():
    """Enforce Neynar rate limit of 300 requests/minute."""
    global _request_timestamps
    now = time.time()
    # Prune timestamps older than the window
    _request_timestamps = [t for t in _request_timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_request_timestamps) >= _RATE_LIMIT_MAX:
        oldest = _request_timestamps[0]
        wait = _RATE_LIMIT_WINDOW - (now - oldest)
        if wait > 0:
            logger.warning(f"Neynar rate limit approaching, sleeping {wait:.1f}s")
            time.sleep(wait)
    _request_timestamps.append(time.time())


class FarcasterIntegration(BaseIntegration):
    """
    Farcaster integration via Neynar API v2.

    Supports:
    - Posting casts (with optional channel targeting)
    - Reading the following feed
    - Reacting to casts (like/recast)
    - Replying to casts
    - Searching for users

    Requires:
    - NEYNAR_API_KEY: API key from neynar.com
    - FARCASTER_SIGNER_UUID: Managed signer UUID for write operations
    - FARCASTER_FID: The agent's Farcaster ID (for reading feed)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        signer_uuid: Optional[str] = None,
        fid: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("NEYNAR_API_KEY", "")
        self._signer_uuid = signer_uuid or os.getenv("FARCASTER_SIGNER_UUID", "")
        self._fid = fid or os.getenv("FARCASTER_FID", "")
        self._connected = False
        self._session = requests.Session()

    # -----------------------------------------------------------------
    # BaseIntegration interface
    # -----------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "farcaster"

    def connect(self) -> bool:
        """Verify API key and signer are valid by fetching signer status."""
        if not self._api_key:
            logger.error("Farcaster connect failed: NEYNAR_API_KEY not set")
            return False
        if not self._signer_uuid:
            logger.warning("Farcaster: FARCASTER_SIGNER_UUID not set — read-only mode")

        try:
            # Validate the API key with a lightweight call
            resp = self._api_get("/user/search", params={"q": "farcaster", "limit": 1})
            if "error" in resp:
                logger.error(f"Farcaster connect failed: {resp['error']}")
                return False
            self._connected = True
            logger.info(f"Farcaster connected | fid={self._fid} | signer={'yes' if self._signer_uuid else 'no'}")
            return True
        except Exception as e:
            logger.error(f"Farcaster connect error: {e}")
            return False

    def is_connected(self) -> bool:
        return self._connected

    def post_content(self, content: str, **kwargs) -> Dict:
        """
        Post a cast to Farcaster.

        Args:
            content: Cast text (max 1024 characters for Farcaster)
            channel_id: Optional channel to post to (e.g. "base", "ai-agents")
            embeds: Optional list of embed URLs

        Returns:
            {"success": True, "cast_hash": "0x...", "url": "..."} or error dict
        """
        if not self._connected:
            return {"success": False, "error": "Not connected to Farcaster"}
        if not self._signer_uuid:
            return {"success": False, "error": "No signer UUID — cannot post (read-only mode)"}

        channel_id = kwargs.get("channel_id", "")
        embeds = kwargs.get("embeds", [])

        # Farcaster cast limit is 1024 characters
        if len(content) > 1024:
            logger.warning(f"Cast text truncated from {len(content)} to 1024 chars")
            content = content[:1021] + "..."

        body: Dict = {
            "signer_uuid": self._signer_uuid,
            "text": content,
        }
        if channel_id:
            body["channel_id"] = channel_id
        if embeds:
            body["embeds"] = [{"url": url} for url in embeds]

        result = self._api_post("/cast", json_body=body)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        cast = result.get("cast", {})
        cast_hash = cast.get("hash", "")
        author_fname = cast.get("author", {}).get("fname", "")
        url = f"https://warpcast.com/{author_fname}/{cast_hash[:10]}" if author_fname and cast_hash else ""

        logger.info(f"Cast posted: {cast_hash[:16]}... channel={channel_id or 'home'}")
        return {
            "success": True,
            "cast_hash": cast_hash,
            "url": url,
            "channel": channel_id,
        }

    def read_feed(self, limit: int = 10) -> List[Dict]:
        """
        Read the agent's following feed.

        Args:
            limit: Number of casts to return (max 100)

        Returns:
            List of cast dicts with keys: hash, text, author, timestamp, reactions, replies
        """
        if not self._connected:
            return []

        params = {
            "feed_type": "following",
            "limit": min(limit, 100),
        }
        if self._fid:
            params["fid"] = self._fid

        result = self._api_get("/feed", params=params)
        if "error" in result:
            logger.error(f"Feed read error: {result['error']}")
            return []

        casts = result.get("casts", [])
        parsed = []
        for cast in casts[:limit]:
            author = cast.get("author", {})
            reactions = cast.get("reactions", {})
            parsed.append({
                "hash": cast.get("hash", ""),
                "text": cast.get("text", ""),
                "author": author.get("display_name", author.get("fname", "?")),
                "author_fid": author.get("fid", ""),
                "author_fname": author.get("fname", ""),
                "timestamp": cast.get("timestamp", ""),
                "likes": reactions.get("likes_count", 0),
                "recasts": reactions.get("recasts_count", 0),
                "replies": cast.get("replies", {}).get("count", 0),
                "channel": cast.get("channel", {}).get("id", "") if cast.get("channel") else "",
            })

        return parsed

    def engage(self, post_id: str, action: str = "like", **kwargs) -> Dict:
        """
        Engage with a cast (like or recast).

        Args:
            post_id: The cast hash to engage with
            action: "like" or "recast"

        Returns:
            {"success": True, "action": "like", "target": "0x..."} or error dict
        """
        if not self._connected:
            return {"success": False, "error": "Not connected to Farcaster"}
        if not self._signer_uuid:
            return {"success": False, "error": "No signer UUID — cannot engage (read-only mode)"}

        if action not in ("like", "recast"):
            return {"success": False, "error": f"Unsupported action: {action}. Use 'like' or 'recast'"}

        body = {
            "signer_uuid": self._signer_uuid,
            "reaction_type": action,
            "target": post_id,
        }

        result = self._api_put("/reaction", json_body=body)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        logger.info(f"Farcaster {action}: {post_id[:16]}...")
        return {
            "success": True,
            "action": action,
            "target": post_id,
        }

    def get_status(self) -> Dict:
        """Get detailed Farcaster integration status."""
        base = super().get_status()
        base.update({
            "fid": self._fid,
            "has_signer": bool(self._signer_uuid),
            "has_api_key": bool(self._api_key),
            "read_only": not bool(self._signer_uuid),
        })
        return base

    # -----------------------------------------------------------------
    # Extended Farcaster operations
    # -----------------------------------------------------------------

    def reply_to_cast(self, parent_hash: str, text: str, **kwargs) -> Dict:
        """
        Reply to an existing cast.

        Args:
            parent_hash: Hash of the cast to reply to
            text: Reply text (max 1024 characters)

        Returns:
            {"success": True, "cast_hash": "0x...", "parent": "0x..."} or error dict
        """
        if not self._connected:
            return {"success": False, "error": "Not connected to Farcaster"}
        if not self._signer_uuid:
            return {"success": False, "error": "No signer UUID — cannot reply (read-only mode)"}

        if len(text) > 1024:
            text = text[:1021] + "..."

        body = {
            "signer_uuid": self._signer_uuid,
            "text": text,
            "parent": parent_hash,
        }

        channel_id = kwargs.get("channel_id", "")
        if channel_id:
            body["channel_id"] = channel_id

        result = self._api_post("/cast", json_body=body)
        if "error" in result:
            return {"success": False, "error": result["error"]}

        cast = result.get("cast", {})
        cast_hash = cast.get("hash", "")
        logger.info(f"Reply posted: {cast_hash[:16]}... -> {parent_hash[:16]}...")
        return {
            "success": True,
            "cast_hash": cast_hash,
            "parent": parent_hash,
        }

    def search_users(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search for Farcaster users by username.

        Args:
            query: Search query (username or display name)
            limit: Max results to return

        Returns:
            List of user dicts with keys: fid, fname, display_name, follower_count
        """
        if not self._connected:
            return []

        result = self._api_get("/user/search", params={"q": query, "limit": min(limit, 10)})
        if "error" in result:
            logger.error(f"User search error: {result['error']}")
            return []

        users = result.get("result", {}).get("users", [])
        parsed = []
        for user in users[:limit]:
            parsed.append({
                "fid": user.get("fid", ""),
                "fname": user.get("username", ""),
                "display_name": user.get("display_name", ""),
                "follower_count": user.get("follower_count", 0),
                "following_count": user.get("following_count", 0),
                "bio": user.get("profile", {}).get("bio", {}).get("text", ""),
            })

        return parsed

    def search_casts(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for casts by text content.

        Args:
            query: Search text
            limit: Max results

        Returns:
            List of cast dicts
        """
        if not self._connected:
            return []

        result = self._api_get("/cast/search", params={"q": query, "limit": min(limit, 25)})
        if "error" in result:
            logger.error(f"Cast search error: {result['error']}")
            return []

        casts = result.get("result", {}).get("casts", [])
        parsed = []
        for cast in casts[:limit]:
            author = cast.get("author", {})
            parsed.append({
                "hash": cast.get("hash", ""),
                "text": cast.get("text", ""),
                "author": author.get("display_name", author.get("fname", "?")),
                "author_fid": author.get("fid", ""),
                "timestamp": cast.get("timestamp", ""),
            })

        return parsed

    # -----------------------------------------------------------------
    # Internal HTTP helpers
    # -----------------------------------------------------------------

    def _headers(self) -> Dict:
        """Build request headers with Neynar API key."""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "api_key": self._api_key,
        }

    def _api_get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Neynar API."""
        _enforce_rate_limit()
        url = f"{NEYNAR_API_BASE}{endpoint}"
        try:
            resp = self._session.get(
                url,
                headers=self._headers(),
                params=params or {},
                timeout=NEYNAR_TIMEOUT,
            )
            if resp.status_code == 429:
                logger.warning("Neynar rate limit hit (429), backing off")
                return {"error": "Rate limited by Neynar API. Try again shortly."}
            if resp.status_code == 401:
                self._connected = False
                return {"error": "Invalid Neynar API key (401)"}
            if resp.status_code >= 400:
                error_body = resp.text[:300]
                return {"error": f"Neynar API error {resp.status_code}: {error_body}"}
            return resp.json()
        except requests.exceptions.Timeout:
            return {"error": "Neynar API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Neynar API"}
        except Exception as e:
            logger.error(f"Neynar GET {endpoint} error: {e}")
            return {"error": str(e)}

    def _api_post(self, endpoint: str, json_body: Dict) -> Dict:
        """Make a POST request to the Neynar API."""
        _enforce_rate_limit()
        url = f"{NEYNAR_API_BASE}{endpoint}"
        try:
            resp = self._session.post(
                url,
                headers=self._headers(),
                json=json_body,
                timeout=NEYNAR_TIMEOUT,
            )
            if resp.status_code == 429:
                logger.warning("Neynar rate limit hit (429), backing off")
                return {"error": "Rate limited by Neynar API. Try again shortly."}
            if resp.status_code == 401:
                self._connected = False
                return {"error": "Invalid Neynar API key (401)"}
            if resp.status_code >= 400:
                error_body = resp.text[:300]
                return {"error": f"Neynar API error {resp.status_code}: {error_body}"}
            return resp.json()
        except requests.exceptions.Timeout:
            return {"error": "Neynar API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Neynar API"}
        except Exception as e:
            logger.error(f"Neynar POST {endpoint} error: {e}")
            return {"error": str(e)}

    def _api_put(self, endpoint: str, json_body: Dict) -> Dict:
        """Make a PUT request to the Neynar API."""
        _enforce_rate_limit()
        url = f"{NEYNAR_API_BASE}{endpoint}"
        try:
            resp = self._session.put(
                url,
                headers=self._headers(),
                json=json_body,
                timeout=NEYNAR_TIMEOUT,
            )
            if resp.status_code == 429:
                logger.warning("Neynar rate limit hit (429), backing off")
                return {"error": "Rate limited by Neynar API. Try again shortly."}
            if resp.status_code == 401:
                self._connected = False
                return {"error": "Invalid Neynar API key (401)"}
            if resp.status_code >= 400:
                error_body = resp.text[:300]
                return {"error": f"Neynar API error {resp.status_code}: {error_body}"}
            return resp.json()
        except requests.exceptions.Timeout:
            return {"error": "Neynar API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Neynar API"}
        except Exception as e:
            logger.error(f"Neynar PUT {endpoint} error: {e}")
            return {"error": str(e)}
