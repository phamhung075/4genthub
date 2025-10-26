"""Get Project Use Case"""

from typing import Dict, Any, Optional
from ...domain.repositories.project_repository import ProjectRepository


class GetProjectUseCase:
    """Use case for retrieving a project by ID"""
    
    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository
    
    async def execute(self, project_id: str) -> Dict[str, Any]:
        """Execute the get project use case"""
        
        project = await self._project_repository.find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        # Calculate project-level aggregations
        branch_count = len(project.git_branchs)
        task_count = sum(tree.get_task_count() for tree in project.git_branchs.values())

        # DEBUG LOGGING
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 GET_PROJECT DEBUG: project_id={project_id}")
        logger.info(f"🔍 branch_count={branch_count}, task_count={task_count}")
        logger.info(f"🔍 project.git_branchs keys: {list(project.git_branchs.keys())}")
        for tree_id, tree in project.git_branchs.items():
            logger.info(f"🔍 Branch {tree_id}: all_tasks count={len(tree.all_tasks)}, get_task_count()={tree.get_task_count()}")

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "branch_count": branch_count,  # Total branches in project
                "task_count": task_count,      # Total tasks across all branches
                "git_branchs": {
                    tree_id: {
                        "id": tree.id,
                        "name": tree.name,
                        "description": tree.description,
                        "created_at": tree.created_at.isoformat(),
                        # Complete branch statistics (matching standalone branch endpoint)
                        "task_count": tree.get_task_count(),
                        "completed_tasks": tree.get_completed_task_count(),
                        "in_progress_tasks": tree.get_active_task_count(),
                        "blocked_tasks": tree.get_tree_status()["status_breakdown"].get("blocked", 0),
                        "todo_tasks": tree.get_tree_status()["status_breakdown"].get("todo", 0),
                        "progress_percentage": tree.get_progress_percentage()
                    }
                    for tree_id, tree in project.git_branchs.items()
                },
                "registered_agents": {
                    agent_id: {
                        "id": agent.id,
                        "name": agent.name,
                        "capabilities": [cap.value for cap in agent.capabilities],
                        "created_at": agent.created_at.isoformat()
                    }
                    for agent_id, agent in project.registered_agents.items()
                },
                "agent_assignments": project.agent_assignments,
                "orchestration_status": project.get_orchestration_status()
            }
        }