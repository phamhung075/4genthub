# MCP HTTP Client Usage Examples

## Overview

This document provides practical, real-world examples of using the MCP HTTP Client Module. Each example includes complete code snippets, error handling, and best practices.

## Table of Contents

- [Basic Setup](#basic-setup)
- [Authentication Flow](#authentication-flow)
- [Task Management](#task-management)
- [Error Handling](#error-handling)
- [Cache Management](#cache-management)
- [Performance Optimization](#performance-optimization)
- [Integration Patterns](#integration-patterns)
- [Testing Examples](#testing-examples)

---

## Basic Setup

### Simple Client Creation

```python
from utils.mcp_client import get_default_client, create_mcp_client

# Quick start with default optimized client
client = get_default_client()

# Or create specific client types
basic_client = create_mcp_client("basic")
resilient_client = create_mcp_client("resilient")
optimized_client = create_mcp_client("optimized")
```

### Environment Configuration

```python
import os
from utils.mcp_client import OptimizedMCPClient

# Set environment variables programmatically (for testing)
os.environ.update({
    'MCP_SERVER_URL': 'http://localhost:8000',
    'KEYCLOAK_URL': 'http://localhost:8080',
    'KEYCLOAK_REALM': 'dhafnck',
    'KEYCLOAK_CLIENT_ID': 'claude-hooks',
    'KEYCLOAK_CLIENT_SECRET': 'your-secret-here'
})

# Create client with configuration
client = OptimizedMCPClient()
```

### Connection Testing

```python
from utils.mcp_client import test_mcp_connection

def startup_check():
    """Verify MCP connectivity on application startup"""
    print("🔌 Checking MCP server connectivity...")
    
    if test_mcp_connection():
        print("✅ MCP server is ready")
        return True
    else:
        print("❌ MCP server unavailable - check configuration")
        return False

# Use in application startup
if __name__ == "__main__":
    if startup_check():
        # Continue with application
        main()
    else:
        exit(1)
```

---

## Authentication Flow

### Basic Authentication

```python
from utils.mcp_client import get_default_client
import logging

logger = logging.getLogger(__name__)

def authenticate_client():
    """Authenticate MCP client with error handling"""
    client = get_default_client()
    
    try:
        if client.authenticate():
            logger.info("✅ MCP authentication successful")
            return client
        else:
            logger.error("❌ Authentication failed - check credentials")
            return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

# Usage
client = authenticate_client()
if client:
    # Proceed with authenticated requests
    tasks = client.query_pending_tasks()
```

### Token Management

```python
from utils.mcp_client import TokenManager

def manual_token_management():
    """Example of manual token management"""
    token_manager = TokenManager()
    
    # Get valid token
    token = token_manager.get_valid_token()
    if token:
        print(f"Token obtained: {token[:20]}...")
        
        # Use token in custom requests
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Make custom API call
        import requests
        response = requests.get(
            "http://localhost:8000/mcp/manage_connection",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Custom request successful")
        else:
            print(f"❌ Request failed: {response.status_code}")
    else:
        print("❌ Token acquisition failed")
```

### Service Account Integration

```python
import asyncio
from dhafnck_mcp_main.src.fastmcp.auth.service_account import ServiceAccountAuth

async def service_account_example():
    """Example using service account authentication"""
    
    # Create service account auth
    auth = ServiceAccountAuth()
    
    try:
        # Authenticate service account
        token = await auth.authenticate()
        if token:
            print(f"✅ Service account authenticated")
            print(f"Token expires in: {token.seconds_until_expiry} seconds")
            
            # Get service info
            service_info = await auth.get_service_info()
            if service_info:
                print(f"Service account: {service_info.get('preferred_username')}")
            
            # Get auth headers for requests
            headers = auth.get_auth_headers()
            print(f"Auth headers ready: {'Authorization' in headers}")
            
        else:
            print("❌ Service account authentication failed")
            
    finally:
        await auth.close()

# Run async example
# asyncio.run(service_account_example())
```

---

## Task Management

### Query Pending Tasks

```python
from utils.mcp_client import get_default_client
from datetime import datetime

def get_pending_tasks(limit=10, user_id=None):
    """Get pending tasks with comprehensive error handling"""
    client = get_default_client()
    
    try:
        print(f"📋 Querying {limit} pending tasks...")
        tasks = client.query_pending_tasks(limit=limit, user_id=user_id)
        
        if tasks:
            print(f"✅ Retrieved {len(tasks)} pending tasks")
            
            for i, task in enumerate(tasks, 1):
                title = task.get('title', 'Unknown Task')
                status = task.get('status', 'unknown')
                priority = task.get('priority', 'medium')
                assignees = task.get('assignees', 'unassigned')
                created = task.get('created_at', 'unknown')
                
                print(f"\n{i}. {title}")
                print(f"   Status: {status}")
                print(f"   Priority: {priority}")
                print(f"   Assignees: {assignees}")
                print(f"   Created: {created}")
            
            return tasks
        else:
            print("📭 No pending tasks found or server unavailable")
            return []
            
    except Exception as e:
        print(f"❌ Failed to query tasks: {e}")
        return []

# Usage examples
tasks = get_pending_tasks()
high_priority_tasks = get_pending_tasks(limit=5)
user_tasks = get_pending_tasks(user_id="user123")
```

### Get Next Recommended Task

```python
def get_next_task(git_branch_id, user_id=None):
    """Get next recommended task for a git branch"""
    client = get_default_client()
    
    if not git_branch_id:
        print("❌ Git branch ID required")
        return None
    
    try:
        print(f"🎯 Getting next task for branch: {git_branch_id[:8]}...")
        task = client.get_next_recommended_task(git_branch_id, user_id)
        
        if task:
            title = task.get('title', 'Unknown Task')
            description = task.get('description', '')
            priority = task.get('priority', 'medium')
            estimated_effort = task.get('estimated_effort', 'unknown')
            
            print(f"✅ Next recommended task: {title}")
            print(f"   Priority: {priority}")
            print(f"   Estimated effort: {estimated_effort}")
            
            if description:
                # Show first 200 characters of description
                desc_preview = description[:200]
                if len(description) > 200:
                    desc_preview += "..."
                print(f"   Description: {desc_preview}")
            
            return task
        else:
            print("🎯 No recommended tasks available")
            return None
            
    except Exception as e:
        print(f"❌ Failed to get next task: {e}")
        return None

# Usage
branch_id = "550e8400-e29b-41d4-a716-446655440000"
next_task = get_next_task(branch_id)
```

### Custom Task Queries

```python
def create_custom_task(title, description, assignees, priority="medium"):
    """Create a new task using custom payload"""
    client = get_default_client()
    
    payload = {
        "action": "create",
        "git_branch_id": "550e8400-e29b-41d4-a716-446655440001",
        "title": title,
        "description": description,
        "assignees": assignees,
        "priority": priority,
        "status": "todo"
    }
    
    try:
        response = client.make_request("/mcp/manage_task", payload)
        
        if response and response.get("success"):
            task_data = response.get("data", {})
            task_id = task_data.get("task_id")
            print(f"✅ Task created successfully: {task_id}")
            return task_data
        else:
            error_msg = response.get("message", "Unknown error") if response else "No response"
            print(f"❌ Task creation failed: {error_msg}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to create task: {e}")
        return None

# Usage
new_task = create_custom_task(
    title="Implement user authentication",
    description="Add JWT-based authentication with login and logout",
    assignees="coding-agent,@security-auditor-agent",
    priority="high"
)
```

---

## Error Handling

### Comprehensive Error Handling

```python
from utils.mcp_client import get_default_client
import requests
import logging

logger = logging.getLogger(__name__)

class MCPClientError(Exception):
    """Custom exception for MCP client errors"""
    pass

def robust_task_query(limit=10, max_retries=3):
    """Query tasks with comprehensive error handling and retries"""
    client = get_default_client()
    
    for attempt in range(max_retries):
        try:
            # Authenticate first
            if not client.authenticate():
                raise MCPClientError("Authentication failed")
            
            # Query tasks
            tasks = client.query_pending_tasks(limit=limit)
            
            if tasks is not None:
                logger.info(f"Successfully retrieved {len(tasks)} tasks on attempt {attempt + 1}")
                return tasks
            else:
                logger.warning(f"No tasks returned on attempt {attempt + 1}")
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise MCPClientError(f"Connection failed after {max_retries} attempts")
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise MCPClientError(f"Timeout after {max_retries} attempts")
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
            if e.response.status_code == 401:
                # Authentication error - don't retry
                raise MCPClientError("Authentication failed - check credentials")
            elif e.response.status_code >= 500:
                # Server error - retry
                if attempt == max_retries - 1:
                    raise MCPClientError(f"Server error after {max_retries} attempts")
            else:
                # Client error - don't retry
                raise MCPClientError(f"Client error: {e.response.status_code}")
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise MCPClientError(f"Unexpected error after {max_retries} attempts: {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            import time
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    return []

# Usage with error handling
def main():
    try:
        tasks = robust_task_query(limit=5, max_retries=3)
        print(f"Retrieved {len(tasks)} tasks")
    except MCPClientError as e:
        print(f"MCP Client Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Graceful Degradation

```python
def query_tasks_with_fallback(limit=10):
    """Query tasks with graceful degradation to cached data"""
    from utils.cache_manager import get_session_cache
    
    cache = get_session_cache()
    client = get_default_client()
    
    # Try live query first
    try:
        tasks = client.query_pending_tasks(limit=limit)
        if tasks:
            # Cache successful result
            cache.cache_pending_tasks(tasks)
            print(f"✅ Retrieved {len(tasks)} live tasks")
            return tasks
    except Exception as e:
        print(f"⚠️ Live query failed: {e}")
    
    # Fall back to cache
    cached_tasks = cache.get_pending_tasks()
    if cached_tasks:
        print(f"📦 Using {len(cached_tasks)} cached tasks")
        return cached_tasks
    
    # Final fallback
    print("📭 No tasks available (live or cached)")
    return []

# Usage
tasks = query_tasks_with_fallback()
```

---

## Cache Management

### Working with Session Cache

```python
from utils.cache_manager import get_session_cache
from datetime import datetime

def cache_management_example():
    """Comprehensive cache management example"""
    cache = get_session_cache()
    
    # Cache pending tasks
    tasks = [
        {"id": "1", "title": "Task 1", "status": "todo"},
        {"id": "2", "title": "Task 2", "status": "in_progress"}
    ]
    
    print("💾 Caching tasks...")
    if cache.cache_pending_tasks(tasks):
        print("✅ Tasks cached successfully")
    
    # Retrieve cached tasks
    cached_tasks = cache.get_pending_tasks()
    if cached_tasks:
        print(f"📦 Retrieved {len(cached_tasks)} cached tasks")
    
    # Cache git status
    git_data = {
        "branch": "feature/auth",
        "uncommitted_changes": 3,
        "recent_commits": ["abc123 Add login", "def456 Fix bug"]
    }
    
    cache.cache_git_status(git_data)
    
    # Cache project context
    branch_id = "550e8400-e29b-41d4-a716-446655440000"
    context = {
        "project_name": "MCP Client",
        "active_features": ["authentication", "caching"],
        "last_updated": datetime.now().isoformat()
    }
    
    cache.cache_project_context(branch_id, context)
    
    # Get cache statistics
    stats = cache.get_cache_stats()
    print("\n📊 Cache Statistics:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_bytes']} bytes")
    print(f"   Valid files: {stats['valid_files']}")
    print(f"   Expired files: {stats['expired_files']}")
    
    # Cleanup expired entries
    deleted_count = cache.cleanup_expired()
    print(f"🧹 Cleaned up {deleted_count} expired entries")

# Run example
cache_management_example()
```

### Custom Cache Keys

```python
from utils.cache_manager import get_session_cache

def custom_caching_example():
    """Example of custom cache key usage"""
    cache = get_session_cache()
    
    # Custom cache keys for different data types
    user_tasks_key = f"user_tasks_{user_id}"
    project_metrics_key = f"project_metrics_{project_id}"
    agent_status_key = f"agent_status_{agent_id}"
    
    # Cache user-specific data
    user_data = {"tasks": 5, "completed": 3, "pending": 2}
    cache.set(user_tasks_key, user_data, ttl=1800)  # 30 minutes
    
    # Cache project metrics
    project_metrics = {
        "total_tasks": 50,
        "completion_rate": 0.85,
        "avg_completion_time": "2.5 days"
    }
    cache.set(project_metrics_key, project_metrics, ttl=3600)  # 1 hour
    
    # Retrieve cached data
    cached_user_data = cache.get(user_tasks_key)
    if cached_user_data:
        print(f"User has {cached_user_data['pending']} pending tasks")
    
    cached_metrics = cache.get(project_metrics_key)
    if cached_metrics:
        print(f"Project completion rate: {cached_metrics['completion_rate']*100}%")

# Usage
user_id = "user123"
project_id = "proj456"
agent_id = "agent789"
custom_caching_example()
```

---

## Performance Optimization

### Connection Pool Management

```python
from utils.mcp_client import OptimizedMCPClient
import time
import threading

def performance_test():
    """Test connection pool performance with concurrent requests"""
    client = OptimizedMCPClient()
    
    def make_request(request_id):
        """Make a single request"""
        start_time = time.time()
        
        try:
            tasks = client.query_pending_tasks(limit=5)
            end_time = time.time()
            
            if tasks:
                print(f"Request {request_id}: {len(tasks)} tasks in {end_time - start_time:.2f}s")
                return True
            else:
                print(f"Request {request_id}: No tasks in {end_time - start_time:.2f}s")
                return False
                
        except Exception as e:
            end_time = time.time()
            print(f"Request {request_id}: Error in {end_time - start_time:.2f}s - {e}")
            return False
    
    # Test concurrent requests
    print("🚀 Testing connection pool with concurrent requests...")
    threads = []
    results = []
    
    start_time = time.time()
    
    # Create 10 concurrent requests
    for i in range(10):
        thread = threading.Thread(
            target=lambda i=i: results.append(make_request(i))
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    successful = sum(results)
    
    print(f"\n📊 Performance Results:")
    print(f"   Total time: {end_time - start_time:.2f}s")
    print(f"   Successful requests: {successful}/10")
    print(f"   Average time per request: {(end_time - start_time)/10:.2f}s")

# Run performance test
# performance_test()
```

### Rate Limiting Management

```python
from utils.mcp_client import RateLimiter, get_default_client
import time

def rate_limiting_example():
    """Example of rate limiting in action"""
    client = get_default_client()
    
    # Custom rate limiter for demo
    rate_limiter = RateLimiter(max_requests=5, time_window=10)  # 5 requests per 10 seconds
    
    print("🎛️ Testing rate limiting (5 requests per 10 seconds)...")
    
    for i in range(8):  # Try 8 requests
        if rate_limiter.allow_request():
            print(f"✅ Request {i+1}: Allowed")
            
            # Simulate work
            tasks = client.query_pending_tasks(limit=1)
            time.sleep(0.5)
            
        else:
            print(f"🛑 Request {i+1}: Rate limited - waiting...")
            
            # Wait for rate limit window
            time.sleep(2)
            
            # Retry
            if rate_limiter.allow_request():
                print(f"✅ Request {i+1}: Allowed after wait")
                tasks = client.query_pending_tasks(limit=1)
            else:
                print(f"❌ Request {i+1}: Still rate limited")

# Run rate limiting example
# rate_limiting_example()
```

---

## Integration Patterns

### Session Hook Integration

```python
# .claude/hooks/session_start.py integration
from utils.mcp_client import get_default_client
from utils.cache_manager import get_session_cache

def inject_mcp_context():
    """Inject MCP context into Claude session"""
    client = get_default_client()
    cache = get_session_cache()
    
    context_parts = []
    
    # Get pending tasks
    tasks = client.query_pending_tasks(limit=5)
    if tasks:
        context_parts.append("📋 **Pending Tasks:**")
        for task in tasks[:3]:
            title = task.get('title', 'Unknown')
            priority = task.get('priority', 'medium')
            status = task.get('status', 'todo')
            
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚫')
            status_emoji = {'todo': '⚪', 'in_progress': '🔵', 'done': '✅'}.get(status, '⚫')
            
            context_parts.append(f"  {priority_emoji} {status_emoji} {title}")
    
    # Get git status from cache
    git_data = cache.get_git_status()
    if git_data:
        branch = git_data.get('branch', 'unknown')
        changes = git_data.get('uncommitted_changes', 0)
        
        context_parts.append(f"\n🌿 **Git Status:**")
        context_parts.append(f"  Branch: {branch}")
        if changes > 0:
            context_parts.append(f"  Uncommitted changes: {changes}")
    
    return "\n".join(context_parts)

# Usage in session hook
context = inject_mcp_context()
print(context)
```

### Background Task Monitor

```python
import threading
import time
from utils.mcp_client import get_default_client
from utils.cache_manager import get_session_cache

class TaskMonitor:
    """Background task monitoring service"""
    
    def __init__(self, check_interval=300):  # 5 minutes
        self.client = get_default_client()
        self.cache = get_session_cache()
        self.check_interval = check_interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Start background monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print("🔄 Task monitor started")
    
    def stop(self):
        """Stop background monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("⏹️ Task monitor stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Update task cache
                tasks = self.client.query_pending_tasks(limit=10)
                if tasks:
                    self.cache.cache_pending_tasks(tasks)
                    print(f"📦 Cached {len(tasks)} tasks")
                
                # Check for high priority tasks
                high_priority = [t for t in tasks if t.get('priority') == 'high']
                if high_priority:
                    print(f"⚠️ {len(high_priority)} high priority tasks detected!")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(60)  # Wait 1 minute on error

# Usage
monitor = TaskMonitor(check_interval=180)  # Check every 3 minutes
monitor.start()

# Let it run...
# time.sleep(600)  # Run for 10 minutes

# monitor.stop()
```

---

## Testing Examples

### Unit Testing Setup

```python
import unittest
from unittest.mock import Mock, patch
from utils.mcp_client import MCPHTTPClient, TokenManager

class TestMCPClient(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = MCPHTTPClient()
        self.mock_response = Mock()
    
    @patch('requests.Session.post')
    def test_successful_authentication(self, mock_post):
        """Test successful authentication flow"""
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token-123",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_post.return_value = mock_response
        
        # Test authentication
        self.assertTrue(self.client.authenticate())
        self.assertIn("Authorization", self.client.session.headers)
        self.assertEqual(
            self.client.session.headers["Authorization"],
            "Bearer test-token-123"
        )
    
    @patch('requests.Session.post')
    def test_failed_authentication(self, mock_post):
        """Test failed authentication handling"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials"
        }
        mock_post.return_value = mock_response
        
        # Test authentication failure
        self.assertFalse(self.client.authenticate())
    
    @patch('requests.Session.post')
    def test_query_pending_tasks(self, mock_post):
        """Test querying pending tasks"""
        # Mock authentication
        with patch.object(self.client, 'authenticate', return_value=True):
            # Mock successful task query
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "tasks": [
                        {"id": "1", "title": "Task 1", "status": "todo"},
                        {"id": "2", "title": "Task 2", "status": "in_progress"}
                    ]
                }
            }
            mock_post.return_value = mock_response
            
            # Test task query
            tasks = self.client.query_pending_tasks(limit=5)
            
            self.assertIsNotNone(tasks)
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0]["title"], "Task 1")

class TestTokenManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.token_manager = TokenManager()
    
    def test_should_refresh_no_token(self):
        """Test refresh logic with no token"""
        self.assertTrue(self.token_manager._should_refresh())
    
    def test_should_refresh_expired_token(self):
        """Test refresh logic with expired token"""
        from datetime import datetime, timedelta
        
        # Set expired token
        self.token_manager.token = "expired-token"
        self.token_manager.token_expiry = datetime.now() - timedelta(seconds=10)
        
        self.assertTrue(self.token_manager._should_refresh())

# Run tests
if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
import pytest
from utils.mcp_client import get_default_client
from utils.cache_manager import get_session_cache

class TestMCPIntegration:
    """Integration tests for MCP client"""
    
    @pytest.fixture
    def client(self):
        """Get test client"""
        return get_default_client()
    
    @pytest.fixture
    def cache(self):
        """Get test cache"""
        return get_session_cache()
    
    def test_end_to_end_task_flow(self, client, cache):
        """Test complete task query and cache flow"""
        # Clear cache
        cache.clear_all()
        
        # Query tasks
        tasks = client.query_pending_tasks(limit=5)
        
        # Verify response
        if tasks:  # Only test if server is available
            assert isinstance(tasks, list)
            assert len(tasks) <= 5
            
            # Verify task structure
            for task in tasks:
                assert "id" in task
                assert "title" in task
                assert "status" in task
            
            # Test cache integration
            cache.cache_pending_tasks(tasks)
            cached_tasks = cache.get_pending_tasks()
            
            assert cached_tasks is not None
            assert len(cached_tasks) == len(tasks)
    
    def test_resilient_client_fallback(self, client, cache):
        """Test fallback behavior when server unavailable"""
        # Cache some test data
        test_tasks = [
            {"id": "test1", "title": "Test Task", "status": "todo"}
        ]
        cache.cache_pending_tasks(test_tasks)
        
        # Query with potential fallback
        tasks = client.query_pending_tasks(limit=5)
        
        # Should get either live data or cached data
        assert tasks is not None or cache.get_pending_tasks() is not None
    
    @pytest.mark.asyncio
    async def test_service_account_auth(self):
        """Test service account authentication"""
        from dhafnck_mcp_main.src.fastmcp.auth.service_account import ServiceAccountAuth
        
        auth = ServiceAccountAuth()
        
        try:
            # Test authentication
            token = await auth.authenticate()
            
            if token:  # Only test if credentials are available
                assert token.access_token is not None
                assert not token.is_expired
                
                # Test token validation
                payload = await auth.validate_token(token.access_token)
                assert payload is not None
                assert "sub" in payload
                
        finally:
            await auth.close()

# Run with pytest
# pytest test_integration.py -v
```

### Mock Server for Testing

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time

class MockMCPServer(BaseHTTPRequestHandler):
    """Mock MCP server for testing"""
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(post_data.decode('utf-8'))
            action = request_data.get('action')
            
            if action == 'list':
                # Return mock tasks
                response = {
                    "success": True,
                    "data": {
                        "tasks": [
                            {
                                "id": "mock-task-1",
                                "title": "Mock Task 1",
                                "status": "todo",
                                "priority": "high"
                            },
                            {
                                "id": "mock-task-2", 
                                "title": "Mock Task 2",
                                "status": "in_progress",
                                "priority": "medium"
                            }
                        ]
                    }
                }
            else:
                response = {"success": False, "message": "Unknown action"}
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_mock_server(port=8001):
    """Start mock server in background thread"""
    server = HTTPServer(('localhost', port), MockMCPServer)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    print(f"🎭 Mock MCP server started on port {port}")
    return server

# Usage in tests
def test_with_mock_server():
    """Test client with mock server"""
    import os
    
    # Start mock server
    mock_server = start_mock_server(port=8001)
    
    # Configure client to use mock server
    os.environ['MCP_SERVER_URL'] = 'http://localhost:8001'
    
    # Test client
    from utils.mcp_client import MCPHTTPClient
    client = MCPHTTPClient()
    
    # Mock authentication (skip actual Keycloak)
    client.session.headers.update({"Authorization": "Bearer mock-token"})
    
    # Test request
    tasks = client.query_pending_tasks()
    
    assert tasks is not None
    assert len(tasks) == 2
    assert tasks[0]['title'] == 'Mock Task 1'
    
    print("✅ Mock server test passed")
    
    # Cleanup
    mock_server.shutdown()

# Run mock server test
# test_with_mock_server()
```

This comprehensive usage guide provides practical examples for every aspect of the MCP HTTP Client Module, from basic setup to advanced integration patterns and testing strategies.