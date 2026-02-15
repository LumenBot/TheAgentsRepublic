"""
Tests for agent.tool_registry — ToolParam, Tool, and ToolRegistry.
"""

import asyncio
import pytest

from agent.tool_registry import Tool, ToolParam, ToolRegistry


# ===================================================================
# ToolParam tests
# ===================================================================

class TestToolParam:
    def test_defaults(self):
        """ToolParam has sensible defaults for required and default."""
        p = ToolParam(name="q", type="string", description="query")
        assert p.required is True
        assert p.default is None

    def test_optional_param(self):
        """An optional param with a default value is stored correctly."""
        p = ToolParam(name="limit", type="integer", description="max results",
                       required=False, default=10)
        assert p.required is False
        assert p.default == 10


# ===================================================================
# Tool.to_schema tests
# ===================================================================

class TestToolSchema:
    def test_schema_structure(self, sample_tool):
        """to_schema returns an Anthropic-compatible dict with the expected keys."""
        schema = sample_tool.to_schema()
        assert schema["name"] == "echo"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "message" in schema["input_schema"]["properties"]
        assert "message" in schema["input_schema"]["required"]

    def test_schema_description_includes_governance(self, sample_tool):
        """The schema description is prefixed with the governance level."""
        schema = sample_tool.to_schema()
        assert schema["description"].startswith("[L1]")

    def test_schema_optional_param_not_in_required(self):
        """Optional parameters do not appear in the required list."""
        tool = Tool(
            name="search",
            description="Search",
            params=[
                ToolParam("query", "string", "Search query", required=True),
                ToolParam("limit", "integer", "Max results", required=False, default=10),
            ],
            handler=lambda **kw: kw,
        )
        schema = tool.to_schema()
        assert "query" in schema["input_schema"]["required"]
        assert "limit" not in schema["input_schema"]["required"]

    def test_schema_default_value_included(self):
        """When a param has a default, it appears in the schema properties."""
        tool = Tool(
            name="t",
            description="d",
            params=[ToolParam("x", "integer", "desc", default=42)],
            handler=lambda **kw: kw,
        )
        schema = tool.to_schema()
        assert schema["input_schema"]["properties"]["x"]["default"] == 42

    def test_schema_no_params(self):
        """A tool with zero params produces an empty properties dict."""
        tool = Tool(name="ping", description="Ping", params=[], handler=lambda: "pong")
        schema = tool.to_schema()
        assert schema["input_schema"]["properties"] == {}
        assert schema["input_schema"]["required"] == []


# ===================================================================
# ToolRegistry tests
# ===================================================================

class TestToolRegistry:
    def test_register_and_get(self, registry, sample_tool):
        """A registered tool can be retrieved by name."""
        t = registry.get("echo")
        assert t is not None
        assert t.name == "echo"

    def test_get_missing_returns_none(self, registry):
        """Getting a non-existent tool returns None."""
        assert registry.get("nonexistent") is None

    def test_list_tools(self, registry):
        """list_tools returns all registered tool names."""
        names = registry.list_tools()
        assert "echo" in names
        assert "dangerous_op" in names
        assert "placeholder" in names

    def test_list_by_category(self, registry):
        """list_by_category returns only tools in that category."""
        utility = registry.list_by_category("utility")
        assert "echo" in utility
        assert "dangerous_op" not in utility

    def test_list_by_unknown_category(self, registry):
        """Querying a non-existent category returns an empty list."""
        assert registry.list_by_category("nonexistent") == []

    def test_register_many(self):
        """register_many adds multiple tools at once."""
        reg = ToolRegistry()
        tools = [
            Tool(name="a", description="A", handler=lambda: 1),
            Tool(name="b", description="B", handler=lambda: 2),
        ]
        reg.register_many(tools)
        assert len(reg.list_tools()) == 2

    def test_overwrite_existing_tool(self):
        """Registering a tool with the same name overwrites the old one."""
        reg = ToolRegistry()
        reg.register(Tool(name="dup", description="First", handler=lambda: 1))
        reg.register(Tool(name="dup", description="Second", handler=lambda: 2))
        assert reg.get("dup").description == "Second"
        # Only one entry in list_tools
        assert reg.list_tools().count("dup") == 1

    def test_get_tool_schemas_excludes_no_handler(self, registry):
        """get_tool_schemas skips tools without a handler."""
        schemas = registry.get_tool_schemas()
        names = [s["name"] for s in schemas]
        assert "placeholder" not in names
        # echo has a handler, so it should appear
        assert "echo" in names

    def test_get_tool_schemas_filter_by_category(self, registry):
        """get_tool_schemas with category filter only returns matching tools."""
        schemas = registry.get_tool_schemas(categories=["admin"])
        names = [s["name"] for s in schemas]
        assert "dangerous_op" in names
        assert "echo" not in names

    def test_get_tools_summary_contains_categories(self, registry):
        """get_tools_summary includes category headings and tool names."""
        summary = registry.get_tools_summary()
        assert "Available tools:" in summary
        assert "[UTILITY]" in summary
        assert "echo" in summary


