"""
Tests for agent.governance.proposals (ProposalManager)
and agent.governance.treasury (TreasuryManager).
"""

import json
import pytest
from pathlib import Path

from agent.governance.proposals import ProposalManager
from agent.governance.treasury import TreasuryManager


# ===================================================================
# ProposalManager tests
# ===================================================================

class TestProposalTypes:
    """Verify the built-in proposal type configurations."""

    def test_standard_type_exists(self):
        assert "standard" in ProposalManager.PROPOSAL_TYPES

    def test_standard_threshold(self):
        assert ProposalManager.PROPOSAL_TYPES["standard"]["threshold"] == 1_000

    def test_constitutional_amendment_majority(self):
        cfg = ProposalManager.PROPOSAL_TYPES["constitutional_amendment"]
        assert cfg["majority_percent"] == 67

    def test_emergency_voting_days(self):
        cfg = ProposalManager.PROPOSAL_TYPES["emergency"]
        assert cfg["voting_days"] == 2

    def test_treasury_spend_threshold(self):
        cfg = ProposalManager.PROPOSAL_TYPES["treasury_spend"]
        assert cfg["threshold"] == 5_000


class TestProposalCreation:
    def test_create_standard_proposal(self, proposal_manager):
        """Creating a standard proposal returns status ok with the proposal dict."""
        result = proposal_manager.create_proposal(
            title="Fund AI research",
            description="Allocate tokens for AI research grants",
        )
        assert result["status"] == "ok"
        p = result["proposal"]
        assert p["title"] == "Fund AI research"
        assert p["status"] == "draft"
        assert p["type"] == "standard"
        assert p["id"] == 1

    def test_create_proposal_invalid_type(self, proposal_manager):
        """Creating a proposal with an unknown type returns an error."""
        result = proposal_manager.create_proposal(
            title="Bad",
            description="Invalid type test",
            proposal_type="nonexistent_type",
        )
        assert result["status"] == "error"
        assert "Unknown type" in result["error"]

    def test_create_proposal_with_changes(self, proposal_manager):
        """The optional changes dict is stored in the proposal."""
        changes = {"article_5": "Updated wording here"}
        result = proposal_manager.create_proposal(
            title="Amend Article 5",
            description="Fix typo",
            proposal_type="constitutional_amendment",
            changes=changes,
        )
        assert result["proposal"]["changes"] == changes

    def test_proposal_ids_increment(self, proposal_manager):
        """Each new proposal gets an incrementing ID."""
        proposal_manager.create_proposal("First", "desc")
        proposal_manager.create_proposal("Second", "desc")
        proposals = proposal_manager.list_proposals()
        assert proposals[0]["id"] == 1
        assert proposals[1]["id"] == 2

    def test_proposal_persists_to_disk(self, tmp_path):
        """Proposals are saved to disk and survive a fresh load."""
        pm = ProposalManager(data_dir=str(tmp_path))
        pm.create_proposal("Persistent", "Saved to disk")

        # Create a new manager pointing at the same directory
        pm2 = ProposalManager(data_dir=str(tmp_path))
        assert len(pm2.list_proposals()) == 1
        assert pm2.list_proposals()[0]["title"] == "Persistent"


class TestProposalListing:
    def test_list_all_proposals(self, proposal_manager):
        """list_proposals with no filter returns all proposals."""
        proposal_manager.create_proposal("A", "desc a")
        proposal_manager.create_proposal("B", "desc b")
        assert len(proposal_manager.list_proposals()) == 2

    def test_list_by_status(self, proposal_manager):
        """list_proposals can filter by status."""
        proposal_manager.create_proposal("Draft1", "desc")
        proposal_manager.create_proposal("Draft2", "desc")
        # All should be drafts
        drafts = proposal_manager.list_proposals(status="draft")
        assert len(drafts) == 2
        voting = proposal_manager.list_proposals(status="voting")
        assert len(voting) == 0

    def test_get_proposal_by_id(self, proposal_manager):
        """get_proposal returns the correct proposal."""
        proposal_manager.create_proposal("Find me", "desc")
        p = proposal_manager.get_proposal(1)
        assert p is not None
        assert p["title"] == "Find me"

    def test_get_nonexistent_proposal(self, proposal_manager):
        """get_proposal for a missing ID returns None."""
        assert proposal_manager.get_proposal(999) is None


