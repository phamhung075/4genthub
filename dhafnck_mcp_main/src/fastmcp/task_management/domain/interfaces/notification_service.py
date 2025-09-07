"""Notification Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


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
    def metadata(self) -> Dict[str, Any]:
        """Get the notification metadata"""
        pass


class INotificationService(ABC):
    """Domain interface for notification operations"""
    
    @abstractmethod
    async def send_notification(self, notification: INotification) -> bool:
        """Send a notification"""
        pass
    
    @abstractmethod
    async def send_bulk_notifications(self, notifications: List[INotification]) -> List[bool]:
        """Send multiple notifications"""
        pass
    
    @abstractmethod
    async def schedule_notification(self, notification: INotification, delay_seconds: int) -> str:
        """Schedule a notification to be sent later"""
        pass
    
    @abstractmethod
    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification"""
        pass
    
    @abstractmethod
    def create_notification(self, 
                          notification_type: NotificationType,
                          recipient: str, 
                          message: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> INotification:
        """Create a notification object"""
        pass