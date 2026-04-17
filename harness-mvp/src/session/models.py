"""Session and TokenUsage data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TokenUsage:
    """Token usage tracking for a session."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, prompt: int = 0, completion: int = 0, cost: float = 0.0) -> None:
        """Add token usage from a single LLM call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.cost_usd += cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenUsage:
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
        )


@dataclass
class Session:
    """Session model - represents an agentic work session."""
    id: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    # Status: active, paused, completed, archived
    status: str = "active"

    # Associated data
    task_ids: list[str] = field(default_factory=list)
    agent_ids: list[str] = field(default_factory=list)
    message_thread_id: str | None = None

    # Statistics
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    tool_calls: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "status": self.status,
            "task_ids": self.task_ids,
            "agent_ids": self.agent_ids,
            "message_thread_id": self.message_thread_id,
            "token_usage": self.token_usage.to_dict(),
            "tool_calls": self.tool_calls,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        updated_at = data["updated_at"]
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        return cls(
            id=data["id"],
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
            status=data.get("status", "active"),
            task_ids=data.get("task_ids", []),
            agent_ids=data.get("agent_ids", []),
            message_thread_id=data.get("message_thread_id"),
            token_usage=TokenUsage.from_dict(data.get("token_usage", {})),
            tool_calls=data.get("tool_calls", 0),
            errors=data.get("errors", 0),
        )
