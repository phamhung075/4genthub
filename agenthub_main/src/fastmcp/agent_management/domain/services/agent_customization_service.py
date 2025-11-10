"""AgentCustomizationService - Domain service for customizing agent configurations"""

import logging
from typing import Any

from ..entities.user_agent_instance import UserAgentInstance
from ..repositories.user_agent_instance_repository import UserAgentInstanceRepository
from ..value_objects.agent_configuration import AgentConfiguration
from ..value_objects.user_agent_instance_id import UserAgentInstanceId
from ..value_objects.user_id import UserId

logger = logging.getLogger(__name__)


class AgentCustomizationService:
    """Domain service for agent customization logic.

    This service handles updating agent configurations, including:
    - System prompts (instructions)
    - Rules
    - Capabilities
    - Output formats
    - Tools

    Following DDD patterns:
    - Service depends on repository interface
    - Contains business logic for configuration updates
    - Validates changes before applying
    - Ensures consistency across configuration updates
    """

    def __init__(
        self,
        instance_repository: UserAgentInstanceRepository
    ):
        """Initialize the service with repository dependency.

        Args:
            instance_repository: Repository for user agent instances
        """
        self.instance_repository = instance_repository

    def update_system_prompt(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        new_system_prompt: str,
        customization_notes: str | None = None
    ) -> UserAgentInstance | None:
        """Update the system prompt (instructions) for an agent instance.

        Args:
            instance_id: The instance to update
            user_id: The user making the update (must be owner)
            new_system_prompt: The new system prompt text
            customization_notes: Optional notes about the customization

        Returns:
            Updated instance if successful, None if not found or unauthorized

        Raises:
            ValueError: If new_system_prompt is empty
        """
        if not new_system_prompt or not new_system_prompt.strip():
            raise ValueError("System prompt cannot be empty")

        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Create new configuration with updated system prompt
        new_config = AgentConfiguration(
            system_prompt=new_system_prompt,
            tools=instance.configuration.tools,
            capabilities=instance.configuration.capabilities,
            rules=instance.configuration.rules,
            output_format=instance.configuration.output_format,
            metadata=instance.configuration.metadata
        )

        # Apply the customization
        instance.customize_configuration(new_config, customization_notes)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Updated system prompt for instance {instance_id} "
            f"(user: {user_id})"
        )

        return updated_instance

    def update_rules(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        new_rules: list[str],
        customization_notes: str | None = None
    ) -> UserAgentInstance | None:
        """Update the rules for an agent instance.

        Args:
            instance_id: The instance to update
            user_id: The user making the update (must be owner)
            new_rules: The new list of rules
            customization_notes: Optional notes about the customization

        Returns:
            Updated instance if successful, None if not found or unauthorized
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Create new configuration with updated rules
        new_config = AgentConfiguration(
            system_prompt=instance.configuration.system_prompt,
            tools=instance.configuration.tools,
            capabilities=instance.configuration.capabilities,
            rules=tuple(new_rules),  # Convert to tuple for immutability
            output_format=instance.configuration.output_format,
            metadata=instance.configuration.metadata
        )

        # Apply the customization
        instance.customize_configuration(new_config, customization_notes)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Updated rules for instance {instance_id} "
            f"(user: {user_id}, {len(new_rules)} rules)"
        )

        return updated_instance

    def update_capabilities(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        new_capabilities: dict[str, Any],
        customization_notes: str | None = None
    ) -> UserAgentInstance | None:
        """Update the capabilities for an agent instance.

        Args:
            instance_id: The instance to update
            user_id: The user making the update (must be owner)
            new_capabilities: The new capabilities dictionary
            customization_notes: Optional notes about the customization

        Returns:
            Updated instance if successful, None if not found or unauthorized
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Create new configuration with updated capabilities
        new_config = AgentConfiguration(
            system_prompt=instance.configuration.system_prompt,
            tools=instance.configuration.tools,
            capabilities=new_capabilities,
            rules=instance.configuration.rules,
            output_format=instance.configuration.output_format,
            metadata=instance.configuration.metadata
        )

        # Apply the customization
        instance.customize_configuration(new_config, customization_notes)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Updated capabilities for instance {instance_id} "
            f"(user: {user_id})"
        )

        return updated_instance

    def update_output_format(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        new_output_format: dict[str, Any],
        customization_notes: str | None = None
    ) -> UserAgentInstance | None:
        """Update the output format for an agent instance.

        Args:
            instance_id: The instance to update
            user_id: The user making the update (must be owner)
            new_output_format: The new output format dictionary
            customization_notes: Optional notes about the customization

        Returns:
            Updated instance if successful, None if not found or unauthorized
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Create new configuration with updated output format
        new_config = AgentConfiguration(
            system_prompt=instance.configuration.system_prompt,
            tools=instance.configuration.tools,
            capabilities=instance.configuration.capabilities,
            rules=instance.configuration.rules,
            output_format=new_output_format,
            metadata=instance.configuration.metadata
        )

        # Apply the customization
        instance.customize_configuration(new_config, customization_notes)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Updated output format for instance {instance_id} "
            f"(user: {user_id})"
        )

        return updated_instance

    def update_full_configuration(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        new_configuration: AgentConfiguration,
        customization_notes: str | None = None
    ) -> UserAgentInstance | None:
        """Update the entire configuration for an agent instance.

        Used when making multiple changes at once (e.g., from markdown editor).

        Args:
            instance_id: The instance to update
            user_id: The user making the update (must be owner)
            new_configuration: The complete new configuration
            customization_notes: Optional notes about the customization

        Returns:
            Updated instance if successful, None if not found or unauthorized
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Apply the customization
        instance.customize_configuration(new_configuration, customization_notes)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Updated full configuration for instance {instance_id} "
            f"(user: {user_id})"
        )

        return updated_instance

    def reset_to_template_defaults(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId,
        template_configuration: AgentConfiguration
    ) -> UserAgentInstance | None:
        """Reset an instance to its template's default configuration.

        Args:
            instance_id: The instance to reset
            user_id: The user making the reset (must be owner)
            template_configuration: The template's default configuration

        Returns:
            Reset instance if successful, None if not found or unauthorized
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Reset configuration
        object.__setattr__(instance, 'configuration', template_configuration)
        object.__setattr__(instance, 'is_customized', False)

        # Clear customization metadata
        metadata_copy = instance.metadata.copy()
        if 'last_customization' in metadata_copy:
            del metadata_copy['last_customization']
        object.__setattr__(instance, 'metadata', metadata_copy)

        # Save and return
        updated_instance = self.instance_repository.save(instance)

        logger.info(
            f"Reset instance {instance_id} to template defaults "
            f"(user: {user_id})"
        )

        return updated_instance

    def _get_and_verify_ownership(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId
    ) -> UserAgentInstance | None:
        """Get instance and verify the user owns it.

        Private helper method for authorization.

        Args:
            instance_id: The instance to get
            user_id: The user claiming ownership

        Returns:
            The instance if found and owned by user, None otherwise
        """
        instance = self.instance_repository.find_by_id(instance_id)

        if not instance:
            logger.warning(f"Instance not found: {instance_id}")
            return None

        if instance.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to modify instance {instance_id} "
                f"owned by {instance.user_id}"
            )
            return None

        return instance
