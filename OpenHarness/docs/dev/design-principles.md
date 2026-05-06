# 设计原则

本文档介绍 OpenHarness 的核心设计原则和理念。

## 核心理念

**"模型是 Agent，代码是 Harness"**

OpenHarness 相信：LLM 本身已经具备智能，Harness 的职责是给它提供：
- **手**（工具执行）
- **眼**（文件系统、Web 访问）
- **记忆**（跨会话上下文）
- **边界**（权限和安全）

## 设计原则

### 1. 简洁优先 (Simplicity First)

**原则**: 最小化复杂度，用最少的代码解决问题。

**实践**:
- 避免过度工程
- 三个相似代码行优于一个过早抽象
- 不为假设的未来需求添加代码
- 只在必要时创建新文件

**反面**:
```python
# 过度抽象
class BaseToolWithPermissionsAndHooks(BaseTool):
    def __init__(self):
        self.hook_executor = HookExecutor()
        self.permission_checker = PermissionChecker()
        ...

# 简洁直接
result = await tool.execute(args, context)
```

### 2. 模型中心 (Model-Centric)

**原则**: 模型是唯一的 Agent，Harness 是辅助。

**实践**:
- QueryEngine 不做决策，只执行
- 工具返回结构化结果，让模型决定
- 避免硬编码业务逻辑
- 提示词驱动行为

**示例**:
```
QueryEngine: 执行工具 → 返回结果 → 模型决定下一步
而非: QueryEngine: if tool == "X" then do Y
```

### 3. 工具即接口 (Tools as Interface)

**原则**: 工具是模型与系统交互的唯一方式。

**实践**:
- 所有操作都通过工具暴露
- 工具 schema 驱动模型理解
- Pydantic 模型验证确保安全
- 权限检查在工具层执行

**好处**:
- 模型行为可预测
- 安全边界清晰
- 易于审计和追踪

### 4. 扩展优于修改 (Extension Over Modification)

**原则**: 通过扩展点添加功能，而非修改核心代码。

**实践**:
- 插件系统支持命令、钩子、代理、MCP
- 技能是 Markdown 文件，无需代码
- 工具注册而非继承
- 配置驱动行为

**示例**:
```python
# 通过注册扩展，而非修改
registry.register(MyCustomTool())

# 通过配置扩展
settings.enabled_plugins["my-plugin"] = True
```

### 5. 安全内置 (Security by Design)

**原则**: 安全不是事后添加，而是内置。

**实践**:
- 敏感路径硬编码保护
- 多层权限检查
- PreToolUse/PostToolUse 钩子
- 只读工具自动识别

**层次**:
```
1. 内置保护（不可覆盖）: SSH 密钥、AWS 凭证等
2. 配置保护: 路径规则、命令规则
3. 模式保护: Plan 模式、Full Auto 模式
4. 用户确认: Default 模式下的交互
```

### 6. 异步优先 (Async-First)

**原则**: 充分利用 Python 异步能力。

**实践**:
- 所有 I/O 操作异步
- 并行工具执行
- 非阻塞流式响应
- asyncio.gather 替代串行

**示例**:
```python
# 并行执行多个工具
results = await asyncio.gather(*[execute(tc) for tc in tool_calls])
```

### 7. 协议兼容 (Protocol Compatibility)

**原则**: 遵循已有协议，而非发明新协议。

**实践**:
- 兼容 Claude Code 工具 schema
- 兼容 Anthropic Messages API
- 兼容 OpenAI Chat Completions API
- 兼容 MCP 协议

**好处**:
- 社区技能和插件可直接使用
- 降低学习成本
- 生态互操作

### 8. 配置分层 (Layered Configuration)

**原则**: 配置来源分层，优先级清晰。

**层次** (高优先级覆盖低优先级):
```
CLI 参数 > 环境变量 > 配置文件 > 默认值
```

**实践**:
- 环境变量易于容器化
- 配置文件易于同步
- CLI 易于调试
- 默认值确保可用性

### 9. 可观测性 (Observability)

**原则**: 所有操作可追踪、可调试。

