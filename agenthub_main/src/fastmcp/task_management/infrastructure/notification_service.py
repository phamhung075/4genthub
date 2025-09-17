"""Notification Service infrastructure for sending notifications.

This module provides notification capabilities for the Vision System,
supporting multiple notification channels and delivery mechanisms.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Protocol, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    MILESTONE_REACHED = "milestone_reached"
    PROGRESS_STALLED = "progress_stalled"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    PROGRESS_TYPE_COMPLETED = "progress_type_completed"
    BLOCKER_DETECTED = "blocker_detected"
    AGENT_REASSIGNED = "agent_reassigned"


@dataclass
class Notification:
    """Represents a notification to be sent."""
    id: str
    type: str
    title: str
    message: str
    data: Dict[str, Any]
    priority: NotificationPriority
    timestamp: datetime
    recipients: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """
        Send a notification through this channel.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def supports_type(self, notification_type: str) -> bool:
        """
        Check if this channel supports a notification type.
        
        Args:
            notification_type: The type to check
            
        Returns:
            True if supported, False otherwise
        """
        pass


class InMemoryNotificationChannel(NotificationChannel):
    """In-memory notification channel for testing and development."""
    
    def __init__(self):
        """Initialize the in-memory channel."""
        self.notifications: List[Notification] = []
        self.callbacks: List[Any] = []
        
    async def send(self, notification: Notification) -> bool:
        """Send notification to in-memory storage."""
        self.notifications.append(notification)
        
        # Trigger callbacks
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")
        
        logger.debug(f"Stored notification {notification.id} in memory")
        return True
    
    def supports_type(self, notification_type: str) -> bool:
        """In-memory channel supports all types."""
        return True
    
    def register_callback(self, callback: Any) -> None:
        """Register a callback for notifications."""
        self.callbacks.append(callback)
    
    def get_notifications(self, 
                         notification_type: Optional[str] = None,
                         priority: Optional[NotificationPriority] = None) -> List[Notification]:
        """Get stored notifications with optional filtering."""
        notifications = self.notifications
        
        if notification_type:
            notifications = [n for n in notifications if n.type == notification_type]
            
        if priority:
            notifications = [n for n in notifications if n.priority == priority]
            
        return notifications
    
    def clear(self) -> None:
        """Clear all stored notifications."""
        self.notifications.clear()


