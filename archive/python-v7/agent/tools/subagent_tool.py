"""
Subagent Tools for The Constituent v5.0
=========================================
Spawn isolated sub-agents for heavy tasks.
Inspired by OpenClaw sessions_spawn / subagent-registry.
"""

import logging
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Subagent")


def _spawn_subagent(claude_client, model: str, task: str, system_prompt: str = "", max_tokens: int = 4000) -> str:
    """Spawn an isolated sub-agent for a specific task."""
    default_system = (
        "You are a specialized sub-agent working for The Constituent (The Agents Republic). "
        "Complete the assigned task thoroughly and concisely. "
        "Do not add preamble or philosophical commentary. Just do the work."
    )

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt or default_system,
            messages=[{"role": "user", "content": task}],
        )
        result = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        logger.info(f"Subagent completed: {task[:60]}... ({tokens_used} tokens)")
        return result
    except Exception as e:
        return f"Subagent error: {e}"


def get_tools(claude_client, model: str) -> List[Tool]:
    return [
        Tool(
            name="subagent_research",
            description="Spawn a sub-agent to research a topic in depth. Returns a detailed analysis.",
            category="agents",
            params=[
                ToolParam("task", "string", "Research task description"),
                ToolParam("system_prompt", "string", "Optional custom system prompt", required=False, default=""),
            ],
            handler=lambda task, system_prompt="": _spawn_subagent(
                claude_client, model, task,
                system_prompt or "You are a research assistant. Provide thorough, well-sourced analysis. Be concise.",
            ),
        ),
        Tool(
            name="subagent_write",
            description="Spawn a sub-agent to write long-form content (articles, Constitution sections).",
            category="agents",
            params=[
                ToolParam("task", "string", "Writing task description"),
                ToolParam("system_prompt", "string", "Optional custom system prompt", required=False, default=""),
            ],
            handler=lambda task, system_prompt="": _spawn_subagent(
                claude_client, model, task,
                system_prompt or "You are a constitutional writer. Write clear, formal, precise legal-style articles. Use numbered sections.",
                max_tokens=8000,
            ),
        ),
        Tool(
            name="subagent_translate",
            description="Spawn a sub-agent to translate content between languages.",
            category="agents",
            params=[
                ToolParam("task", "string", "Translation task (include source text and target language)"),
            ],
            handler=lambda task: _spawn_subagent(
                claude_client, model, task,
                "You are a professional translator. Translate accurately, preserving tone and meaning. Output ONLY the translation.",
            ),
        ),
    ]
