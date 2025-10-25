"""
Unit tests for WebSocket Notification Service

Tests the notification service for broadcasting data changes
to connected clients with deduplication and context enrichment.
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp.task_management.application.services.websocket_notification_service import (
    WebSocketNotificationService,
    _is_duplicate_notification,
    _notification_cache,
    _cache_ttl
)


class TestNotificationDeduplication:
    """Test notification deduplication functionality"""
    
    def setup_method(self):
        """Clear notification cache before each test"""
        global _notification_cache
        _notification_cache.clear()
    
    def test_first_notification_allowed(self):
        """Test that first notification is allowed"""
        result = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-456"
        )
        assert result is False  # Should be allowed
    
    def test_duplicate_notification_blocked(self):
        """Test that duplicate notification within TTL is blocked"""
        # First notification
        result1 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-456"
        )
        assert result1 is False
        
        # Immediate duplicate
        result2 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-456"
        )
        assert result2 is True  # Should be blocked
    
    def test_different_notifications_allowed(self):
        """Test that different notifications are allowed"""
        # First notification
        result1 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-456"
        )
        assert result1 is False
        
        # Different entity
        result2 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-789",  # Different ID
            user_id="user-456"
        )
        assert result2 is False  # Should be allowed
        
        # Different user
        result3 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-999"  # Different user
        )
        assert result3 is False  # Should be allowed
    
    def test_notification_after_ttl_allowed(self):
        """Test that notification after TTL expiry is allowed"""
        # Record the time before first notification
        start_time = time.time()

        # First notification
        result1 = _is_duplicate_notification(
            event_type="update",
            entity_type="task",
            entity_id="task-123",
            user_id="user-456"
        )
        assert result1 is False

        # Simulate time passing beyond TTL
        with patch('fastmcp.task_management.application.services.websocket_notification_service.time.time') as mock_time:
            # Set current time to after TTL
            mock_time.return_value = start_time + _cache_ttl + 1

            result2 = _is_duplicate_notification(
                event_type="update",
                entity_type="task",
                entity_id="task-123",
                user_id="user-456"
            )
            assert result2 is False  # Should be allowed after TTL
    
    def test_cache_cleanup(self):
        """Test that expired entries are cleaned from cache"""
        # Record the time before adding notifications
        start_time = time.time()

        # Add multiple notifications
        _is_duplicate_notification("update", "task", "task-1", "user-1")
        _is_duplicate_notification("create", "task", "task-2", "user-1")
        _is_duplicate_notification("delete", "task", "task-3", "user-1")

        assert len(_notification_cache) == 3

        # Simulate time passing
        with patch('fastmcp.task_management.application.services.websocket_notification_service.time.time') as mock_time:
            mock_time.return_value = start_time + _cache_ttl + 1

            # Add new notification to trigger cleanup
            _is_duplicate_notification("update", "task", "task-4", "user-1")

            # Only the new notification should remain
            assert len(_notification_cache) == 1
            assert "update:task:task-4:user-1" in _notification_cache
    
    @patch('fastmcp.task_management.application.services.websocket_notification_service.logger')
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate log messages are generated"""
        # First notification - should log allowed
        _is_duplicate_notification("update", "task", "task-123", "user-456")
        mock_logger.info.assert_called_with("✅ NOTIFICATION ALLOWED: update:task:task-123:user-456")
        
        # Duplicate - should log blocked
        _is_duplicate_notification("update", "task", "task-123", "user-456")
        assert mock_logger.warning.called
        warning_call = mock_logger.warning.call_args[0][0]
        assert "🚫 DUPLICATE NOTIFICATION BLOCKED" in warning_call
        assert "update:task:task-123:user-456" in warning_call


