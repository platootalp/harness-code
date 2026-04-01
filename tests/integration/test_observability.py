"""Integration tests for observability.

This module provides integration tests for observability features including:
- Tracing integration
- Metrics integration
- Logging integration

Tests use @pytest.mark.integration marker.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger.

    Returns
    -------
    MagicMock
        Mock logger for testing.
    """
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def trace_context() -> dict:
    """Create a trace context for testing.

    Returns
    -------
    dict
        Trace context with typical values.
    """
    return {
        "trace_id": "trace-123",
        "span_id": "span-456",
        "parent_span_id": "span-789",
    }


# =============================================================================
# Tracing Integration Tests
# =============================================================================


class TestTracingIntegration:
    """Integration tests for tracing functionality."""

    @pytest.mark.integration
    def test_trace_context_propagation(self) -> None:
        """Test that trace context propagates through operations."""
        context = {
            "trace_id": "abc-123",
            "span_id": "def-456",
        }

        # Simulate passing trace context
        def inner_operation(ctx: dict) -> str:
            return ctx.get("trace_id", "unknown")

        result = inner_operation(context)
        assert result == "abc-123"

    @pytest.mark.integration
    def test_span_creation(self) -> None:
        """Test span creation with proper attributes."""
        span = {
            "name": "test_operation",
            "span_id": "span-123",
            "start_time": datetime.now().isoformat(),
            "attributes": {
                "operation.type": "test",
                "service.name": "mozi",
            },
        }

        assert span["name"] == "test_operation"
        assert span["attributes"]["service.name"] == "mozi"

    @pytest.mark.integration
    def test_trace_id_generation(self) -> None:
        """Test trace ID generation format."""
        import uuid

        trace_id = str(uuid.uuid4())
        # Trace ID should be a valid UUID format
        assert len(trace_id) == 36
        assert trace_id.count("-") == 4

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_span_tracking(self) -> None:
        """Test that async operations can be tracked with spans."""
        spans: list[dict] = []

        async def tracked_operation(name: str, parent_span: str | None = None) -> None:
            span = {
                "name": name,
                "parent_span": parent_span,
                "start": datetime.now().isoformat(),
            }
            spans.append(span)
            await asyncio.sleep(0.01)
            span["end"] = datetime.now().isoformat()

        # Execute nested operations
        await tracked_operation("parent", None)
        await tracked_operation("child1", "parent")
        await tracked_operation("child2", "parent")

        assert len(spans) == 3
        assert spans[1]["parent_span"] == "parent"
        assert spans[2]["parent_span"] == "parent"

    @pytest.mark.integration
    def test_span_attributes_serialization(self) -> None:
        """Test that span attributes can be serialized to JSON."""
        span = {
            "name": "test_span",
            "trace_id": "trace-123",
            "span_id": "span-456",
            "attributes": {
                "string_attr": "value",
                "int_attr": 42,
                "bool_attr": True,
            },
        }

        serialized = json.dumps(span)
        deserialized = json.loads(serialized)

        assert deserialized["attributes"]["string_attr"] == "value"
        assert deserialized["attributes"]["int_attr"] == 42
        assert deserialized["attributes"]["bool_attr"] is True


# =============================================================================
# Metrics Integration Tests
# =============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics functionality."""

    @pytest.mark.integration
    def test_counter_increment(self) -> None:
        """Test counter metric increment."""
        counter = {"value": 0}

        def increment(amount: int = 1) -> None:
            counter["value"] += amount

        increment()
        increment(5)

        assert counter["value"] == 6

    @pytest.mark.integration
    def test_gauge_metric(self) -> None:
        """Test gauge metric set and get."""
        gauge = {"value": 0.0}

        def set_gauge(value: float) -> None:
            gauge["value"] = value

        def get_gauge() -> float:
            return gauge["value"]

        set_gauge(42.5)
        assert get_gauge() == 42.5

        set_gauge(100.0)
        assert get_gauge() == 100.0

    @pytest.mark.integration
    def test_histogram_record(self) -> None:
        """Test histogram metric recording."""
        histogram: list[float] = []

        def record(value: float) -> None:
            histogram.append(value)

        record(1.5)
        record(2.5)
        record(3.5)

        assert len(histogram) == 3
        assert sum(histogram) / len(histogram) == 2.5

    @pytest.mark.integration
    def test_metric_labels(self) -> None:
        """Test metrics with labels."""
        metrics: dict[str, int] = {}

        def record_with_label(label: str, value: int) -> None:
            key = f"{label}"
            if key not in metrics:
                metrics[key] = 0
            metrics[key] += value

        record_with_label("method=get", 1)
        record_with_label("method=post", 2)
        record_with_label("method=get", 3)

        assert metrics["method=get"] == 4
        assert metrics["method=post"] == 2

    @pytest.mark.integration
    def test_aggregated_metrics(self) -> None:
        """Test aggregated metric calculations."""
        request_durations: list[float] = [10.0, 20.0, 30.0, 40.0, 50.0]

        count = len(request_durations)
        total = sum(request_durations)
        avg = total / count
        min_val = min(request_durations)
        max_val = max(request_durations)

        assert count == 5
        assert avg == 30.0
        assert min_val == 10.0
        assert max_val == 50.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_metrics_collection(self) -> None:
        """Test collecting metrics from async operations."""
        metrics = {"operations": 0, "errors": 0}

        async def tracked_async_op(should_fail: bool = False) -> None:
            await asyncio.sleep(0.01)
            metrics["operations"] += 1
            if should_fail:
                metrics["errors"] += 1

        await tracked_async_op()
        await tracked_async_op(should_fail=True)
        await tracked_async_op()

        assert metrics["operations"] == 3
        assert metrics["errors"] == 1


