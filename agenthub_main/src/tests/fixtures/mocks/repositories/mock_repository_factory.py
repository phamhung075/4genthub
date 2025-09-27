"""Mock Repository Factory for Database-less Operation

This module provides mock repository implementations that can be used
when the database is not available, allowing tools to register and provide
limited functionality.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Fixed timestamp for test consistency
FIXED_TEST_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0)

from fastmcp.task_management.domain.repositories.project_repository import ProjectRepository
from fastmcp.task_management.domain.repositories.git_branch_repository import GitBranchRepository
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.entities.project import Project
from fastmcp.task_management.domain.entities.git_branch import GitBranch
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects import TaskId, TaskStatus, Priority
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)

logger = logging.getLogger(__name__)


class MockProjectRepository(ProjectRepository):
    """Mock project repository for database-less operation"""
    
    def __init__(self):
        self._projects: Dict[str, Project] = {}
        logger.warning("Using MockProjectRepository - data will not persist")
    
    async def save(self, project: Project) -> Project:
        """Save project to in-memory storage"""
        self._projects[project.id] = project
        return project
    
    async def find_by_id(self, project_id: str) -> Optional[Project]:
        """Find a project by its ID"""
        return self._projects.get(project_id)
    
    async def find_all(self) -> List[Project]:
        """Find all projects"""
        return list(self._projects.values())
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project by its ID"""
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False
    
    async def exists(self, project_id: str) -> bool:
        """Check if a project exists"""
        return project_id in self._projects
    
    async def update(self, project: Project) -> None:
        """Update an existing project"""
        if project.id in self._projects:
            self._projects[project.id] = project
        else:
            raise ResourceNotFoundException(f"Project {project.id} not found")
    
    async def find_by_name(self, name: str) -> Optional[Project]:
        """Find a project by its name"""
        for project in self._projects.values():
            if project.name == name:
                return project
        return None
    
    async def count(self) -> int:
        """Count total number of projects"""
        return len(self._projects)
    
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        """Find projects that have a specific agent registered"""
        # In mock implementation, return empty list as we don't track agents
        return []
    
    async def find_projects_by_status(self, status: str) -> List[Project]:
        """Find projects by their status"""
        results = []
        for project in self._projects.values():
            # Check if project has a status attribute
            if hasattr(project, 'status') and project.status == status:
                results.append(project)
        return results
    
    async def get_project_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all projects"""
        return {
            "total_projects": len(self._projects),
            "active_projects": len([p for p in self._projects.values() 
                                   if hasattr(p, 'status') and p.status == 'active']),
            "health": "mock_mode",
            "message": "Running in mock mode - limited functionality"
        }
    
    async def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Unassign an agent from a specific task tree within a project."""
        # In mock implementation, just return success
        return {
            "success": True,
            "message": "Mock operation - agent unassigned",
            "project_id": project_id,
            "agent_id": agent_id,
            "git_branch_id": git_branch_id
        }
    
    # Keep backward compatibility methods for existing code
    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID (backward compatibility)"""
        return await self.find_by_id(project_id)
    
    async def get_by_name(self, name: str) -> Optional[Project]:
        """Get project by name (backward compatibility)"""
        return await self.find_by_name(name)
    
    async def list_all(self) -> List[Project]:
        """List all projects (backward compatibility)"""
        return await self.find_all()


class MockGitBranchRepository(GitBranchRepository):
    """Mock git branch repository for database-less operation"""
    
    def __init__(self):
        self._branches: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        logger.warning("Using MockGitBranchRepository - data will not persist")
    
    async def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch"""
        branch_id = f"branch-{self._next_id}"
        self._next_id += 1
        branch = {
            "id": branch_id,
            "project_id": project_id,
            "name": git_branch_name,
            "description": git_branch_description,
            "created_at": FIXED_TEST_TIMESTAMP.isoformat(),
            "updated_at": FIXED_TEST_TIMESTAMP.isoformat()
        }
        self._branches[branch_id] = branch
        return {"success": True, "git_branch": branch}
    
    async def create_branch(self, project_id: str, branch_name: str, description: str = "") -> GitBranch:
        """Create a new git branch and return GitBranch entity"""
        from fastmcp.task_management.domain.entities.git_branch import GitBranch
        branch_id = f"branch-{self._next_id}"
        self._next_id += 1
        
        # Create GitBranch entity with all required fields
        git_branch = GitBranch(
            id=branch_id,
            name=branch_name,
            description=description,
            project_id=project_id,
            created_at=FIXED_TEST_TIMESTAMP,
            updated_at=FIXED_TEST_TIMESTAMP
        )
        
        # Also store in internal dict for compatibility with other methods
        branch_dict = {
            "id": branch_id,
            "project_id": project_id,
            "name": branch_name,
            "description": description,
            "created_at": FIXED_TEST_TIMESTAMP.isoformat(),
            "updated_at": FIXED_TEST_TIMESTAMP.isoformat()
        }
        self._branches[branch_id] = branch_dict
        
        return git_branch
    
    async def find_by_name(self, project_id: str, branch_name: str) -> Optional['GitBranch']:
        """Find git branch by name within a project"""
        from fastmcp.task_management.domain.entities.git_branch import GitBranch
        for branch_dict in self._branches.values():
            if branch_dict["project_id"] == project_id and branch_dict["name"] == branch_name:
                return GitBranch(
                    id=branch_dict["id"],
                    name=branch_dict["name"],
                    description=branch_dict["description"],
                    project_id=branch_dict["project_id"],
                    created_at=FIXED_TEST_TIMESTAMP,
                    updated_at=FIXED_TEST_TIMESTAMP
                )
        return None
    
    async def find_by_id(self, branch_id: str) -> Optional['GitBranch']:
        """Find git branch by ID"""
        from fastmcp.task_management.domain.entities.git_branch import GitBranch
        if branch_id in self._branches:
            branch_dict = self._branches[branch_id]
            return GitBranch(
                id=branch_dict["id"],
                name=branch_dict["name"],
                description=branch_dict["description"],
                project_id=branch_dict["project_id"],
                created_at=FIXED_TEST_TIMESTAMP,
                updated_at=FIXED_TEST_TIMESTAMP
            )
        return None
    
    async def find_all(self) -> List['GitBranch']:
        """Find all git branches"""
        from fastmcp.task_management.domain.entities.git_branch import GitBranch
        branches = []
        for branch_dict in self._branches.values():
            branches.append(GitBranch(
                id=branch_dict["id"],
                name=branch_dict["name"],
                description=branch_dict["description"],
                project_id=branch_dict["project_id"],
                created_at=FIXED_TEST_TIMESTAMP,
                updated_at=FIXED_TEST_TIMESTAMP
            ))
        return branches
    
    async def delete_branch(self, branch_id: str) -> bool:
        """Delete a git branch by ID"""
        if branch_id in self._branches:
            del self._branches[branch_id]
            return True
        return False
    
    async def update(self, git_branch: 'GitBranch') -> bool:
        """Update a git branch"""
        if git_branch.id in self._branches:
            self._branches[git_branch.id] = {
                "id": git_branch.id,
                "project_id": git_branch.project_id,
                "name": git_branch.name,
                "description": git_branch.description,
                "created_at": self._branches[git_branch.id]["created_at"],  # Keep original
                "updated_at": FIXED_TEST_TIMESTAMP.isoformat()
            }
            return True
        return False
    
    async def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get git branch by ID"""
        if git_branch_id in self._branches:
            return {"success": True, "git_branch": self._branches[git_branch_id]}
        return {"success": False, "error": f"Branch {git_branch_id} not found"}
    
    async def get_git_branch_by_name(self, project_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Get git branch by name within a project"""
        for branch in self._branches.values():
            if branch["project_id"] == project_id and branch["name"] == git_branch_name:
                return {"success": True, "git_branch": branch}
        return {"success": False, "error": f"Branch {git_branch_name} not found in project {project_id}"}
    
    async def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List all git branches for a project"""
        branches = [b for b in self._branches.values() if b["project_id"] == project_id]
        return {"success": True, "git_branchs": branches}
    
    async def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update git branch information"""
        if git_branch_id not in self._branches:
            return {"success": False, "error": f"Branch {git_branch_id} not found"}
        
        branch = self._branches[git_branch_id]
        if git_branch_name:
            branch["name"] = git_branch_name
        if git_branch_description is not None:
            branch["description"] = git_branch_description
        branch["updated_at"] = FIXED_TEST_TIMESTAMP.isoformat()
        return {"success": True, "git_branch": branch}
    
    async def delete_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch"""
        if git_branch_id in self._branches:
            del self._branches[git_branch_id]
            return {"success": True, "message": "Branch deleted"}
        return {"success": False, "error": f"Branch {git_branch_id} not found"}
    
    async def assign_agent_to_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a git branch"""
        return {"success": True, "message": "Mock operation - agent assigned"}
    
    async def unassign_agent_from_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch"""
        return {"success": True, "message": "Mock operation - agent unassigned"}
    
    async def get_branch_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a git branch"""
        if git_branch_id in self._branches:
            return {
                "success": True,
                "statistics": {
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "in_progress_tasks": 0,
                    "pending_tasks": 0
                }
            }
        return {"success": False, "error": f"Branch {git_branch_id} not found"}
    
    async def archive_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch"""
        if git_branch_id in self._branches:
            self._branches[git_branch_id]["archived"] = True
            return {"success": True, "message": "Branch archived"}
        return {"success": False, "error": f"Branch {git_branch_id} not found"}
    
    async def restore_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch"""
        if git_branch_id in self._branches:
            self._branches[git_branch_id]["archived"] = False
            return {"success": True, "message": "Branch restored"}
        return {"success": False, "error": f"Branch {git_branch_id} not found"}
    
    async def find_all(self) -> List[Dict[str, Any]]:
        """Find all git branches across all projects"""
        return list(self._branches.values())
    
    async def count(self) -> int:
        """Count total number of branches"""
        return len(self._branches)


