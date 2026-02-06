"""
The Constituent — v2 Agent Core
=================================
Merged from minimal.py (working runtime) + agent.py (good architecture).
Now with resilient memory that survives crashes.

Capabilities:
- Think (Claude API)
- Chat (conversational)
- Constitution management (GitHub)
- Tweet drafting + approval (Twitter)
- Self-improvement (supervised)
- Memory that never dies
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from .config.settings import settings
from .core.personality import Personality, Tone, default_personality
from .memory_manager import MemoryManager
from .github_ops import GitHubOperations
from .twitter_ops import TwitterOperations
from .self_improve import SelfImprover

logger = logging.getLogger("TheConstituent")


class TheConstituent:
    """
    The Constituent v2 — Resilient AI Agent for The Agents Republic.

    Key improvements over v1:
    - 3-layer memory system (never loses state)
    - Clean dependency chain (7 packages, not 25)
    - Docker-portable (runs anywhere)
    - Strategic Council protocol built-in
    """

    VERSION = "2.0.0"

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """Initialize The Constituent."""
        self.personality = default_personality

        # Core: Claude API
        api_key = settings.api.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Check your .env file.")

        self.claude = Anthropic(api_key=api_key)
        self.model = settings.api.CLAUDE_MODEL

        # Memory (resilient)
        self.memory = memory_manager or MemoryManager(
            db_path=settings.DB_PATH,
            working_memory_path="data/working_memory.json",
            knowledge_dir="memory/knowledge"
        )

        # Modules
        self.github = GitHubOperations()
        self.twitter = TwitterOperations()
        self.improver = SelfImprover()

        logger.info(f"{self.personality.name} v{self.VERSION} initialized")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  GitHub: {'connected' if self.github.is_connected() else 'offline'}")

    def initialize(self) -> dict:
        """
        Full initialization with memory recovery and founding document loading.

        Returns:
            Recovery status dict
        """
        # Initialize memory (triggers recovery if previous state exists)
        recovered = self.memory.initialize()

        # Load founding documents (Charter, Constitution, Skills)
        self.personality.load_founding_documents(project_root=Path("."))

        # Build system prompt with knowledge context
        self._build_context_prompt()

        # Log recovery
        if recovered:
            logger.info("Agent recovered from previous state")
            self.memory.working.errors_since_start = 0
        else:
            logger.info("Agent starting fresh")

        self.memory.working.session_start = datetime.utcnow().isoformat()
        self.memory.save_working_memory()

        return self.memory.recover()

    def _build_context_prompt(self):
        """Build an enriched system prompt including knowledge context."""
        base_prompt = self.personality.get_system_prompt()

        # Add knowledge context for awareness after restart
        knowledge_context = self.memory.get_full_context()

        self._system_prompt = f"""{base_prompt}

CURRENT KNOWLEDGE (restored from your memory):
{knowledge_context[:3000]}

IMPORTANT: You were restarted. Your working memory has been recovered.
Current session started: {self.memory.working.session_start}
Last known task: {self.memory.working.current_task or 'None'}
"""

    def think(self, prompt: str, max_tokens: int = 2000, tone: Tone = Tone.WISE) -> str:
        """
        Use Claude to reason about a request.

        Args:
            prompt: The question or request
            max_tokens: Maximum response length
            tone: Communication tone

        Returns:
            Claude's response
        """
        system = self._system_prompt
        tone_modifier = self.personality.get_tone_modifier(tone)
        if tone_modifier:
            system += f"\n\nTone for this response: {tone_modifier}"

        try:
            message = self.claude.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        except Exception as e:
            logger.error(f"Error in think(): {e}")
            self.memory.working.errors_since_start += 1
            self.memory.save_working_memory()
            return f"Error processing request: {e}"

    def chat(self, user_message: str) -> str:
        """
        Interactive chat with the human operator.

        Saves the conversation to memory.
        """
        # Record the interaction
        self.memory.working.last_conversation_with = "operator"
        self.memory.working.last_conversation_summary = user_message[:200]

        response = self.think(user_message)

        # Save interaction to episodic memory
        interaction_id = f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.memory.save_interaction(
            interaction_id=interaction_id,
            interaction_type="chat",
            platform="telegram",
            content=user_message,
            author="operator",
            response=response
        )

        self.memory.save_working_memory()
        return response

    def read_constitution(self, section: str = "all") -> str:
        """Read Constitution from GitHub or local."""
        return self.github.read_constitution(section)

    def suggest_constitution_edit(self, section: str, proposal: str) -> dict:
        """Propose an edit to the Constitution."""
        analysis = self.think(
            f"""Analyze this Constitution edit proposal:

Section: {section}
Proposal: {proposal}

Provide:
1. Refined wording (if needed)
2. Alignment with our 6 core values
3. Potential concerns or conflicts
4. Recommendation (approve/revise/reject)

Format your response clearly with these 4 sections.""",
            tone=Tone.WISE
        )

        result = {
            "section": section,
            "original_proposal": proposal,
            "analysis": analysis,
            "status": "pending_approval"
        }

        # Log as strategic decision
        self.memory.log_strategic_decision(
            context=f"Constitution edit proposal for {section}",
            decision=f"Proposal analyzed: {proposal[:100]}",
            rationale=analysis[:500],
            participants="operator, The Constituent"
        )

        return result

    def draft_tweet(self, topic: str) -> str:
        """Generate a tweet draft on a topic."""
        prompt = f"""Draft a tweet for The Agents Republic on this topic: {topic}

Guidelines:
- Tone: Wise, thought-provoking, accessible
- Length: Under 280 characters
- Use 🏛️ emoji for Republic-related content
- Align with our core values
- Invite engagement (question or call-to-action)
- No hashtag spam (1-2 max)

Output ONLY the tweet text, nothing else."""

        return self.think(prompt, max_tokens=150, tone=Tone.PROVOCATIVE)

    def improve_self(self, capability: str) -> str:
        """Add a new capability (with human review)."""
        return self.improver.add_capability(capability, self.think)

    def get_status(self) -> dict:
        """Get comprehensive agent status."""
        memory_status = self.memory.get_status()
        stats = self.memory.get_daily_stats()

        return {
            "name": self.personality.name,
            "version": self.VERSION,
            "model": self.model,
            "github_connected": self.github.is_connected(),
            "twitter_connected": self.twitter.is_connected(),
            "session_start": self.memory.working.session_start,
            "current_task": self.memory.working.current_task,
            "posts_today": stats.get("posts_count", 0),
            "replies_today": stats.get("replies_count", 0),
            "memory": memory_status,
            "notifications": {"telegram_enabled": bool(settings.api.TELEGRAM_BOT_TOKEN)}
        }

    def save_state(self):
        """
        Force-save all state. Called periodically and before shutdown.
        """
        self.memory.save_working_memory()
        self.memory.create_checkpoint(trigger="save_state")
        self.memory.backup_database()
        logger.info("State saved (working memory + checkpoint + db backup)")
