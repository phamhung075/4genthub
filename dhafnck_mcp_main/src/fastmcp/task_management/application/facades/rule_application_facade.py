"""Rule Application Facade

This facade orchestrates rule-related use cases and provides a unified interface
for rule management operations following DDD principles.
"""

from typing import Dict, Any, TYPE_CHECKING
from pathlib import Path

from ...domain.interfaces.utility_service import IPathResolver

if TYPE_CHECKING:
    from ...interface.mcp_tools.path_resolver import PathResolver


class RuleApplicationFacade:
    """
    Application facade for rule management operations.
    
    Orchestrates multiple rule-related use cases and provides a clean interface
    for controllers to interact with the rule domain.
    """
    
    def __init__(self, 
                 path_resolver: "PathResolver" = None,
):
        """
        Initialize the rule application facade.
        
        Args:
            path_resolver: Path resolution service
        """
        
        # Import PathResolver here to avoid circular imports
        if path_resolver is None:
            from ...domain.interfaces.utility_service import IPathResolver
            path_resolver = PathResolver()
        
        self._path_resolver = path_resolver
        # --- TEST COMPATIBILITY: Enhanced Orchestrator Adapter ---
        self._enhanced_orchestrator = None  # For test compatibility only
    
    
    
    def validate_rules(self, target: str = "auto_rule") -> Dict[str, Any]:
        """
        Validate rule files.
        
        Args:
            target: Validation target
            
        Returns:
            Validation result
        """
        try:
            if target == "auto_rule":
                return self._validate_auto_rule()
            elif target == "all":
                return self._validate_all_rules()
            else:
                return self._validate_specific_rule(target)
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}",
                "target": target
            }
    
    def manage_rule(self, action: str, target: str = "", content: str = "") -> Dict[str, Any]:
        """
        Manage rules - simplified implementation after removing rule orchestration controller.
        
        Args:
            action: Management action
            target: Target for action
            content: Content for action
            
        Returns:
            Management result
        """
        from datetime import datetime
        return {
            "success": False,
            "error": "Rule management functionality has been removed. Use cursor rules controller instead.",
            "action": action,
            "target": target,
            "content_length": len(content) if content else 0,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "note": "Rule orchestration controller has been deprecated and removed"
            }
        }
    
    def _create_backup(self, file_path: Path) -> None:
        """Create backup of file if it exists"""
        if file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
    
    def _validate_auto_rule(self) -> Dict[str, Any]:
        """Validate auto rule file"""
        auto_rule_path = self._path_resolver.get_auto_rule_path()
        
        if not auto_rule_path.exists():
            return {
                "success": False,
                "error": "Auto rule file does not exist",
                "file_path": str(auto_rule_path)
            }
        
        try:
            content = auto_rule_path.read_text(encoding='utf-8')
            return {
                "success": True,
                "message": "Auto rule validation passed",
                "file_path": str(auto_rule_path),
                "content_length": len(content),
                "encoding": "utf-8"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read auto rule: {str(e)}",
                "file_path": str(auto_rule_path)
            }
    
    def _validate_all_rules(self) -> Dict[str, Any]:
        """Validate all rule files"""
        rules_dir = self._path_resolver.get_rules_directory_from_settings()
        
        if not rules_dir.exists():
            return {
                "success": False,
                "error": "Rules directory does not exist",
                "rules_directory": str(rules_dir)
            }
        
        results = []
        for rule_file in rules_dir.rglob("*.mdc"):
            try:
                content = rule_file.read_text(encoding='utf-8')
                results.append({
                    "file": str(rule_file),
                    "status": "valid",
                    "content_length": len(content)
                })
            except Exception as e:
                results.append({
                    "file": str(rule_file),
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Validated {len(results)} rule files",
            "rules_directory": str(rules_dir),
            "results": results
        }
    
    def _validate_specific_rule(self, target: str) -> Dict[str, Any]:
        """Validate specific rule file"""
        rule_path = Path(target)
        
        if not rule_path.exists():
            return {
                "success": False,
                "error": f"Rule file does not exist: {target}",
                "file_path": target
            }
        
        try:
            content = rule_path.read_text(encoding='utf-8')
            return {
                "success": True,
                "message": "Rule validation passed",
                "file_path": target,
                "content_length": len(content),
                "encoding": "utf-8"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read rule file: {str(e)}",
                "file_path": target
            }