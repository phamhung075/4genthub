"""Validation Service for Template Controller"""

import logging
from typing import Dict, Any

from .....application.use_cases.template_use_cases import TemplateUseCases

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for template validation operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
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