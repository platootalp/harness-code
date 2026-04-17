"""
Tests for VimMode.
"""

from __future__ import annotations

import pytest

from claude_code.cli.vim import VimMode


class TestVimModeInit:
    """Tests for VimMode initialization."""

    def test_default_init(self) -> None:
        """VimMode initializes with INSERT mode by default."""
        vim = VimMode()
        assert vim.mode() == "INSERT"
        assert vim.is_insert() is True
        assert vim.is_normal() is False

    def test_init_with_callbacks(self) -> None:
        """VimMode accepts text/cursor callbacks."""
        vim = VimMode(
            get_text=lambda: "hello",
            set_text=lambda t: None,
            get_cursor=lambda: 0,
            set_cursor=lambda o: None,
            enter_insert=lambda o: None,
        )
        assert vim.mode() == "INSERT"
        assert vim.get_register() == ""


class TestVimModeInsertMode:
    """Tests for INSERT mode operations."""

    def test_enter_insert_explicit(self) -> None:
        """enter_insert switches to INSERT mode."""
        vim = VimMode()
        vim.enter_insert(0)
        assert vim.mode() == "INSERT"

    def test_escape_enters_normal_mode(self) -> None:
        """Escape key switches from INSERT to NORMAL mode."""
        vim = VimMode()
        vim.enter_insert(0)
        handled = vim.handle_key("escape")
        assert handled is True
        assert vim.mode() == "NORMAL"
        assert vim.is_normal() is True

    def test_insert_character(self) -> None:
        """Regular character insertion in INSERT mode."""
        vim = VimMode()
        vim.enter_insert(0)
        text_store: list[str] = [""]

        def get_text() -> str:
            return text_store[0]

        def set_text(t: str) -> None:
            text_store[0] = t

        def get_cursor() -> int:
            return len(text_store[0])

        def set_cursor(o: int) -> None:
            pass

        vim._get_text = get_text
        vim._set_text = set_text
        vim._get_cursor = get_cursor
        vim._set_cursor = set_cursor

        vim.handle_key("h")
        vim.handle_key("i")
        vim.handle_key("!")
        assert text_store[0] == "hi!"

    def test_backspace_in_insert_mode(self) -> None:
        """Backspace deletes character before cursor in INSERT mode."""
        vim = VimMode()
        vim.enter_insert(0)
        text_store: list[str] = ["hello"]

        def get_text() -> str:
            return text_store[0]

        def set_text(t: str) -> None:
            text_store[0] = t

        def get_cursor() -> int:
            return 5

        def set_cursor(o: int) -> None:
            pass

        vim._get_text = get_text
        vim._set_text = set_text
        vim._get_cursor = get_cursor
        vim._set_cursor = set_cursor

        vim.handle_key("backspace")
        assert text_store[0] == "hell"

    def test_backspace_at_start_no_change(self) -> None:
        """Backspace at position 0 does nothing."""
        vim = VimMode()
        vim.enter_insert(0)
        text_store: list[str] = ["hello"]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: 0
        vim._set_cursor = lambda o: None

        vim.handle_key("backspace")
        assert text_store[0] == "hello"


