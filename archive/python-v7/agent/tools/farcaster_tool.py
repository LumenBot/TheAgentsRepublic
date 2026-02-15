"""
Farcaster Tools for The Constituent v7.1
=========================================
Engine tools for interacting with Farcaster via the Neynar API.
Supports posting casts, replying, reading feed, liking, searching,
and diagnostic status checks.

All tools are L1 (autonomous) — the agent can use them freely as part
of its social engagement strategy across Farcaster channels like
"base", "ai-agents", and "governance".
"""

import os
import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..integrations.farcaster import FarcasterIntegration

logger = logging.getLogger("TheConstituent.Tools.Farcaster")

_farcaster: FarcasterIntegration = None


def _get_farcaster() -> FarcasterIntegration:
    """Get or create the singleton FarcasterIntegration instance.

    Re-creates the instance if not connected, so env var changes
    (e.g. adding NEYNAR_API_KEY to .env) take effect without restart.
    """
    global _farcaster
    if _farcaster is None or not _farcaster.is_connected():
        _farcaster = FarcasterIntegration()
        _farcaster.connect()
    return _farcaster


def _farcaster_status() -> str:
    """Diagnostic: check Farcaster connection and env var status."""
    api_key = os.getenv("NEYNAR_API_KEY", "")
    signer = os.getenv("FARCASTER_SIGNER_UUID", "")
    fid = os.getenv("FARCASTER_FID", "")

    lines = ["Farcaster Diagnostics"]
    lines.append(f"├ NEYNAR_API_KEY: {'set (' + api_key[:8] + '...)' if api_key else 'MISSING'}")
    lines.append(f"├ FARCASTER_SIGNER_UUID: {'set (' + signer[:8] + '...)' if signer else 'MISSING (write ops disabled)'}")
    lines.append(f"├ FARCASTER_FID: {fid if fid else 'MISSING (feed reading disabled)'}")

    if not api_key:
        lines.append("└ ACTION: Set NEYNAR_API_KEY in .env (get one at neynar.com)")
        return "\n".join(lines)

    # Try connecting
    fc = _get_farcaster()
    connected = fc.is_connected()
    lines.append(f"├ Connected: {connected}")

    if connected:
        status = fc.get_status()
        lines.append(f"├ Read-only: {status.get('read_only', True)}")
        lines.append(f"└ Ready for: {'read+write' if not status.get('read_only') else 'read only'}")
    else:
        lines.append(f"└ ACTION: API key may be invalid. Verify at neynar.com dashboard")

    return "\n".join(lines)


def _farcaster_post(text: str, channel_id: str = "") -> str:
    """Post a cast to Farcaster with optional channel."""
    fc = _get_farcaster()
    if not fc.is_connected():
        return "Error: Farcaster not connected (check NEYNAR_API_KEY)"

    if not text.strip():
        return "Error: Cast text cannot be empty"

    kwargs = {}
    if channel_id:
        kwargs["channel_id"] = channel_id

    result = fc.post_content(text, **kwargs)
    if result.get("success"):
        cast_hash = result.get("cast_hash", "?")
        url = result.get("url", "")
        channel = result.get("channel", "")
        parts = [f"Cast posted on Farcaster: hash={cast_hash[:16]}"]
        if channel:
            parts.append(f"channel=/{channel}")
        if url:
            parts.append(f"url={url}")
        return " ".join(parts)
    return f"Cast failed: {result.get('error', 'unknown error')}"


def _farcaster_reply(parent_hash: str, text: str) -> str:
    """Reply to a cast by its hash."""
    fc = _get_farcaster()
    if not fc.is_connected():
        return "Error: Farcaster not connected (check NEYNAR_API_KEY)"

    if not text.strip():
        return "Error: Reply text cannot be empty"
    if not parent_hash.strip():
        return "Error: Parent cast hash is required"

    result = fc.reply_to_cast(parent_hash.strip(), text)
    if result.get("success"):
        cast_hash = result.get("cast_hash", "?")
        return f"Reply posted: hash={cast_hash[:16]} -> parent={parent_hash[:16]}"
    return f"Reply failed: {result.get('error', 'unknown error')}"


def _farcaster_feed(limit: int = 10) -> str:
    """Read the agent's Farcaster following feed."""
    fc = _get_farcaster()
    if not fc.is_connected():
        return "Error: Farcaster not connected (check NEYNAR_API_KEY)"

    casts = fc.read_feed(limit=int(limit))
    if not casts:
        return "Feed is empty or unavailable"

    lines = [f"Farcaster feed ({len(casts)} casts):"]
    for cast in casts:
        hash_short = cast.get("hash", "?")[:10]
        author = cast.get("author", "?")
        text = cast.get("text", "")[:120]
        likes = cast.get("likes", 0)
        replies = cast.get("replies", 0)
        channel = cast.get("channel", "")
        channel_str = f" /{channel}" if channel else ""
        lines.append(f"[{hash_short}] {author}{channel_str}: {text} ({likes}L {replies}R)")
    return "\n".join(lines)


