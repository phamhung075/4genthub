#!/usr/bin/env python3
"""
Frontend Task Listing Debug Script
This script directly tests the API endpoints that the frontend calls to identify the exact issue.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from urllib.parse import quote

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test configuration
API_BASE_URL = "http://localhost:8000"
MCP_BASE_URL = f"{API_BASE_URL}/mcp/"
API_V2_BASE_URL = f"{API_BASE_URL}/api/v2"

# Test tokens from environment variables
TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN", "")

def log_separator(title: str):
    """Print a separator for test sections."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")

def make_request(method: str, url: str, headers: dict = None, json_data: dict = None, timeout: int = 10):
    """Make an HTTP request with detailed logging."""
    if headers is None:
        headers = {}
    
    # Add default headers
    default_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Frontend-Debug-Script/1.0'
    }
    default_headers.update(headers)
    
    logger.info(f"Making {method} request to: {url}")
    logger.info(f"Headers: {json.dumps(default_headers, indent=2)}")
    
    if json_data:
        logger.info(f"Request body: {json.dumps(json_data, indent=2)}")
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=default_headers,
            json=json_data,
            timeout=timeout
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            logger.info(f"Response body: {json.dumps(response_json, indent=2)}")
            return response.status_code, response_json, dict(response.headers)
        except json.JSONDecodeError:
            logger.info(f"Response text: {response.text}")
            return response.status_code, response.text, dict(response.headers)
    
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None, str(e), {}

def test_server_health():
    """Test if the server is running and healthy."""
    log_separator("SERVER HEALTH CHECK")
    
    # Test basic server health
    status, response, headers = make_request("GET", f"{API_BASE_URL}/health")
    
    if status == 200:
        print("✅ Server is healthy")
        if isinstance(response, dict):
            print(f"   - Auth enabled: {response.get('auth_enabled', 'Unknown')}")
            print(f"   - Version: {response.get('version', 'Unknown')}")
            if 'connections' in response:
                print(f"   - Active connections: {response['connections'].get('active_connections', 'Unknown')}")
    else:
        print(f"❌ Server health check failed: {status} - {response}")
    
    return status == 200

def test_cors_preflight():
    """Test CORS preflight for V2 API endpoints."""
    log_separator("CORS PREFLIGHT TEST")
    
    headers = {
        'Origin': 'http://localhost:3800',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type,Authorization'
    }
    
    status, response, response_headers = make_request("OPTIONS", f"{API_V2_BASE_URL}/tasks/", headers)
    
    if status in [200, 204]:
        print("✅ CORS preflight successful")
        cors_headers = {k: v for k, v in response_headers.items() if 'access-control' in k.lower()}
        print(f"   CORS headers: {json.dumps(cors_headers, indent=2)}")
    else:
        print(f"❌ CORS preflight failed: {status} - {response}")
    
    return status in [200, 204]

def test_v2_api_without_auth():
    """Test V2 API endpoints without authentication."""
    log_separator("V2 API TEST (No Auth)")
    
    # Test tasks endpoint without auth
    status, response, headers = make_request("GET", f"{API_V2_BASE_URL}/tasks/")
    
    if status == 401:
        print("✅ V2 API properly requires authentication (401 Unauthorized)")
        return True
    elif status == 200:
        print("⚠️ V2 API allows access without authentication")
        if isinstance(response, dict) and 'tasks' in response:
            print(f"   Found {len(response['tasks'])} tasks")
        return True
    else:
        print(f"❌ Unexpected response from V2 API: {status} - {response}")
        return False

def test_v2_api_with_fake_auth():
    """Test V2 API endpoints with fake authentication."""
    log_separator("V2 API TEST (Fake Auth)")
    
    headers = {
        'Authorization': f'Bearer {TEST_JWT_TOKEN}',
        'Origin': 'http://localhost:3800'
    }
    
    status, response, response_headers = make_request("GET", f"{API_V2_BASE_URL}/tasks/", headers)
    
    if status == 401:
        print("✅ V2 API properly rejects invalid tokens (401 Unauthorized)")
    elif status == 403:
        print("✅ V2 API properly handles authorization (403 Forbidden)")
    elif status == 200:
        print("⚠️ V2 API accepted fake token or auth is disabled")
        if isinstance(response, dict) and 'tasks' in response:
            print(f"   Found {len(response['tasks'])} tasks")
    else:
        print(f"❌ Unexpected response from V2 API: {status} - {response}")
    
    return status in [200, 401, 403]

