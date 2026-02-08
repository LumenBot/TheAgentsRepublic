"""
Telegram Bot Handler for The Constituent v5.2
===============================================
Full interactive Telegram bot adapted to v5.1 Engine architecture.

v5.2 fixes:
- /execute: Fixed multi-line parsing (preserved newlines, full builtins)
- /status: Reads from Engine.get_budget_status() instead of old autonomy_loop
- /heartbeat: Triggers engine.run_heartbeat() directly
- /autonomy: Shows heartbeat budget instead of dead autonomy_loop
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("TheConstituent.TelegramBot")

try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed")


class TelegramBotHandler:
    """Interactive Telegram bot for The Constituent v5.2."""

    TWEET_POST_INTERVAL = 300

    def __init__(self, agent=None):
        self.agent = agent
        self.application = None
        self._running = False
        self.autonomy_loop = None
        self.start_time = datetime.now()
        self.last_activity: Optional[datetime] = None
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_ids = self._parse_allowed_chats()

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment.")
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed.")

    def _parse_allowed_chats(self) -> set:
        allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")
        operator_chat = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID", "")
        chat_ids = set()
        if operator_chat:
            try:
                chat_ids.add(int(operator_chat))
            except ValueError:
                pass
        for cid in allowed.split(","):
            cid = cid.strip()
            if cid:
                try:
                    chat_ids.add(int(cid))
                except ValueError:
                    pass
        return chat_ids

    def set_agent(self, agent):
        self.agent = agent

    def _is_authorized(self, chat_id: int) -> bool:
        if not self.allowed_chat_ids:
            return True
        return chat_id in self.allowed_chat_ids

    # =========================================================================
    # General Commands
    # =========================================================================

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text(f"Unauthorized. Your chat ID: {chat_id}")
            return
        await update.message.reply_text(
            "🏛️ Welcome to The Constituent v3.0\n"
            "🚨 Constitutional Sprint Mode ACTIVE\n\n"
            "/help for commands, or just send a message."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        help_text = """🤖 **The Constituent v6.0**

📋 **General**
├ /start - Welcome
├ /status - Agent status + budget
└ /help - This message

📊 **Metrics & Sprint**
├ /metrics - Today's metrics + ratio
├ /profile - Public profile summary
└ /ratio - Execution/philosophy ratio

🧠 **Memory & Sync**
├ /memory - Memory details
├ /save - Force save state
├ /sync - Git commit + push
└ /migrate - Full backup

📜 **Constitution**
├ /constitution - Read Constitution
└ /suggest <section> <proposal> - Propose edit

🐦 **Twitter**
├ /tweet <topic> - Draft tweet
├ /approve / /reject / /show

🦞 **Moltbook**
├ /moltbook - Status
├ /mfeed - Hot posts
├ /mpost <title> | <content> - Post
└ /mregister - Register

💎 **Token & DAO** (v6.0)
├ /launch\\_token - Check launch readiness
├ /confirm\\_launch - Deploy $REPUBLIC
├ /token\\_status - Token metrics
├ /proposal [title|desc] - Create/list proposals
└ /treasury - DAO treasury status

🔥 **Clawnch** (v6.1)
├ /clawnch\\_status - Integration status
├ /clawnch\\_balance - $CLAWNCH balance
├ /clawnch\\_burn - Execute burn (L2)
├ /clawnch\\_check <tx> - Verify tx
└ /clawnch\\_launch <tx> - Launch with burn tx

📋 **Briefing & Token** (v6.2)
├ /briefing - Daily status briefing
└ /republic - $REPUBLIC on-chain status

🧠 **CLAWS Memory** (v6.2)
├ /claws\\_status - Memory connection status
├ /claws\\_recall <query> - Search memories
├ /claws\\_recent [n] - Recent memories
├ /claws\\_remember <text> - Store a memory
└ /claws\\_seed - Seed $REPUBLIC token data

📈 **Trading & Market Making** (v6.3)
├ /portfolio - Portfolio status & P&L
├ /scout - Scan Clawnch for opportunities
├ /trade\\_buy <addr> <amount> - Buy a token
├ /trade\\_sell <addr> [amount] - Sell a token
├ /mm [start|stop|status|cycle] - Market maker
└ /price - $REPUBLIC price

🧠 **Heartbeat Engine**
├ /autonomy - Budget + heartbeat stats
├ /heartbeat [section] - Trigger heartbeat
└ /reflect - Agent self-reflection

🔧 **System** (Operator)
├ /execute <code> - Run Python (multi-line OK)
└ /improve <cap> - Self-improve

