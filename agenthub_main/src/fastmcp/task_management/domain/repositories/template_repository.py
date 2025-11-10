"""Template Repository Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any

from ..entities.template import Template, TemplateUsage
from ..value_objects.template_id import TemplateId


class TemplateRepositoryInterface(ABC):
    """Template repository interface defining contract for template persistence"""
    
    @abstractmethod
    async def save(self, template: Template) -> Template:
        """Save template to storage"""
        pass
    
    @abstractmethod
    async def get_by_id(self, template_id: TemplateId) -> Template | None:
        """Get template by ID"""
        pass
    
    @abstractmethod
    async def list_templates(
        self,
        template_type: str | None = None,
        category: str | None = None,
        agent_compatible: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Template], int]:
        """List templates with filtering and pagination"""
        pass
    
    @abstractmethod
    async def delete(self, template_id: TemplateId) -> bool:
        """Delete template"""
        pass
    
    @abstractmethod
    async def save_usage(self, usage: TemplateUsage) -> bool:
        """Save template usage record"""
        pass
    
    @abstractmethod
    async def get_usage_stats(self, template_id: TemplateId) -> dict[str, Any]:
        """Get usage statistics for template"""
        pass
    
    @abstractmethod
    async def get_analytics(self, template_id: str | None = None) -> dict[str, Any]:
        """Get template analytics"""
        pass 