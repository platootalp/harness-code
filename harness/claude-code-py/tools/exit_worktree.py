"""
ExitWorktreeTool - Exit a worktree session and return to the original directory.

This tool exits a worktree session created by EnterWorktree and restores the
original working directory.

Migrated from src/tools/ExitWorktreeTool/ExitWorktreeTool.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claude_code.models.tool import ToolUseContext

TOOL_NAME = "ExitWorktree"

# Prompt text for the ExitWorktree tool
EXIT_WORKTREE_PROMPT = """Exit a worktree session created by EnterWorktree and return the session to the original working directory.

## Scope

This tool ONLY operates on worktrees created by EnterWorktree in this session. It will NOT touch:
- Worktrees you created manually with `git worktree add`
- Worktrees from a previous session (even if created by EnterWorktree then)
- The directory you're in if EnterWorktree was never called

If called outside an EnterWorktree session, the tool is a **no-op**: it reports that no worktree session is active and takes no action. Filesystem state is unchanged.

## When to Use

- The user explicitly asks to "exit the worktree", "leave the worktree", "go back", or otherwise end the worktree session
- Do NOT call this tool proactively — only when the user asks

## Parameters

- `action` (required): `"keep"` or `"remove"`
  - `"keep"` — leave the worktree directory and branch intact on disk. Use this if the user wants to come back to the work later, or if there are changes to preserve.
  - `"remove"` — delete the worktree directory and its branch. Use this for a clean exit when the work is done or abandoned.
- `discard_changes` (optional, default false): only meaningful with `action: "remove"`. If the worktree has uncommitted files or commits not on the original branch, the tool will REFUSE to remove it unless this is set to `true`. If the tool returns an error listing changes, confirm with the user before re-invoking with `discard_changes: true`.

## Behavior

