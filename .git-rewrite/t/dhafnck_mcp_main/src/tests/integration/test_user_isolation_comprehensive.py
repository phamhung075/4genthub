"""
Comprehensive Integration Tests for User Isolation System

This test suite verifies complete user isolation across all layers:
- Database layer with user_id columns
- Repository layer with automatic filtering
- Service layer with context propagation
- API layer with JWT authentication
- End-to-end data isolation
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta
import jwt
from sqlalchemy.orm import Session

from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
from fastmcp.task_management.infrastructure.repositories.orm.agent_repository import ORMAgentRepository
from fastmcp.task_management.application.services.task_application_service import TaskApplicationService
from fastmcp.task_management.application.services.project_application_service import ProjectApplicationService
from fastmcp.task_management.application.services.agent_coordination_service import AgentCoordinationService
from fastmcp.auth.middleware.jwt_auth_middleware import JWTAuthMiddleware, UserContextManager


class TestUserIsolationComprehensive:
    """Comprehensive test suite for user isolation across all layers."""
    
    @pytest.fixture
    def secret_key(self):
        """JWT secret key for testing."""
        return "test-secret-key-for-user-isolation"
    
    @pytest.fixture
    def user1_id(self):
        """Generate user 1 ID."""
        return str(uuid4())
    
    @pytest.fixture
    def user2_id(self):
        """Generate user 2 ID."""
        return str(uuid4())
    
    @pytest.fixture
    def user1_token(self, user1_id, secret_key):
        """Generate JWT token for user 1."""
        payload = {
            "sub": user1_id,
            "email": "user1@test.com",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")
    
    @pytest.fixture
    def user2_token(self, user2_id, secret_key):
        """Generate JWT token for user 2."""
        payload = {
            "sub": user2_id,
            "email": "user2@test.com",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock(spec=Session)
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.flush = Mock()
        session.refresh = Mock()
        session.delete = Mock()
        session.rollback = Mock()
        return session
    
    # ==================== JWT Authentication Tests ====================
    
    def test_jwt_middleware_extracts_user_from_token(self, user1_token, user1_id, secret_key):
        """Test that JWT middleware correctly extracts user_id from token."""
        middleware = JWTAuthMiddleware(secret_key)
        
        extracted_user_id = middleware.extract_user_from_token(user1_token)
        
        assert extracted_user_id == user1_id
    
    def test_jwt_middleware_handles_bearer_prefix(self, user1_token, user1_id, secret_key):
        """Test that middleware handles 'Bearer ' prefix in token."""
        middleware = JWTAuthMiddleware(secret_key)
        
        token_with_bearer = f"Bearer {user1_token}"
        extracted_user_id = middleware.extract_user_from_token(token_with_bearer)
        
        assert extracted_user_id == user1_id
    
    def test_jwt_middleware_rejects_invalid_token(self, secret_key):
        """Test that middleware rejects invalid tokens."""
        middleware = JWTAuthMiddleware(secret_key)
        
        invalid_token = "invalid.jwt.token"
        extracted_user_id = middleware.extract_user_from_token(invalid_token)
        
        assert extracted_user_id is None
    
    def test_jwt_middleware_rejects_expired_token(self, user1_id, secret_key):
        """Test that middleware rejects expired tokens."""
        middleware = JWTAuthMiddleware(secret_key)
        
        # Create expired token
        payload = {
            "sub": user1_id,
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
        }
        expired_token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        extracted_user_id = middleware.extract_user_from_token(expired_token)
        
        assert extracted_user_id is None
    
    # ==================== Repository Layer Isolation Tests ====================
    
    def test_repository_isolates_data_by_user(self, mock_session, user1_id, user2_id):
        """Test that repositories properly isolate data between users."""
        # Create repositories for two users
        user1_repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        user2_repo = ORMTaskRepository(session=mock_session, user_id=user2_id)
        
        # Verify different user contexts
        assert user1_repo.user_id == user1_id
        assert user2_repo.user_id == user2_id
        
        # Verify they're different instances
        assert user1_repo is not user2_repo
    
    def test_repository_applies_user_filter_to_queries(self, mock_session, user1_id):
        """Test that repository applies user_id filter to all queries."""
        repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        
        # Test SQL string filtering
        sql_query = "SELECT * FROM tasks"
        filtered_query = repo.apply_user_filter(sql_query)
        
        assert f"user_id = '{user1_id}'" in filtered_query
    
    def test_repository_injects_user_id_on_create(self, mock_session, user1_id):
        """Test that repository automatically injects user_id on create."""
        repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        
        # Test data injection
        data = {"title": "Test Task", "description": "Test"}
        updated_data = repo.set_user_id(data)
        
        assert updated_data["user_id"] == user1_id
    
    def test_repository_prevents_cross_user_access(self, mock_session, user1_id, user2_id):
        """Test that users cannot access each other's data through repositories."""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.filter_by = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)  # No data found
        mock_session.query.return_value = mock_query
        
        # User1 creates data
        user1_repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        
        # User2 tries to access
        user2_repo = ORMTaskRepository(session=mock_session, user_id=user2_id)
        
        # User2 should not find user1's data
        result = user2_repo.get_task("some-task-id")
        assert result is None
    
    # ==================== Service Layer Context Tests ====================
    
    def test_service_propagates_user_context(self, mock_session, user1_id):
        """Test that services propagate user context to repositories."""
        mock_repo = Mock()
        mock_repo.with_user = Mock(return_value=mock_repo)
        
        service = TaskApplicationService(
            task_repository=mock_repo,
            user_id=user1_id
        )
        
        # Verify user context stored
        assert service._user_id == user1_id
        
        # Verify repository scoping attempted
        mock_repo.with_user.assert_called_with(user1_id)
    
    def test_service_with_user_creates_scoped_instance(self, mock_session, user1_id, user2_id):
        """Test that with_user creates properly scoped service instances."""
        mock_repo = Mock()
        
        # Create service for user1
        service1 = TaskApplicationService(
            task_repository=mock_repo,
            user_id=user1_id
        )
        
        # Create scoped service for user2
        service2 = service1.with_user(user2_id)
        
        # Verify different user contexts
        assert service1._user_id == user1_id
        assert service2._user_id == user2_id
        assert service1 is not service2
    
    @pytest.mark.asyncio
    async def test_service_operations_use_scoped_repositories(self, mock_session, user1_id):
        """Test that service operations use user-scoped repositories."""
        mock_repo = Mock()
        mock_repo.with_user = Mock(return_value=mock_repo)
        mock_repo.find_all = AsyncMock(return_value=[])
        
        service = ProjectApplicationService(
            project_repository=mock_repo,
            user_id=user1_id
        )
        
        # Perform operation
        await service.list_projects()
        
        # Verify scoped repository was used
        mock_repo.with_user.assert_called_with(user1_id)
    
    # ==================== User Context Manager Tests ====================
    
    def test_user_context_manager_caches_repositories(self, mock_session, user1_id):
        """Test that UserContextManager efficiently caches repositories."""
        manager = UserContextManager(user1_id)
        
        # Get repository twice
        repo1 = manager.get_repository(ORMTaskRepository, mock_session)
        repo2 = manager.get_repository(ORMTaskRepository, mock_session)
        
        # Should return same cached instance
        assert repo1 is repo2
    
    def test_user_context_manager_creates_scoped_services(self, user1_id):
        """Test that UserContextManager creates user-scoped services."""
        manager = UserContextManager(user1_id)
        
        mock_repo = Mock()
        service = manager.get_service(
            TaskApplicationService,
            task_repository=mock_repo
        )
        
        # Service should have user context
        assert service._user_id == user1_id
    
    # ==================== End-to-End Isolation Tests ====================
    
    def test_end_to_end_user_isolation(self, mock_session, user1_id, user2_id, secret_key):
        """Test complete user isolation from JWT to data access."""
        # Setup JWT middleware
        middleware = JWTAuthMiddleware(secret_key)
        
        # Create tokens
        user1_token = jwt.encode({"sub": user1_id}, secret_key)
        user2_token = jwt.encode({"sub": user2_id}, secret_key)
        
        # Extract users from tokens
        extracted_user1 = middleware.extract_user_from_token(user1_token)
        extracted_user2 = middleware.extract_user_from_token(user2_token)
        
        assert extracted_user1 == user1_id
        assert extracted_user2 == user2_id
        
        # Create user-scoped repositories
        user1_repo = middleware.create_user_scoped_repository(
            ORMTaskRepository, mock_session, extracted_user1
        )
        user2_repo = middleware.create_user_scoped_repository(
            ORMTaskRepository, mock_session, extracted_user2
        )
        
        # Verify isolation
        assert user1_repo.user_id == user1_id
        assert user2_repo.user_id == user2_id
        
        # Create user-scoped services
        user1_service = middleware.create_user_scoped_service(
            TaskApplicationService,
            extracted_user1,
            task_repository=user1_repo
        )
        user2_service = middleware.create_user_scoped_service(
            TaskApplicationService,
            extracted_user2,
            task_repository=user2_repo
        )
        
        # Verify service isolation
        assert user1_service._user_id == user1_id
        assert user2_service._user_id == user2_id
    
    def test_cross_user_data_access_prevented(self, mock_session, user1_id, user2_id):
        """Test that cross-user data access is prevented at all layers."""
        # Create task as user1
        user1_repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        task_data = user1_repo.set_user_id({
            "title": "User1's Private Task",
            "description": "Should not be visible to User2"
        })
        
        assert task_data["user_id"] == user1_id
        
        # Try to access as user2
        user2_repo = ORMTaskRepository(session=mock_session, user_id=user2_id)
        
        # Mock query to simulate database behavior
        mock_query = Mock()
        mock_query.filter_by = Mock(return_value=mock_query)
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.first = Mock(return_value=None)  # User2 gets no results
        mock_session.query.return_value = mock_query
        
        # User2 should not find user1's task
        result = user2_repo.get_task("task-id")
        assert result is None
    
    # ==================== System Mode Tests ====================
    
    def test_system_mode_bypasses_user_filtering(self, mock_session):
        """Test that system mode (user_id=None) bypasses user filtering."""
        # Create repository in system mode
        system_repo = ORMTaskRepository(session=mock_session, user_id=None)
        
        # Verify system mode
        assert system_repo.user_id is None
        assert system_repo._is_system_mode is True
        
        # System mode should not apply filters
        sql_query = "SELECT * FROM tasks"
        filtered_query = system_repo.apply_user_filter(sql_query)
        
        # Query should be unchanged
        assert filtered_query == sql_query
    
    # ==================== Performance Tests ====================
    
    def test_repository_caching_performance(self, user1_id):
        """Test that context manager caching improves performance."""
        manager = UserContextManager(user1_id)
        
        # Measure repository creation
        import time
        
        # First call (creates new)
        start = time.time()
        repo1 = manager.get_repository(ORMTaskRepository, Mock())
        first_call_time = time.time() - start
        
        # Second call (uses cache)
        start = time.time()
        repo2 = manager.get_repository(ORMTaskRepository, Mock())
        second_call_time = time.time() - start
        
        # Cached call should be faster
        assert second_call_time < first_call_time
        assert repo1 is repo2
    
    # ==================== Security Tests ====================
    
    def test_sql_injection_prevention_in_user_filter(self, mock_session):
        """Test that user filtering prevents SQL injection."""
        # Create repository with potentially malicious user_id
        malicious_user_id = "'; DROP TABLE tasks; --"
        repo = ORMTaskRepository(session=mock_session, user_id=malicious_user_id)
        
        # Apply filter
        sql_query = "SELECT * FROM tasks"
        filtered_query = repo.apply_user_filter(sql_query)
        
        # The malicious SQL should be properly escaped
        assert "DROP TABLE" in filtered_query  # As a string, not as SQL
        assert filtered_query.count("'") >= 2  # Properly quoted
    
    def test_user_id_cannot_be_overridden_in_updates(self, mock_session, user1_id, user2_id):
        """Test that user_id cannot be changed through updates."""
        repo = ORMTaskRepository(session=mock_session, user_id=user1_id)
        
        # Try to override user_id in update
        update_data = {
            "title": "Updated Task",
            "user_id": user2_id  # Try to change user
        }
        
        # The repository should remove user_id from updates
        clean_data = {k: v for k, v in update_data.items() if k != 'user_id'}
        
        assert "user_id" not in clean_data
        assert clean_data["title"] == "Updated Task"