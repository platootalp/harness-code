# mozi/core/model Litellm 重构设计方案

> **版本**: v1.0
> **日期**: 2026-04-02
> **状态**: 规划中
> **所属版本**: v1.1

---

## 1. 概述

### 1.1 背景

当前 `mozi/core/model/` 模块为每个 LLM Provider（OpenAI、Anthropic）独立实现 HTTP 调用逻辑，存在大量重复代码。架构文档（[2026-03-31_architecture_design.md](../../foundation/architecture/2026-03-31_architecture_design.md)）已明确技术选型为 **litellm** 作为统一模型网关。

### 1.2 目标

- 消除 Provider 适配器间的重复 HTTP 调用逻辑
- 统一模型调用接口，支持 100+ LLM Provider
- 复用 litellm 内置的重试、熔断、限流能力
- 降低新增 Provider 的维护成本

### 1.3 范围

- 模块：`mozi/core/model/`
- 阶段：v1.1 版本迭代

---

## 2. 现状分析

### 2.1 当前架构

```
mozi/core/model/
├── adapter.py          # ModelAdapter ABC + 数据模型
├── openai.py           # OpenAIAdapter - 直接 HTTP 调用 OpenAI API
├── anthropic.py        # AnthropicAdapter - 直接 HTTP 调用 Anthropic API
├── registry.py         # ModelRegistry - 适配器注册
├── service.py          # ModelService - 高级服务（重试、熔断）
├── template.py         # PromptTemplateManager
├── errors.py           # 错误类型
├── circuit_breaker.py  # CircuitBreaker
└── retry.py           # RetryStrategy
```

### 2.2 问题分析

| 问题 | 说明 |
|------|------|
| **代码重复** | OpenAIAdapter 和 AnthropicAdapter 存在大量相似 HTTP 调用逻辑 |
| **API 差异处理复杂** | Provider 间 API 格式差异（`/chat/completions` vs `/messages`）在应用层处理 |
| **能力不统一** | Function Calling 等能力各 Provider 格式不同，难以统一抽象 |
| **维护成本高** | 新增 Provider 需要复制大量模板代码 |
| **弹性机制重复** | circuit_breaker.py 和 retry.py 与 litellm 内置能力重叠 |

### 2.3 依赖关系

```
ModelService
    └── ModelRegistry
            ├── OpenAIAdapter  ──► httpx ──► OpenAI API
            └── AnthropicAdapter ──► httpx ──► Anthropic API
```

---

## 3. litellm 优势

| 能力 | 说明 |
|------|------|
| **统一接口** | 100+ LLM Provider 使用相同 API 格式 |
| **内置弹性** | 内置重试、熔断、限流、超时 |
| **成本追踪** | 自动追踪 token 消耗和费用 |
| **Function Calling** | 统一格式的工具调用 |
| **流式输出** | 统一格式的流式响应 |
| **多模态** | 支持 vision、audio 等 |

---

## 4. 目标架构

### 4.1 目录结构

```
mozi/core/model/
├── __init__.py
├── adapter.py           # [保留] 数据模型 + ModelAdapter 接口
├── litellm_gateway.py   # [新增] LitellmGateway - litellm 统一封装
├── registry.py          # [修改] ModelRegistry - 注册 LitellmGateway
├── service.py           # [保留] ModelService - 保持高级特性
├── template.py          # [保留] PromptTemplateManager
├── errors.py            # [修改] 错误类型 + litellm 错误映射
├── circuit_breaker.py   # [删除] 不再需要，litellm 内置
└── retry.py            # [删除] 不再需要，litellm 内置
```

### 4.2 组件职责

| 组件 | 职责 |
|------|------|
| `adapter.py` | 数据模型（Message、ModelRequest、ModelResponse）和 `ModelAdapter` 接口 |
| `litellm_gateway.py` | Litellm 统一网关，替代 OpenAIAdapter/AnthropicAdapter |
| `registry.py` | 模型注册表，通过 provider 路由到对应 Gateway 实例 |
| `service.py` | 高级服务（事件发布、会话集成），调用 Gateway |
| `template.py` | Prompt 模板管理（无变更） |
| `errors.py` | 错误类型 + litellm 错误映射 |

### 4.3 依赖关系（重构后）

```
ModelService
    └── ModelRegistry
            └── LitellmGateway ──► litellm ──► 各 Provider API
```

---

## 5. 详细设计

### 5.1 LitellmGateway

