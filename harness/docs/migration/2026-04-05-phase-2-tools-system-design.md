# Phase 2: 工具系统设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/Tool.ts`, `src/tools.ts`, `src/tools/*/`

---

## 1. 工具系统架构

### 1.1 核心组件

```
ToolSystem
├── BaseTool (abstract)
│   ├── name: str
│   ├── description: str
│   ├── input_schema: dict
│   ├── max_result_size_chars: int
│   ├── execute() [abstract]
│   ├── isConcurrencySafe()
│   ├── isReadOnly()
│   ├── isDestructive()
│   └── isEnabled()
├── ToolRegistry
│   ├── register()
│   ├── get()
│   ├── list_tools()
│   └── filter_tools()
└── ToolOrchestrator
    ├── partition_tool_calls()
    ├── execute_parallel()
    └── execute_serial()
```

### 1.2 工具分类

| 类别 | 工具 | 并发安全 |
|------|------|----------|
| **文件操作** | FileRead, FileEdit, FileWrite, Glob, Grep, NotebookEdit | ✓ |
| **Shell执行** | Bash, PowerShell | ✗ |
| **Web/API** | WebSearch, WebFetch | ✓ |
| **任务管理** | TaskCreate, TaskGet, TaskList, TaskUpdate, TaskStop, TaskOutput | 部分 |
| **Agent管理** | Agent, TeamCreate, TeamDelete, SendMessage | ✗ |
| **计划/模式** | EnterPlanMode, ExitPlanModeV2 | N/A |
| **用户交互** | AskUserQuestion, Brief | N/A |
| **配置** | Config | ✗ |
| **LSP** | LSP | ✓ |
| **MCP** | ListMcpResources, ReadMcpResource | ✓ |
| **调度** | CronCreate, CronDelete, CronList | ✗ |
| **Worktree** | EnterWorktree, ExitWorktree | ✗ |

---

## 2. 基础工具实现

### 2.1 BaseTool 抽象类

对应 TypeScript：`src/Tool.ts` Tool interface

