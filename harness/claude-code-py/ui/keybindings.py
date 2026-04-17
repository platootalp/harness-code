"""
Keyboard binding system for Claude Code TUI.

Provides a centralized keybinding registry that allows registering keyboard
shortcuts with context, handlers, and priority ordering.

TypeScript equivalents: keybindings/useKeybinding.ts
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Key Names
# =============================================================================


class KeyName(StrEnum):
    """Normalized key names for consistency."""

    # Navigation
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    HOME = "home"
    END = "end"
    PAGE_UP = "pageup"
    PAGE_DOWN = "pagedown"

    # Control
    ENTER = "enter"
    ESCAPE = "escape"
    TAB = "tab"
    BACKTAB = "shift+tab"
    SPACE = "space"
    BACKSPACE = "backspace"
    DELETE = "delete"

    # Editing
    INSERT = "insert"

    # Function keys
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"

    # Ctrl keys
    CTRL_C = "ctrl+c"
    CTRL_D = "ctrl+d"
    CTRL_L = "ctrl+l"
    CTRL_R = "ctrl+r"
    CTRL_U = "ctrl+u"
    CTRL_W = "ctrl+w"

    # Misc
    CTRL_BRACKET = "ctrl+left_square_bracket"


# =============================================================================
# Binding Context
# =============================================================================


class BindingContext(StrEnum):
    """Context in which a binding is active."""

    GLOBAL = "global"
    NORMAL = "normal"
    PROMPT = "prompt"
    DIALOG = "dialog"
    MODAL = "modal"
    SEARCH = "search"
    VIM_NORMAL = "vim_normal"
    VIM_INSERT = "vim_insert"
    VIM_VISUAL = "vim_visual"
    MESSAGE_LIST = "message_list"
    TABS = "tabs"


# =============================================================================
# Key Binding
# =============================================================================


@dataclass
class KeyBinding:
    """A single keyboard binding.

    Attributes:
        action: Unique identifier for the action.
        key: The key or key combination (e.g., "ctrl+c", "escape").
        handler: Callback when the binding is triggered.
        context: Context(s) where this binding is active.
        description: Human-readable description for help display.
        priority: Higher priority bindings are checked first.
        is_active: Whether the binding is currently enabled.
        when: Optional condition function; binding only fires if True.
    """

    action: str
    key: str
    handler: Callable[[], bool | None]
    context: BindingContext | list[BindingContext] = BindingContext.GLOBAL
    description: str = ""
    priority: int = 0
    is_active: bool = True
    when: Callable[[], bool] | None = field(default=None, repr=False)
    _contexts: list[BindingContext] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Normalize context to a list."""
        if isinstance(self.context, str):
            self.context = BindingContext(self.context)
        if isinstance(self.context, BindingContext):
            self._contexts = [self.context]
        else:
            self._contexts = list(self.context)

    @property
    def contexts(self) -> list[BindingContext]:
        """Get the contexts as a list."""
        return self._contexts

    def matches(self, key: str, context: BindingContext) -> bool:
        """Check if this binding matches a key and context.

        Args:
            key: The key pressed.
            context: The current binding context.

        Returns:
            True if the binding matches.
        """
        if not self.is_active:
            return False
        if self.key != key:
            return False
        if BindingContext.GLOBAL not in self._contexts and context not in self._contexts:
            return False
        return not (self.when is not None and not self.when())

    def can_fire_in(self, context: BindingContext) -> bool:
        """Check if this binding can fire in a given context.

        Args:
            context: The context to check.

        Returns:
            True if the binding is active in this context.
        """
        if not self.is_active:
            return False
        if self.when is not None and not self.when():
            return False
        if BindingContext.GLOBAL in self._contexts:
            return True
        return context in self._contexts


# =============================================================================
# Key Binding Manager
# =============================================================================


