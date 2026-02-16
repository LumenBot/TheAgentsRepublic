"""
DAO Proposal Management
========================
The Constituent can create, monitor, and execute governance proposals.

Proposal lifecycle:
1. Draft — Author writes proposal (GitHub Issue or Telegram)
2. Discussion — 3-day community discussion on Moltbook/GitHub
3. Formal Submission — Requires 1,000 $REPUBLIC stake
4. Voting — 7-day on-chain voting period
5. Execution — If passed, executed on-chain or via agent
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TheConstituent.Governance")


class ProposalManager:
    """Handles DAO proposals for The Agents Republic."""

    PROPOSAL_TYPES = {
        "standard": {
            "threshold": 1_000,
            "voting_days": 7,
            "quorum_percent": 10,
            "majority_percent": 50,
        },
        "constitutional_amendment": {
            "threshold": 10_000,
            "voting_days": 14,
            "quorum_percent": 20,
            "majority_percent": 67,
        },
        "emergency": {
            "threshold": 100_000,
            "voting_days": 2,
            "quorum_percent": 5,
            "majority_percent": 50,
        },
        "treasury_spend": {
            "threshold": 5_000,
            "voting_days": 7,
            "quorum_percent": 15,
            "majority_percent": 50,
        },
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.proposals_file = self.data_dir / "proposals.json"
        self._proposals: List[Dict] = []
        self._load()

    def _load(self):
        """Load proposals from disk."""
        if self.proposals_file.exists():
            try:
                self._proposals = json.loads(self.proposals_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load proposals: {e}")
                self._proposals = []

    def _save(self):
        """Save proposals to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.proposals_file.write_text(
            json.dumps(self._proposals, indent=2, default=str)
        )

    def create_proposal(
        self,
        title: str,
        description: str,
        proposal_type: str = "standard",
        author: str = "operator",
        changes: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new governance proposal.

        Args:
            title: Short proposal title
            description: Full description with rationale
            proposal_type: One of PROPOSAL_TYPES keys
            author: Who submitted (wallet address or username)
            changes: Optional dict of specific changes proposed

        Returns:
            The created proposal dict
        """
        if proposal_type not in self.PROPOSAL_TYPES:
            return {"status": "error", "error": f"Unknown type: {proposal_type}"}

        config = self.PROPOSAL_TYPES[proposal_type]
        now = datetime.now(timezone.utc)

        proposal = {
            "id": len(self._proposals) + 1,
            "title": title,
            "description": description,
            "type": proposal_type,
            "author": author,
            "changes": changes,
            "status": "draft",
            "created_at": now.isoformat(),
            "discussion_ends": (now + timedelta(days=3)).isoformat(),
            "voting_ends": None,
            "votes_for": 0,
            "votes_against": 0,
            "voters": [],
            "threshold": config["threshold"],
            "quorum_percent": config["quorum_percent"],
            "majority_percent": config["majority_percent"],
        }

        self._proposals.append(proposal)
        self._save()

        logger.info(f"Proposal #{proposal['id']} created: {title}")
        return {"status": "ok", "proposal": proposal}

    def list_proposals(self, status: Optional[str] = None) -> List[Dict]:
        """List proposals, optionally filtered by status."""
        if status:
            return [p for p in self._proposals if p["status"] == status]
        return self._proposals

    def get_proposal(self, proposal_id: int) -> Optional[Dict]:
        """Get a specific proposal by ID."""
        for p in self._proposals:
            if p["id"] == proposal_id:
                return p
        return None

    def submit_for_voting(self, proposal_id: int) -> Dict:
        """Move proposal from draft to active voting."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            return {"status": "error", "error": f"Proposal #{proposal_id} not found"}

        if proposal["status"] != "draft":
            return {"status": "error", "error": f"Proposal is {proposal['status']}, not draft"}

        config = self.PROPOSAL_TYPES[proposal["type"]]
        now = datetime.now(timezone.utc)

        proposal["status"] = "voting"
        proposal["voting_started"] = now.isoformat()
        proposal["voting_ends"] = (now + timedelta(days=config["voting_days"])).isoformat()
        self._save()

        logger.info(f"Proposal #{proposal_id} submitted for voting (ends {proposal['voting_ends']})")
        return {"status": "ok", "proposal": proposal}

    def vote(self, proposal_id: int, voter: str, support: bool) -> Dict:
        """Cast a vote on a proposal."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            return {"status": "error", "error": f"Proposal #{proposal_id} not found"}

        if proposal["status"] != "voting":
            return {"status": "error", "error": f"Proposal is {proposal['status']}, not in voting"}

        if voter in proposal["voters"]:
            return {"status": "error", "error": f"{voter} already voted"}

        if support:
            proposal["votes_for"] += 1
        else:
            proposal["votes_against"] += 1
        proposal["voters"].append(voter)
        self._save()

        logger.info(f"Vote on #{proposal_id}: {'FOR' if support else 'AGAINST'} by {voter}")
        return {"status": "ok", "votes_for": proposal["votes_for"], "votes_against": proposal["votes_against"]}

    def finalize(self, proposal_id: int) -> Dict:
        """Finalize a proposal after voting period ends."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            return {"status": "error", "error": f"Proposal #{proposal_id} not found"}

        if proposal["status"] != "voting":
            return {"status": "error", "error": "Not in voting phase"}

        total_votes = proposal["votes_for"] + proposal["votes_against"]
        majority = proposal["majority_percent"]

        if total_votes == 0:
            proposal["status"] = "failed"
            proposal["result"] = "No votes cast"
        elif (proposal["votes_for"] / total_votes * 100) >= majority:
            proposal["status"] = "passed"
            proposal["result"] = f"Passed ({proposal['votes_for']}/{total_votes})"
        else:
            proposal["status"] = "failed"
            proposal["result"] = f"Failed ({proposal['votes_for']}/{total_votes}, needed {majority}%)"

        self._save()
        logger.info(f"Proposal #{proposal_id}: {proposal['status']} — {proposal['result']}")
        return {"status": "ok", "proposal": proposal}

    def get_summary(self) -> Dict:
        """Get governance summary stats."""
        return {
            "total_proposals": len(self._proposals),
            "active_voting": len([p for p in self._proposals if p["status"] == "voting"]),
            "passed": len([p for p in self._proposals if p["status"] == "passed"]),
            "failed": len([p for p in self._proposals if p["status"] == "failed"]),
            "drafts": len([p for p in self._proposals if p["status"] == "draft"]),
        }
