# Model API

## Overview

The Model module provides a unified interface for interacting with various LLM providers (OpenAI, Anthropic).

## ModelRegistry

### Methods

#### `register(name: str, adapter: ModelAdapter) -> None`

Registers a model adapter.

**Parameters:**
- `name` (str): Adapter name
- `adapter` (ModelAdapter): Model adapter instance

#### `get(name: str) -> ModelAdapter`

Retrieves a registered adapter.

**Parameters:**
- `name` (str): Adapter name

**Returns:**
- `ModelAdapter`: The adapter instance

**Raises:**
- `ValueError`: If adapter not found

#### `list_models() -> list[str]`

Lists all registered model names.

**Returns:**
- `list[str]`: List of model names

## ModelAdapter

Abstract base class for model adapters.

### Methods

#### `invoke(messages: list[Message], **kwargs) -> Response`

Invokes the model with messages.

**Parameters:**
- `messages` (list[Message]): List of messages
- `**kwargs`: Additional parameters

**Returns:**
- `Response`: Model response

## Built-in Adapters

### OpenAIAdapter

Adapter for OpenAI models.

```python
from mozi.core.model.openai import OpenAIAdapter

adapter = OpenAIAdapter(model="gpt-4")
```

### AnthropicAdapter

Adapter for Anthropic models.

```python
from mozi.core.model.anthropic import AnthropicAdapter

adapter = AnthropicAdapter(model="claude-3-opus")
```

## Error Handling

### ModelInvocationError

Raised when model invocation fails.

### RateLimitError

Raised when rate limit is exceeded.

### InvalidRequestError

Raised when request is invalid.
