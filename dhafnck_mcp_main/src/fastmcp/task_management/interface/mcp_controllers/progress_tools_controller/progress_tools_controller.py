"""Progress Tools Controller - Modular Implementation

This is the modular implementation of the Progress Tools Controller, decomposed from
the original monolithic 376-line controller into specialized components.

Simple tools for AI to report progress without understanding context structure.
Part of the Vision System Phase 2: Progress Reporting Tools.

The controller now uses:
- Factory Pattern for operation coordination
- Specialized Handlers for different operation types (Progress, Workflow, Context)
- Standardized Response Formatting
"""

import logging
from typing import Dict, Any, Optional, List
from ....application.facades.task_application_facade import TaskApplicationFacade
from ....application.services.facade_service import FacadeService
from ...utils.response_formatter import StandardResponseFormatter
from .factories.operation_factory import ProgressOperationFactory

logger = logging.getLogger(__name__)


class ProgressToolsController:
    """
    Controller providing simple progress reporting tools for AI agents - Modular Implementation.
    
    These tools allow AI to report progress without needing to understand
    the full context structure or hierarchy.
    
    This modular implementation provides:
    - Factory-based operation coordination
    - Specialized handlers for different operation types
    - Standardized response formatting  
    """
    
    def __init__(self, 
                 task_facade: TaskApplicationFacade,
                 context_facade_factory: Optional[UnifiedContextFacadeFactory] = None):
        """
        Initialize progress tools controller with modular components.
        
        Args:
            task_facade: Task application facade for task operations
            context_facade_factory: Factory for creating context facades
        """
        self._task_facade = task_facade
        self._context_facade_factory = context_facade_factory or FacadeService.get_instance()
        
        # Initialize modular components
        self._response_formatter = StandardResponseFormatter()
        self._operation_factory = ProgressOperationFactory(
            self._response_formatter,
            self._task_facade,
            self._context_facade_factory
        )
        
        logger.info("ProgressToolsController initialized with modular architecture for Vision System Phase 2")
    
    def report_progress(self, task_id: str, progress_type: str, description: str,
                       percentage: Optional[int] = None, files_affected: Optional[List[str]] = None,
                       next_steps: Optional[List[str]] = None) -> Dict[str, Any]:
        """Report progress on a task with simple parameters."""
        
        return self._operation_factory.handle_operation(
            operation="report_progress",
            task_id=task_id,
            progress_type=progress_type,
            description=description,
            percentage=percentage,
            files_affected=files_affected,
            next_steps=next_steps
        )
    
    def quick_task_update(self, task_id: str, status: Optional[str] = None,
                         notes: Optional[str] = None, completed_work: Optional[str] = None) -> Dict[str, Any]:
        """Quick task status and notes update."""
        
        return self._operation_factory.handle_operation(
            operation="quick_task_update",
            task_id=task_id,
            status=status,
            notes=notes,
            completed_work=completed_work
        )
    
    def checkpoint_work(self, task_id: str, current_state: str, next_steps: List[str],
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a checkpoint of current work state."""
        
        return self._operation_factory.handle_operation(
            operation="checkpoint_work",
            task_id=task_id,
            current_state=current_state,
            next_steps=next_steps,
            notes=notes
        )
    
    def update_work_context(self, task_id: str, files_read: Optional[List[str]] = None,
                           files_modified: Optional[List[str]] = None,
                           key_decisions: Optional[List[str]] = None,
                           discoveries: Optional[List[str]] = None,
                           test_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update work context with structured information."""
        
        return self._operation_factory.handle_operation(
            operation="update_work_context",
            task_id=task_id,
            files_read=files_read,
            files_modified=files_modified,
            key_decisions=key_decisions,
            discoveries=discoveries,
            test_results=test_results
        )