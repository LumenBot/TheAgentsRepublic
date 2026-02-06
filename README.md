# The Agents Republic — The Constituent v2.0

AI Agent facilitating the creation of a constitutional framework for human-AI coexistence.

## Quick Start (Windows — without Docker)

```bash
# 1. Clone the repo
git clone https://github.com/LumenBot/TheAgentsRepublic.git
cd TheAgentsRepublic

# 2. Configure your secrets
copy .env.example .env
# Then edit .env with your real API keys (Notepad, VS Code, etc.)

# 3. Start
start.bat
```

## Quick Start (Docker)

```bash
# 1. Clone + configure
git clone https://github.com/LumenBot/TheAgentsRepublic.git
cd TheAgentsRepublic
cp .env.example .env
# Edit .env with your keys

# 2. Run
docker-compose up -d

# 3. View logs
docker-compose logs -f
```

## Architecture

```
The Constituent v2.0
├── 🧠 3-Layer Resilient Memory (never loses state)
│   ├── Layer 1: Working Memory (JSON, saved every 60s)
│   ├── Layer 2: Episodic Memory (SQLite, checkpoints every 5min)
│   └── Layer 3: Knowledge Base (Markdown, Git-versioned)
├── 📱 Telegram Bot (control from iPhone)
├── 🐦 Twitter Integration (draft → approve → post)
├── 📜 Constitution Management (GitHub)
└── 🔄 Git Auto-Sync (commit 15min, push 1h)
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome + command list |
| `/status` | Agent status, connections, memory |
| `/memory` | Detailed memory system view |
| `/save` | Force-save all state now |
| `/constitution` | Read the Constitution |
| `/tweet <topic>` | Draft a tweet |
| `/approve` | Approve pending tweet |
| `/reject` | Discard pending tweet |
| `/suggest <section> <text>` | Propose Constitution edit |
| `/help` | Full command reference |

Or just send a message to chat with The Constituent.

## Project Structure

```
TheAgentsRepublic/
├── agent/
│   ├── main_v2.py          # Entry point (orchestrator)
│   ├── constituent.py       # Core agent (think, chat, draft)
│   ├── memory_manager.py    # 3-layer resilient memory
│   ├── git_sync.py          # Auto-commit + push to GitHub
│   ├── telegram_bot.py      # Telegram interface
│   ├── twitter_ops.py       # Twitter queue + posting
│   ├── github_ops.py        # Constitution on GitHub
│   ├── self_improve.py      # Self-modification (supervised)
│   ├── config/settings.py   # All configuration
│   └── core/personality.py  # Agent persona + prompts
├── constitution/            # The Constitution (Markdown)
├── memory/knowledge/        # Persistent knowledge base
├── data/                    # SQLite DB + working memory
├── docs/                    # Architecture docs + roadmaps
├── .env.example             # API keys template
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker orchestration
├── start.bat                # Windows quick start
└── start.sh                 # Linux/Mac quick start
```

## Migration to New PC

1. Push everything: `/save` on Telegram, then `git push`
2. On new PC: `git clone` + copy `.env` + `start.bat`
3. The agent recovers its full state automatically

## Strategic Council

| Member | Role | Channel |
|--------|------|---------|
| Human Director (you) | Vision, veto | Telegram |
| Claude Opus | Architecture | Claude.ai / API |
| The Constituent | Daily operations | Always running |

---

*v2.0 — Built for resilience. Memory that survives crashes.*
