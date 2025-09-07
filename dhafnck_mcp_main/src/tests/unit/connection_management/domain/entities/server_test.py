"""Unit tests for Server domain entity"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastmcp.connection_management.domain.entities.server import Server
from fastmcp.connection_management.domain.value_objects.server_status import ServerStatus
from fastmcp.connection_management.domain.value_objects.server_capabilities import ServerCapabilities
from fastmcp.connection_management.domain.events.connection_events import ServerHealthChecked


class TestServer:
    """Tests for Server domain entity"""
    
    def test_create_server(self):
        """Test creating a Server with factory method"""
        name = "test-server"
        version = "1.0.0"
        environment = {"env": "test", "debug": True}
        authentication = {"enabled": True, "mvp_mode": False}
        task_management = {"max_tasks": 100}
        
        with patch('fastmcp.connection_management.domain.entities.server.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            server = Server.create(
                name=name,
                version=version,
                environment=environment,
                authentication=authentication,
                task_management=task_management
            )
            
            assert server.name == name
            assert server.version == version
            assert server.started_at == mock_now
            assert server.restart_count == 0
            assert server.environment == environment
            assert server.authentication == authentication
            assert server.task_management == task_management
    
    def test_get_uptime_seconds(self):
        """Test calculating server uptime"""
        with patch('fastmcp.connection_management.domain.entities.server.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            server = Server.create(
                name="test-server",
                version="1.0.0",
                environment={},
                authentication={},
                task_management={}
            )
            
            # Move time forward by 3 hours
            current_time = datetime(2024, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = current_time
            
            uptime = server.get_uptime_seconds()
            assert uptime == 3 * 3600  # 3 hours in seconds
    
    def test_check_health_healthy(self):
        """Test health check for a healthy server"""
        with patch('fastmcp.connection_management.domain.entities.server.datetime') as mock_datetime:
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = start_time
            
            server = Server.create(
                name="test-server",
                version="1.0.0",
                environment={"env": "test"},
                authentication={"enabled": True},
                task_management={"max_tasks": 100}
            )
            
            # Move time forward by 1 hour
            current_time = datetime(2024, 1, 1, 11, 0, 0)
            mock_datetime.now.return_value = current_time
            
            status = server.check_health()
            
            assert isinstance(status, ServerStatus)
            assert status.status == "healthy"
            assert status.server_name == "test-server"
            assert status.version == "1.0.0"
            assert status.uptime_seconds == 3600
            assert status.restart_count == 0
            
            # Check details
            assert status.details["status"] == "healthy"
            assert status.details["uptime_seconds"] == 3600
            assert status.details["authentication"]["enabled"] is True
            
            # Check that event was raised
            events = server.get_events()
            assert len(events) == 1
            assert isinstance(events[0], ServerHealthChecked)
            assert events[0].server_name == "test-server"
            assert events[0].status == "healthy"
    
    def test_check_health_with_restarts(self):
        """Test health check with restart count"""
        server = Server.create(
            name="test-server",
            version="1.0.0",
            environment={},
            authentication={},
            task_management={}
        )
        
        # Simulate restarts
        server.restart()
        server.restart()
        
        status = server.check_health()
        
        assert status.restart_count == 2
        assert status.details["restart_count"] == 2
    
    def test_get_capabilities_full(self):
        """Test getting server capabilities with authentication enabled"""
        server = Server.create(
            name="test-server",
            version="2.0.0",
            environment={},
            authentication={"enabled": True, "mvp_mode": False},
            task_management={}
        )
        
        capabilities = server.get_capabilities()
        
        assert isinstance(capabilities, ServerCapabilities)
        assert capabilities.version == "2.0.0"
        assert capabilities.authentication_enabled is True
        assert capabilities.mvp_mode is False
        
        # Check core features
        assert "Task Management" in capabilities.core_features
        assert "Project Management" in capabilities.core_features
        assert "Multi-Agent Coordination" in capabilities.core_features
        assert "Token-based Authentication" in capabilities.core_features
        
        # Check available actions
        assert "connection_management" in capabilities.available_actions
        assert "health_check" in capabilities.available_actions["connection_management"]
        assert "authentication" in capabilities.available_actions
        assert "validate_token" in capabilities.available_actions["authentication"]
        assert "task_management" in capabilities.available_actions
        assert "create" in capabilities.available_actions["task_management"]
    
    def test_get_capabilities_mvp_mode(self):
        """Test getting server capabilities in MVP mode"""
        server = Server.create(
            name="test-server",
            version="1.0.0",
            environment={},
            authentication={"enabled": False, "mvp_mode": True},
            task_management={}
        )
        
        capabilities = server.get_capabilities()
        
        assert capabilities.authentication_enabled is False
        assert capabilities.mvp_mode is True
    
    def test_restart(self):
        """Test server restart functionality"""
        with patch('fastmcp.connection_management.domain.entities.server.datetime') as mock_datetime:
            initial_time = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = initial_time
            
            server = Server.create(
                name="test-server",
                version="1.0.0",
                environment={},
                authentication={},
                task_management={}
            )
            
            assert server.restart_count == 0
            assert server.started_at == initial_time
            
            # Simulate restart after 2 hours
            restart_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = restart_time
            
            server.restart()
            
            assert server.restart_count == 1
            assert server.started_at == restart_time
            
            # Another restart
            second_restart_time = datetime(2024, 1, 1, 14, 0, 0)
            mock_datetime.now.return_value = second_restart_time
            
            server.restart()
            
            assert server.restart_count == 2
            assert server.started_at == second_restart_time
    
    def test_domain_events(self):
        """Test domain event management"""
        server = Server.create(
            name="test-server",
            version="1.0.0",
            environment={},
            authentication={},
            task_management={}
        )
        
        # Initially no events
        assert len(server.get_events()) == 0
        
        # Check health raises an event
        server.check_health()
        events = server.get_events()
        assert len(events) == 1
        assert isinstance(events[0], ServerHealthChecked)
        
        # Get events returns a copy
        events2 = server.get_events()
        assert events is not server._events
        assert events2 is not server._events
        
        # Clear events
        server.clear_events()
        assert len(server.get_events()) == 0
    
    def test_server_with_complex_configuration(self):
        """Test server with complex configuration"""
        complex_env = {
            "env": "production",
            "debug": False,
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "dhafnck_mcp"
            },
            "cache": {
                "enabled": True,
                "ttl": 300
            }
        }
        
        complex_auth = {
            "enabled": True,
            "mvp_mode": False,
            "token_expiry": 3600,
            "rate_limit": {
                "requests_per_minute": 60,
                "burst": 100
            }
        }
        
        complex_task_mgmt = {
            "max_tasks": 1000,
            "max_subtasks": 50,
            "auto_complete": True,
            "priorities": ["low", "medium", "high", "critical"]
        }
        
        server = Server.create(
            name="production-server",
            version="3.0.0",
            environment=complex_env,
            authentication=complex_auth,
            task_management=complex_task_mgmt
        )
        
        # Check that complex configuration is preserved
        assert server.environment["database"]["port"] == 5432
        assert server.authentication["rate_limit"]["requests_per_minute"] == 60
        assert server.task_management["priorities"][3] == "critical"
        
        # Check health includes complex configuration
        status = server.check_health()
        assert status.details["environment"]["cache"]["enabled"] is True
        assert status.details["authentication"]["token_expiry"] == 3600
        assert status.details["task_management"]["max_subtasks"] == 50