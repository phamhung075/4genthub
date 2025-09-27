"""
Context Inheritance Service

Handles the logic for merging and inheriting contexts across the hierarchy:
Global → Project → Task with proper override and precedence rules.
"""

import logging
from typing import Dict, Any, List, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)

class ContextInheritanceService:
    """
    Service responsible for handling context inheritance logic.
    
    Implements the inheritance rules:
    - Global context provides base configuration
    - Project context can override global settings
    - Task context can override both global and project settings
    - Local overrides always take precedence
    """
    
    def __init__(self, repository=None, user_id: Optional[str] = None):
        """Initialize context inheritance service"""
        self.repository = repository  # Will be injected if needed
        self._user_id = user_id  # Store user context
        logger.info("ContextInheritanceService initialized")

    def _get_user_scoped_repository(self, repository: Any) -> Any:
        """Get a user-scoped version of the repository if it supports user context."""
        if not repository:
            return repository
        if hasattr(repository, 'with_user') and self._user_id:
            return repository.with_user(self._user_id)
        elif hasattr(repository, 'user_id'):
            if self._user_id and repository.user_id != self._user_id:
                repo_class = type(repository)
                if hasattr(repository, 'session'):
                    return repo_class(repository.session, user_id=self._user_id)
        return repository

    def with_user(self, user_id: str) -> 'ContextInheritanceService':
        """Create a new service instance scoped to a specific user."""
        return ContextInheritanceService(self.repository, user_id)
    
    def get_inherited_context(self, level: str, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get inherited context for a given level and ID.
        
        This is a simplified sync method that returns None,
        indicating no inheritance data is available.
        In a real implementation, this would query the hierarchy.
        """
        # For now, return None to indicate no inheritance
        return None
    
    # ===============================================
    # PROJECT INHERITANCE FROM GLOBAL
    # ===============================================
    
    def inherit_project_from_global(self, global_context: Dict[str, Any], 
                                        project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inherit project context from global context with project overrides.
        
        Args:
            global_context: Resolved global context
            project_context: Project-specific context data
            
        Returns:
            Merged project context with global inheritance
        """
        try:
            logger.debug("Inheriting project context from global")
            
            # Start with global context as base
            inherited = deepcopy(global_context)
            
            # Apply project-specific configurations
            project_config = {
                "team_preferences": project_context.get("team_preferences", {}),
                "technology_stack": project_context.get("technology_stack", {}),
                "project_workflow": project_context.get("project_workflow", {}),
                "local_standards": project_context.get("local_standards", {})
            }
            
            # Merge project configurations into inherited context
            inherited = self._deep_merge(inherited, project_config)
            
            # Also merge any other fields from project context that aren't known fields
            # This is needed for tests that add arbitrary fields
            for key, value in project_context.items():
                if key not in ["team_preferences", "technology_stack", "project_workflow", 
                              "local_standards", "global_overrides", "delegation_rules", 
                              "created_at", "updated_at"]:
                    inherited[key] = value
            
            # Apply global overrides (project-specific overrides of global settings)
            global_overrides = project_context.get("global_overrides", {})
            if global_overrides:
                logger.debug(f"Applying {len(global_overrides)} global overrides")
                inherited = self._apply_overrides(inherited, global_overrides)
            
            # Add project-specific delegation rules
            project_delegation = project_context.get("delegation_rules", {})
            if project_delegation:
                inherited["delegation_rules"] = self._merge_delegation_rules(
                    inherited.get("delegation_rules", {}),
                    project_delegation
                )
            
            # Add inheritance metadata
            inherited["inheritance_metadata"] = {
                "inherited_from": "global",
                "global_context_version": global_context.get("metadata", {}).get("version", 1),
                "project_overrides_applied": len(global_overrides),
                "inheritance_disabled": project_context.get("inheritance_disabled", False)
            }
            
            logger.debug("Project inheritance completed")
            return inherited
            
        except Exception as e:
            logger.error(f"Error in project inheritance: {e}", exc_info=True)
            raise
    
    # ===============================================
    # BRANCH INHERITANCE FROM PROJECT
    # ===============================================
    
    def inherit_branch_from_project(self, project_context: Dict[str, Any], 
                                        branch_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inherit branch context from project context with branch-specific overrides.
        
        Args:
            project_context: Resolved project context (already includes global)
            branch_context: Branch-specific context data
            
        Returns:
            Merged branch context with project inheritance
        """
        try:
            logger.debug("Inheriting branch context from project")
            
            # Start with project context as base (which already includes global)
            inherited = deepcopy(project_context)
            
            # Apply branch-specific configurations
            # First add the known branch fields
            branch_config = {
                "branch_workflow": branch_context.get("branch_workflow", {}),
                "branch_standards": branch_context.get("branch_standards", {}),
                "agent_assignments": branch_context.get("agent_assignments", {})
            }
            
            # Merge branch configurations into inherited context
            inherited = self._deep_merge(inherited, branch_config)
            
            # Also merge any other fields from branch context that aren't known fields
            # This is needed for tests that add arbitrary fields
            for key, value in branch_context.items():
                if key not in ["branch_workflow", "branch_standards", "agent_assignments", 
                              "local_overrides", "delegation_rules", "created_at", "updated_at"]:
                    inherited[key] = value
            
            # Apply local overrides (branch-specific overrides of project/global settings)
            local_overrides = branch_context.get("local_overrides", {})
            if local_overrides:
                logger.debug(f"Applying {len(local_overrides)} branch local overrides")
                inherited = self._apply_overrides(inherited, local_overrides)
            
            # Add branch-specific delegation rules
            branch_delegation = branch_context.get("delegation_rules", {})
            if branch_delegation:
                inherited["delegation_rules"] = self._merge_delegation_rules(
                    inherited.get("delegation_rules", {}),
                    branch_delegation
                )
            
            # Add inheritance metadata
            inherited["inheritance_metadata"] = {
                "inherited_from": "project",
                "project_context_version": project_context.get("metadata", {}).get("version", 1),
                "branch_overrides_applied": len(local_overrides),
                "inheritance_disabled": branch_context.get("inheritance_disabled", False),
                "inheritance_chain": ["global", "project", "branch"]
            }
            
            logger.debug("Branch inheritance completed")
            return inherited
            
        except Exception as e:
            logger.error(f"Error in branch inheritance: {e}", exc_info=True)
            raise
    
    # ===============================================
    # TASK INHERITANCE FROM BRANCH
    # ===============================================
    
    def inherit_task_from_branch(self, branch_context: Dict[str, Any], 
                                     task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inherit task context from branch context with task-specific data.
        
        Args:
            branch_context: Resolved branch context (already includes global + project)
            task_context: Task-specific context data
            
        Returns:
            Merged task context with full inheritance chain
        """
        try:
            logger.debug("Inheriting task context from branch")
            
            # Start with branch context as base (which already includes global + project)
            inherited = deepcopy(branch_context)
            
            # Apply task-specific data
            task_data = task_context.get("task_data", {})
            if task_data:
                inherited["task_data"] = task_data
            
            # Also merge any other fields from task context that aren't known fields
            # This is needed for tests that add arbitrary fields
            for key, value in task_context.items():
                if key not in ["task_data", "local_overrides", "implementation_notes", 
                              "delegation_status", "created_at", "updated_at"]:
                    inherited[key] = value
            
            # Apply local overrides (task-specific overrides)
            local_overrides = task_context.get("local_overrides", {})
            if local_overrides:
                logger.debug(f"Applying {len(local_overrides)} local overrides")
                inherited = self._apply_overrides(inherited, local_overrides)
            
            # Add implementation notes
            implementation_notes = task_context.get("implementation_notes", {})
            if implementation_notes:
                inherited["implementation_notes"] = implementation_notes
            
            # Apply custom inheritance rules if present
            custom_rules = task_context.get("custom_inheritance_rules", {})
            if custom_rules:
                inherited = self._apply_custom_inheritance_rules(inherited, custom_rules)
            
            # Add task-specific delegation triggers
            delegation_triggers = task_context.get("delegation_triggers", {})
            if delegation_triggers:
                inherited["delegation_triggers"] = delegation_triggers
            
            # Add inheritance metadata
            inherited["inheritance_metadata"] = {
                "inherited_from": "branch",
                "branch_context_version": branch_context.get("metadata", {}).get("version", 1),
                "local_overrides_applied": len(local_overrides),
                "custom_rules_applied": len(custom_rules),
                "force_local_only": task_context.get("force_local_only", False),
                "inheritance_chain": ["global", "project", "branch", "task"]
            }
            
            logger.debug("Task inheritance completed")
            return inherited
            
        except Exception as e:
            logger.error(f"Error in task inheritance: {e}", exc_info=True)
            raise
    
    # ===============================================
    # CORE INHERITANCE UTILITIES
    # ===============================================
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries with override precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursively merge nested dictionaries
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    # For lists, override completely or merge based on strategy
                    result[key] = self._merge_lists(result[key], value, key)
                else:
                    # Direct override for non-dict values
                    result[key] = deepcopy(value)
            else:
                # Add new key
                result[key] = deepcopy(value)
        
        return result
    
    def _merge_lists(self, base_list: List, override_list: List, key: str) -> List:
        """
        Merge lists based on context-specific strategies.
        
        Args:
            base_list: Base list
            override_list: Override list
            key: Key name for context-specific logic
            
        Returns:
            Merged list
        """
        # Strategy based on key name
        if key in ["assignees", "labels", "technologies", "frameworks"]:
            # For these keys, combine and deduplicate
            combined = list(base_list) + list(override_list)
            return list(dict.fromkeys(combined))  # Preserve order while removing duplicates
        
        elif key in ["requirements", "checklist", "next_steps"]:
            # For these keys, append override to base
            return list(base_list) + list(override_list)
        
        else:
            # Default: override completely
            return deepcopy(override_list)
    
    def _apply_overrides(self, context: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply explicit overrides to context.
        
        Overrides use dot notation for nested keys:
        {"security_policies.mfa_required": true} overrides context["security_policies"]["mfa_required"]
        
        Args:
            context: Base context
            overrides: Override specifications
            
        Returns:
            Context with overrides applied
        """
        result = deepcopy(context)
        
        for override_path, override_value in overrides.items():
            # Split path by dots for nested access
            path_parts = override_path.split('.')
            
            # Navigate to the parent of the target key
            current = result
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the final value
            final_key = path_parts[-1]
            current[final_key] = deepcopy(override_value)
            
            logger.debug(f"Applied override: {override_path} = {override_value}")
        
        return result
    
    def _merge_delegation_rules(self, base_rules: Dict[str, Any], 
                              project_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge delegation rules with project-specific additions.
        
        Args:
            base_rules: Base delegation rules (from global)
            project_rules: Project-specific delegation rules
            
        Returns:
            Merged delegation rules
        """
        merged = deepcopy(base_rules)
        
        # Merge auto_delegate settings
        if "auto_delegate" in project_rules:
            merged_auto_delegate = merged.get("auto_delegate", {})
            merged_auto_delegate.update(project_rules["auto_delegate"])
            merged["auto_delegate"] = merged_auto_delegate
        
        # Merge thresholds (project can override)
        if "thresholds" in project_rules:
            merged_thresholds = merged.get("thresholds", {})
            merged_thresholds.update(project_rules["thresholds"])
            merged["thresholds"] = merged_thresholds
        
        # Add project-specific rules
        for key, value in project_rules.items():
            if key not in ["auto_delegate", "thresholds"]:
                merged[key] = deepcopy(value)
        
        return merged
    
    def _apply_custom_inheritance_rules(self, context: Dict[str, Any], 
                                      custom_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply custom inheritance rules for specific task requirements.
        
        Args:
            context: Current context
            custom_rules: Custom inheritance rules
            
        Returns:
            Context with custom rules applied
        """
        result = deepcopy(context)
        
        # Custom rule types
        rule_processors = {
            "exclude_keys": self._process_exclude_keys,
            "force_values": self._process_force_values,
            "conditional_overrides": self._process_conditional_overrides,
            "merge_strategies": self._process_merge_strategies
        }
        
        for rule_type, rule_config in custom_rules.items():
            processor = rule_processors.get(rule_type)
            if processor:
                result = processor(result, rule_config)
                logger.debug(f"Applied custom rule: {rule_type}")
        
        return result
    
    def _process_exclude_keys(self, context: Dict[str, Any], 
                            exclude_config: List[str]) -> Dict[str, Any]:
        """Remove specified keys from inherited context"""
        result = deepcopy(context)
        
        for key_path in exclude_config:
            path_parts = key_path.split('.')
            current = result
            
            # Navigate to parent
            for part in path_parts[:-1]:
                if part in current and isinstance(current[part], dict):
                    current = current[part]
                else:
                    break
            else:
                # Remove the final key if it exists
                final_key = path_parts[-1]
                if final_key in current:
                    del current[final_key]
                    logger.debug(f"Excluded key: {key_path}")
        
        return result
    
    def _process_force_values(self, context: Dict[str, Any], 
                            force_config: Dict[str, Any]) -> Dict[str, Any]:
        """Force specific values regardless of inheritance"""
        return self._apply_overrides(context, force_config)
    
    def _process_conditional_overrides(self, context: Dict[str, Any], 
                                     conditional_config: List[Dict]) -> Dict[str, Any]:
        """Apply overrides based on conditions"""
        result = deepcopy(context)
        
        for condition in conditional_config:
            if self._evaluate_condition(result, condition.get("condition", {})):
                overrides = condition.get("overrides", {})
                result = self._apply_overrides(result, overrides)
                logger.debug(f"Applied conditional override: {condition.get('name', 'unnamed')}")
        
        return result
    
    def _process_merge_strategies(self, context: Dict[str, Any], 
                                strategy_config: Dict[str, str]) -> Dict[str, Any]:
        """Apply custom merge strategies for specific keys"""
        # This would implement custom merging logic for specific keys
        # For now, return as-is
        return context
    
    def _evaluate_condition(self, context: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against the current context.
        
        Args:
            context: Current context
            condition: Condition specification
            
        Returns:
            True if condition is met
        """
        condition_type = condition.get("type")
        
        if condition_type == "key_exists":
            key_path = condition.get("key", "")
            return self._key_exists(context, key_path)
        
        elif condition_type == "key_equals":
            key_path = condition.get("key", "")
            expected_value = condition.get("value")
            actual_value = self._get_nested_value(context, key_path)
            return actual_value == expected_value
        
        elif condition_type == "key_contains":
            key_path = condition.get("key", "")
            search_value = condition.get("value")
            actual_value = self._get_nested_value(context, key_path)
            return search_value in str(actual_value) if actual_value else False
        
        # Default: condition not met
        return False
    
    def _key_exists(self, context: Dict[str, Any], key_path: str) -> bool:
        """Check if a nested key exists in context"""
        try:
            self._get_nested_value(context, key_path)
            return True
        except (KeyError, TypeError):
            return False
    
    def _get_nested_value(self, context: Dict[str, Any], key_path: str) -> Any:
        """Get value from nested key path"""
        current = context
        for part in key_path.split('.'):
            current = current[part]
        return current
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # ===============================================
    # INHERITANCE VALIDATION
    # ===============================================
    
    def validate_inheritance_chain(self, context_level: str, context_id: str, 
                                       resolved_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that inheritance was applied correctly.
        
        Args:
            context_level: Level of the resolved context
            context_id: Context identifier
            resolved_context: The resolved context to validate
            
        Returns:
            Validation result with any issues found
        """
        logger.info("Starting inheritance validation")
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "metadata": {
                "context_level": context_level,
                "context_id": context_id,
                "validation_timestamp": self._get_timestamp()
            }
        }
        
        try:
            # Check for required inheritance metadata
            inheritance_metadata = resolved_context.get("inheritance_metadata")
            if not inheritance_metadata:
                validation_result["issues"].append("Missing inheritance metadata")
                validation_result["valid"] = False
            else:
                # Validate inheritance chain completeness
                if context_level == "task":
                    expected_chain = ["global", "project", "branch", "task"]
                    actual_chain = inheritance_metadata.get("inheritance_chain", [])
                    if actual_chain != expected_chain:
                        validation_result["warnings"].append(
                            f"Unexpected inheritance chain: {actual_chain}, expected: {expected_chain}"
                        )
                elif context_level == "branch":
                    expected_chain = ["global", "project", "branch"]
                    actual_chain = inheritance_metadata.get("inheritance_chain", [])
                    if actual_chain != expected_chain:
                        validation_result["warnings"].append(
                            f"Unexpected inheritance chain: {actual_chain}, expected: {expected_chain}"
                        )
            
            # Check for override conflicts
            local_overrides = resolved_context.get("local_overrides", {})
            if local_overrides:
                # Validate that overrides are properly applied
                for override_path in local_overrides.keys():
                    if not self._key_exists(resolved_context, override_path):
                        validation_result["issues"].append(
                            f"Override path not found in resolved context: {override_path}"
                        )
                        validation_result["valid"] = False
            
            logger.info(f"Inheritance validation completed: {'valid' if validation_result['valid'] else 'invalid'}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during inheritance validation: {e}", exc_info=True)
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "warnings": [],
                "metadata": validation_result["metadata"]
            }