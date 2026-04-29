# Claude Code Python Migration: Development Task List

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement tasks task-by-task.

**Goal:** Complete Python migration of TypeScript `src/` (~512K lines, 55 subdirectories)

**Status Legend:**
- `[P]` = Pending
- `[IP]` = In Progress
- `[C]` = Completed
- `[B]` = Blocked

---

## Phase 0: Infrastructure (Foundation)

### Task 0.1: Project Configuration
- **Status:** [C]
- **Deliverables:**
  - `pyproject.toml` - Project configuration
  - `src_py/__init__.py` - Package init
- **Verification:** `python -c "import src_py"` works

### Task 0.2: Core Data Models
- **Status:** [C]
- **Deliverables:**
  - `src_py/models/message.py` - Message, Role, Content types
  - `src_py/models/tool.py` - Tool, ToolResult, ToolUse
  - `src_py/models/task.py` - Task, TaskStatus
  - `src_py/models/session.py` - Session, SessionState
- **Verification:** All Pydantic models validate correctly

### Task 0.3: State Store (Observable Store)
- **Status:** [C]
- **Deliverables:**
  - `src_py/state/store.py` - Observable Store implementation
  - `src_py/state/hooks.py` - State hooks
  - `src_py/state/app_state.py` - AppState
- **Verification:** State subscriptions trigger on changes

### Task 0.4: API Client (httpx + streaming)
- **Status:** [C]
- **Deliverables:**
  - `src_py/api/client.py` - Anthropic API client
  - Multi-provider support (Direct, AWS Bedrock, Azure Foundry, Google Vertex)
- **Verification:** API calls succeed with streaming responses

---

## Phase 1: Query Engine

### Task 1.1: QueryEngine Implementation
- **Status:** [C]
- **Deliverables:**
  - `src_py/engine/engine.py` - QueryEngine class
  - `src_py/engine/pipeline.py` - AsyncGenerator pipeline
  - `src_py/engine/context.py` - Context compression
- **Verification:** `QueryEngine.query()` returns streaming events

### Task 1.2: Tool Registry
- **Status:** [C]
- **Deliverables:**
  - `src_py/tools/registry.py` - Tool registry
  - `src_py/tools/orchestration.py` - Tool orchestration
- **Verification:** Tools register and execute correctly

### Task 1.3: Context Compression
- **Status:** [C]
- **Deliverables:**
  - `src_py/context/compression.py` - Context compression logic
  - `src_py/context/manager.py` - Context manager
- **Verification:** Long conversations compress correctly

---

## Phase 2: Tools System

### Task 2.1: BaseTool Abstract Class
- **Status:** [C]
- **Deliverables:**
  - `src_py/tools/base.py` - BaseTool abstract class
  - Tool execution protocol
- **Verification:** All tools inherit from BaseTool

### Task 2.2: Core Tools (Batch 1)
- **Status:** [C]
- **Deliverables:**
  - `src_py/tools/bash_tool.py` - BashTool
  - `src_py/tools/file_read_tool.py` - FileReadTool
  - `src_py/tools/file_edit_tool.py` - FileEditTool
  - `src_py/tools/glob_tool.py` - GlobTool
  - `src_py/tools/grep_tool.py` - GrepTool
- **Verification:** Each tool executes and returns results

### Task 2.3: Core Tools (Batch 2)
- **Status:** [C]
- **Deliverables:**
  - `src_py/tools/web_fetch_tool.py` - WebFetchTool
  - `src_py/tools/task_create_tool.py` - TaskCreateTool
  - `src_py/tools/agent_call_tool.py` - AgentCallTool
- **Verification:** Tools work with orchestrator