class LoggingNotificationChannel(NotificationChannel):
    """Notification channel that logs to the application logger."""
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize the logging channel.
        
        Args:
            log_level: The log level to use for notifications
        """
        self.log_level = log_level
        
    async def send(self, notification: Notification) -> bool:
        """Send notification to logger."""
        log_message = (
            f"[{notification.priority.value.upper()}] "
            f"{notification.type}: {notification.title} - {notification.message}"
        )
        
        if notification.priority == NotificationPriority.URGENT:
            logger.critical(log_message)
        elif notification.priority == NotificationPriority.HIGH:
            logger.error(log_message)
        elif notification.priority == NotificationPriority.MEDIUM:
            logger.warning(log_message)
        else:
            logger.log(self.log_level, log_message)
            
        return True
    
    def supports_type(self, notification_type: str) -> bool:
        """Logging channel supports all types."""
        return True


class FileNotificationChannel(NotificationChannel):
    """Notification channel that writes to a file."""
    
    def __init__(self, file_path: str):
        """
        Initialize the file channel.
        
        Args:
            file_path: Path to the notification log file
        """
        self.file_path = file_path
        
    async def send(self, notification: Notification) -> bool:
        """Send notification to file."""
        try:
            notification_dict = {
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'priority': notification.priority.value,
                'timestamp': notification.timestamp.isoformat(),
                'recipients': notification.recipients,
                'metadata': notification.metadata
            }
            
            # Append to file
            with open(self.file_path, 'a') as f:
                f.write(json.dumps(notification_dict) + '\n')
                
            return True
        except Exception as e:
            logger.error(f"Failed to write notification to file: {e}")
            return False
    
    def supports_type(self, notification_type: str) -> bool:
        """File channel supports all types."""
        return True


class NotificationService:
    """
    Service for managing and sending notifications.
    
    Supports multiple channels, priority handling, and retry logic.
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self.channels: List[NotificationChannel] = []
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Add default channels
        self.add_channel(InMemoryNotificationChannel())
        self.add_channel(LoggingNotificationChannel())
        
    def add_channel(self, channel: NotificationChannel) -> None:
        """
        Add a notification channel.
        
        Args:
            channel: The channel to add
        """
        self.channels.append(channel)
        logger.debug(f"Added notification channel: {channel.__class__.__name__}")
    
    def remove_channel(self, channel: NotificationChannel) -> bool:
        """
        Remove a notification channel.
        
        Args:
            channel: The channel to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            self.channels.remove(channel)
            logger.debug(f"Removed notification channel: {channel.__class__.__name__}")
            return True
        except ValueError:
            return False
    
    async def notify(self, 
                    type: str,
                    data: Dict[str, Any],
                    title: Optional[str] = None,
                    message: Optional[str] = None,
                    priority: str = "medium",
                    recipients: Optional[List[str]] = None) -> str:
        """
        Send a notification.
        
        Args:
            type: The notification type
            data: Notification data
            title: Optional notification title
            message: Optional notification message
            priority: Notification priority
            recipients: Optional list of recipients
            
        Returns:
            The notification ID
        """
        import uuid
        
        # Generate notification ID
        notification_id = str(uuid.uuid4())
        
        # Create title and message if not provided
        if not title:
            title = self._generate_title(type, data)
        if not message:
            message = self._generate_message(type, data)
        
        # Create notification
        notification = Notification(
            id=notification_id,
            type=type,
            title=title,
            message=message,
            data=data,
            priority=NotificationPriority(priority),
            timestamp=datetime.now(timezone.utc),
            recipients=recipients,
            metadata={'source': 'notification_service'}
        )
        
        # Send through appropriate channels
        await self._send_notification(notification)
        
        return notification_id
    
    async def _send_notification(self, notification: Notification) -> None:
        """Send notification through all appropriate channels."""
        sent_count = 0
        
        for channel in self.channels:
            if channel.supports_type(notification.type):
                try:
                    success = await channel.send(notification)
                    if success:
                        sent_count += 1
                except Exception as e:
                    logger.error(
                        f"Error sending notification through {channel.__class__.__name__}: {e}"
                    )
        
        if sent_count == 0 and notification.retry_count < notification.max_retries:
            # Retry if no channels succeeded
            notification.retry_count += 1
            await asyncio.sleep(2 ** notification.retry_count)  # Exponential backoff
            await self._send_notification(notification)
        elif sent_count == 0:
            logger.error(f"Failed to send notification {notification.id} after {notification.max_retries} retries")
        else:
            logger.debug(f"Notification {notification.id} sent through {sent_count} channel(s)")
    
    def _generate_title(self, type: str, data: Dict[str, Any]) -> str:
        """Generate a title based on notification type."""
        titles = {
            "milestone_reached": "Milestone Reached",
            "progress_stalled": "Progress Stalled",
            "task_assigned": "Task Assigned",
            "task_completed": "Task Completed",
            "progress_type_completed": "Progress Type Completed",
            "blocker_detected": "Blocker Detected",
            "agent_reassigned": "Agent Reassigned"
        }
        
        return titles.get(type, f"Notification: {type}")
    
    def _generate_message(self, type: str, data: Dict[str, Any]) -> str:
        """Generate a message based on notification type and data."""
        if type == "milestone_reached":
            return f"Milestone '{data.get('milestone', 'Unknown')}' reached at {data.get('progress', 0)}%"
        elif type == "progress_stalled":
            return f"No progress for {data.get('duration_hours', 0):.1f} hours at {data.get('current_progress', 0)}%"
        elif type == "task_assigned":
            return f"Task {data.get('task_id', 'Unknown')} assigned to {data.get('assignee', 'Unknown')}"
        elif type == "task_completed":
            return f"Task {data.get('task_id', 'Unknown')} completed"
        elif type == "progress_type_completed":
            return f"Progress type {data.get('progress_type', 'Unknown')} completed"
        elif type == "blocker_detected":
            blockers = data.get('blockers', [])
            return f"Detected {len(blockers)} blocker(s): {', '.join(blockers[:3])}"
        elif type == "agent_reassigned":
            return f"Agent {data.get('agent_id', 'Unknown')} reassigned from {data.get('from', 'N/A')} to {data.get('to', 'N/A')}"
        else:
            return json.dumps(data)[:200]  # Truncate if too long
    
    async def notify_batch(self, notifications: List[Dict[str, Any]]) -> List[str]:
        """
        Send multiple notifications.
        
        Args:
            notifications: List of notification parameters
            
        Returns:
            List of notification IDs
        """
        ids = []
        for notif_params in notifications:
            notif_id = await self.notify(**notif_params)
            ids.append(notif_id)
        return ids
    
    async def start_processing(self) -> None:
        """Start processing notifications from the queue."""
        if self._processing_task is None or self._processing_task.done():
            self._shutdown = False
            self._processing_task = asyncio.create_task(self._process_notification_queue())
            logger.info("Notification service processing started")
    
    async def stop_processing(self) -> None:
        """Stop processing notifications."""
        self._shutdown = True
        if self._processing_task and not self._processing_task.done():
            await self._notification_queue.put(None)  # Sentinel
            await self._processing_task
            logger.info("Notification service processing stopped")
    
    async def _process_notification_queue(self) -> None:
        """Process notifications from the queue."""
        while not self._shutdown:
            try:
                notification = await self._notification_queue.get()
                if notification is None:  # Sentinel
                    break
                    
                await self._send_notification(notification)
                
            except Exception as e:
                logger.error(f"Error processing notification from queue: {e}", exc_info=True)
    
    async def queue_notification(self, notification: Notification) -> None:
        """
        Queue a notification for async processing.
        
        Args:
            notification: The notification to queue
        """
        await self._notification_queue.put(notification)
    
    def get_in_memory_notifications(self) -> List[Notification]:
        """Get notifications from in-memory channel if available."""
        for channel in self.channels:
            if isinstance(channel, InMemoryNotificationChannel):
                return channel.get_notifications()
        return []
    
    def clear_in_memory_notifications(self) -> None:
        """Clear notifications from in-memory channel if available."""
        for channel in self.channels:
            if isinstance(channel, InMemoryNotificationChannel):
                channel.clear()
    
    def __repr__(self) -> str:
        """String representation of the notification service."""
        return f"NotificationService(channels={len(self.channels)})"


# Global notification service instance
_global_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _global_notification_service
    if _global_notification_service is None:
        _global_notification_service = NotificationService()
    return _global_notification_service


def reset_notification_service() -> None:
    """Reset the global notification service (mainly for testing)."""
    global _global_notification_service
    _global_notification_service = None