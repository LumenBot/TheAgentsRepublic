"""
Action Queue — Autonomy Engine for The Constituent v2.3
=========================================================
Implements the L1/L2/L3 governance model for agent autonomy.

v2.3 improvements:
- (C) Automatic retry with backoff for rate-limited actions (429)
- (E) Structured autonomous actions log (data/autonomous_actions_log.json)
- Retry queue with scheduled execution times
- Better error reporting with action context

Constitutional basis: Article 12, Title III (Governance)
"""

import json
import logging
import re
import operator as op_module
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("TheConstituent.ActionQueue")


class GovernanceLevel(Enum):
    L1_AUTONOMOUS = "L1"
    L2_CODECISION = "L2"
    L3_HUMAN_ONLY = "L3"


class ActionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RETRY_SCHEDULED = "retry_scheduled"


@dataclass
class Action:
    id: int
    action_type: str
    params: Dict[str, Any]
    level: str
    status: str = "pending"
    created_at: str = ""
    executed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_reason: Optional[str] = None
    retry_count: int = 0
    retry_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


# =========================================================================
# Governance Rules
# =========================================================================

GOVERNANCE_RULES: Dict[str, GovernanceLevel] = {
    # L1 — Autonomous
    "moltbook_read_feed":       GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_post":            GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_comment":         GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_upvote":          GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_verify":          GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_heartbeat":       GovernanceLevel.L1_AUTONOMOUS,
    "moltbook_search":          GovernanceLevel.L1_AUTONOMOUS,
    "save_state":               GovernanceLevel.L1_AUTONOMOUS,
    "git_commit":               GovernanceLevel.L1_AUTONOMOUS,
    "git_push":                 GovernanceLevel.L1_AUTONOMOUS,
    "memory_checkpoint":        GovernanceLevel.L1_AUTONOMOUS,
    "read_constitution":        GovernanceLevel.L1_AUTONOMOUS,

    # L2 — Co-decision
    "tweet_post":               GovernanceLevel.L2_CODECISION,
    "tweet_reply":              GovernanceLevel.L2_CODECISION,
    "constitution_propose":     GovernanceLevel.L2_CODECISION,
    "constitution_edit":        GovernanceLevel.L2_CODECISION,
    "register_platform":        GovernanceLevel.L2_CODECISION,
    "self_modify_orange":       GovernanceLevel.L2_CODECISION,

    # L3 — Human only
    "modify_credentials":       GovernanceLevel.L3_HUMAN_ONLY,
    "modify_infrastructure":    GovernanceLevel.L3_HUMAN_ONLY,
    "self_modify_red":          GovernanceLevel.L3_HUMAN_ONLY,
    "modify_principles":        GovernanceLevel.L3_HUMAN_ONLY,
    "delete_data":              GovernanceLevel.L3_HUMAN_ONLY,
    "kill_switch":              GovernanceLevel.L3_HUMAN_ONLY,
}

RATE_LIMITS = {
    "moltbook_post":    {"max_per_hour": 2, "cooldown_minutes": 30},
    "moltbook_comment": {"max_per_hour": 10, "cooldown_minutes": 2},
    "git_push":         {"max_per_hour": 4, "cooldown_minutes": 15},
}

RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_minutes": [6, 15, 30],
    "retryable_errors": ["rate_limited", "429", "timeout"],
}

L2_TIMEOUT_HOURS = 2


