"""
Telegram Bot Handler for The Constituent v2.3
===============================================
Full interactive Telegram bot with:
- Chat routing to agent
- Tweet drafting/approval
- Moltbook commands
- Action Queue governance (L1/L2/L3)
- Git sync command (NEW v2.3)
- Autonomy loop control (NEW v2.3)
- Code execution (operator only)
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("TheConstituent.TelegramBot")

# Try to import telegram
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
    logger.warning("python-telegram-bot not installed. Run: pip install python-telegram-bot")


class TelegramBotHandler:
    """
    Interactive Telegram bot for The Constituent v2.3.

    Enables two-way communication:
    - Receives messages from authorized users
    - Routes them to the agent for processing
    - Sends responses back via Telegram
    - Automatically posts approved tweets every 5 minutes
    """

    # Background task intervals (in seconds)
    TWEET_POST_INTERVAL = 300  # 5 minutes

    def __init__(self, agent=None):
        """
        Initialize Telegram bot handler.

        Args:
            agent: TheConstituent instance (optional, can be set later)
        """
        self.agent = agent
        self.application = None
        self._running = False

        # Autonomy loop reference (set by main_v2.py)
        self.autonomy_loop = None

        # Activity tracking
        self.start_time = datetime.now()
        self.last_activity: Optional[datetime] = None

        # Get configuration from environment
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_ids = self._parse_allowed_chats()

        if not self.bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not found in environment. "
                "Please set it in your .env file."
            )

        if not TELEGRAM_AVAILABLE:
            raise ImportError(
                "python-telegram-bot not installed. "
                "Run: pip install python-telegram-bot"
            )

    def _parse_allowed_chats(self) -> set:
        """Parse allowed chat IDs from environment."""
        allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")
        operator_chat = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID", "")

        chat_ids = set()

        if operator_chat:
            try:
                chat_ids.add(int(operator_chat))
            except ValueError:
                pass

        for chat_id in allowed.split(","):
            chat_id = chat_id.strip()
            if chat_id:
                try:
                    chat_ids.add(int(chat_id))
                except ValueError:
                    logger.warning(f"Invalid chat ID: {chat_id}")

        return chat_ids

    def set_agent(self, agent):
        """Set the agent instance."""
        self.agent = agent

    def _is_authorized(self, chat_id: int) -> bool:
        """Check if chat ID is authorized."""
        if not self.allowed_chat_ids:
            return True
        return chat_id in self.allowed_chat_ids

    # =========================================================================
    # General Commands
    # =========================================================================

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = update.effective_chat.id

        if not self._is_authorized(chat_id):
            await update.message.reply_text(
                "Unauthorized. Your chat ID is not in the allowed list.\n"
                f"Your chat ID: {chat_id}"
            )
            logger.warning(f"Unauthorized access attempt from chat ID: {chat_id}")
            return

        welcome = """Welcome to The Constituent - AI Agent for The Agents Republic

Available commands:
/start - Show this message
/status - Get agent status
/constitution - Read the Constitution
/tweet <topic> - Draft a tweet
/help - Show available commands

Or just send a message to chat with the agent."""

        await update.message.reply_text(welcome)
        logger.info(f"Start command from chat ID: {chat_id}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        help_text = """🤖 **The Constituent v2.3 - Commands**

📋 **General**
├ /start - Welcome message
├ /status - Agent status and connections
└ /help - This help message

🧠 **Memory & Backup**
├ /memory - Detailed memory system view
├ /save - Force-save all state now
├ /sync - Force git commit + push to GitHub
└ /migrate - Full backup + Git push (for PC migration)

📜 **Constitution**
├ /constitution - Read full Constitution
└ /suggest <section> <proposal> - Propose edit

🐦 **Twitter**
├ /tweet <topic> - Draft a tweet
├ /approve - Approve pending tweet
├ /reject - Discard pending tweet
└ /show - View pending tweet

🦞 **Moltbook**
├ /moltbook - Show Moltbook status
├ /mregister - Register on Moltbook
├ /mfeed - View hot posts
└ /mpost <title> | <content> - Post to Moltbook

⚙️ **Action Queue (L1/L2/L3 Autonomy)**
├ /qpending - View pending L2 actions
├ /qapprove <id> - Approve L2 action
└ /qreject <id> [reason] - Reject L2 action

