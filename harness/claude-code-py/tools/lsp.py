"""
LSPTool - Code intelligence via Language Server Protocol.

Migrated from src/tools/LSPTool/LSPTool.ts.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)
from ..utils.file import expand_path

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

LSP_TOOL_NAME = "LSP"

# Maximum file size for LSP analysis (10 MB)
MAX_LSP_FILE_SIZE_BYTES = 10_000_000

# =============================================================================
# LSP Operations
# =============================================================================

LSP_OPERATIONS = [
    "goToDefinition",
    "findReferences",
    "hover",
    "documentSymbol",
    "workspaceSymbol",
    "goToImplementation",
    "prepareCallHierarchy",
    "incomingCalls",
    "outgoingCalls",
]


def _is_lsp_connected() -> bool:
    """Check if LSP is connected.

    Mock implementation. Returns False by default.
    """
    try:
        from ..services.lsp.manager import is_lsp_connected

        return bool(is_lsp_connected())
    except ImportError:
        return False


def _get_lsp_server_manager() -> Any | None:
    """Get the LSP server manager.

    Mock implementation. Returns None by default.
    """
    try:
        from ..services.lsp.manager import get_lsp_server_manager

        return get_lsp_server_manager()
    except ImportError:
        return None


def _format_result(
    operation: str,
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format LSP result based on operation type.

    Args:
        operation: The LSP operation name.
        result: The raw LSP result.
        cwd: Current working directory.

    Returns:
        Tuple of (formatted_string, result_count, file_count).
    """
    if result is None:
        return ("No result found.", 0, 0)

    if operation == "goToDefinition":
        return _format_goto_definition(result, cwd)
    elif operation == "findReferences":
        return _format_find_references(result, cwd)
    elif operation == "hover":
        return _format_hover(result, cwd)
    elif operation == "documentSymbol":
        return _format_document_symbol(result, cwd)
    elif operation == "workspaceSymbol":
        return _format_workspace_symbol(result, cwd)
    elif operation == "goToImplementation":
        return _format_goto_definition(result, cwd)
    elif operation == "prepareCallHierarchy":
        return _format_prepare_call_hierarchy(result, cwd)
    elif operation == "incomingCalls":
        return _format_incoming_calls(result, cwd)
    elif operation == "outgoingCalls":
        return _format_outgoing_calls(result, cwd)

    return (str(result), 0, 0)


