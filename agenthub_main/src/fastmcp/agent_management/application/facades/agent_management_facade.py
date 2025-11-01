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
            template_repository=self._template_repo,
            instance_repository=self._instance_repo
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

        # Delegate to domain service - no logic duplication
        instance = self._instantiation_service.get_or_create_instance(
            user_id=user_id,
            template_slug=agent_slug
        )

        if not instance:
            raise ValueError(f"Agent template not found: {agent_slug}")

        logger.info(f"Instance ready: {instance.id.value}")
        return instance

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

    def update_instance(
        self,
        user_id: UserId,
        instance_id: str,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[list[str]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        rules: Optional[list[str]] = None,
        output_format: Optional[str] = None,
        visibility: Optional[str] = None
    ) -> UserAgentInstance:
        """
        Update a user agent instance.

        This method allows users to update their agent instance configuration
        and metadata. Only the instance owner can update their instances.

        Args:
            user_id: User identifier (must match instance owner)
            instance_id: Instance identifier to update
            agent_name: New custom name for instance (optional)
            system_prompt: New system prompt (optional)
            tools: New tools list (optional)
            capabilities: New capabilities dict (optional)
            rules: New rules list (optional)
            output_format: New output format (optional)
            visibility: New visibility ('private' or 'public', optional)

        Returns:
            Updated UserAgentInstance

        Raises:
            ValueError: If instance not found or user is not the owner
        """
        from ..value_objects.user_agent_instance_id import UserAgentInstanceId

        logger.info(f"Updating instance {instance_id} for user {user_id.value}")

        # Find instance
        instance_uuid = UserAgentInstanceId.from_string(instance_id)
        instance = self._instance_repo.find_by_id(instance_uuid)

        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.user_id != user_id:
            raise ValueError(f"Instance {instance_id} does not belong to user {user_id.value}")

        # Update agent name if provided
        if agent_name is not None:
            object.__setattr__(instance, 'agent_name', agent_name)

        # Update configuration if any config fields provided
        if any([system_prompt, tools, capabilities, rules, output_format]):
            current_config = instance.configuration

            # Create new configuration with updates
            new_config_dict = {
                "system_prompt": system_prompt if system_prompt is not None else current_config.system_prompt,
                "tools": tuple(tools) if tools is not None else current_config.tools,
                "capabilities": capabilities if capabilities is not None else current_config.capabilities,
                "rules": tuple(rules) if rules is not None else current_config.rules,
                "output_format": output_format if output_format is not None else current_config.output_format,
            }

            new_config = AgentConfiguration.from_dict(new_config_dict)
            instance.customize_configuration(new_config, "Updated via REST API")

        # Update visibility if provided
        if visibility is not None:
            if visibility not in ('private', 'public'):
                raise ValueError(f"Invalid visibility: {visibility}. Must be 'private' or 'public'")
            object.__setattr__(instance, 'visibility', visibility)

        # Save updates
        updated_instance = self._instance_repo.save(instance)
        logger.info(f"Instance {instance_id} updated successfully")

        return updated_instance

    def delete_instance(
        self,
        user_id: UserId,
        instance_id: str
    ) -> bool:
        """
        Delete a user agent instance.

        Only the instance owner can delete their instances.

        Args:
            user_id: User identifier (must match instance owner)
            instance_id: Instance identifier to delete

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If instance not found or user is not the owner
        """
        from ..value_objects.user_agent_instance_id import UserAgentInstanceId

        logger.info(f"Deleting instance {instance_id} for user {user_id.value}")

        # Find instance
        instance_uuid = UserAgentInstanceId.from_string(instance_id)
        instance = self._instance_repo.find_by_id(instance_uuid)

        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.user_id != user_id:
            raise ValueError(f"Instance {instance_id} does not belong to user {user_id.value}")

        # Delete instance
        result = self._instance_repo.delete(instance_uuid)

        if result:
            logger.info(f"Instance {instance_id} deleted successfully")
        else:
            logger.warning(f"Failed to delete instance {instance_id}")

        return result

    def update_configuration(
        self,
        user_id: UserId,
        agent_slug: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[str]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        rules: Optional[list[str]] = None,
        output_format: Optional[str] = None
    ) -> UserAgentInstance:
        """
        Update agent configuration for a user.

        This is a convenience method that gets or creates an instance and
        updates its configuration. Useful when you want to update by slug
        rather than instance ID.

        Args:
            user_id: User identifier
            agent_slug: Agent template slug
            system_prompt: New system prompt (optional)
            tools: New tools list (optional)
            capabilities: New capabilities dict (optional)
            rules: New rules list (optional)
            output_format: New output format (optional)

        Returns:
            Updated UserAgentInstance

        Raises:
            ValueError: If template not found
        """
        logger.info(f"Updating configuration for agent {agent_slug}, user {user_id.value}")

        # Get or create instance
        instance = self.get_or_create_instance(user_id, agent_slug)

        # Update configuration if any fields provided
        if any([system_prompt, tools, capabilities, rules, output_format]):
            current_config = instance.configuration

            # Create new configuration with updates
            new_config_dict = {
                "system_prompt": system_prompt if system_prompt is not None else current_config.system_prompt,
                "tools": tuple(tools) if tools is not None else current_config.tools,
                "capabilities": capabilities if capabilities is not None else current_config.capabilities,
                "rules": tuple(rules) if rules is not None else current_config.rules,
                "output_format": output_format if output_format is not None else current_config.output_format,
            }

            new_config = AgentConfiguration.from_dict(new_config_dict)
            instance.customize_configuration(new_config, "Updated configuration via REST API")

            # Save updates
            updated_instance = self._instance_repo.save(instance)
            logger.info(f"Configuration updated for {agent_slug}")
            return updated_instance

        # No updates provided, return existing instance
        return instance

    def reset_configuration(
        self,
        user_id: UserId,
        agent_slug: str
    ) -> UserAgentInstance:
        """
        Reset agent configuration to default template.

        This method resets a user's customized instance back to the
        default template configuration.

        Args:
            user_id: User identifier
            agent_slug: Agent template slug

        Returns:
            Reset UserAgentInstance with default configuration

        Raises:
            ValueError: If template or instance not found
        """
        logger.info(f"Resetting configuration for agent {agent_slug}, user {user_id.value}")

        # Get template
        template = self._template_repo.find_by_slug(agent_slug)
        if not template:
            raise ValueError(f"Agent template not found: {agent_slug}")

        # Get existing instance
        instance = self._instance_repo.find_by_user_and_template_slug(
            user_id=user_id,
            template_slug=agent_slug
        )

        if not instance:
            raise ValueError(f"No instance found for user {user_id.value} and agent {agent_slug}")

        # Reset to template configuration
        template_config = template.default_configuration
        instance.customize_configuration(
            template_config,
            "Reset to default template configuration"
        )

        # Mark as not customized
        object.__setattr__(instance, 'is_customized', False)

        # Save updates
        reset_instance = self._instance_repo.save(instance)
        logger.info(f"Configuration reset to default for {agent_slug}")

        return reset_instance
