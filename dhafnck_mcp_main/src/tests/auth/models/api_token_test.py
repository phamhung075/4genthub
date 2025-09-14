"""
Tests for API Token Model
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from fastmcp.auth.models.api_token import ApiToken, Base


class TestApiToken:
    """Test API Token model functionality"""
    
    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing"""
        now = datetime.now(timezone.utc)
        return {
            "id": "tok_12345abcde",
            "user_id": "user_67890fghij",
            "name": "Test API Token",
            "token_hash": "sha256_hash_of_token",
            "scopes": ["read", "write"],
            "created_at": now,
            "expires_at": now + timedelta(days=30),
            "last_used_at": None,
            "usage_count": 0,
            "rate_limit": 1000,
            "is_active": True
        }
    
    def test_api_token_table_name(self):
        """Test that ApiToken has correct table name"""
        assert ApiToken.__tablename__ == 'api_tokens'
    
    def test_api_token_columns(self):
        """Test that ApiToken model has all expected columns"""
        columns = ApiToken.__table__.columns.keys()
        expected_columns = [
            'id', 'user_id', 'name', 'token_hash', 'scopes',
            'created_at', 'expires_at', 'last_used_at',
            'usage_count', 'rate_limit', 'is_active'
        ]
        
        for col in expected_columns:
            assert col in columns
    
    def test_api_token_creation(self, sample_token_data):
        """Test creating an ApiToken instance"""
        token = ApiToken(**sample_token_data)
        
        assert token.id == sample_token_data["id"]
        assert token.user_id == sample_token_data["user_id"]
        assert token.name == sample_token_data["name"]
        assert token.token_hash == sample_token_data["token_hash"]
        assert token.scopes == sample_token_data["scopes"]
        assert token.created_at == sample_token_data["created_at"]
        assert token.expires_at == sample_token_data["expires_at"]
        assert token.last_used_at is None
        assert token.usage_count == 0
        assert token.rate_limit == 1000
        assert token.is_active is True
    
    def test_api_token_defaults(self):
        """Test ApiToken default values"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=expires
        )
        
        # Test default values (SQLAlchemy column defaults only work at DB insert time)
        assert token.scopes is None  # SQLAlchemy doesn't auto-populate mutable defaults
        assert token.usage_count is None  # Column defaults only work at DB insert
        assert token.rate_limit is None  # Column defaults only work at DB insert
        assert token.is_active is None  # Column defaults only work at DB insert
        assert token.last_used_at is None
    
    def test_to_dict_basic(self, sample_token_data):
        """Test converting ApiToken to dictionary"""
        token = ApiToken(**sample_token_data)
        
        result = token.to_dict()
        
        # Should not include token by default
        assert "token" not in result
        
        # Should include all other fields
        assert result["id"] == sample_token_data["id"]
        assert result["name"] == sample_token_data["name"]
        assert result["scopes"] == sample_token_data["scopes"]
        assert result["user_id"] == sample_token_data["user_id"]
        assert result["usage_count"] == sample_token_data["usage_count"]
        assert result["rate_limit"] == sample_token_data["rate_limit"]
        assert result["is_active"] == sample_token_data["is_active"]
    
    def test_to_dict_with_token(self, sample_token_data):
        """Test converting ApiToken to dictionary including token value"""
        token = ApiToken(**sample_token_data)
        token_value = "mcp_live_1234567890abcdef"
        
        result = token.to_dict(include_token=True, token_value=token_value)
        
        # Should include token when requested
        assert result["token"] == token_value
        assert result["id"] == sample_token_data["id"]
    
    def test_to_dict_include_token_no_value(self, sample_token_data):
        """Test converting with include_token=True but no token_value"""
        token = ApiToken(**sample_token_data)
        
        result = token.to_dict(include_token=True)
        
        # Should not include token if no value provided
        assert "token" not in result
    
    def test_to_dict_datetime_formatting(self, sample_token_data):
        """Test that datetime fields are properly formatted in to_dict"""
        token = ApiToken(**sample_token_data)
        
        result = token.to_dict()
        
        # Should format datetime fields as ISO strings
        assert result["created_at"] == sample_token_data["created_at"].isoformat()
        assert result["expires_at"] == sample_token_data["expires_at"].isoformat()
        assert result["last_used_at"] is None  # None should remain None
    
    def test_to_dict_with_last_used(self, sample_token_data):
        """Test to_dict when token has been used"""
        last_used = datetime.now(timezone.utc) - timedelta(hours=2)
        sample_token_data["last_used_at"] = last_used
        sample_token_data["usage_count"] = 5
        
        token = ApiToken(**sample_token_data)
        
        result = token.to_dict()
        
        assert result["last_used_at"] == last_used.isoformat()
        assert result["usage_count"] == 5
    
    def test_to_dict_none_datetimes(self):
        """Test to_dict with None datetime values"""
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=None,  # Test None datetime
            last_used_at=None
        )
        
        result = token.to_dict()
        
        assert result["created_at"] is None
        assert result["last_used_at"] is None
        assert result["expires_at"] is not None  # expires_at is provided
    
    def test_to_dict_empty_scopes(self):
        """Test to_dict with empty or None scopes"""
        now = datetime.now(timezone.utc)
        
        # Test with None scopes
        token1 = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=now + timedelta(days=30),
            scopes=None
        )
        
        result1 = token1.to_dict()
        assert result1["scopes"] == []  # None should become empty list
        
        # Test with empty list scopes
        token2 = ApiToken(
            id="tok_test456",
            user_id="user_test789",
            name="Test Token 2",
            token_hash="hash456",
            expires_at=now + timedelta(days=30),
            scopes=[]
        )
        
        result2 = token2.to_dict()
        assert result2["scopes"] == []
    
    def test_api_token_column_constraints(self):
        """Test column constraints and properties"""
        table = ApiToken.__table__
        
        # Primary key
        assert table.columns['id'].primary_key is True
        
        # Nullable constraints
        assert table.columns['user_id'].nullable is False
        assert table.columns['name'].nullable is False
        assert table.columns['token_hash'].nullable is False
        assert table.columns['created_at'].nullable is False
        assert table.columns['expires_at'].nullable is False
        assert table.columns['last_used_at'].nullable is True
        
        # Unique constraints
        assert table.columns['token_hash'].unique is True
        
        # Index checks
        assert table.columns['user_id'].index is True
        assert table.columns['token_hash'].index is True
        
        # Default values
        assert table.columns['usage_count'].default.arg == 0
        assert table.columns['rate_limit'].default.arg == 1000
        assert table.columns['is_active'].default.arg is True
    
    def test_api_token_id_format(self):
        """Test that token ID follows expected format"""
        # The model doesn't enforce format, but we can test expected usage
        token_id = "tok_1234567890abcdef"
        
        token = ApiToken(
            id=token_id,
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        assert token.id == token_id
        assert token.id.startswith("tok_")
    
    def test_api_token_scopes_array(self):
        """Test that scopes are properly handled as array"""
        scopes = ["read", "write", "admin"]
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            scopes=scopes
        )
        
        assert token.scopes == scopes
        
        result = token.to_dict()
        assert result["scopes"] == scopes
    
    def test_api_token_rate_limit_tracking(self):
        """Test rate limit and usage count tracking"""
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            usage_count=150,
            rate_limit=500
        )
        
        assert token.usage_count == 150
        assert token.rate_limit == 500
        
        result = token.to_dict()
        assert result["usage_count"] == 150
        assert result["rate_limit"] == 500
    
    def test_api_token_active_status(self):
        """Test token active status"""
        # Test active token
        active_token = ApiToken(
            id="tok_active123",
            user_id="user_test456",
            name="Active Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        
        assert active_token.is_active is True
        
        # Test inactive token
        inactive_token = ApiToken(
            id="tok_inactive456",
            user_id="user_test789",
            name="Inactive Token",
            token_hash="hash456",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=False
        )
        
        assert inactive_token.is_active is False
        
        # Check dict conversion
        active_result = active_token.to_dict()
        inactive_result = inactive_token.to_dict()
        
        assert active_result["is_active"] is True
        assert inactive_result["is_active"] is False


class TestApiTokenEdgeCases:
    """Test edge cases and error conditions for ApiToken"""
    
    def test_api_token_with_very_long_name(self):
        """Test token with maximum length name"""
        long_name = "A" * 255  # Maximum length for name field
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name=long_name,
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        assert token.name == long_name
        assert len(token.name) == 255
    
    def test_api_token_with_many_scopes(self):
        """Test token with many scopes"""
        many_scopes = [f"scope_{i}" for i in range(20)]
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Test Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            scopes=many_scopes
        )
        
        assert len(token.scopes) == 20
        assert "scope_0" in token.scopes
        assert "scope_19" in token.scopes
        
        result = token.to_dict()
        assert len(result["scopes"]) == 20
    
    def test_api_token_zero_rate_limit(self):
        """Test token with zero rate limit (unlimited)"""
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="Unlimited Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            rate_limit=0
        )
        
        assert token.rate_limit == 0
        
        result = token.to_dict()
        assert result["rate_limit"] == 0
    
    def test_api_token_high_usage_count(self):
        """Test token with high usage count"""
        high_usage = 1000000
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name="High Usage Token",
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            usage_count=high_usage
        )
        
        assert token.usage_count == high_usage
        
        result = token.to_dict()
        assert result["usage_count"] == high_usage
    
    def test_api_token_past_expiration(self):
        """Test token that has already expired"""
        past_date = datetime.now(timezone.utc) - timedelta(days=10)
        
        token = ApiToken(
            id="tok_expired123",
            user_id="user_test456",
            name="Expired Token",
            token_hash="hash123",
            expires_at=past_date
        )
        
        assert token.expires_at == past_date
        
        result = token.to_dict()
        assert result["expires_at"] == past_date.isoformat()
    
    def test_api_token_special_characters_in_name(self):
        """Test token with special characters in name"""
        special_name = "Test Token 🔑 (API) - #1"
        
        token = ApiToken(
            id="tok_test123",
            user_id="user_test456",
            name=special_name,
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        assert token.name == special_name
        
        result = token.to_dict()
        assert result["name"] == special_name


class TestApiTokenBase:
    """Test ApiToken base class functionality"""
    
    def test_base_class_inheritance(self):
        """Test that ApiToken inherits from declarative base"""
        assert hasattr(ApiToken, '__table__')
        assert hasattr(ApiToken, 'metadata')
        
    def test_base_metadata(self):
        """Test that Base metadata is accessible"""
        assert Base.metadata is not None
        assert ApiToken.__table__ in Base.metadata.tables.values()