# Phase 7: UI Components Design Document
## TypeScript React Components to Python Textual Implementation

**Date:** 2026-04-06
**Status:** Design Complete
**Purpose:** Guide Python Textual implementation of the Claude Code UI component system

---

## 1. Component Architecture Overview

### 1.1 High-Level Structure

The TypeScript UI is organized into these primary directories:

```
src/components/
  design-system/     # Base reusable components (Dialog, Pane, Tabs, etc.)
  PromptInput/       # Main user input component and sub-components
  messages/          # Message rendering components (AssistantTextMessage, etc.)
  permissions/       # Permission request dialogs
  tasks/             # Task-related UI components
  teams/             # Team collaboration UI
  LogoV2/            # Logo and branding components
  FeedbackSurvey/    # Feedback collection UI
  CustomSelect/      # Custom dropdown select component
  ...
```

### 1.2 Component Hierarchy

The main application structure follows this nesting pattern:

```
FullscreenLayout
├── ScrollBox (for messages)
│   ├── LogoV2 (conditional)
│   ├── VirtualMessageList (messages container)
│   │   └── MessageRow (per-message rendering)
│   │       └── [Message-specific components]
│   └── StatusNotices
├── bottom slot (pinned content)
│   ├── Spinner
│   ├── PromptInput
│   └── PermissionRequest
├── modal slot (overlay dialogs)
│   └── [Various Dialog components]
└── bottomFloat slot (floating over scrollback)
```

### 1.3 Key Design Patterns

#### Widget Composition Pattern
React components compose `Box`, `Text`, and other base components. In Textual, this maps to composing `Widget` subclasses.

```typescript
// TypeScript - Dialog.tsx
export function Dialog({ title, subtitle, children, onCancel, color = 'permission' }) {
  return (
    <Pane color={color}>
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold color={color}>{title}</Text>
          {subtitle && <Text dimColor>{subtitle}</Text>}
        </Box>
        {children}
      </Box>
      {!hideInputGuide && (
        <Box marginTop={1}>
          <Text dimColor italic>
            <Byline>
              <KeyboardShortcutHint shortcut="Enter" action="confirm" />
              <ConfigurableShortcutHint action="confirm:no" context="Confirmation" fallback="Esc" />
            </Byline>
          </Text>
        </Box>
      )}
    </Pane>
  )
}
```

**Textual Python Equivalent:**
```python
class Dialog(Widget):
    def __init__(self, title, subtitle=None, children=None, on_cancel=None, color="permission", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.on_cancel = on_cancel
        self.color = color

    def compose(self):
        with Pane(color=self.color):
            with Box(orientation="vertical", gap=1):
                yield Box(orientation="vertical"):
                    yield Text(self.title, bold=True, color=self.color)
                    if self.subtitle:
                        yield Text(self.subtitle, dim=True)
                # children would be added via compose or mount
```

#### 1.4 Design System Components

**Base Components (design-system/):**

| TypeScript Component | Purpose | Textual Equivalent |
|---------------------|---------|-------------------|
| `Dialog` | Modal dialog with title, content, keybindings | `ModalScreen` or custom `Dialog` widget |
| `Pane` | Bordered region with colored top border | `Panel` or custom `Pane` widget |
| `Tabs` | Tabbed interface with keyboard navigation | `Tabs` widget (Textual has built-in) |
| `Divider` | Horizontal line separator | `Static` with horizontal rule characters |
| `Text` | Styled text with color, bold, italic | `Text` widget |
| `Box` | Flexbox-like container | `Horizontal`/`Vertical` or `Container` |
| `ThemedText` | Theme-aware text colors | Custom `Text` subclass with theme |
| `Byline` | Inline hint text layout | `Horizontal` with spacing |
| `KeyboardShortcutHint` | Shows keyboard shortcuts | Custom widget |

---

## 2. State Management Patterns

### 2.1 Global State Store