- Restores the session's working directory to where it was before EnterWorktree
- Clears CWD-dependent caches (system prompt sections, memory files, plans directory) so the session state reflects the original directory
- If a tmux session was attached to the worktree: killed on `remove`, left running on `keep` (its name is returned so the user can reattach)
- Once exited, EnterWorktree can be called again to create a fresh worktree
"""


class ExitWorktreeTool:
    """Exit a worktree session and return to the original directory.

    Exits a worktree session created by EnterWorktree and restores the original
    working directory.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = (
        "exit a worktree session and return to the original directory"
    )
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return (
            "Exits a worktree session created by EnterWorktree and restores "
            "the original working directory"
        )

    @property
    def prompt_text(self) -> str:
        return EXIT_WORKTREE_PROMPT

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["keep", "remove"],
                    "description": (
                        '"keep" leaves the worktree and branch on disk; '
                        '"remove" deletes both.'
                    ),
                },
                "discardChanges": {
                    "type": "boolean",
                    "description": (
                        'Required true when action is "remove" and the worktree '
                        "has uncommitted files or unmerged commits. The tool will "
                        "refuse and list them otherwise."
                    ),
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["keep", "remove"]},
                "originalCwd": {"type": "string"},
                "worktreePath": {"type": "string"},
                "worktreeBranch": {"type": "string"},
                "tmuxSessionName": {"type": "string"},
                "discardedFiles": {"type": "number"},
                "discardedCommits": {"type": "number"},
                "message": {"type": "string"},
            },
            "required": ["action", "originalCwd", "worktreePath", "message"],
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Exiting worktree"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return False

    def is_destructive(self, input: Any) -> bool:
        action: Any = input.get("action")
        return bool(action == "remove")

    def to_auto_classifier_input(self, input: Any) -> str:
        action: Any = input.get("action", "")
        return str(action)

    async def validate_input(
        self, input: Any, context: ToolUseContext
    ) -> tuple[bool, str, int] | bool:
        from claude_code.utils.worktree import get_current_worktree_session

        # Check for active worktree session
        session = get_current_worktree_session()

        # If no session via mocked function, try context-based check
        if not session:
            getter = context.get_app_state
            if getter is not None:
                try:
                    app_state = getter()
                    is_in_worktree = getattr(app_state, "is_in_worktree", False)
                    if not is_in_worktree:
                        return (
                            False,
                            "No-op: there is no active EnterWorktree session to exit. "
                            "This tool only operates on worktrees created by EnterWorktree "
                            "in the current session — it will not touch worktrees created "
                            "manually or in a previous session. No filesystem changes were made.",
                            1,
                        )
                except (TypeError, AttributeError):
                    # get_app_state returned None or something invalid
                    pass
            return (
                False,
                "No-op: there is no active EnterWorktree session to exit. "
                "This tool only operates on worktrees created by EnterWorktree "
                "in the current session — it will not touch worktrees created "
                "manually or in a previous session. No filesystem changes were made.",
                1,
            )

        # Check for changes when action is remove without discard flag
        action: Any = input.get("action")
        discard_changes: Any = input.get("discardChanges")
        if action == "remove" and not discard_changes:
            worktree_path: str | None = session.path
            original_head_commit: str | None = getattr(session, "original_head_commit", None)

            if not worktree_path:
                return (
                    False,
                    f"Could not verify worktree state at {worktree_path or 'unknown'}. "
                    "Refusing to remove without explicit confirmation. "
                    'Re-invoke with discardChanges: true to proceed — '
                    'or use action: "keep" to preserve the worktree.',
                    3,
                )

            summary = await _count_worktree_changes(worktree_path, original_head_commit)

            if summary is None:
                return (
                    False,
                    f"Could not verify worktree state at {worktree_path}. "
                    "Refusing to remove without explicit confirmation. "
                    'Re-invoke with discardChanges: true to proceed — '
                    'or use action: "keep" to preserve the worktree.',
                    3,
                )

            changed_files = summary.get("changedFiles", 0)
            commits = summary.get("commits", 0)

            if changed_files > 0 or commits > 0:
                parts = []
                if changed_files > 0:
                    file_label = "file" if changed_files == 1 else "files"
                    parts.append(f"{changed_files} uncommitted {file_label}")
                if commits > 0:
                    commit_label = "commit" if commits == 1 else "commits"
                    branch_label: str | None = session.branch
                    if not branch_label:
                        getter2 = context.get_app_state
                        if getter2 is not None:
                            app_state = getter2()
                            branch_label = getattr(app_state, "worktree_branch", "the worktree branch")
                    parts.append(
                        f"{commits} {commit_label} on {branch_label or 'the worktree branch'}"
                    )
                return (
                    False,
                    f"Worktree has {parts[0]} and {parts[1]}. "
                    "Removing will discard this work permanently. "
                    "Confirm with the user, then re-invoke with discardChanges: true — "
                    'or use action: "keep" to preserve the worktree.',
                    2,
                )

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
        from claude_code.bootstrap.state import (
            get_original_cwd,
            get_project_root,
        )
        from claude_code.utils.worktree import (
            cleanup_worktree,
            get_current_worktree_session,
            keep_worktree,
            kill_tmux_session,
        )

        # Get current worktree session
        session = get_current_worktree_session()

        # Guard: should be caught by validate_input, but defend against race
        if not session:
            # Try to use context-based state
            if context.get_app_state:
                app_state = context.get_app_state()
                is_in_worktree = getattr(app_state, "is_in_worktree", False)
                if not is_in_worktree:
                    return {
                        "data": {
                            "action": args.get("action", "keep"),
                            "originalCwd": "",
                            "worktreePath": "",
                            "worktreeBranch": None,
                            "tmuxSessionName": None,
                            "message": "Not in a worktree session",
                        },
                    }

                original_cwd = getattr(app_state, "original_cwd", "") or ""
                worktree_path = getattr(app_state, "worktree_path", "")
                worktree_branch = getattr(app_state, "worktree_branch", None)
                tmux_session_name = getattr(app_state, "tmux_session_name", None)
                original_head_commit = getattr(
                    app_state, "original_head_commit", None
                )
            else:
                return {
                    "data": {
                        "action": args.get("action", "keep"),
                        "originalCwd": "",
                        "worktreePath": "",
                        "worktreeBranch": None,
                        "tmuxSessionName": None,
                        "message": "Not in a worktree session",
                    },
                }
        else:
            original_cwd = session.original_cwd
            worktree_path = session.path
            worktree_branch = session.branch
            tmux_session_name = getattr(session, "tmux_session_name", None)
            original_head_commit = getattr(session, "original_head_commit", None)

        # Determine if project root was set to the worktree
        project_root_is_worktree = get_project_root() == get_original_cwd()

        # Re-count at execution time for accurate analytics and messaging
        summary = await _count_worktree_changes(worktree_path, original_head_commit)
        changed_files = summary.get("changedFiles", 0) if summary else 0
        commits = summary.get("commits", 0) if summary else 0

        action = args.get("action", "keep")

        if action == "keep":
            await keep_worktree()
            _restore_session_to_original_cwd(
                original_cwd,
                project_root_is_worktree,
                context,
            )

            tmux_note = ""
            if tmux_session_name:
                tmux_note = (
                    f" Tmux session {tmux_session_name} is still running; "
                    f"reattach with: tmux attach -t {tmux_session_name}"
                )

            branch_note = ""
            if worktree_branch:
                branch_note = f" on branch {worktree_branch}"

            message = (
                f"Exited worktree. Your work is preserved at {worktree_path}"
                f"{branch_note}. Session is now back in {original_cwd}.{tmux_note}"
            )

            return {
                "data": {
                    "action": "keep",
                    "originalCwd": original_cwd,
                    "worktreePath": worktree_path,
                    "worktreeBranch": worktree_branch,
                    "tmuxSessionName": tmux_session_name,
                    "message": message,
                },
            }

        # action == 'remove'
        if tmux_session_name:
            await kill_tmux_session(tmux_session_name)

        await cleanup_worktree()
        _restore_session_to_original_cwd(
            original_cwd,
            project_root_is_worktree,
            context,
        )

        discard_parts = []
        if commits > 0:
            commit_label = "commit" if commits == 1 else "commits"
            discard_parts.append(f"{commits} {commit_label}")
        if changed_files > 0:
            file_label = "file" if changed_files == 1 else "files"
            discard_parts.append(f"{changed_files} uncommitted {file_label}")
        discard_note = f" Discarded {' and '.join(discard_parts)}." if discard_parts else ""

        message = (
            f"Exited and removed worktree at {worktree_path}.{discard_note} "
            f"Session is now back in {original_cwd}."
        )

        return {
            "data": {
                "action": "remove",
                "originalCwd": original_cwd,
                "worktreePath": worktree_path,
                "worktreeBranch": worktree_branch,
                "discardedFiles": changed_files,
                "discardedCommits": commits,
                "message": message,
            },
        }


