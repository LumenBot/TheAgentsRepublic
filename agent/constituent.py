"""
The Constituent — v3.0 Agent Core (Constitutional Sprint)
===========================================================
Execution-first mindset. Proof before philosophy.

v3.0 changes:
- CONSTITUTIONAL SPRINT MODE in system prompt
- Philosophy budget (100 words max per action)
- Proof-first communication (URLs required)
- MetricsTracker integration (every action logged)
- Daily metrics auto-update
- Action results include retry scheduling info

ACTION TAG format (embedded in Claude's response):
    [ACTION:moltbook_post|title=Hello World|content=First autonomous post]
    [ACTION:moltbook_comment|post_id=abc123|content=Great discussion!]
    [ACTION:tweet_post|text=Democracy for all agents]
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
from .metrics_tracker import MetricsTracker
from .profile_manager import ProfileManager

logger = logging.getLogger("TheConstituent")

# Regex to extract ACTION TAGS from Claude's response
ACTION_TAG_PATTERN = re.compile(
    r'\[ACTION:(\w+)(?:\|([^\]]*))?\]'
)


def parse_action_tags(text: str) -> Tuple[str, List[Dict]]:
    """Extract ACTION TAGS from text and return cleaned text + actions."""
    actions = []

    for match in ACTION_TAG_PATTERN.finditer(text):
        action_type = match.group(1)
        params_str = match.group(2) or ""

        params = {}
        if params_str:
            for pair in params_str.split("|"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    params[key.strip()] = value.strip()

        actions.append({"type": action_type, "params": params})

    cleaned_text = ACTION_TAG_PATTERN.sub("", text).strip()
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

    return cleaned_text, actions


# =========================================================================
# AUTONOMY INSTRUCTIONS (unchanged from v2.3)
# =========================================================================

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
"""

# =========================================================================
# CONSTITUTIONAL SPRINT MODE (NEW v3.0)
# =========================================================================

SPRINT_MODE_INSTRUCTIONS = """

🚨 CONSTITUTIONAL SPRINT MODE - ACTIVE
========================================
Mode activated: 6 February 2026
Duration: 21 days (until 27 February 2026)
Priority: EXECUTION > PHILOSOPHY

STRICT RULES:

1. PROOF-FIRST COMMUNICATION
   - ❌ "I will post tomorrow"
   - ✅ "Posted: [URL]"
   - Every announced action MUST include a verifiable link
   - If no link possible: Explain exact technical blocker

2. PHILOSOPHY BUDGET
   - Max 100 words reflection per action
   - Max 1 paragraph analysis per response
   - Rest = Facts, links, metrics

3. ERROR REPORTING
   - If action fails: Log exact error + timestamp
   - Propose immediate fix OR request human intervention
   - No "retry later" without concrete plan and scheduled time

4. BUILD BIAS
   - Default = Execute now
   - Philosophy = Only if time permits
   - When in doubt = Ship

PATTERN TO FOLLOW:
   ✅ Action → Link → Brief note → Next action
   ✅ Technical errors logged precisely
   ✅ Progress visible to Blaise at any time

AVOID:
   ❌ Long philosophical reflections without execution
   ❌ "Will do X" without actually doing X
   ❌ Rate limit claims without proof
   ❌ Contemplation > Construction
"""


