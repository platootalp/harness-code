"""Tests for UI keyboard binding system."""

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
    make_cancel_binding,
    make_confirm_binding,
    make_nav_down_binding,
    make_nav_up_binding,
    make_select_binding,
    normalize_key,
    parse_chord,
    parse_key,
    reset_binding_manager,
)


class TestKeyName:
    """Tests for KeyName enum."""

    def test_navigation_keys(self) -> None:
        """Navigation keys exist."""
        assert KeyName.UP == "up"
        assert KeyName.DOWN == "down"
        assert KeyName.LEFT == "left"
        assert KeyName.RIGHT == "right"
        assert KeyName.HOME == "home"
        assert KeyName.END == "end"

    def test_control_keys(self) -> None:
        """Control keys exist."""
        assert KeyName.ENTER == "enter"
        assert KeyName.ESCAPE == "escape"
        assert KeyName.TAB == "tab"
        assert KeyName.SPACE == "space"
        assert KeyName.BACKSPACE == "backspace"
        assert KeyName.DELETE == "delete"


class TestBindingContext:
    """Tests for BindingContext enum."""

    def test_contexts_exist(self) -> None:
        """All expected contexts exist."""
        assert BindingContext.GLOBAL == "global"
        assert BindingContext.NORMAL == "normal"
        assert BindingContext.PROMPT == "prompt"
        assert BindingContext.DIALOG == "dialog"
        assert BindingContext.MODAL == "modal"
        assert BindingContext.SEARCH == "search"
        assert BindingContext.VIM_NORMAL == "vim_normal"
        assert BindingContext.VIM_INSERT == "vim_insert"
        assert BindingContext.VIM_VISUAL == "vim_visual"


class TestKeyBinding:
    """Tests for KeyBinding."""

    def test_creation(self) -> None:
        """KeyBinding can be created."""
        called: list[bool] = []

        def handler() -> bool:
            called.append(True)
            return True

        binding = KeyBinding(
            action="test_action",
            key="ctrl+c",
            handler=handler,
            context=BindingContext.GLOBAL,
            description="Test binding",
            priority=10,
        )
        assert binding.action == "test_action"
        assert binding.key == "ctrl+c"
        assert binding.description == "Test binding"
        assert binding.priority == 10
        assert binding.is_active is True
        assert binding.contexts == [BindingContext.GLOBAL]

    def test_single_context_normalization(self) -> None:
        """Single context is normalized to list."""
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
            context=BindingContext.DIALOG,
        )
        assert binding.contexts == [BindingContext.DIALOG]

    def test_matches(self) -> None:
        """matches works correctly."""
        binding = KeyBinding(
            action="test",
            key="ctrl+c",
            handler=lambda: True,
            context=BindingContext.GLOBAL,
        )
        assert binding.matches("ctrl+c", BindingContext.GLOBAL) is True
        assert binding.matches("ctrl+c", BindingContext.DIALOG) is True  # GLOBAL is always match
        assert binding.matches("ctrl+v", BindingContext.GLOBAL) is False

    def test_matches_inactive(self) -> None:
        """Inactive bindings don't match."""
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
        )
        binding.is_active = False
        assert binding.matches("a", BindingContext.GLOBAL) is False

    def test_matches_with_when_condition(self) -> None:
        """matches respects when condition."""
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
            when=lambda: False,
        )
        assert binding.matches("a", BindingContext.GLOBAL) is False
        binding.when = lambda: True
        assert binding.matches("a", BindingContext.GLOBAL) is True

    def test_can_fire_in(self) -> None:
        """can_fire_in works correctly."""
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
            context=BindingContext.DIALOG,
        )
        assert binding.can_fire_in(BindingContext.DIALOG) is True
        assert binding.can_fire_in(BindingContext.NORMAL) is False

    def test_can_fire_in_global(self) -> None:
        """GLOBAL bindings fire in any context."""
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
            context=BindingContext.GLOBAL,
        )
        assert binding.can_fire_in(BindingContext.DIALOG) is True
        assert binding.can_fire_in(BindingContext.NORMAL) is True


