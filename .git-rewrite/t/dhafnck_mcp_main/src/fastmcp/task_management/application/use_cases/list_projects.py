"""List Projects Use Case"""

from typing import Dict, Any, List, Optional
from ...domain.repositories.project_repository import ProjectRepository


class ListProjectsUseCase:
    """Use case for listing all projects"""
    
    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository
    
    async def execute(self, include_branches: bool = True) -> Dict[str, Any]:
        """
        Execute the list projects use case
        
        Args:
            include_branches: Whether to include git branch data in the response.
                            Defaults to True for optimal performance.
        """
        
        projects = await self._project_repository.find_all()
        
        # Debug logging to understand what's being returned
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Projects returned from repository: {type(projects)}, count: {len(projects) if projects else 0}")
        if projects and len(projects) > 0:
            logger.info(f"First project type: {type(projects[0])}")
            logger.info(f"First project content: {projects[0]}")
        
        project_list = []
        for project in projects:
            project_info = {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "git_branchs_count": len(project.git_branchs),
                "registered_agents_count": len(project.registered_agents),
                "active_assignments": len(project.agent_assignments),
                "active_sessions": len(project.active_work_sessions)
            }
            
            # Include full git branch data to eliminate N+1 queries in frontend
            if include_branches and project.git_branchs:
                git_branchs_dict = {}
                # Iterate over the values (GitBranch objects), not the keys
                for branch_id, branch in project.git_branchs.items():
                    git_branchs_dict[branch_id] = {
                        "id": branch.id,
                        "name": branch.name,  # GitBranch entity uses 'name' not 'git_branch_name'
                        "description": branch.description if hasattr(branch, 'description') else "",
                        "created_at": branch.created_at.isoformat() if hasattr(branch, 'created_at') else "",
                        "updated_at": branch.updated_at.isoformat() if hasattr(branch, 'updated_at') else "",
                        "status": branch.status if hasattr(branch, 'status') else "active",
                        "agent_assignments": len(branch.agent_assignments) if hasattr(branch, 'agent_assignments') else 0,
                        "task_count": len(branch.all_tasks) if hasattr(branch, 'all_tasks') else 0
                    }
                project_info["git_branchs"] = git_branchs_dict
            
            project_list.append(project_info)
        
        return {
            "success": True,
            "projects": project_list,
            "count": len(project_list)
        }