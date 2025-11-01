"""
Agent Management Application Facade

This facade orchestrates agent-related operations for MCP controllers,
coordinating between domain services and repositories to provide a
high-level API for agent instantiation and retrieval.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ...domain.entities.agent_template import AgentTemplate
from ...domain.entities.user_agent_instance import UserAgentInstance
from ...domain.value_objects.user_id import UserId
from ...domain.services.agent_instantiation_service import AgentInstantiationService
from ...infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository
)

logger = logging.getLogger(__name__)


class AgentManagementFacade:
    """
    Application facade for agent management operations.

    Orchestrates domain services and repositories to provide high-level
    operations for MCP controllers, including:
    - Auto-creating user agent instances from templates
    - Retrieving agent configurations for execution
    - Tracking agent usage
    """

    def __init__(
        self,
        template_repository: Optional[ORMAgentTemplateRepository] = None,
        instance_repository: Optional[ORMUserAgentInstanceRepository] = None,
        instantiation_service: Optional[AgentInstantiationService] = None
    ):
        """
        Initialize the facade with repositories and services.

        Args:
            template_repository: Repository for agent templates
            instance_repository: Repository for user agent instances
            instantiation_service: Domain service for agent instantiation
        """
        self._template_repo = template_repository or ORMAgentTemplateRepository()
        self._instance_repo = instance_repository or ORMUserAgentInstanceRepository()
        self._instantiation_service = instantiation_service or AgentInstantiationService(
            template_repository=self._template_repo
        )

    def get_or_create_instance(
        self,
        user_id: UserId,
        agent_slug: str
    ) -> UserAgentInstance:
        """
        Get or create a user agent instance for the specified user and agent.

        This method:
        1. Checks if user already has an instance of this agent
        2. If not, auto-creates one from the template
        3. Returns the user's instance (existing or newly created)

        Args:
            user_id: User identifier
            agent_slug: Agent template slug (e.g., "coding-agent")

        Returns:
            UserAgentInstance for the user

        Raises:
            ValueError: If agent template not found
        """
        logger.info(f"Getting or creating instance for user={user_id.value}, agent={agent_slug}")

        # Check if user already has this agent instance
        existing_instance = self._instance_repo.find_by_user_and_template_slug(
            user_id=user_id,
            template_slug=agent_slug
        )

        if existing_instance:
            logger.info(f"Found existing instance: {existing_instance.id.value}")
            return existing_instance

        # Create new instance using domain service
        logger.info(f"Creating new instance for user={user_id.value}, agent={agent_slug}")
        new_instance = self._instantiation_service.create_instance_from_template(
            user_id=user_id,
            template_slug=agent_slug
        )

        # Persist the new instance
        self._instance_repo.save(new_instance)
        logger.info(f"Instance created and saved: {new_instance.id.value}")

        return new_instance

    def get_agent_for_call(
        self,
        user_id: UserId,
        agent_slug: str
    ) -> Dict[str, Any]:
        """
        Get agent configuration for MCP call_agent tool.

        This method:
        1. Gets or creates user's agent instance
        2. Extracts configuration for execution
        3. Tracks usage (last_used timestamp)
        4. Returns formatted data for MCP response

        Args:
            user_id: User identifier
            agent_slug: Agent template slug

        Returns:
            Dictionary with agent configuration:
            {
                "name": str,
                "slug": str,
                "description": str,
                "system_prompt": str,
                "tools": List[str],
                "capabilities": Dict[str, Any],
                "rules": Optional[List[str]],
                "output_format": Optional[str],
                "category": str,
                "version": str,
                "is_customized": bool,
                "instance_id": str,
                "template_id": str,
                "metadata": Dict[str, Any]
            }

        Raises:
            ValueError: If agent template not found
        """
        logger.info(f"Getting agent configuration for call: user={user_id.value}, agent={agent_slug}")

        # Get or create user instance
        instance = self.get_or_create_instance(user_id, agent_slug)

        # Update last_used timestamp
        instance.track_usage()
        self._instance_repo.save(instance)

        # Get template for metadata
        template = self._template_repo.find_by_slug(agent_slug)
        if not template:
            raise ValueError(f"Agent template not found: {agent_slug}")

        # Build response using instance's configuration
        config = instance.configuration

        return {
            "name": instance.agent_name or template.name,
            "slug": template.slug,
            "description": template.description,
            "system_prompt": config.system_prompt,
            "tools": list(config.tools),  # Convert tuple to list for JSON serialization
            "capabilities": config.capabilities or {},
            "rules": list(config.rules) if config.rules else [],  # Convert tuple to list
            "output_format": config.output_format,
            "category": template.category,
            "version": template.version,
            "is_customized": instance.is_customized,
            "instance_id": instance.id.value,
            "template_id": template.id.value,
            "metadata": {
                **template.metadata,
                "created_at": instance.created_at.isoformat(),
                "last_used": instance.last_used_at.isoformat() if instance.last_used_at else None,
                "customizations": instance.metadata.get("customizations", {})
            }
        }

    def get_user_instances(self, user_id: UserId) -> list[UserAgentInstance]:
        """
        Get all agent instances for a user.

        Args:
            user_id: User identifier

        Returns:
            List of user's agent instances
        """
        return self._instance_repo.find_all_by_user(user_id)

    def get_template_by_slug(self, agent_slug: str) -> Optional[AgentTemplate]:
        """
        Get agent template by slug.

        Args:
            agent_slug: Agent template slug

        Returns:
            AgentTemplate if found, None otherwise
        """
        return self._template_repo.find_by_slug(agent_slug)

    def list_available_templates(self) -> list[AgentTemplate]:
        """
        List all available agent templates.

        Returns:
            List of all agent templates in the system
        """
        return self._template_repo.find_all()
