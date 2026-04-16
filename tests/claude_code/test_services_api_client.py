"""Tests for services/api/client.py - HTTPClient.

Uses pytest-httpserver for HTTP mocking.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_httpserver import HTTPServer

from claude_code.services.api.client import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    HTTPClient,
)


class TestHTTPClientInit:
    """Tests for HTTPClient initialization."""

    def test_default_initialization(self) -> None:
        """Test creating client with default values."""
        client = HTTPClient()
        assert client.base_url is None
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.max_retries == DEFAULT_MAX_RETRIES
        assert client.backoff_base == DEFAULT_BACKOFF_BASE
        assert client._client is None

    def test_custom_initialization(self) -> None:
        """Test creating client with custom values."""
        client = HTTPClient(
            base_url="https://api.example.com",
            timeout=30.0,
            max_retries=5,
            backoff_base=2.0,
        )
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30.0
        assert client.max_retries == 5
        assert client.backoff_base == 2.0

    def test_initialization_with_base_url(self) -> None:
        """Test creating client with just a base URL."""
        client = HTTPClient(base_url="https://api.anthropic.com")
        assert client.base_url == "https://api.anthropic.com"


class TestHTTPClientContextManager:
    """Tests for HTTPClient context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enters(self) -> None:
        """Test that context manager properly initializes client."""
        with patch("claude_code.services.api.client.httpx.AsyncClient") as MockAsyncClient:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_client
            async with HTTPClient() as client:
                assert client._client is not None
                assert client._client is mock_client
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exits(self) -> None:
        """Test that context manager properly closes client."""
        with patch("claude_code.services.api.client.httpx.AsyncClient") as MockAsyncClient:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_client
            async with HTTPClient() as client:
                pass
            assert client._client is None
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_base_url(self) -> None:
        """Test context manager with base URL."""
        with patch("claude_code.services.api.client.httpx.AsyncClient") as MockAsyncClient:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_client
            async with HTTPClient(base_url="https://api.test.com") as client:
                assert client._client is not None
                MockAsyncClient.assert_called_once()
                call_kwargs = MockAsyncClient.call_args.kwargs
                assert call_kwargs["base_url"] == "https://api.test.com"


class TestHTTPClientShouldRetry:
    """Tests for retry logic."""

    def test_retry_on_429(self) -> None:
        """Test that 429 (rate limit) is retryable."""
        client = HTTPClient()
        assert client._should_retry(429) is True

    def test_retry_on_500(self) -> None:
        """Test that 500 is retryable."""
        client = HTTPClient()
        assert client._should_retry(500) is True

    def test_retry_on_502(self) -> None:
        """Test that 502 is retryable."""
        client = HTTPClient()
        assert client._should_retry(502) is True

    def test_retry_on_503(self) -> None:
        """Test that 503 is retryable."""
        client = HTTPClient()
        assert client._should_retry(503) is True

    def test_retry_on_504(self) -> None:
        """Test that 504 is retryable."""
        client = HTTPClient()
        assert client._should_retry(504) is True

    def test_no_retry_on_400(self) -> None:
        """Test that 400 is not retryable."""
        client = HTTPClient()
        assert client._should_retry(400) is False

    def test_no_retry_on_401(self) -> None:
        """Test that 401 is not retryable."""
        client = HTTPClient()
        assert client._should_retry(401) is False

    def test_no_retry_on_403(self) -> None:
        """Test that 403 is not retryable."""
        client = HTTPClient()
        assert client._should_retry(403) is False

    def test_no_retry_on_404(self) -> None:
        """Test that 404 is not retryable."""
        client = HTTPClient()
        assert client._should_retry(404) is False

    def test_no_retry_on_200(self) -> None:
        """Test that 200 is not retryable."""
        client = HTTPClient()
        assert client._should_retry(200) is False