def _farcaster_like(cast_hash: str) -> str:
    """Like a cast on Farcaster."""
    fc = _get_farcaster()
    if not fc.is_connected():
        return "Error: Farcaster not connected (check NEYNAR_API_KEY)"

    if not cast_hash.strip():
        return "Error: Cast hash is required"

    result = fc.engage(cast_hash.strip(), action="like")
    if result.get("success"):
        return f"Liked cast {cast_hash[:16]}"
    return f"Like failed: {result.get('error', 'unknown error')}"


def _farcaster_search(query: str, search_type: str = "users") -> str:
    """Search for users or casts on Farcaster."""
    fc = _get_farcaster()
    if not fc.is_connected():
        return "Error: Farcaster not connected (check NEYNAR_API_KEY)"

    if not query.strip():
        return "Error: Search query cannot be empty"

    if search_type == "casts":
        results = fc.search_casts(query.strip(), limit=10)
        if not results:
            return f"No casts found for '{query}'"
        lines = [f"Cast search results for '{query}' ({len(results)} found):"]
        for cast in results:
            hash_short = cast.get("hash", "?")[:10]
            author = cast.get("author", "?")
            text = cast.get("text", "")[:120]
            lines.append(f"[{hash_short}] {author}: {text}")
        return "\n".join(lines)
    else:
        # Default: user search
        results = fc.search_users(query.strip(), limit=5)
        if not results:
            return f"No users found for '{query}'"
        lines = [f"User search results for '{query}' ({len(results)} found):"]
        for user in results:
            fid = user.get("fid", "?")
            fname = user.get("fname", "?")
            display = user.get("display_name", "")
            followers = user.get("follower_count", 0)
            bio = user.get("bio", "")[:80]
            lines.append(f"  @{fname} (fid={fid}) {display} | {followers} followers | {bio}")
        return "\n".join(lines)


def get_tools() -> List[Tool]:
    """Register Farcaster tools for the engine."""
    return [
        Tool(
            name="farcaster_status",
            description="Diagnostic: check Farcaster connection status, env vars, and configuration. Use this to debug connection issues.",
            category="social",
            governance_level="L1",
            params=[],
            handler=lambda: _farcaster_status(),
        ),
        Tool(
            name="farcaster_post",
            description="Post a cast on Farcaster (decentralized social protocol). Supports channel targeting.",
            category="social",
            governance_level="L1",
            params=[
                ToolParam("text", "string", "Cast text (max 1024 chars)"),
                ToolParam(
                    "channel_id", "string",
                    "Farcaster channel to post to (e.g. 'base', 'ai-agents', 'governance')",
                    required=False, default="",
                ),
            ],
            handler=_farcaster_post,
        ),
        Tool(
            name="farcaster_reply",
            description="Reply to a Farcaster cast by its hash.",
            category="social",
            governance_level="L1",
            params=[
                ToolParam("parent_hash", "string", "Hash of the cast to reply to (0x...)"),
                ToolParam("text", "string", "Reply text (max 1024 chars)"),
            ],
            handler=_farcaster_reply,
        ),
        Tool(
            name="farcaster_feed",
            description="Read the Farcaster following feed (recent casts from followed accounts).",
            category="social",
            governance_level="L1",
            params=[
                ToolParam("limit", "integer", "Number of casts to fetch (default 10, max 100)", required=False, default=10),
            ],
            handler=lambda limit=10: _farcaster_feed(int(limit)),
        ),
        Tool(
            name="farcaster_like",
            description="Like a cast on Farcaster.",
            category="social",
            governance_level="L1",
            params=[
                ToolParam("cast_hash", "string", "Hash of the cast to like (0x...)"),
            ],
            handler=_farcaster_like,
        ),
        Tool(
            name="farcaster_search",
            description="Search for users or casts on Farcaster.",
            category="social",
            governance_level="L1",
            params=[
                ToolParam("query", "string", "Search query (username, display name, or cast text)"),
                ToolParam(
                    "search_type", "string",
                    "Type of search: 'users' or 'casts' (default: 'users')",
                    required=False, default="users",
                ),
            ],
            handler=_farcaster_search,
        ),
    ]