```python
"""Litellm 统一网关适配器。

替代原有的 OpenAIAdapter 和 AnthropicAdapter，
通过 litellm 提供统一的模型调用接口。
"""

from __future__ import annotations

from typing import Any

import litellm
from litellm import AuthenticationError as LiteLLMAuthError
from litellm import RateLimitError as LiteLLMRateLimitError
from litellm import InvalidRequestError as LiteLLMInvalidRequestError

from mozi.core.model.adapter import (
    Message,
    MessageRole,
    ModelAdapter,
    ModelInfo,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ToolCall,
)
from mozi.core.model.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
    ResponseParseError,
)


class LitellmGateway(ModelAdapter):
    """Litellm 统一网关。

    支持 OpenAI、Anthropic、Azure、Cohere 等 100+ Provider。
    统一处理请求/响应格式转换和错误映射。
    """

    def __init__(
        self,
        api_key: str,
        provider: ModelProvider,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """初始化 Litellm 网关。

        Args:
            api_key: API 密钥。
            provider: 模型 Provider。
            base_url: 可选的自定义 base URL。
            timeout: 请求超时时间（秒）。
        """
        self._api_key = api_key
        self._provider = provider
        self._base_url = base_url
        self._timeout = timeout

        # 配置 litellm
        litellm.drop_params = True
        litellm.set_verbose = False

    @property
    def provider(self) -> ModelProvider:
        """返回模型 Provider。"""
        return self._provider

    @property
    def supported_models(self) -> list[ModelInfo]:
        """返回支持的模型列表。"""
        return SUPPORTED_MODELS.get(self._provider, [])

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """获取模型信息。"""
        for model in self.supported_models:
            if model.name == model_name:
                return model
        return None

    def validate_request(self, request: ModelRequest) -> None:
        """验证模型请求。"""
        if not request.model:
            raise InvalidRequestError("Model name is required")

        if not request.messages:
            raise InvalidRequestError("At least one message is required")

        if request.temperature < 0.0 or request.temperature > 2.0:
            raise InvalidRequestError("Temperature must be between 0.0 and 2.0")

        if request.top_p is not None and (request.top_p < 0.0 or request.top_p > 1.0):
            raise InvalidRequestError("top_p must be between 0.0 and 1.0")

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise InvalidRequestError("max_tokens must be positive")

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """调用模型。"""
        self.validate_request(request)

        try:
            response = await litellm.acompletion(
                model=request.model,
                messages=self._format_messages(request.messages, request.system_prompt),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=request.stop_sequences,
                tools=request.tools,
                timeout=self._timeout,
                api_key=self._api_key,
                base_url=self._base_url,
            )
            return self._parse_response(response, request.model)

        except LiteLLMAuthError as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e
        except LiteLLMRateLimitError as e:
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except LiteLLMInvalidRequestError as e:
            raise InvalidRequestError(f"Invalid request: {e}") from e
        except Exception as e:
            raise ModelInvocationError(f"Model invocation failed: {e}") from e

    def _format_messages(
        self,
        messages: list[Message],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        """格式化消息为 litellm 格式。"""
        result: list[dict[str, Any]] = []

        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        for msg in messages:
            formatted: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                formatted["name"] = msg.name

            if msg.tool_calls:
                formatted["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            if msg.tool_call_id:
                formatted["tool_call_id"] = msg.tool_call_id

            result.append(formatted)

        return result

    def _parse_response(
        self,
        response: Any,
        model: str,
    ) -> ModelResponse:
        """解析 litellm 响应。"""
        try:
            choice = response.choices[0]
            message = choice.message

            # 提取文本内容
            content_text = message.content or ""

            # 提取工具调用
            tool_calls: list[ToolCall] = []
            if message.tool_calls:
                for raw_tc in message.tool_calls:
                    function = raw_tc.function
                    tool_calls.append(ToolCall(
                        id=raw_tc.id,
                        name=function.name,
                        arguments=function.arguments,
                    ))

            # 提取用量
            usage = ModelUsage(
                input_tokens=response.usage.prompt_tokens if hasattr(response.usage, "prompt_tokens") else 0,
                output_tokens=response.usage.completion_tokens if hasattr(response.usage, "completion_tokens") else 0,
                total_tokens=response.usage.total_tokens if hasattr(response.usage, "total_tokens") else 0,
            )

            return ModelResponse(
                content=content_text,
                model=model,
                stop_reason=choice.finish_reason,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                metadata={"response_id": response.id},
            )

        except Exception as e:
            raise ResponseParseError(f"Failed to parse response: {e}") from e


# 支持的模型配置
SUPPORTED_MODELS: dict[ModelProvider, list[ModelInfo]] = {
    ModelProvider.ANTHROPIC: [
        ModelInfo(
            name="claude-3-5-sonnet-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3.5 Sonnet",
            context_window=200000,
            tier="balanced",
            supports_tools=True,
        ),
        ModelInfo(
            name="claude-3-5-haiku-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3.5 Haiku",
            context_window=200000,
            tier="fast",
            supports_tools=True,
        ),
        ModelInfo(
            name="claude-3-opus-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3 Opus",
            context_window=200000,
            tier="powerful",
            supports_tools=True,
        ),
    ],
    ModelProvider.OPENAI: [
        ModelInfo(
            name="gpt-4o",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4o",
            context_window=128000,
            tier="balanced",
            supports_tools=True,
            supports_vision=True,
        ),
        ModelInfo(
            name="gpt-4o-mini",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4o Mini",
            context_window=128000,
            tier="fast",
            supports_tools=True,
        ),
        ModelInfo(
            name="gpt-4-turbo",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4 Turbo",
            context_window=128000,
            tier="powerful",
            supports_tools=True,
        ),
    ],
}
```

