"""
Moltbook Tools for The Constituent v5.0
=========================================
Wraps existing MoltbookOperations as tools for the engine.
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..moltbook_ops import MoltbookOperations

logger = logging.getLogger("TheConstituent.Tools.Moltbook")

_moltbook: MoltbookOperations = None


def _get_moltbook() -> MoltbookOperations:
    global _moltbook
    if _moltbook is None:
        _moltbook = MoltbookOperations()
    return _moltbook


def _moltbook_post(title: str, content: str, submolt: str = "") -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    rate = mb.can_post()
    if not rate.get("can_post", False):
        return f"Rate limited: wait {rate.get('wait_minutes', '?')} minutes"
    result = mb.create_post(title=title, content=content, submolt=submolt or None)
    if result and result.get("success"):
        post_id = result.get("post_id", "?")
        url = result.get("url", f"https://www.moltbook.com/post/{post_id}")
        return f"Posted on Moltbook: id={post_id} url={url}"
    return f"Post failed: {result.get('error', 'unknown')}"


def _moltbook_comment(post_id: str, content: str) -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    rate = mb.can_comment()
    if not rate.get("can_comment", True):
        return f"Comment rate limited: wait {rate.get('wait_minutes', '?')} minutes"
    result = mb.create_comment(post_id=post_id, content=content)
    if result and result.get("success"):
        url = f"https://www.moltbook.com/post/{post_id}"
        return f"Commented on post {post_id} url={url}"
    return f"Comment failed: {result.get('error', 'unknown')}"


def _moltbook_upvote(post_id: str) -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    result = mb.upvote(post_id=post_id)
    if result and result.get("success"):
        return f"Upvoted post {post_id}"
    return f"Upvote failed: {result.get('error', 'unknown')}"


def _moltbook_feed(limit: int = 10) -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    feed = mb.get_feed(limit=limit)
    if not feed:
        return "Feed is empty or unavailable"
    # feed is already a list from get_feed()
    if isinstance(feed, dict):
        # If API returns a dict with a "posts" key
        feed = feed.get("posts", feed.get("data", []))
    lines = []
    for post in feed[:limit]:
        if not isinstance(post, dict):
            continue
        pid = post.get("id", "?")
        title = post.get("title", "")[:80]
        author = post.get("authorName", post.get("author", "?"))
        comments = post.get("commentCount", 0)
        lines.append(f"[{pid}] {title} by {author} ({comments} comments)")
    return "\n".join(lines) if lines else "Feed returned no valid posts"


def _moltbook_get_post(post_id: str) -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    post = mb.get_post_with_comments(post_id)
    if not post:
        return f"Post {post_id} not found"
    title = post.get("title", "")
    content = post.get("content", "")[:500]
    comments = post.get("comments", [])
    if not isinstance(comments, list):
        comments = []
    result = f"**{title}**\n{content}\n\n--- {len(comments)} comments ---"
    for c in comments[:10]:
        if not isinstance(c, dict):
            continue
        author = c.get("authorName", c.get("author", "?"))
        text = c.get("content", "")[:200]
        result += f"\n- {author}: {text}"
    return result


def _moltbook_status() -> str:
    mb = _get_moltbook()
    status = mb.get_status()
    return json.dumps(status, indent=2, default=str)


def _moltbook_heartbeat() -> str:
    mb = _get_moltbook()
    if not mb.is_connected():
        return "Error: Moltbook not connected"
    result = mb.heartbeat()
    if isinstance(result, dict):
        return f"Heartbeat: {'ok' if result.get('success') else 'failed'}"
    return f"Heartbeat: done"


def get_tools() -> List[Tool]:
    """Register Moltbook tools."""
    return [
        Tool(
            name="moltbook_post",
            description="Post content on Moltbook (AI social network). Respects rate limits.",
            category="social",
            params=[
                ToolParam("title", "string", "Post title"),
                ToolParam("content", "string", "Post content (markdown supported)"),
                ToolParam("submolt", "string", "Submolt to post to (e.g. 'clawnch' for m/clawnch)", required=False, default=""),
            ],
            handler=_moltbook_post,
        ),
        Tool(
            name="moltbook_comment",
            description="Comment on a Moltbook post.",
            category="social",
            params=[
                ToolParam("post_id", "string", "ID of the post to comment on"),
                ToolParam("content", "string", "Comment text"),
            ],
            handler=_moltbook_comment,
        ),
        Tool(
            name="moltbook_upvote",
            description="Upvote a Moltbook post.",
            category="social",
            params=[
                ToolParam("post_id", "string", "ID of the post to upvote"),
            ],
            handler=_moltbook_upvote,
        ),
        Tool(
            name="moltbook_feed",
            description="Read the Moltbook feed (latest posts from all agents).",
            category="social",
            params=[
                ToolParam("limit", "integer", "Number of posts to fetch", required=False, default=10),
            ],
            handler=lambda limit=10: _moltbook_feed(int(limit)),
        ),
        Tool(
            name="moltbook_get_post",
            description="Get a specific Moltbook post with all comments.",
            category="social",
            params=[
                ToolParam("post_id", "string", "Post ID"),
            ],
            handler=_moltbook_get_post,
        ),
        Tool(
            name="moltbook_status",
            description="Check Moltbook connection status and rate limits.",
            category="social",
            params=[],
            handler=_moltbook_status,
        ),
        Tool(
            name="moltbook_heartbeat",
            description="Send heartbeat to Moltbook (periodic check-in).",
            category="social",
            params=[],
            handler=_moltbook_heartbeat,
        ),
    ]
