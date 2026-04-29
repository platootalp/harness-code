"""Model registry for managing available model adapters.

Provides a central registry for registering and retrieving model adapters.
"""

from __future__ import annotations

from mozi.core.model.adapter import ModelAdapter, ModelInfo, ModelProvider


class ModelRegistry:
    """Registry for managing model adapters.

    Allows registering adapters and retrieving them by provider or model name.
    """

    def __init__(self) -> None:
        """Initialize model registry."""
        self._adapters: dict[ModelProvider, ModelAdapter] = {}
        self._models: dict[str, ModelAdapter] = {}

    def register_adapter(self, adapter: ModelAdapter) -> None:
        """Register a model adapter.

        Args:
            adapter: The adapter to register.
        """
        self._adapters[adapter.provider] = adapter

        # Register each supported model
        for model_info in adapter.supported_models:
            self._models[model_info.name] = adapter

    def get_adapter(self, provider: ModelProvider) -> ModelAdapter | None:
        """Get adapter by provider.

        Args:
            provider: The model provider.

        Returns:
            The adapter if registered, None otherwise.
        """
        return self._adapters.get(provider)

    def get_adapter_by_model(self, model_name: str) -> ModelAdapter | None:
        """Get adapter by model name.

        Args:
            model_name: Name of the model.

        Returns:
            The adapter if found, None otherwise.
        """
        return self._models.get(model_name)

    def list_providers(self) -> list[ModelProvider]:
        """List all registered providers.

        Returns:
            List of registered provider enums.
        """
        return list(self._adapters.keys())

    def list_models(self) -> list[ModelInfo]:
        """List all registered models.

        Returns:
            List of ModelInfo for all registered models.
        """
        seen: set[str] = set()
        result: list[ModelInfo] = []

        for adapter in self._adapters.values():
            for model_info in adapter.supported_models:
                if model_info.name not in seen:
                    seen.add(model_info.name)
                    result.append(model_info)

        return result

    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available.

        Args:
            model_name: Name of the model.

        Returns:
            True if model is registered, False otherwise.
        """
        return model_name in self._models
