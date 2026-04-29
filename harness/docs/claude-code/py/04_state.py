"""
状态管理 Python 实现

展示 Claude Code 状态管理系统的核心设计模式在 Python 中的实现：
- Observable Store 模式
- React Hook 等价物
- AppState 类型
- 状态变更处理
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    TypeVar,
    Type,
    Iterator,
    Union,
)
from functools import wraps
import copy


# =============================================================================
# 1. Store 类型定义
# =============================================================================

T = TypeVar('T')
S = TypeVar('S')


class Listener(Protocol[T]):
    """监听器协议"""
    def __call__(self, state: T) -> None: ...


@dataclass
class StoreConfig(Generic[T]):
    """Store 配置"""
    initial_state: T
    on_change: Optional[Callable[[T], None]] = None


# =============================================================================
# 2. Observable Store 实现
# =============================================================================

class Store(Generic[T]):
    """
    Observable Store

    等价于 TypeScript 的 createStore()
    """

    def __init__(
        self,
        initial_state: T,
        on_change: Optional[Callable[[T], None]] = None
    ):
        self._state: T = initial_state
        self._listeners: Set[Listener[T]] = set()
        self._on_change = on_change

    def get_state(self) -> T:
        """获取当前状态"""
        return self._state

    def set_state(self, updater: Union[T, Callable[[T], T]]) -> None:
        """
        更新状态

        支持两种方式：
        1. 直接设置: store.set_state(new_state)
        2. 函数式更新: store.set_state(lambda prev: {...})
        """
        # 函数式更新
        if callable(updater):
            next_state = updater(self._state)
        else:
            next_state = updater

        # Memoization guard - Object.is 等价检查
        if not self._is_equal(next_state, self._state):
            self._state = next_state

            # 通知所有监听器
            for listener in self._listeners:
                listener(self._state)

            # 调用 on_change 回调
            if self._on_change:
                self._on_change(self._state)

    def subscribe(self, listener: Listener[T]) -> Callable[[], None]:
        """
        订阅状态变更

        返回取消订阅函数
        """
        self._listeners.add(listener)

        def unsubscribe():
            self._listeners.discard(listener)

        return unsubscribe

    def _is_equal(self, a: Any, b: Any) -> bool:
        """检查是否相等 (Object.is 等价)"""
        if a is b:
            return True
        if type(a) != type(b):
            return False
        if isinstance(a, dict):
            if set(a.keys()) != set(b.keys()):
                return False
            return all(self._is_equal(a[k], b[k]) for k in a)
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(self._is_equal(x, y) for x, y in zip(a, b))
        return False


# =============================================================================
# 3. AppState 类型定义
# =============================================================================

@dataclass
class SettingsJson:
    """设置 JSON"""
    model: Optional[str] = None
    theme: str = "auto"
    thinking_enabled: bool = True
    verbose: bool = False


@dataclass
class ConnectionStatus:
    """连接状态"""
    status: str = "disconnected"  # connecting, connected, reconnecting, disconnected
    url: Optional[str] = None


@dataclass
class MCPServerConnection:
    """MCP 服务器连接"""
    id: str
    name: str
    status: str
    tools: List[Any] = field(default_factory=list)


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    subject: str
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppState:
    """
    应用状态

    等价于 TypeScript 的 AppState
    """
    # ========== 会话与 UI 状态 ==========
    settings: SettingsJson = field(default_factory=SettingsJson)
    verbose: bool = False
    main_loop_model: Optional[str] = None
    main_loop_model_for_session: Optional[str] = None
    status_line_text: Optional[str] = None
    expanded_view: str = "none"  # 'none', 'tasks', 'teammates'
    is_brief_only: bool = False
    coordinator_task_index: int = 0
    view_selection_mode: str = "none"  # 'none', 'selecting-agent', 'viewing-agent'
    footer_selection: Optional[Any] = None
    spinner_tip: Optional[str] = None

    # ========== 远程/桥接状态 ==========
    remote_session_url: Optional[str] = None
    remote_connection_status: ConnectionStatus = field(
        default_factory=ConnectionStatus
    )
    remote_background_task_count: int = 0
    repl_bridge_enabled: bool = False
    repl_bridge_connected: bool = False
    repl_bridge_session_active: bool = False
    repl_bridge_reconnecting: bool = False

    # ========== 任务状态 ==========
    tasks: Dict[str, TaskState] = field(default_factory=dict)
    agent_name_registry: Dict[str, str] = field(default_factory=dict)
    foregrounded_task_id: Optional[str] = None
    viewing_agent_task_id: Optional[str] = None

    # ========== MCP/插件状态 ==========
    mcp: Dict[str, Any] = field(default_factory=lambda: {
        'clients': [],
        'tools': [],
        'commands': [],
        'resources': {},
        'plugin_reconnect_key': 0
    })
    plugins: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': [],
        'disabled': [],
        'errors': [],
        'needs_refresh': False
    })

    # ========== 推测/AI 状态 ==========
    speculation: Dict[str, Any] = field(default_factory=lambda: {'status': 'idle'})
    thinking_enabled: Optional[bool] = None
    prompt_suggestion_enabled: bool = True
    prompt_suggestion: Optional[Dict[str, Any]] = None

    # ========== 通知 ==========
    notifications: Dict[str, Any] = field(default_factory=lambda: {
        'current': None,
        'queue': []
    })


# =============================================================================
# 4. 默认状态工厂
# =============================================================================

def get_default_app_state() -> AppState:
    """
    获取默认 AppState

    等价于 TypeScript 的 getDefaultAppState()
    """
    return AppState(
        settings=SettingsJson(),
        verbose=False,
        expanded_view="none",
        is_brief_only=False,
        coordinator_task_index=0,
        view_selection_mode="none",
        remote_connection_status=ConnectionStatus(),
        tasks={},
        agent_name_registry={},
        mcp={
            'clients': [],
            'tools': [],
            'commands': [],
            'resources': {},
            'plugin_reconnect_key': 0
        },
        plugins={
            'enabled': [],
            'disabled': [],
            'errors': [],
            'needs_refresh': False
        },
        speculation={'status': 'idle'},
        thinking_enabled=True,
        prompt_suggestion_enabled=True,
        notifications={'current': None, 'queue': []}
    )


# =============================================================================
# 5. 状态变更处理
# =============================================================================

class StateChangeHandler:
    """
    状态变更处理

    等价于 TypeScript 的 onChangeAppState()
    """

    def __init__(
        self,
        on_permission_mode_changed: Optional[Callable] = None,
        on_settings_changed: Optional[Callable] = None,
        on_cache_invalidated: Optional[Callable] = None
    ):
        self.on_permission_mode_changed = on_permission_mode_changed
        self.on_settings_changed = on_settings_changed
        self.on_cache_invalidated = on_cache_invalidated

    def handle(
        self,
        prev_state: AppState,
        new_state: AppState
    ) -> None:
        """处理状态变更"""
        # 1. 权限模式同步
        if hasattr(prev_state, 'permission_mode') and hasattr(new_state, 'permission_mode'):
            if prev_state.permission_mode != new_state.permission_mode:
                self._handle_permission_mode_change(prev_state, new_state)

        # 2. 设置持久化
        if prev_state.settings != new_state.settings:
            self._handle_settings_change(prev_state, new_state)

        # 3. 认证缓存失效
        if prev_state.settings != new_state.settings:
            self._handle_cache_invalidation(prev_state, new_state)

        # 4. MCP/插件状态
        if prev_state.mcp.get('plugin_reconnect_key') != new_state.mcp.get('plugin_reconnect_key'):
            self._handle_mcp_reconnect(new_state)

        if new_state.plugins.get('needs_refresh'):
            self._handle_plugin_refresh()

    def _handle_permission_mode_change(
        self,
        prev_state: AppState,
        new_state: AppState
    ) -> None:
        """处理权限模式变更"""
        if self.on_permission_mode_changed:
            self.on_permission_mode_changed(new_state.permission_mode)

    def _handle_settings_change(
        self,
        prev_state: AppState,
        new_state: AppState
    ) -> None:
        """处理设置变更"""
        if self.on_settings_changed:
            self.on_settings_changed(new_state.settings)

    def _handle_cache_invalidation(
        self,
        prev_state: AppState,
        new_state: AppState
    ) -> None:
        """处理缓存失效"""
        if prev_state.settings.env != new_state.settings.env:
            if self.on_cache_invalidated:
                self.on_cache_invalidated()

    def _handle_mcp_reconnect(self, state: AppState) -> None:
        """处理 MCP 重连"""
        pass

    def _handle_plugin_refresh(self) -> None:
        """处理插件刷新"""
        pass


# =============================================================================
# 6. 选择器模式
# =============================================================================

def selector(func: Callable[[AppState], T]) -> Callable[[AppState], T]:
    """选择器装饰器"""
    @wraps(func)
    def wrapper(state: AppState) -> T:
        return func(state)
    return wrapper


# 预定义选择器
def get_viewed_teammate_task(state: AppState) -> Optional[TaskState]:
    """获取当前查看的 teammate 任务"""
    if not state.viewing_agent_task_id:
        return None
    return state.tasks.get(state.viewing_agent_task_id)


def get_active_agent_for_input(state: AppState) -> Dict[str, Any]:
    """
    确定用户输入应该路由到哪里

    等价于 TypeScript 的 getActiveAgentForInput()
    """
    # 1. 如果正在查看 teammate view
    if state.viewing_agent_task_id:
        task = state.tasks.get(state.viewing_agent_task_id)
        if task:
            return {'type': 'viewed', 'task': task}

    # 2. 如果有前台任务
    if state.foregrounded_task_id:
        task = state.tasks.get(state.foregrounded_task_id)
        if task:
            return {'type': 'named_agent', 'task': task}

    # 3. 默认发送到 leader
    return {'type': 'leader'}


# =============================================================================
# 7. React Hook 等价物
# =============================================================================

class ReactStoreHook(Generic[T]):
    """
    React Hook 等价物

    等价于 useSyncExternalStore + useAppState
    """

    def __init__(self, store: Store[T]):
        self._store = store
        self._current_value: Optional[T] = None
        self._unsubscribe: Optional[Callable] = None

    def use(self, selector: Callable[[T], S]) -> S:
        """
        使用 Hook

        等价于 useAppState(selector)
        """
        # 获取当前选定值
        current_state = self._store.get_state()
        selected_value = selector(current_state)

        # 订阅变更
        self._subscribe(selector)

        return selected_value

    def _subscribe(self, selector: Callable[[T], Any]) -> None:
        """订阅状态变更"""
        def listener(state: T):
            new_value = selector(state)
            # 使用存储的值进行比较
            current_state = self._store.get_state()
            if selector(current_state) != new_value:
                # 触发重渲染 (在真实 React 中)
                self._invalidate()

        self._unsubscribe = self._store.subscribe(listener)

    def _invalidate(self) -> None:
        """触发重渲染 - 在真实 React 中这会是 setState"""
        pass


class UseStateHook(Generic[T]):
    """
    状态更新 Hook (不订阅)

    等价于 useSetAppState()
    """

    def __init__(self, store: Store):
        self._store = store

    def set_state(self, updater: Union[T, Callable[[T], T]]) -> None:
        """
        更新状态

        等价于 useSetAppState()
        """
        self._store.set_state(updater)


# =============================================================================
# 8. Provider 模式
# =============================================================================

class AppStateProvider:
    """
    AppState Provider

    等价于 React 的 AppStateProvider
    """

    _instance: Optional['AppStateProvider'] = None
    _store: Optional[Store[AppState]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'AppStateProvider':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(
        self,
        initial_state: Optional[AppState] = None,
        on_change: Optional[Callable[[AppState], None]] = None
    ) -> None:
        """初始化"""
        state = initial_state or get_default_app_state()
        self._store = Store(state, on_change)

        # 设置状态变更处理
        if on_change:
            self._store._on_change = on_change

    def get_store(self) -> Store[AppState]:
        """获取 Store"""
        if self._store is None:
            raise RuntimeError("AppStateProvider not initialized")
        return self._store

    def get_state(self) -> AppState:
        """获取状态"""
        return self._store.get_state()

    def set_state(self, updater: Union[AppState, Callable[[AppState], AppState]]) -> None:
        """设置状态"""
        self._store.set_state(updater)


# =============================================================================
# 9. Teammate View Helpers
# =============================================================================

class TeammateViewHelpers:
    """
    Teammate View 状态转换辅助

    等价于 TypeScript 的 teammateViewHelpers.ts
    """

    @staticmethod
    def enter_teammate_view(
        task_id: str,
        set_state: Callable
    ) -> None:
        """进入 teammate view"""
        def updater(prev: AppState) -> AppState:
            new_state = copy.deepcopy(prev)
            new_state.viewing_agent_task_id = task_id
            new_state.foregrounded_task_id = prev.foregrounded_task_id  # 保留
            return new_state

        set_state(updater)

    @staticmethod
    def exit_teammate_view(set_state: Callable) -> None:
        """退出 teammate view"""
        def updater(prev: AppState) -> AppState:
            new_state = copy.deepcopy(prev)
            new_state.viewing_agent_task_id = None
            new_state.foregrounded_task_id = prev.foregrounded_task_id
            return new_state

        set_state(updater)

    @staticmethod
    def stop_or_dismiss_agent(
        task_id: str,
        set_state: Callable
    ) -> None:
        """停止或解散 agent"""
        def updater(prev: AppState) -> AppState:
            new_state = copy.deepcopy(prev)

            # 如果正在查看该 agent，退出 view
            if new_state.viewing_agent_task_id == task_id:
                new_state.viewing_agent_task_id = None

            # 移除任务
            if task_id in new_state.tasks:
                del new_state.tasks[task_id]

            return new_state

        set_state(updater)


# =============================================================================
# 10. 示例用法
# =============================================================================

def main():
    """示例用法"""

    # 创建状态变更处理器
    handler = StateChangeHandler(
        on_permission_mode_changed=lambda mode: print(f"Permission mode: {mode}"),
        on_settings_changed=lambda settings: print(f"Settings: {settings}"),
        on_cache_invalidated=lambda: print("Cache invalidated")
    )

    # 初始化 Provider
    provider = AppStateProvider.get_instance()
    provider.initialize(
        initial_state=get_default_app_state(),
        on_change=lambda state: handler.handle(
            provider.get_state(), state
        )
    )

    store = provider.get_store()

    # 使用 Hook
    hook = ReactStoreHook(store)

    # 选择器
    view_selection = hook.use(lambda s: s.view_selection_mode)
    print(f"View selection: {view_selection}")

    task_count = hook.use(lambda s: len(s.tasks))
    print(f"Task count: {task_count}")

    # 更新状态
    def new_task_updater(prev: AppState) -> AppState:
        new_state = copy.deepcopy(prev)
        new_state.tasks['task-1'] = TaskState(
            task_id='task-1',
            subject='Test Task',
            status='pending'
        )
        return new_state

    store.set_state(new_task_updater)

    print(f"New task count: {len(store.get_state().tasks)}")

    # 使用 TeammateViewHelpers
    TeammateViewHelpers.enter_teammate_view('task-1', store.set_state)
    print(f"Viewing agent: {store.get_state().viewing_agent_task_id}")

    TeammateViewHelpers.exit_teammate_view(store.set_state)
    print(f"Viewing agent after exit: {store.get_state().viewing_agent_task_id}")


if __name__ == "__main__":
    main()
