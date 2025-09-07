"""Template Controller - Modular Implementation"""

from typing import Dict, Any, Optional
import logging

from ....application.use_cases.template_use_cases import TemplateUseCases
from .factories.template_controller_factory import TemplateControllerFactory

logger = logging.getLogger(__name__)


class TemplateController:
    """Template controller handling HTTP requests and responses"""
    
    def __init__(self, template_use_cases: TemplateUseCases):
        self.template_use_cases = template_use_cases
        self._factory = TemplateControllerFactory(template_use_cases)
        logger.info("TemplateController initialized with modular architecture")
    
    async def create_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new template"""
        return await self._factory.create_template(request_data)
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get template by ID"""
        return await self._factory.get_template(template_id)
    
    async def update_template(self, template_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing template"""
        return await self._factory.update_template(template_id, request_data)
    
    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete template"""
        return await self._factory.delete_template(template_id)
    
    async def list_templates(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """List templates with filtering and pagination"""
        return await self._factory.list_templates(request_params)
    
    async def render_template(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Render template with variables"""
        return await self._factory.render_template(request_data)
    
    async def suggest_templates(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest templates based on context"""
        return await self._factory.suggest_templates(request_data)
    
    async def validate_template(self, template_id: str) -> Dict[str, Any]:
        """Validate template"""
        return await self._factory.validate_template(template_id)
    
    async def get_template_analytics(self, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template analytics"""
        return await self._factory.get_template_analytics(template_id)
    
    # Legacy method compatibility
    def _response_dto_to_dict(self, dto) -> Dict[str, Any]:
        """Convert response DTO to dictionary (legacy method)"""
        return self._factory.get_crud_handler()._response_dto_to_dict(dto)