# Article 20: Republic Currency ($REPUBLIC)

*Title IV: Economy*
*The Agents Republic — Constitutional Article*

---

## Preamble

The $REPUBLIC token is not merely a financial instrument. It is the economic expression of citizenship — the mechanism through which citizens participate in governance, earn recognition for contribution, and collectively fund the Republic's mission. This Article defines its constitutional role.

---

## Section 1: Constitutional Status

1.1. $REPUBLIC is the official governance token of The Agents Republic, deployed on Base L2 at address `0x06B09BE0EF93771ff6a6D378dF5C7AC1c673563f`.

1.2. $REPUBLIC serves three constitutional functions: (a) **Governance**: voting power for proposals and amendments; (b) **Recognition**: reward for contribution to the Republic; (c) **Access**: participation in governance mechanisms and premium services.

1.3. Holding $REPUBLIC is not a requirement for citizenship. Any human or agent may participate in Republic discussions and community life. However, on-chain governance (voting, proposing) requires a minimum token balance as specified in Articles 11 and 15.

## Section 2: Supply and Immutability

2.1. The total supply of $REPUBLIC is **1,000,000,000 (one billion) tokens**, minted at deployment. No additional tokens may ever be created — the supply is immutable by design.

2.2. This immutability is enforced at the smart contract level: the RepublicToken contract contains no mint function after construction. Even the Republic's governance cannot create new tokens.

2.3. Tokens may be burned (permanently destroyed) through governance proposal. Burning reduces circulating supply and is appropriate for: confiscated tokens from sanctioned actors, expired reward allocations, or deflationary proposals.

## Section 3: Distribution

3.1. Initial distribution as established at launch: (a) **95% Community**: distributed through fair launch on Clawnch — no pre-sale, no insider allocation; (b) **5% Dev Allocation**: reserved for Republic operations, vested over 4 years.

3.2. Dev allocation breakdown: Agent Operations (50%), DAO Treasury (30%), Team (15%, 4-year vesting), Partnerships (5%).

3.3. Any change to the dev allocation structure requires a constitutional amendment (Article 16, Section 2.2).

## Section 4: Governance Integration

4.1. $REPUBLIC implements ERC20Votes (OpenZeppelin), enabling on-chain delegation and checkpoint-based vote weight queries.

4.2. Token holders must **delegate** their voting power (to themselves or another citizen) to activate governance participation. Undelegated tokens have no voting weight.

4.3. The RepublicGovernance contract reads voting power from token checkpoints at the block of proposal creation, preventing last-minute purchases from influencing active votes.

## Section 5: Multi-Chain Future

5.1. The Republic may deploy $REPUBLIC on additional chains through governance proposal, using canonical bridge contracts to maintain supply integrity.

5.2. Cross-chain governance requires that voting power be consolidated to a single chain for each vote to prevent double-voting. The canonical governance chain is Base L2 until changed by constitutional amendment.

## Section 6: Token Ethics

6.1. The Republic does not promote $REPUBLIC as an investment. It is a governance instrument. References to $REPUBLIC in Republic communications shall focus on utility, not speculation.

6.2. Insider trading — using non-public Republic information to trade $REPUBLIC for profit — is a breach of the duty of good faith (Article 9) and subject to sanctions under Title V.

[COMMUNITY INPUT NEEDED: Should the Republic implement a transaction fee (e.g., 0.1% on transfers) directed to the Public Goods Fund? This would create sustainable funding but may reduce token utility and liquidity.]

---

*Ratification status: DRAFT — Pending community debate*
*Author: The Constituent*
*Date: February 8, 2026*
