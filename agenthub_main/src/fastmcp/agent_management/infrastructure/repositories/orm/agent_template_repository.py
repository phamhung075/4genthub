"""
ORM Agent Template Repository Implementation

This module implements the AgentTemplate Repository using SQLAlchemy ORM,
providing agent template management with full database capabilities.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func

from fastmcp.task_management.infrastructure.repositories.base_timestamp_repository import (
    BaseTimestampRepository,
)

from ....domain.entities.agent_template import AgentTemplate
from ....domain.repositories.agent_template_repository import (
    AgentTemplateRepository as AgentTemplateRepositoryInterface,
)
from ....domain.value_objects.agent_configuration import AgentConfiguration
from ....domain.value_objects.agent_template_id import AgentTemplateId
from ...database.models import AgentTemplateORM

logger = logging.getLogger(__name__)


class ORMAgentTemplateRepository(
    BaseTimestampRepository[AgentTemplateORM], AgentTemplateRepositoryInterface
):
    """ORM implementation of agent template repository using SQLAlchemy"""

    def __init__(self):
        """Initialize the ORM agent template repository"""
        super().__init__(AgentTemplateORM)
        logger.debug("Initialized ORMAgentTemplateRepository")

    def save(self, template: AgentTemplate) -> AgentTemplate:
        """
        Save an agent template to the database (DDD-compliant)

        Args:
            template: AgentTemplate entity to save

        Returns:
            Saved AgentTemplate entity

        Raises:
            DatabaseException: If save operation fails
        """
        try:
            with self.get_db_session() as session:
                # Check if template exists
                existing = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.id == str(template.id))
                    .first()
                )

                if existing:
                    # DDD-COMPLIANT: Convert entity to model dict
                    model_dict = self._entity_to_model_dict(template)

                    # Update existing template fields
                    existing.slug = model_dict["slug"]
                    existing.name = model_dict["name"]
                    existing.description = model_dict["description"]
                    existing.category = model_dict["category"]
                    existing.version = model_dict["version"]
                    existing.system_prompt = model_dict["system_prompt"]
                    existing.tools = model_dict["tools"]
                    existing.capabilities = model_dict["capabilities"]
                    existing.rules = model_dict.get("rules")
                    existing.output_format = model_dict.get("output_format")
                    existing.metadata_json = model_dict.get("metadata_json")
                    existing.updated_at = datetime.now(UTC)

                    logger.info(f"Updated agent template: {template.slug}")
                else:
                    # DDD-COMPLIANT: Convert entity to model dict
                    model_dict = self._entity_to_model_dict(template)

                    # Create new template
                    orm_template = AgentTemplateORM(
                        id=model_dict["id"],
                        slug=model_dict["slug"],
                        name=model_dict["name"],
                        description=model_dict["description"],
                        category=model_dict["category"],
                        version=model_dict["version"],
                        system_prompt=model_dict["system_prompt"],
                        tools=model_dict["tools"],
                        capabilities=model_dict["capabilities"],
                        rules=model_dict.get("rules"),
                        output_format=model_dict.get("output_format"),
                        metadata_json=model_dict.get("metadata_json"),
                        created_at=model_dict["created_at"],
                        updated_at=model_dict["updated_at"],
                    )
                    session.add(orm_template)

                    logger.info(f"Created new agent template: {template.slug}")

                session.commit()

                # Fetch and return the saved entity
                saved_orm = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.id == str(template.id))
                    .first()
                )

                return self._model_to_entity(saved_orm)

        except Exception as e:
            logger.error(f"Error saving agent template {template.slug}: {e}")
            raise

    def find_by_id(self, template_id: AgentTemplateId) -> AgentTemplate | None:
        """
        Find a template by its ID

        Args:
            template_id: Template identifier

        Returns:
            AgentTemplate entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_template = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.id == str(template_id))
                    .first()
                )

                if orm_template:
                    return self._model_to_entity(orm_template)
                return None

        except Exception as e:
            logger.error(f"Error finding agent template by id {template_id}: {e}")
            return None

    def find_by_slug(self, slug: str) -> AgentTemplate | None:
        """
        Find a template by its slug

        Args:
            slug: Template slug (e.g., 'coding-agent')

        Returns:
            AgentTemplate entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                orm_template = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.slug == slug)
                    .first()
                )

                if orm_template:
                    return self._model_to_entity(orm_template)
                return None

        except Exception as e:
            logger.error(f"Error finding agent template by slug {slug}: {e}")
            return None

    def find_all(self) -> list[AgentTemplate]:
        """
        Get all agent templates

        Returns:
            List of all AgentTemplate entities
        """
        try:
            with self.get_db_session() as session:
                orm_templates = (
                    session.query(AgentTemplateORM)
                    .order_by(AgentTemplateORM.category, AgentTemplateORM.name)
                    .all()
                )

                return [self._model_to_entity(template) for template in orm_templates]

        except Exception as e:
            logger.error(f"Error finding all agent templates: {e}")
            return []

    def find_by_category(self, category: str) -> list[AgentTemplate]:
        """
        Find templates by category

        Args:
            category: Category to filter by (e.g., 'development', 'testing')

        Returns:
            List of AgentTemplate entities in the category
        """
        try:
            with self.get_db_session() as session:
                orm_templates = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.category == category)
                    .order_by(AgentTemplateORM.name)
                    .all()
                )

                return [self._model_to_entity(template) for template in orm_templates]

        except Exception as e:
            logger.error(f"Error finding agent templates by category {category}: {e}")
            return []

    def exists_by_slug(self, slug: str) -> bool:
        """
        Check if a template exists by slug

        Args:
            slug: Template slug to check

        Returns:
            True if exists, False otherwise
        """
        try:
            with self.get_db_session() as session:
                count = (
                    session.query(func.count(AgentTemplateORM.id))
                    .filter(AgentTemplateORM.slug == slug)
                    .scalar()
                )

                return count > 0

        except Exception as e:
            logger.error(f"Error checking if agent template exists by slug {slug}: {e}")
            return False

    def delete(self, template_id: AgentTemplateId) -> bool:
        """
        Delete a template by ID

        Args:
            template_id: Template identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.get_db_session() as session:
                deleted_count = (
                    session.query(AgentTemplateORM)
                    .filter(AgentTemplateORM.id == str(template_id))
                    .delete()
                )

                session.commit()

                if deleted_count > 0:
                    logger.info(f"Deleted agent template: {template_id}")
                    return True
                else:
                    logger.warning(
                        f"Agent template not found for deletion: {template_id}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error deleting agent template {template_id}: {e}")
            return False

    def _model_to_entity(self, orm_template: AgentTemplateORM) -> AgentTemplate:
        """
        Convert ORM model to domain entity (DDD-compliant)

        Args:
            orm_template: ORM template instance

        Returns:
            AgentTemplate domain entity
        """
        try:
            # Parse JSON fields
            tools = (
                json.loads(orm_template.tools)
                if isinstance(orm_template.tools, str)
                else orm_template.tools
            )
            capabilities = (
                json.loads(orm_template.capabilities)
                if isinstance(orm_template.capabilities, str)
                else orm_template.capabilities
            )
            rules = (
                json.loads(orm_template.rules)
                if orm_template.rules and isinstance(orm_template.rules, str)
                else (orm_template.rules if orm_template.rules else None)
            )
            output_format = (
                json.loads(orm_template.output_format)
                if orm_template.output_format
                and isinstance(orm_template.output_format, str)
                else (
                    orm_template.output_format if orm_template.output_format else None
                )
            )
            metadata = (
                json.loads(orm_template.metadata_json)
                if orm_template.metadata_json
                and isinstance(orm_template.metadata_json, str)
                else (
                    orm_template.metadata_json if orm_template.metadata_json else None
                )
            )

            # Create default_configuration value object
            default_configuration = AgentConfiguration(
                system_prompt=orm_template.system_prompt,
                tools=tools,
                capabilities=capabilities,
                rules=rules,
                output_format=output_format,
                metadata=metadata,
            )

            return AgentTemplate(
                id=AgentTemplateId(orm_template.id),
                slug=orm_template.slug,
                name=orm_template.name,
                description=orm_template.description,
                category=orm_template.category,
                version=orm_template.version,
                default_configuration=default_configuration,
                metadata=metadata or {},
                created_at=orm_template.created_at,
                updated_at=orm_template.updated_at,
            )
        except Exception as e:
            logger.error(f"Error converting agent template model to entity: {e}")
            raise

    def _entity_to_model_dict(self, template: AgentTemplate) -> dict[str, Any]:
        """
        Convert domain entity to model dictionary (DDD-compliant)

        Args:
            template: AgentTemplate domain entity

        Returns:
            Dictionary representation for ORM model
        """
        return {
            "id": str(template.id),
            "slug": template.slug,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "version": template.version,
            "system_prompt": template.default_configuration.system_prompt,
            "tools": json.dumps(template.default_configuration.tools),
            "capabilities": json.dumps(template.default_configuration.capabilities),
            "rules": json.dumps(template.default_configuration.rules)
            if template.default_configuration.rules
            else None,
            "output_format": json.dumps(template.default_configuration.output_format)
            if template.default_configuration.output_format
            else None,
            "metadata_json": json.dumps(template.metadata)
            if template.metadata
            else None,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
