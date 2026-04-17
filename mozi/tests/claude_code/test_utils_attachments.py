"""Tests for utils/attachments.py."""

from __future__ import annotations

import pytest

from claude_code.utils.attachments import (
    AlreadyReadFileAttachment,
    CompactFileReferenceAttachment,
    DirectoryAttachment,
    EditedImageFileAttachment,
    EditedTextFileAttachment,
    FileAttachment,
    HookAttachment,
    IDESelection,
    NestedMemoryAttachment,
    OpenedFileInIdeAttachment,
    PDFReferenceAttachment,
    PlanModeAttachment,
    QueuedCommand,
    RelevantMemoriesAttachment,
    SelectedLinesInIdeAttachment,
    SkillListingAttachment,
    TaskReminderAttachment,
    ToolUseContext,
    TodoReminderAttachment,
    attachment_to_dict,
    get_attachments,
    get_changed_files,
    get_date_change_attachments,
    get_nested_memory_attachments,
    get_plan_mode_attachments,
    get_queued_command_attachments,
    get_skill_listing_attachments,
)


class TestFileAttachment:
    """Tests for FileAttachment."""

    def test_basic(self) -> None:
        att = FileAttachment(
            filename="test.py",
            content="print('hello')",
            display_path="/tmp/test.py",
        )
        assert att.type == "file"
        assert att.filename == "test.py"
        assert att.truncated is False


class TestCompactFileReferenceAttachment:
    """Tests for CompactFileReferenceAttachment."""

    def test_basic(self) -> None:
        att = CompactFileReferenceAttachment(filename="test.py", display_path="/tmp/test.py")
        assert att.type == "compact_file_reference"


class TestPDFReferenceAttachment:
    """Tests for PDFReferenceAttachment."""

    def test_basic(self) -> None:
        att = PDFReferenceAttachment(filename="doc.pdf", page_count=10, file_size=1024)
        assert att.type == "pdf_reference"
        assert att.page_count == 10


class TestAlreadyReadFileAttachment:
    """Tests for AlreadyReadFileAttachment."""

    def test_basic(self) -> None:
        att = AlreadyReadFileAttachment(filename="test.py", content="x", display_path="/tmp/test.py")
        assert att.type == "already_read_file"


class TestEditedTextFileAttachment:
    """Tests for EditedTextFileAttachment."""

    def test_basic(self) -> None:
        att = EditedTextFileAttachment(filename="test.py", content="edited", display_path="/tmp/test.py")
        assert att.type == "edited_text_file"


class TestEditedImageFileAttachment:
    """Tests for EditedImageFileAttachment."""

    def test_basic(self) -> None:
        att = EditedImageFileAttachment(filename="img.png", display_path="/tmp/img.png")
        assert att.type == "edited_image"


class TestDirectoryAttachment:
    """Tests for DirectoryAttachment."""

    def test_basic(self) -> None:
        att = DirectoryAttachment(path="/tmp", entries=["a.txt", "b.txt"])
        assert att.type == "directory"
        assert len(att.entries) == 2


class TestSelectedLinesInIdeAttachment:
    """Tests for SelectedLinesInIdeAttachment."""

    def test_basic(self) -> None:
        att = SelectedLinesInIdeAttachment(filename="test.py", lines="def foo():", display_path="/tmp/test.py")
        assert att.type == "selected_lines_in_ide"


class TestOpenedFileInIdeAttachment:
    """Tests for OpenedFileInIdeAttachment."""

    def test_basic(self) -> None:
        att = OpenedFileInIdeAttachment(filename="test.py", display_path="/tmp/test.py")
        assert att.type == "opened_file_in_ide"


class TestTodoReminderAttachment:
    """Tests for TodoReminderAttachment."""

    def test_basic(self) -> None:
        att = TodoReminderAttachment(count=5)
        assert att.type == "todo_reminder"
        assert att.count == 5


class TestTaskReminderAttachment:
    """Tests for TaskReminderAttachment."""

    def test_basic(self) -> None:
        att = TaskReminderAttachment(task_id="task_123", description="Do stuff")
        assert att.type == "task_reminder"
        assert att.task_id == "task_123"


class TestNestedMemoryAttachment:
    """Tests for NestedMemoryAttachment."""

    def test_basic(self) -> None:
        att = NestedMemoryAttachment(filename="memory.md", content="# Memory", display_path="/tmp/memory.md")
        assert att.type == "nested_memory"


class TestRelevantMemoriesAttachment:
    """Tests for RelevantMemoriesAttachment."""

    def test_basic(self) -> None:
        att = RelevantMemoriesAttachment(content="Remember to...")
        assert att.type == "relevant_memories"


class TestHookAttachment:
    """Tests for HookAttachment."""

    def test_basic(self) -> None:
        att = HookAttachment(
            type="hook_result",
            hook_name="my-hook",
            tool_use_id="tu_123",
            hook_event="PreToolUse",
        )
        assert att.hook_name == "my-hook"


class TestSkillListingAttachment:
    """Tests for SkillListingAttachment."""

    def test_basic(self) -> None:
        att = SkillListingAttachment(skills=["python", "bash"])
        assert att.type == "skill_listing"
        assert len(att.skills) == 2