class MockTaskRepository(TaskRepository):
    """Mock task repository for database-less operation"""
    
    def __init__(self, project_id: Optional[str] = None, branch_id: Optional[str] = None, user_id: Optional[str] = None):
        self._tasks: Dict[str, Task] = {}
        self._next_id = 1
        self.project_id = project_id
        self.branch_id = branch_id
        self.user_id = user_id
        logger.warning("Using MockTaskRepository - data will not persist")
    
    def save(self, task: Task) -> Task:
        """Save a task"""
        self._tasks[str(task.id)] = task
        return task
    
    def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID"""
        return self._tasks.get(str(task_id))
    
    def find_all(self) -> List[Task]:
        """Find all tasks"""
        return list(self._tasks.values())
    
    def find_by_status(self, status: TaskStatus) -> List[Task]:
        """Find tasks by status"""
        return [t for t in self._tasks.values() if t.status == status]
    
    def find_by_priority(self, priority: Priority) -> List[Task]:
        """Find tasks by priority"""
        return [t for t in self._tasks.values() if t.priority == priority]
    
    def find_by_assignee(self, assignee: str) -> List[Task]:
        """Find tasks by assignee"""
        return [t for t in self._tasks.values() if hasattr(t, 'assignee') and t.assignee == assignee]
    
    def find_by_labels(self, labels: List[str]) -> List[Task]:
        """Find tasks containing any of the specified labels"""
        results = []
        for task in self._tasks.values():
            if hasattr(task, 'labels') and task.labels:
                if any(label in task.labels for label in labels):
                    results.append(task)
        return results
    
    def search(self, query: str, limit: int = 10) -> List[Task]:
        """Search tasks by query string"""
        results = []
        query_lower = query.lower()
        for task in self._tasks.values():
            if (query_lower in task.title.lower() or 
                (task.description and query_lower in task.description.lower())):
                results.append(task)
                if len(results) >= limit:
                    break
        return results
    
    def delete(self, task_id: TaskId) -> bool:
        """Delete a task"""
        task_id_str = str(task_id)
        if task_id_str in self._tasks:
            del self._tasks[task_id_str]
            return True
        return False
    
    def exists(self, task_id: TaskId) -> bool:
        """Check if task exists"""
        return str(task_id) in self._tasks
    
    def get_next_id(self) -> TaskId:
        """Get next available task ID"""
        from ...domain.value_objects import TaskId
        task_id = TaskId(f"task-{self._next_id}")
        self._next_id += 1
        return task_id
    
    def count(self) -> int:
        """Get total number of tasks"""
        return len(self._tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        from ...domain.value_objects import TaskStatus
        return {
            "total": len(self._tasks),
            "pending": len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING]),
            "in_progress": len([t for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS]),
            "completed": len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED])
        }
    
    def find_by_criteria(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Task]:
        """Find tasks by multiple criteria"""
        results = []
        for task in self._tasks.values():
            match = True
            for key, value in filters.items():
                if not hasattr(task, key) or getattr(task, key) != value:
                    match = False
                    break
            if match:
                results.append(task)
                if limit and len(results) >= limit:
                    break
        return results
    
    def find_by_id_all_states(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID across all states (active, completed, archived)"""
        return self.find_by_id(task_id)


