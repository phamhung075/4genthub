"""Agent Coordination Service for Multi-Agent Task Management"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
import logging

from ...domain.entities.agent import Agent, AgentStatus as EntityAgentStatus
from ...domain.entities.task import Task
from ...domain.value_objects.agents import (
    AgentProfile, AgentCapabilities, AgentRole, AgentExpertise, AgentStatus
)
from ...domain.value_objects.coordination import (
    CoordinationType, CoordinationRequest, WorkAssignment, WorkHandoff,
    HandoffStatus, ConflictResolution, ConflictType, ResolutionStrategy,
    AgentCommunication
)
from ...domain.events.agent_events import (
    AgentAssigned, AgentUnassigned, WorkHandoffRequested, WorkHandoffAccepted,
    WorkHandoffRejected, WorkHandoffCompleted, ConflictDetected, ConflictResolved,
    AgentCollaborationStarted, AgentStatusBroadcast, AgentWorkloadRebalanced
)
from ...domain.exceptions import DomainException
from ...domain.repositories.task_repository import TaskRepository
# from ...infrastructure.repositories.agent_repository import AgentRepository  # TODO: AgentRepository not implemented yet
from ...infrastructure.event_bus import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class AgentCoordinationException(DomainException):
    """Exception for agent coordination issues"""
    pass


@dataclass
class CoordinationContext:
    """Context for coordination decisions"""
    task: Task
    available_agents: List[Agent]
    current_assignments: Dict[str, List[str]]  # agent_id -> task_ids
    workload_metrics: Dict[str, float]  # agent_id -> workload percentage
    
    def get_agent_workload(self, agent_id: str) -> float:
        """Get agent workload percentage"""
        return self.workload_metrics.get(agent_id, 0.0)
    
    def is_agent_overloaded(self, agent_id: str, threshold: float = 0.8) -> bool:
        """Check if agent is overloaded"""
        return self.get_agent_workload(agent_id) > threshold


class AgentCoordinationService:
    """Service for coordinating multi-agent workflows"""
    
    def __init__(
        self,
        task_repository: TaskRepository,
        agent_repository: Optional[Any] = None,  # AgentRepository not implemented yet
        event_bus: Optional[Any] = None,  # EventBus not implemented yet
        coordination_repository: Optional['AgentCoordinationRepository'] = None,
        user_id: Optional[str] = None
    ):
        self.task_repository = task_repository
        self.agent_repository = agent_repository
        self.event_bus = event_bus
        self.coordination_repository = coordination_repository
        self._user_id = user_id  # Store user context
        
        # In-memory storage if no repository provided
        self.coordination_requests: Dict[str, CoordinationRequest] = {}
        self.work_assignments: Dict[str, WorkAssignment] = {}
        self.handoffs: Dict[str, WorkHandoff] = {}
        self.conflicts: Dict[str, ConflictResolution] = {}
        self.communications: List[AgentCommunication] = []
    
    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository
    
    def with_user(self, user_id: str) -> 'AgentCoordinationService':
        """Create a new service instance scoped to a specific user."""
        return AgentCoordinationService(
            self.task_repository,
            self.agent_repository,
            self.event_bus,
            self.coordination_repository,
            user_id
        )
    
    async def assign_agent_to_task(
        self,
        task_id: str,
        agent_id: str,
        role: str,
        assigned_by: str,
        responsibilities: Optional[List[str]] = None,
        estimated_hours: Optional[float] = None,
        due_date: Optional[datetime] = None
    ) -> WorkAssignment:
        """Assign an agent to a task"""
        # Validate task exists
        task_repo = self._get_user_scoped_repository(self.task_repository)
        task = await task_repo.get(task_id)
        if not task:
            raise AgentCoordinationException(f"Task {task_id} not found")
        
        # Validate agent exists and is available
        agent_repo = self._get_user_scoped_repository(self.agent_repository)
        agent = await agent_repo.get(agent_id)
        if not agent:
            raise AgentCoordinationException(f"Agent {agent_id} not found")
        
        if not agent.is_available():
            raise AgentCoordinationException(f"Agent {agent_id} is not available for new assignments")
        
        # Create assignment
        assignment = WorkAssignment(
            assignment_id=str(uuid4()),
            task_id=task_id,
            assigned_agent_id=agent_id,
            assigned_by_agent_id=assigned_by,
            assigned_at=datetime.now(),
            role=role,
            responsibilities=responsibilities or [],
            estimated_hours=estimated_hours,
            due_date=due_date
        )
        
        # Update agent state
        agent.start_task(task_id)
        await self.agent_repository.save(agent)
        
        # Store assignment
        self.work_assignments[assignment.assignment_id] = assignment
        
        # Publish event
        event = AgentAssigned(
            agent_id=agent_id,
            task_id=task_id,
            role=role,
            assigned_by=assigned_by,
            assignment_id=assignment.assignment_id,
            responsibilities=responsibilities or [],
            estimated_hours=estimated_hours,
            due_date=due_date
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Agent {agent_id} assigned to task {task_id} with role {role}")
        
        return assignment
    
    async def request_work_handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        task_id: str,
        work_summary: str,
        completed_items: List[str],
        remaining_items: List[str],
        handoff_notes: str = ""
    ) -> WorkHandoff:
        """Request handoff of work from one agent to another"""
        # Validate agents exist
        from_agent = await self.agent_repository.get(from_agent_id)
        to_agent = await self.agent_repository.get(to_agent_id)
        
        if not from_agent or not to_agent:
            raise AgentCoordinationException("Invalid agent IDs for handoff")
        
        # Create handoff
        handoff = WorkHandoff(
            handoff_id=str(uuid4()),
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            task_id=task_id,
            initiated_at=datetime.now(),
            work_summary=work_summary,
            completed_items=completed_items,
            remaining_items=remaining_items,
            handoff_notes=handoff_notes
        )
        
        # Store handoff
        self.handoffs[handoff.handoff_id] = handoff
        
        # Publish event
        event = WorkHandoffRequested(
            handoff_id=handoff.handoff_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            task_id=task_id,
            work_summary=work_summary,
            completed_items=completed_items,
            remaining_items=remaining_items,
            handoff_notes=handoff_notes
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Work handoff requested from {from_agent_id} to {to_agent_id} for task {task_id}")
        
        return handoff
    
    async def accept_handoff(self, handoff_id: str, agent_id: str, notes: Optional[str] = None) -> None:
        """Accept a work handoff"""
        handoff = self.handoffs.get(handoff_id)
        if not handoff:
            raise AgentCoordinationException(f"Handoff {handoff_id} not found")
        
        if handoff.to_agent_id != agent_id:
            raise AgentCoordinationException(f"Agent {agent_id} is not the target of this handoff")
        
        # Accept handoff
        handoff.accept()
        
        # Reassign task
        await self.assign_agent_to_task(
            task_id=handoff.task_id,
            agent_id=agent_id,
            role="continued_work",
            assigned_by=handoff.from_agent_id
        )
        
        # Publish event
        event = WorkHandoffAccepted(
            handoff_id=handoff_id,
            accepted_by=agent_id,
            task_id=handoff.task_id,
            acceptance_notes=notes
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Handoff {handoff_id} accepted by agent {agent_id}")
    
    async def reject_handoff(self, handoff_id: str, agent_id: str, reason: str) -> None:
        """Reject a work handoff"""
        handoff = self.handoffs.get(handoff_id)
        if not handoff:
            raise AgentCoordinationException(f"Handoff {handoff_id} not found")
        
        if handoff.to_agent_id != agent_id:
            raise AgentCoordinationException(f"Agent {agent_id} is not the target of this handoff")
        
        # Reject handoff
        handoff.reject(reason)
        
        # Publish event
        event = WorkHandoffRejected(
            handoff_id=handoff_id,
            rejected_by=agent_id,
            task_id=handoff.task_id,
            rejection_reason=reason
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Handoff {handoff_id} rejected by agent {agent_id}: {reason}")
    
    async def detect_and_resolve_conflict(
        self,
        task_id: str,
        conflict_type: ConflictType,
        involved_agents: List[str],
        description: str,
        resolution_strategy: Optional[ResolutionStrategy] = None
    ) -> ConflictResolution:
        """Detect and optionally resolve a conflict"""
        # Create conflict
        conflict = ConflictResolution(
            conflict_id=str(uuid4()),
            conflict_type=conflict_type,
            involved_agents=involved_agents,
            task_id=task_id,
            detected_at=datetime.now(),
            description=description
        )
        
        # Store conflict
        self.conflicts[conflict.conflict_id] = conflict
        
        # Publish detection event
        detect_event = ConflictDetected(
            conflict_id=conflict.conflict_id,
            conflict_type=conflict_type.value,
            involved_agents=involved_agents,
            task_id=task_id,
            description=description
        )
        await self.event_bus.publish(detect_event)
        
        # Auto-resolve if strategy provided
        if resolution_strategy:
            await self.resolve_conflict(
                conflict_id=conflict.conflict_id,
                strategy=resolution_strategy,
                resolved_by="system",
                details=f"Auto-resolved using {resolution_strategy.value} strategy"
            )
        
        return conflict
    
    async def resolve_conflict(
        self,
        conflict_id: str,
        strategy: ResolutionStrategy,
        resolved_by: str,
        details: str
    ) -> None:
        """Resolve a conflict"""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            raise AgentCoordinationException(f"Conflict {conflict_id} not found")
        
        # Resolve conflict
        conflict.resolve(strategy, resolved_by, details)
        
        # Publish event
        event = ConflictResolved(
            conflict_id=conflict_id,
            resolution_strategy=strategy.value,
            resolved_by=resolved_by,
            task_id=conflict.task_id,
            resolution_details=details
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Conflict {conflict_id} resolved using {strategy.value} strategy")
    
    async def broadcast_agent_status(
        self,
        agent_id: str,
        status: str,
        current_task_id: Optional[str] = None,
        current_activity: Optional[str] = None,
        blocker_description: Optional[str] = None
    ) -> None:
        """Broadcast agent status to coordination system"""
        agent = await self.agent_repository.get(agent_id)
        if not agent:
            raise AgentCoordinationException(f"Agent {agent_id} not found")
        
        # Publish status event
        event = AgentStatusBroadcast(
            agent_id=agent_id,
            status=status,
            current_task_id=current_task_id,
            current_activity=current_activity,
            blocker_description=blocker_description,
            workload_percentage=agent.get_workload_percentage()
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Agent {agent_id} broadcasted status: {status}")
    
    async def rebalance_workload(
        self,
        project_id: str,
        initiated_by: str,
        reason: str = "Automatic workload balancing"
    ) -> Dict[str, Any]:
        """Rebalance workload across agents"""
        # Get all agents in project
        agents = await self.agent_repository.get_by_project(project_id)
        
        # Calculate current workload distribution
        workload_before = {
            agent.id: len(agent.active_tasks)
            for agent in agents
        }
        
        # Find overloaded and underutilized agents
        overloaded = [a for a in agents if a.get_workload_percentage() > 80]
        underutilized = [a for a in agents if a.get_workload_percentage() < 40 and a.is_available()]
        
        tasks_reassigned = {}
        
        # Reassign tasks from overloaded to underutilized agents
        for overloaded_agent in overloaded:
            if not underutilized:
                break
            
            # Get tasks that can be reassigned
            tasks = list(overloaded_agent.active_tasks)
            for task_id in tasks[:1]:  # Reassign one task at a time
                if underutilized:
                    target_agent = underutilized[0]
                    
                    # Request handoff
                    await self.request_work_handoff(
                        from_agent_id=overloaded_agent.id,
                        to_agent_id=target_agent.id,
                        task_id=task_id,
                        work_summary="Workload rebalancing",
                        completed_items=[],
                        remaining_items=["Continue current work"],
                        handoff_notes=f"Rebalancing workload: {reason}"
                    )
                    
                    tasks_reassigned[task_id] = target_agent.id
                    
                    # Update utilization status
                    if target_agent.get_workload_percentage() >= 40:
                        underutilized.remove(target_agent)
        
        # Calculate new workload
        agents_after = await self.agent_repository.get_by_project(project_id)
        workload_after = {
            agent.id: len(agent.active_tasks)
            for agent in agents_after
        }
        
        # Publish rebalancing event
        event = AgentWorkloadRebalanced(
            rebalance_id=str(uuid4()),
            initiated_by=initiated_by,
            agents_affected=list(set(list(workload_before.keys()) + list(tasks_reassigned.values()))),
            tasks_reassigned=tasks_reassigned,
            reason=reason,
            workload_before=workload_before,
            workload_after=workload_after
        )
        await self.event_bus.publish(event)
        
        logger.info(f"Workload rebalanced for project {project_id}: {len(tasks_reassigned)} tasks reassigned")
        
        return {
            "tasks_reassigned": tasks_reassigned,
            "workload_before": workload_before,
            "workload_after": workload_after
        }
    
    async def get_agent_workload(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed workload information for an agent"""
        agent = await self.agent_repository.get(agent_id)
        if not agent:
            raise AgentCoordinationException(f"Agent {agent_id} not found")
        
        # Get active assignments
        active_assignments = [
            assignment for assignment in self.work_assignments.values()
            if assignment.assigned_agent_id == agent_id and assignment.task_id in agent.active_tasks
        ]
        
        # Get pending handoffs
        pending_handoffs_to = [
            handoff for handoff in self.handoffs.values()
            if handoff.to_agent_id == agent_id and handoff.status == HandoffStatus.PENDING
        ]
        
        pending_handoffs_from = [
            handoff for handoff in self.handoffs.values()
            if handoff.from_agent_id == agent_id and handoff.status == HandoffStatus.PENDING
        ]
        
        return {
            "agent_id": agent_id,
            "status": agent.status.value,
            "workload_percentage": agent.get_workload_percentage(),
            "current_tasks": len(agent.active_tasks),
            "max_tasks": agent.max_concurrent_tasks,
            "active_assignments": [
                {
                    "task_id": a.task_id,
                    "role": a.role,
                    "assigned_at": a.assigned_at.isoformat(),
                    "due_date": a.due_date if a.due_date else None
                }
                for a in active_assignments
            ],
            "pending_handoffs_to_receive": len(pending_handoffs_to),
            "pending_handoffs_to_give": len(pending_handoffs_from),
            "can_accept_work": agent.is_available()
        }
    
    async def find_best_agent_for_task(
        self,
        task_id: str,
        required_role: Optional[AgentRole] = None,
        required_expertise: Optional[Set[AgentExpertise]] = None,
        required_skills: Optional[Dict[str, float]] = None
    ) -> Optional[Agent]:
        """Find the best available agent for a task"""
        task = await self.task_repository.get(task_id)
        if not task:
            raise AgentCoordinationException(f"Task {task_id} not found")
        
        # Get available agents
        all_agents = await self.agent_repository.get_all()
        available_agents = [a for a in all_agents if a.is_available()]
        
        if not available_agents:
            return None
        
        # Build task requirements
        task_requirements = {
            "role": required_role,
            "expertise": list(required_expertise) if required_expertise else [],
            "skills": required_skills or {}
        }
        
        # Score and rank agents
        agent_scores = []
        for agent in available_agents:
            # Create agent profile
            profile = AgentProfile(
                agent_id=agent.id,
                display_name=agent.name,
                capabilities=AgentCapabilities(
                    primary_role=AgentRole.DEVELOPER,  # Default, should be from agent data
                    expertise_areas=required_expertise or set(),
                    skill_levels=required_skills or {}
                ),
                availability_score=1.0 - (agent.get_workload_percentage() / 100.0),
                performance_score=agent.success_rate / 100.0
            )
            
            score = profile.overall_suitability_score(task_requirements)
            agent_scores.append((agent, score))
        
        # Sort by score and return best match
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        
        if agent_scores and agent_scores[0][1] > 0.5:  # Minimum threshold
            return agent_scores[0][0]
        
        return None