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
from sqlalchemy import and_, func, case

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
from ...database.models import ProjectGitBranch, Project

logger = logging.getLogger(__name__)


class ORMGitBranchRepository(BaseORMRepository[ProjectGitBranch], GitBranchRepository):
    """
    ORM-based implementation of GitBranchRepository using SQLAlchemy.
    
    This class handles git branch (project task tree) operations using
    SQLAlchemy ORM models and the ProjectGitBranch model.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize ORM Git Branch Repository.
        
        Args:
            user_id: User identifier for repository isolation
        """
        super().__init__(ProjectGitBranch)
        self.user_id = user_id
        logger.info(f"ORMGitBranchRepository initialized for user: {user_id}")
    
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
        
        # Note: Task counts are calculated dynamically by the entity's get_task_count() 
        # and get_completed_task_count() methods, so we don't set private attributes here
        
        return git_branch
    
    def _git_branch_to_model_data(self, git_branch: GitBranch) -> Dict[str, Any]:
        """
        Convert GitBranch domain entity to model data dictionary.
        
        Args:
            git_branch: GitBranch domain entity
            
        Returns:
            Dictionary with model data
        """
        # Handle user_id - use instance user_id or default to 'system'
        user_id = self.user_id or 'system'
        
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
                    existing.updated_at = datetime.now(timezone.utc)
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
    
    async def find_by_id(self, project_id: str, branch_id: str) -> Optional[GitBranch]:
        """Find a git branch by its project and branch ID"""
        try:
            with self.get_db_session() as session:
                model = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id
                    )
                ).first()
                
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
                models = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.project_id == project_id
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
                deleted_count = session.query(ProjectGitBranch).filter(
                    and_(
                        ProjectGitBranch.id == branch_id,
                        ProjectGitBranch.project_id == project_id
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
        """Delete a git branch by its ID (including cascade delete of tasks)"""
        try:
            with self.get_db_session() as session:
                # First delete all tasks associated with this branch
                from ...database.models import Task
                session.query(Task).filter(
                    Task.git_branch_id == branch_id
                ).delete()
                
                # Then delete the branch itself
                deleted_count = session.query(ProjectGitBranch).filter(
                    ProjectGitBranch.id == branch_id
                ).delete()
                
                session.commit()
                return deleted_count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error deleting git branch {branch_id}: {e}")
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
        git_branch.updated_at = datetime.now(timezone.utc)
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
                    'assigned_agent_id': agent_id,
                    'updated_at': datetime.now(timezone.utc)
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
                    'assigned_agent_id': None,
                    'updated_at': datetime.now(timezone.utc)
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
                    "generated_at": datetime.now(timezone.utc).isoformat()
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
            
            now = datetime.now(timezone.utc)
            
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
            # First find the branch to get project_id
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
                        "priority": str(git_branch.priority)
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
                
                model.updated_at = datetime.now(timezone.utc)
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
                    'status': 'cancelled',
                    'updated_at': datetime.now(timezone.utc)
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
                    'status': 'todo',
                    'updated_at': datetime.now(timezone.utc)
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