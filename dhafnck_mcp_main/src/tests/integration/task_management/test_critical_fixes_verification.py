"""
Verification test for critical MCP tool fixes.

Tests the fixes for:
1. psycopg2.errors.NotNullViolation: null value in column "user_id" violates not-null constraint
2. Context creation NoneType iteration errors
"""

import pytest
import logging
from unittest.mock import Mock, patch

from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService

logger = logging.getLogger(__name__)


class TestCriticalFixesVerification:
    """Verify that the critical fixes are working properly."""
    
    def test_subtask_requires_authentication(self):
        """
        Test that subtask creation requires proper authentication.
        No fallback IDs are used - authentication is mandatory.
        """
        import uuid
        from fastmcp.task_management.domain.exceptions import TaskNotFoundError
        
        # Test 1: With authentication, task not found should raise TaskNotFoundError
        mock_user_id = str(uuid.uuid4())
        facade = SubtaskApplicationFacade(user_id=mock_user_id)
        
        # Mock database session to return None (task not found)
        with patch('fastmcp.task_management.infrastructure.database.database_config.get_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            
            # Should raise TaskNotFoundError when task not found
            with pytest.raises(TaskNotFoundError) as exc_info:
                context = facade._derive_context_from_task("nonexistent-task-id")
            
            assert "not found" in str(exc_info.value).lower()
            
        # Test 2: Without authentication, should require auth
        facade_no_auth = SubtaskApplicationFacade(user_id=None)
        
        # Mock auth helper to raise authentication error
        with patch('fastmcp.task_management.interface.mcp_controllers.auth_helper.auth_helper.get_authenticated_user_id') as mock_auth:
            mock_auth.side_effect = ValueError("User authentication required for task lookup")
            
            # Should raise ValueError for missing authentication
            with pytest.raises(ValueError) as exc_info:
                context = facade_no_auth._derive_context_from_task("some-task-id")
            
            assert "authentication required" in str(exc_info.value).lower()
            
        logger.info("✅ Authentication is properly enforced - no hardcoded IDs")
    
    def test_context_nonetype_iteration_fix(self):
        """
        Test ISSUE 2 FIX: Context service handles None data without iteration errors.
        """
        # Create mock repositories
        mock_repos = [Mock() for _ in range(4)]
        service = UnifiedContextService(*mock_repos)
        
        # Test 1: _merge_context_data with None values
        result = service._merge_context_data({'existing': 'data'}, None)
        assert isinstance(result, dict)
        assert result['existing'] == 'data'
        assert 'updated_at' in result  # Should add timestamp
        
        # Test 2: _merge_context_data with both None
        result = service._merge_context_data(None, None)
        assert isinstance(result, dict)
        assert 'updated_at' in result  # Should add timestamp
        
        # Test 3: _serialize_for_json with None values
        test_data = {
            'field1': None,
            'field2': {'nested': None},
            'field3': [None, 'value', None]
        }
        result = service._serialize_for_json(test_data)
        assert isinstance(result, dict)
        assert result['field1'] is None
        assert result['field2']['nested'] is None
        assert None in result['field3']
        
        # Test 4: _serialize_for_json with None dict/list
        result = service._serialize_for_json(None)
        assert result is None
        
        logger.info("✅ ISSUE 2 FIXED: Context service handles None values correctly")
    
    def test_context_creation_with_none_data(self):
        """
        Test that context creation with None data works without NoneType errors.
        """
        # Create mock repositories
        mock_repos = [Mock() for _ in range(4)]
        service = UnifiedContextService(*mock_repos)
        
        # Mock the repository to avoid actual database calls
        mock_repo = Mock()
        mock_entity = Mock()
        mock_entity.dict.return_value = {'id': 'test-id', 'data': 'test'}
        mock_entity.id = 'test-id'  # Add id attribute
        mock_repo.create.return_value = mock_entity
        
        with patch.object(service, '_get_user_scoped_repository', return_value=mock_repo):
            with patch.object(service.validation_service, 'validate_context_data', return_value={'valid': True}):
                with patch.object(service, '_create_context_entity', return_value=mock_entity):
                    with patch.object(service, '_ensure_parent_contexts_exist', return_value={'success': True}):
                        with patch.object(service.hierarchy_validator, 'validate_hierarchy_requirements', return_value=(True, None, None)):
                            with patch.object(service, '_entity_to_dict', return_value={'id': 'test-id', 'data': {}}):
                                # This should handle None data gracefully
                                result = service.create_context(
                                    level="task",
                                    context_id="test-task-id", 
                                    data=None,  # This was causing NoneType iteration errors
                                    user_id="test-user"
                                )
                                
                                assert result["success"] is True
                                logger.info("✅ Context creation with None data works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])