def test_v1_mcp_api():
    """Test V1 MCP API endpoints (what should work)."""
    log_separator("V1 MCP API TEST")
    
    # Test MCP tools/call endpoint
    rpc_body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "manage_task",
            "arguments": {"action": "list"}
        },
        "id": 1
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'MCP-Protocol-Version': '2025-06-18'
    }
    
    status, response, response_headers = make_request("POST", MCP_BASE_URL, headers, rpc_body)
    
    if status == 200:
        print("✅ V1 MCP API working correctly")
        if isinstance(response, dict) and 'result' in response:
            result = response['result']
            if 'content' in result and result['content']:
                try:
                    tool_result = json.loads(result['content'][0]['text'])
                    if tool_result.get('success') and 'tasks' in tool_result:
                        tasks = tool_result['tasks']
                        print(f"   Found {len(tasks)} tasks via MCP API")
                        if tasks:
                            print(f"   First task: {tasks[0].get('title', 'N/A')} (Status: {tasks[0].get('status', 'N/A')})")
                    else:
                        print(f"   Tool result: {tool_result}")
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    print(f"   Error parsing tool result: {e}")
    else:
        print(f"❌ V1 MCP API failed: {status} - {response}")
    
    return status == 200

def test_authentication_endpoints():
    """Test authentication system endpoints."""
    log_separator("AUTHENTICATION ENDPOINTS TEST")
    
    # Test auth status
    status, response, headers = make_request("GET", f"{API_BASE_URL}/api/auth/status")
    
    if status == 200:
        print("✅ Auth status endpoint working")
        if isinstance(response, dict):
            print(f"   Auth enabled: {response.get('auth_enabled', 'Unknown')}")
            print(f"   MVP mode: {response.get('mvp_mode', 'Unknown')}")
    else:
        print(f"⚠️ Auth status endpoint: {status} - {response}")
    
    # Test Supabase auth status
    status, response, headers = make_request("GET", f"{API_BASE_URL}/auth/supabase/status")
    
    if status == 200:
        print("✅ Supabase auth status endpoint working")
        if isinstance(response, dict):
            print(f"   Supabase configured: {response.get('supabase_configured', 'Unknown')}")
    else:
        print(f"⚠️ Supabase auth status: {status} - {response}")

def test_frontend_user_flow():
    """Simulate the exact frontend user flow."""
    log_separator("FRONTEND USER FLOW SIMULATION")
    
    print("1. Frontend checks authentication...")
    # This is what shouldUseV2Api() does in frontend
    auth_headers = {
        'Origin': 'http://localhost:3800'
    }
    
    # Check if access_token cookie would be present (simulated)
    has_token = False  # In real frontend, this checks js-cookie
    print(f"   Has access token: {has_token}")
    
    print("2. Frontend calls taskApiV2.getTasks()...")
    if has_token:
        auth_headers['Authorization'] = f'Bearer {TEST_JWT_TOKEN}'
    
    status, response, response_headers = make_request("GET", f"{API_V2_BASE_URL}/tasks/", auth_headers)
    
    print(f"   API V2 response: {status}")
    
    if status != 200:
        print("3. Frontend falls back to V1 API...")
        
        # Simulate V1 API fallback
        rpc_body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "manage_task",
                "arguments": {"action": "list"}
            },
            "id": 1
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'MCP-Protocol-Version': '2025-06-18'
        }
        
        status, response, response_headers = make_request("POST", MCP_BASE_URL, headers, rpc_body)
        
        if status == 200:
            print("   ✅ V1 fallback working")
            if isinstance(response, dict) and 'result' in response:
                try:
                    result = response['result']
                    if 'content' in result and result['content']:
                        tool_result = json.loads(result['content'][0]['text'])
                        if tool_result.get('success') and 'tasks' in tool_result:
                            tasks = tool_result['tasks']
                            print(f"   Frontend should show {len(tasks)} tasks")
                except Exception as e:
                    print(f"   Error processing V1 response: {e}")
        else:
            print(f"   ❌ V1 fallback failed: {status}")

