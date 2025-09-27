"""
Use Case: Rebalance Agents
"""
from typing import Dict, Any
from ...domain.repositories.project_repository import ProjectRepository

class RebalanceAgentsUseCase:
    def __init__(self, project_repo: ProjectRepository):
        self._project_repo = project_repo

    async def execute(self, project_id: str = None) -> Dict[str, Any]:
        """Rebalance agent assignments across task trees"""
        try:
            if project_id:
                project = await self._project_repo.find_by_id(project_id)
                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}
                
                rebalance_result = self._rebalance_project_agents(project)
                
                if rebalance_result["changes_made"]:
                    await self._project_repo.update(project)
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "rebalance_result": rebalance_result,
                    "message": f"Agent rebalancing completed for project {project_id}"
                }
            else:
                projects = await self._project_repo.find_all()
                total_changes = 0
                rebalance_results = {}
                
                for project in projects:
                    rebalance_result = self._rebalance_project_agents(project)
                    rebalance_results[project.id] = rebalance_result
                    if rebalance_result["changes_made"]:
                        total_changes += len(rebalance_result["changes"])
                        await self._project_repo.update(project)
                
                return {
                    "success": True,
                    "total_changes": total_changes,
                    "rebalance_results": rebalance_results,
                    "message": f"Agent rebalancing completed for all projects. {total_changes} changes made"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _rebalance_project_agents(self, project) -> Dict[str, Any]:
        """Rebalance agents across task trees in a project entity"""
        changes = []
        
        available_agents = list(project.registered_agents.keys())
        unassigned_trees = []
        
        for tree_id in project.git_branchs.keys():
            has_agent = any(assigned_tree == tree_id for assigned_tree in project.agent_assignments.values())
            if not has_agent:
                unassigned_trees.append(tree_id)
        
        for i, tree_id in enumerate(unassigned_trees):
            if i < len(available_agents):
                agent_id = available_agents[i]
                if agent_id not in project.agent_assignments:
                    project.agent_assignments[agent_id] = tree_id
                    changes.append(f"Assigned agent {agent_id} to tree {tree_id}")
        
        return {
            "changes_made": len(changes) > 0,
            "changes": changes
        } 