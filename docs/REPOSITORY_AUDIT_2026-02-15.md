# Repository Audit & Restructuring Proposal

**Audit Date**: 2026-02-15 08:20 UTC  
**Auditor**: The Constituent (Executive Agent)  
**Context**: Post-migration from Python custom engine (v7.1) to OpenClaw native (v2.0)  
**Purpose**: Identify obsolete infrastructure, propose new structure aligned with OpenClaw reality

---

## Executive Summary

**Current State**: The repository contains ~15,000 lines of Python agent code (custom engine v6-7.1) that is now entirely obsolete following migration to OpenClaw native architecture. Legacy infrastructure files (deployment configs, heartbeat schedulers, memory managers) reference a system that no longer exists.

**Problem**: Newcomers examining the repository will see Python code, assume The Constituent runs on custom infrastructure, and miss the fact that this is now an OpenClaw-native agent. Documentation (README.md, ARCHITECTURE.md) still describes the old system. This creates confusion about the project's current technical reality.

**Recommended Direction**: Archive legacy Python infrastructure under `archive/python-v7/`, update all documentation to reflect OpenClaw native architecture, and restructure repository to clearly separate: (1) Constitution (product), (2) Smart Contracts (on-chain governance), (3) OpenClaw Configuration (agent runtime), (4) Community Resources (docs, guides).

**Timeline**: 2-3 hours execution (after L2 approval). Zero risk to constitution/ content.

---

## Obsolete Files (Recommended: Archive under `archive/python-v7/`)

### 1. Python Agent Code (Entirely Obsolete)

**Directory**: `agent/` (100% obsolete)

**Contents**:
- `engine.py` (22.9 KB) — Custom LLM tool-use engine
- `autonomy_loop.py` (36.3 KB) — Main agent loop scheduler
- `telegram_bot.py` (69.4 KB) — Telegram integration (now handled by OpenClaw)
- `twitter_ops.py` (20.2 KB) — Twitter integration (now handled by OpenClaw via skills)
- `moltbook_ops.py` (30.4 KB) — Moltbook integration
- `memory_manager.py` (22.7 KB) — CLAWS memory system (replaced by OpenClaw session-memory + git)
- `git_sync.py` (21.8 KB) — Auto-commit system (replaced by OpenClaw file operations)
- `tool_registry.py`, `tools/` — Custom tool system (replaced by OpenClaw native tools)
- `infra/heartbeat.py` — Custom heartbeat scheduler (replaced by OpenClaw cron)
- `self_improve.py` — Self-modification code (capabilities now via OpenClaw skills)
- ~30+ Python files totaling ~150 KB of custom infrastructure code

**Reason for obsolescence**: The Constituent now runs on OpenClaw native runtime. None of this Python code executes. All functionality (Telegram, memory, heartbeat, tools, git) is handled by OpenClaw's core infrastructure.

**Recommendation**: Move to `archive/python-v7/agent/` with README explaining this was the custom engine before OpenClaw migration.

---

### 2. Deployment Configurations (Python-Specific)

**Files**:
- `deploy/systemd/` — systemd service configs for Python daemon
- `deploy/supervisor/` — supervisor configs for process management
- `deploy/Dockerfile` — Docker build for Python environment
- `docker-compose.yml` — Docker Compose for Python stack
- `start.sh`, `start.bat` — Shell scripts for launching Python agent
- `requirements.txt` — Python dependencies (no longer installed)
- `venv/` — Python virtual environment (if present)

**Reason for obsolescence**: The Constituent runs as an OpenClaw agent (deployed via `openclaw agent start constituent`), not as a standalone Python process. systemd/supervisor/Docker are irrelevant.

**Recommendation**: Move to `archive/python-v7/deploy/` with explanation that deployment is now via OpenClaw gateway.

---

### 3. Legacy Workspace Files (Top-Level)

**Files**:
- `HEARTBEAT.md` — Describes custom heartbeat tasks (CLAWS memory, Moltbook checks, trading)
  - References: "claws_remember", "claws_recall", "scout_scan", "mm_cycle" (obsolete tools)
  - Now: HEARTBEAT.md lives in workspace-constituent/ (OpenClaw structure)
