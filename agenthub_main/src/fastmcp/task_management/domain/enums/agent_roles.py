"""Agent Roles Enum"""

from enum import Enum
from typing import Optional


class AgentRole(Enum):
    """Enumeration of all available agent roles"""

    # Development & Coding (4)
    ANALYTICS_SETUP = "analytics-setup-agent"
    CODING = "coding-agent"
    CODE_REVIEWER = "code-reviewer-agent"
    DEBUGGER = "debugger-agent"

    # Architecture & Design (4)
    CORE_CONCEPT = "core-concept-agent"
    DESIGN_SYSTEM = "design-system-agent"
    SYSTEM_ARCHITECT = "system-architect-agent"
    UI_SPECIALIST = "shadcn-ui-expert-agent"

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
    def get_all_roles(cls) -> list[str]:
        """Get list of all available role slugs"""
        return [role.value for role in cls]

    @classmethod
    def get_role_by_slug(cls, slug: str) -> Optional["AgentRole"]:
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
        return self.value.replace("-", "_")

    @property
    def display_name(self) -> str:
        """Get the display name for this role"""
        return self.value.replace("-", " ").title()

    @property
    def description(self) -> str:
        """Get the role definition"""
        return ""

    @property
    def when_to_use(self) -> str:
        """Get usage guidelines"""
        return ""

    @property
    def groups(self) -> list[str]:
        """Get role groups"""
        return []


# Convenience functions for backward compatibility
def get_supported_roles() -> list[str]:
    """Get list of supported roles for rule generation"""
    return AgentRole.get_all_roles()


def get_role_folder_name(role_slug: str) -> str | None:
    """Get folder name for a role slug"""
    role = AgentRole.get_role_by_slug(role_slug)
    if role:
        return role.folder_name
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
    "cli_engineer": "coding-agent",
}


def resolve_legacy_role(legacy_role: str) -> str | None:
    """Resolve legacy role names to current slugs"""
    if not legacy_role:
        return None

    # Clean up the role name (remove @ prefix, strip whitespace)
    clean_role = legacy_role.strip().lstrip("@")

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
    underscore_variant = clean_role.replace("-", "_")
    if AgentRole.is_valid_role(underscore_variant):
        return underscore_variant

    # Try converting underscores to hyphens (less common but possible)
    hyphen_variant = clean_role.replace("_", "-")
    if AgentRole.is_valid_role(hyphen_variant):
        return hyphen_variant

    # Return None if no valid resolution found
    return None


def get_all_role_slugs_with_legacy() -> list[str]:
    """Get all role slugs including legacy mappings"""
    current_roles = AgentRole.get_all_roles()
    legacy_roles = list(LEGACY_ROLE_MAPPINGS.keys())
    return current_roles + legacy_roles