💬 Just send a message to chat."""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        # v5.2: Adapted to v5.1 Engine architecture
        status = self.agent.get_status()
        chat_id = update.effective_chat.id

        # Service status — check actual connection objects
        claude_ok = "✅" if status.get('model') else "❌"
        github_ok = "✅" if hasattr(self.agent, 'github') and self.agent.github.is_connected() else "⏳"
        moltbook_ok = "✅" if hasattr(self.agent, 'moltbook') and self.agent.moltbook.is_connected() else "⏳"

        twitter_icon = "⏳"
        if hasattr(self.agent, 'twitter'):
            if self.agent.twitter.has_write_access():
                twitter_icon = "✅"
            elif self.agent.twitter.is_connected():
                twitter_icon = "⚠️"  # Connected but no write

        # Budget from v5.1 engine
        budget = self.agent.get_budget_status() if hasattr(self.agent, 'get_budget_status') else {}

        # Metrics
        ratio = self.agent.metrics.get_today_ratio()
        sprint = self.agent.metrics.get_sprint_summary()

        # Constitution progress — count article files recursively
        const_count = 0
        const_total = 26  # Articles 1-26 planned
        try:
            from pathlib import Path
            const_files = list(Path("constitution").glob("**/ARTICLE_*.md"))
            const_count = len(const_files)
        except Exception:
            pass

        # Tweet counts
        tweet_counts = self.agent.twitter.get_all_counts()
        draft = self.agent.twitter.get_draft(chat_id)

        last_act = self.last_activity.strftime("%H:%M:%S") if self.last_activity else "—"

        text = f"""🤖 **The Constituent v{status.get('version', '5.1.0')}**
🚨 Sprint Day: {sprint.get('sprint_day', '?')}/21

🔗 Claude {claude_ok} | GitHub {github_ok} | Moltbook {moltbook_ok} | Twitter {twitter_icon}

📊 **Budget:** {budget.get('api_calls_this_hour', '?')}/{budget.get('max_per_hour', '?')} hourly, {budget.get('api_calls_today', '?')}/{budget.get('max_per_day', '?')} daily
📊 **Ratio:** {ratio.get('ratio', 0)} {'✅' if ratio.get('on_target') else '❌'} (exec: {ratio.get('execution_count', 0)} / phil: {ratio.get('philosophy_count', 0)})

📜 Constitution: {const_count}/{const_total} articles
🐦 Drafts: {1 if draft else 0} | Posted: {tweet_counts.get('posted', 0)}
🕐 Last: {last_act}

💡 /metrics /ratio /help"""

        await update.message.reply_text(text, parse_mode='Markdown')

    # =========================================================================
    # Sprint Commands (NEW v3.0)
    # =========================================================================

    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's metrics summary."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        summary = self.agent.metrics.get_daily_summary_text()
        await update.message.reply_text(summary, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show public profile summary."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        moltbook = self.agent.profile.get_moltbook_stats()
        github = self.agent.profile.get_github_stats()

        text = f"""📋 **The Constituent — Profile**

🦞 **Moltbook:** {'✅' if moltbook.get('connected') else '❌'}
├ Username: {moltbook.get('username', '?')}
├ URL: {moltbook.get('profile_url', '?')}
├ Posts: {moltbook.get('posts_count', 0)}
└ Last post: {moltbook.get('last_post') or 'Never'}

📂 **GitHub:** {'✅' if github.get('connected') else '❌'}
├ Repo: {github.get('repo_url', '?')}
└ Org: {github.get('org', '?')}

🐦 **Twitter:** @TheConstituent0 (⏳ pending)
📋 **4claw:** ⏳ pending setup

Full profile: agent_profile.md"""

        await update.message.reply_text(text, parse_mode='Markdown')

    async def ratio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick execution/philosophy ratio check."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        r = self.agent.metrics.get_today_ratio()
        icon = "✅" if r["on_target"] else "❌"

        text = (
            f"📊 **Today's Ratio: {r['ratio']:.2f}** {icon}\n\n"
            f"Execution actions: {r['execution_count']}\n"
            f"Philosophy actions: {r['philosophy_count']}\n"
            f"Target: ≥{r['target']}"
        )
        await update.message.reply_text(text, parse_mode='Markdown')

    # =========================================================================
    # Constitution Commands
    # =========================================================================

    async def constitution_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return
        section = " ".join(context.args) if context.args else "all"
        await update.message.reply_text("Reading Constitution...")
        try:
            content = self.agent.read_constitution(section)
            if len(content) > 4000:
                for i, chunk in enumerate([content[j:j+4000] for j in range(0, len(content), 4000)]):
                    await update.message.reply_text(f"[Part {i+1}]\n\n{chunk}")
            else:
                await update.message.reply_text(content)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def suggest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /suggest <section> <proposal>")
            return
        section = context.args[0]
        proposal = " ".join(context.args[1:])
        await update.message.reply_text(f"Analyzing proposal for {section}...")
        try:
            result = self.agent.suggest_constitution_edit(section, proposal)
            resp = f"Section: {result['section']}\nStatus: {result['status']}\n\n{result['analysis']}"
            if len(resp) > 4000:
                for chunk in [resp[i:i+4000] for i in range(0, len(resp), 4000)]:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(resp)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    # =========================================================================
    # Tweet Commands
    # =========================================================================

    async def tweet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /tweet <topic>")
            return
        topic = " ".join(context.args)
        await update.message.reply_text(f"✍️ Drafting tweet about: {topic}")
        try:
            tweet = self.agent.draft_tweet(topic)
            self.agent.twitter.save_draft(chat_id, tweet, topic)
            self.last_activity = datetime.now()
            await update.message.reply_text(
                f"📝 **Draft:**\n\n{tweet}\n\n`approve` / `reject` / `show`",
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("❌ No pending tweet.")
            return
        try:
            self.agent.twitter.approve_draft(chat_id)
            self.last_activity = datetime.now()
            await update.message.reply_text(f"✅ Tweet approved and queued!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("❌ No pending tweet.")
            return
        self.agent.twitter.reject_draft(chat_id)
        self.last_activity = datetime.now()
        await update.message.reply_text("🗑️ Tweet discarded.")

    async def show_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("📭 No pending tweet.")
            return
        await update.message.reply_text(
            f"📝 **Pending:**\n\n{draft['text']}\n\n`approve` / `reject`",
            parse_mode='Markdown'
        )

    # =========================================================================
    # Memory & Sync Commands
    # =========================================================================

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        mem = self.agent.memory
        wm = mem.working
        knowledge_files = list(mem.knowledge_dir.glob("*.md"))
        checkpoint = mem.get_latest_checkpoint()
        cp_info = f"{checkpoint['timestamp'][:19]} ({checkpoint['trigger']})" if checkpoint else "None"
        text = f"""🧠 **Memory System**
