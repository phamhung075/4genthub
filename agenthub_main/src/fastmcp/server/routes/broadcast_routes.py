"""
HTTP routes for triggering WebSocket broadcasts from external processes.
This allows MCP server to notify API server about data changes.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

# Import the broadcast function
from .websocket_routes import broadcast_data_change

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/broadcast",
    tags=["broadcast"]
)


class BroadcastRequest(BaseModel):
    """Request model for broadcast endpoint"""
    event_type: str
    entity_type: str
    entity_id: str
    user_id: str
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/notify")
async def trigger_broadcast(request: BroadcastRequest):
    """
    HTTP endpoint to trigger WebSocket broadcast.
    This allows external processes (like MCP server) to notify about data changes.
    """
    try:
        logger.info(f"HTTP broadcast trigger: {request.entity_type} {request.event_type}")

        # Call the WebSocket broadcast function
        await broadcast_data_change(
            event_type=request.event_type,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            user_id=request.user_id,
            data=request.data,
            metadata=request.metadata
        )

        return {"status": "broadcast_sent", "entity_type": request.entity_type, "event_type": request.event_type}

    except Exception as e:
        logger.error(f"Failed to trigger broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))