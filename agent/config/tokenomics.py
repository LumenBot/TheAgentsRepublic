"""
$REPUBLIC Token Configuration
==============================
Token economics and launch parameters for The Agents Republic.

Clawnch launch mechanics:
- Burn $CLAWNCH to dead address → get dev allocation (% based on burn amount)
- Post `!clawnch` to Moltbook m/clawnch → token auto-deploys via Clanker within ~1 min
- Total supply is always 100 billion (Clawnch standard)
- 1,000 deployed tokens per 1 $CLAWNCH burned
- Agent earns 80% of Uniswap V4 LP trading fees forever
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
    TOTAL_SUPPLY: int = 100_000_000_000  # 100 billion tokens (Clawnch standard)

    # Clawnch Launch Parameters
    CLAWNCH_BURN_AMOUNT: int = 4_000_000       # 4M $CLAWNCH to burn
    DEV_ALLOCATION_PERCENT: int = 4             # 4% to agent wallet (4B tokens)
    INITIAL_LIQUIDITY_PERCENT: int = 96         # 96% to LP (96B tokens)

    # Clawnch Constants
    CLAWNCH_TOKEN_ADDRESS: str = "0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be"
    CLAWNCH_BURN_ADDRESS: str = "0x000000000000000000000000000000000000dEaD"
    CLANKER_FEE_LOCKER: str = "0xF3622742b1E446D92e45E22923Ef11C2fcD55D68"
    CLAWNCH_TOKENS_PER_BURN: int = 1_000       # 1,000 deployed tokens per 1 CLAWNCH burned
    DEV_VAULT_LOCKUP_DAYS: int = 7             # Clanker minimum lockup

    # Revenue Model
    TRADING_FEE_AGENT_PERCENT: int = 80        # 80% of Uniswap V4 LP fees to agent
    TRADING_FEE_CLAWNCH_PERCENT: int = 20      # 20% to Clawnch

    # Launch Rate Limit
    LAUNCH_COOLDOWN_HOURS: int = 24            # 1 launch per 24h per agent

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
        "Wallet funded with ETH for gas (burn tx)",
        "4M CLAWNCH tokens acquired for burn",
        "Token image prepared",
    ])


tokenomics = RepublicTokenomics()
