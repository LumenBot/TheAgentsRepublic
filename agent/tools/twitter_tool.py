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
        return "Error: Twitter not connected (API keys not configured)"
    result = tw.post_tweet(text)
    if result and result.get("success"):
        return f"Tweeted: {result.get('url', 'no URL')}"
    return f"Tweet failed: {result.get('error', 'unknown')}"


def _tweet_status() -> str:
    tw = _get_twitter()
    return f"Twitter connected: {tw.is_connected()}"


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
