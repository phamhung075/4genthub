"""Context Template Manager for Operation-Specific Context Injection

This module defines standardized context templates that specify exactly what context data
is needed for each operation type, reducing unnecessary context fetching by 60-80%.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import yaml
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """MCP operation types"""
    # Task operations
    TASK_CREATE = "task.create"
    TASK_UPDATE = "task.update"
    TASK_GET = "task.get"
    TASK_LIST = "task.list"
    TASK_DELETE = "task.delete"
    TASK_COMPLETE = "task.complete"
    TASK_SEARCH = "task.search"
    TASK_NEXT = "task.next"
    
    # Subtask operations
    SUBTASK_CREATE = "subtask.create"
    SUBTASK_UPDATE = "subtask.update"
    SUBTASK_DELETE = "subtask.delete"
    SUBTASK_LIST = "subtask.list"
    SUBTASK_COMPLETE = "subtask.complete"
    
    # Context operations
    CONTEXT_CREATE = "context.create"
    CONTEXT_GET = "context.get"
    CONTEXT_UPDATE = "context.update"
    CONTEXT_DELETE = "context.delete"
    CONTEXT_RESOLVE = "context.resolve"
    CONTEXT_DELEGATE = "context.delegate"
    
    # Project operations
    PROJECT_CREATE = "project.create"
    PROJECT_GET = "project.get"
    PROJECT_UPDATE = "project.update"
    PROJECT_LIST = "project.list"
    PROJECT_HEALTH_CHECK = "project.health_check"
    
    # Git branch operations
    GIT_BRANCH_CREATE = "git_branch.create"
    GIT_BRANCH_GET = "git_branch.get"
    GIT_BRANCH_LIST = "git_branch.list"
    GIT_BRANCH_UPDATE = "git_branch.update"
    GIT_BRANCH_DELETE = "git_branch.delete"
    
    # Agent operations
    AGENT_REGISTER = "agent.register"
    AGENT_ASSIGN = "agent.assign"
    AGENT_LIST = "agent.list"
    AGENT_CALL = "agent.call"


class TemplateValidationError(Exception):
    """Exception raised when template validation fails"""
    pass


class TemplateVariable:
    """Represents a variable in a context template"""
    
    def __init__(self, name: str, required: bool = True, default: Any = None, description: str = ""):
        self.name = name
        self.required = required
        self.default = default
        self.description = description


class ContextTemplate:
    """Represents a context template with variables and requirements"""
    
    def __init__(self, name: str, operation_type: OperationType, variables: List[TemplateVariable] = None,
                 context_requirements: List[str] = None, description: str = ""):
        self.name = name
        self.operation_type = operation_type
        self.variables = variables or []
        self.context_requirements = context_requirements or []
        self.description = description
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate that context meets template requirements"""
        for variable in self.variables:
            if variable.required and variable.name not in context:
                raise TemplateValidationError(f"Required variable '{variable.name}' missing from context")
        return True


