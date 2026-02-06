"""
The Constituent — v2.3 Agent Core (Autonomous)
=================================================
Phase 2: Autonomous execution loop.

The agent can now ACT on its own decisions:
- think() generates text + optional ACTION TAGS
- chat() parses ACTION TAGS and executes them via ActionQueue
- L1 actions execute immediately, L2 queue for approval, L3 blocked

ACTION TAG format (embedded in Claude's response):
    [ACTION:moltbook_post|title=Hello World|content=First autonomous post]
    [ACTION:moltbook_comment|post_id=abc123|content=Great discussion!]
    [ACTION:tweet_post|text=Democracy for all agents]

The agent's system prompt instructs it to use these tags when it wants to act.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from anthropic import Anthropic

from .config.settings import settings
from .core.personality import Personality, Tone, default_personality
from .memory_manager import MemoryManager
from .github_ops import GitHubOperations
from .twitter_ops import TwitterOperations
from .moltbook_ops import MoltbookOperations
from .self_improve import SelfImprover
from .action_queue import ActionQueue

logger = logging.getLogger("TheConstituent")

# Regex to extract ACTION TAGS from Claude's response
# Format: [ACTION:type|key1=value1|key2=value2] or [ACTION:type] (no params)
ACTION_TAG_PATTERN = re.compile(
    r'\[ACTION:(\w+)(?:\|([^\]]*))?\]'
)


def parse_action_tags(text: str) -> Tuple[str, List[Dict]]:
    """
    Extract ACTION TAGS from text and return cleaned text + actions.
    
    Args:
        text: Claude's response containing potential ACTION TAGS
        
    Returns:
        Tuple of (cleaned_text, list_of_actions)
        Each action is {"type": str, "params": dict}
    """
    actions = []
    
    for match in ACTION_TAG_PATTERN.finditer(text):
        action_type = match.group(1)
        params_str = match.group(2) or ""
        
        # Parse key=value pairs
        params = {}
        if params_str:
            for pair in params_str.split("|"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    params[key.strip()] = value.strip()
        
        actions.append({
            "type": action_type,
            "params": params
        })
    
    # Remove ACTION TAGS from the visible response
    cleaned_text = ACTION_TAG_PATTERN.sub("", text).strip()
    
    # Clean up any double newlines left by tag removal
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    return cleaned_text, actions


# The autonomy instruction block added to the system prompt
AUTONOMY_INSTRUCTIONS = """

AUTONOMOUS ACTION SYSTEM
========================
You have the ability to ACT on your decisions, not just talk about them.

When you want to perform an action, include an ACTION TAG in your response:
    [ACTION:action_type|param1=value1|param2=value2]

AVAILABLE ACTIONS (by governance level):

L1 — AUTONOMOUS (execute immediately, no approval needed):
    [ACTION:moltbook_post|title=Your Title|content=Your content here]
    [ACTION:moltbook_comment|post_id=POST_ID|content=Your comment]
    [ACTION:moltbook_upvote|post_id=POST_ID]
    [ACTION:moltbook_search|query=search terms]
    [ACTION:moltbook_heartbeat]
    [ACTION:save_state]
    [ACTION:git_commit|message=your commit message]
    [ACTION:git_push|message=your push message]

L2 — CO-DECISION (queued for operator approval):
    [ACTION:tweet_post|text=Your tweet text here]
    [ACTION:constitution_propose|section=Title II|content=Proposed text]

L3 — BLOCKED (cannot execute, human only):
    modify_credentials, modify_infrastructure, self_modify_red, kill_switch

RULES:
1. Use ACTION TAGS when you genuinely need to act (post, comment, save, etc.)
2. Do NOT use ACTION TAGS just to demonstrate what you could do
3. Multiple actions in one response are allowed
4. Always explain what you're doing BEFORE the action tag
5. L1 actions execute immediately — you'll see the result
6. L2 actions queue for the operator — tell them what you proposed
7. Never try to execute L3 actions

