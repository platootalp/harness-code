"""Mozi AI Coding Agent.

A coding agent that uses AI to help developers build software more efficiently.
"""

from mozi.exceptions import (
    AuthenticationError,
    CircuitBreakerOpenError,
    CompressionError,
    ConfigurationError,
    ContextError,
    ContextOverflowError,
    DatabaseError,
    EventBusError,
    ExecutionError,
    InfrastructureError,
    InvalidRequestError,
    MemoryError,
    MemoryNotFoundError,
    ModelError,
    ModelInvocationError,
    ModelNotFoundError,
    MoziError,
    OrchestratorError,
    PermissionDeniedError,
    RateLimitError,
    ResourceError,
    ResponseParseError,
    SecurityViolationError,
    SessionCorruptedError,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    TaskRoutingError,
    TimeoutError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    ValidationError,
    VectorStoreError,
    WorkerExecutionError,
)

__all__ = [
    # Base
    "MoziError",
    # Configuration
    "ConfigurationError",
    # Session
    "SessionError",
    "SessionNotFoundError",
    "SessionCorruptedError",
    "SessionExpiredError",
    # Model
    "ModelError",
    "ModelInvocationError",
    "ModelNotFoundError",
    "InvalidRequestError",
    "ResponseParseError",
    "RateLimitError",
    "AuthenticationError",
    "CircuitBreakerOpenError",
    # Tool
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "SecurityViolationError",
    "PermissionDeniedError",
    # Context
    "ContextError",
    "ContextOverflowError",
    "CompressionError",
    # Memory
    "MemoryError",
    "MemoryNotFoundError",
    "VectorStoreError",
    # Orchestrator
    "OrchestratorError",
    "TaskRoutingError",
    "WorkerExecutionError",
    # Infrastructure
    "InfrastructureError",
    "DatabaseError",
    "EventBusError",
    # General
    "ValidationError",
    "ExecutionError",
    "TimeoutError",
    "ResourceError",
]
