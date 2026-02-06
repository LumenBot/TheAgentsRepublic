"""
Telegram Bot Handler for The Constituent
==========================================
Allows the agent to RECEIVE and RESPOND to Telegram messages interactively.

This is separate from notifications.py which only SENDS notifications.
This file implements a full Telegram bot that:
- Listens for incoming messages
- Routes them to the MinimalConstituent agent
- Sends responses back to users
"""

import os
import sys
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
    Interactive Telegram bot for The Constituent.

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
            agent: MinimalConstituent instance (optional, can be set later)
        """
        self.agent = agent
        self.application = None
        self._running = False

        # Activity tracking
        self.start_time = datetime.now()
        self.last_activity: Optional[datetime] = None

        # Get configuration from environment
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_ids = self._parse_allowed_chats()

        if not self.bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not found in environment. "
                "Please set it in Replit Secrets."
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

        # Add operator chat ID
        if operator_chat:
            try:
                chat_ids.add(int(operator_chat))
            except ValueError:
                pass

        # Add additional allowed IDs
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
        # If no allowed chats configured, allow all (for testing)
        if not self.allowed_chat_ids:
            return True
        return chat_id in self.allowed_chat_ids

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

        help_text = """🤖 **The Constituent v2.0 - Commands**

📋 **General**
├ /start - Welcome message
├ /status - Agent status and connections
└ /help - This help message

🧠 **Memory & Backup**
├ /memory - Detailed memory system view
├ /save - Force-save all state now
└ /migrate - Full backup + Git push (for PC migration)

📜 **Constitution**
├ /constitution - Read full Constitution
└ /suggest <section> <proposal> - Propose edit

🐦 **Twitter**
├ /tweet <topic> - Draft a tweet
├ /approve - Approve pending tweet
├ /reject - Discard pending tweet
└ /show - View pending tweet

✏️ **Self-Evolution**
└ /improve <capability> - Request self-improvement