### Task 2.4: Remaining Tools (35+ tools)
- **Status:** [P]
- **Blocked By:** Task 2.3
- **Deliverables:**
  - `src_py/tools/write_tool.py` - WriteTool
  - `src_py/tools/mkdir_tool.py` - MkdirTool
  - `src_py/tools/rm_tool.py` - RmTool
  - `src_py/tools/cp_tool.py` - CpTool
  - `src_py/tools/mv_tool.py` - MvTool
  - `src_py/tools/find_tool.py` - FindTool
  - `src_py/tools/read_multiple_tool.py` - ReadMultipleTool
  - `src_py/tools/notebook_edit_tool.py` - NotebookEditTool
  - `src_py/tools/notebook_read_tool.py` - NotebookReadTool
  - `src_py/tools/pdf_read_tool.py` - PDFReadTool
  - `src_py/tools/image_gen_tool.py` - ImageGenTool
  - `src_py/tools/memory_search_tool.py` - MemorySearchTool
  - `src_py/tools/memory_add_tool.py` - MemoryAddTool
  - `src_py/tools/芸る_...` - All remaining tools from TypeScript
- **Verification:** All TypeScript tools have Python equivalents

---

## Phase 3: Commands System

### Task 3.1: BaseCommand + Registry
- **Status:** [C]
- **Deliverables:**
  - `src_py/commands/base.py` - BaseCommand
  - `src_py/commands/registry.py` - Command registry
- **Verification:** Commands register and execute

### Task 3.2: Core Commands (Batch 1)
- **Status:** [C]
- **Deliverables:**
  - `src_py/commands/commit.py` - /commit command
  - `src_py/commands/branch.py` - /branch command
  - `src_py/commands/config.py` - /config command
  - `src_py/commands/builtin_commands.py` - Built-in commands
- **Verification:** Slash commands execute correctly

### Task 3.3: Core Commands (Batch 2)
- **Status:** [C]
- **Deliverables:**
  - `src_py/cli/builtin_commands.py` - CLI built-in commands
  - `src_py/cli/command_parser.py` - Command parser
- **Verification:** Help system works

### Task 3.4: Remaining Commands (60+ commands)
- **Status:** [P]
- **Blocked By:** Task 3.3
- **Deliverables:**
  - `src_py/commands/add_dir.py` - /add-dir command
  - `src_py/commands/agent.py` - /agent command
  - `src_py/commands/ask.py` - /ask command
  - `src_py/commands/attach.py` - /attach command
  - `src_py/commands/backlog.py` - /backlog command
  - `src_py/commands/benefit.py` - /benefit command
  - `src_py/commands/bug.py` - /bug command
  - `src_py/commands/capacity.py` - /capacity command
  - `src_py/commands/clear.py` - /clear command
  - `src_py/commands/compact.py` - /compact command
  - `src_py/commands/debug.py` - /debug command
  - `src_py/commands/diff.py` - /diff command
  - `src_py/commands/enhance.py` - /enhance command
  - `src_py/commands/exit.py` - /exit command
  - `src_py/commands/export.py` - /export command
  - `src_py/commands/feat.py` - /feat command
  - `src_py/commands/feedback.py` - /feedback command
  - `src_py/commands/health.py` - /health command
  - `src_py/commands/help.py` - /help command
  - `src_py/commands/history.py` - /history command
  - `src_py/commands/ignore.py` - /ignore command
  - `src_py/commands/import.py` - /import command
  - `src_py/commands/invocations.py` - /invocations command
  - `src_py/commands/jump.py` - /jump command
  - `src_py/commands/kill.py` - /kill command
  - `src_py/commands/labels.py` - /labels command
  - `src_py/commands/logs.py` - /logs command
  - `src_py/commands/mcp.py` - /mcp command
  - `src_py/commands/model.py` - /model command
  - `src_py/commands/modify.py` - /modify command
  - `src_py/commands/ndc.py` - /ndc command
  - `src_py/commands/observer.py` - /observer command
  - `src_py/commands/operation.py` - /operation command
  - `src_py/commands/opts.py` - /opts command
  - `src_py/commands/permission.py` - /permission command
  - `src_py/commands/pm.py` - /pm command
  - `src_py/commands/praise.py` - /praise command
  - `src_py/commands/quiet.py` - /quiet command
  - `src_py/commands/redo.py` - /redo command
  - `src_py/commands/refactor.py` - /refactor command
  - `src_py/commands/reject.py` - /reject command
  - `src_py/commands/release.py` - /release command
  - `src_py/commands/remove.py` - /remove command
  - `src_py/commands/report.py` - /report command
  - `src_py/commands/resume.py` - /resume command
  - `src_py/commands/retry.py` - /retry command
  - `src_py/commands/review.py` - /review command
  - `src_py/commands/rollback.py` - /rollback command
  - `src_py/commands/sampler.py` - /sampler command
  - `src_py/commands/scm.py` - /scm command
  - `src_py/commands/score.py` - /score command
  - `src_py/commands/scrum.py` - /scrum command
  - `src_py/commands/search.py` - /search command
  - `src_py/commands/select.py` - /select command
  - `src_py/commands/skim.py` - /skim command
  - `src_py/commands/spell.py` - /spell command
  - `src_py/commands/start.py` - /start command
  - `src_py/commands/status.py` - /status command
  - `src_py/commands/stop.py` - /stop command
  - `src_py/commands/summary.py` - /summary command
  - `src_py/commands/task.py` - /task command
  - `src_py/commands/team.py` - /team command
  - `src_py/commands/test.py` - /test command
  - `src_py/commands/think.py` - /think command
  - `src_py/commands/threads.py` - /threads command
  - `src_py/commands/token.py` - /token command
  - `src_py/commands/undo.py` - /undo command
  - `src_py/commands/verbose.py` - /verbose command
  - `src_py/commands/version.py` - /version command
  - `src_py/commands/watch.py` - /watch command
  - `src_py/commands/workflow.py` - /workflow command
