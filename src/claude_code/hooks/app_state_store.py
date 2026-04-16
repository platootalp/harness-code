"""
AppStateStore - Full application state store integrating AsyncObservable and StateChangeHandler.

Combines the observable state layer with centralized side-effect handling,
providing a complete state management solution for the Claude Code CLI.

Migrated from src/state/AppStateStore.ts (TypeScript).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .handler import StateChangeHandler
from .observable import AsyncObservable

logger = logging.getLogger(__name__)


class AppStateStore:
    """
    Full application state store combining AsyncObservable with change handling.

    This is the main entry point for app-wide state management in the CLI.
    Integrates the observable layer with a StateChangeHandler for centralized
    side-effects (settings persistence, auth cache clearing, etc.).

    Example:
        store = AppStateStore()

        # Get current state
        state = store.get()

        # Update state synchronously
        store.set(lambda s: {**s, "count": s.get("count", 0) + 1})

        # Update state with async side-effects
        await store.set_async(lambda s: {**s, "loading": True})

        # Subscribe to all changes
        unsub = store.subscribe(lambda: print("changed!"))
        unsub()

        # Subscribe to specific key
        from .change_record import ChangeRecord

        unsub = store.subscribe_to_key(
            "settings",
            lambda record: print(f"settings changed to {record.new_value}")
        )
    """

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
        *,
        auto_checkpoint: bool = False,
    ) -> None:
        if initial_state is None:
            initial_state = self._default_state()

        self._change_handler = StateChangeHandler()
        self._register_default_handlers()

        self._observable = AsyncObservable[dict[str, Any]](
            initial_state,
            on_change=self._change_handler.handle_change,
        )
        self._auto_checkpoint = auto_checkpoint
        self._checkpoint_task: asyncio.Task[None] | None = None

    def _register_default_handlers(self) -> None:
        """Register the standard set of state change handlers."""
        self._change_handler.on_key_change("settings", self._settings_change_handler)
        self._change_handler.on_key_change(
            "permission_mode", self._permission_mode_handler
        )

    async def _settings_change_handler(
        self,
        old_settings: dict[str, Any] | None,
        new_settings: dict[str, Any] | None,
    ) -> None:
        """Handle settings changes - clear caches, re-apply env vars."""
        if old_settings is None or new_settings is None:
            return
        if old_settings == new_settings:
            return
        logger.debug("Settings changed, caches may need invalidation")

    async def _permission_mode_handler(
        self,
        old_mode: str | None,
        new_mode: str | None,
    ) -> None:
        """Handle permission mode changes."""
        if old_mode == new_mode:
            return
        logger.info(f"Permission mode changed: {old_mode} -> {new_mode}")

    # === Public API ===

    def get(self) -> dict[str, Any]:
        """Get current state synchronously."""
        return self._observable.get()

    async def get_async(self) -> dict[str, Any]:
        """Get current state asynchronously (with lock)."""
        return await self._observable.get_async()

    def set(
        self, updater: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        """Synchronous state update (no side-effects awaited)."""
        self._observable.set(updater)

    async def set_async(
        self, updater: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        """Async state update with side-effect handling."""
        await self._observable.set_async(updater)

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to any state change."""
        return self._observable.subscribe(listener)

    def subscribe_to_key(
        self, key: str, listener: Callable[..., None]
    ) -> Callable[[], None]:
        """Subscribe to changes for a specific key."""
        return self._observable.subscribe_to_key(key, listener)

    @property
    def version(self) -> int:
        """State version for cache invalidation."""
        return self._observable.version

    @property
    def handler(self) -> StateChangeHandler:
        """Access the underlying change handler for custom handler registration."""
        return self._change_handler

    @property
    def observable(self) -> AsyncObservable[dict[str, Any]]:
        """Access the underlying observable store."""
        return self._observable

    def _default_state(self) -> dict[str, Any]:
        """Return default app state (matches TypeScript getDefaultAppState)."""
        return {
            "settings": {},
            "verbose": False,
            "mainLoopModel": None,
            "mainLoopModelForSession": None,
            "statusLineText": None,
            "expandedView": "none",
            "isBriefOnly": False,
            "showTeammateMessagePreview": False,
            "selectedIPAgentIndex": -1,
            "coordinatorTaskIndex": -1,
            "viewSelectionMode": "none",
            "footerSelection": None,
            "kairosEnabled": False,
            "remoteSessionUrl": None,
            "remoteConnectionStatus": "connecting",
            "remoteBackgroundTaskCount": 0,
            "replBridgeEnabled": False,
            "replBridgeExplicit": False,
            "replBridgeOutboundOnly": False,
            "replBridgeConnected": False,
            "replBridgeSessionActive": False,
            "replBridgeReconnecting": False,
            "replBridgeConnectUrl": None,
            "replBridgeSessionUrl": None,
            "replBridgeEnvironmentId": None,
            "replBridgeSessionId": None,
            "replBridgeError": None,
            "replBridgeInitialName": None,
            "showRemoteCallout": False,
            "toolPermissionContext": {},
            "agent": None,
            "agentDefinitions": {"activeAgents": [], "allAgents": []},
            "fileHistory": {
                "snapshots": [],
                "trackedFiles": set(),
                "snapshotSequence": 0,
            },
            "attribution": {},
            "tasks": {},
            "agentNameRegistry": {},
            "mcp": {
                "clients": [],
                "tools": [],
                "commands": [],
                "resources": {},
                "pluginReconnectKey": 0,
            },
            "plugins": {
                "enabled": [],
                "disabled": [],
                "commands": [],
                "errors": [],
                "installationStatus": {"marketplaces": [], "plugins": []},
                "needsRefresh": False,
            },
            "todos": {},
            "remoteAgentTaskSuggestions": [],
            "notifications": {"current": None, "queue": []},
            "elicitation": {"queue": []},
            "thinkingEnabled": None,
            "promptSuggestionEnabled": True,
            "sessionHooks": {},
            "inbox": {"messages": []},
            "workerSandboxPermissions": {"queue": [], "selectedIndex": 0},
            "pendingWorkerRequest": None,
            "pendingSandboxRequest": None,
            "promptSuggestion": {
                "text": None,
                "promptId": None,
                "shownAt": 0,
                "acceptedAt": 0,
                "generationRequestId": None,
            },
            "speculation": {"status": "idle"},
            "speculationSessionTimeSavedMs": 0,
            "skillImprovement": {"suggestion": None},
            "authVersion": 0,
            "initialMessage": None,
            "effortValue": None,
            "activeOverlays": set(),
            "fastMode": False,
        }
