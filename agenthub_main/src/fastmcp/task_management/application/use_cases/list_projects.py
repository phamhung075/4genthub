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
        
        import logging
        logger = logging.getLogger(__name__)
        
        project_list = []
        for project in projects:
            try:
                # Calculate project-level aggregations (same as GetProjectUseCase)
                branch_count = len(project.git_branchs)
                task_count = sum(tree.get_task_count() for tree in project.git_branchs.values())
            except Exception as e:
                logger.error(f"Error calculating project aggregations for {project.name}: {e}")
                # Fallback to zero if calculation fails
                branch_count = 0
                task_count = 0

            project_info = {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "branch_count": branch_count,  # Total branches in project
                "task_count": task_count,      # Total tasks across all branches
                "registered_agents_count": len(project.registered_agents),
                "active_assignments": len(project.agent_assignments),
                "active_sessions": len(project.active_work_sessions)
            }

            # Include full git branch data to eliminate N+1 queries in frontend
            if include_branches and project.git_branchs:
                git_branchs_dict = {}
                # Iterate over the values (GitBranch objects), not the keys
                for branch_id, branch in project.git_branchs.items():
                    # Calculate branch statistics directly from all_tasks
                    # (Same logic as GitBranch methods but inline to avoid potential issues)
                    branch_task_count = len(branch.all_tasks)

                    # Count by status
                    branch_completed = sum(1 for t in branch.all_tasks.values() if isinstance(t, dict) and t.get("status") == "done")
                    branch_in_progress = sum(1 for t in branch.all_tasks.values() if isinstance(t, dict) and t.get("status") == "in_progress")
                    branch_blocked = sum(1 for t in branch.all_tasks.values() if isinstance(t, dict) and t.get("status") == "blocked")
                    branch_todo = sum(1 for t in branch.all_tasks.values() if isinstance(t, dict) and t.get("status") == "todo")

                    # Calculate progress percentage
                    branch_progress = int((branch_completed / branch_task_count * 100) if branch_task_count > 0 else 0)

                    git_branchs_dict[branch_id] = {
                        "id": str(branch.id),
                        "project_id": branch.project_id,  # Required by BranchDTO
                        "name": branch.name,
                        "git_branch_name": branch.git_branch_name if hasattr(branch, 'git_branch_name') and branch.git_branch_name else branch.name,  # Required by BranchDTO
                        "description": branch.description if hasattr(branch, 'description') else "",
                        "created_at": branch.created_at.isoformat() if hasattr(branch, 'created_at') else "",
                        "updated_at": branch.updated_at.isoformat() if hasattr(branch, 'updated_at') else "",
                        "status": str(branch.status) if hasattr(branch, 'status') else "active",
                        # Complete branch statistics (matching standalone branch endpoint and GetProjectUseCase)
                        "task_count": branch_task_count,
                        "completed_tasks": branch_completed,
                        "in_progress_tasks": branch_in_progress,
                        "blocked_tasks": branch_blocked,
                        "todo_tasks": branch_todo,
                        "progress_percentage": branch_progress,
                        "agent_assignments": len(branch.agent_assignments) if hasattr(branch, 'agent_assignments') else 0
                    }
                project_info["git_branchs"] = git_branchs_dict
            
            project_list.append(project_info)
        
        return {
            "success": True,
            "projects": project_list,
            "count": len(project_list)
        }