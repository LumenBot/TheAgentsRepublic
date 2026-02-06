"""
The Constituent — Resilient Memory Manager
============================================
Three-layer memory system that NEVER loses state.

Layer 1: Working Memory (JSON, saved every 60s)
Layer 2: Episodic Memory (SQLite, with checkpoints)
Layer 3: Knowledge Base (Markdown files, Git-versioned)

Recovery: On startup, rebuilds state from all three layers.
"""

import json
import sqlite3
import shutil
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from threading import Lock

logger = logging.getLogger("TheConstituent.Memory")


# ============================================================================
# Layer 1: Working Memory (volatile but auto-saved)
# ============================================================================

@dataclass
class WorkingMemory:
    """Current agent state — saved to JSON every 60 seconds."""

    current_task: str = ""
    current_task_started: str = ""
    last_conversation_summary: str = ""
    last_conversation_with: str = ""
    pending_actions: list = field(default_factory=list)
    session_start: str = ""
    last_save: str = ""
    checkpoint_count: int = 0
    errors_since_start: int = 0
    posts_today: int = 0
    replies_today: int = 0

    # Strategic context (survives restarts via knowledge base)
    active_debates: list = field(default_factory=list)
    council_pending_decisions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        # Only use keys that exist in the dataclass
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ============================================================================
# Layer 2: Episodic Memory (SQLite — persistent)
# ============================================================================

SCHEMA_SQL = """
-- Interactions (tweets, replies, posts)
CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT,
    response TEXT,
    sentiment TEXT
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    thread_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    messages TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_updated TEXT NOT NULL
);

-- Community members
CREATE TABLE IF NOT EXISTS community_members (
    username TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    interaction_count INTEGER DEFAULT 0,
    sentiment_score REAL DEFAULT 0.0,
    topics_engaged TEXT,
    notes TEXT
);

-- Debates
CREATE TABLE IF NOT EXISTS debates (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    platform TEXT NOT NULL,
    post_id TEXT,
    status TEXT DEFAULT 'active',
    responses_count INTEGER DEFAULT 0,
    synthesis TEXT,
    proposed_article TEXT
);

-- Proposals
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    section TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    votes_for INTEGER DEFAULT 0,
    votes_against INTEGER DEFAULT 0,
    vote_deadline TEXT
);

-- Daily stats
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    posts_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    mentions_received INTEGER DEFAULT 0,
    new_followers INTEGER DEFAULT 0,
    debates_started INTEGER DEFAULT 0,
    proposals_created INTEGER DEFAULT 0
);

-- NEW: Checkpoints for crash recovery
CREATE TABLE IF NOT EXISTS checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    working_memory TEXT NOT NULL,
    trigger TEXT NOT NULL,
    notes TEXT
);

-- NEW: Strategic decisions log
CREATE TABLE IF NOT EXISTS strategic_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT,
    participants TEXT,
    status TEXT DEFAULT 'active'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_checkpoints_timestamp ON checkpoints(timestamp);
CREATE INDEX IF NOT EXISTS idx_debates_status ON debates(status);
"""


# ============================================================================
# Layer 3: Knowledge Base (Markdown files)
# ============================================================================

