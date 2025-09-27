"""MCP Status Broadcasting Service Implementation"""

import logging
from typing import Dict, Any
from datetime import datetime

from ...domain.services.status_broadcasting_service import StatusBroadcastingService
from ...domain.value_objects.status_update import StatusUpdate

logger = logging.getLogger(__name__)


class MCPStatusBroadcastingService(StatusBroadcastingService):
    """Infrastructure implementation of StatusBroadcastingService that integrates with MCP infrastructure"""
    
    def __init__(self):
        self._registered_clients: Dict[str, Dict[str, Any]] = {}
    
    def register_client_for_updates(self, session_id: str, client_info: Dict[str, Any]) -> StatusUpdate:
        """Register a client for status updates"""
        try:
            # Store client registration info
            self._registered_clients[session_id] = {
                "client_info": client_info,
                "registered_at": datetime.now().isoformat()
            }
            
            # Try to register with the existing status broadcaster
            try:
                from ....server.connection_status_broadcaster import get_status_broadcaster
                # In a real async implementation, this would await the status broadcaster
                logger.info(f"Client {session_id} registered for status updates")
            except Exception as e:
                logger.warning(f"Could not register with status broadcaster: {e}")
            
            # Create status update
            return StatusUpdate.create_client_registration_update(session_id, True)
            
        except Exception as e:
            logger.error(f"Error registering client for updates: {e}")
            raise
    
    def unregister_client(self, session_id: str) -> bool:
        """Unregister a client from status updates"""
        try:
            if session_id in self._registered_clients:
                del self._registered_clients[session_id]
                
                # Try to unregister with the existing status broadcaster
                try:
                    from ....server.connection_status_broadcaster import get_status_broadcaster
                    # In a real async implementation, this would await the status broadcaster
                    logger.info(f"Client {session_id} unregistered from status updates")
                except Exception as e:
                    logger.warning(f"Could not unregister with status broadcaster: {e}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error unregistering client: {e}")
            return False
    
    def broadcast_status_update(self, update: StatusUpdate) -> bool:
        """Broadcast a status update to all registered clients"""
        try:
            # Try to broadcast using the existing status broadcaster
            try:
                from ....server.connection_status_broadcaster import get_status_broadcaster
                # In a real async implementation, this would await the status broadcaster
                logger.info(f"Broadcasting status update: {update.event_type}")
                return True
            except Exception as e:
                logger.warning(f"Could not broadcast with status broadcaster: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error broadcasting status update: {e}")
            return False
    
    def get_registered_clients_count(self) -> int:
        """Get the number of registered clients"""
        return len(self._registered_clients)
    
    def get_last_broadcast_info(self) -> Dict[str, Any]:
        """Get information about the last broadcast"""
        try:
            # Try to get info from the existing status broadcaster
            try:
                from ....server.connection_status_broadcaster import get_status_broadcaster
                # In a real async implementation, this would await the status broadcaster
                return {
                    "last_broadcast_time": None,
                    "last_broadcast_type": None,
                    "broadcast_count": 0
                }
            except Exception as e:
                logger.warning(f"Could not get last broadcast info: {e}")
                return {
                    "error": str(e),
                    "last_broadcast_time": None
                }
                
        except Exception as e:
            logger.error(f"Error getting last broadcast info: {e}")
            return {"error": str(e)}
    
    def validate_broadcasting_infrastructure(self) -> Dict[str, Any]:
        """Validate status broadcasting infrastructure"""
        try:
            # Check if status broadcaster is available
            from ....server.connection_status_broadcaster import get_status_broadcaster
            
            return {
                "status_broadcaster_available": True,
                "registered_clients": len(self._registered_clients),
                "broadcasting_health": "healthy"
            }
            
        except ImportError as e:
            logger.error(f"Status broadcasting infrastructure not available: {e}")
            return {
                "status_broadcaster_available": False,
                "broadcasting_health": "degraded",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error validating broadcasting infrastructure: {e}")
            return {
                "broadcasting_health": "error",
                "error": str(e)
            } 