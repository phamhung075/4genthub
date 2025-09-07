"""Template Controller Factory"""

import logging
from typing import Dict, Any, Optional

from .....application.use_cases.template_use_cases import TemplateUseCases
from ..handlers.crud_handler import CrudHandler
from ..handlers.search_handler import SearchHandler
from ..handlers.render_handler import RenderHandler
from ..handlers.suggestion_handler import SuggestionHandler
from ..services.analytics_service import AnalyticsService
from ..services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class TemplateControllerFactory:
    """Factory for creating and managing Template Controller components"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
        self._crud_handler = None
        self._search_handler = None
        self._render_handler = None
        self._suggestion_handler = None
        self._analytics_service = None
        self._validation_service = None
        logger.info("TemplateControllerFactory initialized")
    
    def get_crud_handler(self) -> CrudHandler:
        """Get or create CRUD handler"""
        if self._crud_handler is None:
            self._crud_handler = CrudHandler(self.template_use_cases)
        return self._crud_handler
    
    def get_search_handler(self) -> SearchHandler:
        """Get or create search handler"""
        if self._search_handler is None:
            self._search_handler = SearchHandler(self.template_use_cases)
        return self._search_handler
    
    def get_render_handler(self) -> RenderHandler:
        """Get or create render handler"""
        if self._render_handler is None:
            self._render_handler = RenderHandler(self.template_use_cases)
        return self._render_handler
    
    def get_suggestion_handler(self) -> SuggestionHandler:
        """Get or create suggestion handler"""
        if self._suggestion_handler is None:
            self._suggestion_handler = SuggestionHandler(self.template_use_cases)
        return self._suggestion_handler
    
    def get_analytics_service(self) -> AnalyticsService:
        """Get or create analytics service"""
        if self._analytics_service is None:
            self._analytics_service = AnalyticsService(self.template_use_cases)
        return self._analytics_service
    
    def get_validation_service(self) -> ValidationService:
        """Get or create validation service"""
        if self._validation_service is None:
            self._validation_service = ValidationService(self.template_use_cases)
        return self._validation_service
    
    # Unified operation methods
    async def create_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new template"""
        return await self.get_crud_handler().create_template(request_data)
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template by ID"""
        return await self.get_crud_handler().get_template(template_id)
    
    async def update_template(self, template_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing template"""
        return await self.get_crud_handler().update_template(template_id, request_data)
    
    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete template"""
        return await self.get_crud_handler().delete_template(template_id)
    
    async def list_templates(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """List templates with filtering and pagination"""
        return await self.get_search_handler().list_templates(request_params)
    
    async def render_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render template with variables"""
        return await self.get_render_handler().render_template(request_data)
    
    async def suggest_templates(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest templates based on context"""
        return await self.get_suggestion_handler().suggest_templates(request_data)
    
    async def validate_template(self, template_id: str) -> Dict[str, Any]:
        """Validate template"""
        return await self.get_validation_service().validate_template(template_id)
    
    async def get_template_analytics(self, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template analytics"""
        return await self.get_analytics_service().get_template_analytics(template_id)