"""CRUD Handler for Template Controller"""

import logging
from typing import Dict, Any

from .....application.use_cases.template_use_cases import TemplateUseCases
from .....application.dtos.template_dtos import (
    TemplateCreateDTO, TemplateUpdateDTO, TemplateResponseDTO
)

logger = logging.getLogger(__name__)


class CrudHandler:
    """Handler for template CRUD operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
    async def create_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new template"""
        try:
            create_dto = TemplateCreateDTO(
                name=request_data['name'],
                description=request_data['description'],
                content=request_data['content'],
                template_type=request_data['template_type'],
                category=request_data['category'],
                priority=request_data.get('priority', 'medium'),
                compatible_agents=request_data.get('compatible_agents', ['*']),
                file_patterns=request_data.get('file_patterns', []),
                variables=request_data.get('variables', []),
                metadata=request_data.get('metadata', {})
            )
            
            result = await self.template_use_cases.create_template(create_dto)
            
            return {
                "success": True,
                "template": self._response_dto_to_dict(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template by ID"""
        try:
            result = await self.template_use_cases.get_template(template_id)
            
            return {
                "success": True,
                "template": self._response_dto_to_dict(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_template(self, template_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing template"""
        try:
            update_dto = TemplateUpdateDTO(
                template_id=template_id,
                name=request_data.get('name'),
                description=request_data.get('description'),
                content=request_data.get('content'),
                template_type=request_data.get('template_type'),
                category=request_data.get('category'),
                priority=request_data.get('priority'),
                compatible_agents=request_data.get('compatible_agents'),
                file_patterns=request_data.get('file_patterns'),
                variables=request_data.get('variables'),
                metadata=request_data.get('metadata'),
                is_active=request_data.get('is_active')
            )
            
            result = await self.template_use_cases.update_template(update_dto)
            
            return {
                "success": True,
                "template": self._response_dto_to_dict(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to update template {template_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete template"""
        try:
            success = await self.template_use_cases.delete_template(template_id)
            
            return {
                "success": success,
                "message": "Template deleted successfully" if success else "Failed to delete template"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _response_dto_to_dict(self, dto: TemplateResponseDTO) -> Dict[str, Any]:
        """Convert response DTO to dictionary"""
        return {
            "id": dto.id,
            "name": dto.name,
            "description": dto.description,
            "content": dto.content,
            "template_type": dto.template_type,
            "category": dto.category,
            "status": dto.status,
            "priority": dto.priority,
            "compatible_agents": dto.compatible_agents,
            "file_patterns": dto.file_patterns,
            "variables": dto.variables,
            "metadata": dto.metadata,
            "created_at": dto.created_at,
            "updated_at": dto.updated_at,
            "version": dto.version,
            "is_active": dto.is_active
        }