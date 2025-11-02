"""
Agent Management Application Facade

This facade orchestrates agent-related operations for MCP controllers,
coordinating between domain services and repositories to provide a
high-level API for agent instantiation and retrieval.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ...domain.entities.agent_template import AgentTemplate
from ...domain.entities.user_agent_instance import UserAgentInstance
from ...domain.value_objects.user_id import UserId
from ...domain.value_objects.user_agent_instance_id import UserAgentInstanceId
from ...domain.value_objects.agent_configuration import AgentConfiguration
from ...domain.enums.ordering import InstanceOrdering
from ...domain.services.agent_instantiation_service import AgentInstantiationService
from ...domain.services.agent_sharing_service import AgentSharingService
from ...infrastructure.repositories import (
    ORMAgentTemplateRepository,
    ORMUserAgentInstanceRepository
)
from ...infrastructure.database.models import AgentImportHistoryORM

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
        instantiation_service: Optional[AgentInstantiationService] = None,
        sharing_service: Optional[AgentSharingService] = None
    ):
        """
        Initialize the facade with repositories and services.

        Args:
            template_repository: Repository for agent templates
            instance_repository: Repository for user agent instances
            instantiation_service: Domain service for agent instantiation
            sharing_service: Domain service for agent sharing
        """
        self._template_repo = template_repository or ORMAgentTemplateRepository()
        self._instance_repo = instance_repository or ORMUserAgentInstanceRepository()
        self._instantiation_service = instantiation_service or AgentInstantiationService(
            template_repository=self._template_repo,
            instance_repository=self._instance_repo
        )
        self._sharing_service = sharing_service or AgentSharingService(
            instance_repository=self._instance_repo,
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

        # Delegate to domain service - no logic duplication
        instance = self._instantiation_service.get_or_create_instance(
            user_id=user_id,
            template_slug=agent_slug
        )

        if not instance:
            raise ValueError(f"Agent template not found: {agent_slug}")

        logger.info(f"Instance ready: {instance.id.value}")
        return instance

    def bulk_create_instances(
        self,
        user_id: UserId,
        template_slugs: Optional[list[str]] = None
    ) -> list[UserAgentInstance]:
        """
        Create instances for multiple templates in a single operation.
        Only creates instances that don't already exist for the user.

        Args:
            user_id: User identifier
            template_slugs: List of template slugs to create (if None, creates all available templates)

        Returns:
            List of UserAgentInstance objects (newly created only)
        """
        logger.info(f"Bulk creating instances for user={user_id.value}, templates={template_slugs or 'all'}")

        # Get all available templates if no specific list provided
        all_templates = self._template_repo.find_all()
        if template_slugs is None:
            template_slugs = [t.slug for t in all_templates]
            logger.info(f"Creating instances for all {len(template_slugs)} available templates")

        # Create a mapping of template_id -> slug for existing instances check
        template_id_to_slug = {t.id.value: t.slug for t in all_templates}

        # Get existing instances for user to avoid duplicates
        existing_instances = self._instance_repo.find_by_user(user_id)
        # Map template IDs to slugs for existing instances
        existing_slugs = {
            template_id_to_slug.get(inst.template_id.value)
            for inst in existing_instances
            if inst.template_id and inst.template_id.value in template_id_to_slug
        }
        logger.info(f"User already has {len(existing_slugs)} instances")

        # Create instances for templates user doesn't have yet
        created_instances = []
        skipped_count = 0

        for slug in template_slugs:
            if slug in existing_slugs:
                skipped_count += 1
                logger.debug(f"Skipping {slug} - user already has instance")
                continue

            try:
                instance = self._instantiation_service.get_or_create_instance(
                    user_id=user_id,
                    template_slug=slug
                )
                if instance:
                    created_instances.append(instance)
                    logger.info(f"Created instance for {slug}")
            except Exception as e:
                logger.warning(f"Failed to create instance for {slug}: {e}")
                continue

        logger.info(f"Bulk creation complete: {len(created_instances)} created, {skipped_count} skipped")
        return created_instances

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
        return self._instance_repo.find_by_user(user_id)

    def get_template_by_slug(self, agent_slug: str) -> Optional[AgentTemplate]:
        """
        Get agent template by slug.

        Args:
            agent_slug: Agent template slug

        Returns:
            AgentTemplate if found, None otherwise
        """
        return self._template_repo.find_by_slug(agent_slug)

    def get_template_by_id(self, template_id: str) -> Optional[AgentTemplate]:
        """
        Get agent template by ID.

        Args:
            template_id: Agent template ID (UUID string)

        Returns:
            AgentTemplate if found, None otherwise
        """
        from ...domain.value_objects.agent_template_id import AgentTemplateId

        template_uuid = AgentTemplateId.from_string(template_id)
        return self._template_repo.find_by_id(template_uuid)

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
        is_enabled: Optional[bool] = None,
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
            is_enabled: Whether agent is enabled for use in call_agent tools (optional)
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
        from ...domain.value_objects.user_agent_instance_id import UserAgentInstanceId

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

        # Update is_enabled if provided
        if is_enabled is not None:
            object.__setattr__(instance, 'is_enabled', is_enabled)

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

        # Update visibility if provided - use sharing service for proper token handling
        if visibility is not None:
            if visibility not in ('private', 'public'):
                raise ValueError(f"Invalid visibility: {visibility}. Must be 'private' or 'public'")

            # Use sharing service to handle visibility changes with proper token management
            if visibility == 'public' and not instance.share_token:
                # Generate share token and set visibility to public atomically
                share_token = self._sharing_service.generate_share_token(instance.id, user_id)
                if not share_token:
                    raise ValueError(f"Failed to generate share token for instance {instance_id}")
                # Re-fetch instance with updated share_token
                instance = self._instance_repo.find_by_id(instance_uuid)
            elif visibility == 'private' and instance.share_token:
                # Revoke share token and set visibility to private atomically
                success = self._sharing_service.revoke_share_token(instance.id, user_id)
                if not success:
                    raise ValueError(f"Failed to revoke share token for instance {instance_id}")
                # Re-fetch instance with revoked share_token
                instance = self._instance_repo.find_by_id(instance_uuid)

        # Save updates (if visibility wasn't changed, or after re-fetching from sharing service)
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

    def share_agent(
        self,
        user_id: UserId,
        instance_id: str
    ) -> Optional[str]:
        """
        Generate a share token and make an instance public.

        This allows users to share their customized agent instances with others.
        The generated token can be used by other users to import the agent.

        Args:
            user_id: User identifier (must be instance owner)
            instance_id: Instance identifier to share

        Returns:
            The 64-character share token if successful, None otherwise

        Raises:
            ValueError: If instance not found or user is not the owner
        """
        from ...domain.value_objects.user_agent_instance_id import UserAgentInstanceId

        logger.info(f"Sharing instance {instance_id} for user {user_id.value}")

        instance_uuid = UserAgentInstanceId.from_string(instance_id)
        share_token = self._sharing_service.generate_share_token(
            instance_id=instance_uuid,
            user_id=user_id
        )

        if not share_token:
            raise ValueError(f"Failed to share instance {instance_id}. Instance not found or unauthorized.")

        logger.info(f"Instance {instance_id} shared successfully with token")
        return share_token

    def unshare_agent(
        self,
        user_id: UserId,
        instance_id: str
    ) -> bool:
        """
        Revoke the share token and make an instance private.

        Args:
            user_id: User identifier (must be instance owner)
            instance_id: Instance identifier to unshare

        Returns:
            True if successful

        Raises:
            ValueError: If instance not found or user is not the owner
        """
        from ...domain.value_objects.user_agent_instance_id import UserAgentInstanceId

        logger.info(f"Unsharing instance {instance_id} for user {user_id.value}")

        instance_uuid = UserAgentInstanceId.from_string(instance_id)
        result = self._sharing_service.revoke_share_token(
            instance_id=instance_uuid,
            user_id=user_id
        )

        if not result:
            raise ValueError(f"Failed to unshare instance {instance_id}. Instance not found or unauthorized.")

        logger.info(f"Instance {instance_id} unshared successfully")
        return result

    def import_agent(
        self,
        share_token: str,
        importer_user_id: UserId,
        creator_email: Optional[str] = None
    ) -> Optional[UserAgentInstance]:
        """
        Import a shared agent from another user.

        Creates a copy of the shared agent instance for the importing user.
        Handles name collisions automatically.

        Args:
            share_token: 64-character share token
            importer_user_id: User importing the agent
            creator_email: Email of the original creator (for attribution)

        Returns:
            The newly created instance if successful, None if token invalid

        Raises:
            ValueError: If share_token is invalid or user already has this template
        """
        logger.info(f"Importing agent for user {importer_user_id.value} with share token")

        # Get source instance before import (for history recording)
        source_instance = self._instance_repo.find_by_share_token(share_token)

        imported_instance = self._sharing_service.import_agent(
            share_token=share_token,
            importer_user_id=importer_user_id,
            creator_email=creator_email
        )

        if not imported_instance:
            raise ValueError(
                f"Failed to import agent. Invalid token, instance not public, "
                f"or user already has this template."
            )

        # Record import history
        if source_instance:
            try:
                with self._instance_repo.get_db_session() as session:
                    history_record = AgentImportHistoryORM(
                        id=str(uuid.uuid4()),
                        importer_user_id=str(importer_user_id.value),
                        source_instance_id=str(source_instance.id.value),
                        imported_instance_id=str(imported_instance.id.value),
                        imported_at=datetime.now(timezone.utc),
                        share_token=share_token
                    )
                    session.add(history_record)
                    session.commit()
                    logger.info(
                        f"Recorded import history: {source_instance.id.value} → "
                        f"{imported_instance.id.value} for user {importer_user_id.value}"
                    )
            except Exception as e:
                # Don't fail the import if history recording fails
                logger.warning(f"Failed to record import history: {e}")

        logger.info(
            f"Agent imported successfully as instance {imported_instance.id.value} "
            f"for user {importer_user_id.value}"
        )
        return imported_instance

    def get_marketplace_agents(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: 'InstanceOrdering' = None
    ) -> list[UserAgentInstance]:
        """Get list of publicly shared agents for marketplace browsing.

        Application layer coordinates between presentation and domain layers.

        Args:
            limit: Maximum number of results (default 50)
            offset: Offset for pagination (default 0)
            order_by: Optional ordering preference from presentation layer

        Returns:
            List of public agent instances (validated and ordered by domain service)
        """
        logger.info(
            f"Getting marketplace agents: limit={limit}, offset={offset}, "
            f"order_by={order_by.value if order_by else 'default'}"
        )
        return self._sharing_service.get_public_instances(
            limit=limit,
            offset=offset,
            order_by=order_by
        )

    def get_shared_agent_preview(
        self,
        share_token: str
    ) -> Optional[UserAgentInstance]:
        """
        Preview a shared agent before importing.

        Args:
            share_token: The share token to preview

        Returns:
            The instance if found and public, None otherwise
        """
        logger.info(f"Previewing shared agent with token")

        if not share_token or len(share_token) != 64:
            raise ValueError("Invalid share token")

        instance = self._instance_repo.find_by_share_token(share_token)

        if not instance or not instance.is_public():
            return None

        return instance