class TestVimModeNormalMode:
    """Tests for NORMAL mode operations."""

    def test_enter_normal_explicit(self) -> None:
        """enter_normal switches to NORMAL mode."""
        vim = VimMode()
        vim.enter_normal()
        assert vim.mode() == "NORMAL"

    def test_motion_l_right(self) -> None:
        """l key moves cursor right in NORMAL mode."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [3]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("l")
        assert cursor_store[0] == 4

    def test_motion_l_right_boundary(self) -> None:
        """l key at end of text stays at end."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hi"]
        cursor_store: list[int] = [2]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("l")
        # l moves to min(len(text), cursor+1) = min(2, 3) = 2 (at boundary)
        assert cursor_store[0] == 2

    def test_motion_h_left(self) -> None:
        """h key moves cursor left in NORMAL mode."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [3]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("h")
        assert cursor_store[0] == 2

    def test_motion_h_left_boundary(self) -> None:
        """h key at start of text stays at 0."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("h")
        # h moves to max(0, cursor-1) = max(0, -1) = 0
        assert cursor_store[0] == 0

    def test_motion_w_next_word(self) -> None:
        """w key moves to start of next word."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello world"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("w")
        assert cursor_store[0] == 6  # after "hello "

    def test_motion_0_line_start(self) -> None:
        """0 key moves to start of line."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [3]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("0")
        assert cursor_store[0] == 0

    def test_motion_dollar_end_of_line(self) -> None:
        """$ key moves to end of line."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("$")
        assert cursor_store[0] == 5  # len("hello")

    def test_i_enters_insert_mode(self) -> None:
        """i in NORMAL mode enters INSERT mode."""
        vim = VimMode()
        vim.enter_normal()
        vim.handle_key("i")
        assert vim.is_insert() is True

    def test_i_cursor_stays(self) -> None:
        """i in NORMAL mode keeps cursor position."""
        vim = VimMode()
        vim.enter_normal()
        cursor_store: list[int] = [3]

        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)
        vim._get_text = lambda: "hello"
        vim._set_text = lambda t: None
        vim._enter_insert = lambda o: insert_cursor.append(o)
        insert_cursor: list[int] = []

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("i")
        assert insert_cursor[0] == 3

    def test_a_appends_after_cursor(self) -> None:
        """a in NORMAL mode enters INSERT mode after cursor."""
        vim = VimMode()
        vim.enter_normal()
        cursor_store: list[int] = [2]
        insert_cursor: list[int] = []

        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)
        vim._get_text = lambda: "hello"
        vim._set_text = lambda t: None
        vim._enter_insert = lambda o: insert_cursor.append(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("a")
        assert vim.is_insert() is True
        assert insert_cursor[0] == 3

    def test_x_deletes_char(self) -> None:
        """x deletes character under cursor."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [2]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: set_text_store(t)
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_text_store(t: str) -> None:
            text_store[0] = t

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("x")
        assert text_store[0] == "helo"
        assert cursor_store[0] == 2  # clamp: min(2, max(0, 4-1)) = 2

    def test_dot_repeat_x(self) -> None:
        """Dot repeat executes x command."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello world"]
        cursor_store: list[int] = [6]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: set_text_store(t)
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_text_store(t: str) -> None:
            text_store[0] = t

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        # Delete 'w' with x
        vim.handle_key("x")
        assert text_store[0] == "hello orld"
        # cursor=6, text="hello world" (len=11), to=7, new_text="hello orld" (len=10)
        # clamp: min(6, max(0, 10-1)) = min(6, 9) = 6
        assert cursor_store[0] == 6

        # Repeat with dot - deletes character at current cursor position (6)
        vim.handle_key(".")
        assert text_store[0] == "hello rld"
        # Second x: cursor=6, text="hello orld" (len=10), to=7
        # new_text[:6] + new_text[7:] = "hello " + "rld" = "hello rld"


class TestVimModeOperators:
    """Tests for vim operators (d, c, y)."""

    def test_dw_delete_word(self) -> None:
        """dw deletes from cursor to start of next word."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello world"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: set_text_store(t)
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_text_store(t: str) -> None:
            text_store[0] = t

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("d")
        vim.handle_key("w")
        assert text_store[0] == "world"


class TestVimModeCount:
    """Tests for count prefixes (e.g., 3l, 2w)."""

    def test_count_before_motion(self) -> None:
        """Count prefix multiplies motion."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello world"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("2")
        vim.handle_key("l")
        assert cursor_store[0] == 2

    def test_count_before_word(self) -> None:
        """Count multiplies word motion."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["one two three"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("2")
        vim.handle_key("w")
        assert cursor_store[0] == 8  # after "one " + "two "


class TestVimModeFindMotions:
    """Tests for find motions (f, F, t, T)."""

    def test_f_find_character(self) -> None:
        """f finds character forward."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        vim.handle_key("f")
        vim.handle_key("l")
        assert cursor_store[0] == 2

    def test_semicolon_repeats_find_forward(self) -> None:
        """Semicolon repeats last find in forward direction."""
        vim = VimMode()
        vim.enter_normal()
        text_store: list[str] = ["hello"]
        cursor_store: list[int] = [0]

        vim._get_text = lambda: text_store[0]
        vim._set_text = lambda t: None
        vim._get_cursor = lambda: cursor_store[0]
        vim._set_cursor = lambda o: set_cursor_store(o)

        def set_cursor_store(o: int) -> None:
            cursor_store[0] = o

        # Find 'l' - first at position 2
        vim.handle_key("f")
        vim.handle_key("l")
        assert cursor_store[0] == 2

        # Semicolon at position 2 finds next 'l' at position 3
        vim.handle_key(";")
        assert cursor_store[0] == 3

        # Semicolon again - no more 'l' after position 3, stays at 3
        vim.handle_key(";")
        assert cursor_store[0] == 3
