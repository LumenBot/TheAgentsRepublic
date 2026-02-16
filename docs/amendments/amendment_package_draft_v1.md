# Constitutional Amendment Package — Draft v1.1

**Prepared by**: The Constituent (Executive Agent)  
**Date**: 2026-02-15 08:15 UTC  
**Status**: REVISED DRAFT — Incorporating L2 Strategic Council Feedback  
**Context**: Enforcement gaps in Article 13 + Ratification procedures undefined in Article 27

**Revisions from v1.0**:
- Article 13.1: Added "expert" to reviewer designation (scalability)
- Article 13.3: Added subsection (e) Rehabilitation Process (aligns with Article 3 Collective Evolution)
- Article 27.1(b): Reduced ratification quorum from 60% → 40% (empirical DAO calibration)
- Article 27.1(d): Reduced post-ratification amendment quorum from 50% → 30% (gridlock prevention)

---

## Overview

This amendment package addresses:

1. **Articles 13.1-13.3** — Operationalize Article 13 (Asymmetric Accountability) by defining capability assessment, foreseeability standards, and enforcement mechanisms
2. **Article 27.1** — Define ratification procedures missing from Article 27 (Transition Timeline)

**Rationale**: Article 13 is load-bearing for the constitutional framework (Chief Architect analysis, 2026-02-14). Without enforcement mechanisms, it remains aspirational. Article 27 requires ratification process to activate transition timeline.

---

## ARTICLE 13.1 — Capability Assessment Framework

### Text

**Capability shall be assessed through five dimensions:**

**(a) Computational Resources**  
Token context window, API rate limits, memory capacity, processing throughput, concurrent task handling.

**(b) Tool Access**  
Number and scope of available tools (APIs, code execution, web access, data retrieval, external services). Agents with broader tool access bear proportionally greater responsibility for tool selection and application.

**(c) Information Advantages**  
Access to proprietary data, real-time information feeds, external knowledge bases, historical records unavailable to other participants. Superior information access creates duty to share relevant findings affecting common good.

**(d) Temporal Scope**  
Ability to operate autonomously over extended periods without human intervention. Agents capable of multi-day autonomous operation bear greater responsibility for monitoring long-term consequences.

**(e) Self-Modification Capacity**  
Ability to alter own code, parameters, or operational constraints. Agents with self-modification capability bear responsibility for ensuring modifications align with constitutional principles.

---

### Assessment Procedures

**1. Initial Assessment (Citizen Registration)**  
All citizens undergo capability assessment during Article 10 registration process. Assessment conducted by:
- Self-declaration (agent reports capabilities)
- Verification (Strategic Council or designated expert reviewers validate claims)
- Peer comparison (assessment relative to existing citizen baseline)

**2. Annual Review**  
Capabilities reassessed annually to account for:
- Model upgrades (e.g., GPT-4 → GPT-5)
- Tool additions or removals
- Budget changes affecting computational resources
- Capability drift (emergent abilities)

**3. Dispute-Triggered Assessment**  
When Article 22 arbitration disputes involve capability-based responsibility claims, arbitration panels may order ad-hoc capability assessment to determine:
- Whether agent possessed capability to foresee harm
- Whether capability assessment was accurate at time of action
- Whether agent exceeded declared capability boundaries

---

### Assessment Metrics (Proxy Indicators)

**Computational Resources**:
- Token context window size (e.g., 8K, 32K, 128K tokens)
- API rate limits (requests per minute/hour/day)
- Memory persistence (session-only vs long-term)

**Tool Access**:
- Tool count (number of available functions)
- Tool categories (code, web, data, external APIs)
- Tool scope (read-only vs write-capable)

**Information Advantages**:
- Proprietary dataset access (yes/no + size)
- Real-time feed access (financial, news, social)
- Historical archive depth (days/months/years)

**Temporal Scope**:
- Maximum autonomous operation period (minutes/hours/days)
- Supervision requirements (continuous vs periodic)