def _format_goto_definition(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format goToDefinition result."""
    locations: list[Any] = []
    if isinstance(result, list):
        for item in result:
            loc = _to_location(item)
            if loc and loc.get("uri"):
                locations.append(loc)
    elif result:
        loc = _to_location(result)
        if loc and loc.get("uri"):
            locations.append(loc)

    if not locations:
        return ("No definition found.", 0, 0)

    unique_uris: set[str] = set()
    lines: list[str] = []
    for loc in locations:
        uri = loc["uri"]
        unique_uris.add(uri)
        file_path = _uri_to_filepath(uri, cwd)
        start = loc.get("range", {}).get("start", {})
        line = start.get("line", 0) + 1
        char = start.get("character", 0) + 1
        lines.append(f"{file_path}:{line}:{char}")

    return (
        "Found at: " + "; ".join(lines),
        len(locations),
        len(unique_uris),
    )


def _format_find_references(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format findReferences result."""
    locations: list[Any] = []
    if isinstance(result, list):
        for item in result:
            loc = _to_location(item)
            if loc and loc.get("uri"):
                locations.append(loc)

    if not locations:
        return ("No references found.", 0, 0)

    unique_uris: set[str] = set()
    lines: list[str] = []
    for loc in locations:
        uri = loc["uri"]
        unique_uris.add(uri)
        file_path = _uri_to_filepath(uri, cwd)
        start = loc.get("range", {}).get("start", {})
        line = start.get("line", 0) + 1
        char = start.get("character", 0) + 1
        lines.append(f"{file_path}:{line}:{char}")

    count = len(locations)
    return (
        f"Found {count} reference(s): " + "; ".join(lines),
        count,
        len(unique_uris),
    )


def _format_hover(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format hover result."""
    if not result:
        return ("No hover information available.", 0, 0)

    contents = result.get("contents", "")
    value = contents.get("value", str(contents)) if isinstance(contents, dict) else str(contents)

    return (value, 1, 1)


def _format_document_symbol(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format documentSymbol result."""
    if not result:
        return ("No symbols found.", 0, 0)

    symbols: list[Any] = result if isinstance(result, list) else []
    lines: list[str] = []
    count = 0

    def count_and_format(items: list[Any], indent: int = 0) -> None:
        nonlocal count
        for item in items:
            if isinstance(item, dict):
                name = item.get("name", "?")
                kind = item.get("kind", "?")
                lines.append("  " * indent + f"{kind}: {name}")
                count += 1
                children = item.get("children", [])
                if children:
                    count_and_format(children, indent + 1)

    count_and_format(symbols)
    return ("\n".join(lines) if lines else "No symbols.", count, 1)


def _format_workspace_symbol(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format workspaceSymbol result."""
    if not result:
        return ("No workspace symbols found.", 0, 0)

    symbols: list[Any] = result if isinstance(result, list) else []
    lines: list[str] = []
    unique_uris: set[str] = set()

    for sym in symbols:
        if not isinstance(sym, dict):
            continue
        name = sym.get("name", "?")
        kind = str(sym.get("kind", "?"))
        loc = sym.get("location", {})
        uri = loc.get("uri", "") if isinstance(loc, dict) else ""
        if uri:
            unique_uris.add(uri)
            file_path = _uri_to_filepath(uri, cwd)
            lines.append(f"{kind} {name} ({file_path})")

    return (
        "\n".join(lines) if lines else "No symbols.",
        len(symbols),
        len(unique_uris),
    )


def _format_prepare_call_hierarchy(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format prepareCallHierarchy result."""
    if not result:
        return ("No call hierarchy items found.", 0, 0)

    items: list[Any] = result if isinstance(result, list) else [result]
    lines: list[str] = []
    unique_uris: set[str] = set()

    for item in items:
        if isinstance(item, dict):
            name = item.get("name", "?")
            kind = str(item.get("kind", "?"))
            uri = item.get("uri", "")
            if uri:
                unique_uris.add(uri)
                file_path = _uri_to_filepath(uri, cwd)
                lines.append(f"{kind} {name} at {file_path}")

    return (
        "\n".join(lines) if lines else "No call hierarchy.",
        len(items),
        len(unique_uris),
    )


def _format_incoming_calls(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format incomingCalls result."""
    if not result:
        return ("No incoming calls found.", 0, 0)

    calls: list[Any] = result if isinstance(result, list) else [result]
    lines: list[str] = []
    unique_uris: set[str] = set()

    for call in calls:
        if not isinstance(call, dict):
            continue
        from_item = call.get("from", {})
        if isinstance(from_item, dict):
            name = from_item.get("name", "?")
            uri = from_item.get("uri", "")
            if uri:
                unique_uris.add(uri)
                file_path = _uri_to_filepath(uri, cwd)
                lines.append(f"Called by {name} ({file_path})")

    return (
        "\n".join(lines) if lines else "No incoming calls.",
        len(calls),
        len(unique_uris),
    )


def _format_outgoing_calls(
    result: Any,
    cwd: str,
) -> tuple[str, int, int]:
    """Format outgoingCalls result."""
    if not result:
        return ("No outgoing calls found.", 0, 0)

    calls: list[Any] = result if isinstance(result, list) else [result]
    lines: list[str] = []
    unique_uris: set[str] = set()

    for call in calls:
        if not isinstance(call, dict):
            continue
        to_item = call.get("to", {})
        if isinstance(to_item, dict):
            name = to_item.get("name", "?")
            uri = to_item.get("uri", "")
            if uri:
                unique_uris.add(uri)
                file_path = _uri_to_filepath(uri, cwd)
                lines.append(f"Calls {name} ({file_path})")

    return (
        "\n".join(lines) if lines else "No outgoing calls.",
        len(calls),
        len(unique_uris),
    )


def _to_location(item: Any) -> dict[str, Any] | None:
    """Convert LocationLink to Location format."""
    if not isinstance(item, dict):
        return None
    # LocationLink has targetUri, Location has uri
    if "targetUri" in item:
        return {
            "uri": item.get("targetUri", ""),
            "range": item.get("targetSelectionRange") or item.get("targetRange", {}),
        }
    return {"uri": item.get("uri", ""), "range": item.get("range", {})}


def _uri_to_filepath(uri: str, cwd: str) -> str:
    """Convert file:// URI to a file path."""
    if not uri.startswith("file://"):
        return uri
    file_path = uri[7:]  # Remove "file://"
    # On Windows, file:///C:/path -> /C:/path -> C:/path
    import sys

    if sys.platform == "win32" and len(file_path) > 2 and file_path[0] == "/" and file_path[2] == ":":
        file_path = file_path[1:]
    try:
        import urllib.parse

        file_path = urllib.parse.unquote(file_path)
    except Exception:
        pass
    return file_path


# =============================================================================
# LSPTool
# =============================================================================


class LSPTool(BaseTool):
    """Tool for Language Server Protocol (LSP) operations.

    Provides code intelligence features including go-to-definition,
    find-references, hover information, and symbol search.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "code intelligence (definitions, references, symbols, hover)"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = True

    @property
    def name(self) -> str:
        return LSP_TOOL_NAME

    @property
    def description_text(self) -> str:
        return (
            "LSP tool for code intelligence operations including "
            "go-to-definition, find-references, hover, document symbols, "
            "workspace symbols, implementation lookup, and call hierarchy analysis."
        )

    @property
    def prompt_text(self) -> str:
        return (
            "Use the LSP tool to perform code intelligence operations. "
            "Provide the file path, line number (1-based), and character position (1-based). "
            "Operations include: goToDefinition, findReferences, hover, documentSymbol, "
            "workspaceSymbol, goToImplementation, prepareCallHierarchy, incomingCalls, outgoingCalls."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": LSP_OPERATIONS,
                    "description": "The LSP operation to perform",
                },
                "filePath": {
                    "type": "string",
                    "description": "The absolute or relative path to the file",
                },
                "line": {
                    "type": "number",
                    "description": "The line number (1-based, as shown in editors)",
                },
                "character": {
                    "type": "number",
                    "description": "The character offset (1-based, as shown in editors)",
                },
            },
            "required": ["operation", "filePath", "line", "character"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": LSP_OPERATIONS,
                    "description": "The LSP operation that was performed",
                },
                "result": {
                    "type": "string",
                    "description": "The formatted result of the LSP operation",
                },
                "filePath": {
                    "type": "string",
                    "description": "The file path the operation was performed on",
                },
                "resultCount": {
                    "type": "number",
                    "description": "Number of results (definitions, references, symbols)",
                },
                "fileCount": {
                    "type": "number",
                    "description": "Number of files containing results",
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "LSP"

    def is_enabled(self) -> bool:
        return _is_lsp_connected()

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("filePath", ""))

    def is_lsp(self) -> bool:
        """Return True to indicate this is an LSP tool."""
        return True

    def get_path(self, input: Any) -> str | None:
        return expand_path(input.get("filePath", ""))

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the LSP tool input."""
        file_path = input.get("filePath")
        if not file_path:
            return (False, "filePath is required", 3)

        operation = input.get("operation")
        if operation and operation not in LSP_OPERATIONS:
            return (False, f"Invalid operation: {operation}", 3)

        absolute_path = expand_path(file_path)

        # SECURITY: Skip filesystem operations for UNC paths.
        if absolute_path.startswith("\\\\") or absolute_path.startswith("//"):
            return True

        # Check file exists
        if not os.path.exists(absolute_path):
            return (False, f"File does not exist: {absolute_path}", 1)

        # Check file is a regular file
        if not os.path.isfile(absolute_path):
            return (False, f"Path is not a file: {absolute_path}", 2)

        return True

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[dict[str, Any]]:
        """Execute an LSP operation.

        Args:
            args: Tool input with operation, filePath, line, character.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with LSP operation result.
        """
        operation = args.get("operation", "")
        file_path = args.get("filePath", "")
        line = args.get("line", 1)
        character = args.get("character", 0)

        absolute_path = expand_path(file_path)
        cwd = os.getcwd()

        # Get the LSP server manager
        manager = _get_lsp_server_manager()
        if manager is None:
            output = {
                "operation": operation,
                "result": "LSP server manager not initialized. This may indicate a startup issue.",
                "filePath": file_path,
            }
            return ToolResult(data=output)

        try:
            # Check file size
            try:
                size = os.path.getsize(absolute_path)
                if size > MAX_LSP_FILE_SIZE_BYTES:
                    mb = size / 1_000_000
                    output = {
                        "operation": operation,
                        "result": f"File too large for LSP analysis ({mb:.0f}MB exceeds 10MB limit)",
                        "filePath": file_path,
                    }
                    return ToolResult(data=output)
            except OSError:
                pass

            # Open file in LSP server if not already open
            is_file_open = getattr(manager, "is_file_open", lambda _: False)
            if not is_file_open(absolute_path):
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()
                    open_file = getattr(manager, "open_file", None)
                    if open_file:
                        await open_file(absolute_path, content)
                except OSError:
                    pass

            # Map operation to LSP method and prepare params
            method, params = _get_method_and_params(
                operation, absolute_path, line, character
            )

            # Send request to LSP server
            send_request = getattr(manager, "send_request", None)
            if send_request:
                result = await send_request(absolute_path, method, params)
            else:
                result = None

            # Handle incomingCalls/outgoingCalls (two-step process)
            if operation in ("incomingCalls", "outgoingCalls"):
                if result:
                    # First result is from prepareCallHierarchy
                    call_items = result if isinstance(result, list) else [result]
                    if call_items and len(call_items) > 0:
                        call_method = (
                            "callHierarchy/incomingCalls"
                            if operation == "incomingCalls"
                            else "callHierarchy/outgoingCalls"
                        )
                        call_params = {"item": call_items[0]}
                        if send_request:
                            result = await send_request(
                                absolute_path, call_method, call_params
                            )
                        else:
                            result = None

            # Format the result
            formatted, result_count, file_count = _format_result(
                operation, result, cwd
            )

            output = {
                "operation": operation,
                "result": formatted,
                "filePath": file_path,
                "resultCount": result_count,
                "fileCount": file_count,
            }
            return ToolResult(data=output)

        except Exception as e:
            error_message = str(e)
            output = {
                "operation": operation,
                "result": f"Error performing {operation}: {error_message}",
                "filePath": file_path,
            }
            return ToolResult(data=output)

    def map_tool_result_to_tool_result_block_param(
        self,
        content: dict[str, Any],
        tool_use_id: str,
    ) -> dict[str, Any]:
        """Map LSP tool result to tool result block param."""
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": content.get("result", ""),
        }


def _get_method_and_params(
    operation: str,
    absolute_path: str,
    line: int,
    character: int,
) -> tuple[str, dict[str, Any]]:
    """Map operation to LSP method and params.

    Args:
        operation: The LSP operation name.
        absolute_path: The absolute file path.
        line: 1-based line number.
        character: 1-based character offset.

    Returns:
        Tuple of (lsp_method, params_dict).
    """
    import urllib.parse

    uri = "file://" + urllib.parse.quote(absolute_path)
    # Convert from 1-based (user-friendly) to 0-based (LSP protocol)
    position = {"line": line - 1, "character": character - 1}

    text_doc = {"textDocument": {"uri": uri}}

    if operation == "goToDefinition":
        return ("textDocument/definition", {**text_doc, "position": position})
    elif operation == "findReferences":
        return (
            "textDocument/references",
            {**text_doc, "position": position, "context": {"includeDeclaration": True}},
        )
    elif operation == "hover":
        return ("textDocument/hover", {**text_doc, "position": position})
    elif operation == "documentSymbol":
        return ("textDocument/documentSymbol", text_doc)
    elif operation == "workspaceSymbol":
        return ("workspace/symbol", {"query": ""})
    elif operation == "goToImplementation":
        return ("textDocument/implementation", {**text_doc, "position": position})
    elif operation == "prepareCallHierarchy" or operation == "incomingCalls" or operation == "outgoingCalls":
        return ("textDocument/prepareCallHierarchy", {**text_doc, "position": position})

    return ("", {})
