"""
Tests for ui/keybindings.py - Keyboard binding system.
"""

from __future__ import annotations

import pytest

from claude_code.ui.keybindings import (
    BindingContext,
    KeyBinding,
    KeyBindingManager,
    KeyName,
    KeyType,
    Modifier,
    ParsedKey,
    chord_keys,
    get_binding_manager,
    normalize_key,
    parse_chord,
    parse_key,
    register_binding,
    reset_binding_manager,
    unregister_binding,
)


# =============================================================================
# Key Utilities Tests
# =============================================================================


class TestNormalizeKey:
    """Tests for normalize_key()."""

    def test_simple_keys(self) -> None:
        """normalize_key handles simple keys."""
        assert normalize_key("enter") == "enter"
        assert normalize_key("escape") == "escape"
        assert normalize_key("backspace") == "backspace"
        assert normalize_key("delete") == "delete"

    def test_arrow_keys(self) -> None:
        """normalize_key handles arrow keys."""
        assert normalize_key("up") == "up"
        assert normalize_key("down") == "down"
        assert normalize_key("left") == "left"
        assert normalize_key("right") == "right"

    def test_case_insensitive(self) -> None:
        """normalize_key is case insensitive."""
        assert normalize_key("Enter") == "enter"
        assert normalize_key("ESCAPE") == "escape"
        assert normalize_key("Up") == "up"

    def test_ctrl_keys(self) -> None:
        """normalize_key handles Ctrl modifiers."""
        assert normalize_key("ctrl+c") == "ctrl+c"
        assert normalize_key("Ctrl+C") == "ctrl+c"
        assert normalize_key("^c") == "ctrl+c"

    def test_shift_keys(self) -> None:
        """normalize_key handles Shift modifiers."""
        assert normalize_key("shift+tab") == "shift+tab"
        assert normalize_key("Shift+Tab") == "shift+tab"

    def test_alt_keys(self) -> None:
        """normalize_key handles Alt modifiers."""
        assert normalize_key("alt+x") == "alt+x"
        assert normalize_key("alt+enter") == "alt+enter"

    def test_function_keys(self) -> None:
        """normalize_key handles function keys."""
        assert normalize_key("f1") == "f1"
        assert normalize_key("F12") == "f12"

    def test_special_names(self) -> None:
        """normalize_key handles special key names."""
        assert normalize_key("space") == "space"
        assert normalize_key("tab") == "tab"
        assert normalize_key("home") == "home"
        assert normalize_key("end") == "end"


class TestParseKey:
    """Tests for parse_key()."""

    def test_simple_key(self) -> None:
        """parse_key parses simple keys."""
        result = parse_key("enter")
        assert result.key == "enter"
        assert result.modifiers == []

    def test_ctrl_modifier(self) -> None:
        """parse_key extracts Ctrl modifier."""
        result = parse_key("ctrl+c")
        assert result.key == "c"
        assert Modifier.CTRL in result.modifiers

    def test_shift_modifier(self) -> None:
        """parse_key extracts Shift modifier."""
        result = parse_key("shift+tab")
        assert result.key == "tab"
        assert Modifier.SHIFT in result.modifiers

    def test_alt_modifier(self) -> None:
        """parse_key extracts Alt modifier."""
        result = parse_key("alt+x")
        assert result.key == "x"
        assert Modifier.ALT in result.modifiers

    def test_multiple_modifiers(self) -> None:
        """parse_key extracts multiple modifiers."""
        result = parse_key("ctrl+shift+s")
        assert result.key == "s"
        assert Modifier.CTRL in result.modifiers
        assert Modifier.SHIFT in result.modifiers

    def test_case_normalization(self) -> None:
        """parse_key normalizes case."""
        result = parse_key("Ctrl+C")
        assert result.key == "c"
        assert Modifier.CTRL in result.modifiers


class TestParseChord:
    """Tests for parse_chord()."""

    def test_no_chord(self) -> None:
        """parse_chord returns single key for non-chord."""
        result = parse_chord("enter")
        assert len(result) == 1
        assert result[0].key == "enter"

    def test_two_key_chord(self) -> None:
        """parse_chord parses two-key sequences."""
        result = parse_chord("ctrl+c")
        assert len(result) == 2
        assert result[0].key == "ctrl"
        assert result[1].key == "c"
        assert Modifier.CTRL in result[1].modifiers

    def test_three_key_chord(self) -> None:
        """parse_chord parses three-key sequences."""
        result = parse_chord("ctrl+shift+c")
        assert len(result) == 3
        assert result[2].key == "c"
        assert Modifier.CTRL in result[2].modifiers
        assert Modifier.SHIFT in result[2].modifiers


