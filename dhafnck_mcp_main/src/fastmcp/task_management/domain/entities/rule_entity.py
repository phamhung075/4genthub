"""
Rule Management Domain Entities
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the core domain entities for rule management following DDD principles.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..enums.rule_enums import RuleFormat, RuleType, InheritanceType


@dataclass
class RuleMetadata:
    """Metadata for rule files - Domain Entity"""
    path: str
    format: RuleFormat
    type: RuleType
    size: int
    modified: float
    checksum: str
    dependencies: List[str]
    author: str = "system"
    version: str = "1.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure tags is always a list"""
        if self.tags is None:
            self.tags = []

    def add_tag(self, tag: str) -> None:
        """Add a tag to the metadata"""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the metadata"""
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if metadata has a specific tag"""
        return tag in self.tags

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency"""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def remove_dependency(self, dependency: str) -> None:
        """Remove a dependency"""
        if dependency in self.dependencies:
            self.dependencies.remove(dependency)

    def has_dependency(self, dependency: str) -> bool:
        """Check if rule has a specific dependency"""
        return dependency in self.dependencies


@dataclass
class RuleContent:
    """Structured rule content - Domain Entity"""
    metadata: RuleMetadata
    raw_content: str
    parsed_content: Dict[str, Any]
    sections: Dict[str, str]
    references: List[str]
    variables: Dict[str, Any]

    def get_section(self, section_name: str) -> Optional[str]:
        """Get content of a specific section"""
        return self.sections.get(section_name)

    def set_section(self, section_name: str, content: str) -> None:
        """Set content of a specific section"""
        self.sections[section_name] = content

    def has_section(self, section_name: str) -> bool:
        """Check if rule has a specific section"""
        return section_name in self.sections

    def get_variable(self, variable_name: str, default: Any = None) -> Any:
        """Get value of a specific variable"""
        return self.variables.get(variable_name, default)

    def set_variable(self, variable_name: str, value: Any) -> None:
        """Set value of a specific variable"""
        self.variables[variable_name] = value

    def has_variable(self, variable_name: str) -> bool:
        """Check if rule has a specific variable"""
        return variable_name in self.variables

    def add_reference(self, reference: str) -> None:
        """Add a reference"""
        if reference not in self.references:
            self.references.append(reference)

    def remove_reference(self, reference: str) -> None:
        """Remove a reference"""
        if reference in self.references:
            self.references.remove(reference)

    def has_reference(self, reference: str) -> bool:
        """Check if rule has a specific reference"""
        return reference in self.references

    @property
    def rule_path(self) -> str:
        """Get the rule path from metadata"""
        return self.metadata.path

    @property
    def rule_type(self) -> RuleType:
        """Get the rule type from metadata"""
        return self.metadata.type

    @property
    def rule_format(self) -> RuleFormat:
        """Get the rule format from metadata"""
        return self.metadata.format


@dataclass
class RuleInheritance:
    """Rule inheritance configuration and tracking - Domain Entity"""
    parent_path: str
    child_path: str
    inheritance_type: InheritanceType
    inherited_sections: List[str] = field(default_factory=list)
    overridden_sections: List[str] = field(default_factory=list)
    merged_variables: Dict[str, Any] = field(default_factory=dict)
    inheritance_depth: int = 0
    conflicts: List[str] = field(default_factory=list)

    def add_inherited_section(self, section: str) -> None:
        """Add an inherited section"""
        if section not in self.inherited_sections:
            self.inherited_sections.append(section)

    def add_overridden_section(self, section: str) -> None:
        """Add an overridden section"""
        if section not in self.overridden_sections:
            self.overridden_sections.append(section)

    def add_conflict(self, conflict: str) -> None:
        """Add a conflict"""
        if conflict not in self.conflicts:
            self.conflicts.append(conflict)

    def has_conflicts(self) -> bool:
        """Check if there are any conflicts"""
        return len(self.conflicts) > 0

    def is_section_inherited(self, section: str) -> bool:
        """Check if a section is inherited"""
        return section in self.inherited_sections

    def is_section_overridden(self, section: str) -> bool:
        """Check if a section is overridden"""
        return section in self.overridden_sections

    def merge_variable(self, key: str, value: Any) -> None:
        """Merge a variable"""
        self.merged_variables[key] = value

    def get_merged_variable(self, key: str, default: Any = None) -> Any:
        """Get a merged variable"""
        return self.merged_variables.get(key, default)


@dataclass
class Rule:
    """Main Rule aggregate - Domain Entity"""
    metadata: RuleMetadata
    content: Optional[RuleContent] = None
    inheritance: Optional[RuleInheritance] = None

    def __post_init__(self):
        """Initialize content if not provided"""
        if self.content is None:
            self.content = RuleContent(
                metadata=self.metadata,
                raw_content="",
                parsed_content={},
                sections={},
                references=[],
                variables={}
            ) 