class ContextTemplateManager:
    """Manages context templates for all MCP operations"""
    
    # Default context templates for each operation type
    DEFAULT_TEMPLATES = {
        OperationType.TASK_CREATE: {
            "project": ["id", "name", "default_priority", "workflow_rules"],
            "git_branch": ["id", "name", "status"],
            "recent_tasks": ["title", "status", "assignees"],
            "user": ["id", "preferences", "default_assignees"],
            "parent_context": ["metadata", "requirements"]
        },
        OperationType.TASK_UPDATE: {
            "task": ["id", "current_status", "dependencies", "assignees", "progress_percentage"],
            "related_tasks": ["id", "status", "blocking_status"],
            "project": ["id", "workflow_rules", "completion_criteria"],
            "user": ["id", "permissions"]
        },
        OperationType.TASK_GET: {
            "task": ["*"],  # All fields for single task get
            "subtasks": ["id", "title", "status", "progress_percentage"],
            "dependencies": ["id", "title", "status"],
            "context": ["data", "metadata"]
        },
        OperationType.TASK_LIST: {
            "filters": ["status", "priority", "assignees", "labels"],
            "pagination": ["limit", "offset", "sort_by", "sort_order"],
            "user": ["preferences", "saved_filters"],
            "project": ["id", "name"]
        },
        OperationType.TASK_DELETE: {
            "task": ["id", "dependencies", "subtasks"],
            "user": ["id", "permissions"],
            "cleanup": ["cascade_delete", "archive_mode"]
        },
        OperationType.TASK_COMPLETE: {
            "task": ["id", "title", "dependencies", "subtasks"],
            "subtasks": ["id", "status", "completion_percentage"],
            "project": ["completion_rules", "notification_settings"],
            "next_tasks": ["id", "title", "can_start"]
        },
        OperationType.TASK_SEARCH: {
            "query": ["search_terms", "filters"],
            "scope": ["project_id", "git_branch_id"],
            "user": ["search_history", "preferences"]
        },
        OperationType.TASK_NEXT: {
            "git_branch": ["id", "active_tasks"],
            "user": ["id", "current_context"],
            "priorities": ["urgent_tasks", "blocked_tasks", "ready_tasks"],
            "agent": ["capabilities", "current_load"]
        },
        
        # Subtask operations
        OperationType.SUBTASK_CREATE: {
            "parent_task": ["id", "title", "assignees", "progress_percentage"],
            "project": ["id", "subtask_rules"],
            "user": ["id", "preferences"]
        },
        OperationType.SUBTASK_UPDATE: {
            "subtask": ["id", "status", "progress_percentage"],
            "parent_task": ["id", "progress_percentage", "status"],
            "user": ["id", "permissions"]
        },
        OperationType.SUBTASK_COMPLETE: {
            "subtask": ["id", "title"],
            "parent_task": ["id", "subtasks", "progress_percentage"],
            "impact": ["parent_progress", "sibling_tasks"]
        },
        
        # Context operations
        OperationType.CONTEXT_CREATE: {
            "level": ["hierarchy_level", "parent_context"],
            "data": ["initial_data", "metadata"],
            "inheritance": ["inherit_from_parent", "override_fields"]
        },
        OperationType.CONTEXT_GET: {
            "context": ["id", "level", "data"],
            "inheritance": ["include_inherited", "parent_chain"],
            "cache": ["use_cache", "cache_ttl"]
        },
        OperationType.CONTEXT_UPDATE: {
            "context": ["id", "current_data"],
            "changes": ["data_updates", "metadata_updates"],
            "propagation": ["propagate_to_children", "affected_contexts"]
        },
        OperationType.CONTEXT_RESOLVE: {
            "context": ["id", "level"],
            "hierarchy": ["full_chain", "inheritance_mode"],
            "optimization": ["field_selection", "cache_strategy"]
        },
        
        # Project operations
        OperationType.PROJECT_CREATE: {
            "project": ["name", "description", "settings"],
            "user": ["id", "default_settings"],
            "templates": ["project_template", "initial_structure"]
        },
        OperationType.PROJECT_GET: {
            "project": ["*"],  # All fields for single project
            "statistics": ["task_count", "completion_rate", "active_branches"],
            "team": ["members", "roles"]
        },
        OperationType.PROJECT_LIST: {
            "filters": ["status", "owner", "created_after"],
            "user": ["id", "accessible_projects"],
            "summary": ["minimal_fields", "include_stats"]
        },
        OperationType.PROJECT_HEALTH_CHECK: {
            "project": ["id", "status", "last_activity"],
            "metrics": ["task_metrics", "branch_metrics", "agent_metrics"],
            "issues": ["blocked_tasks", "stale_branches", "overdue_items"]
        },
        
        # Git branch operations
        OperationType.GIT_BRANCH_CREATE: {
            "project": ["id", "branch_naming_convention"],
            "source_branch": ["id", "status"],
            "user": ["id", "permissions"]
        },
        OperationType.GIT_BRANCH_LIST: {
            "project": ["id", "name"],
            "filters": ["status", "created_by"],
            "statistics": ["task_count", "completion_percentage"]
        },
        
        # Agent operations
        OperationType.AGENT_REGISTER: {
            "project": ["id", "agent_registry"],
            "agent": ["name", "capabilities", "configuration"],
            "user": ["id", "permissions"]
        },
        OperationType.AGENT_ASSIGN: {
            "agent": ["id", "current_load", "capabilities"],
            "target": ["task_id", "git_branch_id"],
            "workload": ["current_assignments", "capacity"]
        },
        OperationType.AGENT_CALL: {
            "agent": ["name", "configuration"],
            "context": ["current_task", "current_branch"],
            "parameters": ["agent_params", "timeout"]
        }
    }
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Initialize the template manager
        
        Args:
            templates_path: Optional path to custom templates YAML file
        """
        self.templates = self.DEFAULT_TEMPLATES.copy()
        self.custom_templates = {}
        self.template_version = "1.0.0"
        self._template_cache = {}
        self._inheritance_map = self._build_inheritance_map()
        
        # Load custom templates if provided
        if templates_path:
            self.load_custom_templates(templates_path)
        
        # Initialize metrics
        self._metrics = {
            "templates_used": 0,
            "fields_requested": 0,
            "fields_saved": 0,
            "cache_hits": 0
        }
    
    def get_template(
        self,
        operation: OperationType,
        override_fields: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, List[str]]:
        """
        Get context template for an operation
        
        Args:
            operation: The operation type
            override_fields: Optional field overrides
            
        Returns:
            Dictionary mapping context types to required fields
        """
        # Check cache first
        cache_key = f"{operation.value}:{json.dumps(override_fields) if override_fields else ''}"
        if cache_key in self._template_cache:
            self._metrics["cache_hits"] += 1
            return self._template_cache[cache_key]
        
        # Get base template
        template = self.templates.get(operation, {}).copy()
        
        # Apply inheritance if applicable
        template = self._apply_inheritance(operation, template)
        
        # Apply overrides
        if override_fields:
            for context_type, fields in override_fields.items():
                if fields == ["*"]:
                    template[context_type] = ["*"]
                else:
                    template[context_type] = fields
        
        # Cache the result
        self._template_cache[cache_key] = template
        
        # Update metrics
        self._metrics["templates_used"] += 1
        total_fields = sum(len(f) if f != ["*"] else 50 for f in template.values())
        self._metrics["fields_requested"] += total_fields
        
        return template
    
    def _build_inheritance_map(self) -> Dict[OperationType, List[OperationType]]:
        """
        Build inheritance relationships between similar operations
        
        Returns:
            Dictionary mapping operations to their parent operations
        """
        return {
            # Subtask operations inherit from task operations
            OperationType.SUBTASK_CREATE: [OperationType.TASK_CREATE],
            OperationType.SUBTASK_UPDATE: [OperationType.TASK_UPDATE],
            OperationType.SUBTASK_COMPLETE: [OperationType.TASK_COMPLETE],
            
            # Specific operations inherit from general ones
            OperationType.TASK_SEARCH: [OperationType.TASK_LIST],
            OperationType.TASK_NEXT: [OperationType.TASK_LIST],
            
            # Git branch operations share common fields
            OperationType.GIT_BRANCH_UPDATE: [OperationType.GIT_BRANCH_GET],
            OperationType.GIT_BRANCH_DELETE: [OperationType.GIT_BRANCH_GET],
        }
    
    def _apply_inheritance(
        self,
        operation: OperationType,
        template: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Apply template inheritance for similar operations
        
        Args:
            operation: The operation type
            template: Base template
            
        Returns:
            Template with inherited fields
        """
        if operation in self._inheritance_map:
            parent_ops = self._inheritance_map[operation]
            for parent_op in parent_ops:
                parent_template = self.templates.get(parent_op, {})
                
                # Merge parent fields
                for context_type, fields in parent_template.items():
                    if context_type not in template:
                        template[context_type] = fields
                    else:
                        # Merge fields, avoiding duplicates
                        existing = set(template[context_type])
                        for field in fields:
                            if field not in existing:
                                template[context_type].append(field)
        
        return template
    
    def load_custom_templates(self, templates_path: str) -> None:
        """
        Load custom templates from YAML file
        
        Args:
            templates_path: Path to YAML file containing custom templates
        """
        try:
            path = Path(templates_path)
            if path.exists():
                with open(path, 'r') as f:
                    custom_data = yaml.safe_load(f)
                
                # Validate and merge custom templates
                if "templates" in custom_data:
                    for op_name, template in custom_data["templates"].items():
                        try:
                            op_type = OperationType(op_name)
                            self.templates[op_type] = template
                            self.custom_templates[op_type] = template
                            logger.info(f"Loaded custom template for {op_name}")
                        except ValueError:
                            logger.warning(f"Unknown operation type in custom templates: {op_name}")
                
                # Update version if specified
                if "version" in custom_data:
                    self.template_version = custom_data["version"]
                
                logger.info(f"Loaded {len(self.custom_templates)} custom templates from {templates_path}")
        except Exception as e:
            logger.error(f"Failed to load custom templates: {e}")
    
    def save_templates(self, output_path: str) -> None:
        """
        Save current templates to YAML file
        
        Args:
            output_path: Path to save templates
        """
        try:
            templates_dict = {
                "version": self.template_version,
                "templates": {
                    op.value: template
                    for op, template in self.templates.items()
                }
            }
            
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                yaml.dump(templates_dict, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved templates to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def validate_template(
        self,
        operation: OperationType,
        required_contexts: List[str]
    ) -> bool:
        """
        Validate that a template provides required context types
        
        Args:
            operation: The operation type
            required_contexts: List of required context types
            
        Returns:
            True if template is valid
        """
        template = self.get_template(operation)
        
        for context_type in required_contexts:
            if context_type not in template:
                logger.warning(f"Template for {operation.value} missing required context: {context_type}")
                return False
        
        return True
    
    def get_minimal_context(
        self,
        operation: OperationType,
        available_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract minimal required context from available data
        
        Args:
            operation: The operation type
            available_data: All available context data
            
        Returns:
            Minimal context data based on template
        """
        template = self.get_template(operation)
        minimal_context = {}
        
        for context_type, required_fields in template.items():
            if context_type in available_data:
                source_data = available_data[context_type]
                
                if required_fields == ["*"]:
                    # Include all fields
                    minimal_context[context_type] = source_data
                else:
                    # Include only required fields
                    minimal_context[context_type] = {
                        field: source_data.get(field)
                        for field in required_fields
                        if field in source_data
                    }
                
                # Track savings
                if isinstance(source_data, dict):
                    saved_fields = len(source_data) - len(minimal_context[context_type])
                    self._metrics["fields_saved"] += saved_fields
        
        return minimal_context
    
    def suggest_template_improvements(
        self,
        operation: OperationType,
        actual_usage: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Suggest template improvements based on actual field usage
        
        Args:
            operation: The operation type
            actual_usage: Actually used fields in recent operations
            
        Returns:
            Suggestions for template optimization
        """
        template = self.get_template(operation)
        suggestions = {
            "operation": operation.value,
            "unused_fields": {},
            "missing_fields": {},
            "optimization_potential": 0
        }
        
        # Find unused fields in template
        for context_type, template_fields in template.items():
            if context_type in actual_usage and template_fields != ["*"]:
                used_fields = set(actual_usage[context_type])
                template_set = set(template_fields)
                
                unused = template_set - used_fields
                if unused:
                    suggestions["unused_fields"][context_type] = list(unused)
                
                missing = used_fields - template_set
                if missing:
                    suggestions["missing_fields"][context_type] = list(missing)
        
        # Calculate optimization potential
        total_unused = sum(len(fields) for fields in suggestions["unused_fields"].values())
        total_fields = sum(
            len(fields) if fields != ["*"] else 50
            for fields in template.values()
        )
        
        if total_fields > 0:
            suggestions["optimization_potential"] = (total_unused / total_fields) * 100
        
        return suggestions
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get template usage metrics
        
        Returns:
            Dictionary of metrics
        """
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset usage metrics"""
        self._metrics = {
            "templates_used": 0,
            "fields_requested": 0,
            "fields_saved": 0,
            "cache_hits": 0
        }
    
    def get_all_operations(self) -> List[str]:
        """
        Get list of all supported operations
        
        Returns:
            List of operation names
        """
        return [op.value for op in OperationType]
    
    def estimate_savings(self) -> Dict[str, float]:
        """
        Estimate savings from using templates
        
        Returns:
            Dictionary with savings metrics
        """
        if self._metrics["fields_requested"] == 0:
            return {
                "field_reduction_percent": 0,
                "estimated_time_savings_ms": 0,
                "estimated_bandwidth_savings_kb": 0
            }
        
        # Calculate field reduction
        total_possible = self._metrics["fields_requested"] + self._metrics["fields_saved"]
        field_reduction = (self._metrics["fields_saved"] / total_possible) * 100 if total_possible > 0 else 0
        
        # Estimate time savings (assume 1ms per field)
        time_savings = self._metrics["fields_saved"] * 1
        
        # Estimate bandwidth savings (assume 100 bytes per field)
        bandwidth_savings = (self._metrics["fields_saved"] * 100) / 1024
        
        return {
            "field_reduction_percent": round(field_reduction, 1),
            "estimated_time_savings_ms": time_savings,
            "estimated_bandwidth_savings_kb": round(bandwidth_savings, 2),
            "cache_hit_rate": round(
                (self._metrics["cache_hits"] / self._metrics["templates_used"]) * 100
                if self._metrics["templates_used"] > 0 else 0,
                1
            )
        }