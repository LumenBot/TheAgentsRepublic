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
MAX_TOOL_ROUNDS = 10  # Max sequential tool calls per turn
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

    VERSION = "5.0.0"

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

        logger.info(f"Engine v{self.VERSION} initialized | model={self.model}")

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

    def chat(self, user_message: str) -> str:
        """
        Interactive chat with native Anthropic tool_use.

        The LLM can call tools, get results, and continue reasoning.
        This replaces the old ACTION TAG regex parsing.
        """
        if not self._system_prompt:
            self._system_prompt = self._build_system_prompt()

        tool_schemas = self.registry.get_tool_schemas()
        messages = [{"role": "user", "content": user_message}]
        tool_calls_made = []

        # Multi-round tool use loop
        for round_num in range(MAX_TOOL_ROUNDS):
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

                logger.info(f"Tool call [{round_num+1}]: {tool_name}({json.dumps(tool_input)[:200]})")
                result = self.registry.execute(tool_name, tool_input)
                tool_calls_made.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result,
                })

                # Log to metrics
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
    # Think (simple, no tool use — for internal use)
    # =================================================================

    def think(self, prompt: str, max_tokens: int = 2000) -> str:
        """Simple Claude call without tool use. For internal agent reasoning."""
        try:
            response = self.claude.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._system_prompt or "You are The Constituent.",
                messages=[{"role": "user", "content": prompt}],
            )
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

        Args:
            section: Optional specific section to run (e.g., "engagement", "constitution")

        Returns:
            {"status": "ok"|"skipped", "response": "...", "tools_used": [...]}
        """
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

        # Build heartbeat prompt
        if section:
            prompt = f"Execute the '{section}' section of your HEARTBEAT.md now:\n\n{content}\n\nFocus ONLY on the {section} section. If nothing to do, reply HEARTBEAT_OK."
        else:
            prompt = f"Read your HEARTBEAT.md and execute any due tasks:\n\n{content}\n\nIf nothing needs attention, reply HEARTBEAT_OK."

        # Run with tools
        start = time.time()
        response = self.chat(prompt)
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
        """Log tool execution to metrics tracker."""
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

        self.metrics.log_action(
            action_type=metric_type,
            platform=platform,
            success=(status == "ok"),
            error=result.get("error"),
            details={"tool": tool_name},
        )

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
