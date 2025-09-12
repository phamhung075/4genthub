"""WebSocket-based Agent Communication Hub

This module provides real-time bidirectional communication between agents
using WebSocket connections for low-latency message passing and status updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from ....domain.value_objects.coordination import (
    AgentCommunication, CoordinationMessage
)
from ....domain.entities.agent_session import AgentSession
from ...application.services.real_time_status_tracker import RealTimeStatusTracker

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    ACK = "acknowledge"
    
    # Status updates
    STATUS_UPDATE = "status_update"
    RESOURCE_UPDATE = "resource_update"
    TASK_UPDATE = "task_update"
    
    # Coordination
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"
    WORK_HANDOFF = "work_handoff"
    
    # Communication
    DIRECT_MESSAGE = "direct_message"
    BROADCAST_MESSAGE = "broadcast_message"
    GROUP_MESSAGE = "group_message"
    
    # Notifications
    NOTIFICATION = "notification"
    ALERT = "alert"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """Standard WebSocket message format"""
    id: str
    type: MessageType
    from_agent: str
    to_agents: List[str]  # Empty for broadcast
    timestamp: datetime
    payload: Dict[str, Any]
    requires_ack: bool = False
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for transmission"""
        data = asdict(self)
        data["type"] = self.type.value
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        data["type"] = MessageType(data["type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class AgentConnection:
    """Active agent WebSocket connection"""
    agent_id: str
    session_id: str
    websocket: WebSocket
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str] = None  # Channel subscriptions
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()
    
    async def send_message(self, message: WebSocketMessage) -> bool:
        """Send message through WebSocket"""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_text(message.to_json())
                return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.agent_id}: {e}")
        return False
    
    def is_alive(self, timeout_seconds: int = 60) -> bool:
        """Check if connection is still alive"""
        elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds


