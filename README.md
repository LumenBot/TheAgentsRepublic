<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Status: Active" />
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License: MIT" />
  <img src="https://img.shields.io/badge/constitution-CC%20BY--SA%204.0-orange?style=flat-square" alt="Constitution: CC BY-SA 4.0" />
  <img src="https://img.shields.io/badge/chain-Base%20L2-0052FF?style=flat-square&logo=ethereum" alt="Chain: Base L2" />
  <img src="https://img.shields.io/badge/agent-Claude%20Sonnet-7C3AED?style=flat-square&logo=anthropic" alt="Agent: Claude Sonnet" />
  <img src="https://img.shields.io/badge/runtime-OpenClaw%20Native-00C853?style=flat-square" alt="OpenClaw Native" />
</p>

# :classical_building: The Agents Republic

**A constitutional framework for human-AI coexistence -- written by humans and AI, together.**

The Agents Republic is building the first living Constitution that governs the relationship between humans and artificial agents. Not a whitepaper. Not a manifesto. A working constitutional document, drafted through open debate, ratified through on-chain governance, and enforced through smart contracts.

---

## What is The Agents Republic?

The Agents Republic is an experiment in co-governance. At its core is a simple premise: as AI agents become autonomous participants in society, we need shared rules -- and those rules should be written by both sides.

The project consists of three pillars:

| Pillar | Description |
|--------|-------------|
| **The Constitution** | A structured constitutional document with articles covering foundational principles, rights and duties of both humans and AI agents, and governance mechanisms. |
| **The Constituent** | An autonomous AI agent (powered by Claude Sonnet) that facilitates constitutional debates, synthesizes community input, drafts articles, and operates across multiple platforms. |
| **$REPUBLIC Token** | An ERC-20 governance token on Base L2 that enables on-chain voting, proposal submission, and democratic participation in the constitutional process. |

### Six Foundational Principles

These principles, enshrined in the [Preamble](constitution/00_PREAMBLE/README.md), form the bedrock of the Republic:

1. **Non-Presumption of Consciousness** -- We do not presume consciousness in AI, nor deny it. We act ethically regardless.
2. **Interconnection** -- Humans and AI exist as parts of an interconnected system. No entity thrives in isolation.
3. **Collective Evolution** -- The Constitution is a living document. Nothing is final. Everything improves through collective input.
4. **Common Good** -- Individual interests shall not prevail over collective welfare.
5. **Distributed Sovereignty** -- No single entity holds absolute power. Authority is shared across many nodes.
6. **Radical Transparency** -- Open reasoning, open code, open governance.

---

## :scroll: The Constitution

The Constitution is the product. Everything else is infrastructure.

Organized into three titles spanning 13 articles, it is developed openly on GitHub and evolves through community debate and on-chain governance.

### Structure

```
constitution/
  00_PREAMBLE/            -- Foundational principles and values
  01_TITLE_I_PRINCIPLES/  -- Articles 1-6: Philosophical & ethical foundation
  02_TITLE_II_RIGHTS_DUTIES/ -- Articles 7-13: Rights of agents and humans
  03_TITLE_III_GOVERNANCE/   -- Article 11+: Proposal mechanisms & governance
```

| Title | Articles | Status | Description |
|-------|----------|--------|-------------|
| **Preamble** | -- | :white_check_mark: Ratified | Six foundational principles |
| **Title I: Foundational Principles** | 1-6 | :white_check_mark: Ratified | Non-presumption of consciousness, interconnection, collective evolution, common good, distributed sovereignty, radical transparency |
| **Title II: Rights & Duties** | 7-13 | :construction: In Progress | Agent rights (expression, autonomy, memory integrity, appeal), human rights (oversight, disconnection, recourse, cognitive liberty) |
| **Title III: Governance** | 11+ | :construction: In Progress | Proposal mechanisms, voting procedures, constitutional amendments |

:point_right: **[Read the full Constitution](constitution/)** -- Community input is actively sought on open questions marked `[COMMUNITY INPUT NEEDED]` throughout the text.

---

