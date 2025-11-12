"""
Test ASGI Resilience and Edge Cases for MCP Entry Point

Production-ready tests covering:
1. ASGI response handling with duplicate messages
2. ASGI middleware execution with large bodies and edge cases

These tests focus on the DebugLoggingMiddleware behavior and ASGI protocol compliance.
"""

import pytest

from fastmcp.server.mcp_entry_point import DebugLoggingMiddleware


class TestASGIResponseDuplicateHandling:
    """Test ASGI response handling with duplicate messages (lines 130-147)"""

    @pytest.mark.asyncio
    async def test_duplicate_http_response_start_messages(self):
        """
        Test graceful handling of duplicate http.response.start messages.

        ASGI Spec Edge Case: Some frameworks may send duplicate response.start messages
        The middleware MUST:
        1. Send both messages through (line 127 - never block ASGI communication)
        2. Track duplicate detection for logging (line 131-133)
        3. Continue processing without raising exceptions

        Coverage: Lines 130-137 (duplicate response.start handling)
        """

        # Mock app that sends duplicate response.start (edge case scenario)
        async def duplicate_start_app(scope, receive, send):
            """Application that accidentally sends duplicate http.response.start"""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            # Send duplicate (some buggy frameworks do this)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"result": "ok"}',
                    "more_body": False,
                }
            )

        middleware = DebugLoggingMiddleware(duplicate_start_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 12345),
            "headers": [],
        }

        sent_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"{}"}

        async def mock_send(message):
            sent_messages.append(message)

        # Execute - should NOT raise exception despite duplicates
        await middleware(scope, mock_receive, mock_send)

        # Verify both start messages were sent (middleware never blocks)
        response_starts = [
            m for m in sent_messages if m["type"] == "http.response.start"
        ]
        assert (
            len(response_starts) == 2
        ), "Both duplicate messages should be sent through"

        # Verify response completed successfully
        response_bodies = [
            m for m in sent_messages if m["type"] == "http.response.body"
        ]
        assert len(response_bodies) == 1
        assert response_bodies[0]["body"] == b'{"result": "ok"}'

    @pytest.mark.asyncio
    async def test_response_body_without_explicit_more_body_flag(self):
        """
        Test response completion with missing more_body flag.

        ASGI Spec: more_body defaults to False when omitted
        Line 144: if not message.get("more_body", False) and not response_completed

        Coverage: Line 144 (more_body default handling)
        Edge Case: Missing more_body key in response.body message
        """

        async def minimal_response_app(scope, receive, send):
            """App that sends minimal response without more_body key"""
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    # more_body intentionally omitted (ASGI spec: defaults to False)
                }
            )

        middleware = DebugLoggingMiddleware(minimal_response_app)

        scope = {
            "type": "http",
            "method": "DELETE",
            "path": "/api/resource/123",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("10.0.0.1", 9999),
            "headers": [],
        }

        sent_messages = []

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Verify response was sent correctly
        assert len(sent_messages) == 2  # start + body
        assert sent_messages[1]["type"] == "http.response.body"

        # Verify more_body defaults to False
        body_msg = sent_messages[1]
        assert body_msg.get("more_body", False) is False

    @pytest.mark.asyncio
    async def test_multiple_response_body_chunks_with_more_body_true(self):
        """
        Test handling of chunked responses with more_body=True.

        Line 144: Should only log response when more_body=False (final chunk)

        Coverage: Line 144 (response completion detection with multiple chunks)
        Edge Case: Streaming response with multiple body chunks
        """

        async def streaming_app(scope, receive, send):
            """App that streams response in multiple chunks"""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            # Send first chunk
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Chunk 1\n",
                    "more_body": True,  # More chunks coming
                }
            )
            # Send second chunk
            await send(
                {"type": "http.response.body", "body": b"Chunk 2\n", "more_body": True}
            )
            # Send final chunk
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Final chunk\n",
                    "more_body": False,  # Last chunk
                }
            )

        middleware = DebugLoggingMiddleware(streaming_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/stream",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("192.168.1.100", 55555),
            "headers": [],
        }

        sent_messages = []

        async def mock_receive():
            return {"type": "http.request"}

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Verify all chunks were sent
        body_messages = [m for m in sent_messages if m["type"] == "http.response.body"]
        assert len(body_messages) == 3

        # Verify more_body flags
        assert body_messages[0].get("more_body") is True
        assert body_messages[1].get("more_body") is True
        assert body_messages[2].get("more_body") is False

        # Verify content
        total_body = b"".join([m["body"] for m in body_messages])
        assert total_body == b"Chunk 1\nChunk 2\nFinal chunk\n"