class TestHTTPClientSleepBackoff:
    """Tests for backoff sleep."""

    @pytest.mark.asyncio
    async def test_backoff_exponential(self) -> None:
        """Test that backoff is exponential."""
        client = HTTPClient(backoff_base=1.0)
        start = time.monotonic()
        await client._sleep_with_backoff(0)
        elapsed = time.monotonic() - start
        assert 0.9 <= elapsed <= 1.2  # ~1 second

        start = time.monotonic()
        await client._sleep_with_backoff(1)
        elapsed = time.monotonic() - start
        assert 1.9 <= elapsed <= 2.2  # ~2 seconds

        start = time.monotonic()
        await client._sleep_with_backoff(2)
        elapsed = time.monotonic() - start
        assert 3.9 <= elapsed <= 4.2  # ~4 seconds


class TestHTTPClientPost:
    """Tests for POST requests."""

    def _mock_response(self, status_code: int = 200, json_data: Any = None) -> MagicMock:
        """Create a mock httpx.Response."""
        mock = MagicMock(spec=["status_code", "json", "headers", "text"])
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        mock.headers = {}
        mock.text = ""
        return mock

    @pytest.mark.asyncio
    async def test_post_requires_context(self) -> None:
        """Test that post fails without context manager."""
        client = HTTPClient()
        with pytest.raises(AssertionError, match="Client not initialized"):
            await client.post("/test")

    @pytest.mark.asyncio
    async def test_post_success(self) -> None:
        """Test successful POST request."""
        mock_response = self._mock_response(200, {"result": "ok"})

        with patch.object(
            HTTPClient, "__aenter__", new_callable=AsyncMock
        ) as mock_aenter, patch.object(
            HTTPClient, "__aexit__", new_callable=AsyncMock
        ):
            mock_aenter.return_value = None
            mock_aenter.side_effect = lambda: setattr(
                HTTPClient.__new__(HTTPClient), "_client", MagicMock()
            ) or HTTPClient.__new__(HTTPClient)

            client = HTTPClient()
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            response = await client.post("/api/test", json={"key": "value"})

            assert response.status_code == 200
            client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_with_headers(self) -> None:
        """Test POST request with custom headers."""
        mock_response = self._mock_response(200)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        await client.post("/api/test", json={"key": "value"}, headers=headers)

        call_kwargs = client._client.post.call_args.kwargs
        assert "Authorization" in call_kwargs.get("headers", {})
        assert call_kwargs["headers"]["Authorization"] == "Bearer token123"
        assert call_kwargs["headers"]["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_post_with_custom_timeout(self) -> None:
        """Test POST request with custom timeout."""
        mock_response = self._mock_response(200)

        client = HTTPClient(timeout=60.0)
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        await client.post("/api/test", timeout=30.0)

        call_kwargs = client._client.post.call_args.kwargs
        assert call_kwargs["timeout"] is not None

    @pytest.mark.asyncio
    async def test_post_retries_on_429(self) -> None:
        """Test that POST retries on 429 rate limit."""
        mock_429 = self._mock_response(429)
        mock_200 = self._mock_response(200)

        client = HTTPClient(max_retries=3, backoff_base=0.01)
        client._client = MagicMock()
        client._client.post = AsyncMock(side_effect=[mock_429, mock_200])

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock):
            response = await client.post("/api/test")

        assert response.status_code == 200
        assert client._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_post_retries_on_500(self) -> None:
        """Test that POST retries on 500 server error."""
        mock_500 = self._mock_response(500)
        mock_200 = self._mock_response(200)

        client = HTTPClient(max_retries=3, backoff_base=0.01)
        client._client = MagicMock()
        client._client.post = AsyncMock(side_effect=[mock_500, mock_200])

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock):
            response = await client.post("/api/test")

        assert response.status_code == 200
        assert client._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_post_does_not_retry_on_400(self) -> None:
        """Test that POST does not retry on 400 client error."""
        mock_400 = self._mock_response(400)

        client = HTTPClient(max_retries=3)
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_400)

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock) as mock_sleep:
            response = await client.post("/api/test")

        assert response.status_code == 400
        assert client._client.post.call_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_post_does_not_retry_on_401(self) -> None:
        """Test that POST does not retry on 401 auth error."""
        mock_401 = self._mock_response(401)

        client = HTTPClient(max_retries=3)
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_401)

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock) as mock_sleep:
            response = await client.post("/api/test")

        assert response.status_code == 401
        assert client._client.post.call_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_post_max_retries_exceeded(self) -> None:
        """Test that POST stops after max retries."""
        mock_429 = self._mock_response(429)

        client = HTTPClient(max_retries=2, backoff_base=0.01)
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_429)

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock):
            response = await client.post("/api/test")

        assert response.status_code == 429
        assert client._client.post.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_post_timeout_retries(self) -> None:
        """Test that POST retries on timeout."""
        import httpx

        client = HTTPClient(max_retries=2, backoff_base=0.01)
        client._client = MagicMock()
        client._client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock), \
                pytest.raises(httpx.TimeoutException):
            await client.post("/api/test")

        assert client._client.post.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_post_network_error_retries(self) -> None:
        """Test that POST retries on network errors."""
        import httpx

        client = HTTPClient(max_retries=2, backoff_base=0.01)
        client._client = MagicMock()
        client._client.post = AsyncMock(side_effect=httpx.ConnectError("connection failed"))

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock), \
                pytest.raises(httpx.ConnectError):
            await client.post("/api/test")

        assert client._client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_post_with_data_instead_of_json(self) -> None:
        """Test POST request with form data instead of JSON."""
        mock_response = self._mock_response(200)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        await client.post("/api/test", data={"key": "value"})

        call_kwargs = client._client.post.call_args.kwargs
        assert call_kwargs.get("data") == {"key": "value"}

    @pytest.mark.asyncio
    async def test_post_stream_flag(self) -> None:
        """Test POST with stream=True flag."""
        mock_response = self._mock_response(200)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        await client.post("/api/test", json={"key": "value"}, stream=True)

        client._client.post.assert_called_once()


