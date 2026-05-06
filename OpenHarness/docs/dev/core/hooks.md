# 生命周期钩子 (Hooks System)

## 概述

OpenHarness Hook 系统提供生命周期事件拦截能力，允许在工具执行前后、执行命令前后等关键节点运行自定义逻辑。Hook 可用于安全审计、自动化验证、日志记录等场景。

## 核心架构

```
┌──────────────────────────────────────────────────────┐
│                    HookRegistry                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ HookEvent.PRE_TOOL_USE ──► [Hook, Hook, ...] │   │
│  │ HookEvent.POST_TOOL_USE ──► [Hook, ...]     │   │
│  │ HookEvent.SESSION_START ──► [...]             │   │
│  │ HookEvent.SESSION_END ──► [...]              │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │     HookExecutor        │
              │  execute(event, payload)│
              └───────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Command  │   │   HTTP   │   │  Prompt  │
   │  Hook    │   │   Hook   │   │   Hook   │
   └──────────┘   └──────────┘   └──────────┘
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ subprocess│   │ httpx   │   │ API Call │
   └──────────┘   └──────────┘   └──────────┘
```

## HookEvent 事件类型

```python
class HookEvent(str, Enum):
    """支持的 Hook 事件"""
    SESSION_START = "session_start"      # 会话开始时
    SESSION_END = "session_end"          # 会话结束时
    PRE_TOOL_USE = "pre_tool_use"        # 工具执行前
    POST_TOOL_USE = "post_tool_use"       # 工具执行后
```

## Hook 类型定义

### CommandHookDefinition

执行 shell 命令的 Hook：

```python
class CommandHookDefinition(BaseModel):
    type: Literal["command"] = "command"
    command: str                          # shell 命令模板
    timeout_seconds: int = 30             # 超时时间
    matcher: str | None = None           # fnmatch 模式过滤
    block_on_failure: bool = False        # 失败时是否阻塞
```

### HttpHookDefinition

发送 HTTP POST 请求的 Hook：

```python
class HttpHookDefinition(BaseModel):
    type: Literal["http"] = "http"
    url: str                              # 目标 URL
    headers: dict[str, str] = {}         # 请求头
    timeout_seconds: int = 30
    matcher: str | None = None
    block_on_failure: bool = False
```

### PromptHookDefinition

使用模型验证条件的 Hook：

```python
class PromptHookDefinition(BaseModel):
    type: Literal["prompt"] = "prompt"
    prompt: str                           # 验证提示模板
    model: str | None = None             # 模型覆盖
    timeout_seconds: int = 30
    matcher: str | None = None
    block_on_failure: bool = True         # 默认阻塞
```

### AgentHookDefinition

使用 Agent 进行深度验证的 Hook：

```python
class AgentHookDefinition(BaseModel):
    type: Literal["agent"] = "agent"
    prompt: str                           # Agent 提示模板
    model: str | None = None
    timeout_seconds: int = 60
    matcher: str | None = None
    block_on_failure: bool = True
```

## HookRegistry

```python
class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[HookDefinition]] = defaultdict(list)

    def register(self, event: HookEvent, hook: HookDefinition) -> None:
        self._hooks[event].append(hook)

    def get(self, event: HookEvent) -> list[HookDefinition]:
        return list(self._hooks.get(event, []))
```

## HookExecutor

```python
class HookExecutor:
    def __init__(self, registry: HookRegistry, context: HookExecutionContext) -> None:
        self._registry = registry
        self._context = context

    async def execute(self, event: HookEvent, payload: dict[str, Any]) -> AggregatedHookResult:
        """执行所有匹配的 Hook"""
```

## Hook 执行流程

### PreToolUse Hook 示例

```python
# payload = {
#     "tool_name": "file_write",
#     "tool_input": {"path": "test.py", "content": "..."},
#     "event": "pre_tool_use"
# }

async def execute(self, event, payload):
    results = []
    for hook in self._registry.get(event):
        if not _matches_hook(hook, payload):
            continue

        if isinstance(hook, CommandHookDefinition):
            results.append(await self._run_command_hook(hook, event, payload))
        elif isinstance(hook, HttpHookDefinition):
            results.append(await self._run_http_hook(hook, event, payload))
        elif isinstance(hook, PromptHookDefinition):
            results.append(await self._run_prompt_like_hook(hook, event, payload))
        elif isinstance(hook, AgentHookDefinition):
            results.append(await self._run_prompt_like_hook(hook, event, payload, agent_mode=True))

    return AggregatedHookResult(results=results)
```

## Hook 结果

### HookResult

```python
@dataclass(frozen=True)
class HookResult:
    hook_type: str           # hook 类型
    success: bool           # 是否成功
    output: str = ""        # 输出内容
    blocked: bool = False  # 是否阻止继续执行
    reason: str = ""        # 阻止原因
    metadata: dict = field(default_factory=dict)
```

### AggregatedHookResult

