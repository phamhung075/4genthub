"""
Cascade Calculator Service for Entity Relationships

This service efficiently calculates all affected entities when a change occurs
in the system. It tracks relationships between tasks, subtasks, branches,
projects, and contexts using materialized views for optimal performance.

Performance Requirements:
- Cascade calculation must complete in < 50ms
- Uses materialized views for aggregations
- Implements caching for repeated calculations
- Efficient deduplication algorithm

Clean Code Requirements:
- NO backward compatibility code
- NO legacy patterns
- Direct implementation only
- Clean error handling
"""

import logging
import time
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..entities.task import Task
from ..entities.subtask import Subtask
from ..entities.project import Project

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Supported entity types for cascade calculation"""
    TASK = "task"
    SUBTASK = "subtask"
    BRANCH = "branch"
    PROJECT = "project"
    CONTEXT = "context"


@dataclass
class CascadeResult:
    """Result of cascade calculation containing all affected entities"""

    entity_id: str
    entity_type: EntityType
    affected_tasks: Set[str]
    affected_subtasks: Set[str]
    affected_branches: Set[str]
    affected_projects: Set[str]
    affected_contexts: Set[str]
    calculation_time_ms: float
    cache_hit: bool = False

    def get_all_affected_ids(self) -> Set[str]:
        """Get all affected entity IDs regardless of type"""
        return (
            self.affected_tasks |
            self.affected_subtasks |
            self.affected_branches |
            self.affected_projects |
            self.affected_contexts
        )

    def get_affected_count(self) -> int:
        """Get total count of affected entities"""
        return len(self.get_all_affected_ids())


class CascadeCalculator:
    """
    Service that efficiently calculates all affected entities when a change occurs.

    This service tracks relationships between tasks, subtasks, branches, projects,
    and contexts using materialized views for optimal performance.
    """

    def __init__(self, session: AsyncSession):
        """Initialize cascade calculator with database session"""
        self.session = session
        self._cache: Dict[str, CascadeResult] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
        self._cache_timestamps: Dict[str, float] = {}

    async def calculate_cascade(
        self,
        entity_id: str,
        entity_type: Optional[EntityType] = None,
        use_cache: bool = True
    ) -> CascadeResult:
        """
        Main cascade calculation method that determines entity type and delegates.

        Args:
            entity_id: UUID of the entity that changed
            entity_type: Type of entity (auto-detected if None)
            use_cache: Whether to use cached results

        Returns:
            CascadeResult containing all affected entities
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"{entity_id}:{entity_type.value if entity_type else 'auto'}"
        if use_cache and self._is_cache_valid(cache_key):
            result = self._cache[cache_key]
            result.cache_hit = True
            logger.debug(f"Cache hit for cascade calculation: {cache_key}")
            return result

        # Auto-detect entity type if not provided
        if entity_type is None:
            entity_type = await self._detect_entity_type(entity_id)

        # Delegate to specific cascade method based on entity type
        if entity_type == EntityType.TASK:
            result = await self.calculate_task_cascade(entity_id)
        elif entity_type == EntityType.SUBTASK:
            result = await self.calculate_subtask_cascade(entity_id)
        elif entity_type == EntityType.BRANCH:
            result = await self.calculate_branch_cascade(entity_id)
        elif entity_type == EntityType.PROJECT:
            result = await self.calculate_project_cascade(entity_id)
        elif entity_type == EntityType.CONTEXT:
            result = await self.calculate_context_cascade(entity_id)
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        # Calculate total time
        result.calculation_time_ms = (time.time() - start_time) * 1000

        # Cache the result
        if use_cache:
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()

        # Log performance warning if > 50ms
        if result.calculation_time_ms > 50:
            logger.warning(
                f"Cascade calculation exceeded 50ms: {result.calculation_time_ms:.2f}ms "
                f"for {entity_type.value} {entity_id}"
            )

        return result

    async def calculate_task_cascade(self, task_id: str) -> CascadeResult:
        """
        Calculate cascade when a task changes.

        When a task changes, find:
        - Parent tasks (if this is a dependency)
        - All subtasks
        - Branch summary recalculation
        - Project metrics update
        - Related contexts
        """
        affected_tasks = {task_id}
        affected_subtasks = set()
        affected_branches = set()
        affected_projects = set()
        affected_contexts = set()

        # Get task details
        task_query = text("""
            SELECT t.id, t.git_branch_id, b.project_id, t.context_id
            FROM tasks t
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            WHERE t.id = :task_id
        """)

        task_result = await self.session.execute(task_query, {"task_id": task_id})
        task_row = task_result.fetchone()

        if not task_row:
            logger.warning(f"Task not found: {task_id}")
            return CascadeResult(
                entity_id=task_id,
                entity_type=EntityType.TASK,
                affected_tasks=affected_tasks,
                affected_subtasks=affected_subtasks,
                affected_branches=affected_branches,
                affected_projects=affected_projects,
                affected_contexts=affected_contexts,
                calculation_time_ms=0.0
            )

        branch_id = task_row[1]
        project_id = task_row[2]
        context_id = task_row[3]

        # Add affected branch and project
        affected_branches.add(branch_id)
        affected_projects.add(project_id)

        if context_id:
            affected_contexts.add(context_id)

        # Find all subtasks
        subtasks_query = text("""
            SELECT id FROM subtasks WHERE task_id = :task_id
        """)

        subtasks_result = await self.session.execute(subtasks_query, {"task_id": task_id})
        for row in subtasks_result:
            affected_subtasks.add(row[0])

        # Find parent tasks that depend on this task
        parent_tasks_query = text("""
            SELECT DISTINCT td.task_id
            FROM task_dependencies td
            WHERE td.dependency_id = :task_id
        """)

        parent_tasks_result = await self.session.execute(parent_tasks_query, {"task_id": task_id})
        for row in parent_tasks_result:
            affected_tasks.add(row[0])

        # Get related contexts for the branch and project
        related_contexts = await self._get_related_contexts(branch_id, project_id)
        affected_contexts.update(related_contexts)

        return CascadeResult(
            entity_id=task_id,
            entity_type=EntityType.TASK,
            affected_tasks=affected_tasks,
            affected_subtasks=affected_subtasks,
            affected_branches=affected_branches,
            affected_projects=affected_projects,
            affected_contexts=affected_contexts,
            calculation_time_ms=0.0  # Will be set by caller
        )

    async def calculate_subtask_cascade(self, subtask_id: str) -> CascadeResult:
        """
        Calculate cascade when a subtask changes.

        When a subtask changes, cascade to parent task.
        """
        affected_tasks = set()
        affected_subtasks = {subtask_id}
        affected_branches = set()
        affected_projects = set()
        affected_contexts = set()

        # Get subtask details
        subtask_query = text("""
            SELECT s.task_id, t.git_branch_id, b.project_id, t.context_id
            FROM subtasks s
            JOIN tasks t ON s.task_id = t.id
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            WHERE s.id = :subtask_id
        """)

        subtask_result = await self.session.execute(subtask_query, {"subtask_id": subtask_id})
        subtask_row = subtask_result.fetchone()

        if not subtask_row:
            logger.warning(f"Subtask not found: {subtask_id}")
            return CascadeResult(
                entity_id=subtask_id,
                entity_type=EntityType.SUBTASK,
                affected_tasks=affected_tasks,
                affected_subtasks=affected_subtasks,
                affected_branches=affected_branches,
                affected_projects=affected_projects,
                affected_contexts=affected_contexts,
                calculation_time_ms=0.0
            )

        task_id = subtask_row[0]
        branch_id = subtask_row[1]
        project_id = subtask_row[2]
        context_id = subtask_row[3]

        # Add affected entities
        affected_tasks.add(task_id)
        affected_branches.add(branch_id)
        affected_projects.add(project_id)

        if context_id:
            affected_contexts.add(context_id)

        # Get related contexts
        related_contexts = await self._get_related_contexts(branch_id, project_id)
        affected_contexts.update(related_contexts)

        return CascadeResult(
            entity_id=subtask_id,
            entity_type=EntityType.SUBTASK,
            affected_tasks=affected_tasks,
            affected_subtasks=affected_subtasks,
            affected_branches=affected_branches,
            affected_projects=affected_projects,
            affected_contexts=affected_contexts,
            calculation_time_ms=0.0
        )

    async def calculate_branch_cascade(self, branch_id: str) -> CascadeResult:
        """
        Calculate cascade when a branch changes.

        When a branch changes, cascade to project summary.
        """
        affected_tasks = set()
        affected_subtasks = set()
        affected_branches = {branch_id}
        affected_projects = set()
        affected_contexts = set()

        # Get branch details and all tasks
        branch_query = text("""
            SELECT DISTINCT b.project_id, t.id as task_id, s.id as subtask_id
            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE b.id = :branch_id
        """)

        branch_result = await self.session.execute(branch_query, {"branch_id": branch_id})
        project_id = None

        for row in branch_result:
            if project_id is None:
                project_id = row[0]
                affected_projects.add(project_id)

            if row[1]:  # task_id
                affected_tasks.add(row[1])

            if row[2]:  # subtask_id
                affected_subtasks.add(row[2])

        if not project_id:
            logger.warning(f"Branch not found: {branch_id}")
            return CascadeResult(
                entity_id=branch_id,
                entity_type=EntityType.BRANCH,
                affected_tasks=affected_tasks,
                affected_subtasks=affected_subtasks,
                affected_branches=affected_branches,
                affected_projects=affected_projects,
                affected_contexts=affected_contexts,
                calculation_time_ms=0.0
            )

        # Get related contexts
        related_contexts = await self._get_related_contexts(branch_id, project_id)
        affected_contexts.update(related_contexts)

        return CascadeResult(
            entity_id=branch_id,
            entity_type=EntityType.BRANCH,
            affected_tasks=affected_tasks,
            affected_subtasks=affected_subtasks,
            affected_branches=affected_branches,
            affected_projects=affected_projects,
            affected_contexts=affected_contexts,
            calculation_time_ms=0.0
        )

    async def calculate_project_cascade(self, project_id: str) -> CascadeResult:
        """
        Calculate cascade when a project changes.

        When a project changes, find all affected branches and their tasks.
        """
        affected_tasks = set()
        affected_subtasks = set()
        affected_branches = set()
        affected_projects = {project_id}
        affected_contexts = set()

        # Get all branches, tasks, and subtasks in project
        project_query = text("""
            SELECT DISTINCT b.id as branch_id, t.id as task_id, s.id as subtask_id
            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE b.project_id = :project_id
        """)

        project_result = await self.session.execute(project_query, {"project_id": project_id})

        for row in project_result:
            if row[0]:  # branch_id
                affected_branches.add(row[0])

            if row[1]:  # task_id
                affected_tasks.add(row[1])

            if row[2]:  # subtask_id
                affected_subtasks.add(row[2])

        # Get related contexts for all branches
        for branch_id in affected_branches:
            related_contexts = await self._get_related_contexts(branch_id, project_id)
            affected_contexts.update(related_contexts)

        return CascadeResult(
            entity_id=project_id,
            entity_type=EntityType.PROJECT,
            affected_tasks=affected_tasks,
            affected_subtasks=affected_subtasks,
            affected_branches=affected_branches,
            affected_projects=affected_projects,
            affected_contexts=affected_contexts,
            calculation_time_ms=0.0
        )

    async def calculate_context_cascade(self, context_id: str) -> CascadeResult:
        """
        Calculate cascade when a context changes.

        When a context changes, find all related entities.
        """
        affected_tasks = set()
        affected_subtasks = set()
        affected_branches = set()
        affected_projects = set()
        affected_contexts = {context_id}

        # Find tasks with this context
        context_query = text("""
            SELECT DISTINCT t.id as task_id, t.git_branch_id, b.project_id, s.id as subtask_id
            FROM tasks t
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE t.context_id = :context_id
        """)

        context_result = await self.session.execute(context_query, {"context_id": context_id})

        for row in context_result:
            if row[0]:  # task_id
                affected_tasks.add(row[0])

            if row[1]:  # branch_id
                affected_branches.add(row[1])

            if row[2]:  # project_id
                affected_projects.add(row[2])

            if row[3]:  # subtask_id
                affected_subtasks.add(row[3])

        return CascadeResult(
            entity_id=context_id,
            entity_type=EntityType.CONTEXT,
            affected_tasks=affected_tasks,
            affected_subtasks=affected_subtasks,
            affected_branches=affected_branches,
            affected_projects=affected_projects,
            affected_contexts=affected_contexts,
            calculation_time_ms=0.0
        )

    async def _get_branch_summary(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """Query branch_summaries_mv materialized view"""
        query = text("""
            SELECT * FROM branch_summaries_mv WHERE branch_id = :branch_id
        """)

        result = await self.session.execute(query, {"branch_id": branch_id})
        row = result.fetchone()

        if row:
            return dict(row._mapping)
        return None

    async def _get_project_metrics(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Query project_summaries_mv materialized view"""
        query = text("""
            SELECT * FROM project_summaries_mv WHERE project_id = :project_id
        """)

        result = await self.session.execute(query, {"project_id": project_id})
        row = result.fetchone()

        if row:
            return dict(row._mapping)
        return None

    async def _calculate_parent_progress(self, task_id: str) -> float:
        """Calculate parent task progress from subtasks"""
        query = text("""
            SELECT AVG(progress_percentage) as avg_progress
            FROM subtasks
            WHERE task_id = :task_id
        """)

        result = await self.session.execute(query, {"task_id": task_id})
        row = result.fetchone()

        return float(row[0]) if row and row[0] is not None else 0.0

    async def _get_related_contexts(self, branch_id: str, project_id: str) -> Set[str]:
        """Find contexts related to branch and project"""
        contexts = set()

        # Find contexts from tasks in the branch
        context_query = text("""
            SELECT DISTINCT context_id
            FROM tasks t
            WHERE t.git_branch_id = :branch_id AND context_id IS NOT NULL
        """)

        try:
            result = await self.session.execute(context_query, {"branch_id": branch_id})
            for row in result:
                if row[0]:
                    contexts.add(row[0])
        except Exception as e:
            logger.debug(f"Context query failed (expected for some schemas): {e}")

        return contexts

    async def _detect_entity_type(self, entity_id: str) -> EntityType:
        """Auto-detect entity type by checking which table contains the ID"""
        # Check tasks table
        task_query = text("""
            SELECT COUNT(*) FROM tasks WHERE id = :entity_id
        """)

        result = await self.session.execute(task_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.TASK

        # Check subtasks table
        subtask_query = text("""
            SELECT COUNT(*) FROM subtasks WHERE id = :entity_id
        """)

        result = await self.session.execute(subtask_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.SUBTASK

        # Check branches table
        branch_query = text("""
            SELECT COUNT(*) FROM project_git_branchs WHERE id = :entity_id
        """)

        result = await self.session.execute(branch_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.BRANCH

        # Check projects table
        project_query = text("""
            SELECT COUNT(*) FROM projects WHERE id = :entity_id
        """)

        result = await self.session.execute(project_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.PROJECT

        # Default to context if not found in other tables
        return EntityType.CONTEXT

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid (not expired)"""
        if cache_key not in self._cache:
            return False

        timestamp = self._cache_timestamps.get(cache_key, 0)
        return (time.time() - timestamp) < self._cache_ttl_seconds

    def clear_cache(self) -> None:
        """Clear all cached results"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.debug("Cascade calculator cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(self._cache),
            "cache_entries": list(self._cache.keys()),
            "cache_ttl_seconds": self._cache_ttl_seconds
        }