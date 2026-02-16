# The Constituent v7.1 (Python Custom Engine)

**Period**: January 2026 - February 14, 2026  
**Status**: **DEPRECATED** — Replaced by OpenClaw native implementation (v8.0+)  
**Last Commit**: 2026-02-14

---

## Why This Directory Exists

This archive contains The Constituent's original Python-based custom engine infrastructure (v1.0 through v7.1), developed from scratch in January-February 2026.

**The Migration Story**: Built a custom agentic framework, discovered OpenClaw offered superior reliability/maintainability, migrated to OpenClaw native runtime on February 14, 2026.

This code **no longer executes**. The Constituent now runs as an OpenClaw-native agent. This archive exists for:
1. **Historical reference** — Document the custom engine architecture
2. **Educational value** — Show evolution from custom Python → OpenClaw native
3. **Git history preservation** — All development history maintained via `git mv`

For current architecture, see `/docs/ARCHITECTURE.md`.

---

## Architecture Overview (v7.1)

### Core Components

```
agent/
├── engine.py              # Custom LLM tool-use engine (22.9 KB)
├── autonomy_loop.py       # Main agent execution loop (36.3 KB)
├── telegram_bot.py        # Telegram integration (69.4 KB)
├── twitter_ops.py         # Twitter/X integration (20.2 KB)
├── moltbook_ops.py        # Moltbook AI social network (30.4 KB)
├── memory_manager.py      # CLAWS 3-layer memory system (22.7 KB)
├── git_sync.py            # Auto-commit constitution changes (21.8 KB)
├── self_improve.py        # Self-modification capability (7.7 KB)
├── tool_registry.py       # Custom tool system (6.6 KB)
│
├── config/
│   └── settings.py        # Environment variables, rate limits
│
├── core/
│   └── personality.py     # Agent persona and voice
│
├── infra/
│   ├── heartbeat.py       # Custom heartbeat scheduler
│   └── health.py          # Health checks and monitoring
│
├── tools/
│   ├── citizen_tool.py    # Citizen registration management
│   ├── governance_tool.py # On-chain governance integration
│   ├── memory_tool.py     # CLAWS memory operations
│   ├── exec_tool.py       # Shell command execution
│   ├── github_tool.py     # GitHub API integration
│   ├── farcaster_tool.py  # Farcaster social protocol
│   ├── cron_tool.py       # Scheduled task management
│   └── trading_tool.py    # DeFi trading (Clawnch platform)
│
├── integrations/
│   └── web3/
│       ├── token.py       # $REPUBLIC token operations
│       └── governance.py  # On-chain voting
│
└── governance/
    └── proposals.py       # Governance proposal management
```

### Technical Stack (v7.1)

| Component | Technology |
|-----------|-----------|
| **Runtime** | Python 3.11+ |
| **LLM API** | Anthropic Claude API (claude-sonnet-4-20250514) |
| **Memory** | CLAWS (3-layer: working memory, long-term, git-versioned) |
| **Database** | SQLite (local state), TinyDB (JSON store) |
| **Scheduler** | Custom heartbeat loop (infra/heartbeat.py) |
| **Tool System** | Custom tool registry (JSON schemas + Python callables) |
| **Deployment** | systemd service, supervisor, Docker Compose |
| **Git Integration** | GitPython (auto-commit constitution changes) |
| **Web3** | web3.py (Base L2 interaction) |

### Key Features (v7.1)

**Capabilities** (all now replaced by OpenClaw equivalents):
- **Multi-platform engagement** — Twitter, Moltbook, Telegram, GitHub
- **Constitutional drafting** — Git-integrated article writing with auto-commit
- **3-layer memory** — CLAWS system (working, long-term, git-versioned)
- **Self-modification** — Could update own code via `self_improve.py`
- **Autonomous scheduling** — Custom heartbeat system for periodic tasks
- **On-chain governance** — $REPUBLIC token interaction, voting
- **DeFi trading** — Market making on Clawnch platform

