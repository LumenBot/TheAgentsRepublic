"""
Memory Tools for The Constituent v5.0
=======================================
Persistent memory: search, save, and retrieve information.
Inspired by OpenClaw memory-core (file-backed search).
"""

import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Memory")

MEMORY_DIR = "memory"
MEMORY_FILES = {
    "main": "MEMORY.md",
    "decisions": "memory/decisions.md",
    "contacts": "memory/contacts.md",
    "learnings": "memory/learnings.md",
    "constitution": "memory/knowledge/constitution_progress.md",
    "strategy": "memory/knowledge/strategic_decisions.md",
}


def _ensure_dir(workspace: Path):
    (workspace / "memory" / "knowledge").mkdir(parents=True, exist_ok=True)


def _memory_search(workspace: Path, query: str, max_results: int = 20) -> str:
    """Search across all memory files for a query."""
    _ensure_dir(workspace)
    results = []
    terms = query.lower().split()

    for name, rel_path in MEMORY_FILES.items():
        fp = workspace / rel_path
        if not fp.exists():
            continue
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            lower = line.lower()
            if any(t in lower for t in terms):
                results.append(f"[{name}:{i+1}] {line.strip()[:300]}")
                if len(results) >= max_results:
                    break
        if len(results) >= max_results:
            break

    if not results:
        return f"No memory matches for '{query}'"
    return "\n".join(results)


def _memory_save(workspace: Path, category: str, content: str) -> str:
    """Append content to a memory file."""
    _ensure_dir(workspace)
    rel_path = MEMORY_FILES.get(category)
    if not rel_path:
        available = ", ".join(MEMORY_FILES.keys())
        return f"Error: unknown category '{category}'. Available: {available}"

    fp = workspace / rel_path
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    entry = f"\n\n## [{timestamp}]\n{content}\n"

    with open(fp, "a", encoding="utf-8") as f:
        f.write(entry)

    logger.info(f"Memory saved to {category}: {content[:80]}...")
    return f"Saved to {category} ({fp.stat().st_size} bytes total)"


def _memory_get(workspace: Path, category: str, line_start: int = 0, line_end: int = 0) -> str:
    """Read a specific memory file, optionally specific lines."""
    rel_path = MEMORY_FILES.get(category)
    if not rel_path:
        available = ", ".join(MEMORY_FILES.keys())
        return f"Error: unknown category '{category}'. Available: {available}"

    fp = workspace / rel_path
    if not fp.exists():
        return f"Memory file '{category}' is empty (not yet created)"

    content = fp.read_text(encoding="utf-8", errors="replace")
    if line_start > 0:
        lines = content.splitlines()
        end = line_end if line_end > 0 else len(lines)
        return "\n".join(lines[line_start-1:end])
    return content


def _memory_list(workspace: Path) -> str:
    """List all memory files with sizes."""
    _ensure_dir(workspace)
    lines = ["Memory files:"]
    for name, rel_path in MEMORY_FILES.items():
        fp = workspace / rel_path
        if fp.exists():
            size = fp.stat().st_size
            line_count = len(fp.read_text(encoding="utf-8", errors="replace").splitlines())
            lines.append(f"  {name}: {rel_path} ({size}b, {line_count} lines)")
        else:
            lines.append(f"  {name}: {rel_path} (not created)")
    return "\n".join(lines)


def get_tools(workspace_dir: Path) -> List[Tool]:
    """Register memory tools."""
    ws = Path(workspace_dir).resolve()

    return [
        Tool(
            name="memory_search",
            description="Search across all memory files for information.",
            category="memory",
            params=[
                ToolParam("query", "string", "Search query"),
                ToolParam("max_results", "integer", "Max results", required=False, default=20),
            ],
            handler=lambda query, max_results=20: _memory_search(ws, query, int(max_results)),
        ),
        Tool(
            name="memory_save",
            description="Save information to persistent memory. Categories: main, decisions, contacts, learnings, constitution, strategy.",
            category="memory",
            params=[
                ToolParam("category", "string", "Memory category (main, decisions, contacts, learnings, constitution, strategy)"),
                ToolParam("content", "string", "Content to save"),
            ],
            handler=lambda category, content: _memory_save(ws, category, content),
        ),
        Tool(
            name="memory_get",
            description="Read a memory file. Optionally specify line range.",
            category="memory",
            params=[
                ToolParam("category", "string", "Memory category"),
                ToolParam("line_start", "integer", "Start line (0=all)", required=False, default=0),
                ToolParam("line_end", "integer", "End line (0=end)", required=False, default=0),
            ],
            handler=lambda category, line_start=0, line_end=0: _memory_get(ws, category, int(line_start), int(line_end)),
        ),
        Tool(
            name="memory_list",
            description="List all memory files with sizes.",
            category="memory",
            params=[],
            handler=lambda: _memory_list(ws),
        ),
    ]
