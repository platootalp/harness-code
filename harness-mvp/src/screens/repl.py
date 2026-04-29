"""REPL screen - main interactive UI."""
from __future__ import annotations

import asyncio
import sys
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from ..commands import find_command
from ..lib.api.client import APIClient
from ..lib.query_engine import QueryEngine, StreamEvent
from ..state.app_state import AppState, Message
from ..state.hooks import use_app_state, use_set_app_state
from ..tools import get_tools


class REPL:
    """Main REPL interface."""

    def __init__(self, app_state: AppState, set_app_state: Callable):
        self.app_state = app_state
        self.set_app_state = set_app_state
        self.session = PromptSession(history=InMemoryHistory())
        self.api_client = APIClient()
        self.query_engine = QueryEngine(app_state, self.api_client)

    async def run(self) -> None:
        """Main REPL loop."""
        print("MVP AI CLI - Type /help for commands, /quit to exit\n")

        while True:
            try:
                # Get user input
                user_input = await self.session.prompt_async("> ")
                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith('/'):
                    result = await self._handle_command(user_input)
                    if result is False:  # quit
                        break
                    print(result)
                    continue

                # Handle regular message
                await self._handle_message(user_input)

            except KeyboardInterrupt:
                print("\nUse /quit to exit")
                continue
            except EOFError:
                break

    async def _handle_command(self, user_input: str) -> str | bool:
        """Handle a slash command."""
        parts = user_input[1:].split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        if cmd_name == 'quit':
            return False

        cmd = find_command(cmd_name)
        if not cmd:
            return f"Unknown command: /{cmd_name}"

        if cmd['command_type'] == 'local':
            ctx = {'cwd': self.app_state.cwd}
            result = cmd['execute'](args, ctx)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        elif cmd['command_type'] == 'prompt':
            # Execute prompt command and add result to messages
            ctx = {'cwd': self.app_state.cwd}
            prompts = cmd['get_prompt_for_command'](args, ctx)
            if asyncio.iscoroutine(prompts):
                prompts = await prompts
            for prompt in prompts:
                self.app_state.messages.append(
                    Message(role='user', content=prompt)
                )
            # Then process with AI
            await self._handle_message(prompts[0])
            return ""

        return f"Command /{cmd_name} not implemented"

    async def _handle_message(self, user_input: str) -> None:
        """Handle a regular message to the AI."""
        # Add user message
        self.app_state.messages.append(Message(role='user', content=user_input))
        self.set_app_state(lambda s: s)  # Trigger re-render

        # Process with QueryEngine
        response_text = []
        self.app_state.is_loading = True
        self.set_app_state(lambda s: s)

        try:
            async for event in self.query_engine.submit_message(user_input):
                if event.type == 'assistant':
                    response_text.append(event.data)
                    print(event.data, end='', flush=True)
                elif event.type == 'done':
                    print()
                elif event.type == 'error':
                    print(f"\nError: {event.data}", file=sys.stderr)

            # Add assistant response
            if response_text:
                self.app_state.messages.append(
                    Message(role='assistant', content=''.join(response_text))
                )

        finally:
            self.app_state.is_loading = False
            self.set_app_state(lambda s: s)
