"""Analytics Service for Template Controller"""

import logging
from typing import Dict, Any, Optional

from .....application.use_cases.template_use_cases import TemplateUseCases

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for template analytics operations"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
    
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