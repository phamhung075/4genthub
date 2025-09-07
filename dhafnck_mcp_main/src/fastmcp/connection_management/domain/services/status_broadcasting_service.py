"""Status Broadcasting Service Interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..value_objects.status_update import StatusUpdate


class StatusBroadcastingService(ABC):
    """Domain service interface for status broadcasting operations"""
    
    @abstractmethod
    def register_client_for_updates(self, session_id: str, client_info: Dict[str, Any]) -> StatusUpdate:
        """Register a client for status updates"""
        pass
    
    @abstractmethod
    def unregister_client(self, session_id: str) -> bool:
        """Unregister a client from status updates"""
        pass
    
    @abstractmethod
    def broadcast_status_update(self, update: StatusUpdate) -> bool:
        """Broadcast a status update to all registered clients"""
        pass
    
    @abstractmethod
    def get_registered_clients_count(self) -> int:
        """Get the number of registered clients"""
        pass
    
    @abstractmethod
    def get_last_broadcast_info(self) -> Dict[str, Any]:
        """Get information about the last broadcast"""
        pass
    
    @abstractmethod
    def validate_broadcasting_infrastructure(self) -> Dict[str, Any]:
        """Validate status broadcasting infrastructure"""
        pass 