"""
Tests for utils/file.py - File operations.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from claude_code.utils.file import (
    FILE_NOT_FOUND_CWD_NOTE,
    MAX_OUTPUT_SIZE,
    FileReadMetadata,
    LineEndingType,
    Platform,
    add_line_numbers,
    convert_leading_tabs_to_spaces,
    detect_encoding_for_resolved_path,
    detect_file_encoding,
    detect_line_endings,
    detect_line_endings_for_string,
    expand_path,
    find_similar_file,
    get_absolute_and_relative_paths,
    get_desktop_path,
    get_display_path,
    get_file_modification_time,
    get_file_modification_time_async,
    get_platform,
    is_dir_empty,
    is_file_within_read_size_limit,
    normalize_path_for_comparison,
    path_exists,
    path_exists_sync,
    paths_equal,
    read_file_safe,
    read_file_sync,
    read_file_sync_with_metadata,
    strip_line_number_prefix,
    suggest_path_under_cwd,
    write_file_sync_and_flush_deprecated,
    write_text_content,
)

# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    def test_max_output_size(self) -> None:
        """MAX_OUTPUT_SIZE should be 0.25 MB."""
        assert MAX_OUTPUT_SIZE == 0.25 * 1024 * 1024

    def test_file_not_found_cwd_note(self) -> None:
        """FILE_NOT_FOUND_CWD_NOTE should contain cwd marker."""
        assert "working directory" in FILE_NOT_FOUND_CWD_NOTE


# =============================================================================
# Platform Detection
# =============================================================================


class TestPlatform:
    def test_get_platform(self) -> None:
        """get_platform should return a valid Platform."""
        p = get_platform()
        assert isinstance(p, Platform)
        assert p.value in ("macos", "windows", "wsl", "linux", "unknown")


# =============================================================================
# Path Utilities
# =============================================================================


class TestExpandPath:
    def test_expand_tilde(self) -> None:
        """expand_path should expand ~."""
        result = expand_path("~/foo")
        assert result.startswith(os.path.expanduser("~"))
        assert result.endswith("foo")

    def test_expand_env_var(self) -> None:
        """expand_path should expand environment variables."""
        os.environ["TEST_VAR"] = "test_value"
        result = expand_path("$TEST_VAR/foo")
        assert "test_value" in result
        assert "foo" in result

    def test_expand_windows_style(self) -> None:
        """expand_path %VAR% style - skipped on non-Windows."""
        # %VAR% expansion is Windows-specific; on POSIX, it's not expanded.
        pytest.skip(reason="%VAR% expansion is Windows-specific")


class TestNormalizePathForComparison:
    def test_basic_normalization(self) -> None:
        """normalize_path_for_comparison should normalize path."""
        result = normalize_path_for_comparison("foo//bar/../baz")
        assert result == os.path.normpath("foo//bar/../baz")


class TestPathsEqual:
    def test_equal_paths(self) -> None:
        """paths_equal should return True for same paths."""
        assert paths_equal("foo/bar", "foo/bar") is True

    def test_different_paths(self) -> None:
        """paths_equal should return False for different paths."""
        assert paths_equal("foo/bar", "foo/baz") is False


class TestGetAbsoluteAndRelativePaths:
    def test_with_path(self) -> None:
        """Should return both absolute and relative paths."""
        abs_input = os.path.join(os.getcwd(), "foo.txt")
        abs_path, rel_path = get_absolute_and_relative_paths(abs_input)
        assert abs_path is not None
        assert rel_path is not None
        assert os.path.isabs(abs_path)
        assert rel_path == "foo.txt"

    def test_with_none(self) -> None:
        """Should return None for None input."""
        abs_path, rel_path = get_absolute_and_relative_paths(None)
        assert abs_path is None
        assert rel_path is None


class TestGetDisplayPath:
    def test_relative_path_in_cwd(self) -> None:
        """Should return relative path when file is in cwd."""
        cwd = os.getcwd()
        test_file = os.path.join(cwd, "test.txt")
        result = get_display_path(test_file)
        assert result == "test.txt"

    def test_path_outside_cwd(self) -> None:
        """Should return absolute path for files outside cwd."""
        result = get_display_path("/tmp/some_file.txt")
        assert result.startswith("/")

    def test_home_path(self) -> None:
        """Should use tilde notation for home directory."""
        home = os.path.expanduser("~")
        test_file = os.path.join(home, "Documents", "test.txt")
        result = get_display_path(test_file)
        assert result.startswith("~")


# =============================================================================
# Path Existence
# =============================================================================


class TestPathExists:
    @pytest.mark.asyncio
    async def test_existing_path(self) -> None:
        """path_exists should return True for existing path."""
        assert await path_exists(__file__) is True

    @pytest.mark.asyncio
    async def test_nonexistent_path(self) -> None:
        """path_exists should return False for nonexistent path."""
        assert await path_exists("/nonexistent/path/to/file.txt") is False

    def test_existing_path_sync(self) -> None:
        """path_exists_sync should return True for existing path."""
        assert path_exists_sync(__file__) is True

    def test_nonexistent_path_sync(self) -> None:
        """path_exists_sync should return False for nonexistent path."""
        assert path_exists_sync("/nonexistent/path/to/file.txt") is False


# =============================================================================
# Encoding Detection
# =============================================================================


class TestDetectEncodingForResolvedPath:
    def test_utf8_file(self) -> None:
        """Should detect UTF-8 encoding."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Hello, world!")
            path = f.name

        try:
            enc = detect_encoding_for_resolved_path(path)
            assert enc == "utf-8"
        finally:
            os.unlink(path)

    def test_empty_file(self) -> None:
        """Empty file should default to UTF-8."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            enc = detect_encoding_for_resolved_path(path)
            assert enc == "utf-8"
        finally:
            os.unlink(path)

    def test_nonexistent_file(self) -> None:
        """Nonexistent file should default to UTF-8."""
        enc = detect_encoding_for_resolved_path("/nonexistent/file.txt")
        assert enc == "utf-8"


class TestDetectFileEncoding:
    def test_detect_encoding(self) -> None:
        """Should detect encoding from file path."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Test content")
            path = f.name

        try:
            enc = detect_file_encoding(path)
            assert enc == "utf-8"
        finally:
            os.unlink(path)


