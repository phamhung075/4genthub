"""Work Distribution Service for Intelligent Task Assignment"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4
import logging
from collections import defaultdict
from enum import Enum

from ...domain.entities.agent import Agent, AgentStatus, AgentCapability
from ...domain.entities.task import Task
from ...domain.value_objects.task_status import TaskStatus, TaskStatusEnum
from ...domain.value_objects.priority import Priority, PriorityLevel
from ...domain.value_objects.agents import (
    AgentRole, AgentExpertise, AgentProfile, AgentCapabilities
)
from ...domain.value_objects.coordination import WorkAssignment
from ...domain.events.agent_events import AgentAssigned
from ...domain.exceptions import DomainException
from ...domain.repositories.task_repository import TaskRepository
# from ...infrastructure.repositories.agent_repository import AgentRepository  # TODO: Not implemented yet
# from ..event_bus import EventBus  # TODO: Not implemented yet
from .agent_coordination_service import AgentCoordinationService

logger = logging.getLogger(__name__)


class DistributionStrategy(Enum):
    """Work distribution strategies"""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    SKILL_MATCHED = "skill_matched"
    PRIORITY_BASED = "priority_based"
    HYBRID = "hybrid"  # Combines multiple strategies


class WorkDistributionException(DomainException):
    """Exception for work distribution issues"""
    pass


@dataclass
class TaskRequirements:
    """Requirements for a task"""
    task_id: str
    required_role: Optional[AgentRole] = None
    required_expertise: Set[AgentExpertise] = field(default_factory=set)
    required_skills: Dict[str, float] = field(default_factory=dict)
    preferred_agents: List[str] = field(default_factory=list)
    excluded_agents: List[str] = field(default_factory=list)
    collaboration_needed: bool = False
    estimated_hours: float = 0.0
    deadline: Optional[datetime] = None
    
    @classmethod
    def from_task(cls, task: Task) -> 'TaskRequirements':
        """Create requirements from task metadata"""
        metadata = task.metadata or {}
        
        # Extract requirements from task
        required_role = None
        if 'required_role' in metadata:
            try:
                required_role = AgentRole(metadata['required_role'])
            except ValueError:
                pass
        
        required_expertise = set()
        if 'required_expertise' in metadata:
            for exp in metadata['required_expertise']:
                try:
                    required_expertise.add(AgentExpertise(exp))
                except ValueError:
                    pass
        
        return cls(
            task_id=task.id.value if hasattr(task.id, 'value') else task.id,
            required_role=required_role,
            required_expertise=required_expertise,
            required_skills=metadata.get('required_skills', {}),
            preferred_agents=metadata.get('preferred_agents', []),
            excluded_agents=metadata.get('excluded_agents', []),
            collaboration_needed=metadata.get('collaboration_needed', False),
            estimated_hours=metadata.get('estimated_hours', 0.0),
            deadline=task.due_date
        )


@dataclass
class DistributionPlan:
    """Plan for distributing work"""
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    assignments: List[Tuple[str, str, str]] = field(default_factory=list)  # (task_id, agent_id, role)
    unassignable_tasks: List[str] = field(default_factory=list)
    recommendations: Dict[str, str] = field(default_factory=dict)
    
    def add_assignment(self, task_id: str, agent_id: str, role: str = "assignee") -> None:
        """Add an assignment to the plan"""
        self.assignments.append((task_id, agent_id, role))
    
    def mark_unassignable(self, task_id: str, reason: str) -> None:
        """Mark a task as unassignable"""
        self.unassignable_tasks.append(task_id)
        self.recommendations[task_id] = reason


class WorkDistributionService:
    """Service for intelligent work distribution"""
    
    def __init__(
        self,
        task_repository: TaskRepository,
        agent_repository: Optional[Any] = None,  # AgentRepository not implemented yet
        coordination_service: Optional[AgentCoordinationService] = None,
        event_bus: Optional[Any] = None,  # EventBus not implemented yet
        user_id: Optional[str] = None
    ):
        self.task_repository = task_repository
        self.agent_repository = agent_repository
        self.coordination_service = coordination_service
        self.event_bus = event_bus
        self._user_id = user_id  # Store user context
        
        # Track distribution history for learning
        self.distribution_history: List[Dict[str, Any]] = []
        self.agent_performance_cache: Dict[str, float] = {}

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

    def with_user(self, user_id: str) -> 'WorkDistributionService':
        """Create a new service instance scoped to a specific user."""
        return WorkDistributionService(
            self.task_repository,
            self.agent_repository,
            self.coordination_service,
            self.event_bus,
            user_id
        )
    
    async def distribute_tasks(
        self,
        task_ids: List[str],
        strategy: DistributionStrategy = DistributionStrategy.HYBRID,
        project_id: Optional[str] = None
    ) -> DistributionPlan:
        """Distribute multiple tasks to agents"""
        plan = DistributionPlan()
        
        # Get tasks
        tasks = []
        task_repo = self._get_user_scoped_repository(self.task_repository)
        for task_id in task_ids:
            task = await task_repo.get(task_id)
            if task and task.status.value in [TaskStatusEnum.TODO.value, TaskStatusEnum.IN_PROGRESS.value]:
                tasks.append(task)
        
        if not tasks:
            logger.warning("No distributable tasks found")
            return plan
        
        # Get available agents
        agent_repo = self._get_user_scoped_repository(self.agent_repository)
        if project_id:
            agents = await agent_repo.get_by_project(project_id) if agent_repo else []
        else:
            agents = await agent_repo.get_all() if agent_repo else []
        
        available_agents = [a for a in agents if a.is_available()]
        
        if not available_agents:
            for task in tasks:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "No available agents")
            return plan
        
        # Apply distribution strategy
        if strategy == DistributionStrategy.ROUND_ROBIN:
            await self._distribute_round_robin(tasks, available_agents, plan)
        elif strategy == DistributionStrategy.LOAD_BALANCED:
            await self._distribute_load_balanced(tasks, available_agents, plan)
        elif strategy == DistributionStrategy.SKILL_MATCHED:
            await self._distribute_skill_matched(tasks, available_agents, plan)
        elif strategy == DistributionStrategy.PRIORITY_BASED:
            await self._distribute_priority_based(tasks, available_agents, plan)
        else:  # HYBRID
            await self._distribute_hybrid(tasks, available_agents, plan)
        
        # Execute the plan
        await self._execute_distribution_plan(plan)
        
        # Record for learning
        self._record_distribution(plan, strategy)
        
        return plan
    
    async def _distribute_round_robin(
        self,
        tasks: List[Task],
        agents: List[Agent],
        plan: DistributionPlan
    ) -> None:
        """Simple round-robin distribution"""
        agent_index = 0
        
        for task in tasks:
            if agents:
                agent = agents[agent_index % len(agents)]
                plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, agent.id, "assignee")
                agent_index += 1
            else:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "No agents available")
    
    async def _distribute_load_balanced(
        self,
        tasks: List[Task],
        agents: List[Agent],
        plan: DistributionPlan
    ) -> None:
        """Distribute based on current workload"""
        # Sort agents by workload (ascending)
        agents_by_workload = sorted(agents, key=lambda a: a.get_workload_percentage())
        
        for task in tasks:
            # Find agent with lowest workload
            assigned = False
            for agent in agents_by_workload:
                if agent.is_available():
                    plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, agent.id, "assignee")
                    # Update agent's projected workload
                    agent.current_workload += 1
                    assigned = True
                    break
            
            if not assigned:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "All agents at capacity")
    
    async def _distribute_skill_matched(
        self,
        tasks: List[Task],
        agents: List[Agent],
        plan: DistributionPlan
    ) -> None:
        """Distribute based on skill matching"""
        for task in tasks:
            # Get task requirements
            requirements = TaskRequirements.from_task(task)
            
            # Find best matching agent
            best_agent = await self.coordination_service.find_best_agent_for_task(
                task_id=task.id.value if hasattr(task.id, 'value') else task.id,
                required_role=requirements.required_role,
                required_expertise=requirements.required_expertise,
                required_skills=requirements.required_skills
            )
            
            if best_agent:
                plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, best_agent.id, "specialist")
            else:
                plan.mark_unassignable(
                    task.id.value if hasattr(task.id, 'value') else task.id,
                    f"No agent with required skills: {requirements.required_role or 'any'}"
                )
    
    async def _distribute_priority_based(
        self,
        tasks: List[Task],
        agents: List[Agent],
        plan: DistributionPlan
    ) -> None:
        """Distribute high-priority tasks first to best agents"""
        # Sort tasks by priority (descending)
        priority_order = {
            PriorityLevel.CRITICAL.label: 5,
            PriorityLevel.URGENT.label: 4,
            PriorityLevel.HIGH.label: 3,
            PriorityLevel.MEDIUM.label: 2,
            PriorityLevel.LOW.label: 1,
            'none': 1
        }
        
        sorted_tasks = sorted(
            tasks,
            key=lambda t: priority_order.get(t.priority.value if hasattr(t.priority, 'value') else (t.priority if t.priority else 'none'), 1),
            reverse=True
        )
        
        # Sort agents by performance (descending)
        sorted_agents = sorted(
            agents,
            key=lambda a: self._get_agent_performance_score(a),
            reverse=True
        )
        
        agent_assignments = defaultdict(int)
        
        for task in sorted_tasks:
            # Assign to best available agent
            assigned = False
            for agent in sorted_agents:
                if agent.is_available() and agent_assignments[agent.id] < agent.max_concurrent_tasks:
                    plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, agent.id, "priority_assignee")
                    agent_assignments[agent.id] += 1
                    assigned = True
                    break
            
            if not assigned:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "No suitable agent for priority task")
    
    async def _distribute_hybrid(
        self,
        tasks: List[Task],
        agents: List[Agent],
        plan: DistributionPlan
    ) -> None:
        """Hybrid approach combining multiple strategies"""
        # Categorize tasks
        priority_tasks = []
        skilled_tasks = []
        regular_tasks = []
        
        for task in tasks:
            requirements = TaskRequirements.from_task(task)
            
            task_priority_value = task.priority.value if hasattr(task.priority, 'value') else task.priority
            if task_priority_value and task_priority_value in [PriorityLevel.CRITICAL.label, PriorityLevel.HIGH.label]:
                priority_tasks.append(task)
            elif requirements.required_role or requirements.required_expertise:
                skilled_tasks.append(task)
            else:
                regular_tasks.append(task)
        
        # Track agent utilization
        agent_utilization = {agent.id: 0 for agent in agents}
        
        # 1. Assign priority tasks to best agents
        best_agents = sorted(
            agents,
            key=lambda a: self._get_agent_performance_score(a),
            reverse=True
        )
        
        for task in priority_tasks:
            for agent in best_agents:
                if agent.is_available() and agent_utilization[agent.id] < agent.max_concurrent_tasks:
                    plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, agent.id, "priority_specialist")
                    agent_utilization[agent.id] += 1
                    break
        
        # 2. Assign skilled tasks based on matching
        for task in skilled_tasks:
            requirements = TaskRequirements.from_task(task)
            
            # Find matching agents
            matching_agents = []
            for agent in agents:
                if agent_utilization[agent.id] >= agent.max_concurrent_tasks:
                    continue
                
                # Basic skill matching
                if self._agent_matches_requirements(agent, requirements):
                    matching_agents.append(agent)
            
            if matching_agents:
                # Choose least loaded matching agent
                best_match = min(matching_agents, key=lambda a: agent_utilization[a.id])
                plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, best_match.id, "skill_matched")
                agent_utilization[best_match.id] += 1
            else:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "No agent with required skills available")
        
        # 3. Distribute regular tasks with load balancing
        for task in regular_tasks:
            # Find least loaded agent
            available_agents = [
                a for a in agents
                if agent_utilization[a.id] < a.max_concurrent_tasks
            ]
            
            if available_agents:
                least_loaded = min(available_agents, key=lambda a: agent_utilization[a.id])
                plan.add_assignment(task.id.value if hasattr(task.id, 'value') else task.id, least_loaded.id, "load_balanced")
                agent_utilization[least_loaded.id] += 1
            else:
                plan.mark_unassignable(task.id.value if hasattr(task.id, 'value') else task.id, "All agents at capacity")
    
    def _get_agent_performance_score(self, agent: Agent) -> float:
        """Get cached performance score for an agent"""
        if agent.id in self.agent_performance_cache:
            return self.agent_performance_cache[agent.id]
        
        # Calculate performance score
        score = agent.success_rate / 100.0
        
        # Factor in average completion time if available
        if agent.average_task_duration:
            # Normalize duration (assuming 8 hours is average)
            duration_factor = min(1.0, 8.0 / agent.average_task_duration)
            score = (score * 0.7) + (duration_factor * 0.3)
        
        self.agent_performance_cache[agent.id] = score
        return score
    
    def _agent_matches_requirements(self, agent: Agent, requirements: TaskRequirements) -> bool:
        """Check if agent matches task requirements"""
        # Check exclusions
        if agent.id in requirements.excluded_agents:
            return False
        
        # Check preferences (bonus, not requirement)
        if requirements.preferred_agents and agent.id in requirements.preferred_agents:
            return True
        
        # Check role capability
        if requirements.required_role:
            # Simple check - in real implementation, would check agent's actual roles
            if requirements.required_role == AgentRole.DEVELOPER:
                return AgentCapability.BACKEND_DEVELOPMENT in agent.capabilities
            elif requirements.required_role == AgentRole.TESTER:
                return AgentCapability.TESTING in agent.capabilities
            # Add more role mappings as needed
        
        return True  # Default to capable if no specific requirements
    
    async def _execute_distribution_plan(self, plan: DistributionPlan) -> None:
        """Execute the distribution plan by making actual assignments"""
        for task_id, agent_id, role in plan.assignments:
            try:
                await self.coordination_service.assign_agent_to_task(
                    task_id=task_id,
                    agent_id=agent_id,
                    role=role,
                    assigned_by="work_distribution_service"
                )
                logger.info(f"Assigned task {task_id} to agent {agent_id} with role {role}")
            except Exception as e:
                logger.error(f"Failed to assign task {task_id} to agent {agent_id}: {e}")
                plan.mark_unassignable(task_id, str(e))
    
    def _record_distribution(self, plan: DistributionPlan, strategy: DistributionStrategy) -> None:
        """Record distribution for learning and analysis"""
        record = {
            "plan_id": plan.plan_id,
            "timestamp": plan.created_at,
            "strategy": strategy.value,
            "total_tasks": len(plan.assignments) + len(plan.unassignable_tasks),
            "assigned_tasks": len(plan.assignments),
            "unassignable_tasks": len(plan.unassignable_tasks),
            "assignments": plan.assignments,
            "recommendations": plan.recommendations
        }
        
        self.distribution_history.append(record)
        
        # Keep only recent history (last 100 distributions)
        if len(self.distribution_history) > 100:
            self.distribution_history = self.distribution_history[-100:]
    
    async def get_distribution_analytics(self) -> Dict[str, Any]:
        """Get analytics about work distribution patterns"""
        if not self.distribution_history:
            return {"message": "No distribution history available"}
        
        # Calculate metrics
        total_distributions = len(self.distribution_history)
        total_tasks = sum(d["total_tasks"] for d in self.distribution_history)
        total_assigned = sum(d["assigned_tasks"] for d in self.distribution_history)
        
        # Strategy usage
        strategy_usage = defaultdict(int)
        for record in self.distribution_history:
            strategy_usage[record["strategy"]] += 1
        
        # Success rate by strategy
        strategy_success = defaultdict(lambda: {"assigned": 0, "total": 0})
        for record in self.distribution_history:
            strategy = record["strategy"]
            strategy_success[strategy]["assigned"] += record["assigned_tasks"]
            strategy_success[strategy]["total"] += record["total_tasks"]
        
        strategy_success_rates = {
            strategy: (data["assigned"] / data["total"] * 100) if data["total"] > 0 else 0
            for strategy, data in strategy_success.items()
        }
        
        return {
            "total_distributions": total_distributions,
            "total_tasks_distributed": total_tasks,
            "total_tasks_assigned": total_assigned,
            "overall_assignment_rate": (total_assigned / total_tasks * 100) if total_tasks > 0 else 0,
            "strategy_usage": dict(strategy_usage),
            "strategy_success_rates": strategy_success_rates,
            "recent_unassignable_reasons": [
                reason for record in self.distribution_history[-10:]
                for reason in record["recommendations"].values()
            ]
        }