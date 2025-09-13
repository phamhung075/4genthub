"""Real-time Status Tracking Service for Agent Coordination

This service provides real-time monitoring and tracking of agent status,
workload, and performance metrics across the system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json

from ...domain.entities.agent_session import AgentSession, SessionState
from ...domain.value_objects.coordination import AgentCommunication
from ...domain.events.agent_events import AgentStatusBroadcast
from ...infrastructure.event_bus import EventBus

logger = logging.getLogger(__name__)


class StatusUpdateType(Enum):
    """Types of status updates"""
    HEARTBEAT = "heartbeat"
    STATE_CHANGE = "state_change"
    TASK_UPDATE = "task_update"
    RESOURCE_UPDATE = "resource_update"
    PERFORMANCE_UPDATE = "performance_update"
    ERROR_REPORT = "error_report"
    RECOVERY_NOTICE = "recovery_notice"


@dataclass
class StatusSnapshot:
    """Point-in-time status snapshot for an agent"""
    agent_id: str
    session_id: str
    timestamp: datetime
    state: SessionState
    health_score: float
    active_tasks: List[str]
    resource_usage: Dict[str, float]
    performance_metrics: Dict[str, Any]
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatusSubscription:
    """Subscription for status updates"""
    subscription_id: str
    subscriber_id: str
    agent_patterns: List[str]  # Agent ID patterns to subscribe to
    update_types: Set[StatusUpdateType]
    callback: Optional[Callable] = None
    webhook_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


class RealTimeStatusTracker:
    """
    Real-time status tracking service for agent coordination.
    
    Features:
    - Live agent status monitoring
    - Performance metric collection
    - Health score calculation
    - Status change notifications
    - Historical status tracking
    - Anomaly detection
    """
    
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        history_retention_hours: int = 24,
        snapshot_interval_seconds: int = 30,
        anomaly_threshold: float = 0.8
    ):
        """Initialize the status tracker"""
        self.event_bus = event_bus
        self.history_retention_hours = history_retention_hours
        self.snapshot_interval_seconds = snapshot_interval_seconds
        self.anomaly_threshold = anomaly_threshold
        
        # Active sessions tracking
        self.active_sessions: Dict[str, AgentSession] = {}
        self.session_by_agent: Dict[str, str] = {}  # agent_id -> session_id
        
        # Status history
        self.status_history: Dict[str, List[StatusSnapshot]] = {}  # agent_id -> snapshots
        self.max_history_size = 1000  # Per agent
        
        # Subscriptions
        self.subscriptions: Dict[str, StatusSubscription] = {}
        
        # Performance tracking
        self.performance_baselines: Dict[str, Dict[str, float]] = {}  # agent_id -> metrics
        self.anomaly_counts: Dict[str, int] = {}  # agent_id -> count
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self) -> None:
        """Start the status tracking service"""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._monitor_sessions())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_history())
        
        logger.info("Real-time status tracker started")
    
    async def stop(self) -> None:
        """Stop the status tracking service"""
        self._is_running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time status tracker stopped")
    
    async def register_session(self, session: AgentSession) -> None:
        """Register a new agent session for tracking"""
        self.active_sessions[session.session_id] = session
        self.session_by_agent[session.agent_id] = session.session_id
        
        # Initialize status history
        if session.agent_id not in self.status_history:
            self.status_history[session.agent_id] = []
        
        # Take initial snapshot
        snapshot = self._create_snapshot(session)
        await self._record_snapshot(snapshot)
        
        # Notify subscribers
        await self._notify_status_change(
            session.agent_id,
            StatusUpdateType.STATE_CHANGE,
            {"new_state": "session_started", "session_id": session.session_id}
        )
        
        logger.info(f"Registered session {session.session_id} for agent {session.agent_id}")
    
    async def unregister_session(self, session_id: str) -> None:
        """Unregister an agent session"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        agent_id = session.agent_id
        
        # Take final snapshot
        snapshot = self._create_snapshot(session)
        snapshot.metadata["final_snapshot"] = True
        await self._record_snapshot(snapshot)
        
        # Clean up
        del self.active_sessions[session_id]
        if agent_id in self.session_by_agent:
            del self.session_by_agent[agent_id]
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.STATE_CHANGE,
            {"new_state": "session_ended", "session_id": session_id}
        )
        
        logger.info(f"Unregistered session {session_id} for agent {agent_id}")
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: SessionState,
        current_task_id: Optional[str] = None,
        current_activity: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update agent status in real-time"""
        session_id = self.session_by_agent.get(agent_id)
        if not session_id or session_id not in self.active_sessions:
            logger.warning(f"No active session for agent {agent_id}")
            return
        
        session = self.active_sessions[session_id]
        
        # Update session state based on status
        session.state = status
        
        # Update activity
        if current_task_id:
            if current_task_id not in session.active_tasks:
                session.start_task(current_task_id)
        
        if metadata:
            session.metadata.update(metadata)
        
        # Update heartbeat
        session.update_heartbeat()
        
        # Take snapshot if significant change
        snapshot = self._create_snapshot(session)
        await self._record_snapshot(snapshot)
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.STATE_CHANGE,
            {
                "status": status.value,
                "current_task": current_task_id,
                "activity": current_activity
            }
        )
    
    async def report_task_progress(
        self,
        agent_id: str,
        task_id: str,
        progress_percentage: float,
        status: str,
        details: Optional[str] = None
    ) -> None:
        """Report task progress update"""
        session_id = self.session_by_agent.get(agent_id)
        if not session_id:
            return
        
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Update session metrics
        if status == "completed":
            session.complete_task(task_id, success=True)
        elif status == "failed":
            session.complete_task(task_id, success=False)
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.TASK_UPDATE,
            {
                "task_id": task_id,
                "progress": progress_percentage,
                "status": status,
                "details": details
            }
        )
    
    async def report_resource_usage(
        self,
        agent_id: str,
        resource_type: str,
        used_amount: float,
        allocated_amount: float,
        resource_id: Optional[str] = None
    ) -> None:
        """Report resource usage update"""
        session_id = self.session_by_agent.get(agent_id)
        if not session_id:
            return
        
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Update resource usage
        from ...domain.entities.agent_session import ResourceType
        try:
            res_type = ResourceType(resource_type)
            session.update_resource_usage(res_type, used_amount, resource_id)
        except ValueError:
            logger.warning(f"Unknown resource type: {resource_type}")
        
        # Check for anomalies
        usage_percentage = (used_amount / allocated_amount * 100) if allocated_amount > 0 else 0
        if usage_percentage > self.anomaly_threshold * 100:
            await self._detect_anomaly(
                agent_id,
                "high_resource_usage",
                {
                    "resource_type": resource_type,
                    "usage_percentage": usage_percentage
                }
            )
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.RESOURCE_UPDATE,
            {
                "resource_type": resource_type,
                "usage": used_amount,
                "allocated": allocated_amount,
                "percentage": usage_percentage
            }
        )
    
    async def report_error(
        self,
        agent_id: str,
        error_type: str,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report an error from an agent"""
        session_id = self.session_by_agent.get(agent_id)
        if not session_id:
            return
        
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Update error metrics
        session.metrics["error_count"] += 1
        session.metadata["last_error"] = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": error_context
        }
        
        # Check if recovery needed
        if session.needs_recovery():
            await self._initiate_recovery(session)
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.ERROR_REPORT,
            {
                "error_type": error_type,
                "error_message": error_message,
                "error_count": session.metrics["error_count"]
            }
        )
    
    async def get_agent_status(self, agent_id: str) -> Optional[StatusSnapshot]:
        """Get current status for an agent"""
        session_id = self.session_by_agent.get(agent_id)
        if not session_id:
            return None
        
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return self._create_snapshot(session)
    
    async def get_all_agent_statuses(self) -> Dict[str, StatusSnapshot]:
        """Get current status for all active agents"""
        statuses = {}
        for session in self.active_sessions.values():
            statuses[session.agent_id] = self._create_snapshot(session)
        return statuses
    
    async def get_agent_history(
        self,
        agent_id: str,
        hours: Optional[int] = None
    ) -> List[StatusSnapshot]:
        """Get status history for an agent"""
        if agent_id not in self.status_history:
            return []
        
        history = self.status_history[agent_id]
        
        if hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            return [s for s in history if s.timestamp >= cutoff]
        
        return history.copy()
    
    async def subscribe_to_updates(
        self,
        subscriber_id: str,
        agent_patterns: List[str],
        update_types: Optional[Set[StatusUpdateType]] = None,
        callback: Optional[Callable] = None,
        webhook_url: Optional[str] = None
    ) -> str:
        """Subscribe to status updates"""
        if not update_types:
            update_types = set(StatusUpdateType)
        
        subscription = StatusSubscription(
            subscription_id=f"sub_{subscriber_id}_{datetime.now(timezone.utc).timestamp()}",
            subscriber_id=subscriber_id,
            agent_patterns=agent_patterns,
            update_types=update_types,
            callback=callback,
            webhook_url=webhook_url
        )
        
        self.subscriptions[subscription.subscription_id] = subscription
        
        logger.info(f"Created subscription {subscription.subscription_id} for {subscriber_id}")
        return subscription.subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from status updates"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = False
            del self.subscriptions[subscription_id]
            logger.info(f"Removed subscription {subscription_id}")
    
    def _create_snapshot(self, session: AgentSession) -> StatusSnapshot:
        """Create a status snapshot from session"""
        return StatusSnapshot(
            agent_id=session.agent_id,
            session_id=session.session_id,
            timestamp=datetime.now(timezone.utc),
            state=session.state,
            health_score=session.calculate_health_score(),
            active_tasks=list(session.active_tasks),
            resource_usage=session.get_resource_usage_summary(),
            performance_metrics={
                "messages_sent": session.metrics["messages_sent"],
                "messages_received": session.metrics["messages_received"],
                "tasks_completed": session.metrics["tasks_completed"],
                "tasks_failed": session.metrics["tasks_failed"],
                "error_count": session.metrics["error_count"],
                "avg_response_time_ms": session.metrics["avg_response_time_ms"]
            },
            last_error=session.metadata.get("last_error", {}).get("message"),
            metadata={
                "project_id": session.project_id,
                "uptime_seconds": (datetime.now(timezone.utc) - session.started_at).total_seconds()
            }
        )
    
    async def _record_snapshot(self, snapshot: StatusSnapshot) -> None:
        """Record a status snapshot"""
        agent_id = snapshot.agent_id
        
        if agent_id not in self.status_history:
            self.status_history[agent_id] = []
        
        history = self.status_history[agent_id]
        history.append(snapshot)
        
        # Maintain history size limit
        if len(history) > self.max_history_size:
            self.status_history[agent_id] = history[-self.max_history_size:]
    
    async def _notify_status_change(
        self,
        agent_id: str,
        update_type: StatusUpdateType,
        data: Dict[str, Any]
    ) -> None:
        """Notify subscribers of status change"""
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
            
            # Check if agent matches patterns
            matches = any(
                self._matches_pattern(agent_id, pattern)
                for pattern in subscription.agent_patterns
            )
            
            if not matches:
                continue
            
            # Check if update type is subscribed
            if update_type not in subscription.update_types:
                continue
            
            # Prepare notification
            notification = {
                "subscription_id": subscription.subscription_id,
                "agent_id": agent_id,
                "update_type": update_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            
            # Send notification
            if subscription.callback:
                try:
                    await subscription.callback(notification)
                except Exception as e:
                    logger.error(f"Error in subscription callback: {e}")
            
            if subscription.webhook_url:
                # Queue webhook delivery (not implemented here)
                pass
    
    def _matches_pattern(self, agent_id: str, pattern: str) -> bool:
        """Check if agent ID matches pattern"""
        if pattern == "*":
            return True
        if pattern == agent_id:
            return True
        if pattern.endswith("*") and agent_id.startswith(pattern[:-1]):
            return True
        return False
    
    async def _detect_anomaly(
        self,
        agent_id: str,
        anomaly_type: str,
        details: Dict[str, Any]
    ) -> None:
        """Detect and handle anomalies"""
        self.anomaly_counts[agent_id] = self.anomaly_counts.get(agent_id, 0) + 1
        
        logger.warning(
            f"Anomaly detected for agent {agent_id}: {anomaly_type} - {details}"
        )
        
        # Notify subscribers
        await self._notify_status_change(
            agent_id,
            StatusUpdateType.PERFORMANCE_UPDATE,
            {
                "anomaly_type": anomaly_type,
                "anomaly_count": self.anomaly_counts[agent_id],
                "details": details
            }
        )
        
        # Trigger recovery if threshold exceeded
        if self.anomaly_counts[agent_id] > 5:
            session_id = self.session_by_agent.get(agent_id)
            if session_id:
                session = self.active_sessions.get(session_id)
                if session:
                    await self._initiate_recovery(session)
    
    async def _initiate_recovery(self, session: AgentSession) -> None:
        """Initiate recovery for a session"""
        logger.info(f"Initiating recovery for session {session.session_id}")
        
        try:
            session.recover()
            
            # Reset anomaly count
            if session.agent_id in self.anomaly_counts:
                self.anomaly_counts[session.agent_id] = 0
            
            # Notify subscribers
            await self._notify_status_change(
                session.agent_id,
                StatusUpdateType.RECOVERY_NOTICE,
                {
                    "recovery_count": session.metrics["recovery_count"],
                    "health_score": session.calculate_health_score()
                }
            )
        except Exception as e:
            logger.error(f"Recovery failed for session {session.session_id}: {e}")
    
    async def _monitor_sessions(self) -> None:
        """Background task to monitor sessions"""
        while self._is_running:
            try:
                # Check all active sessions
                for session in list(self.active_sessions.values()):
                    # Check if session is alive
                    if not session.is_alive():
                        await self.unregister_session(session.session_id)
                        continue
                    
                    # Check if session expired
                    if session.is_expired():
                        session.terminate("Session expired")
                        await self.unregister_session(session.session_id)
                        continue
                    
                    # Check if session is idle
                    if session.is_idle():
                        await self._notify_status_change(
                            session.agent_id,
                            StatusUpdateType.STATE_CHANGE,
                            {"new_state": "idle", "idle_time": session.max_idle_time}
                        )
                    
                    # Take periodic snapshot
                    snapshot = self._create_snapshot(session)
                    await self._record_snapshot(snapshot)
                
                # Wait for next interval
                await asyncio.sleep(self.snapshot_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in session monitoring: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _cleanup_old_history(self) -> None:
        """Background task to cleanup old history"""
        while self._is_running:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=self.history_retention_hours)
                
                for agent_id in list(self.status_history.keys()):
                    history = self.status_history[agent_id]
                    # Keep only recent history
                    self.status_history[agent_id] = [
                        s for s in history if s.timestamp >= cutoff
                    ]
                    
                    # Remove empty histories
                    if not self.status_history[agent_id]:
                        del self.status_history[agent_id]
                
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in history cleanup: {e}")
                await asyncio.sleep(300)  # 5 minutes before retry
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tracker metrics"""
        return {
            "active_sessions": len(self.active_sessions),
            "tracked_agents": len(self.session_by_agent),
            "active_subscriptions": len([s for s in self.subscriptions.values() if s.active]),
            "history_entries": sum(len(h) for h in self.status_history.values()),
            "anomaly_agents": len(self.anomaly_counts),
            "total_anomalies": sum(self.anomaly_counts.values())
        }