# =============================================================================
# Line Ending Detection
# =============================================================================


class TestDetectLineEndingsForString:
    def test_lf_only(self) -> None:
        """Should detect LF endings."""
        result = detect_line_endings_for_string("line1\nline2\nline3")
        assert result == LineEndingType.LF

    def test_crlf(self) -> None:
        """Should detect CRLF endings."""
        result = detect_line_endings_for_string("line1\r\nline2\r\nline3")
        assert result == LineEndingType.CRLF

    def test_mixed_prefers_lf(self) -> None:
        """Mixed endings should prefer LF if more LFs."""
        # 2 CRLF vs 99 LF - LF wins
        content = "a\r\nb\r\n" + "\n".join(["x"] * 100)
        result = detect_line_endings_for_string(content)
        assert result == LineEndingType.LF

    def test_empty_string(self) -> None:
        """Empty string should default to LF."""
        result = detect_line_endings_for_string("")
        assert result == LineEndingType.LF


class TestDetectLineEndings:
    def test_detect_from_file(self) -> None:
        """Should detect line endings from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("line1\nline2\n")
            path = f.name

        try:
            result = detect_line_endings(path)
            assert result == LineEndingType.LF
        finally:
            os.unlink(path)


# =============================================================================
# File Read
# =============================================================================


class TestReadFileSyncWithMetadata:
    def test_read_utf8_file(self) -> None:
        """Should read file with metadata."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Hello\nWorld\n")
            path = f.name

        try:
            result = read_file_sync_with_metadata(path)
            assert isinstance(result, FileReadMetadata)
            assert result.content == "Hello\nWorld\n"
            assert result.encoding == "utf-8"
            assert result.line_endings == LineEndingType.LF
        finally:
            os.unlink(path)

    def test_crlf_normalization(self) -> None:
        """Should normalize CRLF to LF and detect CRLF endings."""
        # Use binary mode to write exact CRLF bytes
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"line1\r\nline2\r\n")
            path = f.name

        try:
            result = read_file_sync_with_metadata(path)
            assert "\r\n" not in result.content
            assert result.line_endings == LineEndingType.CRLF
        finally:
            os.unlink(path)