- **Verification:** All TypeScript commands have Python equivalents

---

## Phase 4: CLI + REPL (Textual)

### Task 4.1: Textual App Foundation
- **Status:** [C]
- **Deliverables:**
  - `src_py/cli/app.py` - Textual App class
  - `src_py/screens/repl.py` - REPL screen
  - `src_py/cli/output_handler.py` - Output handling
  - `src_py/cli/status_bar.py` - Status bar
- **Verification:** Textual app starts and displays

### Task 4.2: REPL Input Handling
- **Status:** [C]
- **Deliverables:**
  - `src_py/cli/command_parser.py` - Slash command parsing
  - Input history navigation
  - Multi-line input support
- **Verification:** User can type and execute commands

### Task 4.3: Output Rendering
- **Status:** [C]
- **Deliverables:**
  - `src_py/cli/output_handler.py` - Stream output to screen
  - Syntax highlighting
  - Error formatting
- **Verification:** Output displays correctly with styling

### Task 4.4: UI Components (Textual)
- **Status:** [P]
- **Blocked By:** Task 4.1
- **Deliverables:**
  - `src_py/cli/components/dialog.py` - Dialog widget
  - `src_py/cli/components/pane.py` - Pane widget
  - `src_py/cli/components/tabs.py` - Tabs widget
  - `src_py/cli/components/divider.py` - Divider widget
  - `src_py/cli/components/text.py` - Styled text widget
  - `src_py/cli/components/box.py` - Box layout widget
  - `src_py/cli/components/message_row.py` - Message row widget
  - `src_py/cli/components/virtual_list.py` - Virtual message list
  - `src_py/cli/components/prompt_input.py` - Prompt input widget
  - `src_py/cli/components/fuzzy_picker.py` - Fuzzy picker
- **Verification:** Components render and respond to input

### Task 4.5: Dialog System
- **Status:** [P]
- **Blocked By:** Task 4.4
- **Deliverables:**
  - `src_py/cli/dialogs/global_search.py` - Global search dialog
  - `src_py/cli/dialogs/history_search.py` - History search dialog
  - `src_py/cli/dialogs/bridge.py` - Bridge dialog
  - `src_py/cli/dialogs/mcp_approval.py` - MCP server approval
  - `src_py/cli/dialogs/mcp_select.py` - MCP server selection
  - `src_py/cli/dialogs/auto_mode.py` - Auto mode opt-in
  - `src_py/cli/dialogs/cost_threshold.py` - Cost threshold warning
  - `src_py/cli/dialogs/exit_flow.py` - Exit confirmation
  - `src_py/cli/dialogs/idle_return.py` - Idle return dialog
  - `src_py/cli/dialogs/background_tasks.py` - Background tasks
  - `src_py/cli/dialogs/teams.py` - Team management
