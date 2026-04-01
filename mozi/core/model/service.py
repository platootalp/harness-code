"""Model service for Mozi.

Provides a high-level interface for model invocation with event publishing
and session integration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mozi.core.model.adapter import (
    Message,
    ModelRequest,
    ModelResponse,
)
from mozi.core.model.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
)
from mozi.core.model.errors import (
    CircuitBreakerOpenError,
    ModelInvocationError,
    ModelNotFoundError,
)
from mozi.core.model.registry import ModelRegistry
from mozi.core.model.retry import RetryStrategy, execute_with_retry
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
    - Automatic retry with configurable strategy
    - Circuit breaker protection
    - Session message integration
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

        # Initialize circuit breakers per provider
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        for provider in self._registry.list_providers():
            provider_name = provider.value
            cb_config = CircuitBreakerConfig(
                failure_threshold=self._config.circuit_breaker.failure_threshold,
                recovery_timeout=self._config.circuit_breaker.recovery_timeout,
                half_open_max_calls=self._config.circuit_breaker.half_open_max_calls,
            )
            self._circuit_breakers[provider_name] = CircuitBreaker(config=cb_config)

        # Retry strategy from config
        self._retry_strategy = RetryStrategy(
            max_retries=self._config.retry.max_retries,
            base_delay=self._config.retry.base_delay,
            max_delay=self._config.retry.max_delay,
            exponential_base=self._config.retry.exponential_base,
            jitter=self._config.retry.jitter,
        )

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
            ModelInvocationError: If invocation fails after retries.
            CircuitBreakerOpenError: If circuit breaker is open.
        """
        start_time = datetime.now()
        attempt = 0

        # Get adapter for model
        adapter = self._registry.get_adapter_by_model(model)
        if adapter is None:
            raise ModelNotFoundError(f"Model not found: {model}")

        provider = adapter.provider.value

        # Get circuit breaker for provider
        circuit_breaker = self._circuit_breakers.get(provider)
        if circuit_breaker is None:
            raise ModelInvocationError(f"No circuit breaker for provider: {provider}")

        # Build request
        request = ModelRequest(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature or self._config.defaults.temperature,
            max_tokens=max_tokens or self._config.defaults.max_tokens,
        )

        async def do_invoke() -> ModelResponse:
            nonlocal attempt
            attempt += 1

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

                return response

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
                raise

        try:
            # Execute with circuit breaker and retry
            response = await circuit_breaker.call(
                execute_with_retry(do_invoke(), self._retry_strategy)
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ModelInvocationResult(
                response=response,
                provider=provider,
                model=model,
                duration_ms=duration_ms,
                attempt=attempt,
            )

        except CircuitBreakerOpenError:
            raise
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            raise ModelInvocationError(
                f"Model invocation failed after {attempt} attempts: {e}",
                model=model,
            ) from e

    async def invoke_stream(
        self,
        model: str,
        messages: list[Message],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Invoke a model with streaming response.

        Args:
            model: Model name.
            messages: List of conversation messages.
            system_prompt: Optional system prompt override.
            temperature: Optional temperature override.
            max_tokens: Optional max tokens override.
            session_id: Optional session ID for event correlation.

        Yields:
            Streaming response chunks.

        Raises:
            ModelNotFoundError: If model is not registered.
        """
        # Get adapter for model
        adapter = self._registry.get_adapter_by_model(model)
        if adapter is None:
            raise ModelNotFoundError(f"Model not found: {model}")

        # Build request with streaming enabled
        request = ModelRequest(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature or self._config.defaults.temperature,
            max_tokens=max_tokens or self._config.defaults.max_tokens,
            stream=True,
        )

        # Publish streaming started event
        await self._publish_event(
            topic=f"{MODEL_TOPIC}.{adapter.provider.value}.stream_started",
            event_type="model_stream_started",
            payload={
                "model": model,
                "provider": adapter.provider.value,
                "session_id": session_id,
            },
            correlation_id=session_id,
            priority=EventPriority.LOW,
        )

        try:
            async for chunk in adapter.invoke_stream(request):  # type: ignore
                yield chunk
        except Exception as e:
            # Publish streaming error event
            await self._publish_event(
                topic=f"{MODEL_TOPIC}.{adapter.provider.value}.{MODEL_ERROR_EVENT}",
                event_type=MODEL_ERROR_EVENT,
                payload={
                    "model": model,
                    "provider": adapter.provider.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "session_id": session_id,
                },
                correlation_id=session_id,
                priority=EventPriority.HIGH,
            )
            raise

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
