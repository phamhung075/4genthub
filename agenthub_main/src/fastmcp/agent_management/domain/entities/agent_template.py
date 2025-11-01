"""AgentTemplate Domain Entity - Immutable Template for Agent Instances"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import yaml
import logging

from fastmcp.task_management.domain.entities.base.base_timestamp_entity import BaseTimestampEntity
from ..value_objects.agent_template_id import AgentTemplateId
from ..value_objects.agent_configuration import AgentConfiguration

logger = logging.getLogger(__name__)


@dataclass
class AgentTemplate(BaseTimestampEntity):
    """Immutable template for agent instances loaded from agent-library.

    This entity represents the source-of-truth configuration for an agent type.
    All user instances are derived from these templates. Templates are immutable
    once loaded from agent-library YAML files.

    Attributes:
        id: Unique identifier for this template (UUID)
        slug: URL-friendly identifier (e.g., 'coding-agent')
        name: Human-readable name (e.g., 'Coding Agent')
        category: Agent category (e.g., 'development', 'testing')
        description: Brief description of agent's purpose
        version: Template version string (e.g., '1.0.0')
        default_configuration: Default agent configuration (JSONB in DB)
        metadata: Additional metadata about the template

    DDD Patterns:
        - Aggregate root for template data
        - Immutable after creation (templates don't change)
        - Factory method from_yaml() for loading from agent-library
        - Value objects for structured data (AgentConfiguration)
    """

    id: Optional[AgentTemplateId] = None
    slug: str = ""
    name: str = ""
    category: str = ""
    description: str = ""
    version: str = "1.0.0"
    default_configuration: Optional[AgentConfiguration] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize timestamps and validate entity."""
        # Ensure default_configuration is an AgentConfiguration instance
        if self.default_configuration is None:
            raise ValueError("AgentTemplate must have a default_configuration")

        if isinstance(self.default_configuration, dict):
            object.__setattr__(
                self,
                'default_configuration',
                AgentConfiguration.from_dict(self.default_configuration)
            )

        # Call parent initialization for timestamps
        super().__post_init__()

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity.

        Returns:
            str: String representation of the template ID
        """
        return str(self.id) if self.id else "unknown"

    def _validate_entity(self) -> None:
        """Validate template business rules (invariants).

        Raises:
            ValueError: If any business rules are violated
        """
        if not self.slug or not self.slug.strip():
            raise ValueError("AgentTemplate slug cannot be empty")

        if not self.name or not self.name.strip():
            raise ValueError("AgentTemplate name cannot be empty")

        if not self.category or not self.category.strip():
            raise ValueError("AgentTemplate category cannot be empty")

        if not self.version or not self.version.strip():
            raise ValueError("AgentTemplate version cannot be empty")

        if self.default_configuration is None:
            raise ValueError("AgentTemplate must have default_configuration")

        # Validate slug format (lowercase, alphanumeric, hyphens only)
        if not all(c.isalnum() or c in ('-', '_') for c in self.slug):
            raise ValueError(
                f"AgentTemplate slug '{self.slug}' contains invalid characters. "
                "Only lowercase letters, numbers, hyphens, and underscores allowed."
            )

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str,
        template_id: Optional[AgentTemplateId] = None
    ) -> "AgentTemplate":
        """Create AgentTemplate from YAML file in agent-library.

        This is the primary factory method for loading templates from the
        agent-library YAML format.

        Args:
            yaml_path: Path to the YAML file
            template_id: Optional template ID (generates new if not provided)

        Returns:
            AgentTemplate instance loaded from YAML

        Raises:
            ValueError: If YAML is invalid or missing required fields
            FileNotFoundError: If YAML file doesn't exist
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Agent template YAML not found: {yaml_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_path}: {e}")

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict in YAML, got {type(data)}")

        # Extract required fields
        slug = data.get('slug') or data.get('name', '').lower().replace(' ', '-')
        name = data.get('name')
        if not name:
            raise ValueError(f"Agent template YAML missing 'name' field: {yaml_path}")

        # Build configuration from YAML structure
        config_data = {
            "system_prompt": data.get('system_prompt', ''),
            "tools": data.get('tools', []),
            "capabilities": data.get('capabilities', {}),
            "rules": data.get('rules', []),
            "output_format": data.get('output_format', {}),
            "metadata": data.get('metadata', {})
        }

        configuration = AgentConfiguration.from_dict(config_data)

        # Create template
        return cls(
            id=template_id or AgentTemplateId.generate_new(),
            slug=slug,
            name=name,
            category=data.get('category', 'general'),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            default_configuration=configuration,
            metadata={
                "source_file": yaml_path,
                **data.get('metadata', {})
            }
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Create AgentTemplate from dictionary (e.g., from database).

        Args:
            data: Dictionary containing template data

        Returns:
            AgentTemplate instance
        """
        template_id = None
        if 'id' in data and data['id']:
            template_id = (
                data['id'] if isinstance(data['id'], AgentTemplateId)
                else AgentTemplateId.from_string(str(data['id']))
            )

        # Handle configuration
        config = data.get('default_configuration')
        if isinstance(config, dict):
            configuration = AgentConfiguration.from_dict(config)
        elif isinstance(config, AgentConfiguration):
            configuration = config
        else:
            raise ValueError("Invalid default_configuration format")

        return cls(
            id=template_id,
            slug=data.get('slug', ''),
            name=data.get('name', ''),
            category=data.get('category', ''),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            default_configuration=configuration,
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for storage/serialization.

        Returns:
            Dictionary representation including all fields
        """
        return {
            "id": str(self.id) if self.id else None,
            "slug": self.slug,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "version": self.version,
            "default_configuration": self.default_configuration.to_dict() if self.default_configuration else {},
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def matches_slug(self, slug: str) -> bool:
        """Check if this template matches the given slug.

        Args:
            slug: Slug to match against

        Returns:
            bool: True if slugs match (case-insensitive)
        """
        return self.slug.lower() == slug.lower()

    def get_configuration_copy(self) -> AgentConfiguration:
        """Get a copy of the default configuration.

        Returns:
            AgentConfiguration: Copy of the default configuration
        """
        if not self.default_configuration:
            raise ValueError("Template has no default configuration")

        return AgentConfiguration.from_dict(self.default_configuration.to_dict())

    def __repr__(self) -> str:
        """String representation of the template."""
        return (
            f"AgentTemplate("
            f"id={self.id}, "
            f"slug='{self.slug}', "
            f"name='{self.name}', "
            f"category='{self.category}', "
            f"version='{self.version}')"
        )
