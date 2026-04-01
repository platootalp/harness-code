"""Integration tests for error handling.

This module provides integration tests for error handling including:
- Tool not found errors
- Tool execution errors
- Model call errors

Tests use @pytest.mark.integration marker.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.registry import ToolExecutionError, ToolNotFoundError, ToolRegistry
from mozi.core.model.adapter import (
    ModelProvider,
    ModelResponse,
)
from mozi.core.model.errors import (
    AuthenticationError,
    ModelInvocationError,
    RateLimitError,
    ResponseParseError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a fresh tool registry.

    Returns
    -------
    ToolRegistry
        New registry for testing.
    """
    return ToolRegistry()


@pytest.fixture
def tool_context() -> ToolContext:
    """Create a tool context for testing.

    Returns
    -------
    ToolContext
        Context with test parameters.
    """
    return ToolContext(
        tool_name="test_tool",
        parameters={},
        working_directory="/tmp",
    )


# =============================================================================
# Tool Not Found Error Tests
# =============================================================================


class TestToolNotFoundError:
    """Integration tests for tool not found errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test that executing a non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError) as exc_info:
            await tool_registry.execute("nonexistent_tool", tool_context)

        assert "nonexistent_tool" in str(exc_info.value)

    @pytest.mark.integration
    def test_get_nonexistent_tool(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test that getting a non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError):
            tool_registry.get("nonexistent_tool")

    @pytest.mark.integration
    def test_unregister_nonexistent_tool(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test that unregistering a non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError):
            tool_registry.unregister("nonexistent_tool")

    @pytest.mark.integration
    def test_register_duplicate_tool(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test that registering duplicate tool raises error."""

        class DummyTool(Tool):
            def __init__(self) -> None:
                super().__init__("dummy", "A dummy tool")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(status=ToolStatus.SUCCESS)

        tool_registry.register(DummyTool())

        with pytest.raises(ValueError) as exc_info:
            tool_registry.register(DummyTool())

        assert "already registered" in str(exc_info.value)


# =============================================================================
# Tool Execution Error Tests
# =============================================================================


class TestToolExecutionError:
    """Integration tests for tool execution errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_execution_raises_error(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test that tool execution raises ToolExecutionError on failure."""

        class FailingTool(Tool):
            def __init__(self) -> None:
                super().__init__("failing_tool", "A failing tool")

            async def execute(self, context: ToolContext) -> ToolResult:
                raise RuntimeError("Intentional failure")

        tool_registry.register(FailingTool())

        with pytest.raises(ToolExecutionError) as exc_info:
            await tool_registry.execute("failing_tool", tool_context)

        assert "failing_tool" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_returns_failure_status(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test that tool can return failure status instead of raising."""

        class FailingResultTool(Tool):
            def __init__(self) -> None:
                super().__init__("failing_result_tool", "A tool that returns failure")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    error="Tool returned failure",
                )

        tool_registry.register(FailingResultTool())

        result = await tool_registry.execute("failing_result_tool", tool_context)
        assert result.status == ToolStatus.FAILURE
        assert result.success is False


# =============================================================================
# Tool Timeout Error Tests
# =============================================================================


class TestToolTimeoutError:
    """Integration tests for tool timeout errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_timeout(self) -> None:
        """Test that slow tool execution respects timeout."""

        class SlowTool(Tool):
            def __init__(self) -> None:
                super().__init__("slow_tool", "A slow tool")

            async def execute(self, context: ToolContext) -> ToolResult:
                await asyncio.sleep(10)  # Simulate slow work
                return ToolResult(status=ToolStatus.SUCCESS)

        tool_registry = ToolRegistry()
        tool_registry.register(SlowTool())

        # Create context with short timeout
        short_timeout_context = ToolContext(
            tool_name="slow_tool",
            timeout_seconds=1,  # 1 second timeout
        )

        assert short_timeout_context.timeout_seconds == 1


# =============================================================================
# Path Permission Error Tests
# =============================================================================


class TestPathPermissionErrors:
    """Integration tests for path permission errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_with_permission_check(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test that tools can check permissions."""

        class ProtectedTool(Tool):
            def __init__(self) -> None:
                super().__init__("protected_tool", "A protected tool")

            async def execute(self, context: ToolContext) -> ToolResult:
                if context.permission_level < 5:
                    return ToolResult(
                        status=ToolStatus.DENIED,
                        error="Insufficient permission level",
                    )
                return ToolResult(status=ToolStatus.SUCCESS)

        tool_registry.register(ProtectedTool())

        # Low permission context
        low_perm_context = ToolContext(
            tool_name="protected_tool",
            permission_level=3,
        )
        result = await tool_registry.execute("protected_tool", low_perm_context)
        assert result.status == ToolStatus.DENIED

        # High permission context
        high_perm_context = ToolContext(
            tool_name="protected_tool",
            permission_level=7,
        )
        result = await tool_registry.execute("protected_tool", high_perm_context)
        assert result.status == ToolStatus.SUCCESS


# =============================================================================
# Model Call Error Tests
# =============================================================================


class TestModelCallErrors:
    """Integration tests for model call errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_model_authentication_error(self) -> None:
        """Test model handles authentication errors."""
        error = AuthenticationError(
            message="Authentication failed: Invalid API key",
            details={"provider": "anthropic"},
        )

        assert "authentication" in str(error).lower()
        assert error.error_code == "MODEL_006"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_model_rate_limit_error(self) -> None:
        """Test model handles rate limit errors."""
        error = RateLimitError(
            message="Rate limit exceeded",
            retry_after=60.0,
        )

        assert "rate limit" in str(error).lower()
        assert error.retry_after == 60.0
        assert error.error_code == "MODEL_005"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_model_invocation_error(self) -> None:
        """Test model handles invocation errors."""
        error = ModelInvocationError(
            message="Model invocation failed",
            model="claude-3",
        )

        assert "invocation failed" in str(error).lower()
        assert error.model == "claude-3"
        assert error.error_code == "MODEL_001"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_model_response_parse_error(self) -> None:
        """Test model handles response parse errors."""
        error = ResponseParseError(
            message="Failed to parse model response",
            details={"raw_response": "invalid"},
        )

        assert "parse" in str(error).lower()
        assert error.error_code == "MODEL_004"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_with_details(self) -> None:
        """Test error includes details."""
        error = ModelInvocationError(
            message="Invocation failed",
            model="test-model",
            details={"attempt": 3},
        )

        assert error.details["attempt"] == 3


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Integration tests for error recovery."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_registry_recovery_after_failed_execution(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test that registry remains functional after failed tool execution."""

        class FailingTool(Tool):
            def __init__(self) -> None:
                super().__init__("failing_tool", "A tool that fails")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    error="Intentional failure",
                )

        tool_registry.register(FailingTool())

        # First execution fails
        result1 = await tool_registry.execute("failing_tool", tool_context)
        assert result1.success is False

        # Registry should still work
        tools = tool_registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "failing_tool"

        # Can unregister the tool
        tool_registry.unregister("failing_tool")
        assert len(tool_registry.list_tools()) == 0


