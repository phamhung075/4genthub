"""Simple Multi-Agent Adapter

Interface layer adapter for backward compatibility with existing multi-agent tools.
Moved from interface/mcp_tools/simple_multi_agent_tools.py for proper DDD layering.
"""

import logging
from typing import Optional, Dict, Any
from ...application.services.project_management_service import ProjectManagementService
from ...infrastructure.utilities.path_resolver import PathResolver

logger = logging.getLogger(__name__)


class SimpleMultiAgentAdapter:
    """Simplified multi-agent adapter for testing and backward compatibility"""
    
    def __init__(self, projects_file_path: Optional[str] = None, path_resolver: Optional[PathResolver] = None, project_service: Optional[ProjectManagementService] = None):
        """
        Initialize SimpleMultiAgentAdapter with optional dependency injection for testability.
        Args:
            projects_file_path: Optional path to projects file
            path_resolver: Injected PathResolver instance
            project_service: Injected ProjectManagementService instance
        """
        self._path_resolver = path_resolver or PathResolver()
        self._project_service = project_service or ProjectManagementService(self._path_resolver, projects_file_path)
        
        # Expose attributes that tests expect for backward compatibility
        self._projects_file = self._project_service._projects_file
        self._brain_dir = self._project_service._brain_dir
        self._agent_converter = self._project_service._agent_converter
        self._orchestrator = self._project_service._orchestrator
    
    def create_project(self, project_id: str, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new project"""
        return self._project_service.create_project(
            project_id=project_id,
            name=name,
            description=description or f"Project: {name}"
        )
    
    def register_agent(self, project_id: str, agent_id: str, name: str, call_agent: str = None) -> Dict[str, Any]:
        """Register an agent to a project"""
        return self._project_service.register_agent(
            project_id=project_id,
            agent_id=agent_id,
            name=name,
            call_agent=call_agent or f"@{agent_id.replace('_', '-')}-agent"
        )
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        return self._project_service.get_project(project_id)
    
    def assign_agent_to_tree(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign agent to task tree"""
        return self._project_service.assign_agent_to_tree(project_id, agent_id, git_branch_name)
    
    def list_projects(self) -> Dict[str, Any]:
        """List all projects"""
        return self._project_service.list_projects()
    
    # Properties for testing compatibility
    @property
    def _projects(self):
        """Access to internal projects data for testing"""
        return self._project_service._projects
    
