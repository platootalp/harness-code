"""REPL launcher."""
from __future__ import annotations

import asyncio
from pathlib import Path

from .screens.repl import REPL
from .state.app_state import AppState
from .state.hooks import init_store
from .state.store import create_store


def launch_repl() -> None:
    """Launch the REPL."""
    # Create initial state
    from .tools import get_tools
    from .commands import get_commands

    initial_state = AppState(
        cwd=str(Path.cwd()),
        tools=get_tools(),
        commands=get_commands(),
    )

    # Create store
    store = create_store(initial_state)
    init_store(store)

    # Run REPL
    repl = REPL(initial_state, store.set_state)
    asyncio.run(repl.run())
