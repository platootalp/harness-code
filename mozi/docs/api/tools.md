# Tools API

## Overview

The Tools module provides a framework for executing tools with security controls and permissions.

## Tool Base Class

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Tool name |
| `description` | `str` | Tool description |
| `version` | `str` | Tool version |

### Methods

#### `execute(context: ToolContext) -> ToolResult`

Executes the tool.

**Parameters:**
- `context` (ToolContext): Execution context

**Returns:**
- `ToolResult`: Execution result

## ToolContext

| Attribute | Type | Description |
|-----------|------|-------------|
| `tool_name` | `str` | Name of tool being executed |
| `parameters` | `dict[str, Any]` | Tool parameters |
| `working_directory` | `str` | Current working directory |
| `allowed_paths` | `list[str]` | Paths tool can access |
| `permission_level` | `int` | Permission level (0-4) |
| `timeout_seconds` | `int` | Execution timeout |

## ToolResult

| Attribute | Type | Description |
|-----------|------|-------------|
| `status` | `ToolStatus` | Execution status |
| `output` | `Any` | Tool output |
| `error` | `str \| None` | Error message if failed |
| `execution_time` | `float` | Execution time in seconds |

### ToolStatus Enum

- `SUCCESS`: Execution succeeded
- `FAILURE`: Execution failed
- `TIMEOUT`: Execution timed out
- `DENIED`: Execution denied (permission)

## Permission Levels

| Level | Description |
|-------|-------------|
| 0 | Sandbox - no file/system access |
| 1 | Read access |
| 2 | Read and write access |
| 3 | Command execution |
| 4 | Full access (dangerous) |

## Built-in Tools

### ReadFileTool

Reads file contents.

```python
tool = ReadFileTool()
result = await tool.execute(context)
```

### WriteFileTool

Writes content to files (atomic write).

### EditFileTool

Edits files using string replacement or regex.

### BashTool

Executes shell commands with security controls.

### GrepTool

Searches file contents using patterns.

### GlobTool

Finds files matching glob patterns.

## ToolRegistry

### Methods

#### `register(tool: Tool) -> None`

Registers a tool.

#### `unregister(tool_name: str) -> None`

Unregisters a tool.

#### `get(tool_name: str) -> Tool`

Gets a tool by name.

#### `list_tools() -> list[dict]`

Lists all registered tools.

#### `execute(tool_name: str, context: ToolContext) -> ToolResult`

Executes a tool by name.

## Usage Example

```python
from mozi.core.tools import ToolRegistry, ToolContext, ReadFileTool

registry = ToolRegistry()
registry.register(ReadFileTool())

context = ToolContext(
    tool_name="read",
    parameters={"path": "/path/to/file"},
    permission_level=1
)

result = await registry.execute("read", context)
```