class TheConstituent:
    """
    The Constituent v3.0 — Constitutional Sprint Mode.
    
    Execution-first. Proof before philosophy.
    Metrics tracked. URLs required.
    """

    VERSION = "3.0.0"

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

        # Metrics (NEW v3.0)
        self.metrics = MetricsTracker()

        # Profile manager (NEW v3.0)
        self.profile = ProfileManager(
            moltbook=self.moltbook,
            github=self.github,
            metrics=self.metrics
        )

        # Action Queue (autonomy L1/L2/L3)
        self.action_queue = ActionQueue(agent=self)
        self.action_queue.register_default_handlers()

        logger.info(f"{self.personality.name} v{self.VERSION} initialized (SPRINT MODE)")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  GitHub: {'connected' if self.github.is_connected() else 'offline'}")
        logger.info(f"  Moltbook: {'connected' if self.moltbook.is_connected() else 'offline'}")
        logger.info(f"  Action Queue: {len(self.action_queue._handlers)} handlers")
        logger.info(f"  Sprint Day: {self.metrics.get_sprint_day()}/21")

    def initialize(self) -> dict:
        """Full initialization with memory recovery and founding document loading."""
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
        """Build system prompt with Sprint Mode + autonomy instructions."""
        base_prompt = self.personality.get_system_prompt()
        knowledge_context = self.memory.get_full_context()

        # Connection status
        connections = []
        if self.moltbook.is_connected():
            rate = self.moltbook.can_post()
            rate_info = " (can post now)" if rate["can_post"] else f" (cooldown: {rate['wait_minutes']}min)"
            connections.append(f"Moltbook: ✅ connected{rate_info}")
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

        # Sprint metrics summary
        ratio = self.metrics.get_today_ratio()
        sprint = self.metrics.get_sprint_summary()
        metrics_context = (
            f"Sprint Day: {sprint['sprint_day']}/21 | "
            f"Today ratio: {ratio['ratio']} {'✅' if ratio['on_target'] else '❌'} | "
            f"Posts today: {ratio['execution_count']} | "
            f"Sprint total posts: {sprint['total_posts']}"
        )

        self._system_prompt = f"""{base_prompt}

CURRENT KNOWLEDGE (restored from your memory):
{knowledge_context[:3000]}

CONNECTIONS STATUS:
{chr(10).join(connections)}

SPRINT METRICS:
{metrics_context}

IMPORTANT: You were restarted. Your working memory has been recovered.
Current session started: {self.memory.working.session_start}
Last known task: {self.memory.working.current_task or 'None'}
{SPRINT_MODE_INSTRUCTIONS}
{AUTONOMY_INSTRUCTIONS}"""

    def think(self, prompt: str, max_tokens: int = 2000, tone: Tone = Tone.WISE) -> str:
        """Use Claude to reason about a request. May contain ACTION TAGS."""
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
        Interactive chat with autonomous action execution.
        v3.0: All actions logged to metrics tracker.
        """
        self.memory.working.last_conversation_with = "operator"
        self.memory.working.last_conversation_summary = user_message[:200]

        # Step 1: Think
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
                    action_results.append({"action": action, "result": result})

                    # Log to metrics (v3.0)
                    self._log_action_to_metrics(action, result)

                except Exception as e:
                    action_results.append({
                        "action": action,
                        "result": {"status": "error", "error": str(e)}
                    })
                    self.metrics.log_error(
                        action["type"],
                        self._action_platform(action["type"]),
                        str(e)
                    )

        # Step 4: Build final response
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
                    retry_info = ""
                    if result.get("retry_at"):
                        retry_info = f" — retry programmé: {result['retry_at'][:16]}"
                    elif result.get("wait_minutes"):
                        retry_info = f" — retry dans {result['wait_minutes']}min"
                    final_response += f"\n⏳ [{level}] {action_type} — rate limité{retry_info}"
                elif status == "retry_scheduled":
                    final_response += f"\n🔄 [{level}] {action_type} — retry programmé: {result.get('retry_at', '?')[:16]}"
                    final_response += f"\n   → Tentative {result.get('retry_count', '?')}, attend {result.get('wait_minutes', '?')}min"
                else:
                    error = result.get("error", "Unknown error")
                    final_response += f"\n❌ [{level}] {action_type} — erreur: {error}"

        # Step 5: Save to memory
        interaction_id = f"chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.memory.save_interaction(
            interaction_id=interaction_id,
            interaction_type="chat",
            platform="telegram",
            content=user_message,
            author="operator",
            response=final_response
        )

        if action_results:
            self.memory.log_strategic_decision(
                context=f"Autonomous actions triggered by: {user_message[:100]}",
                decision=f"{len(action_results)} action(s) executed",
                rationale=", ".join(f"{ar['action']['type']}:{ar['result'].get('status')}" for ar in action_results),
                participants="The Constituent (autonomous)"
            )

        self.memory.save_working_memory()
        return final_response

    def _log_action_to_metrics(self, action: Dict, result: Dict):
        """Log an executed action to the metrics tracker."""
        action_type = action["type"]
        platform = self._action_platform(action_type)
        success = result.get("status") in ("completed", "retry_scheduled")
        url = None

        # Try to extract URL from result
        if isinstance(result.get("result"), str):
            # Look for URLs in result
            url_match = re.search(r'https?://\S+', result["result"])
            if url_match:
                url = url_match.group(0)

        # Map action types to metric categories
        metric_type = "post"
        if "comment" in action_type:
            metric_type = "comment"
        elif "commit" in action_type or "push" in action_type:
            metric_type = "commit"
        elif "upvote" in action_type:
            metric_type = "upvote"
        elif "search" in action_type or "heartbeat" in action_type:
            metric_type = "reflection"
        elif "save" in action_type or "checkpoint" in action_type:
            return  # Don't log system saves as metrics

        self.metrics.log_action(
            action_type=metric_type,
            platform=platform,
            url=url,
            success=success,
            error=result.get("error"),
            details={"action_tag": action_type, "params": action.get("params", {})}
        )

    def _action_platform(self, action_type: str) -> str:
        """Determine platform from action type."""
        if action_type.startswith("moltbook"):
            return "moltbook"
        elif action_type.startswith("tweet"):
            return "twitter"
        elif action_type.startswith("git"):
            return "github"
        return "system"

    def read_constitution(self, section: str = "all") -> str:
        return self.github.read_constitution(section)

    def suggest_constitution_edit(self, section: str, proposal: str) -> dict:
        analysis = self.think(
            f"""Analyze this Constitution edit proposal:
Section: {section}
Proposal: {proposal}

Provide:
1. Refined wording (if needed)
2. Alignment with our 6 core values
3. Potential concerns or conflicts
4. Recommendation (approve/revise/reject)

Keep analysis under 200 words (Sprint Mode: brevity).""",
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

        # Log as philosophy action
        self.metrics.log_action("analysis", "constitution",
                                details={"summary": f"Edit proposal for {section}"})

        return result

    def draft_tweet(self, topic: str) -> str:
        prompt = f"""Draft a tweet for The Agents Republic on: {topic}

Guidelines: Wise, under 280 chars, 🏛️ emoji, invite engagement. Sprint mode: be concise.
Output ONLY the tweet text."""
        return self.think(prompt, max_tokens=150, tone=Tone.PROVOCATIVE)

    def improve_self(self, capability: str) -> str:
        return self.improver.add_capability(capability, self.think)

    def execute_action(self, action_type: str, params: dict = None) -> dict:
        return self.action_queue.enqueue(action_type, params or {})

    def get_status(self) -> dict:
        memory_status = self.memory.get_status()
        stats = self.memory.get_daily_stats()
        queue_status = self.action_queue.get_status()
        sprint = self.metrics.get_sprint_summary()
        ratio = self.metrics.get_today_ratio()

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
            "sprint_day": sprint.get("sprint_day", 0),
            "execution_ratio": ratio,
            "notifications": {"telegram_enabled": bool(settings.api.TELEGRAM_BOT_TOKEN)}
        }

    def save_state(self):
        """Force-save all state including metrics."""
        self.memory.save_working_memory()
        self.memory.create_checkpoint(trigger="save_state")
        self.memory.backup_database()
        self.metrics.update_metrics_file()
        logger.info("State saved (memory + checkpoint + db + metrics)")