class TestReadFileSync:
    def test_read_simple(self) -> None:
        """Should read file content."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content\n")
            path = f.name

        try:
            content = read_file_sync(path)
            assert content == "test content\n"
        finally:
            os.unlink(path)


class TestReadFileSafe:
    def test_read_existing(self) -> None:
        """Should return content for existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("safe read test\n")
            path = f.name

        try:
            result = read_file_safe(path)
            assert result == "safe read test\n"
        finally:
            os.unlink(path)

    def test_read_nonexistent(self) -> None:
        """Should return None for nonexistent file."""
        result = read_file_safe("/nonexistent/file.txt")
        assert result is None


# =============================================================================
# File Modification Time
# =============================================================================


class TestGetFileModificationTime:
    def test_get_mtime(self) -> None:
        """Should return modification time in seconds."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            mtime = get_file_modification_time(path)
            assert isinstance(mtime, int)
            assert mtime > 0
        finally:
            os.unlink(path)


class TestGetFileModificationTimeAsync:
    @pytest.mark.asyncio
    async def test_get_mtime_async(self) -> None:
        """Should return modification time asynchronously."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name

        try:
            mtime = await get_file_modification_time_async(path)
            assert isinstance(mtime, int)
            assert mtime > 0
        finally:
            os.unlink(path)


# =============================================================================
# Directory Operations
# =============================================================================


class TestIsDirEmpty:
    def test_empty_dir(self) -> None:
        """Should return True for empty directory."""
        with tempfile.TemporaryDirectory() as d:
            assert is_dir_empty(d) is True

    def test_nonempty_dir(self) -> None:
        """Should return False for non-empty directory."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "file.txt").touch()
            assert is_dir_empty(d) is False

    def test_nonexistent_dir(self) -> None:
        """Should return True for nonexistent path."""
        assert is_dir_empty("/nonexistent/directory/path") is True


# =============================================================================
# File Size Validation
# =============================================================================


class TestIsFileWithinReadSizeLimit:
    def test_small_file(self) -> None:
        """Should return True for small files."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"small content")
            path = f.name

        try:
            assert is_file_within_read_size_limit(path) is True
        finally:
            os.unlink(path)

    def test_large_file(self) -> None:
        """Should return False for files over limit."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"x" * int(MAX_OUTPUT_SIZE * 2))
            path = f.name

        try:
            assert is_file_within_read_size_limit(path) is False
        finally:
            os.unlink(path)

    def test_custom_limit(self) -> None:
        """Should respect custom size limit."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"x" * 100)
            path = f.name

        try:
            assert is_file_within_read_size_limit(path, max_size_bytes=50) is False
            assert is_file_within_read_size_limit(path, max_size_bytes=200) is True
        finally:
            os.unlink(path)


# =============================================================================
# Content Transformations
# =============================================================================


class TestConvertLeadingTabsToSpaces:
    def test_no_tabs(self) -> None:
        """Should return unchanged if no tabs."""
        content = "no tabs\nhere\n"
        assert convert_leading_tabs_to_spaces(content) == content

    def test_tabs_converted(self) -> None:
        """Should convert leading tabs to 2 spaces."""
        content = "\tline1\n\t\tline2\n"
        result = convert_leading_tabs_to_spaces(content)
        assert result == "  line1\n    line2\n"


