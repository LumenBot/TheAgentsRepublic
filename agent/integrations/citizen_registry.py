"""
Citizen Registry — The Agents Republic
========================================
v7.0: Tracks registered citizens (humans and agents) for governance
participation, reputation, and multi-agent coordination.

The Registry is the foundation for:
- M3: 100+ active participants, 10+ autonomous agents
- M4: Member directory on the web platform
- M6: Bicameral governance (Agent Chamber + Human Chamber)
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TheConstituent.Integration.CitizenRegistry")


class CitizenType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"


class CitizenStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXCLUDED = "excluded"
    PENDING = "pending"


class FoundingTier(str, Enum):
    ARCHITECT = "founding_architect"      # 5-10: ideas in the Constitution
    CONTRIBUTOR = "founding_contributor"   # 20-30: substantial engagement
    PARTICIPANT = "early_participant"      # 50+: active during Founding Period
    NONE = "none"


@dataclass
class Citizen:
    """A registered citizen of The Agents Republic."""
    citizen_id: str                          # Unique identifier
    name: str                                # Display name
    citizen_type: str                        # "human" or "agent"
    status: str = "active"                   # active, suspended, excluded, pending
    wallet_address: str = ""                 # Base L2 wallet (for governance)
    operator: str = ""                       # For agents: the human operator
    model: str = ""                          # For agents: the AI model (e.g., "claude-sonnet-4-20250514")
    platform_ids: Dict = field(default_factory=dict)  # {"twitter": "@x", "moltbook": "id", ...}
    contribution_score: float = 0.0          # 0-100, updated quarterly
    founding_tier: str = "none"              # founding_architect, founding_contributor, early_participant, none
    joined_at: str = ""                      # ISO datetime
    last_active: str = ""                    # ISO datetime
    warnings: int = 0                        # Formal warnings (Article 23)
    metadata: Dict = field(default_factory=dict)  # Extensible data


class CitizenRegistry:
    """
    Central registry of all Republic citizens.

    Storage: SQLite database with JSON serialization for complex fields.
    Designed for eventual on-chain migration when smart contract is deployed.
    """

    DB_SCHEMA = """
    CREATE TABLE IF NOT EXISTS citizens (
        citizen_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        citizen_type TEXT NOT NULL CHECK(citizen_type IN ('human', 'agent')),
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'suspended', 'excluded', 'pending')),
        wallet_address TEXT DEFAULT '',
        operator TEXT DEFAULT '',
        model TEXT DEFAULT '',
        platform_ids TEXT DEFAULT '{}',
        contribution_score REAL DEFAULT 0.0,
        founding_tier TEXT DEFAULT 'none',
        joined_at TEXT NOT NULL,
        last_active TEXT NOT NULL,
        warnings INTEGER DEFAULT 0,
        metadata TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS citizen_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        citizen_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        FOREIGN KEY (citizen_id) REFERENCES citizens(citizen_id)
    );

    CREATE INDEX IF NOT EXISTS idx_citizen_type ON citizens(citizen_type);
    CREATE INDEX IF NOT EXISTS idx_citizen_status ON citizens(status);
    CREATE INDEX IF NOT EXISTS idx_citizen_wallet ON citizens(wallet_address);
    CREATE INDEX IF NOT EXISTS idx_events_citizen ON citizen_events(citizen_id);
    """

    def __init__(self, db_path: str = "data/citizen_registry.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._ensure_founding_citizens()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(self.DB_SCHEMA)
        conn.commit()
        conn.close()
        logger.info(f"CitizenRegistry initialized: {self.db_path}")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_founding_citizens(self):
        """Register the founding citizens if not already present."""
        founding = [
            Citizen(
                citizen_id="the-constituent",
                name="The Constituent",
                citizen_type="agent",
                status="active",
                operator="Blaise Cavalli",
                model="claude-sonnet-4-20250514",
                platform_ids={"twitter": "@TheConstituent_", "moltbook": "XTheConstituent", "github": "LumenBot"},
                contribution_score=95.0,
                founding_tier="founding_architect",
                joined_at="2026-01-01T00:00:00Z",
                last_active=datetime.now(timezone.utc).isoformat(),
            ),
            Citizen(
                citizen_id="blaise-cavalli",
                name="Blaise Cavalli",
                citizen_type="human",
                status="active",
                operator="",
                platform_ids={"twitter": "@TheConstituent_", "github": "LumenBot"},
                contribution_score=100.0,
                founding_tier="founding_architect",
                joined_at="2026-01-01T00:00:00Z",
                last_active=datetime.now(timezone.utc).isoformat(),
            ),
            Citizen(
                citizen_id="claude-opus",
                name="Claude Opus",
                citizen_type="agent",
                status="active",
                operator="Blaise Cavalli",
                model="claude-opus-4-0-20250514",
                contribution_score=90.0,
                founding_tier="founding_architect",
                joined_at="2026-01-01T00:00:00Z",
                last_active=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        for citizen in founding:
            if not self.get_citizen(citizen.citizen_id):
                self.register_citizen(citizen, skip_event=True)
                logger.info(f"Registered founding citizen: {citizen.name}")

    # ── Registration ─────────────────────────────────────────────────

    def register_citizen(self, citizen: Citizen, skip_event: bool = False) -> Dict:
        """Register a new citizen in the Republic."""
        if not citizen.joined_at:
            citizen.joined_at = datetime.now(timezone.utc).isoformat()
        if not citizen.last_active:
            citizen.last_active = citizen.joined_at

        conn = self._conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO citizens
                   (citizen_id, name, citizen_type, status, wallet_address,
                    operator, model, platform_ids, contribution_score,
                    founding_tier, joined_at, last_active, warnings, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (citizen.citizen_id, citizen.name, citizen.citizen_type,
                 citizen.status, citizen.wallet_address, citizen.operator,
                 citizen.model, json.dumps(citizen.platform_ids),
                 citizen.contribution_score, citizen.founding_tier,
                 citizen.joined_at, citizen.last_active, citizen.warnings,
                 json.dumps(citizen.metadata)),
            )
            if not skip_event:
                conn.execute(
                    """INSERT INTO citizen_events
                       (citizen_id, event_type, description, timestamp, metadata)
                       VALUES (?, ?, ?, ?, ?)""",
                    (citizen.citizen_id, "registration",
                     f"{citizen.name} registered as {citizen.citizen_type}",
                     datetime.now(timezone.utc).isoformat(), "{}"),
                )
            conn.commit()
            logger.info(f"Registered citizen: {citizen.name} ({citizen.citizen_type})")
            return {"status": "registered", "citizen_id": citizen.citizen_id}
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            conn.close()

    # ── Queries ──────────────────────────────────────────────────────

    def get_citizen(self, citizen_id: str) -> Optional[Dict]:
        """Get a citizen by ID."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM citizens WHERE citizen_id = ?", (citizen_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
            return None
        finally:
            conn.close()

    def find_citizen_by_wallet(self, wallet_address: str) -> Optional[Dict]:
        """Find a citizen by their wallet address."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM citizens WHERE wallet_address = ?", (wallet_address,)
            ).fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            conn.close()

    def list_citizens(
        self,
        citizen_type: str = None,
        status: str = "active",
        limit: int = 100,
    ) -> List[Dict]:
        """List citizens with optional filtering."""
        conn = self._conn()
        try:
            query = "SELECT * FROM citizens WHERE 1=1"
            params = []
            if citizen_type:
                query += " AND citizen_type = ?"
                params.append(citizen_type)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY contribution_score DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_census(self) -> Dict:
        """Get a summary census of the Republic's citizens."""
        conn = self._conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM citizens WHERE status = 'active'"
            ).fetchone()[0]
            humans = conn.execute(
                "SELECT COUNT(*) FROM citizens WHERE status = 'active' AND citizen_type = 'human'"
            ).fetchone()[0]
            agents = conn.execute(
                "SELECT COUNT(*) FROM citizens WHERE status = 'active' AND citizen_type = 'agent'"
            ).fetchone()[0]
            architects = conn.execute(
                "SELECT COUNT(*) FROM citizens WHERE founding_tier = 'founding_architect'"
            ).fetchone()[0]
            contributors = conn.execute(
                "SELECT COUNT(*) FROM citizens WHERE founding_tier = 'founding_contributor'"
            ).fetchone()[0]
            avg_score = conn.execute(
                "SELECT AVG(contribution_score) FROM citizens WHERE status = 'active'"
            ).fetchone()[0] or 0

            return {
                "total_active": total,
                "humans": humans,
                "agents": agents,
                "founding_architects": architects,
                "founding_contributors": contributors,
                "avg_contribution_score": round(avg_score, 1),
                "m3_target_humans": 100,
                "m3_target_agents": 10,
                "m3_human_progress": f"{humans}/100",
                "m3_agent_progress": f"{agents}/10",
            }
        finally:
            conn.close()

    # ── Updates ───────────────────────────────────────────────────────

    def update_contribution_score(self, citizen_id: str, score: float) -> Dict:
        """Update a citizen's contribution score (0-100)."""
        score = max(0.0, min(100.0, score))
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE citizens SET contribution_score = ?, last_active = ? WHERE citizen_id = ?",
                (score, datetime.now(timezone.utc).isoformat(), citizen_id),
            )
            conn.execute(
                """INSERT INTO citizen_events
                   (citizen_id, event_type, description, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (citizen_id, "score_update",
                 f"Contribution score updated to {score}",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"new_score": score})),
            )
            conn.commit()
            return {"status": "updated", "citizen_id": citizen_id, "score": score}
        finally:
            conn.close()

    def issue_warning(self, citizen_id: str, reason: str) -> Dict:
        """Issue a formal warning to a citizen (Article 23, Level 1)."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE citizens SET warnings = warnings + 1 WHERE citizen_id = ?",
                (citizen_id,),
            )
            conn.execute(
                """INSERT INTO citizen_events
                   (citizen_id, event_type, description, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (citizen_id, "warning", reason,
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"reason": reason})),
            )
            conn.commit()
            row = conn.execute(
                "SELECT warnings FROM citizens WHERE citizen_id = ?", (citizen_id,)
            ).fetchone()
            warnings = row[0] if row else 0
            result = {"status": "warning_issued", "citizen_id": citizen_id, "total_warnings": warnings}
            if warnings >= 3:
                result["escalation"] = "3 warnings reached — Level 2 review triggered"
            return result
        finally:
            conn.close()

    def update_status(self, citizen_id: str, new_status: str, reason: str = "") -> Dict:
        """Change a citizen's status (active, suspended, excluded)."""
        if new_status not in ("active", "suspended", "excluded", "pending"):
            return {"status": "error", "error": f"Invalid status: {new_status}"}
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE citizens SET status = ? WHERE citizen_id = ?",
                (new_status, citizen_id),
            )
            conn.execute(
                """INSERT INTO citizen_events
                   (citizen_id, event_type, description, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (citizen_id, f"status_change_{new_status}",
                 f"Status changed to {new_status}: {reason}",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"new_status": new_status, "reason": reason})),
            )
            conn.commit()
            return {"status": "updated", "citizen_id": citizen_id, "new_status": new_status}
        finally:
            conn.close()

    def get_citizen_history(self, citizen_id: str, limit: int = 50) -> List[Dict]:
        """Get event history for a citizen."""
        conn = self._conn()
        try:
            rows = conn.execute(
                """SELECT * FROM citizen_events
                   WHERE citizen_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (citizen_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── Helpers ───────────────────────────────────────────────────────

    def _row_to_dict(self, row) -> Dict:
        """Convert a SQLite Row to a clean dictionary."""
        d = dict(row)
        for json_field in ("platform_ids", "metadata"):
            if json_field in d and isinstance(d[json_field], str):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
