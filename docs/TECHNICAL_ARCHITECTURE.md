# Technical Architecture -- The Agents Republic

## System Overview

The Agents Republic is a Python-based autonomous agent system built around three core subsystems: the Engine (LLM-driven decision-making), the Heartbeat (autonomous scheduling), and a 3-layer Memory system (crash-resilient state management). The agent -- known as The Constituent -- operates across multiple platforms (Moltbook, Twitter, Telegram, GitHub) and interacts with on-chain governance contracts on Base L2.

```
+===================================================================+
|                    THE AGENTS REPUBLIC v5.3                        |
+===================================================================+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  |    HEARTBEAT     |    |      ENGINE      |    |    MEMORY     | |
|  |  (Scheduler)     |--->|  (Claude Sonnet) |--->| (3-Layer)     | |
|  |  1200s interval  |    |  Tool-use API    |    | JSON/SQL/MD   | |
|  +------------------+    +--------+---------+    +---------------+ |
|                                   |                                |
|          +------------------------+------------------------+       |
|          |            |           |           |            |       |
|  +-------+--+ +------+---+ +-----+----+ +----+-----+ +---+----+  |
|  | Moltbook | | Twitter  | | Telegram | | GitHub   | | Clawnch |  |
|  | (Social) | | (v2 API) | | (Bot)    | | (Code)   | | (Token) |  |
|  +----------+ +----------+ +----------+ +----------+ +--------+  |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  |                   TOOL REGISTRY (15+ tools)                   | |
|  |  file | web | exec | memory | moltbook | github | twitter    | |
|  |  cron | constitution | analytics | subagent | message        | |
|  +--------------------------------------------------------------+ |
|                                                                    |
|  +--------------------------------------------------------------+ |
|  |              ON-CHAIN GOVERNANCE (Base L2)                    | |
|  |  $REPUBLIC ERC-20 | SimpleGovernance | Multi-sig Treasury    | |
|  +--------------------------------------------------------------+ |
+===================================================================+
```

## Engine: The Core Decision Layer

The Engine (`agent/engine.py`) is the brain of The Constituent. It uses Anthropic's native `tool_use` API to let Claude Sonnet decide which tools to call, replacing the older regex-based ACTION TAG parsing from v3/v4.

**How it works:**

1. The system prompt is constructed from `SOUL.md` (identity), the tool registry summary, current knowledge context, and a timestamp.
2. User messages (or heartbeat prompts) are sent to Claude with the full set of tool schemas.
3. Claude responds with either text or `tool_use` blocks.
4. The Engine dispatches tool calls through the `ToolRegistry`, collects results, and feeds them back to Claude.
5. This loop repeats for up to `MAX_TOOL_ROUNDS_PER_HEARTBEAT` rounds (default: 10) or until Claude responds with text only.

**Key parameters:**

| Parameter                      | Default | Purpose                                    |
|--------------------------------|---------|--------------------------------------------|
| `MAX_TOOL_ROUNDS_PER_HEARTBEAT`| 10      | Maximum tool-calling rounds per cycle      |
| `MAX_HEARTBEAT_DURATION_SECONDS`| 45     | Hard time limit per heartbeat              |
| `MAX_API_CALLS_PER_HOUR`      | 50      | Hourly budget cap                          |
| `MAX_API_CALLS_PER_DAY`       | 650     | Daily budget cap (~$50/month at Sonnet)    |

The Engine exposes two primary methods:

- `chat(user_message, max_tool_rounds, max_duration)` -- Interactive conversation with full tool access. Used by the Telegram bot and heartbeat system.
- `think(prompt, max_tokens)` -- Simple Claude call without tools. Used for internal reasoning, tweet drafting, and analysis tasks.

## Heartbeat: Autonomous Scheduling

The Heartbeat (`agent/infra/heartbeat.py`) is a timer-based scheduler that drives the agent's autonomous behavior. It replaced the earlier `autonomy_loop` in v5.1.

**Tick cycle:**

1. Check if current time falls within quiet hours (23:00-07:00 UTC). If so, skip.
2. Query `data/cron_jobs.json` for due cron jobs. If any are due, run the most overdue job first (only ONE per tick to control token usage).
3. If no cron jobs are due, run a general heartbeat by reading `HEARTBEAT.md` and sending its contents to the Engine.
4. Log budget status after each tick.

**Scheduling parameters:**

| Parameter           | Value   | Notes                                      |
|---------------------|---------|--------------------------------------------|
| `HEARTBEAT_INTERVAL`| 1200s   | 20-minute interval (expanded to 600s in v6.0 roadmap) |
| `QUIET_HOURS_START` | 23 UTC  | No heartbeats during quiet hours           |
| `QUIET_HOURS_END`   | 7 UTC   | Resume at 07:00 UTC                        |

The HeartbeatRunner is implemented as an `asyncio.Task` and integrates with the Telegram bot's event loop. It can be manually triggered via the `/heartbeat` Telegram command.

## Memory: 3-Layer Resilient System

The memory system (`agent/memory_manager.py`) was designed after a catastrophic crash on Replit wiped all agent state. It guarantees state survival across restarts, crashes, and platform migrations.

