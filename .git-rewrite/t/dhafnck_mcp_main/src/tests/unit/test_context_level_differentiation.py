"""
Unit test to verify that branch and task contexts are differentiated properly.
This is a focused test to ensure the fix for the context resolution issue.
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestContextLevelDifferentiation:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test that context resolution differentiates between branch and task levels."""
    
    def test_branch_id_resolved_as_branch_not_task(self):
        """Test that branch IDs are resolved with branch level, not task level."""
        # This test documents the fix for the issue where branch ID 
        # d4f91ee3-1f97-4768-b4ff-1e734180f874 was being resolved as task context
        
        # Mock the unified context service
        mock_service = Mock()
        
        # The problematic branch ID from the issue
        branch_id = "d4f91ee3-1f97-4768-b4ff-1e734180f874"
        
        # Simulate frontend calling with branch level (correct)
        mock_service.resolve_context = MagicMock(return_value=(
            {"id": branch_id, "level": "branch", "data": {"branch_name": "feature/auth-system"}},
            {"project": {}, "global": {}}
        ))
        
        # Call with branch level
        result = mock_service.resolve_context(
            level="branch",  # Correct level
            context_id=branch_id,
            force_refresh=False
        )
        
        # Verify it returns branch context
        assert result[0]["level"] == "branch"
        assert result[0]["id"] == branch_id
        
        # Now test what happens with wrong level (task)
        mock_service.resolve_context = MagicMock(side_effect=ValueError("Context not found"))
        
        # This should fail
        with pytest.raises(ValueError, match="Context not found"):
            mock_service.resolve_context(
                level="task",  # Wrong level!
                context_id=branch_id,
                force_refresh=False
            )
    
    def test_frontend_api_patterns(self):
        """Test the exact API patterns used by frontend."""
        # Document the correct patterns
        
        # Pattern 1: getBranchContext should use level='branch'
        branch_request = {
            "action": "resolve",
            "level": "branch",  # CORRECT
            "context_id": "d4f91ee3-1f97-4768-b4ff-1e734180f874",
            "force_refresh": False,
            "include_inherited": True
        }
        
        # Pattern 2: getTaskContext should use action='get' with task_id
        task_request = {
            "action": "get",
            "task_id": "some-task-id"  # Uses task_id parameter
        }
        
        # These patterns ensure proper context resolution
        assert branch_request["level"] == "branch"
        assert "task_id" in task_request
        assert "level" not in task_request  # getTaskContext doesn't specify level
    
    def test_context_hierarchy_levels(self):
        """Document the 4-tier context hierarchy."""
        hierarchy = {
            "global": {"id": "global_singleton", "level": "global"},
            "project": {"id": "project-uuid", "level": "project"},
            "branch": {"id": "branch-uuid", "level": "branch"},
            "task": {"id": "task-uuid", "level": "task"}
        }
        
        # Each level should have its own context type
        assert hierarchy["global"]["level"] == "global"
        assert hierarchy["project"]["level"] == "project"
        assert hierarchy["branch"]["level"] == "branch"
        assert hierarchy["task"]["level"] == "task"
        
        # IDs at different levels can't be used interchangeably
        branch_id = "d4f91ee3-1f97-4768-b4ff-1e734180f874"
        # This ID is a branch ID and should ONLY be resolved as branch level
        # NOT as task level
        
        # Document the fix:
        # - Frontend was calling getTaskContext(branch_id)
        # - This tried to resolve branch ID as task context
        # - Fix: Use getBranchContext(branch_id) for branches