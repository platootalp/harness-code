"""Unit tests for tools framework module."""


from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus


class TestToolContext:
    """Tests for ToolContext dataclass."""

    def test_tool_context_creation(self) -> None:
        """Test creating a ToolContext with default values."""
        context = ToolContext(tool_name="test_tool")
        assert context.tool_name == "test_tool"
        assert context.parameters == {}
        assert context.working_directory == "/Users/lijunyi/road/src"
        assert context.allowed_paths == []
        assert context.permission_level == 0
        assert context.timeout_seconds == 300

    def test_tool_context_with_parameters(self) -> None:
        """Test creating a ToolContext with custom parameters."""
        context = ToolContext(
            tool_name="test_tool",
            parameters={"key": "value"},
            permission_level=3,
            timeout_seconds=60,
        )
        assert context.tool_name == "test_tool"
        assert context.parameters == {"key": "value"}
        assert context.permission_level == 3
        assert context.timeout_seconds == 60


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_tool_result_success(self) -> None:
        """Test creating a successful ToolResult."""
        result = ToolResult(status=ToolStatus.SUCCESS, output="done")
        assert result.success is True
        assert result.status == ToolStatus.SUCCESS
        assert result.output == "done"
        assert result.error is None

    def test_tool_result_failure(self) -> None:
        """Test creating a failed ToolResult."""
        result = ToolResult(status=ToolStatus.FAILURE, error="error message")
        assert result.success is False
        assert result.status == ToolStatus.FAILURE
        assert result.error == "error message"

    def test_tool_result_timeout(self) -> None:
        """Test creating a timeout ToolResult."""
        result = ToolResult(status=ToolStatus.TIMEOUT, error="timed out")
        assert result.success is False
        assert result.status == ToolStatus.TIMEOUT

    def test_tool_result_with_execution_time(self) -> None:
        """Test ToolResult with execution time."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output="result",
            execution_time=1.5,
        )
        assert result.execution_time == 1.5


class DummyTool(Tool):
    """Concrete implementation of Tool for testing."""

    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the dummy tool."""
        return ToolResult(status=ToolStatus.SUCCESS, output="executed")


class TestTool:
    """Tests for Tool abstract base class."""

    def test_tool_initialization(self) -> None:
        """Test tool initialization with basic attributes."""
        tool = DummyTool(name="test", description="A test tool", version="1.0.0")
        assert tool.name == "test"
        assert tool.description == "A test tool"
        assert tool.version == "1.0.0"

    def test_tool_schema(self) -> None:
        """Test tool schema property."""
        tool = DummyTool(name="test", description="A test tool")
        schema = tool.schema
        assert schema["name"] == "test"
        assert schema["description"] == "A test tool"
        assert schema["version"] == "1.0.0"
        assert "parameters" in schema