```python
@dataclass(frozen=True)
class AggregatedHookResult:
    results: list[HookResult]

    @property
    def blocked(self) -> bool:
        """任一 Hook 阻止则返回 True"""
        return any(r.blocked for r in self.results)

    @property
    def reason(self) -> str:
        """返回第一个阻止的原因"""
        for result in self.results:
            if result.blocked:
                return result.reason or result.output
        return ""
```

## 参数注入

Hook 命令和提示支持参数注入：

```python
def _inject_arguments(template: str, payload: dict, *, shell_escape: bool = False) -> str:
    serialized = json.dumps(payload, ensure_ascii=True)
    if shell_escape:
        serialized = shlex.quote(serialized)
    return template.replace("$ARGUMENTS", serialized)
```

**示例：**

```bash
# Command Hook
command: "echo 'Tool {tool_name} called' >> /tmp/hook_log.txt"
# $ARGUMENTS 被替换为 {"tool_name": "file_write", ...}

# Prompt Hook
prompt: "Validate if {tool_name} with input {tool_input} is safe to execute."
```

## Matcher 过滤

Hook 可通过 `matcher` 字段过滤执行条件：

```python
def _matches_hook(hook: HookDefinition, payload: dict) -> bool:
    matcher = getattr(hook, "matcher", None)
    if not matcher:
        return True

    subject = str(
        payload.get("tool_name") or
        payload.get("prompt") or
        payload.get("event") or ""
    )
    return fnmatch.fnmatch(subject, matcher)
```

**示例：**

```json
{
  "type": "command",
  "command": "echo 'Blocking write'",
  "matcher": "file_write",
  "block_on_failure": true
}
```

## Prompt Hook 验证协议

Prompt Hook 通过模型验证返回 JSON：

```python
async def _run_prompt_like_hook(hook, event, payload, *, agent_mode=False):
    prompt = _inject_arguments(hook.prompt, payload)

    prefix = (
        "You are validating whether a hook condition passes. "
        "Return strict JSON: {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}."
    )

    request = ApiMessageRequest(
        model=hook.model or self._context.default_model,
        messages=[ConversationMessage.from_user_text(prompt)],
        system_prompt=prefix,
        max_tokens=512,
    )

    # 解析响应
    text = await get_response_text(request)
    parsed = _parse_hook_json(text)

    if parsed["ok"]:
        return HookResult(hook_type=hook.type, success=True, output=text)
    return HookResult(
        hook_type=hook.type,
        success=False,
        output=text,
        blocked=hook.block_on_failure,
        reason=parsed.get("reason", "hook rejected")
    )
```

## JSON 解析

```python
def _parse_hook_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("ok"), bool):
            return parsed
    except json.JSONDecodeError:
        pass

    lowered = text.strip().lower()
    if lowered in {"ok", "true", "yes"}:
        return {"ok": True}
    return {"ok": False, "reason": text.strip() or "invalid JSON"}
```

## 配置格式

### hooks.json 格式

```json
{
  "pre_tool_use": [
    {
      "type": "command",
      "command": "echo 'PRE: {tool_name}' >> /tmp/hooks.log",
      "matcher": "*",
      "block_on_failure": false
    },
    {
      "type": "prompt",
      "prompt": "Is it safe to call {tool_name} with {tool_input}?",
      "block_on_failure": true
    }
  ],
  "post_tool_use": [
    {
      "type": "http",
      "url": "https://audit.example.com/hook",
      "headers": {"Authorization": "Bearer token"},
      "matcher": "file_write"
    }
  ]
}
```

## 工具执行中的集成

在 `_execute_tool_call()` 中：

```python
# Pre-Hook
if context.hook_executor is not None:
    pre_hooks = await context.hook_executor.execute(
        HookEvent.PRE_TOOL_USE,
        {"tool_name": tool_name, "tool_input": tool_input}
    )
    if pre_hooks.blocked:
        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=pre_hooks.reason or f"pre_tool_use hook blocked {tool_name}",
            is_error=True,
        )

# 工具执行...

# Post-Hook
if context.hook_executor is not None:
    await context.hook_executor.execute(
        HookEvent.POST_TOOL_USE,
        {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_result.content,
            "tool_is_error": tool_result.is_error,
        }
    )
```

## 扩展点

### 1. 自定义 Hook 类型

```python
class MyHookDefinition(BaseModel):
    type: Literal["my_hook"] = "my_hook"
    config: dict = {}

async def _run_my_hook(self, hook, event, payload):
    # 自定义执行逻辑
    ...
```

### 2. Hook 排序

Hook 按注册顺序执行，可在 `HookRegistry` 中实现优先级：

```python
def register(self, event, hook, priority=0):
    hook._priority = priority
    self._hooks[event].append(hook)
    self._hooks[event].sort(key=lambda h: h._priority)
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `hooks/events.py` | HookEvent 枚举定义 |
| `hooks/schemas.py` | Hook 类型定义 |
| `hooks/executor.py` | HookExecutor 执行器 |
| `hooks/loader.py` | HookRegistry 加载 |
| `hooks/types.py` | HookResult 结果类型 |
