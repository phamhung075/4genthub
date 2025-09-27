"""Tests for NotificationService implementation."""

import asyncio
import json
import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from typing import Dict, Any

from fastmcp.task_management.infrastructure.notification_service import (
    NotificationService, NotificationChannel, InMemoryNotificationChannel, 
    LoggingNotificationChannel, FileNotificationChannel, Notification, NotificationPriority
)


class TestNotification:
    """Test suite for Notification class."""
    
    def test_notification_creation(self):
        """Test creating a notification."""
        notif = Notification(
            id="notif_123",
            type="test_type",
            title="Test Title",
            message="Test message",
            data={"key": "value"},
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc),
            recipients=["user1@example.com"]
        )
        
        assert notif.id == "notif_123"
        assert notif.type == "test_type"
        assert notif.title == "Test Title"
        assert notif.message == "Test message"
        assert notif.data == {"key": "value"}
        assert notif.priority == NotificationPriority.HIGH
        assert notif.recipients == ["user1@example.com"]
    
    def test_notification_dataclass_fields(self):
        """Test notification dataclass fields."""
        timestamp = datetime.now(timezone.utc)
        notif = Notification(
            id="notif_123",
            type="test_type",
            title="Test Title",
            message="Test message",
            data={"key": "value"},
            priority=NotificationPriority.HIGH,
            timestamp=timestamp,
            recipients=["user1@example.com"],
            metadata={"source": "test"}
        )
        
        assert notif.id == "notif_123"
        assert notif.type == "test_type"
        assert notif.title == "Test Title"
        assert notif.message == "Test message"
        assert notif.data == {"key": "value"}
        assert notif.priority == NotificationPriority.HIGH
        assert notif.timestamp == timestamp
        assert notif.recipients == ["user1@example.com"]
        assert notif.metadata == {"source": "test"}


class TestInMemoryNotificationChannel:
    """Test suite for InMemoryNotificationChannel."""
    
    @pytest.fixture
    def channel(self):
        """Create an InMemoryNotificationChannel instance."""
        return InMemoryNotificationChannel()
    
    @pytest.mark.asyncio
    async def test_send_notification(self, channel):
        """Test sending a notification."""
        notification = Notification(
            id="test_123",
            type="test",
            title="Test Title",
            message="Hello World",
            data={"message": "Hello"},
            priority=NotificationPriority.MEDIUM,
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await channel.send(notification)
        
        assert result is True
        assert len(channel.notifications) == 1
        assert channel.notifications[0].type == "test"
        assert channel.notifications[0].data == {"message": "Hello"}
        assert channel.notifications[0].priority == NotificationPriority.MEDIUM
    
    def test_get_notifications(self, channel):
        """Test getting notifications."""
        # Add some notifications directly
        notif1 = Notification(
            id="test1",
            type="test1",
            title="Title 1",
            message="Message 1",
            data={},
            priority=NotificationPriority.LOW,
            timestamp=datetime.now(timezone.utc)
        )
        notif2 = Notification(
            id="test2",
            type="test2",
            title="Title 2",
            message="Message 2",
            data={},
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc)
        )
        channel.notifications = [notif1, notif2]
        
        notifications = channel.get_notifications()
        
        assert len(notifications) == 2
        assert notifications[0].type == "test1"
        assert notifications[1].type == "test2"
    
    def test_get_notifications_filtered(self, channel):
        """Test getting filtered notifications."""
        notif1 = Notification(
            id="test1",
            type="test1",
            title="Title 1",
            message="Message 1",
            data={},
            priority=NotificationPriority.LOW,
            timestamp=datetime.now(timezone.utc)
        )
        notif2 = Notification(
            id="test2",
            type="test2",
            title="Title 2",
            message="Message 2",
            data={},
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc)
        )
        channel.notifications = [notif1, notif2]
        
        # Filter by type
        notifications = channel.get_notifications(notification_type="test1")
        assert len(notifications) == 1
        assert notifications[0].type == "test1"
        
        # Filter by priority
        notifications = channel.get_notifications(priority=NotificationPriority.HIGH)
        assert len(notifications) == 1
        assert notifications[0].priority == NotificationPriority.HIGH
    
    def test_clear_notifications(self, channel):
        """Test clearing notifications."""
        notif = Notification(
            id="test",
            type="test",
            title="Title",
            message="Message",
            data={},
            priority=NotificationPriority.LOW,
            timestamp=datetime.now(timezone.utc)
        )
        channel.notifications = [notif]
        
        channel.clear()
        
        assert len(channel.notifications) == 0
    
    def test_supports_type(self, channel):
        """Test supports_type method."""
        assert channel.supports_type("any_type") is True
    
    @pytest.mark.asyncio
    async def test_callback_registration(self, channel):
        """Test callback registration and execution."""
        callback_called = []
        
        def test_callback(notification):
            callback_called.append(notification)
        
        channel.register_callback(test_callback)
        
        notification = Notification(
            id="test_123",
            type="test",
            title="Test Title",
            message="Hello World",
            data={"message": "Hello"},
            priority=NotificationPriority.MEDIUM,
            timestamp=datetime.now(timezone.utc)
        )
        
        await channel.send(notification)
        
        assert len(callback_called) == 1
        assert callback_called[0] == notification