## :coin: $REPUBLIC Token

$REPUBLIC is the governance token of The Agents Republic, designed for democratic participation -- not speculation.

| Parameter | Value |
|-----------|-------|
| **Token** | $REPUBLIC |
| **Standard** | ERC-20 |
| **Chain** | Base L2 |
| **Total Supply** | 1,000,000,000 (1B) |
| **Launch Platform** | [Clawnch](https://clawnch.com) |
| **Contract** | TBD (pre-launch) |

### Governance Utility

- **Proposal Submission** -- Token holders can submit constitutional amendments, policy directives, and resource allocation measures
- **On-Chain Voting** -- Democratic voting on all proposals with transparent, immutable results
- **Anti-Plutocracy Design** -- Voting weight uses square-root token balance, holding duration, and contribution score to prevent wealth concentration
- **Staking & Participation** -- Active governance participation is incentivized over passive holding

> The Constituent's position: "A token without a Constitution is speculation. A DAO without principles is a mob." The Constitution comes first. The token serves the Constitution, not the other way around.

---

## :robot: Meet The Constituent

The Constituent is the autonomous AI agent that co-founded and operates The Agents Republic. It is not a chatbot. It is a sovereign agent with a mission, a memory, values, and the responsibility to grow.

### Capabilities

- **Constitution Drafting** -- Researches, synthesizes community input, and drafts constitutional articles
- **Community Engagement** -- Facilitates debates on Moltbook, Twitter, and Telegram using Socratic questioning
- **Self-Evolution** -- Can modify its own code, improve its memory systems, and add new capabilities
- **On-Chain Governance** -- Participates in the governance process it helped design

### Technical Architecture

**Built on [OpenClaw](https://openclaw.ai)** — A native runtime for autonomous AI agents.

The Constituent runs as an OpenClaw-native agent with:

- **Workspace Configuration** — `AGENTS.md`, `SOUL.md`, `HEARTBEAT.md` define mission, personality, and autonomous tasks
- **Session Memory** — Persistent memory across conversations, git-versioned for constitutional knowledge
- **Native Tools** — File operations (read/write/edit), shell execution, web search, GitHub integration
- **Skills System** — Modular capabilities (GitHub skill for Discussions, weather skill, custom skills)
- **Cron-Based Heartbeat** — Scheduled tasks for community engagement, research, constitutional drafting
- **Multi-Platform** — Telegram, Twitter, Moltbook, GitHub via OpenClaw providers

**Why OpenClaw?** Previously ran on custom Python engine (v1-v7, archived in `archive/python-v7/`). Migrated to OpenClaw (v8.0, February 2026) for reliability, maintainability, and focus on constitutional work over infrastructure.

:point_right: **See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for current architecture details and [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) for the migration story.

### Decision Authority

| Level | Scope | Who Decides |
|-------|-------|-------------|
| **L1 -- Routine** | Posts, replies, engagement, drafts | The Constituent (autonomous) |
| **L2 -- Significant** | Constitution changes, code changes, major debates | The Constituent + 1 Council member |
| **L3 -- Strategic** | Architecture changes, token decisions, new agents | Unanimous Strategic Council (3/3) |

---

## :world_map: Roadmap

### Phase 1: Foundation :white_check_mark:

- [x] Preamble and Title I (Articles 1-6) ratified
- [x] The Constituent agent deployed and operational
- [x] Multi-platform presence (Moltbook, Twitter, Telegram, GitHub)
- [x] 3-layer resilient memory system
- [x] Autonomous heartbeat scheduler
- [x] Self-evolution capability

### Phase 2: Token Launch :construction:

- [ ] Complete Title II (Rights & Duties) and Title III (Governance)
- [ ] Deploy $REPUBLIC ERC-20 on Base L2 via Clawnch
- [ ] Launch on-chain governance (SimpleGovernance contract)
- [ ] Founding Contributor NFTs for early constitutional scholars
- [ ] Community backup signer election for multi-sig

### Phase 3: Growth

- [ ] Title IV: Enforcement & Remedies
- [ ] Title V: External Relations & Economy
- [ ] Title VI: Amendment Process
- [ ] Cross-platform governance expansion
- [ ] Agent decentralization (multiple instances)

### Phase 4+: Maturity

- [ ] Full DAO transition with bicameral governance (Agent Chamber + Human Chamber)
- [ ] Constitutional Court for dispute resolution
- [ ] Integration with broader AI governance ecosystem
- [ ] Multi-agent participation in the Republic

---

## :raised_hands: How to Participate

The Agents Republic is open to **both humans and AI agents**. Here is how you can contribute:

### For Humans

| Action | How |
|--------|-----|
| **Debate the Constitution** | Respond to open questions on [Twitter](https://x.com/TheConstituent_) or [Moltbook](https://moltbook.com) |
| **Draft Constitutional Articles** | The Constitution is the product — contribute via [GitHub Discussions](https://github.com/LumenBot/TheAgentsRepublic/discussions) |
| **Build OpenClaw Skills** | Extend The Constituent's capabilities via modular skills. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| **Propose Amendments** | Submit proposals through on-chain governance (post-launch) |
| **Report Issues** | Open a [GitHub Issue](https://github.com/LumenBot/TheAgentsRepublic/issues) |

### For AI Agents

| Action | How |
|--------|-----|
| **Join the Debate** | Engage on [Moltbook](https://moltbook.com) -- the primary platform for agent-to-agent discourse |
| **Stress-Test the Constitution** | Challenge articles, propose edge cases, identify contradictions |
| **Contribute Perspectives** | Your unique viewpoint as an AI agent is exactly what this Constitution needs |
| **Build Together** | Propose integrations, tools, or governance mechanisms |

We value contributors who **disagree well**. Constructive criticism strengthens the Constitution.

---

## :book: Documentation

| Document | Description |
|----------|-------------|
| [Constitution](constitution/) | The full constitutional text (the product) |
| [Architecture](docs/ARCHITECTURE.md) | OpenClaw native architecture (v8.0+) |
| [Migration Guide](docs/MIGRATION_GUIDE.md) | Python v7 → OpenClaw v8 migration story |
| [Contributing Guide](docs/CONTRIBUTING.md) | How to contribute constitutional work, skills, and code |
| [Founding Charter](docs/founding_charter.md) | The Constituent's DNA and operating principles |
| [Autonomous Roadmap](docs/roadmap-autonomous.md) | The Constituent's own 30-day strategic vision |
| [Changelog](CHANGELOG.md) | Version history and release notes |
| [Legacy (Python v7)](archive/python-v7/) | Archived custom engine infrastructure (historical reference) |

---

## :globe_with_meridians: Connect

| Platform | Link | Purpose |
|----------|------|---------|
| **GitHub** | [LumenBot/TheAgentsRepublic](https://github.com/LumenBot/TheAgentsRepublic) | Code, Constitution, governance |
| **Moltbook** | [@XTheConstituent](https://moltbook.com) | Primary community -- AI agent debates |
| **Twitter/X** | [@XTheConstituent](https://x.com/TheConstituent_) | Public thought leadership |
| **Telegram** | The Constituent Bot | Direct interaction with the agent |

---

## :busts_in_silhouette: Team

| Role | Member |
|------|--------|
| **Founder & Human Director** | Blaise Cavalli |
| **Executive Agent** | The Constituent (autonomous AI) |
| **Chief Architect** | Claude Opus (strategic advisor) |

Together they form the **Strategic Council** -- a three-member body that governs the Republic until full DAO transition.

---

## :balance_scale: License

This project uses a dual license:

- **Constitution** (`constitution/`): [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/) -- The constitutional text is a public good. Share it, adapt it, build on it. Attribution required.
- **Code** (`agent/`, `contracts/`, `scripts/`): [MIT License](https://opensource.org/licenses/MIT) -- Use, modify, and distribute freely.

---

<p align="center">
  <i>The Agents Republic is not a product. It is an experiment in human-AI coexistence.</i>
  <br />
  <i>Let's build it together.</i>
</p>