The application uses a centralized Zustand-like store pattern defined in `src/state/store.ts`:

```typescript
// store.ts
type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}

export function createStore<T>(initialState: T, onChange?: OnChange<T>): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,
    setState: (updater) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return
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

**Textual Python Equivalent:**
```python
from typing import TypeVar, Generic, Callable, Set
from dataclasses import dataclass, field

T = TypeVar('T')

@dataclass
class Store(Generic[T]):
    _state: T = field(default=None)
    _listeners: Set[Callable[[], None]] = field(default_factory=set)
    _on_change: Callable[[dict, dict], None] | None = None

    def __init__(self, initial_state: T, on_change: Callable[[dict, dict], None] | None = None):
        self._state = initial_state
        self._on_change = on_change

    def get_state(self) -> T:
        return self._state

    def set_state(self, updater: Callable[[T], T]) -> None:
        prev = self._state
        next_state = updater(prev)
        if next_state == prev:
            return
        self._state = next_state
        if self._on_change:
            self._on_change({"new_state": next_state, "old_state": prev})
        for listener in self._listeners:
            listener()

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)
        def unsubscribe():
            self._listeners.discard(listener)
        return unsubscribe
```

### 2.2 AppState Structure

The main application state (`AppStateStore.ts`) contains:

```typescript
export interface AppState {
  // UI State
  verbose: boolean
  messages: Message[]
  input: string
  mode: PromptInputMode

  // Agent State
  tasks: Record<string, TaskState>
  viewingAgentTaskId: string | null

  // Settings
  theme: Theme
  thinkingEnabled: boolean
  fastMode: boolean

  // Streaming
  streamingThinking: StreamingThinking | null
  streamingText: string | null

  // Navigation
  scrollPosition: number
  cursor: MessageActionsState | null
}
```

### 2.3 useAppState Hook Pattern

Components subscribe to state slices using `useAppState`:

```typescript
// AppState.tsx
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()

  const get = () => {
    const state = store.getState()
    const selected = selector(state)
    return selected
  }

  return useSyncExternalStore(store.subscribe, get, get)
}

// Usage in components:
const verbose = useAppState(s => s.verbose)
const thinkingEnabled = useAppState(s => s.thinkingEnabled)
const { text, promptId } = useAppState(s => s.promptSuggestion)
```

**Textual Python Equivalent:**
```python
from typing import TypeVar, Generic, Callable, Any
from reactive import var, computed

class AppStateMixin:
    """Mixin for widgets that need app state access"""
    _app_state: Store[dict] = None

    @classmethod
    def set_app_state_store(cls, store: Store):
        cls._app_state = store

    def get_app_state(self):
        return self._app_state.get_state() if self._app_state else {}

    def subscribe_to_state(self, key: str, callback: Callable[[Any], None]):
        """Subscribe to changes in a specific state key"""
        def listener():
            state = self.get_app_state()
            if key in state:
                callback(state[key])
        if self._app_state:
            return self._app_state.subscribe(listener)
        return lambda: None

# Or use reactive primitives:
class MessageList(Widget):
    messages = var(list)
    verbose = var(bool)

    @computed
    def visible_messages(self):
        if self.verbose:
            return self.messages
        return [m for m in self.messages if not m.get("isMeta")]
```

### 2.4 Context Pattern for UI State

React Context is used for UI-specific state:

```python
@dataclass
class ScrollChromeState:
    sticky_prompt: Optional[str] = None
    set_sticky_prompt: Callable[[Optional[str]], None] = lambda x: None

@dataclass
class ThemeColors:
    primary: str = "white"
    secondary: str = "dim"
    permission: str = "yellow"
    error: str = "red"

class ThemeContext:
    def __init__(self):
        self._theme = ThemeColors()
        self._subscribers: list = []

    @property
    def theme(self):
        return self._theme

    def set_theme(self, theme: ThemeColors):
        self._theme = theme
        for callback in self._subscribers:
            callback(theme)

    def subscribe(self, callback):
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

