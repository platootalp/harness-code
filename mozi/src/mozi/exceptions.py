"""Custom exceptions for the Mozi AI Coding Agent."""


class MoziError(Exception):
    """Base exception for all Mozi errors."""

    pass


class ConfigurationError(MoziError):
    """Raised when there's a configuration error."""

    pass


class SessionError(MoziError):
    """Raised when there's a session-related error."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""

    pass


class SessionCorruptedError(SessionError):
    """Raised when a session is corrupted."""

    pass


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""

    pass


class ModelError(MoziError):
    """Base exception for model-related errors."""

    pass


class ModelInvocationError(ModelError):
    """Raised when model invocation fails."""

    pass


class ModelNotFoundError(ModelError):
    """Raised when a model is not found."""

    pass


class InvalidRequestError(ModelError):
    """Raised when request is invalid."""

    pass


class ResponseParseError(ModelError):
    """Raised when response parsing fails."""

    pass


class RateLimitError(ModelError):
    """Raised when rate limit is exceeded."""

    pass


class AuthenticationError(MoziError):
    """Raised when authentication fails."""

    pass


class CircuitBreakerOpenError(MoziError):
    """Raised when circuit breaker is open."""

    pass


class ToolError(MoziError):
    """Base exception for tool-related errors."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class ToolTimeoutError(ToolError):
    """Raised when tool execution times out."""

    pass


class SecurityViolationError(MoziError):
    """Raised when a security violation is detected."""

    pass


class PermissionDeniedError(MoziError):
    """Raised when permission is denied."""

    pass


class ContextError(MoziError):
    """Base exception for context-related errors."""

    pass


class ContextOverflowError(ContextError):
    """Raised when context overflows its limit."""

    pass


class CompressionError(ContextError):
    """Raised when compression fails."""

    pass


class MemoryError(MoziError):
    """Base exception for memory-related errors."""

    pass


class MemoryNotFoundError(MemoryError):
    """Raised when a requested memory block is not found."""

    pass


class VectorStoreError(MoziError):
    """Raised when there's an error with the vector store."""

    pass


class OrchestratorError(MoziError):
    """Base exception for orchestrator errors."""

    pass


class TaskRoutingError(OrchestratorError):
    """Raised when task routing fails."""

    pass


class WorkerExecutionError(OrchestratorError):
    """Raised when worker execution fails."""

    pass


class InfrastructureError(MoziError):
    """Base exception for infrastructure errors."""

    pass


class DatabaseError(InfrastructureError):
    """Raised when database operation fails."""

    pass


class EventBusError(InfrastructureError):
    """Raised when event bus operation fails."""

    pass


class ValidationError(MoziError):
    """Raised when validation fails."""

    pass


class ExecutionError(MoziError):
    """Raised when execution fails."""

    pass


class TimeoutError(MoziError):
    """Raised when operation times out."""

    pass


class ResourceError(MoziError):
    """Raised when resource is not available."""

    pass