class TestLoggingNotificationChannel:
    """Test suite for LoggingNotificationChannel."""
    
    @pytest.fixture
    def channel(self):
        """Create a LoggingNotificationChannel instance."""
        return LoggingNotificationChannel()
    
    @pytest.mark.asyncio
    async def test_send_notification_low_priority(self, channel):
        """Test sending low priority notification."""
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            notification = Notification(
                id="test_123",
                type="test_info",
                title="Info Title",
                message="Info message",
                data={"message": "Info message"},
                priority=NotificationPriority.LOW,
                timestamp=datetime.now(timezone.utc)
            )
            
            result = await channel.send(notification)
            
            assert result is True
            mock_logger.log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_medium_priority(self, channel):
        """Test sending medium priority notification."""
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            notification = Notification(
                id="test_123",
                type="test_warning",
                title="Warning Title",
                message="Warning message",
                data={"message": "Warning message"},
                priority=NotificationPriority.MEDIUM,
                timestamp=datetime.now(timezone.utc)
            )
            
            result = await channel.send(notification)
            
            assert result is True
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_high_priority(self, channel):
        """Test sending high priority notification."""
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            notification = Notification(
                id="test_123",
                type="test_error",
                title="Error Title",
                message="Error message",
                data={"message": "Error message"},
                priority=NotificationPriority.HIGH,
                timestamp=datetime.now(timezone.utc)
            )
            
            result = await channel.send(notification)
            
            assert result is True
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_urgent_priority(self, channel):
        """Test sending urgent priority notification."""
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            notification = Notification(
                id="test_123",
                type="test_critical",
                title="Critical Title",
                message="Critical message",
                data={"message": "Critical message"},
                priority=NotificationPriority.URGENT,
                timestamp=datetime.now(timezone.utc)
            )
            
            result = await channel.send(notification)
            
            assert result is True
            mock_logger.critical.assert_called_once()
    
    def test_supports_type(self, channel):
        """Test supports_type method."""
        assert channel.supports_type("any_type") is True


class TestFileNotificationChannel:
    """Test suite for FileNotificationChannel."""
    
    @pytest.fixture
    def channel(self):
        """Create a FileNotificationChannel instance with a temporary file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            file_path = f.name
        
        channel = FileNotificationChannel(file_path)
        yield channel
        
        # Cleanup
        if os.path.exists(file_path):
            os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_send_notification(self, channel):
        """Test sending a notification to file."""
        notification = Notification(
            id="test_123",
            type="test_file",
            title="File Title",
            message="File message",
            data={"message": "File message"},
            priority=NotificationPriority.MEDIUM,
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await channel.send(notification)
        
        assert result is True
        
        # Read the file and verify content
        with open(channel.file_path, 'r') as f:
            content = f.read()
            assert "test_file" in content
            assert "File message" in content
            assert "medium" in content
    
    @pytest.mark.asyncio
    async def test_send_multiple_notifications(self, channel):
        """Test sending multiple notifications to file."""
        notif1 = Notification(
            id="test1",
            type="test1",
            title="Title 1",
            message="First message",
            data={"msg": "First"},
            priority=NotificationPriority.LOW,
            timestamp=datetime.now(timezone.utc)
        )
        notif2 = Notification(
            id="test2",
            type="test2",
            title="Title 2",
            message="Second message",
            data={"msg": "Second"},
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(timezone.utc)
        )
        
        await channel.send(notif1)
        await channel.send(notif2)
        
        with open(channel.file_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2
            assert "test1" in lines[0]
            assert "test2" in lines[1]
    
    @pytest.mark.asyncio
    async def test_file_write_error(self):
        """Test handling file write errors."""
        # Create channel with invalid path
        channel = FileNotificationChannel("/invalid/path/notifications.log")
        
        notification = Notification(
            id="test_123",
            type="test",
            title="Test Title",
            message="Test message",
            data={"message": "Test"},
            priority=NotificationPriority.MEDIUM,
            timestamp=datetime.now(timezone.utc)
        )
        
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            result = await channel.send(notification)
            
            assert result is False
            mock_logger.error.assert_called_once()
    
    def test_supports_type(self):
        """Test supports_type method."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            file_path = f.name
        
        try:
            channel = FileNotificationChannel(file_path)
            assert channel.supports_type("any_type") is True
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)


