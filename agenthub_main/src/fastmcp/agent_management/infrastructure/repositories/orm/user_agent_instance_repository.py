"""
ORM User Agent Instance Repository Implementation

This module implements the UserAgentInstance Repository using SQLAlchemy ORM,
providing per-user agent instance management with full database capabilities.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_

from fastmcp.task_management.infrastructure.repositories.base_timestamp_repository import (
    BaseTimestampRepository,
)

from ....domain.entities.user_agent_instance import UserAgentInstance
from ....domain.enums.ordering import InstanceOrdering
from ....domain.repositories.user_agent_instance_repository import (
    UserAgentInstanceRepository as UserAgentInstanceRepositoryInterface,
)
from ....domain.value_objects.agent_configuration import AgentConfiguration
from ....domain.value_objects.agent_template_id import AgentTemplateId
from ....domain.value_objects.user_agent_instance_id import UserAgentInstanceId
from ....domain.value_objects.user_id import UserId
from ...database.models import UserAgentInstanceORM

logger = logging.getLogger(__name__)


class ORMUserAgentInstanceRepository(BaseTimestampRepository[UserAgentInstanceORM], UserAgentInstanceRepositoryInterface):
    """ORM implementation of user agent instance repository using SQLAlchemy"""

    def __init__(self):
        """Initialize the ORM user agent instance repository"""
        super().__init__(UserAgentInstanceORM)
        logger.debug("Initialized ORMUserAgentInstanceRepository")

    def save(self, instance: UserAgentInstance) -> UserAgentInstance:
        """
        Save a user agent instance to the database (DDD-compliant)

        Args:
            instance: UserAgentInstance entity to save

        Returns:
            Saved UserAgentInstance entity

        Raises:
            DatabaseException: If save operation fails
        """
        try:
            with self.get_db_session() as session:
                # Check if instance exists
                existing = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.id == str(instance.id)
                ).first()

                if existing:
                    # DDD-COMPLIANT: Convert entity to model dict
                    model_dict = self._entity_to_model_dict(instance)

                    # Update existing instance fields
                    existing.agent_name = model_dict["agent_name"]
                    existing.is_customized = model_dict["is_customized"]
                    existing.is_enabled = model_dict.get("is_enabled", True)
                    existing.customization_notes = model_dict.get("customization_notes")
                    existing.system_prompt = model_dict["system_prompt"]
                    existing.tools = model_dict["tools"]
                    existing.capabilities = model_dict["capabilities"]
                    existing.rules = model_dict.get("rules")
                    existing.output_format = model_dict.get("output_format")
                    existing.metadata_json = model_dict.get("metadata_json")
                    existing.visibility = model_dict["visibility"]
                    existing.share_token = model_dict.get("share_token")
                    existing.share_created_at = model_dict.get("share_created_at")
                    existing.usage_count = model_dict.get("usage_count", 0)
                    existing.last_used_at = model_dict.get("last_used_at")
                    existing.updated_at = datetime.now(UTC)

                    logger.info(f"Updated user agent instance: {instance.agent_name} for user {instance.user_id}")
                else:
                    # DDD-COMPLIANT: Convert entity to model dict
                    model_dict = self._entity_to_model_dict(instance)

                    # Create new instance
                    orm_instance = UserAgentInstanceORM(
                        id=model_dict["id"],
                        user_id=model_dict["user_id"],
                        template_id=model_dict["template_id"],
                        agent_name=model_dict["agent_name"],
                        is_customized=model_dict["is_customized"],
                        is_enabled=model_dict.get("is_enabled", True),
                        customization_notes=model_dict.get("customization_notes"),
                        system_prompt=model_dict["system_prompt"],
                        tools=model_dict["tools"],
                        capabilities=model_dict["capabilities"],
                        rules=model_dict.get("rules"),
                        output_format=model_dict.get("output_format"),
                        metadata_json=model_dict.get("metadata_json"),
                        visibility=model_dict["visibility"],
                        share_token=model_dict.get("share_token"),
                        share_created_at=model_dict.get("share_created_at"),
                        original_creator_id=model_dict.get("original_creator_id"),
                        imported_at=model_dict.get("imported_at"),
                        usage_count=model_dict.get("usage_count", 0),
                        last_used_at=model_dict.get("last_used_at"),
                        created_at=model_dict["created_at"],
                        updated_at=model_dict["updated_at"]
                    )
                    session.add(orm_instance)

                    logger.info(f"Created new user agent instance: {instance.agent_name} for user {instance.user_id}")

                session.commit()

                # Fetch and return the saved entity
                saved_orm = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.id == str(instance.id)
                ).first()

                return self._model_to_entity(saved_orm)

        except Exception as e:
            logger.error(f"Error saving user agent instance {instance.agent_name}: {e}")
            raise

    def find_by_id(self, instance_id: UserAgentInstanceId) -> UserAgentInstance | None:
        """
        Find an instance by its ID

        Args:
            instance_id: Instance identifier

        Returns:
            UserAgentInstance entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_instance = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.id == str(instance_id)
                ).first()

                if orm_instance:
                    return self._model_to_entity(orm_instance)
                return None

        except Exception as e:
            logger.error(f"Error finding user agent instance by id {instance_id}: {e}")
            return None

    def find_by_user_and_template(
        self,
        user_id: UserId,
        template_id: AgentTemplateId
    ) -> UserAgentInstance | None:
        """
        Find an instance by user ID and template ID

        Args:
            user_id: User identifier
            template_id: Template identifier

        Returns:
            UserAgentInstance entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_instance = session.query(UserAgentInstanceORM).filter(
                    and_(
                        UserAgentInstanceORM.user_id == str(user_id),
                        UserAgentInstanceORM.template_id == str(template_id)
                    )
                ).first()

                if orm_instance:
                    return self._model_to_entity(orm_instance)
                return None

        except Exception as e:
            logger.error(f"Error finding user agent instance by user {user_id} and template {template_id}: {e}")
            return None

    def find_by_user_and_template_slug(
        self,
        user_id: UserId,
        template_slug: str
    ) -> UserAgentInstance | None:
        """
        Find an instance by user ID and template slug.

        This is a convenience method that combines template lookup by slug
        with instance lookup by user and template ID.

        Args:
            user_id: User identifier
            template_slug: Template slug (e.g., 'coding-agent')

        Returns:
            UserAgentInstance entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                # Import here to avoid circular dependency
                from ...database.models import AgentTemplateORM

                # First find the template by slug
                template = session.query(AgentTemplateORM).filter(
                    AgentTemplateORM.slug == template_slug
                ).first()

                if not template:
                    logger.debug(f"Template not found for slug: {template_slug}")
                    return None

                # Then find the instance by user and template ID
                orm_instance = session.query(UserAgentInstanceORM).filter(
                    and_(
                        UserAgentInstanceORM.user_id == str(user_id),
                        UserAgentInstanceORM.template_id == template.id
                    )
                ).first()

                if orm_instance:
                    return self._model_to_entity(orm_instance)
                return None

        except Exception as e:
            logger.error(f"Error finding user agent instance by user {user_id} and template slug {template_slug}: {e}")
            return None

    def exists_by_user_and_template(
        self,
        user_id: UserId,
        template_id: AgentTemplateId
    ) -> bool:
        """
        Check if an instance exists for user and template.

        Args:
            user_id: User identifier
            template_id: Template identifier

        Returns:
            True if instance exists, False otherwise
        """
        try:
            with self.get_db_session() as session:
                exists = session.query(UserAgentInstanceORM).filter(
                    and_(
                        UserAgentInstanceORM.user_id == str(user_id),
                        UserAgentInstanceORM.template_id == str(template_id)
                    )
                ).first() is not None

                return exists

        except Exception as e:
            logger.error(f"Error checking if user agent instance exists for user {user_id} and template {template_id}: {e}")
            return False

    def find_by_user(self, user_id: UserId) -> list[UserAgentInstance]:
        """
        Find all instances for a user

        Args:
            user_id: User identifier

        Returns:
            List of UserAgentInstance entities for the user
        """
        try:
            with self.get_db_session() as session:
                orm_instances = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.user_id == str(user_id)
                ).order_by(UserAgentInstanceORM.agent_name).all()

                return [self._model_to_entity(instance) for instance in orm_instances]

        except Exception as e:
            logger.error(f"Error finding user agent instances for user {user_id}: {e}")
            return []

    def find_enabled_by_user(self, user_id: UserId) -> list[UserAgentInstance]:
        """
        Find all enabled instances for a user

        Used when populating call_agent tool options - only shows enabled agents.

        Args:
            user_id: User identifier

        Returns:
            List of enabled UserAgentInstance entities (is_enabled=True)
        """
        try:
            with self.get_db_session() as session:
                orm_instances = session.query(UserAgentInstanceORM).filter(
                    and_(
                        UserAgentInstanceORM.user_id == str(user_id),
                        UserAgentInstanceORM.is_enabled
                    )
                ).order_by(UserAgentInstanceORM.agent_name).all()

                return [self._model_to_entity(instance) for instance in orm_instances]

        except Exception as e:
            logger.error(f"Error finding enabled user agent instances for user {user_id}: {e}")
            return []

    def find_by_share_token(self, share_token: str) -> UserAgentInstance | None:
        """
        Find an instance by its share token

        Args:
            share_token: Share token to search for

        Returns:
            UserAgentInstance entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_instance = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.share_token == share_token
                ).first()

                if orm_instance:
                    return self._model_to_entity(orm_instance)
                return None

        except Exception as e:
            logger.error(f"Error finding user agent instance by share token: {e}")
            return None

    def find_public_instances(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: 'InstanceOrdering' = None
    ) -> list[UserAgentInstance]:
        """Find public instances (for browsing shared agents).

        Following DDD: Domain defines WHAT ordering options exist,
        infrastructure defines HOW to implement them in SQL.

        Business Rule: Exclude orphaned imports (imports where original creator deleted their agent).
        Only show:
        1. Original agents (original_creator_id IS NULL)
        2. Imported agents where original still exists

        Args:
            limit: Maximum number of instances to return
            offset: Offset for pagination
            order_by: Domain-defined ordering preference

        Returns:
            List of public UserAgentInstance entities ordered as specified
        """
        from sqlalchemy import exists, select

        from ....domain.enums.ordering import InstanceOrdering

        # Default ordering if none specified
        if order_by is None:
            order_by = InstanceOrdering.CREATED_DESC

        try:
            with self.get_db_session() as session:
                # Base filter: public and has share token
                query = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.visibility == 'public',
                    UserAgentInstanceORM.share_token.isnot(None)  # Defensive: ensure business invariant
                )

                # Business rule: Exclude orphaned imports
                # Show only: original agents OR imported agents where original still exists
                # Need to alias the table for the subquery to avoid ambiguity
                from sqlalchemy.orm import aliased
                OriginalInstance = aliased(UserAgentInstanceORM)

                query = query.filter(
                    or_(
                        # Original agents (not imported)
                        UserAgentInstanceORM.original_creator_id.is_(None),
                        # Imported agents where original creator still has an instance
                        # Check if there exists any instance owned by the original_creator_id
                        exists(
                            select(1).select_from(OriginalInstance).where(
                                OriginalInstance.user_id == UserAgentInstanceORM.original_creator_id
                            )
                        )
                    )
                )

                # Infrastructure translates domain ordering to SQL
                ordering_map = {
                    InstanceOrdering.CREATED_DESC: UserAgentInstanceORM.created_at.desc(),
                    InstanceOrdering.CREATED_ASC: UserAgentInstanceORM.created_at.asc(),
                    InstanceOrdering.UPDATED_DESC: UserAgentInstanceORM.updated_at.desc(),
                    InstanceOrdering.UPDATED_ASC: UserAgentInstanceORM.updated_at.asc(),
                    InstanceOrdering.NAME_ASC: UserAgentInstanceORM.agent_name.asc(),
                    InstanceOrdering.NAME_DESC: UserAgentInstanceORM.agent_name.desc(),
                }

                order_clause = ordering_map.get(order_by, UserAgentInstanceORM.created_at.desc())
                orm_instances = query.order_by(order_clause).offset(offset).limit(limit).all()

                return [self._model_to_entity(instance) for instance in orm_instances]

        except Exception as e:
            logger.error(f"Error finding public user agent instances: {e}")
            return []

    def is_orphaned(self, instance_id: UserAgentInstanceId) -> bool:
        """Check if an instance is orphaned (imported but original creator deleted their agent).

        An instance is considered orphaned if:
        1. It has an original_creator_id (it's an imported copy)
        2. The original creator's instance no longer exists (was deleted)

        Args:
            instance_id: Instance identifier to check

        Returns:
            True if orphaned, False otherwise (including original agents and active imports)
        """
        try:
            with self.get_db_session() as session:
                instance = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.id == str(instance_id)
                ).first()

                if not instance:
                    logger.debug(f"Instance not found: {instance_id}")
                    return False

                # Not imported (original agent) - not orphaned
                if not instance.original_creator_id:
                    return False

                # Check if original creator (user) still has any instance
                # original_creator_id is a USER ID, not an instance ID
                original_exists = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.user_id == instance.original_creator_id
                ).first() is not None

                # Orphaned if original creator no longer has any instance
                return not original_exists

        except Exception as e:
            logger.error(f"Error checking if instance {instance_id} is orphaned: {e}")
            return False

    def count_by_agent_name_for_user(self, user_id: UserId, agent_name: str) -> int:
        """
        Count instances with a specific name for a user

        Args:
            user_id: User identifier
            agent_name: Agent name to count

        Returns:
            Count of instances with the name
        """
        try:
            with self.get_db_session() as session:
                count = session.query(func.count(UserAgentInstanceORM.id)).filter(
                    and_(
                        UserAgentInstanceORM.user_id == str(user_id),
                        UserAgentInstanceORM.agent_name == agent_name
                    )
                ).scalar()

                return count or 0

        except Exception as e:
            logger.error(f"Error counting user agent instances by name {agent_name} for user {user_id}: {e}")
            return 0

    def delete(self, instance_id: UserAgentInstanceId) -> bool:
        """
        Delete an instance by ID

        Args:
            instance_id: Instance identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.get_db_session() as session:
                deleted_count = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.id == str(instance_id)
                ).delete()

                session.commit()

                if deleted_count > 0:
                    logger.info(f"Deleted user agent instance: {instance_id}")
                    return True
                else:
                    logger.warning(f"User agent instance not found for deletion: {instance_id}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting user agent instance {instance_id}: {e}")
            return False

    def _model_to_entity(self, orm_instance: UserAgentInstanceORM) -> UserAgentInstance:
        """
        Convert ORM model to domain entity (DDD-compliant)

        Args:
            orm_instance: ORM instance

        Returns:
            UserAgentInstance domain entity
        """
        try:
            # Parse JSON fields - handle empty strings
            def safe_json_parse(value, default=None):
                """Safely parse JSON, handling empty strings and None"""
                if not value or (isinstance(value, str) and value.strip() == ''):
                    return default
                if isinstance(value, str):
                    return json.loads(value)
                return value

            tools = safe_json_parse(orm_instance.tools, [])
            capabilities = safe_json_parse(orm_instance.capabilities, {})
            rules = safe_json_parse(orm_instance.rules, None)
            output_format = safe_json_parse(orm_instance.output_format, None)
            metadata_json = safe_json_parse(orm_instance.metadata_json, {})

            # Create configuration value object
            configuration = AgentConfiguration(
                system_prompt=orm_instance.system_prompt,
                tools=tools,
                capabilities=capabilities,
                rules=rules,
                output_format=output_format,
                metadata=metadata_json
            )

            # Ensure last_used_at is timezone-aware (SQLite loses timezone info)
            last_used_at = None
            if hasattr(orm_instance, 'last_used_at') and orm_instance.last_used_at:
                if orm_instance.last_used_at.tzinfo is None:
                    # Assume UTC if no timezone info (SQLite behavior)
                    last_used_at = orm_instance.last_used_at.replace(tzinfo=UTC)
                else:
                    last_used_at = orm_instance.last_used_at

            return UserAgentInstance(
                id=UserAgentInstanceId(orm_instance.id),
                user_id=UserId(orm_instance.user_id),
                template_id=AgentTemplateId(orm_instance.template_id),
                agent_name=orm_instance.agent_name,
                is_customized=orm_instance.is_customized,
                is_enabled=getattr(orm_instance, 'is_enabled', True),
                configuration=configuration,
                visibility=orm_instance.visibility,
                share_token=orm_instance.share_token,
                original_creator_id=UserId(orm_instance.original_creator_id) if orm_instance.original_creator_id else None,
                usage_count=orm_instance.usage_count if hasattr(orm_instance, 'usage_count') else 0,
                last_used_at=last_used_at,
                # Note: customization_notes, share_created_at, imported_at are ORM-only fields
                # They are not part of the domain entity
                created_at=orm_instance.created_at,
                updated_at=orm_instance.updated_at
            )
        except Exception as e:
            logger.error(f"Error converting user agent instance model to entity: {e}")
            raise

    def _entity_to_model_dict(self, instance: UserAgentInstance) -> dict[str, Any]:
        """
        Convert domain entity to model dictionary (DDD-compliant)

        Args:
            instance: UserAgentInstance domain entity

        Returns:
            Dictionary representation for ORM model
        """
        # Extract customization_notes from metadata if present
        customization_notes = None
        if instance.metadata and 'last_customization' in instance.metadata:
            customization_notes = instance.metadata['last_customization'].get('notes')

        # Extract share_created_at and imported_at if present
        # These are ORM-specific fields that may not be in the domain entity yet
        share_created_at = getattr(instance, 'share_created_at', None)
        imported_at = getattr(instance, 'imported_at', None)

        return {
            "id": str(instance.id),
            "user_id": str(instance.user_id),
            "template_id": str(instance.template_id),
            "agent_name": instance.agent_name,
            "is_customized": instance.is_customized,
            "is_enabled": getattr(instance, 'is_enabled', True),
            "customization_notes": customization_notes,
            "system_prompt": instance.configuration.system_prompt,
            "tools": json.dumps(instance.configuration.tools),
            "capabilities": json.dumps(instance.configuration.capabilities),
            "rules": json.dumps(instance.configuration.rules) if instance.configuration.rules else None,
            "output_format": json.dumps(instance.configuration.output_format) if instance.configuration.output_format else None,
            "metadata_json": json.dumps(instance.configuration.metadata) if instance.configuration.metadata else None,
            "visibility": instance.visibility,
            "share_token": instance.share_token,
            "share_created_at": share_created_at,
            "original_creator_id": str(instance.original_creator_id) if instance.original_creator_id else None,
            "imported_at": imported_at,
            "usage_count": instance.usage_count,
            "last_used_at": instance.last_used_at,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at
        }
