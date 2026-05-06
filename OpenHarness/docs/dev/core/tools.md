# 工具系统 (Tools System)

## 概述

OpenHarness 内置 43+ 工具，覆盖文件 I/O、Shell 命令、代码搜索、Web 访问、MCP 集成等核心能力。每个工具都通过 Pydantic 模型进行输入验证，并与权限系统和 Hook 系统深度集成。

## 核心抽象 (`tools/base.py`)

### BaseTool

所有工具的基类：

```python
class BaseTool(ABC):
    name: str                          # 工具唯一名称
    description: str                   # 工具描述（供模型理解）
    input_model: type[BaseModel]      # Pydantic 输入模型

    @abstractmethod
    async def execute(
        self,
        arguments: BaseModel,
        context: ToolExecutionContext
    ) -> ToolResult:
        """执行工具逻辑"""

    def is_read_only(self, arguments: BaseModel) -> bool:
        """判断是否为只读操作"""
        return False

    def to_api_schema(self) -> dict[str, Any]:
        """返回 Anthropic Messages API 格式的工具 schema"""
```

### ToolExecutionContext

工具执行时的共享上下文：

```python
@dataclass
class ToolExecutionContext:
    cwd: Path                          # 当前工作目录
    metadata: dict[str, Any]          # 额外元数据
```

### ToolResult

工具执行结果：

```python
@dataclass(frozen=True)
class ToolResult:
    output: str                        # 执行输出
    is_error: bool = False            # 是否为错误
    metadata: dict[str, Any] = field(default_factory=dict)
```

### ToolRegistry

工具注册中心：

```python
class ToolRegistry:
    def register(self, tool: BaseTool) -> None:
        """注册工具"""

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具"""

    def list_tools(self) -> list[BaseTool]:
        """列出所有工具"""

    def to_api_schema(self) -> list[dict[str, Any]]:
        """生成 API 格式的工具列表"""
```

## 内置工具一览

### 文件操作类

| 工具名 | 功能 | 只读 |
|--------|------|------|
| `BashTool` | 执行 Shell 命令 | ✗ |
| `FileReadTool` | 读取文件内容 | ✓ |
| `FileWriteTool` | 写入文件内容 | ✗ |
| `FileEditTool` | 编辑文件（替换） | ✗ |
| `NotebookEditTool` | 编辑 Jupyter 单元格 | ✗ |
| `GlobTool` | 文件模式匹配 | ✓ |
| `GrepTool` | 正则搜索文件内容 | ✓ |
| `LspTool` | LSP 代码操作 | ✓ |

### 搜索类

| 工具名 | 功能 |
|--------|------|
| `WebFetchTool` | 获取网页内容 |
| `WebSearchTool` | Web 搜索 |
| `ToolSearchTool` | 搜索可用工具 |

### Agent/团队类

| 工具名 | 功能 |
|--------|------|
| `AgentTool` | 派生子 Agent |
| `SendMessageTool` | 向 Agent 发送消息 |
| `TeamCreateTool` | 创建团队 |
| `TeamDeleteTool` | 删除团队 |

### 任务类

| 工具名 | 功能 |
|--------|------|
| `TaskCreateTool` | 创建后台任务 |
| `TaskGetTool` | 获取任务详情 |
| `TaskListTool` | 列出任务 |
| `TaskUpdateTool` | 更新任务 |
| `TaskStopTool` | 停止任务 |
| `TaskOutputTool` | 读取任务输出 |

### 模式切换类

| 工具名 | 功能 |
|--------|------|
| `EnterPlanModeTool` | 进入计划模式 |
| `ExitPlanModeTool` | 退出计划模式 |
| `EnterWorktreeTool` | 创建 Git Worktree |
| `ExitWorktreeTool` | 退出 Worktree |

### 定时任务类

| 工具名 | 功能 |
|--------|------|
| `CronCreateTool` | 创建定时任务 |
| `CronListTool` | 列出定时任务 |
| `CronDeleteTool` | 删除定时任务 |
| `CronToggleTool` | 切换定时任务状态 |
| `RemoteTriggerTool` | 远程触发 |

### 知识类

| 工具名 | 功能 |
|--------|------|
| `SkillTool` | 加载 Markdown 技能 |
| `ConfigTool` | 配置管理 |
| `BriefTool` | 总结对话 |
| `AskUserQuestionTool` | 向用户提问 |

### MCP 类

| 工具名 | 功能 |
|--------|------|
| `McpToolAdapter` | 适配 MCP 工具 |
| `McpAuthTool` | MCP 认证 |
| `ListMcpResourcesTool` | 列出 MCP 资源 |
| `ReadMcpResourceTool` | 读取 MCP 资源 |

### 其他

| 工具名 | 功能 |
|--------|------|
| `SleepTool` | 延时等待 |
| `TodoWriteTool` | 写入 Todo 列表 |

