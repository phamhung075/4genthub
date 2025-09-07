"""Security Access Controller

Infrastructure component for managing security access control and validation.
"""

import logging
from typing import Dict, Any
from datetime import datetime
import json

from ...domain.enums.compliance_enums import SecurityLevel
from ...domain.value_objects.compliance_objects import SecurityContext

logger = logging.getLogger(__name__)


class AccessController:
    """Infrastructure service for security access control"""
    
    def __init__(self):
        self._access_rules = {
            ".cursor/rules/": SecurityLevel.PROTECTED,
            ".cursor/rules/02_AI-DOCS/": SecurityLevel.RESTRICTED,
            "src/": SecurityLevel.PROTECTED,
            "tests/": SecurityLevel.PUBLIC,
            ".git/": SecurityLevel.CONFIDENTIAL
        }
        
    def validate_access(self, context: SecurityContext) -> Dict[str, Any]:
        """Validate access to resource based on security context"""
        try:
            # Determine required security level
            required_level = self._get_required_security_level(context.resource_path)
            
            # Check permissions
            has_permission = self._check_permissions(context, required_level)
            
            # Log access attempt if audit required
            if context.audit_required:
                self._log_access_attempt(context, has_permission, required_level)
            
            return {
                "success": True,
                "access_granted": has_permission,
                "required_level": required_level.value,
                "user_level": context.security_level.value,
                "audit_logged": context.audit_required
            }
            
        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            return {
                "success": False,
                "access_granted": False,
                "error": str(e)
            }
    
    def _get_required_security_level(self, resource_path: str) -> SecurityLevel:
        """Get required security level for resource"""
        for path_pattern, level in self._access_rules.items():
            if resource_path.startswith(path_pattern):
                return level
        return SecurityLevel.PUBLIC
    
    def _check_permissions(self, context: SecurityContext, required_level: SecurityLevel) -> bool:
        """Check if user has required permissions"""
        # Level-based access control
        level_hierarchy = {
            SecurityLevel.PUBLIC: 0,
            SecurityLevel.PROTECTED: 1,
            SecurityLevel.RESTRICTED: 2,
            SecurityLevel.CONFIDENTIAL: 3
        }
        
        user_level = level_hierarchy.get(context.security_level, 0)
        required_level_num = level_hierarchy.get(required_level, 0)
        
        return user_level >= required_level_num
    
    def _log_access_attempt(self, context: SecurityContext, granted: bool, required_level: SecurityLevel):
        """Log access attempt for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": context.user_id,
            "operation": context.operation,
            "resource": context.resource_path,
            "required_level": required_level.value,
            "user_level": context.security_level.value,
            "access_granted": granted
        }
        
        # Log to secure audit log
        logger.info(f"Access audit: {json.dumps(log_entry)}")
    
    def update_access_rules(self, rules: Dict[str, SecurityLevel]):
        """Update access rules (for configuration management)"""
        self._access_rules.update(rules)
        logger.info("Access rules updated")