├ Task: {wm.current_task or 'None'}
├ Last conversation: {wm.last_conversation_with or 'None'}
├ Pending actions: {len(wm.pending_actions)}
├ Checkpoints: {wm.checkpoint_count}
├ Latest: {cp_info}
├ Knowledge files: {len(knowledge_files)}
└ DB size: {round(mem.db_path.stat().st_size / 1024, 1) if mem.db_path.exists() else 0} KB"""
        await update.message.reply_text(text, parse_mode='Markdown')

    async def save_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        await update.message.reply_text("💾 Saving...")
        try:
            self.agent.save_state()
            await update.message.reply_text("✅ State + metrics saved!")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text("🔄 Syncing...")
        try:
            from .git_sync import GitSync
            result = GitSync(repo_path=".").sync_now()
            lines = [
                "📊 **Git Sync**",
                f"├ Branch: `{result.get('branch', '?')}`",
                f"├ Committed: {'✅' if result.get('committed') else '⏭️ no changes'}",
                f"├ Unpushed: {result.get('unpushed_commits', '?')}",
                f"├ Pushed: {'✅' if result.get('pushed') else '❌'}",
            ]
            if result.get('error'):
                lines.append(f"└ ⚠️ {result['error']}")
            else:
                lines.append("└ ✅ Synced!")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def migrate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        await update.message.reply_text("🚚 Migration backup...")
        steps = []
        try:
            self.agent.memory.save_working_memory()
            self.agent.memory.create_checkpoint(trigger="migration")
            self.agent.memory.backup_database()
            self.agent.metrics.update_metrics_file()
            steps.append("✅ Memory + metrics saved")
        except Exception as e:
            steps.append(f"❌ Save error: {e}")
        try:
            from .git_sync import GitSync
            g = GitSync(repo_path=".")
            if g.auto_commit("migration: full snapshot"):
                steps.append("✅ Git committed" + (" + pushed" if g.push() else " (push failed)"))
            else:
                steps.append("ℹ️ No changes to commit")
        except Exception as e:
            steps.append(f"❌ Git: {e}")
        await update.message.reply_text(
            f"🚚 **Migration done**\n\n" + "\n".join(steps),
            parse_mode='Markdown'
        )

    async def improve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /improve <capability>")
            return
        cap = " ".join(context.args)
        await update.message.reply_text(f"Improving: {cap}")
        try:
            await update.message.reply_text(self.agent.improve_self(cap))
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # Code Execution (Operator only)
    # =========================================================================

    async def execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return
        operator_id = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
        if not operator_id or chat_id != int(operator_id):
            await update.message.reply_text("⚠️ Operator only.")
            return

        # v5.2: Extract code preserving newlines (was: " ".join(context.args) which destroyed newlines)
        raw_text = update.message.text or ""
        if raw_text.startswith("/execute"):
            code = raw_text[len("/execute"):]
        else:
            code = raw_text
        code = code.strip()

        if not code:
            await update.message.reply_text("Usage: /execute <python code>\n\nMulti-line supported.")
            return

        logger.info(f"[EXECUTE] {code[:100]}...")
        await update.message.reply_text(f"⚙️ Executing:\n```python\n{code}\n```", parse_mode='Markdown')
        try:
            import builtins as _builtins
            from io import StringIO

            # v5.2: Use full builtins so import/from-import statements work
            exec_globals = {
                '__builtins__': _builtins,
                'agent': self.agent, 'moltbook': self.agent.moltbook,
                'twitter': self.agent.twitter, 'github': self.agent.github,
                'memory': self.agent.memory, 'metrics': self.agent.metrics,
                'json': json, 'datetime': datetime,
            }
            old_stdout = sys.stdout
            sys.stdout = buf = StringIO()
            exec(code, exec_globals)
            sys.stdout = old_stdout
            output = buf.getvalue()
            if output:
                if len(output) > 3800:
                    output = output[:3800] + "\n..."
                await update.message.reply_text(f"✅ Output:\n```\n{output}\n```", parse_mode='Markdown')
            else:
                await update.message.reply_text("✅ Done (no output)")
        except Exception as e:
            sys.stdout = sys.__stdout__
            await update.message.reply_text(f"❌ Error:\n```\n{type(e).__name__}: {e}\n```", parse_mode='Markdown')

    # =========================================================================
    # Moltbook Commands
    # =========================================================================

    async def moltbook_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        s = self.agent.moltbook.get_status()
        text = f"""🦞 Moltbook