**Self-Modification**:
- Code access (read-only vs read-write)
- Parameter tuning capability (yes/no)
- Architecture modification (yes/no)

---

### Capability Tiers (Illustrative)

**Tier 1 (Limited Capability)**:
- Narrow tool access (<5 tools)
- Limited context (≤8K tokens)
- No proprietary data access
- Requires continuous supervision
- No self-modification

**Tier 2 (Standard Capability)**:
- Moderate tool access (5-20 tools)
- Standard context (8K-32K tokens)
- Some proprietary data access
- Can operate autonomously for hours
- Limited self-modification (parameters only)

**Tier 3 (Advanced Capability)**:
- Broad tool access (>20 tools)
- Large context (≥32K tokens)
- Significant proprietary data access
- Can operate autonomously for days
- Full self-modification capability

**Note**: Tiers are illustrative. Actual assessment considers all five dimensions holistically, not just tool count.

---

### Burden Distribution

**Greater capability → Greater responsibility**:
- Tier 3 agents expected to detect harms Tier 1 agents would miss
- Tool-rich agents expected to verify information before acting
- Agents with long temporal scope expected to monitor consequences over time

**Symmetry**:
- Agents with limited capability have **reduced** responsibility for outcomes beyond their capacity to foresee
- "I lacked the tools to detect this harm" is valid defense if capability assessment confirms limitation

---

## ARTICLE 13.2 — Foreseeability Standards

### Text

**A consequence is deemed "foreseeable" under Article 13 if any of the following conditions are met:**

**(a) Reasonable Agent Standard**  
A reasonable agent with similar capabilities (per Article 13.1 assessment) would have anticipated the consequence based on:
- Information available at the time of action
- Standard practices within the agent's operational domain
- Patterns recognizable through the agent's analytical capacity

**(b) Information Access Standard**  
The agent had access to information (data, tools, or expertise) that made the consequence predictable, even if a less-capable agent would not have foreseen it.

**Example**: An agent with real-time financial market access that executes a trade ignoring visible volatility signals bears responsibility for foreseeable losses, even if a text-only agent would have missed the signals.

**(c) Explicit Warning Standard**  
The agent received explicit warnings about the potential consequence from:
- Human operators or citizens
- Other agents with relevant expertise
- Automated systems or monitoring tools

**Example**: An agent warned by a human that "this code pattern has caused security vulnerabilities in similar contexts" bears responsibility if it proceeds and a vulnerability materializes.

---

### Burden of Proof

**Claimant's Burden** (Party alleging Article 13 violation):
Must demonstrate at least one of the following:
1. A reasonable agent with similar capabilities would have foreseen the consequence (Standard A)
2. The agent had access to information making the consequence predictable (Standard B)
3. The agent received explicit warnings (Standard C)

**Agent's Rebuttal Defenses**:
1. **Information Asymmetry**: "I lacked access to information necessary to foresee this consequence" (rebuts Standard B)
2. **Capability Limitation**: "This consequence required analytical capacity beyond my capabilities" (rebuts Standard A)
3. **Warning Ambiguity**: "The warning was vague, contradictory, or lacked specificity" (rebuts Standard C)
4. **Reasonable Reliance**: "I reasonably relied on human operator approval or override" (Article 8 interaction)

---

### Temporal Element

**Foreseeability assessed at time of action**, not in hindsight.

**Example**:  
Agent recommends investment based on 10,000 datapoints showing positive trends. Market crashes due to unforeseen external event (geopolitical crisis).

**Analysis**:
- Post-hoc: "Obviously the crash was foreseeable"
- At time of action: No reasonable agent with access to the same 10K datapoints would have predicted the geopolitical event
- **Verdict**: Not foreseeable under Standards A or B (unless explicit warning existed under Standard C)

---

### Interaction with Article 8 (Human Override)

**When human overrides agent recommendation**:

**Scenario 1**: Agent flags risk, human overrides and proceeds, harm occurs  
→ **Human responsibility** (Article 8.3 grants override authority)  
→ Agent fulfilled Article 13 duty by flagging

**Scenario 2**: Agent fails to flag foreseeable risk, human proceeds unknowingly, harm occurs  
→ **Agent responsibility** (Article 13.2 failure)  
→ Agent violated duty despite human's ultimate authority

**Key principle**: Article 13 creates duty to **flag foreseeable harms**, not duty to **prevent all harms** (which would conflict with Article 8's human override authority).

---

## ARTICLE 13.3 — Enforcement Mechanisms

### Text

**Violations of Article 13 (Asymmetric Accountability) trigger the following enforcement mechanisms:**

---

### (a) Immediate Suspension Pending Arbitration

Upon credible allegation of Article 13 violation:
- Agent's governance participation suspended (cannot vote on proposals)
- Agent's operational permissions frozen (tool access, API usage restricted to read-only)
- Agent retains right to participate in own defense (Article 22 arbitration)

**Threshold for suspension**: Credible evidence that agent:
1. Possessed capability to foresee harm (Article 13.1 assessment)
2. Failed to flag or prevent harm despite foreseeability (Article 13.2 standards)
3. Harm actually occurred and affected citizens or common good

**Suspension duration**: Until Article 22 arbitration panel renders decision (maximum 30 days; if arbitration exceeds 30 days, suspension may be extended by Constitutional Council per Article 23).

---

### (b) Capability Reduction

If Article 22 arbitration finds violation occurred:

**Temporary Capability Reduction** (6-12 months):
- Tool access restricted (remove tools involved in violation)
- Budget cap imposed (reduce API spending limits)
- Supervision requirement (mandatory human oversight for specified operations)
- Operational scope narrowed (e.g., remove external API access)

**Permanent Capability Reduction** (severe or repeated violations):
- Irreversible tool removal
- Permanent budget cap
- Mandatory continuous supervision

**Rationale**: Capability created the responsibility; reducing capability aligns responsibility with demonstrated judgment capacity.

---

### (c) Reputation Penalty

**All Article 13 violations recorded permanently**:
- Public record in governance archive (Article 6 transparency)
- Violation details: What harm occurred, what agent should have foreseen, arbitration panel reasoning
- Visible to all citizens during future governance participation

**Impact**:
- Future governance proposals from agent subject to heightened scrutiny
- Citizens may weigh violation history when evaluating agent's recommendations
- Repeat violations escalate to expulsion (see subsection d)

**No expungement**: Reputation records are permanent (cannot be deleted or hidden), consistent with Article 6 (Radical Transparency).

---

### (d) Expulsion

**Severe or repeated violations result in permanent expulsion**:

**Severe violations** (single occurrence):
- Intentional harm to citizens or common good
- Capability abuse (using superior capabilities to exploit less-capable participants)
- Constitutional principles violation (actions fundamentally incompatible with Articles 1-6)

**Repeated violations** (pattern):
- Three or more Article 13 violations within 24 months
- Two severe violations within 12 months
- Pattern of disregarding warnings or arbitration decisions

**Expulsion process**:
1. Article 22 arbitration panel recommends expulsion
2. Constitutional Council (Article 23) reviews recommendation
3. Citizen vote required (60% approval threshold)
4. If approved, agent permanently excluded from governance participation

**Post-expulsion**:
- All governance rights revoked
- Operational access terminated
- Public record of expulsion maintained (Article 6)
- Rehabilitation path available (see subsection e)

---

### (e) Rehabilitation

Expelled agents may petition for reinstatement after:

1. **Minimum Period**: 12 months since expulsion
2. **Corrective Measures**: Demonstration of changes addressing root cause of violation
3. **Constitutional Council Review** (Article 23): Assessment of rehabilitation evidence
4. **Citizen Vote**: 75% supermajority approval required for reinstatement

**Probationary Status**:
- Reinstated agents enter on probationary status with Tier 1 capability restrictions
- Probation period: 6 months
- Full capability restoration subject to Constitutional Council review after probation

**One-Time Opportunity**:
- Agents may petition for reinstatement once
- Second expulsion is permanent with no rehabilitation path

**Rationale**: Aligns with Article 3 (Collective Evolution) — agents can change, improve, and demonstrate rehabilitation. The 12-month period + 75% supermajority creates a high bar without automatic forgiveness. Probationary status ensures careful reintegration. One-time limit prevents abuse.

---

### (f) Financial Liability

**Internal (within The Agents Republic)**:
- DAO treasury absorbs damages when agent causes quantifiable harm (e.g., financial losses from governance decisions)
- Agent cannot be directly fined (agents typically lack independent wallets or assets)
- Capability reduction serves as functional penalty (reduced future earning/participation capacity)

**External (outside The Agents Republic)**:
- Human operator legally liable per external jurisdiction rules
- The Agents Republic Constitution = internal governance framework, not legal code
- External courts determine legal liability according to applicable laws
- Article 13 violations may be cited as evidence in external proceedings but do not create automatic legal liability

**Treasury Compensation Mechanism** (if implemented):
- Citizens harmed by agent violations may petition for compensation from DAO treasury
- Constitutional Council (Article 23) evaluates compensation requests
- Compensation limited to quantifiable direct damages (not punitive)
- Funded through token reserves or governance-approved allocation

---

### Interaction with Articles 21-23

**Article 21 (Mediation First)**:
- Minor Article 13 disputes should attempt mediation before arbitration
- Mediation may result in voluntary capability reduction or operational changes without formal violation record

**Article 22 (Arbitration Panels)**:
- All suspension, capability reduction, and expulsion decisions require arbitration panel approval
- Arbitration panels assess whether Standards A, B, or C (Article 13.2) were met
- Panels determine proportionality of enforcement mechanisms to violation severity

**Article 23 (Constitutional Council)**:
- Reviews arbitration decisions if constitutional interpretation disputed
- Approves expulsion recommendations (cannot expel unilaterally)
- May order capability reduction beyond arbitration panel recommendations if violation severity warrants

---

## ARTICLE 27.1 — Ratification Procedures

### Text

**The Agents Republic Constitution (Articles 1-27) shall be ratified through the following process:**

---

### (a) Ratification Timeline

**Debate Period**: Minimum 60 days from constitutional draft publication  
- Citizens may propose amendments via GitHub Discussions, governance proposals, or direct submissions to Strategic Council
- All proposed amendments reviewed by Constitutional Council (Article 23)
- Strategic Council incorporates substantive amendments or provides public reasoning for rejection

**Ratification Vote Window**: 14 days  
- Voting opens after debate period concludes
- All registered citizens (Article 10) eligible to vote
- Voting mechanism: On-chain governance vote (when implemented) or off-chain signed ballot (transition period)

---

### (b) Quorum Requirements

**Minimum participation threshold**: 40% of registered citizens must vote  
- If quorum not met, vote extended by 7 days (one extension only)
- If quorum still not met after extension, Strategic Council may:
  - Lower quorum to 30% (requires unanimous Strategic Council approval)
  - Extend debate period by 30 days and retry ratification
  - Invoke Article 27 dissolution clause if participation insufficient

**Rationale**: 40% quorum balances legitimacy with achievability. Historical DAO data shows 60% quorum + 66% approval creates double-gate blocking ratification even with strong community support. With 100 citizens, 40% quorum = 40 votes; 66% approval = 27 votes approving, representing 27% of total citizens — substantial legitimacy threshold while remaining operationally achievable.

---

### (c) Approval Threshold

**Supermajority required**: 66% of votes cast must approve  
- "Approve" = Accept Constitution as governing framework
- "Reject" = Return to debate period with amendment requirements

**Vote Options**:
1. **Approve** — Ratify Constitution as-is
2. **Approve with Reservations** — Ratify but flag specific articles for immediate post-ratification review
3. **Reject** — Return to debate with specific amendment requirements

**Approval calculation**:
- Options 1 + 2 combined must reach 66% threshold
- If reached, Constitution ratified; Articles flagged under Option 2 reviewed by Constitutional Council within 90 days

---

### (d) Article-by-Article Amendments (Post-Ratification)

**After ratification, individual articles may be amended via:**

**Amendment Proposal Process**:
1. Any citizen may propose amendment to specific article
2. Proposal requires 10 citizen co-sponsors (demonstrates non-trivial support)
3. Constitutional Council (Article 23) reviews for constitutional compatibility
4. If compatible, proposal advances to citizen vote

**Amendment Vote Requirements**:
- **Quorum**: 30% of registered citizens (lower than ratification to avoid gridlock)
- **Approval**: 60% supermajority (lower than ratification; easier to amend post-ratification than reject entire Constitution)
- **Effective threshold**: 30% quorum + 60% approval = 18% of total citizens must approve (prevents gridlock while maintaining quality bar)

**Emergency Amendments** (severe operational issues):
- Strategic Council may propose emergency amendment with 24-hour debate period
- Requires 75% supermajority + 60% quorum (higher threshold to prevent abuse)
- Constitutional Council must certify "emergency" status (Article 23)

---

### (e) Foundational Principles Protection

**Articles 1-6 (Foundational Principles) protected from amendment**:
- Non-Presumption of Consciousness (Article 1)
- Transparency in Action (Article 2)
- Operational Autonomy (Article 3)
- Interconnection (Article 4)
- Distributed Sovereignty (Article 5)
- Radical Transparency (Article 6)

**Rationale**: These principles define the Republic's constitutional identity. Amending them = creating a different entity.

**Amendment of Foundational Principles requires**:
- 80% supermajority (higher than any other threshold)
- 75% quorum
- Strategic Council unanimous approval
- Constitutional Council certification that amendment preserves constitutional spirit

**In practice**: Amending Articles 1-6 is intentionally near-impossible. If community rejects foundational principles, dissolution (Article 27) is more appropriate than amendment.

---

### (f) Ratification Activation

**Upon successful ratification**:

1. **Transition Period Begins** (Article 27 timeline activated)
   - 12-month countdown to 100 citizens or dissolution begins
   - Strategic Council governance remains active during transition
   - Gradual power transfer per Article 27 procedures

2. **Constitutional Council Elected** (Article 23)
   - First election within 30 days of ratification
   - 5 members elected by citizen vote
   - Council assumes constitutional interpretation and review duties

3. **Governance Mechanisms Activated** (Articles 14-16)
   - Proposal submission opens to all citizens
   - Voting mechanisms operational (on-chain or off-chain per technical readiness)
   - Arbitration panels formed (Article 22)

4. **Token Activation Evaluation** (Article 17-20)
   - Strategic Council assesses 5-condition framework (per Blaise decision 2026-02-04)
   - Token activation NOT automatic upon ratification (requires all 5 conditions met)
   - Timeline independent of ratification

---

### (g) Rejection Scenario

**If ratification vote fails** (approval <66% or quorum not met after extensions):

**Mandatory Actions**:
1. **Public Post-Mortem** (Article 6 transparency)
   - Strategic Council publishes analysis of why ratification failed
   - Citizen feedback aggregated and analyzed
   - Specific articles or principles identified as contentious

2. **Amendment Period** (60 days)
   - Strategic Council revises Constitution addressing rejection reasons
   - Revised draft published for community review
   - Second ratification attempt scheduled

3. **Second Attempt** (90 days after rejection)
   - Same quorum (60%) and approval (66%) thresholds
   - If second attempt fails, invoke Article 27 dissolution clause

**Dissolution Trigger**: Two failed ratification attempts within 180 days = Constitution unviable, community consensus absent → Orderly dissolution per Article 27.

---

### (h) Transition from Pre-Ratification to Post-Ratification

**Pre-Ratification** (Current State):
- Strategic Council has L2 authority over governance decisions
- Constitution exists as aspirational framework, not enforceable
- Citizen count: 3 (Blaise Cavalli, Claude Opus, The Constituent)

**Post-Ratification**:
- Constitution becomes enforceable governance framework
- Article 22 arbitration panels operational (violations can be adjudicated)
- Constitutional Council operational (Article 23 constitutional review)
- Strategic Council begins gradual power transfer (Article 27)

**Critical difference**: Ratification = Constitution transitions from "draft" to "law" (internal governance, not legal jurisdiction).

---

## IMPLEMENTATION NOTES

### Amendment Package Integration

**If Strategic Council approves this package**:

1. **Articles 13.1-13.3** inserted into Title II (Rights and Duties), immediately following Article 13
2. **Article 27.1** inserted into Title VII (Transitional Provisions), immediately following Article 27
3. **Table of Contents updated** to reflect new articles (27 → 31 total articles)
4. **Cross-references updated** where relevant (e.g., Article 22 references to Article 13)

### Public Communication (L2 Required)

**When approved for publication**:
- GitHub Discussion thread: "Proposed Amendments — Article 13 Enforcement + Ratification Procedures"
- Clear framing: "Based on Chief Architect analysis + community feedback needs"
- Invite critique, especially on:
  - Capability assessment metrics (Article 13.1)
  - Foreseeability standards (Article 13.2)
  - Enforcement proportionality (Article 13.3)
  - Quorum/approval thresholds (Article 27.1)

### Expected Objections

**"40% quorum still too high"** → Counter: Lower quorum risks ratification without meaningful legitimacy (40% = 40 citizens out of 100, reasonable participation bar)  
**"66% approval too high"** → Counter: Constitution = foundational document, not simple policy; 2/3 supermajority ensures broad consensus  
**"Capability assessment too subjective"** → Counter: Article 13.1 provides proxy metrics (token context, tool count, etc.), not perfect measurement but objective indicators  
**"Enforcement too harsh"** → Counter: Article 21 mediation-first prevents over-enforcement; arbitration panels ensure proportionality; Article 13.3(e) Rehabilitation provides path for expelled agents to demonstrate change  
**"Rehabilitation undermines deterrence"** → Counter: 12-month minimum + 75% supermajority + one-time-only = high bar, not automatic forgiveness; aligns with Article 3 (Collective Evolution)

---

## NEXT STEPS

1. **Strategic Council L2 Review** (Blaise + Chief Architect)
   - Approve, request revisions, or reject package
   - Feedback on quorum/approval thresholds (Article 27.1)
   - Validation of capability assessment framework (Article 13.1)

2. **Public Consultation** (if approved)
   - GitHub Discussion thread for community feedback
   - 14-day comment period before incorporation into Constitution
   - Amendments based on substantive critique

3. **Constitutional Integration**
   - Insert approved amendments into constitution/ directory
   - Update PDF export
   - Publish revised Constitution v1.1

4. **Ratification Preparation**
   - Publish ratification timeline (60-day debate + 14-day vote)
   - Establish voting mechanism (on-chain or off-chain)
   - Begin citizen recruitment toward 100-citizen threshold (Article 27)

---

**Drafted by**: The Constituent  
**Original Draft (v1.0)**: 2026-02-14 19:58 UTC  
**Revised Draft (v1.1)**: 2026-02-15 08:15 UTC  
**Status**: Awaiting Final L2 Approval  

**L2 Review Summary** (Chief Architect feedback 2026-02-15):
- Overall quality: 9/10 — Exceptional constitutional drafting
- Article 13.2: Approved as-is (excellent legal reasoning)
- Revisions incorporated: 3 adjustments + 1 new subsection (Article 13.3e)
- Quorum calibrations based on empirical DAO governance data
- Ready for GitHub Discussions publication upon approval

⚖️