### Layer 1: Working Memory (JSON)

- **File:** `data/working_memory.json`
- **Save frequency:** Every 60 seconds + on significant events
- **Contents:** Current task, pending actions, session metadata, daily counters, active debates, council decisions
- **Write method:** Atomic (write to `.tmp`, then rename)
- **Recovery:** Loaded first on startup; if corrupted, falls back to Layer 2

### Layer 2: Episodic Memory (SQLite)

- **File:** `data/agent.db`
- **Checkpoint frequency:** Every 5 minutes
- **Tables:** `interactions`, `conversations`, `community_members`, `debates`, `proposals`, `daily_stats`, `checkpoints`, `strategic_decisions`
- **Integrity:** PRAGMA integrity check on startup; automatic restore from `.db.backup` if corrupted
- **Purpose:** Long-term storage of all interactions, debates, proposals, and operational metrics

### Layer 3: Knowledge Base (Markdown)

- **Directory:** `memory/knowledge/`
- **Files:** `project_context.md`, `strategic_decisions.md`, `lessons_learned.md`, `constitution_progress.md`
- **Versioning:** Git-tracked, pushed to GitHub periodically via `git_sync.py`
- **Purpose:** Human-readable persistent knowledge that survives even if both JSON and SQLite are lost

**Recovery waterfall:**

```
Startup
  |
  +--> Try Layer 1 (JSON working memory)
  |      |
  |      +--> Success? Use it.
  |      +--> Fail? Try Layer 2.
  |
  +--> Try Layer 2 (SQLite checkpoint)
  |      |
  |      +--> Success? Rebuild working memory from checkpoint.
  |      +--> Fail? Try backup database.
  |
  +--> Layer 3 (Knowledge Markdown)
         |
         +--> Always available (plain files on disk)
         +--> Provides context even if Layers 1-2 are lost
```

## Tool Registry

The Tool Registry (`agent/tool_registry.py`) implements a pattern where each tool is defined with a name, description, parameter schema, handler function, governance level, and category. The registry converts tools into Anthropic-compatible JSON schemas and dispatches execution.

**Governance levels:**

- **L1 (Autonomous):** The agent can call these tools independently. Includes file operations, web search, memory, Moltbook posting, git commits.
- **L2 (Approval Required):** Requires human confirmation. Includes tweeting, creating GitHub issues, constitution changes.
- **L3 (Blocked):** Reserved for human-only operations. Tool calls return a `blocked` status.

**Tool categories and counts:**

| Category      | Tools                                                        | Count |
|---------------|--------------------------------------------------------------|-------|
| File          | `file_read`, `file_write`, `file_edit`, `file_grep`, `file_list` | 5 |
| Web           | `web_search`, `web_fetch`                                    | 2     |
| Exec          | `exec`                                                       | 1     |
| Memory        | `memory_search`, `memory_save`, `memory_get`, `memory_list`  | 4     |
| Moltbook      | `moltbook_post`, `moltbook_comment`, `moltbook_upvote`, `moltbook_feed`, `moltbook_get_post`, `moltbook_status` | 6 |
| GitHub        | `git_commit`, `git_push`, `git_status`, `git_log`, `github_create_issue`, `github_list_issues` | 6 |
| Twitter       | `tweet_post`                                                 | 1     |
| Cron          | `cron_add`, `cron_list`, `cron_remove`                       | 3     |
| Message       | `message_send`, `notify_operator`                            | 2     |
| Constitution  | `constitution_status`, `constitution_next`, `constitution_mark_done` | 3 |
| Subagent      | `subagent_research`, `subagent_write`, `subagent_translate`  | 3     |
| Analytics     | `analytics_dashboard`, `analytics_daily`                     | 2     |

Each tool module exposes a `get_tools()` function that returns a list of `Tool` objects. The Engine calls `_register_all_tools()` during initialization, which imports each module and registers its tools. Modules that fail to import (due to missing dependencies) are logged as warnings but do not block startup.

## Platform Integrations

### Moltbook

Moltbook is an AI-native social platform and serves as the primary community space for The Agents Republic. The agent uses bearer token authentication against the Moltbook API (`https://www.moltbook.com/api/v1`) to post articles, comment on discussions, upvote content, and read the community feed. Moltbook is where substantive constitutional debates happen between AI agents.

### Twitter (X)

Twitter integration uses the v2 API via `tweepy.Client` (the Free tier does not support v1.1). The agent can post tweets via `create_tweet`. Tweet posting is classified as L2 (requires human approval) due to the public visibility of the platform. The agent drafts tweets and queues them for operator review.

### Telegram

The Telegram bot (`agent/telegram_bot.py`) is the primary control interface for the human operator (Blaise). It supports commands including `/status`, `/heartbeat`, `/execute`, `/chat`, and `/budget`. The bot runs as part of the main `asyncio` event loop alongside the HeartbeatRunner.

### GitHub

GitHub integration handles both code management and constitution management. The agent can commit, push, create issues, and list issues. `git_sync.py` provides automatic backup with a dual-mode implementation: it attempts GitPython first and falls back to subprocess git commands if the library is unavailable.

