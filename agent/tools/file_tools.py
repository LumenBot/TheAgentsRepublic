"""
File Tools for The Constituent v5.0
=====================================
Read, write, edit, search, and list files in workspace.
Inspired by OpenClaw read/write/edit/grep/find/ls tools.
"""

import os
import re
import logging
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.File")


def _safe_path(workspace: Path, path_str: str) -> Path:
    """Resolve path safely within workspace. Prevent path traversal."""
    resolved = (workspace / path_str).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise ValueError(f"Path traversal blocked: {path_str}")
    return resolved


def _file_read(workspace: Path, path: str, line_start: int = 0, line_end: int = 0) -> str:
    fp = _safe_path(workspace, path)
    if not fp.exists():
        return f"Error: file not found: {path}"
    content = fp.read_text(encoding="utf-8", errors="replace")
    if line_start > 0:
        lines = content.splitlines()
        end = line_end if line_end > 0 else len(lines)
        return "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines[line_start-1:end]))
    return content


def _file_write(workspace: Path, path: str, content: str) -> str:
    fp = _safe_path(workspace, path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    size = fp.stat().st_size
    logger.info(f"Wrote {path} ({size} bytes)")
    return f"Written: {path} ({size} bytes)"


def _file_edit(workspace: Path, path: str, old_str: str, new_str: str) -> str:
    fp = _safe_path(workspace, path)
    if not fp.exists():
        return f"Error: file not found: {path}"
    content = fp.read_text(encoding="utf-8")
    count = content.count(old_str)
    if count == 0:
        return f"Error: string not found in {path}"
    if count > 1:
        return f"Error: string appears {count} times in {path} (must be unique)"
    new_content = content.replace(old_str, new_str, 1)
    fp.write_text(new_content, encoding="utf-8")
    return f"Edited {path}: replaced 1 occurrence"


def _file_grep(workspace: Path, pattern: str, path: str = ".", max_results: int = 50) -> str:
    search_dir = _safe_path(workspace, path)
    results = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    for fp in search_dir.rglob("*"):
        if not fp.is_file():
            continue
        if fp.suffix in (".pyc", ".db", ".json", ".sqlite"):
            continue
        if any(part.startswith(".") for part in fp.parts):
            continue
        try:
            for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines()):
                if regex.search(line):
                    rel = fp.relative_to(workspace)
                    results.append(f"{rel}:{i+1}: {line.strip()[:200]}")
                    if len(results) >= max_results:
                        return "\n".join(results) + f"\n... ({max_results} results shown)"
        except Exception:
            continue

    if not results:
        return f"No matches for '{pattern}' in {path}"
    return "\n".join(results)


def _file_list(workspace: Path, path: str = ".", depth: int = 2) -> str:
    target = _safe_path(workspace, path)
    if not target.exists():
        return f"Error: directory not found: {path}"
    if target.is_file():
        size = target.stat().st_size
        return f"{path} ({size} bytes)"

    lines = []
    for item in sorted(target.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            count = sum(1 for _ in item.rglob("*") if _.is_file())
            lines.append(f"📁 {item.name}/ ({count} files)")
            if depth > 1:
                for sub in sorted(item.iterdir())[:10]:
                    if sub.name.startswith("."):
                        continue
                    if sub.is_dir():
                        lines.append(f"  📁 {sub.name}/")
                    else:
                        lines.append(f"  📄 {sub.name} ({sub.stat().st_size}b)")
        else:
            lines.append(f"📄 {item.name} ({item.stat().st_size}b)")

    return "\n".join(lines) if lines else "(empty directory)"


def get_tools(workspace_dir: Path) -> List[Tool]:
    """Register all file tools."""
    ws = Path(workspace_dir).resolve()

    return [
        Tool(
            name="file_read",
            description="Read a file's contents. Supports line ranges.",
            category="files",
            params=[
                ToolParam("path", "string", "File path relative to workspace"),
                ToolParam("line_start", "integer", "Start line (1-indexed, 0=all)", required=False, default=0),
                ToolParam("line_end", "integer", "End line (0=end)", required=False, default=0),
            ],
            handler=lambda path, line_start=0, line_end=0: _file_read(ws, path, int(line_start), int(line_end)),
        ),
        Tool(
            name="file_write",
            description="Create or overwrite a file with content.",
            category="files",
            params=[
                ToolParam("path", "string", "File path relative to workspace"),
                ToolParam("content", "string", "File content to write"),
            ],
            handler=lambda path, content: _file_write(ws, path, content),
        ),
        Tool(
            name="file_edit",
            description="Replace a unique string in a file (surgical edit).",
            category="files",
            params=[
                ToolParam("path", "string", "File path relative to workspace"),
                ToolParam("old_str", "string", "Exact string to find (must be unique)"),
                ToolParam("new_str", "string", "Replacement string"),
            ],
            handler=lambda path, old_str, new_str: _file_edit(ws, path, old_str, new_str),
        ),
        Tool(
            name="file_grep",
            description="Search for a pattern in files (recursive).",
            category="files",
            params=[
                ToolParam("pattern", "string", "Search pattern (regex or plain text)"),
                ToolParam("path", "string", "Directory to search (default: workspace root)", required=False, default="."),
            ],
            handler=lambda pattern, path=".": _file_grep(ws, pattern, path),
        ),
        Tool(
            name="file_list",
            description="List directory contents with file sizes.",
            category="files",
            params=[
                ToolParam("path", "string", "Directory path (default: workspace root)", required=False, default="."),
            ],
            handler=lambda path=".": _file_list(ws, path),
        ),
    ]
