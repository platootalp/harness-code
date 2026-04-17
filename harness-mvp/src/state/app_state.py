"""AppState type definition."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _get_default_model() -> str:
    return os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')


@dataclass
class Message:
    role: str  # 'user' | 'assistant' | 'tool'
    content: str
    tool_name: str | None = None


@dataclass
class PermissionRule:
    source: str  # 'user' | 'project' | 'builtin'
    behavior: str  # 'allow' | 'deny' | 'ask'
    tool_name: str
    pattern: str | None = None


@dataclass
class PermissionContext:
    mode: str = 'default'  # 'default' | 'bypass' | 'ask'
    always_allow: list[PermissionRule] = field(default_factory=list)
    always_deny: list[PermissionRule] = field(default_factory=list)


@dataclass
class PermissionResult:
    behavior: str  # 'allow' | 'deny' | 'ask'
    reason: str | None = None
    updated_input: Any = None


@dataclass
class AppState:
    messages: list[Message] = field(default_factory=list)
    is_loading: bool = False
    error: str | None = None
    model: str = field(default_factory=_get_default_model)
    permission_context: PermissionContext = field(default_factory=PermissionContext)
    # Tool state
    tools: list[Any] = field(default_factory=list)
    # Command state
    commands: list[Any] = field(default_factory=list)
    cwd: str = ''
