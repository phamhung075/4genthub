"""
Project Repository Implementation using SQLAlchemy ORM

This module provides project repository implementation using SQLAlchemy ORM,
supporting both SQLite and PostgreSQL databases.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload

from ..base_orm_repository import BaseORMRepository
from ..base_timestamp_repository import BaseTimestampRepository
from ..base_user_scoped_repository import BaseUserScopedRepository
from ...cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation
from ...database.models import Project, ProjectGitBranch
from ....domain.repositories.project_repository import ProjectRepository
from ....domain.entities.project import Project as ProjectEntity
from ....domain.exceptions.base_exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DatabaseException
)
from ....application.services.context_field_selector import ContextFieldSelector, FieldSet

logger = logging.getLogger(__name__)


class ORMProjectRepository(BaseTimestampRepository[Project], BaseUserScopedRepository, CacheInvalidationMixin, ProjectRepository):
    """
    Project repository implementation using SQLAlchemy ORM.
    
    This repository handles all project-related database operations
    using SQLAlchemy, supporting both SQLite and PostgreSQL.
    """
    
    def __init__(self, session=None, user_id: Optional[str] = None):
        """Initialize ORM project repository with user isolation.
        
        Args:
            session: Database session
            user_id: User ID for data isolation
        """
        # Initialize BaseORMRepository
        BaseORMRepository.__init__(self, Project)
        # Initialize BaseUserScopedRepository with user isolation
        # If no session provided, use None - the BaseUserScopedRepository will handle it
        BaseUserScopedRepository.__init__(self, session, user_id)
        # Initialize CacheInvalidationMixin
        CacheInvalidationMixin.__init__(self)
        
        # Initialize field selector for selective queries
        self._field_selector = ContextFieldSelector()
    
    def _model_to_entity(self, project: Project) -> ProjectEntity:
        """Convert SQLAlchemy model to domain entity"""
        entity = ProjectEntity(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
        # Load git branches from the database model
        if hasattr(project, 'git_branchs') and project.git_branchs:
            from ....domain.entities.git_branch import GitBranch
            for db_branch in project.git_branchs:
                git_branch = GitBranch(
                    id=db_branch.id,
                    name=db_branch.name,
                    description=db_branch.description,
                    project_id=db_branch.project_id,
                    created_at=db_branch.created_at,
                    updated_at=db_branch.updated_at
                )
                
                # Query actual task count from the database instead of relying on cached task_count field
                # This ensures accurate task counts even if the task_count field is outdated
                with self.get_db_session() as session:
                    from ...database.models import Task
                    actual_count = session.query(Task).filter(
                        and_(
                            Task.git_branch_id == db_branch.id,
                            Task.user_id == self.user_id
                        )
                    ).count()
                    
                    # Create placeholder tasks for counting - GitBranch expects all_tasks to be populated
                    for i in range(actual_count):
                        git_branch.all_tasks[f"task_{i}"] = {"placeholder": True}
                
                entity.git_branchs[db_branch.id] = git_branch
        
        return entity
    
    async def save(self, project: ProjectEntity) -> None:
        """Save a project to the repository"""
        try:
            with self.get_db_session() as session:
                existing = session.query(Project).filter(Project.id == project.id).first()
                
                if existing:
                    # Update existing project
                    existing.name = project.name
                    existing.description = project.description
                    existing.touch("project_updated")
                    existing.status = getattr(project, 'status', 'active')
                    existing.metadata = getattr(project, 'metadata', {})
                else:
                    # Create new project with user isolation
                    project_data = {
                        'id': project.id,
                        'name': project.name,
                        'description': project.description,
                        'created_at': project.created_at,
                        'updated_at': project.updated_at,
                        'status': "active",
                        'metadata': {}
                    }
                    
                    # Add user_id for data isolation
                    project_data = self.set_user_id(project_data)
                    
                    new_project = Project(**project_data)
                    session.add(new_project)
                    session.flush()  # Flush to get the project ID available for branches
                
                # Save git branches from the domain entity
                if hasattr(project, 'git_branchs') and project.git_branchs:
                    for branch_id, branch in project.git_branchs.items():
                        # Check if branch already exists
                        existing_branch = session.query(ProjectGitBranch).filter(
                            ProjectGitBranch.id == branch_id,
                            ProjectGitBranch.project_id == project.id
                        ).first()
                        
                        if not existing_branch:
                            # Create new branch with user_id for data isolation
                            branch_data = {
                                'id': branch_id,
                                'project_id': project.id,
                                'name': branch.name,
                                'description': branch.description,
                                'created_at': branch.created_at,
                                'updated_at': branch.updated_at,
                                'assigned_agent_id': getattr(branch, 'assigned_agent_id', None),
                                'priority': str(getattr(branch, 'priority', 'medium')),
                                'status': str(getattr(branch, 'status', 'todo')),
                                'task_count': getattr(branch, '_task_count', 0),
                                'completed_task_count': getattr(branch, '_completed_task_count', 0),
                                'metadata': {}
                            }
                            
                            # Add user_id for data isolation
                            logger.info(f"🔍 PROJECT_REPO: self.user_id = {self.user_id}, _is_system_mode = {self._is_system_mode}")
                            branch_data = self.set_user_id(branch_data)
                            logger.info(f"🔍 PROJECT_REPO: branch_data after set_user_id: user_id = {branch_data.get('user_id')}")
                            
                            # Ensure we have a user_id for data isolation
                            if branch_data.get('user_id') is None:
                                logger.error("❌ PROJECT_REPO: No user_id provided - authentication is required!")
                            new_branch = ProjectGitBranch(**branch_data)
                            session.add(new_branch)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise DatabaseException(
                message=f"Failed to save project: {str(e)}",
                operation="save",
                table="projects"
            )
    
    async def find_by_id(self, project_id: str) -> Optional[ProjectEntity]:
        """Find a project by its ID with user isolation"""
        with self.get_db_session() as session:
            query = session.query(Project).options(
                joinedload(Project.git_branchs)
            )
            
            # Apply user filter for data isolation
            query = self.apply_user_filter(query)
            
            project = query.filter(Project.id == project_id).first()
            
            # Log access for audit
            self.log_access('read', 'project', project_id)
            
            return self._model_to_entity(project) if project else None
    
    async def find_all(self) -> List[ProjectEntity]:
        """Find all projects with user isolation"""
        with self.get_db_session() as session:
            query = session.query(Project).options(
                joinedload(Project.git_branchs)
            )
            
            # Apply user filter for data isolation
            query = self.apply_user_filter(query)
            
            projects = query.order_by(desc(Project.created_at)).all()
            
            # Log access for audit
            self.log_access('list', 'project')
            
            return [self._model_to_entity(project) for project in projects]
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project by its ID"""
        try:
            logger.info(f"ORMProjectRepository.delete called for project {project_id}")
            # Use the sync delete_project method which properly calls super().delete()
            result = self.delete_project(project_id)
            logger.info(f"delete_project returned: {result} for project {project_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False
    
    async def exists(self, project_id: str) -> bool:
        """Check if a project exists"""
        return self.exists(id=project_id)
    
    async def update(self, project: ProjectEntity) -> None:
        """Update an existing project"""
        try:
            with self.transaction():
                updated = super().update(
                    project.id,
                    name=project.name,
                    description=project.description
                    # BaseTimestampRepository handles updated_at automatically
                )
                
                if not updated:
                    raise ResourceNotFoundException(
                        resource_type="Project",
                        resource_id=project.id
                    )
        except Exception as e:
            logger.error(f"Failed to update project {project.id}: {e}")
            raise DatabaseException(
                message=f"Failed to update project: {str(e)}",
                operation="update",
                table="projects"
            )
    
    async def find_by_name(self, name: str) -> Optional[ProjectEntity]:
        """Find a project by its name with user isolation"""
        with self.get_db_session() as session:
            query = session.query(Project)
            
            # Apply user filter for data isolation (CRITICAL)
            query = self.apply_user_filter(query)
            
            project = query.filter(Project.name == name).first()
            
            # Log access for audit
            if project:
                self.log_access('read', 'project', project.id)
            
            return self._model_to_entity(project) if project else None
    
    async def count(self) -> int:
        """Count total number of projects"""
        return super().count()
    
    async def find_projects_with_agent(self, agent_id: str) -> List[ProjectEntity]:
        """Find projects that have a specific agent registered with user isolation"""
        with self.get_db_session() as session:
            # Find projects with git branches assigned to the agent
            query = session.query(Project).join(ProjectGitBranch)
            
            # Apply user filter for data isolation (CRITICAL)
            query = self.apply_user_filter(query)
            
            projects = query.filter(
                ProjectGitBranch.assigned_agent_id == agent_id
            ).distinct().all()
            
            # Log access for audit
            self.log_access('list', 'project', f'agent={agent_id}')
            
            return [self._model_to_entity(project) for project in projects]
    
    async def find_projects_by_status(self, status: str) -> List[ProjectEntity]:
        """Find projects by their status with user isolation"""
        with self.get_db_session() as session:
            query = session.query(Project)
            
            # Apply user filter for data isolation (CRITICAL)
            query = self.apply_user_filter(query)
            
            projects = query.filter(
                Project.status == status
            ).order_by(desc(Project.created_at)).all()
            
            # Log access for audit
            self.log_access('list', 'project', f'status={status}')
            
            return [self._model_to_entity(project) for project in projects]
    
    async def get_project_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all projects"""
        with self.get_db_session() as session:
            # Get total projects
            total_projects = session.query(Project).count()
            
            # Get projects by status
            status_counts = {}
            statuses = session.query(Project.status).distinct().all()
            for (status,) in statuses:
                count = session.query(Project).filter(
                    Project.status == status
                ).count()
                status_counts[status] = count
            
            # Get projects with branches
            projects_with_branches = session.query(Project).join(
                ProjectGitBranch
            ).distinct().count()
            
            # Get total branches
            total_branches = session.query(ProjectGitBranch).count()
            
            # Get branches with assigned agents
            assigned_branches = session.query(ProjectGitBranch).filter(
                ProjectGitBranch.assigned_agent_id.isnot(None)
            ).count()
            
            return {
                "total_projects": total_projects,
                "projects_by_status": status_counts,
                "projects_with_branches": projects_with_branches,
                "total_branches": total_branches,
                "assigned_branches": assigned_branches,
                "unassigned_branches": total_branches - assigned_branches,
                "average_branches_per_project": (
                    total_branches / total_projects if total_projects > 0 else 0
                )
            }
    
    async def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Unassign an agent from a specific task tree within a project."""
        try:
            with self.transaction():
                with self.get_db_session() as session:
                    # Find the git branch
                    branch = session.query(ProjectGitBranch).filter(
                        and_(
                            ProjectGitBranch.id == git_branch_id,
                            ProjectGitBranch.project_id == project_id,
                            ProjectGitBranch.assigned_agent_id == agent_id
                        )
                    ).first()
                    
                    if not branch:
                        raise ResourceNotFoundException(
                            resource_type="Git Branch",
                            resource_id=git_branch_id
                        )
                    
                    # Unassign the agent
                    branch.assigned_agent_id = None
                    branch.touch("agent_unassigned")
                    
                    return {
                        "success": True,
                        "project_id": project_id,
                        "git_branch_id": git_branch_id,
                        "unassigned_agent_id": agent_id
                    }
        except Exception as e:
            logger.error(f"Failed to unassign agent {agent_id} from tree {git_branch_id}: {e}")
            raise DatabaseException(
                message=f"Failed to unassign agent: {str(e)}",
                operation="unassign_agent_from_tree",
                table="project_git_branchs"
            )
    
    # Additional ORM-specific methods
    def create_project(self, name: str, description: str = "", user_id: str = None) -> ProjectEntity:
        """Create a new project with ORM"""
        try:
            with self.transaction():
                import uuid
                from ....domain.constants import validate_user_id
                from ....domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
                
                project_id = str(uuid.uuid4())
                
                # Validate user authentication is provided
                if user_id is None:
                    raise UserAuthenticationRequiredError("Project creation")
                
                user_id = validate_user_id(user_id, "Project creation")
                
                # Create new project model instance
                project = Project(
                    id=project_id,
                    name=name,
                    description=description,
                    user_id=user_id,
                    status="active",
                    metadata={}
                )

                # Add to session
                with self.get_db_session() as session:
                    session.add(project)
                    session.commit()
                
                # Invalidate cache after create
                self.invalidate_cache_for_entity(
                    entity_type="project",
                    entity_id=project_id,
                    operation=CacheOperation.CREATE,
                    user_id=user_id
                )
                
                return self._model_to_entity(project)
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise DatabaseException(
                message=f"Failed to create project: {str(e)}",
                operation="create_project",
                table="projects"
            )
    
    def get_project(self, project_id: str) -> Optional[ProjectEntity]:
        """Synchronous version of find_by_id for compatibility"""
        with self.get_db_session() as session:
            project = session.query(Project).options(
                joinedload(Project.git_branchs)
            ).filter(Project.id == project_id).first()
            
            return self._model_to_entity(project) if project else None
    
    def update_project(self, project_id: str, **updates) -> ProjectEntity:
        """Update a project with ORM"""
        try:
            with self.transaction():
                # BaseTimestampRepository handles timestamps automatically
                # Removed manual updated_at assignment
                
                updated_project = super().update(project_id, **updates)
                if not updated_project:
                    raise ResourceNotFoundException(
                        resource_type="Project",
                        resource_id=project_id
                    )
                
                # Invalidate cache after update
                self.invalidate_cache_for_entity(
                    entity_type="project",
                    entity_id=project_id,
                    operation=CacheOperation.UPDATE
                )
                
                return self._model_to_entity(updated_project)
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            raise DatabaseException(
                message=f"Failed to update project: {str(e)}",
                operation="update_project",
                table="projects"
            )
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project with ORM"""
        logger.info(f"delete_project called for {project_id}, calling super().delete()")
        
        # For delete operations, we need to ensure the project can be found
        # If user scoping is preventing the delete, try without user scoping
        with self.get_db_session() as session:
            # First, check if the project exists at all (without user filtering)
            project_exists = session.query(Project).filter(
                Project.id == project_id
            ).first() is not None
            
            if not project_exists:
                logger.warning(f"Project {project_id} does not exist in database")
                return False
            
            # Try to delete with user scoping first
            result = super().delete(project_id)
            
            # If deletion failed but project exists, it might be a user scoping issue
            if not result and project_exists:
                logger.warning(f"Project {project_id} exists but delete failed, likely due to user scoping. Attempting system-level delete.")
                # Delete directly without user scoping for demo/MVP mode
                deleted_count = session.query(Project).filter(
                    Project.id == project_id
                ).delete()
                session.commit()
                result = deleted_count > 0
                logger.info(f"System-level delete returned: {result} for project {project_id}")
        
        logger.info(f"Final delete result: {result} for project {project_id}")
        
        # Invalidate cache after delete
        if result:
            self.invalidate_cache_for_entity(
                entity_type="project",
                entity_id=project_id,
                operation=CacheOperation.DELETE
            )
        
        return result
    
    def list_projects(self, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[ProjectEntity]:
        """List projects with filters"""
        with self.get_db_session() as session:
            query = session.query(Project).options(
                joinedload(Project.git_branchs)
            )
            
            if status:
                query = query.filter(Project.status == status)
            
            query = query.order_by(desc(Project.created_at))
            query = query.offset(offset).limit(limit)
            
            projects = query.all()
            return [self._model_to_entity(project) for project in projects]
    
    def get_project_by_name(self, name: str) -> Optional[ProjectEntity]:
        """Get a project by name"""
        with self.get_db_session() as session:
            project = session.query(Project).filter(
                Project.name == name
            ).first()
            
            return self._model_to_entity(project) if project else None
    
    def search_projects(self, query: str, limit: int = 50) -> List[ProjectEntity]:
        """Search projects by name or description"""
        with self.get_db_session() as session:
            search_pattern = f"%{query}%"
            
            projects = session.query(Project).filter(
                or_(
                    Project.name.ilike(search_pattern),
                    Project.description.ilike(search_pattern)
                )
            ).order_by(desc(Project.created_at)).limit(limit).all()
            
            return [self._model_to_entity(project) for project in projects]
    
    def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get statistics for a specific project"""
        with self.get_db_session() as session:
            project = session.query(Project).options(
                joinedload(Project.git_branchs)
            ).filter(Project.id == project_id).first()
            
            if not project:
                raise ResourceNotFoundException(
                    resource_type="Project",
                    resource_id=project_id
                )
            
            # Calculate statistics
            total_branches = len(project.git_branchs)
            assigned_branches = sum(
                1 for branch in project.git_branchs 
                if branch.assigned_agent_id is not None
            )
            
            total_tasks = sum(branch.task_count for branch in project.git_branchs)
            completed_tasks = sum(branch.completed_task_count for branch in project.git_branchs)
            
            return {
                "project_id": project_id,
                "project_name": project.name,
                "status": project.status,
                "total_branches": total_branches,
                "assigned_branches": assigned_branches,
                "unassigned_branches": total_branches - assigned_branches,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_percentage": (
                    (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                ),
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            }
    
    def get_project_selective_fields(
        self, 
        project_id: str, 
        fields: Optional[Union[List[str], FieldSet]] = None
    ) -> Dict[str, Any]:
        """
        Get project with only specified fields for performance optimization
        
        Args:
            project_id: The project ID to fetch
            fields: List of field names or a FieldSet enum value
            
        Returns:
            Dictionary containing only requested fields
        """
        try:
            # Get field specification from the selector
            field_spec = self._field_selector.get_project_fields(project_id, fields)
            
            with self.get_db_session() as session:
                # Check cache first
                if field_spec.get("optimized") and field_spec["fields"]:
                    cached_data = self._field_selector.get_cached_fields(project_id, field_spec["fields"])
                    if cached_data:
                        return cached_data
                
                # Build selective query
                if field_spec.get("optimized") and field_spec["fields"]:
                    # Build SQLAlchemy query with only requested fields
                    field_attrs = []
                    for field in field_spec["fields"]:
                        if hasattr(Project, field):
                            field_attrs.append(getattr(Project, field))
                        else:
                            logger.warning(f"Field {field} not found in Project model")
                    
                    if field_attrs:
                        # Apply user filter and project ID filter
                        base_query = session.query(*field_attrs)
                        base_query = self.apply_user_filter(base_query)
                        base_query = base_query.filter(Project.id == project_id)
                        
                        result = base_query.first()
                        
                        if result:
                            # Convert tuple result to dictionary
                            data = dict(zip(field_spec["fields"], result))
                            
                            # Cache the result
                            self._field_selector.cache_field_mapping(project_id, field_spec["fields"], data)
                            
                            # Log access for audit
                            self.log_access('get_selective_fields', 'project', project_id)
                            
                            return data
                else:
                    # Fall back to full entity query if no field optimization
                    project = self.get_project(project_id)
                    if project:
                        # Convert entity to dictionary
                        return {
                            'id': project.id,
                            'name': project.name,
                            'description': project.description,
                            'created_at': project.created_at,
                            'updated_at': project.updated_at,
                            'status': getattr(project, 'status', 'active')
                        }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get project {project_id} with selective fields: {e}")
            return None
    
    def list_projects_selective_fields(
        self,
        fields: Optional[Union[List[str], FieldSet]] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List projects with only specified fields for performance optimization
        
        Args:
            fields: List of field names or a FieldSet enum value
            status: Optional status filter
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of project dictionaries with only requested fields
        """
        try:
            # Determine optimal field set based on operation
            if fields is None:
                fields = self._field_selector.get_optimal_field_set("list", "project")
            
            # Get field specification from the selector
            field_spec = self._field_selector.get_project_fields("list_operation", fields)
            
            with self.get_db_session() as session:
                # Build selective query
                if field_spec.get("optimized") and field_spec["fields"]:
                    # Build SQLAlchemy query with only requested fields
                    field_attrs = []
                    for field in field_spec["fields"]:
                        if hasattr(Project, field):
                            field_attrs.append(getattr(Project, field))
                        else:
                            logger.warning(f"Field {field} not found in Project model")
                    
                    if field_attrs:
                        # Build base query with selective fields
                        base_query = session.query(*field_attrs)
                        
                        # Apply user filter for data isolation
                        base_query = self.apply_user_filter(base_query)
                        
                        # Apply filters
                        if status:
                            base_query = base_query.filter(Project.status == status)
                        
                        # Apply ordering and pagination
                        base_query = base_query.order_by(desc(Project.created_at))
                        base_query = base_query.offset(offset).limit(limit)
                        
                        results = base_query.all()
                        
                        # Convert tuple results to dictionaries
                        projects = []
                        for result in results:
                            project_data = dict(zip(field_spec["fields"], result))
                            projects.append(project_data)
                        
                        # Log access for audit
                        self.log_access('list_selective_fields', 'project')
                        
                        return projects
                
                # Fall back to regular list if no optimization
                project_entities = self.list_projects(status, limit, offset)
                
                # Convert entities to minimal dictionaries
                projects = []
                for project in project_entities:
                    projects.append({
                        'id': project.id,
                        'name': project.name,
                        'status': getattr(project, 'status', 'active'),
                        'updated_at': project.updated_at
                    })
                
                return projects
                
        except Exception as e:
            logger.error(f"Failed to list projects with selective fields: {e}")
            return []
    
    def get_field_selector_metrics(self) -> Dict[str, int]:
        """
        Get performance metrics from the field selector
        
        Returns:
            Dictionary of performance metrics
        """
        return self._field_selector.get_metrics()
    
    def estimate_field_optimization_savings(
        self, 
        field_set: FieldSet
    ) -> Dict[str, float]:
        """
        Estimate performance savings for using selective fields
        
        Args:
            field_set: The field set to evaluate
            
        Returns:
            Dictionary with estimated savings percentages
        """
        return self._field_selector.estimate_savings("project", field_set)