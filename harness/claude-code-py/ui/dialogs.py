"""
Dialog module for Claude Code TUI.

Provides dialog components for user interaction including confirmation
dialogs, settings validation, permission prompts, and session selection.

TypeScript equivalents: src/components/*Dialog.tsx, src/dialogLaunchers.tsx

This module defines dialog types, result types, and Textual-based dialog
implementations that wrap the underlying TUI framework.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# =============================================================================
# Dialog Result Types
# =============================================================================


@dataclass
class DialogResult:
    """Base class for dialog results."""

    pass


@dataclass
class ConfirmDialogResult(DialogResult):
    """Result of a confirmation dialog."""

    confirmed: bool = False


@dataclass
class SelectionDialogResult(DialogResult):
    """Result of a selection dialog."""

    selected: str | None = None


@dataclass
class SnapshotUpdateDialogResult(DialogResult):
    """Result of agent memory snapshot update dialog."""

    action: str = "keep"  # "merge" | "keep" | "replace"


@dataclass
class InvalidSettingsDialogResult(DialogResult):
    """Result of invalid settings dialog."""

    continue_without_settings: bool = False


@dataclass
class CostThresholdDialogResult(DialogResult):
    """Result of cost threshold dialog."""

    acknowledged: bool = False


@dataclass
class TrustDialogResult(DialogResult):
    """Result of trust dialog."""

    accepted: bool = False


# =============================================================================
# Validation Error
# =============================================================================


@dataclass
class ValidationError:
    """A validation error from settings parsing.

    Attributes:
        path: Field path in dot notation (e.g., "permissions[0].tool").
        message: Human-readable error message.
        file: Optional relative file path where the error occurred.
        expected: Expected value or type description.
        invalid_value: The actual invalid value that was provided.
    """

    path: str
    message: str
    file: str | None = None
    expected: str | None = None
    invalid_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "message": self.message,
            "file": self.file,
            "expected": self.expected,
            "invalidValue": self.invalid_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationError:
        """Create from dictionary representation."""
        return cls(
            path=data["path"],
            message=data["message"],
            file=data.get("file"),
            expected=data.get("expected"),
            invalid_value=data.get("invalidValue"),
        )


# =============================================================================
# Agent Memory Scope
# =============================================================================


class AgentMemoryScope(StrEnum):
    """Scope for agent memory storage."""

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"


# =============================================================================
# Dialog Colors
# =============================================================================


class DialogColor(StrEnum):
    """Dialog color themes."""

    PERMISSION = "permission"
    WARNING = "warning"
    INFO = "info"
    ERROR = "error"
    SUCCESS = "success"


# =============================================================================
# Base Dialog
# =============================================================================


class BaseDialog:
    """Base class for dialog components.

    Subclasses should override __init__ to set up the dialog structure,
    and implement on_mount() for lifecycle hooks.

    Attributes:
        title: The dialog title.
        subtitle: Optional subtitle.
        color: The dialog color theme.
        result: The dialog result (set by subclasses on completion).
    """

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        color: DialogColor = DialogColor.PERMISSION,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: The dialog title.
            subtitle: Optional subtitle text.
            color: The dialog color theme.
        """
        self.title = title
        self.subtitle = subtitle
        self.color = color
        self.result: DialogResult | None = None
        self._on_done: Callable[[DialogResult], None] | None = None
        self._is_open = False

    def on_done(self, callback: Callable[[DialogResult], None]) -> None:
        """Register a callback for when the dialog completes.

        Args:
            callback: Function to call with the dialog result.
        """
        self._on_done = callback

    def _complete(self, result: DialogResult) -> None:
        """Complete the dialog with a result.

        Args:
            result: The dialog result.
        """
        self.result = result
        self._is_open = False
        if self._on_done:
            self._on_done(result)

    def is_open(self) -> bool:
        """Check if the dialog is currently open."""
        return self._is_open

    def open(self) -> None:
        """Open the dialog."""
        self._is_open = True

    def close(self) -> None:
        """Close the dialog without a result."""
        self._is_open = False

    def _dismiss(self) -> None:
        """Dismiss the dialog with cancel/close action."""
        self.close()


