# 任务系统

本文档介绍 OpenHarness 的后台任务管理系统。

## 概述

任务系统管理 Agent 的后台执行任务，包括 Shell 命令任务和本地 Agent 任务。

## 架构概览

```
src/openharness/tasks/
├── __init__.py          # 包初始化
├── manager.py           # 任务管理器
├── types.py             # 类型定义
├── local_shell_task.py  # Shell 任务
└── local_agent_task.py  # Agent 任务
```

## 核心概念

### TaskRecord

任务记录：

```python
@dataclass
class TaskRecord:
    id: str                      # 任务 ID (如 "a1b2c3d4")
    type: TaskType               # 任务类型
    status: TaskStatus           # 状态: running, completed, failed, killed
    description: str             # 描述
    cwd: str                     # 工作目录
    output_file: Path            # 输出文件路径
    command: str | None = None   # Shell 命令
    prompt: str | None = None    # Agent 提示
    created_at: float            # 创建时间
    started_at: float | None     # 开始时间
    ended_at: float | None       # 结束时间
    return_code: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### TaskType

```python
class TaskType(str, Enum):
    LOCAL_BASH = "local_bash"        # 本地 Shell 命令
    LOCAL_AGENT = "local_agent"      # 本地 Agent
    REMOTE_AGENT = "remote_agent"    # 远程 Agent
    IN_PROCESS_TEAMMATE = "in_process_teammate"  # 进程内队友
```

### TaskStatus

```python
class TaskStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
```

## 任务管理器 (BackgroundTaskManager)

### 创建 Shell 任务

```python
async def create_shell_task(
    self,
    *,
    command: str,
    description: str,
    cwd: str | Path,
    task_type: TaskType = "local_bash",
) -> TaskRecord:
    task_id = _task_id(task_type)
    output_path = get_tasks_dir() / f"{task_id}.log"

    record = TaskRecord(
        id=task_id,
        type=task_type,
        status="running",
        description=description,
        cwd=str(Path(cwd).resolve()),
        output_file=output_path,
        command=command,
        created_at=time.time(),
        started_at=time.time(),
    )

    output_path.write_text("", encoding="utf-8")
    self._tasks[task_id] = record
    self._output_locks[task_id] = asyncio.Lock()
    self._input_locks[task_id] = asyncio.Lock()

    await self._start_process(task_id)
    return record
```

### 创建 Agent 任务

```python
async def create_agent_task(
    self,
    *,
    prompt: str,
    description: str,
    cwd: str | Path,
    task_type: TaskType = "local_agent",
    model: str | None = None,
    api_key: str | None = None,
    command: str | None = None,
) -> TaskRecord:
    if command is None:
        effective_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        cmd = ["python", "-m", "openharness", "--api-key", effective_api_key]
        if model:
            cmd.extend(["--model", model])
        command = " ".join(shlex.quote(part) for part in cmd)

    record = await self.create_shell_task(
        command=command,
        description=description,
        cwd=cwd,
        task_type=task_type,
    )
    updated = replace(record, prompt=prompt)
    self._tasks[record.id] = updated
    await self.write_to_task(record.id, prompt)
    return updated
```

### 任务操作

| 方法 | 说明 |
|------|------|
| `get_task(task_id)` | 获取任务记录 |
| `list_tasks(status)` | 列出任务（可选状态过滤） |
| `update_task(task_id, ...)` | 更新任务元数据 |
| `stop_task(task_id)` | 停止任务 |
| `write_to_task(task_id, data)` | 向任务 stdin 写入数据 |
| `read_task_output(task_id)` | 读取任务输出 |

## 任务生命周期

```
创建 → 运行中 → 完成/失败/被杀死
         ↓
    stdin 可输入
         ↓
    输出重定向到文件
```

### 任务监控

```python
async def _watch_process(
    self,
    task_id: str,
    process: asyncio.subprocess.Process,
    generation: int,
) -> None:
    reader = asyncio.create_task(self._copy_output(task_id, process))
    return_code = await process.wait()
    await reader

    # 检查 generation 是否过期
    current_generation = self._generations.get(task_id)
    if current_generation != generation:
        return

    task = self._tasks[task_id]
    task.return_code = return_code
    if task.status != "killed":
        task.status = "completed" if return_code == 0 else "failed"
    task.ended_at = time.time()
```

## 输出管理

### 输出文件

每个任务的输出写入独立的日志文件：

```python
output_path = get_tasks_dir() / f"{task_id}.log"
```

### 异步输出复制

```python
async def _copy_output(
    self,
    task_id: str,
    process: asyncio.subprocess.Process,
) -> None:
    if process.stdout is None:
        return

    while True:
        chunk = await process.stdout.read(4096)
        if not chunk:
            return

        async with self._output_locks[task_id]:
            with self._tasks[task_id].output_file.open("ab") as handle:
                handle.write(chunk)
```

### 读取输出

```python
def read_task_output(self, task_id: str, *, max_bytes: int = 12000) -> str:
    task = self._require_task(task_id)
    content = task.output_file.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_bytes:
        return content[-max_bytes:]
    return content
```

## 任务输入

### 向任务写入数据

```python
async def write_to_task(self, task_id: str, data: str) -> None:
    task = self._require_task(task_id)
    async with self._input_locks[task_id]:
        process = await self._ensure_writable_process(task)
        process.stdin.write((data.rstrip("\n") + "\n").encode("utf-8"))
        try:
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            # Agent 可能已退出，重启
            process = await self._restart_agent_task(task)
            process.stdin.write((data.rstrip("\n") + "\n").encode("utf-8"))
            await process.stdin.drain()
```

## 任务停止

```python
async def stop_task(self, task_id: str) -> TaskRecord:
    task = self._require_task(task_id)
    process = self._processes.get(task_id)

    if process is None:
        if task.status in {"completed", "failed", "killed"}:
            return task
        raise ValueError(f"Task {task_id} is not running")

    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=3)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()

    task.status = "killed"
    task.ended_at = time.time()
    return task
```

## 单例模式

```python
_DEFAULT_MANAGER: BackgroundTaskManager | None = None
_DEFAULT_MANAGER_KEY: str | None = None


def get_task_manager() -> BackgroundTaskManager:
    """返回单例任务管理器"""
    global _DEFAULT_MANAGER, _DEFAULT_MANAGER_KEY
    current_key = str(get_tasks_dir().resolve())

    if _DEFAULT_MANAGER is None or _DEFAULT_MANAGER_KEY != current_key:
        _DEFAULT_MANAGER = BackgroundTaskManager()
        _DEFAULT_MANAGER_KEY = current_key

    return _DEFAULT_MANAGER
```

## 任务 ID 格式

```python
def _task_id(task_type: TaskType) -> str:
    prefixes = {
        "local_bash": "b",
        "local_agent": "a",
        "remote_agent": "r",
        "in_process_teammate": "t",
    }
    return f"{prefixes[task_type]}{uuid4().hex[:8]}"
```

- `b` - Bash 任务
- `a` - Agent 任务
- `r` - 远程 Agent
- `t` - 进程内队友

## 任务工具

Agent 可以通过工具管理任务：

| 工具 | 说明 |
|------|------|
| `task_create` | 创建后台任务 |
| `task_get` | 获取任务详情 |
| `task_list` | 列出所有任务 |
| `task_update` | 更新任务状态 |
| `task_stop` | 停止任务 |
| `task_output` | 获取任务输出 |

## 与其他模块的关系

- **QueryEngine**: 通过工具调用任务管理
- **Coordinator**: Agent 协作使用任务系统
- **Tools**: 任务工具注册到 ToolRegistry
