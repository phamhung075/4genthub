"""Task Plan Domain Entity

Represents the AI-generated plan that breaks down a planning request
into executable tasks with dependencies and agent assignments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from enum import Enum

class TaskType(Enum):
    """Types of tasks in the plan"""
    EPIC = "epic"                    # Large feature spanning multiple sprints
    FEATURE = "feature"              # User-facing feature
    STORY = "story"                  # Development story  
    TASK = "task"                    # Implementation task
    SUBTASK = "subtask"              # Subtask of a larger task
    BUG = "bug"                      # Bug fix task
    SPIKE = "spike"                  # Research/investigation task
    DOCUMENTATION = "documentation"  # Documentation task
    TESTING = "testing"             # Testing task
    REVIEW = "review"               # Code/design review task

class ExecutionPhase(Enum):
    """Phases of execution"""
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

@dataclass
class TaskDependency:
    """Represents a dependency between tasks"""
    dependent_task_id: str
    prerequisite_task_id: str
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, etc.
    lag_time: int = 0  # in hours
    
class AgentAssignment:
    """Represents assignment of agents to tasks"""
    def __init__(self, primary_agent: str, supporting_agents: Optional[List[str]] = None, 
                 effort_percentage: Dict[str, float] = None):
        self.primary_agent = primary_agent
        self.supporting_agents = supporting_agents or []
        self.effort_percentage = effort_percentage or {primary_agent: 100.0}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'primary_agent': self.primary_agent,
            'supporting_agents': self.supporting_agents,
            'effort_percentage': self.effort_percentage
        }

@dataclass 
class PlannedTask:
    """
    Represents a single task in the AI-generated plan.
    
    This contains all information needed to create an MCP task
    and assign it to appropriate agents.
    """
    id: str
    title: str
    description: str
    task_type: TaskType
    phase: ExecutionPhase
    
    # Hierarchy
    parent_task_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    
    # Assignment and effort
    agent_assignment: Optional[AgentAssignment] = None
    estimated_hours: float = 0.0
    estimated_complexity: str = "medium"  # trivial, simple, medium, complex, epic
    
    # Execution details
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_requirements: List[str] = field(default_factory=list)
    file_references: List[str] = field(default_factory=list)
    code_references: Dict[str, List[str]] = field(default_factory=dict)
    
    # Planning metadata
    priority: str = "medium"
    tags: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    
    # Status tracking
    status: str = "planned"  # planned, created, in_progress, completed
    mcp_task_id: Optional[str] = None  # Reference to created MCP task
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_subtask(self, subtask: 'PlannedTask'):
        """Add a subtask to this task"""
        if subtask.id not in self.subtask_ids:
            self.subtask_ids.append(subtask.id)
        subtask.parent_task_id = self.id
    
    def can_run_in_parallel(self, other_task: 'PlannedTask') -> bool:
        """Check if this task can run in parallel with another task"""
        # Same agent can't work on both tasks simultaneously
        if (self.agent_assignment and other_task.agent_assignment and
            self.agent_assignment.primary_agent == other_task.agent_assignment.primary_agent):
            return False

        # Check for file conflicts
        self_files = set(self.file_references)
        other_files = set(other_task.file_references)
        if self_files.intersection(other_files):
            return False

        # Tasks can run in parallel if they don't conflict on agent or files
        # Additional phase restrictions for certain incompatible phases
        incompatible_phases = {
            (ExecutionPhase.PLANNING, ExecutionPhase.IMPLEMENTATION),
            (ExecutionPhase.ARCHITECTURE, ExecutionPhase.TESTING),
        }

        phase_pair = (self.phase, other_task.phase)
        if phase_pair in incompatible_phases or phase_pair[::-1] in incompatible_phases:
            return False

        # If no conflicts, tasks can run in parallel
        return True
    
    def to_mcp_task_request(self) -> Dict[str, Any]:
        """Convert to MCP task creation request format"""
        assignees = [self.agent_assignment.primary_agent] if self.agent_assignment else []
        if self.agent_assignment and self.agent_assignment.supporting_agents:
            assignees.extend(self.agent_assignment.supporting_agents)
        
        details = f"""
        **Task Type**: {self.task_type.value}
        **Phase**: {self.phase.value}
        **Estimated Hours**: {self.estimated_hours}
        **Complexity**: {self.estimated_complexity}
        
        **Acceptance Criteria**:
        {chr(10).join(f'- {criteria}' for criteria in self.acceptance_criteria)}
        
        **Technical Requirements**:
        {chr(10).join(f'- {req}' for req in self.technical_requirements)}
        
        **File References**:
        {chr(10).join(f'- {file}' for file in self.file_references)}
        
        **Code References**:
        {chr(10).join(f'- {file}: {", ".join(ranges)}' for file, ranges in self.code_references.items())}
        
        **Risks**:
        {chr(10).join(f'- {risk}' for risk in self.risks)}
        
        **Assumptions**:
        {chr(10).join(f'- {assumption}' for assumption in self.assumptions)}
        """.strip()
        
        return {
            'title': self.title,
            'description': self.description,
            'assignees': assignees,
            'details': details,
            'priority': self.priority,
            'estimated_effort': f"{self.estimated_hours}h",
            'labels': self.tags
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type.value,
            'phase': self.phase.value,
            'parent_task_id': self.parent_task_id,
            'subtask_ids': self.subtask_ids,
            'agent_assignment': self.agent_assignment.to_dict() if self.agent_assignment else None,
            'estimated_hours': self.estimated_hours,
            'estimated_complexity': self.estimated_complexity,
            'acceptance_criteria': self.acceptance_criteria,
            'technical_requirements': self.technical_requirements,
            'file_references': self.file_references,
            'code_references': self.code_references,
            'priority': self.priority,
            'tags': self.tags,
            'risks': self.risks,
            'assumptions': self.assumptions,
            'status': self.status,
            'mcp_task_id': self.mcp_task_id,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class TaskPlan:
    """
    Represents a complete AI-generated task plan.
    
    Contains the hierarchical breakdown of a planning request
    into executable tasks with dependencies and scheduling.
    """
    id: str
    planning_request_id: str
    title: str
    description: str
    
    # Task hierarchy
    tasks: List[PlannedTask] = field(default_factory=list)
    dependencies: List[TaskDependency] = field(default_factory=list)
    
    # Planning metadata
    total_estimated_hours: float = 0.0
    estimated_duration_days: float = 0.0
    confidence_score: float = 0.0  # 0-1 confidence in the plan
    risk_level: str = "medium"
    
    # Execution information
    execution_phases: List[ExecutionPhase] = field(default_factory=list)
    parallel_execution_groups: List[List[str]] = field(default_factory=list)  # Groups of task IDs that can run in parallel
    critical_path: List[str] = field(default_factory=list)  # Task IDs on critical path
    
    # Agent allocation
    agent_workload: Dict[str, float] = field(default_factory=dict)  # agent -> estimated hours
    required_agents: Set[str] = field(default_factory=set)
    
    # Planning metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "ai_task_planning_engine"
    version: str = "1.0"
    
    def add_task(self, task: PlannedTask):
        """Add a task to the plan"""
        if task.id not in [t.id for t in self.tasks]:
            self.tasks.append(task)
            
            # Update agent workload
            if task.agent_assignment:
                agent = task.agent_assignment.primary_agent
                self.agent_workload[agent] = self.agent_workload.get(agent, 0) + task.estimated_hours
                self.required_agents.add(agent)
                
                for support_agent in task.agent_assignment.supporting_agents:
                    support_hours = task.estimated_hours * task.agent_assignment.effort_percentage.get(support_agent, 10) / 100
                    self.agent_workload[support_agent] = self.agent_workload.get(support_agent, 0) + support_hours
                    self.required_agents.add(support_agent)
            
            # Update totals
            self.total_estimated_hours += task.estimated_hours
            
            # Add execution phase if not already present
            if task.phase not in self.execution_phases:
                self.execution_phases.append(task.phase)
    
    def add_dependency(self, dependent_task_id: str, prerequisite_task_id: str, 
                      dependency_type: str = "finish_to_start", lag_time: int = 0):
        """Add a dependency between tasks"""
        dependency = TaskDependency(
            dependent_task_id=dependent_task_id,
            prerequisite_task_id=prerequisite_task_id, 
            dependency_type=dependency_type,
            lag_time=lag_time
        )
        self.dependencies.append(dependency)
    
    def get_task_by_id(self, task_id: str) -> Optional[PlannedTask]:
        """Get a task by its ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_root_tasks(self) -> List[PlannedTask]:
        """Get tasks that have no parent (top-level tasks)"""
        return [task for task in self.tasks if task.parent_task_id is None]
    
    def get_subtasks(self, parent_task_id: str) -> List[PlannedTask]:
        """Get all subtasks of a given task"""
        return [task for task in self.tasks if task.parent_task_id == parent_task_id]
    
    def calculate_critical_path(self) -> List[str]:
        """Calculate and update the critical path through the task network"""
        # Simple implementation - can be enhanced with more sophisticated algorithms
        task_duration = {task.id: task.estimated_hours for task in self.tasks}
        
        # Build dependency graph
        predecessors = {}
        successors = {}
        
        for task in self.tasks:
            predecessors[task.id] = []
            successors[task.id] = []
        
        for dep in self.dependencies:
            predecessors[dep.dependent_task_id].append(dep.prerequisite_task_id)
            successors[dep.prerequisite_task_id].append(dep.dependent_task_id)
        
        # Find critical path (simplified - longest path)
        def calculate_longest_path(task_id: str, visited: Set[str]) -> float:
            if task_id in visited:
                return 0  # Avoid cycles
            
            visited.add(task_id)
            
            if not successors[task_id]:
                return task_duration[task_id]
            
            max_successor_path = max(
                calculate_longest_path(successor, visited.copy()) 
                for successor in successors[task_id]
            )
            
            return task_duration[task_id] + max_successor_path
        
        # Calculate longest paths from root tasks
        critical_tasks = []
        max_path_length = 0
        
        for root_task in self.get_root_tasks():
            path_length = calculate_longest_path(root_task.id, set())
            if path_length > max_path_length:
                max_path_length = path_length
                # For simplicity, just store the root task - real implementation would trace full path
                critical_tasks = [root_task.id]
        
        self.critical_path = critical_tasks
        return self.critical_path
    
    def find_parallel_execution_groups(self) -> List[List[str]]:
        """Identify groups of tasks that can be executed in parallel"""
        groups = []
        remaining_tasks = self.tasks.copy()
        
        while remaining_tasks:
            parallel_group = []
            
            for task in remaining_tasks[:]:
                # Check if task can be added to current group
                can_add = True
                for group_task_id in parallel_group:
                    group_task = self.get_task_by_id(group_task_id)
                    if group_task and not task.can_run_in_parallel(group_task):
                        can_add = False
                        break
                
                if can_add:
                    parallel_group.append(task.id)
                    remaining_tasks.remove(task)
            
            if parallel_group:
                groups.append(parallel_group)
            else:
                # If no tasks can be grouped, add the first remaining task alone
                if remaining_tasks:
                    groups.append([remaining_tasks.pop(0).id])
        
        self.parallel_execution_groups = groups
        return groups
    
    def validate_plan(self) -> tuple[bool, List[str]]:
        """Validate the plan for consistency and completeness"""
        errors = []
        
        # Check for circular dependencies
        def has_circular_dependency(task_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            # Check all tasks that depend on this one
            for dep in self.dependencies:
                if dep.prerequisite_task_id == task_id:
                    dependent_id = dep.dependent_task_id
                    if dependent_id not in visited:
                        if has_circular_dependency(dependent_id, visited, rec_stack):
                            return True
                    elif dependent_id in rec_stack:
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        visited = set()
        for task in self.tasks:
            if task.id not in visited:
                if has_circular_dependency(task.id, visited, set()):
                    errors.append(f"Circular dependency detected involving task {task.id}")
        
        # Check for missing task references in dependencies
        task_ids = {task.id for task in self.tasks}
        for dep in self.dependencies:
            if dep.dependent_task_id not in task_ids:
                errors.append(f"Dependency references non-existent task: {dep.dependent_task_id}")
            if dep.prerequisite_task_id not in task_ids:
                errors.append(f"Dependency references non-existent task: {dep.prerequisite_task_id}")
        
        # Check for unassigned critical tasks
        unassigned_tasks = [task for task in self.tasks if not task.agent_assignment]
        if unassigned_tasks:
            errors.append(f"Tasks without agent assignments: {[task.id for task in unassigned_tasks]}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'planning_request_id': self.planning_request_id,
            'title': self.title,
            'description': self.description,
            'tasks': [task.to_dict() for task in self.tasks],
            'dependencies': [
                {
                    'dependent_task_id': dep.dependent_task_id,
                    'prerequisite_task_id': dep.prerequisite_task_id,
                    'dependency_type': dep.dependency_type,
                    'lag_time': dep.lag_time
                } for dep in self.dependencies
            ],
            'total_estimated_hours': self.total_estimated_hours,
            'estimated_duration_days': self.estimated_duration_days,
            'confidence_score': self.confidence_score,
            'risk_level': self.risk_level,
            'execution_phases': [phase.value for phase in self.execution_phases],
            'parallel_execution_groups': self.parallel_execution_groups,
            'critical_path': self.critical_path,
            'agent_workload': self.agent_workload,
            'required_agents': list(self.required_agents),
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version
        }