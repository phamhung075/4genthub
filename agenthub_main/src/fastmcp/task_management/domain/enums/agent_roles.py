"""
Agent Roles Enum - Updated to match agent-library
Updated on: 2025-09-11
Total agents: 32

This file contains all available agent roles from agenthub_main/agent-library/agents.
Manually updated to match actual agent directories.
"""

from enum import Enum
from typing import List, Dict, Optional
import os
import yaml


class AgentRole(Enum):
    """Enumeration of all available agent roles - matches agenthub_main/agent-library/agents"""
    
    # Development & Coding (4)
    ANALYTICS_SETUP = "analytics-setup-agent"
    CODING = "coding-agent"
    CODE_REVIEWER = "code-reviewer-agent"
    DEBUGGER = "debugger-agent"
    
    # Architecture & Design (4)
    CORE_CONCEPT = "core-concept-agent"
    DESIGN_SYSTEM = "design-system-agent"
    SYSTEM_ARCHITECT = "system-architect-agent"
    UI_SPECIALIST = "ui-specialist-agent"
    
    # Testing & QA (3)
    PERFORMANCE_LOAD_TESTER = "performance-load-tester-agent"
    TEST_ORCHESTRATOR = "test-orchestrator-agent"
    UAT_COORDINATOR = "uat-coordinator-agent"
    
    # DevOps & Infrastructure (1)
    DEVOPS = "devops-agent"
    
    # Documentation (1)
    DOCUMENTATION = "documentation-agent"
    
    # Project & Planning (4)
    ELICITATION = "elicitation-agent"
    MASTER_ORCHESTRATOR = "master-orchestrator-agent"
    PROJECT_INITIATOR = "project-initiator-agent"
    TASK_PLANNING = "task-planning-agent"
    
    # Security & Compliance (3)
    COMPLIANCE_SCOPE = "compliance-scope-agent"
    ETHICAL_REVIEW = "ethical-review-agent"
    SECURITY_AUDITOR = "security-auditor-agent"
    
    # Analytics & Optimization (2)
    EFFICIENCY_OPTIMIZATION = "efficiency-optimization-agent"
    HEALTH_MONITOR = "health-monitor-agent"
    
    # Marketing & Branding (3)
    BRANDING = "branding-agent"
    COMMUNITY_STRATEGY = "community-strategy-agent"
    MARKETING_STRATEGY_ORCHESTRATOR = "marketing-strategy-orchestrator-agent"
    
    # Research & Analysis (4)
    DEEP_RESEARCH = "deep-research-agent"
    LLM_AI_AGENTS_RESEARCH = "llm-ai-agents-research"
    ROOT_CAUSE_ANALYSIS = "root-cause-analysis-agent"
    TECHNOLOGY_ADVISOR = "technology-advisor-agent"
    
    # AI & Machine Learning (1)
    ML_SPECIALIST = "ml-specialist-agent"
    
    # Creative & Ideation (1)
    CREATIVE_IDEATION = "creative-ideation-agent"
    
    # Prototyping (1)
    PROTOTYPING = "prototyping-agent"


    @classmethod
    def get_all_roles(cls) -> List[str]:
        """Get list of all available role slugs"""
        return [role.value for role in cls]
    
    @classmethod
    def get_role_by_slug(cls, slug: str) -> Optional['AgentRole']:
        """Get role enum by slug"""
        for role in cls:
            if role.value == slug:
                return role
        return None
    
    @classmethod
    def is_valid_role(cls, slug: str) -> bool:
        """Check if a slug is a valid role"""
        return slug in cls.get_all_roles()
    
    @property
    def folder_name(self) -> str:
        """Get the folder name for this role"""
        return self.value.replace('-', '_')
    
    @property
    def display_name(self) -> str:
        """Get the display name for this role"""
        metadata = get_role_metadata_from_yaml(self)
        return metadata.get("name", "") if metadata else ""
    
    @property
    def description(self) -> str:
        """Get the role definition"""
        metadata = get_role_metadata_from_yaml(self)
        return metadata.get("role_definition", "") if metadata else ""
    
    @property
    def when_to_use(self) -> str:
        """Get usage guidelines"""
        metadata = get_role_metadata_from_yaml(self)
        return metadata.get("when_to_use", "") if metadata else ""
    
    @property
    def groups(self) -> List[str]:
        """Get role groups"""
        metadata = get_role_metadata_from_yaml(self)
        return metadata.get("groups", []) if metadata else []


