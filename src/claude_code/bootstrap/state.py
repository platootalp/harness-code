"""
Bootstrap state module - re-exports from __init__ for backwards compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ..bootstrap import (
    get_original_cwd,
    get_project_root,
    is_app_initialized,
    set_app_initialized,
    set_original_cwd,
    set_project_root,
)

__all__ = [
    "set_original_cwd",
    "get_original_cwd",
    "is_app_initialized",
    "set_app_initialized",
    "get_project_root",
    "set_project_root",
]