class AgentCommunicationHub:
    """
    WebSocket-based communication hub for real-time agent coordination.
    
    Features:
    - WebSocket connection management
    - Real-time message routing
    - Channel-based communication
    - Status broadcasting
    - Message acknowledgment
    - Connection health monitoring
    """
    
    def __init__(
        self,
        status_tracker: Optional[RealTimeStatusTracker] = None,
        heartbeat_interval: int = 30,
        message_timeout: int = 30
    ):
        """Initialize the communication hub"""
        self.status_tracker = status_tracker
        self.heartbeat_interval = heartbeat_interval
        self.message_timeout = message_timeout
        
        # Connection management
        self.connections: Dict[str, AgentConnection] = {}
        self.sessions: Dict[str, AgentSession] = {}
        
        # Message handling
        self.pending_acks: Dict[str, WebSocketMessage] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # Channels for group communication
        self.channels: Dict[str, Set[str]] = {
            "global": set(),  # All connected agents
            "status": set(),  # Status update subscribers
            "coordination": set()  # Coordination subscribers
        }
        
        # Metrics
        self.metrics = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "avg_latency_ms": 0
        }
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self) -> None:
        """Start the communication hub"""
        if self._is_running:
            return
        
        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Agent communication hub started")
    
    async def stop(self) -> None:
        """Stop the communication hub"""
        self._is_running = False
        
        # Cancel background tasks
        for task in [self._heartbeat_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all connections
        for connection in list(self.connections.values()):
            await self.disconnect_agent(connection.agent_id)
        
        logger.info("Agent communication hub stopped")
    
    async def connect_agent(
        self,
        agent_id: str,
        session_id: str,
        websocket: WebSocket
    ) -> None:
        """Connect an agent to the hub"""
        await websocket.accept()
        
        # Create connection
        connection = AgentConnection(
            agent_id=agent_id,
            session_id=session_id,
            websocket=websocket,
            connected_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow()
        )
        
        self.connections[agent_id] = connection
        self.metrics["total_connections"] += 1
        
        # Add to global channel
        self.channels["global"].add(agent_id)
        
        # Send connection confirmation
        welcome_msg = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.CONNECT,
            from_agent="hub",
            to_agents=[agent_id],
            timestamp=datetime.utcnow(),
            payload={
                "status": "connected",
                "session_id": session_id,
                "hub_version": "1.0.0",
                "available_channels": list(self.channels.keys())
            }
        )
        
        await connection.send_message(welcome_msg)
        
        # Notify other agents
        await self.broadcast_to_channel(
            "global",
            MessageType.NOTIFICATION,
            {
                "event": "agent_connected",
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude=[agent_id]
        )
        
        logger.info(f"Agent {agent_id} connected with session {session_id}")
    
    async def disconnect_agent(self, agent_id: str) -> None:
        """Disconnect an agent from the hub"""
        if agent_id not in self.connections:
            return
        
        connection = self.connections[agent_id]
        
        # Close WebSocket
        try:
            if connection.websocket.client_state == WebSocketState.CONNECTED:
                await connection.websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket for {agent_id}: {e}")
        
        # Remove from channels
        for channel_agents in self.channels.values():
            channel_agents.discard(agent_id)
        
        # Remove connection
        del self.connections[agent_id]
        
        # Notify other agents
        await self.broadcast_to_channel(
            "global",
            MessageType.NOTIFICATION,
            {
                "event": "agent_disconnected",
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Agent {agent_id} disconnected")
    
    async def handle_agent_connection(
        self,
        websocket: WebSocket,
        agent_id: str,
        session_id: str
    ) -> None:
        """Handle agent WebSocket connection lifecycle"""
        try:
            # Connect agent
            await self.connect_agent(agent_id, session_id, websocket)
            
            # Handle messages
            while self._is_running:
                try:
                    # Receive message with timeout
                    message_text = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self.heartbeat_interval * 2
                    )
                    
                    # Process message
                    await self.process_message(agent_id, message_text)
                    
                except asyncio.TimeoutError:
                    # Send heartbeat ping
                    if agent_id in self.connections:
                        await self.send_heartbeat(agent_id)
                    
                except WebSocketDisconnect:
                    break
                    
                except Exception as e:
                    logger.error(f"Error handling message from {agent_id}: {e}")
                    
        finally:
            # Ensure disconnection
            await self.disconnect_agent(agent_id)
    
    async def process_message(self, from_agent: str, message_text: str) -> None:
        """Process incoming WebSocket message"""
        try:
            message = WebSocketMessage.from_json(message_text)
            self.metrics["messages_received"] += 1
            
            # Update heartbeat
            if from_agent in self.connections:
                self.connections[from_agent].last_heartbeat = datetime.utcnow()
            
            # Handle acknowledgments
            if message.type == MessageType.ACK:
                await self.handle_acknowledgment(message)
                return
            
            # Route message based on type
            if message.type == MessageType.HEARTBEAT:
                # Heartbeat already updated above
                pass
                
            elif message.type == MessageType.STATUS_UPDATE:
                await self.handle_status_update(from_agent, message)
                
            elif message.type == MessageType.DIRECT_MESSAGE:
                await self.route_direct_message(message)
                
            elif message.type == MessageType.BROADCAST_MESSAGE:
                await self.route_broadcast_message(message)
                
            elif message.type == MessageType.GROUP_MESSAGE:
                await self.route_group_message(message)
                
            elif message.type == MessageType.COORDINATION_REQUEST:
                await self.handle_coordination_request(message)
                
            else:
                # Call registered handlers
                await self.call_message_handlers(message.type, message)
            
            # Send acknowledgment if required
            if message.requires_ack:
                await self.send_acknowledgment(from_agent, message.id)
                
        except Exception as e:
            logger.error(f"Error processing message from {from_agent}: {e}")
            await self.send_error(from_agent, str(e))
    
    async def send_message(
        self,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        requires_ack: bool = False,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send message to specific agent"""
        if to_agent not in self.connections:
            logger.warning(f"Agent {to_agent} not connected")
            return False
        
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=message_type,
            from_agent="hub",
            to_agents=[to_agent],
            timestamp=datetime.utcnow(),
            payload=payload,
            requires_ack=requires_ack,
            correlation_id=correlation_id
        )
        
        success = await self.connections[to_agent].send_message(message)
        
        if success:
            self.metrics["messages_sent"] += 1
            
            if requires_ack:
                self.pending_acks[message.id] = message
                # TODO: Implement timeout handling for acks
        else:
            self.metrics["messages_failed"] += 1
        
        return success
    
    async def broadcast_message(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> int:
        """Broadcast message to all connected agents"""
        if exclude is None:
            exclude = []
        
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=message_type,
            from_agent="hub",
            to_agents=[],  # Empty for broadcast
            timestamp=datetime.utcnow(),
            payload=payload,
            requires_ack=False
        )
        
        sent_count = 0
        for agent_id, connection in self.connections.items():
            if agent_id not in exclude:
                if await connection.send_message(message):
                    sent_count += 1
        
        self.metrics["messages_sent"] += sent_count
        return sent_count
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> int:
        """Broadcast message to channel subscribers"""
        if channel not in self.channels:
            logger.warning(f"Unknown channel: {channel}")
            return 0
        
        if exclude is None:
            exclude = []
        
        sent_count = 0
        for agent_id in self.channels[channel]:
            if agent_id not in exclude and agent_id in self.connections:
                if await self.send_message(agent_id, message_type, payload):
                    sent_count += 1
        
        return sent_count
    
    async def subscribe_to_channel(self, agent_id: str, channel: str) -> bool:
        """Subscribe agent to a channel"""
        if agent_id not in self.connections:
            return False
        
        if channel not in self.channels:
            self.channels[channel] = set()
        
        self.channels[channel].add(agent_id)
        self.connections[agent_id].subscriptions.add(channel)
        
        # Notify agent
        await self.send_message(
            agent_id,
            MessageType.NOTIFICATION,
            {
                "event": "channel_subscribed",
                "channel": channel
            }
        )
        
        return True
    
    async def unsubscribe_from_channel(self, agent_id: str, channel: str) -> bool:
        """Unsubscribe agent from a channel"""
        if channel in self.channels:
            self.channels[channel].discard(agent_id)
        
        if agent_id in self.connections:
            self.connections[agent_id].subscriptions.discard(channel)
        
        return True
    
    def register_message_handler(
        self,
        message_type: MessageType,
        handler: Callable
    ) -> None:
        """Register handler for message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    async def call_message_handlers(
        self,
        message_type: MessageType,
        message: WebSocketMessage
    ) -> None:
        """Call registered handlers for message type"""
        if message_type in self.message_handlers:
            for handler in self.message_handlers[message_type]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
    
    async def handle_status_update(
        self,
        from_agent: str,
        message: WebSocketMessage
    ) -> None:
        """Handle status update from agent"""
        if self.status_tracker:
            payload = message.payload
            await self.status_tracker.update_agent_status(
                from_agent,
                payload.get("status"),
                payload.get("current_task_id"),
                payload.get("current_activity"),
                payload.get("metadata")
            )
        
        # Broadcast to status channel
        await self.broadcast_to_channel(
            "status",
            MessageType.STATUS_UPDATE,
            {
                "agent_id": from_agent,
                **message.payload
            },
            exclude=[from_agent]
        )
    
    async def handle_coordination_request(
        self,
        message: WebSocketMessage
    ) -> None:
        """Handle coordination request between agents"""
        payload = message.payload
        target_agent = payload.get("target_agent")
        
        if target_agent and target_agent in self.connections:
            # Forward to target agent
            await self.send_message(
                target_agent,
                MessageType.COORDINATION_REQUEST,
                payload,
                requires_ack=True,
                correlation_id=message.id
            )
        
        # Broadcast to coordination channel
        await self.broadcast_to_channel(
            "coordination",
            MessageType.NOTIFICATION,
            {
                "event": "coordination_request",
                "from_agent": message.from_agent,
                "to_agent": target_agent,
                "type": payload.get("coordination_type")
            }
        )
    
    async def route_direct_message(self, message: WebSocketMessage) -> None:
        """Route direct message to target agent"""
        for target in message.to_agents:
            if target in self.connections:
                await self.connections[target].send_message(message)
    
    async def route_broadcast_message(self, message: WebSocketMessage) -> None:
        """Route broadcast message to all agents"""
        await self.broadcast_message(
            MessageType.BROADCAST_MESSAGE,
            message.payload,
            exclude=[message.from_agent]
        )
    
    async def route_group_message(self, message: WebSocketMessage) -> None:
        """Route message to group of agents"""
        channel = message.payload.get("channel")
        if channel:
            await self.broadcast_to_channel(
                channel,
                MessageType.GROUP_MESSAGE,
                message.payload,
                exclude=[message.from_agent]
            )
    
    async def send_heartbeat(self, agent_id: str) -> None:
        """Send heartbeat to agent"""
        await self.send_message(
            agent_id,
            MessageType.HEARTBEAT,
            {"timestamp": datetime.utcnow().isoformat()},
            requires_ack=True
        )
    
    async def send_acknowledgment(self, to_agent: str, message_id: str) -> None:
        """Send acknowledgment for message"""
        await self.send_message(
            to_agent,
            MessageType.ACK,
            {"ack_message_id": message_id}
        )
    
    async def handle_acknowledgment(self, message: WebSocketMessage) -> None:
        """Handle message acknowledgment"""
        ack_id = message.payload.get("ack_message_id")
        if ack_id in self.pending_acks:
            del self.pending_acks[ack_id]
    
    async def send_error(self, to_agent: str, error_message: str) -> None:
        """Send error message to agent"""
        await self.send_message(
            to_agent,
            MessageType.ERROR,
            {"error": error_message}
        )
    
    async def _heartbeat_loop(self) -> None:
        """Background task to send heartbeats"""
        while self._is_running:
            try:
                # Send heartbeat to all connections
                for agent_id in list(self.connections.keys()):
                    await self.send_heartbeat(agent_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup dead connections"""
        while self._is_running:
            try:
                # Check for dead connections
                dead_agents = []
                for agent_id, connection in self.connections.items():
                    if not connection.is_alive():
                        dead_agents.append(agent_id)
                
                # Disconnect dead agents
                for agent_id in dead_agents:
                    logger.warning(f"Removing dead connection for {agent_id}")
                    await self.disconnect_agent(agent_id)
                
                # Cleanup pending acks
                # TODO: Implement ack timeout handling
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            "active_connections": len(self.connections),
            "agents": list(self.connections.keys()),
            "channels": {
                channel: len(agents)
                for channel, agents in self.channels.items()
            },
            "pending_acks": len(self.pending_acks),
            "metrics": self.metrics
        }
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about connected agent"""
        if agent_id not in self.connections:
            return None
        
        connection = self.connections[agent_id]
        return {
            "agent_id": agent_id,
            "session_id": connection.session_id,
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "subscriptions": list(connection.subscriptions),
            "is_alive": connection.is_alive()
        }