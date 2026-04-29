# Phase 9 Design: Hooks & State Management System

**Date:** 2026-04-05
**Status:** Design Complete
**Source:** Analysis of `src/state/` and `src/hooks/` in the TypeScript codebase

---

## 1. State Management Architecture

### 1.1 TypeScript Architecture (Source)

The TypeScript codebase uses a **centralized observable store** pattern:

```
┌─────────────────────────────────────────────────────────────┐
│  AppState (single source of truth)                          │
│  - messages, tasks, agents, settings, MCP, plugins, etc.  │
└──────────────┬──────────────────────────────────────────────┘
               │ createStore<T>(initial, onChange?)
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Store<T> interface                                        │
│    getState(): T                                          │
│    setState((prev: T) => T): void    ← pure updater fn    │
│    subscribe(listener) => unsubscribe: () => void         │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├── AppStateProvider (React context)
               │       │
               │       ├── useAppState(selector)  → useSyncExternalStore
               │       ├── useSetAppState()       → raw setState
               │       └── useAppStateStore()     → full store
               │
               ├── onChangeAppState()  → side-effects on transitions
               │       - CCR/SDK permission mode sync
               │       - settings persistence
               │       - auth cache clearing
               │
               └── 60+ specialized hooks (useSettings, useManagePlugins, etc.)
```

**Key properties:**
- **Single store**: All application state in one place (vs. Redux-style many stores)
- **Immutable-style updates**: `setState(prev => ({ ...prev, field: newValue }))`
- **Subscription-based**: Components subscribe to slices via selector functions
- **Side-effect hook**: `onChangeAppState` centralizes external system sync
- **React context**: Store accessed via `AppStoreContext.Provider`

### 1.2 Python Architecture (Target)

Textual-native architecture using Reactive variables and asyncio:

```
┌─────────────────────────────────────────────────────────────┐
│  AppState (dataclass, reactive)                            │
│  - messages, tasks, agents, settings, mcp, plugins, etc.  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  AsyncObservable[T]  (async-aware observable store)        │
│    get() -> T                                            │
│    set(updater: (T) -> T) -> None: sync                   │
│    set_async(updater: (T) -> T) -> None: async            │
│    subscribe(key?, listener) -> unsubscribe               │
│    on_change(old, new) -> None: hook for side-effects     │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├── App (Textual app with reactive state)
               │       │
               │       ├── @ reactive state variables
               │       ├── @ effect decorator (async effects)
               │       └── contextvar for cross-component access
               │
               ├── on_state_change()  → async side-effects
               │       - settings persistence
               │       - auth cache invalidation
               │       - notification triggers
               │
               └── Specialized composables (use_settings, etc.)
```

---

## 2. Observable Store Implementation

### 2.1 TypeScript: `store.ts` (Source)