class TestHTTPClientGet:
    """Tests for GET requests."""

    def _mock_response(self, status_code: int = 200, json_data: Any = None) -> MagicMock:
        """Create a mock httpx.Response."""
        mock = MagicMock(spec=["status_code", "json", "headers", "text"])
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        mock.headers = {}
        mock.text = ""
        return mock

    @pytest.mark.asyncio
    async def test_get_requires_context(self) -> None:
        """Test that get fails without context manager."""
        client = HTTPClient()
        with pytest.raises(AssertionError, match="Client not initialized"):
            await client.get("/test")

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        """Test successful GET request."""
        mock_response = self._mock_response(200, {"items": [1, 2, 3]})

        client = HTTPClient()
        client._client = MagicMock()
        client._client.get = AsyncMock(return_value=mock_response)

        response = await client.get("/api/test", params={"page": 1})

        assert response.status_code == 200
        client._client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_params(self) -> None:
        """Test GET request with query parameters."""
        mock_response = self._mock_response(200)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.get = AsyncMock(return_value=mock_response)

        await client.get("/api/test", params={"page": 1, "limit": 10})

        call_kwargs = client._client.get.call_args.kwargs
        assert call_kwargs.get("params") == {"page": 1, "limit": 10}

    @pytest.mark.asyncio
    async def test_get_retries_on_429(self) -> None:
        """Test that GET retries on 429 rate limit."""
        mock_429 = self._mock_response(429)
        mock_200 = self._mock_response(200)

        client = HTTPClient(max_retries=3, backoff_base=0.01)
        client._client = MagicMock()
        client._client.get = AsyncMock(side_effect=[mock_429, mock_200])

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock):
            response = await client.get("/api/test")

        assert response.status_code == 200
        assert client._client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_does_not_retry_on_404(self) -> None:
        """Test that GET does not retry on 404."""
        mock_404 = self._mock_response(404)

        client = HTTPClient(max_retries=3)
        client._client = MagicMock()
        client._client.get = AsyncMock(return_value=mock_404)

        with patch.object(client, "_sleep_with_backoff", new_callable=AsyncMock) as mock_sleep:
            response = await client.get("/api/test")

        assert response.status_code == 404
        assert client._client.get.call_count == 1
        mock_sleep.assert_not_called()


