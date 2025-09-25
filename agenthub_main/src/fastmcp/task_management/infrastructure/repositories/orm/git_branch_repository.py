"""
ORM Git Branch Repository Implementation

SQLAlchemy ORM-based implementation of the Git Branch Repository
for managing project branches/task trees.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_, func, case, text

from ....domain.repositories.git_branch_repository import GitBranchRepository
from ....domain.entities.git_branch import GitBranch
from ....domain.value_objects.task_status import TaskStatus
from ....domain.value_objects.priority import Priority
from ....domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)
from ..base_orm_repository import BaseORMRepository
from ..base_timestamp_repository import BaseTimestampRepository
from ...database.models import ProjectGitBranch, Project
from ...performance.task_performance_optimizer import get_performance_optimizer

logger = logging.getLogger(__name__)


class ORMGitBranchRepository(BaseTimestampRepository[ProjectGitBranch], GitBranchRepository):
    """
    ORM-based implementation of GitBranchRepository using SQLAlchemy.
    
    This class handles git branch (project task tree) operations using
    SQLAlchemy ORM models and the ProjectGitBranch model.
    """
    
    def __init__(self, user_id: Optional[str] = None, performance_mode: bool = False):
        """
        Initialize ORM Git Branch Repository.

        Args:
            user_id: User identifier for repository isolation
            performance_mode: Enable performance optimizations (caching, optimized queries)
        """
        super().__init__(ProjectGitBranch)
        self.user_id = user_id
        self.performance_mode = performance_mode

        # Initialize performance optimizer if performance mode is enabled
        if self.performance_mode:
            self.optimizer = get_performance_optimizer()
        else:
            self.optimizer = None

        logger.info(f"ORMGitBranchRepository initialized for user: {user_id}, performance_mode: {performance_mode}")
    
    def _model_to_git_branch(self, model: ProjectGitBranch) -> GitBranch:
        """
        Convert ProjectGitBranch model to GitBranch domain entity.
        
        Args:
            model: ProjectGitBranch model instance
            
        Returns:
            GitBranch domain entity
        """
        git_branch = GitBranch(
            id=model.id,
            name=model.name,
            description=model.description,
            project_id=model.project_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
        
        # Set additional fields
        git_branch.assigned_agent_id = model.assigned_agent_id
        git_branch.priority = Priority(model.priority)
        git_branch.status = TaskStatus(model.status)
        
        # Query actual tasks from the database to get accurate counts and statuses
        # This ensures accurate task counts even if the task_count field is outdated
        # IMPORTANT: For collaborative task visibility, we query ALL tasks
        # in a branch regardless of owner. Project-level security is still enforced.
        with self.get_db_session() as session:
            from ...database.models import Task
            tasks = session.query(Task).filter(
                Task.git_branch_id == model.id
            ).all()
            
            # Populate all_tasks with actual task data for accurate counting
            for task in tasks:
                git_branch.all_tasks[str(task.id)] = {
                    "id": str(task.id),
                    "status": task.status,
                    "priority": task.priority,
                    "title": task.title
                }
        
        return git_branch
    
    def _git_branch_to_model_data(self, git_branch: GitBranch) -> Dict[str, Any]:
        """
        Convert GitBranch domain entity to model data dictionary.
        
        Args:
            git_branch: GitBranch domain entity
            
        Returns:
            Dictionary with model data
        """
        # Handle user_id - require valid user_id
        user_id = self.user_id
        if not user_id:
            raise ValueError("user_id is required for git branch operations")
        
        return {
            'id': git_branch.id,
            'project_id': git_branch.project_id,
            'name': git_branch.name,
            'description': git_branch.description,
            'created_at': git_branch.created_at,
            'updated_at': git_branch.updated_at,
            'assigned_agent_id': git_branch.assigned_agent_id,
            'priority': str(git_branch.priority),
            'status': str(git_branch.status),
            'task_count': git_branch.get_task_count(),
            'completed_task_count': git_branch.get_completed_task_count(),
            'user_id': user_id,  # Add required user_id field
            'model_metadata': {}
        }
    
    # Repository interface implementation
    
    async def save(self, git_branch: GitBranch) -> None:
        """Save a git branch to the repository"""
        try:
            with self.get_db_session() as session:
                # Check if branch exists
                existing = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == git_branch.id,
                        ProjectGitBranch.project_id == git_branch.project_id
                    )
                ).first()
                
                model_data = self._git_branch_to_model_data(git_branch)
                
                if existing:
                    # Update existing branch
                    for key, value in model_data.items():
                        if key not in ['id', 'project_id', 'created_at']:  # Don't update immutable fields
                            setattr(existing, key, value)
                    existing.touch("git_branch_updated")
                else:
                    # Create new branch
                    new_branch = ProjectGitBranch(**model_data)
                    session.add(new_branch)
                
                session.flush()
        except SQLAlchemyError as e:
            logger.error(f"Error saving git branch {git_branch.id}: {e}")
            raise DatabaseException(
                message=f"Failed to save git branch: {str(e)}",
                operation="save",
                table="project_git_branchs"
            )
    
    async def find_by_id(self, branch_id: str, project_id: Optional[str] = None) -> Optional[GitBranch]:
        """Find a git branch by its ID, optionally filtered by project"""
        try:
            with self.get_db_session() as session:
                query = session.query(ProjectGitBranch)
                
                # SECURITY FIX: Always apply user filtering for data isolation
                if not self.user_id:
                    raise ValueError("User authentication required for branch operations")
                
                if project_id:
                    # If project_id is provided, filter by branch, project, and user
                    query = query.filter(
                        and_(
                            ProjectGitBranch.id == branch_id,
                            ProjectGitBranch.project_id == project_id,
                            ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                        )
                    )
                else:
                    # Filter by branch ID and user ID for security
                    query = query.filter(
                        and_(
                            ProjectGitBranch.id == branch_id,
                            ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                        )
                    )
                
                model = query.first()
                
                if not model:
                    return None
                
                return self._model_to_git_branch(model)
        except SQLAlchemyError as e:
            logger.error(f"Error finding git branch by ID {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find git branch: {str(e)}",
                operation="find_by_id",
                table="project_git_branchs"
            )
    
    async def find_by_name(self, project_id: str, branch_name: str) -> Optional[GitBranch]:
        """Find a git branch by its project and branch name"""
        try:
            with self.get_db_session() as session:
                model = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.name == branch_name,
                        ProjectGitBranch.project_id == project_id
                    )
                ).first()
                
                if not model:
                    return None
                
                return self._model_to_git_branch(model)
        except SQLAlchemyError as e:
            logger.error(f"Error finding git branch by name {branch_name}: {e}")
            raise DatabaseException(
                message=f"Failed to find git branch: {str(e)}",
                operation="find_by_name",
                table="project_git_branchs"
            )
    
    async def find_all_by_project(self, project_id: str) -> List[GitBranch]:
        """Find all git branches for a project"""
        try:
            with self.get_db_session() as session:
                # SECURITY FIX: Always apply user filtering for data isolation
                if not self.user_id:
                    raise ValueError("User authentication required for branch operations")
                
                models = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.project_id == project_id,
                        ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                    )
                ).order_by(ProjectGitBranch.created_at.desc()).all()
                
                branches = []
                for model in models:
                    try:
                        branch = self._model_to_git_branch(model)
                        branches.append(branch)
                    except Exception as e:
                        logger.error(f"Error converting model {model.id}: {e}")
                        continue
                
                return branches
        except SQLAlchemyError as e:
            logger.error(f"Error finding branches for project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find branches: {str(e)}",
                operation="find_all_by_project",
                table="project_git_branchs"
            )
    
    async def find_all(self) -> List[GitBranch]:
        """Find all git branches"""
        try:
            with self.get_db_session() as session:
                models = session.query(ProjectGitBranch).order_by(
                    ProjectGitBranch.created_at.desc()
                ).all()
                
                branches = []
                for model in models:
                    try:
                        branch = self._model_to_git_branch(model)
                        branches.append(branch)
                    except Exception as e:
                        logger.error(f"Error converting model {model.id}: {e}")
                        continue
                
                return branches
        except SQLAlchemyError as e:
            logger.error(f"Error finding all branches: {e}")
            raise DatabaseException(
                message=f"Failed to find branches: {str(e)}",
                operation="find_all",
                table="project_git_branchs"
            )
    
    async def delete(self, project_id: str, branch_id: str) -> bool:
        """Delete a git branch by its project and branch ID"""
        try:
            with self.get_db_session() as session:
                # SECURITY FIX: Always apply user filtering for data isolation
                if not self.user_id:
                    raise ValueError("User authentication required for branch operations")
                
                deleted_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id,
                        ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                    )
                ).delete()
                
                return deleted_count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error deleting git branch {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete git branch: {str(e)}",
                operation="delete",
                table="project_git_branchs"
            )
    
    async def delete_branch(self, branch_id: str) -> bool:
        """Delete a git branch by its ID (including comprehensive cascade delete of all dependent records)"""
        try:
            with self.get_db_session() as session:
                # SECURITY: Apply user isolation if user_id is available
                if self.user_id:
                    # Verify user owns this branch before allowing deletion
                    branch_check = session.query(ProjectGitBranch).filter(
                        and_(
                            ProjectGitBranch.id == branch_id,
                            ProjectGitBranch.user_id == self.user_id
                        )
                    ).first()
                    if not branch_check:
                        logger.warning(f"User {self.user_id} attempted to delete branch {branch_id} they don't own")
                        return False
                
                logger.info(f"Starting comprehensive cascade deletion for branch {branch_id}")
                
                # COMPREHENSIVE CASCADE DELETION SEQUENCE:
                
                # Step 1: Delete ContextInheritanceCache records for this branch
                from ...database.models import ContextInheritanceCache
                cache_filter = and_(
                    ContextInheritanceCache.context_id == branch_id,
                    ContextInheritanceCache.context_level == 'branch'
                )
                if self.user_id:
                    cache_filter = and_(cache_filter, ContextInheritanceCache.user_id == self.user_id)
                
                cache_count = session.query(ContextInheritanceCache).filter(cache_filter).delete()
                logger.info(f"Deleted {cache_count} ContextInheritanceCache records for branch {branch_id}")
                
                # Step 2: Delete ContextDelegation records where this branch is source or target
                from ...database.models import ContextDelegation
                delegation_filter = and_(
                    or_(
                        and_(ContextDelegation.source_id == branch_id, ContextDelegation.source_level == 'branch'),
                        and_(ContextDelegation.target_id == branch_id, ContextDelegation.target_level == 'branch')
                    )
                )
                if self.user_id:
                    delegation_filter = and_(delegation_filter, ContextDelegation.user_id == self.user_id)
                
                delegation_count = session.query(ContextDelegation).filter(delegation_filter).delete()
                logger.info(f"Deleted {delegation_count} ContextDelegation records for branch {branch_id}")
                
                # Step 3: Get BranchContext IDs for this branch (needed for TaskContext cleanup)
                from ...database.models import BranchContext
                branch_context_query = session.query(BranchContext.id).filter(
                    BranchContext.branch_id == branch_id
                )
                if self.user_id:
                    branch_context_query = branch_context_query.filter(BranchContext.user_id == self.user_id)
                
                branch_context_ids = [row[0] for row in branch_context_query.all()]
                logger.info(f"Found {len(branch_context_ids)} BranchContext records for branch {branch_id}")
                
                # Step 4: Get Task IDs for this branch (needed for task-related cascades)
                from ...database.models import Task
                task_query = session.query(Task.id).filter(Task.git_branch_id == branch_id)
                if self.user_id:
                    task_query = task_query.filter(Task.user_id == self.user_id)
                
                task_ids = [row[0] for row in task_query.all()]
                logger.info(f"Found {len(task_ids)} Task records for branch {branch_id}")
                
                # Step 5: Delete Subtask records for tasks in this branch
                if task_ids:
                    from ...database.models import Subtask
                    subtask_filter = Subtask.task_id.in_(task_ids)
                    if self.user_id:
                        subtask_filter = and_(subtask_filter, Subtask.user_id == self.user_id)
                    
                    subtask_count = session.query(Subtask).filter(subtask_filter).delete(synchronize_session=False)
                    logger.info(f"Deleted {subtask_count} Subtask records for branch {branch_id}")
                
                # Step 6: Delete TaskAssignee records for tasks in this branch
                if task_ids:
                    from ...database.models import TaskAssignee
                    assignee_filter = TaskAssignee.task_id.in_(task_ids)
                    if self.user_id:
                        assignee_filter = and_(assignee_filter, TaskAssignee.user_id == self.user_id)
                    
                    assignee_count = session.query(TaskAssignee).filter(assignee_filter).delete(synchronize_session=False)
                    logger.info(f"Deleted {assignee_count} TaskAssignee records for branch {branch_id}")
                
                # Step 7: Delete TaskLabel records for tasks in this branch
                if task_ids:
                    from ...database.models import TaskLabel
                    label_filter = TaskLabel.task_id.in_(task_ids)
                    if self.user_id:
                        label_filter = and_(label_filter, TaskLabel.user_id == self.user_id)
                    
                    label_count = session.query(TaskLabel).filter(label_filter).delete(synchronize_session=False)
                    logger.info(f"Deleted {label_count} TaskLabel records for branch {branch_id}")
                
                # Step 8: Delete TaskDependency records (both directions) for tasks in this branch
                if task_ids:
                    from ...database.models import TaskDependency
                    dependency_filter = or_(
                        TaskDependency.task_id.in_(task_ids),
                        TaskDependency.depends_on_task_id.in_(task_ids)
                    )
                    if self.user_id:
                        dependency_filter = and_(dependency_filter, TaskDependency.user_id == self.user_id)
                    
                    dependency_count = session.query(TaskDependency).filter(dependency_filter).delete(synchronize_session=False)
                    logger.info(f"Deleted {dependency_count} TaskDependency records for branch {branch_id}")
                
                # Step 9: Delete TaskContext records referencing this branch directly
                from ...database.models import TaskContext
                task_context_filter = TaskContext.parent_branch_id == branch_id
                if self.user_id:
                    task_context_filter = and_(task_context_filter, TaskContext.user_id == self.user_id)
                
                direct_task_context_count = session.query(TaskContext).filter(task_context_filter).delete()
                logger.info(f"Deleted {direct_task_context_count} direct TaskContext records for branch {branch_id}")
                
                # Step 10: Delete TaskContext records referencing BranchContext records from this branch
                if branch_context_ids:
                    indirect_task_context_filter = TaskContext.parent_branch_context_id.in_(branch_context_ids)
                    if self.user_id:
                        indirect_task_context_filter = and_(indirect_task_context_filter, TaskContext.user_id == self.user_id)
                    
                    indirect_task_context_count = session.query(TaskContext).filter(indirect_task_context_filter).delete(synchronize_session=False)
                    logger.info(f"Deleted {indirect_task_context_count} indirect TaskContext records for branch {branch_id}")
                
                # Step 11: Delete Task records for this branch
                task_filter = Task.git_branch_id == branch_id
                if self.user_id:
                    task_filter = and_(task_filter, Task.user_id == self.user_id)
                
                task_count = session.query(Task).filter(task_filter).delete()
                logger.info(f"Deleted {task_count} Task records for branch {branch_id}")
                
                # Step 12: Delete BranchContext records for this branch
                branch_context_filter = BranchContext.branch_id == branch_id
                if self.user_id:
                    branch_context_filter = and_(branch_context_filter, BranchContext.user_id == self.user_id)
                
                branch_context_count = session.query(BranchContext).filter(branch_context_filter).delete()
                logger.info(f"Deleted {branch_context_count} BranchContext records for branch {branch_id}")
                
                # Step 13: Finally delete the branch itself
                branch_filter = ProjectGitBranch.id == branch_id
                if self.user_id:
                    branch_filter = and_(branch_filter, ProjectGitBranch.user_id == self.user_id)
                
                deleted_count = session.query(ProjectGitBranch).filter(branch_filter).delete()
                logger.info(f"Deleted branch {branch_id}: {deleted_count > 0}")
                
                session.commit()
                logger.info(f"Comprehensive cascade deletion completed for branch {branch_id}")
                return deleted_count > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Error in comprehensive cascade deletion for branch {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete git branch: {str(e)}",
                operation="delete_branch",
                table="project_git_branchs"
            )
    
    async def exists(self, project_id: str, branch_id: str) -> bool:
        """Check if a git branch exists"""
        try:
            with self.get_db_session() as session:
                result = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).first()
                return result is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking branch existence {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to check branch existence: {str(e)}",
                operation="exists",
                table="project_git_branchs"
            )
    
    async def update(self, git_branch: GitBranch) -> None:
        """Update an existing git branch"""
        git_branch.touch("git_branch_manual_update")
        await self.save(git_branch)
    
    async def count_by_project(self, project_id: str) -> int:
        """Count total number of git branches for a project"""
        try:
            with self.get_db_session() as session:
                return session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.project_id == project_id
                ).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting branches for project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to count branches: {str(e)}",
                operation="count_by_project",
                table="project_git_branchs"
            )
    
    async def count_all(self) -> int:
        """Count total number of git branches"""
        try:
            with self.get_db_session() as session:
                return session.query(ProjectGitBranch).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting all branches: {e}")
            raise DatabaseException(
                message=f"Failed to count branches: {str(e)}",
                operation="count_all",
                table="project_git_branchs"
            )
    
    async def find_by_assigned_agent(self, agent_id: str) -> List[GitBranch]:
        """Find git branches assigned to a specific agent"""
        try:
            with self.get_db_session() as session:
                models = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.assigned_agent_id == agent_id
                ).order_by(ProjectGitBranch.created_at.desc()).all()
                
                branches = []
                for model in models:
                    try:
                        branch = self._model_to_git_branch(model)
                        branches.append(branch)
                    except Exception as e:
                        logger.error(f"Error converting model {model.id}: {e}")
                        continue
                
                return branches
        except SQLAlchemyError as e:
            logger.error(f"Error finding branches for agent {agent_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find branches: {str(e)}",
                operation="find_by_assigned_agent",
                table="project_git_branchs"
            )
    
    async def find_by_status(self, project_id: str, status: str) -> List[GitBranch]:
        """Find git branches by status within a project"""
        try:
            with self.get_db_session() as session:
                models = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.project_id == project_id,
                        ProjectGitBranch.status == status
                    )
                ).order_by(ProjectGitBranch.created_at.desc()).all()
                
                branches = []
                for model in models:
                    try:
                        branch = self._model_to_git_branch(model)
                        branches.append(branch)
                    except Exception as e:
                        logger.error(f"Error converting model {model.id}: {e}")
                        continue
                
                return branches
        except SQLAlchemyError as e:
            logger.error(f"Error finding branches by status {status}: {e}")
            raise DatabaseException(
                message=f"Failed to find branches: {str(e)}",
                operation="find_by_status",
                table="project_git_branchs"
            )
    
    async def find_available_for_assignment(self, project_id: str) -> List[GitBranch]:
        """Find git branches that can be assigned to agents"""
        try:
            with self.get_db_session() as session:
                models = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.project_id == project_id,
                        ProjectGitBranch.assigned_agent_id.is_(None),
                        ProjectGitBranch.status.in_(['todo', 'in_progress', 'review'])
                    )
                ).order_by(
                    ProjectGitBranch.priority.desc(),
                    ProjectGitBranch.created_at.asc()
                ).all()
                
                branches = []
                for model in models:
                    try:
                        branch = self._model_to_git_branch(model)
                        branches.append(branch)
                    except Exception as e:
                        logger.error(f"Error converting model {model.id}: {e}")
                        continue
                
                return branches
        except SQLAlchemyError as e:
            logger.error(f"Error finding available branches for project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find available branches: {str(e)}",
                operation="find_available_for_assignment",
                table="project_git_branchs"
            )
    
    async def assign_agent(self, project_id: str, branch_id: str, agent_id: str) -> bool:
        """Assign an agent to a git branch"""
        try:
            with self.get_db_session() as session:
                updated_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).update({
                    'assigned_agent_id': agent_id
                    # BaseTimestampRepository handles updated_at automatically
                })
                
                return updated_count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error assigning agent {agent_id} to branch {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to assign agent: {str(e)}",
                operation="assign_agent",
                table="project_git_branchs"
            )
    
    async def unassign_agent(self, project_id: str, branch_id: str) -> bool:
        """Unassign the current agent from a git branch"""
        try:
            with self.get_db_session() as session:
                updated_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).update({
                    'assigned_agent_id': None
                    # BaseTimestampRepository handles updated_at automatically
                })
                
                return updated_count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error unassigning agent from branch {branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to unassign agent: {str(e)}",
                operation="unassign_agent",
                table="project_git_branchs"
            )
    
    async def get_project_branch_summary(self, project_id: str) -> Dict[str, Any]:
        """Get summary of all branches in a project"""
        try:
            with self.get_db_session() as session:
                # Get basic stats using aggregate functions
                stats = session.query(
                    func.count(ProjectGitBranch.id).label('total_branches'),
                    func.sum(case((ProjectGitBranch.status == 'done', 1), else_=0)).label('completed_branches'),
                    func.sum(case((ProjectGitBranch.status == 'in_progress', 1), else_=0)).label('active_branches'),
                    func.sum(case((ProjectGitBranch.assigned_agent_id.isnot(None), 1), else_=0)).label('assigned_branches'),
                    func.sum(ProjectGitBranch.task_count).label('total_tasks'),
                    func.sum(ProjectGitBranch.completed_task_count).label('total_completed_tasks')
                ).filter(ProjectGitBranch.project_id == project_id).first()
                
                # Get status breakdown
                status_rows = session.query(
                    ProjectGitBranch.status,
                    func.count(ProjectGitBranch.id).label('count')
                ).filter(ProjectGitBranch.project_id == project_id).group_by(
                    ProjectGitBranch.status
                ).all()
                
                status_breakdown = {row.status: row.count for row in status_rows}
                
                # Calculate overall progress
                overall_progress = 0.0
                if stats.total_tasks and stats.total_tasks > 0:
                    overall_progress = (stats.total_completed_tasks / stats.total_tasks) * 100.0
                
                return {
                    "project_id": project_id,
                    "summary": {
                        "total_branches": stats.total_branches or 0,
                        "completed_branches": stats.completed_branches or 0,
                        "active_branches": stats.active_branches or 0,
                        "assigned_branches": stats.assigned_branches or 0
                    },
                    "tasks": {
                        "total_tasks": stats.total_tasks or 0,
                        "completed_tasks": stats.total_completed_tasks or 0,
                        "overall_progress_percentage": overall_progress
                    },
                    "status_breakdown": status_breakdown,
                    "user_id": self.user_id,
                    "generated_at": "auto-generated"  # BaseTimestampRepository handles timestamps
                }
        except SQLAlchemyError as e:
            logger.error(f"Error getting project branch summary for {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to get project branch summary: {str(e)}",
                operation="get_project_branch_summary",
                table="project_git_branchs"
            )
    
    async def create_branch(self, project_id: str, branch_name: str, description: str = "") -> GitBranch:
        """Create a new git branch for a project"""
        try:
            # Generate unique branch ID
            branch_id = str(uuid.uuid4())
            
            # BaseTimestampRepository handles timestamps automatically
            
            # Create GitBranch entity
            git_branch = GitBranch(
                id=branch_id,
                name=branch_name,
                description=description,
                project_id=project_id,
                created_at=now,
                updated_at=now
            )
            
            # Save to repository
            await self.save(git_branch)
            
            return git_branch
        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {e}")
            raise DatabaseException(
                message=f"Failed to create branch: {str(e)}",
                operation="create_branch",
                table="project_git_branchs"
            )
    
    # Implementation of abstract methods from GitBranchRepository interface
    
    async def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch - implements abstract method"""
        try:
            git_branch = await self.create_branch(project_id, git_branch_name, git_branch_description)
            return {
                "success": True,
                "git_branch": {
                    "id": git_branch.id,
                    "name": git_branch.name,
                    "description": git_branch.description,
                    "project_id": git_branch.project_id,
                    "created_at": git_branch.created_at.isoformat(),
                    "updated_at": git_branch.updated_at.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error in create_git_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "CREATE_FAILED"
            }
    
    async def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get git branch by ID - implements abstract method"""
        try:
            # SECURITY FIX: Always apply user filtering for data isolation
            if not self.user_id:
                raise ValueError("User authentication required for branch operations")
            
            # First find the branch to get project_id
            with self.get_db_session() as session:
                model = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == git_branch_id,
                        ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                    )
                ).first()
                
                if not model:
                    return {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_id}",
                        "error_code": "NOT_FOUND"
                    }
                
                git_branch = self._model_to_git_branch(model)
                
                return {
                    "success": True,
                    "git_branch": {
                        "id": git_branch.id,
                        "name": git_branch.name,
                        "description": git_branch.description,
                        "project_id": git_branch.project_id,
                        "created_at": git_branch.created_at.isoformat(),
                        "updated_at": git_branch.updated_at.isoformat(),
                        "assigned_agent_id": git_branch.assigned_agent_id,
                        "status": str(git_branch.status),
                        "priority": str(git_branch.priority),
                        "task_count": git_branch.get_task_count(),
                        "completed_task_count": git_branch.get_completed_task_count(),
                        "active_task_count": git_branch.get_active_task_count()
                    }
                }
        except Exception as e:
            logger.error(f"Error in get_git_branch_by_id: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "GET_FAILED"
            }
    
    async def get_git_branch_by_name(self, project_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Get git branch by name within a project - implements abstract method"""
        try:
            git_branch = await self.find_by_name(project_id, git_branch_name)
            if not git_branch:
                return {
                    "success": False,
                    "error": f"Git branch not found: {git_branch_name}",
                    "error_code": "NOT_FOUND"
                }
            
            return {
                "success": True,
                "git_branch": {
                    "id": git_branch.id,
                    "name": git_branch.name,
                    "description": git_branch.description,
                    "project_id": git_branch.project_id,
                    "created_at": git_branch.created_at.isoformat(),
                    "updated_at": git_branch.updated_at.isoformat(),
                    "assigned_agent_id": git_branch.assigned_agent_id,
                    "status": str(git_branch.status),
                    "priority": str(git_branch.priority)
                }
            }
        except Exception as e:
            logger.error(f"Error in get_git_branch_by_name: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "GET_FAILED"
            }
    
    async def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List all git branches for a project - implements abstract method"""
        try:
            git_branchs = await self.find_all_by_project(project_id)
            
            branches = []
            for git_branch in git_branchs:
                branches.append({
                    "id": git_branch.id,
                    "name": git_branch.name,
                    "description": git_branch.description,
                    "project_id": git_branch.project_id,
                    "created_at": git_branch.created_at.isoformat(),
                    "updated_at": git_branch.updated_at.isoformat(),
                    "assigned_agent_id": git_branch.assigned_agent_id,
                    "status": str(git_branch.status),
                    "priority": str(git_branch.priority)
                })
            
            return {
                "success": True,
                "git_branchs": branches,
                "count": len(branches)
            }
        except Exception as e:
            logger.error(f"Error in list_git_branchs: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "LIST_FAILED"
            }
    
    async def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update git branch information - implements abstract method"""
        try:
            # Get the branch first
            with self.get_db_session() as session:
                model = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.id == git_branch_id
                ).first()
                
                if not model:
                    return {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_id}",
                        "error_code": "NOT_FOUND"
                    }
                
                # Update fields
                if git_branch_name is not None:
                    model.name = git_branch_name
                if git_branch_description is not None:
                    model.description = git_branch_description
                
                model.touch("git_branch_description_updated")
                session.flush()
                
                git_branch = self._model_to_git_branch(model)
                
                return {
                    "success": True,
                    "message": "Git branch updated successfully",
                    "git_branch": {
                        "id": git_branch.id,
                        "name": git_branch.name,
                        "description": git_branch.description,
                        "project_id": git_branch.project_id,
                        "updated_at": git_branch.updated_at.isoformat()
                    }
                }
        except Exception as e:
            logger.error(f"Error in update_git_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "UPDATE_FAILED"
            }
    
    async def delete_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch - implements abstract method"""
        try:
            deleted = await self.delete(project_id, git_branch_id)
            
            if deleted:
                return {
                    "success": True,
                    "message": f"Git branch {git_branch_id} deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Git branch not found: {git_branch_id}",
                    "error_code": "NOT_FOUND"
                }
        except Exception as e:
            logger.error(f"Error in delete_git_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "DELETE_FAILED"
            }
    
    async def assign_agent_to_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a git branch - implements abstract method"""
        try:
            # Find branch by name first
            git_branch = await self.find_by_name(project_id, git_branch_name)
            if not git_branch:
                return {
                    "success": False,
                    "error": f"Git branch not found: {git_branch_name}",
                    "error_code": "NOT_FOUND"
                }
            
            # Assign agent
            assigned = await self.assign_agent(project_id, git_branch.id, agent_id)
            
            if assigned:
                return {
                    "success": True,
                    "message": f"Agent {agent_id} assigned to branch {git_branch_name}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to assign agent",
                    "error_code": "ASSIGN_FAILED"
                }
        except Exception as e:
            logger.error(f"Error in assign_agent_to_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "ASSIGN_FAILED"
            }
    
    async def unassign_agent_from_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch - implements abstract method"""
        try:
            # Find branch by name first
            git_branch = await self.find_by_name(project_id, git_branch_name)
            if not git_branch:
                return {
                    "success": False,
                    "error": f"Git branch not found: {git_branch_name}",
                    "error_code": "NOT_FOUND"
                }
            
            # Unassign agent
            unassigned = await self.unassign_agent(project_id, git_branch.id)
            
            if unassigned:
                return {
                    "success": True,
                    "message": f"Agent {agent_id} unassigned from branch {git_branch_name}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to unassign agent",
                    "error_code": "UNASSIGN_FAILED"
                }
        except Exception as e:
            logger.error(f"Error in unassign_agent_from_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNASSIGN_FAILED"
            }
    
    async def get_branch_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a git branch - implements abstract method"""
        try:
            with self.get_db_session() as session:
                model = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == git_branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).first()
                
                if not model:
                    return {"error": "Branch not found"}
                
                progress = 0.0
                if model.task_count and model.task_count > 0:
                    progress = (model.completed_task_count or 0) / model.task_count * 100.0
                
                return {
                    "branch_id": model.id,
                    "branch_name": model.name,
                    "project_id": model.project_id,
                    "status": model.status,
                    "priority": model.priority,
                    "assigned_agent_id": model.assigned_agent_id,
                    "task_count": model.task_count or 0,
                    "completed_task_count": model.completed_task_count or 0,
                    "progress_percentage": progress,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                    "updated_at": model.updated_at.isoformat() if model.updated_at else None
                }
        except Exception as e:
            logger.error(f"Error in get_branch_statistics: {e}")
            return {"error": str(e)}
    
    async def archive_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch - implements abstract method"""
        try:
            with self.get_db_session() as session:
                updated_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == git_branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).update({
                    'status': 'cancelled'
                    # BaseTimestampRepository handles updated_at automatically
                })
                
                if updated_count > 0:
                    return {
                        "success": True,
                        "message": f"Git branch {git_branch_id} archived successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_id}",
                        "error_code": "NOT_FOUND"
                    }
        except Exception as e:
            logger.error(f"Error in archive_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "ARCHIVE_FAILED"
            }
    
    async def restore_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch - implements abstract method"""
        try:
            with self.get_db_session() as session:
                updated_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == git_branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).update({
                    'status': 'todo'
                    # BaseTimestampRepository handles updated_at automatically
                })
                
                if updated_count > 0:
                    return {
                        "success": True,
                        "message": f"Git branch {git_branch_id} restored successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Git branch not found: {git_branch_id}",
                        "error_code": "NOT_FOUND"
                    }
        except Exception as e:
            logger.error(f"Error in restore_branch: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "RESTORE_FAILED"
            }

    # ========================================================================================
    # PERFORMANCE-OPTIMIZED METHODS (Merged from optimized_branch_repository.py)
    # ========================================================================================

    def get_branches_with_task_counts(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all branches for a project with their task counts in a single query.

        This method uses subqueries to calculate counts, avoiding the N+1 query problem
        that occurs when loading branches and then counting tasks for each.

        Performance improvement: ~95% reduction in query time compared to eager loading.

        Args:
            project_id: The project ID to fetch branches for

        Returns:
            List of dictionaries containing branch data with task counts
        """
        if not project_id:
            logger.warning("No project_id provided for branch query")
            return []

        # Validate project_id format
        try:
            import uuid
            uuid.UUID(project_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid project UUID: {project_id}")
            return []

        with self.get_db_session() as session:
            # Single optimized query with subqueries for counts
            sql = text("""
                SELECT
                    gb.id as branch_id,
                    gb.name as branch_name,
                    gb.description,
                    gb.status as branch_status,
                    gb.priority,
                    gb.created_at,
                    gb.updated_at,
                    gb.assigned_agent_id,
                    gb.user_id,
                    -- Total task count
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id) as total_tasks,
                    -- Task counts by status
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND status = 'todo') as todo_count,
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND status = 'in_progress') as in_progress_count,
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND status = 'done') as done_count,
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND status = 'blocked') as blocked_count,
                    -- Task counts by priority
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND priority = 'urgent') as urgent_tasks,
                    (SELECT COUNT(*)
                     FROM tasks
                     WHERE git_branch_id = gb.id
                     AND priority = 'high') as high_priority_tasks,
                    -- Completion percentage
                    CASE
                        WHEN (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id) > 0
                        THEN CAST(
                            (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id AND status = 'done') * 100.0 /
                            (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id)
                            AS INTEGER
                        )
                        ELSE 0
                    END as completion_percentage
                FROM project_git_branchs gb
                WHERE gb.project_id = :project_id
                """ + (f" AND gb.user_id = :user_id" if self.user_id else "") + """
                ORDER BY gb.updated_at DESC, gb.created_at DESC
            """)

            try:
                params = {"project_id": project_id}
                if self.user_id:
                    params["user_id"] = self.user_id

                result = session.execute(sql, params)
                branches = []

                for row in result:
                    branch_data = {
                        "id": str(row.branch_id) if row.branch_id else None,
                        "name": row.branch_name,
                        "description": row.description,
                        "status": row.branch_status,
                        "priority": row.priority,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                        "assigned_agent_id": str(row.assigned_agent_id) if row.assigned_agent_id else None,
                        "user_id": str(row.user_id) if row.user_id else None,
                        "task_counts": {
                            "total": row.total_tasks,
                            "by_status": {
                                "todo": row.todo_count,
                                "in_progress": row.in_progress_count,
                                "done": row.done_count,
                                "blocked": row.blocked_count
                            },
                            "by_priority": {
                                "urgent": row.urgent_tasks,
                                "high": row.high_priority_tasks
                            },
                            "completion_percentage": row.completion_percentage
                        },
                        # Quick status indicators
                        "has_tasks": row.total_tasks > 0,
                        "has_urgent_tasks": row.urgent_tasks > 0,
                        "is_active": row.in_progress_count > 0,
                        "is_completed": row.total_tasks > 0 and row.done_count == row.total_tasks
                    }
                    branches.append(branch_data)

                logger.info(f"Retrieved {len(branches)} branches with task counts for project {project_id}")
                return branches

            except Exception as e:
                logger.error(f"Error fetching branches with task counts: {e}")
                return []

    def get_branch_summary_stats(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get summary statistics for all branches in a project.

        Returns aggregated statistics across all branches in a single query.
        """
        if not project_id:
            return {"error": "No project_id provided"}

        with self.get_db_session() as session:
            sql = text("""
                SELECT
                    COUNT(DISTINCT gb.id) as total_branches,
                    COUNT(DISTINCT CASE WHEN t.id IS NOT NULL THEN gb.id END) as active_branches,
                    COUNT(DISTINCT t.id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.status = 'todo' THEN t.id END) as todo_tasks,
                    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) as in_progress_tasks,
                    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as done_tasks,
                    COUNT(DISTINCT CASE WHEN t.priority = 'urgent' THEN t.id END) as urgent_tasks
                FROM project_git_branchs gb
                LEFT JOIN tasks t ON t.git_branch_id = gb.id
                WHERE gb.project_id = :project_id
                """ + (f" AND gb.user_id = :user_id" if self.user_id else ""))

            try:
                params = {"project_id": project_id}
                if self.user_id:
                    params["user_id"] = self.user_id

                result = session.execute(sql, params).first()

                return {
                    "branches": {
                        "total": result.total_branches,
                        "active": result.active_branches,
                        "inactive": result.total_branches - result.active_branches
                    },
                    "tasks": {
                        "total": result.total_tasks,
                        "todo": result.todo_tasks,
                        "in_progress": result.in_progress_tasks,
                        "done": result.done_tasks,
                        "urgent": result.urgent_tasks
                    },
                    "completion_percentage": (
                        round((result.done_tasks / result.total_tasks) * 100, 1)
                        if result.total_tasks > 0 else 0
                    )
                }
            except Exception as e:
                logger.error(f"Error fetching branch summary stats: {e}")
                return {"error": str(e)}

    def get_single_branch_with_counts(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single branch with its task counts.

        Optimized version for fetching a single branch's data.
        """
        if not branch_id:
            return None

        with self.get_db_session() as session:
            sql = text("""
                SELECT
                    gb.id as branch_id,
                    gb.name as branch_name,
                    gb.description,
                    gb.status as branch_status,
                    gb.project_id,
                    gb.user_id,
                    (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id) as total_tasks,
                    (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id AND status = 'todo') as todo_count,
                    (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id AND status = 'in_progress') as in_progress_count,
                    (SELECT COUNT(*) FROM tasks WHERE git_branch_id = gb.id AND status = 'done') as done_count
                FROM project_git_branchs gb
                WHERE gb.id = :branch_id
                """ + (f" AND gb.user_id = :user_id" if self.user_id else ""))

            try:
                params = {"branch_id": branch_id}
                if self.user_id:
                    params["user_id"] = self.user_id

                result = session.execute(sql, params).first()

                if not result:
                    return None

                return {
                    "id": str(result.branch_id) if result.branch_id else None,
                    "name": result.branch_name,
                    "description": result.description,
                    "status": result.branch_status,
                    "project_id": str(result.project_id) if result.project_id else None,
                    "user_id": str(result.user_id) if result.user_id else None,
                    "task_counts": {
                        "total": result.total_tasks,
                        "todo": result.todo_count,
                        "in_progress": result.in_progress_count,
                        "done": result.done_count
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching single branch with counts: {e}")
                return None

    async def check_name_exists_in_project(self, project_id: str, name: str, exclude_branch_id: Optional[str] = None) -> bool:
        """
        Check if a git branch name already exists within a project.

        Args:
            project_id: The project ID to scope the check to
            name: The branch name to check
            exclude_branch_id: Optional branch ID to exclude from the check (for updates)

        Returns:
            True if the name exists, False otherwise
        """
        try:
            with self.get_db_session() as session:
                # SECURITY: Always apply user filtering for data isolation
                if not self.user_id:
                    raise ValueError("User authentication required for branch operations")

                query = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.project_id == project_id,
                        ProjectGitBranch.name == name.strip(),
                        ProjectGitBranch.user_id == self.user_id  # USER ISOLATION
                    )
                )

                # Exclude specific branch if provided (for updates)
                if exclude_branch_id:
                    query = query.filter(ProjectGitBranch.id != exclude_branch_id)

                existing = query.first()
                return existing is not None

        except SQLAlchemyError as e:
            logger.error(f"Error checking branch name exists: {e}")
            raise DatabaseException(
                message=f"Failed to check branch name: {str(e)}",
                operation="check_name_exists_in_project",
                table="project_git_branchs"
            )