"""
Web Tools for The Constituent v5.0
=====================================
Web search (Brave API) and web page fetching.
Inspired by OpenClaw web-search.ts and web-fetch.ts.
"""

import os
import re
import json
import logging
import hashlib
import time
from typing import List, Dict, Optional
from html.parser import HTMLParser

import requests

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Web")

# Cache (in-memory, TTL 5 min)
_cache: Dict[str, dict] = {}
CACHE_TTL = 300


def _cache_get(key: str) -> Optional[dict]:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data: dict):
    _cache[key] = {"data": data, "ts": time.time()}


# ===== HTML Text Extractor (lightweight readability) =====

class _TextExtractor(HTMLParser):
    """Simple HTML-to-text extractor. Strips tags, keeps text."""
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag.lower() in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._text.append(data)

    def get_text(self) -> str:
        raw = "".join(self._text)
        # Collapse whitespace
        raw = re.sub(r'[ \t]+', ' ', raw)
        raw = re.sub(r'\n{3,}', '\n\n', raw)
        return raw.strip()


def _extract_text(html: str, max_chars: int = 30000) -> str:
    """Extract readable text from HTML."""
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(truncated)"
    return text


# ===== Web Search (Brave API) =====

def _web_search(query: str, count: int = 5) -> str:
    """Search the web using Brave Search API."""
    api_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
    if not api_key:
        return "Error: BRAVE_SEARCH_API_KEY not set. Add it to your .env file. Free tier: https://brave.com/search/api/"

    cache_key = hashlib.md5(f"search:{query}:{count}".encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": min(count, 10)},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return f"Search error: {e}"

    results = []
    for item in data.get("web", {}).get("results", [])[:count]:
        title = item.get("title", "")
        url = item.get("url", "")
        desc = item.get("description", "")[:200]
        age = item.get("age", "")
        results.append(f"**{title}**\n{url}\n{desc}" + (f" ({age})" if age else ""))

    output = "\n\n".join(results) if results else "No results found."
    _cache_set(cache_key, output)
    return output


# ===== Web Fetch (page content) =====

def _web_fetch(url: str, max_chars: int = 30000) -> str:
    """Fetch and extract readable text from a web page."""
    # SSRF guard
    if any(blocked in url.lower() for blocked in ["localhost", "127.0.0.1", "0.0.0.0", "169.254", "[::1]"]):
        return "Error: blocked URL (localhost/internal)"

    if not url.startswith("http"):
        url = "https://" + url

    cache_key = hashlib.md5(f"fetch:{url}".encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            },
            timeout=15,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"Fetch error: {e}"

    content_type = resp.headers.get("Content-Type", "")

    if "application/json" in content_type:
        try:
            text = json.dumps(resp.json(), indent=2, ensure_ascii=False)[:max_chars]
        except Exception:
            text = resp.text[:max_chars]
    elif "text/html" in content_type or "<html" in resp.text[:500].lower():
        text = _extract_text(resp.text, max_chars)
    else:
        text = resp.text[:max_chars]

    if not text.strip():
        text = "(page returned no readable content)"

    _cache_set(cache_key, text)
    return text


def get_tools() -> List[Tool]:
    """Register web tools."""
    return [
        Tool(
            name="web_search",
            description="Search the web. Returns titles, URLs, and descriptions.",
            category="web",
            params=[
                ToolParam("query", "string", "Search query (1-6 words work best)"),
                ToolParam("count", "integer", "Number of results (1-10)", required=False, default=5),
            ],
            handler=lambda query, count=5: _web_search(query, int(count)),
        ),
        Tool(
            name="web_fetch",
            description="Fetch and extract readable text from a URL.",
            category="web",
            params=[
                ToolParam("url", "string", "URL to fetch"),
                ToolParam("max_chars", "integer", "Max characters to return", required=False, default=30000),
            ],
            handler=lambda url, max_chars=30000: _web_fetch(url, int(max_chars)),
        ),
    ]
