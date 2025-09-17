"""Service for resolving task dependency chains and relationships"""

import logging
from typing import List, Dict, Optional, Set, Any
from collections import defaultdict, deque
from datetime import datetime

from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError
from fastmcp.task_management.application.dtos.task.dependency_info import DependencyInfo, DependencyChain, DependencyRelationships

logger = logging.getLogger(__name__)


class DependencyResolverService:
    """Service to resolve and analyze task dependency relationships"""
    
    def __init__(self, task_repository: TaskRepository, user_id: Optional[str] = None):
        self.task_repository = task_repository
        self._user_id = user_id  # Store user context
    
    def _get_user_scoped_repository(self) -> TaskRepository:
        """Get a user-scoped version of the repository if it supports user context."""
        if hasattr(self.task_repository, 'with_user') and self._user_id:
            return self.task_repository.with_user(self._user_id)
        elif hasattr(self.task_repository, 'user_id'):
            if self._user_id and self.task_repository.user_id != self._user_id:
                repo_class = type(self.task_repository)
                if hasattr(self.task_repository, 'session'):
                    return repo_class(self.task_repository.session, user_id=self._user_id)
        return self.task_repository
    
    def with_user(self, user_id: str) -> 'DependencyResolverService':
        """Create a new service instance scoped to a specific user."""
        return DependencyResolverService(self.task_repository, user_id)
    
    def resolve_dependencies(self, task_id: str) -> DependencyRelationships:
        """
        Resolve complete dependency information for a task
        
        Args:
            task_id: The task ID to resolve dependencies for
            
        Returns:
            DependencyRelationships containing complete dependency information
        """
        try:
            # Get user-scoped repository
            repo = self._get_user_scoped_repository()
            
            # Get the main task
            main_task = repo.find_by_id(TaskId(task_id))
            if not main_task:
                raise TaskNotFoundError(f"Task {task_id} not found")
            
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(task_id)
            
            # Resolve direct dependencies
            depends_on = self._resolve_direct_dependencies(main_task.get_dependency_ids())
            blocks = self._resolve_blocking_tasks(task_id)
            
            # Build dependency chains
            upstream_chains = self._build_upstream_chains(task_id, dependency_graph)
            downstream_chains = self._build_downstream_chains(task_id, dependency_graph)
            
            # Calculate summary information
            total_dependencies = len(depends_on)
            completed_dependencies = sum(1 for dep in depends_on if dep.status == 'done')
            blocked_dependencies = sum(1 for dep in depends_on if dep.status == 'blocked')
            
            # Determine status indicators
            can_start = self._can_task_start(depends_on)
            is_blocked = self._is_task_blocked(depends_on)
            is_blocking_others = len(blocks) > 0
            
            # Generate workflow information
            dependency_summary = self._generate_dependency_summary(depends_on, blocks)
            next_actions = self._generate_next_actions(depends_on, blocks, can_start)
            blocking_reasons = self._generate_blocking_reasons(depends_on)
            
            return DependencyRelationships(
                task_id=task_id,
                depends_on=depends_on,
                blocks=blocks,
                upstream_chains=upstream_chains,
                downstream_chains=downstream_chains,
                total_dependencies=total_dependencies,
                completed_dependencies=completed_dependencies,
                blocked_dependencies=blocked_dependencies,
                can_start=can_start,
                is_blocked=is_blocked,
                is_blocking_others=is_blocking_others,
                dependency_summary=dependency_summary,
                next_actions=next_actions,
                blocking_reasons=blocking_reasons
            )
            
        except TaskNotFoundError:
            # Re-raise TaskNotFoundError to caller
            raise
        except Exception as e:
            logger.error(f"Error resolving dependencies for task {task_id}: {e}")
            # Return empty relationships on other errors
            return DependencyRelationships(
                task_id=task_id,
                depends_on=[],
                blocks=[],
                upstream_chains=[],
                downstream_chains=[],
                total_dependencies=0,
                completed_dependencies=0,
                blocked_dependencies=0,
                can_start=True,
                is_blocked=False,
                is_blocking_others=False,
                dependency_summary="Unable to resolve dependencies",
                next_actions=["Check task dependencies manually"],
                blocking_reasons=[]
            )
    
    def _build_dependency_graph(self, root_task_id: str) -> Dict[str, List[str]]:
        """Build a complete dependency graph starting from root task"""
        graph = defaultdict(list)
        visited = set()
        
        def traverse(task_id: str, depth: int = 0):
            if task_id in visited or depth > 10:  # Prevent infinite loops
                return
            
            visited.add(task_id)
            
            try:
                task = self.task_repository.find_by_id(TaskId(task_id))
                if task:
                    dependencies = task.get_dependency_ids()
                    graph[task_id] = dependencies
                    
                    # Recursively traverse dependencies
                    for dep_id in dependencies:
                        traverse(dep_id, depth + 1)
            except Exception as e:
                logger.warning(f"Error traversing task {task_id}: {e}")
        
        traverse(root_task_id)
        return dict(graph)
    
    def _resolve_direct_dependencies(self, dependency_ids: List[str]) -> List[DependencyInfo]:
        """Resolve direct dependencies to DependencyInfo objects"""
        dependencies = []
        
        for dep_id in dependency_ids:
            try:
                task = self.task_repository.find_by_id(TaskId(dep_id))
                if task:
                    dep_info = DependencyInfo(
                        task_id=dep_id,
                        title=task.title,
                        status=task.status.value,
                        priority=task.priority.value,
                        completion_percentage=task.overall_progress,
                        is_blocking=False,  # Will be calculated separately
                        is_blocked=self._is_task_blocked_by_dependencies(task),
                        estimated_effort=task.estimated_effort,
                        assignees=task.assignees.copy() if task.assignees else [],
                        updated_at=task.updated_at
                    )
                    dependencies.append(dep_info)
            except Exception as e:
                logger.warning(f"Error resolving dependency {dep_id}: {e}")
        
        return dependencies
    
    def _resolve_blocking_tasks(self, task_id: str) -> List[DependencyInfo]:
        """Find tasks that are blocked by this task"""
        blocking_tasks = []
        
        try:
            # Find all tasks that depend on this task
            all_tasks = self.task_repository.find_all()
            
            for task in all_tasks:
                if task_id in task.get_dependency_ids():
                    dep_info = DependencyInfo(
                        task_id=str(task.id),
                        title=task.title,
                        status=task.status.value,
                        priority=task.priority.value,
                        completion_percentage=task.overall_progress,
                        is_blocking=True,
                        is_blocked=self._is_task_blocked_by_dependencies(task),
                        estimated_effort=task.estimated_effort,
                        assignees=task.assignees.copy() if task.assignees else [],
                        updated_at=task.updated_at
                    )
                    blocking_tasks.append(dep_info)
        except Exception as e:
            logger.warning(f"Error finding blocking tasks for {task_id}: {e}")
        
        return blocking_tasks
    
    def _build_upstream_chains(self, task_id: str, dependency_graph: Dict[str, List[str]]) -> List[DependencyChain]:
        """Build upstream dependency chains"""
        chains = []
        
        # Use topological sort to build chains
        def build_chain(start_task: str, visited: Set[str]) -> Optional[DependencyChain]:
            if start_task in visited:
                return None
            
            visited.add(start_task)
            chain_tasks = []
            
            # BFS to build chain
            queue = deque([start_task])
            while queue:
                current_task = queue.popleft()
                
                try:
                    task = self.task_repository.find_by_id(TaskId(current_task))
                    if task:
                        dep_info = DependencyInfo(
                            task_id=current_task,
                            title=task.title,
                            status=task.status.value,
                            priority=task.priority.value,
                            completion_percentage=task.overall_progress,
                            is_blocking=False,
                            is_blocked=self._is_task_blocked_by_dependencies(task),
                            estimated_effort=task.estimated_effort,
                            assignees=task.assignees.copy() if task.assignees else [],
                            updated_at=task.updated_at
                        )
                        chain_tasks.append(dep_info)
                        
                        # Add dependencies to queue
                        for dep_id in dependency_graph.get(current_task, []):
                            if dep_id not in visited:
                                queue.append(dep_id)
                                visited.add(dep_id)
                except Exception as e:
                    logger.warning(f"Error building chain for task {current_task}: {e}")
            
            if chain_tasks:
                completed_tasks = sum(1 for t in chain_tasks if t.status == 'done')
                blocked_tasks = sum(1 for t in chain_tasks if t.status == 'blocked')
                
                # Determine chain status
                if completed_tasks == len(chain_tasks):
                    chain_status = 'completed'
                elif blocked_tasks > 0:
                    chain_status = 'blocked'
                elif any(t.status == 'in_progress' for t in chain_tasks):
                    chain_status = 'in_progress'
                else:
                    chain_status = 'not_started'
                
                return DependencyChain(
                    chain_id=f"upstream_{start_task}",
                    tasks=chain_tasks,
                    total_tasks=len(chain_tasks),
                    completed_tasks=completed_tasks,
                    blocked_tasks=blocked_tasks,
                    chain_status=chain_status
                )
            
            return None
        
        # Build chains for each direct dependency
        visited = set()
        for dep_id in dependency_graph.get(task_id, []):
            chain = build_chain(dep_id, visited)
            if chain:
                chains.append(chain)
        
        return chains
    
    def _build_downstream_chains(self, task_id: str, dependency_graph: Dict[str, List[str]]) -> List[DependencyChain]:
        """Build downstream dependency chains (tasks that depend on this task)"""
        chains = []
        
        # Find tasks that depend on this task
        dependent_tasks = []
        for tid, deps in dependency_graph.items():
            if task_id in deps:
                dependent_tasks.append(tid)
        
        # Build chains for each dependent task
        for dep_task in dependent_tasks:
            chain_tasks = []
            
            try:
                task = self.task_repository.find_by_id(TaskId(dep_task))
                if task:
                    dep_info = DependencyInfo(
                        task_id=dep_task,
                        title=task.title,
                        status=task.status.value,
                        priority=task.priority.value,
                        completion_percentage=task.overall_progress,
                        is_blocking=True,
                        is_blocked=self._is_task_blocked_by_dependencies(task),
                        estimated_effort=task.estimated_effort,
                        assignees=task.assignees.copy() if task.assignees else [],
                        updated_at=task.updated_at
                    )
                    chain_tasks.append(dep_info)
                    
                    if chain_tasks:
                        completed_tasks = sum(1 for t in chain_tasks if t.status == 'done')
                        blocked_tasks = sum(1 for t in chain_tasks if t.status == 'blocked')
                        
                        chain_status = 'completed' if completed_tasks == len(chain_tasks) else 'in_progress'
                        
                        chain = DependencyChain(
                            chain_id=f"downstream_{dep_task}",
                            tasks=chain_tasks,
                            total_tasks=len(chain_tasks),
                            completed_tasks=completed_tasks,
                            blocked_tasks=blocked_tasks,
                            chain_status=chain_status
                        )
                        chains.append(chain)
            except Exception as e:
                logger.warning(f"Error building downstream chain for {dep_task}: {e}")
        
        return chains
    
    def _can_task_start(self, dependencies: List[DependencyInfo]) -> bool:
        """Check if task can start based on dependencies"""
        return all(dep.status == 'done' for dep in dependencies)
    
    def _is_task_blocked(self, dependencies: List[DependencyInfo]) -> bool:
        """Check if task is blocked by dependencies"""
        return any(dep.status == 'blocked' for dep in dependencies)
    
    def _is_task_blocked_by_dependencies(self, task) -> bool:
        """Check if a task is blocked by its dependencies"""
        dependency_ids = task.get_dependency_ids()
        for dep_id in dependency_ids:
            try:
                dep_task = self.task_repository.find_by_id(TaskId(dep_id))
                if dep_task and dep_task.status.value not in ['done', 'cancelled']:
                    return True
            except Exception:
                pass
        return False
    
    def _generate_dependency_summary(self, depends_on: List[DependencyInfo], blocks: List[DependencyInfo]) -> str:
        """Generate human-readable dependency summary"""
        if not depends_on and not blocks:
            return "No dependencies"
        
        summary_parts = []
        
        if depends_on:
            completed = sum(1 for dep in depends_on if dep.status == 'done')
            total = len(depends_on)
            summary_parts.append(f"Depends on {total} task(s) ({completed}/{total} completed)")
        
        if blocks:
            summary_parts.append(f"Blocks {len(blocks)} task(s)")
        
        return " | ".join(summary_parts)
    
    def _generate_next_actions(self, depends_on: List[DependencyInfo], blocks: List[DependencyInfo], can_start: bool) -> List[str]:
        """Generate suggested next actions based on dependencies"""
        actions = []
        
        if can_start:
            actions.append("✅ Ready to start - no blocking dependencies")
        else:
            incomplete_deps = [dep for dep in depends_on if dep.status != 'done']
            if incomplete_deps:
                actions.append(f"⏳ Wait for {len(incomplete_deps)} dependencies to complete")
                
                # Suggest working on dependencies
                todo_deps = [dep for dep in incomplete_deps if dep.status == 'todo']
                if todo_deps:
                    actions.append(f"💡 Consider working on {len(todo_deps)} unstarted dependencies")
        
        if blocks:
            actions.append(f"🚧 Completing this task will unblock {len(blocks)} other task(s)")
        
        return actions
    
    def _generate_blocking_reasons(self, depends_on: List[DependencyInfo]) -> List[str]:
        """Generate reasons why task is blocked"""
        reasons = []
        
        for dep in depends_on:
            if dep.status != 'done':
                reasons.append(f"'{dep.title}' ({dep.status})")
        
        return reasons