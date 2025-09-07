"""
Test datetime serialization for token routes
"""
import pytest
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
import json

from fastmcp.server.routes.token_router import TokenResponse


class TestTokenDatetimeSerialization:
    """Test that datetime fields in TokenResponse are properly serialized"""
    
    def test_token_response_model_dump_json_mode(self):
        """Test that model_dump with mode='json' properly serializes datetime fields"""
        # Create a TokenResponse with datetime fields
        response = TokenResponse(
            id="tok_test123",
            name="Test Token",
            token="jwt-token-here",
            scopes=["read", "write"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            last_used_at=datetime.utcnow(),
            usage_count=5,
            rate_limit=1000,
            is_active=True,
            metadata={"key": "value"}
        )
        
        # Test model_dump with mode='json' - should not raise an error
        json_dict = response.model_dump(mode='json')
        
        # Verify the result is JSON serializable
        json_str = json.dumps(json_dict)
        assert json_str is not None
        
        # Verify datetime fields are serialized as ISO format strings
        assert isinstance(json_dict['created_at'], str)
        assert isinstance(json_dict['expires_at'], str)
        assert isinstance(json_dict['last_used_at'], str)
        
        # Verify the datetime strings are in ISO format
        assert 'T' in json_dict['created_at']  # ISO format includes 'T' separator
        assert 'T' in json_dict['expires_at']
        assert 'T' in json_dict['last_used_at']
    
    def test_token_response_dict_fails_json_serialization(self):
        """Test that using .dict() on TokenResponse fails JSON serialization"""
        # Create a TokenResponse with datetime fields
        response = TokenResponse(
            id="tok_test456",
            name="Test Token 2",
            token=None,  # Token not included in list responses
            scopes=["read"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=15),
            last_used_at=None,  # Can be None
            usage_count=0,
            rate_limit=500,
            is_active=True,
            metadata={}
        )
        
        # Using .dict() keeps datetime objects
        dict_result = response.dict()
        
        # Verify datetime objects are still datetime instances
        assert isinstance(dict_result['created_at'], datetime)
        assert isinstance(dict_result['expires_at'], datetime)
        assert dict_result['last_used_at'] is None  # None is OK
        
        # Attempting to JSON serialize should fail
        with pytest.raises(TypeError) as exc_info:
            json.dumps(dict_result)
        
        assert "not JSON serializable" in str(exc_info.value)
    
    def test_token_response_with_none_datetime(self):
        """Test that None datetime fields are handled correctly"""
        response = TokenResponse(
            id="tok_test789",
            name="Test Token 3",
            token=None,
            scopes=[],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            last_used_at=None,  # This can be None for unused tokens
            usage_count=0,
            rate_limit=100,
            is_active=False,
            metadata={}
        )
        
        # Test model_dump with mode='json'
        json_dict = response.model_dump(mode='json')
        
        # Verify None is preserved
        assert json_dict['last_used_at'] is None
        
        # Verify it's JSON serializable
        json_str = json.dumps(json_dict)
        assert json_str is not None
        
        # Verify we can parse it back
        parsed = json.loads(json_str)
        assert parsed['last_used_at'] is None
    
    def test_pydantic_v2_compatibility(self):
        """Test that we're using Pydantic v2 methods correctly"""
        response = TokenResponse(
            id="tok_pydantic",
            name="Pydantic Test",
            token="test-token",
            scopes=["admin"],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            last_used_at=datetime.utcnow(),
            usage_count=10,
            rate_limit=10000,
            is_active=True,
            metadata={"version": "v2"}
        )
        
        # Verify Pydantic v2 methods exist and work
        assert hasattr(response, 'model_dump')
        assert hasattr(response, 'model_dump_json')
        
        # Test model_dump_json() directly returns JSON string
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        
        # Verify we can parse it
        parsed = json.loads(json_str)
        assert parsed['id'] == "tok_pydantic"
        assert isinstance(parsed['created_at'], str)