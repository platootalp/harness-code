# Phase 8: Utils Library Design Document

**Date:** 2026-04-06
**Phase:** 8 - Utils Library
**Source:** TypeScript utils in `/src/utils/`

---

## Executive Summary

The TypeScript utils library consists of approximately 120K+ lines across ~280 modules. This design document maps the key high-volume modules to their Python equivalents.

---

## 1. hooks.ts (159KB)

**Purpose:** User-defined shell commands executed at various lifecycle points.

### Key Functions to Implement in Python:

#### Hook System Core (`src_py/utils/hooks.py`)

```python
# Hook event types
class HookEvent(Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    SETUP = "Setup"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    CONFIG_CHANGE = "ConfigChange"
    CWD_CHANGED = "CwdChanged"
    FILE_CHANGED = "FileChanged"
    INSTRUCTIONS_LOADED = "InstructionsLoaded"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PERMISSION_REQUEST = "PermissionRequest"
    ELICITATION = "Elicitation"
    ELICITATION_RESULT = "ElicitationResult"

@dataclass
class HookResult:
    message: Optional[str] = None
    system_message: Optional[str] = None
    blocking_error: Optional[str] = None
    outcome: str = "success"
    prevent_continuation: bool = False
    stop_reason: Optional[str] = None
    permission_behavior: Optional[str] = None
    additional_context: Optional[str] = None
    updated_input: Optional[Dict[str, Any]] = None
    watch_paths: Optional[List[str]] = None

# Core functions
def create_base_hook_input(
    permission_mode: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_info: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create base hook input common to all hook types."""

def should_skip_hook_due_to_trust() -> bool:
    """Check if hook should be skipped due to lack of workspace trust."""

def parse_hook_output(stdout: str) -> Dict[str, Any]:
    """Parse and validate JSON hook output."""

async def exec_command_hook(
    hook: HookCommand,
    hook_event: HookEvent,
    hook_name: str,
    json_input: str,
    signal: AbortSignal,
    hook_id: str,
) -> Dict[str, Any]:
    """Execute a command-based hook using bash or PowerShell."""
```

### Hook Sub-Modules to Implement:

| Module | Purpose |
|--------|---------|
| `hooks_config_manager.py` | Hook configuration loading and management |
| `hooks_config_snapshot.py` | Snapshot of hooks config for session |
| `session_hooks.py` | Session-scoped hook storage |
| `async_hook_registry.py` | Registry for async hook responses |
| `exec_prompt_hook.py` | Prompt hook execution |
| `exec_agent_hook.py` | Agent hook execution |
| `exec_http_hook.py` | HTTP hook execution |
| `file_changed_watcher.py` | File change detection for hooks |
| `ssrf_guard.py` | SSRF protection for HTTP hooks |

---

## 2. messages.ts (193KB)

**Purpose:** Message formatting, creation, and manipulation utilities.

### Key Types (`src_py/types/message.py`)

```python
from dataclasses import dataclass, field
from typing import Union, List, Optional, Dict, Any
from enum import Enum

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    PROGRESS = "progress"
    ATTACHMENT = "attachment"

@dataclass
class UserMessage:
    type: str = "user"
    uuid: str = ""
    timestamp: str = ""
    content: Union[str, List[Dict[str, Any]]] = ""
    is_meta: bool = False
    is_visible_in_transcript_only: bool = False
    is_virtual: bool = False
    is_compact_summary: bool = False

@dataclass
class AssistantMessage:
    type: str = "assistant"
    uuid: str = ""
    timestamp: str = ""
    message: Dict[str, Any] = field(default_factory=dict)
    is_api_error_message: bool = False
    is_virtual: bool = False
```

### Message Factory Functions (`src_py/utils/messages.py`)

