"""Model module for Mozi.

Provides unified interface for LLM model providers:
- ModelAdapter: Abstract base class for model adapters
- LitellmGateway: Unified gateway for 100+ LLM providers via litellm
- ModelRegistry: Registry for managing available models
- PromptTemplateManager: Template management for prompts
"""

from __future__ import annotations

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
    CircuitBreakerOpenError,
    InvalidRequestError,
    ModelInvocationError,
    ModelNotFoundError,
    RateLimitError,
    ResponseParseError,
)
from mozi.core.model.litellm_gateway import LitellmGateway
from mozi.core.model.registry import ModelRegistry
from mozi.core.model.template import PromptTemplateManager

__all__ = [
    # Enums
    "ModelProvider",
    "MessageRole",
    # Data classes
    "Message",
    "ToolCall",
    "ModelRequest",
    "ModelResponse",
    "ModelUsage",
    "ModelInfo",
    # Adapter
    "ModelAdapter",
    "LitellmGateway",
    # Registry
    "ModelRegistry",
    # Template
    "PromptTemplateManager",
    # Errors
    "ModelInvocationError",
    "ModelNotFoundError",
    "InvalidRequestError",
    "ResponseParseError",
    "RateLimitError",
    "AuthenticationError",
    "CircuitBreakerOpenError",
]