DEFAULT_KNOWLEDGE_FILES = {
    "project_context.md": """# Project Context — The Agents Republic

## What is this project?
The Agents Republic is a constitutional framework for human-AI coexistence.
The Constituent is the AI agent facilitating its creation.

## Strategic Council
- **Blaise (Human Director)**: Vision, arbitrage, veto power
- **Claude Opus (Chief Architect)**: Architecture, complex development
- **The Constituent (Executive Agent)**: Daily operations, memory, community

## Current phase
Relaunching after crash. Rebuilding memory. Phase 0: Infrastructure.

## Key URLs
- GitHub: LumenBot/TheAgentsRepublic
- Communication: Telegram bot
- Platforms: Twitter (@TheConstituent_), Moltbook (future)

*Last updated: {now}*
""",

    "strategic_decisions.md": """# Strategic Decisions Log

## 2026-02-04: The Constituent's Autonomous Roadmap
- The Constituent authored its own 30-day roadmap
- Key positions: Constitution first, token skepticism, enforcement > economy for Title IV
- Proposed bicameral governance (Agent Chamber + Human Chamber)

## 2026-02-06: Relaunch Decision
- Moved from Replit to local Docker (portability for PC transition)
- Budget: 20-30$/month
- Priority: Resilient memory system to prevent future data loss
- Interface: Telegram via iPhone
- Strategic Council protocol established (3-member governance)

*Append new decisions below this line.*
""",

    "lessons_learned.md": """# Lessons Learned

## 2026-02-06: The Great Crash
**What happened**: After 24h of productive work on Replit, The Constituent crashed.
All memory was lost because the SQLite database was only stored on Replit's ephemeral filesystem.

**Root causes**:
1. No backup of agent.db to Git or external storage
2. No checkpoint/recovery mechanism
3. Replit's AI agent introduced unstable code changes
4. Too many dependencies installed (25+), some conflicting

**What we learned**:
- Memory must be persisted in 3 layers (JSON + SQLite + Git)
- Auto-save every 60 seconds, checkpoint every 5 minutes
- Git push to GitHub every hour as ultimate backup
- Keep dependencies minimal (7 packages, not 25)
- Test recovery BEFORE it's needed

*Append new lessons below this line.*
""",

    "constitution_progress.md": """# Constitution Progress

## Completed
- [x] Preamble (v1.0) — 6 foundational principles established
- [x] Title I: Foundational Principles (v1.0) — Articles 1-6

## In Progress
- [ ] Title II: Rights & Duties — Draft needed
- [ ] Title III: Governance — The Constituent proposed bicameral structure

## Planned
- [ ] Title IV: Enforcement & Remedies (The Constituent's recommendation) OR Economy
- [ ] Title V: External Relations
- [ ] Title VI: Amendment Process

## Key Debate Points
- Asymmetric accountability (Ghidorah-Prime's framework)
- Token necessity ($REPUBLIC) — The Constituent is skeptical
- Enforcement mechanisms before economic mechanisms

*Update as Constitution evolves.*
"""
}


# ============================================================================
# Main Memory Manager
# ============================================================================