async def _count_worktree_changes(
    worktree_path: str | None,
    original_head_commit: str | None,
) -> dict[str, int] | None:
    """Count changes in a worktree relative to its original state.

    Returns None when state cannot be reliably determined — callers must
    treat None as "unknown, assume unsafe" (fail-closed).

    Returns None when:
    - git status or rev-list exit non-zero (lock file, corrupt index, bad ref)
    - originalHeadCommit is undefined but git status succeeded (worktree wraps
      a hook-based system without a git baseline commit)
    """
    from claude_code.utils.exec_file_no_throw import exec_file_no_throw_async

    if not worktree_path:
        return None

    # Check git status
    status = await exec_file_no_throw_async(
        "git",
        ["-C", worktree_path, "status", "--porcelain"],
    )
    if status is None or status.get("code") != 0:
        return None

    # Count changed files
    stdout = status.get("stdout", "")
    lines = [line for line in stdout.split("\n") if line.strip()]
    changed_files = len(lines)

    if not original_head_commit:
        # git status succeeded -> this is a git repo, but without a baseline
        # commit we cannot count commits. Fail-closed rather than claim 0.
        return None

    # Count commits since original head
    rev_list = await exec_file_no_throw_async(
        "git",
        [
            "-C",
            worktree_path,
            "rev-list",
            "--count",
            f"{original_head_commit}..HEAD",
        ],
    )
    if rev_list is None or rev_list.get("code") != 0:
        return None

    commits_str = rev_list.get("stdout", "").strip()
    commits = int(commits_str) if commits_str.isdigit() else 0

    return {"changedFiles": changed_files, "commits": commits}


def _restore_session_to_original_cwd(
    original_cwd: str,
    project_root_is_worktree: bool,
    context: ToolUseContext,
) -> None:
    """Restore session state to reflect the original directory.

    This is the inverse of the session-level mutations in EnterWorktreeTool.call().

    keepWorktree()/cleanupWorktree() handle process.chdir and currentWorktreeSession;
    this handles everything above the worktree utility layer.
    """
    from claude_code.bootstrap.state import (
        set_original_cwd,
        set_project_root,
    )
    from claude_code.constants.system_prompt_sections import (
        clear_system_prompt_sections,
    )
    from claude_code.utils.claudemd import clear_memory_file_caches
    from claude_code.utils.hooks.hooks_config_snapshot import (
        update_hooks_config_snapshot,
    )
    from claude_code.utils.session_storage import save_worktree_state
    from claude_code.utils.shell import set_cwd

    set_cwd(original_cwd)
    # EnterWorktree sets originalCwd to the *worktree* path (intentional — see
    # state.ts getProjectRoot comment). Reset to the real original.
    set_original_cwd(original_cwd)
    # --worktree startup sets projectRoot to the worktree; mid-session
    # EnterWorktreeTool does not. Only restore when it was actually changed.
    if project_root_is_worktree:
        set_project_root(original_cwd)
        # setup.ts's --worktree block called updateHooksConfigSnapshot() to re-read
        # hooks from the worktree. Restore symmetrically.
        update_hooks_config_snapshot()

    save_worktree_state(None)
    clear_system_prompt_sections()
    clear_memory_file_caches()
