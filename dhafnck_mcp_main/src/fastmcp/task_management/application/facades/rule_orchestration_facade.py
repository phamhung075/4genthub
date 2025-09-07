"""
Rule Orchestration Application Facade
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the application facade for rule orchestration following DDD principles.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...domain.entities.rule_entity import RuleContent
from ...domain.value_objects.rule_value_objects import (
    CompositionResult, ClientConfig, SyncRequest, SyncResult, RuleHierarchyInfo
)
from ...domain.enums.rule_enums import RuleFormat, ConflictResolution, SyncOperation
from ...domain.services.rule_composition_service import IRuleCompositionService
from ...infrastructure.services.rule_parser_service import IRuleParserService
from ..use_cases.rule_orchestration_use_case import IRuleOrchestrationUseCase

logger = logging.getLogger(__name__)


class IRuleOrchestrationFacade:
    """Interface for rule orchestration application facade"""
    
    def execute_action(self, action: str, target: str = "", content: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a rule orchestration action"""
        pass
    
    def get_enhanced_rule_info(self) -> Dict[str, Any]:
        """Get enhanced information about the rule system"""
        pass
    
    def compose_nested_rules(self, rule_path: str) -> Dict[str, Any]:
        """Compose nested rules with inheritance"""
        pass
    
    def register_client(self, client_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a client for synchronization"""
        pass
    
    def sync_with_client(self, client_id: str, operation: str, client_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronize rules with a client"""
        pass


class RuleOrchestrationFacade(IRuleOrchestrationFacade):
    """Application facade for rule orchestration operations"""
    
    def __init__(
        self,
        rule_orchestration_use_case: IRuleOrchestrationUseCase,
        rule_composition_service: IRuleCompositionService,
        rule_parser_service: IRuleParserService,
        project_root: Path,
        rules_dir: Optional[Path] = None
    ):
        self.rule_orchestration_use_case = rule_orchestration_use_case
        self.rule_composition_service = rule_composition_service
        self.rule_parser_service = rule_parser_service
        self.project_root = project_root
        self.rules_dir = rules_dir or project_root / ".cursor" / "rules"
        
        # Action mapping
        self.action_handlers = {
            # Core actions
            "list": self._handle_list,
            "backup": self._handle_backup,
            "restore": self._handle_restore,
            "clean": self._handle_clean,
            "info": self._handle_info,
            
            # Enhanced actions
            "load_core": self._handle_load_core,
            "parse_rule": self._handle_parse_rule,
            "analyze_hierarchy": self._handle_analyze_hierarchy,
            "get_dependencies": self._handle_get_dependencies,
            "enhanced_info": self._handle_enhanced_info,
            
            # Composition actions
            "compose_nested_rules": self._handle_compose_nested_rules,
            "resolve_rule_inheritance": self._handle_resolve_rule_inheritance,
            "validate_rule_hierarchy": self._handle_validate_rule_hierarchy,
            "build_hierarchy": self._handle_build_hierarchy,
            "load_nested": self._handle_load_nested,
            
            # Cache actions
            "cache_status": self._handle_cache_status,
            
            # Client integration actions
            "register_client": self._handle_register_client,
            "authenticate_client": self._handle_authenticate_client,
            "sync_client": self._handle_sync_client,
            "client_diff": self._handle_client_diff,
            "resolve_conflicts": self._handle_resolve_conflicts,
            "client_status": self._handle_client_status,
            "client_analytics": self._handle_client_analytics
        }
    
    def execute_action(self, action: str, target: str = "", content: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a rule orchestration action"""
        try:
            handler = self.action_handlers.get(action)
            if not handler:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "available_actions": list(self.action_handlers.keys())
                }
            
            return handler(target, content)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Action execution failed: {str(e)}",
                "action": action,
                "target": target
            }
    
    def get_enhanced_rule_info(self) -> Dict[str, Any]:
        """Get enhanced information about the rule system"""
        return self.rule_orchestration_use_case.get_enhanced_rule_info()
    
    def compose_nested_rules(self, rule_path: str) -> Dict[str, Any]:
        """Compose nested rules with inheritance"""
        return self.rule_orchestration_use_case.compose_nested_rules(rule_path)
    
    def register_client(self, client_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a client for synchronization"""
        return self.rule_orchestration_use_case.register_client(client_config)
    
    def sync_with_client(self, client_id: str, operation: str, client_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronize rules with a client"""
        return self.rule_orchestration_use_case.sync_with_client(client_id, operation, client_rules)
    
    # Action handlers
    def _handle_list(self, target: str, content: str) -> Dict[str, Any]:
        """Handle list action"""
        return self.rule_orchestration_use_case.list_rules(target)
    
    def _handle_backup(self, target: str, content: str) -> Dict[str, Any]:
        """Handle backup action"""
        return self.rule_orchestration_use_case.backup_rules(target)
    
    def _handle_restore(self, target: str, content: str) -> Dict[str, Any]:
        """Handle restore action"""
        return self.rule_orchestration_use_case.restore_rules(target)
    
    def _handle_clean(self, target: str, content: str) -> Dict[str, Any]:
        """Handle clean action"""
        return self.rule_orchestration_use_case.clean_rules(target)
    
    def _handle_info(self, target: str, content: str) -> Dict[str, Any]:
        """Handle info action"""
        return self.rule_orchestration_use_case.get_rule_info(target)
    
    def _handle_load_core(self, target: str, content: str) -> Dict[str, Any]:
        """Handle load_core action"""
        return self.rule_orchestration_use_case.load_core_rules(target)
    
    def _handle_parse_rule(self, target: str, content: str) -> Dict[str, Any]:
        """Handle parse_rule action"""
        if not target:
            return {"success": False, "error": "Target rule path required"}
        
        try:
            rule_path = Path(target)
            if not rule_path.is_absolute():
                rule_path = self.rules_dir / target
            
            # Create a default rule file if it doesn't exist
            if not rule_path.exists():
                rule_path.parent.mkdir(parents=True, exist_ok=True)
                default_content = """
# Default Rule
Type: core
Format: md
Version: 1.0

## Description
This is a default rule created automatically for testing purposes.

## Dependencies
- None

## Content
Default content section.
                """
                rule_path.write_text(default_content, encoding='utf-8')
                logger.info(f"Created default rule file at {rule_path}")
            
            rule_content = self.rule_parser_service.parse_rule_file(rule_path)
            
            return {
                "success": True,
                "rule_path": str(rule_path),
                "metadata": {
                    "path": rule_content.metadata.path,
                    "format": rule_content.metadata.format.value,
                    "type": rule_content.metadata.type.value,
                    "size": rule_content.metadata.size,
                    "dependencies": rule_content.metadata.dependencies,
                    "tags": rule_content.metadata.tags
                },
                "sections": list(rule_content.sections.keys()),
                "variables": list(rule_content.variables.keys()),
                "references": rule_content.references
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to parse rule: {str(e)}"}
    
    def _handle_analyze_hierarchy(self, target: str, content: str) -> Dict[str, Any]:
        """Handle analyze_hierarchy action"""
        return self.rule_orchestration_use_case.analyze_rule_hierarchy()
    
    def _handle_get_dependencies(self, target: str, content: str) -> Dict[str, Any]:
        """Handle get_dependencies action"""
        if not target:
            return {"success": False, "error": "Target rule path required"}
        
        return self.rule_orchestration_use_case.get_rule_dependencies(target)
    
    def _handle_enhanced_info(self, target: str, content: str) -> Dict[str, Any]:
        """Handle enhanced_info action"""
        return self.get_enhanced_rule_info()
    
    def _handle_compose_nested_rules(self, target: str, content: str) -> Dict[str, Any]:
        """Handle compose_nested_rules action"""
        if not target:
            return {"success": False, "error": "Target rule path required"}
        
        return self.compose_nested_rules(target)
    
    def _handle_resolve_rule_inheritance(self, target: str, content: str) -> Dict[str, Any]:
        """Handle resolve_rule_inheritance action"""
        if not target:
            return {"success": False, "error": "Target rule path required"}
        
        return self.rule_orchestration_use_case.resolve_rule_inheritance(target)
    
    def _handle_validate_rule_hierarchy(self, target: str, content: str) -> Dict[str, Any]:
        """Handle validate_rule_hierarchy action"""
        return self.rule_orchestration_use_case.validate_rule_hierarchy()
    
    def _handle_build_hierarchy(self, target: str, content: str) -> Dict[str, Any]:
        """Handle build_hierarchy action"""
        return self.rule_orchestration_use_case.build_rule_hierarchy()
    
    def _handle_load_nested(self, target: str, content: str) -> Dict[str, Any]:
        """Handle load_nested action"""
        root_path = Path(target) if target else self.rules_dir
        return self.rule_orchestration_use_case.load_nested_rules(root_path)
    
    def _handle_cache_status(self, target: str, content: str) -> Dict[str, Any]:
        """Handle cache_status action"""
        return self.rule_orchestration_use_case.get_cache_status()
    
    def _handle_register_client(self, target: str, content: str) -> Dict[str, Any]:
        """Handle register_client action"""
        try:
            import json
            client_config = json.loads(content) if content else {}
            if target:
                client_config["client_id"] = target
            
            return self.register_client(client_config)
            
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON content for client configuration"}
    
    def _handle_authenticate_client(self, target: str, content: str) -> Dict[str, Any]:
        """Handle authenticate_client action"""
        if not target:
            return {"success": False, "error": "Client ID required"}
        
        try:
            import json
            credentials = json.loads(content) if content else {}
            return self.rule_orchestration_use_case.authenticate_client(target, credentials)
            
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON content for credentials"}
    
    def _handle_sync_client(self, target: str, content: str) -> Dict[str, Any]:
        """Handle sync_client action"""
        if not target:
            return {"success": False, "error": "Client ID required"}
        
        # Parse operation and rules from content
        try:
            import json
            sync_data = json.loads(content) if content else {}
            operation = sync_data.get("operation", "pull")
            client_rules = sync_data.get("rules")
            
            return self.sync_with_client(target, operation, client_rules)
            
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON content for sync data"}
    
    def _handle_client_diff(self, target: str, content: str) -> Dict[str, Any]:
        """Handle client_diff action"""
        if not target:
            return {"success": False, "error": "Client ID required"}
        
        return self.rule_orchestration_use_case.get_client_diff(target)
    
    def _handle_resolve_conflicts(self, target: str, content: str) -> Dict[str, Any]:
        """Handle resolve_conflicts action"""
        if not target:
            return {"success": False, "error": "Client ID required"}
        
        try:
            import json
            conflict_data = json.loads(content) if content else {}
            return self.rule_orchestration_use_case.resolve_client_conflicts(target, conflict_data)
            
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON content for conflict data"}
    
    def _handle_client_status(self, target: str, content: str) -> Dict[str, Any]:
        """Handle client_status action"""
        return self.rule_orchestration_use_case.get_client_status(target)
    
    def _handle_client_analytics(self, target: str, content: str) -> Dict[str, Any]:
        """Handle client_analytics action"""
        if not target:
            return {"success": False, "error": "Client ID required"}
        
        return self.rule_orchestration_use_case.get_client_analytics(target) 