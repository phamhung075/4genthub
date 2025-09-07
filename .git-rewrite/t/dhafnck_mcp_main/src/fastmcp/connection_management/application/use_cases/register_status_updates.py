"""Register Status Updates Use Case"""

import logging
from datetime import datetime

from ..dtos.connection_dtos import RegisterUpdatesRequest, RegisterUpdatesResponse
from ...domain.services.status_broadcasting_service import StatusBroadcastingService
from ...domain.value_objects.status_update import StatusUpdate

logger = logging.getLogger(__name__)


class RegisterStatusUpdatesUseCase:
    """Use case for registering clients for status updates"""
    
    def __init__(self, broadcasting_service: StatusBroadcastingService):
        self._broadcasting_service = broadcasting_service
    
    def execute(self, request: RegisterUpdatesRequest) -> RegisterUpdatesResponse:
        """Execute the register status updates use case"""
        try:
            # Prepare client info
            client_info = request.client_info or {}
            client_info.update({
                "session_id": request.session_id,
                "registered_at": datetime.now().isoformat()
            })
            
            # Register client for updates
            status_update = self._broadcasting_service.register_client_for_updates(
                request.session_id, client_info
            )
            
            # Get broadcasting info
            clients_count = self._broadcasting_service.get_registered_clients_count()
            last_broadcast = self._broadcasting_service.get_last_broadcast_info()
            
            update_info = {
                "registered_clients": clients_count,
                "last_broadcast": last_broadcast,
                "registration_time": status_update.timestamp.isoformat(),
                "event_type": status_update.event_type
            }
            
            return RegisterUpdatesResponse(
                success=True,
                session_id=request.session_id,
                registered=True,
                update_info=update_info
            )
            
        except Exception as e:
            logger.error(f"Error registering for status updates: {e}")
            return RegisterUpdatesResponse(
                success=False,
                session_id=request.session_id,
                registered=False,
                update_info={},
                error=str(e)
            ) 