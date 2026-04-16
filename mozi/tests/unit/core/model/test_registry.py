"""Unit tests for ModelRegistry."""

from __future__ import annotations

import pytest

from mozi.core.model.adapter import (
    ModelAdapter,
    ModelInfo,
    ModelProvider,
    ModelRequest,
    ModelResponse,
)
from mozi.core.model.registry import ModelRegistry


class MockAdapter(ModelAdapter):
    """Mock adapter for testing."""

    def __init__(self, model_id: str = "mock-model") -> None:
        self._model_id = model_id
        self._call_count = 0

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.OPENAI

    @property
    def supported_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                name=self._model_id,
                provider=ModelProvider.OPENAI,
                display_name="Mock Model",
                context_window=100000,
                tier="balanced",
            )
        ]

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self._call_count += 1
        return ModelResponse(
            content="mock response",
            model=self._model_id,
            provider=ModelProvider.OPENAI,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    def validate_request(self, request: ModelRequest) -> None:
        """Validate request (always passes for mock)."""
        pass

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Get model info by name."""
        if model_name == self._model_id:
            return self.supported_models[0]
        return None


class TestModelRegistry:
    """Tests for ModelRegistry."""

    @pytest.fixture
    def registry(self) -> ModelRegistry:
        """Create a fresh registry."""
        return ModelRegistry()

    @pytest.fixture
    def mock_adapter(self) -> MockAdapter:
        """Create a mock adapter."""
        return MockAdapter()

    def test_register_adapter(self, registry: ModelRegistry, mock_adapter: MockAdapter) -> None:
        """Test registering an adapter."""
        registry.register_adapter(mock_adapter)
        assert mock_adapter in registry._adapters.values()

    def test_get_registered_adapter(
        self, registry: ModelRegistry, mock_adapter: MockAdapter
    ) -> None:
        """Test getting a registered adapter."""
        registry.register_adapter(mock_adapter)
        retrieved = registry.get_adapter(ModelProvider.OPENAI)
        assert retrieved is mock_adapter

    def test_get_unregistered_provider(
        self, registry: ModelRegistry
    ) -> None:
        """Test getting an unregistered provider returns None."""
        retrieved = registry.get_adapter(ModelProvider.ANTHROPIC)
        assert retrieved is None

    def test_list_providers_empty(self, registry: ModelRegistry) -> None:
        """Test listing providers when empty."""
        providers = registry.list_providers()
        assert providers == []

    def test_list_providers_with_adapters(
        self, registry: ModelRegistry, mock_adapter: MockAdapter
    ) -> None:
        """Test listing providers with adapters."""
        registry.register_adapter(mock_adapter)
        providers = registry.list_providers()
        assert ModelProvider.OPENAI in providers

    def test_get_adapter_by_model(
        self, registry: ModelRegistry, mock_adapter: MockAdapter
    ) -> None:
        """Test getting adapter by model name."""
        registry.register_adapter(mock_adapter)
        retrieved = registry.get_adapter_by_model("mock-model")
        assert retrieved is mock_adapter

    def test_get_adapter_by_model_not_found(
        self, registry: ModelRegistry
    ) -> None:
        """Test getting adapter by unknown model name."""
        retrieved = registry.get_adapter_by_model("unknown-model")
        assert retrieved is None

    def test_list_models(
        self, registry: ModelRegistry, mock_adapter: MockAdapter
    ) -> None:
        """Test listing all registered models."""
        registry.register_adapter(mock_adapter)
        models = registry.list_models()
        assert len(models) == 1
        assert models[0].name == "mock-model"

    def test_is_model_available(
        self, registry: ModelRegistry, mock_adapter: MockAdapter
    ) -> None:
        """Test checking if model is available."""
        registry.register_adapter(mock_adapter)
        assert registry.is_model_available("mock-model") is True
        assert registry.is_model_available("unknown-model") is False
