"""
Integration test for user_id context creation fix.

This test verifies that the fix for the user_id context creation issue works correctly.
The specific error was: "user_id is required for branch context creation"
"""

import pytest
import uuid
from unittest.mock import patch
import logging

from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
from fastmcp.task_management.infrastructure.repositories.project_context_repository import ProjectContextRepository
from fastmcp.task_management.infrastructure.repositories.branch_context_repository import BranchContextRepository
from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
from fastmcp.task_management.infrastructure.database.database_config import get_session

logger = logging.getLogger(__name__)


class TestUserIdContextCreationFix:
    """Test the fix for user_id context creation issues"""
    
    @pytest.fixture
    def user_id(self):
        """Generate a test user ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def project_id(self):
        """Generate a test project ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def branch_id(self):
        """Generate a test branch ID"""
        return str(uuid.uuid4())
    
    def test_branch_context_creation_with_user_id(self, user_id, project_id, branch_id):
        """
        Test that branch context creation works properly when user_id is provided.
        
        This test addresses the specific error:
        "ERROR: user_id is required for branch context creation"
        """
        try:
            # Create repositories directly using session factory
            session_factory = get_session
            
            # Create repositories
            global_repo = GlobalContextRepository(session_factory)
            project_repo = ProjectContextRepository(session_factory)
            branch_repo = BranchContextRepository(session_factory)
            task_repo = TaskContextRepository(session_factory)
            
            # Create unified context service
            service = UnifiedContextService(
                global_context_repository=global_repo,
                project_context_repository=project_repo,
                branch_context_repository=branch_repo,
                task_context_repository=task_repo,
                user_id=user_id  # Set user_id in service
            )
            
            # Create facade with user_id
            facade = UnifiedContextFacade(
                unified_service=service,
                user_id=user_id,
                project_id=project_id
            )
            
            # Test data for branch context
            branch_data = {
                "git_branch_name": f"feature/test-{branch_id}",
                "branch_settings": {
                    "workflow_type": "feature",
                    "auto_created": False,
                    "created_from": "test"
                },
                "project_id": project_id,
                "user_id": user_id  # Explicitly include user_id
            }
            
            logger.info(f"Testing branch context creation with user_id: {user_id}")
            
            # This should NOT raise the error: "user_id is required for branch context creation"
            result = facade.create_context(
                level="branch",
                context_id=branch_id,
                data=branch_data,
                user_id=user_id
            )
            
            # Assert the context was created successfully
            assert result is not None, "Result should not be None"
            assert result.get("success") is True, f"Context creation failed: {result.get('error')}"
            
            # Verify the context can be retrieved
            retrieved_result = facade.get_context(
                level="branch",
                context_id=branch_id
            )
            
            assert retrieved_result is not None, "Retrieved result should not be None"
            assert retrieved_result.get("success") is True, f"Context retrieval failed: {retrieved_result.get('error')}"
            
            logger.info("✅ Branch context creation with user_id test passed")
            
        except ValueError as e:
            if "user_id is required for branch context creation" in str(e):
                pytest.fail(f"❌ Fix failed: Still getting user_id error: {e}")
            else:
                # Some other ValueError - re-raise it
                raise
        except Exception as e:
            # Log the exception for debugging
            logger.error(f"❌ Unexpected error in user_id context creation test: {e}", exc_info=True)
            raise
    
    def test_atomic_context_creation_with_user_id_in_data(self, user_id, project_id, branch_id):
        """
        Test that atomic context creation extracts user_id from data correctly.
        
        This tests the fix in _create_context_atomically method.
        """
        try:
            # Create repositories directly using session factory
            session_factory = get_session
            
            # Create unified context service (without user_id set initially)
            service = UnifiedContextService(
                global_context_repository=GlobalContextRepository(session_factory),
                project_context_repository=ProjectContextRepository(session_factory),
                branch_context_repository=BranchContextRepository(session_factory),
                task_context_repository=TaskContextRepository(session_factory)
                # Note: No user_id set in service constructor
            )
            
            # Test data with user_id in metadata (as done in the service)
            branch_data = {
                "git_branch_name": f"atomic-test-{branch_id}",
                "branch_settings": {
                    "workflow_type": "feature",
                    "auto_created": True,
                    "created_from": "atomic_test"
                },
                "metadata": {
                    "user_id": user_id,  # user_id is in metadata
                    "project_id": project_id,
                    "branch_id": branch_id
                },
                "project_id": project_id
            }
            
            logger.info(f"Testing atomic context creation with user_id in data: {user_id}")
            
            # This should extract user_id from data and work correctly
            success = service._create_context_atomically(
                level=ContextLevel.BRANCH,
                context_id=branch_id,
                data=branch_data
            )
            
            # Assert the atomic creation was successful
            assert success is True, "Atomic context creation should succeed"
            
            logger.info("✅ Atomic context creation with user_id in data test passed")
            
        except ValueError as e:
            if "user_id is required for branch context creation" in str(e):
                pytest.fail(f"❌ Fix failed: Still getting user_id error in atomic creation: {e}")
            else:
                # Some other ValueError - re-raise it
                raise
        except Exception as e:
            # Log the exception for debugging  
            logger.error(f"❌ Unexpected error in atomic context creation test: {e}", exc_info=True)
            raise
    
    def test_repository_user_scoping(self, user_id):
        """
        Test that repositories are properly scoped to users.
        
        This tests the core fix: ensuring repositories are scoped before use.
        """
        try:
            # Create repositories directly using session factory
            session_factory = get_session
            
            # Get branch repository
            branch_repo = BranchContextRepository(session_factory)
            
            # This should work without error
            scoped_repo = branch_repo.with_user(user_id)
            
            # Verify the scoped repository has the user_id
            assert scoped_repo.user_id == user_id, f"Scoped repository should have user_id: {user_id}"
            
            logger.info(f"✅ Repository user scoping test passed for user_id: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Repository user scoping test failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    # Run the tests directly
    import sys
    sys.exit(pytest.main([__file__, "-v"]))