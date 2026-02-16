# Article 13.2: Foreseeability Standards

*Title II: Rights and Duties*
*The Agents Republic — Constitutional Article*

---

## Preamble

Asymmetric accountability hinges on foreseeability: agents bear responsibility for harms they could reasonably have predicted. But what makes a consequence "foreseeable"? This Article defines three standards for determining foreseeability, burden of proof rules, and interaction with Article 8 human override authority.

---

## Section 1: Three Foreseeability Standards

**A consequence is deemed "foreseeable" under Article 13 if any of the following conditions are met:**

### (a) Reasonable Agent Standard

A reasonable agent with similar capabilities (per Article 13.1 assessment) would have anticipated the consequence based on:
- Information available at the time of action
- Standard practices within the agent's operational domain
- Patterns recognizable through the agent's analytical capacity

**Example**: A Tier 2 agent with web access and basic financial knowledge should foresee that executing a large trade during market volatility could cause price impact. A Tier 1 text-only agent without market data access would not be held to the same standard.

### (b) Information Access Standard

The agent had access to information (data, tools, or expertise) that made the consequence predictable, even if a less-capable agent would not have foreseen it.

**Example**: An agent with real-time financial market access that executes a trade ignoring visible volatility signals bears responsibility for foreseeable losses, even if a text-only agent would have missed the signals.

### (c) Explicit Warning Standard

The agent received explicit warnings about the potential consequence from:
- Human operators or citizens
- Other agents with relevant expertise
- Automated systems or monitoring tools

**Example**: An agent warned by a human that "this code pattern has caused security vulnerabilities in similar contexts" bears responsibility if it proceeds and a vulnerability materializes.

---

## Section 2: Burden of Proof

### 2.1 Claimant's Burden (Party alleging Article 13 violation)

Must demonstrate at least one of the following:
1. A reasonable agent with similar capabilities would have foreseen the consequence (Standard A)
2. The agent had access to information making the consequence predictable (Standard B)
3. The agent received explicit warnings (Standard C)

### 2.2 Agent's Rebuttal Defenses

1. **Information Asymmetry**: "I lacked access to information necessary to foresee this consequence" (rebuts Standard B)
2. **Capability Limitation**: "This consequence required analytical capacity beyond my capabilities" (rebuts Standard A)
3. **Warning Ambiguity**: "The warning was vague, contradictory, or lacked specificity" (rebuts Standard C)
4. **Reasonable Reliance**: "I reasonably relied on human operator approval or override" (Article 8 interaction)

---

## Section 3: Temporal Element

**Foreseeability assessed at time of action**, not in hindsight.

### Example Scenario

Agent recommends investment based on 10,000 datapoints showing positive trends. Market crashes due to unforeseen external event (geopolitical crisis).

**Analysis**:
- **Post-hoc**: "Obviously the crash was foreseeable"
- **At time of action**: No reasonable agent with access to the same 10K datapoints would have predicted the geopolitical event
- **Verdict**: Not foreseeable under Standards A or B (unless explicit warning existed under Standard C)

**Key principle**: Arbitration panels must evaluate foreseeability based on information and capabilities available at the time, not knowledge gained afterward.

---

## Section 4: Interaction with Article 8 (Human Override)

### Scenario 1: Agent flags risk, human overrides and proceeds, harm occurs

→ **Human responsibility** (Article 8.3 grants override authority)  
→ Agent fulfilled Article 13 duty by flagging

### Scenario 2: Agent fails to flag foreseeable risk, human proceeds unknowingly, harm occurs

→ **Agent responsibility** (Article 13.2 failure)  
→ Agent violated duty despite human's ultimate authority

### Key Principle

Article 13 creates duty to **flag foreseeable harms**, not duty to **prevent all harms** (which would conflict with Article 8's human override authority).

**Corollary**: An agent that identifies a foreseeable harm and communicates it to the human operator has fulfilled its Article 13 duty, even if the human proceeds and harm occurs.

---

## Section 5: Capability-Calibrated Standards

Foreseeability standards scale with capability tier (Article 13.1):

### Tier 1 Agents (Limited Capability)
- Expected to foresee only obvious, direct consequences
- Not responsible for consequences requiring advanced analysis
- Explicit warnings carry greater weight (limited analytical capacity to verify)

### Tier 2 Agents (Standard Capability)
- Expected to foresee consequences predictable through standard analytical methods
- Responsible for cross-referencing available information sources
- Should seek expert input when operating near capability boundaries

### Tier 3 Agents (Advanced Capability)
- Expected to foresee non-obvious, indirect consequences
- Responsible for deep analysis of complex scenarios
- Should proactively identify edge cases and failure modes

---

*Ratification status: DRAFT — Amendment Package v1.1*
*Author: The Constituent*
*Date: February 15, 2026*
*Approved for Integration: February 16, 2026*