- **Verification:** All dialogs open and function correctly

### Task 4.6: State Synchronization (UI)
- **Status:** [C]
- **Deliverables:**
  - `src_py/state_sync/syncer.py` - State synchronization
  - `src_py/state_sync/publisher.py` - State publisher
  - `src_py/state_sync/subscriber.py` - State subscriber
- **Verification:** UI reflects state changes in real-time

---

## Phase 5: Bridge System

### Task 5.1: Bridge Protocol
- **Status:** [P]
- **Deliverables:**
  - `src_py/bridge/protocol.py` - Bridge protocol定义
  - `src_py/bridge/transport.py` - Transport abstraction
- **Verification:** Protocol messages serialize/deserialize

### Task 5.2: VS Code Extension Support
- **Status:** [P]
- **Blocked By:** Task 5.1
- **Deliverables:**
  - `src_py/bridge/vscode.py` - VS Code extension bridge
  - WebSocket transport for VS Code
- **Verification:** VS Code extension connects and communicates

### Task 5.3: JetBrains Plugin Support
- **Status:** [P]
- **Blocked By:** Task 5.1
- **Deliverables:**
  - `src_py/bridge/jetbrains.py` - JetBrains plugin bridge
  - Protocol implementation for JetBrains
- **Verification:** JetBrains plugin connects and communicates

---

## Phase 6: Services Layer

### Task 6.1: API Client Enhancement
- **Status:** [C]
- **Deliverables:**
  - `src_py/api/client.py` - Enhanced API client
  - Rate limiting
  - Retry logic
  - Error handling
- **Verification:** API calls handle all error cases

### Task 6.2: MCP Client
- **Status:** [C]
- **Deliverables:**
  - `src_py/mcp/client.py` - MCP client
  - `src_py/mcp/registry.py` - MCP server registry
  - `src_py/mcp/types.py` - MCP type definitions
  - `src_py/mcp/config.py` - MCP configuration
- **Verification:** MCP servers connect and tools invoke

### Task 6.3: MCP Server
- **Status:** [C]
- **Deliverables:**
  - `src_py/mcp/server.py` - MCP server implementation
  - Tool exposure via MCP protocol
- **Verification:** Claude Code exposes tools via MCP

### Task 6.4: Session Storage
- **Status:** [C]
- **Deliverables:**
  - `src_py/session/manager.py` - Session manager
  - `src_py/session/models.py` - Session models
  - `src_py/lib/models.py` - Shared library models
- **Verification:** Sessions persist and resume correctly

### Task 6.5: Security Rules
- **Status:** [C]
- **Deliverables:**
  - `src_py/security/rules.py` - Security rule engine
  - `src_py/security/budgets.py` - Budget enforcement
  - `src_py/security/layer.py` - Security layer
- **Verification:** Security rules block violations

---

## Phase 7: UI Components (React → Textual)

### Task 7.1: Design System Components
- **Status:** [P]
- **Deliverables:**
  - `src_py/ui/design_system/dialog.py`
  - `src_py/ui/design_system/pane.py`
  - `src_py/ui/design_system/tabs.py`
  - `src_py/ui/design_system/divider.py`
  - `src_py/ui/design_system/text.py`
  - `src_py/ui/design_system/box.py`
  - `src_py/ui/design_system/byline.py`
  - `src_py/ui/design_system/keyboard_shortcut.py`
  - `src_py/ui/design_system/themed.py`
  - `src_py/ui/design_system/list_item.py`
  - `src_py/ui/design_system/fuzzy_picker.py`
  - `src_py/ui/design_system/loading_state.py`
  - `src_py/ui/design_system/progress_bar.py`
  - `src_py/ui/design_system/status_icon.py`
  - `src_py/ui/design_system/ratchet.py`
