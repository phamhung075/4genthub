"""Test data builders for task management domain objects."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.agent import Agent, AgentStatus, AgentCapability
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.entities.work_session import WorkSession
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority


class TaskBuilder:
    """Builder for creating Task entities with sensible defaults."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to default state."""
        self._id = TaskId.generate_new()
        self._title = "Test Task"
        self._description = "Test task description"
        self._status = TaskStatus.todo()
        self._priority = Priority.medium()
        self._git_branch_id = None
        self._details = ""
        self._estimated_effort = ""
        self._assignees = []
        self._labels = []
        self._dependencies = []
        self._subtasks = []
        self._due_date = None
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        self._context_id = None
        self._overall_progress = 0.0
        return self
    
    def with_id(self, task_id: Optional[TaskId] = None) -> 'TaskBuilder':
        """Set task ID."""
        self._id = task_id or TaskId.generate_new()
        return self
    
    def with_title(self, title: str) -> 'TaskBuilder':
        """Set task title."""
        self._title = title
        return self
    
    def with_description(self, description: str) -> 'TaskBuilder':
        """Set task description."""
        self._description = description
        return self
    
    def with_status(self, status: TaskStatus) -> 'TaskBuilder':
        """Set task status."""
        self._status = status
        return self
    
    def with_priority(self, priority: Priority) -> 'TaskBuilder':
        """Set task priority."""
        self._priority = priority
        return self
    
    def with_assignees(self, assignees: List[str]) -> 'TaskBuilder':
        """Set task assignees."""
        self._assignees = assignees
        return self
    
    def with_labels(self, labels: List[str]) -> 'TaskBuilder':
        """Set task labels."""
        self._labels = labels
        return self
    
    def with_dependencies(self, dependencies: List[TaskId]) -> 'TaskBuilder':
        """Set task dependencies."""
        self._dependencies = dependencies
        return self
    
    def with_context_id(self, context_id: str) -> 'TaskBuilder':
        """Set context ID (required for completion)."""
        self._context_id = context_id
        return self
    
    def in_progress(self) -> 'TaskBuilder':
        """Set task to in progress status."""
        self._status = TaskStatus.in_progress()
        return self
    
    def completed(self) -> 'TaskBuilder':
        """Set task to completed status with context."""
        self._status = TaskStatus.done()
        self._context_id = f"context-{uuid.uuid4()}"
        self._overall_progress = 100
        return self
    
    def with_estimated_effort(self, effort: str) -> 'TaskBuilder':
        """Set task estimated effort."""
        self._estimated_effort = effort
        return self
    
    def high_priority(self) -> 'TaskBuilder':
        """Set task to high priority."""
        self._priority = Priority.high()
        return self
    
    def build(self) -> Task:
        """Build the Task entity."""
        task = Task(
            id=self._id,
            title=self._title,
            description=self._description,
            status=self._status,
            priority=self._priority,
            git_branch_id=self._git_branch_id,
            estimated_effort=self._estimated_effort,
            assignees=self._assignees,
            labels=self._labels,
            dependencies=self._dependencies,
            subtasks=self._subtasks,
            due_date=self._due_date,
            created_at=self._created_at,
            updated_at=self._updated_at,
            context_id=self._context_id,
            overall_progress=self._overall_progress
        )
        return task


class AgentBuilder:
    """Builder for creating Agent entities with sensible defaults."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to default state."""
        self._id = f"agent-{uuid.uuid4()}"
        self._name = "Test Agent"
        self._description = "Test agent description"
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        self._capabilities = {AgentCapability.FRONTEND_DEVELOPMENT}
        self._specializations = []
        self._preferred_languages = []
        self._preferred_frameworks = []
        self._status = AgentStatus.AVAILABLE
        self._max_concurrent_tasks = 1
        self._current_workload = 0
        self._assigned_projects = set()
        self._assigned_trees = set()
        return self
    
    def with_name(self, name: str) -> 'AgentBuilder':
        """Set agent name."""
        self._name = name
        return self
    
    def with_capabilities(self, capabilities: set) -> 'AgentBuilder':
        """Set agent capabilities."""
        self._capabilities = capabilities
        return self
    
    def with_languages(self, languages: List[str]) -> 'AgentBuilder':
        """Set programming languages."""
        self._preferred_languages = languages
        return self
    
    def with_frameworks(self, frameworks: List[str]) -> 'AgentBuilder':
        """Set frameworks."""
        self._preferred_frameworks = frameworks
        return self
    
    def busy(self) -> 'AgentBuilder':
        """Set agent as busy."""
        self._status = AgentStatus.BUSY
        self._current_workload = 1
        return self
    
    def assigned_to_project(self, project_id: str, branch_name: str = None) -> 'AgentBuilder':
        """Assign agent to a project and optionally a specific branch."""
        if not hasattr(self, '_assigned_projects'):
            self._assigned_projects = set()
        if not hasattr(self, '_assigned_trees'):
            self._assigned_trees = set()
        
        self._assigned_projects.add(project_id)
        if branch_name:
            self._assigned_trees.add(f"{project_id}:{branch_name}")
        return self
    
    def build(self) -> Agent:
        """Build the Agent entity."""
        return Agent(
            id=self._id,
            name=self._name,
            description=self._description,
            created_at=self._created_at,
            updated_at=self._updated_at,
            capabilities=self._capabilities,
            specializations=self._specializations,
            preferred_languages=self._preferred_languages,
            preferred_frameworks=self._preferred_frameworks,
            status=self._status,
            max_concurrent_tasks=self._max_concurrent_tasks,
            current_workload=self._current_workload,
            assigned_projects=self._assigned_projects,
            assigned_trees=self._assigned_trees
        )


