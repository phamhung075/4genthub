from typing import List
"""
Mock MCP Server for Performance Testing

Provides controlled testing environment for validating session hook performance
without external dependencies.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading
import logging
from pathlib import Path
from unittest.mock import Mock
import secrets
import base64

logger = logging.getLogger(__name__)


@dataclass
class MockTask:
    """Mock task data structure matching MCP server format."""
    id: str
    title: str
    description: str
    status: str = "todo"
    priority: str = "medium"
    assignees: List[str] = None
    created_at: str = None
    updated_at: str = None
    estimated_effort: str = "1 hour"
    git_branch_id: str = None
    
    def __post_init__(self):
        if not self.assignees:
            self.assignees = ["coding-agent"]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass 
class MockGitBranch:
    """Mock git branch data structure."""
    id: str
    name: str
    description: str
    project_id: str
    created_at: str = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class MockKeycloakServer:
    """Mock Keycloak server for authentication testing."""
    
    def __init__(self):
        self.tokens: Dict[str, Dict] = {}
        self.client_credentials = {
            "claude-hooks": "test-secret"
        }
        
    def authenticate_client(self, client_id: str, client_secret: str) -> Optional[Dict]:
        """Simulate client credentials authentication."""
        if self.client_credentials.get(client_id) == client_secret:
            # Generate mock JWT token
            token_data = {
                "access_token": self._generate_mock_jwt(),
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "openid profile email mcp:read mcp:write"
            }
            return token_data
        return None
    
    def _generate_mock_jwt(self) -> str:
        """Generate a mock JWT token for testing."""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "service-account-claude-hooks",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "aud": "agenthub",
            "iss": "http://localhost:8080/realms/agenthub"
        }
        
        # Simple base64 encoding for mock token (not cryptographically secure)
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = secrets.token_urlsafe(32)
        
        return f"{header_b64}.{payload_b64}.{signature}"
    
    def validate_token(self, token: str) -> bool:
        """Validate mock JWT token."""
        try:
            # Simple validation for testing
            parts = token.split('.')
            return len(parts) == 3
        except Exception:
            return False


class MockMCPServer:
    """Mock MCP server for controlled performance testing."""
    
    def __init__(self, 
                 response_delay: float = 0.1,
                 error_rate: float = 0.0,
                 token_failure_rate: float = 0.0):
        """Initialize mock server with configurable behavior."""
        self.response_delay = response_delay
        self.error_rate = error_rate  
        self.token_failure_rate = token_failure_rate
        
        self.keycloak = MockKeycloakServer()
        self.request_count = 0
        self.request_history: List[Dict] = []
        self.performance_metrics = {
            "total_requests": 0,
            "avg_response_time": 0.0,
            "error_count": 0,
            "token_failures": 0
        }
        
        # Mock data
        self._init_mock_data()
        self.lock = threading.RLock()
    
    def _init_mock_data(self):
        """Initialize mock tasks and branches."""
        self.projects = {
            "proj-123": {"id": "proj-123", "name": "Test Project"}
        }
        
        self.git_branches = {
            "branch-456": MockGitBranch(
                id="branch-456",
                name="feature/performance-testing", 
                description="Performance testing branch",
                project_id="proj-123"
            )
        }
        
        self.tasks = {
            f"task-{i:03d}": MockTask(
                id=f"task-{i:03d}",
                title=f"Test Task {i}",
                description=f"Description for test task {i}",
                status="todo" if i % 3 == 0 else "in_progress",
                priority=["low", "medium", "high"][i % 3],
                git_branch_id="branch-456"
            ) for i in range(1, 21)  # 20 mock tasks
        }
    
    async def simulate_request_delay(self):
        """Simulate network and processing delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def should_simulate_error(self) -> bool:
        """Determine if we should simulate an error."""
        return self.error_rate > 0 and time.time() % 1.0 < self.error_rate
    
    def should_simulate_token_failure(self) -> bool:
        """Determine if we should simulate token failure.""" 
        return self.token_failure_rate > 0 and time.time() % 1.0 < self.token_failure_rate
    
    async def handle_manage_task(self, payload: Dict) -> Dict:
        """Handle manage_task requests."""
        start_time = time.time()
        
        with self.lock:
            self.request_count += 1
            self.performance_metrics["total_requests"] += 1
        
        await self.simulate_request_delay()
        
        if self.should_simulate_error():
            self.performance_metrics["error_count"] += 1
            return {"success": False, "error": "Simulated server error"}
        
        action = payload.get("action", "list")
        
        if action == "list":
            status_filter = payload.get("status")
            limit = payload.get("limit", 10)
            
            filtered_tasks = []
            for task in self.tasks.values():
                if not status_filter or task.status == status_filter:
                    filtered_tasks.append(asdict(task))
                if len(filtered_tasks) >= limit:
                    break
            
            response = {
                "success": True,
                "data": {
                    "tasks": filtered_tasks,
                    "total": len(filtered_tasks),
                    "page": 1
                }
            }
            
        elif action == "next":
            git_branch_id = payload.get("git_branch_id")
            if git_branch_id and git_branch_id in self.git_branches:
                # Return next prioritized task
                next_task = None
                for task in self.tasks.values():
                    if task.status == "todo" and task.git_branch_id == git_branch_id:
                        next_task = asdict(task)
                        break
                
                response = {
                    "success": True,
                    "data": {
                        "task": next_task,
                        "workflow_hints": ["Start with unit tests", "Review requirements"],
                        "estimated_duration": "2 hours"
                    }
                }
            else:
                response = {
                    "success": False,
                    "error": "Invalid git_branch_id"
                }
        
        else:
            response = {"success": False, "error": f"Unknown action: {action}"}
        
        # Update metrics
        response_time = time.time() - start_time
        with self.lock:
            current_avg = self.performance_metrics["avg_response_time"]
            count = self.performance_metrics["total_requests"]
            self.performance_metrics["avg_response_time"] = (
                (current_avg * (count - 1) + response_time) / count
            )
            
            self.request_history.append({
                "timestamp": time.time(),
                "action": action,
                "response_time": response_time,
                "success": response.get("success", False)
            })
        
        return response
    
    async def handle_token_request(self, payload: Dict) -> Dict:
        """Handle Keycloak token requests."""
        if self.should_simulate_token_failure():
            self.performance_metrics["token_failures"] += 1
            return {"error": "invalid_client"}
        
        client_id = payload.get("client_id")
        client_secret = payload.get("client_secret")
        
        token_data = self.keycloak.authenticate_client(client_id, client_secret)
        if token_data:
            return token_data
        else:
            return {"error": "unauthorized"}
    
    def get_performance_metrics(self) -> Dict:
        """Get accumulated performance metrics."""
        with self.lock:
            return self.performance_metrics.copy()
    
    def get_request_history(self) -> List[Dict]:
        """Get request history for analysis."""
        with self.lock:
            return self.request_history.copy()
    
    def reset_metrics(self):
        """Reset performance metrics."""
        with self.lock:
            self.performance_metrics = {
                "total_requests": 0,
                "avg_response_time": 0.0,
                "error_count": 0,
                "token_failures": 0
            }
            self.request_history = []
            self.request_count = 0
    
    def configure_behavior(self, 
                          response_delay: Optional[float] = None,
                          error_rate: Optional[float] = None,
                          token_failure_rate: Optional[float] = None):
        """Dynamically configure mock server behavior."""
        if response_delay is not None:
            self.response_delay = response_delay
        if error_rate is not None:
            self.error_rate = error_rate
        if token_failure_rate is not None:
            self.token_failure_rate = token_failure_rate


class MockMCPServerManager:
    """Manager for mock MCP server instances."""
    
    def __init__(self):
        self.servers: Dict[str, MockMCPServer] = {}
    
    def create_server(self, name: str, **config) -> MockMCPServer:
        """Create a named mock server instance."""
        server = MockMCPServer(**config)
        self.servers[name] = server
        return server
    
    def get_server(self, name: str) -> Optional[MockMCPServer]:
        """Get existing server by name."""
        return self.servers.get(name)
    
    def cleanup_server(self, name: str):
        """Remove server instance."""
        self.servers.pop(name, None)
    
    def cleanup_all(self):
        """Remove all server instances."""
        self.servers.clear()


# Global manager instance
mock_server_manager = MockMCPServerManager()


def create_performance_test_server(**config) -> MockMCPServer:
    """Convenience function to create a performance test server."""
    return mock_server_manager.create_server("performance_test", **config)


def create_high_latency_server() -> MockMCPServer:
    """Create server with high latency for stress testing."""
    return mock_server_manager.create_server(
        "high_latency",
        response_delay=2.0,
        error_rate=0.1
    )


def create_unreliable_server() -> MockMCPServer:
    """Create unreliable server for fallback testing.""" 
    return mock_server_manager.create_server(
        "unreliable",
        response_delay=0.5,
        error_rate=0.3,
        token_failure_rate=0.2
    )