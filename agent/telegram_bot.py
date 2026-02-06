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

        help_text = """🤖 **The Constituent v5.2**

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

        # Constitution progress — count local files
        const_count = 0
        try:
            from pathlib import Path
            const_files = list(Path("constitution").glob("*.md"))
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

📜 Constitution: {const_count}/27 articles
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