class TestChordKeys:
    """Tests for chord_keys()."""

    def test_single_key(self) -> None:
        """chord_keys returns key for single key."""
        assert chord_keys(ParsedKey(key="enter")) == "enter"

    def test_chord(self) -> None:
        """chord_keys joins keys with +."""
        k1 = parse_key("ctrl")
        k2 = parse_key("c")
        assert chord_keys(k1, k2) == "ctrl+c"


# =============================================================================
# KeyBinding Tests
# =============================================================================


class TestKeyBindingInit:
    """Tests for KeyBinding initialization."""

    def test_required_fields(self) -> None:
        """KeyBinding requires action, key, and handler."""
        binding = KeyBinding(action="quit", key="ctrl+q", handler=lambda: None)
        assert binding.action == "quit"
        assert binding.key == "ctrl+q"
        assert binding.is_active is True
        assert binding.priority == 0

    def test_context_normalization(self) -> None:
        """Context is normalized to list."""
        b1 = KeyBinding(action="a", key="x", handler=lambda: None, context=BindingContext.DIALOG)
        assert b1.contexts == [BindingContext.DIALOG]

        b2 = KeyBinding(
            action="a",
            key="x",
            handler=lambda: None,
            context=[BindingContext.DIALOG, BindingContext.MODAL],
        )
        assert b2.contexts == [BindingContext.DIALOG, BindingContext.MODAL]

    def test_global_context(self) -> None:
        """GLOBAL context means active in all contexts."""
        binding = KeyBinding(action="a", key="x", handler=lambda: None)
        assert binding.can_fire_in(BindingContext.DIALOG) is True
        assert binding.can_fire_in(BindingContext.NORMAL) is True
        assert binding.can_fire_in(BindingContext.SEARCH) is True

    def test_when_condition(self) -> None:
        """when condition controls whether binding fires."""
        active: list[bool] = [True]

        binding = KeyBinding(
            action="a",
            key="x",
            handler=lambda: None,
            context=BindingContext.DIALOG,
            when=lambda: active[0],
        )

        assert binding.can_fire_in(BindingContext.DIALOG) is True
        active[0] = False
        assert binding.can_fire_in(BindingContext.DIALOG) is False


class TestKeyBindingMatches:
    """Tests for KeyBinding.matches()."""

    def setup_method(self) -> None:
        """Create a binding for tests."""
        self.binding = KeyBinding(
            action="quit",
            key="ctrl+q",
            handler=lambda: True,
            context=BindingContext.DIALOG,
        )

    def test_matches_key_and_context(self) -> None:
        """matches returns True when key and context match."""
        assert self.binding.matches("ctrl+q", BindingContext.DIALOG) is True

    def test_no_match_wrong_key(self) -> None:
        """matches returns False for wrong key."""
        assert self.binding.matches("ctrl+c", BindingContext.DIALOG) is False

    def test_no_match_wrong_context(self) -> None:
        """matches returns False for wrong context."""
        assert self.binding.matches("ctrl+q", BindingContext.NORMAL) is False

    def test_global_context_matches_any(self) -> None:
        """GLOBAL binding matches any context."""
        global_binding = KeyBinding(
            action="help",
            key="f1",
            handler=lambda: True,
        )
        assert global_binding.matches("f1", BindingContext.NORMAL) is True
        assert global_binding.matches("f1", BindingContext.DIALOG) is True

    def test_inactive_binding(self) -> None:
        """Inactive binding never matches."""
        self.binding.is_active = False
        assert self.binding.matches("ctrl+q", BindingContext.DIALOG) is False

    def test_when_condition_blocks_match(self) -> None:
        """when condition blocks matches when False."""
        self.binding.when = lambda: False
        assert self.binding.matches("ctrl+q", BindingContext.DIALOG) is False


# =============================================================================
# KeyBindingManager Tests
# =============================================================================


