"""
Global Context Validation and Error Handling

This module provides comprehensive validation for the nested global context structure,
including schema validation, data consistency checks, and migration validation.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
import jsonschema
from jsonschema import validate, ValidationError

from ...domain.entities.global_context_schema import (
    NestedCategorySchema, 
    GlobalContextNestedData
)
from ...domain.entities.context import GlobalContext

logger = logging.getLogger(__name__)

# Migration field mapping (default mapping if not imported)
MIGRATION_FIELD_MAPPING = {
    "organization_standards": "organization.standards",
    "organization_policies": "organization.policies",
    "development_patterns": "development.patterns",
    "development_tools": "development.tools",
    "security_authentication": "security.authentication",
    "security_encryption": "security.encryption",
    "operations_resources": "operations.resources",
    "operations_monitoring": "operations.monitoring",
    "preferences_user_interface": "preferences.user_interface",
    "preferences_agent_behavior": "preferences.agent_behavior"
}


class GlobalContextValidationError(Exception):
    """Exception raised when global context validation fails."""
    
    def __init__(self, message: str, errors: List[str] = None, field: str = None):
        self.message = message
        self.errors = errors or []
        self.field = field
        super().__init__(message)


class GlobalContextValidator:
    """Comprehensive validator for global context data and operations."""
    
    def __init__(self):
        self.schema = NestedCategorySchema()
        self._nested_schema = self._create_nested_json_schema()
        self._flat_schema = self._create_flat_json_schema()
    
    def _create_nested_json_schema(self) -> Dict[str, Any]:
        """Create JSON schema for nested global context structure."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Global Context Nested Structure Schema",
            "description": "Schema for nested global context categorization",
            "required": ["organization", "development", "security", "operations", "preferences"],
            "properties": {
                "organization": {
                    "type": "object",
                    "properties": {
                        "standards": {
                            "type": "object",
                            "description": "Coding standards and requirements"
                        },
                        "compliance": {
                            "type": "object", 
                            "description": "Regulatory and compliance requirements"
                        },
                        "policies": {
                            "type": "object",
                            "description": "Organizational policies and procedures"
                        }
                    }
                },
                "development": {
                    "type": "object",
                    "properties": {
                        "patterns": {
                            "type": "object",
                            "description": "Reusable design patterns and templates"
                        },
                        "tools": {
                            "type": "object",
                            "description": "Development tools and configurations"
                        },
                        "workflows": {
                            "type": "object",
                            "description": "Development workflows and automation"
                        }
                    }
                },
                "security": {
                    "type": "object",
                    "properties": {
                        "authentication": {
                            "type": "object",
                            "description": "Authentication and authorization settings"
                        },
                        "encryption": {
                            "type": "object",
                            "description": "Encryption and cryptographic settings"
                        },
                        "access_control": {
                            "type": "object",
                            "description": "Access control and permissions"
                        }
                    }
                },
                "operations": {
                    "type": "object",
                    "properties": {
                        "resources": {
                            "type": "object",
                            "description": "Shared operational resources"
                        },
                        "monitoring": {
                            "type": "object",
                            "description": "Monitoring and observability"
                        },
                        "deployment": {
                            "type": "object",
                            "description": "Deployment and infrastructure settings"
                        }
                    }
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "user_interface": {
                            "type": "object",
                            "description": "User interface preferences"
                        },
                        "agent_behavior": {
                            "type": "object",
                            "description": "AI agent behavior preferences"
                        },
                        "workflow": {
                            "type": "object",
                            "description": "Personal workflow preferences"
                        }
                    }
                },
                "_schema_version": {
                    "type": "string",
                    "enum": ["2.0"]
                },
                "_migrated_from": {
                    "type": ["string", "null"]
                },
                "_migration_timestamp": {
                    "type": ["string", "null"],
                    "format": "date-time"
                },
                "_custom_categories": {
                    "type": "object"
                }
            },
            "additionalProperties": False
        }
    
    def _create_flat_json_schema(self) -> Dict[str, Any]:
        """Create JSON schema for flat global context structure."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Global Context Flat Structure Schema",
            "description": "Schema for legacy flat global context structure",
            "properties": {
                "id": {"type": "string"},
                "organization_name": {"type": "string"},
                "global_settings": {
                    "type": "object",
                    "properties": {
                        "organization_standards": {"type": "object"},
                        "security_policies": {"type": "object"},
                        "compliance_requirements": {"type": "object"},
                        "shared_resources": {"type": "object"},
                        "reusable_patterns": {"type": "object"},
                        "global_preferences": {"type": "object"},
                        "user_preferences": {"type": "object"},
                        "delegation_rules": {"type": "object"}
                    }
                },
                "metadata": {"type": "object"}
            },
            "required": ["id", "global_settings"],
            "additionalProperties": True
        }
    
    def validate_nested_structure(self, nested_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate nested global context structure.
        
        Args:
            nested_data: Nested structure data to validate
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        try:
            validate(instance=nested_data, schema=self._nested_schema)
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            if e.absolute_path:
                errors.append(f"Path: {'.'.join(str(p) for p in e.absolute_path)}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        # Additional semantic validation
        semantic_errors = self._validate_nested_semantics(nested_data)
        errors.extend(semantic_errors)
        
        return len(errors) == 0, errors
    
    def validate_flat_structure(self, flat_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate flat global context structure.
        
        Args:
            flat_data: Flat structure data to validate
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        try:
            validate(instance=flat_data, schema=self._flat_schema)
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        # Additional semantic validation
        semantic_errors = self._validate_flat_semantics(flat_data)
        errors.extend(semantic_errors)
        
        return len(errors) == 0, errors
    
    def _validate_nested_semantics(self, nested_data: Dict[str, Any]) -> List[str]:
        """Validate semantic correctness of nested structure."""
        errors = []
        
        # Validate schema version
        schema_version = nested_data.get("_schema_version")
        if schema_version != "2.0":
            errors.append(f"Invalid schema version: {schema_version}, expected '2.0'")
        
        # Validate category completeness
        required_categories = ["organization", "development", "security", "operations", "preferences"]
        for category in required_categories:
            if category not in nested_data:
                errors.append(f"Missing required category: {category}")
            else:
                category_data = nested_data[category]
                if not isinstance(category_data, dict):
                    errors.append(f"Category {category} must be an object")
        
        # Validate subcategory structure
        expected_subcategories = self.schema.NESTED_STRUCTURE
        for category, subcategories in expected_subcategories.items():
            if category in nested_data:
                category_data = nested_data[category]
                for subcategory in subcategories.keys():
                    if subcategory in category_data:
                        subcategory_data = category_data[subcategory]
                        if not isinstance(subcategory_data, dict):
                            errors.append(f"Subcategory {category}.{subcategory} must be an object")
        
        # Validate migration timestamp format
        migration_timestamp = nested_data.get("_migration_timestamp")
        if migration_timestamp:
            try:
                datetime.fromisoformat(migration_timestamp.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"Invalid migration timestamp format: {migration_timestamp}")
        
        return errors
    
    def _validate_flat_semantics(self, flat_data: Dict[str, Any]) -> List[str]:
        """Validate semantic correctness of flat structure."""
        errors = []
        
        # Validate required fields
        if "id" not in flat_data:
            errors.append("Missing required field: id")
        
        if "global_settings" not in flat_data:
            errors.append("Missing required field: global_settings")
            return errors
        
        global_settings = flat_data["global_settings"]
        if not isinstance(global_settings, dict):
            errors.append("global_settings must be an object")
            return errors
        
        # Validate known flat fields are objects
        known_fields = list(MIGRATION_FIELD_MAPPING.keys())
        for field in known_fields:
            if field in global_settings:
                field_value = global_settings[field]
                if field_value is not None and not isinstance(field_value, dict):
                    errors.append(f"Field {field} must be an object, got {type(field_value)}")
        
        return errors
    
    def validate_global_context_entity(self, context: GlobalContext) -> Tuple[bool, List[str]]:
        """
        Validate a GlobalContext entity comprehensively.
        
        Args:
            context: GlobalContext entity to validate
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Validate basic structure
        if not context.id:
            errors.append("GlobalContext must have an ID")
        
        if not isinstance(context.global_settings, dict):
            errors.append("global_settings must be a dictionary")
        
        if not isinstance(context.metadata, dict):
            errors.append("metadata must be a dictionary")
        
        # Validate nested structure if present
        if hasattr(context, '_nested_data') and context._nested_data:
            nested_dict = context._nested_data.to_dict()
            nested_valid, nested_errors = self.validate_nested_structure(nested_dict)
            if not nested_valid:
                errors.extend([f"Nested structure: {err}" for err in nested_errors])
        
        # Validate flat structure
        flat_valid, flat_errors = self.validate_flat_structure(context.dict())
        if not flat_valid:
            errors.extend([f"Flat structure: {err}" for err in flat_errors])
        
        # Validate consistency between structures
        consistency_errors = self._validate_structure_consistency(context)
        errors.extend(consistency_errors)
        
        return len(errors) == 0, errors
    
    def _validate_structure_consistency(self, context: GlobalContext) -> List[str]:
        """Validate consistency between flat and nested structures."""
        errors = []
        
        if not hasattr(context, '_nested_data') or not context._nested_data:
            return errors  # No nested structure to compare
        
        try:
            # Get flat representation from nested structure
            from ...infrastructure.migration.global_context_migration import GlobalContextMigrator
            migrator = GlobalContextMigrator()
            flat_from_nested = migrator.migrate_to_flat(context._nested_data)
            
            # Compare key fields
            key_fields = ["organization_standards", "security_policies", "compliance_requirements",
                         "shared_resources", "reusable_patterns", "delegation_rules"]
            
            for field in key_fields:
                flat_value = context.global_settings.get(field, {})
                nested_value = flat_from_nested.get(field, {})
                
                # Allow for empty vs missing fields
                if not flat_value and not nested_value:
                    continue
                
                if flat_value != nested_value:
                    errors.append(f"Inconsistency in field {field} between flat and nested structures")
        
        except Exception as e:
            errors.append(f"Error validating structure consistency: {str(e)}")
        
        return errors
    
    def validate_migration_data(self, original_flat: Dict[str, Any], 
                               migrated_nested: GlobalContextNestedData) -> List[str]:
        """
        Validate that migration preserved data integrity.
        
        Args:
            original_flat: Original flat structure data
            migrated_nested: Migrated nested structure data
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate nested structure
        nested_dict = migrated_nested.to_dict()
        nested_valid, nested_errors = self.validate_nested_structure(nested_dict)
        if not nested_valid:
            errors.extend([f"Migration result validation: {err}" for err in nested_errors])
        
        # Validate reverse migration
        try:
            from ...infrastructure.migration.global_context_migration import GlobalContextMigrator
            migrator = GlobalContextMigrator()
            reverse_flat = migrator.migrate_to_flat(migrated_nested)
            
            # Check for data loss
            for key, value in original_flat.items():
                if key not in reverse_flat:
                    if value:  # Only report loss of non-empty data
                        errors.append(f"Data lost during migration: {key}")
                elif reverse_flat[key] != value:
                    # Allow for reasonable transformations
                    if not self._is_acceptable_transformation(key, value, reverse_flat[key]):
                        errors.append(f"Data modified during migration: {key}")
        
        except Exception as e:
            errors.append(f"Error validating migration: {str(e)}")
        
        return errors
    
    def _is_acceptable_transformation(self, key: str, original: Any, transformed: Any) -> bool:
        """Check if a data transformation during migration is acceptable."""
        # Empty dict to empty dict is acceptable
        if not original and not transformed:
            return True
        
        # Allow restructuring of preferences
        if key in ["global_preferences", "user_preferences"]:
            if isinstance(original, dict) and isinstance(transformed, dict):
                return True
        
        # Allow minor structural changes for complex objects
        if isinstance(original, dict) and isinstance(transformed, dict):
            if len(original) == len(transformed):
                return True
        
        return False
    
    def create_validation_report(self, context: GlobalContext) -> Dict[str, Any]:
        """
        Create a comprehensive validation report for a GlobalContext.
        
        Args:
            context: GlobalContext to validate
            
        Returns:
            Validation report dictionary
        """
        is_valid, errors = self.validate_global_context_entity(context)
        
        # Additional diagnostics
        has_nested = hasattr(context, '_nested_data') and context._nested_data is not None
        has_flat = bool(context.global_settings)
        is_migrated = getattr(context, '_is_migrated', False)
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "is_valid": is_valid,
            "errors": errors,
            "structure_info": {
                "has_nested_structure": has_nested,
                "has_flat_structure": has_flat,
                "is_migrated": is_migrated,
                "schema_version": context._nested_data._schema_version if has_nested else "1.0"
            },
            "field_counts": {
                "flat_fields": len(context.global_settings) if has_flat else 0,
                "nested_categories": len([cat for cat in ["organization", "development", "security", "operations", "preferences"] 
                                        if context._nested_data and getattr(context._nested_data, cat)]) if has_nested else 0
            }
        }
        
        if context.metadata.get("migration_warnings"):
            report["migration_warnings"] = context.metadata["migration_warnings"]
        
        return report


def validate_global_context(context: GlobalContext, raise_on_error: bool = False) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a global context.
    
    Args:
        context: GlobalContext to validate
        raise_on_error: Whether to raise exception on validation failure
        
    Returns:
        Tuple of (is_valid, errors)
        
    Raises:
        GlobalContextValidationError: If raise_on_error=True and validation fails
    """
    validator = GlobalContextValidator()
    is_valid, errors = validator.validate_global_context_entity(context)
    
    if not is_valid and raise_on_error:
        raise GlobalContextValidationError(
            message=f"Global context validation failed with {len(errors)} errors",
            errors=errors
        )
    
    return is_valid, errors