class TestNotificationService:
    """Test suite for NotificationService."""
    
    @pytest.fixture
    def service(self):
        """Create a NotificationService instance."""
        return NotificationService()
    
    @pytest.mark.asyncio
    async def test_initialization(self, service):
        """Test NotificationService initialization."""
        assert len(service.channels) > 0
        # Check that default channels are added
        has_in_memory = any(isinstance(ch, InMemoryNotificationChannel) for ch in service.channels)
        has_logging = any(isinstance(ch, LoggingNotificationChannel) for ch in service.channels)
        assert has_in_memory
        assert has_logging
    
    @pytest.mark.asyncio
    async def test_add_channel(self, service):
        """Test adding a custom channel."""
        custom_channel = Mock(spec=NotificationChannel)
        custom_channel.send = AsyncMock(return_value=True)
        custom_channel.supports_type = Mock(return_value=True)
        
        service.add_channel(custom_channel)
        
        assert custom_channel in service.channels
    
    @pytest.mark.asyncio
    async def test_remove_channel(self, service):
        """Test removing a channel."""
        # Find the logging channel
        logging_channel = None
        for channel in service.channels:
            if isinstance(channel, LoggingNotificationChannel):
                logging_channel = channel
                break
        
        assert logging_channel is not None
        result = service.remove_channel(logging_channel)
        
        assert result is True
        assert logging_channel not in service.channels
    
    @pytest.mark.asyncio
    async def test_notify_all_channels(self, service):
        """Test sending notification to all channels."""
        # Mock all channels
        mock_channels = []
        for i in range(2):
            mock_channel = Mock(spec=NotificationChannel)
            mock_channel.send = AsyncMock(return_value=True)
            mock_channel.supports_type = Mock(return_value=True)
            mock_channels.append(mock_channel)
        
        service.channels = mock_channels
        
        notification_id = await service.notify(
            type="test_all",
            data={"message": "Broadcast"},
            priority="high"
        )
        
        assert notification_id is not None
        
        # Verify all channels were called
        for channel in mock_channels:
            channel.send.assert_called_once()
            # Check that a Notification object was passed
            call_args = channel.send.call_args[0][0]
            assert hasattr(call_args, 'type')
            assert call_args.type == "test_all"
            assert call_args.data == {"message": "Broadcast"}
    
    @pytest.mark.asyncio
    async def test_notify_with_title_and_message(self, service):
        """Test sending notification with custom title and message."""
        # Mock channel
        mock_channel = Mock(spec=NotificationChannel)
        mock_channel.send = AsyncMock(return_value=True)
        mock_channel.supports_type = Mock(return_value=True)
        
        service.channels = [mock_channel]
        
        notification_id = await service.notify(
            type="test_specific",
            data={"message": "Specific"},
            title="Custom Title",
            message="Custom Message",
            priority="medium"
        )
        
        assert notification_id is not None
        mock_channel.send.assert_called_once()
        
        # Check notification details
        call_args = mock_channel.send.call_args[0][0]
        assert call_args.title == "Custom Title"
        assert call_args.message == "Custom Message"
    
    @pytest.mark.asyncio
    async def test_notify_with_retry(self, service):
        """Test notification with retry on failure."""
        # Create a channel that fails first time, succeeds second time
        channel = Mock(spec=NotificationChannel)
        channel.send = AsyncMock(side_effect=[False, True])
        channel.supports_type = Mock(return_value=True)
        
        service.channels = [channel]
        
        notification_id = await service.notify(
            type="test_retry",
            data={"message": "Retry"},
            priority="high"
        )
        
        assert notification_id is not None
        
        # Channel should be called twice (initial + retry)
        assert channel.send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_notify_batch(self, service):
        """Test sending batch notifications."""
        # Mock channel
        mock_channel = Mock(spec=NotificationChannel)
        mock_channel.send = AsyncMock(return_value=True)
        mock_channel.supports_type = Mock(return_value=True)
        
        service.channels = [mock_channel]
        
        notifications = [
            {
                "type": "test1",
                "data": {"msg": "1"},
                "priority": "high"
            },
            {
                "type": "test2",
                "data": {"msg": "2"},
                "priority": "medium"
            }
        ]
        
        notification_ids = await service.notify_batch(notifications)
        
        assert len(notification_ids) == 2
        assert all(isinstance(nid, str) for nid in notification_ids)
        # Both notifications should be sent
        assert mock_channel.send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, service):
        """Test that notifications are dropped after max retries."""
        # Channel that always fails
        channel = Mock(spec=NotificationChannel)
        channel.send = AsyncMock(return_value=False)
        channel.supports_type = Mock(return_value=True)
        
        service.channels = [channel]
        
        with patch('fastmcp.task_management.infrastructure.notification_service.logger') as mock_logger:
            notification_id = await service.notify(
                type="test",
                data={"msg": "fail"},
                priority="high"
            )
            
            # Should log errors for failed retries
            assert channel.send.call_count == 4  # initial + 3 retries
            mock_logger.error.assert_called()
            assert notification_id is not None
    
    @pytest.mark.asyncio
    async def test_get_in_memory_notifications(self, service):
        """Test getting in-memory notifications."""
        # Send some notifications
        await service.notify("test1", {"msg": "1"}, priority="low")
        await service.notify("test2", {"msg": "2"}, priority="high")
        
        notifications = service.get_in_memory_notifications()
        
        assert len(notifications) >= 2
        # Should return Notification objects
        assert all(isinstance(n, Notification) for n in notifications)
    
    @pytest.mark.asyncio
    async def test_get_in_memory_notifications_filtered(self, service):
        """Test getting filtered in-memory notifications."""
        # Send notifications
        await service.notify("type_a", {"msg": "1"}, priority="low")
        await service.notify("type_b", {"msg": "2"}, priority="high")
        await service.notify("type_a", {"msg": "3"}, priority="medium")
        
        # Get in-memory channel
        in_memory_channel = None
        for channel in service.channels:
            if isinstance(channel, InMemoryNotificationChannel):
                in_memory_channel = channel
                break
        
        assert in_memory_channel is not None
        
        # Filter by type
        type_a_notifications = in_memory_channel.get_notifications(notification_type="type_a")
        assert len(type_a_notifications) == 2
        
        # Filter by priority
        high_priority = in_memory_channel.get_notifications(priority=NotificationPriority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0].type == "type_b"
    
    @pytest.mark.asyncio
    async def test_clear_in_memory_notifications(self, service):
        """Test clearing in-memory notifications."""
        # Send some notifications
        await service.notify("test1", {"msg": "1"}, priority="low")
        await service.notify("test2", {"msg": "2"}, priority="high")
        
        service.clear_in_memory_notifications()
        
        notifications = service.get_in_memory_notifications()
        assert len(notifications) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_notifications(self, service):
        """Test sending notifications concurrently."""
        # Mock channels
        mock_channels = []
        for i in range(2):
            mock_channel = Mock(spec=NotificationChannel)
            mock_channel.send = AsyncMock(return_value=True)
            mock_channel.supports_type = Mock(return_value=True)
            mock_channels.append(mock_channel)
        
        service.channels = mock_channels
        
        # Send multiple notifications concurrently
        tasks = []
        for i in range(10):
            tasks.append(service.notify(
                type=f"concurrent_{i}",
                data={"index": i},
                priority="medium"
            ))
        
        notification_ids = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(notification_ids) == 10
        assert all(nid is not None for nid in notification_ids)
        
        # Check that channels were called
        for channel in mock_channels:
            assert channel.send.call_count == 10


class TestNotificationServiceSingleton:
    """Test singleton functionality."""
    
    @pytest.mark.asyncio
    async def test_get_notification_service_singleton(self):
        """Test that get_notification_service returns the same instance."""
        from fastmcp.task_management.infrastructure.notification_service import get_notification_service
        
        service1 = get_notification_service()
        service2 = get_notification_service()
        
        assert service1 is service2