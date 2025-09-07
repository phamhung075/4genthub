"""Template Controller - Interface Layer"""

from typing import Dict, Any, List, Optional
import logging

from ...application.use_cases.template_use_cases import TemplateUseCases
from ...application.dtos.template_dtos import (
    TemplateCreateDTO, TemplateUpdateDTO, TemplateResponseDTO, TemplateListDTO,
    TemplateRenderRequestDTO, TemplateRenderResponseDTO, TemplateSuggestionDTO,
    TemplateSuggestionRequestDTO, TemplateSearchDTO, TemplateValidationDTO,
    TemplateAnalyticsDTO
)

logger = logging.getLogger(__name__)


class TemplateController:
    """Template controller handling HTTP requests and responses"""
    
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
    
    async def render_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render template with variables"""
        try:
            render_dto = TemplateRenderRequestDTO(
                template_id=request_data['template_id'],
                variables=request_data['variables'],
                task_context=request_data.get('task_context'),
                output_path=request_data.get('output_path'),
                cache_strategy=request_data.get('cache_strategy', 'default'),
                force_regenerate=request_data.get('force_regenerate', False)
            )
            
            result = await self.template_use_cases.render_template(render_dto)
            
            return {
                "success": True,
                "result": {
                    "content": result.content,
                    "template_id": result.template_id,
                    "variables_used": result.variables_used,
                    "generated_at": result.generated_at,
                    "generation_time_ms": result.generation_time_ms,
                    "cache_hit": result.cache_hit,
                    "output_path": result.output_path
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def suggest_templates(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest templates based on context"""
        try:
            suggestion_dto = TemplateSuggestionRequestDTO(
                task_context=request_data['task_context'],
                agent_type=request_data.get('agent_type'),
                file_patterns=request_data.get('file_patterns'),
                limit=int(request_data.get('limit', 10))
            )
            
            suggestions = await self.template_use_cases.suggest_templates(suggestion_dto)
            
            return {
                "success": True,
                "suggestions": [
                    {
                        "template_id": s.template_id,
                        "name": s.name,
                        "description": s.description,
                        "template_type": s.template_type,
                        "category": s.category,
                        "priority": s.priority,
                        "suggestion_score": s.suggestion_score,
                        "suggestion_reason": s.suggestion_reason,
                        "compatible_agents": s.compatible_agents,
                        "file_patterns": s.file_patterns,
                        "variables": s.variables
                    } for s in suggestions
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to suggest templates: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_template(self, template_id: str) -> Dict[str, Any]:
        """Validate template"""
        try:
            result = await self.template_use_cases.validate_template(template_id)
            
            return {
                "success": True,
                "validation": {
                    "is_valid": result.is_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "template_id": result.template_id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to validate template {template_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_template_analytics(self, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template analytics"""
        try:
            result = await self.template_use_cases.get_template_analytics(template_id)
            
            return {
                "success": True,
                "analytics": {
                    "template_id": result.template_id,
                    "usage_count": result.usage_count,
                    "success_rate": result.success_rate,
                    "avg_generation_time": result.avg_generation_time,
                    "total_generation_time": result.total_generation_time,
                    "cache_hit_rate": result.cache_hit_rate,
                    "most_used_variables": result.most_used_variables,
                    "usage_by_agent": result.usage_by_agent,
                    "usage_by_project": result.usage_by_project,
                    "usage_over_time": result.usage_over_time
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get template analytics: {e}")
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