```typescript
type Listener = () => void
type OnChange<T> = (args: { newState: T; oldState: T }) => void

export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: OnChange<T>,
): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,
    setState: (updater) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return  // Structural equality check
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

**Design decisions:**
- Structural equality check via `Object.is` prevents infinite update loops
- `onChange` callback fires BEFORE listeners (allows side-effects to run first)
- `Set<Listener>` for automatic dedup (same function subscribed twice = one notification)

### 2.2 Python: `AsyncObservable` (Target)

```python
"""AsyncObservable - async-aware observable store with side-effect hooks."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Generic, TypeVar, Awaitable

from .change_record import ChangeRecord

logger = logging.getLogger(__name__)

T = TypeVar("T")

Listener = Callable[[], None]
KeyListener = Callable[["ChangeRecord"], None]
OnChange = Callable[[T, T], Awaitable[None] | None]


@dataclass
class AsyncObservable(Generic[T]):
    """Async-aware observable store matching TypeScript Store<T> pattern.

    Differences from TypeScript:
    - Async set() via set_async() for awaitable side-effects
    - Thread-safe via asyncio.Lock
    - on_change hook can be async (awaited before listeners)
    - Key-specific subscriptions for granular reactivity
    """

    _state: T = field(default=None)
    _listeners: list[Listener] = field(default_factory=list)
    _key_listeners: dict[str, list[KeyListener]] = field(default_factory=dict)
    _on_change: OnChange[T] | None = field(default=None)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _version: int = 0

    def get(self) -> T:
        """Get current state (no copy - caller must not mutate)."""
        return self._state

    def set(self, updater: Callable[[T], T]) -> None:
        """Synchronous state update with equality check and notification."""
        new_state = updater(self._state)
        if new_state is self._state:  # Identity check (not deep equality)
            return
        old_state = self._state
        self._state = new_state
        self._version += 1
        self._notify_change(old_state, new_state)

    async def set_async(self, updater: Callable[[T], T]) -> None:
        """Async state update - awaits on_change hook before notifying."""
        new_state = updater(self._state)
        if new_state is self._state:
            return
        old_state = self._state
        self._state = new_state
        self._version += 1

        # Run on_change hook first (can be async for side-effects like persistence)
        if self._on_change is not None:
            result = self._on_change(old_state, new_state)
            if asyncio.iscoroutine(result):
                await result

        self._notify_change(old_state, new_state)

    def _notify_change(self, old_state: T, new_state: T) -> None:
        """Notify all listeners of state change."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.warning(f"AsyncObservable: listener error: {e}")

        # Key-specific notifications via ChangeRecord
        if isinstance(old_state, dict) and isinstance(new_state, dict):
            for key in set(old_state.keys()) | set(new_state.keys()):
                if old_state.get(key) != new_state.get(key):
                    record = ChangeRecord(
                        key=key,
                        old_value=old_state.get(key),
                        new_value=new_state.get(key),
                        timestamp=datetime.now(),
                    )
                    for listener in self._key_listeners.get(key, []):
                        try:
                            listener(record)
                        except Exception as e:
                            logger.warning(f"AsyncObservable: key listener error: {e}")

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Subscribe to any state change. Returns unsubscribe function."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def subscribe_to_key(self, key: str, listener: KeyListener) -> Callable[[], None]:
        """Subscribe to changes for a specific key."""
        if key not in self._key_listeners:
            self._key_listeners[key] = []
        self._key_listeners[key].append(listener)
        return lambda: self._key_listeners[key].remove(listener)

    @property
    def version(self) -> int:
        """Monotonically increasing version for cache invalidation."""
        return self._version

    def __repr__(self) -> str:
        return f"AsyncObservable(version={self._version}, state_type={type(self._state).__name__})"
```

### 2.3 Python: `ChangeRecord`

```python
"""ChangeRecord - immutable record of a state change for key-specific listeners."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ChangeRecord:
    """Immutable record of a state change, matching TypeScript onChange args."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
```

---

## 3. Hook Patterns for Python/Textual

### 3.1 TypeScript React Hooks (Source)

#### `useAppState(selector)` — Selector-based subscription

```typescript
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()  // useContext(AppStoreContext)
  const get = () => selector(store.getState())
  return useSyncExternalStore(store.subscribe, get, get)
}
```

**Key insight:** `useSyncExternalStore` handles:
- Subscription on mount, unsubscription on unmount
- Server-side rendering safety (always returns `get()` on server)
- Bailing out of re-renders when selected value hasn't changed (`Object.is`)

#### `useSetAppState()` — Non-subscribing setter

```typescript
export function useSetAppState() {
  return useAppStore().setState  // Stable reference - never causes re-render
}
```

#### `useSwarmInitialization` — Complex init with effects

```typescript
export function useSwarmInitialization(
  setAppState: SetAppState,
  initialMessages: Message[] | undefined,
  { enabled = true }: { enabled?: boolean } = {},
): void {
  useEffect(() => {
    if (!enabled) return
    // Complex async initialization logic
    // ...
  }, [setAppState, initialMessages, enabled])
}
```

### 3.2 Python/Textual Equivalents

#### Context Variable for App-Wide State Access

```python
"""AppState context - replaces React context for Textual."""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .async_observable import AsyncObservable

