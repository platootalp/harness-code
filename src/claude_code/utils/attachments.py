"""Attachment generation utilities for context injection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Attachment Types
# =============================================================================


@dataclass
class FileAttachment:
    """A file attachment with content."""

    type: str = "file"
    filename: str = ""
    content: Any = None
    truncated: bool = False
    display_path: str = ""


@dataclass
class CompactFileReferenceAttachment:
    """A compact file reference attachment."""

    type: str = "compact_file_reference"
    filename: str = ""
    display_path: str = ""


@dataclass
class PDFReferenceAttachment:
    """A PDF reference attachment."""

    type: str = "pdf_reference"
    filename: str = ""
    page_count: int = 0
    file_size: int = 0
    display_path: str = ""


@dataclass
class AlreadyReadFileAttachment:
    """An attachment for a file that was already read."""

    type: str = "already_read_file"
    filename: str = ""
    content: Any = None
    display_path: str = ""


@dataclass
class EditedTextFileAttachment:
    """An edited text file attachment."""

    type: str = "edited_text_file"
    filename: str = ""
    content: Any = None
    truncated: bool = False
    display_path: str = ""


@dataclass
class EditedImageFileAttachment:
    """An edited image file attachment."""

    type: str = "edited_image"
    filename: str = ""
    display_path: str = ""


@dataclass
class DirectoryAttachment:
    """A directory listing attachment."""

    type: str = "directory"
    path: str = ""
    entries: list[str] = field(default_factory=list)


@dataclass
class SelectedLinesInIdeAttachment:
    """Selected lines from the IDE."""

    type: str = "selected_lines_in_ide"
    filename: str = ""
    lines: str = ""
    display_path: str = ""


@dataclass
class OpenedFileInIdeAttachment:
    """An opened file in the IDE."""

    type: str = "opened_file_in_ide"
    filename: str = ""
    display_path: str = ""


@dataclass
class TodoReminderAttachment:
    """A todo reminder attachment."""

    type: str = "todo_reminder"
    count: int = 0


@dataclass
class TaskReminderAttachment:
    """A task reminder attachment."""

    type: str = "task_reminder"
    task_id: str = ""
    description: str = ""


@dataclass
class NestedMemoryAttachment:
    """A nested memory file attachment."""

    type: str = "nested_memory"
    filename: str = ""
    content: Any = None
    display_path: str = ""


@dataclass
class RelevantMemoriesAttachment:
    """Relevant memories attachment."""

    type: str = "relevant_memories"
    content: Any = None


@dataclass
class HookAttachment:
    """A hook result attachment."""

    type: str = ""
    hook_name: str = ""
    tool_use_id: str = ""
    hook_event: str = ""


@dataclass
class SkillListingAttachment:
    """A skill listing attachment."""

    type: str = "skill_listing"
    skills: list[str] = field(default_factory=list)


@dataclass
class PlanModeAttachment:
    """A plan mode reminder attachment."""

    type: str = "plan_mode_reminder"
    active: bool = False


# Union type alias
Attachment = (
    FileAttachment
    | CompactFileReferenceAttachment
    | PDFReferenceAttachment
    | AlreadyReadFileAttachment
    | EditedTextFileAttachment
    | EditedImageFileAttachment
    | DirectoryAttachment
    | SelectedLinesInIdeAttachment
    | OpenedFileInIdeAttachment
    | TodoReminderAttachment
    | TaskReminderAttachment
    | NestedMemoryAttachment
    | RelevantMemoriesAttachment
    | HookAttachment
    | SkillListingAttachment
    | PlanModeAttachment
)


# =============================================================================
# Tool Use Context (placeholder interface)
# =============================================================================


@dataclass
class ToolUseContext:
    """Context for tool use operations."""

    pass


@dataclass
class IDESelection:
    """IDE selection information."""

    pass


@dataclass
class QueuedCommand:
    """A queued slash command."""

    command: str = ""
    args: str = ""


# =============================================================================
# Attachment Generation
# =============================================================================


def get_attachments(
    input_text: str | None,
    tool_use_context: ToolUseContext | None = None,
    ide_selection: IDESelection | None = None,
    queued_commands: list[QueuedCommand] | None = None,
    messages: list[Any] | None = None,
    query_source: str | None = None,
) -> list[Attachment]:
    """Get all attachments for the current context.

    This is the main entry point for gathering attachments from
    multiple sources.

    Args:
        input_text: The user's input text.
        tool_use_context: Current tool use context.
        ide_selection: Current IDE selection.
        queued_commands: Queued slash commands.
        messages: Conversation messages.
        query_source: Source of the query.

    Returns:
        List of all applicable attachments.
    """
    attachments: list[Attachment] = []

    if queued_commands:
        attachments.extend(get_queued_command_attachments(queued_commands))

    if messages:
        date_attachment = get_date_change_attachments(messages)
        if date_attachment:
            attachments.append(date_attachment)

    return attachments


def get_queued_command_attachments(
    queued_commands: list[QueuedCommand],
) -> list[Attachment]:
    """Get attachments from queued commands.

    Args:
        queued_commands: List of queued commands.

    Returns:
        List of command-related attachments.
    """
    return []


def get_date_change_attachments(
    messages: list[Any] | None,
) -> Attachment | None:
    """Detect date changes between conversation turns.

    Args:
        messages: Conversation messages.

    Returns:
        Date change attachment if a date change was detected.
    """
    return None


def get_changed_files(context: ToolUseContext) -> list[Attachment]:
    """Get files changed since the last turn.

    Args:
        context: Tool use context.

    Returns:
        List of changed file attachments.
    """
    return []


def get_nested_memory_attachments(
    context: ToolUseContext,
) -> list[NestedMemoryAttachment]:
    """Get nested memory file attachments.

    Args:
        context: Tool use context.

    Returns:
        List of nested memory attachments.
    """
    return []


def get_skill_listing_attachments(
    context: ToolUseContext,
) -> Attachment | None:
    """Get skill listing attachment.

    Args:
        context: Tool use context.

    Returns:
        Skill listing attachment, or None.
    """
    return None


def get_plan_mode_attachments(
    messages: list[Any] | None,
    tool_use_context: ToolUseContext | None = None,
) -> Attachment | None:
    """Get plan mode reminder attachment.

    Args:
        messages: Conversation messages.
        tool_use_context: Tool use context.

    Returns:
        Plan mode attachment, or None.
    """
    return None


# =============================================================================
# Attachment Serialization
# =============================================================================


def attachment_to_dict(attachment: Attachment) -> dict[str, Any]:
    """Convert an attachment to a dictionary.

    Args:
        attachment: The attachment to serialize.

    Returns:
        Dictionary representation.
    """
    if isinstance(attachment, FileAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "content": attachment.content,
            "truncated": attachment.truncated,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, CompactFileReferenceAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, PDFReferenceAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "page_count": attachment.page_count,
            "file_size": attachment.file_size,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, SkillListingAttachment):
        return {
            "type": attachment.type,
            "skills": attachment.skills,
        }
    if isinstance(attachment, PlanModeAttachment):
        return {
            "type": attachment.type,
            "active": attachment.active,
        }
    if isinstance(attachment, NestedMemoryAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "content": attachment.content,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, RelevantMemoriesAttachment):
        return {
            "type": attachment.type,
            "content": attachment.content,
        }
    if isinstance(attachment, HookAttachment):
        return {
            "type": attachment.type,
            "hook_name": attachment.hook_name,
            "tool_use_id": attachment.tool_use_id,
            "hook_event": attachment.hook_event,
        }
    if isinstance(attachment, TodoReminderAttachment):
        return {"type": attachment.type, "count": attachment.count}
    if isinstance(attachment, TaskReminderAttachment):
        return {
            "type": attachment.type,
            "task_id": attachment.task_id,
            "description": attachment.description,
        }
    if isinstance(attachment, EditedTextFileAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "content": attachment.content,
            "truncated": attachment.truncated,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, EditedImageFileAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, DirectoryAttachment):
        return {
            "type": attachment.type,
            "path": attachment.path,
            "entries": attachment.entries,
        }
    if isinstance(attachment, SelectedLinesInIdeAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "lines": attachment.lines,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, OpenedFileInIdeAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "display_path": attachment.display_path,
        }
    if isinstance(attachment, AlreadyReadFileAttachment):
        return {
            "type": attachment.type,
            "filename": attachment.filename,
            "content": attachment.content,
            "display_path": attachment.display_path,
        }
    return {"type": "unknown"}
