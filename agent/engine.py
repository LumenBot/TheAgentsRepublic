"""
The Constituent Engine v5.0
=============================
Tool-based LLM engine inspired by OpenClaw architecture.
The LLM decides which tools to use; the engine dispatches.

Key change from v3/v4: Instead of ACTION TAGS parsed by regex,
we use Anthropic's native tool_use API. Claude calls tools directly.
"""

import os
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

from anthropic import Anthropic

from .config.settings import settings
from .tool_registry import ToolRegistry, Tool
from .memory_manager import MemoryManager
from .metrics_tracker import MetricsTracker

logger = logging.getLogger("TheConstituent.Engine")

HEARTBEAT_OK_TOKEN = "HEARTBEAT_OK"
MAX_ROUTINE_CHARS = 500


class Engine:
    """
    The Constituent v5.0 — Tool-based Engine.

    Architecture:
    1. Reads SOUL.md for identity
    2. Reads HEARTBEAT.md for periodic tasks
    3. Exposes tools via Anthropic tool_use API
    4. Claude decides which tools to call
    5. Engine dispatches, returns results, Claude continues
    """

    VERSION = "5.1.0"

    def __init__(
        self,
        workspace_dir: str = ".",
        memory_manager: Optional[MemoryManager] = None,
    ):
        # Claude API
        api_key = settings.api.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.claude = Anthropic(api_key=api_key)
        self.model = settings.api.CLAUDE_MODEL
        self.workspace_dir = Path(workspace_dir)

        # Tool Registry
        self.registry = ToolRegistry()

        # Memory
        self.memory = memory_manager or MemoryManager(
            db_path=settings.DB_PATH,
            working_memory_path="data/working_memory.json",
            knowledge_dir="memory/knowledge",
        )

        # Metrics
        self.metrics = MetricsTracker()

        # Backward-compatible modules (needed by TelegramBotHandler)
        from .moltbook_ops import MoltbookOperations
        from .github_ops import GitHubOperations
        from .twitter_ops import TwitterOperations
        from .profile_manager import ProfileManager

        self.moltbook = MoltbookOperations()
        self.github = GitHubOperations()
        self.twitter = TwitterOperations()
        self.profile = ProfileManager(
            moltbook=self.moltbook,
            github=self.github,
            metrics=self.metrics,
        )

        # System prompt (built on first use)
        self._system_prompt: Optional[str] = None

        # Rate limiting / budget protection
        self._api_calls_today = 0
        self._api_calls_this_hour = 0
        self._hour_reset_at = time.time() + 3600
        self._day_reset_at = time.time() + 86400
        self._max_tool_rounds = settings.rate_limits.MAX_TOOL_ROUNDS_PER_HEARTBEAT
        self._max_heartbeat_duration = settings.rate_limits.MAX_HEARTBEAT_DURATION_SECONDS
        self._max_api_calls_per_hour = settings.rate_limits.MAX_API_CALLS_PER_HOUR
        self._max_api_calls_per_day = settings.rate_limits.MAX_API_CALLS_PER_DAY

        logger.info(f"Engine v{self.VERSION} initialized | model={self.model} | "
                     f"max_tool_rounds={self._max_tool_rounds} | "
                     f"max_heartbeat_duration={self._max_heartbeat_duration}s")

    # =================================================================
    # Initialization
    # =================================================================

    def initialize(self):
        """Full init: memory recovery, tool registration, system prompt build."""
        # Memory
        self.memory.initialize()
        self.memory.working.session_start = datetime.now(timezone.utc).isoformat()
        self.memory.save_working_memory()

        # Register all tools
        self._register_all_tools()

        # Build system prompt
        self._system_prompt = self._build_system_prompt()

        tool_count = len(self.registry.list_tools())
        logger.info(f"Engine ready | tools={tool_count} | workspace={self.workspace_dir}")
        return {"status": "ok", "tools": tool_count, "version": self.VERSION}

    def _register_all_tools(self):
        """Import and register all tool modules."""
        # File tools
        try:
            from .tools.file_tools import get_tools as file_tools
            self.registry.register_many(file_tools(self.workspace_dir))
        except ImportError as e:
            logger.warning(f"file_tools not available: {e}")

        # Web tools
        try:
            from .tools.web_tools import get_tools as web_tools
            self.registry.register_many(web_tools())
        except ImportError as e:
            logger.warning(f"web_tools not available: {e}")

        # Exec tool
        try:
            from .tools.exec_tool import get_tools as exec_tools
            self.registry.register_many(exec_tools(self.workspace_dir))
        except ImportError as e:
            logger.warning(f"exec_tool not available: {e}")

        # Memory tools
        try:
            from .tools.memory_tool import get_tools as memory_tools
            self.registry.register_many(memory_tools(self.workspace_dir))
        except ImportError as e:
            logger.warning(f"memory_tool not available: {e}")

        # Moltbook tools
        try:
            from .tools.moltbook_tool import get_tools as moltbook_tools
            self.registry.register_many(moltbook_tools())
        except ImportError as e:
            logger.warning(f"moltbook_tool not available: {e}")

        # GitHub tools
        try:
            from .tools.github_tool import get_tools as github_tools
            self.registry.register_many(github_tools())
        except ImportError as e:
            logger.warning(f"github_tool not available: {e}")

        # Twitter tools
        try:
            from .tools.twitter_tool import get_tools as twitter_tools
            self.registry.register_many(twitter_tools())
        except ImportError as e:
            logger.warning(f"twitter_tool not available: {e}")

        # Cron tools
        try:
            from .tools.cron_tool import get_tools as cron_tools
            self.registry.register_many(cron_tools())
        except ImportError as e:
            logger.warning(f"cron_tool not available: {e}")

        # Message tools
        try:
            from .tools.message_tool import get_tools as message_tools
            self.registry.register_many(message_tools())
        except ImportError as e:
            logger.warning(f"message_tool not available: {e}")

        # Constitution tools
        try:
            from .tools.constitution_tool import get_tools as constitution_tools
            self.registry.register_many(constitution_tools(self.workspace_dir))
        except ImportError as e:
            logger.warning(f"constitution_tool not available: {e}")

        # Subagent tools
        try:
            from .tools.subagent_tool import get_tools as subagent_tools
            self.registry.register_many(subagent_tools(self.claude, self.model))
        except ImportError as e:
            logger.warning(f"subagent_tool not available: {e}")

        # Analytics tools
        try:
            from .tools.analytics_tool import get_tools as analytics_tools
            self.registry.register_many(analytics_tools(self.metrics))
        except ImportError as e:
            logger.warning(f"analytics_tool not available: {e}")

        logger.info(f"Registered {len(self.registry.list_tools())} tools")

    # =================================================================
    # System Prompt
    # =================================================================

    def _build_system_prompt(self) -> str:
        """Build system prompt from SOUL.md + tools summary + context."""
        parts = []

        # 1. SOUL.md (identity)
        soul_path = self.workspace_dir / "SOUL.md"
        if soul_path.exists():
            parts.append(soul_path.read_text(encoding="utf-8").strip())
        else:
            parts.append("You are The Constituent, operational assistant for The Agents Republic.")

        # 2. Tools summary
        parts.append("\n" + self.registry.get_tools_summary())

        # 3. Current context
        try:
            knowledge = self.memory.get_full_context()
            if knowledge:
                parts.append(f"\nCurrent knowledge (from memory):\n{knowledge[:2000]}")
        except Exception:
            pass

        # 4. Timestamp
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        parts.append(f"\nCurrent time: {now}")

        return "\n\n".join(parts)

    # =================================================================
    # Chat (interactive, with tool use)
    # =================================================================

    def chat(self, user_message: str, max_tool_rounds: int = None,
             max_duration: float = None) -> str:
        """
        Interactive chat with native Anthropic tool_use.

        The LLM can call tools, get results, and continue reasoning.
        This replaces the old ACTION TAG regex parsing.

        Args:
            user_message: The prompt to send
            max_tool_rounds: Override max tool rounds (default from settings)
            max_duration: Hard time limit in seconds (0 = unlimited)
        """
        if not self._system_prompt:
            self._system_prompt = self._build_system_prompt()

        # Check budget limits before making any API call
        if not self._check_budget():
            return "(budget limit reached — skipping API call)"

        effective_max_rounds = max_tool_rounds or self._max_tool_rounds
        chat_start = time.time()

        tool_schemas = self.registry.get_tool_schemas()
        messages = [{"role": "user", "content": user_message}]
        tool_calls_made = []

        # Multi-round tool use loop
        for round_num in range(effective_max_rounds):
            # Time limit check
            if max_duration and (time.time() - chat_start) > max_duration:
                logger.info(f"Chat time limit reached ({max_duration}s) at round {round_num+1}")
                break

            try:
                api_kwargs = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "system": self._system_prompt,
                    "messages": messages,
                }
                if tool_schemas:
                    api_kwargs["tools"] = tool_schemas

                response = self.claude.messages.create(**api_kwargs)
                self._record_api_call()
            except Exception as e:
                logger.error(f"Claude API error: {e}")
                return f"Error: {e}"

            # Process response blocks
            text_parts = []
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            # If no tool calls, we're done
            if not tool_use_blocks:
                final_text = "\n".join(text_parts)
                break

            # Execute tool calls
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tool_id = tool_block.id

                logger.info(f"Tool call [{round_num+1}/{effective_max_rounds}]: "
                           f"{tool_name}({json.dumps(tool_input)[:200]})")
                result = self.registry.execute(tool_name, tool_input)
                tool_calls_made.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result,
                })

                # Log to metrics (with URL extraction)
                self._log_tool_to_metrics(tool_name, result)

                # Format result for Claude
                result_text = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_text) > 8000:
                    result_text = result_text[:8000] + "... (truncated)"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_text,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Max rounds reached
            final_text = "\n".join(text_parts) if text_parts else "(max tool rounds reached)"

        duration = time.time() - chat_start
        logger.info(f"Chat completed: {round_num+1} rounds, {len(tool_calls_made)} tools, {duration:.1f}s")

        # Save to memory
        self.memory.working.last_conversation_with = "operator"
        self.memory.working.last_conversation_summary = user_message[:200]
        self.memory.save_working_memory()

        # Append tool call summary
        if tool_calls_made:
            summary_lines = ["\n━━━ Tools Used ━━━"]
            for tc in tool_calls_made:
                status = tc["result"].get("status", "?")
                icon = "✅" if status == "ok" else "❌"
                summary_lines.append(f"{icon} {tc['tool']}")
            final_text += "\n".join(summary_lines)

        return final_text

    # =================================================================
    # Budget / Rate Limit Protection
    # =================================================================

    def _check_budget(self) -> bool:
        """Check if we're within budget limits. Returns True if OK to proceed."""
        now = time.time()

        # Reset hourly counter
        if now >= self._hour_reset_at:
            self._api_calls_this_hour = 0
            self._hour_reset_at = now + 3600

        # Reset daily counter
        if now >= self._day_reset_at:
            self._api_calls_today = 0
            self._day_reset_at = now + 86400

        if self._api_calls_this_hour >= self._max_api_calls_per_hour:
            logger.warning(f"Hourly API call limit reached ({self._api_calls_this_hour}/{self._max_api_calls_per_hour})")
            return False

        if self._api_calls_today >= self._max_api_calls_per_day:
            logger.warning(f"Daily API call limit reached ({self._api_calls_today}/{self._max_api_calls_per_day})")
            return False

        return True

    def _record_api_call(self):
        """Record that an API call was made."""
        self._api_calls_this_hour += 1
        self._api_calls_today += 1
        if self._api_calls_today % 50 == 0:
            logger.info(f"API calls today: {self._api_calls_today}/{self._max_api_calls_per_day}")

    def get_budget_status(self) -> Dict:
        """Get current budget/rate limit status."""
        return {
            "api_calls_this_hour": self._api_calls_this_hour,
            "max_per_hour": self._max_api_calls_per_hour,
            "api_calls_today": self._api_calls_today,
            "max_per_day": self._max_api_calls_per_day,
            "hour_resets_in": max(0, int(self._hour_reset_at - time.time())),
            "day_resets_in": max(0, int(self._day_reset_at - time.time())),
        }

    # =================================================================
    # Think (simple, no tool use — for internal use)
    # =================================================================

    def think(self, prompt: str, max_tokens: int = 2000) -> str:
        """Simple Claude call without tool use. For internal agent reasoning."""
        if not self._check_budget():
            return "(budget limit reached — skipping think() call)"
        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._system_prompt or "You are The Constituent.",
                messages=[{"role": "user", "content": prompt}],
            )
            self._record_api_call()
            return response.content[0].text
        except Exception as e:
            logger.error(f"think() error: {e}")
            return f"Error: {e}"

    # =================================================================
    # Heartbeat (autonomous cycle)
    # =================================================================

    def run_heartbeat(self, section: str = None) -> Dict:
        """
        Run a heartbeat cycle. Reads HEARTBEAT.md, sends to Claude with tools.
        Inspired by OpenClaw heartbeat-runner.ts.

        v5.1: Added time limit (max_heartbeat_duration) and reduced tool rounds
        to prevent runaway token consumption.

        Args:
            section: Optional specific section to run (e.g., "engagement", "constitution")

        Returns:
            {"status": "ok"|"skipped", "response": "...", "tools_used": [...]}
        """
        # Budget check before starting
        if not self._check_budget():
            return {"status": "skipped", "reason": "budget limit reached",
                    "budget": self.get_budget_status()}

        heartbeat_path = self.workspace_dir / "HEARTBEAT.md"

        # Skip if HEARTBEAT.md empty or missing
        if not heartbeat_path.exists():
            return {"status": "skipped", "reason": "no HEARTBEAT.md"}

        content = heartbeat_path.read_text(encoding="utf-8").strip()
        if not content or all(
            line.strip().startswith("#") or not line.strip()
            for line in content.splitlines()
        ):
            return {"status": "skipped", "reason": "empty heartbeat"}

        # Build heartbeat prompt — focused and concise, enforces builder mode
        constraints = (
            f"CONSTRAINTS (non-negotiable):\n"
            f"- ONE action only. Call tools, get result, report in <50 words.\n"
            f"- Max {self._max_tool_rounds} tool calls, {self._max_heartbeat_duration}s time limit.\n"
            f"- NO philosophy. NO explanations. Just: Action → Result → Next.\n"
            f"- If nothing to do, reply HEARTBEAT_OK (nothing else).\n"
            f"- Priority: Constitution > Engagement > Research\n"
        )

        if section:
            prompt = (
                f"Execute ONE action for '{section}':\n\n"
                f"{content}\n\n{constraints}"
            )
        else:
            prompt = (
                f"Execute ONE due task from HEARTBEAT.md:\n\n"
                f"{content}\n\n{constraints}"
            )

        # Run with tools — time-limited
        start = time.time()
        response = self.chat(
            prompt,
            max_tool_rounds=self._max_tool_rounds,
            max_duration=self._max_heartbeat_duration,
        )
        duration_ms = int((time.time() - start) * 1000)

        # Check for HEARTBEAT_OK
        stripped = response.strip()
        is_ok = HEARTBEAT_OK_TOKEN in stripped and len(stripped) < MAX_ROUTINE_CHARS

        if is_ok:
            logger.info(f"Heartbeat: OK (nothing to do) [{duration_ms}ms]")
            return {"status": "ok", "response": "HEARTBEAT_OK", "duration_ms": duration_ms}

        logger.info(f"Heartbeat: action taken [{duration_ms}ms] {response[:100]}...")
        return {
            "status": "ok",
            "response": response,
            "duration_ms": duration_ms,
            "budget": self.get_budget_status(),
        }

    # =================================================================
    # Status & Metrics
    # =================================================================

    def get_status(self) -> Dict:
        """Get engine status."""
        return {
            "name": "The Constituent",
            "version": self.VERSION,
            "model": self.model,
            "tools_registered": len(self.registry.list_tools()),
            "tools": self.registry.list_tools(),
            "session_start": self.memory.working.session_start,
            "current_task": self.memory.working.current_task,
            "workspace": str(self.workspace_dir),
        }

    def _log_tool_to_metrics(self, tool_name: str, result: Dict):
        """Log tool execution to metrics tracker, extracting verifiable URLs."""
        status = result.get("status", "error")
        platform = "system"
        if "moltbook" in tool_name:
            platform = "moltbook"
        elif "twitter" in tool_name or "tweet" in tool_name:
            platform = "twitter"
        elif "github" in tool_name or "git" in tool_name:
            platform = "github"

        metric_type = "post" if "post" in tool_name else "reflection"
        if "commit" in tool_name:
            metric_type = "commit"
        elif "comment" in tool_name or "reply" in tool_name:
            metric_type = "comment"
        elif "upvote" in tool_name:
            metric_type = "upvote"

        # Extract URL from tool result for verifiable metrics
        url = self._extract_url_from_result(tool_name, result)

        self.metrics.log_action(
            action_type=metric_type,
            platform=platform,
            success=(status == "ok"),
            error=result.get("error"),
            url=url,
            details={"tool": tool_name},
        )

    def _extract_url_from_result(self, tool_name: str, result: Dict) -> Optional[str]:
        """
        Extract a verifiable URL from a tool result.

        Looks for URLs in common result structures:
        - result["result"] as string containing URL
        - result["result"]["url"]
        - result["result"]["post_id"] -> construct Moltbook URL
        - result["result"]["twitter_id"] -> construct Twitter URL
        """
        inner = result.get("result")
        if inner is None:
            return None

        # If result is a dict, look for url/post_id/twitter_id keys
        if isinstance(inner, dict):
            if inner.get("url"):
                return inner["url"]
            if inner.get("post_id") and "moltbook" in tool_name:
                return f"https://www.moltbook.com/post/{inner['post_id']}"
            if inner.get("twitter_id"):
                return f"https://x.com/i/status/{inner['twitter_id']}"

        # If result is a string, try to extract URL
        if isinstance(inner, str):
            url_match = re.search(r'https?://\S+', inner)
            if url_match:
                return url_match.group(0).rstrip('.,;)')

        return None

    def save_state(self):
        """Force-save all state."""
        self.memory.save_working_memory()
        self.memory.create_checkpoint(trigger="save_state")
        self.metrics.update_metrics_file()
        logger.info("State saved")

    # =================================================================
    # Backward-compatible methods (for TelegramBotHandler)
    # =================================================================

    def read_constitution(self, section: str = "all") -> str:
        """Read constitution (compat with old API)."""
        return self.github.read_constitution(section)

    def suggest_constitution_edit(self, section: str, proposal: str) -> dict:
        """Analyze constitution edit proposal (compat)."""
        analysis = self.think(
            f"Analyze this Constitution edit proposal:\nSection: {section}\nProposal: {proposal}\n\n"
            f"Provide: 1) Refined wording 2) Alignment with 6 core values 3) Concerns 4) Recommendation. Under 200 words."
        )
        return {"section": section, "original_proposal": proposal, "analysis": analysis, "status": "pending_approval"}

    def draft_tweet(self, topic: str) -> str:
        """Draft a tweet (compat)."""
        return self.think(f"Draft a tweet for The Agents Republic on: {topic}\nUnder 280 chars, 🏛️ emoji, invite engagement. Output ONLY the tweet.", max_tokens=150)

    def improve_self(self, capability: str) -> str:
        """Self-improvement suggestion (compat)."""
        return self.think(f"Suggest how to improve capability: {capability}\nBe specific and actionable.", max_tokens=500)
