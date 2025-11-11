"""Unit tests for EventDispatcher domain service"""

from unittest.mock import Mock, patch

from fastmcp.task_management.domain.services.event_dispatcher import (
    EventDispatcher,
    dispatch_domain_event,
    get_event_dispatcher,
)


class TestEventDispatcher:
    """Test cases for EventDispatcher class"""

    def setup_method(self):
        """Set up test dependencies"""
        self.dispatcher = EventDispatcher()

    def test_init_empty_handlers(self):
        """Test dispatcher initializes with empty handler dictionaries"""
        assert self.dispatcher._handlers == {}
        assert self.dispatcher._async_handlers == {}

    def test_register_handler_new_event_type(self):
        """Test registering a handler for a new event type"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler)

        assert event_type in self.dispatcher._handlers
        assert handler in self.dispatcher._handlers[event_type]
        assert len(self.dispatcher._handlers[event_type]) == 1

    def test_register_handler_existing_event_type(self):
        """Test registering multiple handlers for the same event type"""
        handler1 = Mock(__name__="handler1")
        handler2 = Mock(__name__="handler2")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler1)
        self.dispatcher.register_handler(event_type, handler2)

        assert len(self.dispatcher._handlers[event_type]) == 2
        assert handler1 in self.dispatcher._handlers[event_type]
        assert handler2 in self.dispatcher._handlers[event_type]

    def test_register_handler_duplicate_prevention(self):
        """Test that duplicate handlers are not registered"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler)
        self.dispatcher.register_handler(event_type, handler)  # Try to add again

        assert len(self.dispatcher._handlers[event_type]) == 1

    @patch("fastmcp.task_management.domain.services.event_dispatcher.logger")
    def test_register_handler_logging(self, mock_logger):
        """Test that registering a handler logs the action"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler)

        mock_logger.debug.assert_called_once_with(
            "Registered handler test_handler for event test_event"
        )

    def test_unregister_handler_success(self):
        """Test successfully unregistering a handler"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler)
        self.dispatcher.unregister_handler(event_type, handler)

        assert len(self.dispatcher._handlers[event_type]) == 0

    def test_unregister_handler_not_found(self):
        """Test unregistering a handler that doesn't exist"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        # Should not raise error
        self.dispatcher.unregister_handler(event_type, handler)

    @patch("fastmcp.task_management.domain.services.event_dispatcher.logger")
    def test_unregister_handler_logging(self, mock_logger):
        """Test that unregistering a handler logs the action"""
        handler = Mock(__name__="test_handler")
        event_type = "test_event"

        self.dispatcher.register_handler(event_type, handler)
        mock_logger.reset_mock()  # Clear registration log

        self.dispatcher.unregister_handler(event_type, handler)

        mock_logger.debug.assert_called_once_with(
            "Unregistered handler test_handler for event test_event"
        )

    def test_dispatch_with_handlers(self):
        """Test dispatching an event to registered handlers"""
        handler1 = Mock(__name__="handler1")
        handler2 = Mock(__name__="handler2")
        event_type = "test_event"
        event_data = {"key": "value"}

        self.dispatcher.register_handler(event_type, handler1)
        self.dispatcher.register_handler(event_type, handler2)

        self.dispatcher.dispatch(event_type, event_data)

        handler1.assert_called_once_with(event_data)
        handler2.assert_called_once_with(event_data)

    @patch("fastmcp.task_management.domain.services.event_dispatcher.logger")
    def test_dispatch_no_handlers(self, mock_logger):
        """Test dispatching an event with no registered handlers"""
        event_type = "test_event"
        event_data = {"key": "value"}

        self.dispatcher.dispatch(event_type, event_data)

        mock_logger.debug.assert_called_once_with(
            "No handlers registered for event test_event"
        )

    @patch("fastmcp.task_management.domain.services.event_dispatcher.logger")
    def test_dispatch_handler_exception(self, mock_logger):
        """Test that handler exceptions are caught and logged"""
        handler1 = Mock(__name__="handler1", side_effect=Exception("Handler error"))
        handler2 = Mock(__name__="handler2")  # This should still be called
        event_type = "test_event"
        event_data = {"key": "value"}

        self.dispatcher.register_handler(event_type, handler1)
        self.dispatcher.register_handler(event_type, handler2)

        self.dispatcher.dispatch(event_type, event_data)

        handler1.assert_called_once_with(event_data)
        handler2.assert_called_once_with(event_data)

        # Check error was logged
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert len(error_calls) == 1
        assert "failed processing" in error_calls[0][0][0]

    def test_clear_handlers_specific_type(self):
        """Test clearing handlers for a specific event type"""
        handler1 = Mock(__name__="handler1")
        handler2 = Mock(__name__="handler2")
        event_type1 = "test_event1"
        event_type2 = "test_event2"

        self.dispatcher.register_handler(event_type1, handler1)
        self.dispatcher.register_handler(event_type2, handler2)

        self.dispatcher.clear_handlers(event_type1)

        assert event_type1 not in self.dispatcher._handlers
        assert event_type2 in self.dispatcher._handlers
        assert handler2 in self.dispatcher._handlers[event_type2]

    def test_clear_handlers_all(self):
        """Test clearing all handlers"""
        handler1 = Mock(__name__="handler1")
        handler2 = Mock(__name__="handler2")

        self.dispatcher.register_handler("event1", handler1)
        self.dispatcher.register_handler("event2", handler2)

        self.dispatcher.clear_handlers()

        assert len(self.dispatcher._handlers) == 0

    def test_get_handler_count(self):
        """Test getting the count of handlers for an event type"""
        handler1 = Mock(__name__="handler1")
        handler2 = Mock(__name__="handler2")
        event_type = "test_event"

        assert self.dispatcher.get_handler_count(event_type) == 0

        self.dispatcher.register_handler(event_type, handler1)
        assert self.dispatcher.get_handler_count(event_type) == 1

        self.dispatcher.register_handler(event_type, handler2)
        assert self.dispatcher.get_handler_count(event_type) == 2

    def test_get_handler_count_unknown_event(self):
        """Test getting handler count for unknown event type returns 0"""
        assert self.dispatcher.get_handler_count("unknown_event") == 0


class TestEventDispatcherGlobalFunctions:
    """Test cases for global event dispatcher functions"""

    @patch(
        "fastmcp.task_management.domain.services.event_dispatcher._event_dispatcher",
        None,
    )
    def test_get_event_dispatcher_creates_singleton(self):
        """Test that get_event_dispatcher creates a singleton instance"""
        dispatcher1 = get_event_dispatcher()
        dispatcher2 = get_event_dispatcher()

        assert dispatcher1 is dispatcher2
        assert isinstance(dispatcher1, EventDispatcher)

    @patch(
        "fastmcp.task_management.domain.services.event_dispatcher._event_dispatcher",
        None,
    )
    @patch("fastmcp.task_management.domain.services.event_dispatcher.logger")
    def test_get_event_dispatcher_logging(self, mock_logger):
        """Test that creating the global dispatcher is logged"""
        get_event_dispatcher()

        mock_logger.info.assert_called_once_with("Created global event dispatcher")

    @patch(
        "fastmcp.task_management.domain.services.event_dispatcher.get_event_dispatcher"
    )
    def test_dispatch_domain_event(self, mock_get_dispatcher):
        """Test the convenience dispatch_domain_event function"""
        mock_dispatcher = Mock()
        mock_get_dispatcher.return_value = mock_dispatcher

        event_type = "test_event"
        event_data = {"key": "value"}

        dispatch_domain_event(event_type, event_data)

        mock_get_dispatcher.assert_called_once()
        mock_dispatcher.dispatch.assert_called_once_with(event_type, event_data)


class TestEventDispatcherIntegration:
    """Integration tests for EventDispatcher with real handlers"""

    def setup_method(self):
        """Set up test dependencies"""
        self.dispatcher = EventDispatcher()
        self.handler_calls = []

    def create_handler(self, name):
        """Create a handler that records its calls"""

        def handler(event_data):
            self.handler_calls.append((name, event_data))

        handler.__name__ = name
        return handler

    def test_multiple_events_multiple_handlers(self):
        """Test dispatching multiple events to multiple handlers"""
        # Register handlers
        handler_a1 = self.create_handler("handler_a1")
        handler_a2 = self.create_handler("handler_a2")
        handler_b1 = self.create_handler("handler_b1")

        self.dispatcher.register_handler("event_a", handler_a1)
        self.dispatcher.register_handler("event_a", handler_a2)
        self.dispatcher.register_handler("event_b", handler_b1)

        # Dispatch events
        self.dispatcher.dispatch("event_a", {"type": "a", "value": 1})
        self.dispatcher.dispatch("event_b", {"type": "b", "value": 2})
        self.dispatcher.dispatch("event_a", {"type": "a", "value": 3})

        # Verify calls
        expected_calls = [
            ("handler_a1", {"type": "a", "value": 1}),
            ("handler_a2", {"type": "a", "value": 1}),
            ("handler_b1", {"type": "b", "value": 2}),
            ("handler_a1", {"type": "a", "value": 3}),
            ("handler_a2", {"type": "a", "value": 3}),
        ]

        assert self.handler_calls == expected_calls

    def test_handler_registration_and_removal_flow(self):
        """Test the complete flow of registering, using, and removing handlers"""
        handler = self.create_handler("test_handler")
        event_type = "test_event"

        # Initially no handlers
        assert self.dispatcher.get_handler_count(event_type) == 0

        # Register handler
        self.dispatcher.register_handler(event_type, handler)
        assert self.dispatcher.get_handler_count(event_type) == 1

        # Dispatch event
        self.dispatcher.dispatch(event_type, {"data": "test"})
        assert len(self.handler_calls) == 1

        # Unregister handler
        self.dispatcher.unregister_handler(event_type, handler)
        assert self.dispatcher.get_handler_count(event_type) == 0

        # Dispatch again - no handler should be called
        self.dispatcher.dispatch(event_type, {"data": "test2"})
        assert len(self.handler_calls) == 1  # Still only 1 from before
