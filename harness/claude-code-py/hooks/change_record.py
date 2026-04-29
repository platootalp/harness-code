"""
ChangeRecord - Immutable record of a state change for key-specific listeners.

Records which key changed, the old and new values, and when the change occurred.
Used by AsyncObservable to notify key-specific subscribers.

Migrated from src/state/handlers.ts pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ChangeRecord:
    """
    Immutable record of a state change.

    Created by AsyncObservable when a key-specific subscription fires.
    Provides old_value, new_value, and timestamp for the change.

    Example:
        store.subscribe_to_key("settings", handle_settings_change)

        def handle_settings_change(record: ChangeRecord) -> None:
            print(f"settings changed from {record.old_value} to {record.new_value}")
            print(f"  at {record.timestamp}")
    """

    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime

    def __repr__(self) -> str:
        return (
            f"ChangeRecord(key={self.key!r}, "
            f"old={self.old_value!r}, new={self.new_value!r}, "
            f"ts={self.timestamp.isoformat()})"
        )
