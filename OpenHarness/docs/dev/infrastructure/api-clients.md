# API 客户端

本文档介绍 OpenHarness 的 API 客户端架构，涵盖对 Anthropic、OpenAI-Compatible、GitHub Copilot 和 OpenAI Codex 等 Provider 的支持。

## 架构概览

```
src/openharness/api/
├── client.py          # AnthropicApiClient（核心抽象）
├── openai_client.py   # OpenAICompatibleClient
├── copilot_client.py  # CopilotClient
├── codex_client.py    # CodexApiClient
├── provider.py        # ProviderInfo 检测
├── registry.py        # Provider 注册表
├── errors.py          # 错误类型定义
└── usage.py           # 用量追踪
```

所有客户端实现统一的 `SupportsStreamingMessages` 协议，可作为 QueryEngine 的可插拔后端：

```python
class SupportsStreamingMessages(Protocol):
    async def stream_message(self, request: ApiMessageRequest) -> AsyncIterator[ApiStreamEvent]:
        """Yield streamed events for the request."""
```

## 核心类型

### ApiMessageRequest

```python
@dataclass(frozen=True)
class ApiMessageRequest:
    model: str
    messages: list[ConversationMessage]
    system_prompt: str | None = None
    max_tokens: int = 4096
    tools: list[dict[str, Any]] = field(default_factory=list)
```

### 流式事件

```python
ApiStreamEvent = ApiTextDeltaEvent | ApiMessageCompleteEvent | ApiRetryEvent
```

- `ApiTextDeltaEvent` — 模型输出的增量文本
- `ApiMessageCompleteEvent` — 终端事件，包含完整 Assistant 消息和用量
- `ApiRetryEvent` — 可恢复错误，自动重试前的通知

## AnthropicApiClient

`client.py` 中的 `AnthropicApiClient` 是核心实现，基于官方 `anthropic` SDK 构建：

```python
class AnthropicApiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        auth_token: str | None = None,       # Claude OAuth token
        base_url: str | None = None,          # 兼容代理
        claude_oauth: bool = False,
        auth_token_resolver: Callable[[], str] | None = None,
    ) -> None:
```

### 重试逻辑

- 最大重试次数：`MAX_RETRIES = 3`
- 指数退避：基础延迟 1s，最大 30s
- 可重试状态码：`{429, 500, 502, 503, 529}`
- 支持 `Retry-After` 响应头

### OAuth 支持

Claude Subscription（Claude OAuth）通过 `claude_oauth=True` 启用，客户端会注入：
- `anthropic-beta: oauth-2025-04-20` 请求头
- 特殊的 `metadata` 和 `betas` 参数
- `x-client-request-id` 追踪头

## OpenAICompatibleClient

`openai_client.py` 中的 `OpenAICompatibleClient` 支持 DashScope（月暗）、GitHub Models 等 OpenAI 兼容 Provider：

```python
class OpenAICompatibleClient:
    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
```

### 消息格式转换

Anthropic 消息格式与 OpenAI 的差异：
- **System Prompt**：Anthropic 用独立参数，OpenAI 用 `role=system` 消息
- **Tool Use**：Anthropic 是 content block，OpenAI 用 `tool_calls` 字段
- **Tool Result**：Anthropic 是 content block，OpenAI 用独立的 `role=tool` 消息

### Reasoning Content

Kimi 等 Thinking 模型需要在每个 Assistant 消息中包含 `reasoning_content` 字段。客户端在解析响应时暂存 reasoning，发送时回放。

## CopilotClient

`copilot_client.py` 中的 `CopilotClient` 基于 `OpenAICompatibleClient`，使用 GitHub OAuth Token：

```python
class CopilotClient:
    def __init__(
        self,
        github_token: str | None = None,
        *,
        enterprise_url: str | None = None,
        model: str | None = None,
    ) -> None:
```

关键特点：
- 直接使用 GitHub OAuth Token 作为 Bearer Token
- 支持企业 GitHub（通过 `enterprise_url`）
- 使用 `Openai-Intent: conversation-edits` 头
- 默认模型：`gpt-4o`

认证信息从 `~/.openharness/copilot_auth.json` 加载。

## CodexApiClient

`codex_client.py` 中的 `CodexApiClient` 使用 ChatGPT/Codex Subscription 的 `/codex/responses` 端点：

```python
class CodexApiClient:
    def __init__(self, auth_token: str, *, base_url: str | None = None) -> None:
```

- 基于 JWT 解析 `chatgpt_account_id`
- 使用 SSE 流式传输
- 支持 function_call 事件：`response.output_item.done`
- 默认 Base URL：`https://chatgpt.com/backend-api`

## Provider 检测

`provider.py` 中的 `detect_provider()` 函数根据配置推断活跃 Provider：

```python
def detect_provider(settings: Settings) -> ProviderInfo:
    """Infer the active provider and rough capability set using the registry."""
```

返回 `ProviderInfo`（name、auth_kind、voice_supported、voice_reason）。

## 错误类型

`errors.py` 定义了统一错误层次：

```python
class OpenHarnessApiError(Exception): ...

class AuthenticationFailure(OpenHarnessApiError): ...  # 401/403
class RateLimitFailure(OpenHarnessApiError): ...       # 429
class RequestFailure(OpenHarnessApiError): ...         # 其他错误
```

## 扩展指南

### 添加新的 API Provider

1. 在 `api/` 目录创建新的 `*_client.py` 文件
2. 实现 `SupportsStreamingMessages` 协议
3. 在 `api/registry.py` 中注册 Provider（如果使用注册表检测）
4. 在 `cli.py` 中添加相应的认证命令

### Provider 注册表

`registry.py` 维护一个动态注册表，支持通过模型名、API Key 前缀、Base URL 等特征自动检测 Provider 类型。详情参考 `api/registry.py`。

## 关键文件

| 文件 | 职责 |
|------|------|
| `client.py` | Anthropic 官方 SDK 封装 + 重试 |
| `openai_client.py` | OpenAI 兼容格式转换 + 流式处理 |
| `copilot_client.py` | GitHub OAuth + Copilot 特定头 |
| `codex_client.py` | ChatGPT.com Codex Responses 端点 |
| `provider.py` | Provider 能力检测 |
| `errors.py` | 统一错误类型 |
| `usage.py` | Token 用量快照 |