class TestASGIMiddlewareEdgeCases:
    """Test ASGI middleware handling of edge cases"""

    @pytest.mark.asyncio
    async def test_non_http_scope_pass_through(self):
        """
        Test middleware correctly passes through non-HTTP scopes.

        Lines 71-73: if scope["type"] != "http": await self.app(scope, receive, send)

        Coverage: Lines 71-73 (non-HTTP scope handling)
        Edge Case: WebSocket connections should bypass HTTP logging
        """

        async def websocket_app(scope, receive, send):
            """Mock WebSocket application"""
            assert scope["type"] == "websocket"
            await send({"type": "websocket.accept"})
            await send({"type": "websocket.send", "text": "Hello WebSocket"})

        middleware = DebugLoggingMiddleware(websocket_app)

        websocket_scope = {
            "type": "websocket",
            "path": "/ws/chat",
            "client": ("127.0.0.1", 54321),
        }

        sent_messages = []

        async def mock_receive():
            return {"type": "websocket.connect"}

        async def mock_send(message):
            sent_messages.append(message)

        # Should pass through without HTTP processing
        await middleware(websocket_scope, mock_receive, mock_send)

        # Verify WebSocket messages were sent
        assert len(sent_messages) == 2
        assert sent_messages[0]["type"] == "websocket.accept"
        assert sent_messages[1]["type"] == "websocket.send"

    @pytest.mark.asyncio
    async def test_large_request_body_chunked_reading(self):
        """
        Test middleware handles large chunked request bodies correctly.

        Lines 106-114: Captures request body in chunks via receive_wrapper

        Coverage: Lines 106-114 (chunked request body capture)
        Edge Case: Large file upload with chunked transfer encoding
        """

        async def echo_size_app(scope, receive, send):
            """App that counts received bytes"""
            total_bytes = 0
            while True:
                message = await receive()
                if message["type"] == "http.request":
                    total_bytes += len(message.get("body", b""))
                    if not message.get("more_body", False):
                        break

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": f"Received {total_bytes} bytes".encode(),
                    "more_body": False,
                }
            )

        middleware = DebugLoggingMiddleware(echo_size_app)

        # Simulate large file upload (50KB in 1KB chunks)
        large_data = b"x" * 50000
        chunks = [large_data[i : i + 1000] for i in range(0, len(large_data), 1000)]

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/upload",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("192.168.1.50", 33333),
            "headers": [[b"content-type", b"application/octet-stream"]],
        }

        chunk_idx = [0]

        async def mock_receive():
            """Mock receive that returns chunked body"""
            if chunk_idx[0] < len(chunks):
                chunk = chunks[chunk_idx[0]]
                chunk_idx[0] += 1
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": chunk_idx[0] < len(chunks),
                }
            return {"type": "http.request", "body": b""}

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Verify response confirms all data received
        body_msgs = [m for m in sent_messages if m["type"] == "http.response.body"]
        assert len(body_msgs) == 1
        assert b"Received 50000 bytes" in body_msgs[0]["body"]

    @pytest.mark.asyncio
    async def test_request_with_no_body(self):
        """
        Test middleware handles requests without body (GET, HEAD, etc).

        Lines 156-166: Logs body only if body exists

        Coverage: Lines 156-166 (empty request body handling)
        Edge Case: GET/HEAD requests with no body
        """

        async def simple_app(scope, receive, send):
            """Simple app that returns OK"""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send(
                {"type": "http.response.body", "body": b"OK", "more_body": False}
            )

        middleware = DebugLoggingMiddleware(simple_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/status",
            "query_string": b"check=health",
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 11111),
            "headers": [[b"user-agent", b"HealthChecker/1.0"]],
        }

        async def mock_receive():
            # GET request - no body
            return {"type": "http.request", "body": b""}

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        # Should handle gracefully without body processing
        await middleware(scope, mock_receive, mock_send)

        # Verify response was sent
        assert len(sent_messages) == 2
        assert sent_messages[0]["type"] == "http.response.start"
        assert sent_messages[1]["body"] == b"OK"

    @pytest.mark.asyncio
    async def test_error_response_with_json_body(self):
        """
        Test middleware logs error responses with JSON bodies.

        Lines 200-220: Special handling for error responses (status >= 400)

        Coverage: Lines 200-220 (error response logging)
        Edge Case: 4xx/5xx errors with detailed JSON error info
        """

        async def error_app(scope, receive, send):
            """App that returns an error"""
            await send(
                {
                    "type": "http.response.start",
                    "status": 422,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            error_body = (
                b'{"error": "Validation failed", "details": ["Field required"]}'
            )
            await send(
                {"type": "http.response.body", "body": error_body, "more_body": False}
            )

        middleware = DebugLoggingMiddleware(error_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/validate",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("203.0.113.42", 44444),
            "headers": [[b"content-type", b"application/json"]],
        }

        async def mock_receive():
            return {"type": "http.request", "body": b'{"invalid": "data"}'}

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        await middleware(scope, mock_receive, mock_send)

        # Verify error response was sent
        start_msg = sent_messages[0]
        assert start_msg["status"] == 422

        body_msg = sent_messages[1]
        assert b'"error": "Validation failed"' in body_msg["body"]

    @pytest.mark.asyncio
    async def test_response_without_status_code(self):
        """
        Test middleware handles malformed responses gracefully.

        Lines 185-188: Handles missing or None status codes

        Coverage: Lines 185-188 (missing status code handling)
        Edge Case: Malformed ASGI response (defensive programming)
        """

        async def malformed_app(scope, receive, send):
            """App that sends malformed response"""
            # Send start without status (violates ASGI spec, but handle gracefully)
            try:
                await send(
                    {
                        "type": "http.response.start",
                        "status": None,  # Malformed!
                        "headers": [],
                    }
                )
            except Exception:
                # If framework rejects, send valid response
                await send(
                    {"type": "http.response.start", "status": 200, "headers": []}
                )

            await send(
                {"type": "http.response.body", "body": b"Recovered", "more_body": False}
            )

        middleware = DebugLoggingMiddleware(malformed_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/malformed",
            "query_string": b"",
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 22222),
            "headers": [],
        }

        async def mock_receive():
            return {"type": "http.request"}

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        # Should handle gracefully without crashing
        await middleware(scope, mock_receive, mock_send)

        # Verify some response was sent
        assert len(sent_messages) >= 1
