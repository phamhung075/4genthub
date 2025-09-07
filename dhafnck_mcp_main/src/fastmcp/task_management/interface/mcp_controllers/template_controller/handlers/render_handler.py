"""Render Handler for Template Controller"""

import logging
from typing import Dict, Any

from .....application.use_cases.template_use_cases import TemplateUseCases
from .....application.dtos.template_dtos import (
    TemplateRenderRequestDTO
)

logger = logging.getLogger(__name__)


class RenderHandler:
    """Handler for template rendering operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
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