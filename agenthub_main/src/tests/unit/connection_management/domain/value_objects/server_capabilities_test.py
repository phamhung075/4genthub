"""Unit tests for ServerCapabilities Value Object following DDD patterns"""

import pytest
from typing import List, Dict

from fastmcp.connection_management.domain.value_objects.server_capabilities import ServerCapabilities


class TestServerCapabilities:
    """Test suite for ServerCapabilities value object following DDD patterns"""
    
    def test_server_capabilities_creation_success(self):
        """Test successful creation of ServerCapabilities with valid data"""
        capabilities = ServerCapabilities(
            core_features=["authentication", "task_management", "context_management"],
            available_actions={
                "task": ["create", "update", "delete"],
                "project": ["create", "list"],
                "context": ["get", "update", "resolve"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.core_features == ["authentication", "task_management", "context_management"]
        assert capabilities.available_actions["task"] == ["create", "update", "delete"]
        assert capabilities.authentication_enabled is True
        assert capabilities.mvp_mode is False
        assert capabilities.version == "1.0.0"
    
    def test_server_capabilities_immutability(self):
        """Test that ServerCapabilities is immutable (frozen dataclass)"""
        capabilities = ServerCapabilities(
            core_features=["auth"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        # Attempt to modify should raise error
        with pytest.raises(AttributeError):
            capabilities.version = "2.0.0"
        
        with pytest.raises(AttributeError):
            capabilities.authentication_enabled = False
    
    def test_empty_core_features_raises_error(self):
        """Test that empty core features raises ValueError"""
        with pytest.raises(ValueError, match="Core features cannot be empty"):
            ServerCapabilities(
                core_features=[],
                available_actions={"task": ["create"]},
                authentication_enabled=True,
                mvp_mode=False,
                version="1.0.0"
            )
    
    def test_empty_available_actions_raises_error(self):
        """Test that empty available actions raises ValueError"""
        with pytest.raises(ValueError, match="Available actions cannot be empty"):
            ServerCapabilities(
                core_features=["auth"],
                available_actions={},
                authentication_enabled=True,
                mvp_mode=False,
                version="1.0.0"
            )
    
    def test_empty_version_raises_error(self):
        """Test that empty version raises ValueError"""
        with pytest.raises(ValueError, match="Version cannot be empty"):
            ServerCapabilities(
                core_features=["auth"],
                available_actions={"task": ["create"]},
                authentication_enabled=True,
                mvp_mode=False,
                version=""
            )
    
    def test_get_total_actions_count(self):
        """Test calculation of total actions count"""
        capabilities = ServerCapabilities(
            core_features=["auth"],
            available_actions={
                "task": ["create", "update", "delete"],
                "project": ["create", "list"],
                "context": ["get", "update", "resolve", "delegate"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        # 3 task + 2 project + 4 context = 9 total
        assert capabilities.get_total_actions_count() == 9
    
    def test_get_total_actions_count_single_category(self):
        """Test total actions count with single category"""
        capabilities = ServerCapabilities(
            core_features=["auth"],
            available_actions={
                "task": ["create", "update", "delete"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.get_total_actions_count() == 3
    
    def test_has_feature_existing(self):
        """Test has_feature returns True for existing feature"""
        capabilities = ServerCapabilities(
            core_features=["authentication", "task_management", "context_management"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.has_feature("authentication") is True
        assert capabilities.has_feature("task_management") is True
        assert capabilities.has_feature("context_management") is True
    
    def test_has_feature_non_existing(self):
        """Test has_feature returns False for non-existing feature"""
        capabilities = ServerCapabilities(
            core_features=["authentication"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.has_feature("reporting") is False
        assert capabilities.has_feature("analytics") is False
    
    def test_has_action_category_existing(self):
        """Test has_action_category returns True for existing category"""
        capabilities = ServerCapabilities(
            core_features=["auth"],
            available_actions={
                "task": ["create", "update"],
                "project": ["list"],
                "context": ["get"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.has_action_category("task") is True
        assert capabilities.has_action_category("project") is True
        assert capabilities.has_action_category("context") is True
    
    def test_has_action_category_non_existing(self):
        """Test has_action_category returns False for non-existing category"""
        capabilities = ServerCapabilities(
            core_features=["auth"],
            available_actions={
                "task": ["create"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        assert capabilities.has_action_category("user") is False
        assert capabilities.has_action_category("report") is False
    
    def test_to_dict_complete(self):
        """Test complete dictionary conversion"""
        capabilities = ServerCapabilities(
            core_features=["authentication", "task_management"],
            available_actions={
                "task": ["create", "update", "delete"],
                "project": ["create", "list"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0"
        )
        
        result = capabilities.to_dict()
        
        assert result["success"] is True
        assert result["core_features"] == ["authentication", "task_management"]
        assert result["available_actions"] == {
            "task": ["create", "update", "delete"],
            "project": ["create", "list"]
        }
        assert result["authentication_enabled"] is True
        assert result["mvp_mode"] is False
        assert result["version"] == "1.0.0"
        assert result["total_actions"] == 5
    
    def test_mvp_mode_enabled(self):
        """Test ServerCapabilities with MVP mode enabled"""
        capabilities = ServerCapabilities(
            core_features=["basic_auth"],
            available_actions={
                "task": ["create", "list"]
            },
            authentication_enabled=False,
            mvp_mode=True,
            version="0.1.0"
        )
        
        assert capabilities.mvp_mode is True
        assert capabilities.authentication_enabled is False
        
        result = capabilities.to_dict()
        assert result["mvp_mode"] is True
        assert result["authentication_enabled"] is False
    
    def test_complex_action_structure(self):
        """Test with complex nested action structure"""
        capabilities = ServerCapabilities(
            core_features=["full_features"],
            available_actions={
                "task": ["create", "update", "delete", "complete", "search"],
                "project": ["create", "list", "update", "archive"],
                "context": ["get", "update", "resolve", "delegate", "inherit"],
                "user": ["authenticate", "authorize", "profile"],
                "report": ["generate", "export"]
            },
            authentication_enabled=True,
            mvp_mode=False,
            version="2.0.0"
        )
        
        assert capabilities.get_total_actions_count() == 19
        assert capabilities.has_action_category("task") is True
        assert capabilities.has_action_category("user") is True
        assert capabilities.has_action_category("report") is True
        assert len(capabilities.available_actions) == 5
    
    def test_version_formats(self):
        """Test various version format support"""
        # Semantic version
        capabilities1 = ServerCapabilities(
            core_features=["auth"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.2.3"
        )
        assert capabilities1.version == "1.2.3"
        
        # Version with suffix
        capabilities2 = ServerCapabilities(
            core_features=["auth"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0-beta"
        )
        assert capabilities2.version == "1.0.0-beta"
        
        # Simple version
        capabilities3 = ServerCapabilities(
            core_features=["auth"],
            available_actions={"task": ["create"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="v1"
        )
        assert capabilities3.version == "v1"