"""Project Application Service following DDD patterns"""

from typing import Dict, Any, Optional
from fastmcp.task_management.application.use_cases.create_project import CreateProjectUseCase
from fastmcp.task_management.application.use_cases.get_project import GetProjectUseCase
from fastmcp.task_management.application.use_cases.list_projects import ListProjectsUseCase
from fastmcp.task_management.application.use_cases.update_project import UpdateProjectUseCase
from fastmcp.task_management.application.use_cases.create_git_branch import CreateGitBranchUseCase
from fastmcp.task_management.application.use_cases.project_health_check import ProjectHealthCheckUseCase
from ...domain.repositories.project_repository import ProjectRepository


class ProjectApplicationService:
    """Application service for project management following DDD patterns"""
    
    def __init__(self, project_repository: ProjectRepository, user_id: Optional[str] = None):
        self._project_repository = project_repository
        self._user_id = user_id  # Store user context
        
        # Initialize use cases with user-scoped repository
        self._create_project_use_case = CreateProjectUseCase(self._get_user_scoped_repository())
        self._get_project_use_case = GetProjectUseCase(self._get_user_scoped_repository())
        self._list_projects_use_case = ListProjectsUseCase(self._get_user_scoped_repository())
        self._update_project_use_case = UpdateProjectUseCase(self._get_user_scoped_repository())
        self._create_git_branch_use_case = CreateGitBranchUseCase(self._get_user_scoped_repository())
        self._project_health_check_use_case = ProjectHealthCheckUseCase(self._get_user_scoped_repository())
    
    def _get_user_scoped_repository(self) -> ProjectRepository:
        """Get a user-scoped version of the repository if it supports user context."""
        if hasattr(self._project_repository, 'with_user') and self._user_id:
            # Repository supports user scoping
            return self._project_repository.with_user(self._user_id)
        elif hasattr(self._project_repository, 'user_id'):
            # Repository has user_id property, set it if needed
            if self._user_id and self._project_repository.user_id != self._user_id:
                # Create new instance with user_id
                repo_class = type(self._project_repository)
                if hasattr(self._project_repository, 'session'):
                    return repo_class(self._project_repository.session, user_id=self._user_id)
        return self._project_repository
    
    def with_user(self, user_id: str) -> 'ProjectApplicationService':
        """Create a new service instance scoped to a specific user."""
        return ProjectApplicationService(self._project_repository, user_id)
    
    async def create_project(self, project_id: str, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new project"""
        return await self._create_project_use_case.execute(project_id, name, description)
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        return await self._get_project_use_case.execute(project_id)
    
    async def list_projects(self) -> Dict[str, Any]:
        """List all projects"""
        return await self._list_projects_use_case.execute()
    
    async def update_project(self, project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing project"""
        return await self._update_project_use_case.execute(project_id, name, description)
    
    async def create_git_branch(self, project_id: str, git_branch_name: str, tree_name: str, tree_description: str = "") -> Dict[str, Any]:
        """Create a new task tree within a project"""
        return await self._create_git_branch_use_case.execute(project_id, git_branch_name, tree_name, tree_description)
    
    async def project_health_check(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform health check on project(s)"""
        return await self._project_health_check_use_case.execute(project_id)
    
    async def register_agent(self, project_id: str, agent_id: str, name: str, capabilities: Optional[list] = None) -> Dict[str, Any]:
        """Register an agent to a project"""
        from ...domain.entities.agent import Agent
        from ...domain.enums.agent_roles import AgentRole
        from datetime import datetime, timezone
        
        project = await self._get_user_scoped_repository().find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        # Create agent entity
        agent_capabilities = set()
        if capabilities:
            for cap in capabilities:
                try:
                    agent_capabilities.add(AgentRole(cap))
                except ValueError:
                    # Skip invalid capabilities
                    pass
        
        agent = Agent(
            id=agent_id,
            name=name,
            capabilities=agent_capabilities
            # created_at will be set automatically by the entity
        )
        
        # Register agent to project
        try:
            project.register_agent(agent)
            await self._get_user_scoped_repository().update(project)
            
            return {
                "success": True,
                "agent": {
                    "id": agent.id,
                    "name": agent.name,
                    "capabilities": [cap.value for cap in agent.capabilities],
                    "created_at": agent.created_at.isoformat()
                },
                "message": f"Agent '{agent_id}' registered successfully"
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def assign_agent_to_tree(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a task tree"""
        project = await self._get_user_scoped_repository().find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        try:
            project.assign_agent_to_tree(agent_id, git_branch_name)
            await self._get_user_scoped_repository().update(project)
            
            return {
                "success": True,
                "message": f"Agent '{agent_id}' assigned to tree '{git_branch_name}' successfully"
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def unregister_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Unregister an agent from a project"""
        project = await self._get_user_scoped_repository().find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        if agent_id not in project.registered_agents:
            return {
                "success": False,
                "error": f"Agent '{agent_id}' not found in project '{project_id}'"
            }
        
        # Get agent details before removal
        agent = project.registered_agents[agent_id]
        
        # Remove agent from registered agents
        del project.registered_agents[agent_id]
        
        # Remove agent assignments  
        assignments_to_remove = []
        for branch_name, assigned_agent_id in project.agent_assignments.items():
            if assigned_agent_id == agent_id:
                assignments_to_remove.append(branch_name)
        
        for branch_name in assignments_to_remove:
            del project.agent_assignments[branch_name]
        
        # Remove any active work sessions
        sessions_to_remove = []
        for session_id, session in project.active_work_sessions.items():
            if session.agent_id == agent_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del project.active_work_sessions[session_id]
        
        # Remove resource locks
        resources_to_unlock = []
        for resource, locked_agent_id in project.resource_locks.items():
            if locked_agent_id == agent_id:
                resources_to_unlock.append(resource)
        
        for resource in resources_to_unlock:
            del project.resource_locks[resource]
        
        await self._project_repository.update(project)
        
        return {
            "success": True,
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "capabilities": [cap.value for cap in agent.capabilities]
            },
            "removed_sessions": len(sessions_to_remove),
            "unlocked_resources": len(resources_to_unlock),
            "message": f"Agent '{agent_id}' unregistered successfully"
        }
    
    async def cleanup_obsolete(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Clean up obsolete project data"""
        if project_id:
            project = await self._get_user_scoped_repository().find_by_id(project_id)
            
            if not project:
                return {
                    "success": False,
                    "error": f"Project with ID '{project_id}' not found"
                }
            
            cleaned_items = self._cleanup_project_data(project)
            
            if cleaned_items:
                await self._get_user_scoped_repository().update(project)
            
            return {
                "success": True,
                "project_id": project_id,
                "cleaned_items": cleaned_items,
                "message": f"Cleanup completed for project '{project_id}'"
            }
        
        else:
            # Clean all projects
            projects = await self._get_user_scoped_repository().find_all()
            total_cleaned = 0
            cleanup_results = {}
            
            for project in projects:
                cleaned_items = self._cleanup_project_data(project)
                cleanup_results[project.id] = cleaned_items
                total_cleaned += len(cleaned_items)
                
                if cleaned_items:
                    await self._get_user_scoped_repository().update(project)
            
            return {
                "success": True,
                "total_cleaned": total_cleaned,
                "cleanup_results": cleanup_results,
                "message": f"Cleanup completed for all projects. {total_cleaned} items cleaned"
            }
    
    def _cleanup_project_data(self, project) -> list:
        """Clean up obsolete data from a project"""
        cleaned_items = []
        
        # Remove assignments to non-existent trees
        assignments_to_remove = []
        for git_branch_name, agent_id in project.agent_assignments.items():
            if git_branch_name not in project.git_branchs:
                assignments_to_remove.append(git_branch_name)
            elif agent_id not in project.registered_agents:
                assignments_to_remove.append(git_branch_name)
        
        for git_branch_name in assignments_to_remove:
            del project.agent_assignments[git_branch_name]
            cleaned_items.append(f"Removed assignment to tree '{git_branch_name}'")
        
        # Remove active work sessions for unregistered agents
        sessions_to_remove = []
        for session_id, session in project.active_work_sessions.items():
            if session.agent_id not in project.registered_agents:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del project.active_work_sessions[session_id]
            cleaned_items.append(f"Removed orphaned work session '{session_id}'")
        
        # Remove resource locks for unregistered agents
        resources_to_unlock = []
        for resource, agent_id in project.resource_locks.items():
            if agent_id not in project.registered_agents:
                resources_to_unlock.append(resource)
        
        for resource in resources_to_unlock:
            del project.resource_locks[resource]
            cleaned_items.append(f"Unlocked resource '{resource}'")
        
        return cleaned_items