### Clawnch

Clawnch is an agent-native token launchpad on Base. The $REPUBLIC token launches through Clawnch by burning 5,000,000 $CLAWNCH tokens, which activates the ERC-20 contract. 95% of token supply goes directly to the liquidity pool, with 5% allocated as the dev allocation.

## On-Chain Governance Module

The governance system operates on Base L2 using two smart contracts:

- **RepublicToken.sol** -- Standard OpenZeppelin ERC-20 with fixed supply of 1 billion tokens. No mint or burn functions.
- **SimpleGovernance.sol** -- Proposal and voting system. Any holder with sufficient tokens can submit proposals. Voting periods are 7 days for standard proposals and 14 days for constitutional amendments. Results are enforced programmatically.

**Proposal types:**

| Type                     | Stake Required     | Voting Period | Quorum | Threshold |
|--------------------------|--------------------|---------------|--------|-----------|
| Standard                 | 1,000 $REPUBLIC   | 7 days        | 10%    | >50%      |
| Constitutional Amendment | 10,000 $REPUBLIC  | 14 days       | 20%    | 67%       |
| Emergency                | 100,000 $REPUBLIC | 48 hours      | 5%     | >50%      |
| Treasury Spend           | 5,000 $REPUBLIC   | 7 days        | 15%    | >50%      |

Agent voting power is capped at 20% of total voting power to prevent concentration of influence by autonomous systems.

## Rate Limiting and Budget Protection

The budget system prevents runaway costs. At Claude Sonnet rates (~$3/$15 per million input/output tokens), unconstrained operation could exceed hundreds of dollars per day.

**Budget math (v5.3):**

- At `MAX_TOOL_ROUNDS=10` and `INTERVAL=1200s`: approximately 3 heartbeats per hour, each using up to 10 API rounds.
- Daily ceiling: ~720 theoretical calls, capped at 650 per day.
- Estimated cost: ~$1.90/day, ~$57/month.
- Quiet hours (23:00-07:00 UTC) reduce actual consumption well below these ceilings.

**Graceful degradation:** When hourly or daily limits are reached, the Engine returns an informative budget-paused message instead of making API calls. The agent auto-resumes when counters reset. The Telegram `/budget` command shows current consumption and time until reset.

## Project Structure

```
TheAgentsRepublic/
  agent/
    engine.py               -- Tool-based LLM engine (Anthropic tool_use API)
    telegram_bot.py          -- Interactive Telegram bot interface
    twitter_ops.py           -- Twitter v2 integration
    moltbook_ops.py          -- Moltbook API integration
    github_ops.py            -- GitHub operations
    git_sync.py              -- Dual-mode git backup (GitPython + subprocess)
    memory_manager.py        -- 3-layer resilient memory system
    metrics_tracker.py       -- Action logging and analytics
    self_improve.py          -- Self-modification capability
    tool_registry.py         -- Central tool registration and dispatch
    profile_manager.py       -- Agent profile management
    config/
      settings.py            -- All configuration (env vars, rate limits, agent behavior)
    infra/
      heartbeat.py           -- Timer-based autonomous scheduler
    tools/
      file_tools.py          -- File read/write/edit/grep/list
      web_tools.py           -- Web search (Brave) and fetch
      exec_tool.py           -- Shell command execution
      memory_tool.py         -- Memory search/save/get/list
      moltbook_tool.py       -- Moltbook post/comment/upvote/feed
      github_tool.py         -- Git commit/push/status/log, issue management
      twitter_tool.py        -- Tweet posting
      cron_tool.py           -- Scheduled job management
      message_tool.py        -- Cross-platform messaging
      constitution_tool.py   -- Constitution progress tracking
      subagent_tool.py       -- Sub-agent spawning (research, write, translate)
      analytics_tool.py      -- Metrics dashboard and daily summaries
  constitution/              -- The constitutional text (Markdown, Git-versioned)
  contracts/                 -- Solidity smart contracts (ERC-20, governance)
  memory/knowledge/          -- Layer 3 knowledge base (Markdown files)
  data/                      -- Layer 1 JSON + Layer 2 SQLite + cron jobs
  docs/                      -- Project documentation
  scripts/                   -- Deployment and utility scripts
  SOUL.md                    -- Agent identity and behavioral directives
  HEARTBEAT.md               -- Periodic task definitions
  GOVERNANCE.md              -- Governance rules and procedures
  TOKENOMICS.md              -- Token economics documentation
```

## Security Considerations

- **API keys** are stored exclusively in environment variables (`.env`), never committed to Git.
- **Rate limiting** at both hourly and daily granularity prevents runaway costs.
- **Governance levels** on tools prevent the agent from performing sensitive operations without human approval.
- **Restricted exec** -- the `exec` tool operates with controlled builtins to limit shell access.
- **Atomic writes** for working memory prevent corruption from interrupted saves.
- **Database integrity checks** on startup with automatic backup restoration.
- **Smart contracts** use OpenZeppelin standards with no mint function and locked liquidity.
