"""
Tests for Email Token Repository
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import json
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from fastmcp.auth.infrastructure.repositories.email_token_repository import (
    EmailTokenRepository,
    EmailToken,
    EmailTokenModel,
    get_email_token_repository,
    Base
)


class TestEmailToken:
    """Test EmailToken data class"""
    
    def test_email_token_creation(self):
        """Test creating an EmailToken"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=1)
        
        token = EmailToken(
            token="test-token-123",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=expires,
            created_at=now,
            metadata={"key": "value"}
        )
        
        assert token.token == "test-token-123"
        assert token.email == "test@example.com"
        assert token.token_type == "verification"
        assert token.token_hash == "hash123"
        assert token.expires_at == expires
        assert token.created_at == now
        assert token.metadata == {"key": "value"}
        assert not token.is_used
        assert token.used_at is None


class TestEmailTokenModel:
    """Test EmailTokenModel SQLAlchemy model"""
    
    def test_model_table_name(self):
        """Test that model has correct table name"""
        assert EmailTokenModel.__tablename__ == "email_tokens"
    
    def test_model_columns(self):
        """Test that model has expected columns"""
        columns = EmailTokenModel.__table__.columns.keys()
        expected_columns = [
            'token', 'email', 'token_type', 'token_hash',
            'expires_at', 'created_at', 'used_at', 'is_used',
            'token_metadata', 'user_id', 'ip_address', 'user_agent'
        ]
        
        for col in expected_columns:
            assert col in columns


