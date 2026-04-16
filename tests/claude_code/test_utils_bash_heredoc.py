"""
Tests for utils/bash/heredoc.py - Heredoc extraction and restoration.
"""

from __future__ import annotations

import pytest

from claude_code.utils.bash.heredoc import (
    HeredocExtractionResult,
    HeredocInfo,
    extract_heredocs,
    restore_heredocs,
    restore_heredocs_in_string,
)


class TestExtractHeredocs:
    """Tests for extract_heredocs."""

    def test_no_heredoc_returns_original(self) -> None:
        result = extract_heredocs("echo hello")
        assert result.processed_command == "echo hello"
        assert result.heredocs == {}

    def test_extracts_simple_heredoc(self) -> None:
        result = extract_heredocs("cat << EOF\nhello\nEOF\n")
        assert result.processed_command != "cat << EOF\nhello\nEOF\n"
        assert len(result.heredocs) >= 1

    def test_extracts_quoted_heredoc(self) -> None:
        result = extract_heredocs("cat << 'EOF'\nhello\nEOF\n")
        assert len(result.heredocs) >= 1

    def test_extracts_double_quoted_heredoc(self) -> None:
        result = extract_heredocs('cat << "EOF"\nhello\nEOF\n')
        assert len(result.heredocs) >= 1

    def test_extracts_dash_stripping_heredoc(self) -> None:
        result = extract_heredocs("cat <<-EOF\n\thello\nEOF")
        assert len(result.heredocs) >= 1

    def test_bails_on_ansi_c_quoting(self) -> None:
        result = extract_heredocs("cat << EOF\n$'\nhello\nEOF")
        assert result.heredocs == {}

    def test_bails_on_backtick_before_heredoc(self) -> None:
        result = extract_heredocs("`echo` cat << EOF\nhello\nEOF")
        assert result.heredocs == {}

    def test_multiple_heredocs(self) -> None:
        result = extract_heredocs(
            "cat << EOF1\nhello\nEOF1\ncat << EOF2\nworld\nEOF2"
        )
        assert len(result.heredocs) >= 1

    def test_empty_command(self) -> None:
        result = extract_heredocs("")
        assert result.processed_command == ""
        assert result.heredocs == {}

    def test_quoted_only_mode_skips_unquoted(self) -> None:
        result = extract_heredocs("cat << EOF\nhello\nEOF", quoted_only=True)
        # Unquoted heredocs are skipped when quoted_only=True
        assert result.heredocs == {}


class TestRestoreHeredocs:
    """Tests for restore_heredocs."""

    def test_no_heredocs_returns_parts_unchanged(self) -> None:
        parts = ["cat", "file.txt"]
        result = restore_heredocs(parts, {})
        assert result == parts

    def test_restores_heredoc_in_string(self) -> None:
        info = HeredocInfo(
            full_text="<<EOF\nhello\nEOF",
            delimiter="EOF",
            operator_start_index=0,
            operator_end_index=6,
            content_start_index=6,
            content_end_index=17,
        )
        parts = ["cat __HEREDOC_0_salt__"]
        result = restore_heredocs(parts, {"__HEREDOC_0_salt__": info})
        assert "EOF" in result[0]
        assert "hello" in result[0]


class TestRestoreHeredocsInString:
    """Tests for restore_heredocs_in_string."""

    def test_no_placeholders_returns_original(self) -> None:
        result = restore_heredocs_in_string("echo hello", {})
        assert result == "echo hello"

    def test_restores_placeholder(self) -> None:
        info = HeredocInfo(
            full_text="<<EOF\nhello\nEOF",
            delimiter="EOF",
            operator_start_index=0,
            operator_end_index=0,
            content_start_index=0,
            content_end_index=0,
        )
        result = restore_heredocs_in_string(
            "cat __HEREDOC_0_abc__", {"__HEREDOC_0_abc__": info}
        )
        assert "hello" in result


class TestHeredocInfo:
    """Tests for HeredocInfo dataclass."""

    def test_creation(self) -> None:
        info = HeredocInfo(
            full_text="<<EOF\nhello\nEOF",
            delimiter="EOF",
            operator_start_index=0,
            operator_end_index=5,
            content_start_index=6,
            content_end_index=16,
        )
        assert info.delimiter == "EOF"
        assert info.full_text == "<<EOF\nhello\nEOF"


class TestHeredocExtractionResult:
    """Tests for HeredocExtractionResult dataclass."""

    def test_creation(self) -> None:
        result = HeredocExtractionResult(processed_command="echo hello", heredocs={})
        assert result.processed_command == "echo hello"
        assert result.heredocs == {}