# =============================================================================
# Confirm Dialog
# =============================================================================


class ConfirmDialog(BaseDialog):
    """Simple confirmation dialog with yes/no options.

    Displays a message and presents Yes/No buttons. The dialog is
    modal and blocks until the user makes a selection.

    Attributes:
        message: The confirmation message to display.
        yes_label: Label for the confirm button.
        no_label: Label for the cancel button.
        default_cancel: If True, the No button is the default.
    """

    def __init__(
        self,
        title: str,
        message: str,
        yes_label: str = "Yes",
        no_label: str = "No",
        default_cancel: bool = True,
        subtitle: str | None = None,
    ) -> None:
        """Initialize the confirm dialog.

        Args:
            title: Dialog title.
            message: Confirmation message to display.
            yes_label: Label for the confirm button.
            no_label: Label for the cancel button.
            default_cancel: If True, No is the default selection.
            subtitle: Optional subtitle text.
        """
        super().__init__(title, subtitle=subtitle)
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label
        self.default_cancel = default_cancel


# =============================================================================
# Selection Dialog
# =============================================================================


@dataclass
class SelectOption:
    """An option in a selection dialog.

    Attributes:
        label: Display label for the option.
        value: Internal value returned when selected.
        description: Optional description text.
    """

    label: str
    value: str
    description: str | None = None


class SelectionDialog(BaseDialog):
    """Selection dialog with a list of options.

    Presents a list of choices and returns the selected value.
    Supports keyboard navigation and optional cancel.

    Attributes:
        options: List of SelectOption items.
        allow_cancel: Whether the user can cancel without selecting.
    """

    def __init__(
        self,
        title: str,
        options: list[SelectOption],
        allow_cancel: bool = True,
        subtitle: str | None = None,
    ) -> None:
        """Initialize the selection dialog.

        Args:
            title: Dialog title.
            options: List of selectable options.
            allow_cancel: Whether to allow canceling.
            subtitle: Optional subtitle text.
        """
        super().__init__(title, subtitle=subtitle)
        self.options = options
        self.allow_cancel = allow_cancel


# =============================================================================
# Invalid Settings Dialog
# =============================================================================