class TestEmailTokenRepository:
    """Test EmailTokenRepository functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        db_url = f"sqlite:///{temp_file.name}"
        yield db_url
        os.unlink(temp_file.name)
    
    @pytest.fixture
    def repository(self, temp_db):
        """Create repository instance with temporary database"""
        return EmailTokenRepository(temp_db)
    
    @pytest.fixture
    def sample_token(self):
        """Create sample EmailToken for testing"""
        now = datetime.now(timezone.utc)
        return EmailToken(
            token="test-token-123",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            metadata={"user_agent": "test-browser", "ip": "127.0.0.1"}
        )
    
    def test_repository_initialization_default_url(self):
        """Test repository initialization with default database URL"""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            with patch('fastmcp.auth.infrastructure.repositories.email_token_repository.create_engine') as mock_engine:
                with patch.object(Base.metadata, 'create_all'):
                    repo = EmailTokenRepository()
                    mock_engine.assert_called_once_with("sqlite:///test.db")
    
    def test_repository_initialization_custom_url(self):
        """Test repository initialization with custom database URL"""
        custom_url = "sqlite:///custom.db"
        with patch('fastmcp.auth.infrastructure.repositories.email_token_repository.create_engine') as mock_engine:
            with patch.object(Base.metadata, 'create_all'):
                repo = EmailTokenRepository(custom_url)
                mock_engine.assert_called_once_with(custom_url)
    
    def test_save_token_success(self, repository, sample_token):
        """Test successfully saving a token"""
        result = repository.save_token(sample_token)
        
        assert result is True
        
        # Verify token was saved
        retrieved = repository.get_token(sample_token.token)
        assert retrieved is not None
        assert retrieved.email == sample_token.email
        assert retrieved.token_type == sample_token.token_type
    
    def test_save_token_failure(self, repository, sample_token):
        """Test saving token failure due to database error"""
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.add.side_effect = SQLAlchemyError("Database error")
            mock_session_class.return_value = mock_session
            
            result = repository.save_token(sample_token)
            assert result is False
    
    def test_get_token_exists(self, repository, sample_token):
        """Test getting existing token"""
        repository.save_token(sample_token)
        
        retrieved = repository.get_token(sample_token.token)
        
        assert retrieved is not None
        assert retrieved.token == sample_token.token
        assert retrieved.email == sample_token.email
        assert retrieved.token_type == sample_token.token_type
        assert retrieved.metadata == sample_token.metadata
    
    def test_get_token_not_exists(self, repository):
        """Test getting non-existent token"""
        result = repository.get_token("nonexistent-token")
        assert result is None
    
    def test_get_token_database_error(self, repository):
        """Test getting token with database error"""
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.side_effect = SQLAlchemyError("Database error")
            mock_session_class.return_value = mock_session
            
            result = repository.get_token("some-token")
            assert result is None
    
    def test_get_tokens_by_email(self, repository):
        """Test getting tokens by email"""
        now = datetime.now(timezone.utc)
        
        # Create multiple tokens for same email
        token1 = EmailToken(
            token="token1",
            email="test@example.com",
            token_type="verification",
            token_hash="hash1",
            expires_at=now + timedelta(hours=1),
            created_at=now
        )
        
        token2 = EmailToken(
            token="token2",
            email="test@example.com",
            token_type="password_reset",
            token_hash="hash2",
            expires_at=now + timedelta(hours=2),
            created_at=now
        )
        
        repository.save_token(token1)
        repository.save_token(token2)
        
        # Get all tokens for email
        tokens = repository.get_tokens_by_email("test@example.com")
        assert len(tokens) == 2
        
        # Get tokens by type
        verification_tokens = repository.get_tokens_by_email(
            "test@example.com", token_type="verification"
        )
        assert len(verification_tokens) == 1
        assert verification_tokens[0].token_type == "verification"
    
    def test_get_tokens_by_email_include_used(self, repository, sample_token):
        """Test getting tokens by email including used tokens"""
        repository.save_token(sample_token)
        repository.mark_token_used(sample_token.token)
        
        # Without include_used should return empty
        tokens = repository.get_tokens_by_email(sample_token.email, include_used=False)
        assert len(tokens) == 0
        
        # With include_used should return the token
        tokens = repository.get_tokens_by_email(sample_token.email, include_used=True)
        assert len(tokens) == 1
        assert tokens[0].is_used is True
    
    def test_mark_token_used_success(self, repository, sample_token):
        """Test marking token as used"""
        repository.save_token(sample_token)
        
        result = repository.mark_token_used(sample_token.token)
        assert result is True
        
        # Verify token is marked as used
        retrieved = repository.get_token(sample_token.token)
        assert retrieved.is_used is True
        assert retrieved.used_at is not None
    
    def test_mark_token_used_custom_time(self, repository, sample_token):
        """Test marking token as used with custom timestamp"""
        repository.save_token(sample_token)
        
        used_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        result = repository.mark_token_used(sample_token.token, used_time)
        assert result is True
        
        # Verify custom timestamp was used
        retrieved = repository.get_token(sample_token.token)
        assert retrieved.used_at == used_time
    
    def test_mark_token_used_failure(self, repository, sample_token):
        """Test marking token as used with database error"""
        repository.save_token(sample_token)
        
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.return_value.filter_by.return_value.update.side_effect = SQLAlchemyError("Error")
            mock_session_class.return_value = mock_session
            
            result = repository.mark_token_used(sample_token.token)
            assert result is False
    
    def test_delete_token_success(self, repository, sample_token):
        """Test deleting token"""
        repository.save_token(sample_token)
        
        result = repository.delete_token(sample_token.token)
        assert result is True
        
        # Verify token is deleted
        retrieved = repository.get_token(sample_token.token)
        assert retrieved is None
    
    def test_delete_token_not_exists(self, repository):
        """Test deleting non-existent token"""
        result = repository.delete_token("nonexistent-token")
        assert result is False
    
    def test_delete_token_failure(self, repository, sample_token):
        """Test deleting token with database error"""
        repository.save_token(sample_token)
        
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.return_value.filter_by.return_value.delete.side_effect = SQLAlchemyError("Error")
            mock_session_class.return_value = mock_session
            
            result = repository.delete_token(sample_token.token)
            assert result is False
    
    def test_cleanup_expired_tokens(self, repository):
        """Test cleaning up expired tokens"""
        now = datetime.now(timezone.utc)
        
        # Create expired token
        expired_token = EmailToken(
            token="expired-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash1",
            expires_at=now - timedelta(hours=1),  # Expired
            created_at=now - timedelta(days=10)   # Old
        )
        
        # Create valid token
        valid_token = EmailToken(
            token="valid-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash2",
            expires_at=now + timedelta(hours=1),  # Not expired
            created_at=now
        )
        
        repository.save_token(expired_token)
        repository.save_token(valid_token)
        
        # Clean up expired tokens
        deleted_count = repository.cleanup_expired_tokens(older_than_days=7)
        assert deleted_count == 1
        
        # Verify only valid token remains
        assert repository.get_token(expired_token.token) is None
        assert repository.get_token(valid_token.token) is not None
    
    def test_cleanup_expired_tokens_failure(self, repository):
        """Test cleanup failure due to database error"""
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.delete.side_effect = SQLAlchemyError("Error")
            mock_session_class.return_value = mock_session
            
            result = repository.cleanup_expired_tokens()
            assert result == 0
    
    def test_validate_token_success(self, repository, sample_token):
        """Test successful token validation"""
        repository.save_token(sample_token)
        
        validated = repository.validate_token(
            token=sample_token.token,
            email=sample_token.email,
            token_type=sample_token.token_type
        )
        
        assert validated is not None
        assert validated.token == sample_token.token
        assert validated.is_used is True  # Should be marked as used
    
    def test_validate_token_not_found(self, repository):
        """Test validating non-existent token"""
        result = repository.validate_token(
            token="nonexistent",
            email="test@example.com",
            token_type="verification"
        )
        assert result is None
    
    def test_validate_token_already_used(self, repository, sample_token):
        """Test validating already used token"""
        repository.save_token(sample_token)
        repository.mark_token_used(sample_token.token)
        
        result = repository.validate_token(
            token=sample_token.token,
            email=sample_token.email,
            token_type=sample_token.token_type
        )
        assert result is None
    
    def test_validate_token_expired(self, repository):
        """Test validating expired token"""
        now = datetime.now(timezone.utc)
        expired_token = EmailToken(
            token="expired-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash1",
            expires_at=now - timedelta(hours=1),  # Expired
            created_at=now
        )
        
        repository.save_token(expired_token)
        
        result = repository.validate_token(
            token=expired_token.token,
            email=expired_token.email,
            token_type=expired_token.token_type
        )
        assert result is None
    
    def test_validate_token_no_mark_used(self, repository, sample_token):
        """Test validating token without marking as used"""
        repository.save_token(sample_token)
        
        validated = repository.validate_token(
            token=sample_token.token,
            email=sample_token.email,
            token_type=sample_token.token_type,
            mark_used=False
        )
        
        assert validated is not None
        assert validated.is_used is False  # Should not be marked as used
    
    def test_validate_token_database_error(self, repository, sample_token):
        """Test token validation with database error"""
        repository.save_token(sample_token)
        
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.side_effect = SQLAlchemyError("Database error")
            mock_session_class.return_value = mock_session
            
            result = repository.validate_token(
                token=sample_token.token,
                email=sample_token.email,
                token_type=sample_token.token_type
            )
            assert result is None
    
    def test_get_token_stats(self, repository):
        """Test getting token statistics"""
        now = datetime.now(timezone.utc)
        
        # Create various tokens
        tokens = [
            EmailToken("token1", "test1@example.com", "verification", "hash1", 
                     now + timedelta(hours=1), now),
            EmailToken("token2", "test2@example.com", "password_reset", "hash2", 
                     now + timedelta(hours=2), now),
            EmailToken("token3", "test3@example.com", "verification", "hash3", 
                     now - timedelta(hours=1), now),  # Expired
        ]
        
        for token in tokens:
            repository.save_token(token)
        
        # Mark one as used
        repository.mark_token_used("token1")
        
        stats = repository.get_token_stats()
        
        assert stats["total_tokens"] == 3
        assert stats["used_tokens"] == 1
        assert stats["expired_tokens"] == 1
        assert stats["active_tokens"] == 1
        assert stats["verification_tokens"] == 2
        assert stats["reset_tokens"] == 1
        assert stats["usage_rate"] > 0
    
    def test_get_token_stats_empty_db(self, repository):
        """Test getting statistics from empty database"""
        stats = repository.get_token_stats()
        
        assert stats["total_tokens"] == 0
        assert stats["used_tokens"] == 0
        assert stats["expired_tokens"] == 0
        assert stats["active_tokens"] == 0
        assert stats["usage_rate"] == 0
    
    def test_get_token_stats_database_error(self, repository):
        """Test getting statistics with database error"""
        with patch.object(repository, 'SessionLocal') as mock_session_class:
            mock_session = MagicMock()
            mock_session.__enter__.return_value = mock_session
            mock_session.query.side_effect = SQLAlchemyError("Database error")
            mock_session_class.return_value = mock_session
            
            stats = repository.get_token_stats()
            assert stats == {}
    
    def test_model_to_token_conversion(self, repository):
        """Test conversion from SQLAlchemy model to EmailToken"""
        now = datetime.now(timezone.utc)
        metadata = {"key": "value", "number": 42}
        
        model = EmailTokenModel(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            token_metadata=json.dumps(metadata),
            user_id="user123",
            ip_address="192.168.1.1",
            user_agent="test-agent"
        )
        
        token = repository._model_to_token(model)
        
        assert token.token == "test-token"
        assert token.email == "test@example.com"
        assert token.metadata == metadata
        assert token.user_id == "user123"
        assert token.ip_address == "192.168.1.1"
        assert token.user_agent == "test-agent"
    
    def test_model_to_token_invalid_json(self, repository):
        """Test conversion with invalid JSON metadata"""
        now = datetime.now(timezone.utc)
        
        model = EmailTokenModel(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            token_metadata="invalid json {"
        )
        
        token = repository._model_to_token(model)
        assert token.metadata is None
    
    def test_token_to_model_conversion(self, repository):
        """Test conversion from EmailToken to SQLAlchemy model"""
        now = datetime.now(timezone.utc)
        metadata = {"key": "value"}
        
        token = EmailToken(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            metadata=metadata,
            user_id="user123"
        )
        
        model = repository._token_to_model(token)
        
        assert model.token == "test-token"
        assert model.email == "test@example.com"
        assert model.token_metadata == json.dumps(metadata)
        assert model.user_id == "user123"
    
    def test_token_to_model_invalid_metadata(self, repository):
        """Test conversion with non-serializable metadata"""
        now = datetime.now(timezone.utc)
        
        # Create token with non-serializable metadata
        token = EmailToken(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            metadata={"func": lambda x: x}  # Non-serializable
        )
        
        model = repository._token_to_model(token)
        assert model.token_metadata is None


class TestGlobalRepository:
    """Test global repository instance"""
    
    def test_get_email_token_repository_singleton(self):
        """Test that global repository returns same instance"""
        # Reset global instance
        import fastmcp.auth.infrastructure.repositories.email_token_repository as module
        module._token_repository = None
        
        repo1 = get_email_token_repository()
        repo2 = get_email_token_repository()
        
        assert repo1 is repo2
    
    def test_get_email_token_repository_type(self):
        """Test that global repository returns correct type"""
        repo = get_email_token_repository()
        assert isinstance(repo, EmailTokenRepository)


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def repository(self, temp_db):
        return EmailTokenRepository(temp_db)
    
    def test_timezone_handling_naive_datetime(self, repository):
        """Test handling of naive datetime in token expiration"""
        now = datetime.now()  # Naive datetime
        
        token = EmailToken(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),  # Naive datetime
            created_at=now
        )
        
        repository.save_token(token)
        
        # Should handle naive datetime correctly
        validated = repository.validate_token(
            token=token.token,
            email=token.email,
            token_type=token.token_type
        )
        assert validated is not None
    
    def test_empty_email_handling(self, repository):
        """Test handling of empty email in token operations"""
        tokens = repository.get_tokens_by_email("")
        assert tokens == []
    
    def test_large_metadata_handling(self, repository):
        """Test handling of large metadata"""
        now = datetime.now(timezone.utc)
        large_metadata = {"data": "x" * 10000}  # Large metadata
        
        token = EmailToken(
            token="test-token",
            email="test@example.com",
            token_type="verification",
            token_hash="hash123",
            expires_at=now + timedelta(hours=1),
            created_at=now,
            metadata=large_metadata
        )
        
        result = repository.save_token(token)
        assert result is True
        
        retrieved = repository.get_token(token.token)
        assert retrieved.metadata == large_metadata