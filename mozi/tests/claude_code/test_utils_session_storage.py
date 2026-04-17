"""Tests for utils/session_storage.py."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from claude_code.utils.session_storage import (
    MAX_TRANSCRIPT_READ_BYTES,
    AgentMetadata,
    Entry,
    MAX_TOMBSTONE_REWRITE_BYTES,
    Project,
    get_agent_transcript_path,
    get_projects_dir,
    get_transcript_path,
    get_transcript_path_for_session,
    read_transcript_entries,
    read_agent_metadata,
    session_id_exists,
    write_agent_metadata,
)


class TestEntry:
    """Tests for Entry dataclass."""

    def test_to_jsonl(self) -> None:
        entry = Entry(ts="2024-01-01T00:00:00Z", type="user", data={"text": "hello"})
        line = entry.to_jsonl()
        assert line.endswith("\n")
        assert "user" in line
        assert "hello" in line

    def test_from_dict(self) -> None:
        data = {"ts": "2024-01-01T00:00:00Z", "type": "assistant", "data": {"content": "hi"}}
        entry = Entry.from_dict(data)
        assert entry.ts == "2024-01-01T00:00:00Z"
        assert entry.type == "assistant"
        assert entry.data == {"content": "hi"}


class TestGetProjectsDir:
    """Tests for get_projects_dir."""

    def test_returns_path(self) -> None:
        path = get_projects_dir()
        assert ".claude" in path
        assert "projects" in path


class TestGetTranscriptPath:
    """Tests for get_transcript_path."""

    def test_uses_session_id(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": "test-session-123"}):
            path = get_transcript_path()
            assert "test-session-123" in path

    def test_default_session(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            path = get_transcript_path()
            assert "default" in path


class TestGetTranscriptPathForSession:
    """Tests for get_transcript_path_for_session."""

    def test_session_path_format(self) -> None:
        path = get_transcript_path_for_session("abc123")
        assert "abc123" in path
        assert path.endswith(".jsonl")


class TestGetAgentTranscriptPath:
    """Tests for get_agent_transcript_path."""

    def test_agent_path_format(self) -> None:
        path = get_agent_transcript_path("agent_xyz")
        assert "agent_agent_xyz" in path


class TestSessionIdExists:
    """Tests for session_id_exists."""

    def test_nonexistent_session(self) -> None:
        assert session_id_exists("nonexistent-session-xyz-abc") is False

    def test_with_temp_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            f.write(b"{}")
            temp_path = f.name

        try:
            session_id = f"test-{os.getpid()}"
            with patch(
                "claude-code-py.utils.session_storage.get_transcript_path_for_session",
                return_value=temp_path,
            ):
                assert session_id_exists(session_id) is True
        finally:
            os.unlink(temp_path)


class TestProjectSingleton:
    """Tests for Project singleton."""

    def test_get_instance(self) -> None:
        Project.reset_for_testing()
        proj1 = Project.get_instance()
        proj2 = Project.get_instance()
        assert proj1 is proj2

    def test_reset_for_testing(self) -> None:
        Project.reset_for_testing()
        proj1 = Project.get_instance()
        Project.reset_for_testing()
        proj2 = Project.get_instance()
        assert proj1 is not proj2

    def test_set_session_file(self) -> None:
        Project.reset_for_testing()
        proj = Project.get_instance()
        proj.set_session_file("/tmp/test.jsonl")
        assert proj.session_file == "/tmp/test.jsonl"

    async def test_append_entry_no_file(self) -> None:
        Project.reset_for_testing()
        proj = Project.get_instance()
        proj.session_file = None
        entry = Entry(ts="t", type="test", data={})
        await proj.append_entry(entry)

    async def test_flush_no_file(self) -> None:
        Project.reset_for_testing()
        proj = Project.get_instance()
        proj.session_file = None
        await proj.flush()

    async def test_remove_message_by_uuid_no_file(self) -> None:
        Project.reset_for_testing()
        proj = Project.get_instance()
        proj.session_file = None
        await proj.remove_message_by_uuid("any-uuid")


class TestReadTranscriptEntries:
    """Tests for read_transcript_entries."""

    async def test_nonexistent_session(self) -> None:
        entries = await read_transcript_entries("nonexistent-session-xyz")
        assert entries == []


class TestAgentMetadata:
    """Tests for AgentMetadata."""

    def test_basic(self) -> None:
        meta = AgentMetadata(agent_type="claude", worktree_path="/tmp")
        assert meta.agent_type == "claude"
        assert meta.worktree_path == "/tmp"


class TestWriteReadAgentMetadata:
    """Tests for write/read_agent_metadata."""

    async def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = AgentMetadata(
                agent_type="test-agent",
                worktree_path="/tmp/work",
                description="Test agent",
            )
            agent_id = f"agent-{os.getpid()}"
            with patch(
                "claude-code-py.utils.session_storage.get_projects_dir",
                return_value=tmpdir,
            ):
                await write_agent_metadata(agent_id, meta)
                result = await read_agent_metadata(agent_id)
                assert result is not None
                assert result.agent_type == "test-agent"
                assert result.worktree_path == "/tmp/work"

    async def test_nonexistent_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "claude-code-py.utils.session_storage.get_projects_dir",
                return_value=tmpdir,
            ):
                result = await read_agent_metadata("nonexistent-agent-xyz")
                assert result is None
