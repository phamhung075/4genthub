"""Project Health Check Use Case"""

from typing import Dict, Any, Optional
from ...domain.repositories.project_repository import ProjectRepository


class ProjectHealthCheckUseCase:
    """Use case for performing health checks on projects"""
    
    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository
    
    async def execute(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the project health check use case"""
        
        if project_id:
            # Check specific project
            project = await self._project_repository.find_by_id(project_id)
            
            if not project:
                return {
                    "success": False,
                    "error": f"Project with ID '{project_id}' not found"
                }
            
            health_status = self._check_project_health(project)
            
            return {
                "success": True,
                "project_id": project_id,
                "health_status": health_status,
                "message": f"Health check completed for project '{project_id}'"
            }
        
        else:
            # Check all projects
            projects = await self._project_repository.find_all()
            health_results = {}
            overall_health = "healthy"
            
            for project in projects:
                health_status = self._check_project_health(project)
                health_results[project.id] = health_status
                
                if health_status["status"] != "healthy":
                    overall_health = "warning"
            
            return {
                "success": True,
                "overall_health": overall_health,
                "project_health": health_results,
                "total_projects": len(projects),
                "message": "Health check completed for all projects"
            }
    
    def _check_project_health(self, project) -> Dict[str, Any]:
        """Check health of a single project"""
        from datetime import datetime, timezone
        
        issues = []
        warnings = []
        
        # Check for task trees
        if not project.git_branchs:
            warnings.append("No task trees defined")
        
        # Check for circular dependencies in cross-tree dependencies
        if project.cross_tree_dependencies:
            if self._has_circular_dependencies(project.cross_tree_dependencies):
                issues.append("Circular dependencies detected in cross-tree dependencies")
        
        # Check agent assignments
        for git_branch_name, agent_id in project.agent_assignments.items():
            if agent_id not in project.registered_agents:
                issues.append(f"Agent '{agent_id}' assigned to tree '{git_branch_name}' but not registered")
            
            if git_branch_name not in project.git_branchs:
                issues.append(f"Agent '{agent_id}' assigned to non-existent tree '{git_branch_name}'")
        
        # Check for orphaned work sessions
        for session_id, session in project.active_work_sessions.items():
            if session.agent_id not in project.registered_agents:
                issues.append(f"Active work session '{session_id}' references unregistered agent '{session.agent_id}'")
        
        # Check for resource locks
        for resource, agent_id in project.resource_locks.items():
            if agent_id not in project.registered_agents:
                issues.append(f"Resource '{resource}' locked by unregistered agent '{agent_id}'")
        
        # Determine overall status
        if issues:
            status = "critical"
        elif warnings:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "git_branchs_count": len(project.git_branchs),
            "registered_agents_count": len(project.registered_agents),
            "active_assignments": len(project.agent_assignments),
            "active_sessions": len(project.active_work_sessions),
            "cross_tree_dependencies": sum(len(deps) for deps in project.cross_tree_dependencies.values())
        }
    
    def _has_circular_dependencies(self, dependencies: Dict[str, set]) -> bool:
        """Check for circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            if node in rec_stack:
                return True  # Circular dependency found
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, set()):
                if dfs(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False