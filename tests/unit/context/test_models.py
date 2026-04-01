"""Tests for context models."""

from __future__ import annotations

from mozi.context.models import (
    BuiltContext,
    CompressionResult,
    CompressionStrategy,
    ContextConfig,
)


class TestCompressionStrategy:
    """Tests for CompressionStrategy enum."""

    def test_compression_strategy_values(self) -> None:
        """Test all compression strategy values exist."""
        assert CompressionStrategy.NONE.value == "none"
        assert CompressionStrategy.TRUNCATE.value == "truncate"
        assert CompressionStrategy.SUMMARIZE.value == "summarize"
        assert CompressionStrategy.MIXED.value == "mixed"


class TestContextConfig:
    """Tests for ContextConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ContextConfig()
        assert config.max_tokens == 100000
        assert config.compression_strategy == CompressionStrategy.MIXED
        assert config.system_prompt is None
        assert config.include_history is True
        assert config.include_memory is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ContextConfig(
            max_tokens=50000,
            compression_strategy=CompressionStrategy.TRUNCATE,
            system_prompt="Test prompt",
            include_history=False,
            include_memory=False,
        )
        assert config.max_tokens == 50000
        assert config.compression_strategy == CompressionStrategy.TRUNCATE
        assert config.system_prompt == "Test prompt"
        assert config.include_history is False
        assert config.include_memory is False

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = ContextConfig(max_tokens=50000)
        result = config.to_dict()
        assert result["max_tokens"] == 50000
        assert result["compression_strategy"] == "mixed"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {"max_tokens": 75000, "compression_strategy": "truncate"}
        config = ContextConfig.from_dict(data)
        assert config.max_tokens == 75000
        assert config.compression_strategy == CompressionStrategy.TRUNCATE

    def test_from_dict_defaults(self) -> None:
        """Test from_dict with missing values uses defaults."""
        data: dict[str, object] = {}
        config = ContextConfig.from_dict(data)
        assert config.max_tokens == 100000
        assert config.compression_strategy == CompressionStrategy.MIXED


class TestCompressionResult:
    """Tests for CompressionResult dataclass."""

    def test_compression_ratio_calculation(self) -> None:
        """Test compression ratio is calculated correctly."""
        result = CompressionResult(
            original_tokens=100,
            compressed_tokens=25,
            strategy_used=CompressionStrategy.TRUNCATE,
        )
        assert result.compression_ratio == 0.75

    def test_compression_ratio_zero_original(self) -> None:
        """Test compression ratio with zero original tokens."""
        result = CompressionResult(
            original_tokens=0,
            compressed_tokens=0,
            strategy_used=CompressionStrategy.NONE,
        )
        assert result.compression_ratio == 1.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = CompressionResult(
            original_tokens=100,
            compressed_tokens=50,
            strategy_used=CompressionStrategy.SUMMARIZE,
        )
        data = result.to_dict()
        assert data["original_tokens"] == 100
        assert data["compressed_tokens"] == 50
        assert data["strategy_used"] == "summarize"
        assert "compression_ratio" in data


class TestBuiltContext:
    """Tests for BuiltContext dataclass."""

    def test_default_values(self) -> None:
        """Test default built context values."""
        context = BuiltContext(system_prompt="Test")
        assert context.system_prompt == "Test"
        assert context.messages == []
        assert context.memory_results == []
        assert context.total_tokens == 0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = ContextConfig(max_tokens=50000)
        context = BuiltContext(
            system_prompt="Test prompt",
            messages=["User: Hello", "Assistant: Hi"],
            memory_results=["Memory: Test"],
            config=config,
            total_tokens=100,
        )
        data = context.to_dict()
        assert data["system_prompt"] == "Test prompt"
        assert len(data["messages"]) == 2
        assert len(data["memory_results"]) == 1

    def test_get_full_prompt(self) -> None:
        """Test getting full prompt string."""
        context = BuiltContext(
            system_prompt="System prompt",
            messages=["User: Hello", "Assistant: Hi"],
            memory_results=["Memory: Test"],
        )
        prompt = context.get_full_prompt()
        assert "System: System prompt" in prompt
        assert "User: Hello" in prompt
        assert "Memory: Test" in prompt

    def test_get_full_prompt_empty(self) -> None:
        """Test getting full prompt with minimal context."""
        context = BuiltContext(system_prompt="")
        prompt = context.get_full_prompt()
        assert prompt == ""

    def test_estimate_tokens(self) -> None:
        """Test token estimation."""
        context = BuiltContext(system_prompt="Test content")
        tokens = context.estimate_tokens("Test content here")
        assert tokens == 4  # len("Test content here") // 4 = 19 // 4 = 4
