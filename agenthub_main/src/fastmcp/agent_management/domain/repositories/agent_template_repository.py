"""AgentTemplateRepository - Repository interface for AgentTemplate aggregate"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities.agent_template import AgentTemplate
from ..value_objects.agent_template_id import AgentTemplateId


class AgentTemplateRepository(ABC):
    """Repository interface for AgentTemplate persistence.

    Following DDD patterns, this interface lives in the domain layer
    while implementations live in the infrastructure layer.
    """

    @abstractmethod
    def save(self, template: AgentTemplate) -> AgentTemplate:
        """Save or update an agent template.

        Args:
            template: The template to save

        Returns:
            The saved template with updated timestamps
        """
        pass

    @abstractmethod
    def find_by_id(self, template_id: AgentTemplateId) -> Optional[AgentTemplate]:
        """Find a template by its ID.

        Args:
            template_id: The template ID to search for

        Returns:
            The template if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_slug(self, slug: str) -> Optional[AgentTemplate]:
        """Find a template by its slug.

        Args:
            slug: The template slug to search for

        Returns:
            The template if found, None otherwise
        """
        pass

    @abstractmethod
    def find_all(self) -> List[AgentTemplate]:
        """Get all agent templates.

        Returns:
            List of all templates
        """
        pass

    @abstractmethod
    def find_by_category(self, category: str) -> List[AgentTemplate]:
        """Find templates by category.

        Args:
            category: The category to filter by

        Returns:
            List of templates in the category
        """
        pass

    @abstractmethod
    def exists_by_slug(self, slug: str) -> bool:
        """Check if a template with the given slug exists.

        Args:
            slug: The slug to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, template_id: AgentTemplateId) -> None:
        """Delete a template by ID.

        Args:
            template_id: The template ID to delete
        """
        pass