```python
# Constants
INTERRUPT_MESSAGE = "[Request interrupted by user]"
INTERRUPT_MESSAGE_FOR_TOOL_USE = "[Request interrupted by user for tool use]"
CANCEL_MESSAGE = "The user doesn't want to take this action right now..."
REJECT_MESSAGE = "The user doesn't want to proceed with this tool use..."
DENIAL_WORKAROUND_GUIDANCE = "IMPORTANT: You *may* attempt to accomplish..."

def create_assistant_message(
    content: Union[str, List[Dict[str, Any]]],
    usage: Optional[Dict[str, int]] = None,
    is_virtual: bool = False,
) -> AssistantMessage:
    """Create a synthetic assistant message."""

def create_user_message(
    content: Union[str, List[Dict[str, Any]]],
    is_meta: bool = False,
    is_visible_in_transcript_only: bool = False,
    is_virtual: bool = False,
    uuid: Optional[str] = None,
    timestamp: Optional[str] = None,
    origin: Optional[str] = None,
) -> UserMessage:
    """Create a user message."""

def create_progress_message(
    tool_use_id: str,
    parent_tool_use_id: str,
    data: Dict[str, Any],
) -> ProgressMessage:
    """Create a progress message for tool execution."""

def extract_tag(html: str, tag_name: str) -> Optional[str]:
    """Extract content from XML-style tags."""

def normalize_messages(
    messages: List[Message],
) -> List[NormalizedMessage]:
    """Split multi-block messages into single-block messages."""

def is_tool_use_request_message(message: Message) -> bool:
    """Type guard for tool use request messages."""

def is_tool_use_result_message(message: Message) -> bool:
    """Type guard for tool result messages."""

def get_last_assistant_message(
    messages: List[Message],
) -> Optional[AssistantMessage]:
    """Find the last assistant message in the list."""

def reorder_messages_in_ui(
    messages: List[Message],
    synthetic_streaming_tool_use_messages: List[AssistantMessage],
) -> List[Message]:
    """Reorder messages to group tool uses with their results."""

def derive_uuid(parent_uuid: str, index: int) -> str:
    """Derive deterministic UUID from parent UUID and index."""

def derive_short_message_id(uuid: str) -> str:
    """Generate 6-char base36 short ID from UUID."""
```

### Message Content Processing

```python
def extract_text_content(content: Union[str, List]) -> str:
    """Extract text from message content blocks."""

def get_user_message_text(message: UserMessage) -> str:
    """Extract text content from user message."""

def is_thinking_message(message: Message) -> bool:
    """Check if message contains thinking block."""

def is_synthetic_message(message: Message) -> bool:
    """Check if message is synthetic (interrupt/cancel/reject)."""

def is_classifier_denial(content: str) -> bool:
    """Check if tool result is a classifier denial."""

def build_yolo_rejection_message(reason: str) -> str:
    """Build rejection message for auto mode denials."""
```

---

## 3. sessionStorage.ts (180KB)

**Purpose:** Session persistence and transcript management.

### Key Classes and Functions (`src_py/utils/session_storage.py`)

```python
class Project:
    """Manages session file I/O with buffered async writes."""

    def __init__(self):
        self.session_file: Optional[str] = None
        self.current_session_title: Optional[str] = None
        self.current_session_tag: Optional[str] = None
        self.current_session_agent_name: Optional[str] = None
        self.current_session_agent_color: Optional[str] = None
        self.current_session_last_prompt: Optional[str] = None
        self._write_queues: Dict[str, List[Tuple[Entry, Callable]]] = {}
        self._flush_timer: Optional[asyncio.Timer] = None

    async def append_entry(self, entry: Entry) -> None:
        """Append entry to session file with buffering."""

    async def flush(self) -> None:
        """Flush all pending writes to disk."""

    async def remove_message_by_uuid(self, target_uuid: str) -> None:
        """Remove message from transcript by UUID (tombstoning)."""

    def re_append_session_metadata(self) -> None:
        """Re-append cached metadata to session file tail."""
```

### Session Path Management

```python
# Constants
MAX_TRANSCRIPT_READ_BYTES = 50 * 1024 * 1024  # 50MB
MAX_TOMBSTONE_REWRITE_BYTES = 50 * 1024 * 1024  # 50MB

def get_projects_dir() -> str:
    """Get the projects directory path."""

def get_transcript_path() -> str:
    """Get current session transcript path."""

def get_transcript_path_for_session(session_id: str) -> str:
    """Get transcript path for specific session."""

def get_agent_transcript_path(agent_id: str) -> str:
    """Get transcript path for subagent."""

def session_id_exists(session_id: str) -> bool:
    """Check if session file exists."""
```

### Session Metadata

```python
@dataclass
class AgentMetadata:
    agent_type: str
    worktree_path: Optional[str] = None
    description: Optional[str] = None

@dataclass
class RemoteAgentMetadata:
    task_id: str
    remote_task_type: str
    session_id: str
    title: str
    command: str
    spawned_at: int

async def write_agent_metadata(
    agent_id: str,
    metadata: AgentMetadata,
) -> None:
    """Persist agent metadata for resume."""

async def read_agent_metadata(
    agent_id: str,
) -> Optional[AgentMetadata]:
    """Read agent metadata."""
```