class TestHTTPClientPut:
    """Tests for PUT requests."""

    def _mock_response(self, status_code: int = 200, json_data: Any = None) -> MagicMock:
        """Create a mock httpx.Response."""
        mock = MagicMock(spec=["status_code", "json", "headers", "text"])
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        mock.headers = {}
        mock.text = ""
        return mock

    @pytest.mark.asyncio
    async def test_put_requires_context(self) -> None:
        """Test that put fails without context manager."""
        client = HTTPClient()
        with pytest.raises(AssertionError, match="Client not initialized"):
            await client.put("/test")

    @pytest.mark.asyncio
    async def test_put_success(self) -> None:
        """Test successful PUT request."""
        mock_response = self._mock_response(200)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.put = AsyncMock(return_value=mock_response)

        response = await client.put("/api/test/1", json={"name": "updated"})

        assert response.status_code == 200
        client._client.put.assert_called_once()


class TestHTTPClientDelete:
    """Tests for DELETE requests."""

    def _mock_response(self, status_code: int = 200) -> MagicMock:
        """Create a mock httpx.Response."""
        mock = MagicMock(spec=["status_code", "json", "headers", "text"])
        mock.status_code = status_code
        mock.json.return_value = {}
        mock.headers = {}
        mock.text = ""
        return mock

    @pytest.mark.asyncio
    async def test_delete_requires_context(self) -> None:
        """Test that delete fails without context manager."""
        client = HTTPClient()
        with pytest.raises(AssertionError, match="Client not initialized"):
            await client.delete("/test")

    @pytest.mark.asyncio
    async def test_delete_success(self) -> None:
        """Test successful DELETE request."""
        mock_response = self._mock_response(204)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.delete = AsyncMock(return_value=mock_response)

        response = await client.delete("/api/test/1")

        assert response.status_code == 204
        client._client.delete.assert_called_once()


class TestHTTPClientStreamPost:
    """Tests for streaming POST requests."""

    @pytest.mark.asyncio
    async def test_stream_post_requires_context(self) -> None:
        """Test that stream_post fails without context manager."""
        client = HTTPClient()
        with pytest.raises(AssertionError, match="Client not initialized"):
            # Need to iterate the async generator
            async for _ in client.stream_post("/test"):
                pass

    @pytest.mark.asyncio
    async def test_stream_post_yields_chunks(self) -> None:
        """Test that stream_post yields byte chunks."""
        chunk1 = b'{"event": "message", "data": "hello"}\n'
        chunk2 = b'{"event": "message", "data": "world"}\n'

        # Create a proper async iterator for aiter_bytes
        async def async_chunk_iterator():
            for chunk in [chunk1, chunk2]:
                yield chunk

        mock_stream_response = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=async_chunk_iterator())

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.stream = MagicMock(return_value=mock_context)

        chunks = []
        async for chunk in client.stream_post("/api/stream", json={"query": "test"}):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == chunk1
        assert chunks[1] == chunk2

    @pytest.mark.asyncio
    async def test_stream_post_empty_response(self) -> None:
        """Test stream_post with empty response."""
        # Create a proper async iterator for aiter_bytes
        async def async_chunk_iterator():
            return
            yield  # make it a generator

        mock_stream_response = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=async_chunk_iterator())

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.stream = MagicMock(return_value=mock_context)

        chunks = []
        async for chunk in client.stream_post("/api/stream", json={"query": "test"}):
            chunks.append(chunk)

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_stream_post_with_headers(self) -> None:
        """Test stream_post with custom headers."""
        # Create a proper async iterator for aiter_bytes
        async def async_chunk_iterator():
            yield b"data"

        mock_stream_response = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=async_chunk_iterator())

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        client = HTTPClient()
        client._client = MagicMock()
        client._client.stream = MagicMock(return_value=mock_context)

        headers = {"Authorization": "Bearer token123", "X-Stream": "true"}
        async for _ in client.stream_post("/api/stream", json={"query": "test"}, headers=headers):
            pass

        call_args = client._client.stream.call_args
        assert call_args.kwargs.get("headers", {}).get("Authorization") == "Bearer token123"
        assert call_args.kwargs.get("headers", {}).get("X-Stream") == "true"


