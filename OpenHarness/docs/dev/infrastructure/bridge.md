# Bridge 系统

本文档介绍 OpenHarness 的 Bridge 系统，用于管理子进程会话和桥接消息。

## 架构概览

```
src/openharness/bridge/
├── manager.py        # BridgeSessionManager — 会话追踪
├── session_runner.py # SessionHandle / spawn_session — 进程启动
├── types.py          # BridgeConfig、WorkData、WorkSecret
└── work_secret.py    # Work Secret 编解码
```

## BridgeSessionManager

`manager.py` 中的 `BridgeSessionManager` 管理所有桥接会话的生命周期：

```python
class BridgeSessionManager:
    """Manage bridge-run child sessions and capture their output."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionHandle] = {}
        self._commands: dict[str, str] = {}
        self._output_paths: dict[str, Path] = {}
        self._copy_tasks: dict[str, asyncio.Task[None]] = {}
```

### 核心方法

```python
async def spawn(
    self,
    *,
    session_id: str,
    command: str,
    cwd: str | Path,
) -> SessionHandle:
    """Spawn a bridge-managed child session."""

def list_sessions(self) -> list[BridgeSessionRecord]:
    """Return UI-safe session snapshots."""

def read_output(self, session_id: str, *, max_bytes: int = 12000) -> str:
    """Read buffered output for a session."""

async def stop(self, session_id: str) -> None:
    """Terminate a session gracefully."""
```

### 会话记录

```python
@dataclass(frozen=True)
class BridgeSessionRecord:
    session_id: str
    command: str
    cwd: str
    pid: int
    status: str        # "running" | "completed" | "failed"
    started_at: float
    output_path: str
```

### 输出捕获

每个会话的 stdout 被异步复制到 `~/.openharness/data/bridge/{session_id}.log`，支持：
- 实时流式写入
- 最多保留 12000 字节（可配置）

## SessionHandle

`session_runner.py` 中的 `SessionHandle` 是子进程的句柄：

```python
@dataclass
class SessionHandle:
    session_id: str
    process: asyncio.subprocess.Process
    cwd: Path
    started_at: float = field(default_factory=time.time)

    async def kill(self) -> None:
        """Terminate the session process gracefully, then kill if needed."""
```

### 会话启动

```python
async def spawn_session(
    *,
    session_id: str,
    command: str,
    cwd: str | Path,
) -> SessionHandle:
    """Spawn a bridge-managed child session."""
```

- 使用 `asyncio.subprocess` 启动
- 设置独立工作目录（`cwd`）
- 捕获 stdout/stderr

### 终止策略

1. 首先调用 `process.terminate()`
2. 等待最多 3 秒
3. 若超时，调用 `process.kill()` 强制终止

## Bridge 类型

`types.py` 定义了 Bridge 配置和消息类型：

```python
@dataclass(frozen=True)
class BridgeConfig:
    dir: str
    machine_name: str
    max_sessions: int = 1
    verbose: bool = False
    session_timeout_ms: int = DEFAULT_SESSION_TIMEOUT_MS  # 24h

@dataclass(frozen=True)
class WorkData:
    type: Literal["session", "healthcheck"]
    id: str

@dataclass(frozen=True)
class WorkSecret:
    version: int
    session_ingress_token: str
    api_base_url: str
```

## 与 TUI 的集成

Bridge Session 通过 `useBackendSession.ts` hook 集成到前端：

```typescript
// frontend/terminal/src/hooks/useBackendSession.ts
export function useBackendSession(config: FrontendConfig, onExit: (code?: number | null) => void) {
    // ...
    const [bridgeSessions, setBridgeSessions] = useState<BridgeSessionSnapshot[]>([]);
    // ...
}
```

后端通过 JSON 行协议（`OHJSON:` 前缀）发送 `BackendEvent`，其中包含 `bridge_sessions` 快照。

## 单例模式

`BridgeSessionManager` 使用模块级单例：

```python
_DEFAULT_MANAGER: BridgeSessionManager | None = None

def get_bridge_manager() -> BridgeSessionManager:
    """Return the singleton bridge manager."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = BridgeSessionManager()
    return _DEFAULT_MANAGER
```

## 扩展指南

### 添加新的会话类型

1. 在 `types.py` 的 `WorkData.type` 中添加新的字面量
2. 在 `session_runner.py` 中处理新的会话类型分支
3. 在 `manager.py` 中更新状态追踪逻辑

### 添加输出后端

当前 stdout 被写入文件。要添加其他后端（如 syslog、云存储），修改 `manager.py` 中的 `_copy_output()` 方法。

## 关键文件

| 文件 | 职责 |
|------|------|
| `manager.py` | 会话生命周期管理、输出捕获、单例 |
| `session_runner.py` | 进程启动、优雅终止 |
| `types.py` | Bridge 配置、工作数据、Work Secret |
| `work_secret.py` | Work Secret 编解码（如果需要） |