class TestProposalVoting:
    def test_submit_for_voting(self, proposal_manager):
        """A draft proposal can be submitted for voting."""
        proposal_manager.create_proposal("Vote me", "desc")
        result = proposal_manager.submit_for_voting(1)
        assert result["status"] == "ok"
        assert result["proposal"]["status"] == "voting"
        assert result["proposal"]["voting_ends"] is not None

    def test_submit_nonexistent_proposal(self, proposal_manager):
        """Submitting a non-existent proposal returns error."""
        result = proposal_manager.submit_for_voting(999)
        assert result["status"] == "error"

    def test_submit_already_voting(self, proposal_with_votes):
        """Submitting an already-voting proposal returns error."""
        result = proposal_with_votes.submit_for_voting(1)
        assert result["status"] == "error"
        assert "not draft" in result["error"]

    def test_cast_vote_for(self, proposal_with_votes):
        """Casting a vote increments the correct counter."""
        result = proposal_with_votes.vote(1, "voter_alice", True)
        assert result["status"] == "ok"
        assert result["votes_for"] == 1
        assert result["votes_against"] == 0

    def test_cast_vote_against(self, proposal_with_votes):
        """Voting against increments votes_against."""
        result = proposal_with_votes.vote(1, "voter_bob", False)
        assert result["status"] == "ok"
        assert result["votes_against"] == 1

    def test_duplicate_vote_rejected(self, proposal_with_votes):
        """The same voter cannot vote twice on the same proposal."""
        proposal_with_votes.vote(1, "voter_x", True)
        result = proposal_with_votes.vote(1, "voter_x", True)
        assert result["status"] == "error"
        assert "already voted" in result["error"]

    def test_vote_on_draft_fails(self, proposal_manager):
        """Cannot vote on a proposal still in draft status."""
        proposal_manager.create_proposal("Not yet", "desc")
        result = proposal_manager.vote(1, "voter", True)
        assert result["status"] == "error"
        assert "not in voting" in result["error"]

    def test_vote_on_nonexistent_proposal(self, proposal_manager):
        """Voting on a non-existent proposal returns error."""
        result = proposal_manager.vote(999, "voter", True)
        assert result["status"] == "error"


class TestProposalFinalization:
    def test_finalize_passed(self, proposal_with_votes):
        """A proposal with majority support passes."""
        pm = proposal_with_votes
        pm.vote(1, "alice", True)
        pm.vote(1, "bob", True)
        pm.vote(1, "carol", False)
        result = pm.finalize(1)
        assert result["status"] == "ok"
        assert result["proposal"]["status"] == "passed"

    def test_finalize_failed(self, proposal_with_votes):
        """A proposal without majority support fails."""
        pm = proposal_with_votes
        pm.vote(1, "alice", True)
        pm.vote(1, "bob", False)
        pm.vote(1, "carol", False)
        result = pm.finalize(1)
        assert result["status"] == "ok"
        assert result["proposal"]["status"] == "failed"

    def test_finalize_no_votes(self, proposal_with_votes):
        """A proposal with zero votes fails."""
        result = proposal_with_votes.finalize(1)
        assert result["status"] == "ok"
        assert result["proposal"]["status"] == "failed"
        assert "No votes" in result["proposal"]["result"]

    def test_finalize_nonexistent(self, proposal_manager):
        """Finalizing a non-existent proposal returns error."""
        result = proposal_manager.finalize(999)
        assert result["status"] == "error"

    def test_finalize_draft_fails(self, proposal_manager):
        """Cannot finalize a proposal still in draft."""
        proposal_manager.create_proposal("Draft", "desc")
        result = proposal_manager.finalize(1)
        assert result["status"] == "error"
        assert "Not in voting" in result["error"]

    def test_constitutional_amendment_needs_supermajority(self, tmp_path):
        """A constitutional amendment needs 67% to pass."""
        pm = ProposalManager(data_dir=str(tmp_path))
        pm.create_proposal(
            "Amendment",
            "Change constitution",
            proposal_type="constitutional_amendment",
        )
        pm.submit_for_voting(1)
        # 60% support -- not enough for 67%
        pm.vote(1, "a", True)
        pm.vote(1, "b", True)
        pm.vote(1, "c", True)
        pm.vote(1, "d", False)
        pm.vote(1, "e", False)
        result = pm.finalize(1)
        assert result["proposal"]["status"] == "failed"