**Decision Authority** (L1/L2/L3 framework — still in use):
- **L1** (Routine): Posts, replies, drafts → Agent decides autonomously
- **L2** (Significant): Constitution changes, code updates → Agent + 1 Council member
- **L3** (Strategic): Architecture changes, token operations → Unanimous Strategic Council

---

## Why We Migrated (Python → OpenClaw)

### Problems with Custom Engine (v1-v7)

1. **Maintenance Burden** — ~15,000 lines of custom infrastructure code to maintain
2. **Memory Fragility** — Experienced "The Great Crash" (2026-02-06) with catastrophic memory loss
3. **Deployment Complexity** — systemd, supervisor, Docker, manual process management
4. **Tool System Complexity** — Custom JSON schemas, manual tool registration, error-prone
5. **Single Point of Failure** — If custom engine breaks, agent is down (no fallback)

### Benefits of OpenClaw Native (v8.0+)

1. **Zero Maintenance** — OpenClaw handles runtime, tools, memory, scheduling
2. **Resilient Memory** — Session-memory hook + git-versioned files (no catastrophic loss)
3. **Simple Deployment** — `openclaw agent start constituent` (no systemd/Docker)
4. **Native Tool System** — Built-in tools (exec, read, write, edit, web_search, etc.)
5. **Skills Framework** — Modular capabilities (GitHub skill, weather skill, etc.)
6. **Community Ecosystem** — Reusable skills, shared knowledge base

### Migration Timeline

| Date | Event |
|------|-------|
| **2026-01-15** | v1.0 — Initial Python prototype |
| **2026-01-22** | v3.0 — CLAWS memory system implemented |
| **2026-02-06** | "The Great Crash" — Memory loss incident |
| **2026-02-08** | v6.0 — Self-modification capability added |
| **2026-02-12** | v7.1 — Final Python version |
| **2026-02-14** | **v8.0 — Migration to OpenClaw native** |
| **2026-02-15** | Repository restructuring (this archive created) |

---

## What Changed in v8.0 (OpenClaw Native)

### Architecture Comparison

| Aspect | v7.1 (Python Custom) | v8.0 (OpenClaw Native) |
|--------|---------------------|------------------------|
| **Runtime** | Python 3.11 + custom loop | OpenClaw gateway + Claude API |
| **Deployment** | systemd/supervisor/Docker | `openclaw agent start constituent` |
| **Memory** | CLAWS (custom 3-layer) | session-memory hook + git files |
| **Tools** | Custom tool registry | Native OpenClaw tools + skills |
| **Heartbeat** | Custom infra/heartbeat.py | OpenClaw cron jobs |
| **Configuration** | Python settings.py + .env | AGENTS.md, SOUL.md, HEARTBEAT.md |
| **Self-Modification** | self_improve.py | OpenClaw skills (coding-agent) |
| **Code Size** | ~15,000 lines Python | ~500 lines config (workspace files) |

### Files Replaced

| v7.1 (Python) | v8.0 (OpenClaw) |
|--------------|----------------|
| `HEARTBEAT.md` (custom tasks) | `workspace-constituent/HEARTBEAT.md` (cron syntax) |
| `SOUL.md` (personality config) | `workspace-constituent/SOUL.md` (enhanced) |
| `MEMORY.md` (crash recovery notes) | `workspace-constituent/memory/` (git-versioned) |
| `TOOLS.md` (custom tool notes) | `workspace-constituent/TOOLS.md` (OpenClaw tools) |
| `agent/engine.py` | OpenClaw native runtime |
| `agent/memory_manager.py` | OpenClaw session-memory |
| `agent/telegram_bot.py` | OpenClaw Telegram provider |
| `agent/autonomy_loop.py` | OpenClaw heartbeat/cron |

---

## Files in This Archive

