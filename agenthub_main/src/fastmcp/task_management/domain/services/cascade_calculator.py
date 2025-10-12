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
from typing import Dict, Optional, Set, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from .protocols.cascade_data_provider import CascadeDataProvider

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
    Domain service that calculates all affected entities when a change occurs.

    This service uses a CascadeDataProvider Protocol to access data, following
    the Dependency Inversion Principle. It operates purely in the domain layer
    without knowledge of infrastructure details like databases or ORMs.

    The data provider is injected during initialization, allowing for:
    - Clean separation between domain and infrastructure
    - Easy testing with mock data providers
    - Infrastructure independence (can switch databases without changing domain logic)
    """

    def __init__(self, data_provider: "CascadeDataProvider"):
        """
        Initialize cascade calculator with data provider.

        Args:
            data_provider: Implementation of CascadeDataProvider Protocol
                          (e.g., SQLAlchemyCascadeDataProvider)
        """
        self._data_provider = data_provider
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
            entity_type = await self._data_provider.detect_entity_type(entity_id)
            if entity_type is None:
                raise ValueError(f"Could not detect entity type for ID: {entity_id}")

        # Delegate to specific cascade method based on entity type
        if entity_type == EntityType.TASK:
            result = await self.calculate_task_cascade(entity_id)
        elif entity_type == EntityType.SUBTASK:
            result = await self.calculate_subtask_cascade(entity_id)
        elif entity_type == EntityType.BRANCH:
            result = await self.calculate_branch_cascade(entity_id)
        elif entity_type == EntityType.PROJECT:
            result = await self.calculate_project_cascade(entity_id)
        else:  # entity_type == EntityType.CONTEXT
            result = await self.calculate_context_cascade(entity_id)

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

        # Get task details using data provider
        task_data = await self._data_provider.get_task_cascade_data(task_id)

        if not task_data:
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

        # Add affected branch and project
        affected_branches.add(task_data.git_branch_id)
        affected_projects.add(task_data.project_id)

        if task_data.context_id:
            affected_contexts.add(task_data.context_id)

        # Find all subtasks
        subtask_ids = await self._data_provider.get_task_subtask_ids(task_id)
        affected_subtasks.update(subtask_ids)

        # Find parent tasks that depend on this task
        parent_task_ids = await self._data_provider.get_task_parent_task_ids(task_id)
        affected_tasks.update(parent_task_ids)

        # Get related contexts for the branch and project
        related_contexts = await self._data_provider.get_related_context_ids(
            task_data.git_branch_id, task_data.project_id
        )
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

        # Get subtask details using data provider
        subtask_data = await self._data_provider.get_subtask_cascade_data(subtask_id)

        if not subtask_data:
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

        # Add affected entities
        affected_tasks.add(subtask_data.task_id)
        affected_branches.add(subtask_data.git_branch_id)
        affected_projects.add(subtask_data.project_id)

        if subtask_data.context_id:
            affected_contexts.add(subtask_data.context_id)

        # Get related contexts
        related_contexts = await self._data_provider.get_related_context_ids(
            subtask_data.git_branch_id, subtask_data.project_id
        )
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

        # Get branch details using data provider
        branch_data = await self._data_provider.get_branch_cascade_data(branch_id)

        if not branch_data:
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

        # Add affected entities
        affected_projects.add(branch_data.project_id)
        affected_tasks.update(branch_data.task_ids)
        affected_subtasks.update(branch_data.subtask_ids)

        # Get related contexts
        related_contexts = await self._data_provider.get_related_context_ids(
            branch_id, branch_data.project_id
        )
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

        # Get project details using data provider
        project_data = await self._data_provider.get_project_cascade_data(project_id)

        if not project_data:
            logger.warning(f"Project not found: {project_id}")
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

        # Add affected entities
        affected_branches.update(project_data.branch_ids)
        affected_tasks.update(project_data.task_ids)
        affected_subtasks.update(project_data.subtask_ids)

        # Get related contexts for all branches
        for branch_id in affected_branches:
            related_contexts = await self._data_provider.get_related_context_ids(
                branch_id, project_id
            )
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

        # Get context details using data provider
        context_data = await self._data_provider.get_context_cascade_data(context_id)

        if not context_data:
            logger.warning(f"Context not found: {context_id}")
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

        # Add affected entities
        affected_tasks.update(context_data.task_ids)
        affected_branches.update(context_data.branch_ids)
        affected_projects.update(context_data.project_ids)
        affected_subtasks.update(context_data.subtask_ids)

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