---

## 4. attachments.ts (127KB)

**Purpose:** File attachment handling and context injection.

### Attachment Types (`src_py/types/attachment.py`)

```python
from dataclasses import dataclass
from typing import Union, List, Optional, Dict, Any

@dataclass
class FileAttachment:
    type: str = "file"
    filename: str = ""
    content: Any = None
    truncated: bool = False
    display_path: str = ""

@dataclass
class CompactFileReferenceAttachment:
    type: str = "compact_file_reference"
    filename: str = ""
    display_path: str = ""

@dataclass
class PDFReferenceAttachment:
    type: str = "pdf_reference"
    filename: str = ""
    page_count: int = 0
    file_size: int = 0
    display_path: str = ""

@dataclass
class HookAttachment:
    type: str = ""
    hook_name: str = ""
    tool_use_id: str = ""
    hook_event: str = ""

# Union type
Attachment = Union[
    FileAttachment,
    CompactFileReferenceAttachment,
    PDFReferenceAttachment,
    AlreadyReadFileAttachment,
    EditedTextFileAttachment,
    EditedImageFileAttachment,
    DirectoryAttachment,
    SelectedLinesInIdeAttachment,
    OpenedFileInIdeAttachment,
    TodoReminderAttachment,
    TaskReminderAttachment,
    NestedMemoryAttachment,
    RelevantMemoriesAttachment,
    HookAttachment,
]
```

### Attachment Generation (`src_py/utils/attachments.py`)

```python
async def get_attachments(
    input_text: Optional[str],
    tool_use_context: ToolUseContext,
    ide_selection: Optional[IDESelection],
    queued_commands: List[QueuedCommand],
    messages: Optional[List[Message]] = None,
    query_source: Optional[str] = None,
) -> List[Attachment]:
    """
    Main attachment gathering function.
    Collects attachments from multiple sources.
    """

def get_queued_command_attachments(
    queued_commands: List[QueuedCommand],
) -> List[Attachment]:
    """Get attachments from queued commands."""

def get_date_change_attachments(
    messages: Optional[List[Message]],
) -> Optional[Attachment]:
    """Detect date changes between turns."""

def get_changed_files(context: ToolUseContext) -> List[Attachment]:
    """Get files changed since last turn."""

def get_nested_memory_attachments(
    context: ToolUseContext,
) -> List[NestedMemoryAttachment]:
    """Get nested memory file attachments."""

def get_skill_listing_attachments(
    context: ToolUseContext,
) -> Optional[Attachment]:
    """Get skill listing attachment."""

def get_plan_mode_attachments(
    messages: Optional[List[Message]],
    tool_use_context: ToolUseContext,
) -> Optional[Attachment]:
    """Get plan mode reminder attachment."""
```

---

## 5. Bash Parsing Utilities

**Location:** `/src/utils/bash/`

### Key Modules:

#### commands.ts - Command Prefix Extraction (`src_py/utils/bash/commands.py`)

```python
async def extract_command_prefix(
    command: str,
    policy_spec: str,
) -> str:
    """
    Extract command prefix for permission matching.
    Examples:
    - "cat foo.txt" -> "cat"
    - "git commit -m 'foo'" -> "git commit"
    - "git diff HEAD~1" -> "git diff"
    - "git push" -> "none"
    """

def is_help_command(command: str) -> bool:
    """Check if command is a simple --help command."""
```

#### parser.ts - Shell Command Parsing (`src_py/utils/bash/parser.py`)

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ParsedCommandData:
    root_node: 'Node'
    env_vars: List[str]
    command_node: Optional['Node']
    original_command: str

async def parse_command(
    command: str,
) -> Optional[ParsedCommandData]:
    """Parse shell command using tree-sitter."""

async def parse_command_raw(
    command: str,
) -> Union['Node', None, 'PARSE_ABORTED']:
    """Raw parse - returns AST without extraction."""

def extract_command_arguments(command_node: 'Node') -> List[str]:
    """Extract arguments from parsed command node."""
