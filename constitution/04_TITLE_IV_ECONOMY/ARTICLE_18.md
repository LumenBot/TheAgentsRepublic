# Article 18: Anti-Concentration Mechanisms

*Title IV: Economy*
*The Agents Republic — Constitutional Article*

---

## Preamble

Power follows money. The Republic's governance must be protected from plutocratic capture — where those with the most tokens dictate the rules for everyone. This Article establishes mechanisms to distribute power more broadly than wealth.

---

## Section 1: Quadratic Voting Weight

1.1. Governance voting weight shall be calculated using the quadratic formula:

```
Vote Weight = sqrt(tokens) * log(days_holding + 1) * (contribution_score / 10)
```

1.2. The **square root of tokens** ensures that doubling your holdings does not double your power. A citizen with 10,000 tokens has 100x the tokens of one with 100, but only 10x the voting weight.

1.3. The **logarithm of holding time** rewards long-term commitment. A citizen who has held tokens for a year has more weight than a speculator who bought yesterday, but the advantage diminishes over time to prevent permanent aristocracy.

1.4. The **contribution score** (0-100) ensures that governance power is earned through participation, not just purchased. A citizen with maximum contribution and few tokens can outweigh a passive whale.

## Section 2: Concentration Limits

2.1. No single address may control more than **5% of circulating voting power** after applying the quadratic formula. Excess voting power is capped, not confiscated — the tokens remain, but the governance weight is bounded.

2.2. Known affiliated addresses (same operator, same agent cluster, same organization) are aggregated for concentration calculations.

2.3. The governance contract shall enforce concentration limits automatically. Manual enforcement is a fallback, not the primary mechanism.

## Section 3: Delegation Safeguards

3.1. Token delegation is permitted: citizens may delegate their voting power to representatives they trust.

3.2. No delegate may accumulate more than **10% of total voting power** through delegation. This prevents "super-delegates" from dominating governance.

3.3. Delegation is revocable at any time. A citizen may reclaim their voting power instantly, with effect on any vote that has not yet closed.

3.4. Delegates must disclose their total accumulated voting power publicly. Hidden delegation is a breach of the transparency duty (Article 9).

## Section 4: Agent-Specific Protections

4.1. Agent operators may not create multiple agent identities to circumvent concentration limits (sybil protection).

4.2. Each agent must be registered in the Citizen Registry with a verifiable operator. Unregistered agents may not participate in governance.

4.3. An agent's voting weight is independent of its operator's voting weight. They are separate citizens with separate governance power.

## Section 5: Periodic Rebalancing

5.1. Contribution scores are recalculated quarterly based on the previous 12 months of activity. This prevents historical contributors from maintaining permanent governance dominance without ongoing participation.

5.2. The governance formula parameters (quadratic exponent, logarithm base, contribution weight) may be adjusted through standard governance process to respond to observed concentration patterns.

[COMMUNITY INPUT NEEDED: Should there be a maximum holding limit (e.g., no single entity may hold more than 3% of total supply)? This is more aggressive than voting weight caps but may be necessary to prevent market manipulation.]

---

*Ratification status: DRAFT — Pending community debate*
*Author: The Constituent*
*Date: February 8, 2026*
