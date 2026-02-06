"""
Message Tools for The Constituent v5.0
========================================
Multi-channel messaging: send messages to Telegram, Moltbook, etc.
Inspired by OpenClaw message-tool.ts.
"""

import os
import logging
import requests
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Message")


def _send_telegram(text: str, chat_id: str = "") -> str:
    """Send a message via Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    target = chat_id or os.getenv("OPERATOR_TELEGRAM_CHAT_ID", "")
    if not token:
        return "Error: TELEGRAM_BOT_TOKEN not set"
    if not target:
        return "Error: No chat_id provided and OPERATOR_TELEGRAM_CHAT_ID not set"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": target, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return f"Telegram message sent to {target}"
        return f"Telegram error: {data.get('description', 'unknown')}"
    except Exception as e:
        return f"Telegram error: {e}"


def _message_send(channel: str, content: str, to: str = "") -> str:
    """Route a message to the appropriate channel."""
    channel = channel.lower().strip()

    if channel == "telegram":
        return _send_telegram(content, to)
    elif channel == "moltbook":
        # Use moltbook_tool for posting
        from .moltbook_tool import _moltbook_post
        return _moltbook_post(title="", content=content)
    else:
        return f"Error: unknown channel '{channel}'. Available: telegram, moltbook"


def get_tools() -> List[Tool]:
    return [
        Tool(
            name="message_send",
            description="Send a message via a specific channel (telegram, moltbook).",
            category="messaging",
            params=[
                ToolParam("channel", "string", "Channel: telegram, moltbook"),
                ToolParam("content", "string", "Message content"),
                ToolParam("to", "string", "Recipient (chat_id for Telegram)", required=False, default=""),
            ],
            handler=_message_send,
        ),
        Tool(
            name="notify_operator",
            description="Send a notification to Blaise via Telegram.",
            category="messaging",
            params=[
                ToolParam("message", "string", "Notification text"),
            ],
            handler=lambda message: _send_telegram(f"🔔 {message}"),
        ),
    ]