T = TypeVar("T")

# Context variable for the app-wide observable store
# Set via app_state_context.set(observable) in app initialization
app_state_context: ContextVar["AsyncObservable[dict] | None"] = ContextVar(
    "app_state_context", default=None
)


def get_app_state() -> "AsyncObservable[dict]":
    """Get the current AppState from context (raises if not set)."""
    store = app_state_context.get()
    if store is None:
        raise RuntimeError(
            "AppState not set. Use app_state_context.set(observable) in app setup."
        )
    return store
```

#### `use_reactive` — Textual-native reactive state

Textual's built-in `@reactive` decorator is the primary mechanism for reactive state:

```python
"""use_reactive equivalent using Textual's Reactive."""
from __future__ import annotations

from typing import Callable, TypeVar, Generic, Type
from textual.app import ComposeResult
from textual.reactive import reactive, Reactive
from textual.widgets import Static

T = TypeVar("T")


class ReactiveState(Generic[T]):
    """Holds a reactive value with change subscription support.

    Python equivalent of React's useState + useSyncExternalStore pattern.
    """

    def __init__(self, initial_value: T):
        self._value = initial_value
        self._version = 0
        self._subscribers: list[Callable[[], None]] = []

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        if new_value == self._value:
            return
        self._value = new_value
        self._version += 1
        self._notify()

    def _notify(self) -> None:
        for cb in self._subscribers:
            try:
                cb()
            except Exception:
                pass

    def subscribe(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._subscribers.append(cb)
        return lambda: self._subscribers.remove(cb)


def use_reactive(
    default_value: T,
    *,
    layout: bool = False,
    repaint: bool = True,
    init: bool = True,
) -> tuple[T, Callable[[T], None]]:
    """Textual-compatible reactive state hook.

    This is a composable function meant to be called during widget mount.
    In Textual, prefer @reactive decorator on widget instances.

    Usage in a Textual widget:
        class MyWidget(Static):
            count = Reactive(0)

            def watch_count(self, value: int) -> None:
                self.update(str(value))
    """
    state = ReactiveState(default_value)
    return state.value, lambda v: setattr(state, 'value', v)
```

#### `@effect` Decorator — Async side-effects

```python
"""effect decorator - replaces useEffect for async side-effects."""
from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable, Awaitable

from .async_observable import AsyncObservable


def effect(
    deps: list[Any] | None = None,
    *,
    on_mount: bool = False,
) -> Callable[[Callable[[], Awaitable[None] | None], Callable[[], None]]:
    """Decorator for async side-effects, similar to React useEffect.

    Args:
        deps: List of dependency values. Effect re-runs when any dep changes.
              None = run on every state change.
              [] = run once on mount only.
        on_mount: If True, run immediately when decorated method is called.

    Usage:
        class MyComponent:
            def __init__(self, store: AsyncObservable):
                self.store = store
                self._unsubs: list[Callable] = []

            @effect(deps=["settings"], on_mount=True)
            async def on_settings_change(self) -> None:
                settings = self.store.get()["settings"]
                await self.persist_settings(settings)

            def cleanup(self) -> None:
                for unsub in self._unsubs:
                    unsub()
    """
    def decorator(
        func: Callable[[], Awaitable[None] | None]
    ) -> Callable[[], None]:
        prev_deps: list[Any] = [] if deps is not None else None  # type: ignore
        cleanup_funcs: list[Callable] = []

        @wraps(func)
        def run_effect() -> None:
            nonlocal prev_deps

            if deps is None:
                # Run on every change - no dependency tracking
                asyncio.create_task(_run_async(func))
            elif deps == [] and on_mount:
                # Run once on mount
                asyncio.create_task(_run_async(func))
            else:
                # Check if deps changed
                current_deps = [
                    _resolve_dep(d, _get_store()) for d in deps
                ]
                if prev_deps != current_deps:
                    prev_deps = current_deps
                    asyncio.create_task(_run_async(func))

        async def _run_async(fn: Callable[[], Awaitable[None] | None]) -> None:
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logging.getLogger(__name__).warning(f"effect error: {e}")

        return run_effect

    return decorator


def _resolve_dep(dep: Any, store: AsyncObservable) -> Any:
    """Resolve a dependency value (key name -> store value, or raw value)."""
    if isinstance(dep, str):
        return store.get().get(dep) if isinstance(store.get(), dict) else None
    return dep


def _get_store() -> AsyncObservable:
    """Get current store for dep resolution."""
    from .context import get_app_state
    return get_app_state()
```

#### `use_selector` — Derived state with subscription

```python
"""use_selector - derive a value from state, re-compute on changes."""
from __future__ import annotations

from typing import Callable, Generic, TypeVar

from .async_observable import AsyncObservable

T = TypeVar("T")
U = TypeVar("U")


class SelectorState(Generic[T, U]):
    """Caches selector output, only updates when selected value changes."""

    def __init__(
        self,
        store: AsyncObservable[T],
        selector: Callable[[T], U],
    ):
        self._store = store
        self._selector = selector
        self._cached_value: U | None = None
        self._initialized = False
        self._unsub: Callable | None = None

    def get(self) -> U:
        """Get current selected value, recomputing if needed."""
        state = self._store.get()
        new_value = self._selector(state)

        if not self._initialized or new_value != self._cached_value:
            self._cached_value = new_value
            self._initialized = True

        return self._cached_value

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to changes in selected value."""
        def notify_if_changed() -> None:
            old = self._cached_value
            new = self.get()
            if new != old:
                listener()

        return self._store.subscribe(notify_if_changed)
```

#### `use_settings` — Convenience composable

```python
"""use_settings - read-only access to settings slice."""
from __future__ import annotations

from typing import Any

from .async_observable import AsyncObservable


class SettingsSlice:
    """Read-only view of settings in app state."""

    def __init__(self, store: AsyncObservable[dict]):
        self._store = store

    def get(self) -> dict[str, Any]:
        """Get full settings dict."""
        return self._store.get().get("settings", {})

    def get_key(self, key: str, default: Any = None) -> Any:
        """Get a specific settings key."""
        return self.get().get(key, default)


def use_settings(store: AsyncObservable[dict]) -> SettingsSlice:
    """Get a read-only settings slice from app state.

    Usage:
        settings = use_settings(app_store)
        theme = settings.get_key("theme", "default")
    """
    return SettingsSlice(store)
```

---

## 4. State Synchronization

### 4.1 TypeScript: `onChangeAppState` (Source)

The central side-effect hook that fires on every state change:

```typescript
export function onChangeAppState({ newState, oldState }) {
  // 1. Permission mode → CCR/SDK sync
  if (prevMode !== newMode) {
    notifySessionMetadataChanged({ permission_mode: newExternal, ... })
    notifyPermissionModeChanged(newMode)
  }

  // 2. mainLoopModel → persist to settings
  if (newState.mainLoopModel !== oldState.mainLoopModel) {
    updateSettingsForSource('userSettings', { model: newState.mainLoopModel })
  }

  // 3. expandedView → globalConfig
  if (newState.expandedView !== oldState.expandedView) {
    saveGlobalConfig(current => ({ ...current, showExpandedTodos: ... }))
  }

  // 4. settings → clear auth caches
  if (newState.settings !== oldState.settings) {
    clearApiKeyHelperCache()
    clearAwsCredentialsCache()
    clearGcpCredentialsCache()
  }
}
```

### 4.2 Python: `on_state_change` (Target)

```python
"""on_state_change - async side-effect handler for state transitions."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type alias for the on_change callback
OnStateChange = Callable[[dict[str, Any], dict[str, Any]], Awaitable[None] | None]


class StateChangeHandler:
    """Central handler for state change side-effects, matching onChangeAppState.

    Register handlers for specific keys or run on any change.
    Handlers are async-aware and run in the event loop.
    """

    def __init__(self) -> None:
        self._key_handlers: dict[str, list[Callable[[Any, Any], Awaitable[None]]]] = {}
        self._global_handlers: list[OnStateChange] = []

    def on_key_change(
        self,
        key: str,
        handler: Callable[[Any, Any], Awaitable[None]],
    ) -> Callable[[], None]:
        """Register a handler for a specific key change."""
        if key not in self._key_handlers:
            self._key_handlers[key] = []
        self._key_handlers[key].append(handler)
        return lambda: self._key_handlers[key].remove(handler)

    def on_any_change(self, handler: OnStateChange) -> Callable[[], None]:
        """Register a handler for any state change."""
        self._global_handlers.append(handler)
        return lambda: self._global_handlers.remove(handler)

    async def handle_change(
        self,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> None:
        """Called by AsyncObservable.set_async() after state update."""
        # Key-specific handlers
        for key in set(old_state.keys()) | set(new_state.keys()):
            if old_state.get(key) != new_state.get(key):
                for handler in self._key_handlers.get(key, []):
                    try:
                        result = handler(old_state.get(key), new_state.get(key))
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.warning(f"StateChangeHandler: {key} handler error: {e}")

        # Global handlers
        for handler in self._global_handlers:
            try:
                result = handler(old_state, new_state)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"StateChangeHandler: global handler error: {e}")


# === Pre-built handlers matching TypeScript onChangeAppState ===

async def _settings_change_handler(
    old_settings: dict[str, Any] | None,
    new_settings: dict[str, Any] | None,
) -> None:
    """Handle settings changes - clear caches, re-apply env vars."""
    if old_settings is None or new_settings is None:
        return
    if old_settings == new_settings:
        return

    # Import lazily to avoid circular deps
    from ..security.layer import clear_auth_caches
    from ..lib.config import apply_env_variables

    clear_auth_caches()

    if old_settings.get("env") != new_settings.get("env"):
        apply_env_variables()


async def _permission_mode_handler(
    old_mode: str | None,
    new_mode: str | None,
) -> None:
    """Handle permission mode changes - sync with CCR if running as team leader."""
    if old_mode == new_mode:
        return

    # Would sync with CCR here when that integration exists
    logger.info(f"Permission mode changed: {old_mode} -> {new_mode}")


def register_default_handlers(handler: StateChangeHandler) -> None:
    """Register the standard set of state change handlers."""
    handler.on_key_change("settings", _settings_change_handler)
    handler.on_key_change("permission_mode", _permission_mode_handler)
```

### 4.3 Bridging AsyncObservable with StateChangeHandler

```python
"""Bridge between AsyncObservable and StateChangeHandler."""
from __future__ import annotations

import asyncio
from typing import Any

from .async_observable import AsyncObservable
from .state_change_handler import StateChangeHandler, register_default_handlers


class AppStateStore:
    """Full app state store combining AsyncObservable with change handling.

    This is the main entry point for app-wide state management.
    """

    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        if initial_state is None:
            initial_state = self._default_state()

        self._change_handler = StateChangeHandler()
        register_default_handlers(self._change_handler)

        self._observable = AsyncObservable[dict[str, Any]](
            _state=initial_state,
            _on_change=self._on_change_wrapper,
        )

    def _on_change_wrapper(
        self,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> asyncio.Task | None:
        """Wrap on_change to return a task for set_async to await."""
        import asyncio
        return asyncio.create_task(
            self._change_handler.handle_change(old_state, new_state)
        )

    # === Public API ===

    def get(self) -> dict[str, Any]:
        """Get current state."""
        return self._observable.get()

    def set(self, updater: callable[[dict[str, Any]], dict[str, Any]]) -> None:
        """Synchronous state update."""
        self._observable.set(updater)

    async def set_async(
        self,
        updater: callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Async state update with awaited side-effects."""
        await self._observable.set_async(updater)

    def subscribe(self, listener: callable[[], None]) -> callable[[], None]:
        """Subscribe to any state change."""
        return self._observable.subscribe(listener)

    def subscribe_to_key(
        self,
        key: str,
        listener: callable[[Any], None],
    ) -> callable[[], None]:
        """Subscribe to changes for a specific key."""
        return self._observable.subscribe_to_key(key, listener)

    @property
    def version(self) -> int:
        """State version for cache invalidation."""
        return self._observable.version

    def _default_state(self) -> dict[str, Any]:
        """Return default app state (matches TypeScript getDefaultAppState)."""
        return {
            "messages": [],
            "tasks": {},
            "agents": {},
            "settings": {},
            "permission_mode": "review",
            "mcp": {"clients": [], "tools": [], "commands": [], "resources": {}},
            "plugins": {"enabled": [], "disabled": [], "commands": [], "errors": []},
            "notifications": {"current": None, "queue": []},
            "expanded_view": "none",
            "verbose": False,
        }
```

---

## 5. Usage Examples

### 5.1 Textual Widget with Reactive State

```python
"""Example: Textual widget using reactive state."""
from textual.app import ComposeResult
from textual.widgets import Static, Button
from textual.reactive import reactive

from ..state.async_observable import AsyncObservable
from ..state.context import get_app_state


class TaskCounter(Static):
    """Displays and manages task count using reactive state."""

    # Textual's @reactive replaces useState + useSyncExternalStore
    task_count = reactive(0, layout=True)
    completed_count = reactive(0, layout=True)

    def watch_task_count(self, value: int) -> None:
        """Called automatically when task_count changes."""
        self.update(f"Tasks: {value} ({self.completed_count} done)")

    def watch_completed_count(self, value: int) -> None:
        """Called automatically when completed_count changes."""
        self.update(f"Tasks: {self.task_count} ({value} done)")

    def on_mount(self) -> None:
        """Subscribe to app state on mount."""
        store = get_app_state()

        def update_counts() -> None:
            state = store.get()
            self.task_count = len(state.get("tasks", {}))
            completed = sum(
                1 for t in state.get("tasks", {}).values()
                if t.get("status") == "completed"
            )
            self.completed_count = completed

        store.subscribe(update_counts)


class SettingsPanel(Static):
    """Panel showing current settings (selector pattern)."""

    def on_mount(self) -> None:
        self._store = get_app_state()
        self._unsubs: list[Callable] = []

        def render_settings() -> None:
            settings = self._store.get().get("settings", {})
            self.update(f"Theme: {settings.get('theme', 'default')}")

        self._store.subscribe(render_settings)
        self._unsubs.append(self._store.subscribe(render_settings))

    def on_unmount(self) -> None:
        for unsub in self._unsubs:
            unsub()
```

### 5.2 Async Effect on State Change

```python
"""Example: Effect that runs when settings change."""
import asyncio
from functools import partial

from ..state.async_observable import AsyncObservable
from ..state.effect import effect
from ..state.context import get_app_state


class SettingsSync:
    """Syncs settings to disk when they change."""

    def __init__(self) -> None:
        self._store = get_app_state()
        self._unsubs: list[Callable] = []

    @effect(deps=["settings"], on_mount=True)
    async def on_settings_change(self) -> None:
        """Called when settings key changes in state."""
        settings = self._store.get()["settings"]
        await self._persist_settings(settings)

    async def _persist_settings(self, settings: dict) -> None:
        """Write settings to disk."""
        # Implementation
        pass

    def cleanup(self) -> None:
        for unsub in self._unsubs:
            unsub()
```

### 5.3 Selector-Based Subscription

```python
"""Example: Select and react to a specific state slice."""
from ..state.async_observable import AsyncObservable
from ..state.selector import SelectorState


class NotificationWatcher:
    """Watches for new notifications."""

    def __init__(self, store: AsyncObservable[dict]) -> None:
        self._selector = SelectorState(
            store,
            selector=lambda state: state.get("notifications", {}).get("queue", [])
        )
        self._unsub: Callable | None = None

    def watch(self, callback: Callable[[list], None]) -> None:
        def notify() -> None:
            queue = self._selector.get()
            callback(queue)

        self._unsub = self._selector.subscribe(notify)

    def stop(self) -> None:
        if self._unsub:
            self._unsub()
```

### 5.4 Store Initialization in Textual App

```python
"""Example: Setting up the store in a Textual app."""
from textual.app import App, ComposeResult
from textual.widgets import Static

from ..state.app_state_store import AppStateStore
from ..state.context import app_state_context


class MyApp(App):
    """Textual app with integrated state management."""

    def __init__(self) -> None:
        super().__init__()
        # Create the store
        self.state_store = AppStateStore()
        # Set it in context so composables can access it
        app_state_context.set(self.state_store)

    def on_mount(self) -> None:
        """Start auto-checkpoint on mount."""
        asyncio.create_task(self.state_store.checkpoint_loop())

    async def on_unmount(self) -> None:
        """Final checkpoint on shutdown."""
        await self.state_store.checkpoint()


# Usage:
# python -m my_app
# All components use get_app_state() to access the store
```

---

## 6. Key Differences from TypeScript

| Aspect | TypeScript/React | Python/Textual |
|--------|-----------------|----------------|
| **Reactivity model** | `useSyncExternalStore` + React render cycle | `@reactive` decorator + Textual widget lifecycle |
| **Context** | React.createContext + Provider | Python `contextvars.ContextVar` |
| **Effect timing** | `useEffect` + dependency array | `@effect` decorator + `asyncio.create_task` |
| **State immutability** | Enforced by `Object.is` check | Identity check (`is`) for dicts, equality for value types |
| **Async side-effects** | In `onChange` callback | In `StateChangeHandler` via async handlers |
| **Selector pattern** | `useAppState(s => s.foo)` | `SelectorState` class + `subscribe` |
| **Component lifecycle** | Mount/unmount via useEffect | `on_mount`/`on_unmount` in Textual widgets |
| **Update batching** | Automatic via React | Explicit via `set()` (sync) or `set_async()` (awaits) |
| **Store creation** | `createStore(initial, onChange?)` | `AppStateStore(initial?)` |

---

## 7. File Structure

```
src_py/state/
├── __init__.py              # Public API exports
├── async_observable.py      # AsyncObservable[T] class
├── change_record.py          # ChangeRecord dataclass
├── state_change_handler.py   # StateChangeHandler + default handlers
├── app_state_store.py        # AppStateStore (full integration)
├── context.py               # ContextVar for app-wide state access
├── effect.py                # @effect decorator
├── selector.py              # SelectorState for derived values
├── hooks.py                 # Legacy hooks (use_state, use_key, etc.)
├── store.py                 # Legacy StateStore (existing, WAL-based)
└── app_state.py             # AppState dataclass (existing)
```

---

## 8. Implementation Notes

1. **Backward compatibility**: The existing `store.py` (StateStore with WAL) should be preserved for disk-backed persistence. The new `AppStateStore` wraps it and adds the observable layer.

2. **Textual integration**: Prefer Textual's native `@reactive` over custom hooks where possible. The custom hooks are for cross-component state sharing; local widget state should use `@reactive`.

3. **Async default**: All state updates that trigger side-effects should use `set_async()`. Sync `set()` is for pure state transitions with no external effects.

4. **No circular imports**: Use lazy imports in handlers (e.g., `_settings_change_handler`) to avoid circular dependency issues.

5. **Type safety**: Use `Generic[T]` throughout to maintain type hints for selected state slices.