## 工具注册流程

默认工具注册表由 `create_default_tool_registry()` 创建：

```python
def create_default_tool_registry(mcp_manager=None) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (
        BashTool(),
        FileReadTool(),
        FileWriteTool(),
        # ... 40+ more
    ):
        registry.register(tool)

    # 如果有 MCP 管理器，注册 MCP 工具
    if mcp_manager is not None:
        registry.register(ListMcpResourcesTool(mcp_manager))
        registry.register(ReadMcpResourceTool(mcp_manager))
        for tool_info in mcp_manager.list_tools():
            registry.register(McpToolAdapter(mcp_manager, tool_info))

    return registry
```

## 权限检查集成

工具执行前会调用 `PermissionChecker.evaluate()`：

```python
decision = context.permission_checker.evaluate(
    tool_name,
    is_read_only=tool.is_read_only(parsed_input),
    file_path=_file_path,
    command=_command,
)
```

**权限检查流程：**
1. 敏感路径保护（内置、不可覆盖）
2. 显式工具拒绝列表
3. 显式工具允许列表
4. 路径级规则匹配
5. 命令模式匹配
6. 权限模式评估（default/plan/full_auto）

## Hook 集成

每个工具执行都支持 PreToolUse 和 PostToolUse Hook：

```python
# Pre-Hook
pre_hooks = await context.hook_executor.execute(
    HookEvent.PRE_TOOL_USE,
    {"tool_name": tool_name, "tool_input": tool_input}
)
if pre_hooks.blocked:
    return ToolResultBlock(..., is_error=True)

# 工具执行...

# Post-Hook
await context.hook_executor.execute(
    HookEvent.POST_TOOL_USE,
    {"tool_name": tool_name, "tool_input": tool_input, "tool_output": result.content}
)
```

## 自定义工具开发

### 基本结构

```python
from pydantic import BaseModel, Field
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult

class MyToolInput(BaseModel):
    query: str = Field(description="搜索查询")
    limit: int = Field(default=10, description="结果数量限制")

class MyTool(BaseTool):
    name = "my_tool"
    description = "执行自定义搜索"
    input_model = MyToolInput

    async def execute(
        self,
        arguments: MyToolInput,
        context: ToolExecutionContext
    ) -> ToolResult:
        # 实现逻辑
        result = await do_search(arguments.query, arguments.limit)
        return ToolResult(output=result)

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True  # 或根据参数动态判断
```

### 注册自定义工具

```python
from openharness.tools import create_default_tool_registry

# 创建默认注册表
registry = create_default_tool_registry()

# 注册自定义工具
registry.register(MyTool())
```

### 生成 API Schema

```python
schema = my_tool.to_api_schema()
# 返回:
# {
#     "name": "my_tool",
#     "description": "执行自定义搜索",
#     "input_schema": {...}  # Pydantic model JSON schema
# }
```

## 工具输入规范化

Query 引擎在权限检查前会规范化工具输入中的路径：

```python
def _resolve_permission_file_path(
    cwd: Path,
    raw_input: dict[str, object],
    parsed_input: object,
) -> str | None:
    # 优先检查 file_path，然后是 path
    for key in ("file_path", "path"):
        value = raw_input.get(key)
        if isinstance(value, str) and value.strip():
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = cwd / path
            return str(path.resolve())
    return None
```

## 扩展点

### 1. 添加新类别工具

在 `tools/` 目录下创建新工具文件，并在 `tools/__init__.py` 中注册。

### 2. MCP 工具适配

MCP 服务器暴露的工具通过 `McpToolAdapter` 自动适配：

```python
class McpToolAdapter(BaseTool):
    """将 MCP 工具适配为 OpenHarness 工具"""

    def __init__(self, mcp_manager: McpClientManager, tool_info: McpToolInfo):
        self._manager = mcp_manager
        self._tool_info = tool_info
        self.name = f"mcp_{tool_info.server_name}_{tool_info.name}"
        self.description = tool_info.description

    async def execute(self, arguments, context):
        result = await self._manager.call_tool(
            self._tool_info.server_name,
            self._tool_info.name,
            arguments.model_dump()
        )
        return ToolResult(output=result)
```

### 3. 动态工具注册

可根据配置或插件动态注册/注销工具：

```python
registry = ToolRegistry()
# 根据条件注册
if settings.enable_experimental:
    registry.register(ExperimentalTool())
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `tools/base.py` | BaseTool 抽象基类和 ToolRegistry |
| `tools/__init__.py` | 默认工具注册表创建 |
| `tools/bash_tool.py` | Bash 工具实现 |
| `tools/file_read_tool.py` | 文件读取工具 |
| `tools/file_write_tool.py` | 文件写入工具 |
| `tools/mcp_tool.py` | MCP 工具适配器 |
| `tools/agent_tool.py` | Agent 派生工具 |