class MockSubtaskRepository(SubtaskRepository):
    """Mock subtask repository for database-less operation"""
    
    def __init__(self, project_id: Optional[str] = None, branch_id: Optional[str] = None, user_id: Optional[str] = None):
        self._subtasks: Dict[str, Subtask] = {}
        self._next_id = 1
        self.project_id = project_id
        self.branch_id = branch_id
        self.user_id = user_id
        logger.warning("Using MockSubtaskRepository - data will not persist")
    
    def save(self, subtask: Subtask) -> Subtask:
        """Save a subtask"""
        self._subtasks[str(subtask.id)] = subtask
        return subtask
    
    def find_by_id(self, id: str) -> Optional[Subtask]:
        """Find a subtask by its id."""
        return self._subtasks.get(id)
    
    def find_by_parent_task_id(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() if str(s.task_id) == task_id_str]
    
    def find_by_assignee(self, assignee: str) -> List[Subtask]:
        """Find subtasks by assignee"""
        return [s for s in self._subtasks.values() if hasattr(s, 'assignee') and s.assignee == assignee]
    
    def find_by_status(self, status: str) -> List[Subtask]:
        """Find subtasks by status"""
        return [s for s in self._subtasks.values() if s.status == status]
    
    def find_completed(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find completed subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() 
                if str(s.task_id) == task_id_str and s.status == 'completed']
    
    def find_pending(self, parent_task_id: TaskId) -> List[Subtask]:
        """Find pending subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() 
                if str(s.task_id) == task_id_str and s.status == 'pending']
    
    def delete(self, id: str) -> bool:
        """Delete a subtask by its id."""
        if id in self._subtasks:
            del self._subtasks[id]
            return True
        return False
    
    def delete_by_parent_task_id(self, parent_task_id: TaskId) -> bool:
        """Delete all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        to_delete = [id for id, s in self._subtasks.items() if str(s.task_id) == task_id_str]
        for id in to_delete:
            del self._subtasks[id]
        return len(to_delete) > 0
    
    def exists(self, id: str) -> bool:
        """Check if a subtask exists by its id."""
        return id in self._subtasks
    
    def count_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """Count subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return len([s for s in self._subtasks.values() if str(s.task_id) == task_id_str])
    
    def count_completed_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """Count completed subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return len([s for s in self._subtasks.values() 
                   if str(s.task_id) == task_id_str and s.status == 'completed'])
    
    def get_next_id(self, parent_task_id: TaskId) -> SubtaskId:
        """Get next available subtask ID for a parent task"""
        from ...domain.value_objects.subtask_id import SubtaskId
        subtask_id = SubtaskId(f"subtask-{self._next_id}")
        self._next_id += 1
        return subtask_id
    
    def get_subtask_progress(self, parent_task_id: TaskId) -> Dict[str, Any]:
        """Get subtask progress statistics for a parent task"""
        subtasks = self.find_by_parent_task_id(parent_task_id)
        completed = len([s for s in subtasks if s.status == 'completed'])
        total = len(subtasks)
        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0
        }
    
    def bulk_update_status(self, parent_task_id: TaskId, status: str) -> bool:
        """Update status of all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        updated = False
        for subtask in self._subtasks.values():
            if str(subtask.task_id) == task_id_str:
                subtask.status = status
                updated = True
        return updated
    
    def bulk_complete(self, parent_task_id: TaskId) -> bool:
        """Mark all subtasks as completed for a parent task"""
        return self.bulk_update_status(parent_task_id, 'completed')
    
    def remove_subtask(self, parent_task_id: str, subtask_id: str) -> bool:
        """Remove a subtask from a parent task by subtask ID."""
        if subtask_id in self._subtasks:
            subtask = self._subtasks[subtask_id]
            if str(subtask.task_id) == parent_task_id:
                del self._subtasks[subtask_id]
                return True
        return False


class MockRepositoryFactory:
    """Factory for creating mock repositories when database is unavailable"""
    
    # Singleton instances for consistency
    _project_repo: Optional[MockProjectRepository] = None
    _branch_repo: Optional[MockGitBranchRepository] = None
    _task_repo: Optional[MockTaskRepository] = None
    _subtask_repo: Optional[MockSubtaskRepository] = None
    
    @classmethod
    def get_project_repository(cls) -> ProjectRepository:
        """Get mock project repository"""
        if cls._project_repo is None:
            cls._project_repo = MockProjectRepository()
        return cls._project_repo
    
    @classmethod
    def get_git_branch_repository(cls) -> GitBranchRepository:
        """Get mock git branch repository"""
        if cls._branch_repo is None:
            cls._branch_repo = MockGitBranchRepository()
        return cls._branch_repo
    
    @classmethod
    def get_task_repository(cls, project_id: str = None, branch_id: str = None, user_id: str = None) -> TaskRepository:
        """Get mock task repository"""
        if cls._task_repo is None:
            cls._task_repo = MockTaskRepository(project_id, branch_id, user_id)
        return cls._task_repo
    
    @classmethod
    def get_subtask_repository(cls, project_id: str = None, branch_id: str = None, user_id: str = None) -> SubtaskRepository:
        """Get mock subtask repository"""
        if cls._subtask_repo is None:
            cls._subtask_repo = MockSubtaskRepository(project_id, branch_id, user_id)
        return cls._subtask_repo