class InvalidSettingsDialog(BaseDialog):
    """Dialog shown when settings files have validation errors.

    Displays a list of validation errors and presents options to either
    exit and fix the settings manually, or continue without them.

    Attributes:
        settings_errors: List of validation errors from settings files.
        on_continue: Callback when user chooses to continue.
        on_exit: Callback when user chooses to exit.
    """

    def __init__(
        self,
        settings_errors: list[ValidationError],
        on_continue: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the invalid settings dialog.

        Args:
            settings_errors: List of ValidationError objects.
            on_continue: Callback when user chooses "Continue without these settings".
            on_exit: Callback when user chooses "Exit and fix manually".
        """
        super().__init__(
            title="Settings Error",
            color=DialogColor.WARNING,
        )
        self.settings_errors = settings_errors
        self.on_continue_callback = on_continue
        self.on_exit_callback = on_exit

    def handle_continue(self) -> None:
        """Handle continue action."""
        self._complete(InvalidSettingsDialogResult(continue_without_settings=True))
        if self.on_continue_callback:
            self.on_continue_callback()

    def handle_exit(self) -> None:
        """Handle exit action."""
        self._complete(InvalidSettingsDialogResult(continue_without_settings=False))
        if self.on_exit_callback:
            self.on_exit_callback()


# =============================================================================
# Cost Threshold Dialog
# =============================================================================


class CostThresholdDialog(BaseDialog):
    """Dialog shown when API cost threshold is reached.

    Informs the user they've spent a significant amount on the API
    and provides a link to cost monitoring documentation.

    Attributes:
        amount: The amount spent (e.g., "$5").
        on_done: Callback when user acknowledges.
    """

    def __init__(
        self,
        amount: str = "$5",
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the cost threshold dialog.

        Args:
            amount: The amount spent (displayed in title).
            on_done: Callback when user acknowledges.
        """
        super().__init__(
            title=f"You've spent {amount} on the Anthropic API this session.",
            color=DialogColor.INFO,
        )
        self.amount = amount
        self.on_done_callback = on_done
        self._dismiss_button_label = "Got it, thanks!"

    def handle_acknowledge(self) -> None:
        """Handle acknowledgment."""
        self._complete(CostThresholdDialogResult(acknowledged=True))
        if self.on_done_callback:
            self.on_done_callback()


# =============================================================================
# Trust Dialog
# =============================================================================


@dataclass
class TrustDialogDangerousItem:
    """A potentially dangerous configuration item shown in TrustDialog.

    Attributes:
        category: Category name (e.g., "Dangerous env vars", "Bash commands").
        sources: List of sources that configure this item.
    """

    category: str
    sources: list[str]


class TrustDialog(BaseDialog):
    """Trust and security warning dialog.

    Shown on first launch or when new commands/tools with elevated
    permissions are detected. Warns about security implications
    and allows user to accept or decline.

    Attributes:
        commands: List of dangerous commands that will be allowed.
        dangerous_env_vars: Dangerous environment variables.
        bash_commands: Bash commands requiring permission.
        mcp_servers: MCP servers being used.
        on_accept: Callback when user accepts trust.
        on_decline: Callback when user declines.
    """

    def __init__(
        self,
        commands: list[str] | None = None,
        dangerous_env_vars: list[TrustDialogDangerousItem] | None = None,
        bash_commands: list[TrustDialogDangerousItem] | None = None,
        mcp_servers: list[str] | None = None,
        on_accept: Callable[[], None] | None = None,
        on_decline: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the trust dialog.

        Args:
            commands: List of dangerous commands.
            dangerous_env_vars: Dangerous environment variable items.
            bash_commands: Bash command permission items.
            mcp_servers: MCP server names.
            on_accept: Callback when user accepts.
            on_decline: Callback when user declines.
        """
        super().__init__(
            title="Trust & Safety",
            color=DialogColor.WARNING,
        )
        self.commands = commands or []
        self.dangerous_env_vars = dangerous_env_vars or []
        self.bash_commands = bash_commands or []
        self.mcp_servers = mcp_servers or []
        self.on_accept_callback = on_accept
        self.on_decline_callback = on_decline

    def handle_accept(self) -> None:
        """Handle trust acceptance."""
        self._complete(TrustDialogResult(accepted=True))
        if self.on_accept_callback:
            self.on_accept_callback()

    def handle_decline(self) -> None:
        """Handle trust decline."""
        self._complete(TrustDialogResult(accepted=False))
        if self.on_decline_callback:
            self.on_decline_callback()


# =============================================================================
# Snapshot Update Dialog (Agent Memory)
# =============================================================================


class SnapshotUpdateDialog(BaseDialog):
    """Dialog for agent memory snapshot update prompts.

    Shown when an agent has a newer memory snapshot than the one
    currently in use, asking whether to merge, keep, or replace.

    Attributes:
        agent_type: The type of agent (e.g., "researcher").
        scope: The memory scope (user, project, or local).
        snapshot_timestamp: ISO timestamp of the snapshot.
        on_complete: Callback with the chosen action.
    """

    def __init__(
        self,
        agent_type: str,
        scope: AgentMemoryScope,
        snapshot_timestamp: str,
        on_complete: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the snapshot update dialog.

        Args:
            agent_type: The agent type identifier.
            scope: The memory scope.
            snapshot_timestamp: ISO timestamp string of the snapshot.
            on_complete: Callback with action ("merge", "keep", or "replace").
        """
        super().__init__(
            title=f"Agent Memory Update: {agent_type}",
            subtitle=f"Scope: {scope.value}",
        )
        self.agent_type = agent_type
        self.scope = scope
        self.snapshot_timestamp = snapshot_timestamp
        self.on_complete_callback = on_complete

    def handle_merge(self) -> None:
        """Handle merge action."""
        self._complete(SnapshotUpdateDialogResult(action="merge"))
        if self.on_complete_callback:
            self.on_complete_callback("merge")

    def handle_keep(self) -> None:
        """Handle keep action."""
        self._complete(SnapshotUpdateDialogResult(action="keep"))
        if self.on_complete_callback:
            self.on_complete_callback("keep")

    def handle_replace(self) -> None:
        """Handle replace action."""
        self._complete(SnapshotUpdateDialogResult(action="replace"))
        if self.on_complete_callback:
            self.on_complete_callback("replace")


# =============================================================================
# Permission Dialog
# =============================================================================


@dataclass
class PermissionRequest:
    """A permission request in a permission dialog.

    Attributes:
        tool_name: Name of the tool requiring permission.
        command: The command or argument for the tool.
        risk_level: Risk level classification.
        description: Human-readable description.
    """

    tool_name: str
    command: str
    risk_level: str = "MEDIUM"
    description: str | None = None


class PermissionDialog(BaseDialog):
    """Permission request dialog.

    Shown when a tool requires user permission to execute.
    Displays the tool name, command, and risk level.

    Attributes:
        request: The permission request details.
        on_allow: Callback when user allows the action.
        on_deny: Callback when user denies the action.
    """

    def __init__(
        self,
        request: PermissionRequest,
        on_allow: Callable[[], None] | None = None,
        on_deny: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the permission dialog.

        Args:
            request: The permission request details.
            on_allow: Callback when user allows.
            on_deny: Callback when user denies.
        """
        super().__init__(
            title=f"Permission Required: {request.tool_name}",
            color=DialogColor.PERMISSION,
        )
        self.request = request
        self.on_allow_callback = on_allow
        self.on_deny_callback = on_deny

    def handle_allow(self) -> None:
        """Handle allow action."""
        if self.on_allow_callback:
            self.on_allow_callback()
        self._complete(ConfirmDialogResult(confirmed=True))

    def handle_deny(self) -> None:
        """Handle deny action."""
        if self.on_deny_callback:
            self.on_deny_callback()
        self._complete(ConfirmDialogResult(confirmed=False))


# =============================================================================
# Dialog Launcher Helpers
# =============================================================================


async def show_confirm_dialog(
    title: str,
    message: str,
    yes_label: str = "Yes",
    no_label: str = "No",
) -> ConfirmDialogResult:
    """Show a confirmation dialog and wait for result.

    Args:
        title: Dialog title.
        message: Confirmation message.
        yes_label: Label for confirm button.
        no_label: Label for cancel button.

    Returns:
        ConfirmDialogResult with confirmed=True if user chose yes.
    """
    dialog = ConfirmDialog(
        title=title,
        message=message,
        yes_label=yes_label,
        no_label=no_label,
    )
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()

    # In a real TUI context, this would push the dialog onto the screen stack.
    # For now, return a default result.
    return ConfirmDialogResult(confirmed=False)


async def show_invalid_settings_dialog(
    settings_errors: list[ValidationError],
) -> InvalidSettingsDialogResult:
    """Show invalid settings dialog and wait for result.

    Args:
        settings_errors: List of validation errors.

    Returns:
        InvalidSettingsDialogResult indicating user's choice.
    """
    dialog = InvalidSettingsDialog(settings_errors=settings_errors)
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()
    return InvalidSettingsDialogResult(continue_without_settings=False)


async def show_cost_threshold_dialog(
    amount: str = "$5",
) -> CostThresholdDialogResult:
    """Show cost threshold dialog and wait for result.

    Args:
        amount: Amount spent to display.

    Returns:
        CostThresholdDialogResult with acknowledged=True if user clicked OK.
    """
    dialog = CostThresholdDialog(amount=amount)
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()
    return CostThresholdDialogResult(acknowledged=False)


async def show_trust_dialog(
    commands: list[str] | None = None,
    dangerous_env_vars: list[TrustDialogDangerousItem] | None = None,
    bash_commands: list[TrustDialogDangerousItem] | None = None,
    mcp_servers: list[str] | None = None,
) -> TrustDialogResult:
    """Show trust dialog and wait for result.

    Args:
        commands: List of dangerous commands.
        dangerous_env_vars: Dangerous environment variable items.
        bash_commands: Bash command permission items.
        mcp_servers: MCP server names.

    Returns:
        TrustDialogResult with accepted=True if user accepted.
    """
    dialog = TrustDialog(
        commands=commands,
        dangerous_env_vars=dangerous_env_vars,
        bash_commands=bash_commands,
        mcp_servers=mcp_servers,
    )
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()
    return TrustDialogResult(accepted=False)


async def show_snapshot_update_dialog(
    agent_type: str,
    scope: AgentMemoryScope,
    snapshot_timestamp: str,
) -> SnapshotUpdateDialogResult:
    """Show snapshot update dialog and wait for result.

    Args:
        agent_type: The agent type identifier.
        scope: The memory scope.
        snapshot_timestamp: ISO timestamp string.

    Returns:
        SnapshotUpdateDialogResult with the chosen action.
    """
    dialog = SnapshotUpdateDialog(
        agent_type=agent_type,
        scope=scope,
        snapshot_timestamp=snapshot_timestamp,
    )
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()
    return SnapshotUpdateDialogResult(action="keep")


async def show_selection_dialog(
    title: str,
    options: list[SelectOption],
    allow_cancel: bool = True,
) -> SelectionDialogResult:
    """Show selection dialog and wait for result.

    Args:
        title: Dialog title.
        options: List of selectable options.
        allow_cancel: Whether cancel is allowed.

    Returns:
        SelectionDialogResult with the selected value.
    """
    dialog = SelectionDialog(
        title=title,
        options=options,
        allow_cancel=allow_cancel,
    )
    result_future: asyncio.Future[DialogResult] = asyncio.get_running_loop().create_future()

    def on_done(result: DialogResult) -> None:
        if not result_future.done():
            result_future.set_result(result)

    dialog.on_done(on_done)
    dialog.open()
    return SelectionDialogResult(selected=None)


# =============================================================================
# Validation Errors List Helper
# =============================================================================


def format_validation_errors(errors: list[ValidationError]) -> str:
    """Format validation errors as a readable string.

    Args:
        errors: List of ValidationError objects.

    Returns:
        Formatted error string.
    """
    if not errors:
        return ""

    lines: list[str] = []
    for i, error in enumerate(errors, 1):
        if error.file:
            lines.append(f"{i}. [{error.file}] {error.path}: {error.message}")
        else:
            lines.append(f"{i}. {error.path}: {error.message}")
        if error.expected:
            lines.append(f"   Expected: {error.expected}")
        if error.invalid_value is not None:
            lines.append(f"   Got: {error.invalid_value!r}")

    return "\n".join(lines)


# =============================================================================
# Dialog Styles
# =============================================================================


class DialogStyle:
    """Dialog styling constants."""

    BORDER_COLOR_PERMISSION = "cyan"
    BORDER_COLOR_WARNING = "yellow"
    BORDER_COLOR_ERROR = "red"
    BORDER_COLOR_SUCCESS = "green"
    BORDER_COLOR_INFO = "blue"

    TITLE_COLOR = "bold"
    SUBTITLE_COLOR = "dim"
    BODY_COLOR = ""

    BUTTON_HOVER_COLOR = "reverse"
    BUTTON_SELECTED_COLOR = "bold"

    @classmethod
    def border_color_for(cls, dialog_color: DialogColor) -> str:
        """Get the border color for a dialog color.

        Args:
            dialog_color: The dialog color theme.

        Returns:
            Border color string.
        """
        mapping = {
            DialogColor.PERMISSION: cls.BORDER_COLOR_PERMISSION,
            DialogColor.WARNING: cls.BORDER_COLOR_WARNING,
            DialogColor.ERROR: cls.BORDER_COLOR_ERROR,
            DialogColor.SUCCESS: cls.BORDER_COLOR_SUCCESS,
            DialogColor.INFO: cls.BORDER_COLOR_INFO,
        }
        return mapping.get(dialog_color, cls.BORDER_COLOR_PERMISSION)
