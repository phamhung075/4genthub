"""
ORM User Agent Instance Repository Implementation

This module implements the UserAgentInstance Repository using SQLAlchemy ORM,
providing per-user agent instance management with full database capabilities.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ....domain.entities.user_agent_instance import UserAgentInstance
from ....domain.value_objects.user_agent_instance_id import UserAgentInstanceId
from ....domain.value_objects.agent_template_id import AgentTemplateId
from ....domain.value_objects.user_id import UserId
from ....domain.value_objects.agent_configuration import AgentConfiguration
from ....domain.repositories.user_agent_instance_repository import UserAgentInstanceRepository as UserAgentInstanceRepositoryInterface
from fastmcp.task_management.infrastructure.repositories.base_timestamp_repository import BaseTimestampRepository
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
                    existing.updated_at = datetime.now(timezone.utc)

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

    def find_by_id(self, instance_id: UserAgentInstanceId) -> Optional[UserAgentInstance]:
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
    ) -> Optional[UserAgentInstance]:
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

    def find_by_user(self, user_id: UserId) -> List[UserAgentInstance]:
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

    def find_by_share_token(self, share_token: str) -> Optional[UserAgentInstance]:
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

    def find_public_instances(self, limit: int = 50) -> List[UserAgentInstance]:
        """
        Find public instances (for browsing shared agents)

        Args:
            limit: Maximum number of instances to return

        Returns:
            List of public UserAgentInstance entities
        """
        try:
            with self.get_db_session() as session:
                orm_instances = session.query(UserAgentInstanceORM).filter(
                    UserAgentInstanceORM.visibility == 'public'
                ).order_by(UserAgentInstanceORM.created_at.desc()).limit(limit).all()

                return [self._model_to_entity(instance) for instance in orm_instances]

        except Exception as e:
            logger.error(f"Error finding public user agent instances: {e}")
            return []

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
            # Parse JSON fields
            tools = json.loads(orm_instance.tools) if isinstance(orm_instance.tools, str) else orm_instance.tools
            capabilities = json.loads(orm_instance.capabilities) if isinstance(orm_instance.capabilities, str) else orm_instance.capabilities
            rules = json.loads(orm_instance.rules) if orm_instance.rules and isinstance(orm_instance.rules, str) else (orm_instance.rules if orm_instance.rules else None)
            output_format = json.loads(orm_instance.output_format) if orm_instance.output_format and isinstance(orm_instance.output_format, str) else (orm_instance.output_format if orm_instance.output_format else None)
            metadata = json.loads(orm_instance.metadata_json) if orm_instance.metadata_json and isinstance(orm_instance.metadata_json, str) else (orm_instance.metadata_json if orm_instance.metadata_json else None)

            # Create configuration value object
            configuration = AgentConfiguration(
                system_prompt=orm_instance.system_prompt,
                tools=tools,
                capabilities=capabilities,
                rules=rules,
                output_format=output_format,
                metadata=metadata
            )

            return UserAgentInstance(
                id=UserAgentInstanceId(orm_instance.id),
                user_id=UserId(orm_instance.user_id),
                template_id=AgentTemplateId(orm_instance.template_id),
                agent_name=orm_instance.agent_name,
                is_customized=orm_instance.is_customized,
                customization_notes=orm_instance.customization_notes,
                configuration=configuration,
                visibility=orm_instance.visibility,
                share_token=orm_instance.share_token,
                share_created_at=orm_instance.share_created_at,
                original_creator_id=UserId(orm_instance.original_creator_id) if orm_instance.original_creator_id else None,
                imported_at=orm_instance.imported_at,
                created_at=orm_instance.created_at,
                updated_at=orm_instance.updated_at
            )
        except Exception as e:
            logger.error(f"Error converting user agent instance model to entity: {e}")
            raise

    def _entity_to_model_dict(self, instance: UserAgentInstance) -> Dict[str, Any]:
        """
        Convert domain entity to model dictionary (DDD-compliant)

        Args:
            instance: UserAgentInstance domain entity

        Returns:
            Dictionary representation for ORM model
        """
        return {
            "id": str(instance.id),
            "user_id": str(instance.user_id),
            "template_id": str(instance.template_id),
            "agent_name": instance.agent_name,
            "is_customized": instance.is_customized,
            "customization_notes": instance.customization_notes,
            "system_prompt": instance.configuration.system_prompt,
            "tools": json.dumps(instance.configuration.tools),
            "capabilities": json.dumps(instance.configuration.capabilities),
            "rules": json.dumps(instance.configuration.rules) if instance.configuration.rules else None,
            "output_format": json.dumps(instance.configuration.output_format) if instance.configuration.output_format else None,
            "metadata_json": json.dumps(instance.configuration.metadata) if instance.configuration.metadata else None,
            "visibility": instance.visibility,
            "share_token": instance.share_token,
            "share_created_at": instance.share_created_at,
            "original_creator_id": str(instance.original_creator_id) if instance.original_creator_id else None,
            "imported_at": instance.imported_at,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at
        }