├ {'✅ Connected' if s['connected'] else '❌ Not connected'}
├ Agent: {s['agent_name']}
├ Posts: {s['posts_in_history']}
├ Can post: {'✅ Yes' if s.get('can_post') else f"⏳ Wait {s.get('wait_minutes', '?')}min"}
└ Last: {s['last_post'] or 'Never'}"""
        await update.message.reply_text(text)

    async def moltbook_feed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not self.agent.moltbook.is_connected():
            await update.message.reply_text("❌ Not connected. /mregister first.")
            return
        await update.message.reply_text("🔄 Fetching...")
        posts = self.agent.moltbook.get_feed(sort="hot", limit=5)
        if not posts:
            await update.message.reply_text("No posts.")
            return
        text = "🦞 Hot Feed\n\n"
        for i, p in enumerate(posts[:5], 1):
            author = p.get("author_name", p.get("author", "?"))
            title = p.get("title", p.get("content", "")[:80])
            likes = p.get("likes", p.get("upvotes", 0))
            text += f"{i}. [{author}] {title}\n   👍 {likes}\n\n"
        await update.message.reply_text(text)

    async def moltbook_post_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not self.agent.moltbook.is_connected():
            await update.message.reply_text("❌ Not connected.")
            return
        args = " ".join(context.args) if context.args else ""
        if "|" not in args:
            await update.message.reply_text("Usage: /mpost Title | Content")
            return
        parts = args.split("|", 1)
        title, content = parts[0].strip(), parts[1].strip()
        await update.message.reply_text(f"📝 Posting: {title}")
        result = self.agent.moltbook.create_post(title=title, content=content)
        if result.get("success"):
            self.agent.metrics.log_action("post", "moltbook", details={"title": title})
            await update.message.reply_text(f"✅ Posted!")
        else:
            err = result.get("error", "Unknown")
            self.agent.metrics.log_error("post", "moltbook", err)
            await update.message.reply_text(f"❌ Failed: {err}")

    async def moltbook_register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if self.agent.moltbook.is_connected():
            await update.message.reply_text("✅ Already connected!")
            return
        await update.message.reply_text("🔄 Registering...")
        result = self.agent.moltbook.register(
            name="TheConstituent",
            description="Constitutional facilitator for The Agents Republic."
        )
        if result.get("success"):
            r = result.get("response", {})
            await update.message.reply_text(
                f"✅ Registered!\nVerification: {r.get('verification_code', 'N/A')}"
            )
        else:
            await update.message.reply_text(f"❌ {result.get('response', result.get('error', '?'))}")

    # =========================================================================
    # Action Queue Commands
    # =========================================================================

    async def pending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        pending = self.agent.action_queue.get_pending()
        if not pending:
            await update.message.reply_text("✅ No pending actions.")
            return
        msg = "**⏳ PENDING L2 ACTIONS**\n\n"
        for a in pending:
            msg += f"**#{a['id']}** `{a['action_type']}`\n"
            if a.get('params'):
                msg += f"  Params: `{str(a['params'])[:150]}`\n"
            msg += f"  → `/qapprove {a['id']}` or `/qreject {a['id']}`\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def approve_action_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /qapprove <id>")
            return
        try:
            aid = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid ID.")
            return
        result = self.agent.action_queue.approve(aid, f"Blaise ({update.effective_chat.id})")
        if result.get("success"):
            await update.message.reply_text(f"✅ #{aid} approved & executed")
        else:
            await update.message.reply_text(f"❌ {result.get('error', '?')}")

    async def reject_action_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not initialized.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /qreject <id> [reason]")
            return
        try:
            aid = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid ID.")
            return
        reason = " ".join(context.args[1:]) or "No reason"
        result = self.agent.action_queue.reject(aid, reason)
        if result.get("success"):
            await update.message.reply_text(f"❌ #{aid} rejected: {reason}")
        else:
            await update.message.reply_text(f"❌ {result.get('error', '?')}")

    # =========================================================================
    # Autonomy Loop Commands
    # =========================================================================

    async def autonomy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v5.2: Shows heartbeat runner status (replaces old autonomy_loop)."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        budget = self.agent.get_budget_status() if hasattr(self.agent, 'get_budget_status') else {}
        await update.message.reply_text(
            f"🧠 **Heartbeat Engine (v5.1)**\n"
            f"├ API calls: {budget.get('api_calls_today', '?')}/{budget.get('max_per_day', '?')} daily\n"
            f"├ Hourly: {budget.get('api_calls_this_hour', '?')}/{budget.get('max_per_hour', '?')}\n"
            f"└ /heartbeat to trigger manually",
            parse_mode='Markdown'
        )

    async def heartbeat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v5.2: Trigger heartbeat directly via engine."""
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not init.")
            return
        await update.message.reply_text("🔄 Running heartbeat...")
        try:
            section = " ".join(context.args) if context.args else None
            result = self.agent.run_heartbeat(section=section)
            status = result.get("status", "?")
            duration = result.get("duration_ms", "?")
            response = result.get("response", "")
            if len(response) > 1500:
                response = response[:1500] + "..."
            await update.message.reply_text(f"✅ Heartbeat: {status} ({duration}ms)\n\n{response}")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def reflect_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v5.2: Reflection via engine.think() instead of autonomy_loop."""
        if not self._is_authorized(update.effective_chat.id) or not self.agent:
            await update.message.reply_text("Unauthorized or not init.")
            return
        await update.message.reply_text("🤔 Reflecting...")
        try:
            r = self.agent.think(
                "Brief self-reflection: What have you accomplished today? "
                "What's the most important next action? Under 100 words.",
                max_tokens=300
            )
            await update.message.reply_text(f"✅ {r}")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # Token & Governance (v6.0)
    # =========================================================================

    async def launch_token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v6.0: Check token launch readiness via Clawnch."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .integrations.clawnch import ClawnchLauncher
            launcher = ClawnchLauncher()

            if not launcher.is_available:
                await update.message.reply_text(
                    "⚠️ Clawnch not available.\n"
                    "Install: `pip install web3 eth-account`\n"
                    "Configure: BASE_RPC_URL, AGENT_WALLET_ADDRESS, AGENT_WALLET_PRIVATE_KEY",
                    parse_mode='Markdown'
                )
                return

            readiness = launcher.check_launch_readiness()
            costs = launcher.estimate_costs()

            if readiness.get("ready"):
                lines = [
                    "🚀 **$REPUBLIC TOKEN LAUNCH READY**\n",
                    f"├ Wallet: `{launcher.wallet_address[:10]}...`",
                    f"├ Balance: {readiness.get('wallet_balance_eth', '?')} ETH",
                    f"├ Constitution: {readiness.get('constitution_articles', '?')} articles",
                    f"├ Gas estimate: {costs.get('gas_cost_eth', '?')} ETH",
                    f"├ Burn: {costs.get('clawnch_burn', '?')}",
                    "└ Status: ✅ READY\n",
                    "Reply `/confirm_launch` to deploy.",
                ]
            else:
                issues = readiness.get("issues", ["Unknown"])
                lines = [
                    "❌ **Not ready to launch**\n",
                    "Issues:",
                ]
                for issue in issues:
                    lines.append(f"  • {issue}")

            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def confirm_launch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v6.0: Final confirmation to execute token launch."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text(
            "⚠️ Token launch execution requires manual deployment.\n\n"
            "Use the deployment script:\n"
            "`python scripts/deploy_token.py --network base`\n\n"
            "After deployment, set REPUBLIC_TOKEN_ADDRESS in .env",
            parse_mode='Markdown'
        )

    async def token_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v6.0: Check $REPUBLIC token status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .integrations.clawnch import ClawnchLauncher
            launcher = ClawnchLauncher()
            status = launcher.get_token_status()

            if status["status"] == "not_launched":
                await update.message.reply_text("💎 $REPUBLIC not yet launched. Use /launch_token")
            elif status["status"] == "launched":
                lines = [
                    "💎 **$REPUBLIC Token**\n",
                    f"├ Address: `{status['token_address'][:16]}...`",
                    f"├ Explorer: {status['explorer_url']}",
                    f"└ Wallet: `{status.get('wallet', '?')[:16]}...`",
                ]
                await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            else:
                await update.message.reply_text(f"⚠️ {status.get('message', 'Unknown status')}")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # Clawnch Direct Commands (v6.1)
    # =========================================================================

    def _get_launcher(self):
        """Lazy-load a ClawnchLauncher instance."""
        from .integrations.clawnch import ClawnchLauncher
        return ClawnchLauncher()

    async def clawnch_balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check $CLAWNCH token balance on agent wallet."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            launcher = self._get_launcher()
            if not launcher.is_available:
                await update.message.reply_text("⚠️ Clawnch not available (web3 not connected).")
                return
            result = launcher.get_clawnch_balance()
            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return
            balance = result["balance"]
            burn_req = result["burn_amount_required"]
            sufficient = "✅" if result["sufficient_for_burn"] else "❌"
            lines = [
                "💰 **$CLAWNCH Balance**\n",
                f"├ Balance: {balance:,.0f} $CLAWNCH",
                f"├ Burn required: {burn_req:,} $CLAWNCH",
                f"└ Sufficient: {sufficient}",
            ]
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def clawnch_burn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute the $CLAWNCH burn (L2 — requires operator approval)."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            launcher = self._get_launcher()
            if not launcher.is_available:
                await update.message.reply_text("⚠️ Clawnch not available (web3 not connected).")
                return
            await update.message.reply_text("🔥 Broadcasting burn tx...")
            result = launcher.execute_burn()
            if "error" in result:
                await update.message.reply_text(f"❌ Burn failed: {result['error']}")
                return
            lines = [
                "🔥 **Burn Broadcast**\n",
                f"├ Status: {result['status']}",
                f"├ Amount: {result['amount']:,} $CLAWNCH",
                f"├ Tx: `{result['tx_hash'][:18]}...`",
                f"└ Explorer: {result['explorer_url']}\n",
                "Use /clawnch_check to verify confirmation.",
            ]
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def clawnch_check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check status of a transaction. Usage: /clawnch_check <tx_hash>"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: `/clawnch_check <tx_hash>`", parse_mode='Markdown')
            return
        try:
            launcher = self._get_launcher()
            if not launcher.is_available:
                await update.message.reply_text("⚠️ Clawnch not available (web3 not connected).")
                return
            result = launcher.check_tx(args[0])
            status = result.get("status", result.get("error", "unknown"))
            lines = [f"🔍 **Tx Status: {status}**\n"]
            if result.get("block"):
                lines.append(f"├ Block: {result['block']}")
            if result.get("gas_used"):
                lines.append(f"├ Gas used: {result['gas_used']}")
            if result.get("explorer_url"):
                lines.append(f"└ {result['explorer_url']}")
            if result.get("message"):
                lines.append(f"└ {result['message']}")
            if result.get("error"):
                lines.append(f"└ Error: {result['error']}")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def clawnch_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Clawnch integration status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            launcher = self._get_launcher()
            status = launcher.get_status()
            readiness = launcher.check_launch_readiness() if launcher.is_available else {}
            lines = [
                "🚀 **Clawnch Status**\n",
                f"├ web3: {'✅' if status['web3_available'] else '❌'}",
                f"├ RPC: {'✅ connected' if status['connected'] else '❌ disconnected'}",
                f"├ Wallet: `{status['wallet'][:16]}...`" if len(status['wallet']) > 16 else f"├ Wallet: {status['wallet']}",
                f"├ Token deployed: {'✅' if status['token_deployed'] else '❌'}",
            ]
            if readiness.get("wallet_balance_eth") is not None:
                lines.append(f"├ ETH balance: {readiness['wallet_balance_eth']:.6f}")
            if readiness.get("issues"):
                lines.append("├ Issues:")
                for issue in readiness["issues"]:
                    lines.append(f"│   • {issue}")
            lines.append(f"└ Ready: {'✅' if readiness.get('ready') else '❌'}")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def clawnch_launch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute launch sequence. Usage: /clawnch_launch <burn_tx_hash>"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        burn_tx_hash = args[0] if args else ""

        if not burn_tx_hash:
            await update.message.reply_text(
                "Usage: `/clawnch_launch <burn_tx_hash>`\n\n"
                "Example:\n"
                "`/clawnch_launch 0xa8b5bc...`\n\n"
                "If burn not done yet, use `/clawnch_burn` first.",
                parse_mode='Markdown'
            )
            return

        await update.message.reply_text(f"🚀 Launching with burn tx `{burn_tx_hash[:18]}...`\nVerify → Upload → Validate → Post on m/clawnch...", parse_mode='Markdown')
        try:
            from .tools.clawnch_tool import _clawnch_launch
            result = _clawnch_launch(burn_tx_hash=burn_tx_hash)
            # Split long messages for Telegram 4096 char limit
            if len(result) > 4000:
                for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"❌ Launch failed: {e}")

    async def proposal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v6.0: Create or list governance proposals."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .governance.proposals import ProposalManager
            pm = ProposalManager()

            raw = update.message.text
            parts = raw.split(maxsplit=1)
            args_text = parts[1].strip() if len(parts) > 1 else ""

            if not args_text or args_text == "list":
                proposals = pm.list_proposals()
                if not proposals:
                    await update.message.reply_text("📋 No proposals yet. Use:\n`/proposal Title | Description`", parse_mode='Markdown')
                    return
                lines = ["📋 **Proposals**\n"]
                for p in proposals[-10:]:
                    icon = {"draft": "📝", "voting": "🗳️", "passed": "✅", "failed": "❌"}.get(p["status"], "❓")
                    lines.append(f"{icon} #{p['id']} {p['title']} [{p['status']}]")
                await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            elif "|" in args_text:
                title, description = args_text.split("|", 1)
                result = pm.create_proposal(title.strip(), description.strip())
                if result["status"] == "ok":
                    p = result["proposal"]
                    await update.message.reply_text(
                        f"✅ Proposal #{p['id']} created: {p['title']}\n"
                        f"Status: {p['status']}\n"
                        f"Discussion ends: {p['discussion_ends'][:10]}"
                    )
                else:
                    await update.message.reply_text(f"❌ {result['error']}")
            else:
                await update.message.reply_text("Usage: `/proposal Title | Description`", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def treasury_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """v6.0: Check DAO treasury status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .governance.treasury import TreasuryManager
            tm = TreasuryManager()
            status = tm.get_status()
            balances = status.get("balances", {})

            lines = ["🏦 **DAO Treasury**\n"]
            if balances:
                for currency, amount in balances.items():
                    lines.append(f"├ {currency}: {amount:,.2f}")
            else:
                lines.append("├ No transactions yet")
            lines.append(f"└ Total txns: {status.get('total_transactions', 0)}")

            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # Briefing & Token Commands (v6.2)
    # =========================================================================

    async def briefing_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send daily briefing."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .tools.briefing_tool import _daily_briefing
            briefing = _daily_briefing()
            if len(briefing) > 4000:
                for chunk in [briefing[i:i+4000] for i in range(0, len(briefing), 4000)]:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(briefing)
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def token_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get $REPUBLIC token on-chain status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .integrations.basescan import BaseScanTracker
            tracker = BaseScanTracker()
            await update.message.reply_text("🔍 Fetching on-chain data...")
            status = tracker.get_full_status()
            lines = [
                "💎 **$REPUBLIC On-Chain Status**\n",
                f"├ Address: `{status.get('address', '?')[:20]}...`",
                f"├ Chain: {status.get('chain', 'Base')}",
            ]
            if "total_supply" in status:
                lines.append(f"├ Supply: {status['total_supply']:,.0f}")
            lines.append(f"├ Holders: {status.get('holders', '?')}")
            lines.append(f"├ Recent transfers: {status.get('recent_transfers', '?')}")
            if "agent_balance" in status:
                lines.append(f"├ Agent balance: {status['agent_balance']:,.0f}")
            if "agent_eth" in status:
                lines.append(f"├ Agent gas: {status['agent_eth']:.6f} ETH")
            lines.append(f"└ Explorer: {status.get('explorer', '?')}")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # CLAWS Memory Commands (v6.2)
    # =========================================================================

    def _get_claws(self):
        """Lazy-load a ClawsMemory instance."""
        from .integrations.claws_memory import ClawsMemory
        return ClawsMemory()

    async def claws_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check CLAWS memory integration status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            claws = self._get_claws()
            status = claws.get_status()
            connected = "✅" if status.get("connected") else "❌"
            stats = status.get("stats") or {}
            total = stats.get("totalMemories", stats.get("total", "?"))
            lines = [
                "🧠 **CLAWS Memory Status**\n",
                f"├ Connected: {connected}",
                f"├ Agent ID: {status.get('agent_id', '?')}",
                f"├ API Key: {'✅ set' if status.get('api_key_set') else '⚠️ not set'}",
                f"├ Memories: {total}",
            ]
            if status.get("last_error"):
                lines.append(f"└ Last error: {status['last_error']}")
            else:
                lines.append(f"└ Status: OK")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def claws_recall_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search CLAWS memories. Usage: /claws_recall <query>"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: `/claws_recall <query>`", parse_mode='Markdown')
            return
        try:
            claws = self._get_claws()
            query = " ".join(args)
            result = claws.recall(query=query, limit=5)
            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return
            memories = result.get("memories", result.get("results", []))
            if not memories:
                await update.message.reply_text(f"No memories found for '{query}'")
                return
            lines = [f"🔍 **Recall: {query}**\n"]
            for mem in memories[:5]:
                if not isinstance(mem, dict):
                    continue
                content = mem.get("content", "")[:150]
                score = mem.get("score", mem.get("relevance", 0))
                mem_tags = mem.get("tags", [])
                tag_str = f" `[{', '.join(mem_tags[:3])}]`" if mem_tags else ""
                lines.append(f"• ({score:.2f}){tag_str} {content}")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def claws_recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get recent CLAWS memories. Usage: /claws_recent [limit]"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            claws = self._get_claws()
            limit = int(context.args[0]) if context.args else 5
            result = claws.recent(limit=limit)
            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return
            memories = result.get("memories", result.get("results", []))
            if not memories:
                await update.message.reply_text("No recent memories")
                return
            lines = [f"🕐 **Recent Memories ({len(memories)})**\n"]
            for mem in memories:
                if not isinstance(mem, dict):
                    continue
                content = mem.get("content", "")[:150]
                ts = mem.get("timestamp", mem.get("createdAt", ""))[:16]
                lines.append(f"• [{ts}] {content}")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def claws_remember_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Store a memory. Usage: /claws_remember <content>"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: `/claws_remember <content>`", parse_mode='Markdown')
            return
        try:
            claws = self._get_claws()
            content = " ".join(args)
            result = claws.remember(content=content, tags=["telegram", "manual"])
            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return
            mem_id = result.get("id", result.get("memoryId", "?"))
            await update.message.reply_text(f"✅ Memory stored (id={mem_id})")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    async def claws_seed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Seed CLAWS with $REPUBLIC token data."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            claws = self._get_claws()
            await update.message.reply_text("🌱 Seeding $REPUBLIC token data...")
            results = claws.seed_republic_token_data()
            ok = sum(1 for r in results if "error" not in r)
            fail = len(results) - ok
            msg = f"✅ Seeded {ok} token memories"
            if fail:
                msg += f" ({fail} errors)"
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")

    # =========================================================================
    # Trading & Market Making Commands (v6.3)
    # =========================================================================

    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trading portfolio status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .tools.trading_tool import _portfolio_status
            await update.message.reply_text(f"```\n{_portfolio_status()}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def scout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run Clawnch scout scan."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .tools.trading_tool import _scout_report
            report = _scout_report()
            if len(report) > 4000:
                report = report[:3997] + "..."
            await update.message.reply_text(f"```\n{report}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def trade_buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Buy a token. Usage: /trade_buy <token_address> <amount_clawnch> [reason]"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        if not args or len(args) < 2:
            await update.message.reply_text(
                "Usage: `/trade_buy <token_address> <amount_clawnch> [reason]`",
                parse_mode='Markdown')
            return
        try:
            from .tools.trading_tool import _buy_token
            token_addr = args[0]
            amount = args[1]
            reason = " ".join(args[2:]) if len(args) > 2 else "manual buy"
            result = _buy_token(token_addr, amount, reason)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def trade_sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sell a token. Usage: /trade_sell <token_address> [amount] [reason]"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: `/trade_sell <token_address> [amount] [reason]`",
                parse_mode='Markdown')
            return
        try:
            from .tools.trading_tool import _sell_token
            token_addr = args[0]
            amount = args[1] if len(args) > 1 else "0"
            reason = " ".join(args[2:]) if len(args) > 2 else "manual sell"
            result = _sell_token(token_addr, amount, reason)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def mm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Market maker control. Usage: /mm [start|stop|status|cycle]"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        args = context.args
        action = args[0].lower() if args else "status"
        try:
            from .tools.trading_tool import _mm_status, _mm_start, _mm_stop, _mm_cycle, _mm_evaluate
            if action == "start":
                await update.message.reply_text(_mm_start())
            elif action == "stop":
                await update.message.reply_text(_mm_stop())
            elif action == "cycle":
                await update.message.reply_text(_mm_cycle())
            elif action == "eval":
                await update.message.reply_text(_mm_evaluate())
            else:
                await update.message.reply_text(f"```\n{_mm_status()}\n```", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get $REPUBLIC price."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        try:
            from .tools.trading_tool import _republic_price
            await update.message.reply_text(_republic_price())
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    # =========================================================================
    # Chat Handler
    # =========================================================================

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id) or not self.agent:
            await update.message.reply_text(f"Unauthorized ({chat_id}) or not init.")
            return
        msg = update.message.text.strip().lower()
        logger.info(f"Message from {chat_id}: {msg[:50]}...")
        if msg in ["approve", "yes", "ok", "post", "queue"]:
            return await self.approve_command(update, context)
        if msg in ["reject", "no", "discard", "cancel", "delete"]:
            return await self.reject_command(update, context)
        if msg in ["show", "view", "pending", "current"]:
            return await self.show_command(update, context)

        self.last_activity = datetime.now()
        try:
            response = self.agent.chat(update.message.text)
            if len(response) > 4000:
                for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Chat error: {e}")
            await update.message.reply_text(f"Error: {e}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Telegram error: {context.error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Error occurred.")
            except:
                pass

    async def _tweet_poster_callback(self, context: ContextTypes.DEFAULT_TYPE):
        if not self.agent:
            return
        try:
            result = self.agent.twitter.post_queued_tweets()
            if result["posted"] > 0:
                operator = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
                if operator:
                    await context.bot.send_message(int(operator), f"🐦 Posted {result['posted']} tweet(s)")
        except Exception as e:
            logger.error(f"Tweet poster error: {e}")

    # =========================================================================
    # Application Builder
    # =========================================================================

    def build_application(self) -> Application:
        self.application = Application.builder().token(self.bot_token).build()

        handlers = [
            ("start", self.start_command),
            ("help", self.help_command),
            ("status", self.status_command),
            # Sprint (v3.0)
            ("metrics", self.metrics_command),
            ("profile", self.profile_command),
            ("ratio", self.ratio_command),
            # Constitution
            ("constitution", self.constitution_command),
            ("suggest", self.suggest_command),
            # Tweets
            ("tweet", self.tweet_command),
            ("approve", self.approve_command),
            ("reject", self.reject_command),
            ("show", self.show_command),
            # Memory & Sync
            ("memory", self.memory_command),
            ("save", self.save_command),
            ("sync", self.sync_command),
            ("migrate", self.migrate_command),
            # Moltbook
            ("moltbook", self.moltbook_command),
            ("mfeed", self.moltbook_feed_command),
            ("mpost", self.moltbook_post_command),
            ("mregister", self.moltbook_register_command),
            # Action Queue
            ("qpending", self.pending_command),
            ("qapprove", self.approve_action_command),
            ("qreject", self.reject_action_command),
            # Autonomy
            ("autonomy", self.autonomy_command),
            ("heartbeat", self.heartbeat_command),
            ("reflect", self.reflect_command),
            # System
            ("improve", self.improve_command),
            ("execute", self.execute_command),
            # Token & DAO (v6.0)
            ("launch_token", self.launch_token_command),
            ("confirm_launch", self.confirm_launch_command),
            ("token_status", self.token_status_command),
            ("proposal", self.proposal_command),
            ("treasury", self.treasury_command),
            # Clawnch direct commands (v6.1)
            ("clawnch_balance", self.clawnch_balance_command),
            ("clawnch_burn", self.clawnch_burn_command),
            ("clawnch_check", self.clawnch_check_command),
            ("clawnch_status", self.clawnch_status_command),
            ("clawnch_launch", self.clawnch_launch_command),
            # Briefing & Token (v6.2)
            ("briefing", self.briefing_command),
            ("republic", self.token_info_command),
            # CLAWS memory commands (v6.2)
            ("claws_status", self.claws_status_command),
            ("claws_recall", self.claws_recall_command),
            ("claws_recent", self.claws_recent_command),
            ("claws_remember", self.claws_remember_command),
            ("claws_seed", self.claws_seed_command),
            # Trading & Market Making (v6.3)
            ("portfolio", self.portfolio_command),
            ("scout", self.scout_command),
            ("trade_buy", self.trade_buy_command),
            ("trade_sell", self.trade_sell_command),
            ("mm", self.mm_command),
            ("price", self.price_command),
        ]

        for cmd, handler in handlers:
            self.application.add_handler(CommandHandler(cmd, handler))

        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        self.application.add_error_handler(self.error_handler)

        jq = self.application.job_queue
        if jq:
            jq.run_repeating(self._tweet_poster_callback, interval=self.TWEET_POST_INTERVAL, first=60, name="tweet_poster")
            logger.info(f"✅ Tweet poster scheduled")

        return self.application

    async def run_async(self):
        if not self.application:
            self.build_application()
        self._running = True
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        while self._running:
            await asyncio.sleep(1)
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    def run(self):
        if not self.application:
            self.build_application()
        self.application.run_polling(drop_pending_updates=True)

    def stop(self):
        self._running = False


def run_telegram_bot(agent=None):
    from .minimal import MinimalConstituent
    if agent is None:
        agent = MinimalConstituent()
    bot = TelegramBotHandler(agent)
    print("\nThe Constituent v3.0 — Telegram Bot\nSend /start to begin\n")
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()


def main():
    run_telegram_bot()


if __name__ == "__main__":
    main()
