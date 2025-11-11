"""
SQLAlchemy Cascade Data Provider Implementation

This infrastructure implementation provides data access for cascade calculations
using SQLAlchemy. It implements the CascadeDataProvider Protocol defined in the
domain layer, following the Dependency Inversion Principle.

This class can depend on SQLAlchemy because it lives in the infrastructure layer.
The domain layer depends only on the Protocol abstraction, not this concrete implementation.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.services.cascade_calculator import EntityType
from ....domain.services.protocols.cascade_data_provider import (
    BranchCascadeData,
    ContextCascadeData,
    ProjectCascadeData,
    SubtaskCascadeData,
    TaskCascadeData,
)

logger = logging.getLogger(__name__)


class SQLAlchemyCascadeDataProvider:
    """
    SQLAlchemy-based implementation of CascadeDataProvider Protocol.

    This class encapsulates all database queries needed for cascade calculations,
    keeping SQLAlchemy dependencies in the infrastructure layer where they belong.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize with SQLAlchemy session.

        Args:
            session: Async database session for executing queries
        """
        self.session = session

    async def get_task_cascade_data(self, task_id: str) -> TaskCascadeData | None:
        """Get cascade-relevant data for a task"""
        query = text("""
            SELECT t.id, t.git_branch_id, b.project_id, t.context_id
            FROM tasks t
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            WHERE t.id = :task_id
        """)

        result = await self.session.execute(query, {"task_id": task_id})
        row = result.fetchone()

        if not row:
            return None

        return TaskCascadeData(
            id=row[0],
            git_branch_id=row[1],
            project_id=row[2],
            context_id=row[3],
        )

    async def get_task_subtask_ids(self, task_id: str) -> set[str]:
        """Get all subtask IDs for a task"""
        query = text("""
            SELECT id FROM subtasks WHERE task_id = :task_id
        """)

        result = await self.session.execute(query, {"task_id": task_id})
        return {row[0] for row in result}

    async def get_task_parent_task_ids(self, task_id: str) -> set[str]:
        """Get IDs of tasks that depend on this task"""
        query = text("""
            SELECT DISTINCT td.task_id
            FROM task_dependencies td
            WHERE td.dependency_id = :task_id
        """)

        result = await self.session.execute(query, {"task_id": task_id})
        return {row[0] for row in result}

    async def get_subtask_cascade_data(
        self, subtask_id: str
    ) -> SubtaskCascadeData | None:
        """Get cascade-relevant data for a subtask"""
        query = text("""
            SELECT s.id, s.task_id, t.git_branch_id, b.project_id, t.context_id
            FROM subtasks s
            JOIN tasks t ON s.task_id = t.id
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            WHERE s.id = :subtask_id
        """)

        result = await self.session.execute(query, {"subtask_id": subtask_id})
        row = result.fetchone()

        if not row:
            return None

        return SubtaskCascadeData(
            id=row[0],
            task_id=row[1],
            git_branch_id=row[2],
            project_id=row[3],
            context_id=row[4],
        )

    async def get_branch_cascade_data(self, branch_id: str) -> BranchCascadeData | None:
        """Get cascade-relevant data for a branch"""
        query = text("""
            SELECT DISTINCT b.id, b.project_id, t.id as task_id, s.id as subtask_id
            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE b.id = :branch_id
        """)

        result = await self.session.execute(query, {"branch_id": branch_id})
        rows = result.fetchall()

        if not rows:
            return None

        # First row contains branch and project IDs
        branch_id = rows[0][0]
        project_id = rows[0][1]

        # Collect all task and subtask IDs
        task_ids = {row[2] for row in rows if row[2]}
        subtask_ids = {row[3] for row in rows if row[3]}

        return BranchCascadeData(
            id=branch_id,
            project_id=project_id,
            task_ids=task_ids,
            subtask_ids=subtask_ids,
        )

    async def get_project_cascade_data(
        self, project_id: str
    ) -> ProjectCascadeData | None:
        """Get cascade-relevant data for a project"""
        query = text("""
            SELECT DISTINCT b.id as branch_id, t.id as task_id, s.id as subtask_id
            FROM project_git_branchs b
            LEFT JOIN tasks t ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE b.project_id = :project_id
        """)

        result = await self.session.execute(query, {"project_id": project_id})
        rows = result.fetchall()

        if not rows:
            return None

        # Collect all IDs
        branch_ids = {row[0] for row in rows if row[0]}
        task_ids = {row[1] for row in rows if row[1]}
        subtask_ids = {row[2] for row in rows if row[2]}

        return ProjectCascadeData(
            id=project_id,
            branch_ids=branch_ids,
            task_ids=task_ids,
            subtask_ids=subtask_ids,
        )

    async def get_context_cascade_data(
        self, context_id: str
    ) -> ContextCascadeData | None:
        """Get cascade-relevant data for a context"""
        query = text("""
            SELECT DISTINCT t.id as task_id, t.git_branch_id, b.project_id, s.id as subtask_id
            FROM tasks t
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            LEFT JOIN subtasks s ON s.task_id = t.id
            WHERE t.context_id = :context_id
        """)

        result = await self.session.execute(query, {"context_id": context_id})
        rows = result.fetchall()

        if not rows:
            return None

        # Collect all IDs
        task_ids = {row[0] for row in rows if row[0]}
        branch_ids = {row[1] for row in rows if row[1]}
        project_ids = {row[2] for row in rows if row[2]}
        subtask_ids = {row[3] for row in rows if row[3]}

        return ContextCascadeData(
            id=context_id,
            task_ids=task_ids,
            branch_ids=branch_ids,
            project_ids=project_ids,
            subtask_ids=subtask_ids,
        )

    async def get_related_context_ids(
        self, branch_id: str, project_id: str
    ) -> set[str]:
        """Get context IDs related to a branch and project"""
        query = text("""
            SELECT DISTINCT context_id
            FROM tasks t
            WHERE t.git_branch_id = :branch_id AND context_id IS NOT NULL
        """)

        try:
            result = await self.session.execute(query, {"branch_id": branch_id})
            return {row[0] for row in result if row[0]}
        except Exception as e:
            logger.debug(f"Context query failed (expected for some schemas): {e}")
            return set()

    async def detect_entity_type(self, entity_id: str) -> EntityType | None:
        """Auto-detect entity type by checking which table contains the ID"""
        # Check tasks table
        task_query = text("SELECT COUNT(*) FROM tasks WHERE id = :entity_id")
        result = await self.session.execute(task_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.TASK

        # Check subtasks table
        subtask_query = text("SELECT COUNT(*) FROM subtasks WHERE id = :entity_id")
        result = await self.session.execute(subtask_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.SUBTASK

        # Check branches table
        branch_query = text(
            "SELECT COUNT(*) FROM project_git_branchs WHERE id = :entity_id"
        )
        result = await self.session.execute(branch_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.BRANCH

        # Check projects table
        project_query = text("SELECT COUNT(*) FROM projects WHERE id = :entity_id")
        result = await self.session.execute(project_query, {"entity_id": entity_id})
        if result.scalar() > 0:
            return EntityType.PROJECT

        # Default to context if not found in other tables
        return EntityType.CONTEXT
