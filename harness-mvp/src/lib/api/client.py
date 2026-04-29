"""Anthropic API client with custom endpoint support."""
from __future__ import annotations

import os
from typing import AsyncGenerator

import httpx
from anthropic import AsyncAnthropic
from anthropic._client import AsyncAnthropic as SyncAnthropic


class APIClient:
    """Anthropic API client with custom endpoint support."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_ms: int | None = None,
    ):
        # Get config from env or use provided
        auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', api_key)
        self.base_url = base_url or os.environ.get(
            'ANTHROPIC_BASE_URL', 'https://api.anthropic.com'
        )
        timeout_ms = timeout_ms or int(os.environ.get('API_TIMEOUT_MS', '300000'))

        # Create httpx client with auth header and custom base URL
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=timeout_ms / 1000,
        )

        # Create SDK client - use base_url override via environment
        # The SDK checks env vars first, so we set them
        env_base = os.environ.get('ANTHROPIC_BASE_URL')
        if env_base:
            os.environ['ANTHROPIC_BASE_URL'] = env_base

        # Create client with httpx client (SDK will use it for transport)
        self.client = AsyncAnthropic(
            http_client=self.http_client,
            api_key=auth_token,
        )

    async def stream(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream a response from the API."""
        async with self.client.messages.stream(
            model=model,
            max_tokens=4096,
            messages=messages,
            tools=tools,
            system=system,
        ) as stream:
            async for event in stream:
                # Handle content block delta
                if hasattr(event, 'type') and event.type == 'content_block_delta':
                    delta = getattr(event, 'delta', None)
                    if delta:
                        # Text content
                        if hasattr(delta, 'text'):
                            yield {'type': 'content', 'text': delta.text}
                        # Thinking content (skip)
                        elif hasattr(delta, 'thinking'):
                            pass
                # Message done
                elif hasattr(event, 'type') and event.type == 'message':
                    yield {'type': 'message', 'message': event}
                # Message delta (skip)
                elif hasattr(event, 'type') and event.type == 'message_delta':
                    pass

            # Get final message
            try:
                final = await stream.get_final_message()
                yield {'type': 'message', 'message': final}
            except Exception:
                pass

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


def get_api_client() -> APIClient:
    """Get configured API client from environment."""
    return APIClient()