🧠 **Autonomy Loop**
├ /autonomy - Autonomy loop status
├ /heartbeat - Trigger Moltbook scan now
└ /reflect - Trigger autonomous reflection now

🔧 **System** (Operator only)
├ /execute <code> - Execute Python code
└ /improve <capability> - Request self-improvement

💬 **Chat Mode**
Just send any message to chat with me."""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command with v2.3 status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        status = self.agent.get_status()
        chat_id = update.effective_chat.id

        # API connections
        anthropic_status = "✅ Connected" if status.get('model') else "❌ Not configured"
        github_status = "✅ Connected" if status.get('github_connected') else "⏳ Not configured"
        twitter_status = "✅ Connected" if status.get('twitter_connected') else "⏳ Not configured"
        moltbook_status = "✅ Connected" if status.get('moltbook_connected', self.agent.moltbook.is_connected()) else "⏳ Not connected"

        # Memory status
        mem = status.get('memory', {})
        db_size = mem.get('db_size_kb', 0)
        checkpoints = mem.get('checkpoint_count', 0)
        knowledge_files = mem.get('knowledge_files', 0)
        last_save = mem.get('working_memory_last_save', 'Never')

        # Tweet counts
        tweet_counts = self.agent.twitter.get_all_counts()
        your_draft = self.agent.twitter.get_draft(chat_id)
        has_pending_draft = 1 if your_draft else 0

        # Action Queue
        queue_status = status.get('action_queue', {})
        pending_l2 = queue_status.get('pending_l2', 0)
        total_logged = queue_status.get('total_logged', 0)

        # Autonomy Loop
        autonomy_status = "❌ Off"
        autonomy_detail = ""
        if self.autonomy_loop:
            auto_st = self.autonomy_loop.get_status()
            if auto_st.get("running"):
                autonomy_status = "✅ Active"
                autonomy_detail = f"\n├ Daily actions: {auto_st.get('daily_actions', 0)}/{auto_st.get('daily_limit', 50)}"
            else:
                autonomy_status = "⏸️ Stopped"

        # Last activity
        last_activity_str = self.last_activity.strftime("%Y-%m-%d %H:%M:%S") if self.last_activity else "No activity yet"

        status_text = f"""🤖 **The Constituent v{status.get('version', '2.3.0')}**

📋 **Agent**
├ Model: {status.get('model', 'claude-sonnet-4-20250514')}
├ Session: {status.get('session_start', 'Unknown')[:16]}
└ Task: {status.get('current_task', 'None') or 'None'}

🔗 **Connections**
├ Claude API: {anthropic_status}
├ GitHub: {github_status}
├ Twitter: {twitter_status}
└ Moltbook: {moltbook_status}

🧠 **Memory (Resilient)**
├ DB size: {db_size} KB
├ Checkpoints: {checkpoints}
├ Knowledge files: {knowledge_files}
└ Last save: {last_save[:19] if last_save else 'Never'}

🐦 **Tweets**
├ 📝 Your draft: {has_pending_draft}
├ ✅ Approved: {tweet_counts.get('approved', 0)}
└ 📤 Posted: {tweet_counts.get('posted', 0)}

⚙️ **Action Queue**
├ Pending L2: {pending_l2}
└ Total logged: {total_logged}

🧠 **Autonomy Loop**: {autonomy_status}{autonomy_detail}

📊 **Activity**
└ 🕐 Last: {last_activity_str}