class KeyBindingManager:
    """Centralized keyboard binding registry.

    Manages registration, lookup, and dispatching of keyboard bindings
    across different contexts. Bindings are checked in priority order.

    TypeScript equivalent: keybindings registry with context awareness.
    """

    def __init__(self) -> None:
        """Initialize the binding manager."""
        self._bindings: list[KeyBinding] = []
        self._action_map: dict[str, KeyBinding] = {}
        self._current_context: BindingContext = BindingContext.NORMAL
        self._suppressed_contexts: set[BindingContext] = set()

    def register(self, binding: KeyBinding) -> None:
        """Register a keyboard binding.

        Args:
            binding: The binding to register.
        """
        # Remove existing binding with same action
        if binding.action in self._action_map:
            existing = self._action_map[binding.action]
            if existing in self._bindings:
                self._bindings.remove(existing)
        self._bindings.append(binding)
        self._bindings.sort(key=lambda b: -b.priority)  # Highest priority first
        self._action_map[binding.action] = binding

    def register_many(self, bindings: list[KeyBinding]) -> None:
        """Register multiple bindings at once.

        Args:
            bindings: List of bindings to register.
        """
        for b in bindings:
            self.register(b)

    def unregister(self, action: str) -> bool:
        """Unregister a binding by action name.

        Args:
            action: The action identifier.

        Returns:
            True if a binding was removed.
        """
        if action not in self._action_map:
            return False
        binding = self._action_map.pop(action)
        if binding in self._bindings:
            self._bindings.remove(binding)
        return True

    def unregister_all(self) -> int:
        """Unregister all bindings.

        Returns:
            The number of bindings removed.
        """
        count = len(self._bindings)
        self._bindings.clear()
        self._action_map.clear()
        return count

    def unregister_by_context(self, context: BindingContext) -> int:
        """Unregister all bindings in a specific context.

        Args:
            context: The context to clear.

        Returns:
            The number of bindings removed.
        """
        to_remove = [b for b in self._bindings if b.can_fire_in(context)]
        for b in to_remove:
            self.unregister(b.action)
        return len(to_remove)

    def get_binding(self, action: str) -> KeyBinding | None:
        """Get a binding by action name.

        Args:
            action: The action identifier.

        Returns:
            The binding if found.
        """
        return self._action_map.get(action)

    def get_bindings_for_context(
        self, context: BindingContext
    ) -> list[KeyBinding]:
        """Get all bindings active in a context.

        Args:
            context: The binding context.

        Returns:
            List of bindings for this context.
        """
        return [b for b in self._bindings if b.can_fire_in(context)]

    def get_bindings_for_key(self, key: str) -> list[KeyBinding]:
        """Get all bindings for a specific key.

        Args:
            key: The key to look up.

        Returns:
            List of bindings for this key.
        """
        return [b for b in self._bindings if b.key == key]

    def find_match(
        self, key: str, context: BindingContext | None = None
    ) -> KeyBinding | None:
        """Find the first matching binding for a key.

        Bindings are checked in priority order (highest first).

        Args:
            key: The key pressed.
            context: The current context (defaults to current context).

        Returns:
            The first matching binding, or None.
        """
        ctx = context or self._current_context
        for binding in self._bindings:
            if binding.matches(key, ctx):
                return binding
        return None

    def handle_key(
        self, key: str, context: BindingContext | None = None
    ) -> bool:
        """Handle a key press and dispatch to matching binding.

        Args:
            key: The key that was pressed.
            context: The current context (defaults to current context).

        Returns:
            True if a binding handled the key.
        """
        if self._suppressed_contexts:
            ctx = context or self._current_context
            if ctx in self._suppressed_contexts:
                return False

        binding = self.find_match(key, context)
        if binding is not None:
            result = binding.handler()
            return result is None or result is True
        return False

    def set_context(self, context: BindingContext) -> None:
        """Set the current binding context.

        Args:
            context: The new context.
        """
        self._current_context = context

    @property
    def current_context(self) -> BindingContext:
        """Get the current binding context."""
        return self._current_context

    def suppress_context(self, context: BindingContext) -> None:
        """Suppress all bindings in a context (used during modal, etc.).

        Args:
            context: The context to suppress.
        """
        self._suppressed_contexts.add(context)

    def unsuppress_context(self, context: BindingContext) -> None:
        """Remove suppression for a context.

        Args:
            context: The context to unsuppress.
        """
        self._suppressed_contexts.discard(context)

    def unsuppress_all(self) -> None:
        """Remove all context suppressions."""
        self._suppressed_contexts.clear()

    def get_help_text(self, context: BindingContext) -> list[tuple[str, str]]:
        """Get help text for all bindings in a context.

        Args:
            context: The context to get help for.

        Returns:
            List of (key, description) tuples sorted by key.
        """
        bindings = self.get_bindings_for_context(context)
        result = [(b.key, b.description) for b in bindings if b.description]
        result.sort(key=lambda x: x[0])
        return result

    def get_all_bindings(self) -> list[KeyBinding]:
        """Get all registered bindings.

        Returns:
            List of all bindings.
        """
        return list(self._bindings)


