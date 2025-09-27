"""
Unit tests for User Repository

Tests cover all methods in UserRepository including:
- save (create and update)
- get_by_id, find_by_id
- get_by_email, get_by_username
- get_by_reset_token
- list_all with filtering
- delete
- exists_by_email, exists_by_username
- search functionality
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from unittest.mock import Mock, patch, MagicMock

from fastmcp.auth.infrastructure.repositories.user_repository import UserRepository
from fastmcp.auth.infrastructure.database.models import User as UserModel
from fastmcp.auth.domain.entities.user import User as DomainUser, UserStatus, UserRole


class TestUserRepository:
    """Test suite for UserRepository"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create a UserRepository instance with mock session"""
        return UserRepository(mock_session)
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample domain user for testing"""
        return DomainUser(
            id="test-user-id",
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
            status=UserStatus.ACTIVE,
            roles=[UserRole.USER],
            email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def sample_db_user(self):
        """Create a sample database user model"""
        db_user = Mock(spec=UserModel)
        db_user.id = "test-user-id"
        db_user.email = "test@example.com"
        db_user.username = "testuser"
        db_user.password_hash = "hashed_password"
        db_user.full_name = "Test User"
        db_user.status = UserStatus.ACTIVE.value
        db_user.roles = [UserRole.USER.value]
        db_user.email_verified = True
        db_user.email_verified_at = datetime.now(timezone.utc)
        db_user.last_login_at = None
        db_user.failed_login_attempts = 0
        db_user.locked_until = None
        db_user.password_changed_at = None
        db_user.password_reset_token = None
        db_user.password_reset_expires = None
        db_user.refresh_token_family = None
        db_user.refresh_token_version = 0
        db_user.created_at = datetime.now(timezone.utc)
        db_user.updated_at = datetime.now(timezone.utc)
        db_user.created_by = None
        db_user.project_ids = []
        db_user.default_project_id = None
        db_user.metadata = {}
        return db_user
    
    # Test save method
    @pytest.mark.asyncio
    async def test_save_new_user_without_id(self, repository, mock_session, sample_user):
        """Test saving a new user without ID"""
        # Arrange
        sample_user.id = None
        mock_db_user = Mock()
        mock_db_user.id = "generated-id"
        
        with patch('fastmcp.auth.infrastructure.database.models.User.from_domain', return_value=mock_db_user):
            # Act
            result = await repository.save(sample_user)
            
            # Assert
            mock_session.add.assert_called_once_with(mock_db_user)
            mock_session.flush.assert_called_once()
            mock_session.expunge.assert_called_once_with(mock_db_user)
            assert result.id == "generated-id"
            assert result.email == sample_user.email
    
    @pytest.mark.asyncio
    async def test_save_new_user_with_id(self, repository, mock_session, sample_user):
        """Test saving a new user with existing ID"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_db_user = Mock()
        mock_db_user.id = sample_user.id
        
        with patch('fastmcp.auth.infrastructure.database.models.User.from_domain', return_value=mock_db_user):
            # Act
            result = await repository.save(sample_user)
            
            # Assert
            mock_session.add.assert_called_once_with(mock_db_user)
            mock_session.flush.assert_called_once()
            assert result.id == sample_user.id
    
    @pytest.mark.asyncio
    async def test_save_update_existing_user(self, repository, mock_session, sample_user, sample_db_user):
        """Test updating an existing user"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        sample_user.full_name = "Updated Name"
        
        # Act
        result = await repository.save(sample_user)
        
        # Assert
        mock_session.add.assert_not_called()
        mock_session.flush.assert_called_once()
        assert result.full_name == sample_user.full_name
    
    @pytest.mark.asyncio
    async def test_save_integrity_error(self, repository, mock_session, sample_user):
        """Test save with integrity error (e.g., duplicate email)"""
        # Arrange
        mock_session.flush.side_effect = IntegrityError("", "", "")
        
        # Act & Assert
        with pytest.raises(IntegrityError):
            await repository.save(sample_user)
    
    # Test find_by_id method (synchronous)
    def test_find_by_id_found(self, repository, mock_session, sample_db_user):
        """Test finding user by ID when user exists"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = repository.find_by_id("test-user-id")
        
        # Assert
        assert result is not None
        assert result.id == "test-user-id"
        assert result.email == sample_db_user.email
        mock_session.query.assert_called_once()
    
    def test_find_by_id_not_found(self, repository, mock_session):
        """Test finding user by ID when user doesn't exist"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Act
        result = repository.find_by_id("non-existent-id")
        
        # Assert
        assert result is None
    
    def test_find_by_id_with_exception(self, repository, mock_session):
        """Test find_by_id handles exceptions gracefully"""
        # Arrange
        mock_session.query.side_effect = Exception("Database error")
        
        # Act
        result = repository.find_by_id("test-user-id")
        
        # Assert
        assert result is None
    
    # Test get_by_id method (asynchronous)
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session, sample_db_user):
        """Test getting user by ID when user exists"""
        # Arrange
        sample_db_user.to_domain = Mock(return_value=DomainUser(
            id="test-user-id",
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        ))
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = await repository.get_by_id("test-user-id")
        
        # Assert
        assert result is not None
        assert result.id == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test getting user by ID when user doesn't exist"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Act
        result = await repository.get_by_id("non-existent-id")
        
        # Assert
        assert result is None
    
    # Test get_by_email method
    @pytest.mark.asyncio
    async def test_get_by_email_found(self, repository, mock_session, sample_db_user):
        """Test getting user by email when user exists"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = await repository.get_by_email("TEST@EXAMPLE.COM")  # Test case insensitive
        
        # Assert
        assert result is not None
        assert result.email == sample_db_user.email
        mock_session.query.return_value.filter_by.assert_called_with(email="test@example.com")
    
    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repository, mock_session):
        """Test getting user by email when user doesn't exist"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Act
        result = await repository.get_by_email("notfound@example.com")
        
        # Assert
        assert result is None
    
    # Test get_by_username method
    @pytest.mark.asyncio
    async def test_get_by_username_found(self, repository, mock_session, sample_db_user):
        """Test getting user by username when user exists"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = await repository.get_by_username("testuser")
        
        # Assert
        assert result is not None
        assert result.username == sample_db_user.username
    
    # Test get_by_reset_token method
    @pytest.mark.asyncio
    async def test_get_by_reset_token_found(self, repository, mock_session, sample_db_user):
        """Test getting user by reset token"""
        # Arrange
        sample_db_user.password_reset_token = "reset-token-123"
        sample_db_user.to_domain = Mock(return_value=DomainUser(
            id="test-user-id",
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        ))
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = await repository.get_by_reset_token("reset-token-123")
        
        # Assert
        assert result is not None
    
    # Test list_all method
    @pytest.mark.asyncio
    async def test_list_all_with_status_filter(self, repository, mock_session):
        """Test listing users with status filter"""
        # Arrange
        mock_users = []
        for i in range(3):
            mock_user = Mock()
            mock_user.to_domain = Mock(return_value=DomainUser(
                id=f"user-{i}",
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash="hash"
            ))
            mock_users.append(mock_user)
        
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value.all.return_value = mock_users
        
        # Act
        result = await repository.list_all(limit=10, offset=0, status="active")
        
        # Assert
        assert len(result) == 3
        mock_query.filter_by.assert_called_with(status="active")
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)
    
    @pytest.mark.asyncio
    async def test_list_all_without_filter(self, repository, mock_session):
        """Test listing all users without filter"""
        # Arrange
        mock_query = mock_session.query.return_value
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value.all.return_value = []
        
        # Act
        result = await repository.list_all()
        
        # Assert
        assert result == []
        mock_query.filter_by.assert_not_called()
    
    # Test delete method
    @pytest.mark.asyncio
    async def test_delete_existing_user(self, repository, mock_session, sample_db_user):
        """Test deleting an existing user"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = await repository.delete("test-user-id")
        
        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(sample_db_user)
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_non_existing_user(self, repository, mock_session):
        """Test deleting a non-existing user"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Act
        result = await repository.delete("non-existent-id")
        
        # Assert
        assert result is False
        mock_session.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_with_exception(self, repository, mock_session, sample_db_user):
        """Test delete raises exception on error"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        mock_session.delete.side_effect = Exception("Delete error")
        
        # Act & Assert
        with pytest.raises(Exception):
            await repository.delete("test-user-id")
    
    # Test exists_by_email method
    @pytest.mark.asyncio
    async def test_exists_by_email_true(self, repository, mock_session):
        """Test checking if user exists by email (exists)"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.count.return_value = 1
        
        # Act
        result = await repository.exists_by_email("TEST@EXAMPLE.COM")
        
        # Assert
        assert result is True
        mock_session.query.return_value.filter_by.assert_called_with(email="test@example.com")
    
    @pytest.mark.asyncio
    async def test_exists_by_email_false(self, repository, mock_session):
        """Test checking if user exists by email (doesn't exist)"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.count.return_value = 0
        
        # Act
        result = await repository.exists_by_email("notfound@example.com")
        
        # Assert
        assert result is False
    
    # Test exists_by_username method
    @pytest.mark.asyncio
    async def test_exists_by_username_true(self, repository, mock_session):
        """Test checking if user exists by username"""
        # Arrange
        mock_session.query.return_value.filter_by.return_value.count.return_value = 1
        
        # Act
        result = await repository.exists_by_username("testuser")
        
        # Assert
        assert result is True
    
    # Test search method
    @pytest.mark.asyncio
    async def test_search_users(self, repository, mock_session):
        """Test searching users by email, username, or full name"""
        # Arrange
        mock_users = []
        for i in range(2):
            mock_user = Mock()
            mock_user.to_domain = Mock(return_value=DomainUser(
                id=f"user-{i}",
                email=f"test{i}@example.com",
                username=f"testuser{i}",
                password_hash="hash"
            ))
            mock_users.append(mock_user)
        
        mock_filter = Mock()
        mock_filter.limit.return_value.all.return_value = mock_users
        mock_session.query.return_value.filter.return_value = mock_filter
        
        # Act
        result = await repository.search("test", limit=10)
        
        # Assert
        assert len(result) == 2
        mock_session.query.assert_called_once()
        mock_filter.limit.assert_called_with(10)
    
    @pytest.mark.asyncio
    async def test_search_with_exception(self, repository, mock_session):
        """Test search handles exceptions gracefully"""
        # Arrange
        mock_session.query.side_effect = Exception("Search error")
        
        # Act
        result = await repository.search("test")
        
        # Assert
        assert result == []
    
    # Test edge cases and error conditions
    def test_find_by_id_with_none_values(self, repository, mock_session, sample_db_user):
        """Test find_by_id handles None values correctly"""
        # Arrange
        sample_db_user.roles = None
        sample_db_user.project_ids = None
        sample_db_user.metadata = None
        sample_db_user.failed_login_attempts = None
        sample_db_user.refresh_token_version = None
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = repository.find_by_id("test-user-id")
        
        # Assert
        assert result is not None
        assert result.roles == []
        assert result.project_ids == []
        assert result.metadata == {}
        assert result.failed_login_attempts == 0
        assert result.refresh_token_version == 0
    
    def test_find_by_id_with_string_enums(self, repository, mock_session, sample_db_user):
        """Test find_by_id handles string enum values correctly"""
        # Arrange
        sample_db_user.status = "active"
        sample_db_user.roles = ["user", "admin"]
        mock_session.query.return_value.filter_by.return_value.first.return_value = sample_db_user
        
        # Act
        result = repository.find_by_id("test-user-id")
        
        # Assert
        assert result is not None
        assert result.status == UserStatus.ACTIVE
        assert UserRole.USER in result.roles
        assert UserRole.ADMIN in result.roles