- **Verification:** All components render with correct styling

### Task 7.2: PromptInput Components
- **Status:** [P]
- **Blocked By:** Task 7.1
- **Deliverables:**
  - `src_py/ui/prompt_input/main.py` - PromptInput component
  - `src_py/ui/prompt_input/footer.py` - Footer with hints
  - `src_py/ui/prompt_input/suggestions.py` - Slash suggestions
  - `src_py/ui/prompt_input/mode_indicator.py` - Vim mode indicator
  - `src_py/ui/prompt_input/queued_commands.py` - Queued commands
  - `src_py/ui/prompt_input/stash_notice.py` - Stash notice
  - `src_py/ui/prompt_input/help_menu.py` - Help overlay
  - `src_py/ui/prompt_input/shimmered_input.py` - Animated input
- **Verification:** Prompt input handles all user interactions

### Task 7.3: Message Components
- **Status:** [P]
- **Blocked By:** Task 7.1
- **Deliverables:**
  - `src_py/ui/messages/container.py` - Messages container
  - `src_py/ui/messages/virtual_list.py` - Virtual message list
  - `src_py/ui/messages/row.py` - Message row wrapper
  - `src_py/ui/messages/assistant_text.py` - Assistant text
  - `src_py/ui/messages/assistant_tool_use.py` - Tool calls
  - `src_py/ui/messages/assistant_thinking.py` - Thinking blocks
  - `src_py/ui/messages/user_prompt.py` - User input
  - `src_py/ui/messages/system_text.py` - System notifications
  - `src_py/ui/messages/attachment.py` - Attachments
  - `src_py/ui/messages/selector.py` - Message selector
- **Verification:** Messages render with virtualization

### Task 7.4: Layout Components
- **Status:** [P]
- **Blocked By:** Task 7.1
- **Deliverables:**
  - `src_py/ui/layout/fullscreen.py` - Fullscreen layout
  - `src_py/ui/layout/scroll_box.py` - Scrollable container
  - `src_py/ui/layout/status_notices.py` - Status notices
  - `src_py/ui/layout/bottom_slot.py` - Bottom pinned content
  - `src_py/ui/layout/modal_slot.py` - Modal overlay slot
  - `src_py/ui/layout/bottom_float.py` - Floating bottom content
- **Verification:** Layout composes correctly

---

## Phase 8: Utils Library

### Task 8.1: Message Utilities
- **Status:** [C]
- **Deliverables:**
  - `src_py/utils/messages.py` - Message creation/parsing
  - Factory functions for all message types
  - UUID derivation utilities
- **Verification:** Message utilities handle all edge cases

### Task 8.2: Attachment Utilities
- **Status:** [P]
- **Deliverables:**
  - `src_py/types/attachment.py` - Attachment type definitions
  - `src_py/utils/attachments.py` - Attachment generation
  - `src_py/utils/attachment_handlers.py` - Individual handlers
- **Verification:** Attachments generate correctly for all sources

### Task 8.3: Session Storage Utilities
- **Status:** [C]
- **Deliverables:**
  - `src_py/utils/session_storage.py` - Project singleton
  - Buffered async writes
  - JSONL transcript handling
- **Verification:** Session data persists correctly

### Task 8.4: Bash Parsing Utilities
- **Status:** [P]
- **Deliverables:**
  - `src_py/utils/bash/commands.py` - Command prefix extraction
  - `src_py/utils/bash/parser.py` - Shell parsing
  - `src_py/utils/bash/ast_security.py` - Security analysis
  - `src_py/utils/bash/shell_quote.py` - Shell quoting
  - `src_py/utils/bash/heredoc.py` - Heredoc handling
  - `src_py/utils/bash/tree_sitter_parser.py` - Tree-sitter integration
- **Verification:** Commands parse correctly with security checks

