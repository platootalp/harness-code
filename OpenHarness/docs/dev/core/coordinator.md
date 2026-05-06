# 多 Agent 协调系统

本文档介绍 OpenHarness 的多 Agent 协调系统，包括 Subagent 委派和团队协作。

## 概述

OpenHarness 支持多 Agent 协作模式：
- **Coordinator 模式**: 一个协调者管理多个 Worker
- **Team 模式**: 多个 Agent 形成团队协作
- **Subagent**: Agent 可以启动子 Agent 完成任务

## 架构概览

```
src/openharness/coordinator/
├── __init__.py                # 包初始化
├── coordinator_mode.py         # 协调者模式
└── agent_definitions.py       # Agent 定义
```

## 协调者模式 (CoordinatorMode)

### 模式检测

```python
def is_coordinator_mode() -> bool:
    """检测是否处于协调者模式"""
    val = os.environ.get("CLAUDE_CODE_COORDINATOR_MODE", "")
    return val.lower() in {"1", "true", "yes"}
```

### 协调者工具

```python
def get_coordinator_tools() -> list[str]:
    """返回协调者专用的工具"""
    return ["agent", "send_message", "task_stop"]
```

### Worker 工具集

```python
_WORKER_TOOLS = [
    "bash",
    "file_read",
    "file_edit",
    "file_write",
    "glob",
    "grep",
    "web_fetch",
    "web_search",
    "task_create",
    "task_get",
    "task_list",
    "task_output",
    "skill",
]

_SIMPLE_WORKER_TOOLS = ["bash", "file_read", "file_edit"]
```

## TeamRegistry

团队注册表管理团队和成员：

```python
class TeamRecord:
    """轻量级内存团队"""
    name: str
    description: str = ""
    agents: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


class TeamRegistry:
    def create_team(self, name: str, description: str = "") -> TeamRecord
    def delete_team(self, name: str) -> None
    def add_agent(self, team_name: str, task_id: str) -> None
    def send_message(self, team_name: str, message: str) -> None
    def list_teams(self) -> list[TeamRecord]
```

## Agent 定义

### AgentDefinition

```python
@dataclass
class AgentDefinition:
    name: str                      # Agent 名称
    description: str                # 描述
    system_prompt: str | None     # 系统提示
    tools: list[str] = []          # 允许的工具
    disallowed_tools: list[str] = []  # 禁止的工具
    model: str | None = None      # 指定模型
    effort: str | int | None = None
    permission_mode: str | None = None
    max_turns: int | None = None
    skills: list[str] = []         # 技能列表
    mcp_servers: list[str] | None = None
    hooks: list[str] | None = None
    color: str | None = None       # UI 颜色
    background: bool = False       # 是否后台运行
    initial_prompt: str | None = None
    memory: str | None = None      # 记忆范围
    isolation: str | None = None   # 隔离模式
    omit_claude_md: bool = False
    critical_system_reminder: str | None = None
    required_mcp_servers: list[str] = []
    permissions: list[str] = []
    filename: str
    base_dir: str
    subagent_type: str
    source: str = "plugin"
```

## Agent 协作工具

### agent 工具

启动子 Agent：

```python
class AgentTool(BaseTool):
    name = "agent"
    description = "Spawn a new agent to handle a task"

    input_model = AgentInput

    async def execute(self, args: AgentInput, ctx: ToolExecutionContext) -> ToolResult:
        # 创建子 Agent 任务
        task = await task_manager.create_agent_task(
            prompt=args.prompt,
            description=args.description,
            cwd=ctx.cwd,
            model=args.model,
        )
        return ToolResult(output=f"Agent started: {task.id}")
```

### send_message 工具

向 Agent 发送消息：

```python
class SendMessageTool(BaseTool):
    name = "send_message"
    description = "Send a message to an existing agent"

    async def execute(self, args: SendMessageInput, ctx: ToolExecutionContext) -> ToolResult:
        await task_manager.write_to_task(args.to, args.message)
        return ToolResult(output=f"Message sent to {args.to}")
```

