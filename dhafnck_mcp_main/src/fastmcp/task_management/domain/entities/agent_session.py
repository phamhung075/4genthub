"""Agent Session Entity for Real-time Coordination

This entity manages active agent sessions, tracking their state, resource usage,
and communication channels for real-time coordination.
"""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..value_objects.agents import AgentStatus
from ..value_objects.coordination import CoordinationMessage
from ..exceptions.base import DomainException


class SessionState(Enum):
    """Agent session states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    TERMINATED = "terminated"


class ResourceType(Enum):
    """Types of resources an agent can hold"""
    DATABASE_CONNECTION = "database_connection"
    FILE_LOCK = "file_lock"
    API_QUOTA = "api_quota"
    MEMORY_ALLOCATION = "memory_allocation"
    CPU_THREAD = "cpu_thread"


@dataclass
class ResourceUsage:
    """Track resource usage for an agent session"""
    resource_type: ResourceType
    allocated_amount: float
    used_amount: float
    allocation_time: datetime
    resource_id: Optional[str] = None
    
    @property
    def usage_percentage(self) -> float:
        """Calculate resource usage percentage"""
        if self.allocated_amount == 0:
            return 0.0
        return (self.used_amount / self.allocated_amount) * 100
    
    def is_overutilized(self, threshold: float = 90.0) -> bool:
        """Check if resource is over-utilized"""
        return self.usage_percentage > threshold


@dataclass
class CommunicationChannel:
    """Communication channel for agent-to-agent messaging"""
    channel_id: str
    channel_type: str  # websocket, message_queue, direct
    created_at: datetime
    participants: List[str]  # agent_ids
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentSession:
    """
    Agent Session entity for managing real-time agent coordination.
    
    This entity tracks:
    - Session lifecycle (initialization, active, termination)
    - Resource allocation and usage
    - Communication channels
    - Performance metrics
    - Session health and recovery
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        agent_id: str = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        heartbeat_interval: int = 30,  # seconds
        max_idle_time: int = 300,  # 5 minutes
        max_session_duration: Optional[int] = None  # seconds
    ):
        """Initialize agent session"""
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.user_id = user_id
        self.project_id = project_id
        self.started_at = started_at or datetime.now(timezone.utc)
        self.state = SessionState.INITIALIZING
        self.last_heartbeat = datetime.now(timezone.utc)
        self.heartbeat_interval = heartbeat_interval
        self.max_idle_time = max_idle_time
        self.max_session_duration = max_session_duration
        
        # Session tracking
        self.active_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Resource management
        self.resources: Dict[str, ResourceUsage] = {}
        self.resource_locks: Set[str] = set()
        
        # Communication
        self.channels: Dict[str, CommunicationChannel] = {}
        self.pending_messages: List[CoordinationMessage] = []
        self.message_history: List[CoordinationMessage] = []
        
        # Performance metrics
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_response_time_ms": 0,
            "total_processing_time_ms": 0,
            "error_count": 0,
            "recovery_count": 0
        }
        
        # Session metadata
        self.metadata: Dict[str, Any] = {}
    
    def activate(self) -> None:
        """Activate the session"""
        if self.state != SessionState.INITIALIZING:
            raise DomainException(
                f"Cannot activate session in state {self.state.value}"
            )
        self.state = SessionState.ACTIVE
        self.update_heartbeat()
    
    def update_heartbeat(self) -> None:
        """Update session heartbeat"""
        self.last_heartbeat = datetime.now(timezone.utc)
        if self.state == SessionState.IDLE:
            self.state = SessionState.ACTIVE
    
    def is_alive(self) -> bool:
        """Check if session is still alive based on heartbeat"""
        if self.state in [SessionState.DISCONNECTED, SessionState.TERMINATED]:
            return False
        
        time_since_heartbeat = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
        return time_since_heartbeat < self.heartbeat_interval * 2  # Allow 2x interval
    
    def is_expired(self) -> bool:
        """Check if session has exceeded maximum duration"""
        if not self.max_session_duration:
            return False
        
        session_duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return session_duration > self.max_session_duration
    
    def is_idle(self) -> bool:
        """Check if session is idle"""
        if not self.active_tasks:
            time_since_heartbeat = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
            return time_since_heartbeat > self.max_idle_time
        return False
    
    def start_task(self, task_id: str) -> None:
        """Mark task as started"""
        self.active_tasks.add(task_id)
        self.state = SessionState.BUSY
        self.update_heartbeat()
    
    def complete_task(self, task_id: str, success: bool = True) -> None:
        """Mark task as completed"""
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)

        if success:
            self.completed_tasks.add(task_id)
            self.metrics["tasks_completed"] += 1
        else:
            self.failed_tasks.add(task_id)
            self.metrics["tasks_failed"] += 1

        # Update heartbeat first
        self.last_heartbeat = datetime.now(timezone.utc)

        # Then determine state based on active tasks
        if not self.active_tasks:
            self.state = SessionState.IDLE
        else:
            self.state = SessionState.BUSY
    
    def allocate_resource(
        self,
        resource_type: ResourceType,
        amount: float,
        resource_id: Optional[str] = None
    ) -> ResourceUsage:
        """Allocate resource to session"""
        resource = ResourceUsage(
            resource_type=resource_type,
            allocated_amount=amount,
            used_amount=0,
            allocation_time=datetime.now(timezone.utc),
            resource_id=resource_id
        )
        
        key = f"{resource_type.value}_{resource_id or 'default'}"
        self.resources[key] = resource
        
        if resource_id:
            self.resource_locks.add(resource_id)
        
        return resource
    
    def update_resource_usage(
        self,
        resource_type: ResourceType,
        used_amount: float,
        resource_id: Optional[str] = None
    ) -> None:
        """Update resource usage"""
        key = f"{resource_type.value}_{resource_id or 'default'}"
        if key in self.resources:
            self.resources[key].used_amount = used_amount
    
    def release_resource(
        self,
        resource_type: ResourceType,
        resource_id: Optional[str] = None
    ) -> None:
        """Release allocated resource"""
        key = f"{resource_type.value}_{resource_id or 'default'}"
        if key in self.resources:
            del self.resources[key]
        
        if resource_id and resource_id in self.resource_locks:
            self.resource_locks.remove(resource_id)
    
    def get_resource_usage_summary(self) -> Dict[str, float]:
        """Get summary of resource usage"""
        summary = {}
        for resource_type in ResourceType:
            total_allocated = 0
            total_used = 0
            
            for key, usage in self.resources.items():
                if usage.resource_type == resource_type:
                    total_allocated += usage.allocated_amount
                    total_used += usage.used_amount
            
            if total_allocated > 0:
                summary[resource_type.value] = (total_used / total_allocated) * 100
        
        return summary
    
    def open_channel(
        self,
        channel_id: str,
        channel_type: str,
        participants: List[str]
    ) -> CommunicationChannel:
        """Open a communication channel"""
        channel = CommunicationChannel(
            channel_id=channel_id,
            channel_type=channel_type,
            created_at=datetime.now(timezone.utc),
            participants=participants
        )
        self.channels[channel_id] = channel
        return channel
    
    def close_channel(self, channel_id: str) -> None:
        """Close a communication channel"""
        if channel_id in self.channels:
            self.channels[channel_id].is_active = False
    
    def add_message(self, message: CoordinationMessage, is_outgoing: bool = True) -> None:
        """Add message to session history"""
        self.message_history.append(message)

        if is_outgoing:
            self.metrics["messages_sent"] += 1
        else:
            self.metrics["messages_received"] += 1

        # Keep history size manageable - trim to 500 when exceeding 500
        if len(self.message_history) > 500:
            self.message_history = self.message_history[-500:]  # Keep last 500
    
    def get_active_channels(self) -> List[CommunicationChannel]:
        """Get list of active channels"""
        return [
            channel for channel in self.channels.values()
            if channel.is_active
        ]
    
    def calculate_health_score(self) -> float:
        """
        Calculate session health score (0-100)
        
        Based on:
        - Resource utilization
        - Error rate
        - Task success rate
        - Response time
        """
        score = 100.0
        
        # Resource utilization impact (max -30 points)
        resource_summary = self.get_resource_usage_summary()
        if resource_summary:
            avg_usage = sum(resource_summary.values()) / len(resource_summary)
            if avg_usage > 90:
                score -= 30
            elif avg_usage > 75:
                score -= 20
            elif avg_usage > 60:
                score -= 10
        
        # Error rate impact (max -30 points)
        total_operations = (
            self.metrics["tasks_completed"] + 
            self.metrics["tasks_failed"] +
            self.metrics["messages_sent"]
        )
        if total_operations > 0:
            error_rate = self.metrics["error_count"] / total_operations
            score -= min(error_rate * 100, 30)
        
        # Task success rate impact (max -20 points)
        total_tasks = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        if total_tasks > 0:
            failure_rate = self.metrics["tasks_failed"] / total_tasks
            score -= min(failure_rate * 40, 20)
        
        # Session duration impact (max -20 points)
        if self.max_session_duration:
            duration_percentage = (
                (datetime.now(timezone.utc) - self.started_at).total_seconds() /
                self.max_session_duration
            ) * 100
            if duration_percentage > 90:
                score -= 20
            elif duration_percentage > 75:
                score -= 10
        
        return max(0, score)
    
    def needs_recovery(self) -> bool:
        """Check if session needs recovery"""
        return (
            self.calculate_health_score() < 50 or
            self.metrics["error_count"] > 10 or
            not self.is_alive()
        )
    
    def recover(self) -> None:
        """Attempt to recover session"""
        self.metrics["recovery_count"] += 1
        self.metrics["error_count"] = 0  # Reset error count
        self.state = SessionState.ACTIVE
        self.update_heartbeat()
        
        # Clear pending messages that might be causing issues
        self.pending_messages.clear()
        
        # Reset any overloaded resources
        for resource in self.resources.values():
            if resource.is_overutilized():
                resource.used_amount = resource.allocated_amount * 0.5
    
    def terminate(self, reason: str = "Normal termination") -> None:
        """Terminate session"""
        self.state = SessionState.TERMINATED
        
        # Close all channels
        for channel_id in list(self.channels.keys()):
            self.close_channel(channel_id)
        
        # Release all resources
        for resource_id in list(self.resource_locks):
            self.resource_locks.remove(resource_id)
        
        self.resources.clear()
        self.metadata["termination_reason"] = reason
        self.metadata["terminated_at"] = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "active_tasks": list(self.active_tasks),
            "completed_tasks_count": len(self.completed_tasks),
            "failed_tasks_count": len(self.failed_tasks),
            "health_score": self.calculate_health_score(),
            "metrics": self.metrics,
            "resource_usage": self.get_resource_usage_summary(),
            "active_channels": len(self.get_active_channels()),
            "is_alive": self.is_alive(),
            "is_expired": self.is_expired(),
            "metadata": self.metadata
        }