# Metadata for each role - now loaded dynamically from YAML files


# Convenience functions for backward compatibility
def get_supported_roles() -> List[str]:
    """Get list of supported roles for rule generation"""
    return AgentRole.get_all_roles()


def get_role_metadata(role_slug: str) -> Optional[Dict[str, any]]:
    """Get metadata for a specific role"""
    return get_role_metadata_from_yaml(role_slug)


def get_role_folder_name(role_slug: str) -> Optional[str]:
    """Get folder name for a role slug"""
    role = AgentRole.get_role_by_slug(role_slug)
    if role:
        return role.folder_name
    return None


def get_yaml_lib_path(role_input) -> Optional[str]:
    """Get relative path to agent-library directory for a role
    
    Args:
        role_input: Either a role slug (string) or AgentRole enum
        
    Returns:
        Relative path to agent-library directory (e.g., "agent-library/coding-agent")
        or None if role is invalid
    """
    if isinstance(role_input, str):
        role = AgentRole.get_role_by_slug(role_input)
    elif isinstance(role_input, AgentRole):
        role = role_input
    else:
        return None
    
    if role:
        return f"cursor_agent/agent-library/{role.folder_name}"
    return None


def get_role_metadata_from_yaml(role_input) -> Optional[Dict[str, any]]:
    """Get role metadata by reading from YAML files
    
    Args:
        role_input: Either a role slug (string) or AgentRole enum
        
    Returns:
        Dictionary containing role metadata or None if role is invalid or file not found
    """
    if isinstance(role_input, str):
        role = AgentRole.get_role_by_slug(role_input)
    elif isinstance(role_input, AgentRole):
        role = role_input
    else:
        return None
    
    if not role:
        return None
    
    # Calculate folder name from role slug
    folder_name = role.value.replace('-', '_')
    
    # Build path to job_desc.yaml file
    yaml_path = os.path.join("cursor_agent", "agent-library", folder_name, "job_desc.yaml")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
            
        if yaml_data:
            # Add folder_name and slug to the metadata
            yaml_data['folder_name'] = folder_name
            yaml_data['slug'] = role.value
            return yaml_data
            
    except (FileNotFoundError, yaml.YAMLError, IOError):
        # Return None if file doesn't exist or can't be parsed
        pass
    
    return None


# Legacy role mappings for backward compatibility
LEGACY_ROLE_MAPPINGS = {
    "senior_developer": "coding-agent",
    "platform_engineer": "devops-agent",
    "qa_engineer": "test-orchestrator-agent",  # Fixed: functional_tester_agent doesn't exist
    "code_reviewer": "code-reviewer-agent",
    "devops_engineer": "devops-agent",
    "security_engineer": "security-auditor-agent",
    "technical_writer": "documentation-agent",
    "task_planner": "task-planning-agent",
    "context_engineer": "core-concept-agent",
    "cache_engineer": "efficiency-optimization-agent",
    "metrics_engineer": "analytics-setup-agent",
    "cli_engineer": "coding-agent"
}


def resolve_legacy_role(legacy_role: str) -> Optional[str]:
    """Resolve legacy role names to current slugs"""
    if not legacy_role:
        return None
    
    # Clean up the role name (remove @ prefix, strip whitespace)
    clean_role = legacy_role.strip().lstrip('@')
    
    # First check if it's already a valid role
    if AgentRole.is_valid_role(clean_role):
        return clean_role
    
    # Check legacy mappings
    resolved = LEGACY_ROLE_MAPPINGS.get(clean_role)
    if resolved:
        # Validate that the resolved role is actually valid
        if AgentRole.is_valid_role(resolved):
            return resolved
    
    # Try converting hyphens to underscores for common variants
    underscore_variant = clean_role.replace('-', '_')
    if AgentRole.is_valid_role(underscore_variant):
        return underscore_variant
    
    # Try converting underscores to hyphens (less common but possible)
    hyphen_variant = clean_role.replace('_', '-')
    if AgentRole.is_valid_role(hyphen_variant):
        return hyphen_variant
    
    # Return None if no valid resolution found
    return None


def get_all_role_slugs_with_legacy() -> List[str]:
    """Get all role slugs including legacy mappings"""
    current_roles = AgentRole.get_all_roles()
    legacy_roles = list(LEGACY_ROLE_MAPPINGS.keys())
    return current_roles + legacy_roles