# =============================================================================
# Common Binding Factories
# =============================================================================


def make_confirm_binding(
    handler: Callable[[], None],
    priority: int = 0,
) -> KeyBinding:
    """Create a confirm/ok binding (Enter key).

    Args:
        handler: Function to call on Enter.
        priority: Binding priority.

    Returns:
        A KeyBinding for Enter.
    """
    def _wrapper() -> bool:
        handler()
        return True

    return KeyBinding(
        action="confirm",
        key="enter",
        handler=_wrapper,
        context=BindingContext.DIALOG,
        description="Confirm",
        priority=priority,
    )


def make_cancel_binding(
    handler: Callable[[], None],
    priority: int = 0,
) -> KeyBinding:
    """Create a cancel binding (Escape key).

    Args:
        handler: Function to call on Escape.
        priority: Binding priority.

    Returns:
        A KeyBinding for Escape.
    """

    def _wrapper() -> bool:
        handler()
        return True

    return KeyBinding(
        action="cancel",
        key="escape",
        handler=_wrapper,
        context=BindingContext.DIALOG,
        description="Cancel / Close",
        priority=priority,
    )


def make_nav_up_binding(
    handler: Callable[[], None],
    context: BindingContext | list[BindingContext] = BindingContext.DIALOG,
    priority: int = 0,
) -> KeyBinding:
    """Create an upward navigation binding.

    Args:
        handler: Function to call on Up.
        context: Binding context(s).
        priority: Binding priority.

    Returns:
        A KeyBinding for Up arrow.
    """

    def _wrapper() -> bool:
        handler()
        return True

    return KeyBinding(
        action="nav_up",
        key="up",
        handler=_wrapper,
        context=context,
        description="Move up",
        priority=priority,
    )


def make_nav_down_binding(
    handler: Callable[[], None],
    context: BindingContext | list[BindingContext] = BindingContext.DIALOG,
    priority: int = 0,
) -> KeyBinding:
    """Create a downward navigation binding.

    Args:
        handler: Function to call on Down.
        context: Binding context(s).
        priority: Binding priority.

    Returns:
        A KeyBinding for Down arrow.
    """

    def _wrapper() -> bool:
        handler()
        return True

    return KeyBinding(
        action="nav_down",
        key="down",
        handler=_wrapper,
        context=context,
        description="Move down",
        priority=priority,
    )


def make_select_binding(
    handler: Callable[[], None],
    priority: int = 0,
) -> KeyBinding:
    """Create a select binding (Enter key).

    Args:
        handler: Function to call on Enter.
        priority: Binding priority.

    Returns:
        A KeyBinding for Enter in selection context.
    """

    def _wrapper() -> bool:
        handler()
        return True

    return KeyBinding(
        action="select",
        key="enter",
        handler=_wrapper,
        context=BindingContext.SEARCH,
        description="Select",
        priority=priority,
    )


# =============================================================================
# Global Binding Manager Instance
# =============================================================================

_binding_manager: KeyBindingManager | None = None


def get_binding_manager() -> KeyBindingManager:
    """Get the global binding manager instance.

    Returns:
        The global KeyBindingManager.
    """
    global _binding_manager
    if _binding_manager is None:
        _binding_manager = KeyBindingManager()
    return _binding_manager


def reset_binding_manager() -> None:
    """Reset the global binding manager (for testing)."""
    global _binding_manager
    _binding_manager = KeyBindingManager()


