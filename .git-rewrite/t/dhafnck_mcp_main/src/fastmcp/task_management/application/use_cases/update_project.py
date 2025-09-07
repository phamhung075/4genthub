"""Update Project Use Case"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from ...domain.repositories.project_repository import ProjectRepository


class UpdateProjectUseCase:
    """Use case for updating a project"""
    
    def __init__(self, project_repository: ProjectRepository):
        self._project_repository = project_repository
    
    async def execute(self, project_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Execute the update project use case"""
        
        project = await self._project_repository.find_by_id(project_id)
        
        if not project:
            return {
                "success": False,
                "error": f"Project with ID '{project_id}' not found"
            }
        
        updated_fields = []
        
        if name is not None:
            project.name = name
            updated_fields.append("name")
        
        if description is not None:
            project.description = description
            updated_fields.append("description")
        
        if not updated_fields:
            return {
                "success": False,
                "error": "No fields to update. Provide name and/or description."
            }
        
        # Update timestamp
        project.updated_at = datetime.now(timezone.utc)
        
        # Save to repository
        await self._project_repository.update(project)
        
        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            },
            "updated_fields": updated_fields,
            "message": f"Project '{project_id}' updated successfully"
        }