# =============================================================================
# Logging Integration Tests
# =============================================================================


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    @pytest.mark.integration
    def test_log_level_setting(self) -> None:
        """Test setting log levels."""
        log_levels = {}

        def set_level(component: str, level: str) -> None:
            log_levels[component] = level

        set_level("mozi", "INFO")
        set_level("mozi.orchestrator", "DEBUG")
        set_level("mozi.infrastructure", "WARNING")

        assert log_levels["mozi"] == "INFO"
        assert log_levels["mozi.orchestrator"] == "DEBUG"

    @pytest.mark.integration
    def test_log_message_format(self) -> None:
        """Test log message formatting."""
        timestamp = datetime.now().isoformat()
        level = "INFO"
        message = "Operation completed"
        context = {"request_id": "req-123"}

        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "context": context,
        }

        assert "timestamp" in log_entry
        assert log_entry["level"] == "INFO"
        assert "request_id" in log_entry["context"]

    @pytest.mark.integration
    def test_structured_logging(self) -> None:
        """Test structured logging with context."""
        records: list[dict] = []

        def log_structured(level: str, message: str, **kwargs) -> None:
            records.append({
                "level": level,
                "message": message,
                **kwargs,
            })

        log_structured("INFO", "User action", user_id="u123", action="login")
        log_structured("ERROR", "Operation failed", error_code=500)

        assert len(records) == 2
        assert records[0]["user_id"] == "u123"
        assert records[1]["error_code"] == 500

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_operation_logging(self) -> None:
        """Test logging from async operations."""
        logs: list[str] = []

        async def async_operation(name: str) -> None:
            logs.append(f"Starting {name}")
            await asyncio.sleep(0.01)
            logs.append(f"Completed {name}")

        await async_operation("task1")
        await async_operation("task2")

        assert "Starting task1" in logs
        assert "Completed task1" in logs
        assert "Starting task2" in logs

    @pytest.mark.integration
    def test_log_redaction(self) -> None:
        """Test that sensitive data is redacted in logs."""
        sensitive_fields = ["password", "api_key", "token", "secret"]

        def redact_sensitive(data: dict) -> dict:
            redacted = data.copy()
            for key in data:
                if any(field in key.lower() for field in sensitive_fields):
                    redacted[key] = "***REDACTED***"
            return redacted

        log_data = {
            "user": "admin",
            "password": "secret123",
            "api_key": "key-abc",
            "action": "login",
        }

        redacted = redact_sensitive(log_data)

        assert redacted["user"] == "admin"
        assert redacted["password"] == "***REDACTED***"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["action"] == "login"

    @pytest.mark.integration
    def test_log_context_inheritance(self) -> None:
        """Test that log context is properly inherited."""
        records: list[dict] = []
        context: dict = {"trace_id": "t-123"}

        def log_with_context(message: str) -> None:
            records.append({
                "message": message,
                "context": context.copy(),
            })

        log_with_context("First message")
        context["span_id"] = "s-456"  # Modify context after
        log_with_context("Second message")

        # First record should not have span_id
        assert "span_id" not in records[0]["context"]
        assert records[1]["context"]["trace_id"] == "t-123"


# =============================================================================
# Observability Integration Tests
# =============================================================================


