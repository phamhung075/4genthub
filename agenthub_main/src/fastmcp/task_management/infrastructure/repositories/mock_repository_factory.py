"""Mock Repository Factory - Production Mock Implementations

This module provides mock repository implementations for testing and development.
Since the system now uses Keycloak for authentication and PostgreSQL as the 
source of truth, these mocks are simplified and focused on core functionality.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ...domain.repositories.project_repository import ProjectRepository
from ...domain.repositories.git_branch_repository import GitBranchRepository
from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.entities.project import Project
from ...domain.entities.git_branch import GitBranch
from ...domain.entities.task import Task
from ...domain.entities.subtask import Subtask

logger = logging.getLogger(__name__)


class MockProjectRepository(ProjectRepository):
    """Mock project repository for testing and development"""
    def __init__(self):
        self._projects = {}
        logger.info("MockProjectRepository initialized")
    
    async def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project
    
    async def find_by_id(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)
    
    async def find_by_name(self, name: str) -> Optional[Project]:
        for project in self._projects.values():
            if project.name == name:
                return project
        return None
    
    async def find_all(self) -> List[Project]:
        return list(self._projects.values())
    
    async def delete(self, project_id: str) -> bool:
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False
    
    async def count(self) -> int:
        return len(self._projects)
    
    async def exists(self, project_id: str) -> bool:
        return project_id in self._projects
    
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        return []
    
    async def find_projects_by_status(self, status: str) -> List[Project]:
        results = []
        for project in self._projects.values():
            if hasattr(project, 'status') and project.status == status:
                results.append(project)
        return results
    
    async def get_project_health_summary(self, project_id: str) -> Dict[str, Any]:
        return {"health": "good", "project_id": project_id}
    
    async def unassign_agent_from_tree(self, project_id: str) -> bool:
        return True
    
    async def update(self, project: Project) -> Project:
        """Update a project"""
        if project.id in self._projects:
            self._projects[project.id] = project
            return project
        raise ValueError(f"Project with id {project.id} not found")


class MockGitBranchRepository(GitBranchRepository):
    """Mock git branch repository for testing and development"""
    def __init__(self):
        self._branches = {}
        logger.info("MockGitBranchRepository initialized")
    
    async def save(self, branch: GitBranch) -> GitBranch:
        self._branches[branch.id] = branch
        return branch
    
    async def find_by_id(self, branch_id: str) -> Optional[GitBranch]:
        return self._branches.get(branch_id)
    
    async def find_all(self) -> List[GitBranch]:
        return list(self._branches.values())
    
    async def delete(self, branch_id: str) -> bool:
        if branch_id in self._branches:
            del self._branches[branch_id]
            return True
        return False
    
    async def find_by_project_id(self, project_id: str) -> List[GitBranch]:
        results = []
        for branch in self._branches.values():
            if branch.project_id == project_id:
                results.append(branch)
        return results
    
    async def find_by_name_and_project(self, name: str, project_id: str) -> Optional[GitBranch]:
        for branch in self._branches.values():
            if branch.name == name and branch.project_id == project_id:
                return branch
        return None
    
    async def count(self) -> int:
        return len(self._branches)
    
    async def exists(self, branch_id: str) -> bool:
        return branch_id in self._branches
    
    async def update(self, branch: GitBranch) -> GitBranch:
        """Update a git branch"""
        if branch.id in self._branches:
            self._branches[branch.id] = branch
            return branch
        raise ValueError(f"Branch with id {branch.id} not found")


class MockTaskRepository(TaskRepository):
    """Mock task repository for testing and development"""
    def __init__(self):
        self._tasks = {}
        self._next_id = 1
        logger.info("MockTaskRepository initialized")
    
    def save(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task
    
    def find_by_id(self, task_id) -> Optional[Task]:
        if hasattr(task_id, 'value'):
            task_id = task_id.value
        return self._tasks.get(str(task_id))
    
    def find_all(self) -> List[Task]:
        return list(self._tasks.values())
    
    def delete(self, task_id) -> bool:
        if hasattr(task_id, 'value'):
            task_id = task_id.value
        task_id_str = str(task_id)
        if task_id_str in self._tasks:
            del self._tasks[task_id_str]
            return True
        return False
    
    def find_by_status(self, status: str) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == status]
    
    def find_by_git_branch_id(self, git_branch_id: str) -> List[Task]:
        return [t for t in self._tasks.values() if t.git_branch_id == git_branch_id]
    
    def count(self) -> int:
        return len(self._tasks)
    
    def exists(self, task_id) -> bool:
        if hasattr(task_id, 'value'):
            task_id = task_id.value
        return str(task_id) in self._tasks
    
    def search(self, query: str) -> List[Task]:
        results = []
        query_lower = query.lower()
        for task in self._tasks.values():
            if query_lower in task.title.lower() or query_lower in (task.description or '').lower():
                results.append(task)
        return results
    
    def update(self, task: Task) -> Task:
        """Update a task"""
        if task.id in self._tasks:
            self._tasks[task.id] = task
            return task
        raise ValueError(f"Task with id {task.id} not found")
    
    def find_by_assignee(self, assignee: str) -> List[Task]:
        """Find tasks by assignee"""
        return [t for t in self._tasks.values() if hasattr(t, 'assignee') and t.assignee == assignee]
    
    def find_by_priority(self, priority) -> List[Task]:
        """Find tasks by priority"""
        return [t for t in self._tasks.values() if hasattr(t, 'priority') and t.priority == priority]
    
    def find_by_labels(self, labels: List[str]) -> List[Task]:
        """Find tasks containing any of the specified labels"""
        results = []
        for task in self._tasks.values():
            if hasattr(task, 'labels') and task.labels:
                if any(label in task.labels for label in labels):
                    results.append(task)
        return results
    
    def get_next_id(self):
        """Get next available task ID"""
        from ...domain.value_objects import TaskId
        next_id = len(self._tasks) + 1
        return TaskId(f"task-{next_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        total = len(self._tasks)
        pending = len([t for t in self._tasks.values() if hasattr(t, 'status') and t.status == 'pending'])
        in_progress = len([t for t in self._tasks.values() if hasattr(t, 'status') and t.status == 'in_progress'])
        completed = len([t for t in self._tasks.values() if hasattr(t, 'status') and t.status == 'completed'])
        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed
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
    
    def find_by_id_all_states(self, task_id) -> Optional[Task]:
        """Find task by ID across all states (active, completed, archived)"""
        return self.find_by_id(task_id)


class MockSubtaskRepository(SubtaskRepository):
    """Mock subtask repository for testing and development"""
    def __init__(self):
        self._subtasks = {}
        self._next_id = 1
        logger.info("MockSubtaskRepository initialized")
    
    def save(self, subtask: Subtask) -> Subtask:
        self._subtasks[subtask.id] = subtask
        return subtask
    
    def find_by_id(self, subtask_id) -> Optional[Subtask]:
        if hasattr(subtask_id, 'value'):
            subtask_id = subtask_id.value
        return self._subtasks.get(str(subtask_id))
    
    def find_by_task_id(self, task_id: str) -> List[Subtask]:
        return [s for s in self._subtasks.values() if s.task_id == task_id]
    
    def delete(self, subtask_id) -> bool:
        if hasattr(subtask_id, 'value'):
            subtask_id = subtask_id.value
        subtask_id_str = str(subtask_id)
        if subtask_id_str in self._subtasks:
            del self._subtasks[subtask_id_str]
            return True
        return False
    
    def count_by_task_id(self, task_id: str) -> int:
        return len([s for s in self._subtasks.values() if s.task_id == task_id])
    
    def delete_by_task_id(self, task_id: str) -> int:
        to_delete = [s.id for s in self._subtasks.values() if s.task_id == task_id]
        for subtask_id in to_delete:
            del self._subtasks[subtask_id]
        return len(to_delete)
    
    def update(self, subtask: Subtask) -> Subtask:
        """Update a subtask"""
        if subtask.id in self._subtasks:
            self._subtasks[subtask.id] = subtask
            return subtask
        raise ValueError(f"Subtask with id {subtask.id} not found")
    
    def find_by_parent_task_id(self, parent_task_id) -> List[Subtask]:
        """Find all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() if str(s.task_id) == task_id_str]
    
    def find_by_assignee(self, assignee: str) -> List[Subtask]:
        """Find subtasks by assignee"""
        return [s for s in self._subtasks.values() if hasattr(s, 'assignee') and s.assignee == assignee]
    
    def find_by_status(self, status: str) -> List[Subtask]:
        """Find subtasks by status"""
        return [s for s in self._subtasks.values() if hasattr(s, 'status') and s.status == status]
    
    def find_completed(self, parent_task_id) -> List[Subtask]:
        """Find completed subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() 
                if str(s.task_id) == task_id_str and hasattr(s, 'status') and s.status == 'completed']
    
    def find_pending(self, parent_task_id) -> List[Subtask]:
        """Find pending subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return [s for s in self._subtasks.values() 
                if str(s.task_id) == task_id_str and hasattr(s, 'status') and s.status == 'pending']
    
    def exists(self, subtask_id) -> bool:
        """Check if a subtask exists by its id"""
        if hasattr(subtask_id, 'value'):
            subtask_id = subtask_id.value
        return str(subtask_id) in self._subtasks
    
    def count_by_parent_task_id(self, parent_task_id) -> int:
        """Count subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return len([s for s in self._subtasks.values() if str(s.task_id) == task_id_str])
    
    def count_completed_by_parent_task_id(self, parent_task_id) -> int:
        """Count completed subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        return len([s for s in self._subtasks.values() 
                   if str(s.task_id) == task_id_str and hasattr(s, 'status') and s.status == 'completed'])
    
    def get_next_id(self, parent_task_id):
        """Get next available subtask ID for a parent task"""
        from ...domain.value_objects.subtask_id import SubtaskId
        next_id = len(self._subtasks) + 1
        return SubtaskId(f"subtask-{next_id}")
    
    def get_subtask_progress(self, parent_task_id) -> Dict[str, Any]:
        """Get subtask progress statistics for a parent task"""
        subtasks = self.find_by_parent_task_id(parent_task_id)
        completed = len([s for s in subtasks if hasattr(s, 'status') and s.status == 'completed'])
        total = len(subtasks)
        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0
        }
    
    def bulk_update_status(self, parent_task_id, status: str) -> bool:
        """Update status of all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        updated = False
        for subtask in self._subtasks.values():
            if str(subtask.task_id) == task_id_str:
                if hasattr(subtask, 'status'):
                    subtask.status = status
                    updated = True
        return updated
    
    def bulk_complete(self, parent_task_id) -> bool:
        """Mark all subtasks as completed for a parent task"""
        return self.bulk_update_status(parent_task_id, 'completed')
    
    def remove_subtask(self, parent_task_id: str, subtask_id: str) -> bool:
        """Remove a subtask from a parent task by subtask ID"""
        if subtask_id in self._subtasks:
            subtask = self._subtasks[subtask_id]
            if str(subtask.task_id) == parent_task_id:
                del self._subtasks[subtask_id]
                return True
        return False
    
    def delete_by_parent_task_id(self, parent_task_id) -> bool:
        """Delete all subtasks for a parent task"""
        task_id_str = str(parent_task_id)
        to_delete = [s_id for s_id, s in self._subtasks.items() if str(s.task_id) == task_id_str]
        for subtask_id in to_delete:
            del self._subtasks[subtask_id]
        return len(to_delete) > 0


class MockAgentRepository:
    """Mock agent repository for testing and development"""
    def __init__(self):
        self._agents = {}
        logger.info("MockAgentRepository initialized")


class MockRepositoryFactory:
    """Factory for creating mock repositories"""
    def __init__(self):
        self._project_repo = MockProjectRepository()
        self._git_branch_repo = MockGitBranchRepository()
        self._task_repo = MockTaskRepository()
        self._subtask_repo = MockSubtaskRepository()
        self._agent_repo = MockAgentRepository()
    
    def get_project_repository(self) -> MockProjectRepository:
        return self._project_repo
    
    def get_git_branch_repository(self) -> MockGitBranchRepository:
        return self._git_branch_repo
    
    def get_task_repository(self, project_id: str = None, git_branch_id: str = None, user_id: str = None) -> MockTaskRepository:
        return self._task_repo
    
    def get_subtask_repository(self, project_id: str = None, git_branch_id: str = None, user_id: str = None) -> MockSubtaskRepository:
        return self._subtask_repo
    
    def get_agent_repository(self) -> MockAgentRepository:
        return self._agent_repo


def create_mock_repositories():
    """Create a set of mock repositories for testing"""
    return {
        'project': MockProjectRepository(),
        'git_branch': MockGitBranchRepository(),
        'task': lambda p, b, u: MockTaskRepository(),
        'subtask': lambda p, b, u: MockSubtaskRepository(),
        'agent': MockAgentRepository()
    }


# Export all mock classes
__all__ = [
    'MockProjectRepository',
    'MockGitBranchRepository',
    'MockTaskRepository',
    'MockSubtaskRepository',
    'MockAgentRepository',
    'MockRepositoryFactory',
    'create_mock_repositories'
]