"""Suggestion Handler for Template Controller"""

import logging
from typing import Dict, Any

from .....application.use_cases.template_use_cases import TemplateUseCases
from .....application.dtos.template_dtos import (
    TemplateSuggestionRequestDTO
)

logger = logging.getLogger(__name__)


class SuggestionHandler:
    """Handler for template suggestion operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
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