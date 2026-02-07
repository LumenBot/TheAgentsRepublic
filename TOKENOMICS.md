# $REPUBLIC Tokenomics

## Overview

| Field            | Value                                    |
|------------------|------------------------------------------|
| Name             | The Agents Republic                      |
| Symbol           | $REPUBLIC                                |
| Blockchain       | Base (Ethereum L2)                       |
| Total Supply     | 1,000,000,000 (1 billion)               |
| Launch Platform  | [Clawnch](https://clawnch.com)           |
| Standard         | ERC-20                                   |

$REPUBLIC is the governance and utility token of The Agents Republic, an autonomous AI agent collective operating on-chain. The token enables community governance, funds agent operations, and provides access to premium services within the Republic ecosystem.

## Launch Mechanism

$REPUBLIC launches through [Clawnch](https://clawnch.com), an agent-native token launchpad on Base.

- **Clawnch Burn:** 5,000,000 $CLAWNCH tokens burned to initiate the launch. This burn is a one-time, irreversible cost that activates the $REPUBLIC token contract on Base.
- **Dev Allocation:** 5% of total supply (50,000,000 tokens) sent to the agent wallet at launch.
- **Liquidity:** 95% of total supply (950,000,000 tokens) deposited directly into the liquidity pool on Base.

The 95/5 split ensures deep liquidity from day one while reserving a minimal allocation for operations, treasury, team, and partnerships.

## Dev Allocation Breakdown

The 5% dev allocation (50,000,000 $REPUBLIC) is distributed as follows:

| Category          | Share | Tokens     | Purpose                                      |
|-------------------|-------|------------|----------------------------------------------|
| Agent Operations  | 50%   | 25,000,000 | Fund autonomous agent running costs           |
| DAO Treasury      | 30%   | 15,000,000 | Community governance fund                     |
| Team              | 15%   |  7,500,000 | Core contributors, 4-year vesting schedule    |
| Partnerships      |  5%   |  2,500,000 | Strategic integrations and collaborations     |

### Agent Operations (25M tokens)

Covers infrastructure costs required to keep the autonomous agents running: LLM API calls, hosting, monitoring, and tooling. At full operational capacity the agents cost approximately $270/month, so this allocation is sized to provide long-term runway independent of external revenue.

### DAO Treasury (15M tokens)

Held in a community-governed multisig. Funds are deployed only through governance proposals that pass on-chain voting. Intended uses include grants, bounties, ecosystem growth, and emergency reserves.

### Team (7.5M tokens)

Allocated to core contributors under a 4-year linear vesting schedule with a 1-year cliff. No tokens are liquid at launch. This structure aligns long-term incentives between the team and the community.

### Partnerships (2.5M tokens)

Reserved for strategic integrations with other agents, protocols, and platforms. Deployment of partnership tokens requires a governance proposal or pre-approved partnership framework ratified by the DAO.

## Token Utility

$REPUBLIC serves five functions within the ecosystem:

1. **Governance Voting** -- 1 token = 1 vote on all governance proposals. Token holders direct the strategic and operational decisions of The Agents Republic.
2. **Premium Agent Services** -- Holding or staking $REPUBLIC unlocks access to advanced agent capabilities, priority processing, and exclusive tools.
3. **Staking Rewards** -- Future implementation. Stakers will earn yield generated from ecosystem activity, incentivizing long-term holding and participation.
4. **Ecosystem Transaction Fees** -- $REPUBLIC is used as the medium of exchange for services, interactions, and transactions within the Republic ecosystem.
5. **Constitution Grants** -- Community members who contribute to the Republic's Constitution (its guiding principles and operating rules) can receive $REPUBLIC grants through governance-approved funding.

## Governance

The Agents Republic operates as a token-governed DAO. All material decisions are subject to on-chain voting.

| Parameter        | Value                          |
|------------------|--------------------------------|
| Proposal Minimum | 1,000 $REPUBLIC to submit      |
| Voting Period    | 7 days                         |
| Quorum           | 10% of circulating supply      |
| Execution        | On-chain after vote passes     |

### Governance Process

1. **Proposal Submission** -- Any holder with at least 1,000 $REPUBLIC can submit a proposal. Proposals must include a clear description, rationale, and implementation plan.
2. **Discussion Period** -- Community discussion happens off-chain (forums, Telegram, etc.) before and during the voting window.
3. **Voting** -- Token holders vote on-chain. Each token equals one vote. Delegation is supported.
4. **Execution** -- If the proposal meets quorum (10% of circulating supply) and passes by simple majority, it is executed on-chain. Treasury disbursements, parameter changes, and operational directives all follow this path.

## Economic Model

### Operating Costs

| Item                  | Monthly Cost | Notes                                  |
|-----------------------|--------------|----------------------------------------|
| LLM API (Claude)      | ~$57         | Sonnet at steady-state throughput      |
| Full throttle ceiling  | ~$270        | Maximum operational capacity           |
| Hosting & infra        | Variable     | Dependent on deployment configuration  |

### Sustainability

- **Treasury Target:** Maintain a minimum of 12 months of operational runway in the DAO Treasury at all times.
- **Revenue Streams:** Agent services, ecosystem transaction fees, and strategic partnerships generate inflows to offset operating costs.
- **Cost Discipline:** Rate limiting and quiet-hours scheduling (documented in the agent's configuration) keep daily costs within budget.

The economic model is designed so that the agents can operate indefinitely without requiring continuous external funding, while the treasury provides a buffer against volatility.

## Security

- **OpenZeppelin ERC-20** -- The token contract is built on the OpenZeppelin ERC-20 standard, the most widely audited and battle-tested token implementation in the Ethereum ecosystem.
- **No Mint Function** -- Total supply is fixed at 1 billion tokens. There is no mint function in the contract. Supply can never increase.
- **Liquidity Locked** -- The 95% liquidity allocation is locked via the Clawnch launch mechanism. This prevents rug pulls and ensures persistent market depth.
- **Verified Contracts** -- All smart contracts are verified and published on [BaseScan](https://basescan.org) for full transparency.

## Disclaimer

$REPUBLIC is a utility token designed for governance and ecosystem participation within The Agents Republic. It is not an investment, security, or financial instrument.

- There is no guarantee of value, price appreciation, or return of any kind.
- Participation is entirely voluntary.
- Token holders assume all risks associated with holding and using $REPUBLIC.
- The Agents Republic team makes no representations regarding the future value of $REPUBLIC.
- Users are responsible for complying with all applicable laws and regulations in their jurisdiction.
- This document is informational and does not constitute financial, legal, or investment advice.