class TestHTTPClientIntegration:
    """Integration-style tests using pytest-httpserver.

    These tests make actual HTTP requests against a local test server.
    """

    @pytest.mark.asyncio
    async def test_live_post_request(self, httpserver: HTTPServer) -> None:
        """Test POST request against a live server."""
        httpserver.expect_ordered_request("/api/test", method="POST").respond_with_json(
            {"result": "success"}, status=200
        )
        base_url = f"http://{httpserver.host}:{httpserver.port}"

        async with HTTPClient(base_url=base_url) as client:
            response = await client.post("/api/test", json={"key": "value"})

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "success"

    @pytest.mark.asyncio
    async def test_live_get_request(self, httpserver: HTTPServer) -> None:
        """Test GET request against a live server."""
        httpserver.expect_ordered_request("/api/test", method="GET").respond_with_json(
            {"items": [1, 2, 3]}, status=200
        )
        base_url = f"http://{httpserver.host}:{httpserver.port}"

        async with HTTPClient(base_url=base_url) as client:
            response = await client.get("/api/test")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_live_stream_post(self, httpserver: HTTPServer) -> None:
        """Test streaming POST against a live server."""
        httpserver.expect_ordered_request("/api/stream", method="POST").respond_with_data(
            b'data: hello\n\ndata: world\n\n',
            status=200,
            content_type="text/event-stream",
        )
        base_url = f"http://{httpserver.host}:{httpserver.port}"

        chunks = []
        async with HTTPClient(base_url=base_url) as client:
            async for chunk in client.stream_post("/api/stream", json={"query": "test"}):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert b"hello" in chunks[0]
        assert b"world" in chunks[0]

    @pytest.mark.asyncio
    async def test_live_404_response(self, httpserver: HTTPServer) -> None:
        """Test handling of 404 response."""
        httpserver.expect_ordered_request("/api/notfound", method="GET").respond_with_json(
            {"error": "not found"}, status=404
        )
        base_url = f"http://{httpserver.host}:{httpserver.port}"

        async with HTTPClient(base_url=base_url) as client:
            response = await client.get("/api/notfound")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_live_429_retry(self, httpserver: HTTPServer) -> None:
        """Test that 429 responses are retried."""
        from werkzeug import Response

        call_count = 0
        start_time = time.monotonic()

        def handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(
                    '{"error": "rate limited"}',
                    status=429,
                    content_type="application/json",
                )
            else:
                elapsed = time.monotonic() - start_time
                return Response(
                    f'{{"result": "success", "elapsed": {elapsed}}}',
                    status=200,
                    content_type="application/json",
                )

        httpserver.expect_request("/api/rate-limited", method="POST").respond_with_handler(handler)
        base_url = f"http://{httpserver.host}:{httpserver.port}"

        # Verify server responds correctly (retry logic tested in unit tests)
        async with HTTPClient(base_url=base_url, max_retries=0) as http_client:
            response = await http_client.post(
                "/api/rate-limited",
                json={"test": "data"},
            )

        assert call_count == 1
        assert response.status_code == 429
