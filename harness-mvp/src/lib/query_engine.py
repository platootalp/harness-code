"""QueryEngine - handles query lifecycle."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from ..state.app_state import AppState, Message
from ..tools.base import ToolContext
from .api.client import APIClient
from .permissions import check_permission


@dataclass
class ToolCall:
    name: str
    input: dict


@dataclass
class StreamEvent:
    type: str  # 'assistant' | 'tool_use' | 'tool_result' | 'done' | 'error'
    data: Any


class QueryEngine:
    """Query lifecycle manager."""

    def __init__(
        self,
        app_state: AppState,
        api_client: APIClient,
    ):
        self.app_state = app_state
        self.api_client = api_client

    async def submit_message(
        self,
        prompt: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a user message and yield stream events."""
        # Add user message
        self.app_state.messages.append(Message(role='user', content=prompt))

        # Build API messages
        api_messages = [
            {'role': m.role, 'content': m.content}
            for m in self.app_state.messages
        ]

        # Build system prompt
        system = self._build_system_prompt()

        # Build tools
        tools = self._build_tools()

        try:
            async for event in self.api_client.stream(
                model=self.app_state.model,
                messages=api_messages,
                tools=tools,
                system=system,
            ):
                if event['type'] == 'content':
                    yield StreamEvent(type='assistant', data=event['text'])
                elif event['type'] == 'message':
                    # Process tool uses from final message
                    msg = event['message']
                    for block in msg.content:
                        if hasattr(block, 'type') and block.type == 'tool_use':
                            yield StreamEvent(
                                type='tool_use',
                                data=ToolCall(
                                    name=block.name,
                                    input=block.input,
                                )
                            )
                    yield StreamEvent(type='done', data=msg.content)

        except Exception as e:
            yield StreamEvent(type='error', data=str(e))

    def _build_system_prompt(self) -> str:
        """Build system prompt."""
        return """You are a helpful CLI assistant. You have access to tools:
- Bash: execute shell commands
- FileRead: read files
- FileEdit: edit files
- Grep: search code

Use tools when needed to help the user."""

    def _build_tools(self) -> list[dict]:
        """Build tool definitions for API."""
        return [
            {
                'name': 'Bash',
                'description': 'Run a shell command',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'command': {'type': 'string', 'description': 'The command to execute'},
                        'timeout': {'type': 'integer', 'description': 'Timeout in seconds', 'default': 30},
                    },
                    'required': ['command'],
                },
            },
            {
                'name': 'FileRead',
                'description': 'Read a file',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string', 'description': 'Path to file'},
                        'limit': {'type': 'integer', 'description': 'Max lines'},
                    },
                    'required': ['file_path'],
                },
            },
            {
                'name': 'FileEdit',
                'description': 'Edit a file',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string'},
                        'old_string': {'type': 'string'},
                        'new_string': {'type': 'string'},
                    },
                    'required': ['file_path', 'old_string', 'new_string'],
                },
            },
            {
                'name': 'Grep',
                'description': 'Search for pattern in files',
                'input_schema': {
                    'type': 'object',
                    'properties': {
                        'pattern': {'type': 'string'},
                        'path': {'type': 'string', 'default': '.'},
                        'case_sensitive': {'type': 'boolean', 'default': True},
                    },
                    'required': ['pattern'],
                },
            },
        ]