def register_binding(binding: KeyBinding) -> None:
    """Register a binding with the global manager.

    Args:
        binding: The binding to register.
    """
    get_binding_manager().register(binding)


def unregister_binding(action: str) -> bool:
    """Unregister a binding from the global manager.

    Args:
        action: The action identifier.

    Returns:
        True if removed.
    """
    return get_binding_manager().unregister(action)


# =============================================================================
# Key Utilities
# =============================================================================


class Modifier(StrEnum):
    """Keyboard modifier keys."""

    CTRL = "ctrl"
    SHIFT = "shift"
    ALT = "alt"
    META = "meta"


class KeyType(StrEnum):
    """Key type classification."""

    PLAIN = "plain"
    ARROW = "arrow"
    FUNCTION = "function"
    CONTROL = "control"
    SPECIAL = "special"


@dataclass
class ParsedKey:
    """A parsed key with its modifiers.

    Attributes:
        key: The base key name.
        modifiers: List of modifier keys.
    """

    key: str
    modifiers: list[Modifier] = field(default_factory=list)

    def chord_string(self) -> str:
        """Return the chord representation of this key.

        Returns:
            The key with modifiers as a chord string.
        """
        if not self.modifiers:
            return self.key
        mod_str = "+".join(m.value for m in self.modifiers)
        return f"{mod_str}+{self.key}"


def normalize_key(key: str) -> str:
    """Normalize a key string to canonical form.

    Converts keys to lowercase, handles Ctrl (^) notation,
    and normalizes special names.

    Args:
        key: The key string to normalize.

    Returns:
        Normalized key string.
    """
    k = key.lower().strip()
    # Handle Ctrl notation (^c -> ctrl+c)
    if k.startswith("^"):
        k = f"ctrl+{k[1:]}"
    # Normalize key names
    aliases: dict[str, str] = {
        "return": "enter",
        "esc": "escape",
        "del": "delete",
        "ins": "insert",
        "pgup": "pageup",
        "pgdn": "pagedown",
        "ctrl": "ctrl",
        "shift": "shift",
        "alt": "alt",
        "meta": "meta",
    }
    return aliases.get(k, k)


def parse_key(key: str) -> ParsedKey:
    """Parse a key string into key + modifiers.

    Args:
        key: The key string (e.g., "ctrl+c", "shift+tab").

    Returns:
        ParsedKey with base key and modifiers.
    """
    normalized = normalize_key(key)
    parts = normalized.split("+")
    modifiers: list[Modifier] = []
    base_key = parts[-1] if parts else normalized

    for part in parts[:-1]:
        with contextlib.suppress(ValueError):
            modifiers.append(Modifier(part))

    return ParsedKey(key=base_key, modifiers=modifiers)


def parse_chord(key: str) -> list[ParsedKey]:
    """Parse a key chord into individual keys.

    A chord is a sequence of keys pressed together (e.g., ctrl+c).
    This splits it into the modifier key(s) and the final key.

    Args:
        key: The key chord string.

    Returns:
        List of ParsedKeys (modifier keys + final key).
    """
    parts = key.lower().split("+")
    if len(parts) <= 1:
        return [ParsedKey(key=parts[0] if parts else key)]

    result: list[ParsedKey] = []
    for part in parts[:-1]:
        with contextlib.suppress(ValueError):
            result.append(ParsedKey(key=part, modifiers=[Modifier(part)]))

    final_mods: list[Modifier] = []
    for part in parts[:-1]:
        with contextlib.suppress(ValueError):
            final_mods.append(Modifier(part))

    result.append(ParsedKey(key=parts[-1], modifiers=final_mods))
    return result


def chord_keys(*keys: ParsedKey) -> str:
    """Build a chord string from ParsedKey objects.

    Args:
        *keys: ParsedKey objects.

    Returns:
        Chord string (e.g., "ctrl+c").
    """
    if not keys:
        return ""
    result_parts: list[str] = []
    for k in keys:
        if k.modifiers:
            result_parts.append("+".join(m.value for m in k.modifiers))
        result_parts.append(k.key)
    return "+".join(result_parts)