class TestPlanModeAttachment:
    """Tests for PlanModeAttachment."""

    def test_basic(self) -> None:
        att = PlanModeAttachment(active=True)
        assert att.type == "plan_mode_reminder"
        assert att.active is True


class TestGetAttachments:
    """Tests for get_attachments."""

    def test_empty_input(self) -> None:
        attachments = get_attachments(None)
        assert attachments == []

    def test_with_queued_commands(self) -> None:
        commands = [QueuedCommand(command="test", args="arg")]
        attachments = get_attachments(None, queued_commands=commands)
        assert isinstance(attachments, list)


class TestGetQueuedCommandAttachments:
    """Tests for get_queued_command_attachments."""

    def test_empty(self) -> None:
        result = get_queued_command_attachments([])
        assert result == []


class TestGetDateChangeAttachments:
    """Tests for get_date_change_attachments."""

    def test_returns_none(self) -> None:
        result = get_date_change_attachments([])
        assert result is None


class TestGetChangedFiles:
    """Tests for get_changed_files."""

    def test_returns_empty(self) -> None:
        result = get_changed_files(ToolUseContext())
        assert result == []


class TestGetNestedMemoryAttachments:
    """Tests for get_nested_memory_attachments."""

    def test_returns_empty(self) -> None:
        result = get_nested_memory_attachments(ToolUseContext())
        assert result == []


class TestGetSkillListingAttachments:
    """Tests for get_skill_listing_attachments."""

    def test_returns_none(self) -> None:
        result = get_skill_listing_attachments(ToolUseContext())
        assert result is None


class TestGetPlanModeAttachments:
    """Tests for get_plan_mode_attachments."""

    def test_returns_none(self) -> None:
        result = get_plan_mode_attachments([])
        assert result is None


class TestAttachmentToDict:
    """Tests for attachment_to_dict."""

    def test_file_attachment(self) -> None:
        att = FileAttachment(filename="test.py", content="print('hi')", truncated=False, display_path="/tmp/test.py")
        d = attachment_to_dict(att)
        assert d["type"] == "file"
        assert d["filename"] == "test.py"

    def test_compact_file_reference(self) -> None:
        att = CompactFileReferenceAttachment(filename="x.txt", display_path="/x.txt")
        d = attachment_to_dict(att)
        assert d["type"] == "compact_file_reference"

    def test_pdf_reference(self) -> None:
        att = PDFReferenceAttachment(filename="doc.pdf", page_count=5, file_size=1024, display_path="/doc.pdf")
        d = attachment_to_dict(att)
        assert d["page_count"] == 5

    def test_skill_listing(self) -> None:
        att = SkillListingAttachment(skills=["a", "b"])
        d = attachment_to_dict(att)
        assert d["skills"] == ["a", "b"]

    def test_plan_mode(self) -> None:
        att = PlanModeAttachment(active=True)
        d = attachment_to_dict(att)
        assert d["active"] is True

    def test_nested_memory(self) -> None:
        att = NestedMemoryAttachment(filename="m.md", content="# Hi", display_path="/m.md")
        d = attachment_to_dict(att)
        assert d["content"] == "# Hi"

    def test_relevant_memories(self) -> None:
        att = RelevantMemoriesAttachment(content="Remember things")
        d = attachment_to_dict(att)
        assert d["content"] == "Remember things"

    def test_hook_attachment(self) -> None:
        att = HookAttachment(type="hook_result", hook_name="h", tool_use_id="t", hook_event="Pre")
        d = attachment_to_dict(att)
        assert d["hook_name"] == "h"

    def test_todo_reminder(self) -> None:
        att = TodoReminderAttachment(count=3)
        d = attachment_to_dict(att)
        assert d["count"] == 3

    def test_edited_text_file(self) -> None:
        att = EditedTextFileAttachment(filename="x.txt", content="y", display_path="/x.txt")
        d = attachment_to_dict(att)
        assert d["content"] == "y"

    def test_edited_image(self) -> None:
        att = EditedImageFileAttachment(filename="x.png", display_path="/x.png")
        d = attachment_to_dict(att)
        assert d["filename"] == "x.png"

    def test_directory(self) -> None:
        att = DirectoryAttachment(path="/tmp", entries=["a", "b"])
        d = attachment_to_dict(att)
        assert d["entries"] == ["a", "b"]

    def test_selected_lines_in_ide(self) -> None:
        att = SelectedLinesInIdeAttachment(filename="x.txt", lines="...", display_path="/x.txt")
        d = attachment_to_dict(att)
        assert d["lines"] == "..."

    def test_opened_file_in_ide(self) -> None:
        att = OpenedFileInIdeAttachment(filename="x.txt", display_path="/x.txt")
        d = attachment_to_dict(att)
        assert d["filename"] == "x.txt"

    def test_already_read_file(self) -> None:
        att = AlreadyReadFileAttachment(filename="x.txt", content="y", display_path="/x.txt")
        d = attachment_to_dict(att)
        assert d["content"] == "y"

    def test_task_reminder(self) -> None:
        att = TaskReminderAttachment(task_id="t", description="d")
        d = attachment_to_dict(att)
        assert d["task_id"] == "t"