**实践**:
- 流式事件传递中间状态
- HookExecutor 支持审计
- 工具执行日志
- Token 使用量追踪

**事件流**:
```
AssistantTextDelta → ToolExecutionStarted → ToolExecutionCompleted → ...
```

### 10. 渐进复杂性 (Progressive Complexity)

**原则**: 从简单开始，按需增加复杂度。

**实践**:
- 默认配置开箱即用
- 单文件工具实现
- 简单模式逐步解锁
- 高级功能显式启用

**示例**:
```
simple worker: 3 个工具
standard worker: 14 个工具
coordinator mode: 完整多 Agent
```

## 架构决策记录

### AD-001: 使用 Pydantic 进行验证

**决策**: 工具输入使用 Pydantic 模型验证。

**理由**:
- 类型安全
- JSON Schema 自动生成
- 验证逻辑内聚
- 错误信息清晰

### AD-002: 异步流式架构

**决策**: 所有 API 调用和工具执行使用异步流式。

**理由**:
- 实时反馈用户体验
- 高效利用连接
- 易于实现重试
- 中间状态可观测

### AD-003: Markdown 技能格式

**决策**: 技能使用 Markdown 文件格式。

**理由**:
- 人类可读
- 版本控制友好
- 无需代码修改
- 社区可直接贡献

### AD-004: 插件命名空间

**决策**: 插件命令使用 `plugin-name:command` 命名空间。

**理由**:
- 避免命名冲突
- 来源清晰
- 易于发现
- 与 Claude Code 一致

### AD-005: 单例任务管理器

**决策**: BackgroundTaskManager 使用单例模式。

**理由**:
- 进程内任务共享状态
- 简化跨组件协调
- 避免传递管理器实例
- 与进程生命周期一致

## 反模式

### 避免: 工具做决策

```python
# 反模式
class BashTool(BaseTool):
    async def execute(self, args, ctx):
        if "rm" in args.command:
            if not confirm("Delete?"):
                return ToolResult(output="Cancelled")
        # 执行...

# 正确: 权限系统处理
decision = permission_checker.evaluate("bash", command=args.command)
if not decision.allowed:
    return ToolResult(output="Permission denied")
```

### 避免: 过早抽象

```python
# 反模式
class BaseToolWithLogging(BaseTool):
    def log_start(self): ...
    def log_end(self): ...
    def log_error(self): ...

class MyTool(BaseToolWithLogging):
    ...

# 正确: 按需添加
class MyTool(BaseTool):
    async def execute(self, args, ctx):
        result = await do_work()
        ctx.metadata.get("logger", lambda x: None)(result)
        return result
```

### 避免: 硬编码工具列表

```python
# 反模式
if tool_name in ["bash", "read", "write", "edit", ...]:
    require_permission(tool_name)

# 正确: 基于属性
if not tool.is_read_only(args):
    require_permission(tool_name)
```

## 最佳实践

### 1. 工具开发

```python
# 1. 明确输入模型
class MyToolInput(BaseModel):
    required_arg: str
    optional_arg: str | None = None

# 2. 描述清晰
class MyTool(BaseTool):
    name = "my_tool"
    description = "Does X. Use when Y."

# 3. 正确标识只读
def is_read_only(self, args) -> bool:
    return True  # 或 False

# 4. 错误处理
async def execute(self, args, ctx) -> ToolResult:
    try:
        return ToolResult(output=do_work())
    except Exception as e:
        return ToolResult(output=str(e), is_error=True)
```

### 2. 插件开发

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What it does",
  "enabled_by_default": true
}
```

### 3. 技能编写

```markdown
---
name: my-skill
description: Brief description
---

# My Skill

## When to use
...

## Workflow
1. ...
2. ...
```

## 总结

OpenHarness 的设计原则强调：
- **简洁**: 用最少的代码解决问题
- **模型中心**: 模型是 Agent，Harness 是辅助
- **安全内置**: 安全是核心，不是附加
- **协议兼容**: 遵循已有标准
- **扩展优于修改**: 通过扩展点添加功能

这些原则确保 OpenHarness 保持：
- 可维护性
- 可扩展性
- 安全性
- 互操作性
