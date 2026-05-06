# 任务模块详细设计

## 1. 概述

任务模块是 Agent 的内部能力，用于将复杂目标拆解为可执行的子任务，并管理子任务之间的依赖关系、并行执行、状态跟踪和结果处理。

### 设计目标

- Agent 通过声明式接口创建任务和依赖关系
- 支持 DAG 依赖管理，拓扑排序，并行执行
- 任务完成后通知 Agent 介入决策
- 失败独立，不级联
- 持久化到文件系统

---

## 2. 核心架构

```
Agent
  ├── create_task(TaskDef) × N
  ├── start()
  │     ├── DAGScheduler 调度循环
  │     │     ├── 扫描 pending 任务
  │     │     ├── 找入度=0 的任务
  │     │     ├── 并行启动（max_concurrency）
  │     │     ├── Watcher 线程监控
  │     │     ├── 任务完成 → asyncio.Event → 唤醒调度
  │     │     └── pause() → Agent 介入
  │     └── Agent 处理 → resume()
  └── wait(task_id)

持久化
  └── ~/.openharness/sessions/{session_id}/tasks/
        ├── {task_id}.json    # TaskDef + TaskStatus 合并
        └── results/
            ├── {task_id}.out
            └── {task_id}.err
```

---

## 3. 数据模型

### TaskType

```python
TaskType = Literal["shell", "agent"]
```

### TaskDef（任务定义）

```python
@dataclass
class TaskDef:
    id: str                     # 任务唯一ID（Agent 生成）
    description: str            # 任务描述（Agent 可理解）
    command: str               # shell 命令 或 agent prompt
    task_type: TaskType        # shell / agent
    dependencies: list[str]    # 依赖的 task_id 列表（默认 []）
    result_file: str           # 结果文件路径
    retry: int = 3            # 最大重试次数
    timeout: int = 3600       # 超时秒数
```

### TaskRecord（持久化格式）

TaskDef 和 TaskStatus 合并存储在一个 JSON 文件中：

```python
@dataclass
class TaskRecord:
    # TaskDef 字段
    id: str
    description: str
    command: str
    task_type: TaskType
    dependencies: list[str]
    result_file: str
    retry: int = 3
    timeout: int = 3600

    # TaskStatus 字段
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: float | None = None
    ended_at: float | None = None
    retry_count: int = 0
    return_code: int | None = None
    result_summary: str | None = None
    error: str | None = None
```

### 持久化文件格式

`~/.openharness/sessions/{session_id}/tasks/{task_id}.json`

```json
{
  "id": "b1234567",
  "description": "编译后端服务",
  "command": "cd backend && make build",
  "task_type": "shell",
  "dependencies": ["a1234567"],
  "result_file": "results/b1234567.out",
  "retry": 3,
  "timeout": 3600,
  "status": "completed",
  "started_at": 1744654800.0,
  "ended_at": 1744654820.0,
  "retry_count": 0,
  "return_code": 0,
  "result_summary": "Build succeeded in 20s",
  "error": null
}
```

结果输出文件：
- `~/.openharness/sessions/{session_id}/tasks/results/{task_id}.out` — stdout
- `~/.openharness/sessions/{session_id}/tasks/results/{task_id}.err` — stderr

---

## 4. API 设计

```python
class DAGScheduler:
    def __init__(self, session_id: str, max_concurrency: int = 3):
        """初始化调度器。

        Args:
            session_id: 会话ID，用于持久化路径
            max_concurrency: 最大并发任务数
        """

    async def create_task(self, task_def: TaskDef) -> str:
        """创建任务并持久化。

        Args:
            task_def: 任务定义

        Returns:
            task_id
        """

    async def start(self) -> None:
        """启动调度循环。

        调度流程：
        1. 扫描所有 pending 任务
        2. 找出依赖已满足（入度=0）的任务
        3. 并行启动（不超过 max_concurrency）
        4. Watcher 线程监控任务完成
        5. 任务完成 → asyncio.Event 唤醒调度协程
        6. pause() 等待 Agent 介入
        7. Agent 处理完后 resume() 继续
        """

    def pause(self) -> None:
        """暂停调度，等待 Agent 介入决策。

        Agent 调用此方法后，调度循环阻塞。
        Agent 处理完事件后调用 resume() 继续。
        """

    def resume(self) -> None:
        """继续调度循环。"""

    async def wait(self, task_id: str) -> TaskRecord:
        """等待特定任务完成。

        Args:
            task_id: 任务ID

        Returns:
            任务最终状态
        """

    def get_task(self, task_id: str) -> TaskRecord | None:
        """获取任务记录。"""

    def list_tasks(self) -> list[TaskRecord]:
        """列出所有任务。"""

    def get_result(self, task_id: str) -> str:
        """读取任务结果文件内容。

        Args:
            task_id: 任务ID

        Returns:
            结果文件内容（stdout）
        """
```

---

## 5. DAG 调度算法

### 拓扑排序

