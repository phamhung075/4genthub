"""MCP Controller for unified logging management."""

import logging
import json
from typing import Any, Dict, List, Optional, Annotated, TYPE_CHECKING
from datetime import datetime
from pydantic import Field

if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP

from .manage_logging_description import get_manage_logging_description, get_manage_logging_parameters
from pathlib import Path

def get_project_root() -> Path:
    """Get the project root directory."""
    current_dir = Path(__file__).resolve()
    # Navigate up from interface layer
    project_root = current_dir.parent.parent.parent.parent.parent.parent
    
    # In Docker, try to use /app/logs if available, otherwise fallback to project root
    if Path('/app').exists():
        return Path('/app')
    return project_root


class LoggingMCPController:
    """MCP Controller for handling frontend and system logs."""
    
    def __init__(self):
        self.project_root = get_project_root()
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        self.frontend_log_path = self.logs_dir / "frontend.log"
        self.logger = logging.getLogger(__name__)
    
    def register_tools(self, mcp: "FastMCP") -> None:
        """Register logging tools with FastMCP server."""
        
        # Get centralized parameter definitions
        params = get_manage_logging_parameters()
        
        @mcp.tool(description=get_manage_logging_description())
        def manage_logging(
            action: Annotated[str, Field(description=params["action"]["description"])],
            logs: Annotated[str, Field(description=params["logs"]["description"])] = None,
            loggerId: Annotated[str, Field(description=params["loggerId"]["description"])] = None
        ) -> Dict[str, Any]:
            """Main logging management function with two-stage validation pattern:
            - Schema level: Only 'action' is required (MCP compatibility)
            - Business logic level: Action-specific validation in controller
            """
            return self.manage_logging(action=action, logs=logs, loggerId=loggerId)
    
    def manage_logging(self, action: str, logs: Optional[str] = None, loggerId: Optional[str] = None) -> Dict[str, Any]:
        """Main logging management method that routes actions to appropriate handlers"""
        try:
            # Import parameter coercion utility
            from ...utils.parameter_validation_fix import coerce_parameter_types
            
            # Coerce string parameters to proper types
            coerced_params = coerce_parameter_types({
                "logs": logs,
                "loggerId": loggerId
            })
            
            # Apply coerced values
            logs = coerced_params.get("logs", logs)
            loggerId = coerced_params.get("loggerId", loggerId)
            
            if action == "receive_frontend_logs":
                if not logs:
                    return {
                        "success": False,
                        "error": "Missing required field: logs",
                        "error_code": "MISSING_FIELD",
                        "field": "logs",
                        "expected": "Array of log entries with level, message, timestamp fields",
                        "hint": "Include 'logs' parameter with log entries array"
                    }
                
                # Parse logs if it's a string
                if isinstance(logs, str):
                    try:
                        import json
                        logs = json.loads(logs)
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Invalid JSON in logs parameter: {str(e)}",
                            "error_code": "INVALID_JSON",
                            "field": "logs",
                            "hint": "Ensure logs parameter contains valid JSON array"
                        }
                
                return self._handle_receive_frontend_logs(logs, loggerId)
                
            elif action == "get_log_status":
                return self._handle_get_log_status()
                
            else:
                return {
                    "success": False,
                    "error": f"Invalid action: {action}. Valid actions are: receive_frontend_logs, get_log_status",
                    "error_code": "UNKNOWN_ACTION",
                    "field": "action",
                    "expected": "One of: receive_frontend_logs, get_log_status",
                    "hint": "Check the 'action' parameter for typos"
                }
                
        except Exception as e:
            self.logger.error(f"Error in logging action '{action}': {e}")
            return {
                "success": False,
                "error": f"Logging operation failed: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "details": str(e)
            }
    
    def _handle_receive_frontend_logs(self, logs: List[Dict[str, Any]], loggerId: str = None) -> Dict[str, Any]:
        """Handle receive_frontend_logs action"""
        try:
            # Generate unique batch ID
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Open frontend log file in append mode
            with open(self.frontend_log_path, 'a', encoding='utf-8') as f:
                for log_entry in logs:
                    # Format log entry with batch ID for traceability
                    formatted_log = self._format_frontend_log(log_entry, batch_id)
                    f.write(formatted_log + '\n')
                    f.flush()  # Ensure immediate write
            
            self.logger.info(f"Received {len(logs)} frontend log entries - Batch: {batch_id}")
            
            return {
                "success": True,
                "message": f"Successfully logged {len(logs)} entries",
                "batch_id": batch_id,
                "log_file": str(self.frontend_log_path)
            }
            
        except Exception as e:
            error_msg = f"Failed to save frontend logs: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _handle_get_log_status(self) -> Dict[str, Any]:
        """Handle get_log_status action"""
        try:
            backend_log_path = self.logs_dir / "backend.log"
            
            status = {
                "logs_directory": str(self.logs_dir),
                "backend_log": {
                    "path": str(backend_log_path),
                    "exists": backend_log_path.exists(),
                    "size_bytes": backend_log_path.stat().st_size if backend_log_path.exists() else 0
                },
                "frontend_log": {
                    "path": str(self.frontend_log_path),
                    "exists": self.frontend_log_path.exists(),
                    "size_bytes": self.frontend_log_path.stat().st_size if self.frontend_log_path.exists() else 0
                }
            }
            
            return {
                "success": True,
                "status": status
            }
            
        except Exception as e:
            error_msg = f"Failed to get log status: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _format_frontend_log(self, log_entry: Dict[str, Any], batch_id: str) -> str:
        """Format a frontend log entry for file storage."""
        try:
            timestamp = log_entry.get('timestamp', datetime.now().isoformat())
            level = log_entry.get('level', 'INFO').upper()
            message = log_entry.get('message', '')
            logger_id = log_entry.get('loggerId', 'unknown')
            data = log_entry.get('data')
            
            # Base log format
            log_line = f"[{logger_id}] {timestamp} - {level} - {message}"
            
            # Add data if present
            if data:
                try:
                    data_str = json.dumps(data, ensure_ascii=False)
                    log_line += f" | Data: {data_str}"
                except Exception:
                    log_line += f" | Data: {str(data)}"
            
            # Add batch ID for traceability
            log_line += f" | Batch: {batch_id}"
            
            return log_line
            
        except Exception as e:
            # Fallback format if there's an error
            return f"[ERROR] {datetime.now().isoformat()} - WARN - Failed to format log entry: {str(e)} | Original: {log_entry} | Batch: {batch_id}"