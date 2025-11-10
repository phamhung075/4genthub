"""Mock Unified Context Service - Wrapper for Test Fixtures

This module maintains backward compatibility by importing the mock implementation
from test fixtures. The actual implementation is in:
tests/fixtures/mocks/services/mock_unified_context_service.py
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
    from fixtures.mocks.services.mock_unified_context_service import (
        MockUnifiedContextService,
    )
    logger.debug("MockUnifiedContextService imported from test fixtures")
    
except ImportError as e:
    logger.warning(f"Could not import MockUnifiedContextService from test fixtures: {e}")
    logger.info("Using inline fallback implementation")
    
    # Fallback inline implementation
    from datetime import datetime
    from typing import Any
    
    class MockUnifiedContextService:
        """Mock unified context service for database-less operation"""
        
        def __init__(self):
            """Initialize mock service with in-memory storage"""
            self._contexts = {}
            logger.warning("Using inline MockUnifiedContextService - context operations will not persist")
        
        def get_context(
            self,
            level: str,
            context_id: str,
            include_inherited: bool = True,
            force_refresh: bool = False
        ) -> dict[str, Any] | None:
            """Get context by level and ID"""
            key = f"{level}:{context_id}"
            return self._contexts.get(key)
        
        def create_context(
            self,
            level: str,
            context_id: str,
            data: dict[str, Any],
            parent_id: str | None = None
        ) -> dict[str, Any]:
            """Create a new context"""
            key = f"{level}:{context_id}"
            context = {
                "id": context_id,
                "level": level,
                "data": data,
                "parent_id": parent_id,
                # Timestamps managed by repository layer in real implementation
                # Mock maintains timestamps for testing compatibility
                # Mock maintains timestamps for testing compatibility
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self._contexts[key] = context
            return context
        
        def update_context(
            self,
            level: str,
            context_id: str,
            data: dict[str, Any],
            merge: bool = True,
            propagate_changes: bool = False
        ) -> dict[str, Any]:
            """Update an existing context"""
            key = f"{level}:{context_id}"
            if key not in self._contexts:
                # Auto-create if doesn't exist
                return self.create_context(level, context_id, data)
            
            context = self._contexts[key]
            if merge and context.get("data"):
                # Merge with existing data
                context["data"].update(data)
            else:
                # Replace data
                context["data"] = data

            # Mock maintains timestamps for testing compatibility
            # Mock maintains timestamps for testing compatibility
            context["updated_at"] = datetime.now().isoformat()
            return context
        
        def delete_context(
            self,
            level: str,
            context_id: str
        ) -> bool:
            """Delete a context"""
            key = f"{level}:{context_id}"
            if key in self._contexts:
                del self._contexts[key]
                return True
            return False
        
        def resolve_context(
            self,
            level: str,
            context_id: str,
            include_inherited: bool = True,
            force_refresh: bool = False
        ) -> dict[str, Any]:
            """Resolve context with inheritance"""
            key = f"{level}:{context_id}"
            if key in self._contexts:
                return self._contexts[key]
            
            # Return a default context
            return {
                "id": context_id,
                "level": level,
                "data": {},
                "resolved": True,
                # Mock maintains timestamps for testing compatibility
                "created_at": datetime.now().isoformat()
            }
        
        def delegate_context(
            self,
            level: str,
            context_id: str,
            delegate_to: str,
            delegate_data: dict[str, Any],
            delegation_reason: str | None = None
        ) -> dict[str, Any]:
            """Delegate context to higher level"""
            # In mock implementation, just log the delegation
            logger.info(f"Mock delegation from {level}:{context_id} to {delegate_to}")
            return {
                "success": True,
                "delegated_to": delegate_to,
                "delegation_reason": delegation_reason
            }
        
        def list_contexts(
            self,
            level: str | None = None,
            filters: dict[str, Any] | None = None
        ) -> list[dict[str, Any]]:
            """List contexts with optional filtering"""
            results = []
            for key, context in self._contexts.items():
                if level and not key.startswith(f"{level}:"):
                    continue
                results.append(context)
            return results
        
        def add_insight(
            self,
            level: str,
            context_id: str,
            insight: dict[str, Any]
        ) -> dict[str, Any]:
            """Add an insight to context"""
            key = f"{level}:{context_id}"
            if key not in self._contexts:
                self.create_context(level, context_id, {"insights": []})
            
            context = self._contexts[key]
            if "insights" not in context["data"]:
                context["data"]["insights"] = []
            
            context["data"]["insights"].append(insight)
            # Mock maintains timestamps for testing compatibility
            context["updated_at"] = datetime.now().isoformat()
            return context
        
        def add_progress(
            self,
            level: str,
            context_id: str,
            progress: dict[str, Any]
        ) -> dict[str, Any]:
            """Add progress update to context"""
            key = f"{level}:{context_id}"
            if key not in self._contexts:
                self.create_context(level, context_id, {"progress": []})
            
            context = self._contexts[key]
            if "progress" not in context["data"]:
                context["data"]["progress"] = []
            
            context["data"]["progress"].append(progress)
            # Mock maintains timestamps for testing compatibility
            context["updated_at"] = datetime.now().isoformat()
            return context
        
        def validate_hierarchy(
            self,
            task_id: str,
            branch_id: str | None = None,
            project_id: str | None = None
        ) -> dict[str, Any]:
            """Validate context hierarchy"""
            # In mock implementation, always return valid
            return {
                "valid": True,
                "message": "Mock hierarchy validation - always valid"
            }
        
        def get_hierarchy_chain(
            self,
            level: str,
            context_id: str
        ) -> list[dict[str, Any]]:
            """Get the full hierarchy chain for a context"""
            # In mock implementation, return single context
            key = f"{level}:{context_id}"
            if key in self._contexts:
                return [self._contexts[key]]
            return []

# Export
__all__ = ['MockUnifiedContextService']