"""
Tests for agent.config.tokenomics — RepublicTokenomics configuration.
"""

import pytest
from agent.config.tokenomics import RepublicTokenomics, tokenomics


class TestTokenBasicInfo:
    """Test basic token metadata fields."""

    def test_name(self):
        assert tokenomics.NAME == "The Agents Republic"

    def test_symbol(self):
        assert tokenomics.SYMBOL == "REPUBLIC"

    def test_decimals(self):
        assert tokenomics.DECIMALS == 18

    def test_total_supply_is_one_billion(self):
        assert tokenomics.TOTAL_SUPPLY == 1_000_000_000


class TestTokenDeployment:
    """Test on-chain deployment configuration."""

    def test_chain_id_is_base(self):
        """Chain ID 8453 is Base mainnet."""
        assert tokenomics.CHAIN_ID == 8453

    def test_token_address_format(self):
        """Token address should be a valid hex address (0x + 40 hex chars)."""
        addr = tokenomics.TOKEN_ADDRESS
        assert addr.startswith("0x")
        assert len(addr) == 42

    def test_explorer_url_contains_address(self):
        """The explorer URL references the token address."""
        assert tokenomics.TOKEN_ADDRESS in tokenomics.EXPLORER_URL

    def test_burn_tx_hash_format(self):
        """Burn transaction hash looks like a valid tx hash (0x + 64 hex chars)."""
        assert tokenomics.BURN_TX_HASH.startswith("0x")
        assert len(tokenomics.BURN_TX_HASH) == 66


class TestTokenAllocations:
    """Test token allocation percentages and breakdown."""

    def test_dev_plus_liquidity_equals_100(self):
        """Dev allocation + initial liquidity should sum to 100%."""
        total = tokenomics.DEV_ALLOCATION_PERCENT + tokenomics.INITIAL_LIQUIDITY_PERCENT
        assert total == 100

    def test_dev_allocation_breakdown_sums_to_one(self):
        """The dev allocation breakdown percentages sum to 1.0 (100%)."""
        total = sum(tokenomics.DEV_ALLOCATION_BREAKDOWN.values())
        assert abs(total - 1.0) < 1e-9

    def test_dev_allocation_has_expected_keys(self):
        """Dev breakdown includes the four expected categories."""
        expected_keys = {"agent_operations", "treasury_dao", "team_vested", "partnerships"}
        assert set(tokenomics.DEV_ALLOCATION_BREAKDOWN.keys()) == expected_keys

    def test_agent_operations_is_largest(self):
        """Agent operations should be the largest dev allocation."""
        breakdown = tokenomics.DEV_ALLOCATION_BREAKDOWN
        assert breakdown["agent_operations"] == max(breakdown.values())


class TestGovernanceParams:
    """Test governance-related token parameters."""

    def test_proposal_threshold(self):
        assert tokenomics.PROPOSAL_THRESHOLD == 1_000

    def test_voting_period(self):
        assert tokenomics.VOTING_PERIOD_DAYS == 7

    def test_quorum_percent(self):
        assert tokenomics.QUORUM_PERCENT == 10

    def test_amendment_supermajority(self):
        assert tokenomics.AMENDMENT_SUPERMAJORITY == 67


class TestTokenUtilities:
    """Test utility list configuration."""

    def test_utilities_is_nonempty_list(self):
        assert isinstance(tokenomics.UTILITIES, list)
        assert len(tokenomics.UTILITIES) > 0

    def test_governance_voting_is_utility(self):
        """Governance voting should be listed as a token utility."""
        assert any("Governance" in u for u in tokenomics.UTILITIES)


class TestLaunchChecks:
    """Test launch readiness checklist."""

    def test_launch_checks_exist(self):
        assert isinstance(tokenomics.LAUNCH_READY_CHECKS, list)
        assert len(tokenomics.LAUNCH_READY_CHECKS) >= 5

    def test_constitution_check_present(self):
        """Constitution check is part of launch readiness."""
        assert any("Constitution" in c for c in tokenomics.LAUNCH_READY_CHECKS)


class TestTokenomicsInstantiation:
    """Test that RepublicTokenomics can be freely instantiated."""

    def test_fresh_instance_matches_module_level(self):
        """A new instance should have the same defaults as the module-level one."""
        fresh = RepublicTokenomics()
        assert fresh.NAME == tokenomics.NAME
        assert fresh.TOTAL_SUPPLY == tokenomics.TOTAL_SUPPLY
        assert fresh.CHAIN_ID == tokenomics.CHAIN_ID

    def test_instance_fields_are_independent(self):
        """Mutating a fresh instance does not affect the module-level singleton."""
        fresh = RepublicTokenomics()
        fresh.DECIMALS = 8
        assert tokenomics.DECIMALS == 18
