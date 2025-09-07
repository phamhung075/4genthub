"""Search Handler for Template Controller"""

import logging
from typing import Dict, Any

from .....application.use_cases.template_use_cases import TemplateUseCases
from .....application.dtos.template_dtos import (
    TemplateSearchDTO, TemplateResponseDTO
)

logger = logging.getLogger(__name__)


class SearchHandler:
    """Handler for template search operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
    async def list_templates(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """List templates with filtering and pagination"""
        try:
            search_dto = TemplateSearchDTO(
                query=request_params.get('query', ''),
                template_type=request_params.get('template_type'),
                category=request_params.get('category'),
                agent_compatible=request_params.get('agent_compatible'),
                is_active=request_params.get('is_active'),
                limit=int(request_params.get('limit', 50)),
                offset=int(request_params.get('offset', 0))
            )
            
            result = await self.template_use_cases.list_templates(search_dto)
            
            return {
                "success": True,
                "templates": [self._response_dto_to_dict(t) for t in result.templates],
                "pagination": {
                    "total_count": result.total_count,
                    "page": result.page,
                    "page_size": result.page_size,
                    "has_next": result.has_next,
                    "has_previous": result.has_previous
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
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