class TestKeyBindingManagerRegister:
    """Tests for KeyBindingManager registration."""

    def test_register_single(self) -> None:
        """register() adds a binding."""
        mgr = KeyBindingManager()
        binding = KeyBinding(action="quit", key="ctrl+q", handler=lambda: True)
        mgr.register(binding)
        assert len(mgr.get_all_bindings()) == 1

    def test_register_replaces_same_action(self) -> None:
        """register() replaces existing binding with same action."""
        mgr = KeyBindingManager()
        b1 = KeyBinding(action="quit", key="ctrl+q", handler=lambda: True)
        b2 = KeyBinding(action="quit", key="ctrl+x", handler=lambda: True)
        mgr.register(b1)
        mgr.register(b2)
        assert len(mgr.get_all_bindings()) == 1
        assert mgr.get_binding("quit").key == "ctrl+x"

    def test_register_many(self) -> None:
        """register_many() adds multiple bindings."""
        mgr = KeyBindingManager()
        bindings = [
            KeyBinding(action="a", key="a", handler=lambda: True),
            KeyBinding(action="b", key="b", handler=lambda: True),
        ]
        mgr.register_many(bindings)
        assert len(mgr.get_all_bindings()) == 2

    def test_unregister(self) -> None:
        """unregister() removes a binding by action."""
        mgr = KeyBindingManager()
        binding = KeyBinding(action="quit", key="ctrl+q", handler=lambda: True)
        mgr.register(binding)
        assert mgr.unregister("quit") is True
        assert len(mgr.get_all_bindings()) == 0
        assert mgr.unregister("nonexistent") is False

    def test_unregister_all(self) -> None:
        """unregister_all() clears all bindings."""
        mgr = KeyBindingManager()
        mgr.register_many([
            KeyBinding(action="a", key="a", handler=lambda: True),
            KeyBinding(action="b", key="b", handler=lambda: True),
        ])
        count = mgr.unregister_all()
        assert count == 2
        assert len(mgr.get_all_bindings()) == 0

    def test_unregister_by_context(self) -> None:
        """unregister_by_context() removes bindings in a context."""
        mgr = KeyBindingManager()
        mgr.register_many([
            KeyBinding(action="a", key="a", handler=lambda: True, context=BindingContext.DIALOG),
            KeyBinding(action="b", key="b", handler=lambda: True, context=BindingContext.NORMAL),
            KeyBinding(action="c", key="c", handler=lambda: True, context=BindingContext.DIALOG),
        ])
        count = mgr.unregister_by_context(BindingContext.DIALOG)
        assert count == 2
        assert len(mgr.get_all_bindings()) == 1


class TestKeyBindingManagerLookup:
    """Tests for KeyBindingManager lookup methods."""

    def setup_method(self) -> None:
        """Create manager with test bindings."""
        self.mgr = KeyBindingManager()
        self.mgr.register_many([
            KeyBinding(action="quit", key="ctrl+q", handler=lambda: True, context=BindingContext.DIALOG),
            KeyBinding(action="help", key="f1", handler=lambda: True),
            KeyBinding(action="nav_up", key="up", handler=lambda: True, context=BindingContext.DIALOG),
            KeyBinding(action="nav_down", key="down", handler=lambda: True, context=BindingContext.DIALOG),
        ])

    def test_get_binding(self) -> None:
        """get_binding() finds by action."""
        binding = self.mgr.get_binding("help")
        assert binding is not None
        assert binding.key == "f1"

    def test_get_binding_missing(self) -> None:
        """get_binding() returns None for missing action."""
        assert self.mgr.get_binding("missing") is None

    def test_get_bindings_for_context(self) -> None:
        """get_bindings_for_context() returns relevant bindings."""
        bindings = self.mgr.get_bindings_for_context(BindingContext.DIALOG)
        actions = {b.action for b in bindings}
        assert "quit" in actions
        assert "help" in actions  # GLOBAL
        assert "nav_up" in actions
        assert "nav_down" in actions

    def test_get_bindings_for_context_only(self) -> None:
        """get_bindings_for_context excludes GLOBAL."""
        bindings = self.mgr.get_bindings_for_context(BindingContext.NORMAL)
        actions = {b.action for b in bindings}
        assert "help" in actions  # GLOBAL
        assert "quit" not in actions

    def test_get_bindings_for_key(self) -> None:
        """get_bindings_for_key() returns bindings for key."""
        bindings = self.mgr.get_bindings_for_key("up")
        assert len(bindings) == 1
        assert bindings[0].action == "nav_up"

    def test_find_match(self) -> None:
        """find_match() returns first matching binding."""
        binding = self.mgr.find_match("ctrl+q", BindingContext.DIALOG)
        assert binding is not None
        assert binding.action == "quit"

    def test_find_match_not_found(self) -> None:
        """find_match() returns None when no match."""
        binding = self.mgr.find_match("ctrl+z", BindingContext.DIALOG)
        assert binding is None


