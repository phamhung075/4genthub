"""Compliance MCP Controller - Modular Implementation

Interface layer controller for compliance management MCP tools.
Documentation is loaded from external files for maintainability.
"""

import logging
from typing import Dict, Any, Optional, Annotated, Union, TYPE_CHECKING
from pydantic import Field  # type: ignore
from pathlib import Path

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .manage_compliance_description import get_manage_compliance_description, get_manage_compliance_parameters
from ....application.orchestrators.compliance_orchestrator import ComplianceOrchestrator
from .factories.compliance_controller_factory import ComplianceControllerFactory

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
        self._factory = ComplianceControllerFactory(self._compliance_orchestrator)
        logger.info("ComplianceMCPController initialized with modular architecture")

    def register_tools(self, mcp: "FastMCP"):
        """Register compliance management MCP tools with the FastMCP server"""
        
        # Get centralized parameter definitions
        params = get_manage_compliance_parameters()

        @mcp.tool(description=get_manage_compliance_description())
        def manage_compliance(
            action: Annotated[str, Field(description=params["action"]["description"])],
            operation: Annotated[str, Field(description=params["operation"]["description"])] = None,
            command: Annotated[str, Field(description=params["command"]["description"])] = None,
            file_path: Annotated[str, Field(description=params["file_path"]["description"])] = None,
            content: Annotated[str, Field(description=params["content"]["description"])] = None,
            user_id: Annotated[str, Field(description=params["user_id"]["description"])] = None,
            security_level: Annotated[str, Field(description=params["security_level"]["description"])] = None,
            audit_required: Annotated[str, Field(description=params["audit_required"]["description"])] = None,
            timeout: Annotated[int, Field(description=params["timeout"]["description"])] = None,
            limit: Annotated[int, Field(description=params["limit"]["description"])] = None
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

    def manage_compliance(self, action: str, operation: Optional[str] = None, 
                         command: Optional[str] = None, file_path: Optional[str] = None, 
                         content: Optional[str] = None, user_id: Optional[str] = None, 
                         security_level: Optional[str] = None, audit_required: Optional[str] = None,
                         timeout: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Main compliance management method that routes actions to appropriate handlers"""
        try:
            # Import parameter coercion utility
            from ...utils.parameter_validation_fix import coerce_parameter_types
            
            # Coerce string parameters to proper types
            coerced_params = coerce_parameter_types({
                "security_level": security_level,
                "audit_required": audit_required,
                "timeout": timeout,
                "limit": limit
            })
            
            # Apply coerced values
            security_level = coerced_params.get("security_level", "public")
            audit_required = coerced_params.get("audit_required", True)
            timeout = coerced_params.get("timeout", timeout)
            limit = coerced_params.get("limit", 100)
            
            # Validate user ID and handle MVP mode fallbacks
            from ....domain.constants import validate_user_id
            validated_user_id = validate_user_id(user_id, "Compliance operation")
            
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
                return self._factory.handle_validate_compliance(
                    operation=operation,
                    file_path=file_path,
                    content=content,
                    user_id=user_id,
                    security_level=security_level,
                    audit_required=audit_required
                )
            elif action == "get_compliance_dashboard":
                return self._factory.handle_get_compliance_dashboard()
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
                return self._factory.handle_execute_with_compliance(
                    command=command,
                    timeout=timeout,
                    user_id=user_id,
                    audit_required=audit_required
                )
            elif action == "get_audit_trail":
                return self._factory.handle_get_audit_trail(limit=limit)
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

    # Legacy method compatibility
    def _handle_validate_compliance(self, operation: Optional[str], file_path: Optional[str] = None,
                                   content: Optional[str] = None, user_id: Optional[str] = None,
                                   security_level: str = "public", audit_required: bool = True) -> Dict[str, Any]:
        """Handle validate_compliance action (legacy method)"""
        return self._factory.handle_validate_compliance(operation, file_path, content, user_id, security_level, audit_required)

    def _handle_get_compliance_dashboard(self) -> Dict[str, Any]:
        """Handle get_compliance_dashboard action (legacy method)"""
        return self._factory.handle_get_compliance_dashboard()

    def _handle_execute_with_compliance(self, command: Optional[str], timeout: Optional[int] = None,
                                       user_id: Optional[str] = None, audit_required: bool = True) -> Dict[str, Any]:
        """Handle execute_with_compliance action (legacy method)"""
        return self._factory.handle_execute_with_compliance(command, timeout, user_id, audit_required)

    def _handle_get_audit_trail(self, limit: int = 100) -> Dict[str, Any]:
        """Handle get_audit_trail action (legacy method)"""
        return self._factory.handle_get_audit_trail(limit)