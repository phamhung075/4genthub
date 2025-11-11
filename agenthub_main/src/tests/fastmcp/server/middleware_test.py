"""
Tests for fastmcp.server.middleware module.

This test file focuses on increasing coverage for middleware.py to reach 60%+.
Target coverage areas:
- MiddlewareContext.copy() method
- make_middleware_wrapper function
- Middleware dispatch logic (__call__ and _dispatch_handler)
- Individual handler methods (on_message, on_request, on_notification, etc.)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import mcp.types as mt
import pytest

from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
    make_middleware_wrapper,
)


class TestMiddlewareContext:
    """Test MiddlewareContext dataclass functionality."""

    def test_middleware_context_creation(self):
        """Test basic MiddlewareContext creation."""
        message = {"test": "data"}
        context = MiddlewareContext(message=message)

        assert context.message == message
        assert context.fastmcp_context is None
        assert context.source == "client"
        assert context.type == "request"
        assert context.method is None
        assert isinstance(context.timestamp, datetime)

    def test_middleware_context_copy(self):
        """Test MiddlewareContext.copy() method - covers line 103."""
        original_message = {"original": "data"}
        original_context = MiddlewareContext(
            message=original_message,
            source="client",
            type="request",
            method="tools/call",
        )

        # Test copy with updates
        new_message = {"updated": "data"}
        copied_context = original_context.copy(message=new_message, source="server")

        # Verify original is unchanged
        assert original_context.message == original_message
        assert original_context.source == "client"

        # Verify copy has updated values
        assert copied_context.message == new_message
        assert copied_context.source == "server"
        assert copied_context.type == "request"  # Unchanged
        assert copied_context.method == "tools/call"  # Unchanged

    def test_middleware_context_with_all_parameters(self):
        """Test MiddlewareContext with all parameters set."""
        message = {"test": "message"}
        fastmcp_ctx = MagicMock()
        timestamp = datetime.now(UTC)

        context = MiddlewareContext(
            message=message,
            fastmcp_context=fastmcp_ctx,
            source="server",
            type="notification",
            method="resources/read",
            timestamp=timestamp,
        )

        assert context.message == message
        assert context.fastmcp_context == fastmcp_ctx
        assert context.source == "server"
        assert context.type == "notification"
        assert context.method == "resources/read"
        assert context.timestamp == timestamp


class TestMakeMiddlewareWrapper:
    """Test make_middleware_wrapper function - covers lines 113-116."""

    @pytest.mark.asyncio
    async def test_make_middleware_wrapper_basic(self):
        """Test make_middleware_wrapper creates proper wrapper."""

        # Create a simple middleware
        async def test_middleware(context, call_next):
            result = await call_next(context)
            return f"wrapped:{result}"

        # Create a simple call_next
        async def simple_call_next(context):
            return "original"

        # Create wrapper
        wrapper = make_middleware_wrapper(test_middleware, simple_call_next)

        # Test the wrapper
        context = MiddlewareContext(message={"test": "data"})
        result = await wrapper(context)

        assert result == "wrapped:original"

    @pytest.mark.asyncio
    async def test_make_middleware_wrapper_with_context_modification(self):
        """Test middleware wrapper that modifies context."""

        async def modifying_middleware(context, call_next):
            # Modify context before passing to next
            modified_context = context.copy(source="server")
            return await call_next(modified_context)

        async def verifying_call_next(context):
            return context.source

        wrapper = make_middleware_wrapper(modifying_middleware, verifying_call_next)

        context = MiddlewareContext(message={"test": "data"}, source="client")
        result = await wrapper(context)

        assert result == "server"


class TestMiddlewareDispatch:
    """Test Middleware class dispatch logic - covers lines 128-164."""

    @pytest.mark.asyncio
    async def test_middleware_call_method_dispatches(self):
        """Test Middleware.__call__ orchestrates the pipeline - covers lines 128-132."""
        middleware = Middleware()

        async def mock_call_next(context):
            return "result"

        context = MiddlewareContext(
            message={"test": "data"}, method="tools/call", type="request"
        )

        result = await middleware(context, mock_call_next)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_dispatch_handler_tools_call(self):
        """Test _dispatch_handler for tools/call method - covers line 142."""
        middleware = Middleware()

        async def mock_call_next(context):
            return {"content": []}

        context = MiddlewareContext(
            message=mt.CallToolRequestParams(name="test_tool", arguments={}),
            method="tools/call",
            type="request",
        )

        result = await middleware(context, mock_call_next)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dispatch_handler_resources_read(self):
        """Test _dispatch_handler for resources/read method - covers line 144."""
        middleware = Middleware()

        async def mock_call_next(context):
            return mt.ReadResourceResult(contents=[])

        context = MiddlewareContext(
            message=mt.ReadResourceRequestParams(uri="test://resource"),
            method="resources/read",
            type="request",
        )

        result = await middleware(context, mock_call_next)
        assert isinstance(result, mt.ReadResourceResult)

    @pytest.mark.asyncio
    async def test_dispatch_handler_prompts_get(self):
        """Test _dispatch_handler for prompts/get method - covers line 146."""
        middleware = Middleware()

        async def mock_call_next(context):
            return mt.GetPromptResult(description="test", messages=[])

        context = MiddlewareContext(
            message=mt.GetPromptRequestParams(name="test_prompt"),
            method="prompts/get",
            type="request",
        )

        result = await middleware(context, mock_call_next)
        assert isinstance(result, mt.GetPromptResult)

    @pytest.mark.asyncio
    async def test_dispatch_handler_notification_type(self):
        """Test _dispatch_handler for notification type - covers line 160."""
        middleware = Middleware()

        async def mock_call_next(context):
            return None

        context = MiddlewareContext(
            message=mt.Notification(method="test/notification", params={}),
            method="test/notification",
            type="notification",
        )

        result = await middleware(context, mock_call_next)
        assert result is None


class TestMiddlewareHandlers:
    """Test individual middleware handler methods - covers lines 171-236."""

    @pytest.mark.asyncio
    async def test_on_message_handler(self):
        """Test on_message handler - covers line 171."""
        middleware = Middleware()

        async def mock_call_next(context):
            return "message_result"

        context = MiddlewareContext(message={"test": "data"})
        result = await middleware.on_message(context, mock_call_next)

        assert result == "message_result"

    @pytest.mark.asyncio
    async def test_on_request_handler(self):
        """Test on_request handler - covers line 178."""
        middleware = Middleware()

        async def mock_call_next(context):
            return "request_result"

        context = MiddlewareContext(
            message=mt.Request(method="test/method", params={}), type="request"
        )
        result = await middleware.on_request(context, mock_call_next)

        assert result == "request_result"

    @pytest.mark.asyncio
    async def test_on_notification_handler(self):
        """Test on_notification handler - covers line 185."""
        middleware = Middleware()

        async def mock_call_next(context):
            return None

        context = MiddlewareContext(
            message=mt.Notification(method="test/notification", params={}),
            type="notification",
        )
        result = await middleware.on_notification(context, mock_call_next)

        assert result is None

    @pytest.mark.asyncio
    async def test_on_call_tool_handler(self):
        """Test on_call_tool handler - covers line 192."""
        middleware = Middleware()

        async def mock_call_next(context):
            return mt.CallToolResult(content=[])

        context = MiddlewareContext(
            message=mt.CallToolRequestParams(name="test_tool", arguments={}),
            method="tools/call",
        )
        result = await middleware.on_call_tool(context, mock_call_next)

        assert isinstance(result, mt.CallToolResult)

    @pytest.mark.asyncio
    async def test_on_read_resource_handler(self):
        """Test on_read_resource handler - covers line 199."""
        middleware = Middleware()

        async def mock_call_next(context):
            return mt.ReadResourceResult(contents=[])

        context = MiddlewareContext(
            message=mt.ReadResourceRequestParams(uri="test://resource"),
            method="resources/read",
        )
        result = await middleware.on_read_resource(context, mock_call_next)

        assert isinstance(result, mt.ReadResourceResult)

    @pytest.mark.asyncio
    async def test_on_get_prompt_handler(self):
        """Test on_get_prompt handler - covers line 206."""
        middleware = Middleware()

        async def mock_call_next(context):
            return mt.GetPromptResult(description="test", messages=[])

        context = MiddlewareContext(
            message=mt.GetPromptRequestParams(name="test_prompt"), method="prompts/get"
        )
        result = await middleware.on_get_prompt(context, mock_call_next)

        assert isinstance(result, mt.GetPromptResult)


class TestCustomMiddleware:
    """Test custom middleware implementations."""

    @pytest.mark.asyncio
    async def test_custom_middleware_can_override_handlers(self):
        """Test that custom middleware can override specific handlers."""

        class CustomMiddleware(Middleware):
            async def on_call_tool(self, context, call_next):
                # Custom logic before calling next
                result = await call_next(context)
                # Custom logic after calling next
                return result

        custom = CustomMiddleware()

        async def mock_call_next(context):
            return mt.CallToolResult(content=[])

        context = MiddlewareContext(
            message=mt.CallToolRequestParams(name="test", arguments={}),
            method="tools/call",
            type="request",
        )

        result = await custom(context, mock_call_next)
        assert isinstance(result, mt.CallToolResult)

    @pytest.mark.asyncio
    async def test_middleware_chain_execution(self):
        """Test that middleware can be chained using make_middleware_wrapper."""

        class LoggingMiddleware(Middleware):
            def __init__(self):
                super().__init__()
                self.log = []

            async def on_message(self, context, call_next):
                self.log.append("before")
                result = await call_next(context)
                self.log.append("after")
                return result

        logging_middleware = LoggingMiddleware()

        async def final_handler(context):
            return "final_result"

        # Create wrapper
        wrapper = make_middleware_wrapper(logging_middleware, final_handler)

        context = MiddlewareContext(message={"test": "data"})
        result = await wrapper(context)

        assert result == "final_result"
        assert logging_middleware.log == ["before", "after"]