class TestKeyBindingManagerDispatch:
    """Tests for KeyBindingManager key handling."""

    def setup_method(self) -> None:
        """Create manager with test handlers."""
        self.mgr = KeyBindingManager()
        self.events: list[str] = []

        def record(event: str) -> bool:
            self.events.append(event)
            return True

        self.mgr.register_many([
            KeyBinding(action="a", key="a", handler=lambda: record("a")),
            KeyBinding(action="enter", key="enter", handler=lambda: record("enter"), context=BindingContext.DIALOG),
            KeyBinding(action="quit", key="ctrl+q", handler=lambda: record("quit"), context=BindingContext.DIALOG),
        ])

    def test_handle_key_fires_handler(self) -> None:
        """handle_key() fires the matching handler."""
        handled = self.mgr.handle_key("a", BindingContext.NORMAL)
        assert handled is True
        assert self.events == ["a"]

    def test_handle_key_returns_false_on_no_match(self) -> None:
        """handle_key() returns False when no binding matches."""
        handled = self.mgr.handle_key("ctrl+z", BindingContext.NORMAL)
        assert handled is False
        assert self.events == []

    def test_handle_key_respects_context(self) -> None:
        """handle_key() only fires bindings in current context."""
        self.mgr.set_context(BindingContext.NORMAL)
        # "enter" is only in DIALOG context
        handled = self.mgr.handle_key("enter", BindingContext.NORMAL)
        assert handled is False

    def test_handle_key_global_always_matches(self) -> None:
        """handle_key() fires GLOBAL bindings in any context."""
        self.mgr.set_context(BindingContext.DIALOG)
        handled = self.mgr.handle_key("a", BindingContext.DIALOG)
        assert handled is True
        assert "a" in self.events

    def test_priority_order(self) -> None:
        """Higher priority bindings fire first."""
        mgr = KeyBindingManager()
        events: list[str] = []

        mgr.register(KeyBinding(action="low", key="x", handler=lambda: (events.append("low"), True)[1], priority=0))
        mgr.register(KeyBinding(action="high", key="x", handler=lambda: (events.append("high"), True)[1], priority=10))

        mgr.handle_key("x", BindingContext.NORMAL)
        assert events == ["high"]

    def test_suppress_context(self) -> None:
        """suppress_context() blocks all bindings in a context."""
        self.mgr.suppress_context(BindingContext.DIALOG)
        handled = self.mgr.handle_key("enter", BindingContext.DIALOG)
        assert handled is False

    def test_unsuppress_context(self) -> None:
        """unsuppress_context() re-enables a context."""
        self.mgr.suppress_context(BindingContext.DIALOG)
        self.mgr.unsuppress_context(BindingContext.DIALOG)
        handled = self.mgr.handle_key("enter", BindingContext.DIALOG)
        assert handled is True

    def test_unsuppress_all(self) -> None:
        """unsuppress_all() clears all suppressions."""
        self.mgr.suppress_context(BindingContext.DIALOG)
        self.mgr.suppress_context(BindingContext.NORMAL)
        self.mgr.unsuppress_all()
        # Should not crash and bindings should work
        handled = self.mgr.handle_key("enter", BindingContext.DIALOG)
        assert handled is True


class TestKeyBindingManagerContext:
    """Tests for context management."""

    def test_set_context(self) -> None:
        """set_context() changes the current context."""
        mgr = KeyBindingManager()
        mgr.set_context(BindingContext.DIALOG)
        assert mgr.current_context == BindingContext.DIALOG

    def test_default_context(self) -> None:
        """Manager defaults to NORMAL context."""
        mgr = KeyBindingManager()
        assert mgr.current_context == BindingContext.NORMAL

    def test_get_help_text(self) -> None:
        """get_help_text() returns bindings with descriptions."""
        mgr = KeyBindingManager()
        mgr.register_many([
            KeyBinding(action="a", key="a", handler=lambda: True, context=BindingContext.DIALOG, description="Do A"),
            KeyBinding(action="b", key="b", handler=lambda: True, context=BindingContext.DIALOG, description="Do B"),
            KeyBinding(action="c", key="c", handler=lambda: True, context=BindingContext.NORMAL, description="Do C"),
        ])
        help_text = mgr.get_help_text(BindingContext.DIALOG)
        assert len(help_text) == 2
        assert ("a", "Do A") in help_text
        assert ("b", "Do B") in help_text


# =============================================================================
# Global Functions Tests
# =============================================================================


class TestGlobalBindingFunctions:
    """Tests for global binding manager functions."""

    def setup_method(self) -> None:
        """Reset global manager before each test."""
        reset_binding_manager()

    def test_get_binding_manager_singleton(self) -> None:
        """get_binding_manager() returns same instance."""
        m1 = get_binding_manager()
        m2 = get_binding_manager()
        assert m1 is m2

    def test_register_binding_global(self) -> None:
        """register_binding() uses global manager."""
        register_binding(KeyBinding(action="test", key="t", handler=lambda: True))
        assert get_binding_manager().get_binding("test") is not None

    def test_unregister_binding_global(self) -> None:
        """unregister_binding() uses global manager."""
        register_binding(KeyBinding(action="test", key="t", handler=lambda: True))
        assert unregister_binding("test") is True
        assert get_binding_manager().get_binding("test") is None
