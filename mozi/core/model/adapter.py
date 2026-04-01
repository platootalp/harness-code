"""Model adapter base classes and data models.

Defines the abstract ModelAdapter interface and supporting data structures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelProvider(Enum):
    """Model provider enumeration."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class MessageRole(Enum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Tool call from model."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Conversation message."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass
class ModelUsage:
    """Model usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ModelInfo:
    """Information about a supported model."""

    name: str
    provider: ModelProvider
    display_name: str
    context_window: int
    tier: str  # "fast" | "balanced" | "powerful"
    supports_tools: bool = True
    supports_vision: bool = False


@dataclass
class ModelRequest:
    """Model invocation request."""

    model: str
    messages: list[Message]
    system_prompt: str | None = None
    temperature: float = 1.0
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] | None = None
    tools: list[dict[str, Any]] | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Model invocation response."""

    content: str
    model: str
    stop_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: ModelUsage | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(ABC):
    """Abstract base class for model adapters.

    All model adapters must implement this interface.
    """

    @property
    @abstractmethod
    def provider(self) -> ModelProvider:
        """Return the model provider.

        Returns:
            The model provider enum value.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_models(self) -> list[ModelInfo]:
        """Return list of supported models.

        Returns:
            List of ModelInfo for supported models.
        """
        raise NotImplementedError

    @abstractmethod
    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """Invoke the model with a request.

        Args:
            request: The model request.

        Returns:
            The model response.

        Raises:
            InvalidRequestError: If the request is invalid.
            ModelInvocationError: If the invocation fails.
            ResponseParseError: If response parsing fails.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request: ModelRequest) -> None:
        """Validate a model request.

        Args:
            request: The request to validate.

        Raises:
            InvalidRequestError: If the request is invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Get information about a specific model.

        Args:
            model_name: Name of the model.

        Returns:
            ModelInfo if found, None otherwise.
        """
        raise NotImplementedError
