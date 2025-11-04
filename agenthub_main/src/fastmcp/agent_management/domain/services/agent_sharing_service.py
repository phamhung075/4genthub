"""AgentSharingService - Domain service for agent sharing and importing"""

import logging
import secrets
from typing import Optional

from ..entities.user_agent_instance import UserAgentInstance
from ..value_objects.user_agent_instance_id import UserAgentInstanceId
from ..value_objects.user_id import UserId
from ..repositories.user_agent_instance_repository import UserAgentInstanceRepository
from ..repositories.agent_template_repository import AgentTemplateRepository

logger = logging.getLogger(__name__)


class AgentSharingService:
    """Domain service for agent sharing and importing logic.

    This service handles:
    - Generating secure share tokens for public sharing
    - Revoking share tokens
    - Importing shared agents from other users
    - Resolving name collisions during import

    Following DDD patterns:
    - Service depends on repository interfaces
    - Contains complex business logic for sharing workflow
    - Enforces security rules (ownership, token generation)
    """

    def __init__(
        self,
        instance_repository: UserAgentInstanceRepository,
        template_repository: AgentTemplateRepository
    ):
        """Initialize the service with repository dependencies.

        Args:
            instance_repository: Repository for user agent instances
            template_repository: Repository for agent templates
        """
        self.instance_repository = instance_repository
        self.template_repository = template_repository

    def generate_share_token(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId
    ) -> Optional[str]:
        """Generate a share token and make the instance public.

        Business Rules:
        - Only the instance owner can share
        - Share token is 64 characters (secure random)
        - Visibility automatically set to 'public'
        - Existing imports are unaffected

        Args:
            instance_id: The instance to share
            user_id: The user requesting to share (must be owner)

        Returns:
            The share token if successful, None if unauthorized or not found
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return None

        # Generate secure 64-character token
        share_token = secrets.token_urlsafe(48)[:64]  # URL-safe, 64 chars

        # Make instance public with share token
        instance.generate_share_token(share_token)

        # Save updated instance
        self.instance_repository.save(instance)

        logger.info(
            f"Generated share token for instance {instance_id} "
            f"(user: {user_id})"
        )

        return share_token

    def revoke_share_token(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId
    ) -> bool:
        """Revoke the share token and make the instance private.

        Business Rules:
        - Only the instance owner can revoke
        - Existing imports remain unaffected (they're copies)
        - Share token is removed
        - Visibility set to 'private'

        Args:
            instance_id: The instance to unshare
            user_id: The user requesting to unshare (must be owner)

        Returns:
            True if successful, False if unauthorized or not found
        """
        instance = self._get_and_verify_ownership(instance_id, user_id)
        if not instance:
            return False

        # Make instance private
        instance.revoke_share_token()

        # Save updated instance
        self.instance_repository.save(instance)

        logger.info(
            f"Revoked share token for instance {instance_id} "
            f"(user: {user_id})"
        )

        return True

    def import_agent(
        self,
        share_token: str,
        importer_user_id: UserId,
        creator_email: Optional[str] = None
    ) -> Optional[UserAgentInstance]:
        """Import a shared agent into the importer's account.

        This creates a COPY of the shared instance for the importer.
        It handles name collisions by appending "- created by [email]".

        Business Rules:
        - Source instance must be public with valid share token
        - Import creates a complete copy (not a reference)
        - Name collisions resolved by appending creator attribution
        - Imported instance marked with original_creator_id
        - Imported instance starts as private

        Args:
            share_token: The share token of the instance to import
            importer_user_id: The user importing the agent
            creator_email: Email of the original creator (for attribution)

        Returns:
            The newly created instance if successful, None if token invalid

        Raises:
            ValueError: If share_token is invalid
        """
        if not share_token or len(share_token) != 64:
            raise ValueError("Invalid share token")

        # Find the shared instance
        source_instance = self.instance_repository.find_by_share_token(share_token)

        if not source_instance:
            logger.warning(f"No instance found for share token: {share_token[:10]}...")
            return None

        if not source_instance.is_public():
            logger.warning(
                f"Instance {source_instance.id} is not public, "
                f"cannot import with token"
            )
            return None

        # Check if user already has instance for this template
        existing_instance = self.instance_repository.find_by_user_and_template(
            user_id=importer_user_id,
            template_id=source_instance.template_id
        )

        if existing_instance:
            logger.info(
                f"User {importer_user_id} already has instance for template "
                f"{source_instance.template_id}, cannot import"
            )
            return None

        # Resolve name collision
        final_agent_name = self._resolve_name_collision(
            base_name=source_instance.agent_name,
            importer_user_id=importer_user_id,
            creator_email=creator_email
        )

        # Create new instance (copy) for the importer
        imported_instance = UserAgentInstance(
            id=UserAgentInstanceId.generate_new(),
            user_id=importer_user_id,
            template_id=source_instance.template_id,
            agent_name=final_agent_name,
            is_customized=source_instance.is_customized,
            configuration=source_instance.configuration,  # Copy configuration
            visibility='private',  # Start as private
            share_token=None,  # No share token initially
            original_creator_id=source_instance.user_id,  # Track original creator
            usage_count=0,  # Reset usage
            last_used_at=None,  # Reset usage timestamp
            metadata={
                'imported_from': str(source_instance.id),
                'imported_via_token': share_token,
                'original_agent_name': source_instance.agent_name
            }
        )

        # Save the new instance
        saved_instance = self.instance_repository.save(imported_instance)

        logger.info(
            f"Imported instance {source_instance.id} as {saved_instance.id} "
            f"for user {importer_user_id} with name '{final_agent_name}'"
        )

        return saved_instance

    def _resolve_name_collision(
        self,
        base_name: str,
        importer_user_id: UserId,
        creator_email: Optional[str] = None
    ) -> str:
        """Resolve name collision by appending creator attribution.

        Business Rule:
        - If name exists for user, append "- created by [creator_email]"
        - If still collision, append number: "- created by [email] (2)"

        Args:
            base_name: The original agent name
            importer_user_id: The user importing the agent
            creator_email: Email of the creator (for attribution)

        Returns:
            A unique name for the importer's account
        """
        # Check if base name exists
        count = self.instance_repository.count_by_agent_name_for_user(
            user_id=importer_user_id,
            agent_name=base_name
        )

        # If no collision, use base name as-is
        if count == 0:
            return base_name

        # If collision, append creator attribution
        attribution = f"- created by {creator_email}" if creator_email else "- imported"
        candidate_name = f"{base_name} {attribution}"

        # Check if attributed name exists
        count = self.instance_repository.count_by_agent_name_for_user(
            user_id=importer_user_id,
            agent_name=candidate_name
        )

        # If still collision, append number
        if count > 0:
            counter = 2
            while True:
                numbered_name = f"{candidate_name} ({counter})"
                count = self.instance_repository.count_by_agent_name_for_user(
                    user_id=importer_user_id,
                    agent_name=numbered_name
                )
                if count == 0:
                    return numbered_name
                counter += 1

        return candidate_name

    def get_public_instances(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: 'InstanceOrdering' = None
    ) -> list[UserAgentInstance]:
        """Get list of publicly shared instances for marketplace.

        Domain service adds business value:
        - Enforces marketplace ordering policy (newest first by default)
        - Validates pagination boundaries
        - Ensures only truly shareable instances returned

        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            order_by: Optional ordering preference (defaults to CREATED_DESC for marketplace)

        Returns:
            List of public instances ordered and validated
        """
        from ..enums.ordering import InstanceOrdering

        # Business policy: marketplace defaults to newest first
        if order_by is None:
            order_by = InstanceOrdering.CREATED_DESC

        # Business rule: validate pagination boundaries
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")

        if offset < 0:
            raise ValueError(f"Offset must be non-negative, got {offset}")

        # Retrieve instances using domain-defined criteria
        instances = self.instance_repository.find_public_instances(
            limit=limit,
            offset=offset,
            order_by=order_by
        )

        # Business validation: double-check all returned instances are shareable
        # (defensive programming - infrastructure should already filter, but we verify)
        return [inst for inst in instances if inst.is_public()]

    def _get_and_verify_ownership(
        self,
        instance_id: UserAgentInstanceId,
        user_id: UserId
    ) -> Optional[UserAgentInstance]:
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
                f"User {user_id} attempted to share instance {instance_id} "
                f"owned by {instance.user_id}"
            )
            return None

        return instance