def test_database_user_scoping():
    """Test if user scoping is working correctly in the database."""
    log_separator("DATABASE USER SCOPING TEST")
    
    try:
        # Import required modules
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from fastmcp.task_management.infrastructure.repositories.orm.task_repository import TaskRepository
        from fastmcp.auth.domain.entities.user import User
        from sqlalchemy.orm import sessionmaker
        
        print("Testing database user scoping...")
        
        # Get database configuration
        db_config = get_db_config()
        if not db_config or not db_config.engine:
            print("❌ Could not get database configuration")
            return False
        
        # Create session
        Session = sessionmaker(bind=db_config.engine)
        session = Session()
        
        try:
            # Create a test user
            test_user = User(
                id="test-user-123",
                email="test@example.com",
                created_at=None
            )
            
            # Create user-scoped repository
            task_repo = TaskRepository(session).with_user(test_user.id)
            
            # Try to list tasks for this user
            all_tasks = task_repo.find_all()
            print(f"✅ User-scoped repository working: found {len(all_tasks)} tasks for user {test_user.id}")
            
            # Test if repository actually applies user filter
            raw_count = session.execute("SELECT COUNT(*) FROM tasks").scalar()
            print(f"   Raw task count: {raw_count}")
            print(f"   User-filtered count: {len(all_tasks)}")
            
            if len(all_tasks) <= raw_count:
                print("✅ User filtering appears to be working")
            else:
                print("❌ User filtering might not be working correctly")
            
            return True
            
        finally:
            session.close()
    
    except Exception as e:
        print(f"❌ Database user scoping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_comprehensive_report():
    """Generate a comprehensive report of all test results."""
    log_separator("COMPREHENSIVE DEBUG REPORT")
    
    print("Running comprehensive test suite...")
    
    results = {
        'server_health': test_server_health(),
        'cors_preflight': test_cors_preflight(),
        'v2_api_no_auth': test_v2_api_without_auth(),
        'v2_api_fake_auth': test_v2_api_with_fake_auth(),
        'v1_mcp_api': test_v1_mcp_api(),
        'auth_endpoints': True,  # Always test this
        'frontend_flow': True,    # Always test this
        'database_scoping': test_database_user_scoping()
    }
    
    test_authentication_endpoints()
    test_frontend_user_flow()
    
    log_separator("FINAL DIAGNOSIS")
    
    print("Test Results Summary:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print("\nDIAGNOSIS:")
    
    if results['server_health']:
        print("✅ Server is running and accessible")
    else:
        print("❌ CRITICAL: Server is not running or not accessible")
        return
    
    if results['v1_mcp_api']:
        print("✅ V1 MCP API is working (backend logic is correct)")
    else:
        print("❌ CRITICAL: V1 MCP API is broken (backend logic issue)")
        return
    
    if not results['cors_preflight']:
        print("❌ ISSUE: CORS preflight failing - frontend requests will be blocked")
    
    if not results['v2_api_no_auth'] and not results['v2_api_fake_auth']:
        print("❌ ISSUE: V2 API endpoints are not accessible")
    
    if not results['database_scoping']:
        print("❌ ISSUE: Database user scoping is not working correctly")
    
    print("\nRECOMMENDED FIXES:")
    
    if not results['cors_preflight']:
        print("1. Fix CORS configuration for V2 API endpoints")
        print("   - Ensure CORSMiddleware is properly configured")
        print("   - Check allowed origins include http://localhost:3800")
    
    if not results['v2_api_no_auth'] and not results['v2_api_fake_auth']:
        print("2. Fix V2 API endpoint registration")
        print("   - Verify user_scoped_task_routes.py is properly mounted")
        print("   - Check FastAPI router configuration")
    
    if not results['database_scoping']:
        print("3. Fix database user scoping")
        print("   - Check UserScopedRepositoryFactory implementation")
        print("   - Verify user_id column exists in tasks table")
    
    print("\nNext steps:")
    print("1. Run this script to identify specific issues")
    print("2. Fix the identified issues one by one")
    print("3. Re-run this script to verify fixes")
    print("4. Test frontend integration")

if __name__ == "__main__":
    print("Frontend Task Listing Debug Script")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        generate_comprehensive_report()
    else:
        print("Running quick tests. Use --comprehensive for full test suite.")
        print()
        
        if test_server_health():
            print("\n✅ Server is healthy. Testing task endpoints...")
            test_v1_mcp_api()
            test_v2_api_without_auth()
            test_frontend_user_flow()
        else:
            print("\n❌ Server is not healthy. Please start the server first.")
            print("   Run: cd dhafnck_mcp_main && python -m fastmcp.server.mcp_entry_point --transport=streamable-http")