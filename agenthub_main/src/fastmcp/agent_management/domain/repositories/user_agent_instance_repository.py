"""UserAgentInstanceRepository - Repository interface for UserAgentInstance aggregate"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities.user_agent_instance import UserAgentInstance
from ..value_objects.user_agent_instance_id import UserAgentInstanceId
from ..value_objects.user_id import UserId
from ..value_objects.agent_template_id import AgentTemplateId
from ..enums.ordering import InstanceOrdering


class UserAgentInstanceRepository(ABC):
    """Repository interface for UserAgentInstance persistence.

    Following DDD patterns, this interface lives in the domain layer
    while implementations live in the infrastructure layer.
    """

    @abstractmethod
    def save(self, instance: UserAgentInstance) -> UserAgentInstance:
        """Save or update a user agent instance.

        Args:
            instance: The instance to save

        Returns:
            The saved instance with updated timestamps
        """
        pass

    @abstractmethod
    def find_by_id(self, instance_id: UserAgentInstanceId) -> Optional[UserAgentInstance]:
        """Find an instance by its ID.

        Args:
            instance_id: The instance ID to search for

        Returns:
            The instance if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_user_and_template(
        self,
        user_id: UserId,
        template_id: AgentTemplateId
    ) -> Optional[UserAgentInstance]:
        """Find an instance by user ID and template ID.

        Enforces UNIQUE(user_id, template_id) constraint.

        Args:
            user_id: The user ID
            template_id: The template ID

        Returns:
            The instance if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_user(self, user_id: UserId) -> List[UserAgentInstance]:
        """Find all instances for a user.

        Args:
            user_id: The user ID

        Returns:
            List of instances owned by the user
        """
        pass

    @abstractmethod
    def find_enabled_by_user(self, user_id: UserId) -> List[UserAgentInstance]:
        """Find all enabled instances for a user.

        Used when populating call_agent tool options - only shows enabled agents.

        Args:
            user_id: The user ID

        Returns:
            List of enabled instances owned by the user (is_enabled=True)
        """
        pass

    @abstractmethod
    def find_by_share_token(self, share_token: str) -> Optional[UserAgentInstance]:
        """Find an instance by its share token.

        Args:
            share_token: The share token to search for

        Returns:
            The instance if found, None otherwise
        """
        pass

    @abstractmethod
    def find_public_instances(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: InstanceOrdering = InstanceOrdering.CREATED_DESC
    ) -> List[UserAgentInstance]:
        """Find all publicly shared instances.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            order_by: Ordering preference (domain-defined business option)

        Returns:
            List of public instances ordered as specified
        """
        pass

    @abstractmethod
    def exists_by_user_and_template(
        self,
        user_id: UserId,
        template_id: AgentTemplateId
    ) -> bool:
        """Check if an instance exists for user and template.

        Args:
            user_id: The user ID
            template_id: The template ID

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def count_by_agent_name_for_user(self, user_id: UserId, agent_name: str) -> int:
        """Count instances with a specific name for a user.

        Used for name collision detection during import.

        Args:
            user_id: The user ID
            agent_name: The agent name to count

        Returns:
            Number of instances with that name
        """
        pass

    @abstractmethod
    def delete(self, instance_id: UserAgentInstanceId) -> None:
        """Delete an instance by ID.

        Args:
            instance_id: The instance ID to delete
        """
        pass