💬 **Chat Mode**
Just send any message to chat with me."""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command with v2 memory status."""
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

        # Last activity
        last_activity_str = self.last_activity.strftime("%Y-%m-%d %H:%M:%S") if self.last_activity else "No activity yet"

        status_text = f"""🤖 **The Constituent v{status.get('version', '2.0.0')}**

📋 **Agent**
├ Model: {status.get('model', 'claude-sonnet-4-20250514')}
├ Session: {status.get('session_start', 'Unknown')[:16]}
└ Task: {status.get('current_task', 'None') or 'None'}

🔗 **Connections**
├ Claude API: {anthropic_status}
├ GitHub: {github_status}
└ Twitter: {twitter_status}

🧠 **Memory (Resilient)**
├ DB size: {db_size} KB
├ Checkpoints: {checkpoints}
├ Knowledge files: {knowledge_files}
└ Last save: {last_save[:19] if last_save else 'Never'}

🐦 **Tweets**
├ 📝 Your draft: {has_pending_draft}
├ ✅ Approved: {tweet_counts.get('approved', 0)}
└ 📤 Posted: {tweet_counts.get('posted', 0)}

📊 **Activity**
└ 🕐 Last: {last_activity_str}

💡 /help for commands | /memory for details"""

        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def constitution_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /constitution command."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        # Get section argument if provided
        section = " ".join(context.args) if context.args else "all"

        await update.message.reply_text("Reading Constitution...")

        try:
            content = self.agent.read_constitution(section)

            # Telegram has a 4096 character limit per message
            if len(content) > 4000:
                # Split into chunks
                chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(
                        f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"
                    )
            else:
                await update.message.reply_text(content)

        except Exception as e:
            await update.message.reply_text(f"Error reading Constitution: {e}")

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

            # Store the draft in twitter_ops (JSON persistence)
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

        # Get draft from twitter_ops (JSON storage)
        draft = self.agent.twitter.get_draft(chat_id)

        if not draft:
            await update.message.reply_text(
                "❌ No pending tweet to approve.\n"
                "Use /tweet <topic> to draft a new tweet first."
            )
            return

        tweet = draft["text"]
        topic = draft.get("topic", "Unknown")

        # Approve the draft (changes status to "approved" in JSON)
        try:
            self.agent.twitter.approve_draft(chat_id)
            self.last_activity = datetime.now()

            await update.message.reply_text(
                f"✅ **Tweet approved and queued!**\n\n"
                f"Topic: {topic}\n"
                f"Tweet: {tweet}\n\n"
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

        # Get and reject draft from twitter_ops (JSON storage)
        draft = self.agent.twitter.get_draft(chat_id)

        if not draft:
            await update.message.reply_text(
                "❌ No pending tweet to reject.\n"
                "Use /tweet <topic> to draft a new tweet first."
            )
            return

        topic = draft.get("topic", "Unknown")

        self.agent.twitter.reject_draft(chat_id)
        self.last_activity = datetime.now()

        await update.message.reply_text(
            f"🗑️ **Tweet discarded**\n\n"
            f"Topic: {topic}\n\n"
            "Use /tweet <topic> to draft a new one.",
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

        # Get draft from twitter_ops (JSON storage)
        draft = self.agent.twitter.get_draft(chat_id)

        if not draft:
            await update.message.reply_text(
                "📭 No pending tweet.\n"
                "Use /tweet <topic> to draft a new tweet."
            )
            return

        tweet = draft["text"]
        topic = draft.get("topic", "Unknown")
        timestamp = draft.get("queued_at", "Unknown")[:19]  # Trim ISO format

        await update.message.reply_text(
            f"📝 **Your Pending Tweet:**\n\n"
            f"Topic: {topic}\n"
            f"Created: {timestamp}\n\n"
            f"{tweet}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Commands:\n"
            "• `approve` - Queue for posting\n"
            "• `reject` - Discard this draft",
            parse_mode='Markdown'
        )

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

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory command - show detailed memory status."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        mem = self.agent.memory

        # Working memory details
        wm = mem.working
        knowledge_files = list(mem.knowledge_dir.glob("*.md"))

        # Get latest checkpoint
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
                "✅ **State saved!**\n"
                "├ Working memory: saved\n"
                "├ Checkpoint: created\n"
                "└ DB backup: done"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Save error: {e}")

    async def migrate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /migrate command — full backup + push for PC migration."""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return

        if not self.agent:
            await update.message.reply_text("Agent not initialized.")
            return

        await update.message.reply_text(
            "🚚 **Migration mode activated**\n\n"
            "Performing full state backup..."
        )

        steps = []

        # Step 1: Save all memory layers
        try:
            self.agent.memory.save_working_memory()
            self.agent.memory.create_checkpoint(trigger="migration")
            self.agent.memory.backup_database()
            steps.append("✅ Memory: working + checkpoint + DB backup")
        except Exception as e:
            steps.append(f"❌ Memory save error: {e}")

        # Step 2: Update knowledge base with migration note
        try:
            from datetime import datetime
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

        # Final report
        report = "\n".join(steps)
        await update.message.reply_text(
            f"🚚 **Migration backup complete**\n\n"
            f"{report}\n\n"
            f"**On the new PC:**\n"
            f"```\n"
            f"git clone https://github.com/LumenBot/TheAgentsRepublic.git\n"
            f"cd TheAgentsRepublic\n"
            f"# Copy your .env file\n"
            f"start.bat\n"
            f"```\n"
            f"I will wake up with my full memory intact. 🧠",
            parse_mode='Markdown'
        )

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
                "Usage: /improve <capability>\n"
                "Example: /improve add autonomous debate scheduling"
            )
            return

        capability = " ".join(context.args)
        await update.message.reply_text(f"Generating improvement: {capability}")

        try:
            result = self.agent.improve_self(capability)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error generating improvement: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages - route to agent chat or handle tweet approval."""
        chat_id = update.effective_chat.id

        if not self._is_authorized(chat_id):
            await update.message.reply_text(
                f"Unauthorized. Your chat ID: {chat_id}"
            )
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
            # Route to agent's chat function (use original case)
            response = self.agent.chat(update.message.text)

            # Handle long responses
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

    async def _tweet_poster_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Background task: Post approved tweets to Twitter.

        Runs every TWEET_POST_INTERVAL seconds.
        """
        logger.info("🔄 Tweet poster task running...")

        if not self.agent:
            logger.warning("Tweet poster: agent not initialized")
            return

        try:
            # Post queued tweets
            result = self.agent.twitter.post_queued_tweets()
            logger.info(f"Tweet poster result: {result}")

            # Log results
            if result["posted"] > 0 or result["failed"] > 0:
                logger.info(
                    f"Tweet posting: {result['posted']} posted, "
                    f"{result['failed']} failed, {result['skipped']} skipped"
                )

                # Notify operator of any posts or failures
                if result["posted"] > 0:
                    operator_chat = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
                    if operator_chat:
                        try:
                            await context.bot.send_message(
                                chat_id=int(operator_chat),
                                text=f"🐦 Auto-posted {result['posted']} tweet(s) to Twitter!"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify operator: {e}")

                if result["failed"] > 0:
                    operator_chat = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID")
                    if operator_chat:
                        try:
                            await context.bot.send_message(
                                chat_id=int(operator_chat),
                                text=f"⚠️ {result['failed']} tweet(s) failed to post. Check logs."
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify operator: {e}")

        except Exception as e:
            logger.error(f"Error in tweet poster task: {e}")
            # Don't crash - just log and continue

    def build_application(self) -> Application:
        """Build the Telegram application with handlers."""
        # Build application with JobQueue enabled (required for background tasks)
        self.application = (
            Application.builder()
            .token(self.bot_token)
            .build()
        )

        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("constitution", self.constitution_command))
        self.application.add_handler(CommandHandler("tweet", self.tweet_command))
        self.application.add_handler(CommandHandler("suggest", self.suggest_command))
        self.application.add_handler(CommandHandler("improve", self.improve_command))
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        self.application.add_handler(CommandHandler("save", self.save_command))
        self.application.add_handler(CommandHandler("migrate", self.migrate_command))

        # Tweet approval commands
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(CommandHandler("show", self.show_command))

        # Add message handler for regular chat
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Add error handler
        self.application.add_error_handler(self.error_handler)

        # Schedule background task for posting tweets
        job_queue = self.application.job_queue
        if job_queue is not None:
            job_queue.run_repeating(
                self._tweet_poster_callback,
                interval=self.TWEET_POST_INTERVAL,
                first=60,  # First run after 60 seconds
                name="tweet_poster"
            )
            logger.info(f"✅ Tweet poster scheduled every {self.TWEET_POST_INTERVAL}s (first run in 60s)")
        else:
            logger.error("❌ JobQueue is None - background tweet posting DISABLED!")
            logger.error("   Install: pip install 'python-telegram-bot[job-queue]'")

        return self.application

    async def run_async(self):
        """Run the bot asynchronously."""
        if not self.application:
            self.build_application()

        self._running = True
        logger.info("Starting Telegram bot...")

        # Initialize and start
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

        logger.info("Telegram bot is running. Press Ctrl+C to stop.")

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)

        # Cleanup
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
    """
    Convenience function to run the Telegram bot.

    Args:
        agent: Optional MinimalConstituent instance
    """
    from .minimal import MinimalConstituent

    # Create agent if not provided
    if agent is None:
        agent = MinimalConstituent()

    # Create and run bot
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
