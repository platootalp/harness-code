"""Custom exceptions for the Mozi AI Coding Agent."""


class MoziError(Exception):
    """Base exception for all Mozi errors."""

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


class ConfigurationError(MoziError):
    """Raised when there's a configuration error."""

    pass


class SessionError(MoziError):
    """Raised when there's a session-related error."""

    pass
