"""Template Domain Entity"""

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from ..value_objects.template_id import TemplateId
from ..enums.template_enums import TemplateType, TemplateCategory, TemplateStatus, TemplatePriority
from .base.base_timestamp_entity import BaseTimestampEntity


@dataclass
class Template(BaseTimestampEntity):
    """Template domain entity representing a template in the system"""

    id: Optional[TemplateId] = None
    name: str = ""
    description: str = ""
    content: str = ""
    template_type: Optional[TemplateType] = None
    category: Optional[TemplateCategory] = None
    status: Optional[TemplateStatus] = None
    priority: Optional[TemplatePriority] = None
    compatible_agents: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    is_active: bool = True

    def _get_entity_id(self) -> str:
        """Get the unique identifier for this entity."""
        return str(self.id)
    
    def __post_init__(self):
        """Initialize timestamps through BaseTimestampEntity."""
        super().__post_init__()
    
    def _validate_entity(self) -> None:
        """Ensure template invariants hold."""
        if not self.name or not self.name.strip():
            raise ValueError("Template name cannot be empty")
        if not self.content or not self.content.strip():
            raise ValueError("Template content cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Template description cannot be empty")
    
    def update_content(self, content: str) -> None:
        """Update template content and increment version"""
        if not content.strip():
            raise ValueError("Template content cannot be empty")
        self.content = content
        self.version += 1
        self.touch("content_updated")
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update template metadata"""
        self.metadata.update(metadata)
        self.touch("metadata_updated")
    
    def add_compatible_agent(self, agent_name: str) -> None:
        """Add compatible agent to template"""
        if agent_name not in self.compatible_agents:
            self.compatible_agents.append(agent_name)
            self.touch("agent_added")
    
    def remove_compatible_agent(self, agent_name: str) -> None:
        """Remove compatible agent from template"""
        if agent_name in self.compatible_agents:
            self.compatible_agents.remove(agent_name)
            self.touch("agent_removed")
    
    def add_file_pattern(self, pattern: str) -> None:
        """Add file pattern to template"""
        if pattern not in self.file_patterns:
            self.file_patterns.append(pattern)
            self.touch("pattern_added")
    
    def remove_file_pattern(self, pattern: str) -> None:
        """Remove file pattern from template"""
        if pattern in self.file_patterns:
            self.file_patterns.remove(pattern)
            self.touch("pattern_removed")
    
    def add_variable(self, variable: str) -> None:
        """Add variable to template"""
        if variable not in self.variables:
            self.variables.append(variable)
            self.touch("variable_added")
    
    def remove_variable(self, variable: str) -> None:
        """Remove variable from template"""
        if variable in self.variables:
            self.variables.remove(variable)
            self.touch("variable_removed")
    
    def activate(self) -> None:
        """Activate template"""
        self.is_active = True
        self.status = TemplateStatus.ACTIVE
        self.touch("template_activated")
    
    def deactivate(self) -> None:
        """Deactivate template"""
        self.is_active = False
        self.status = TemplateStatus.INACTIVE
        self.touch("template_deactivated")
    
    def archive(self) -> None:
        """Archive template"""
        self.is_active = False
        self.status = TemplateStatus.ARCHIVED
        self.touch("template_archived")
    
    def is_compatible_with_agent(self, agent_name: str) -> bool:
        """Check if template is compatible with given agent"""
        return "*" in self.compatible_agents or agent_name in self.compatible_agents
    
    def matches_file_patterns(self, file_patterns: List[str]) -> bool:
        """Check if template matches any of the given file patterns"""
        if not self.file_patterns:
            return True  # No restrictions
        
        for template_pattern in self.file_patterns:
            for file_pattern in file_patterns:
                if self._pattern_matches(template_pattern, file_pattern):
                    return True
        return False
    
    def _pattern_matches(self, template_pattern: str, file_pattern: str) -> bool:
        """Check if patterns match using fnmatch for wildcard support"""
        return fnmatch.fnmatch(file_pattern, template_pattern)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary representation"""
        return {
            "id": self.id.value,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "template_type": self.template_type.value,
            "category": self.category.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "compatible_agents": self.compatible_agents,
            "file_patterns": self.file_patterns,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """Create template from dictionary representation"""
        # Create the template instance
        template = cls(
            id=TemplateId(data["id"]),
            name=data["name"],
            description=data["description"],
            content=data["content"],
            template_type=TemplateType(data["template_type"]),
            category=TemplateCategory(data["category"]),
            status=TemplateStatus(data["status"]),
            priority=TemplatePriority(data["priority"]),
            compatible_agents=data["compatible_agents"],
            file_patterns=data["file_patterns"],
            variables=data["variables"],
            metadata=data["metadata"],
            version=data.get("version", 1),
            is_active=data.get("is_active", True)
        )

        # Set BaseTimestampEntity timestamps if provided
        if "created_at" in data:
            template.created_at = template._coerce_to_utc(
                datetime.fromisoformat(data["created_at"])
            )
        if "updated_at" in data:
            template.updated_at = template._coerce_to_utc(
                datetime.fromisoformat(data["updated_at"])
            )

        return template


@dataclass
class TemplateResult:
    """Result of template rendering operation"""
    content: str
    template_id: TemplateId
    variables_used: Dict[str, Any]
    generated_at: datetime
    generation_time_ms: int
    cache_hit: bool
    output_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation"""
        return {
            "content": self.content,
            "template_id": self.template_id.value,
            "variables_used": self.variables_used,
            "generated_at": self.generated_at.isoformat(),
            "generation_time_ms": self.generation_time_ms,
            "cache_hit": self.cache_hit,
            "output_path": self.output_path
        }


@dataclass
class TemplateRenderRequest:
    """Request for template rendering"""
    template_id: TemplateId
    variables: Dict[str, Any]
    task_context: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    cache_strategy: str = "default"
    force_regenerate: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary representation"""
        return {
            "template_id": self.template_id.value,
            "variables": self.variables,
            "task_context": self.task_context,
            "output_path": self.output_path,
            "cache_strategy": self.cache_strategy,
            "force_regenerate": self.force_regenerate
        }


@dataclass
class TemplateUsage:
    """Template usage tracking entity"""
    template_id: TemplateId
    task_id: Optional[str]
    project_id: Optional[str]
    agent_name: Optional[str]
    variables_used: Dict[str, Any]
    output_path: Optional[str]
    generation_time_ms: int
    cache_hit: bool
    used_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert usage to dictionary representation"""
        return {
            "template_id": self.template_id.value,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "agent_name": self.agent_name,
            "variables_used": self.variables_used,
            "output_path": self.output_path,
            "generation_time_ms": self.generation_time_ms,
            "cache_hit": self.cache_hit,
            "used_at": self.used_at.isoformat()
        } 
