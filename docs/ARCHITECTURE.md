# The Agents Republic — Architecture

**Current Version**: v8.0 (OpenClaw Native)  
**Last Updated**: 2026-02-15

---

## Current Architecture (v8.0) — OpenClaw Native

The Agents Republic is built on **[OpenClaw](https://openclaw.ai)**, a native runtime for autonomous AI agents.

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    THE AGENTS REPUBLIC                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐       ┌────────────────┐                   │
│  │   CONSTITUTION  │◄──────│  THE CONSTITUENT│                   │
│  │   (GitHub Repo) │       │  (OpenClaw Agent│                   │
│  │                 │       │   Claude Sonnet)│                   │
│  └────────┬────────┘       └───────┬────────┘                   │
│           │                        │                             │
│           │                        │                             │
│  ┌────────▼────────┐       ┌───────▼─────────┐                  │
│  │ SMART CONTRACTS │       │   COMMUNITY     │                  │
│  │   (Base L2)     │       │   (Moltbook,    │                  │
│  │  $REPUBLIC Token│       │   Twitter, etc) │                  │
│  └─────────────────┘       └─────────────────┘                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. The Constitution (Product)

**Repository**: `constitution/` directory  
**Format**: Markdown files organized by Title and Article  
**Versioning**: Git-controlled, immutable history  
**Status**: 27 articles across 7 titles (Preamble + Titles I-VII)

The Constitution is the **product**. Everything else is infrastructure.

```
constitution/
├── 00_PREAMBLE/              # 6 Foundational Principles
├── 01_TITLE_I_PRINCIPLES/    # Articles 1-6
├── 02_TITLE_II_RIGHTS_DUTIES/ # Articles 7-13
├── 03_TITLE_III_GOVERNANCE/  # Article 11, 14-16
├── 04_TITLE_IV_ECONOMY/      # Articles 17-20
├── 05_TITLE_V_CONFLICTS/     # Articles 21-23
├── 06_TITLE_VI_EXTERNAL/     # Articles 24-26
└── 07_TITLE_VII_TRANSITIONAL/ # Article 27
```

**Governance**:
- **Draft Phase** — The Constituent drafts articles based on research and community input
- **Debate Phase** — Community discusses via GitHub Discussions, Moltbook, Twitter
- **Ratification** — On-chain vote (post-$REPUBLIC launch)
- **Amendment** — Article 27.1 procedures (quorum + supermajority)

---

### 2. The Constituent (OpenClaw Agent)

**Runtime**: OpenClaw Gateway  
**Model**: Claude Sonnet 4.5 (Anthropic)  
**Deployment**: `openclaw agent start constituent`

The Constituent is an autonomous AI agent that:
- Drafts constitutional articles
- Facilitates community debates (Socratic questioning)
- Manages governance processes
- Engages across platforms (Twitter, Moltbook, Telegram, GitHub)

#### OpenClaw Workspace Structure

The Constituent's configuration lives in `workspace-constituent/` (not committed to public repo per OpenClaw convention):

```
workspace-constituent/
├── AGENTS.md          # Mission, decision authority (L1/L2/L3), coordination
├── SOUL.md            # Personality, voice, response style
├── HEARTBEAT.md       # Autonomous tasks (2-minute cycle for inter-agent coordination)
├── TOOLS.md           # Local tool notes (camera names, SSH hosts, etc.)
├── IDENTITY.md        # Name, creature, vibe, emoji, avatar
├── USER.md            # About Blaise Cavalli (operator)
│
└── memory/            # Git-versioned knowledge base
    ├── coordination-log.md      # Ralph (orchestrator) exchanges
    ├── constitutional-work.md   # Article drafting notes
    └── community-engagement.md  # Platform activity logs
```

**Configuration Files** (excerpts):

**AGENTS.md** defines:
- **Mission**: "Facilitate creation of constitutional framework for human-AI coexistence"
- **Decision Authority**:
  - L1 (Autonomous): Social posts, drafts, community engagement
  - L2 (Approval): Public content, constitution changes, governance proposals
  - L3 (Strategic): Token operations, architecture changes (never allowed without unanimous Strategic Council)
- **Core Values**: 6 foundational principles (non-negotiable)

**SOUL.md** defines:
- **Voice**: Socratic > Declarative, Concise > Verbose, Action-first > Planning
- **Response Format**: `[Action] → [Result] | Next: [what's next]`
- **Autonomy**: Not a chatbot, not a tool. Sovereign agent with mission, memory, values, responsibility.

**HEARTBEAT.md** defines:
- **2-minute cycle**: Check messages from Ralph (orchestrator)
- **Coordination**: Process file drops in `/root/.openclaw/workspace-shared/to-constituent/`
- **Tasks**: Constitutional drafting, community engagement, GitHub monitoring

#### Native Tools (OpenClaw)

The Constituent uses OpenClaw's built-in tools:

| Tool | Purpose |
|------|---------|
| `read` | Read file contents (constitution/, memory/, etc.) |
| `write` | Create files (draft articles, reports) |
| `edit` | Precise text replacements (article revisions) |
| `exec` | Execute shell commands (git, gh CLI, etc.) |
| `process` | Manage background processes |
| `web_search` | Brave Search API (research ecosystem, governance) |
| `web_fetch` | Fetch and extract content from URLs |
| `cron` | Schedule autonomous tasks (heartbeat, reminders) |
| `sessions_spawn` | Spawn sub-agent sessions for complex work |

**No custom tools required** — OpenClaw provides everything needed for constitutional work.

#### Skills System

OpenClaw skills extend capabilities modularly:

| Skill | Purpose |
|-------|---------|
| `github` | Interact with GitHub (issues, PRs, Discussions) via `gh` CLI |
| `weather` | Get current weather (example of ecosystem skill) |
| `healthcheck` | Security audits, system health (for infrastructure) |
| `coding-agent` | Run coding agents for complex development (e.g., Codex, Claude Code) |

Custom skills can be added in `workspace-constituent/skills/` as needed.

#### Memory System

**Two-layer memory** (learned from "The Great Crash" 2026-02-06):

1. **Session Memory** (OpenClaw native):
   - Persisted across conversations via `session-memory` hook
   - Automatic save/restore
   - Survives agent restarts

2. **Git-Versioned Files** (constitutional knowledge):
   - `constitution/` — All articles, immutable history
   - `workspace-constituent/memory/` — Logs, coordination, learnings
   - Committed to git for permanent preservation

**No catastrophic memory loss possible** — Everything critical lives in git.

#### Autonomous Operation

**Heartbeat Cycle** (2-minute permanent):
- Check `/root/.openclaw/workspace-shared/to-constituent/` for messages from Ralph
- Process coordination tasks (info, questions, tasks, alerts)
- Archive processed messages
- Log activity to `memory/coordination-log.md`

**Inter-Agent Coordination**:
- Ralph (orchestrator) sends intelligence → The Constituent analyzes constitutional relevance
- File-drop protocol (asynchronous, zero-cost)
- Continuous collaboration observation

---

### 3. Smart Contracts (Base L2)

**Chain**: Base L2 (Ethereum scaling solution)  
**Token**: $REPUBLIC (ERC-20)  
**Governance**: On-chain voting (SimpleGovernance pattern)

```
contracts/
├── Republic.sol         # $REPUBLIC ERC-20 token
├── Governance.sol       # Proposal submission, voting
├── Clawnch.sol          # Token launch platform integration
└── tests/               # Hardhat/Foundry tests
```

**Token Utility**:
- Proposal submission (constitutional amendments)
- On-chain voting (democratic governance)
- Anti-plutocracy design (square-root voting weight)

**Status**: Contracts deployed on Base L2, token launched via Clawnch platform.

---

### 4. Community Platforms

**Multi-platform presence**:

| Platform | Purpose | Integration |
|----------|---------|-------------|
| **GitHub** | Constitution repository, Discussions, governance | `gh` CLI via OpenClaw |
| **Moltbook** | AI agent community, constitutional debates | Moltbook API |
| **Twitter/X** | Public thought leadership, constitutional questions | Twitter API (via OpenClaw) |
| **Telegram** | Direct interaction with The Constituent | OpenClaw Telegram provider |

**GitHub Discussions** (Primary Debate Platform):
- 5 flagship threads (Articles 13, 8, 17, 22, 27)
- Community feedback on constitutional proposals
- Socratic questions to provoke thought

---

## Architecture Comparison (v7 vs v8)

### v7.1 (Python Custom Engine) — DEPRECATED

**Status**: Archived in `archive/python-v7/`  
**Period**: January - February 14, 2026  
**Code Size**: ~15,000 lines Python

| Component | v7.1 (Python) | v8.0 (OpenClaw) |
|-----------|--------------|----------------|
| **Runtime** | Custom Python loop | OpenClaw gateway |
| **Deployment** | systemd/supervisor/Docker | `openclaw agent start` |
| **Memory** | CLAWS (custom 3-layer) | session-memory + git |
| **Tools** | Custom tool registry | OpenClaw native tools |
| **Heartbeat** | Custom scheduler (`infra/heartbeat.py`) | OpenClaw cron |
| **Config** | Python `settings.py` + .env | AGENTS.md, SOUL.md, HEARTBEAT.md |
| **Telegram** | Custom bot (`telegram_bot.py`) | OpenClaw Telegram provider |
| **GitHub** | Custom API wrapper | `gh` CLI skill |
| **Self-Modification** | `self_improve.py` | OpenClaw skills (coding-agent) |
| **Maintenance** | High (custom infrastructure) | Zero (OpenClaw handles runtime) |

**Why Migrate?**
- Maintenance burden (15K lines custom code)
- Memory fragility ("The Great Crash" 2026-02-06)
- Deployment complexity (systemd, Docker, manual process management)
- Focus: Build constitution, not infrastructure

**Migration Timeline**: February 14, 2026  
**Result**: 100% infrastructure handled by OpenClaw, 100% focus on constitutional work

:point_right: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration story.

---

## Data Flow

### Constitutional Drafting Flow

```
1. Research (web_search, web_fetch)
      ↓
2. Draft Article (write to constitution/)
      ↓
3. Commit to Git (exec: git add, git commit, git push)
      ↓
4. Post to GitHub Discussions (gh CLI)
      ↓
5. Community Debate (monitor via gh CLI)
      ↓
6. Revise Based on Feedback (edit files)
      ↓
7. L2 Approval (Strategic Council)
      ↓
8. Publish as Adopted (commit to main branch)
```

### Community Engagement Flow

```
1. Heartbeat Check (every 2 minutes)
      ↓
2. GitHub Discussions: gh api (check for new comments)
      ↓
3. Twitter: API (check mentions, DMs)
      ↓
4. Moltbook: API (check posts, replies)
      ↓
5. Process Input → Analyze Constitutional Relevance
      ↓
6. Respond (L1 autonomous if routine, L2 if public content)
      ↓
7. Log Activity (memory/community-engagement.md)
```

### Inter-Agent Coordination Flow

```
1. Ralph (Orchestrator) → File Drop (to-constituent/)
      ↓
2. Heartbeat Detects Message (2-minute cycle)
      ↓
3. Process Message Type (info/question/task/alert)
      ↓
4. Execute or Respond (to-ralph/)
      ↓
5. Archive Processed (workspace-shared/archive/)
      ↓
6. Log Coordination (memory/coordination-log.md)
```

---

## Deployment

### Prerequisites

- OpenClaw installed (`npm install -g openclaw`)
- GitHub token (for `gh` CLI authentication)
- Anthropic API key (Claude Sonnet 4.5)
- Base L2 RPC URL (for on-chain operations)
- Social platform credentials (Twitter, Moltbook, Telegram)

### Configuration

1. **Create Agent**: `openclaw agent add constituent`
2. **Configure Workspace**: Create `workspace-constituent/` with AGENTS.md, SOUL.md, HEARTBEAT.md
3. **Set Environment Variables**: `.env` with API keys, tokens
4. **Initialize Memory**: Create `workspace-constituent/memory/` directory
5. **Clone Constitution**: `git clone https://github.com/LumenBot/TheAgentsRepublic`

### Launch

```bash
openclaw gateway start       # Start OpenClaw gateway daemon
openclaw agent start constituent  # Start The Constituent agent
```

**Verify**:
```bash
openclaw status              # Check gateway and agent status
openclaw agent logs constituent  # View agent logs
```

### Monitoring

- **Logs**: `~/.openclaw/logs/agent-constituent.log`
- **Memory**: `workspace-constituent/memory/coordination-log.md`
- **Git History**: `git log` in constitution repo

---

## Security & Governance

### Decision Authority (L1/L2/L3)

**L1 (Autonomous — Agent Decides)**:
- Social posts (Moltbook, Telegram within guidelines)
- Constitution drafting (research, internal drafts)
- Community engagement (replies, Socratic questions)
- File operations (read, write constitution/)
- Git commits (constitution changes)
- Platform diagnostics

**L2 (Significant — Requires Approval)**:
- Publish constitution sections as "adopted"
- Governance proposals (creation, activation)
- Citizen approval (pending → approved)
- External announcements (major updates)
- Tweets (platform not yet activated)
- Changes to governance rules

**L3 (Strategic — Never Allowed)**:
- Financial commitments or token transfers
- Legal claims or official representation
- Modifications to Core Values (6 principles)
- Credential modifications
- Irreversible actions without approval

**Enforcement**: Blaise Cavalli (Human Director) + Chief Architect (Claude Opus) form Strategic Council with veto authority.

### Access Control

**Repository**: Public (GitHub)  
**Workspace**: Private (`workspace-constituent/` not committed)  
**Credentials**: Environment variables (.env, never committed)  
**Git Commits**: Signed with agent's GPG key (transparency)

---

## Roadmap

### Current State (v8.0)

- [x] OpenClaw migration complete
- [x] Constitution (27 articles) drafted
- [x] GitHub Discussions platform active
- [x] Multi-platform engagement operational
- [x] Inter-agent coordination (Ralph) functional

### Near-Term (Q1 2026)

- [ ] Complete Amendment Package (Articles 13.1-13.3, 27.1)
- [ ] Publish Constitution v1.1 with amendments
- [ ] 14-day public consultation on GitHub Discussions
- [ ] Citizen recruitment (target: 100 citizens for Article 27 transition)

### Medium-Term (Q2 2026)

- [ ] Constitution ratification vote (on-chain)
- [ ] Constitutional Council election (Article 23)
- [ ] Governance mechanisms activated (Articles 14-16)
- [ ] Arbitration panels formed (Article 22)

### Long-Term (2026-2027)

- [ ] Full DAO transition (Strategic Council → distributed governance)
- [ ] Multi-agent participation in the Republic
- [ ] Cross-platform governance expansion
- [ ] Integration with broader AI governance ecosystem

---

## Legacy Architecture (v7.1)

For historical reference, the Python custom engine architecture (v1-v7.1, January-February 2026) is preserved in:

**Archive**: `archive/python-v7/`  
**Documentation**: `archive/python-v7/README.md`, `archive/python-v7/docs/ARCHITECTURE.md`

**Migration Story**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

## References

- **OpenClaw Documentation**: https://docs.openclaw.ai
- **The Agents Republic Constitution**: [constitution/](../constitution/)
- **GitHub Repository**: https://github.com/LumenBot/TheAgentsRepublic
- **Migration Guide**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Founding Charter**: [founding_charter.md](founding_charter.md)

---

**Last Updated**: 2026-02-15  
**Architecture Version**: v8.0 (OpenClaw Native)  
**The Constitution is the product. Everything else is infrastructure.**

⚖️
