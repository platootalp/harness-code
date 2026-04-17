"""
Plugin hooks subsystem.

Provides hook definitions and the hook manager for plugin lifecycle events.
"""

from .definitions import (
    HookDefinition,
    HookEventType,
    HookType,
)
from .manager import HookManager

__all__ = [
    "HookDefinition",
    "HookEventType",
    "HookManager",
    "HookType",
]
