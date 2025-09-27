"""
Context Operation Factory

Factory class that coordinates unified context operations.
"""

import logging
from typing import Dict, Any
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from .....application.facades.unified_context_facade import UnifiedContextFacade
from ..handlers.context_operation_handler import ContextOperationHandler

logger = logging.getLogger(__name__)


class ContextOperationFactory:
    """Factory for coordinating unified context operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        self._context_handler = ContextOperationHandler(response_formatter)
        
        logger.info("ContextOperationFactory initialized with modular handler")
    
    def handle_operation(self, facade: UnifiedContextFacade, action: str, **kwargs) -> Dict[str, Any]:
        """Route operation to the context handler."""
        
        try:
            return self._context_handler.handle_context_operation(
                facade=facade,
                action=action,
                **kwargs
            )
                
        except Exception as e:
            logger.error(f"Error in ContextOperationFactory.handle_operation: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=f"manage_context.{action}",
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"operation": f"manage_context.{action}"}
            )