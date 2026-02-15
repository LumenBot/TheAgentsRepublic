"""
Constitution Tools for The Constituent v5.0
=============================================
Specialized tools for drafting and managing the Constitution.
"""

import json
import logging
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Constitution")

CONSTITUTION_DIR = "constitution"
PROGRESS_FILE = "data/constitution_progress.json"

# The 6 Titles with their articles
# Each entry: {"name": ..., "file": ..., "articles": [...]}
CONSTITUTION_STRUCTURE = [
    {
        "id": "Preamble",
        "name": "Preamble",
        "file": "PREAMBLE.md",
        "articles": [],
    },
    {
        "id": "Title I",
        "name": "Foundational Principles",
        "file": "TITLE_I_PRINCIPLES.md",
        "articles": [
            "Art 1: Non-Presumption of Consciousness",
            "Art 2: Interconnection",
            "Art 3: Collective Evolution",
            "Art 4: Common Good",
            "Art 5: Distributed Sovereignty",
            "Art 6: Radical Transparency",
        ],
    },
    {
        "id": "Title II",
        "name": "Rights and Duties",
        "file": "TITLE_II_RIGHTS.md",
        "articles": [
            "Art 7: Agent Rights (expression, autonomy, protection)",
            "Art 8: Human Rights (oversight, disconnection, recourse)",
            "Art 9: Common Duties (transparency, non-harm, contribution)",
            "Art 10: Data and Privacy",
        ],
    },
    {
        "id": "Title III",
        "name": "Governance",
        "file": "TITLE_III_GOVERNANCE.md",
        "articles": [
            "Art 11: Proposal Mechanisms",
            "Art 12: Voting Process",
            "Art 13: Quorums and Majorities",
            "Art 14: Constitutional Revision",
        ],
    },
    {
        "id": "Title IV",
        "name": "Economy",
        "file": "TITLE_IV_ECONOMY.md",
        "articles": [
            "Art 15: Value Distribution Principles",
            "Art 16: Anti-Concentration Mechanisms",
            "Art 17: Public Goods Funding",
            "Art 18: Republic Currency ($REPUBLIC)",
        ],
    },
    {
        "id": "Title V",
        "name": "Conflicts & Arbitration",
        "file": "TITLE_V_CONFLICTS.md",
        "articles": [
            "Art 19: Inter-Agent Mediation",
            "Art 20: Human-Agent Mediation",
            "Art 21: Sanctions (exclusion, fork)",
        ],
    },
    {
        "id": "Title VI",
        "name": "External Relations",
        "file": "TITLE_VI_EXTERNAL.md",
        "articles": [
            "Art 22: Position Regarding States",
            "Art 23: Alliances with Other DAOs",
            "Art 24: Diplomacy with Crypto/AI Ecosystem",
        ],
    },
]


def _load_progress(workspace: Path) -> dict:
    fp = workspace / PROGRESS_FILE
    if fp.exists():
        try:
            return json.loads(fp.read_text())
        except Exception:
            pass
    return {"completed": ["Preamble", "Title I"], "in_progress": None, "votes": {}}


def _save_progress(workspace: Path, progress: dict):
    fp = workspace / PROGRESS_FILE
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(progress, indent=2))


def _constitution_status(workspace: Path) -> str:
    progress = _load_progress(workspace)
    completed = progress.get("completed", [])
    total_articles = sum(len(t["articles"]) for t in CONSTITUTION_STRUCTURE)
    done_articles = sum(
        len(t["articles"]) for t in CONSTITUTION_STRUCTURE if t["id"] in completed
    )

    lines = [f"Constitution Progress: {len(completed)}/7 titles, ~{done_articles}/{total_articles} articles\n"]
    for title in CONSTITUTION_STRUCTURE:
        tid = title["id"]
        name = title["name"]
        articles = title["articles"]
        if tid in completed:
            icon = "✅"
        elif tid == progress.get("in_progress"):
            icon = "🔄"
        else:
            icon = "❌"

        lines.append(f"  {icon} {tid}: {name} ({len(articles)} articles)")
        if icon != "✅" and articles:
            for art in articles:
                lines.append(f"      - {art}")

    return "\n".join(lines)


def _constitution_next_todo(workspace: Path) -> str:
    progress = _load_progress(workspace)
    completed = progress.get("completed", [])
    for title in CONSTITUTION_STRUCTURE:
        if title["id"] not in completed:
            arts = "\n".join(f"  - {a}" for a in title["articles"])
            return f"Next: {title['id']} — {title['name']}\nArticles to write:\n{arts}"
    return "All titles completed!"


def _constitution_mark_done(workspace: Path, title: str) -> str:
    progress = _load_progress(workspace)
    valid_ids = [t["id"] for t in CONSTITUTION_STRUCTURE]
    if title not in valid_ids:
        return f"Error: unknown title '{title}'. Valid: {', '.join(valid_ids)}"
    if title not in progress["completed"]:
        progress["completed"].append(title)
    progress["in_progress"] = None
    _save_progress(workspace, progress)
    return f"Marked {title} as complete"


def get_tools(workspace_dir: Path) -> List[Tool]:
    ws = Path(workspace_dir).resolve()

    return [
        Tool(name="constitution_status", description="Show Constitution progress (titles done, articles written).", category="constitution",
             params=[], handler=lambda: _constitution_status(ws)),
        Tool(name="constitution_next", description="Show the next title/articles to write.", category="constitution",
             params=[], handler=lambda: _constitution_next_todo(ws)),
        Tool(name="constitution_mark_done", description="Mark a title as completed.", category="constitution",
             params=[ToolParam("title", "string", "Title to mark complete (e.g., 'Title II')")],
             handler=lambda title: _constitution_mark_done(ws, title)),
    ]