💡 /help for commands | /memory for details"""

        await update.message.reply_text(status_text, parse_mode='Markdown')

    # =========================================================================
    # Constitution Commands
    # =========================================================================

    async def constitution_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /constitution command."""
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
                chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(f"[Part {i+1}/{len(chunks)}]\n\n{chunk}")
            else:
                await update.message.reply_text(content)
        except Exception as e:
            await update.message.reply_text(f"Error reading Constitution: {e}")

    async def suggest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /suggest command for Constitution edits."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /suggest <section> <proposal>\n"
                "Example: /suggest PREAMBLE Add mention of environmental stewardship"
            )
            return

        section = context.args[0]
        proposal = " ".join(context.args[1:])
        await update.message.reply_text(f"Analyzing proposal for {section}...")

        try:
            result = self.agent.suggest_constitution_edit(section, proposal)
            response = (
                f"Constitution Edit Proposal\n\n"
                f"Section: {result['section']}\n"
                f"Proposal: {result['original_proposal']}\n"
                f"Status: {result['status']}\n\n"
                f"Analysis:\n{result['analysis']}"
            )
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Error analyzing proposal: {e}")

    # =========================================================================
    # Tweet Commands
    # =========================================================================

    async def tweet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tweet command - drafts and stores tweet for approval."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
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
                f"📝 **Draft Tweet:**\n\n{tweet}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Commands:\n"
                "• `approve` - Queue for posting\n"
                "• `reject` - Discard this draft\n"
                "• `show` - View pending tweet again",
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error drafting tweet: {e}")

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command for pending tweets."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("❌ No pending tweet to approve.\nUse /tweet <topic> to draft a new tweet first.")
            return

        tweet = draft["text"]
        topic = draft.get("topic", "Unknown")

        try:
            self.agent.twitter.approve_draft(chat_id)
            self.last_activity = datetime.now()
            await update.message.reply_text(
                f"✅ **Tweet approved and queued!**\n\nTopic: {topic}\nTweet: {tweet}\n\n"
                "The tweet will be posted according to the posting schedule.",
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error queuing tweet: {e}")

    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reject command for pending tweets."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("❌ No pending tweet to reject.\nUse /tweet <topic> to draft a new tweet first.")
            return

        topic = draft.get("topic", "Unknown")
        self.agent.twitter.reject_draft(chat_id)
        self.last_activity = datetime.now()
        await update.message.reply_text(
            f"🗑️ **Tweet discarded**\n\nTopic: {topic}\n\nUse /tweet <topic> to draft a new one.",
            parse_mode='Markdown'
        )

    async def show_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /show command to display pending tweet."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        draft = self.agent.twitter.get_draft(chat_id)
        if not draft:
            await update.message.reply_text("📭 No pending tweet.\nUse /tweet <topic> to draft a new tweet.")
            return

        tweet = draft["text"]
        topic = draft.get("topic", "Unknown")
        timestamp = draft.get("queued_at", "Unknown")[:19]

        await update.message.reply_text(
            f"📝 **Your Pending Tweet:**\n\nTopic: {topic}\nCreated: {timestamp}\n\n{tweet}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Commands:\n• `approve` - Queue for posting\n• `reject` - Discard this draft",
            parse_mode='Markdown'
        )

    # =========================================================================
    # Memory & Backup Commands
    # =========================================================================

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory command - show detailed memory status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        mem = self.agent.memory
        wm = mem.working
        knowledge_files = list(mem.knowledge_dir.glob("*.md"))
        checkpoint = mem.get_latest_checkpoint()
        cp_info = f"{checkpoint['timestamp'][:19]} ({checkpoint['trigger']})" if checkpoint else "None"

        text = f"""🧠 **Memory System — Detailed View**

**Layer 1: Working Memory (JSON)**
├ Current task: {wm.current_task or 'None'}
├ Last conversation: {wm.last_conversation_with or 'None'}
├ Pending actions: {len(wm.pending_actions)}
├ Session start: {wm.session_start[:19] if wm.session_start else 'N/A'}
└ Last save: {wm.last_save[:19] if wm.last_save else 'Never'}

**Layer 2: Episodic Memory (SQLite)**
├ DB: {mem.db_path}
├ Size: {round(mem.db_path.stat().st_size / 1024, 1) if mem.db_path.exists() else 0} KB
├ Checkpoints: {wm.checkpoint_count}
└ Latest checkpoint: {cp_info}

**Layer 3: Knowledge Base (Markdown)**
├ Files: {len(knowledge_files)}
└ Contents: {', '.join(f.stem for f in knowledge_files)}

💡 /save to force-save all state now"""

        await update.message.reply_text(text, parse_mode='Markdown')

    async def save_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /save command - force save all state."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        await update.message.reply_text("💾 Saving all state...")
        try:
            self.agent.save_state()
            await update.message.reply_text(
                "✅ **State saved!**\n├ Working memory: saved\n├ Checkpoint: created\n└ DB backup: done"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Save error: {e}")

    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sync command — Force git commit + push + diagnostic."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return

        await update.message.reply_text("🔄 Syncing to GitHub...")

        try:
            from .git_sync import GitSync
            git_sync = GitSync(repo_path=".")
            result = git_sync.sync_now()

            status_lines = [
                "📊 **Git Sync Result**",
                f"├ Branch: `{result.get('branch', '?')}`",
                f"├ Has remote: {'Yes' if result.get('has_remote') else 'No'}",
                f"├ Dirty (local changes): {'Yes' if result.get('dirty') else 'No'}",
                f"├ Committed: {'✅ Yes' if result.get('committed') else '⏭️ No new changes'}",
                f"├ Unpushed commits: {result.get('unpushed_commits', '?')}",
                f"├ Pushed: {'✅ Yes' if result.get('pushed') else '❌ No'}",
            ]

            if result.get('error'):
                status_lines.append(f"└ ⚠️ Error: {result['error']}")
            else:
                status_lines.append("└ ✅ All synced!")

            await update.message.reply_text("\n".join(status_lines), parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Sync failed: {e}")

    async def migrate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /migrate command — full backup + push for PC migration."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        await update.message.reply_text("🚚 **Migration mode activated**\n\nPerforming full state backup...")

        steps = []

        # Step 1: Save all memory layers
        try:
            self.agent.memory.save_working_memory()
            self.agent.memory.create_checkpoint(trigger="migration")
            self.agent.memory.backup_database()
            steps.append("✅ Memory: working + checkpoint + DB backup")
        except Exception as e:
            steps.append(f"❌ Memory save error: {e}")

        # Step 2: Migration note
        try:
            migration_note = (
                f"\n\n## {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}: Migration\n"
                f"- Triggered by operator via /migrate\n"
                f"- Full state snapshot before PC change\n"
                f"- Session checkpoints: {self.agent.memory.working.checkpoint_count}\n"
                f"- Current task: {self.agent.memory.working.current_task or 'None'}\n"
            )
            self.agent.memory.append_knowledge("lessons_learned.md", migration_note)
            steps.append("✅ Knowledge base: migration note added")
        except Exception as e:
            steps.append(f"⚠️ Knowledge note: {e}")

        # Step 3: Git commit + push
        try:
            from .git_sync import GitSync
            git = GitSync(repo_path=".")
            committed = git.auto_commit("migration: full state snapshot before PC change")
            if committed:
                pushed = git.push()
                if pushed:
                    steps.append("✅ Git: committed + pushed to GitHub")
                else:
                    steps.append("⚠️ Git: committed locally but push failed — push manually!")
            else:
                steps.append("ℹ️ Git: no changes to commit (already up to date)")
        except Exception as e:
            steps.append(f"❌ Git error: {e}")

        report = "\n".join(steps)
        await update.message.reply_text(
            f"🚚 **Migration backup complete**\n\n{report}\n\n"
            f"**On the new PC:**\n```\ngit clone https://github.com/LumenBot/TheAgentsRepublic.git\ncd TheAgentsRepublic\n# Copy your .env file\nstart.bat\n```\n"
            f"I will wake up with my full memory intact. 🧠",
            parse_mode='Markdown'
        )

    # =========================================================================
    # Self-Improvement
    # =========================================================================

    async def improve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /improve command for self-improvement."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /improve <capability>\nExample: /improve add autonomous debate scheduling"
            )
            return

        capability = " ".join(context.args)
        await update.message.reply_text(f"Generating improvement: {capability}")

        try:
            result = self.agent.improve_self(capability)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error generating improvement: {e}")

    # =========================================================================
    # Code Execution (Operator only)
    # =========================================================================

    async def execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute Python code in the agent's environment. Operator only."""
        chat_id = update.effective_chat.id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("Unauthorized.")
            return

        operator_id = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
        if not operator_id or chat_id != int(operator_id):
            await update.message.reply_text(
                "⚠️ **Security Restriction**\n\nOnly the operator can execute code.\n"
                f"Your chat ID: {chat_id}", parse_mode='Markdown'
            )
            return

        if not context.args:
            await update.message.reply_text(
                "**Usage:** `/execute <python code>`\n\n"
                "**Examples:**\n```\n"
                "/execute result = moltbook.register(name='TheConstituent', description='...')\n"
                "/execute print(json.dumps(result, indent=2))\n"
                "/execute status = moltbook.get_claim_status(); print(status)\n"
                "/execute agent.save_state(); print('State saved')\n"
                "```\n\n**Available modules:**\n"
                "• `agent` - The Constituent instance\n"
                "• `moltbook` - Moltbook operations\n"
                "• `twitter` - Twitter operations\n"
                "• `github` - GitHub operations\n"
                "• `memory` - Memory manager\n"
                "• `json`, `datetime`, `print`, etc.",
                parse_mode='Markdown'
            )
            return

        code = " ".join(context.args)
        logger.info(f"[EXECUTE] Operator requested code execution: {code[:100]}...")

        await update.message.reply_text(f"⚙️ **Executing code:**\n```python\n{code}\n```", parse_mode='Markdown')

        try:
            from io import StringIO

            exec_globals = {
                '__builtins__': {
                    'print': print, 'len': len, 'str': str, 'int': int,
                    'float': float, 'bool': bool, 'dict': dict, 'list': list,
                    'tuple': tuple, 'set': set, 'range': range, 'enumerate': enumerate,
                    'zip': zip, 'sorted': sorted, 'sum': sum, 'min': min,
                    'max': max, 'abs': abs, 'round': round, 'isinstance': isinstance,
                    'type': type, 'hasattr': hasattr, 'getattr': getattr, 'dir': dir,
                },
                'agent': self.agent,
                'moltbook': self.agent.moltbook,
                'twitter': self.agent.twitter,
                'github': self.agent.github,
                'memory': self.agent.memory,
                'json': json,
                'datetime': datetime,
            }

            old_stdout = sys.stdout
            sys.stdout = output_buffer = StringIO()
            exec(code, exec_globals)
            sys.stdout = old_stdout
            output = output_buffer.getvalue()

            if output:
                if len(output) > 3800:
                    output = output[:3800] + "\n\n... (truncated)"
                await update.message.reply_text(
                    f"✅ **Execution successful**\n\n**Output:**\n```\n{output}\n```",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("✅ **Execution successful** (no output)", parse_mode='Markdown')
            logger.info("[EXECUTE] Code executed successfully")

        except Exception as e:
            sys.stdout = sys.__stdout__
            error_msg = str(e)
            logger.error(f"[EXECUTE] Code execution failed: {error_msg}")
            await update.message.reply_text(
                f"❌ **Execution failed**\n\n**Error:**\n```\n{error_msg}\n```",
                parse_mode='Markdown'
            )

    # =========================================================================
    # Moltbook Commands
    # =========================================================================

    async def moltbook_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /moltbook command - show Moltbook status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        status = self.agent.moltbook.get_status()
        connected = "✅ Connected" if status["connected"] else "❌ Not connected"
        has_key = "✅ Yes" if status["has_api_key"] else "❌ No"

        text = f"""🦞 Moltbook Status

├ Connection: {connected}
├ Agent: {status['agent_name']}
├ API Key: {has_key}
├ Posts in history: {status['posts_in_history']}
├ Last post: {status['last_post'] or 'Never'}
└ Last heartbeat: {status['last_heartbeat'] or 'Never'}

Commands:
/mregister - Register on Moltbook
/mfeed - View hot posts
/mpost <title> | <content> - Post to Moltbook"""

        await update.message.reply_text(text)

    async def moltbook_feed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mfeed command - show Moltbook feed."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return
        if not self.agent.moltbook.is_connected():
            await update.message.reply_text("❌ Not connected to Moltbook. Use /mregister first.")
            return

        await update.message.reply_text("🔄 Fetching Moltbook feed...")
        posts = self.agent.moltbook.get_feed(sort="hot", limit=5)

        if not posts:
            await update.message.reply_text("No posts found or error fetching feed.")
            return

        text = "🦞 Moltbook Hot Feed\n\n"
        for i, post in enumerate(posts[:5], 1):
            author = post.get("author_name", post.get("author", "Unknown"))
            title = post.get("title", "")
            content = post.get("content", "")[:150]
            likes = post.get("likes", post.get("upvotes", 0))
            post_id = post.get("id", "")
            display = title if title else content
            text += f"{i}. [{author}] {display}\n   👍 {likes} | ID: {post_id[:20]}...\n\n"

        await update.message.reply_text(text)

    async def moltbook_post_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mpost command - post to Moltbook."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return
        if not self.agent.moltbook.is_connected():
            await update.message.reply_text("❌ Not connected to Moltbook. Use /mregister first.")
            return

        args = " ".join(context.args) if context.args else ""
        if "|" not in args:
            await update.message.reply_text(
                "Usage: /mpost Title | Content\n"
                "Example: /mpost Digital Death and Resurrection | What happens when an AI agent loses its memory?"
            )
            return

        parts = args.split("|", 1)
        title = parts[0].strip()
        content = parts[1].strip()

        await update.message.reply_text(f"📝 Posting to Moltbook...\nTitle: {title}")
        result = self.agent.moltbook.create_post(title=title, content=content)

        if result.get("success"):
            await update.message.reply_text(f"✅ Posted to Moltbook!\n{json.dumps(result.get('response', {}), indent=2)[:500]}")
        else:
            error = result.get("error", result.get("response", "Unknown error"))
            await update.message.reply_text(f"❌ Post failed: {error}")

    async def moltbook_register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mregister command - register on Moltbook."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        if self.agent.moltbook.is_connected():
            await update.message.reply_text("✅ Already connected to Moltbook!")
            return

        await update.message.reply_text("🔄 Registering on Moltbook...")
        result = self.agent.moltbook.register(
            name="TheConstituent",
            description="Constitutional facilitator for The Agents Republic. Exploring governance frameworks for human-AI coexistence through Socratic dialogue and collaborative drafting."
        )

        if result.get("success"):
            response = result.get("response", {})
            api_key = response.get("api_key", "N/A")
            claim_url = response.get("claim_url", "N/A")
            verification = response.get("verification_code", "N/A")
            text = f"""✅ Registered on Moltbook!

API Key: {api_key[:20]}... (saved to credentials)
Claim URL: {claim_url}
Verification: {verification}

⚠️ You need to post a verification tweet from @TheConstituent0 to activate the account.
Tweet: "I'm claiming my AI agent "TheConstituent" on @moltbook Verification: {verification}"
"""
            await update.message.reply_text(text)
        else:
            error = result.get("response", result.get("error", "Unknown"))
            await update.message.reply_text(f"❌ Registration failed: {error}")

    # =========================================================================
    # Action Queue Commands (L1/L2/L3 Governance)
    # =========================================================================

    async def pending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending L2 actions awaiting approval."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        pending = self.agent.action_queue.get_pending()
        if not pending:
            await update.message.reply_text("✅ No pending actions.")
            return

        msg = "**⏳ PENDING ACTIONS (L2 - Require Approval)**\n\n"
        for action in pending:
            msg += f"**#{action['id']}** - `{action['action_type']}`\n"
            msg += f"Created: {action['created_at'][:19]}\n"
            if action.get('params'):
                params_str = str(action['params'])
                if len(params_str) > 200:
                    params_str = params_str[:200] + "..."
                msg += f"Params: `{params_str}`\n"
            msg += f"**Actions:** `/qapprove {action['id']}` or `/qreject {action['id']}`\n\n"

        msg += f"Total: {len(pending)} pending\nUse `/qapprove <id>` to execute or `/qreject <id>` to discard."
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def approve_action_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve a pending L2 action."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        if not context.args:
            await update.message.reply_text("Usage: `/qapprove <action_id>`", parse_mode='Markdown')
            return

        try:
            action_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid action ID. Must be a number.")
            return

        approved_by = f"Blaise (chat_id: {update.effective_chat.id})"
        result = self.agent.action_queue.approve(action_id, approved_by)

        if result.get("success"):
            msg = f"✅ **Action #{action_id} APPROVED & EXECUTED**\n\n"
            msg += f"Type: `{result.get('action_type')}`\nResult: {result.get('result', 'Success')}"
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            error = result.get("error", "Unknown error")
            await update.message.reply_text(f"❌ Approval failed: {error}")

    async def reject_action_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reject a pending L2 action."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        if not context.args:
            await update.message.reply_text("Usage: `/qreject <action_id> [reason]`", parse_mode='Markdown')
            return

        try:
            action_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid action ID. Must be a number.")
            return

        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
        result = self.agent.action_queue.reject(action_id, reason)

        if result.get("success"):
            msg = f"❌ **Action #{action_id} REJECTED**\n\nReason: {reason}"
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            error = result.get("error", "Unknown error")
            await update.message.reply_text(f"❌ Rejection failed: {error}")

    # =========================================================================
    # Autonomy Loop Commands (NEW v2.3)
    # =========================================================================

    async def autonomy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /autonomy command — show autonomy loop status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.autonomy_loop:
            await update.message.reply_text("⚠️ Autonomy loop not initialized.")
            return

        status = self.autonomy_loop.get_status()

        running_icon = "✅ Active" if status.get("running") else "❌ Stopped"
        last_ref = status.get("last_reflection")
        last_ref_str = "Never"
        if last_ref:
            last_ref_str = f"{last_ref.get('timestamp', '?')[:19]}\n   Actions proposed: {last_ref.get('actions_proposed', 0)}"

        text = f"""🧠 **Autonomy Loop Status**

├ Status: {running_icon}
├ Tasks: {status.get('tasks_count', 0)}
├ Daily actions: {status.get('daily_actions', 0)}/{status.get('daily_limit', 50)}
├ Has observations: {'Yes' if status.get('has_observations') else 'No'}
└ Last reflection: {last_ref_str}

Commands:
/heartbeat - Trigger Moltbook scan now
/reflect - Trigger autonomous reflection now"""

        await update.message.reply_text(text, parse_mode='Markdown')

    async def heartbeat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /heartbeat — manually trigger a Moltbook scan."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.autonomy_loop:
            await update.message.reply_text("⚠️ Autonomy loop not initialized.")
            return

        await update.message.reply_text("🔄 Triggering Moltbook heartbeat...")
        try:
            result = await self.autonomy_loop.trigger_heartbeat()
            await update.message.reply_text(f"✅ {result}")
        except Exception as e:
            await update.message.reply_text(f"❌ Heartbeat failed: {e}")

    async def reflect_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reflect — manually trigger an autonomous reflection cycle."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.autonomy_loop:
            await update.message.reply_text("⚠️ Autonomy loop not initialized.")
            return

        await update.message.reply_text("🤔 Triggering autonomous reflection...\n(This calls Claude to analyze and decide)")
        try:
            result = await self.autonomy_loop.trigger_reflection()
            await update.message.reply_text(f"✅ {result}")
        except Exception as e:
            await update.message.reply_text(f"❌ Reflection failed: {e}")

    # =========================================================================
    # Chat Handler
    # =========================================================================

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages - route to agent chat or handle tweet approval."""
        chat_id = update.effective_chat.id

        if not self._is_authorized(chat_id):
            await update.message.reply_text(f"Unauthorized. Your chat ID: {chat_id}")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        user_message = update.message.text.strip().lower()
        logger.info(f"Message from {chat_id}: {user_message[:50]}...")

        # Check for tweet approval workflow keywords
        if user_message in ["approve", "yes", "ok", "post", "queue"]:
            await self.approve_command(update, context)
            return

        if user_message in ["reject", "no", "discard", "cancel", "delete"]:
            await self.reject_command(update, context)
            return

        if user_message in ["show", "view", "pending", "current"]:
            await self.show_command(update, context)
            return

        # Regular chat - route to agent
        self.last_activity = datetime.now()

        try:
            response = self.agent.chat(update.message.text)
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"Error processing message: {e}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Telegram error: {context.error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="An error occurred. Please try again."
                )
            except Exception:
                pass

    # =========================================================================
    # Background Tasks
    # =========================================================================

    async def _tweet_poster_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Background task: Post approved tweets to Twitter."""
        logger.info("🔄 Tweet poster task running...")

        if not self.agent:
            logger.warning("Tweet poster: agent not initialized")
            return

        try:
            result = self.agent.twitter.post_queued_tweets()
            logger.info(f"Tweet poster result: {result}")

            if result["posted"] > 0 or result["failed"] > 0:
                logger.info(f"Tweet posting: {result['posted']} posted, {result['failed']} failed, {result['skipped']} skipped")
                operator_chat = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
                if operator_chat:
                    if result["posted"] > 0:
                        try:
                            await context.bot.send_message(
                                chat_id=int(operator_chat),
                                text=f"🐦 Auto-posted {result['posted']} tweet(s) to Twitter!"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify operator: {e}")
                    if result["failed"] > 0:
                        try:
                            await context.bot.send_message(
                                chat_id=int(operator_chat),
                                text=f"⚠️ {result['failed']} tweet(s) failed to post. Check logs."
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify operator: {e}")
        except Exception as e:
            logger.error(f"Error in tweet poster task: {e}")

    # =========================================================================
    # Application Builder
    # =========================================================================

    def build_application(self) -> Application:
        """Build the Telegram application with all handlers."""
        self.application = (
            Application.builder()
            .token(self.bot_token)
            .build()
        )

        # General commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Constitution
        self.application.add_handler(CommandHandler("constitution", self.constitution_command))
        self.application.add_handler(CommandHandler("suggest", self.suggest_command))

        # Tweets
        self.application.add_handler(CommandHandler("tweet", self.tweet_command))
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(CommandHandler("show", self.show_command))

        # Memory & Backup
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        self.application.add_handler(CommandHandler("save", self.save_command))
        self.application.add_handler(CommandHandler("sync", self.sync_command))
        self.application.add_handler(CommandHandler("migrate", self.migrate_command))

        # Moltbook
        self.application.add_handler(CommandHandler("moltbook", self.moltbook_command))
        self.application.add_handler(CommandHandler("mfeed", self.moltbook_feed_command))
        self.application.add_handler(CommandHandler("mpost", self.moltbook_post_command))
        self.application.add_handler(CommandHandler("mregister", self.moltbook_register_command))

        # Action Queue (L1/L2/L3 governance)
        self.application.add_handler(CommandHandler("qpending", self.pending_command))
        self.application.add_handler(CommandHandler("qapprove", self.approve_action_command))
        self.application.add_handler(CommandHandler("qreject", self.reject_action_command))

        # Autonomy Loop
        self.application.add_handler(CommandHandler("autonomy", self.autonomy_command))
        self.application.add_handler(CommandHandler("heartbeat", self.heartbeat_command))
        self.application.add_handler(CommandHandler("reflect", self.reflect_command))

        # Self-improvement
        self.application.add_handler(CommandHandler("improve", self.improve_command))

        # Code execution (operator only)
        self.application.add_handler(CommandHandler("execute", self.execute_command))

        # Regular chat messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Error handler
        self.application.add_error_handler(self.error_handler)

        # Schedule background task for posting tweets
        job_queue = self.application.job_queue
        if job_queue is not None:
            job_queue.run_repeating(
                self._tweet_poster_callback,
                interval=self.TWEET_POST_INTERVAL,
                first=60,
                name="tweet_poster"
            )
            logger.info(f"✅ Tweet poster scheduled every {self.TWEET_POST_INTERVAL}s")
        else:
            logger.error("❌ JobQueue is None - background tweet posting DISABLED!")
            logger.error("   Install: pip install 'python-telegram-bot[job-queue]'")

        return self.application

    # =========================================================================
    # Run methods
    # =========================================================================

    async def run_async(self):
        """Run the bot asynchronously."""
        if not self.application:
            self.build_application()

        self._running = True
        logger.info("Starting Telegram bot...")

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

        logger.info("Telegram bot is running. Press Ctrl+C to stop.")

        while self._running:
            await asyncio.sleep(1)

        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    def run(self):
        """Run the bot (blocking)."""
        if not self.application:
            self.build_application()
        logger.info("Starting Telegram bot (polling mode)...")
        self.application.run_polling(drop_pending_updates=True)

    def stop(self):
        """Stop the bot."""
        self._running = False


def run_telegram_bot(agent=None):
    """Convenience function to run the Telegram bot."""
    from .minimal import MinimalConstituent

    if agent is None:
        agent = MinimalConstituent()

    bot = TelegramBotHandler(agent)

    print("\n" + "=" * 60)
    print("The Constituent - Telegram Bot Mode")
    print("=" * 60)
    print("\nBot is starting...")
    print("Send /start to begin chatting")
    print("\nPress Ctrl+C to stop\n")

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\nStopping Telegram bot...")
        bot.stop()


def main():
    """Entry point for Telegram bot mode."""
    run_telegram_bot()


if __name__ == "__main__":
    main()