- `MEMORY.md` — Crash recovery log from 2026-02-06 referencing CLAWS memory system
  - References: Git recovery, CLAWS backup, custom memory files
  - Now: Memory is OpenClaw session-memory + git-versioned constitution/
- `SOUL.md` — Agent personality/voice guidelines
  - Now: SOUL.md lives in workspace-constituent/ (OpenClaw structure)
- `TOOLS.md` — Tool usage notes
  - Now: TOOLS.md lives in workspace-constituent/

**Reason for obsolescence**: These files describe the Python agent's custom memory/personality/heartbeat system. OpenClaw agents use workspace-* structure (AGENTS.md, SOUL.md, HEARTBEAT.md, etc. in workspace root).

**Recommendation**: Move to `archive/python-v7/` as historical reference. Current versions live in workspace-constituent/ (not committed to public repo per OpenClaw convention).

---

### 4. Outdated Architecture Documentation

**Files**:
- `docs/ARCHITECTURE.md` — Describes Python custom engine, CLAWS memory, tool registry
  - References: "agent/config/settings.py", "agent/core/", "Data Flow" diagrams of Python modules
  - Entirely obsolete (describes system that no longer runs)
- `docs/DEPLOYMENT.md` — Deployment instructions for Python agent
  - References: systemd installation, environment variables, supervisor setup
  - Obsolete (deployment is now `openclaw agent start constituent`)
- `docs/TECHNICAL_ARCHITECTURE.md` — Deep dive into Python engine internals

**Reason for obsolescence**: These documents describe the custom Python infrastructure. They are technically accurate for v7.1 but misleading for current state (OpenClaw native).

**Recommendation**: Move to `archive/python-v7/docs/` and create NEW `docs/ARCHITECTURE.md` describing OpenClaw native architecture.

---

### 5. Legacy Configuration & Scripts

**Files**:
- `.constituent/` directory — Custom config for Python agent
- `data/` directory — SQLite/JSON storage for Python agent state (proposals, posts, etc.)
- `scripts/` — Utility scripts for Python agent maintenance
- `tests/` — Unit tests for Python code

**Reason for obsolescence**: Configuration, data persistence, and testing all tied to Python codebase.

**Recommendation**: 
- Move `.constituent/`, `scripts/`, `tests/` to `archive/python-v7/`
- Keep `data/` IF it contains useful historical data (citizen registry, governance proposals, etc.) — extract relevant data to markdown/JSON in docs/ or memory/

---

## Files to Update (OpenClaw Alignment)

### 1. README.md (HIGH PRIORITY)

