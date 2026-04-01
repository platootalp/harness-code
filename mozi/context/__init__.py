"""Context module for Mozi.

Provides context management capabilities including:
- Context building from multiple sources
- Context window management
- Context compression
- Context offloading
- Context isolation for multi-agent scenarios
"""

from __future__ import annotations

from mozi.context.builder import ContextBuilder
from mozi.context.compactor import Compactor
from mozi.context.isolator import IsolationResult, Isolator
from mozi.context.models import (
    BuiltContext,
    CompressionResult,
    CompressionStrategy,
    ContextConfig,
)
from mozi.context.offloader import OffloadEntry, Offloader
from mozi.context.window import WindowManager, WindowSnapshot

__all__ = [
    "BuiltContext",
    "CompressionResult",
    "CompressionStrategy",
    "ContextBuilder",
    "ContextConfig",
    "Compactor",
    "IsolationResult",
    "Isolator",
    "OffloadEntry",
    "Offloader",
    "WindowManager",
    "WindowSnapshot",
]