### task_stop 工具

停止 Agent：

```python
class TaskStopTool(BaseTool):
    name = "task_stop"
    description = "Stop a running agent"

    async def execute(self, args: TaskStopInput, ctx: ToolExecutionContext) -> ToolResult:
        task = await task_manager.stop_task(args.task_id)
        return ToolResult(output=f"Agent stopped: {task.status}")
```

## 协调者系统提示

```python
def get_coordinator_system_prompt() -> str:
    """返回协调者模式的系统提示"""
    return """You are Claude Code, an AI assistant that orchestrates software engineering tasks across multiple workers.

## 1. Your Role

You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user
- Answer questions directly when possible

## 2. Your Tools

- **{agent}** - Spawn a new worker
- **{send_message}** - Continue an existing worker
- **{task_stop}** - Stop a running worker

## 3. Workers

Workers execute tasks autonomously. When calling {agent}:
- Do not use one worker to check on another
- Do not use workers to trivially report file contents
- Continue workers whose work is complete via {send_message}
"""
```

## 任务通知 (TaskNotification)

Worker 完成时发送 XML 格式通知：

```python
@dataclass
class TaskNotification:
    task_id: str
    status: str          # completed, failed, killed
    summary: str         # 人类可读的状态摘要
    result: str | None   # Agent 的最终文本响应
    usage: dict | None  # 使用量统计


def format_task_notification(n: TaskNotification) -> str:
    return f"""<task-notification>
<task-id>{n.task_id}</task-id>
<status>{n.status}</status>
<summary>{n.summary}</summary>
{("<result>" + n.result + "</result>") if n.result else ""}
<usage>
  <total_tokens>{n.usage.get("total_tokens", 0)}</total_tokens>
  <tool_uses>{n.usage.get("tool_uses", 0)}</tool_uses>
  <duration_ms>{n.usage.get("duration_ms", 0)}</duration_ms>
</usage>
</task-notification>"""
```

## 协作流程

### 1. 启动 Worker

```
协调者:
  /agent(description="研究 auth 模块", prompt="调查 src/auth/ 中的问题...")

  <task_id: a1b2c3d4>
```

### 2. Worker 执行

Worker 异步执行任务，完成后发送通知：

```
User:
  <task-notification>
  <task-id>a1b2c3d4</task-id>
  <status>completed</status>
  <summary>Agent "研究 auth 模块" completed</summary>
  <result>发现 null pointer 在 src/auth/validate.ts:42...</result>
  </task-notification>
```

### 3. 继续 Worker

```python
/send_message(to="a1b2c3d4", message="修复 null pointer...")
```

### 4. 停止 Worker

```python
/task_stop(task_id="a1b2c3d4")
```

## Worker 类型

### worker

标准 Worker，执行复杂任务：

```yaml
agent:
  description: "研究任务"
  subagent_type: "worker"
  prompt: "调查 auth 模块..."
```

### simple worker

简化 Worker，只能使用基础工具：

```yaml
agent:
  description: "简单任务"
  subagent_type: "simple"
  tools: ["bash", "file_read", "file_edit"]
```

## 并行执行

协调者可以并行启动多个 Worker：

```python
# 并行研究多个问题
/agent(description="研究 auth bug", prompt="调查 src/auth/...")
/agent(description="研究性能问题", prompt="分析性能瓶颈...")
/agent(description="审查安全问题", prompt="检查安全漏洞...")
```

## 团队创建

```python
team = team_registry.create_team(
    name="auth-refactor",
    description="Auth 模块重构团队"
)
team_registry.add_agent("auth-refactor", "a1b2c3d4")
team_registry.send_message("auth-refactor", "开始重构")
```

## 与其他模块的关系

- **TaskManager**: Agent 作为任务运行
- **QueryEngine**: 协调者通过 QueryEngine 运行
- **Tools**: agent, send_message, task_stop 是内置工具
- **Settings**: Agent 配置可存储在 Settings 中