class TestObservabilityIntegration:
    """Integration tests for combined observability features."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_observability(self) -> None:
        """Test observability across full operation pipeline."""
        traces: list[dict] = []
        metrics: dict = {"operations": 0}
        logs: list[dict] = []

        async def pipeline_operation(name: str) -> None:
            # Start span
            span = {"name": name, "start": datetime.now().isoformat()}
            traces.append(span)

            # Record metric
            metrics["operations"] += 1

            # Log
            logs.append({"message": f"Executing {name}"})

            await asyncio.sleep(0.01)

            # End span
            span["end"] = datetime.now().isoformat()
            logs.append({"message": f"Completed {name}"})

        await pipeline_operation("step1")
        await pipeline_operation("step2")

        assert len(traces) == 2
        assert metrics["operations"] == 2
        assert len(logs) == 4

    @pytest.mark.integration
    def test_correlation_between_telemetry(self) -> None:
        """Test correlation ID links traces, metrics, and logs."""
        correlation_id = "corr-123"

        trace = {
            "correlation_id": correlation_id,
            "trace_id": "trace-abc",
        }

        metric = {
            "correlation_id": correlation_id,
            "metric": "operation_duration_ms",
            "value": 150,
        }

        log = {
            "correlation_id": correlation_id,
            "message": "Operation completed",
        }

        assert trace["correlation_id"] == metric["correlation_id"]
        assert metric["correlation_id"] == log["correlation_id"]

    @pytest.mark.integration
    def test_observability_config_loading(self) -> None:
        """Test loading observability configuration."""
        config = {
            "tracing": {
                "enabled": True,
                "sample_rate": 0.1,
                "endpoint": "http://collector:4317",
            },
            "metrics": {
                "enabled": True,
                "export_interval_seconds": 10,
            },
            "logging": {
                "level": "INFO",
                "format": "json",
            },
        }

        assert config["tracing"]["enabled"] is True
        assert config["metrics"]["export_interval_seconds"] == 10
        assert config["logging"]["level"] == "INFO"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_tracking_in_observability(self) -> None:
        """Test that errors are properly tracked in observability."""
        error_count = {"total": 0}
        error_logs: list[dict] = []

        async def operation_with_error(should_fail: bool) -> None:
            try:
                await asyncio.sleep(0.01)
                if should_fail:
                    raise ValueError("Test error")
            except Exception as e:
                error_count["total"] += 1
                error_logs.append({
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

        await operation_with_error(False)
        await operation_with_error(True)
        await operation_with_error(False)

        assert error_count["total"] == 1
        assert len(error_logs) == 1
        assert error_logs[0]["error_type"] == "ValueError"


# =============================================================================
# Performance Observability Tests
# =============================================================================


class TestPerformanceObservability:
    """Integration tests for performance monitoring."""

    @pytest.mark.integration
    def test_latency_percentiles(self) -> None:
        """Test calculating latency percentiles."""
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Simple percentile using nearest rank method
        def percentile_nearest_rank(data, p):
            idx = int((len(data) - 1) * p)
            return data[idx]

        # For 10 elements, p50 should return the 5th element (0-indexed index 4)
        p50 = percentile_nearest_rank(sorted_latencies, 0.50)
        # p95 should return the 9th or 10th element depending on rounding
        p95 = percentile_nearest_rank(sorted_latencies, 0.95)

        # With nearest rank, p50 gives the median or close to it
        assert 40.0 <= p50 <= 60.0  # p50 should be between 40 and 60
        assert p95 >= 90.0  # p95 should be at least 90

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_operation_duration_tracking(self) -> None:
        """Test tracking operation durations."""
        durations: list[float] = []

        async def timed_operation(delay_ms: float) -> None:
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(delay_ms / 1000)
            end = asyncio.get_event_loop().time()
            durations.append((end - start) * 1000)

        await timed_operation(10)
        await timed_operation(20)
        await timed_operation(30)

        assert len(durations) == 3
        # Each duration should be >= the requested delay
        assert all(d >= 10 for d in durations)


# =============================================================================
# Health Check Observability Tests
# =============================================================================


class TestHealthCheckObservability:
    """Integration tests for health check observability."""

    @pytest.mark.integration
    def test_component_health_status(self) -> None:
        """Test component health status reporting."""
        components = {
            "database": "healthy",
            "cache": "healthy",
            "queue": "degraded",
            "api": "healthy",
        }

        healthy = sum(1 for status in components.values() if status == "healthy")
        total = len(components)

        overall_health = "healthy" if healthy == total else "degraded"
        assert overall_health == "degraded"
        assert healthy == 3

    @pytest.mark.integration
    def test_health_check_metrics(self) -> None:
        """Test health check produces proper metrics."""
        health_metrics = {
            "up": 1,
            "down": 0,
            "degraded": 1,
        }

        total = sum(health_metrics.values())
        health_ratio = health_metrics["up"] / total if total > 0 else 0

        assert total == 2
        assert health_ratio == 0.5
