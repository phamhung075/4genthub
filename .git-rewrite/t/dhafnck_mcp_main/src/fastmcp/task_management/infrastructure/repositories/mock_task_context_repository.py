"""Mock Task Context Repository - Wrapper for Test Fixtures

This module maintains backward compatibility by importing the mock implementation
from test fixtures. The actual implementation is in:
tests/fixtures/mocks/repositories/mock_task_context_repository.py
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add tests directory to path
project_root = Path(__file__).resolve().parents[6]
tests_path = project_root / "tests"
if str(tests_path) not in sys.path:
    sys.path.insert(0, str(tests_path))

try:
    # Import from test fixtures
    from fixtures.mocks.repositories.mock_task_context_repository import MockTaskContextRepository
    logger.debug("MockTaskContextRepository imported from test fixtures")
    
except ImportError as e:
    logger.warning(f"Could not import MockTaskContextRepository from test fixtures: {e}")
    logger.info("Using inline fallback implementation")
    
    # Fallback inline implementation
    from typing import Dict, Any, Optional, List
    from datetime import datetime
    import uuid
    
    class MockTaskContextRepository:
        """Mock task context repository for database-less operation"""
        
        def __init__(self, session_factory=None):
            """Initialize mock repository with in-memory storage"""
            self._contexts = {}
            logger.warning("Using inline MockTaskContextRepository - context data will not persist")
        
        def get_context(self, task_id: str) -> Optional[Dict[str, Any]]:
            """Get context for a task"""
            return self._contexts.get(task_id)
        
        def create_context(self, task_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
            """Create context for a task"""
            context = {
                "task_id": task_id,
                "data": context_data,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self._contexts[task_id] = context
            return context
        
        def update_context(self, task_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
            """Update context for a task"""
            if task_id not in self._contexts:
                return self.create_context(task_id, context_data)
            
            context = self._contexts[task_id]
            context["data"].update(context_data)
            context["updated_at"] = datetime.now().isoformat()
            return context
        
        def delete_context(self, task_id: str) -> bool:
            """Delete context for a task"""
            if task_id in self._contexts:
                del self._contexts[task_id]
                return True
            return False
        
        def exists(self, task_id: str) -> bool:
            """Check if context exists for a task"""
            return task_id in self._contexts
        
        def list_contexts(self) -> List[Dict[str, Any]]:
            """List all contexts"""
            return list(self._contexts.values())
        
        def get_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
            """Get context by task ID (alias for get_context)"""
            return self.get_context(task_id)
        
        def save(self, task_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
            """Save context for a task (creates or updates)"""
            if task_id in self._contexts:
                return self.update_context(task_id, context_data)
            return self.create_context(task_id, context_data)

# Export
__all__ = ['MockTaskContextRepository']