class TestAddLineNumbers:
    def test_basic_numbering(self) -> None:
        """Should add line numbers."""
        content = "line1\nline2\nline3"
        result = add_line_numbers(content, start_line=1)
        lines = result.split("\n")
        assert lines[0].endswith("line1")
        assert lines[1].endswith("line2")
        assert lines[2].endswith("line3")

    def test_custom_start_line(self) -> None:
        """Should start from specified line number."""
        content = "a\nb"
        result = add_line_numbers(content, start_line=10)
        assert "10\u2192a" in result
        assert "11\u2192b" in result

    def test_empty_content(self) -> None:
        """Should return empty string for empty content."""
        assert add_line_numbers("") == ""

    def test_whitespace_content(self) -> None:
        """Should number a single line of whitespace."""
        result = add_line_numbers("   ")
        assert "\u2192   " in result  # Contains arrow followed by spaces


class TestStripLineNumberPrefix:
    def test_arrow_prefix(self) -> None:
        """Should strip arrow prefix."""
        assert strip_line_number_prefix("10\u2192content") == "content"

    def test_tab_prefix(self) -> None:
        """Should strip tab prefix."""
        assert strip_line_number_prefix("5\tcontent") == "content"

    def test_no_prefix(self) -> None:
        """Should return unchanged if no prefix."""
        assert strip_line_number_prefix("plain content") == "plain content"


# =============================================================================
# File Writing
# =============================================================================


class TestWriteTextContent:
    def test_write_lf(self) -> None:
        """Should write with LF endings."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            write_text_content(path, "line1\nline2\n", "utf-8", LineEndingType.LF)
            content = Path(path).read_text()
            assert "\r\n" not in content

    def test_write_crlf(self) -> None:
        """Should write with CRLF endings."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            write_text_content(path, "line1\nline2\n", "utf-8", LineEndingType.CRLF)
            content = Path(path).read_bytes()
            assert b"\r\n" in content


class TestWriteFileSyncAndFlushDeprecated:
    def test_write_new_file(self) -> None:
        """Should write to a new file."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "new_file.txt")
            write_file_sync_and_flush_deprecated(path, "hello world\n")
            assert Path(path).read_text() == "hello world\n"

    def test_overwrite_existing(self) -> None:
        """Should overwrite existing file."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "existing.txt")
            Path(path).write_text("old content\n")
            write_file_sync_and_flush_deprecated(path, "new content\n")
            assert Path(path).read_text() == "new content\n"

    def test_write_unicode(self) -> None:
        """Should handle unicode content."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "unicode.txt")
            content = "Hello \u4e16\u754c \U0001F600\n"
            write_file_sync_and_flush_deprecated(path, content)
            assert Path(path).read_text() == content


# =============================================================================
# Desktop Path
# =============================================================================


class TestGetDesktopPath:
    def test_returns_path(self) -> None:
        """Should return a valid path."""
        result = get_desktop_path()
        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Find Similar File
# =============================================================================


class TestFindSimilarFile:
    def test_finds_similar(self) -> None:
        """Should find file with different extension."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "test.txt").touch()
            Path(d, "test.py").touch()

            result = find_similar_file(os.path.join(d, "test.md"))
            assert result is not None
            assert result.endswith(".py")

    def test_no_match(self) -> None:
        """Should return None when no similar file exists."""
        with tempfile.TemporaryDirectory() as d:
            result = find_similar_file(os.path.join(d, "test.md"))
            assert result is None


# =============================================================================
# Suggest Path Under CWD
# =============================================================================


class TestSuggestPathUnderCwd:
    @pytest.mark.asyncio
    async def test_no_suggestion_when_inside_cwd(self) -> None:
        """Should return None if path is inside cwd."""
        cwd = os.getcwd()
        result = await suggest_path_under_cwd(os.path.join(cwd, "existing.txt"))
        assert result is None

    @pytest.mark.asyncio
    async def test_no_suggestion_for_unreachable_path(self) -> None:
        """Should return None if path doesn't exist anywhere."""
        result = await suggest_path_under_cwd("/nonexistent/weird/path/file.txt")
        assert result is None
