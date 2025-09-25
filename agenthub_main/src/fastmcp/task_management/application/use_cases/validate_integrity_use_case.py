"""
Use Case: Validate Project Integrity
"""
from typing import Dict, Any
from ...domain.repositories.project_repository import ProjectRepository

class ValidateIntegrityUseCase:
    def __init__(self, project_repo: ProjectRepository):
        self._project_repo = project_repo

    async def execute(self, project_id: str = None) -> Dict[str, Any]:
        """Validate integrity of project data"""
        try:
            if project_id:
                project = await self._project_repo.find_by_id(project_id)
                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}
                
                validation_result = self._validate_project_integrity(project)
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "validation_result": validation_result,
                    "message": f"Integrity validation completed for project {project_id}"
                }
            else:
                projects = await self._project_repo.find_all()
                validation_results = {}
                overall_valid = True
                
                for project in projects:
                    validation_result = self._validate_project_integrity(project)
                    validation_results[project.id] = validation_result
                    
                    if not validation_result["is_valid"]:
                        overall_valid = False
                
                return {
                    "success": True,
                    "overall_valid": overall_valid,
                    "validation_results": validation_results,
                    "total_projects": len(projects),
                    "message": "Integrity validation completed for all projects"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_project_integrity(self, project) -> Dict[str, Any]:
        """Validate integrity of a single project entity"""
        errors = []
        warnings = []
        
        # Validate basic structure
        if not project.id:
            errors.append("Project missing ID")
        if not project.name:
            errors.append("Project missing name")
        
        # Validate task trees
        for tree_id, tree in project.git_branchs.items():
            if not tree.name:
                errors.append(f"Task tree {tree_id} missing name")
            if tree.project_id != project.id:
                errors.append(f"Task tree {tree_id} has incorrect project_id")
        
        # Validate agent assignments
        for agent_id, tree_id in project.agent_assignments.items():
            if agent_id not in project.registered_agents:
                errors.append(f"Agent {agent_id} assigned but not registered")
            if tree_id not in project.git_branchs:
                errors.append(f"Agent {agent_id} assigned to non-existent tree {tree_id}")
        
        # Validate registered agents
        for agent_id, agent in project.registered_agents.items():
            if not agent.name:
                warnings.append(f"Agent {agent_id} missing name")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        } 