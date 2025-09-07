"""Mock Repository Factory - Wrapper for Test Fixtures

This module maintains backward compatibility by importing mock implementations
from the test fixtures. The actual implementations are maintained in:
tests/fixtures/mocks/repositories/mock_repository_factory.py

This allows production code to continue using the same import paths
while the actual mock implementations are properly organized in the test suite.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Add tests directory to path to import from fixtures
# Navigate up from src/fastmcp/task_management/infrastructure/repositories to project root
project_root = Path(__file__).resolve().parents[5]  # Goes to dhafnck_mcp_main
tests_path = project_root / "tests"
if str(tests_path) not in sys.path:
    sys.path.insert(0, str(tests_path))

# Try to import from test fixtures, otherwise use the copies in fixtures
try:
    # Import all mocks from test fixtures
    from fixtures.mocks.repositories.mock_repository_factory import (
        MockProjectRepository,
        MockGitBranchRepository,
        MockTaskRepository,
        MockSubtaskRepository,
        MockRepositoryFactory
    )
    logger.debug("Mock repositories successfully imported from test fixtures")
    
except ImportError as e:
    logger.warning(f"Could not import from test fixtures: {e}")
    logger.warning("Falling back to copied implementations in fixtures directory")
    
    # If test fixtures not available (e.g., in Docker), 
    # the implementations are also copied to the fixtures directory
    try:
        # Try alternate import path
        import fixtures.mocks.repositories.mock_repository_factory as mock_module
        
        MockProjectRepository = mock_module.MockProjectRepository
        MockGitBranchRepository = mock_module.MockGitBranchRepository
        MockTaskRepository = mock_module.MockTaskRepository
        MockSubtaskRepository = mock_module.MockSubtaskRepository
        MockRepositoryFactory = mock_module.MockRepositoryFactory
        
    except ImportError:
        # Last resort: Define minimal mock implementations inline
        logger.error("Could not import mock implementations from any location")
        logger.error("Defining minimal mock implementations inline")
        
        from ...domain.repositories.project_repository import ProjectRepository
        from ...domain.repositories.git_branch_repository import GitBranchRepository
        from ...domain.repositories.task_repository import TaskRepository
        from ...domain.repositories.subtask_repository import SubtaskRepository
        from ...domain.entities.project import Project
        from ...domain.entities.git_branch import GitBranch
        from ...domain.entities.task import Task
        from ...domain.entities.subtask import Subtask
        from typing import List, Optional
        from datetime import datetime
        import uuid
        
        class MockProjectRepository(ProjectRepository):
            """Minimal mock project repository"""
            def __init__(self):
                self._projects = {}
                logger.warning("Using minimal inline MockProjectRepository")
            
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
            """Minimal mock git branch repository"""
            def __init__(self):
                self._branches = {}
                logger.warning("Using minimal inline MockGitBranchRepository")
            
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
            """Minimal mock task repository"""
            def __init__(self):
                self._tasks = {}
                self._next_id = 1
                logger.warning("Using minimal inline MockTaskRepository")
            
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
            """Minimal mock subtask repository"""
            def __init__(self):
                self._subtasks = {}
                self._next_id = 1
                logger.warning("Using minimal inline MockSubtaskRepository")
            
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
            """Minimal mock agent repository"""
            def __init__(self):
                self._agents = {}
                logger.warning("Using minimal inline MockAgentRepository")
        
        def create_mock_repositories():
            """Create a set of mock repositories for testing"""
            return {
                'project': MockProjectRepository(),
                'git_branch': MockGitBranchRepository(),
                'task': lambda p, b, u: MockTaskRepository(),
                'subtask': lambda p, b, u: MockSubtaskRepository(),
                'agent': MockAgentRepository()
            }

# Define MockAgentRepository and create_mock_repositories if not imported
try:
    # Try to access MockAgentRepository to see if it was defined
    _ = MockAgentRepository
except NameError:
    # MockAgentRepository was not imported or defined, create it
    class MockAgentRepository:
        """Minimal mock agent repository"""
        def __init__(self):
            self._agents = {}
            logger.warning("Using minimal MockAgentRepository")

try:
    # Try to access create_mock_repositories to see if it was defined
    _ = create_mock_repositories
except NameError:
    # create_mock_repositories was not defined, create it
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
    'create_mock_repositories',
    'MockRepositoryFactory'
]