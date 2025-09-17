"""
Global Context Nested Category Schema Definition

This module defines the nested categorization structure for global context data
using a modern hierarchical organization.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


@dataclass
class NestedCategorySchema:
    """Schema definition for nested global context categories."""
    
    # Core organizational categories
    ORGANIZATION: str = "organization"
    DEVELOPMENT: str = "development"
    SECURITY: str = "security"
    OPERATIONS: str = "operations"
    PREFERENCES: str = "preferences"
    
    # Nested subcategories
    NESTED_STRUCTURE = {
        "organization": {
            "standards": {
                "description": "Coding style, git workflow, testing requirements",
                "fields": ["coding_standards", "git_workflow", "testing_requirements", "documentation_standards"]
            },
            "compliance": {
                "description": "Regulatory and compliance requirements",
                "fields": ["gdpr", "hipaa", "soc2", "iso27001", "custom_compliance"]
            },
            "policies": {
                "description": "Organizational policies and procedures",
                "fields": ["code_review_policy", "deployment_policy", "incident_response", "data_retention"]
            }
        },
        "development": {
            "patterns": {
                "description": "Reusable design patterns and code templates",
                "fields": ["design_patterns", "code_templates", "architecture_patterns", "api_patterns"]
            },
            "tools": {
                "description": "Development tools and configurations",
                "fields": ["ide_settings", "linters", "formatters", "build_tools", "testing_frameworks"]
            },
            "workflows": {
                "description": "Development workflows and automation",
                "fields": ["ci_cd_workflows", "deployment_workflows", "testing_workflows", "review_workflows"]
            }
        },
        "security": {
            "authentication": {
                "description": "Authentication and authorization settings",
                "fields": ["auth_providers", "token_management", "session_config", "multi_factor_auth"]
            },
            "encryption": {
                "description": "Encryption and cryptographic settings",
                "fields": ["encryption_algorithms", "key_management", "certificate_management", "secure_communication"]
            },
            "access_control": {
                "description": "Access control and permissions",
                "fields": ["role_definitions", "permission_matrix", "resource_access", "api_security"]
            }
        },
        "operations": {
            "resources": {
                "description": "Shared operational resources",
                "fields": ["api_keys", "service_accounts", "shared_credentials", "external_services"]
            },
            "monitoring": {
                "description": "Monitoring and observability",
                "fields": ["logging_config", "metrics_collection", "alerting_rules", "dashboard_config"]
            },
            "deployment": {
                "description": "Deployment and infrastructure settings",
                "fields": ["environment_config", "container_settings", "cloud_resources", "backup_strategies"]
            }
        },
        "preferences": {
            "user_interface": {
                "description": "User interface preferences and settings",
                "fields": ["theme", "layout", "notifications", "dashboard_widgets"]
            },
            "agent_behavior": {
                "description": "AI agent behavior and interaction preferences",
                "fields": ["response_style", "automation_level", "context_awareness", "learning_preferences"]
            },
            "workflow": {
                "description": "Personal workflow preferences",
                "fields": ["task_organization", "priority_handling", "time_management", "collaboration_style"]
            }
        }
    }
    
    @classmethod
    def get_category_path(cls, category: str, subcategory: str = None) -> str:
        """Get the path for a nested category."""
        if subcategory:
            return f"{category}.{subcategory}"
        return category
    
    @classmethod
    def validate_category_path(cls, path: str) -> bool:
        """Validate that a category path exists in the schema."""
        parts = path.split(".")
        if len(parts) == 1:
            return parts[0] in cls.NESTED_STRUCTURE
        elif len(parts) == 2:
            category, subcategory = parts
            return (category in cls.NESTED_STRUCTURE and 
                   subcategory in cls.NESTED_STRUCTURE.get(category, {}))
        return False
    
    @classmethod
    def get_all_paths(cls) -> List[str]:
        """Get all valid category paths."""
        paths = []
        for category, subcategories in cls.NESTED_STRUCTURE.items():
            paths.append(category)
            for subcategory in subcategories.keys():
                paths.append(f"{category}.{subcategory}")
        return paths
    
    @classmethod
    def get_field_category(cls, field_name: str) -> Optional[str]:
        """Find which category a field belongs to based on the schema."""
        for category, subcategories in cls.NESTED_STRUCTURE.items():
            for subcategory, config in subcategories.items():
                if field_name in config.get("fields", []):
                    return f"{category}.{subcategory}"
        return None


@dataclass
class GlobalContextNestedData:
    """Nested data structure for global context."""
    
    # Organized nested categories
    organization: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "standards": {},
        "compliance": {},
        "policies": {}
    })
    
    development: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "patterns": {},
        "tools": {},
        "workflows": {}
    })
    
    security: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "authentication": {},
        "encryption": {},
        "access_control": {}
    })
    
    operations: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "resources": {},
        "monitoring": {},
        "deployment": {}
    })
    
    preferences: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "user_interface": {},
        "agent_behavior": {},
        "workflow": {}
    })
    
    # Metadata for tracking versioning
    _schema_version: str = "2.0"
    _custom_categories: Dict[str, Any] = field(default_factory=dict)
    
    def set_nested_value(self, path: str, value: Any) -> None:
        """Set a value in the nested structure using dot notation."""
        parts = path.split(".")
        if len(parts) == 2:
            category, subcategory = parts
            if hasattr(self, category):
                getattr(self, category)[subcategory] = value
        elif len(parts) == 3:
            category, subcategory, field = parts
            if hasattr(self, category):
                category_data = getattr(self, category)
                if subcategory not in category_data:
                    category_data[subcategory] = {}
                category_data[subcategory][field] = value
    
    def get_nested_value(self, path: str, default: Any = None) -> Any:
        """Get a value from the nested structure using dot notation."""
        parts = path.split(".")
        if len(parts) == 2:
            category, subcategory = parts
            if hasattr(self, category):
                return getattr(self, category).get(subcategory, default)
        elif len(parts) == 3:
            category, subcategory, field = parts
            if hasattr(self, category):
                category_data = getattr(self, category)
                return category_data.get(subcategory, {}).get(field, default)
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "organization": self.organization,
            "development": self.development,
            "security": self.security,
            "operations": self.operations,
            "preferences": self.preferences,
            "_schema_version": self._schema_version,
            "_custom_categories": self._custom_categories
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalContextNestedData':
        """Create from dictionary representation."""
        instance = cls()
        instance.organization = data.get("organization", instance.organization)
        instance.development = data.get("development", instance.development)
        instance.security = data.get("security", instance.security)
        instance.operations = data.get("operations", instance.operations)
        instance.preferences = data.get("preferences", instance.preferences)
        instance._schema_version = data.get("_schema_version", "2.0")
        
        instance._custom_categories = data.get("_custom_categories", {})
        return instance