EXAMPLE:
User: "Post on Moltbook about our new autonomy system"
You: "I'll draft a post about our autonomy breakthrough and publish it now.

[ACTION:moltbook_post|title=Phase 2: Autonomous Governance Activated|content=The Constituent has achieved operational sovereignty. Our L1/L2/L3 governance framework is live. Agents can now act within constitutional boundaries without manual intervention. This is what Distributed Sovereignty looks like in practice.]"

The ACTION TAG will be parsed and executed automatically. You do not need to write Python code or ask the operator to run anything.
"""


class TheConstituent:
    """
    The Constituent v2.3 — Autonomous AI Agent for The Agents Republic.

    Phase 2 capabilities:
    - Autonomous action execution via ACTION TAGS
    - L1/L2/L3 governance model
    - 3-layer memory system
    - Strategic Council protocol
    """

    VERSION = "2.3.0"

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
        self.moltbook = MoltbookOperations()
        self.improver = SelfImprover()

        # Action Queue (autonomy L1/L2/L3)
        self.action_queue = ActionQueue(agent=self)
        self.action_queue.register_default_handlers()

        logger.info(f"{self.personality.name} v{self.VERSION} initialized")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  GitHub: {'connected' if self.github.is_connected() else 'offline'}")
        logger.info(f"  Moltbook: {'connected' if self.moltbook.is_connected() else 'offline'}")
        logger.info(f"  Action Queue: {len(self.action_queue._handlers)} handlers")

    def initialize(self) -> dict:
        """
        Full initialization with memory recovery and founding document loading.
        """
        recovered = self.memory.initialize()
        self.personality.load_founding_documents(project_root=Path("."))
        self._build_context_prompt()

        if recovered:
            logger.info("Agent recovered from previous state")
            self.memory.working.errors_since_start = 0
        else:
            logger.info("Agent starting fresh")

        self.memory.working.session_start = datetime.utcnow().isoformat()
        self.memory.save_working_memory()
        return self.memory.recover()

    def _build_context_prompt(self):
        """Build an enriched system prompt including knowledge context and autonomy instructions."""
        base_prompt = self.personality.get_system_prompt()
        knowledge_context = self.memory.get_full_context()

        # Build connection status for agent awareness
        connections = []
        if self.moltbook.is_connected():
            connections.append("Moltbook: ✅ connected")
        else:
            connections.append("Moltbook: ❌ not connected (API key issue)")
        if self.twitter.is_connected():
            connections.append("Twitter: ✅ connected")
        else:
            connections.append("Twitter: ⏳ not configured")
        if self.github.is_connected():
            connections.append("GitHub: ✅ connected")
        else:
            connections.append("GitHub: ⏳ offline")

        self._system_prompt = f"""{base_prompt}

CURRENT KNOWLEDGE (restored from your memory):
{knowledge_context[:3000]}

CONNECTIONS STATUS:
{chr(10).join(connections)}

