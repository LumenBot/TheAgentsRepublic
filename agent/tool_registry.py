"""
Tool Registry for The Constituent v5.0
========================================
Central registration, discovery, and dispatch for all agent tools.
Inspired by OpenClaw's tool system — tools are described in JSON schema,
the LLM picks which to call, and the registry executes them.
"""

import json
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("TheConstituent.ToolRegistry")


@dataclass
class ToolParam:
    """A single parameter for a tool."""
    name: str
    type: str  # "string", "integer", "boolean"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """A registered tool that the LLM can call."""
    name: str
    description: str
    params: List[ToolParam] = field(default_factory=list)
    handler: Optional[Callable] = None
    governance_level: str = "L1"  # L1=autonomous, L2=approval, L3=blocked
    category: str = "general"

    def to_schema(self) -> Dict:
        """Convert to Anthropic tool_use JSON schema."""
        properties = {}
        required = []
        for p in self.params:
            properties[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.default is not None:
                properties[p.name]["default"] = p.default
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": f"[{self.governance_level}] {self.description}",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }


class ToolRegistry:
    """
    Central registry for all agent tools.

    Usage:
        registry = ToolRegistry()
        registry.register(Tool(name="web_search", ...))
        schemas = registry.get_tool_schemas()
        result = registry.execute("web_search", {"query": "AI agents"})
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self._tools[tool.name] = tool
        cat = tool.category
        if cat not in self._categories:
            self._categories[cat] = []
        if tool.name not in self._categories[cat]:
            self._categories[cat].append(tool.name)
        logger.debug(f"Registered tool: {tool.name} [{tool.governance_level}]")

    def register_many(self, tools: List[Tool]):
        """Register multiple tools at once."""
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_by_category(self, category: str) -> List[str]:
        """List tools in a category."""
        return self._categories.get(category, [])

    def get_tool_schemas(self, categories: List[str] = None) -> List[Dict]:
        """Get Anthropic-compatible tool schemas for all (or filtered) tools."""
        schemas = []
        for name, tool in self._tools.items():
            if categories and tool.category not in categories:
                continue
            if tool.handler is None:
                continue  # Skip tools without handlers
            schemas.append(tool.to_schema())
        return schemas

    def get_tools_summary(self) -> str:
        """Get a text summary of all tools for the system prompt."""
        lines = ["Available tools:"]
        by_cat = {}
        for name, tool in self._tools.items():
            cat = tool.category
            if cat not in by_cat:
                by_cat[cat] = []
            params_str = ", ".join(
                f"{p.name}: {p.type}" + ("?" if not p.required else "")
                for p in tool.params
            )
            by_cat[cat].append(f"  - {name}({params_str}): {tool.description}")

        for cat, tool_lines in sorted(by_cat.items()):
            lines.append(f"\n[{cat.upper()}]")
            lines.extend(sorted(tool_lines))

        return "\n".join(lines)

    def execute(self, tool_name: str, params: Dict) -> Dict:
        """
        Execute a tool by name with given parameters.

        Returns:
            {"status": "ok", "result": ...} or
            {"status": "error", "error": "..."} or
            {"status": "blocked", "reason": "..."}
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

        if tool.governance_level == "L3":
            return {"status": "blocked", "reason": f"Tool '{tool_name}' requires human-only access"}

        if tool.handler is None:
            return {"status": "error", "error": f"Tool '{tool_name}' has no handler"}

        try:
            result = tool.handler(**params)
            return {"status": "ok", "result": result}
        except TypeError as e:
            return {"status": "error", "error": f"Invalid params for '{tool_name}': {e}"}
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return {"status": "error", "error": str(e)}

    async def execute_async(self, tool_name: str, params: Dict) -> Dict:
        """Async version of execute (for tools that are async)."""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

        if tool.governance_level == "L3":
            return {"status": "blocked", "reason": f"Tool '{tool_name}' requires human-only access"}

        if tool.handler is None:
            return {"status": "error", "error": f"Tool '{tool_name}' has no handler"}

        try:
            import asyncio
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**params)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool.handler(**params))
            return {"status": "ok", "result": result}
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return {"status": "error", "error": str(e)}