class TestProposalSummary:
    def test_empty_summary(self, proposal_manager):
        """Summary on empty state reports all zeros."""
        s = proposal_manager.get_summary()
        assert s["total_proposals"] == 0
        assert s["active_voting"] == 0
        assert s["passed"] == 0
        assert s["failed"] == 0
        assert s["drafts"] == 0

    def test_summary_counts(self, proposal_with_votes):
        """Summary counts different statuses correctly."""
        pm = proposal_with_votes
        # proposal #1 is already in voting
        pm.create_proposal("Draft one", "desc")  # stays draft
        pm.vote(1, "alice", True)
        pm.finalize(1)  # now passed

        s = pm.get_summary()
        assert s["total_proposals"] == 2
        assert s["passed"] == 1
        assert s["drafts"] == 1
        assert s["active_voting"] == 0


# ===================================================================
# TreasuryManager tests
# ===================================================================

class TestTreasuryRecord:
    def test_record_income(self, treasury):
        """Recording income returns status ok with the entry."""
        result = treasury.record_transaction("income", 1000.0, "REPUBLIC", "grant")
        assert result["status"] == "ok"
        assert result["entry"]["amount"] == 1000.0
        assert result["entry"]["type"] == "income"

    def test_record_expense(self, treasury):
        """Recording an expense works correctly."""
        result = treasury.record_transaction("expense", 250.0, "ETH", "gas costs")
        assert result["status"] == "ok"
        assert result["entry"]["currency"] == "ETH"

    def test_transaction_ids_increment(self, treasury):
        """Transaction IDs increment sequentially."""
        treasury.record_transaction("income", 100.0)
        treasury.record_transaction("expense", 50.0)
        status = treasury.get_status()
        assert status["total_transactions"] == 2

    def test_persists_to_disk(self, tmp_path):
        """Transactions persist across TreasuryManager instances."""
        tm = TreasuryManager(data_dir=str(tmp_path))
        tm.record_transaction("income", 500.0, "REPUBLIC", "initial")

        tm2 = TreasuryManager(data_dir=str(tmp_path))
        assert tm2.get_status()["total_transactions"] == 1


class TestTreasuryBalance:
    def test_empty_balance(self, treasury):
        """Empty treasury has no balances."""
        assert treasury.get_balance() == {}

    def test_single_income(self, treasury):
        """Single income produces a positive balance."""
        treasury.record_transaction("income", 1000.0, "REPUBLIC")
        bal = treasury.get_balance()
        assert bal["REPUBLIC"] == 1000.0

    def test_income_minus_expense(self, funded_treasury):
        """Balance is income minus expenses per currency."""
        bal = funded_treasury.get_balance()
        assert bal["REPUBLIC"] == 9500.0  # 10000 - 500
        assert bal["ETH"] == 5.0

    def test_multiple_currencies(self, treasury):
        """Balances are tracked per currency independently."""
        treasury.record_transaction("income", 100.0, "REPUBLIC")
        treasury.record_transaction("income", 2.0, "ETH")
        treasury.record_transaction("income", 50.0, "USDC")
        bal = treasury.get_balance()
        assert len(bal) == 3
        assert bal["USDC"] == 50.0


class TestTreasuryReporting:
    def test_monthly_report_structure(self, funded_treasury):
        """Monthly report contains expected keys."""
        report = funded_treasury.get_monthly_report()
        assert "period" in report
        assert "income" in report
        assert "expenses" in report
        assert "net" in report
        assert "transactions" in report
        assert "balance" in report

    def test_monthly_report_empty_month(self, treasury):
        """Monthly report for a month with no transactions returns zeros."""
        report = treasury.get_monthly_report(year=2020, month=1)
        assert report["income"] == 0
        assert report["expenses"] == 0
        assert report["net"] == 0
        assert report["transactions"] == 0

    def test_status_last_transaction(self, funded_treasury):
        """get_status returns the last transaction."""
        status = funded_treasury.get_status()
        assert status["last_transaction"] is not None
        assert status["last_transaction"]["description"] == "API costs"

    def test_status_empty_treasury(self, treasury):
        """get_status on empty treasury has no last_transaction."""
        status = treasury.get_status()
        assert status["last_transaction"] is None
        assert status["total_transactions"] == 0


class TestTreasuryEdgeCases:
    def test_corrupt_ledger_file(self, tmp_path):
        """A corrupt JSON file does not crash the manager."""
        ledger = tmp_path / "treasury_ledger.json"
        ledger.write_text("THIS IS NOT JSON")
        tm = TreasuryManager(data_dir=str(tmp_path))
        assert tm.get_status()["total_transactions"] == 0

    def test_default_currency_is_republic(self, treasury):
        """Default currency for transactions is REPUBLIC."""
        result = treasury.record_transaction("income", 100.0)
        assert result["entry"]["currency"] == "REPUBLIC"
