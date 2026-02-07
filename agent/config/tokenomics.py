"""
$REPUBLIC Token Configuration
==============================
Token economics and launch parameters for The Agents Republic.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RepublicTokenomics:
    """$REPUBLIC Token Configuration."""

    # Basic Info
    NAME: str = "The Agents Republic"
    SYMBOL: str = "REPUBLIC"
    DECIMALS: int = 18
    TOTAL_SUPPLY: int = 1_000_000_000  # 1 billion tokens

    # Token Metadata (used by Clawnch launchpad during deployment)
    DESCRIPTION: str = (
        "The governance token of The Agents Republic — "
        "a constitutional AI republic where autonomous agents "
        "collaborate under a living constitution. "
        "$REPUBLIC enables on-chain governance, treasury management, "
        "and community participation in the first AI-native democratic experiment."
    )
    IMAGE_PATH: str = "assets/republic-token.png"
    IMAGE_URL: str = (
        "https://raw.githubusercontent.com/LumenBot/TheAgentsRepublic"
        "/main/assets/republic-token.png"
    )
    WEBSITE: str = "https://github.com/LumenBot/TheAgentsRepublic"
    TWITTER: str = "https://x.com/XTheConstituent"

    # Clawnch Launch Parameters
    CLAWNCH_BURN_AMOUNT: int = 5_000_000       # 5M $CLAWNCH to burn
    DEV_ALLOCATION_PERCENT: int = 5             # 5% to agent wallet (50M tokens)
    INITIAL_LIQUIDITY_PERCENT: int = 95         # 95% to LP (950M tokens)

    # Dev Allocation Breakdown (from 5% = 50M tokens)
    DEV_ALLOCATION_BREAKDOWN: Dict[str, float] = field(default_factory=lambda: {
        "agent_operations": 0.50,    # 25M — Fund autonomous agent running costs
        "treasury_dao": 0.30,        # 15M — DAO governance treasury
        "team_vested": 0.15,         # 7.5M — Team (4-year vesting)
        "partnerships": 0.05,        # 2.5M — Strategic partnerships
    })

    # Governance Parameters
    PROPOSAL_THRESHOLD: int = 1_000            # Min tokens to submit proposal
    VOTING_PERIOD_DAYS: int = 7
    QUORUM_PERCENT: int = 10                   # % of circulating supply
    AMENDMENT_SUPERMAJORITY: int = 67           # % for constitutional changes

    # Token Utility
    UTILITIES: List[str] = field(default_factory=lambda: [
        "Governance voting (1 token = 1 vote)",
        "Access to premium agent services",
        "Staking rewards (future)",
        "Transaction fees in Republic ecosystem",
        "Grants for community contributions",
    ])

    # Launch Readiness Checks
    LAUNCH_READY_CHECKS: List[str] = field(default_factory=lambda: [
        "Constitution published (7+ articles)",
        "GitHub documentation finalized",
        "Agent operational >72 hours stable",
        "Operator approval obtained",
        "Wallet funded with ETH for gas",
        "CLAWNCH tokens acquired for burn",
    ])


tokenomics = RepublicTokenomics()
