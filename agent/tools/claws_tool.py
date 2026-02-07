"""
CLAWS Tools for The Constituent v6.2
======================================
Wraps CLAWS (Clawnch Long-term Agentic Working Storage) as engine tools.
Gives Claude persistent, searchable, semantic memory via the Clawnch API.
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..integrations.claws_memory import ClawsMemory

logger = logging.getLogger("TheConstituent.Tools.CLAWS")

_claws: ClawsMemory = None


def _get_claws() -> ClawsMemory:
    global _claws
    if _claws is None:
        _claws = ClawsMemory()
    return _claws


# ------------------------------------------------------------------
# Tool Handlers
# ------------------------------------------------------------------


def _claws_remember(content: str, tags: str = "", importance: float = 0.5, thread_id: str = "") -> str:
    """Store a memory in CLAWS persistent storage."""
    claws = _get_claws()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = claws.remember(
        content=content,
        tags=tag_list,
        importance=float(importance),
        thread_id=thread_id or None,
    )
    if "error" in result:
        return f"Error storing memory: {result['error']}"
    mem_id = result.get("id", result.get("memoryId", "?"))
    return f"Memory stored (id={mem_id})"


def _claws_recall(query: str, limit: int = 10, tags: str = "") -> str:
    """Search memories using BM25 + semantic search."""
    claws = _get_claws()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = claws.recall(query=query, limit=int(limit), tags=tag_list)
    if "error" in result:
        return f"Error searching: {result['error']}"

    memories = result.get("memories", result.get("results", []))
    if not memories:
        return f"No memories found for '{query}'"

    lines = [f"Found {len(memories)} memories:"]
    for mem in memories:
        if not isinstance(mem, dict):
            continue
        mid = mem.get("id", "?")[:12]
        content = mem.get("content", "")[:200]
        score = mem.get("score", mem.get("relevance", 0))
        mem_tags = mem.get("tags", [])
        tag_str = f" [{', '.join(mem_tags)}]" if mem_tags else ""
        lines.append(f"[{mid}] (score={score:.2f}){tag_str} {content}")
    return "\n".join(lines)


def _claws_recent(limit: int = 10, thread_id: str = "") -> str:
    """Get most recent memories."""
    claws = _get_claws()
    result = claws.recent(limit=int(limit), thread_id=thread_id or None)
    if "error" in result:
        return f"Error: {result['error']}"

    memories = result.get("memories", result.get("results", []))
    if not memories:
        return "No recent memories"

    lines = [f"Recent {len(memories)} memories:"]
    for mem in memories:
        if not isinstance(mem, dict):
            continue
        mid = mem.get("id", "?")[:12]
        content = mem.get("content", "")[:200]
        ts = mem.get("timestamp", mem.get("createdAt", ""))
        mem_tags = mem.get("tags", [])
        tag_str = f" [{', '.join(mem_tags)}]" if mem_tags else ""
        lines.append(f"[{mid}] {ts}{tag_str} {content}")
    return "\n".join(lines)


def _claws_forget(memory_id: str) -> str:
    """Delete a memory by ID."""
    claws = _get_claws()
    result = claws.forget(memory_id)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Memory {memory_id} deleted"


def _claws_tag(memory_id: str, tags: str) -> str:
    """Add tags to an existing memory."""
    claws = _get_claws()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    if not tag_list:
        return "Error: provide comma-separated tags"
    result = claws.tag(memory_id, tag_list)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Tags added to {memory_id}: {', '.join(tag_list)}"


def _claws_stats() -> str:
    """Get CLAWS memory statistics."""
    claws = _get_claws()
    result = claws.stats()
    if "error" in result:
        return f"Error: {result['error']}"
    return json.dumps(result, indent=2, default=str)


def _claws_context(query: str, max_tokens: int = 2000, tags: str = "") -> str:
    """Get a context window of relevant memories for the current task."""
    claws = _get_claws()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = claws.context(query=query, max_tokens=int(max_tokens), tags=tag_list)
    if "error" in result:
        return f"Error: {result['error']}"
    context_text = result.get("context", result.get("text", ""))
    if not context_text:
        return "No relevant context found"
    return context_text


def _claws_seed_token() -> str:
    """Seed CLAWS with $REPUBLIC token deployment data."""
    claws = _get_claws()
    results = claws.seed_republic_token_data()
    ok = sum(1 for r in results if "error" not in r)
    fail = len(results) - ok
    return f"Seeded {ok} token memories ({fail} errors)" if fail else f"Seeded {ok} token memories"


def _claws_status() -> str:
    """Get CLAWS integration status."""
    claws = _get_claws()
    status = claws.get_status()
    return json.dumps(status, indent=2, default=str)


# ------------------------------------------------------------------
# Tool Registration
# ------------------------------------------------------------------


def get_tools() -> List[Tool]:
    """Register CLAWS memory tools."""
    return [
        Tool(
            name="claws_remember",
            description=(
                "Store a memory in CLAWS persistent storage. Use this to remember "
                "important events, decisions, conversations, token data, and learnings. "
                "Memories persist across sessions and are searchable."
            ),
            category="memory",
            params=[
                ToolParam("content", "string", "The memory content to store"),
                ToolParam("tags", "string", "Comma-separated tags (e.g. 'token,governance,decision')", required=False, default=""),
                ToolParam("importance", "string", "Importance score 0.0-1.0 (default 0.5)", required=False, default="0.5"),
                ToolParam("thread_id", "string", "Thread ID for grouping related memories", required=False, default=""),
            ],
            handler=lambda content, tags="", importance="0.5", thread_id="": _claws_remember(content, tags, float(importance), thread_id),
        ),
        Tool(
            name="claws_recall",
            description=(
                "Search memories using BM25 + semantic search. Returns the most relevant "
                "memories matching the query. Use this to recall past decisions, events, "
                "token data, conversations, and learnings."
            ),
            category="memory",
            params=[
                ToolParam("query", "string", "Search query"),
                ToolParam("limit", "integer", "Max results (default 10)", required=False, default=10),
                ToolParam("tags", "string", "Filter by comma-separated tags", required=False, default=""),
            ],
            handler=lambda query, limit=10, tags="": _claws_recall(query, int(limit), tags),
        ),
        Tool(
            name="claws_recent",
            description="Get the most recent memories from CLAWS storage.",
            category="memory",
            params=[
                ToolParam("limit", "integer", "Number of recent memories (default 10)", required=False, default=10),
                ToolParam("thread_id", "string", "Filter by thread ID", required=False, default=""),
            ],
            handler=lambda limit=10, thread_id="": _claws_recent(int(limit), thread_id),
        ),
        Tool(
            name="claws_forget",
            description="Delete a specific memory from CLAWS by its ID.",
            category="memory",
            params=[
                ToolParam("memory_id", "string", "ID of the memory to delete"),
            ],
            handler=_claws_forget,
        ),
        Tool(
            name="claws_tag",
            description="Add tags to an existing CLAWS memory.",
            category="memory",
            params=[
                ToolParam("memory_id", "string", "ID of the memory to tag"),
                ToolParam("tags", "string", "Comma-separated tags to add"),
            ],
            handler=_claws_tag,
        ),
        Tool(
            name="claws_context",
            description=(
                "Get a context window of relevant memories for a query. "
                "Returns a formatted block of the most relevant memories "
                "to include in prompts or reasoning."
            ),
            category="memory",
            params=[
                ToolParam("query", "string", "Context query (e.g. current task description)"),
                ToolParam("max_tokens", "integer", "Max token budget (default 2000)", required=False, default=2000),
                ToolParam("tags", "string", "Filter by comma-separated tags", required=False, default=""),
            ],
            handler=lambda query, max_tokens=2000, tags="": _claws_context(query, int(max_tokens), tags),
        ),
        Tool(
            name="claws_stats",
            description="Get CLAWS memory statistics (total memories, storage usage, etc.).",
            category="memory",
            params=[],
            handler=_claws_stats,
        ),
        Tool(
            name="claws_seed_token",
            description="Seed CLAWS with $REPUBLIC token deployment data (run once after launch).",
            category="token",
            params=[],
            handler=_claws_seed_token,
        ),
        Tool(
            name="claws_status",
            description="Check CLAWS memory integration status and connectivity.",
            category="memory",
            params=[],
            handler=_claws_status,
        ),
    ]
