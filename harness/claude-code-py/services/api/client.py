"""Async HTTP client with streaming support, timeout control, and retry mechanism.

TypeScript equivalent: src/services/api/client.ts (getAnthropicClient factory)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeout in seconds (matches TypeScript API_TIMEOUT_MS default of 600000)
DEFAULT_TIMEOUT = 600.0
# Default max retries for transient errors
DEFAULT_MAX_RETRIES = 3
# Default base delay for exponential backoff (seconds)
DEFAULT_BACKOFF_BASE = 1.0


class HTTPClient:
    """Async HTTP client with streaming support, timeout control, and retry mechanism.

    Features:
    - Streaming POST requests for SSE/streaming responses
    - Configurable timeout per-request or globally
    - Exponential backoff retry for transient errors
    - Context manager for lifecycle management
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Optional base URL for all requests.
            timeout: Default timeout in seconds for all requests.
            max_retries: Maximum number of retries for transient errors.
            backoff_base: Base delay for exponential backoff in seconds.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HTTPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url or "",
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _should_retry(self, status_code: int) -> bool:
        """Determine if a status code is retryable.

        Args:
            status_code: HTTP status code.

        Returns:
            True if the request should be retried.
        """
        # Retry on 429 (rate limit) and 5xx server errors
        return status_code == 429 or (status_code >= 500 and status_code < 600)

    async def _sleep_with_backoff(self, attempt: int) -> None:
        """Sleep with exponential backoff.

        Args:
            attempt: Current retry attempt (0-indexed).
        """
        delay = self.backoff_base * (2 ** attempt)
        await asyncio.sleep(delay)

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Send a POST request with optional streaming.

        Args:
            url: Request URL (appended to base_url if set).
            json: JSON body to send.
            data: Form data to send.
            headers: Additional headers.
            timeout: Request-specific timeout override.
            stream: If True, return streaming response; otherwise await full response.

        Returns:
            httpx.Response (streaming or complete depending on stream flag).

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On timeout.
            httpx.HTTPError: On other HTTP errors.
        """
        assert self._client is not None, "Client not initialized. Use context manager."

        request_headers = dict(headers) if headers else {}
        request_timeout = httpx.Timeout(timeout) if timeout is not None else None

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    # For streaming, we use the streaming context manager
                    response = await self._client.post(
                        url,
                        json=json,
                        data=data,
                        headers=request_headers,
                        timeout=request_timeout,
                    )
                    return response
                else:
                    response = await self._client.post(
                        url,
                        json=json,
                        data=data,
                        headers=request_headers,
                        timeout=request_timeout,
                    )

                # Check if we should retry
                if self._should_retry(response.status_code) and attempt < self.max_retries:
                    logger.warning(
                        "HTTP %d on %s, retrying (attempt %d/%d)",
                        response.status_code,
                        url,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep_with_backoff(attempt)
                    continue

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "Timeout on %s, retrying (attempt %d/%d)",
                        url,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "Network error on %s: %s, retrying (attempt %d/%d)",
                        url,
                        e,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

            except httpx.HTTPError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "HTTP error on %s: %s, retrying (attempt %d/%d)",
                        url,
                        e,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

        # Should not reach here, but just in case
        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Unexpected error in post retry loop")

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Send a GET request.

        Args:
            url: Request URL (appended to base_url if set).
            params: Query parameters.
            headers: Additional headers.
            timeout: Request-specific timeout override.

        Returns:
            httpx.Response.

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On timeout.
        """
        assert self._client is not None, "Client not initialized. Use context manager."

        request_headers = dict(headers) if headers else {}
        request_timeout = httpx.Timeout(timeout) if timeout is not None else None

        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=request_timeout,
                )

                if self._should_retry(response.status_code) and attempt < self.max_retries:
                    logger.warning(
                        "HTTP %d on %s, retrying (attempt %d/%d)",
                        response.status_code,
                        url,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep_with_backoff(attempt)
                    continue

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

            except httpx.HTTPError as e:
                last_exception = e
                if attempt < self.max_retries:
                    await self._sleep_with_backoff(attempt)
                else:
                    raise

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Unexpected error in get retry loop")

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Send a PUT request.

        Args:
            url: Request URL (appended to base_url if set).
            json: JSON body to send.
            data: Form data to send.
            headers: Additional headers.
            timeout: Request-specific timeout override.

        Returns:
            httpx.Response.

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On timeout.
        """
        assert self._client is not None, "Client not initialized. Use context manager."

        request_headers = dict(headers) if headers else {}
        request_timeout = httpx.Timeout(timeout) if timeout is not None else None

        response = await self._client.put(
            url,
            json=json,
            data=data,
            headers=request_headers,
            timeout=request_timeout,
        )
        return response

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Send a DELETE request.

        Args:
            url: Request URL (appended to base_url if set).
            headers: Additional headers.
            timeout: Request-specific timeout override.

        Returns:
            httpx.Response.

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On timeout.
        """
        assert self._client is not None, "Client not initialized. Use context manager."

        request_headers = dict(headers) if headers else {}
        request_timeout = httpx.Timeout(timeout) if timeout is not None else None

        response = await self._client.delete(
            url,
            headers=request_headers,
            timeout=request_timeout,
        )
        return response

    async def stream_post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming POST request that yields response chunks.

        This method is ideal for SSE (Server-Sent Events) and other
        streaming response formats.

        Args:
            url: Request URL (appended to base_url if set).
            json: JSON body to send.
            data: Form data to send.
            headers: Additional headers.
            timeout: Request-specific timeout override.

        Yields:
            Raw bytes from the response stream.

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On timeout.
        """
        assert self._client is not None, "Client not initialized. Use context manager."

        request_headers = dict(headers) if headers else {}
        request_timeout = httpx.Timeout(timeout) if timeout is not None else None

        async with self._client.stream(
            "POST",
            url,
            json=json,
            data=data,
            headers=request_headers,
            timeout=request_timeout,
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