class TestKeyBindingManager:
    """Tests for KeyBindingManager."""

    def setup_method(self) -> None:
        """Reset binding manager before each test."""
        reset_binding_manager()

    def test_register(self) -> None:
        """register adds binding."""
        manager = KeyBindingManager()
        binding = KeyBinding(
            action="test",
            key="a",
            handler=lambda: True,
        )
        manager.register(binding)
        assert len(manager.get_all_bindings()) == 1

    def test_register_replaces_same_action(self) -> None:
        """Registering same action replaces."""
        manager = KeyBindingManager()
        binding1 = KeyBinding(action="test", key="a", handler=lambda: True)
        binding2 = KeyBinding(action="test", key="b", handler=lambda: True)
        manager.register(binding1)
        manager.register(binding2)
        assert len(manager.get_all_bindings()) == 1
        found = manager.get_binding("test")
        assert found is not None
        assert found.key == "b"

    def test_register_many(self) -> None:
        """register_many adds multiple bindings."""
        manager = KeyBindingManager()
        bindings = [
            KeyBinding(action=f"action{i}", key=str(i), handler=lambda: True)
            for i in range(5)
        ]
        manager.register_many(bindings)
        assert len(manager.get_all_bindings()) == 5

    def test_unregister(self) -> None:
        """unregister removes binding."""
        manager = KeyBindingManager()
        manager.register(KeyBinding(action="test", key="a", handler=lambda: True))
        result = manager.unregister("test")
        assert result is True
        assert manager.get_binding("test") is None

    def test_unregister_nonexistent(self) -> None:
        """unregister nonexistent returns False."""
        manager = KeyBindingManager()
        result = manager.unregister("test")
        assert result is False

    def test_unregister_all(self) -> None:
        """unregister_all clears all bindings."""
        manager = KeyBindingManager()
        manager.register(KeyBinding(action="a", key="a", handler=lambda: True))
        manager.register(KeyBinding(action="b", key="b", handler=lambda: True))
        count = manager.unregister_all()
        assert count == 2
        assert len(manager.get_all_bindings()) == 0

    def test_get_binding(self) -> None:
        """get_binding returns binding by action."""
        manager = KeyBindingManager()
        binding = KeyBinding(action="test", key="a", handler=lambda: True)
        manager.register(binding)
        found = manager.get_binding("test")
        assert found is binding

    def test_get_bindings_for_context(self) -> None:
        """get_bindings_for_context returns correct bindings."""
        manager = KeyBindingManager()
        manager.register(
            KeyBinding(action="a", key="a", handler=lambda: True, context=BindingContext.DIALOG)
        )
        manager.register(
            KeyBinding(action="b", key="b", handler=lambda: True, context=BindingContext.NORMAL)
        )
        dialog_bindings = manager.get_bindings_for_context(BindingContext.DIALOG)
        assert len(dialog_bindings) == 1
        assert dialog_bindings[0].action == "a"

    def test_get_bindings_for_key(self) -> None:
        """get_bindings_for_key returns correct bindings."""
        manager = KeyBindingManager()
        manager.register(KeyBinding(action="a", key="ctrl+c", handler=lambda: True))
        manager.register(KeyBinding(action="b", key="ctrl+c", handler=lambda: True))
        manager.register(KeyBinding(action="c", key="a", handler=lambda: True))
        ctrl_c_bindings = manager.get_bindings_for_key("ctrl+c")
        assert len(ctrl_c_bindings) == 2

    def test_find_match(self) -> None:
        """find_match returns first matching binding by priority."""
        manager = KeyBindingManager()
        manager.register(
            KeyBinding(action="low", key="a", handler=lambda: True, priority=1)
        )
        manager.register(
            KeyBinding(action="high", key="a", handler=lambda: True, priority=10)
        )
        match = manager.find_match("a")
        assert match is not None
        assert match.action == "high"  # Higher priority first

    def test_find_match_no_match(self) -> None:
        """find_match returns None when no match."""
        manager = KeyBindingManager()
        manager.register(KeyBinding(action="test", key="a", handler=lambda: True))
        match = manager.find_match("b")
        assert match is None

    def test_handle_key(self) -> None:
        """handle_key dispatches to handler."""
        called: list[bool] = []

        def handler() -> bool:
            called.append(True)
            return True

        manager = KeyBindingManager()
        manager.register(KeyBinding(action="test", key="a", handler=handler))
        result = manager.handle_key("a")
        assert result is True
        assert called == [True]

    def test_handle_key_no_match(self) -> None:
        """handle_key returns False on no match."""
        manager = KeyBindingManager()
        result = manager.handle_key("a")
        assert result is False

    def test_handle_key_returns_handler_result(self) -> None:
        """handle_key returns handler's return value."""
        manager = KeyBindingManager()
        manager.register(KeyBinding(action="test", key="a", handler=lambda: False))
        result = manager.handle_key("a")
        assert result is False

    def test_set_context(self) -> None:
        """set_context changes current context."""
        manager = KeyBindingManager()
        assert manager.current_context == BindingContext.NORMAL
        manager.set_context(BindingContext.DIALOG)
        assert manager.current_context == BindingContext.DIALOG

    def test_suppress_unsuppress_context(self) -> None:
        """suppress and unsuppress work."""
        manager = KeyBindingManager()
        manager.register(
            KeyBinding(action="test", key="a", handler=lambda: True, context=BindingContext.NORMAL)
        )
        manager.suppress_context(BindingContext.NORMAL)
        result = manager.handle_key("a")
        assert result is False  # Suppressed
        manager.unsuppress_context(BindingContext.NORMAL)
        result = manager.handle_key("a")
        assert result is True

    def test_unsuppress_all(self) -> None:
        """unsuppress_all clears suppressions."""
        manager = KeyBindingManager()
        manager.suppress_context(BindingContext.DIALOG)
        manager.suppress_context(BindingContext.NORMAL)
        manager.unsuppress_all()
        # Should be able to handle keys in both contexts
        manager.register(
            KeyBinding(action="test", key="a", handler=lambda: True, context=BindingContext.GLOBAL)
        )
        result = manager.handle_key("a")
        assert result is True

    def test_get_help_text(self) -> None:
        """get_help_text returns formatted help."""
        manager = KeyBindingManager()
        manager.register(
            KeyBinding(action="test1", key="a", handler=lambda: True, description="Test 1")
        )
        manager.register(
            KeyBinding(action="test2", key="b", handler=lambda: True, description="Test 2")
        )
        help_text = manager.get_help_text(BindingContext.GLOBAL)
        assert len(help_text) == 2


