"""Template Repository Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from ..entities.template import Template, TemplateUsage
from ..value_objects.template_id import TemplateId


class TemplateRepositoryInterface(ABC):
    """Template repository interface defining contract for template persistence"""
    
    @abstractmethod
    async def save(self, template: Template) -> Template:
        """Save template to storage"""
        pass
    
    @abstractmethod
    async def get_by_id(self, template_id: TemplateId) -> Optional[Template]:
        """Get template by ID"""
        pass
    
    @abstractmethod
    async def list_templates(
        self,
        template_type: Optional[str] = None,
        category: Optional[str] = None,
        agent_compatible: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Template], int]:
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
    async def get_usage_stats(self, template_id: TemplateId) -> Dict[str, Any]:
        """Get usage statistics for template"""
        pass
    
    @abstractmethod
    async def get_analytics(self, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Get template analytics"""
        pass 