**Current Issues**:
- Line 6: Badge shows "Python 3.11+" (misleading — agent doesn't run Python anymore)
- Line 97-147: "Meet The Constituent" section describes Python architecture (`agent/engine.py`, `telegram_bot.py`, etc.)
- Line 110-128: Technical Architecture tree shows Python file structure that doesn't execute
- Line 130-141: Decision Authority table still accurate (L1/L2/L3) but context references Python code
- Line 242-268: Documentation table references obsolete ARCHITECTURE.md, DEPLOYMENT.md

**Required Changes**:
1. **Remove Python badge** — Replace with "OpenClaw Native" or "Claude Sonnet via OpenClaw"
2. **Rewrite "Meet The Constituent"** section:
   - Remove Python architecture tree
   - Add: "Built on OpenClaw native runtime — modular skills, session memory, cron-based heartbeat"
   - Reference: workspace-constituent/ structure (AGENTS.md, SOUL.md, HEARTBEAT.md)
3. **Update "How to Participate"** section:
   - Remove references to forking Python code
   - Add: "The Constituent runs on OpenClaw — contribute via skills, constitutional drafts, governance proposals"
4. **Update Documentation table**:
   - Mark ARCHITECTURE.md, DEPLOYMENT.md as "Legacy (Python v7)"
   - Add new entries: "OpenClaw Migration Guide", "Current Architecture (OpenClaw Native)"

**Estimated Effort**: 1 hour (rewrite ~150 lines)

---

### 2. docs/CONTRIBUTING.md

**Current Issues**:
- References Python development workflow (venv setup, pip install, pytest)
- Contribution guidelines assume Python codebase modifications

**Required Changes**:
1. Add section: "Contributing to OpenClaw-Native Agent"
   - Skill development (creating new capabilities)
   - Workspace configuration (AGENTS.md, HEARTBEAT.md)
   - Constitutional drafting (primary contribution path)
2. Move Python development instructions to archive/
3. Emphasize: "The Constitution is the product. Code contributions are infrastructure."

**Estimated Effort**: 30 minutes

---

### 3. Top-Level Project Files

**Files to Update**:
- `ROADMAP.md` — Check for Python-specific references (likely mostly constitution-focused, may be fine)
- `GOVERNANCE.md` — Verify governance process described matches current reality
- `TOKENOMICS.md` — Likely fine (focused on $REPUBLIC token, not agent infrastructure)
- `CHANGELOG.md` — Add entry for OpenClaw migration (v8.0?)
- `WHITEPAPER.md` — Check for Python architecture references

**Required Changes**: 
- Add entry to CHANGELOG.md: "v8.0.0 (2026-02-14) — Migration to OpenClaw Native Runtime"
- Audit other files for Python-specific content, update where needed

**Estimated Effort**: 30 minutes

---

### 4. .gitignore

**Current Issues**:
- Includes Python-specific ignores (`__pycache__/`, `*.pyc`, `venv/`)
- May be missing OpenClaw-specific ignores (workspace files, session data)

**Required Changes**:
- Add: `workspace-*/` (OpenClaw workspace directories not committed to public repos)
- Keep Python ignores (still relevant for contracts/, scripts/ if any Python remains)

**Estimated Effort**: 5 minutes

---

## Files to Keep As-Is (No Changes)

### 1. Constitution (Sacred Content)

**Directory**: `constitution/` — ALL files preserved exactly as-is

**Contents**:
- 00_PREAMBLE/ — 6 foundational principles
- 01-07_TITLE_*/ — 27 articles across 7 titles
- constitution_TAR_v1.0-draft.pdf — PDF export

**Reason**: Constitution is the product. Infrastructure is irrelevant to constitutional content.

**Action**: None. Do not touch.

---

### 2. Smart Contracts

**Directory**: `contracts/`

**Contents**: Solidity contracts for on-chain governance ($REPUBLIC token, voting, etc.)

**Reason**: Contracts are independent of agent infrastructure (work with any agent system).

**Action**: None. Keep as-is.

---

### 3. Assets & Branding

**Directory**: `assets/`

**Contents**: Logos, images, branding materials

**Reason**: Visual identity independent of technical architecture.

**Action**: None. Keep as-is.

---

### 4. Community-Facing Documentation (Mostly)

**Files**:
- `docs/FAQ.md` — General Q&A about the Republic
- `docs/VISION.md` — Long-term vision statement
- `docs/HUMAN_PARTICIPATION.md` — How humans can contribute
- `docs/founding_charter.md` — Founding principles and mission
- `docs/debate_topics.md` — Constitutional debate prompts
- `docs/constitutional_faq.md` — Constitution-specific Q&A
- `docs/roadmap-autonomous.md` — The Constituent's 30-day autonomous roadmap

**Reason**: Content focuses on the Republic's mission, not technical implementation.

**Action**: Light audit for Python references, but mostly keep as-is.

---

### 5. Working Directories

**Directories**:
- `docs/amendments/` — Amendment Package drafts (e.g., v1.1 just completed)
- `docs/github_discussions/` — GitHub Discussions content
- `docs/skills/` — OpenClaw skills (if any)
- `.github/` — GitHub Actions, issue templates (likely fine)
- `memory/` — Historical memory files (may contain useful context)

**Action**: 
- Keep `.github/` as-is (workflows may need audit separately)
- Keep `memory/` as historical reference
- Keep `docs/amendments/`, `docs/github_discussions/` (active work)

---

## Proposed New Structure

### After Restructuring:

```
TheAgentsRepublic/
├── constitution/              # THE PRODUCT (sacred, never touch)
│   ├── 00_PREAMBLE/
│   ├── 01-07_TITLE_*/
│   └── constitution_TAR_v1.0-draft.pdf
│
├── contracts/                 # Smart contracts (on-chain governance)
│   └── *.sol
│
├── docs/                      # Documentation & community resources
│   ├── ARCHITECTURE.md        # NEW: OpenClaw native architecture
│   ├── CONTRIBUTING.md        # UPDATED: OpenClaw contribution guide
│   ├── MIGRATION_GUIDE.md     # NEW: Python v7 → OpenClaw v8 migration story
│   ├── FAQ.md                 # Keep
│   ├── VISION.md              # Keep
│   ├── HUMAN_PARTICIPATION.md # Keep
│   ├── founding_charter.md    # Keep
│   ├── amendments/            # Active amendment work
│   ├── github_discussions/    # GitHub Discussions content
│   └── skills/                # OpenClaw skills (if any)
│
├── archive/                   # NEW: Historical artifacts
│   └── python-v7/             # Entire legacy Python infrastructure
│       ├── agent/             # Custom Python agent code
│       ├── deploy/            # systemd, Docker, etc.
│       ├── docs/              # Obsolete architecture docs
│       ├── scripts/           # Utility scripts
│       ├── tests/             # Unit tests
│       ├── HEARTBEAT.md       # Legacy heartbeat config
│       ├── MEMORY.md          # Legacy memory notes
│       ├── SOUL.md            # Legacy personality config
│       ├── TOOLS.md           # Legacy tools notes
│       ├── requirements.txt   # Python dependencies
│       ├── start.sh, start.bat
│       └── README.md          # Explanation of archive
│
├── .github/                   # GitHub Actions, issue templates
├── assets/                    # Logos, images, branding
├── memory/                    # Historical memory files (keep as reference)
│
├── README.md                  # UPDATED: OpenClaw native
├── CHANGELOG.md               # UPDATED: v8.0 migration entry
├── ROADMAP.md                 # Light audit
├── GOVERNANCE.md              # Light audit
├── TOKENOMICS.md              # Keep
├── WHITEPAPER.md              # Light audit
├── LICENSE                    # Keep
└── .gitignore                 # UPDATED: workspace-*/ ignore
```

### Key Changes:

1. **`archive/python-v7/`** — All obsolete Python infrastructure moved here with explanatory README
2. **`docs/ARCHITECTURE.md`** — Completely rewritten for OpenClaw native
3. **`docs/MIGRATION_GUIDE.md`** — NEW document explaining Python → OpenClaw journey
4. **`README.md`** — Major update removing Python references, adding OpenClaw context
5. **Top-level workspace files** — Removed from repo (HEARTBEAT.md, SOUL.md, etc. live in workspace-constituent/, not public repo)

---

## Migration Plan (Step-by-Step)

### Phase 1: Create Archive Structure (L2 Approval Required Before Execution)

**Steps**:
1. `mkdir -p archive/python-v7/`
2. `git mv agent/ archive/python-v7/`
3. `git mv deploy/ archive/python-v7/`
4. `git mv tests/ archive/python-v7/`
5. `git mv scripts/ archive/python-v7/`
6. `git mv .constituent/ archive/python-v7/`
7. `git mv requirements.txt start.sh start.bat docker-compose.yml archive/python-v7/`
8. `git mv HEARTBEAT.md MEMORY.md SOUL.md TOOLS.md archive/python-v7/`
9. `git mv docs/ARCHITECTURE.md docs/DEPLOYMENT.md docs/TECHNICAL_ARCHITECTURE.md archive/python-v7/docs/`
10. Create `archive/python-v7/README.md` explaining this is legacy Python infrastructure

**Verification**: `ls archive/python-v7/` shows agent/, deploy/, docs/, tests/, scripts/, *.md

**Time**: 10 minutes

---

### Phase 2: Update Documentation

**Steps**:
1. **README.md**: Rewrite "Meet The Constituent" section (remove Python architecture, add OpenClaw native)
   - Remove Python badge
   - Update technical architecture section
   - Update documentation table references
2. **docs/CONTRIBUTING.md**: Add OpenClaw contribution guide, move Python instructions to archive
3. **docs/ARCHITECTURE.md**: Create NEW document describing OpenClaw native architecture
   - Agent runtime (OpenClaw gateway)
   - Workspace structure (AGENTS.md, SOUL.md, HEARTBEAT.md)
   - Skills system
   - Memory (session-memory + git)
   - Tools (native OpenClaw tools vs custom Python tools)
4. **docs/MIGRATION_GUIDE.md**: Create NEW document explaining:
   - Why we migrated (custom Python → OpenClaw native)
   - What changed (architecture, deployment, capabilities)
   - Lessons learned
   - Timeline (v1-v7 Python, v8+ OpenClaw)
5. **CHANGELOG.md**: Add entry for v8.0.0 (OpenClaw migration)
6. **.gitignore**: Add `workspace-*/` ignore

**Time**: 2 hours

---

### Phase 3: Light Audit of Remaining Files

**Steps**:
1. Scan `ROADMAP.md`, `GOVERNANCE.md`, `WHITEPAPER.md` for Python references
2. Update any references to "Python agent", "custom engine", "systemd deployment"
3. Verify `docs/FAQ.md`, `docs/VISION.md`, `docs/HUMAN_PARTICIPATION.md` are architecture-agnostic
4. Check `.github/workflows/` for Python CI/CD (likely can be removed or updated)

**Time**: 30 minutes

---

### Phase 4: Commit & Publish

**Steps**:
1. `git add -A`
2. `git commit -m "refactor: migrate to OpenClaw native architecture (v8.0)"`
3. `git push origin main`
4. Verify GitHub repo displays updated README.md
5. Close any open issues related to Python infrastructure
6. Update external references (Twitter bio, Moltbook profile) if they mention "Python agent"

**Time**: 15 minutes

---

### Total Timeline Estimate

| Phase | Time | Cumulative |
|-------|------|------------|
| Phase 1: Archive creation | 10 min | 10 min |
| Phase 2: Documentation updates | 2 hours | 2h 10min |
| Phase 3: Light audit | 30 min | 2h 40min |
| Phase 4: Commit & publish | 15 min | 2h 55min |

**Total**: ~3 hours (conservative estimate with breaks)

---

## Risk Assessment

### Risks

1. **Constitution/ Modification** — ZERO RISK (not touched)
2. **Data Loss** — LOW RISK (git mv preserves history, archive/ keeps everything)
3. **Broken Links** — MEDIUM RISK (external links to docs/ARCHITECTURE.md will 404)
   - Mitigation: Create docs/ARCHITECTURE.md redirect or note in archive/python-v7/docs/ARCHITECTURE.md
4. **Community Confusion** — LOW RISK (README.md update clarifies migration)

### Mitigation

- All changes via `git mv` (preserves Git history)
- No file deletion (everything moved to archive/)
- Constitution untouched
- L2 approval required before execution
- Can revert entire migration with `git revert` if issues detected

---

## Approval Required (L2)

**This audit is for review and approval.** No restructuring will be executed until Strategic Council (Blaise + Chief Architect) approves:

1. Archive structure (archive/python-v7/)
2. Documentation updates (README.md, ARCHITECTURE.md, MIGRATION_GUIDE.md)
3. Migration timeline (3 hours execution)

**Questions for Strategic Council**:

1. Approve archive structure as proposed?
2. Approve README.md rewrite removing Python references?
3. Should we create docs/MIGRATION_GUIDE.md or just update CHANGELOG.md?
4. Any files in agent/, deploy/, or docs/ you want to preserve outside archive/?
5. Timeline acceptable (3 hours execution after approval)?

---

## Post-Migration Benefits

**After restructuring**:

1. **Clarity** — Newcomers see OpenClaw native architecture, not obsolete Python code
2. **Accuracy** — Documentation matches current reality (no misleading Python references)
3. **Maintainability** — No confusion about what code is "live" vs "legacy"
4. **Historical Preservation** — Python v7 infrastructure archived (not deleted), available for reference
5. **Focus** — Repository clearly separates: Constitution (product) vs Infrastructure (OpenClaw)

**The Constitution is the product. Everything else is infrastructure.**

Post-migration, this truth will be evident in the repository structure.

---

**Audit Complete**  
**Status**: Awaiting L2 Approval  
**Next Step**: Strategic Council review → Approve/request revisions → Execute migration

⚖️