class ProjectBuilder:
    """Builder for creating Project entities with sensible defaults."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to default state."""
        self._id = f"project-{uuid.uuid4()}"
        self._name = "Test Project"
        self._description = "Test project description"
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        self._git_branchs = {}
        self._agents = {}
        self._work_sessions = []
        self._cross_tree_dependencies = []
        return self
    
    def with_name(self, name: str) -> 'ProjectBuilder':
        """Set project name."""
        self._name = name
        return self
    
    def with_agent(self, agent: Agent) -> 'ProjectBuilder':
        """Add agent to project."""
        self._agents[agent.id] = agent
        return self
    
    def with_git_branch(self, branch_name: str, tree: Optional[GitBranch] = None) -> 'ProjectBuilder':
        """Add git branch with optional task tree."""
        if tree is None:
            tree = GitBranch.create(
                name=f"{branch_name} Tasks",
                description=f"Tasks for {branch_name}",
                project_id=self._id
            )
        self._git_branchs[branch_name] = {
            "id": f"branch-{uuid.uuid4()}",
            "name": branch_name,
            "git_branch": tree,
            "assigned_agent_id": None
        }
        return self
    
    def build(self) -> Project:
        """Build the Project entity."""
        project = Project(
            id=self._id,
            name=self._name,
            description=self._description,
            created_at=self._created_at,
            updated_at=self._updated_at
        )
        
        # Set internal state
        project.git_branchs = self._git_branchs
        project.agents = self._agents
        project.work_sessions = self._work_sessions
        project.cross_tree_dependencies = self._cross_tree_dependencies
        
        return project


class SubtaskBuilder:
    """Builder for creating Subtask entities with sensible defaults."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to default state."""
        self._id = SubtaskId.generate_new()
        self._parent_task_id = TaskId.generate_new().value
        self._title = "Test Subtask"
        self._description = "Test subtask description"
        self._status = TaskStatus.todo()
        self._priority = Priority.medium()
        self._assignees = []
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        return self
    
    def with_parent_task_id(self, parent_id: str) -> 'SubtaskBuilder':
        """Set parent task ID."""
        self._parent_task_id = parent_id
        return self
    
    def with_title(self, title: str) -> 'SubtaskBuilder':
        """Set subtask title."""
        self._title = title
        return self
    
    def completed(self) -> 'SubtaskBuilder':
        """Set subtask as completed."""
        self._status = TaskStatus.done()
        return self
    
    def build(self) -> Subtask:
        """Build the Subtask entity."""
        return Subtask(
            id=self._id,
            parent_task_id=self._parent_task_id,
            title=self._title,
            description=self._description,
            status=self._status,
            priority=self._priority,
            assignees=self._assignees,
            created_at=self._created_at,
            updated_at=self._updated_at
        )


class WorkSessionBuilder:
    """Builder for creating WorkSession entities with sensible defaults."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to default state."""
        self._id = f"session-{uuid.uuid4()}"
        self._agent_id = f"agent-{uuid.uuid4()}"
        self._task_id = f"task-{uuid.uuid4()}"
        self._git_branch_name = "main"
        self._started_at = datetime.now(timezone.utc)
        return self
    
    def for_agent(self, agent_id: str) -> 'WorkSessionBuilder':
        """Set agent ID."""
        self._agent_id = agent_id
        return self
    
    def for_task(self, task_id: str) -> 'WorkSessionBuilder':
        """Set task ID."""
        self._task_id = task_id
        return self
    
    def on_branch(self, branch_name: str) -> 'WorkSessionBuilder':
        """Set git branch name."""
        self._git_branch_name = branch_name
        return self
    
    def build(self) -> WorkSession:
        """Build the WorkSession entity."""
        return WorkSession(
            id=self._id,
            agent_id=self._agent_id,
            task_id=self._task_id,
            git_branch_name=self._git_branch_name,
            started_at=self._started_at
        )


# Convenience functions for quick object creation
def a_task() -> TaskBuilder:
    """Create a new TaskBuilder."""
    return TaskBuilder()


def an_agent() -> AgentBuilder:
    """Create a new AgentBuilder."""
    return AgentBuilder()


def a_project() -> ProjectBuilder:
    """Create a new ProjectBuilder."""
    return ProjectBuilder()


def a_subtask() -> SubtaskBuilder:
    """Create a new SubtaskBuilder."""
    return SubtaskBuilder()


def a_work_session() -> WorkSessionBuilder:
    """Create a new WorkSessionBuilder."""
    return WorkSessionBuilder()