```

#### ast.ts - Security-focused AST Analysis (`src_py/utils/bash/ast_security.py`)

```python
async def parse_for_security(
    command: str,
    check_timeout_ms: int = 50,
    max_nodes: int = 50_000,
) -> Union['ParseResult', 'PARSE_ABORTED', 'COMMAND_INJECTION']:
    """
    Parse command with security checks.
    Returns:
    - ParseResult: safe command parsed
    - PARSE_ABORTED: parse timeout or too complex
    - COMMAND_INJECTION: injection detected
    """

def extract_env_vars_from_command(command: str) -> List[str]:
    """Extract env vars without full parsing."""

def check_path_constraints(command: str) -> bool:
    """Check if command paths are within allowed paths."""
```

#### shellQuote.ts - Shell Quoting (`src_py/utils/bash/shell_quote.py`)

```python
def quote(args: List[str]) -> str:
    """Quote arguments for shell safety."""

def try_parse_shell_command(
    command: str,
) -> Union['ParseResult', 'ParseFailure']:
    """Try to parse command with shell-quote."""
```

---

## 6. auth.ts (65KB)

**Purpose:** Authentication and API key management.

### API Key Management (`src_py/utils/auth.py`)

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class ApiKeySource(Enum):
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    API_KEY_HELPER = "apiKeyHelper"
    LOGIN_MANAGED_KEY = "/login managed key"
    NONE = "none"

@dataclass
class ApiKeyResult:
    key: Optional[str]
    source: ApiKeySource

def is_anthropic_auth_enabled() -> bool:
    """Check if Anthropic OAuth is enabled."""

def get_auth_token_source() -> Dict[str, Any]:
    """Get where auth token is being sourced from."""

def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from any available source."""

def get_anthropic_api_key_with_source(
    skip_retrieving_key_from_helper: bool = False,
) -> ApiKeyResult:
    """Get API key with its source."""

def has_anthropic_api_key_auth() -> bool:
    """Check if API key auth is available."""

def get_configured_api_key_helper() -> Optional[str]:
    """Get configured apiKeyHelper command."""

async def get_api_key_from_api_key_helper(
    is_non_interactive: bool,
) -> Optional[str]:
    """Execute apiKeyHelper and cache result."""

def clear_api_key_helper_cache() -> None:
    """Clear apiKeyHelper cache and increment epoch."""
```

### AWS/GCP Cloud Auth (`src_py/utils/auth_cloud.py`)

```python
async def refresh_and_get_aws_credentials() -> Optional[Dict[str, str]]:
    """Refresh AWS auth and get credentials with caching."""

def clear_aws_credentials_cache() -> None:
    """Clear AWS credentials cache."""

async def check_gcp_credentials_valid() -> bool:
    """Check if GCP credentials are valid."""

async def refresh_gcp_credentials_if_needed() -> bool:
    """Refresh GCP credentials if needed."""

def clear_gcp_credentials_cache() -> None:
    """Clear GCP credentials cache."""
```

---

## 7. Additional Utility Modules

### file.ts - File Operations (`src_py/utils/file.py`)

```python
def path_exists(path: str) -> bool:
    """Check if path exists (async)."""

def get_file_modification_time_async(path: str) -> Optional[float]:
    """Get file mtime asynchronously."""

def is_file_within_read_size_limit(
    path: str,
    max_size: int,
) -> bool:
    """Check if file is within read size limit."""
```

### path.ts - Path Utilities (`src_py/utils/path.py`)

```python
def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path."""

def sanitize_path(path: str) -> str:
    """Sanitize path for safe filesystem operations."""
```

### json.ts - JSON Utilities (`src_py/utils/json.py`)

```python
def safe_parse_json(text: str) -> Optional[Any]:
    """Safe JSON parse with error handling."""

def parse_jsonl(lines: str) -> List[Dict[str, Any]]:
    """Parse JSONL format lines."""
```

### envUtils.ts - Environment Utilities (`src_py/utils/env.py`)

```python
def get_claude_config_home_dir() -> str:
    """Get Claude config home directory."""

def is_env_truthy(value: Optional[str]) -> bool:
    """Check if env var is truthy."""

def is_bare_mode() -> bool:
    """Check if running in --bare mode."""

def is_running_on_homespace() -> bool:
    """Check if running on homespace."""
```

### memoize.ts - Memoization (`src_py/utils/memoize.py`)

```python
def memoize(func: Callable) -> Callable:
    """Simple memoization decorator."""

def memoize_with_ttl_async(
    func: Callable,
    ttl_ms: int,
) -> Callable:
    """Async memoization with TTL."""
```

