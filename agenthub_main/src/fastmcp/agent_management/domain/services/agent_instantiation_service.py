"""AgentInstantiationService - Domain service for creating agent instances"""

import logging

from ..entities.agent_template import AgentTemplate
from ..entities.user_agent_instance import UserAgentInstance
from ..repositories.agent_template_repository import AgentTemplateRepository
from ..repositories.user_agent_instance_repository import UserAgentInstanceRepository
from ..value_objects.user_agent_instance_id import UserAgentInstanceId
from ..value_objects.user_id import UserId

logger = logging.getLogger(__name__)


class AgentInstantiationService:
    """Domain service for agent instantiation logic.

    This service handles the business logic of creating user-specific
    agent instances from templates. It enforces the rule that each user
    can have only one instance per template (UNIQUE constraint).

    Following DDD patterns:
    - Service depends on repository interfaces (not implementations)
    - Contains business logic that spans multiple entities
    - Stateless - doesn't hold data between calls
    """

    def __init__(
        self,
        template_repository: AgentTemplateRepository,
        instance_repository: UserAgentInstanceRepository,
    ):
        """Initialize the service with repository dependencies.

        Args:
            template_repository: Repository for agent templates
            instance_repository: Repository for user agent instances
        """
        self.template_repository = template_repository
        self.instance_repository = instance_repository

    def get_or_create_instance(
        self, user_id: UserId, template_slug: str
    ) -> UserAgentInstance | None:
        """Get existing instance or create new one for user and template.

        This is the primary method called by call_agent MCP tool.
        It implements the auto-instantiation logic:
        1. Find template by slug
        2. Check if user already has an instance
        3. If not, create new instance from template defaults
        4. Return the instance (new or existing)

        Business Rules:
        - Each user gets exactly one instance per template
        - New instances use template's default configuration
        - Instance name defaults to template name
        - All instances start with visibility='default' (from template, not customized)

        Args:
            user_id: The user requesting the agent
            template_slug: The agent template slug (e.g., 'coding-agent')

        Returns:
            UserAgentInstance if successful, None if template not found

        Raises:
            ValueError: If user_id or template_slug is invalid
        """
        if not user_id:
            raise ValueError("user_id is required")

        if not template_slug or not template_slug.strip():
            raise ValueError("template_slug cannot be empty")

        # Step 1: Find the template
        template = self.template_repository.find_by_slug(template_slug)
        if not template:
            logger.warning(f"Template not found for slug: {template_slug}")
            return None

        logger.debug(f"Found template: {template.name} (id={template.id})")

        # Step 2: Check if instance already exists
        existing_instance = self.instance_repository.find_by_user_and_template(
            user_id=user_id, template_id=template.id
        )

        if existing_instance:
            logger.info(
                f"Returning existing instance for user {user_id} "
                f"and template {template_slug}"
            )
            return existing_instance

        # Step 3: Create new instance from template
        new_instance = self._create_instance_from_template(
            user_id=user_id, template=template
        )

        # Step 4: Save and return
        saved_instance = self.instance_repository.save(new_instance)

        logger.info(
            f"Created new instance {saved_instance.id} for user {user_id} "
            f"and template {template_slug}"
        )

        return saved_instance

    def _create_instance_from_template(
        self, user_id: UserId, template: AgentTemplate
    ) -> UserAgentInstance:
        """Create a new user agent instance from a template.

        Private helper method that instantiates a UserAgentInstance
        with defaults from the template.

        Args:
            user_id: The user who will own this instance
            template: The template to instantiate from

        Returns:
            A new UserAgentInstance (not yet saved)
        """
        return UserAgentInstance(
            id=UserAgentInstanceId.generate_new(),
            user_id=user_id,
            template_id=template.id,
            agent_name=template.name,  # Default to template name
            is_customized=False,  # Not customized initially
            configuration=template.get_configuration_copy(),  # Copy default config
            visibility="private",  # Default to private for new instances
            share_token=None,  # No share token initially
            original_creator_id=None,  # Not imported
            usage_count=0,  # No usage yet
            last_used_at=None,  # Never used
            metadata={
                "instantiated_from_template": str(template.id),
                "template_slug": template.slug,
                "template_version": template.version,
            },
        )

    def get_instance_by_id(
        self, instance_id: UserAgentInstanceId
    ) -> UserAgentInstance | None:
        """Get an agent instance by its ID.

        Args:
            instance_id: The instance ID to find

        Returns:
            The instance if found, None otherwise
        """
        return self.instance_repository.find_by_id(instance_id)

    def get_instances_for_user(self, user_id: UserId) -> list[UserAgentInstance]:
        """Get all agent instances for a user.

        Args:
            user_id: The user ID to find instances for

        Returns:
            List of all instances owned by the user
        """
        return self.instance_repository.find_by_user(user_id)