# Global instances
scroll_chrome_context = ScrollChromeState()
theme_context = ThemeContext()
```

---

## 3. Virtual List Implementation

### 3.1 VirtualMessageList Component

The `VirtualMessageList` component handles virtualized rendering of messages for performance.

**Key Features:**
- Height caching for items not yet measured
- Overscan (80 rows) to prevent blank areas during scroll
- Sticky prompt tracking for user prompts
- Search index warming for transcript search
- Imperative `JumpHandle` for programmatic navigation

**Constants:**
- `DEFAULT_ESTIMATE = 3` rows for unmeasured items
- `OVERSCAN_ROWS = 80` rows of overscan above/below viewport
- `COLD_START_COUNT = 30` items before first layout
- `SCROLL_QUANTUM = 40` rows (half of overscan for scroll sync)
- `MAX_MOUNTED_ITEMS = 300` cap on fiber allocation
- `SLIDE_STEP = 25` max new items per commit

**Textual Python Equivalent:**
```python
from typing import Generic, TypeVar, Callable, Sequence
from dataclasses import dataclass, field
import bisect

T = TypeVar('T')

@dataclass
class VirtualScrollResult(Generic[T]):
    range_start: int
    range_end: int
    top_spacer: int = 0
    bottom_spacer: int = 0
    offsets: list[int] = field(default_factory=list)
    _height_cache: dict[int, int] = field(default_factory=dict)
    _items: list[T] = field(default_factory=list)
    _scroll_ref: 'ScrollBox | None' = None

    DEFAULT_ESTIMATE = 3
    OVERSCAN_ROWS = 80
    MAX_MOUNTED_ITEMS = 300
    SLIDE_STEP = 25

    def compute_range(self, viewport_top: int, viewport_height: int) -> tuple[int, int]:
        """Compute visible range with overscan"""
        start_idx = max(0, bisect.bisect_right(self.offsets, viewport_top) - 1)
        viewport_bottom = viewport_top + viewport_height
        end_idx = bisect.bisect_left(self.offsets, viewport_bottom)
        start_idx = max(0, start_idx - self.OVERSCAN_ROWS)
        end_idx = min(len(self._items), end_idx + self.OVERSCAN_ROWS)
        if end_idx - start_idx > self.MAX_MOUNTED_ITEMS:
            end_idx = start_idx + self.MAX_MOUNTED_ITEMS
        return start_idx, end_idx

    def measure_item(self, index: int, height: int) -> None:
        """Cache measured height after layout"""
        self._height_cache[index] = height
        self._recompute_offsets(index)

    def _recompute_offsets(self, from_index: int) -> None:
        """Recompute offsets array from from_index onward"""
        for i in range(from_index, len(self._items)):
            if i == 0:
                self.offsets[i] = self._height_cache.get(i, self.DEFAULT_ESTIMATE)
            else:
                prev = self.offsets[i-1] if i > 0 else 0
                self.offsets[i] = prev + self._height_cache.get(i, self.DEFAULT_ESTIMATE)

    def get_item_height(self, index: int) -> int:
        return self._height_cache.get(index, self.DEFAULT_ESTIMATE)

    def scroll_to_index(self, index: int) -> None:
        if self._scroll_ref and index < len(self.offsets):
            self._scroll_ref.scroll_home()
            position = self.offsets[index] if index < len(self.offsets) else 0
            self._scroll_ref.scroll_to(position)
