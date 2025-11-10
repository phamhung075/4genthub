"""Get Project Use Case"""

from typing import Any

from ...domain.repositories.project_repository import ProjectRepository


class GetProjectUseCase:
    """Use case for retrieving a project by ID"""

    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository

    def _build_git_branchs_dict(self, git_branchs: dict, logger) -> dict[str, Any]:
        """Build git branches dictionary with proper error handling"""
        result = {}

        for tree_id, tree in git_branchs.items():
            try:
                logger.info(f"Processing branch {tree_id}, type: {type(tree)}")

                # Check if tree.status exists
                if hasattr(tree, 'status'):
                    logger.info(f"Branch {tree_id} has status attribute: {tree.status}")
                else:
                    logger.warning(f"Branch {tree_id} does NOT have status attribute")

                # Try to get tree_status
                try:
                    tree_status = tree.get_tree_status()
                    logger.info(f"Branch {tree_id} tree_status type: {type(tree_status)}")
                except Exception as status_err:
                    logger.error(f"Error getting tree_status for branch {tree_id}: {status_err}", exc_info=True)
                    tree_status = {"status_breakdown": {}}

                result[tree_id] = {
                    "id": tree.id,
                    "project_id": tree.project_id,  # Required by BranchDTO
                    "name": tree.name,
                    "git_branch_name": tree.git_branch_name if hasattr(tree, 'git_branch_name') and tree.git_branch_name else tree.name,  # Required by BranchDTO
                    "description": tree.description,
                    "created_at": tree.created_at.isoformat(),
                    "updated_at": tree.updated_at.isoformat() if hasattr(tree, 'updated_at') else tree.created_at.isoformat(),
                    "status": str(tree.status) if hasattr(tree, 'status') else "active",  # Required by BranchDTO
                    # Complete branch statistics (matching standalone branch endpoint)
                    "task_count": tree.get_task_count(),
                    "completed_tasks": tree.get_completed_task_count(),
                    "in_progress_tasks": tree.get_active_task_count(),
                    "blocked_tasks": tree_status["status_breakdown"].get("blocked", 0),
                    "todo_tasks": tree_status["status_breakdown"].get("todo", 0),
                    "progress_percentage": tree.get_progress_percentage()
                }
            except Exception as e:
                logger.error(f"Error processing branch {tree_id}: {e}", exc_info=True)
                # Return minimal branch info on error
                result[tree_id] = {
                    "id": str(tree_id),
                    "project_id": getattr(tree, 'project_id', ''),
                    "name": getattr(tree, 'name', 'unknown'),
                    "git_branch_name": getattr(tree, 'name', 'unknown'),
                    "description": "",
                    "created_at": "",
                    "updated_at": "",
                    "status": "active",
                    "task_count": 0,
                    "completed_tasks": 0,
                    "in_progress_tasks": 0,
                    "blocked_tasks": 0,
                    "todo_tasks": 0,
                    "progress_percentage": 0
                }

        return result
    
    async def execute(self, project_id: str) -> dict[str, Any]:
        """Execute the get project use case"""

        import logging
        logger = logging.getLogger(__name__)

        try:
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
            logger.info(f"🔍 GET_PROJECT DEBUG: project_id={project_id}")
            logger.info(f"🔍 branch_count={branch_count}, task_count={task_count}")
            logger.info(f"🔍 project.git_branchs keys: {list(project.git_branchs.keys())}")
            for tree_id, tree in project.git_branchs.items():
                logger.info(f"🔍 Branch {tree_id}: type={type(tree)}, all_tasks count={len(tree.all_tasks)}, get_task_count()={tree.get_task_count()}")
        except Exception as e:
            logger.error(f"Error calculating project aggregations: {e}", exc_info=True)
            raise

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
                "git_branchs": self._build_git_branchs_dict(project.git_branchs, logger),
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