"""Vim mode state machine for Claude Code.

Implements a vim-like input handler for the REPL with:
- INSERT mode: Normal text input
- NORMAL mode: Command keybindings (d, c, y, w, etc.)
- Text objects (iw, aw, i", a(, etc.)
- Operators (delete, change, yank)
- Motions (h, j, k, l, w, b, e, etc.)
- Counts (3w, 2dd, etc.)
- Find motions (f, F, t, T)
- Dot-repeat (.)

TypeScript equivalent: src/vim/types.ts, src/vim/motions.ts,
    src/vim/operators.ts, src/vim/textObjects.ts, src/vim/transitions.ts
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

# =============================================================================
# Constants
# =============================================================================


class Operator(StrEnum):
    """Vim operators."""

    DELETE = "delete"
    CHANGE = "change"
    YANK = "yank"


class FindType(StrEnum):
    """Vim find motion types."""

    F = "f"  # Forward find
    B = "F"  # Backward find
    T = "t"  # Forward until
    TB = "T"  # Backward until


class TextObjScope(StrEnum):
    """Vim text object scopes."""

    INNER = "inner"
    AROUND = "around"


# Delimiter pairs for text objects
DELIMITER_PAIRS: dict[str, tuple[str, str]] = {
    "(": ("(", ")"),
    ")": ("(", ")"),
    "b": ("(", ")"),
    "[": ("[", "]"),
    "]": ("[", "]"),
    "{": ("{", "}"),
    "}": ("{", "}"),
    "B": ("{", "}"),
    "<": ("<", ">"),
    ">": ("<", ">"),
    '"': ('"', '"'),
    "'": ("'", "'"),
    "`": ("`", "`"),
}

# Simple motion keys
SIMPLE_MOTIONS: frozenset[str] = frozenset({
    "h", "l", "j", "k",  # Basic movement
    "w", "b", "e",  # Word motions
    "W", "B", "E",  # WORD motions
    "0", "^", "$",  # Line positions
})

# Find keys
FIND_KEYS: frozenset[str] = frozenset({"f", "F", "t", "T"})

# Text object scopes
TEXT_OBJ_SCOPES: dict[str, TextObjScope] = {
    "i": TextObjScope.INNER,
    "a": TextObjScope.AROUND,
}

# Text object types
TEXT_OBJ_TYPES: frozenset[str] = frozenset({
    "w", "W",  # Word/WORD
    '"', "'", "`",  # Quotes
    "(", ")", "b",  # Parens
    "[", "]",  # Brackets
    "{", "}", "B",  # Braces
    "<", ">",  # Angle brackets
})

# Operators
OPERATORS: dict[str, Operator] = {
    "d": Operator.DELETE,
    "c": Operator.CHANGE,
    "y": Operator.YANK,
}

MAX_VIM_COUNT = 10000

# =============================================================================
# Vim State Types
# =============================================================================


@dataclass
class VimInsertState:
    """INSERT mode state."""

    mode: str = "INSERT"
    inserted_text: str = ""


@dataclass
class VimNormalState:
    """NORMAL mode command state."""

    type: str  # idle, count, operator, operatorCount, operatorFind, operatorTextObj,
    # find, g, operatorG, replace, indent
    op: Operator | None = None
    count: int = 1
    digits: str = ""
    find: str | None = None
    scope: TextObjScope | None = None
    dir: str | None = None  # '>' or '<' for indent


@dataclass
class PersistentVimState:
    """Persistent state across vim commands."""

    last_change: RecordedChange | None = None
    last_find: tuple[str, str] | None = None  # (type, char)
    register: str = ""
    register_is_linewise: bool = False


# =============================================================================
# Recorded Change Types
# =============================================================================

RecordedChange = dict  # Simplified: {type, op, motion, count, ...}


# =============================================================================
# Vim Mode Class
# =============================================================================


class VimMode:
    """Vim mode input handler.

    Provides INSERT and NORMAL mode with full vim-like keybindings.

    TypeScript equivalent: src/vim/ module (combined)
    """

    def __init__(
        self,
        get_text: Callable[[], str] | None = None,
        set_text: Callable[[str], None] | None = None,
        get_cursor: Callable[[], int] | None = None,
        set_cursor: Callable[[int], None] | None = None,
        enter_insert: Callable[[int], None] | None = None,
    ) -> None:
        """Initialize vim mode handler.

        Args:
            get_text: Callback to get current text.
            set_text: Callback to set current text.
            get_cursor: Callback to get cursor offset.
            set_cursor: Callback to set cursor offset.
            enter_insert: Callback to enter insert mode.
        """
        self._get_text = get_text if get_text is not None else (lambda: "")
        self._set_text = set_text if set_text is not None else (lambda t: None)
        self._get_cursor = get_cursor if get_cursor is not None else (lambda: 0)
        self._set_cursor = set_cursor if set_cursor is not None else (lambda o: None)
        self._enter_insert = enter_insert if enter_insert is not None else (lambda o: None)

        # Current mode state
        self._mode: VimInsertState | VimNormalState = VimInsertState()
        self._persistent = PersistentVimState()

        # Insert mode state
        self._inserted_text: str = ""

    # =========================================================================
    # Public API
    # =========================================================================

    def mode(self) -> str:
        """Get the current vim mode.

        Returns:
            "INSERT" or "NORMAL".
        """
        if isinstance(self._mode, VimInsertState):
            return "INSERT"
        return "NORMAL"

    def is_insert(self) -> bool:
        """Check if in INSERT mode.

        Returns:
            True if in INSERT mode.
        """
        return isinstance(self._mode, VimInsertState)

    def is_normal(self) -> bool:
        """Check if in NORMAL mode.

        Returns:
            True if in NORMAL mode.
        """
        return isinstance(self._mode, VimNormalState)

    def enter_insert(self, offset: int | None = None) -> None:
        """Enter INSERT mode.

        Args:
            offset: Optional cursor offset to insert at.
        """
        self._inserted_text = ""
        self._mode = VimInsertState(inserted_text="")
        if offset is not None:
            self._set_cursor(offset)
        self._enter_insert(offset if offset is not None else self._get_cursor())

    def enter_normal(self) -> None:
        """Enter NORMAL mode."""
        self._mode = VimNormalState(type="idle")
        self._set_cursor(self._get_cursor())

    def handle_key(self, key: str) -> bool:
        """Handle a key press.

        Args:
            key: The key pressed.

        Returns:
            True if the key was handled (no default action needed).
            False if the key should be processed normally.
        """
        if isinstance(self._mode, VimInsertState):
            return self._handle_insert(key)
        else:
            return self._handle_normal(key)

    def get_register(self) -> str:
        """Get the current register content.

        Returns:
            Register content string.
        """
        return self._persistent.register

    def get_last_find(self) -> tuple[str, str] | None:
        """Get the last find motion.

        Returns:
            Tuple of (find_type, char) or None.
        """
        return self._persistent.last_find

    # =========================================================================
    # INSERT mode handling
    # =========================================================================

    def _handle_insert(self, key: str) -> bool:
        """Handle INSERT mode key.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        if key == "escape":
            # Record inserted text for dot-repeat before exiting
            if self._inserted_text:
                self._persistent.last_change = {
                    "type": "insert",
                    "text": self._inserted_text,
                }
            self.enter_normal()
            return True

        if key == "backspace":
            # Handle backspace in insert mode
            cursor = self._get_cursor()
            if cursor > 0:
                text = self._get_text()
                new_text = text[: cursor - 1] + text[cursor:]
                self._set_text(new_text)
                self._set_cursor(cursor - 1)
                self._inserted_text = self._inserted_text[:-1]
            return True

        if len(key) == 1:
            # Regular character insertion
            cursor = self._get_cursor()
            text = self._get_text()
            new_text = text[:cursor] + key + text[cursor:]
            self._set_text(new_text)
            self._set_cursor(cursor + len(key))
            self._inserted_text += key
            return True

        return False

    # =========================================================================
    # NORMAL mode handling
    # =========================================================================

    def _handle_normal(self, key: str) -> bool:
        """Handle NORMAL mode key.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)

        if state.type == "idle":
            return self._from_idle(key)

        if state.type == "count":
            return self._from_count(key)

        if state.type == "operator":
            return self._from_operator(key)

        if state.type == "operatorCount":
            return self._from_operator_count(key)

        if state.type == "operatorFind":
            return self._from_operator_find(key)

        if state.type == "operatorTextObj":
            return self._from_operator_text_obj(key)

        if state.type == "find":
            return self._from_find(key)

        if state.type == "g":
            return self._from_g(key)

        if state.type == "operatorG":
            return self._from_operator_g(key)

        if state.type == "replace":
            return self._from_replace(key)

        if state.type == "indent":
            return self._from_indent(key)

        return False

    def _from_idle(self, key: str) -> bool:
        """Handle idle state in NORMAL mode.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        # 0 is line-start, not count
        if key == "0":
            self._set_cursor(self._line_start())
            return True

        if re.match(r"[1-9]", key):
            self._mode = VimNormalState(type="count", digits=key)
            return True

        return self._handle_normal_input(key, 1)

    def _from_count(self, key: str) -> bool:
        """Handle count state in NORMAL mode.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)

        if re.match(r"[0-9]", key):
            new_digits = state.digits + key
            count = min(int(new_digits), MAX_VIM_COUNT)
            self._mode = VimNormalState(type="count", digits=str(count))
            return True

        count = int(state.digits)
        result = self._handle_normal_input(key, count)
        if not result:
            self._mode = VimNormalState(type="idle")
        return result

    def _from_operator(self, key: str) -> bool:
        """Handle operator state in NORMAL mode.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.op is not None

        # Double-key line operation (dd, cc, yy)
        if key == state.op.value[0]:
            self._execute_line_op(state.op, state.count)
            self._mode = VimNormalState(type="idle")
            return True

        # Count prefix
        if re.match(r"[0-9]", key):
            self._mode = VimNormalState(
                type="operatorCount",
                op=state.op,
                count=state.count,
                digits=key,
            )
            return True

        return self._handle_operator_input(state.op, state.count, key)

    def _from_operator_count(self, key: str) -> bool:
        """Handle operator+count state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.op is not None

        if re.match(r"[0-9]", key):
            new_digits = state.digits + key
            parsed = min(int(new_digits), MAX_VIM_COUNT)
            self._mode = VimNormalState(
                type="operatorCount",
                op=state.op,
                count=state.count,
                digits=str(parsed),
            )
            return True

        motion_count = int(state.digits)
        effective_count = state.count * motion_count
        result = self._handle_operator_input(state.op, effective_count, key)
        if not result:
            self._mode = VimNormalState(type="idle")
        return result

    def _from_operator_find(self, key: str) -> bool:
        """Handle operator+find state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.op is not None
        assert state.find is not None

        self._execute_operator_find(state.op, state.find, key, state.count)
        self._persistent.last_find = (state.find, key)
        self._persistent.last_change = {
            "type": "operatorFind",
            "op": state.op.value,
            "find": state.find,
            "char": key,
            "count": state.count,
        }
        self._mode = VimNormalState(type="idle")
        return True

    def _from_operator_text_obj(self, key: str) -> bool:
        """Handle operator+text object state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.op is not None
        assert state.scope is not None

        if key in TEXT_OBJ_TYPES:
            self._execute_operator_text_obj(
                state.op, state.scope, key, state.count
            )
            self._persistent.last_change = {
                "type": "operatorTextObj",
                "op": state.op.value,
                "objType": key,
                "scope": state.scope.value,
                "count": state.count,
            }
            self._mode = VimNormalState(type="idle")
            return True

        self._mode = VimNormalState(type="idle")
        return False

    def _from_find(self, key: str) -> bool:
        """Handle find state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.find is not None

        target = self._find_character(key, state.find, state.count)
        if target is not None:
            self._set_cursor(target)
            self._persistent.last_find = (state.find, key)
        self._mode = VimNormalState(type="idle")
        return True

    def _from_g(self, key: str) -> bool:
        """Handle g state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)

        if key in ("j", "k"):
            target = self._resolve_motion(f"g{key}", state.count)
            self._set_cursor(target.offset)
            self._mode = VimNormalState(type="idle")
            return True

        if key == "g":
            # gg - go to first line
            if state.count > 1:
                self._set_cursor(self._go_to_line(state.count))
            else:
                self._set_cursor(self._start_of_first_line())
            self._mode = VimNormalState(type="idle")
            return True

        self._mode = VimNormalState(type="idle")
        return False

    def _from_operator_g(self, key: str) -> bool:
        """Handle operator+G state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.op is not None

        if key in ("j", "k"):
            self._execute_operator_motion(state.op, f"g{key}", state.count)
            self._mode = VimNormalState(type="idle")
            return True

        if key == "g":
            self._execute_operator_gg(state.op, state.count)
            self._mode = VimNormalState(type="idle")
            return True

        self._mode = VimNormalState(type="idle")
        return False

    def _from_replace(self, key: str) -> bool:
        """Handle replace state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)

        if key in ("escape", ""):
            self._mode = VimNormalState(type="idle")
            return True

        self._execute_replace(key, state.count)
        self._persistent.last_change = {
            "type": "replace",
            "char": key,
            "count": state.count,
        }
        self._mode = VimNormalState(type="idle")
        return True

    def _from_indent(self, key: str) -> bool:
        """Handle indent state.

        Args:
            key: The key pressed.

        Returns:
            True if handled.
        """
        state = self._mode
        assert isinstance(state, VimNormalState)
        assert state.dir is not None

        if key == state.dir:
            self._execute_indent(state.dir, state.count)
            self._persistent.last_change = {
                "type": "indent",
                "dir": state.dir,
                "count": state.count,
            }
            self._mode = VimNormalState(type="idle")
            return True

        self._mode = VimNormalState(type="idle")
        return False

    # =========================================================================
    # Shared Input Handlers
    # =========================================================================

    def _handle_normal_input(self, key: str, count: int) -> bool:
        """Handle input valid in idle state.

        Args:
            key: The key pressed.
            count: Motion count.

        Returns:
            True if handled.
        """
        # Operators
        if key in OPERATORS:
            self._mode = VimNormalState(type="operator", op=OPERATORS[key], count=count)
            return True

        # Simple motions
        if key in SIMPLE_MOTIONS:
            target = self._resolve_motion(key, count)
            self._set_cursor(target.offset)
            return True

        # Find motions
        if key in FIND_KEYS:
            self._mode = VimNormalState(type="find", find=key, count=count)
            return True

        # Special keys
        if key == "g":
            self._mode = VimNormalState(type="g", count=count)
            return True

        if key == "r":
            self._mode = VimNormalState(type="replace", count=count)
            return True

        if key in (">", "<"):
            self._mode = VimNormalState(type="indent", dir=key, count=count)
            return True

        # Single-character commands
        if key == "~":
            self._execute_toggle_case(count)
            return True

        if key == "x":
            self._execute_x(count)
            return True

        if key == "J":
            self._execute_join(count)
            return True

        if key in ("p", "P"):
            self._execute_paste(key == "p", count)
            return True

        if key == "D":
            self._execute_operator_motion(Operator.DELETE, "$", 1)
            return True

        if key == "C":
            self._execute_operator_motion(Operator.CHANGE, "$", 1)
            return True

        if key == "Y":
            self._execute_line_op(Operator.YANK, count)
            return True

        if key == "G":
            if count == 1:
                self._set_cursor(self._start_of_last_line())
            else:
                self._set_cursor(self._go_to_line(count))
            return True

        if key == ".":
            self._dot_repeat()
            return True

        if key in (";", ","):
            self._repeat_find(key == ",")
            return True

        if key == "u":
            # Undo - not fully implemented
            return True

        if key == "i":
            self.enter_insert(self._get_cursor())
            return True

        if key == "I":
            self.enter_insert(self._first_non_blank())
            return True

        if key == "a":
            cursor = self._get_cursor()
            text = self._get_text()
            if cursor < len(text):
                self.enter_insert(cursor + 1)
            else:
                self.enter_insert(cursor)
            return True

        if key == "A":
            self.enter_insert(self._line_end())
            return True

        if key == "o":
            self._open_line("below")
            return True

        if key == "O":
            self._open_line("above")
            return True

        return False

    def _handle_operator_input(
        self, op: Operator, count: int, key: str
    ) -> bool:
        """Handle input after an operator.

        Args:
            op: The operator.
            count: Motion count.
            key: The key pressed.

        Returns:
            True if handled.
        """
        # Text object scope
        if key in TEXT_OBJ_SCOPES:
            self._mode = VimNormalState(
                type="operatorTextObj",
                op=op,
                count=count,
                scope=TEXT_OBJ_SCOPES[key],
            )
            return True

        # Find motions
        if key in FIND_KEYS:
            self._mode = VimNormalState(
                type="operatorFind",
                op=op,
                count=count,
                find=key,
            )
            return True

        # Simple motions
        if key in SIMPLE_MOTIONS:
            self._execute_operator_motion(op, key, count)
            self._mode = VimNormalState(type="idle")
            return True

        if key == "G":
            self._execute_operator_g(op, count)
            self._mode = VimNormalState(type="idle")
            return True

        if key == "g":
            self._mode = VimNormalState(type="operatorG", op=op, count=count)
            return True

        return False

    # =========================================================================
    # Motion Resolution
    # =========================================================================

    def _resolve_motion(self, key: str, count: int) -> MotionResult:
        """Resolve a motion to a target cursor position.

        Args:
            key: Motion key.
            count: Repeat count.

        Returns:
            MotionResult with target offset.
        """
        cursor = self._get_cursor()
        text = self._get_text()

        for _ in range(count):
            next_cursor = self._apply_single_motion(key, cursor, text)
            if next_cursor == cursor:
                break
            cursor = next_cursor

        return MotionResult(cursor)

    def _apply_single_motion(self, key: str, cursor: int, text: str) -> int:
        """Apply a single motion step.

        Args:
            key: Motion key.
            cursor: Current cursor offset.
            text: Current text.

        Returns:
            New cursor offset.
        """
        if key == "h":
            return max(0, cursor - 1)
        if key == "l":
            return min(len(text), cursor + 1)
        if key == "j":
            return self._down_logical_line(cursor, text)
        if key == "k":
            return self._up_logical_line(cursor, text)
        if key == "w":
            return self._next_word(cursor, text)
        if key == "b":
            return self._prev_word(cursor, text)
        if key == "e":
            return self._end_of_word(cursor, text)
        if key == "W":
            return self._next_WORD(cursor, text)
        if key == "B":
            return self._prev_WORD(cursor, text)
        if key == "E":
            return self._end_of_WORD(cursor, text)
        if key == "0":
            return self._line_start()
        if key == "^":
            return self._first_non_blank()
        if key == "$":
            return self._line_end()
        if key == "gj":
            return self._down(cursor, text)
        if key == "gk":
            return self._up(cursor, text)
        return cursor

    def _is_word_char(self, ch: str) -> bool:
        """Check if a character is a vim word character."""
        return ch.isalnum() or ch == "_"

    def _is_whitespace(self, ch: str) -> bool:
        """Check if a character is whitespace."""
        return ch.isspace()

    def _next_word(self, cursor: int, text: str) -> int:
        """Move to the start of the next word."""
        n = len(text)
        if cursor >= n:
            return n
        # Skip current word
        while cursor < n and self._is_word_char(text[cursor]):
            cursor += 1
        # Skip whitespace
        while cursor < n and self._is_whitespace(text[cursor]):
            cursor += 1
        return min(cursor, n)

    def _prev_word(self, cursor: int, text: str) -> int:
        """Move to the start of the previous word."""
        if cursor <= 0:
            return 0
        cursor -= 1
        # Skip current word
        while cursor > 0 and self._is_whitespace(text[cursor]):
            cursor -= 1
        while cursor > 0 and self._is_word_char(text[cursor - 1]):
            cursor -= 1
        return max(0, cursor)

    def _end_of_word(self, cursor: int, text: str) -> int:
        """Move to the end of the current word."""
        n = len(text)
        if cursor >= n:
            return n
        # Skip current word
        while cursor < n and self._is_word_char(text[cursor]):
            cursor += 1
        # Skip whitespace
        while cursor < n and self._is_whitespace(text[cursor]):
            cursor += 1
        # Go back to end of word
        while cursor > 0 and cursor < n and self._is_word_char(text[cursor - 1]):
            cursor += 1
        return min(cursor, n)

    def _next_WORD(self, cursor: int, text: str) -> int:
        """Move to the start of the next WORD (non-whitespace)."""
        n = len(text)
        if cursor >= n:
            return n
        while cursor < n and not self._is_whitespace(text[cursor]):
            cursor += 1
        while cursor < n and self._is_whitespace(text[cursor]):
            cursor += 1
        return min(cursor, n)

    def _prev_WORD(self, cursor: int, text: str) -> int:
        """Move to the start of the previous WORD."""
        if cursor <= 0:
            return 0
        cursor -= 1
        while cursor > 0 and self._is_whitespace(text[cursor]):
            cursor -= 1
        while cursor > 0 and not self._is_whitespace(text[cursor - 1]):
            cursor -= 1
        return max(0, cursor)

    def _end_of_WORD(self, cursor: int, text: str) -> int:
        """Move to the end of the current WORD."""
        n = len(text)
        if cursor >= n:
            return n
        while cursor < n and not self._is_whitespace(text[cursor]):
            cursor += 1
        return min(cursor, n)

    def _down_logical_line(self, cursor: int, text: str) -> int:
        """Move down by logical lines (newline-separated)."""
        lines = text.split("\n")
        current_line = text[:cursor].count("\n")
        if current_line >= len(lines) - 1:
            return len(text)
        # Find position in next line
        current_col = cursor - text[:cursor].rfind("\n") - 1
        next_line_start = cursor + text[cursor:].find("\n") + 1
        next_line = lines[current_line + 1] if current_line + 1 < len(lines) else ""
        return min(next_line_start + min(current_col, len(next_line)), len(text))

    def _up_logical_line(self, cursor: int, text: str) -> int:
        """Move up by logical lines."""
        current_line = text[:cursor].count("\n")
        if current_line == 0:
            return 0
        lines = text.split("\n")
        current_col = cursor - text[:cursor].rfind("\n") - 1
        prev_line_start = text[:cursor].rfind("\n") + 1
        prev_line = lines[current_line - 1] if current_line > 0 else ""
        return prev_line_start + min(current_col, len(prev_line))

    def _down(self, cursor: int, text: str) -> int:
        """Move down (visual line)."""
        return self._down_logical_line(cursor, text)

    def _up(self, cursor: int, text: str) -> int:
        """Move up (visual line)."""
        return self._up_logical_line(cursor, text)

    def _line_start(self) -> int:
        """Move to start of logical line."""
        text = self._get_text()
        cursor = self._get_cursor()
        last_newline = text.rfind("\n", 0, cursor)
        return last_newline + 1 if last_newline >= 0 else 0

    def _first_non_blank(self) -> int:
        """Move to first non-blank in logical line."""
        text = self._get_text()
        line_start = self._line_start()
        i = line_start
        while i < len(text) and text[i] in " \t":
            i += 1
        return i

    def _line_end(self) -> int:
        """Move to end of logical line."""
        text = self._get_text()
        cursor = self._get_cursor()
        next_newline = text.find("\n", cursor)
        return next_newline if next_newline >= 0 else len(text)

    def _start_of_first_line(self) -> int:
        """Move to start of first line."""
        return 0

    def _start_of_last_line(self) -> int:
        """Move to start of last line."""
        text = self._get_text()
        last_newline = text.rfind("\n")
        return last_newline + 1 if last_newline >= 0 else 0

    def _go_to_line(self, line_num: int) -> int:
        """Go to the start of a specific line number (1-indexed)."""
        text = self._get_text()
        lines = text.split("\n")
        target = max(0, min(line_num - 1, len(lines) - 1))
        offset = sum(len(lines[i]) + 1 for i in range(target))
        return min(offset, len(text))

    # =========================================================================
    # Find Operations
    # =========================================================================

    def _find_character(
        self, char: str, find_type: str, count: int
    ) -> int | None:
        """Find a character in the text.

        Args:
            char: Character to find.
            find_type: f, F, t, or T.
            count: Repeat count.

        Returns:
            Target offset or None if not found.
        """
        text = self._get_text()
        cursor = self._get_cursor()

        if find_type == "f":
            for _ in range(count):
                idx = text.find(char, cursor + 1)
                if idx < 0:
                    return None
                cursor = idx
            return cursor

        if find_type == "F":
            for _ in range(count):
                idx = text.rfind(char, 0, cursor)
                if idx < 0:
                    return None
                cursor = idx
            return cursor

        if find_type == "t":
            for _ in range(count):
                idx = text.find(char, cursor + 1)
                if idx < 0:
                    return None
                cursor = idx - 1
            return max(0, cursor)

        if find_type == "T":
            for _ in range(count):
                idx = text.rfind(char, 0, cursor)
                if idx < 0:
                    return None
                cursor = idx + 1
            return min(cursor, len(text))

        return None

    def _repeat_find(self, reverse: bool) -> None:
        """Repeat the last find motion.

        Args:
            reverse: If True, reverse the direction.
        """
        last_find = self._persistent.last_find
        if not last_find:
            return

        find_type, char = last_find
        if reverse:
            flip = {"f": "F", "F": "f", "t": "T", "T": "t"}
            find_type = flip.get(find_type, find_type)

        target = self._find_character(char, find_type, 1)
        if target is not None:
            self._set_cursor(target)

    # =========================================================================
    # Operator Execution
    # =========================================================================

    def _execute_operator_motion(
        self, op: Operator, motion: str, count: int
    ) -> None:
        """Execute an operator with a motion.

        Args:
            op: The operator.
            motion: The motion key.
            count: Motion count.
        """
        cursor = self._get_cursor()
        text = self._get_text()
        target = self._resolve_motion(motion, count)
        target_off = target.offset

        if target_off == cursor:
            return

        frm = min(cursor, target_off)
        to = max(cursor, target_off)

        # Inclusive motions
        if motion in ("e", "E", "$"):
            to = min(to + 1, len(text))

        # Linewise motions
        if motion in ("j", "k", "G") or motion == "gg":
            # For simplicity, treat as linewise
            pass

        self._apply_operator_range(op, frm, to)

    def _execute_line_op(self, op: Operator, count: int) -> None:
        """Execute a line operation (dd, cc, yy).

        Args:
            op: The operator.
            count: Number of lines.
        """
        text = self._get_text()
        cursor = self._get_cursor()
        lines = text.split("\n")
        current_line = text[:cursor].count("\n")
        lines_to_affect = min(count, len(lines) - current_line)
        line_start = self._line_start()

        # Find end of lines to affect
        line_end = line_start
        for _ in range(lines_to_affect):
            next_newline = text.find("\n", line_end)
            line_end = next_newline + 1 if next_newline >= 0 else len(text)

        content = text[line_start:line_end]
        if not content.endswith("\n"):
            content += "\n"

        self._persistent.register = content
        self._persistent.register_is_linewise = True

        if op == Operator.YANK:
            self._set_cursor(line_start)
        elif op == Operator.DELETE:
            new_text = text[:line_start] + text[line_end:]
            self._set_text(new_text)
            self._set_cursor(min(line_start, max(0, len(new_text) - 1)))
        elif op == Operator.CHANGE:
            new_text = text[:line_start] + text[line_end:]
            self._set_text(new_text)
            self.enter_insert(line_start)

    def _execute_operator_find(
        self, op: Operator, find_type: str, char: str, count: int
    ) -> None:
        """Execute an operator with a find motion.

        Args:
            op: The operator.
            find_type: f, F, t, or T.
            char: Character to find.
            count: Repeat count.
        """
        cursor = self._get_cursor()
        target = self._find_character(char, find_type, count)
        if target is None:
            return

        frm = min(cursor, target)
        to = max(cursor, target)

        # t/T are exclusive (don't include target char)
        if find_type in ("t", "T"):
            to = max(0, to - 1) if target > cursor else to + 1

        self._apply_operator_range(op, frm, to)

    def _execute_operator_text_obj(
        self, op: Operator, scope: TextObjScope, obj_type: str, count: int
    ) -> None:
        """Execute an operator with a text object.

        Args:
            op: The operator.
            scope: Inner or around.
            obj_type: The text object type.
            count: Repeat count.
        """
        text = self._get_text()
        cursor = self._get_cursor()

        range_ = self._find_text_object(text, cursor, obj_type, scope == TextObjScope.INNER)
        if range_ is None:
            return

        self._apply_operator_range(op, range_.start, range_.end)

    def _execute_operator_g(self, op: Operator, count: int) -> None:
        """Execute an operator with G motion.

        Args:
            op: The operator.
            count: Line number or 1 for end of file.
        """
        target_off = self._start_of_last_line() if count == 1 else self._go_to_line(count)

        cursor = self._get_cursor()
        frm = min(cursor, target_off)
        to = max(cursor, target_off)
        self._apply_operator_range(op, frm, to)

    def _execute_operator_gg(self, op: Operator, count: int) -> None:
        """Execute an operator with gg motion.

        Args:
            op: The operator.
            count: Line number or 1 for first line.
        """
        target_off = 0 if count == 1 else self._go_to_line(count)

        cursor = self._get_cursor()
        frm = min(cursor, target_off)
        to = max(cursor, target_off)
        self._apply_operator_range(op, frm, to)

    def _apply_operator_range(
        self, op: Operator, frm: int, to: int
    ) -> None:
        """Apply an operator to a range.

        Args:
            op: The operator.
            frm: Start offset (inclusive).
            to: End offset (exclusive).
        """
        text = self._get_text()
        content = text[frm:to]
        self._persistent.register = content
        self._persistent.register_is_linewise = False

        if op == Operator.YANK:
            self._set_cursor(frm)
        elif op == Operator.DELETE:
            new_text = text[:frm] + text[to:]
            self._set_text(new_text)
            self._set_cursor(min(frm, max(0, len(new_text) - 1)))
        elif op == Operator.CHANGE:
            new_text = text[:frm] + text[to:]
            self._set_text(new_text)
            self.enter_insert(frm)

    def _execute_x(self, count: int) -> None:
        """Execute x command (delete character).

        Args:
            count: Number of characters.
        """
        cursor = self._get_cursor()
        text = self._get_text()
        to = min(cursor + count, len(text))
        if cursor >= len(text):
            return

        deleted = text[cursor:to]
        new_text = text[:cursor] + text[to:]
        self._set_text(new_text)
        self._persistent.register = deleted
        self._set_cursor(min(cursor, max(0, len(new_text) - 1)))
        self._persistent.last_change = {"type": "x", "count": count}

    def _execute_replace(self, char: str, count: int) -> None:
        """Execute r command (replace character).

        Args:
            char: Replacement character.
            count: Number of replacements.
        """
        cursor = self._get_cursor()
        text = self._get_text()
        for _ in range(count):
            if cursor >= len(text):
                break
            text = text[:cursor] + char + text[cursor + 1 :]
            cursor += 1
        self._set_text(text)
        self._set_cursor(max(0, cursor - 1))
        self._persistent.last_change = {"type": "replace", "char": char, "count": count}

    def _execute_toggle_case(self, count: int) -> None:
        """Execute ~ command (toggle case).

        Args:
            count: Number of characters.
        """
        cursor = self._get_cursor()
        text = self._get_text()
        toggled = 0
        i = cursor
        while i < len(text) and toggled < count:
            ch = text[i]
            if ch.isalpha():
                text = text[:i] + ch.swapcase() + text[i + 1 :]
                toggled += 1
            i += 1
        self._set_text(text)
        self._set_cursor(i)
        self._persistent.last_change = {"type": "toggleCase", "count": count}

    def _execute_join(self, count: int) -> None:
        """Execute J command (join lines).

        Args:
            count: Number of joins.
        """
        text = self._get_text()
        cursor = self._get_cursor()
        current_line = text[:cursor].count("\n")
        lines = text.split("\n")
        if current_line >= len(lines) - 1:
            return

        lines_to_join = min(count, len(lines) - current_line - 1)
        joined = lines[current_line]
        for i in range(1, lines_to_join + 1):
            next_line = lines[current_line + i].lstrip()
            if next_line:
                if not joined.endswith(" ") and joined:
                    joined += " "
                joined += next_line

        new_lines = lines[:current_line] + [joined] + lines[current_line + lines_to_join + 1 :]
        new_text = "\n".join(new_lines)
        self._set_text(new_text)
        # Position cursor at end of joined line
        new_cursor = sum(len(new_lines[j]) + 1 for j in range(current_line)) + len(joined) - 1
        self._set_cursor(max(0, new_cursor))
        self._persistent.last_change = {"type": "join", "count": count}

    def _execute_paste(self, after: bool, count: int) -> None:
        """Execute p or P command (paste).

        Args:
            after: If True, paste after cursor.
            count: Number of pastes.
        """
        register = self._persistent.register
        if not register:
            return

        is_linewise = register.endswith("\n")
        content = register[:-1] if is_linewise else register

        text = self._get_text()
        cursor = self._get_cursor()

        if is_linewise:
            lines = text.split("\n")
            current_line = text[:cursor].count("\n")
            insert_line = current_line + 1 if after else current_line
            new_lines = lines[:insert_line] + [content] + lines[insert_line:]
            new_text = "\n".join(new_lines)
            new_cursor = sum(len(new_lines[i]) + 1 for i in range(insert_line))
        else:
            insert_point = cursor + 1 if after and cursor < len(text) else cursor
            new_text = text[:insert_point] + content + text[insert_point:]
            new_cursor = insert_point + len(content) - 1

        self._set_text(new_text)
        self._set_cursor(max(0, new_cursor))
        self._persistent.last_change = {"type": "paste", "after": after, "count": count}

    def _execute_indent(self, direction: str, count: int) -> None:
        """Execute > or < command (indent).

        Args:
            direction: '>' to indent, '<' to dedent.
            count: Number of indent levels.
        """
        text = self._get_text()
        cursor = self._get_cursor()
        current_line = text[:cursor].count("\n")
        lines = text.split("\n")
        lines_to_affect = min(count, len(lines) - current_line)
        indent = "  "

        for i in range(lines_to_affect):
            line_idx = current_line + i
            line = lines[line_idx]
            if direction == ">":
                lines[line_idx] = indent + line
            else:
                if line.startswith(indent):
                    lines[line_idx] = line[len(indent) :]
                elif line.startswith("\t"):
                    lines[line_idx] = line[1:]
                else:
                    # Remove leading whitespace up to indent length
                    removed = 0
                    j = 0
                    while j < len(line) and removed < len(indent) and line[j].isspace():
                        removed += 1
                        j += 1
                    lines[line_idx] = line[j:]

        new_text = "\n".join(lines)
        self._set_text(new_text)
        self._set_cursor(cursor)

    def _open_line(self, direction: str) -> None:
        """Execute o or O command (open line).

        Args:
            direction: 'above' or 'below'.
        """
        text = self._get_text()
        cursor = self._get_cursor()
        current_line = text[:cursor].count("\n")
        lines = text.split("\n")

        insert_line = current_line + 1 if direction == "below" else current_line
        new_lines = lines[:insert_line] + [""] + lines[insert_line:]
        new_text = "\n".join(new_lines)
        new_cursor = sum(len(new_lines[i]) + 1 for i in range(insert_line))
        self._set_text(new_text)
        self.enter_insert(new_cursor)
        self._persistent.last_change = {"type": "openLine", "direction": direction}

    def _dot_repeat(self) -> None:
        """Execute . command (repeat last change)."""
        last = self._persistent.last_change
        if not last:
            return

        change_type = last.get("type")
        if change_type == "insert":
            text = last["text"]
            cursor = self._get_cursor()
            new_text = self._get_text()[:cursor] + text + self._get_text()[cursor:]
            self._set_text(new_text)
            self._set_cursor(cursor + len(text))
        elif change_type == "operator":
            self._execute_operator_motion(
                Operator(last["op"]), last["motion"], last.get("count", 1)
            )
        elif change_type == "operatorTextObj":
            self._execute_operator_text_obj(
                Operator(last["op"]),
                TextObjScope(last["scope"]),
                last["objType"],
                last.get("count", 1),
            )
        elif change_type == "operatorFind":
            self._execute_operator_find(
                Operator(last["op"]),
                last["find"],
                last["char"],
                last.get("count", 1),
            )
        elif change_type == "replace":
            self._execute_replace(last["char"], last.get("count", 1))
        elif change_type == "x":
            self._execute_x(last.get("count", 1))
        elif change_type == "toggleCase":
            self._execute_toggle_case(last.get("count", 1))
        elif change_type == "indent":
            self._execute_indent(last["dir"], last.get("count", 1))
        elif change_type == "openLine":
            self._open_line(last["direction"])
        elif change_type == "join":
            self._execute_join(last.get("count", 1))

    # =========================================================================
    # Text Objects
    # =========================================================================

    def _find_text_object(
        self, text: str, offset: int, obj_type: str, is_inner: bool
    ) -> TextObjRange | None:
        """Find a text object at the given position.

        Args:
            text: The text to search.
            offset: Current cursor offset.
            obj_type: Text object type (w, W, ", ', etc.).
            is_inner: If True, find inner (exclude delimiters).

        Returns:
            TextObjRange with start/end or None.
        """
        if obj_type == "w":
            return self._find_word_object(text, offset, is_inner)

        if obj_type == "W":
            return self._find_WORD_object(text, offset, is_inner)

        pair = DELIMITER_PAIRS.get(obj_type)
        if not pair:
            return None

        open_delim, close_delim = pair
        if open_delim == close_delim:
            return self._find_quote_object(text, offset, open_delim, is_inner)
        else:
            return self._find_bracket_object(text, offset, open_delim, close_delim, is_inner)

    def _find_word_object(
        self, text: str, offset: int, is_inner: bool
    ) -> TextObjRange | None:
        """Find a word text object."""
        n = len(text)
        if offset < 0 or offset >= n:
            return None

        def is_word(ch: str) -> bool:
            return ch.isalnum() or ch == "_"

        def is_ws(ch: str) -> bool:
            return ch.isspace()

        def is_punct(ch: str) -> bool:
            return ch in ".,!?;:'\"()-[]{}"

        start = offset
        end = offset

        if is_word(text[offset]):
            while start > 0 and is_word(text[start - 1]):
                start -= 1
            while end < n and is_word(text[end]):
                end += 1
        elif is_ws(text[offset]):
            while start > 0 and is_ws(text[start - 1]):
                start -= 1
            while end < n and is_ws(text[end]):
                end += 1
            return TextObjRange(start=start, end=end)
        elif is_punct(text[offset]):
            while start > 0 and is_punct(text[start - 1]):
                start -= 1
            while end < n and is_punct(text[end]):
                end += 1

        if not is_inner:
            # Include surrounding whitespace
            while end < n and is_ws(text[end]):
                end += 1
            while start > 0 and is_ws(text[start - 1]):
                start -= 1

        return TextObjRange(start=start, end=end)

    def _find_WORD_object(
        self, text: str, offset: int, is_inner: bool
    ) -> TextObjRange | None:
        """Find a WORD text object (non-whitespace sequences)."""
        n = len(text)

        def is_ws(ch: str) -> bool:
            return ch.isspace()

        if offset < 0 or offset >= n:
            return None

        start = offset
        end = offset

        if not is_ws(text[offset]):
            while start > 0 and not is_ws(text[start - 1]):
                start -= 1
            while end < n and not is_ws(text[end]):
                end += 1
        else:
            while start > 0 and is_ws(text[start - 1]):
                start -= 1
            while end < n and is_ws(text[end]):
                end += 1

        if not is_inner:
            while end < n and is_ws(text[end]):
                end += 1
            while start > 0 and is_ws(text[start - 1]):
                start -= 1

        return TextObjRange(start=start, end=end)

    def _find_quote_object(
        self, text: str, offset: int, quote: str, is_inner: bool
    ) -> TextObjRange | None:
        """Find a quote text object."""
        line_start = text.rfind("\n", 0, offset) + 1
        line_end = text.find("\n", offset)
        effective_end = line_end if line_end >= 0 else len(text)
        line = text[line_start:effective_end]
        pos_in_line = offset - line_start

        positions = [i for i, ch in enumerate(line) if ch == quote]
        for i in range(0, len(positions) - 1, 2):
            qs = positions[i]
            qe = positions[i + 1]
            if qs <= pos_in_line <= qe:
                if is_inner:
                    return TextObjRange(
                        start=line_start + qs + 1, end=line_start + qe
                    )
                else:
                    return TextObjRange(
                        start=line_start + qs, end=line_start + qe + 1
                    )

        return None

    def _find_bracket_object(
        self,
        text: str,
        offset: int,
        open_d: str,
        close_d: str,
        is_inner: bool,
    ) -> TextObjRange | None:
        """Find a bracket text object."""
        n = len(text)

        # Find opening bracket
        depth = 0
        start = -1
        for i in range(offset, -1, -1):
            if text[i] == close_d and i != offset:
                depth += 1
            elif text[i] == open_d:
                if depth == 0:
                    start = i
                    break
                depth -= 1
        if start == -1:
            return None

        # Find closing bracket
        depth = 0
        end = -1
        for i in range(start + 1, n):
            if text[i] == open_d:
                depth += 1
            elif text[i] == close_d:
                if depth == 0:
                    end = i
                    break
                depth -= 1
        if end == -1:
            return None

        if is_inner:
            return TextObjRange(start=start + 1, end=end)
        else:
            return TextObjRange(start=start, end=end + 1)


# =============================================================================
# Helper Classes
# =============================================================================


@dataclass
class MotionResult:
    """Result of a motion resolution."""

    offset: int


@dataclass
class TextObjRange:
    """Range returned by text object finding."""

    start: int
    end: int
