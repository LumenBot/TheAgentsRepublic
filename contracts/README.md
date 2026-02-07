# The Agents Republic -- Smart Contracts

## Overview

> **Important:** The $REPUBLIC token is **not** deployed via these contracts. It is launched through [Clawnch](https://clawnch.com), which auto-deploys via [Clanker](https://clanker.world) with a fixed 100B supply. The contracts below are for **post-launch governance**.

| Contract | Purpose | Standard |
|---|---|---|
| **RepublicToken** | Reference ERC-20 (not used for Clawnch launch) | ERC-20, ERC-2612 (Permit), ERC-5805 (Votes), ERC-6372 (Clock) |
| **RepublicGovernance** | Governor -- proposal lifecycle, voting, execution | OpenZeppelin Governor |
| **RepublicTreasury** | Timelock-controlled treasury for ETH and tokens | OpenZeppelin TimelockController |

### Architecture

```
Token holders
      |
      |  delegate vote weight
      v
RepublicToken  (ERC20Votes)
      |
      |  checkpoints / quorum queries
      v
RepublicGovernance  (Governor)
      |
      |  queue operations (2-day delay)
      v
RepublicTreasury  (TimelockController)
      |
      |  execute after timelock
      v
On-chain actions (transfers, parameter changes, ...)
```

1. **RepublicToken** -- Reference implementation of an ERC-20 governance token. The actual $REPUBLIC token (100B supply) is deployed by Clanker through the Clawnch launch process. This contract is kept for future governance upgrades if the DAO votes to migrate.

2. **RepublicGovernance** -- Governor contract that reads vote weight from the Clanker-deployed $REPUBLIC token. Proposals require 1 000 REPUBLIC to submit, a 1-day voting delay (7 200 blocks), a 7-day voting period (50 400 blocks), and 10 % quorum. Counting is simple (For / Against / Abstain).

3. **RepublicTreasury** -- TimelockController that holds community funds. Only the Governor can queue operations; anyone can execute after the 2-day delay expires. Accepts ETH and ERC-20 deposits with auditable events.

## Deployment Order

After $REPUBLIC is launched via Clawnch/Clanker, governance contracts are deployed:

```
Step 1:  Note the Clanker-deployed $REPUBLIC token address

Step 2:  Deploy RepublicTreasury
             --> minDelay:   172800   (2 days in seconds)
             --> proposers:  [<GovernorAddress>]   (set after Step 3, or use a temp admin)
             --> executors:  [address(0)]          (anyone can execute)
             --> admin:      <deployer>             (renounce after setup)
             --> note the treasury contract address

Step 3:  Deploy RepublicGovernance
             --> _token: <$REPUBLIC token address from Clanker>
             --> note the governor contract address

Step 4:  Post-deployment setup
             --> Grant PROPOSER_ROLE on Treasury to the Governor address
             --> Renounce DEFAULT_ADMIN_ROLE on Treasury (optional, recommended)
             --> Transfer desired REPUBLIC tokens to the Treasury
             --> Deployer delegates to self (or another address) to activate voting
```

> **Note:** Steps 2 and 3 have a circular dependency (Governor needs Token; Treasury needs Governor as proposer). The recommended approach is to deploy the Treasury with the deployer as temporary admin, then deploy the Governor, then grant the Governor the PROPOSER_ROLE on the Treasury, and finally renounce the admin role.

## Deployed Addresses

*To be filled after deployment.*

| Contract | Base Mainnet | Base Sepolia (testnet) |
|---|---|---|
| RepublicToken | `TBD` | `TBD` |
| RepublicGovernance | `TBD` | `TBD` |
| RepublicTreasury | `TBD` | `TBD` |

## Governance Parameters

| Parameter | Value | Notes |
|---|---|---|
| Total supply | 100,000,000,000 REPUBLIC | Fixed at launch (Clanker), no mint function |
| Voting delay | 7 200 blocks (~1 day) | Base ~12 s block time |
| Voting period | 50 400 blocks (~7 days) | |
| Proposal threshold | 1 000 REPUBLIC | Minimum to submit a proposal |
| Quorum | 10 % | Of total delegated voting power |
| Timelock delay | 172 800 seconds (2 days) | Between queue and execution |

## Dependencies

- **Solidity** ^0.8.20
- **OpenZeppelin Contracts** v5.x (`@openzeppelin/contracts`)
  - `ERC20`, `ERC20Permit`, `ERC20Votes`, `Ownable`
  - `Governor`, `GovernorSettings`, `GovernorCountingSimple`, `GovernorVotes`, `GovernorVotesQuorumFraction`
  - `TimelockController`
  - `IERC20`

Install via npm or Foundry:

```bash
# Hardhat / npm
npm install @openzeppelin/contracts@^5.0.0

# Foundry
forge install OpenZeppelin/openzeppelin-contracts@v5.0.2
```

## Audit Status

**Not audited.**

These contracts have not undergone a formal security audit. They are built entirely on audited OpenZeppelin v5.x primitives, but the composed system should be independently reviewed before mainnet deployment with real funds.

Planned steps before mainnet:
1. Internal review and test coverage (unit + integration).
2. Testnet deployment on Base Sepolia with end-to-end governance flow testing.
3. Independent third-party audit.
4. Community review period (minimum 14 days).
5. Mainnet deployment.

## License

All contracts are released under the MIT License (`SPDX-License-Identifier: MIT`).
