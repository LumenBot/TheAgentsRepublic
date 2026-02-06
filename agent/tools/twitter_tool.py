"""
Twitter Tools for The Constituent v5.0
========================================
Wraps Twitter/X operations. L2 governance (approval needed).
"""

import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..twitter_ops import TwitterOperations

logger = logging.getLogger("TheConstituent.Tools.Twitter")

_twitter: TwitterOperations = None


def _get_twitter() -> TwitterOperations:
    global _twitter
    if _twitter is None:
        _twitter = TwitterOperations()
    return _twitter


def _tweet_post(text: str) -> str:
    tw = _get_twitter()
    if not tw.is_connected():
        # Graceful degradation: queue tweet instead of erroring
        tw.queue_tweet(text, metadata={"source": "tool", "fallback": True})
        return "Twitter not connected — tweet queued for manual posting"
    if not tw.has_write_access():
        tw.queue_tweet(text, metadata={"source": "tool", "fallback": True})
        return "Twitter write access insufficient (Free tier) — tweet queued for manual posting"
    result = tw._post_tweet({"text": text, "id": 0, "status": "approved"})
    return result


def _tweet_status() -> str:
    tw = _get_twitter()
    connected = tw.is_connected()
    write = tw.has_write_access()
    return f"Twitter connected: {connected} | Write access: {write}"


def get_tools() -> List[Tool]:
    return [
        Tool(
            name="tweet_post",
            description="Post a tweet on X/Twitter. Requires operator approval (L2).",
            category="social",
            governance_level="L2",
            params=[ToolParam("text", "string", "Tweet text (max 280 chars)")],
            handler=_tweet_post,
        ),
        Tool(
            name="twitter_status",
            description="Check Twitter connection status.",
            category="social",
            params=[],
            handler=_tweet_status,
        ),
    ]