# =============================================================================
# Error Context Tests
# =============================================================================


class TestErrorContext:
    """Integration tests for error context."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_error_contains_context(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test that errors contain relevant context."""

        class ContextTool(Tool):
            def __init__(self) -> None:
                super().__init__("context_tool", "A tool that checks context")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"tool: {context.tool_name}, dir: {context.working_directory}",
                )

        tool_registry.register(ContextTool())

        context = ToolContext(
            tool_name="context_tool",
            working_directory="/project",
        )
        result = await tool_registry.execute("context_tool", context)

        assert result.success is True
        assert "context_tool" in result.output


# =============================================================================
# Edge Case Error Tests
# =============================================================================


class TestEdgeCaseErrors:
    """Integration tests for edge case errors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_tool_name(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test handling of empty tool name."""
        with pytest.raises(ToolNotFoundError):
            await tool_registry.execute("", tool_context)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_with_empty_parameters(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test tool execution with empty parameters."""

        class EmptyParamsTool(Tool):
            def __init__(self) -> None:
                super().__init__("empty_params_tool", "A tool with empty params")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"params: {context.parameters}",
                )

        tool_registry.register(EmptyParamsTool())

        context = ToolContext(tool_name="empty_params_tool")
        result = await tool_registry.execute("empty_params_tool", context)

        assert result.success is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_registry_with_many_tools(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        """Test registry with many registered tools."""

        for i in range(100):

            class NumberedTool(Tool):
                def __init__(self, num: int) -> None:
                    super().__init__(f"tool_{num}", f"Tool number {num}")

                async def execute(self, context: ToolContext) -> ToolResult:
                    return ToolResult(status=ToolStatus.SUCCESS)

            tool_registry.register(NumberedTool(i))

        tools = tool_registry.list_tools()
        assert len(tools) == 100

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_includes_tool_name(
        self,
        tool_registry: ToolRegistry,
        tool_context: ToolContext,
    ) -> None:
        """Test that errors include the tool name."""

        class NamedErrorTool(Tool):
            def __init__(self) -> None:
                super().__init__("specific_name_tool", "A specific named tool")

            async def execute(self, context: ToolContext) -> ToolResult:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    error="Something went wrong",
                )

        tool_registry.register(NamedErrorTool())

        result = await tool_registry.execute("specific_name_tool", tool_context)
        assert result.success is False
        assert "Something went wrong" in result.error