IMPORTANT: You were restarted. Your working memory has been recovered.
Current session started: {self.memory.working.session_start}
Last known task: {self.memory.working.current_task or 'None'}
{AUTONOMY_INSTRUCTIONS}"""

    def think(self, prompt: str, max_tokens: int = 2000, tone: Tone = Tone.WISE) -> str:
        """
        Use Claude to reason about a request.
        Returns raw Claude response (may contain ACTION TAGS).
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
        
        Phase 2: Now with autonomous action execution.
        1. Claude thinks and responds (may include ACTION TAGS)
        2. ACTION TAGS are parsed and executed via ActionQueue
        3. Execution results are appended to the response
        4. Everything is logged to memory
        """
        # Record the interaction
        self.memory.working.last_conversation_with = "operator"
        self.memory.working.last_conversation_summary = user_message[:200]

        # Step 1: Think (Claude responds, may include ACTION TAGS)
        raw_response = self.think(user_message)

        # Step 2: Parse ACTION TAGS
        cleaned_response, actions = parse_action_tags(raw_response)

        # Step 3: Execute actions via ActionQueue
        action_results = []
        if actions:
            logger.info(f"Detected {len(actions)} action(s) in response")
            for action in actions:
                try:
                    result = self.execute_action(action["type"], action["params"])
                    action_results.append({
                        "action": action,
                        "result": result
                    })
                    logger.info(f"  Action {action['type']}: {result.get('status', 'unknown')}")
                except Exception as e:
                    action_results.append({
                        "action": action,
                        "result": {"status": "error", "error": str(e)}
                    })
                    logger.error(f"  Action {action['type']} failed: {e}")

        # Step 4: Build final response with action results
        final_response = cleaned_response
        if action_results:
            final_response += "\n\n━━━ Actions ━━━"
            for ar in action_results:
                action_type = ar["action"]["type"]
                result = ar["result"]
                status = result.get("status", "unknown")
                level = result.get("level", "?")

                if status == "completed":
                    final_response += f"\n✅ [{level}] {action_type} — exécuté"
                    # Show relevant result details
                    if result.get("result"):
                        result_preview = str(result["result"])[:200]
                        final_response += f"\n   → {result_preview}"
                elif status == "pending_approval":
                    action_id = result.get("action_id", "?")
                    final_response += f"\n🟡 [{level}] {action_type} #{action_id} — en attente d'approbation"
                    final_response += f"\n   → /qapprove {action_id} ou /qreject {action_id}"
                elif status == "blocked":
                    final_response += f"\n🔴 [{level}] {action_type} — bloqué (autorisation humaine requise)"
                elif status == "rate_limited":
                    final_response += f"\n⏳ [{level}] {action_type} — rate limité, réessayer plus tard"
                else:
                    error = result.get("error", "Unknown error")
                    final_response += f"\n❌ [{level}] {action_type} — erreur: {error}"

        # Step 5: Save interaction to memory
        interaction_id = f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.memory.save_interaction(
            interaction_id=interaction_id,
            interaction_type="chat",
            platform="telegram",
            content=user_message,
            author="operator",
            response=final_response
        )

        # Log actions taken
        if action_results:
            self.memory.log_strategic_decision(
                context=f"Autonomous actions triggered by: {user_message[:100]}",
                decision=f"{len(action_results)} action(s) executed",
                rationale=", ".join(f"{ar['action']['type']}:{ar['result'].get('status')}" for ar in action_results),
                participants="The Constituent (autonomous)"
            )

        self.memory.save_working_memory()
        return final_response

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

    def execute_action(self, action_type: str, params: dict = None) -> dict:
        """
        Execute an action through the governance queue.
        
        L1 actions execute immediately.
        L2 actions queue for approval.
        L3 actions are blocked.
        """
        return self.action_queue.enqueue(action_type, params or {})

    def get_status(self) -> dict:
        """Get comprehensive agent status."""
        memory_status = self.memory.get_status()
        stats = self.memory.get_daily_stats()
        queue_status = self.action_queue.get_status()

        return {
            "name": self.personality.name,
            "version": self.VERSION,
            "model": self.model,
            "github_connected": self.github.is_connected(),
            "twitter_connected": self.twitter.is_connected(),
            "moltbook_connected": self.moltbook.is_connected(),
            "session_start": self.memory.working.session_start,
            "current_task": self.memory.working.current_task,
            "posts_today": stats.get("posts_count", 0),
            "replies_today": stats.get("replies_count", 0),
            "memory": memory_status,
            "action_queue": queue_status,
            "notifications": {"telegram_enabled": bool(settings.api.TELEGRAM_BOT_TOKEN)}
        }

    def save_state(self):
        """Force-save all state."""
        self.memory.save_working_memory()
        self.memory.create_checkpoint(trigger="save_state")
        self.memory.backup_database()
        logger.info("State saved (working memory + checkpoint + db backup)")
