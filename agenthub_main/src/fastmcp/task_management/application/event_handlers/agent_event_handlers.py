"""
Event handlers for agent-related domain events.

This module processes agent coordination events, workload management,
handoff workflows, and agent performance tracking.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ...domain.events.agent_events import (
    AgentAssigned,
    AgentCollaborationEnded,
    AgentCollaborationStarted,
    AgentCommunicationSent,
    AgentEscalationRaised,
    AgentEscalationResolved,
    AgentPerformanceEvaluated,
    AgentStatusBroadcast,
    AgentUnassigned,
    AgentWorkloadChanged,
    AgentWorkloadRebalanced,
    ConflictDetected,
    ConflictResolved,
    WorkHandoffAccepted,
    WorkHandoffCompleted,
    WorkHandoffRejected,
    WorkHandoffRequested,
)
from ...domain.events.base import BaseDomainEvent
from ...infrastructure.event_store import EventStore

logger = logging.getLogger(__name__)


class AgentEventHandlers:
    """
    Handles agent-related domain events.

    Processes events to coordinate agents, manage workloads,
    track performance, and enable collaboration.
    """

    def __init__(
        self,
        event_store: EventStore,
        agent_repository: Any | None = None,
        coordination_service: Any | None = None
    ):
        self.event_store = event_store
        self.agent_repository = agent_repository
        self.coordination_service = coordination_service

        # Agent statistics tracking
        self.agent_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "assignments": 0,
                "unassignments": 0,
                "handoffs_requested": 0,
                "handoffs_completed": 0,
                "conflicts": 0,
                "escalations": 0,
                "communications": 0
            }
        )

        # Workload tracking
        self.agent_workloads: dict[str, dict[str, Any]] = {}

        # Collaboration tracking
        self.active_collaborations: dict[str, list[str]] = defaultdict(list)

        # Performance tracking
        self.performance_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def handle_agent_assigned(self, event: AgentAssigned) -> None:
        """
        Handle agent assigned event.

        Updates workload tracking and notifies the agent.
        """
        logger.info(
            f"Agent assigned: {event.agent_id} to task {event.task_id} "
            f"(role: {event.role if hasattr(event, 'role') else 'worker'})"
        )

        # Update statistics
        self.agent_stats[str(event.agent_id)]["assignments"] += 1

        # Update workload
        if str(event.agent_id) not in self.agent_workloads:
            self.agent_workloads[str(event.agent_id)] = {
                "active_tasks": [],
                "total_assignments": 0,
                "last_updated": datetime.now(UTC)
            }

        self.agent_workloads[str(event.agent_id)]["active_tasks"].append(str(event.task_id))
        self.agent_workloads[str(event.agent_id)]["total_assignments"] += 1
        self.agent_workloads[str(event.agent_id)]["last_updated"] = event.occurred_at

        # Notify coordination service
        if self.coordination_service:
            await self.coordination_service.notify_agent_assigned(
                agent_id=event.agent_id,
                task_id=event.task_id,
                role=getattr(event, 'role', 'worker')
            )

    async def handle_agent_unassigned(self, event: AgentUnassigned) -> None:
        """
        Handle agent unassigned event.

        Updates workload tracking and frees up agent capacity.
        """
        logger.info(
            f"Agent unassigned: {event.agent_id} from task {event.task_id} "
            f"(reason: {event.reason if hasattr(event, 'reason') else 'not specified'})"
        )

        # Update statistics
        self.agent_stats[str(event.agent_id)]["unassignments"] += 1

        # Update workload
        if str(event.agent_id) in self.agent_workloads:
            workload = self.agent_workloads[str(event.agent_id)]
            if str(event.task_id) in workload["active_tasks"]:
                workload["active_tasks"].remove(str(event.task_id))
            workload["last_updated"] = event.occurred_at

        # Notify coordination service
        if self.coordination_service:
            await self.coordination_service.notify_agent_freed(
                agent_id=event.agent_id,
                task_id=event.task_id
            )

    async def handle_agent_workload_changed(self, event: AgentWorkloadChanged) -> None:
        """
        Handle agent workload changed event.

        Updates workload metrics and triggers rebalancing if needed.
        """
        logger.info(
            f"Agent workload changed: {event.agent_id} - "
            f"new load: {event.new_workload_level}"
        )

        # Update workload tracking
        self.agent_workloads[str(event.agent_id)] = {
            "workload_level": event.new_workload_level,
            "previous_level": event.previous_workload_level,
            "active_tasks": getattr(event, 'active_tasks', []),
            "last_updated": event.occurred_at
        }

        # Check if rebalancing is needed
        if event.new_workload_level > 0.8:  # 80% threshold
            logger.warning(
                f"Agent {event.agent_id} is overloaded ({event.new_workload_level:.0%})"
            )
            if self.coordination_service:
                await self.coordination_service.trigger_workload_rebalancing(
                    overloaded_agent=event.agent_id,
                    workload_level=event.new_workload_level
                )

    async def handle_work_handoff_requested(self, event: WorkHandoffRequested) -> None:
        """
        Handle work handoff requested event.

        Initiates handoff workflow and finds suitable agent.
        """
        logger.info(
            f"Work handoff requested: from {event.from_agent_id} to {event.to_agent_id} "
            f"for task {event.task_id} (reason: {event.reason})"
        )

        # Update statistics
        self.agent_stats[str(event.from_agent_id)]["handoffs_requested"] += 1

        # Process handoff through coordination service
        if self.coordination_service:
            await self.coordination_service.process_handoff_request(
                from_agent=event.from_agent_id,
                to_agent=event.to_agent_id,
                task_id=event.task_id,
                reason=event.reason,
                context=getattr(event, 'handoff_context', {})
            )

    async def handle_work_handoff_accepted(self, event: WorkHandoffAccepted) -> None:
        """
        Handle work handoff accepted event.

        Completes handoff process and transfers context.
        """
        logger.info(
            f"Work handoff accepted: {event.to_agent_id} accepted task {event.task_id} "
            f"from {event.from_agent_id}"
        )

        if self.coordination_service:
            await self.coordination_service.complete_handoff(
                from_agent=event.from_agent_id,
                to_agent=event.to_agent_id,
                task_id=event.task_id
            )

    async def handle_work_handoff_rejected(self, event: WorkHandoffRejected) -> None:
        """
        Handle work handoff rejected event.

        Finds alternative agent or escalates.
        """
        logger.warning(
            f"Work handoff rejected: {event.to_agent_id} rejected task {event.task_id} "
            f"from {event.from_agent_id} (reason: {event.rejection_reason})"
        )

        if self.coordination_service:
            await self.coordination_service.handle_handoff_rejection(
                from_agent=event.from_agent_id,
                rejected_by=event.to_agent_id,
                task_id=event.task_id,
                reason=event.rejection_reason
            )

    async def handle_work_handoff_completed(self, event: WorkHandoffCompleted) -> None:
        """
        Handle work handoff completed event.

        Finalizes handoff and updates tracking.
        """
        logger.info(
            f"Work handoff completed: task {event.task_id} transferred from "
            f"{event.from_agent_id} to {event.to_agent_id}"
        )

        # Update statistics
        self.agent_stats[str(event.from_agent_id)]["handoffs_completed"] += 1

    async def handle_conflict_detected(self, event: ConflictDetected) -> None:
        """
        Handle conflict detected event.

        Initiates conflict resolution workflow.
        """
        logger.warning(
            f"Conflict detected: between agents {', '.join(map(str, event.involved_agents))} "
            f"(type: {event.conflict_type})"
        )

        # Update statistics
        for agent_id in event.involved_agents:
            self.agent_stats[str(agent_id)]["conflicts"] += 1

        # Trigger conflict resolution
        if self.coordination_service:
            await self.coordination_service.initiate_conflict_resolution(
                agents=event.involved_agents,
                conflict_type=event.conflict_type,
                description=event.conflict_description
            )

    async def handle_conflict_resolved(self, event: ConflictResolved) -> None:
        """
        Handle conflict resolved event.

        Records resolution and applies learnings.
        """
        logger.info(
            f"Conflict resolved: between agents {', '.join(map(str, event.involved_agents))} "
            f"(resolution: {event.resolution_strategy})"
        )

        # Store resolution for future learning
        if self.coordination_service:
            await self.coordination_service.record_conflict_resolution(
                agents=event.involved_agents,
                conflict_id=event.conflict_id,
                strategy=event.resolution_strategy,
                outcome=getattr(event, 'outcome', 'resolved')
            )

    async def handle_agent_collaboration_started(self, event: AgentCollaborationStarted) -> None:
        """
        Handle agent collaboration started event.

        Sets up collaboration context and tracking.
        """
        logger.info(
            f"Collaboration started: {', '.join(map(str, event.participating_agents))} "
            f"on task {event.task_id} (type: {event.collaboration_type})"
        )

        # Track active collaboration
        collaboration_id = str(event.task_id)
        self.active_collaborations[collaboration_id] = [
            str(agent) for agent in event.participating_agents
        ]

        if self.coordination_service:
            await self.coordination_service.setup_collaboration(
                agents=event.participating_agents,
                task_id=event.task_id,
                collaboration_type=event.collaboration_type
            )

    async def handle_agent_collaboration_ended(self, event: AgentCollaborationEnded) -> None:
        """
        Handle agent collaboration ended event.

        Finalizes collaboration and captures learnings.
        """
        logger.info(
            f"Collaboration ended: {', '.join(map(str, event.participating_agents))} "
            f"on task {event.task_id} (outcome: {event.outcome})"
        )

        # Remove from active collaborations
        collaboration_id = str(event.task_id)
        if collaboration_id in self.active_collaborations:
            del self.active_collaborations[collaboration_id]

        if self.coordination_service:
            await self.coordination_service.finalize_collaboration(
                agents=event.participating_agents,
                task_id=event.task_id,
                outcome=event.outcome
            )

    async def handle_agent_status_broadcast(self, event: AgentStatusBroadcast) -> None:
        """
        Handle agent status broadcast event.

        Updates agent availability and status tracking.
        """
        logger.debug(
            f"Agent status broadcast: {event.agent_id} - {event.status}"
        )

        # Update agent status
        if str(event.agent_id) in self.agent_workloads:
            self.agent_workloads[str(event.agent_id)]["status"] = event.status
            self.agent_workloads[str(event.agent_id)]["last_broadcast"] = event.occurred_at

    async def handle_agent_workload_rebalanced(self, event: AgentWorkloadRebalanced) -> None:
        """
        Handle agent workload rebalanced event.

        Records rebalancing actions and updates metrics.
        """
        logger.info(
            f"Agent workload rebalanced: {len(event.affected_agents)} agents affected"
        )

        # Record rebalancing strategy
        if self.coordination_service:
            await self.coordination_service.record_rebalancing(
                agents=event.affected_agents,
                strategy=event.rebalancing_strategy,
                tasks_moved=getattr(event, 'tasks_moved', [])
            )

    async def handle_agent_escalation_raised(self, event: AgentEscalationRaised) -> None:
        """
        Handle agent escalation raised event.

        Routes escalation to appropriate authority.
        """
        logger.warning(
            f"Escalation raised by {event.raised_by_agent_id}: {event.escalation_reason} "
            f"(severity: {event.severity})"
        )

        # Update statistics
        self.agent_stats[str(event.raised_by_agent_id)]["escalations"] += 1

        # Route escalation
        if self.coordination_service:
            await self.coordination_service.handle_escalation(
                raised_by=event.raised_by_agent_id,
                task_id=getattr(event, 'task_id', None),
                reason=event.escalation_reason,
                severity=event.severity
            )

    async def handle_agent_escalation_resolved(self, event: AgentEscalationResolved) -> None:
        """
        Handle agent escalation resolved event.

        Records resolution and applies learnings.
        """
        logger.info(
            f"Escalation resolved: {event.escalation_id} "
            f"(resolution: {event.resolution_summary})"
        )

        if self.coordination_service:
            await self.coordination_service.record_escalation_resolution(
                escalation_id=event.escalation_id,
                resolution=event.resolution_summary,
                resolved_by=event.resolved_by_agent_id
            )

    async def handle_agent_communication_sent(self, event: AgentCommunicationSent) -> None:
        """
        Handle agent communication sent event.

        Tracks inter-agent communication patterns.
        """
        logger.debug(
            f"Communication sent: from {event.sender_agent_id} to {event.recipient_agent_id} "
            f"(type: {event.communication_type})"
        )

        # Update statistics
        self.agent_stats[str(event.sender_agent_id)]["communications"] += 1

    async def handle_agent_performance_evaluated(self, event: AgentPerformanceEvaluated) -> None:
        """
        Handle agent performance evaluated event.

        Records performance metrics and trends.
        """
        logger.info(
            f"Performance evaluated for {event.agent_id}: score {event.performance_score} "
            f"(period: {event.evaluation_period})"
        )

        # Store performance history
        performance_record = {
            "agent_id": str(event.agent_id),
            "score": event.performance_score,
            "metrics": event.performance_metrics,
            "period": event.evaluation_period,
            "timestamp": event.occurred_at.isoformat()
        }
        self.performance_history[str(event.agent_id)].append(performance_record)

        # Keep only last 30 evaluations per agent
        if len(self.performance_history[str(event.agent_id)]) > 30:
            self.performance_history[str(event.agent_id)] = (
                self.performance_history[str(event.agent_id)][-30:]
            )

    async def get_agent_statistics(self, agent_id: UUID | None = None) -> dict[str, Any]:
        """
        Get agent statistics for a specific agent or all agents.

        Args:
            agent_id: Optional agent ID to filter statistics

        Returns:
            Dictionary containing agent statistics
        """
        if agent_id:
            agent_key = str(agent_id)
            stats = self.agent_stats.get(agent_key, {})
            workload = self.agent_workloads.get(agent_key, {})
            performance = self.performance_history.get(agent_key, [])

            return {
                "agent_id": agent_key,
                "statistics": dict(stats),
                "workload": workload,
                "performance_history": performance[-5:] if performance else []
            }

        # Aggregate across all agents
        return {
            "total_agents": len(self.agent_stats),
            "active_collaborations": len(self.active_collaborations),
            "statistics_by_agent": {k: dict(v) for k, v in self.agent_stats.items()},
            "workload_summary": {
                "total_active_tasks": sum(
                    len(w.get("active_tasks", [])) for w in self.agent_workloads.values()
                ),
                "average_workload": (
                    sum(w.get("workload_level", 0) for w in self.agent_workloads.values()) /
                    max(len(self.agent_workloads), 1)
                ) if self.agent_workloads else 0.0
            }
        }

    async def process_event(self, event: BaseDomainEvent) -> None:
        """
        Process a domain event.

        Routes events to appropriate handlers.
        """
        handlers = {
            "agent_assigned": self.handle_agent_assigned,
            "agent_unassigned": self.handle_agent_unassigned,
            "agent_workload_changed": self.handle_agent_workload_changed,
            "work_handoff_requested": self.handle_work_handoff_requested,
            "work_handoff_accepted": self.handle_work_handoff_accepted,
            "work_handoff_rejected": self.handle_work_handoff_rejected,
            "work_handoff_completed": self.handle_work_handoff_completed,
            "conflict_detected": self.handle_conflict_detected,
            "conflict_resolved": self.handle_conflict_resolved,
            "agent_collaboration_started": self.handle_agent_collaboration_started,
            "agent_collaboration_ended": self.handle_agent_collaboration_ended,
            "agent_status_broadcast": self.handle_agent_status_broadcast,
            "agent_workload_rebalanced": self.handle_agent_workload_rebalanced,
            "agent_escalation_raised": self.handle_agent_escalation_raised,
            "agent_escalation_resolved": self.handle_agent_escalation_resolved,
            "agent_communication_sent": self.handle_agent_communication_sent,
            "agent_performance_evaluated": self.handle_agent_performance_evaluated,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"No handler for event type: {event.event_type}")
