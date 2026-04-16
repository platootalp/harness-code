"""Unit tests for ModelService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.core.model.adapter import (
    Message,
    MessageRole,
    ModelAdapter,
    ModelInfo,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from mozi.core.model.errors import (
    ModelNotFoundError,
)
from mozi.core.model.registry import ModelRegistry
from mozi.core.model.service import (
    ModelInvocationResult,
    ModelService,
    get_model_service,
)
from mozi.infrastructure.config import Config, DefaultsConfig


class MockAdapter(ModelAdapter):
    """Mock adapter for testing."""

    def __init__(self, provider: ModelProvider = ModelProvider.ANTHROPIC) -> None:
        self._provider = provider
        self._supported_models = [
            ModelInfo(
                name="test-model",
                provider=provider,
                display_name="Test Model",
                context_window=100000,
                tier="balanced",
            ),
        ]
        self._invoke_call_count = 0

    @property
    def provider(self) -> ModelProvider:
        return self._provider

    @property
    def supported_models(self) -> list[ModelInfo]:
        return self._supported_models

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        for model in self._supported_models:
            if model.name == model_name:
                return model
        return None

    def validate_request(self, request: ModelRequest) -> None:
        if not request.model:
            raise ValueError("Model name is required")
        if not request.messages:
            raise ValueError("At least one message is required")

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self._invoke_call_count += 1
        return ModelResponse(
            content=f"Response {self._invoke_call_count}",
            model=request.model,
            stop_reason="stop",
            usage=ModelUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
            ),
        )


@pytest.fixture
def mock_config() -> Config:
    """Create a mock config for testing."""
    return Config(
        providers={},
        defaults=DefaultsConfig(
            provider="anthropic",
            model="test-model",
            temperature=1.0,
            max_tokens=4096,
        ),
    )


@pytest.fixture
def mock_registry() -> ModelRegistry:
    """Create a mock registry with test adapter."""
    registry = ModelRegistry()
    adapter = MockAdapter(provider=ModelProvider.ANTHROPIC)
    registry.register_adapter(adapter)
    return registry


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """Create a mock event bus."""
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def model_service(
    mock_registry: ModelRegistry,
    mock_event_bus: MagicMock,
    mock_config: Config,
) -> ModelService:
    """Create a model service instance for testing."""
    return ModelService(
        registry=mock_registry,
        event_bus=mock_event_bus,
        config=mock_config,
    )


class TestModelServiceInitialization:
    """Tests for ModelService initialization."""

    def test_init_with_registry(
        self,
        mock_registry: ModelRegistry,
        mock_config: Config,
    ) -> None:
        """Test service initialization with registry."""
        service = ModelService(
            registry=mock_registry,
            config=mock_config,
        )
        assert service._registry is mock_registry
        assert service._event_bus is None

    def test_init_with_event_bus(
        self,
        mock_registry: ModelRegistry,
        mock_event_bus: MagicMock,
        mock_config: Config,
    ) -> None:
        """Test service initialization with event bus."""
        service = ModelService(
            registry=mock_registry,
            event_bus=mock_event_bus,
            config=mock_config,
        )
        assert service._event_bus is mock_event_bus


class TestModelServiceInvoke:
    """Tests for ModelService.invoke."""

    @pytest.mark.asyncio
    async def test_invoke_success(
        self,
        model_service: ModelService,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test successful model invocation."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        result = await model_service.invoke(
            model="test-model",
            messages=messages,
            session_id="session-123",
        )

        assert isinstance(result, ModelInvocationResult)
        assert result.model == "test-model"
        assert result.provider == "anthropic"
        assert result.response.content == "Response 1"
        assert result.attempt == 1

    @pytest.mark.asyncio
    async def test_invoke_with_system_prompt(
        self,
        model_service: ModelService,
    ) -> None:
        """Test invocation with system prompt."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        result = await model_service.invoke(
            model="test-model",
            messages=messages,
            system_prompt="You are helpful.",
        )

        assert result.response.content == "Response 1"

    @pytest.mark.asyncio
    async def test_invoke_model_not_found(
        self,
        model_service: ModelService,
    ) -> None:
        """Test invocation with unknown model raises error."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        with pytest.raises(ModelNotFoundError):
            await model_service.invoke(
                model="unknown-model",
                messages=messages,
            )

    @pytest.mark.asyncio
    async def test_invoke_publishes_events(
        self,
        model_service: ModelService,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test that invoke publishes events to event bus."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        await model_service.invoke(
            model="test-model",
            messages=messages,
            session_id="session-123",
        )

        # Should have published model_invoked and model_response events
        assert mock_event_bus.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_invoke_no_event_bus(
        self,
        mock_registry: ModelRegistry,
        mock_config: Config,
    ) -> None:
        """Test invocation works without event bus."""
        service = ModelService(
            registry=mock_registry,
            event_bus=None,
            config=mock_config,
        )
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        # Should not raise
        result = await service.invoke(
            model="test-model",
            messages=messages,
        )
        assert result.response.content == "Response 1"

    @pytest.mark.asyncio
    async def test_invoke_with_temperature_override(
        self,
        model_service: ModelService,
    ) -> None:
        """Test invocation with temperature override."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        # Just verify it doesn't raise
        result = await model_service.invoke(
            model="test-model",
            messages=messages,
            temperature=0.5,
        )
        assert result.response.content == "Response 1"

    @pytest.mark.asyncio
    async def test_invoke_with_max_tokens_override(
        self,
        model_service: ModelService,
    ) -> None:
        """Test invocation with max_tokens override."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        # Just verify it doesn't raise
        result = await model_service.invoke(
            model="test-model",
            messages=messages,
            max_tokens=100,
        )
        assert result.response.content == "Response 1"

    @pytest.mark.asyncio
    async def test_invoke_returns_duration_ms(
        self,
        model_service: ModelService,
    ) -> None:
        """Test that invoke returns duration in milliseconds."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        result = await model_service.invoke(
            model="test-model",
            messages=messages,
        )

        assert result.duration_ms >= 0


class TestGetModelService:
    """Tests for get_model_service global function."""

    def test_get_model_service_creates_instance(self) -> None:
        """Test get_model_service creates an instance."""
        # Reset global
        import mozi.core.model.service as service_module

        service_module._service = None

        service = get_model_service()

        assert isinstance(service, ModelService)

    def test_get_model_service_returns_cached(self) -> None:
        """Test get_model_service returns cached instance."""
        import mozi.core.model.service as service_module

        service_module._service = None
        service1 = get_model_service()
        service2 = get_model_service()

        assert service1 is service2

    def test_get_model_service_with_registry_override(self) -> None:
        """Test get_model_service with registry override creates new instance."""
        import mozi.core.model.service as service_module

        service_module._service = None
        registry = ModelRegistry()
        service = get_model_service(registry=registry)

        assert isinstance(service, ModelService)


class TestModelInvocationResult:
    """Tests for ModelInvocationResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a ModelInvocationResult."""
        response = ModelResponse(
            content="Test",
            model="test-model",
        )
        result = ModelInvocationResult(
            response=response,
            provider="anthropic",
            model="test-model",
            duration_ms=100.5,
            attempt=1,
        )

        assert result.response is response
        assert result.provider == "anthropic"
        assert result.model == "test-model"
        assert result.duration_ms == 100.5
        assert result.attempt == 1
