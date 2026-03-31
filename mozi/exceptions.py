"""Mozi exceptions.

This module defines all custom exceptions used throughout the Mozi project.
All custom exceptions must inherit from MoziError.
"""

from __future__ import annotations


class MoziError(Exception):
    """Base exception for all Mozi errors.

    All custom exceptions in the project should inherit from this class.
    This follows the rule that custom exceptions must inherit from MoziError.
    """

    pass


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(MoziError):
    """Raised when there is a configuration-related error.

    This includes invalid configuration values, missing required settings,
    or configuration file parsing errors.
    """

    pass


# =============================================================================
# Session Errors
# =============================================================================


class SessionError(MoziError):
    """Raised when there is a session-related error.

    This includes session not found, session corruption,
    session state transitions, and session persistence errors.
    """

    pass


class SessionNotFoundError(SessionError):
    """Raised when a requested session does not exist."""

    pass


class SessionCorruptedError(SessionError):
    """Raised when a session's data is corrupted or cannot be parsed."""

    pass


class SessionExpiredError(SessionError):
    """Raised when attempting to use an expired session."""

    pass


# =============================================================================
# Model Errors
# =============================================================================


class ModelError(MoziError):
    """Raised when there is a model-related error.

    This includes model invocation failures, response parsing errors,
    and model configuration issues.
    """

    pass


class ModelInvocationError(ModelError):
    """Raised when a model API call fails."""

    pass


class ModelNotFoundError(ModelError):
    """Raised when a requested model is not available or not found."""

    pass


class InvalidRequestError(ModelError):
    """Raised when the request to the model is invalid."""

    pass


class ResponseParseError(ModelError):
    """Raised when the model's response cannot be parsed."""

    pass


class RateLimitError(ModelError):
    """Raised when the model API rate limit is exceeded."""

    pass


class AuthenticationError(ModelError):
    """Raised when authentication with the model provider fails."""

    pass


class CircuitBreakerOpenError(ModelError):
    """Raised when the circuit breaker is open and requests are blocked."""

    pass


# =============================================================================
# Tool Errors
# =============================================================================


class ToolError(MoziError):
    """Raised when there is a tool-related error.

    This includes tool not found, tool execution failures,
    and tool security violations.
    """

    pass


class ToolNotFoundError(ToolError):
    """Raised when a requested tool does not exist."""

    pass


class ToolExecutionError(ToolError):
    """Raised when a tool's execution fails."""

    pass


class ToolTimeoutError(ToolError):
    """Raised when a tool's execution times out."""

    pass


class SecurityViolationError(ToolError):
    """Raised when a tool operation violates security policies.

    This includes path traversal attempts, dangerous function calls,
    and permission denied errors.
    """

    pass


class PermissionDeniedError(SecurityViolationError):
    """Raised when a tool operation is denied due to permissions."""

    pass


# =============================================================================
# Context Errors
# =============================================================================


class ContextError(MoziError):
    """Raised when there is a context-related error.

    This includes context building failures, compression errors,
    and context window overflow.
    """

    pass


class ContextOverflowError(ContextError):
    """Raised when the context window exceeds its limit."""

    pass


class CompressionError(ContextError):
    """Raised when context compression fails."""

    pass


# =============================================================================
# Memory Errors
# =============================================================================


class MemoryError(MoziError):
    """Raised when there is a memory-related error.

    This includes memory storage failures, retrieval errors,
    and vector store issues.
    """

    pass


class MemoryNotFoundError(MemoryError):
    """Raised when requested memory does not exist."""

    pass


class VectorStoreError(MemoryError):
    """Raised when there is an error with the vector store."""

    pass


# =============================================================================
# Orchestrator Errors
# =============================================================================


class OrchestratorError(MoziError):
    """Raised when there is an orchestrator-related error.

    This includes task routing failures, worker execution errors,
    and ReAct loop issues.
    """

    pass


class TaskRoutingError(OrchestratorError):
    """Raised when task routing fails."""

    pass


class WorkerExecutionError(OrchestratorError):
    """Raised when a worker's execution fails."""

    pass


# =============================================================================
# Infrastructure Errors
# =============================================================================


class InfrastructureError(MoziError):
    """Raised when there is an infrastructure-related error.

    This includes database errors, event bus failures,
    and network issues.
    """

    pass


class DatabaseError(InfrastructureError):
    """Raised when there is a database operation error."""

    pass


class EventBusError(InfrastructureError):
    """Raised when there is an event bus error."""

    pass


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(MoziError):
    """Raised when input validation fails."""

    pass


# =============================================================================
# Execution Errors
# =============================================================================


class ExecutionError(MoziError):
    """Raised when there is a general execution error."""

    pass


class TimeoutError(ExecutionError):
    """Raised when an operation times out."""

    pass


class ResourceError(ExecutionError):
    """Raised when a resource (CPU, memory, disk) is exhausted."""

    pass