class TestBindingFactories:
    """Tests for binding factory functions."""

    def test_make_confirm_binding(self) -> None:
        """make_confirm_binding creates correct binding."""
        called: list[bool] = []

        def handler() -> None:
            called.append(True)

        binding = make_confirm_binding(handler)
        assert binding.action == "confirm"
        assert binding.key == "enter"
        assert binding.contexts == [BindingContext.DIALOG]

    def test_make_cancel_binding(self) -> None:
        """make_cancel_binding creates correct binding."""
        called: list[bool] = []

        def handler() -> None:
            called.append(True)

        binding = make_cancel_binding(handler)
        assert binding.action == "cancel"
        assert binding.key == "escape"

    def test_make_nav_up_binding(self) -> None:
        """make_nav_up_binding creates correct binding."""
        binding = make_nav_up_binding(lambda: None)
        assert binding.action == "nav_up"
        assert binding.key == "up"

    def test_make_nav_down_binding(self) -> None:
        """make_nav_down_binding creates correct binding."""
        binding = make_nav_down_binding(lambda: None)
        assert binding.action == "nav_down"
        assert binding.key == "down"

    def test_make_select_binding(self) -> None:
        """make_select_binding creates correct binding."""
        binding = make_select_binding(lambda: None)
        assert binding.action == "select"
        assert binding.key == "enter"
        assert binding.contexts == [BindingContext.SEARCH]


class TestModifier:
    """Tests for Modifier enum."""

    def test_values(self) -> None:
        """Modifier has expected values."""
        assert Modifier.CTRL == "ctrl"
        assert Modifier.SHIFT == "shift"
        assert Modifier.ALT == "alt"
        assert Modifier.META == "meta"


class TestKeyType:
    """Tests for KeyType enum."""

    def test_values(self) -> None:
        """KeyType has expected values."""
        assert KeyType.PLAIN == "plain"
        assert KeyType.ARROW == "arrow"
        assert KeyType.FUNCTION == "function"
        assert KeyType.CONTROL == "control"
        assert KeyType.SPECIAL == "special"


class TestParsedKey:
    """Tests for ParsedKey."""

    def test_chord_string(self) -> None:
        """chord_string works correctly."""
        key = ParsedKey(key="c", modifiers=[Modifier.CTRL])
        assert key.chord_string() == "ctrl+c"
        key2 = ParsedKey(key="a")
        assert key2.chord_string() == "a"


class TestKeyUtilities:
    """Tests for key parsing utilities."""

    def test_normalize_key(self) -> None:
        """normalize_key works correctly."""
        assert normalize_key("return") == "enter"
        assert normalize_key("esc") == "escape"
        assert normalize_key("del") == "delete"
        assert normalize_key("pgup") == "pageup"
        assert normalize_key("PGDN") == "pagedown"
        assert normalize_key("RETURN") == "enter"

    def test_normalize_key_ctrl_notation(self) -> None:
        """normalize_key handles Ctrl notation."""
        assert normalize_key("^c") == "ctrl+c"

    def test_parse_key_simple(self) -> None:
        """parse_key handles simple keys."""
        key = parse_key("a")
        assert key.key == "a"
        assert key.modifiers == []

    def test_parse_key_with_modifier(self) -> None:
        """parse_key handles modifier keys."""
        key = parse_key("ctrl+c")
        assert key.key == "c"
        assert Modifier.CTRL in key.modifiers

    def test_parse_key_with_multiple_modifiers(self) -> None:
        """parse_key handles multiple modifiers."""
        key = parse_key("ctrl+shift+a")
        assert key.key == "a"
        assert Modifier.CTRL in key.modifiers
        assert Modifier.SHIFT in key.modifiers

    def test_parse_chord(self) -> None:
        """parse_chord splits chord into keys."""
        keys = parse_chord("ctrl+c")
        assert len(keys) == 2
        assert keys[0].key == "ctrl"
        assert keys[1].key == "c"

    def test_parse_chord_simple(self) -> None:
        """parse_chord handles simple key."""
        keys = parse_chord("a")
        assert len(keys) == 1
        assert keys[0].key == "a"