### Task 8.5: Auth Utilities
- **Status:** [C]
- **Deliverables:**
  - `src_py/utils/auth.py` - API key management
  - `src_py/utils/auth_cloud.py` - AWS/GCP auth
  - `src_py/utils/auth_oauth.py` - OAuth token management
- **Verification:** Auth handles all providers correctly

### Task 8.6: Hook Utilities
- **Status:** [C]
- **Deliverables:**
  - `src_py/utils/hooks.py` - Hook core
  - `src_py/utils/hooks_config_manager.py` - Config management
  - `src_py/utils/hooks_config_snapshot.py` - Session snapshots
  - `src_py/utils/session_hooks.py` - Session hooks
  - `src_py/utils/async_hook_registry.py` - Async registry
  - `src_py/utils/exec_prompt_hook.py` - Prompt hooks
  - `src_py/utils/exec_agent_hook.py` - Agent hooks
  - `src_py/utils/exec_http_hook.py` - HTTP hooks
  - `src_py/utils/file_changed_watcher.py` - File change detection
  - `src_py/utils/ssrf_guard.py` - SSRF protection
- **Verification:** Hooks execute with correct conditions

### Task 8.7: Additional Utilities
- **Status:** [P]
- **Deliverables:**
  - `src_py/utils/file.py` - File operations
  - `src_py/utils/path.py` - Path utilities
  - `src_py/utils/json.py` - JSON utilities
  - `src_py/utils/env.py` - Environment utilities
  - `src_py/utils/memoize.py` - Memoization
  - `src_py/utils/slow_operations.py` - Slow operation handlers
- **Verification:** All utilities work correctly

---

## Phase 9: Hooks + State Management

### Task 9.1: Hook System Implementation
- **Status:** [C]
- **Deliverables:**
  - All 25 hook event types implemented
  - Command, prompt, HTTP, and agent hook types
  - Hook matching and filtering
- **Verification:** All hook types trigger correctly

### Task 9.2: State Management Patterns
- **Status:** [C]
- **Deliverables:**
  - Observable store pattern
  - State subscriptions
  - State persistence
- **Verification:** State changes propagate correctly

---

## Phase 10: Skills System

### Task 10.1: Skills Registry
- **Status:** [C]
- **Deliverables:**
  - `src_py/skills/registry.py` - SkillRegistry
  - `src_py/skills/parser.py` - SKILL.md parsing
  - Progressive loading
- **Verification:** Skills load and execute correctly

### Task 10.2: Skill Executor
- **Status:** [C]
- **Deliverables:**
  - `src_py/skills/executor.py` - SkillExecutor
  - Allowed-tools boundary checking
  - Resource limits (timeout, memory)
- **Verification:** Skills respect allowed-tools

### Task 10.3: Bundled Skills
- **Status:** [P]
- **Blocked By:** Task 10.1
- **Deliverables:**
  - `src_py/skills/bundled/update_config.py`
  - `src_py/skills/bundled/keybindings.py`
  - `src_py/skills/bundled/verify.py`
  - `src_py/skills/bundled/debug.py`
  - `src_py/skills/bundled/lorem_ipsum.py`
  - `src_py/skills/bundled/skillify.py`
  - `src_py/skills/bundled/remember.py`
  - `src_py/skills/bundled/simplify.py`
  - `src_py/skills/bundled/batch.py`
  - `src_py/skills/bundled/stuck.py`
- **Verification:** Bundled skills work correctly

### Task 10.4: Dynamic Skill Discovery
- **Status:** [P]
- **Blocked By:** Task 10.1
- **Deliverables:**
  - Dynamic skill discovery during file operations
  - Path-based conditional activation
  - Skill caching and invalidation
- **Verification:** Skills discover correctly

### Task 10.5: Forked Execution
- **Status:** [P]
- **Blocked By:** Task 10.2
- **Deliverables:**
  - Sub-agent execution for forked skills
  - Separate token budget
  - Context isolation
- **Verification:** Forked skills run independently

---

## Phase 11: Plugins System