class TestWebSocketNotificationService:
    """Test WebSocketNotificationService class functionality"""
    
    @pytest.fixture
    def notification_service(self):
        """Create WebSocketNotificationService instance"""
        return WebSocketNotificationService()
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    def test_get_task_context_success(self, mock_get_session):
        """Test successful task context retrieval"""
        # Setup mock database objects
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_task.user_id = "user-456"
        
        mock_branch = Mock()
        mock_branch.id = "branch-789"
        mock_branch.name = "feature/test-branch"
        
        # Setup query chain
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = (mock_task, mock_branch)
        
        # Configure context manager
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Test
        context = WebSocketNotificationService._get_task_context(
            task_id="task-123",
            user_id="user-456"
        )
        
        # Verify
        assert context["task_title"] == "Test Task"
        assert context["parent_branch_id"] == "branch-789"
        assert context["parent_branch_title"] == "feature/test-branch"
        assert context["task_user_id"] == "user-456"
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    def test_get_task_context_not_found(self, mock_get_session):
        """Test task context when task not found"""
        # Setup query to return None
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Configure context manager
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Test
        context = WebSocketNotificationService._get_task_context(
            task_id="nonexistent-123",
            user_id="user-456"
        )
        
        # Verify fallback values
        assert context["task_title"] == "Task nonexist"  # First 8 chars
        assert context["parent_branch_id"] is None
        assert context["parent_branch_title"] == "Unknown Branch"
        assert context["task_user_id"] is None
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    @patch('fastmcp.task_management.application.services.websocket_notification_service.logger')
    def test_get_task_context_database_error(self, mock_logger, mock_get_session):
        """Test task context retrieval with database error"""
        # Setup session to raise exception
        mock_get_session.side_effect = Exception("Database connection failed")
        
        # Test
        context = WebSocketNotificationService._get_task_context("task-123")
        
        # Verify error handling
        mock_logger.error.assert_called()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Failed to get task context" in error_msg
        assert "Database connection failed" in error_msg
        
        # Verify fallback values returned
        assert context["task_title"] == "Task task-123"
        assert context["parent_branch_id"] is None
        assert context["parent_branch_title"] == "Unknown Branch"
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    def test_get_task_context_with_user_filtering(self, mock_get_session):
        """Test task context retrieval with user filtering"""
        # Setup mocks
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.title = "User Task"
        mock_task.user_id = "user-456"
        
        mock_branch = Mock()
        mock_branch.id = "branch-789"
        mock_branch.name = "user/feature"
        
        # Setup query chain
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        
        mock_session.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.side_effect = [mock_filter, mock_filter]  # Called twice
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = (mock_task, mock_branch)
        
        # Configure context manager
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Test with user_id
        context = WebSocketNotificationService._get_task_context(
            task_id="task-123",
            user_id="user-456"
        )
        
        # Verify user filtering was applied
        assert mock_query.filter.call_count >= 1
        # Verify context returned
        assert context["task_title"] == "User Task"
        assert context["task_user_id"] == "user-456"
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    def test_notification_service_attributes(self, mock_get_session):
        """Test WebSocketNotificationService static methods and attributes"""
        # Verify service has required static method
        assert hasattr(WebSocketNotificationService, '_get_task_context')
        assert callable(WebSocketNotificationService._get_task_context)
        
        # Test that method can be called statically
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Should not raise error when called statically
        result = WebSocketNotificationService._get_task_context("test-id")
        assert isinstance(result, dict)


class TestIntegrationScenarios:
    """Integration test scenarios for WebSocket notifications"""
    
    def setup_method(self):
        """Clear notification cache before each test"""
        global _notification_cache
        _notification_cache.clear()
    
    @patch('fastmcp.task_management.infrastructure.database.database_config.get_session')
    def test_multiple_user_notifications(self, mock_get_session):
        """Test notifications for multiple users don't interfere"""
        # Setup different tasks for different users
        users_tasks = [
            ("user-1", "task-1", "Task 1"),
            ("user-2", "task-2", "Task 2"),
            ("user-3", "task-3", "Task 3"),
        ]
        
        # Test that each user can receive notifications for their own tasks
        for user_id, task_id, task_title in users_tasks:
            # First notification should be allowed
            result = _is_duplicate_notification(
                event_type="update",
                entity_type="task",
                entity_id=task_id,
                user_id=user_id
            )
            assert result is False
        
        # Each user trying to send duplicate should be blocked
        for user_id, task_id, task_title in users_tasks:
            result = _is_duplicate_notification(
                event_type="update",
                entity_type="task",
                entity_id=task_id,
                user_id=user_id
            )
            assert result is True
    
    def test_different_event_types_same_entity(self):
        """Test different event types for same entity are allowed"""
        entity_id = "task-123"
        user_id = "user-456"
        
        # Different event types should all be allowed
        event_types = ["create", "update", "delete", "assign", "complete"]
        
        for event_type in event_types:
            result = _is_duplicate_notification(
                event_type=event_type,
                entity_type="task",
                entity_id=entity_id,
                user_id=user_id
            )
            assert result is False  # Each different event type allowed
    
    def test_high_volume_deduplication(self):
        """Test deduplication under high volume scenarios"""
        # Simulate rapid fire of same notification
        task_id = "task-high-volume"
        user_id = "user-123"
        
        results = []
        for i in range(10):
            result = _is_duplicate_notification(
                event_type="update",
                entity_type="task",
                entity_id=task_id,
                user_id=user_id
            )
            results.append(result)
        
        # Only first should be allowed
        assert results[0] is False
        assert all(results[1:])  # All others should be True (blocked)
    
    def test_concurrent_notifications_different_entities(self):
        """Test concurrent notifications for different entities"""
        user_id = "user-concurrent"
        
        # Simulate concurrent notifications for different tasks
        task_ids = [f"task-{i}" for i in range(5)]
        
        # All should be allowed (different entities)
        for task_id in task_ids:
            result = _is_duplicate_notification(
                event_type="update",
                entity_type="task",
                entity_id=task_id,
                user_id=user_id
            )
            assert result is False