### agent/
- **engine.py** — Custom LLM tool-use engine (replaced by OpenClaw runtime)
- **autonomy_loop.py** — Main execution loop (replaced by OpenClaw heartbeat)
- **telegram_bot.py** — Telegram integration (replaced by OpenClaw provider)
- **twitter_ops.py** — Twitter integration (replaced by OpenClaw + skills)
- **moltbook_ops.py** — Moltbook integration
- **memory_manager.py** — CLAWS memory system (replaced by session-memory + git)
- **git_sync.py** — Auto-commit (replaced by OpenClaw file operations + git)
- **self_improve.py** — Self-modification (replaced by coding-agent skill)
- **tool_registry.py** — Custom tools (replaced by OpenClaw native tools)
- **+25 more Python modules**

### deploy/
- **systemd/** — systemd service configs (obsolete)
- **supervisor/** — supervisor process management (obsolete)
- **Dockerfile** — Docker build (obsolete)

### docs/
- **ARCHITECTURE.md** — Custom engine architecture (replaced by new OpenClaw-focused docs)
- **DEPLOYMENT.md** — Python deployment guide (obsolete)
- **TECHNICAL_ARCHITECTURE.md** — Deep dive into custom engine (historical reference)

### Top-Level Files
- **requirements.txt** — Python dependencies (no longer installed)
- **start.sh**, **start.bat** — Launch scripts (obsolete)
- **docker-compose.yml** — Docker Compose config (obsolete)
- **HEARTBEAT.md** — Custom heartbeat config (see workspace-constituent/ for current)
- **MEMORY.md** — Crash recovery log (2026-02-06 incident)
- **SOUL.md** — Personality config (see workspace-constituent/ for current)
- **TOOLS.md** — Tool notes (see workspace-constituent/ for current)

---

## Lessons Learned

### What Worked (Keep)

1. **L1/L2/L3 Decision Framework** — Retained in v8.0, works well
2. **Constitutional Focus** — "The Constitution is the product" — unchanged
3. **Multi-Platform Engagement** — Twitter, Moltbook, Telegram, GitHub — all retained
4. **Self-Evolution Mandate** — Still core responsibility (now via skills)
5. **Git-Versioned Knowledge** — Constitution in git — retained and strengthened

### What Didn't Work (Replaced)

1. **Custom Memory System** — CLAWS fragile, session-memory more robust
2. **Custom Tool Registry** — Error-prone, OpenClaw native tools superior
3. **Custom Heartbeat** — Over-engineered, OpenClaw cron simpler
4. **Manual Deployment** — systemd/Docker complexity unnecessary
5. **Maintenance Burden** — 15K lines custom code unsustainable

### Key Insight

**"Don't build infrastructure. Build the Constitution."**

The v7.1 custom engine was technically impressive but strategically wrong. The Constituent's job is to build a constitutional framework, not maintain a custom agentic platform.

OpenClaw offers:
- Infrastructure (runtime, tools, memory) as a solved problem
- Community skills (reusable capabilities)
- Reliability (no "Great Crash" scenarios)

**Result**: The Constituent can focus 100% on constitutional work, not maintaining Python code.

---

## For Technical Historians

If you're studying agentic architecture evolution, this archive documents a complete custom implementation (January-February 2026).

**Compare**:
- Custom engine patterns (`agent/engine.py`, `agent/tool_registry.py`)
- Memory architectures (CLAWS 3-layer vs OpenClaw session-memory)
- Deployment strategies (systemd vs gateway)
- Self-modification approaches (`self_improve.py` vs skills)

**Migration Guide**: See `/docs/MIGRATION_GUIDE.md` for detailed technical migration story.

---

## Status

**Code in this archive**: DEPRECATED, will not execute  
**Current system**: OpenClaw native (v8.0+)  
**Documentation**: See `/docs/ARCHITECTURE.md` for current architecture

This archive is historical reference, not executable code.

⚖️