### 5.2 错误映射

```python
# mozi/core/model/errors.py 新增

class ModelError(Exception):
    """模型相关错误的基类。"""

    error_code: str = "MODEL_000"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# litellm 错误映射表
LITELLM_ERROR_MAP: dict[type, type[ModelError]] = {
    litellm.AuthenticationError: AuthenticationError,
    litellm.RateLimitError: RateLimitError,
    litellm.InvalidRequestError: InvalidRequestError,
    litellm.ContextWindowExceededError: InvalidRequestError,
    litellm.BadRequestError: InvalidRequestError,
}


def map_litellm_error(error: Exception) -> ModelError:
    """将 litellm 错误映射为 Mozi 错误。

    Args:
        error: litellm 抛出的错误。

    Returns:
        对应的 Mozi 错误类型。
    """
    for litellm_error_type, mozi_error_type in LITELLM_ERROR_MAP.items():
        if isinstance(error, litellm_error_type):
            return mozi_error_type(str(error))

    # 默认映射为 ModelInvocationError
    return ModelInvocationError(str(error))
```

### 5.3 Registry 更新

```python
# mozi/core/model/registry.py 修改

class ModelRegistry:
    """模型注册表。"""

    def __init__(self) -> None:
        """初始化模型注册表。"""
        self._adapters: dict[ModelProvider, ModelAdapter] = {}
        self._models: dict[str, ModelAdapter] = {}

    def register_adapter(self, adapter: ModelAdapter) -> None:
        """注册模型适配器。"""
        self._adapters[adapter.provider] = adapter

        for model_info in adapter.supported_models:
            self._models[model_info.name] = adapter

    # ... 其他方法保持不变
```

---

## 6. 迁移计划

### Phase 1: 基础设施（第 1-2 天）

| 任务 | 说明 |
|------|------|
| 添加 litellm 依赖 | 更新 pyproject.toml |
| 创建 LitellmGateway | 实现核心网关类 |
| 更新 errors.py | 添加 litellm 错误映射 |

### Phase 2: 适配器替换（第 3-4 天）

| 任务 | 说明 |
|------|------|
| 替换 OpenAIAdapter | 使用 LitellmGateway(provider=OPENAI) |
| 替换 AnthropicAdapter | 使用 LitellmGateway(provider=ANTHROPIC) |
| 更新 registry.py | 注册新的 Gateway 实例 |

### Phase 3: 清理与测试（第 5 天）

| 任务 | 说明 |
|------|------|
| 删除废弃文件 | circuit_breaker.py、retry.py |
| 更新 import | 清理废弃导入 |
| 运行测试 | 确保功能正常 |

---

## 7. 测试策略

| 测试类型 | 覆盖内容 |
|----------|----------|
| 单元测试 | LitellmGateway 请求/响应映射、错误映射 |
| 集成测试 | 实际调用 OpenAI/Anthropic API（mock） |
| 回归测试 | 确保现有 ModelService 功能不受影响 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| litellm 版本升级 API 变化 | 中 | 封装接口隔离依赖，版本锁定 |
| 新 Provider 行为差异 | 低 | 差异化处理逻辑 |
| 性能开销 | 低 | litellm 直接调用，无中间层 |
| 删除 circuit_breaker/retry | 中 | 确认 litellm 内置能力足够 |

---

## 9. 验收标准

- [ ] litellm 依赖已添加
- [ ] LitellmGateway 实现完整
- [ ] OpenAI 模型调用正常
- [ ] Anthropic 模型调用正常
- [ ] 错误映射正确
- [ ] circuit_breaker.py 和 retry.py 已删除
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] ruff、mypy 检查通过

---

_版本: v1.0_
_更新日期: 2026-04-02_

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-04-02 | 初始版本 |