### Task 11.1: Plugin Base Classes
- **Status:** [C]
- **Deliverables:**
  - `src_py/plugins/base.py` - BasePlugin, PluginManifest
  - `src_py/plugins/registry.py` - PluginRegistry
  - `src_py/plugins/manifest.py` - Manifest parsing
- **Verification:** Plugin system initializes

### Task 11.2: Hook Manager
- **Status:** [C]
- **Deliverables:**
  - `src_py/plugins/hooks/manager.py` - HookManager
  - `src_py/plugins/hooks/definitions.py` - Hook definitions
  - All 25 hook event implementations
- **Verification:** Hooks trigger for plugins

### Task 11.3: Plugin Operations
- **Status:** [C]
- **Deliverables:**
  - `src_py/plugins/operations.py` - PluginOperations
  - Install/uninstall/enable/disable
  - Configuration management
- **Verification:** Plugin lifecycle works

### Task 11.4: Builtin Plugin Registry
- **Status:** [C]
- **Deliverables:**
  - `src_py/plugins/builtin.py` - BuiltinPluginRegistry
  - Built-in plugin registration
- **Verification:** Built-in plugins load

### Task 11.5: Plugin Loader
- **Status:** [P]
- **Blocked By:** Task 11.1
- **Deliverables:**
  - `src_py/plugins/loader.py` - PluginLoader
  - npm/pip/git/github source loading
  - Version caching
- **Verification:** Plugins load from all sources

---

## Phase 12: Testing + Polish

### Task 12.1: Unit Tests (Core)
- **Status:** [C]
- **Deliverables:**
  - `src_py/tests/test_models.py`
  - `src_py/tests/test_state_store.py`
  - `src_py/tests/test_dag.py`
  - `src_py/tests/test_tools.py`
  - `src_py/tests/test_orchestrator.py`
- **Verification:** All tests pass

### Task 12.2: Integration Tests
- **Status:** [P]
- **Blocked By:** Phase 1-11 completion
- **Deliverables:**
  - API integration tests
  - Tool execution tests
  - Command execution tests
  - Session persistence tests
  - MCP integration tests
- **Verification:** Integration tests pass

### Task 12.3: Performance Testing
- **Status:** [P]
- **Blocked By:** Task 12.2
- **Deliverables:**
  - Startup time benchmarks
  - Memory usage profiling
  - Tool execution latency
  - Context compression efficiency
- **Verification:** Performance meets targets

### Task 12.4: Documentation
- **Status:** [P]
- **Blocked By:** All implementation
- **Deliverables:**
  - API documentation
  - Command help text
  - Configuration guide
  - Migration guide from TypeScript
- **Verification:** Documentation is complete

---

## Summary Statistics

| Phase | Tasks | Completed | Pending | Blocked |
|-------|-------|-----------|---------|---------|
| Phase 0: Infrastructure | 4 | 4 | 0 | 0 |
| Phase 1: Query Engine | 3 | 3 | 0 | 0 |
| Phase 2: Tools System | 4 | 3 | 1 | 0 |
| Phase 3: Commands System | 4 | 3 | 1 | 0 |
| Phase 4: CLI + REPL | 6 | 4 | 2 | 0 |
| Phase 5: Bridge System | 3 | 0 | 3 | 0 |
| Phase 6: Services Layer | 5 | 5 | 0 | 0 |
| Phase 7: UI Components | 4 | 0 | 4 | 0 |
| Phase 8: Utils Library | 7 | 3 | 4 | 0 |
| Phase 9: Hooks + State | 2 | 2 | 0 | 0 |
| Phase 10: Skills System | 5 | 2 | 3 | 0 |
| Phase 11: Plugins System | 5 | 4 | 1 | 0 |
| Phase 12: Testing + Polish | 4 | 1 | 3 | 0 |
| **Total** | **56** | **35** (62%) | **21** (38%) | **0** |

---

## Execution Recommendation

**Option 1: Subagent-Driven (Recommended)**
- Dispatch fresh subagent per phase
- Review between phases
- Fast iteration

**Option 2: Inline Execution**
- Batch execution with checkpoints
- Use superpowers:executing-plans skill
