# 任务管理

## 概述

OpenHarness 提供任务管理系统，支持在后台运行 Shell 命令和 Agent 子进程，方便管理长时间运行的任务。

## 任务类型

### 1. Shell 任务 (`local_bash`)

在后台执行 Shell 命令。

### 2. Agent 任务 (`local_agent`)

启动一个完整的 Agent 子进程来执行任务。

### 3. 远程任务 (`remote_agent`)

连接到远程 Agent 服务。

### 4. 进程内任务 (`in_process_teammate`)

在当前进程内运行子 Agent（用于多 Agent 协作）。

## 任务目录

任务日志和元数据存储在：

```
~/.openharness/tasks/
```

每个任务生成：
- `{task_id}.log` - 任务输出日志

## 使用任务

### 在 TUI 中管理任务

```
/tasks           # 查看任务列表
/task start      # 启动新任务
/task stop <id>  # 停止任务
/task logs <id>  # 查看任务日志
```

### 命令行创建任务

```bash
# 在 Python 代码中
from openharness.tasks.manager import get_task_manager

manager = get_task_manager()

# 创建 Shell 任务
task = await manager.create_shell_task(
    command="python train.py --epochs 100",
    description="训练模型",
    cwd="/path/to/project"
)

# 创建 Agent 任务
agent_task = await manager.create_agent_task(
    prompt="分析这个项目的代码结构",
    description="代码分析",
    cwd="/path/to/project"
)
```

## 任务生命周期

1. **创建** - 任务被创建，状态为 `running`
2. **运行** - 任务正在执行
3. **完成** - 任务成功结束（return_code = 0）
4. **失败** - 任务异常结束（return_code != 0）
5. **终止** - 任务被手动停止

## 查看任务状态

### 列出所有任务

```python
manager = get_task_manager()
tasks = manager.list_tasks()

for task in tasks:
    print(f"{task.id}: {task.status} - {task.description}")
```

### 查看单个任务

```python
task = manager.get_task(task_id)
print(f"状态: {task.status}")
print(f"描述: {task.description}")
print(f"工作目录: {task.cwd}")
print(f"命令: {task.command}")
```

### 读取任务输出

```python
output = manager.read_task_output(task_id)
print(output)
```

## 任务控制

### 停止任务

```python
task = await manager.stop_task(task_id)
print(f"任务已停止: {task.status}")
```

### 向任务发送输入

```python
await manager.write_to_task(task_id, "input data\n")
```

### 重启 Agent 任务

Agent 任务支持自动重启，当 stdin 断开时会重新启动。

## 任务记录结构

```python
@dataclass
class TaskRecord:
    id: str                    # 任务 ID (格式: {type_prefix}{uuid})
    type: TaskType             # 任务类型
    status: str                # running/completed/failed/killed
    description: str           # 任务描述
    cwd: str                   # 工作目录
    command: str | None        # 要执行的命令
    output_file: Path          # 输出日志文件
    created_at: float          # 创建时间戳
    started_at: float | None   # 开始时间戳
    ended_at: float | None     # 结束时间戳
    return_code: int | None    # 进程返回码
    prompt: str | None         # Agent 任务的提示词
    metadata: dict             # 额外元数据
```

## Cron 调度集成

任务可以与 Cron 调度系统配合使用，详见 [CLI 参考](./cli-reference.md#cron-调度)。

### 配置定时任务

```json
{
  "cron_jobs": [
    {
      "name": "daily-report",
      "schedule": "0 9 * * *",
      "command": "python scripts/daily_report.py",
      "enabled": true
    }
  ]
}
```

## 最佳实践

### 1. 任务描述清晰

提供有意义的描述便于识别任务：

```python
await manager.create_shell_task(
    command="python train.py",
    description="训练 ResNet50 模型（100 epochs）",
    cwd="/project"
)
```

### 2. 监控任务输出

定期检查任务日志，确保任务正常运行：

```python
output = manager.read_task_output(task_id, max_bytes=4096)
if "error" in output.lower():
    print("检测到错误！")
```

### 3. 正确处理长时间任务

对于长时间运行的任务：

```python
# 定期检查状态
while task.status == "running":
    await asyncio.sleep(10)
    task = manager.get_task(task_id)
    print(f"进度: {task.metadata.get('progress', 'N/A')}")
```

### 4. 资源清理

任务完成后及时清理：

```python
# 停止任务
if task.status == "running":
    await manager.stop_task(task_id)
```

## 多 Agent 协作

OpenHarness 支持多 Agent 协作，一个 Agent 可以启动子 Agent 任务：

```python
# 主 Agent 创建子 Agent 任务
sub_agent = await manager.create_agent_task(
    prompt="审查这段代码的安全问题",
    description="安全审查",
    cwd="/project",
    task_type="in_process_teammate"
)

# 向子 Agent 发送指令
await manager.write_to_task(sub_agent.id, code_to_review)

# 读取子 Agent 输出
output = manager.read_task_output(sub_agent.id)
```

## 常见问题

### Q: 任务启动失败？

1. 检查命令是否正确
2. 确认工作目录存在
3. 查看错误日志

### Q: Agent 任务自动退出？

Agent 任务可能因为：
- API 密钥无效
- 模型不可用
- 输入/输出问题

查看任务日志获取详细信息。

### Q: 如何查看历史任务？

```python
# 列出所有任务（包括已完成）
tasks = manager.list_tasks()

# 只看运行中的
running = manager.list_tasks(status="running")
```