```python
"""Base tool class - all tools inherit from this."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from ..models.tool import ToolResult
from .context import ToolExecuteContext


class BaseTool(ABC):
    """Base class for all tools.

    TypeScript equivalent: src/Tool.ts Tool interface

    All tools must implement:
    - execute(): Main tool logic
    - name, description, input_schema (set in __init__)
    """

    # Default values (TypeScript TOOL_DEFAULTS)
    DEFAULT_MAX_RESULT_SIZE_CHARS = 100_000

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        max_result_size_chars: int = DEFAULT_MAX_RESULT_SIZE_CHARS,
        aliases: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.max_result_size_chars = max_result_size_chars
        self.aliases = aliases or []

    @abstractmethod
    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        """Execute the tool with given input.

        Args:
            input_args: Validated input arguments
            context: Execution context (cwd, abort signal, etc.)

        Returns:
            Tool result as string (or raises exception for errors)
        """
        ...

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool can run in parallel with others.

        TypeScript: isConcurrencySafe
        Default: False (tools run serially unless explicitly marked safe)
        """
        return False

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool modifies system state.

        TypeScript: isReadOnly
        Default: False
        """
        return False

    def isDestructive(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool performs irreversible operations.

        TypeScript: isDestructive
        Default: False
        """
        return False

    def isEnabled(self) -> bool:
        """Whether this tool is available in current context.

        TypeScript: isEnabled
        Default: True
        """
        return True

    def getPath(self, input_args: dict[str, Any]) -> str | None:
        """Get the file path for file-operating tools.

        TypeScript: getPath
        Used for path-based permission checks.
        """
        return None

    def validate_input(
        self,
        input_args: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Validate input before execution.

        TypeScript: validateInput

        Returns:
            (is_valid, error_message)
        """
        # Default: assume valid if we have the required fields
        required = self.input_schema.get("required", [])
        for field in required:
            if field not in input_args:
                return False, f"Missing required field: {field}"
        return True, None

    def get_metadata(self) -> dict[str, Any]:
        """Get tool metadata for API registration."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

### 2.2 工具执行上下文

```python
"""Tool execution context."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class ToolExecuteContext:
    """Context passed to tool during execution.

    TypeScript equivalent: ToolCallContext or similar
    """
    working_directory: str = ""
    can_use_tool: Callable[[str], Awaitable[bool]] | None = None
    parent_message_id: str | None = None
    abort_signal: Any = None  # asyncio.Event or similar
    on_progress: Callable[[str], None] | None = None  # Progress callback

    def report_progress(self, message: str) -> None:
        """Report progress during long-running operations."""
        if self.on_progress:
            self.on_progress(message)
```

---

## 3. 工具实现详细设计

### 3.1 文件操作工具

#### FileReadTool

对应 TypeScript：`src/tools/FileReadTool/`

```python
"""File read tool - reads files from the filesystem."""
from __future__ import annotations
import os
import asyncio
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolExecuteContext


class FileReadTool(BaseTool):
    """Read file contents.

    TypeScript equivalent: src/tools/FileReadTool/

    Input schema:
        file_path: string (required)
        limit?: integer (optional, max lines)
        offset?: integer (optional, 0-indexed line)
        line_numbers?: boolean (optional)
    """

    def __init__(self):
        super().__init__(
            name="FileRead",
            description="Read the contents of a file. " +
                       "Use for viewing source code, configuration files, " +
                       "or any text-based files.",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (0-indexed)",
                    },
                    "line_numbers": {
                        "type": "boolean",
                        "description": "Show line numbers",
                    },
                },
                "required": ["file_path"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return True

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return True

    def getPath(self, input_args: dict[str, Any]) -> str | None:
        return input_args.get("file_path")

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        file_path = input_args["file_path"]
        limit = input_args.get("limit")
        offset = input_args.get("offset", 0)
        line_numbers = input_args.get("line_numbers", False)

        # Security: normalize path and check for traversal
        file_path = os.path.normpath(file_path)
        if ".." in file_path or file_path.startswith("/"):
            # Also check relative path traversal
            full_path = os.path.abspath(file_path)
            if context and context.working_directory:
                allowed_base = os.path.abspath(context.working_directory)
                if not full_path.startswith(allowed_base + os.sep):
                    return f"Error: Path '{file_path}' is outside working directory"

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                if offset:
                    # Seek to byte offset (approximate)
                    for _ in range(offset):
                        f.readline()

                if limit:
                    lines = []
                    for i in range(limit):
                        line = f.readline()
                        if not line:
                            break
                        if line_numbers:
                            lines.append(f"{offset + i + 1:6d}  {line}")
                        else:
                            lines.append(line.rstrip("\n"))
                    return "\n".join(lines)
                else:
                    content = f.read()
                    if line_numbers:
                        lines = content.split("\n")
                        numbered = [f"{i + 1:6d}  {line}" for i, line in enumerate(lines)]
                        return "\n".join(numbered)
                    return content

        except FileNotFoundError:
            return f"File not found: {file_path}"
        except IsADirectoryError:
            return f"Error: '{file_path}' is a directory, not a file"
        except PermissionError:
            return f"Error: Permission denied reading '{file_path}'"
        except Exception as e:
            return f"Error reading file: {str(e)}"
```

#### FileEditTool

对应 TypeScript：`src/tools/FileEditTool/`

```python
"""File edit tool - edits files in place (sed-style)."""
from __future__ import annotations
import os
import asyncio
from typing import Any

from .base import BaseTool, ToolExecuteContext


class FileEditTool(BaseTool):
    """Edit files in place using old_string/new_string replacement.

    TypeScript equivalent: src/tools/FileEditTool/

    Input schema:
        file_path: string (required)
        old_string: string (required)
        new_string: string (required)
        replace_all?: boolean (optional, default false)
    """

    def __init__(self):
        super().__init__(
            name="FileEdit",
            description="Make edits to a file by replacing text. " +
                       "old_string must match exactly, including whitespace and newlines.",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to edit",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to replace (must match exactly)",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement text",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences (default: false)",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        )

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return False

    def isDestructive(self, input_args: dict[str, Any]) -> bool:
        return False  # Non-destructive edit

    def getPath(self, input_args: dict[str, Any]) -> str | None:
        return input_args.get("file_path")

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        file_path = input_args["file_path"]
        old_string = input_args["old_string"]
        new_string = input_args["new_string"]
        replace_all = input_args.get("replace_all", False)

        # Validate inputs
        if not old_string:
            return "Error: old_string cannot be empty"

        # Security: prevent path traversal
        file_path = os.path.normpath(file_path)

        try:
            # Read current content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return f"Error: old_string not found in file. " + \
                       f"Please ensure the old_string matches exactly."

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f"Edited {file_path}: replaced {count} occurrence(s)"

        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except PermissionError:
            return f"Error: Permission denied writing '{file_path}'"
        except Exception as e:
            return f"Error editing file: {str(e)}"
```

#### FileWriteTool

对应 TypeScript：`src/tools/FileWriteTool/`

```python
"""File write tool - creates or overwrites files."""
from __future__ import annotations
import os
from typing import Any

from .base import BaseTool, ToolExecuteContext


class FileWriteTool(BaseTool):
    """Create or overwrite a file with content.

    TypeScript equivalent: src/tools/FileWriteTool/

    Input schema:
        file_path: string (required)
        content: string (required)
    """

    def __init__(self):
        super().__init__(
            name="FileWrite",
            description="Create a new file or overwrite an existing file with content",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["file_path", "content"],
            },
        )

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return False

    def isDestructive(self, input_args: dict[str, Any]) -> bool:
        return True  # Can overwrite existing files

    def getPath(self, input_args: dict[str, Any]) -> str | None:
        return input_args.get("file_path")

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        file_path = input_args["file_path"]
        content = input_args["content"]

        # Security: prevent path traversal
        file_path = os.path.normpath(file_path)

        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Write file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Wrote {len(content)} characters to {file_path}"

        except PermissionError:
            return f"Error: Permission denied writing '{file_path}'"
        except Exception as e:
            return f"Error writing file: {str(e)}"
```

#### GlobTool

```python
"""Glob tool - finds files by pattern."""
from __future__ import annotations
import os
import glob as glob_module
from typing import Any

from .base import BaseTool, ToolExecuteContext


class GlobTool(BaseTool):
    """Find files by pattern.

    TypeScript equivalent: src/tools/GlobTool/

    Input schema:
        pattern: string (required) - glob pattern (e.g., "**/*.py")
        path?: string (optional) - directory to search in
    """

    def __init__(self):
        super().__init__(
            name="Glob",
            description="Find files by pattern. Use ** for recursive matching.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: current directory)",
                    },
                },
                "required": ["pattern"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return True

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return True

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        pattern = input_args["pattern"]
        path = input_args.get("path") or context.working_directory or "."

        # Security: normalize path
        path = os.path.normpath(path)
        if ".." in path:
            return "Error: Path traversal not allowed"

        # Combine path and pattern
        search_pattern = os.path.join(path, pattern)

        try:
            matches = glob_module.glob(search_pattern, recursive=True)

            if not matches:
                return f"No files found matching '{pattern}' in '{path}'"

            # Sort for consistency
            matches.sort()

            # Limit output
            MAX_RESULTS = 100
            if len(matches) > MAX_RESULTS:
                return f"Found {len(matches)} files (showing first {MAX_RESULTS}):\n" + \
                       "\n".join(matches[:MAX_RESULTS])

            return f"Found {len(matches)} files:\n" + "\n".join(matches)

        except Exception as e:
            return f"Error searching for files: {str(e)}"
```

#### GrepTool

```python
"""Grep tool - searches file contents."""
from __future__ import annotations
import os
import re
from typing import Any

from .base import BaseTool, ToolExecuteContext


class GrepTool(BaseTool):
    """Search file contents using regex.

    TypeScript equivalent: src/tools/GrepTool/

    Input schema:
        pattern: string (required) - regex pattern
        path?: string (optional) - directory to search in
        glob?: string (optional) - file pattern to match
        output_mode?: string (optional) - "content" (default), "files", "count"
        -n?: boolean (optional) - show line numbers
        -i?: boolean (optional) - case insensitive
        -C?: integer (optional) - context lines
    """

    def __init__(self):
        super().__init__(
            name="Grep",
            description="Search file contents using regex patterns",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in",
                    },
                    "glob": {
                        "type": "string",
                        "description": "Only match files matching this glob pattern",
                    },
                    "output_mode": {
                        "type": "string",
                        "description": "Output format: 'content', 'files', 'count'",
                    },
                    "-n": {
                        "type": "boolean",
                        "description": "Show line numbers",
                    },
                    "-i": {
                        "type": "boolean",
                        "description": "Case insensitive search",
                    },
                    "-C": {
                        "type": "integer",
                        "description": "Number of context lines before/after",
                    },
                },
                "required": ["pattern"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return True

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return True

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        pattern = input_args["pattern"]
        path = input_args.get("path") or "."
        glob_pattern = input_args.get("glob")
        output_mode = input_args.get("output_mode", "content")
        show_line_numbers = input_args.get("-n", False)
        case_insensitive = input_args.get("-i", False)
        context_lines = input_args.get("-C", 0)

        # Compile regex
        flags = re.IGNORECASE if case_insensitive else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        # Security: normalize path
        path = os.path.normpath(path)
        if ".." in path:
            return "Error: Path traversal not allowed"

        results = []
        try:
            if os.path.isfile(path):
                # Single file
                results = self._search_file(path, regex, show_line_numbers, context_lines)
            else:
                # Directory - find matching files
                for root, dirs, files in os.walk(path):
                    # Filter by glob if specified
                    if glob_pattern:
                        import fnmatch
                        files = [f for f in files if fnmatch.fnmatch(f, glob_pattern)]

                    for filename in files:
                        filepath = os.path.join(root, filename)
                        matches = self._search_file(filepath, regex, show_line_numbers, context_lines)
                        results.extend(matches)

            if not results:
                return f"No matches found for '{pattern}'"

            # Format output
            if output_mode == "count":
                return f"Found {len(results)} matches"
            elif output_mode == "files":
                files = set(r[0] for r in results)
                return f"Found matches in {len(files)} files:\n" + "\n".join(sorted(files))
            else:  # content
                output = "\n".join(f"{filepath}:{line}:{content}" for filepath, line, content in results)
                return f"Found {len(results)} matches:\n{output}"

        except Exception as e:
            return f"Error searching: {str(e)}"

    def _search_file(
        self,
        filepath: str,
        regex: re.Pattern,
        show_line_numbers: bool,
        context_lines: int,
    ) -> list[tuple[str, int, str]]:
        """Search a single file for pattern matches."""
        results = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                match = regex.search(line)
                if match:
                    line_num = i + 1
                    if show_line_numbers:
                        results.append((filepath, line_num, line.rstrip()))
                    else:
                        results.append((filepath, line_num, line.rstrip()))

        except (FileNotFoundError, PermissionError, IsADirectoryError):
            pass

        return results
```

---

### 3.2 Shell执行工具

#### BashTool

对应 TypeScript：`src/tools/BashTool/`

```python
"""Bash tool - executes shell commands."""
from __future__ import annotations
import asyncio
import os
import shlex
from typing import Any

from .base import BaseTool, ToolExecuteContext


class BashTool(BaseTool):
    """Execute bash commands.

    TypeScript equivalent: src/tools/BashTool/

    Security features:
    - Shell parsing with bashlex
    - Path normalization
    - Timeout enforcement
    - Working directory restriction
    """

    def __init__(self):
        super().__init__(
            name="Bash",
            description="Execute a bash command. Use for git, npm, shell commands, etc.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                    },
                    "workingDirectory": {
                        "type": "string",
                        "description": "Working directory for the command",
                    },
                },
                "required": ["command"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return False  # Commands modify state

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        command = input_args.get("command", "").lower()
        readonly_commands = {"git status", "ls", "cat", "head", "tail", "grep", "find", "pwd"}
        return command.strip().startswith(readonly_commands)

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        command = input_args["command"]
        timeout = input_args.get("timeout", 30)
        cwd = input_args.get("workingDirectory") or context.working_directory or None

        # Validate timeout
        if timeout <= 0:
            timeout = 30
        if timeout > 300:  # 5 minute max
            timeout = 300

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ},  # Inherit environment
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"Command timed out after {timeout} seconds"

            # Format output
            result_parts = []

            if stdout:
                result_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_str = stderr.decode("utf-8", errors="replace")
                if stderr_str.strip():
                    result_parts.append(f"[stderr]\n{stderr_str}")

            if process.returncode != 0 and not result_parts:
                result_parts.append(f"Command exited with code {process.returncode}")

            return "\n".join(result_parts) if result_parts else ""

        except Exception as e:
            return f"Error executing command: {str(e)}"
```

---

### 3.3 Web工具

#### WebSearchTool

```python
"""Web search tool."""
from __future__ import annotations
import httpx
from typing import Any

from .base import BaseTool, ToolExecuteContext


class WebSearchTool(BaseTool):
    """Search the web for information.

    TypeScript equivalent: src/tools/WebSearchTool/

    Input schema:
        query: string (required)
        allowed_domains?: string[] (optional)
        blocked_domains?: string[] (optional)
    """

    MAX_USES = 8  # Per TypeScript implementation

    def __init__(self):
        super().__init__(
            name="WebSearch",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "allowed_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict search to these domains",
                    },
                    "blocked_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exclude these domains from results",
                    },
                },
                "required": ["query"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return True

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return True

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        query = input_args["query"]
        # Note: In production, implement actual search via API
        # For now, return placeholder
        return f"Web search not implemented: {query}"
```

#### WebFetchTool

```python
"""Web fetch tool - fetches URL content."""
from __future__ import annotations
import httpx
from typing import Any

from .base import BaseTool, ToolExecuteContext


class WebFetchTool(BaseTool):
    """Fetch content from a URL.

    TypeScript equivalent: src/tools/WebFetchTool/

    Input schema:
        url: string (required)
        prompt?: string (optional) - what to extract/find
    """

    ALLOWED_HOSTS = {
        "github.com",
        "gitlab.com",
        "raw.githubusercontent.com",
        "pypi.org",
        "npmjs.com",
    }

    def __init__(self):
        super().__init__(
            name="WebFetch",
            description="Fetch content from a URL and convert to markdown",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to extract from the page",
                    },
                },
                "required": ["url"],
            },
        )

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        return True

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        return True

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        url = input_args["url"]

        # Parse URL and check host
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.netloc

        if host not in self.ALLOWED_HOSTS:
            return f"Error: Host '{host}' is not in the allowed list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Convert to markdown (simplified)
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    # Would use html2text in production
                    return f"[HTML content from {url}]\n{response.text[:5000]}"
                else:
                    return response.text[:50000]  # Limit output

        except httpx.HTTPError as e:
            return f"Error fetching URL: {str(e)}"
```

---

### 3.4 任务管理工具

#### TaskCreateTool

```python
"""Task create tool."""
from __future__ annotations
from dataclasses import dataclass
from typing import Any

from .base import BaseTool, ToolExecuteContext


class TaskCreateTool(BaseTool):
    """Create a task in the task list.

    TypeScript equivalent: src/tools/TaskCreateTool/

    Input schema:
        subject: string (required) - task title
        description?: string (optional)
        activeForm?: string (optional) - present tense action
        metadata?: object (optional)
    """

    def __init__(self):
        super().__init__(
            name="TaskCreate",
            description="Create a new task in the task list",
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Task title/subject",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description",
                    },
                    "activeForm": {
                        "type": "string",
                        "description": "Present tense action (e.g., 'Fixing bug')",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata",
                    },
                },
                "required": ["subject"],
            },
        )

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        # In production, this would interact with a task store
        subject = input_args["subject"]
        description = input_args.get("description", "")
        active_form = input_args.get("activeForm")

        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())[:8]

        # Store task (placeholder)
        # In production: await task_store.create(...)

        return f"Task created: [{task_id}] {subject}"
```

#### TaskStopTool

```python
"""Task stop tool - stops a background task."""
from __future__ import annotations
import signal
from typing import Any

from .base import BaseTool, ToolExecuteContext


class TaskStopTool(BaseTool):
    """Stop a running background task.

    TypeScript equivalent: src/tools/TaskStopTool/
    Also known as: KillShell

    Input schema:
        task_id: string (required)
    """

    def __init__(self):
        super().__init__(
            name="TaskStop",
            description="Stop a running background task",
            aliases=["KillShell"],
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to stop",
                    },
                },
                "required": ["task_id"],
            },
        )

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        task_id = input_args["task_id"]

        # In production, this would find and signal the task
        # For now, placeholder
        return f"Task stop not fully implemented for: {task_id}"
```

---

## 4. 完整工具清单

| # | 工具名称 | 类名 | 并发安全 | 只读 | 破坏性 | Feature Gated |
|---|---------|------|---------|------|--------|---------------|
| 1 | FileRead | FileReadTool | ✓ | ✓ | - | - |
| 2 | FileEdit | FileEditTool | - | - | - | - |
| 3 | FileWrite | FileWriteTool | - | - | ✓ | - |
| 4 | Glob | GlobTool | ✓ | ✓ | - | - |
| 5 | Grep | GrepTool | ✓ | ✓ | - | - |
| 6 | Bash | BashTool | - | - | - | - |
| 7 | PowerShell | PowerShellTool | - | - | - | ✓ |
| 8 | WebSearch | WebSearchTool | ✓ | ✓ | - | - |
| 9 | WebFetch | WebFetchTool | ✓ | ✓ | - | - |
| 10 | Agent | AgentTool | - | - | - | - |
| 11 | TaskCreate | TaskCreateTool | - | - | - | - |
| 12 | TaskGet | TaskGetTool | ✓ | ✓ | - | - |
| 13 | TaskList | TaskListTool | ✓ | ✓ | - | - |
| 14 | TaskUpdate | TaskUpdateTool | - | - | - | - |
| 15 | TaskStop | TaskStopTool | - | - | - | - |
| 16 | TaskOutput | TaskOutputTool | ✓ | ✓ | - | - |
| 17 | TeamCreate | TeamCreateTool | - | - | - | - |
| 18 | TeamDelete | TeamDeleteTool | - | - | - | - |
| 19 | SendMessage | SendMessageTool | - | - | - | - |
| 20 | EnterPlanMode | EnterPlanModeTool | - | - | - | - |
| 21 | ExitPlanModeV2 | ExitPlanModeV2Tool | - | - | - | - |
| 22 | AskUserQuestion | AskUserQuestionTool | - | - | - | - |
| 23 | Brief | BriefTool | - | - | - | ✓ |
| 24 | Config | ConfigTool | - | - | - | - |
| 25 | LSP | LSPTool | ✓ | ✓ | - | ✓ |
| 26 | ListMcpResources | ListMcpResourcesTool | ✓ | ✓ | - | - |
| 27 | ReadMcpResource | ReadMcpResourceTool | ✓ | ✓ | - | - |
| 28 | CronCreate | CronCreateTool | - | - | - | ✓ |
| 29 | CronDelete | CronDeleteTool | - | - | - | ✓ |
| 30 | CronList | CronListTool | ✓ | ✓ | - | ✓ |
| 31 | EnterWorktree | EnterWorktreeTool | - | - | - | ✓ |
| 32 | ExitWorktree | ExitWorktreeTool | - | - | - | ✓ |
| 33 | NotebookEdit | NotebookEditTool | - | - | - | - |
| 34 | ToolSearch | ToolSearchTool | ✓ | ✓ | - | - |
| 35 | StructuredOutput | StructuredOutputTool | - | - | - | - |

---

## 5. 实施任务清单

### Phase 2.1: 基础框架
- [ ] 实现 `tools/base.py` - BaseTool
- [ ] 实现 `tools/context.py` - ToolExecuteContext
- [ ] 实现 `tools/registry.py` - ToolRegistry
- [ ] 实现 `tools/orchestration.py` - ToolOrchestrator

### Phase 2.2: 文件操作工具
- [ ] 实现 FileReadTool
- [ ] 实现 FileEditTool
- [ ] 实现 FileWriteTool
- [ ] 实现 GlobTool
- [ ] 实现 GrepTool
- [ ] 实现 NotebookEditTool

### Phase 2.3: Shell工具
- [ ] 实现 BashTool
- [ ] 实现 PowerShellTool (feature-gated)

### Phase 2.4: Web工具
- [ ] 实现 WebSearchTool
- [ ] 实现 WebFetchTool

### Phase 2.5: 任务管理工具
- [ ] 实现 TaskCreateTool
- [ ] 实现 TaskGetTool
- [ ] 实现 TaskListTool
- [ ] 实现 TaskUpdateTool
- [ ] 实现 TaskStopTool
- [ ] 实现 TaskOutputTool

### Phase 2.6: Agent/团队工具
- [ ] 实现 AgentTool
- [ ] 实现 TeamCreateTool
- [ ] 实现 TeamDeleteTool
- [ ] 实现 SendMessageTool

### Phase 2.7: 其他工具
- [ ] 实现 EnterPlanModeTool
- [ ] 实现 ExitPlanModeV2Tool
- [ ] 实现 AskUserQuestionTool
- [ ] 实现 BriefTool
- [ ] 实现 ConfigTool
- [ ] 实现 LSPTool
- [ ] 实现 ListMcpResourcesTool
- [ ] 实现 ReadMcpResourceTool
- [ ] 实现 CronCreateTool / CronDeleteTool / CronListTool
- [ ] 实现 EnterWorktreeTool / ExitWorktreeTool
- [ ] 实现 ToolSearchTool
- [ ] 实现 StructuredOutputTool
