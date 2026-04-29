"""
EnterWorktreeTool - Create an isolated git worktree and switch into it.

This tool creates an isolated worktree (via git or configured hooks) and switches
the session into it.

Migrated from src/tools/EnterWorktreeTool/EnterWorktreeTool.ts.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claude_code.models.tool import ToolUseContext

TOOL_NAME = "EnterWorktree"

# Prompt text for the EnterWorktree tool
ENTER_WORKTREE_PROMPT = """Use this tool ONLY when the user explicitly asks to work in a worktree. This tool creates an isolated git worktree and switches the current session into it.

## When to Use

- The user explicitly says "worktree" (e.g., "start a worktree", "work in a worktree", "create a worktree", "use a worktree")

## When NOT to Use

- The user asks to create a branch, switch branches, or work on a different branch — use git commands instead
- The user asks to fix a bug or work on a feature — use normal git workflow unless they specifically mention worktrees
- Never use this tool unless the user explicitly mentions "worktree"

## Requirements

- Must be in a git repository, OR have WorktreeCreate/WorktreeRemove hooks configured in settings.json
- Must not already be in a worktree

## Behavior

- In a git repository: creates a new git worktree inside `.claude/worktrees/` with a new branch based on HEAD
- Outside a git repository: delegates to WorktreeCreate/WorktreeRemove hooks for VCS-agnostic isolation
- Switches the session's working directory to the new worktree
- Use ExitWorktree to leave the worktree mid-session (keep or remove). On session exit, if still in the worktree, the user will be prompted to keep or remove it

## Parameters

- `name` (optional): A name for the worktree. If not provided, a random name is generated.
"""


class EnterWorktreeTool:
    """Create an isolated git worktree and switch into it.

    Creates an isolated worktree (via git or configured hooks) and switches the
    session into it.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "create an isolated git worktree and switch into it"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return (
            "Creates an isolated worktree (via git or configured hooks) and "
            "switches the session into it"
        )

    @property
    def prompt_text(self) -> str:
        return ENTER_WORKTREE_PROMPT

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": (
                        "Optional name for the worktree. Each \"/\"-separated segment "
                        "may contain only letters, digits, dots, underscores, and dashes; "
                        "max 64 chars total. A random name is generated if not provided."
                    ),
                },
            },
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "worktreePath": {"type": "string"},
                "worktreeBranch": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["worktreePath", "worktreeBranch", "message"],
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Creating worktree"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return False

    def should_defer_property(self) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        name: Any = input.get("name", "")
        return str(name)

    def validate_input(
        self, input: Any, context: ToolUseContext
    ) -> tuple[bool, str, int] | bool:
        # name is optional, no validation needed
        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        message = content.get("message", "")
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": message,
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        from claude_code.bootstrap.state import set_original_cwd
        from claude_code.constants.system_prompt_sections import (
            clear_system_prompt_sections,
        )
        from claude_code.utils.claudemd import clear_memory_file_caches
        from claude_code.utils.git import find_canonical_git_root
        from claude_code.utils.session_storage import save_worktree_state
        from claude_code.utils.shell import get_cwd, set_cwd
        from claude_code.utils.worktree import (
            create_worktree_for_session,
            get_current_worktree_session,
            get_session_id,
        )

        # Validate not already in a worktree created by this session
        if get_current_worktree_session():
            return {
                "data": {
                    "error": "Already in a worktree session",
                    "worktreePath": "",
                    "worktreeBranch": None,
                    "message": "Already in a worktree session",
                },
            }

        # Resolve to main repo root so worktree creation works from within a worktree
        main_repo_root = find_canonical_git_root(get_cwd())
        if main_repo_root and main_repo_root != get_cwd():
            os.chdir(main_repo_root)
            set_cwd(main_repo_root)

        # Use provided name or generate from plan slug
        slug = args.get("name")
        if not slug:
            # Try to get plan slug from app state
            if context.get_app_state:
                app_state = context.get_app_state()
                slug = getattr(app_state, "current_plan_slug", None)
            if not slug:
                slug = _generate_random_worktree_name()

        worktree_session = await create_worktree_for_session(get_session_id(), slug)

        # Update working directory to worktree
        worktree_path = worktree_session.get("worktreePath")
        if worktree_path:
            os.chdir(worktree_path)
            set_cwd(worktree_path)
            set_original_cwd(worktree_path)

        # Persist worktree state
        save_worktree_state(worktree_session)

        # Clear cached system prompt sections so env_info recomputes with worktree context
        clear_system_prompt_sections()
        # Clear memoized caches that depend on CWD
        clear_memory_file_caches()

        branch_info = ""
        if worktree_session.get("worktreeBranch"):
            branch_info = f" on branch {worktree_session['worktreeBranch']}"

        message = (
            f"Created worktree at {worktree_path}{branch_info}. "
            f"The session is now working in the worktree. "
            f"Use ExitWorktree to leave mid-session, or exit the session to be prompted."
        )

        return {
            "data": {
                "worktreePath": worktree_path,
                "worktreeBranch": worktree_session.get("worktreeBranch"),
                "message": message,
            },
        }


def _generate_random_worktree_name() -> str:
    """Generate a random worktree name based on timestamp."""
    import time

    ts = int(time.time() * 1000) % 0xFFFFFFFF
    return f"worktree-{ts}"
