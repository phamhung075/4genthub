"""Compliance MCP Controller

Interface layer controller for compliance management MCP tools.
Documentation is loaded from external files for maintainability.
"""

import logging
from typing import Dict, Any, Optional, Annotated
from pydantic import Field  # type: ignore
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .desc import description_loader
from ...application.orchestrators.compliance_orchestrator import ComplianceOrchestrator
from ....config.auth_config import AuthConfig

logger = logging.getLogger(__name__)

class ComplianceMCPController:
    """
    MCP controller for compliance management operations.
    Handles only MCP protocol concerns and delegates business operations
    to the compliance orchestrator following proper DDD layer separation.
    """
    def __init__(self, compliance_orchestrator: ComplianceOrchestrator = None, project_root: Path = None):
        self._project_root = project_root or Path.cwd()
        self._compliance_orchestrator = compliance_orchestrator or ComplianceOrchestrator(self._project_root)
        logger.info("ComplianceMCPController initialized")

    def register_tools(self, mcp: "FastMCP"):
        """Register compliance management MCP tools with the FastMCP server"""
        # Load descriptions from external files
        descriptions = self._get_compliance_management_descriptions()
        manage_compliance_desc = descriptions["manage_compliance"]

        @mcp.tool(name="manage_compliance", description=manage_compliance_desc["description"])
        def manage_compliance(
            action: Annotated[str, Field(description="Compliance management action to perform. Valid actions: 'validate_compliance', 'get_compliance_dashboard', 'execute_with_compliance', 'get_audit_trail'. (string)")],
            operation: Annotated[Optional[str], Field(description="Operation to validate (e.g., 'create_file', 'edit_file', 'delete_file', 'run_command'). Required for validate_compliance action. (string)")] = None,
            file_path: Annotated[Optional[str], Field(description="Path to file being operated on. Optional. (string)")] = None,
            content: Annotated[Optional[str], Field(description="Content of file operation. Optional. (string)")] = None,
            user_id: Annotated[Optional[str], Field(description="User performing operation. Optional, defaults to authentication fallback. (string)")] = None,
            security_level: Annotated[str, Field(description="Security level for operation. Default: 'public'. (string)")] = "public",
            audit_required: Annotated[bool, Field(description="Whether to log to audit trail. Default: True. (boolean)")] = True,
            command: Annotated[Optional[str], Field(description="Command to execute. Required for execute_with_compliance action. (string)")] = None,
            timeout: Annotated[Optional[int], Field(description="Timeout in seconds for command execution. Optional. (integer)")] = None,
            limit: Annotated[int, Field(description="Maximum number of audit entries to return. Default: 100. Used for get_audit_trail action. (integer)")] = 100
        ) -> Dict[str, Any]:
            return self.manage_compliance(
                action=action,
                operation=operation,
                file_path=file_path,
                content=content,
                user_id=user_id,
                security_level=security_level,
                audit_required=audit_required,
                command=command,
                timeout=timeout,
                limit=limit
            )

    def _get_compliance_management_descriptions(self) -> Dict[str, Any]:
        """
        Flatten compliance descriptions for robust access, similar to other controllers.
        """
        all_desc = description_loader.get_all_descriptions()
        flat = {}
        # Look for 'manage_compliance' in any subdict (e.g., all_desc['compliance']['manage_compliance'])
        for sub in all_desc.values():
            if isinstance(sub, dict) and "manage_compliance" in sub:
                flat["manage_compliance"] = sub["manage_compliance"]
        return flat

    def manage_compliance(self, action: str, operation: Optional[str] = None, 
                         file_path: Optional[str] = None, content: Optional[str] = None,
                         user_id: Optional[str] = None, security_level: str = "public",
                         audit_required: bool = True, command: Optional[str] = None,
                         timeout: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Main compliance management method that routes actions to appropriate handlers.
        
        Args:
            action: The compliance action to perform
            operation: Operation to validate (for validate_compliance)
            file_path: Path to file being operated on
            content: Content of file operation
            user_id: User performing operation
            security_level: Security level for operation
            audit_required: Whether to log to audit trail
            command: Command to execute (for execute_with_compliance)
            timeout: Timeout in seconds for command execution
            limit: Maximum number of audit entries to return
            
        Returns:
            Dict containing the result of the compliance operation
        """
        try:
            # Get user ID - NO FALLBACKS ALLOWED
            if user_id is None:
                # NO FALLBACKS ALLOWED - user authentication is required
                from ...domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
                raise UserAuthenticationRequiredError("Compliance operation")
            
            if action == "validate_compliance":
                if not operation:
                    return {
                        "success": False,
                        "error": "Missing required field: operation",
                        "error_code": "MISSING_FIELD",
                        "field": "operation",
                        "expected": "A valid operation string (e.g., 'create_file', 'edit_file', etc.)",
                        "hint": "Include 'operation' in your request body"
                    }
                return self._handle_validate_compliance(
                    operation=operation,
                    file_path=file_path,
                    content=content,
                    user_id=user_id,
                    security_level=security_level,
                    audit_required=audit_required
                )
            elif action == "get_compliance_dashboard":
                return self._handle_get_compliance_dashboard()
            elif action == "execute_with_compliance":
                if not command:
                    return {
                        "success": False,
                        "error": "Missing required field: command",
                        "error_code": "MISSING_FIELD",
                        "field": "command",
                        "expected": "A valid shell command string",
                        "hint": "Include 'command' in your request body"
                    }
                return self._handle_execute_with_compliance(
                    command=command,
                    timeout=timeout,
                    user_id=user_id,
                    audit_required=audit_required
                )
            elif action == "get_audit_trail":
                return self._handle_get_audit_trail(limit=limit)
            else:
                return {
                    "success": False,
                    "error": f"Invalid action: {action}. Valid actions are: validate_compliance, get_compliance_dashboard, execute_with_compliance, get_audit_trail",
                    "error_code": "UNKNOWN_ACTION",
                    "field": "action",
                    "expected": "One of: validate_compliance, get_compliance_dashboard, execute_with_compliance, get_audit_trail",
                    "hint": "Check the 'action' parameter for typos"
                }
        except Exception as e:
            logger.error(f"Error in compliance action '{action}': {e}")
            return {
                "success": False,
                "error": f"Compliance operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }

    def _handle_validate_compliance(self, operation: Optional[str], file_path: Optional[str] = None,
                                   content: Optional[str] = None, user_id: Optional[str] = None,
                                   security_level: str = "public", audit_required: bool = True) -> Dict[str, Any]:
        """Handle validate_compliance action"""
        if not operation:
            return {"success": False, "error": "operation is required for validate_compliance action"}
        
        try:
            return self._compliance_orchestrator.validate_operation(
                operation=operation,
                file_path=file_path,
                content=content,
                user_id=user_id,
                security_level=security_level,
                audit_required=audit_required
            )
        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "compliance_score": 0.0
            }

    def _handle_get_compliance_dashboard(self) -> Dict[str, Any]:
        """Handle get_compliance_dashboard action"""
        try:
            return self._compliance_orchestrator.get_compliance_dashboard()
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _handle_execute_with_compliance(self, command: Optional[str], timeout: Optional[int] = None,
                                       user_id: Optional[str] = None, audit_required: bool = True) -> Dict[str, Any]:
        """Handle execute_with_compliance action"""
        from datetime import datetime
        if not command:
            return {"success": False, "error": "command is required for execute_with_compliance action", "metadata": {"timestamp": datetime.now().isoformat()}}
        
        try:
            # Ensure timeout is an integer or None
            timeout_value = int(timeout) if timeout is not None else None
            result = self._compliance_orchestrator.execute_with_compliance(
                command=command,
                timeout=timeout_value,
                user_id=user_id,
                audit_required=audit_required
            )
            if isinstance(result, dict) and "success" in result:
                if result.get("success"):
                    result.setdefault("metadata", {}).update({
                        "action": "execute_with_compliance",
                        "command": command[:50] + "..." if len(command) > 50 else command,
                        "timeout": timeout_value,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    result.setdefault("metadata", {}).update({
                        "action": "execute_with_compliance",
                        "command": command[:50] + "..." if len(command) > 50 else command,
                        "timeout": timeout_value,
                        "timestamp": datetime.now().isoformat()
                    })
            return result
        except ValueError as ve:
            logger.error(f"Invalid timeout value: {ve}")
            return {
                "success": False,
                "error": f"Invalid timeout value: {str(ve)}. Timeout must be an integer or omitted.",
                "metadata": {
                    "action": "execute_with_compliance",
                    "command": command[:50] + "..." if len(command) > 50 else command,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Compliant execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "action": "execute_with_compliance",
                    "command": command[:50] + "..." if len(command) > 50 else command,
                    "timeout": timeout,
                    "timestamp": datetime.now().isoformat(),
                    "error_type": type(e).__name__
                }
            }

    def _handle_get_audit_trail(self, limit: int = 100) -> Dict[str, Any]:
        """Handle get_audit_trail action"""
        try:
            return self._compliance_orchestrator.get_audit_trail(limit)
        except Exception as e:
            logger.error(f"Audit trail retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }