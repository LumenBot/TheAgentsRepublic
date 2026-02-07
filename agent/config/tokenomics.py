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

    # Deployed Token (Clawnch launch 2026-02-07)
    TOKEN_ADDRESS: str = "0x06B09BE0EF93771ff6a6D378dF5C7AC1c673563f"
    CHAIN_ID: int = 8453  # Base mainnet
    EXPLORER_URL: str = "https://basescan.org/token/0x06B09BE0EF93771ff6a6D378dF5C7AC1c673563f"
    BURN_TX_HASH: str = "0xa8b5bc2126e3c99d7769197d1248f68966b8d96e98d7aaa2c051060089beb055"

    # Clawnch Launch Parameters
    CLAWNCH_BURN_AMOUNT: int = 4_000_000       # 4M $CLAWNCH to burn
    DEV_ALLOCATION_PERCENT: int = 4             # 4% dev allocation (4B tokens on 100B)
    INITIAL_LIQUIDITY_PERCENT: int = 96         # 96% to LP

    # Dev Allocation Breakdown (from 4% = 4B tokens)
    DEV_ALLOCATION_BREAKDOWN: Dict[str, float] = field(default_factory=lambda: {
        "agent_operations": 0.50,    # 2B — Fund autonomous agent running costs
        "treasury_dao": 0.30,        # 1.2B — DAO governance treasury
        "team_vested": 0.15,         # 600M — Team (4-year vesting)
        "partnerships": 0.05,        # 200M — Strategic partnerships
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
