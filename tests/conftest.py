"""
Shared pytest fixtures for TheAgentsRepublic test suite.
"""

import json
import pytest
from pathlib import Path

from agent.tool_registry import Tool, ToolParam, ToolRegistry
from agent.governance.proposals import ProposalManager
from agent.governance.treasury import TreasuryManager


# ---------------------------------------------------------------------------
# Tool Registry fixtures
# ---------------------------------------------------------------------------

def _echo_handler(**kwargs):
    """Simple handler that echoes its arguments back."""
    return kwargs


async def _async_echo_handler(**kwargs):
    """Async handler that echoes its arguments back."""
    return kwargs


@pytest.fixture
def sample_tool():
    """A simple tool with one required param and a handler."""
    return Tool(
        name="echo",
        description="Echoes input back",
        params=[
            ToolParam(name="message", type="string", description="Message to echo"),
        ],
        handler=_echo_handler,
        governance_level="L1",
        category="utility",
    )


@pytest.fixture
def l3_tool():
    """A tool with L3 (blocked) governance level."""
    return Tool(
        name="dangerous_op",
        description="A dangerous operation",
        params=[],
        handler=lambda: "should never run",
        governance_level="L3",
        category="admin",
    )


@pytest.fixture
def no_handler_tool():
    """A tool with no handler (schema-only)."""
    return Tool(
        name="placeholder",
        description="Placeholder tool with no handler",
        params=[
            ToolParam(name="arg", type="string", description="An argument"),
        ],
        handler=None,
        governance_level="L1",
        category="general",
    )


@pytest.fixture
def registry(sample_tool, l3_tool, no_handler_tool):
    """A ToolRegistry pre-loaded with sample tools."""
    reg = ToolRegistry()
    reg.register(sample_tool)
    reg.register(l3_tool)
    reg.register(no_handler_tool)
    return reg


# ---------------------------------------------------------------------------
# Governance / Proposals fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def proposal_manager(tmp_path):
    """A ProposalManager backed by a temporary directory."""
    return ProposalManager(data_dir=str(tmp_path))


@pytest.fixture
def proposal_with_votes(proposal_manager):
    """A ProposalManager with one proposal already in voting phase."""
    pm = proposal_manager
    pm.create_proposal(
        title="Test proposal",
        description="A test proposal",
        proposal_type="standard",
        author="alice",
    )
    pm.submit_for_voting(1)
    return pm


# ---------------------------------------------------------------------------
# Treasury fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def treasury(tmp_path):
    """A TreasuryManager backed by a temporary directory."""
    return TreasuryManager(data_dir=str(tmp_path))


@pytest.fixture
def funded_treasury(treasury):
    """A TreasuryManager with some initial transactions."""
    treasury.record_transaction("income", 10000.0, "REPUBLIC", "Initial funding")
    treasury.record_transaction("income", 5.0, "ETH", "Gas deposit")
    treasury.record_transaction("expense", 500.0, "REPUBLIC", "API costs")
    return treasury


# ---------------------------------------------------------------------------
# Data-directory fixtures (for briefing tool)
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with sample JSON files."""
    d = tmp_path / "data"
    d.mkdir()

    # constitution_progress.json
    (d / "constitution_progress.json").write_text(json.dumps({
        "articles_written": ["Article I", "Article II", "Article III"],
    }))

    # daily_metrics.json
    (d / "daily_metrics.json").write_text(json.dumps({
        "posts": 5,
        "replies": 12,
        "commits": 3,
    }))

    # pending_tweets.json
    (d / "pending_tweets.json").write_text(json.dumps({
        "tweets": [
            {"text": "hello", "status": "pending"},
            {"text": "world", "status": "posted"},
            {"text": "draft tweet", "status": "draft"},
        ],
    }))

    return d
