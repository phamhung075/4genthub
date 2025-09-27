"""Project Domain Entity"""

from typing import Dict, List, Optional, Set, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid

from .base.base_timestamp_entity import BaseTimestampEntity

from ..value_objects.task_id import TaskId
from .git_branch import GitBranch
from .agent import Agent

if TYPE_CHECKING:
    from ..repositories.git_branch_repository import GitBranchRepository


@dataclass
class Project(BaseTimestampEntity):
    """Project aggregate root for multi-agent task orchestration"""

    id: str = ""
    name: str = ""
    description: str = ""

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id) if self.id else "unknown"

    @classmethod
    def create(
        cls,
        name: str,
        description: str = ""
    ) -> 'Project':
        """Create a new project with auto-generated UUID"""
        project_id = str(uuid.uuid4())

        return cls(
            id=project_id,
            name=name,
            description=description
        )
    
    def __hash__(self):
        """Make Project hashable based on its id"""
        return hash(self.id)

    # Multi-tree structure
    git_branchs: Dict[str, GitBranch] = field(default_factory=dict)
    
    # Agent management
    registered_agents: Dict[str, Agent] = field(default_factory=dict)
    agent_assignments: Dict[str, str] = field(default_factory=dict)  # git_branch_name -> agent_id
    
    # Cross-tree dependencies
    cross_tree_dependencies: Dict[str, Set[str]] = field(default_factory=dict)  # task_id -> dependent_task_ids
    
    # Work coordination
    active_work_sessions: Dict[str, 'WorkSession'] = field(default_factory=dict)
    resource_locks: Dict[str, str] = field(default_factory=dict)  # resource -> agent_id

    def _validate_entity(self) -> None:
        """Ensure project invariants hold."""
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")
    
    async def create_git_branch_async(
        self, 
        git_branch_repository: 'GitBranchRepository',
        branch_name: str, 
        description: str = ""
    ) -> GitBranch:
        """Create a new git branch/task tree within the project using repository"""
        # Check if branch already exists
        existing_branch = await git_branch_repository.find_by_name(self.id, branch_name)
        if existing_branch:
            raise ValueError(f"Git branch {branch_name} already exists in project {self.id}")
        
        # Create new branch using repository
        git_branch = await git_branch_repository.create_branch(
            project_id=self.id,
            branch_name=branch_name,
            description=description
        )
        
        # Update local cache
        self.git_branchs[git_branch.id] = git_branch
        self.touch("git_branch_added")
        return git_branch
    
    def create_git_branch(self, git_branch_name: str, name: str, description: str = "") -> GitBranch:
        """Create a new task tree/branch within the project (legacy method)"""
        # Check if branch name already exists in any git branch
        for git_branch in self.git_branchs.values():
            if git_branch.git_branch_name == git_branch_name:
                raise ValueError(f"Git branch {git_branch_name} already exists")
        
        # Generate unique ID for the git branch following clean relationship chain
        import uuid
        git_branch_id = str(uuid.uuid4())
        
        git_branch = GitBranch(
            id=git_branch_id,
            name=name,
            description=description,
            project_id=self.id,
            git_branch_name=git_branch_name
        )
        
        self.git_branchs[git_branch_id] = git_branch
        self.touch("git_branch_created")
        return git_branch
    
    def add_git_branch(self, git_branch: GitBranch) -> None:
        """Add a git branch to the project"""
        self.git_branchs[git_branch.id] = git_branch
        self.touch("git_branch_added")
    
    def get_git_branch(self, branch_name: str) -> Optional[GitBranch]:
        """Get a git branch by name"""
        for git_branch in self.git_branchs.values():
            if git_branch.name == branch_name:
                return git_branch
        return None
    
    def register_agent(self, agent: Agent) -> None:
        """Register an AI agent to work on this project"""
        self.registered_agents[agent.id] = agent
        self.touch("agent_registered")
    
    def assign_agent_to_tree(self, agent_id: str, git_branch_name: str) -> None:
        """Assign an agent to work on a specific task tree"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")
        if git_branch_name not in self.git_branchs:
            raise ValueError(f"Task tree {git_branch_name} not found")
        
        # Check if tree is already assigned
        if git_branch_name in self.agent_assignments:
            current_agent = self.agent_assignments[git_branch_name]
            if current_agent != agent_id:
                raise ValueError(f"Task tree {git_branch_name} already assigned to agent {current_agent}")
        
        self.agent_assignments[git_branch_name] = agent_id
        self.touch("agent_assigned_to_tree")
    
    def add_cross_tree_dependency(self, dependent_task_id: str, prerequisite_task_id: str) -> None:
        """Add a dependency between tasks in different trees"""
        # Normalize task IDs for consistent storage
        dependent_task_id = self._normalize_task_id(dependent_task_id)
        prerequisite_task_id = self._normalize_task_id(prerequisite_task_id)
        
        # Validate that tasks exist and are in different trees
        dependent_tree = self._find_git_branch(dependent_task_id)
        prerequisite_tree = self._find_git_branch(prerequisite_task_id)
        
        if not dependent_tree or not prerequisite_tree:
            raise ValueError("One or both tasks not found in project")
        
        if dependent_tree.id == prerequisite_tree.id:
            raise ValueError("Use regular task dependencies for tasks within the same tree")
        
        # Add cross-tree dependency
        if dependent_task_id not in self.cross_tree_dependencies:
            self.cross_tree_dependencies[dependent_task_id] = set()
        
        self.cross_tree_dependencies[dependent_task_id].add(prerequisite_task_id)
        self.touch("cross_tree_dependency_added")
    
    def get_available_work_for_agent(self, agent_id: str) -> List['Task']:
        """Get available tasks for a specific agent based on their assignments and dependencies"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")
        
        available_tasks = []
        
        # Find trees assigned to this agent
        assigned_trees = [git_branch_name for git_branch_name, assigned_agent in self.agent_assignments.items() 
                         if assigned_agent == agent_id]
        
        for git_branch_name in assigned_trees:
            branch = self.git_branchs[git_branch_name]
            branch_tasks = branch.get_available_tasks()
            
            # Filter out tasks blocked by cross-tree dependencies
            for task in branch_tasks:
                if self._is_task_ready_for_work(task.id.value):
                    available_tasks.append(task)
        
        return available_tasks
    
    def start_work_session(self, agent_id: str, task_id: str, max_duration_hours: Optional[float] = None) -> 'WorkSession':
        """Start a work session for an agent on a specific task"""
        from .work_session import WorkSession
        
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not registered")
        
        # Check if agent is assigned to the tree containing this task
        git_branch = self._find_git_branch(task_id)
        if not git_branch:
            raise ValueError(f"Task {task_id} not found")
        
        if self.agent_assignments.get(git_branch.id) != agent_id:
            raise ValueError(f"Agent {agent_id} not assigned to tree {git_branch.id}")
        
        # Create work session using factory method
        session = WorkSession.create_session(
            agent_id=agent_id,
            task_id=task_id,
            git_branch_name=git_branch.id,
            max_duration_hours=max_duration_hours
        )
        
        self.active_work_sessions[session.id] = session
        self.touch("work_session_started")
        return session
    
    def _find_git_branch(self, task_id: str) -> Optional[GitBranch]:
        """Find which git branch contains a specific task"""
        # Normalize task_id to canonical format for consistent comparison
        normalized_task_id = self._normalize_task_id(task_id)
        for branch in self.git_branchs.values():
            if branch.has_task(normalized_task_id):
                return branch
        return None
    
    def _normalize_task_id(self, task_id: str) -> str:
        """Normalize task_id to canonical UUID format"""
        if len(task_id) == 32 and '-' not in task_id:
            # Convert hex format to canonical
            return f"{task_id[:8]}-{task_id[8:12]}-{task_id[12:16]}-{task_id[16:20]}-{task_id[20:]}"
        return task_id
    
    def _is_task_ready_for_work(self, task_id: str) -> bool:
        """Check if a task is ready for work (all cross-tree dependencies satisfied)"""
        normalized_task_id = self._normalize_task_id(task_id)
        if normalized_task_id not in self.cross_tree_dependencies:
            return True  # No cross-tree dependencies
        
        # Check if all prerequisite tasks are completed
        for prerequisite_id in self.cross_tree_dependencies[normalized_task_id]:
            prerequisite_tree = self._find_git_branch(prerequisite_id)
            if not prerequisite_tree:
                return False  # Prerequisite task not found
            
            prerequisite_task = prerequisite_tree.get_task(prerequisite_id)
            if not prerequisite_task:
                return False  # Prerequisite task not found
            
            # Handle both Task entity and dict representation
            if hasattr(prerequisite_task, 'status'):
                if not prerequisite_task.status.is_done():
                    return False  # Prerequisite not completed
            elif isinstance(prerequisite_task, dict):
                if prerequisite_task.get('status') != 'done':
                    return False  # Prerequisite not completed
            else:
                return False  # Unknown prerequisite task format
        
        return True
    
    def get_orchestration_status(self) -> Dict:
        """Get comprehensive status for orchestration dashboard"""
        return {
            "project_id": self.id,
            "project_name": self.name,
            "total_branches": len(self.git_branchs),
            "registered_agents": len(self.registered_agents),
            "active_assignments": len(self.agent_assignments),
            "active_sessions": len(self.active_work_sessions),
            "cross_tree_dependencies": sum(len(deps) for deps in self.cross_tree_dependencies.values()),
            "resource_locks": len(self.resource_locks),
            "branches": {
                git_branch_name: {
                    "name": branch.name,
                    "assigned_agent": self.agent_assignments.get(git_branch_name),
                    "total_tasks": branch.get_task_count(),
                    "completed_tasks": branch.get_completed_task_count(),
                    "progress": branch.get_progress_percentage()
                }
                for git_branch_name, branch in self.git_branchs.items()
            },
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "capabilities": [cap.value for cap in agent.capabilities],  # Convert set to list
                    "assigned_trees": [git_branch_name for git_branch_name, assigned_agent in self.agent_assignments.items() 
                                     if assigned_agent == agent_id],
                    "active_sessions": [session.id for session in self.active_work_sessions.values() 
                                      if session.agent_id == agent_id]
                }
                for agent_id, agent in self.registered_agents.items()
            }
        }
    
    def coordinate_cross_tree_dependencies(self) -> Dict:
        """Coordinate and validate cross-tree dependencies"""
        coordination_result = {
            "total_dependencies": sum(len(deps) for deps in self.cross_tree_dependencies.values()),
            "validated_dependencies": 0,
            "blocked_tasks": [],
            "ready_tasks": [],
            "missing_prerequisites": []
        }
        
        for dependent_task_id, prerequisite_ids in self.cross_tree_dependencies.items():
            # Check if dependent task exists
            dependent_tree = self._find_git_branch(dependent_task_id)
            if not dependent_tree:
                coordination_result["missing_prerequisites"].append({
                    "task_id": dependent_task_id,
                    "issue": "Dependent task not found"
                })
                continue
            
            # Check each prerequisite
            all_prerequisites_met = True
            for prerequisite_id in prerequisite_ids:
                prerequisite_tree = self._find_git_branch(prerequisite_id)
                if not prerequisite_tree:
                    coordination_result["missing_prerequisites"].append({
                        "task_id": prerequisite_id,
                        "issue": "Prerequisite task not found"
                    })
                    all_prerequisites_met = False
                    continue
                
                prerequisite_task = prerequisite_tree.get_task(prerequisite_id)
                if not prerequisite_task:
                    all_prerequisites_met = False
                    continue
                
                # Handle both Task entity and dict representation
                task_not_done = False
                if hasattr(prerequisite_task, 'status'):
                    task_not_done = not prerequisite_task.status.is_done()
                elif isinstance(prerequisite_task, dict):
                    task_not_done = prerequisite_task.get('status') != 'done'
                else:
                    task_not_done = True  # Unknown format, assume not done
                
                if task_not_done:
                    all_prerequisites_met = False
            
            if all_prerequisites_met:
                coordination_result["ready_tasks"].append(dependent_task_id)
            else:
                coordination_result["blocked_tasks"].append(dependent_task_id)
            
            coordination_result["validated_dependencies"] += 1
        
        return coordination_result 