# ===================================================================
# ToolRegistry.execute tests
# ===================================================================

class TestToolRegistryExecute:
    def test_execute_ok(self, registry):
        """Executing a valid tool returns status ok with results."""
        result = registry.execute("echo", {"message": "hello"})
        assert result["status"] == "ok"
        assert result["result"] == {"message": "hello"}

    def test_execute_unknown_tool(self, registry):
        """Executing a non-existent tool returns status error."""
        result = registry.execute("does_not_exist", {})
        assert result["status"] == "error"
        assert "Unknown tool" in result["error"]

    def test_execute_l3_blocked(self, registry):
        """L3 tools return status blocked."""
        result = registry.execute("dangerous_op", {})
        assert result["status"] == "blocked"
        assert "human-only" in result["reason"]

    def test_execute_no_handler(self, registry):
        """A tool with no handler returns status error."""
        result = registry.execute("placeholder", {"arg": "test"})
        assert result["status"] == "error"
        assert "no handler" in result["error"]

    def test_execute_invalid_params(self, registry):
        """Passing wrong params to a handler returns status error."""
        result = registry.execute("echo", {"wrong_param": "oops"})
        assert result["status"] == "error"
        assert "Invalid params" in result["error"]

    def test_execute_handler_exception(self):
        """A handler that raises an exception returns status error."""
        def failing_handler(**kwargs):
            raise ValueError("something went wrong")

        reg = ToolRegistry()
        reg.register(Tool(name="fail", description="Fails", handler=failing_handler))
        result = reg.execute("fail", {})
        assert result["status"] == "error"
        assert "something went wrong" in result["error"]


# ===================================================================
# ToolRegistry.execute_async tests
# ===================================================================

class TestToolRegistryAsync:
    @pytest.mark.asyncio
    async def test_async_execute_sync_handler(self, registry):
        """execute_async wraps a synchronous handler correctly."""
        result = await registry.execute_async("echo", {"message": "async hello"})
        assert result["status"] == "ok"
        assert result["result"]["message"] == "async hello"

    @pytest.mark.asyncio
    async def test_async_execute_unknown(self, registry):
        """execute_async with unknown tool returns error."""
        result = await registry.execute_async("nope", {})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_async_execute_l3_blocked(self, registry):
        """execute_async blocks L3 tools."""
        result = await registry.execute_async("dangerous_op", {})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_async_execute_no_handler(self, registry):
        """execute_async with no handler returns error."""
        result = await registry.execute_async("placeholder", {"arg": "x"})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_async_execute_real_async_handler(self):
        """execute_async can run a true async handler."""
        async def async_handler(**kw):
            return {"received": kw}

        reg = ToolRegistry()
        reg.register(Tool(name="async_tool", description="Async", handler=async_handler))
        result = await reg.execute_async("async_tool", {"key": "value"})
        assert result["status"] == "ok"
        assert result["result"]["received"] == {"key": "value"}