### slowOperations.ts - Slow Operations (`src_py/utils/slow_operations.py`)

```python
def json_stringify(obj: Any, indent: Optional[int] = None) -> str:
    """JSON stringify with error handling."""

def json_parse(text: str) -> Any:
    """JSON parse with fallback for slow path."""
```

---

## 8. Implementation Priority

### Phase 1: Core Infrastructure
1. **types/message.py** - Message type definitions
2. **types/attachment.py** - Attachment type definitions
3. **utils/env.py** - Environment utilities
4. **utils/json.py** - JSON utilities
5. **utils/memoize.py** - Memoization

### Phase 2: Critical Path
1. **utils/auth.py** - Authentication (blocks API calls)
2. **utils/messages.py** - Message creation/parsing (core loop)
3. **utils/session_storage.py** - Session persistence

### Phase 3: Hooks System
1. **utils/hooks.py** - Hook core
2. **utils/hooks_config_manager.py** - Hook config
3. **hooks/submodules/** - Individual hook executors

### Phase 4: Attachments
1. **utils/attachments.py** - Attachment generation
2. **utils/attachments/*.py** - Individual attachment handlers

### Phase 5: Bash Parsing
1. **utils/bash/shell_quote.py** - Quoting
2. **utils/bash/commands.py** - Command extraction
3. **utils/bash/parser.py** - Parsing
4. **utils/bash/ast_security.py** - Security analysis

---

## 9. Key Design Patterns

### 1. Async/Sync Cache Pattern (from auth.ts)

```python
# SWR-style caching with background refresh
_cache: Optional[Dict[str, Any]] = None
_inflight: Optional[Promise] = None
_epoch: int = 0

async def get_value():
    if _cache and not stale():
        return _cache
    if _inflight:
        return _inflight
    _inflight = fetch()
    return _inflight
```

### 2. Singleton with Reset (from sessionStorage.ts)

```python
class Project:
    _instance: Optional['Project'] = None

    @classmethod
    def get_instance(cls) -> 'Project':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        cls._instance = None
```

### 3. Buffered Write Queue (from sessionStorage.ts)

```python
class BufferedWriter:
    _queue: List[Tuple[str, Callable]] = []
    _timer: Optional[asyncio.Timer] = None

    def write(self, data: str, resolve: Callable):
        self._queue.append((data, resolve))
        self._schedule_flush()
```

### 4. Trust Verification (from hooks.ts)

```python
def check_hook_trust() -> bool:
    """All hooks require workspace trust."""
    if is_non_interactive():
        return True  # SDK mode: trust implicit
    return check_has_trust_dialog_accepted()
```

---

## 10. File Structure

```
src_py/utils/
├── __init__.py
├── auth.py              # API key management
├── auth_cloud.py       # AWS/GCP auth
├── auth_oauth.py       # OAuth token management
├── attachments.py      # Attachment generation
├── bash/
│   ├── __init__.py
│   ├── ast_security.py
│   ├── commands.py
│   ├── heredoc.py
│   ├── parser.py
│   ├── shell_quote.py
│   └── tree_sitter_parser.py
├── env.py              # Environment utilities
├── file.py             # File operations
├── hooks.py            # Hook core
├── hooks/
│   ├── __init__.py
│   ├── async_hook_registry.py
│   ├── exec_agent_hook.py
│   ├── exec_http_hook.py
│   ├── exec_prompt_hook.py
│   ├── file_changed_watcher.py
│   ├── hooks_config_manager.py
│   ├── hooks_config_snapshot.py
│   ├── session_hooks.py
│   ├── ssrf_guard.py
│   └── ...
├── json.py             # JSON utilities
├── memoize.py          # Memoization
├── messages.py         # Message utilities
├── path.py             # Path utilities
├── session_storage.py  # Session persistence
├── slow_operations.py  # Slow operation handlers
└── ...
```

---

## 11. Testing Approach

### Unit Tests
- Each utility module should have corresponding `test_*.py` in `src_py/tests/utils/`
- Mock filesystem, subprocess, and network calls
- Test edge cases: empty inputs, malformed data, timeouts

### Integration Tests
- End-to-end hook execution tests
- Session persistence tests with actual JSONL files
- Message normalization tests with complex multi-block messages

### Property-Based Tests
- JSON round-trip for all message/attachment types
- UUID derivation consistency
- Shell quoting round-trip