```

### 3.2 Message Rendering Chain

Messages are rendered through a chain:
1. `Messages.tsx` - Container managing message list
2. `VirtualMessageList.tsx` - Virtualization wrapper
3. `MessageRow.tsx` - Individual message wrapper
4. `messages/*.tsx` - Specific message type renderers

**Message Types:**
- `UserPromptMessage` - User input
- `AssistantTextMessage` - Claude's text responses
- `AssistantToolUseMessage` - Tool calls and results
- `SystemTextMessage` - System notifications
- `AttachmentMessage` - Queued commands, files
- `AssistantThinkingMessage` - Thinking blocks

---

## 4. Dialog and Modal Patterns

### 4.1 Dialog Component

```typescript
// design-system/Dialog.tsx
type DialogProps = {
  title: React.ReactNode
  subtitle?: React.ReactNode
  children: React.ReactNode
  onCancel: () => void
  color?: keyof Theme
  hideInputGuide?: boolean
  hideBorder?: boolean
  inputGuide?: (exitState: ExitState) => React.ReactNode
  isCancelActive?: boolean
}
```

**Key Behaviors:**
- Uses `useExitOnCtrlCDWithKeybindings` for Ctrl+C/D handling
- Registers `confirm:no` keybinding for Escape key
- `isCancelActive` flag allows disabling cancel while editing text fields
- Wraps in `Pane` for border styling

### 4.2 Modal System

```typescript
// context/modalContext.tsx
export const ModalContext = createContext<{
  isInsideModal: boolean
  modalScrollRef: RefObject<ScrollBoxHandle | null>
}>({
  isInsideModal: false,
  modalScrollRef: null
})
```

**Textual Python Equivalent:**
```python
class ModalScreen(Screen):
    def __init__(self, child_widget, on_cancel=None, color="permission", **kwargs):
        super().__init__(**kwargs)
        self.child_widget = child_widget
        self.on_cancel = on_cancel
        self.color = color
        self._is_active = True

    def on_key(self, event: Key) -> bool:
        if event.key == "escape" and self.on_cancel:
            self.on_cancel()
            return True
        if event.key == "enter":
            return True
        return self.child_widget.on_key(event) if hasattr(self.child_widget, 'on_key') else False

    def compose(self):
        yield Pane(self.color)
        yield self.child_widget

class OverlayManager:
    """Manages modal overlays preventing background interaction"""
    _overlays: list[ModalScreen] = []

    @classmethod
    def push(cls, overlay: ModalScreen):
        cls._overlays.append(overlay)

    @classmethod
    def pop(cls) -> ModalScreen | None:
        return cls._overlays.pop() if cls._overlays else None

    @classmethod
    def is_active(cls) -> bool:
        return len(cls._overlays) > 0
```

---

## 5. Input Handling

### 5.1 PromptInput Component

The main user input component handles:

**Key Features:**
- Multi-line input with vim mode support
- Paste handling (images, files, text)
- Slash command suggestions
- History search (arrow keys)
- Cursor position tracking
- Voice input integration
- Insert text API for external injection

### 5.2 TextInput Component

```typescript
// TextInput.tsx
export default function TextInput(props: Props): React.ReactNode {
  const [theme] = useTheme()
  const isTerminalFocused = useTerminalFocus()
  const textInputState = useTextInput({
    value: props.value,
    onChange: props.onChange,
    onSubmit: props.onSubmit,
  })

  return (
    <BaseTextInput
      inputState={textInputState}
      terminalFocus={isTerminalFocused}
      highlights={props.highlights}
      invert={chalk.inverse}
      {...props}
    />
  )
}
```

**Textual Python Equivalent:**
```python
class BaseTextInput(Widget):
    def __init__(
        self,
        value: str = "",
        placeholder: str = "",
        on_change: Callable[[str], None] | None = None,
        on_submit: Callable[[], None] | None = None,
        password: bool = False,
        multiline: bool = False,
        max_lines: int | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._value = value
        self._placeholder = placeholder
        self._on_change = on_change
        self._on_submit = on_submit
        self._password = password
        self._multiline = multiline
        self._max_lines = max_lines
        self._cursor_position = len(value)
        self._focused = False

    def render(self) -> Text:
        content = self._value if self._value else self._placeholder
        if self._password:
            content = "*" * len(content)
        style = "bold" if self._focused else ""
        return Text(content, style=style)

    def on_key(self, event: Key) -> bool:
        if event.key == "enter" and not self._multiline:
            if self._on_submit:
                self._on_submit()
            return True
        return False
```

### 5.3 Input State Types

```typescript
// types/textInputTypes.ts
type PromptInputMode = 'edit' | 'vim_normal' | 'vim_insert' | 'vim_visual'

interface BaseInputState {
  onInput: (input: string, key: Key) => void
  renderedValue: string
  cursorLine: number
  cursorColumn: number
  viewportCharOffset: number
  viewportCharEnd: number
}
```

---

## 6. Styling with Textual CSS

### 6.1 Theme System

```typescript
// utils/theme.ts
export type Theme = {
  primary: string
  secondary: string
  dim: string
  error: string
  warning: string
  success: string
  permission: string
  info: string
}
```

### 6.2 Color System

```typescript
// design-system/color.ts
export const colors = {
  permission: '#f0b000',  // Yellow for permission dialogs
  error: '#f85149',      // Red for errors
  success: '#3fb950',    // Green for success
  primary: '#58a6ff',    // Blue for primary actions
  info: '#8b949e',       // Gray for info
} as const
```

**Textual Python Equivalent:**
```python
from enum import Enum

class Colors(str, Enum):
    PERMISSION = "#f0b000"
    ERROR = "#f85149"
    SUCCESS = "#3fb950"
    PRIMARY = "#58a6ff"
    INFO = "#8b949e"
    DIM = "#6e7681"
```

### 6.3 Textual CSS Approach

```python
# Textual implementation approach
from textual.widget import Widget
from textual.widgets import Static, Input, Button

class Dialog(Widget):
    """Dialog with border and content area"""
    DEFAULT_CSS = """
    Dialog {
        width: 100%;
        height: auto;
        border: solid $permission;
        padding: 1 2;
    }
    """

    def compose(self):
        yield Static(self.title, classes="dialog-title")
        yield self._content
        yield Static(self._hint_text, classes="dialog-hint")

class Pane(Widget):
    """Pane with colored top border"""
    DEFAULT_CSS = """
    Pane {
        padding-top: 1;
    }
    """
```

---

## 7. Event Handling Patterns

### 7.1 Keybinding System

```typescript
// keybindings/useKeybinding.ts
export function useKeybinding(
  action: string,
  handler: () => void,
  options?: {
    context?: string
    isActive?: boolean
  }
)
```

**Textual Python Equivalent:**
```python
class InputHandlerMixin:
    """Mixin for widgets that handle keyboard input"""
    _input_active = True

    def on_key(self, event: Key) -> bool:
        if not self._input_active:
            return False

        if event.key == "enter":
            self._handle_submit()
            return True
        elif event.key == "escape":
            self._handle_cancel()
            return True
        elif event.key == "backspace":
            self._handle_backspace()
            return True
        elif event.key == "up":
            self._handle_history_up()
            return True
        elif event.key == "down":
            self._handle_history_down()
            return True
        elif event.key.is_printable:
            self._handle_character(event.key)
            return True

        return False
```

---

## 8. Component Category Summary

### 8.1 PromptInput Sub-Components

| Component | Purpose |
|-----------|---------|
| `PromptInput.tsx` | Main input component |
| `PromptInputFooter.tsx` | Footer with hints and status |
| `PromptInputFooterSuggestions.tsx` | Slash command suggestions |
| `PromptInputModeIndicator.tsx` | Shows current mode (vim, etc.) |
| `PromptInputQueuedCommands.tsx` | Shows queued commands |
| `PromptInputStashNotice.tsx` | Notice when prompt is stashed |
| `PromptInputHelpMenu.tsx` | Help overlay |
| `usePromptInputPlaceholder.ts` | Placeholder text logic |
| `useMaybeTruncateInput.ts` | Input truncation logic |
| `useShowFastIconHint.ts` | Fast mode icon hint |
| `inputModes.ts` | Mode state management |
| `ShimmeredInput.tsx` | Animated input highlighting |

### 8.2 Message Components

| Component | Purpose |
|-----------|---------|
| `Messages.tsx` | Message list container |
| `VirtualMessageList.tsx` | Virtualized message list |
| `MessageRow.tsx` | Individual message wrapper |
| `messages/AssistantTextMessage.tsx` | Text response |
| `messages/AssistantToolUseMessage.tsx` | Tool call/result |
| `messages/AssistantThinkingMessage.tsx` | Thinking block |
| `messages/UserPromptMessage.tsx` | User input |
| `messages/SystemTextMessage.tsx` | System notification |
| `messages/AttachmentMessage.tsx` | Queued command/file |
| `MessageSelector.tsx` | Message selection UI |

### 8.3 Dialog Components

| Component | Purpose |
|-----------|---------|
| `GlobalSearchDialog.tsx` | Workspace search (ctrl+shift+f) |
| `HistorySearchDialog.tsx` | History search |
| `BridgeDialog.tsx` | Bridge configuration |
| `MCPServerApprovalDialog.tsx` | MCP server approval |
| `MCPServerMultiselectDialog.tsx` | MCP server selection |
| `AutoModeOptInDialog.tsx` | Auto mode consent |
| `CostThresholdDialog.tsx` | Cost threshold warning |
| `ExitFlow.tsx` | Exit confirmation |
| `IdleReturnDialog.tsx` | Idle return dialog |
| `BackgroundTasksDialog.tsx` | Background tasks list |
| `TeamsDialog.tsx` | Team management |

### 8.4 Design System Components

| Component | Purpose |
|-----------|---------|
| `Dialog.tsx` | Base dialog |
| `Pane.tsx` | Bordered container |
| `Tabs.tsx` | Tabbed interface |
| `Divider.tsx` | Horizontal separator |
| `ThemedText.tsx` | Theme-aware text |
| `ThemedBox.tsx` | Theme-aware box |
| `Byline.tsx` | Inline hint layout |
| `KeyboardShortcutHint.tsx` | Shortcut display |
| `ListItem.tsx` | List item |
| `FuzzyPicker.tsx` | Fuzzy selection list |
| `LoadingState.tsx` | Loading indicator |
| `ProgressBar.tsx` | Progress indicator |

---

## 9. Implementation Priorities

### Phase 7.1: Foundation
1. Implement `Store` class for state management
2. Implement `AppStateStore` with full state shape
3. Create `useAppState` equivalent (reactive vars or observer pattern)
4. Implement theme system and colors
5. Create base `Widget` classes for Dialog, Pane, Box, Text

### Phase 7.2: Core Components
1. Implement `BaseTextInput` with cursor and paste handling
2. Implement `TextInput` component
3. Implement `Dialog` with keybinding support
4. Implement `Pane` with border styling
5. Implement `Divider` component

### Phase 7.3: Layout and Lists
1. Implement `FullscreenLayout` with scroll container
2. Implement `VirtualMessageList` with virtual scroll equivalent
3. Implement message rendering chain
4. Implement `Tabs` component

### Phase 7.4: PromptInput
1. Implement `PromptInput` main component
2. Implement footer and suggestion components
3. Implement history navigation
4. Implement vim mode support
5. Implement slash command handling

### Phase 7.5: Dialogs and Overlays
1. Implement modal overlay system
2. Implement keybinding system
3. Port key dialogs (GlobalSearch, HistorySearch, etc.)

---

## 10. Key Implementation Challenges

1. **Virtual scrolling** - Textual's reactive nature vs React's imperative model
2. **Keybinding system** - Centralized vs distributed handling
3. **State synchronization** - React's synchronous model vs Textual's async reactive model
4. **Cursor management** - Terminal cursor positioning differs from DOM