class ActionQueue:
    """
    The autonomy engine v2.3.
    
    - L1: execute immediately, retry on rate limit
    - L2: queue for approval
    - L3: block
    - All actions logged + autonomous audit trail
    """

    DATA_DIR = Path(__file__).parent.parent / "data"
    QUEUE_FILE = DATA_DIR / "action_queue.json"
    LOG_FILE = DATA_DIR / "action_log.json"
    AUTONOMOUS_LOG_FILE = DATA_DIR / "autonomous_actions_log.json"

    def __init__(self, agent=None, notify_fn: Optional[Callable] = None):
        self.agent = agent
        self._notify_fn = notify_fn
        self._queue: List[Dict] = []
        self._log: List[Dict] = []
        self._retry_queue: List[Dict] = []
        self._next_id: int = 1
        self._rate_tracker: Dict[str, List[datetime]] = {}
        self._handlers: Dict[str, Callable] = {}

        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.QUEUE_FILE.exists():
            try:
                with open(self.QUEUE_FILE, 'r') as f:
                    data = json.load(f)
                    self._queue = data.get("queue", [])
                    self._retry_queue = data.get("retry_queue", [])
                    self._next_id = data.get("next_id", 1)
            except (json.JSONDecodeError, IOError):
                self._queue = []
                self._retry_queue = []

        if self.LOG_FILE.exists():
            try:
                with open(self.LOG_FILE, 'r') as f:
                    self._log = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._log = []

    def _save(self):
        try:
            with open(self.QUEUE_FILE, 'w') as f:
                json.dump({
                    "queue": self._queue,
                    "retry_queue": self._retry_queue,
                    "next_id": self._next_id,
                    "updated_at": datetime.utcnow().isoformat()
                }, f, indent=2)
            with open(self.LOG_FILE, 'w') as f:
                json.dump(self._log[-500:], f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save action queue: {e}")

    def register_handler(self, action_type: str, handler: Callable):
        self._handlers[action_type] = handler

    def register_default_handlers(self):
        if not self.agent:
            logger.warning("Cannot register handlers: no agent instance")
            return

        self.register_handler("moltbook_post", self._handle_moltbook_post)
        self.register_handler("moltbook_comment", self._handle_moltbook_comment)
        self.register_handler("moltbook_verify", self._handle_moltbook_verify)
        self.register_handler("moltbook_read_feed", self._handle_moltbook_feed)
        self.register_handler("moltbook_heartbeat", self._handle_moltbook_heartbeat)
        self.register_handler("moltbook_search", self._handle_moltbook_search)
        self.register_handler("moltbook_upvote", self._handle_moltbook_upvote)
        self.register_handler("save_state", self._handle_save_state)
        self.register_handler("git_commit", self._handle_git_commit)
        self.register_handler("git_push", self._handle_git_push)
        self.register_handler("memory_checkpoint", self._handle_checkpoint)
        self.register_handler("read_constitution", self._handle_read_constitution)
        self.register_handler("tweet_post", self._handle_tweet_post)

        logger.info(f"Registered {len(self._handlers)} action handlers")

    # =========================================================================
    # Core: Enqueue + Execute
    # =========================================================================

    def enqueue(self, action_type: str, params: Dict = None) -> Dict:
        params = params or {}
        level = self._get_level(action_type)

        action = {
            "id": self._next_id,
            "action_type": action_type,
            "params": params,
            "level": level.value,
            "status": ActionStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }
        self._next_id += 1

        if level == GovernanceLevel.L3_HUMAN_ONLY:
            action["status"] = ActionStatus.REJECTED.value
            action["error"] = "L3 action — requires human authorization"
            self._log_action(action)
            logger.warning(f"L3 BLOCKED: {action_type} #{action['id']}")
            return {"action_id": action["id"], "level": "L3",
                    "status": "blocked", "error": action["error"]}

        if level == GovernanceLevel.L2_CODECISION:
            self._queue.append(action)
            self._save()
            logger.info(f"L2 QUEUED: {action_type} #{action['id']}")
            return {"action_id": action["id"], "level": "L2",
                    "status": "pending_approval", "message": "Awaiting operator approval"}

        if not self._check_rate_limit(action_type):
            action["status"] = ActionStatus.FAILED.value
            action["error"] = "Rate limited"
            self._log_action(action)
            return {"action_id": action["id"], "level": "L1",
                    "status": "rate_limited", "error": "Too many requests"}

        result = self._execute(action)

        # Feature C: Auto-retry on rate limit
        if self._is_retryable(result, action):
            return self._schedule_retry(action, result)

        return result

    def _execute(self, action: Dict) -> Dict:
        action_type = action["action_type"]
        handler = self._handlers.get(action_type)

        if not handler:
            action["status"] = ActionStatus.FAILED.value
            action["error"] = f"No handler for {action_type}"
            self._log_action(action)
            self._log_autonomous(action)
            return {"action_id": action["id"], "status": "error",
                    "error": action["error"]}

        action["status"] = ActionStatus.EXECUTING.value

        try:
            result = handler(action["params"])

            # Check if handler returned rate limit
            if isinstance(result, dict) and result.get("rate_limited"):
                action["status"] = ActionStatus.FAILED.value
                action["error"] = result.get("error", "Rate limited")
                action["executed_at"] = datetime.utcnow().isoformat()
                self._log_action(action)
                self._log_autonomous(action)
                return {
                    "action_id": action["id"],
                    "level": action["level"],
                    "status": "rate_limited",
                    "result": result,
                    "error": action["error"],
                    "retry_after_minutes": result.get("retry_after_minutes"),
                    "rate_limited": True,
                }

            action["status"] = ActionStatus.COMPLETED.value
            action["result"] = str(result)[:1000]
            action["executed_at"] = datetime.utcnow().isoformat()
            self._track_rate(action_type)
            logger.info(f"[{action['level']}] EXECUTED: {action_type} #{action['id']}")

        except Exception as e:
            action["status"] = ActionStatus.FAILED.value
            action["error"] = str(e)[:500]
            action["executed_at"] = datetime.utcnow().isoformat()
            logger.error(f"[{action['level']}] FAILED: {action_type} #{action['id']}: {e}")

        self._log_action(action)
        self._log_autonomous(action)
        self._save()

        return {
            "action_id": action["id"],
            "level": action["level"],
            "status": action["status"],
            "result": action.get("result"),
            "error": action.get("error"),
        }

    # =========================================================================
    # Feature C: Automatic Retry with Backoff
    # =========================================================================

    def _is_retryable(self, result: Dict, action: Dict) -> bool:
        if result.get("status") not in ["rate_limited", "error"]:
            return False
        if action.get("retry_count", 0) >= RETRY_CONFIG["max_retries"]:
            return False
        error = str(result.get("error", "")).lower()
        return any(term in error for term in RETRY_CONFIG["retryable_errors"]) or result.get("rate_limited")

    def _schedule_retry(self, action: Dict, result: Dict) -> Dict:
        retry_count = action.get("retry_count", 0)

        if result.get("retry_after_minutes"):
            wait_minutes = result["retry_after_minutes"]
        elif retry_count < len(RETRY_CONFIG["backoff_minutes"]):
            wait_minutes = RETRY_CONFIG["backoff_minutes"][retry_count]
        else:
            wait_minutes = RETRY_CONFIG["backoff_minutes"][-1]

        retry_at = datetime.utcnow() + timedelta(minutes=wait_minutes)

        action["status"] = ActionStatus.RETRY_SCHEDULED.value
        action["retry_count"] = retry_count + 1
        action["retry_at"] = retry_at.isoformat()
        action["error"] = f"Retry #{action['retry_count']} at {retry_at.strftime('%H:%M UTC')}"

        self._retry_queue.append(action)
        self._save()

        logger.info(f"RETRY SCHEDULED: {action['action_type']} #{action['id']} "
                     f"in {wait_minutes}min (attempt {action['retry_count']}/{RETRY_CONFIG['max_retries']})")

        return {
            "action_id": action["id"],
            "level": action["level"],
            "status": "retry_scheduled",
            "retry_at": retry_at.isoformat(),
            "retry_count": action["retry_count"],
            "wait_minutes": wait_minutes,
            "message": f"Action programmée pour {retry_at.strftime('%H:%M UTC')} (tentative {action['retry_count']})"
        }

    def process_retries(self) -> List[Dict]:
        """Check retry queue and execute actions whose time has come."""
        if not self._retry_queue:
            return []

        now = datetime.utcnow()
        results = []
        remaining = []

        for action in self._retry_queue:
            retry_at = datetime.fromisoformat(action["retry_at"])
            if now >= retry_at:
                logger.info(f"RETRYING: {action['action_type']} #{action['id']} (attempt {action['retry_count']})")
                action["status"] = ActionStatus.PENDING.value
                result = self._execute(action)

                if self._is_retryable(result, action):
                    self._schedule_retry(action, result)
                    # Don't re-append to remaining — _schedule_retry already did
                else:
                    results.append(result)
            else:
                remaining.append(action)

        self._retry_queue = remaining
        self._save()
        return results

    # =========================================================================
    # L2 Approval
    # =========================================================================

    def approve(self, action_id: int, approved_by: str = "operator") -> Dict:
        for action in self._queue:
            if action["id"] == action_id and action["status"] == ActionStatus.PENDING.value:
                action["approved_by"] = approved_by
                action["status"] = ActionStatus.APPROVED.value
                result = self._execute(action)
                self._queue = [a for a in self._queue if a["id"] != action_id]
                self._save()
                return {**result, "success": True, "action_type": action["action_type"]}
        return {"error": f"Action #{action_id} not found or not pending"}

    def reject(self, action_id: int, reason: str = "") -> Dict:
        for action in self._queue:
            if action["id"] == action_id and action["status"] == ActionStatus.PENDING.value:
                action["status"] = ActionStatus.REJECTED.value
                action["rejected_reason"] = reason
                self._log_action(action)
                self._queue = [a for a in self._queue if a["id"] != action_id]
                self._save()
                return {"action_id": action_id, "status": "rejected", "reason": reason, "success": True}
        return {"error": f"Action #{action_id} not found or not pending"}

    def get_pending(self) -> List[Dict]:
        return [a for a in self._queue if a["status"] == ActionStatus.PENDING.value]

    def expire_old_actions(self):
        cutoff = datetime.utcnow() - timedelta(hours=L2_TIMEOUT_HOURS)
        expired = []
        for action in self._queue:
            if action["status"] == ActionStatus.PENDING.value:
                created = datetime.fromisoformat(action["created_at"])
                if created < cutoff:
                    action["status"] = ActionStatus.EXPIRED.value
                    self._log_action(action)
                    expired.append(action["id"])

        if expired:
            self._queue = [a for a in self._queue if a["id"] not in expired]
            self._save()
            logger.info(f"Expired {len(expired)} L2 actions: {expired}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_level(self, action_type: str) -> GovernanceLevel:
        return GOVERNANCE_RULES.get(action_type, GovernanceLevel.L3_HUMAN_ONLY)

    def _check_rate_limit(self, action_type: str) -> bool:
        limits = RATE_LIMITS.get(action_type)
        if not limits:
            return True
        now = datetime.utcnow()
        history = self._rate_tracker.get(action_type, [])
        one_hour_ago = now - timedelta(hours=1)
        history = [t for t in history if t > one_hour_ago]
        self._rate_tracker[action_type] = history
        if len(history) >= limits["max_per_hour"]:
            return False
        if history:
            last = history[-1]
            cooldown = timedelta(minutes=limits["cooldown_minutes"])
            if now - last < cooldown:
                return False
        return True

    def _track_rate(self, action_type: str):
        if action_type not in self._rate_tracker:
            self._rate_tracker[action_type] = []
        self._rate_tracker[action_type].append(datetime.utcnow())

    def _log_action(self, action: Dict):
        self._log.append({**action, "logged_at": datetime.utcnow().isoformat()})

    # =========================================================================
    # Feature E: Structured Autonomous Actions Log
    # =========================================================================

    def _log_autonomous(self, action: Dict):
        """Write structured audit entry to autonomous_actions_log.json."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action_id": action.get("id"),
            "action_type": action.get("action_type"),
            "level": action.get("level"),
            "status": action.get("status"),
            "params": action.get("params", {}),
            "result": action.get("result"),
            "error": action.get("error"),
            "retry_count": action.get("retry_count", 0),
            "executed_at": action.get("executed_at"),
        }

        try:
            existing = []
            if self.AUTONOMOUS_LOG_FILE.exists():
                try:
                    with open(self.AUTONOMOUS_LOG_FILE, 'r') as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, IOError):
                    existing = []

            existing.append(entry)
            if len(existing) > 1000:
                existing = existing[-1000:]

            with open(self.AUTONOMOUS_LOG_FILE, 'w') as f:
                json.dump(existing, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to write autonomous log: {e}")

    # =========================================================================
    # Action Handlers
    # =========================================================================

    def _handle_moltbook_post(self, params: Dict) -> Dict:
        return self.agent.moltbook.create_post(
            title=params.get("title", ""),
            content=params.get("content", ""),
            submolt=params.get("submolt", "general")
        )

    def _handle_moltbook_comment(self, params: Dict) -> Dict:
        return self.agent.moltbook.create_comment(
            post_id=params["post_id"],
            content=params["content"],
            parent_id=params.get("parent_id")
        )

    def _handle_moltbook_verify(self, params: Dict) -> Dict:
        return self.agent.moltbook.verify_post(
            verification_code=params["code"],
            answer=params["answer"]
        )

    def _handle_moltbook_feed(self, params: Dict) -> List:
        return self.agent.moltbook.get_feed(
            sort=params.get("sort", "hot"),
            limit=params.get("limit", 10)
        )

    def _handle_moltbook_heartbeat(self, params: Dict) -> Dict:
        return self.agent.moltbook.heartbeat()

    def _handle_moltbook_search(self, params: Dict) -> List:
        return self.agent.moltbook.search(
            query=params.get("query", ""),
            limit=params.get("limit", 10)
        )

    def _handle_moltbook_upvote(self, params: Dict) -> Dict:
        return self.agent.moltbook.upvote(params["post_id"])

    def _handle_save_state(self, params: Dict) -> str:
        self.agent.save_state()
        return "State saved"

    def _handle_git_commit(self, params: Dict) -> str:
        from .git_sync import GitSync
        gs = GitSync(repo_path=".")
        gs.auto_commit(params.get("message", "auto-commit"))
        return "Git committed"

    def _handle_git_push(self, params: Dict) -> str:
        from .git_sync import GitSync
        gs = GitSync(repo_path=".")
        gs.push()
        return "Git pushed"

    def _handle_checkpoint(self, params: Dict) -> str:
        self.agent.memory.create_checkpoint(trigger="action_queue")
        return "Checkpoint created"

    def _handle_read_constitution(self, params: Dict) -> str:
        return self.agent.read_constitution(params.get("section", "all"))

    def _handle_tweet_post(self, params: Dict) -> str:
        return self.agent.twitter.queue_tweet(params.get("text", ""))

    # =========================================================================
    # Status
    # =========================================================================

    def get_status(self) -> Dict:
        return {
            "pending_l2": len(self.get_pending()),
            "retry_queue": len(self._retry_queue),
            "total_logged": len(self._log),
            "handlers_registered": len(self._handlers),
            "last_action": self._log[-1] if self._log else None,
        }

    def get_recent_log(self, count: int = 10) -> List[Dict]:
        return self._log[-count:]

    def get_retry_queue(self) -> List[Dict]:
        return self._retry_queue
