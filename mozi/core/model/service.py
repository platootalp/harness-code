"""Model service for Mozi.

Provides a high-level interface for model invocation with event publishing
and session integration.

Note: Retry and circuit breaker functionality is now handled by litellm internally.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mozi.core.model.adapter import (
    Message,
    ModelRequest,
    ModelResponse,
)
from mozi.core.model.errors import (
    ModelInvocationError,
    ModelNotFoundError,
)
from mozi.core.model.registry import ModelRegistry
from mozi.infrastructure.config import Config, load_config
from mozi.infrastructure.event_bus import BaseEventBus, Event, EventPriority

# Event topics for model operations
MODEL_TOPIC = "model"
MODEL_INVOKED_EVENT = "model_invoked"
MODEL_ERROR_EVENT = "model_error"


@dataclass
class ModelInvocationResult:
    """Result of a model invocation with metadata."""

    response: ModelResponse
    provider: str
    model: str
    duration_ms: float
    attempt: int


class ModelService:
    """High-level model service with event publishing and session integration.

    This service wraps model adapters and provides:
    - Event publishing for model invocations and errors
    - Session message integration

    Note: Retry and circuit breaker functionality is now handled by litellm internally.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        event_bus: BaseEventBus | None = None,
        config: Config | None = None,
    ) -> None:
        """Initialize model service.

        Args:
            registry: Model registry for adapter lookup.
            event_bus: Event bus for publishing events. If None, no events published.
            config: Configuration. If None, loaded from default path.
        """
        self._registry = registry
        self._event_bus = event_bus
        self._config = config or load_config()

    async def invoke(
        self,
        model: str,
        messages: list[Message],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> ModelInvocationResult:
        """Invoke a model with automatic adapter selection and event publishing.

        Note: Retry and circuit breaker functionality is now handled by litellm internally.

        Args:
            model: Model name (e.g., 'claude-sonnet-4-7' or 'gpt-4o').
            messages: List of conversation messages.
            system_prompt: Optional system prompt override.
            temperature: Optional temperature override.
            max_tokens: Optional max tokens override.
            session_id: Optional session ID for event correlation.

        Returns:
            ModelInvocationResult with response and metadata.

        Raises:
            ModelNotFoundError: If model is not registered.
            ModelInvocationError: If invocation fails.
        """
        start_time = datetime.now()
        attempt = 1

        # Get adapter for model
        adapter = self._registry.get_adapter_by_model(model)
        if adapter is None:
            raise ModelNotFoundError(f"Model not found: {model}")

        provider = adapter.provider.value

        # Build request
        request = ModelRequest(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature or self._config.defaults.temperature,
            max_tokens=max_tokens or self._config.defaults.max_tokens,
        )

        # Publish model_invoked event before call
        await self._publish_event(
            topic=f"{MODEL_TOPIC}.{provider}.{MODEL_INVOKED_EVENT}",
            event_type=MODEL_INVOKED_EVENT,
            payload={
                "model": model,
                "provider": provider,
                "attempt": attempt,
                "message_count": len(messages),
                "session_id": session_id,
            },
            correlation_id=session_id,
            priority=EventPriority.LOW,
        )

        try:
            response = await adapter.invoke(request)

            # Publish success event
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            await self._publish_event(
                topic=f"{MODEL_TOPIC}.{provider}.response",
                event_type="model_response",
                payload={
                    "model": model,
                    "provider": provider,
                    "duration_ms": duration_ms,
                    "attempt": attempt,
                    "usage": {
                        "input_tokens": response.usage.input_tokens if response.usage else 0,
                        "output_tokens": response.usage.output_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                    "session_id": session_id,
                },
                correlation_id=session_id,
                priority=EventPriority.LOW,
            )

            return ModelInvocationResult(
                response=response,
                provider=provider,
                model=model,
                duration_ms=duration_ms,
                attempt=attempt,
            )

        except Exception as e:
            # Publish error event
            await self._publish_event(
                topic=f"{MODEL_TOPIC}.{provider}.{MODEL_ERROR_EVENT}",
                event_type=MODEL_ERROR_EVENT,
                payload={
                    "model": model,
                    "provider": provider,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempt": attempt,
                    "session_id": session_id,
                },
                correlation_id=session_id,
                priority=EventPriority.HIGH,
            )
            raise ModelInvocationError(
                f"Model invocation failed: {e}",
                model=model,
            ) from e

    async def _publish_event(
        self,
        topic: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Publish an event to the event bus.

        Args:
            topic: Event topic.
            event_type: Type of event.
            payload: Event payload.
            correlation_id: Optional correlation ID.
            priority: Event priority.
        """
        if self._event_bus is None:
            return

        event = Event(
            topic=topic,
            event_type=event_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            source="model_service",
        )

        await self._event_bus.publish(event)


# Global model service instance
_service: ModelService | None = None


def get_model_service(
    registry: ModelRegistry | None = None,
    event_bus: BaseEventBus | None = None,
) -> ModelService:
    """Get the global model service instance.

    Args:
        registry: Optional model registry override.
        event_bus: Optional event bus override.

    Returns:
        ModelService instance.
    """
    global _service
    if _service is None or registry is not None or event_bus is not None:
        _service = ModelService(
            registry=registry or ModelRegistry(),
            event_bus=event_bus,
        )
    return _service