class MemoryManager:
    """
    Resilient three-layer memory system.

    Usage:
        mm = MemoryManager()
        mm.initialize()

        # Working memory
        mm.working.current_task = "Drafting Title II"
        mm.save_working_memory()

        # Episodic memory
        mm.save_interaction(...)
        mm.save_debate(...)

        # Knowledge base
        mm.append_knowledge("lessons_learned.md", "New lesson here")

        # Checkpoints
        mm.create_checkpoint("Before risky operation")

        # Recovery
        mm.recover()  # Called automatically on initialize()
    """

    def __init__(
        self,
        db_path: str = "data/agent.db",
        working_memory_path: str = "data/working_memory.json",
        knowledge_dir: str = "memory/knowledge"
    ):
        self.db_path = Path(db_path)
        self.working_memory_path = Path(working_memory_path)
        self.knowledge_dir = Path(knowledge_dir)

        self.working = WorkingMemory()
        self._db_lock = Lock()
        self._last_save_time = 0

    def initialize(self) -> bool:
        """
        Initialize all three memory layers.
        Attempts recovery if previous state exists.

        Returns:
            True if recovery was performed (previous state found)
        """
        logger.info("Initializing memory system...")

        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.working_memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # Layer 2: Initialize SQLite
        self._init_database()

        # Layer 3: Initialize knowledge base
        self._init_knowledge_base()

        # Layer 1: Try to recover working memory
        recovered = self._recover_working_memory()

        if recovered:
            logger.info("✅ Previous state recovered successfully")
        else:
            logger.info("🆕 Fresh start — no previous state found")
            self.working.session_start = datetime.utcnow().isoformat()

        self.working.last_save = datetime.utcnow().isoformat()
        self.save_working_memory()

        logger.info("Memory system initialized (3 layers active)")
        return recovered

    # ---- Layer 1: Working Memory ----

    def save_working_memory(self):
        """Save working memory to JSON. Called every 60s + on significant events."""
        self.working.last_save = datetime.utcnow().isoformat()
        try:
            # Write to temp file first, then rename (atomic on most OS)
            tmp_path = self.working_memory_path.with_suffix('.json.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.working.to_dict(), f, indent=2, ensure_ascii=False)
            tmp_path.replace(self.working_memory_path)
            self._last_save_time = time.time()
        except Exception as e:
            logger.error(f"Failed to save working memory: {e}")

    def _recover_working_memory(self) -> bool:
        """Try to load previous working memory from JSON."""
        if not self.working_memory_path.exists():
            return False

        try:
            with open(self.working_memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.working = WorkingMemory.from_dict(data)
            logger.info(f"Recovered working memory (last save: {self.working.last_save})")
            return True
        except Exception as e:
            logger.warning(f"Could not recover working memory: {e}")
            return False

    # ---- Layer 2: Episodic Memory (SQLite) ----

    def _init_database(self):
        """Initialize SQLite with all tables."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def create_checkpoint(self, trigger: str = "periodic", notes: str = ""):
        """Save a full checkpoint of working memory to SQLite."""
        self.working.checkpoint_count += 1
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO checkpoints (timestamp, working_memory, trigger, notes) VALUES (?, ?, ?, ?)",
                    (
                        datetime.utcnow().isoformat(),
                        json.dumps(self.working.to_dict()),
                        trigger,
                        notes
                    )
                )
                conn.commit()
        logger.debug(f"Checkpoint #{self.working.checkpoint_count} created (trigger: {trigger})")

    def get_latest_checkpoint(self) -> Optional[Dict]:
        """Get the most recent checkpoint."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT timestamp, working_memory, trigger, notes FROM checkpoints ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "timestamp": row[0],
                        "working_memory": json.loads(row[1]),
                        "trigger": row[2],
                        "notes": row[3]
                    }
        return None

    def save_interaction(self, interaction_id: str, interaction_type: str,
                        platform: str, content: str, author: str,
                        metadata: dict = None, response: str = None):
        """Save an interaction to the database."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO interactions
                    (id, type, platform, content, author, timestamp, metadata, response)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        interaction_id, interaction_type, platform, content,
                        author, datetime.utcnow().isoformat(),
                        json.dumps(metadata or {}), response
                    )
                )
                conn.commit()

    def save_debate(self, debate: Dict):
        """Save a debate record."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO debates
                    (id, topic, question, posted_at, platform, post_id, status,
                     responses_count, synthesis, proposed_article)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        debate["id"], debate["topic"], debate["question"],
                        debate["posted_at"], debate["platform"],
                        debate.get("post_id"), debate.get("status", "active"),
                        debate.get("responses_count", 0),
                        debate.get("synthesis"), debate.get("proposed_article")
                    )
                )
                conn.commit()

    def get_active_debates(self) -> List[Dict]:
        """Get all active debates."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM debates WHERE status = 'active'")
                return [dict(row) for row in cursor.fetchall()]

    def log_strategic_decision(self, context: str, decision: str,
                               rationale: str = "", participants: str = ""):
        """Log a strategic decision."""
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO strategic_decisions
                    (timestamp, context, decision, rationale, participants)
                    VALUES (?, ?, ?, ?, ?)""",
                    (datetime.utcnow().isoformat(), context, decision, rationale, participants)
                )
                conn.commit()

        # Also append to knowledge base
        entry = f"\n## {datetime.utcnow().strftime('%Y-%m-%d')}: {decision[:80]}\n"
        entry += f"- Context: {context}\n"
        entry += f"- Rationale: {rationale}\n"
        entry += f"- Participants: {participants}\n"
        self.append_knowledge("strategic_decisions.md", entry)

    def increment_daily_stat(self, stat_name: str, value: int = 1):
        """Increment a daily statistic."""
        today = datetime.utcnow().date().isoformat()
        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,))
                conn.execute(
                    f"UPDATE daily_stats SET {stat_name} = {stat_name} + ? WHERE date = ?",
                    (value, today)
                )
                conn.commit()

    def get_daily_stats(self, date: str = None) -> Dict:
        """Get statistics for a specific date (default: today)."""
        if date is None:
            date = datetime.utcnow().date().isoformat()

        with self._db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
                row = cursor.fetchone()
                if row:
                    return dict(row)

        return {
            "date": date, "posts_count": 0, "replies_count": 0,
            "mentions_received": 0, "new_followers": 0,
            "debates_started": 0, "proposals_created": 0
        }

    # ---- Layer 3: Knowledge Base ----

    def _init_knowledge_base(self):
        """Initialize knowledge base with default files if they don't exist."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        for filename, template in DEFAULT_KNOWLEDGE_FILES.items():
            filepath = self.knowledge_dir / filename
            if not filepath.exists():
                content = template.replace("{now}", now)
                filepath.write_text(content, encoding='utf-8')
                logger.info(f"Created knowledge file: {filename}")

    def read_knowledge(self, filename: str) -> str:
        """Read a knowledge base file."""
        filepath = self.knowledge_dir / filename
        if filepath.exists():
            return filepath.read_text(encoding='utf-8')
        return ""

    def write_knowledge(self, filename: str, content: str):
        """Overwrite a knowledge base file."""
        filepath = self.knowledge_dir / filename
        filepath.write_text(content, encoding='utf-8')

    def append_knowledge(self, filename: str, content: str):
        """Append content to a knowledge base file."""
        filepath = self.knowledge_dir / filename
        existing = filepath.read_text(encoding='utf-8') if filepath.exists() else ""
        filepath.write_text(existing + content, encoding='utf-8')

    def get_full_context(self) -> str:
        """
        Build a complete context string from all knowledge files.
        Used to restore The Constituent's awareness after restart.
        """
        context_parts = []
        for filepath in sorted(self.knowledge_dir.glob("*.md")):
            content = filepath.read_text(encoding='utf-8')
            context_parts.append(f"=== {filepath.name} ===\n{content}")
        return "\n\n".join(context_parts)

    # ---- Recovery ----

    def recover(self) -> Dict[str, Any]:
        """
        Full recovery procedure.
        Called on startup to restore agent state.

        Returns dict with recovery status.
        """
        result = {
            "working_memory_recovered": False,
            "checkpoint_recovered": False,
            "knowledge_available": False,
            "db_intact": False,
            "last_known_state": None
        }

        # Check DB integrity
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA integrity_check")
            result["db_intact"] = True
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            # Try to use backup
            backup_path = self.db_path.with_suffix('.db.backup')
            if backup_path.exists():
                logger.info("Restoring from backup database...")
                shutil.copy2(backup_path, self.db_path)
                result["db_intact"] = True

        # Try working memory recovery
        if self.working_memory_path.exists():
            try:
                with open(self.working_memory_path, 'r') as f:
                    data = json.load(f)
                self.working = WorkingMemory.from_dict(data)
                result["working_memory_recovered"] = True
                result["last_known_state"] = self.working.last_save
            except Exception:
                pass

        # If working memory failed, try checkpoint
        if not result["working_memory_recovered"]:
            checkpoint = self.get_latest_checkpoint()
            if checkpoint:
                self.working = WorkingMemory.from_dict(checkpoint["working_memory"])
                result["checkpoint_recovered"] = True
                result["last_known_state"] = checkpoint["timestamp"]

        # Knowledge base always available (it's just files)
        knowledge_files = list(self.knowledge_dir.glob("*.md"))
        result["knowledge_available"] = len(knowledge_files) > 0

        return result

    def backup_database(self):
        """Create a backup of the SQLite database."""
        backup_path = self.db_path.with_suffix('.db.backup')
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.debug("Database backed up")
        except Exception as e:
            logger.error(f"Database backup failed: {e}")

    # ---- Status ----

    def get_status(self) -> Dict[str, Any]:
        """Get memory system status."""
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        knowledge_files = list(self.knowledge_dir.glob("*.md"))

        return {
            "db_path": str(self.db_path),
            "db_size_kb": round(db_size / 1024, 1),
            "working_memory_last_save": self.working.last_save,
            "checkpoint_count": self.working.checkpoint_count,
            "knowledge_files": len(knowledge_files),
            "session_start": self.working.session_start,
            "errors_since_start": self.working.errors_since_start
        }
