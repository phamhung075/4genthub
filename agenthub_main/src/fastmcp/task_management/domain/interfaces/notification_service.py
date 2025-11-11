"""Notification Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class NotificationType(Enum):
    """Types of notifications"""

    EMAIL = "email"
    WEBHOOK = "webhook"
    INTERNAL = "internal"
    PUSH = "push"


class INotification(ABC):
    """Domain interface for notifications"""

    @property
    @abstractmethod
    def notification_type(self) -> NotificationType:
        """Get the notification type"""
        pass

    @property
    @abstractmethod
    def recipient(self) -> str:
        """Get the notification recipient"""
        pass

    @property
    @abstractmethod
    def message(self) -> str:
        """Get the notification message"""
        pass

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Get the notification metadata"""
        pass


class INotificationService(ABC):
    """Domain interface for notification operations"""

    @abstractmethod
    async def send_notification(self, notification: INotification) -> bool:
        """Send a notification"""
        pass

    @abstractmethod
    async def send_bulk_notifications(
        self, notifications: list[INotification]
    ) -> list[bool]:
        """Send multiple notifications"""
        pass

    @abstractmethod
    async def schedule_notification(
        self, notification: INotification, delay_seconds: int
    ) -> str:
        """Schedule a notification to be sent later"""
        pass

    @abstractmethod
    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification"""
        pass

    @abstractmethod
    def create_notification(
        self,
        notification_type: NotificationType,
        recipient: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> INotification:
        """Create a notification object"""
        pass
