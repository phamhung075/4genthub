"""
Use Case: Cleanup Obsolete Project Data
"""
from typing import Dict, Any
from ...domain.repositories.project_repository import ProjectRepository
from datetime import datetime

class CleanupObsoleteUseCase:
    def __init__(self, project_repo: ProjectRepository):
        self._project_repo = project_repo

    async def execute(self, project_id: str = None) -> Dict[str, Any]:
        """Clean up obsolete project data"""
        try:
            if project_id:
                project = await self._project_repo.find_by_id(project_id)
                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}
                
                cleaned_items = self._cleanup_project_data(project)
                
                if cleaned_items:
                    await self._project_repo.update(project)
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "cleaned_items": cleaned_items,
                    "message": f"Cleanup completed for project {project_id}"
                }
            else:
                projects = await self._project_repo.find_all()
                total_cleaned = 0
                cleanup_results = {}
                
                for project in projects:
                    cleaned_items = self._cleanup_project_data(project)
                    cleanup_results[project.id] = cleaned_items
                    total_cleaned += len(cleaned_items)
                    
                    if cleaned_items:
                        await self._project_repo.update(project)
                
                return {
                    "success": True,
                    "total_cleaned": total_cleaned,
                    "cleanup_results": cleanup_results,
                    "message": f"Cleanup completed for all projects. {total_cleaned} items cleaned"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _cleanup_project_data(self, project) -> list:
        """Clean up obsolete data from a project entity"""
        cleaned_items = []
        
        # Remove assignments to non-existent trees
        assignments_to_remove = []
        for agent_id, tree_id in project.agent_assignments.items():
            if tree_id not in project.git_branchs:
                assignments_to_remove.append(agent_id)
                cleaned_items.append(f"Removed assignment of agent {agent_id} to non-existent tree {tree_id}")
        
        for agent_id in assignments_to_remove:
            del project.agent_assignments[agent_id]
        
        # Remove unregistered agents from assignments
        unregistered_agents = []
        for agent_id in project.agent_assignments:
            if agent_id not in project.registered_agents:
                unregistered_agents.append(agent_id)
                cleaned_items.append(f"Removed unregistered agent {agent_id} from assignments")
        
        for agent_id in unregistered_agents:
            del project.agent_assignments[agent_id]
        
        return cleaned_items 