```python
def find_ready_tasks(self) -> list[str]:
    """找出所有依赖已满足且状态为 pending 的任务。

    Returns:
        可立即执行的任务ID列表
    """
    ready = []
    for task_id, record in self._tasks.items():
        if record.status != "pending":
            continue
        deps_met = all(
            self._tasks[dep_id].status == "completed"
            for dep_id in record.dependencies
        )
        if deps_met:
            ready.append(task_id)
    return ready
```

### 并行执行

```python
async def _run_ready_tasks(self, ready: list[str]) -> None:
    """并行启动就绪的任务。"""
    sem = asyncio.Semaphore(self._max_concurrency)

    async def run_one(task_id: str):
        async with sem:
            await self._execute_task(task_id)

    await asyncio.gather(*[run_one(t) for t in ready])
```

### 失败处理

- 单个任务失败不影响其他独立分支
- 失败任务状态更新为 "failed"，不自动重试（重试由 Agent 决定）
- Agent 介入时可选择重试、增加依赖、取消任务等

### 任务完成流程

```python
async def _execute_task(self, task_id: str) -> None:
    record = self._tasks[task_id]
    record.status = "running"
    record.started_at = time.time()
    self._persist(task_id)

    if record.task_type == "shell":
        proc = await asyncio.create_subprocess_shell(
            record.command,
            stdout=open(record.result_file.with_suffix('.out'), 'w'),
            stderr=open(record.result_file.with_suffix('.err'), 'w'),
        )
        return_code = await proc.wait()
    else:
        # agent 类型：启动子 Agent 进程
        ...

    record.return_code = return_code
    record.status = "completed" if return_code == 0 else "failed"
    record.ended_at = time.time()
    self._persist(task_id)

    # 通知 Watcher → 设置 Event → 唤醒调度协程
    self._task_done_event.set()
```

---

## 6. Watcher 线程

Watcher 是一个后台线程，监控所有运行中任务的标准输出/错误输出，并将完成的任务通知给 DAGScheduler。

```python
class TaskWatcher:
    def __init__(self, scheduler: DAGScheduler):
        self._scheduler = scheduler
        self._running = True

    def watch(self, task_id: str, proc: asyncio.subprocess.Process):
        """启动监控一个任务进程。"""
        ...

    def stop(self):
        self._running = False

    def _on_task_done(self, task_id: str):
        """任务完成时调用，设置 Event 唤醒调度器。"""
        self._scheduler._task_done_event.set()
```

---

## 7. Agent 介入机制

### 回调流程

```
Agent                    DAGScheduler
  │                            │
  ├── create_task() × N       │
  ├── start() ────────────────→ 调度循环启动
  │                            │ 扫描/启动任务
  │                            │ 任务完成
  │                            │ pause() ← 阻塞
  │←─ wait() 返回 ─────────────┤
  │                            │
  ├── 处理事件                  │
  │   - 读取结果 get_result()   │
  │   - 决策：重试/新增任务      │
  │   - 增加依赖 create_task()  │
  │                            │
  ├── resume() ────────────────→ 继续调度
  │                            │
```

### Agent 典型使用模式

```python
scheduler = DAGScheduler(session_id="sess_001")

# 创建任务
await scheduler.create_task(TaskDef(
    id="build",
    description="编译后端",
    command="make build",
    task_type="shell",
    dependencies=[],
))

await scheduler.create_task(TaskDef(
    id="test",
    description="运行测试",
    command="make test",
    task_type="shell",
    dependencies=["build"],
))

# 启动调度
await scheduler.start()

# wait() 会返回（pause 时）
status = await scheduler.wait("test")
print(f"任务完成: {status}")
```

---

## 8. 持久化

### 目录结构

```
~/.openharness/sessions/{session_id}/tasks/
  ├── {task_id}.json       # TaskRecord（定义+状态合并）
  └── results/
      ├── {task_id}.out    # 标准输出
      └── {task_id}.err    # 标准错误
```

### 重建 DAG

启动时扫描任务目录，重建内存中的 DAG：

```python
def _rebuild_dag(self) -> None:
    task_dir = self._tasks_dir
    for json_file in task_dir.glob("*.json"):
        record = TaskRecord.from_json(json_file.read_text())
        self._tasks[record.id] = record
        # 从 dependencies 构建入度统计
```

---

## 9. 状态机

```
pending ──→ running ──→ completed
              │
              └──→ failed

任何状态可被 Agent 手动 kill → killed
```

---

## 10. 与现有 BackgroundTaskManager 的关系

现有 `BackgroundTaskManager` 提供单任务的后台执行能力（shell 进程管理）。

新的 `DAGScheduler` 建立在 BackgroundTaskManager 之上：
- DAGScheduler 调用 BackgroundTaskManager 执行具体任务
- DAGScheduler 管理任务依赖、调度、状态聚合
- BackgroundTaskManager 仍是进程管理的底层

---

## 11. 实现顺序

1. **Task 数据模型** — 定义 TaskRecord，持久化读写
2. **DAGScheduler 核心** — create_task、find_ready_tasks、状态机
3. **执行引擎** — 调用 BackgroundTaskManager，捕获结果
4. **Watcher 线程** — 监控任务完成，asyncio.Event 通知
5. **Agent 介入** — pause/resume 机制
6. **持久化恢复** — 启动时从文件重建 DAG
