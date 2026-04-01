# Model API

## Overview

The Model module provides a unified interface for interacting with various LLM providers (OpenAI, Anthropic, Azure, Cohere, etc.) via litellm.

## LitellmGateway

The `LitellmGateway` class provides a unified adapter for all litellm-supported models.

### Initialization

```python
from mozi.core.model import LitellmGateway, ModelProvider

# For OpenAI models
gateway = LitellmGateway(
    api_key="your-api-key",
    provider=ModelProvider.OPENAI,
)

# For Anthropic models
gateway = LitellmGateway(
    api_key="your-api-key",
    provider=ModelProvider.ANTHROPIC,
)
```

### Supported Models

#### OpenAI

- `gpt-4o` - GPT-4o (balanced, supports vision)
- `gpt-4o-mini` - GPT-4o Mini (fast)
- `gpt-4-turbo` - GPT-4 Turbo (powerful)
- `gpt-4` - GPT-4
- `gpt-3.5-turbo` - GPT-3.5 Turbo (fast)

#### Anthropic

- `claude-3-5-sonnet-latest` - Claude 3.5 Sonnet (balanced)
- `claude-3-5-haiku-latest` - Claude 3.5 Haiku (fast)
- `claude-3-opus-latest` - Claude 3 Opus (powerful)

### Methods

#### `invoke(request: ModelRequest) -> ModelResponse`

Invokes the model with a request.

```python
from mozi.core.model import Message, MessageRole, ModelRequest

request = ModelRequest(
    model="gpt-4o",
    messages=[Message(role=MessageRole.USER, content="Hello!")],
    temperature=1.0,
    max_tokens=4096,
)

response = await gateway.invoke(request)
print(response.content)
```

#### `validate_request(request: ModelRequest) -> None`

Validates a model request before invocation.

#### `get_model_info(model_name: str) -> ModelInfo | None`

Retrieves information about a specific model.

## ModelRegistry

### Methods

#### `register_adapter(adapter: ModelAdapter) -> None`

Registers a model adapter.

#### `get_adapter(provider: ModelProvider) -> ModelAdapter | None`

Retrieves an adapter by provider.

#### `get_adapter_by_model(model_name: str) -> ModelAdapter | None`

Retrieves an adapter by model name.

#### `list_providers() -> list[ModelProvider]`

Lists all registered providers.

#### `list_models() -> list[ModelInfo]`

Lists all registered models.

## Error Handling

### ModelInvocationError

Raised when model invocation fails.

### RateLimitError

Raised when rate limit is exceeded.

### InvalidRequestError

Raised when request is invalid.

### AuthenticationError

Raised when authentication fails.
