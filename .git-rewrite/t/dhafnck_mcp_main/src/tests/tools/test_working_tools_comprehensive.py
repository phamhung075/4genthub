#!/usr/bin/env python3
"""
Comprehensive test suite to verify which tools are working correctly
"""

import sys
import os
import asyncio
import httpx
import uvicorn
import json
from contextlib import asynccontextmanager
from pathlib import Path
import traceback
from typing import Dict, Any, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastmcp.server.server import FastMCP


class ToolTester:
    def __init__(self, base_url: str, session_id: str, client: httpx.AsyncClient):
        self.base_url = base_url
        self.session_id = session_id
        self.client = client
        self.results = {}
        
    def test_tool(self, tool_name: str, test_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """Test a single tool call and return success status and details"""
        try:
            response = self.client.post(
                self.base_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": self.session_id
                },
                timeout=15.0
            )
            
            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text}"
            
            if not response.text.strip():
                return False, "Empty response"
            
            try:
                data = response.json()
                if 'error' in data:
                    error_msg = data['error'].get('message', str(data['error']))
                    return False, f"Tool error: {error_msg}"
                elif 'result' in data:
                    return True, f"Success: {str(data['result'])[:200]}..."
                else:
                    return False, f"Unexpected response format: {str(data)[:200]}..."
            except json.JSONDecodeError as e:
                return False, f"JSON decode error: {e}"
                
        except asyncio.TimeoutError:
            return False, "Request timeout"
        except Exception as e:
            return False, f"Exception: {str(e)}"
    
    async def run_test_suite(self):
        """Run comprehensive test suite"""
        print("🧪 Running comprehensive tool test suite...")
        
        # Test basic task management operations
        await self.test_task_management()
        
        # Test subtask management
        await self.test_subtask_management()
        
        # Test context management
        await self.test_context_management()
        
        # Test project management
        await self.test_project_management()
        
        # Test agent management
        await self.test_agent_management()
        
        # Test connection management
        await self.test_connection_management()
        
        # Test compliance management
        await self.test_compliance_management()
        
        # Print summary
        self.print_summary()
    
    def test_task_management(self):
        """Test manage_task tool with various actions"""
        print("\n=== Testing Task Management ===")
        
        tests = [
            # Basic operations that should work
            ("list_tasks", {"action": "list"}),
            ("next_task", {"action": "next"}),
            ("search_tasks", {"action": "search", "query": "test"}),
            
            # Create task (should work)
            ("create_task", {
                "action": "create",
                "title": "Test Task",
                "description": "Test task description",
                "priority": "medium",
                "status": "todo"
            }),
            
            # Operations that might have missing fields
            ("add_dependency_missing_task_id", {
                "action": "add_dependency",
                "query": "some-dependency-id"
            }),
            
            ("remove_dependency_missing_task_id", {
                "action": "remove_dependency", 
                "query": "some-dependency-id"
            }),
            
            # Update with missing task_id
            ("update_missing_task_id", {
                "action": "update",
                "title": "Updated title"
            }),
            
            # Get with missing task_id
            ("get_missing_task_id", {
                "action": "get"
            }),
            
            # Delete with missing task_id
            ("delete_missing_task_id", {
                "action": "delete"
            }),
            
            # Complete with missing task_id
            ("complete_missing_task_id", {
                "action": "complete"
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_task", test_name, args)
            self.results[f"manage_task_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_subtask_management(self):
        """Test manage_subtask tool"""
        print("\n=== Testing Subtask Management ===")
        
        tests = [
            # List subtasks (should work if parent task exists)
            ("list_subtasks", {
                "action": "list",
                "task_id": "test-task-id",
                "git_branch_id": "main",
                "user_id": "test-user"
            }),
            
            # Create subtask
            ("create_subtask", {
                "action": "create",
                "task_id": "test-task-id",
                "git_branch_id": "main", 
                "user_id": "test-user",
                "subtask_data": {
                    "title": "Test Subtask",
                    "description": "Test subtask description",
                    "status": "todo"
                }
            }),
            
            # Delete subtask (might be missing method)
            ("delete_subtask", {
                "action": "delete",
                "task_id": "test-task-id",
                "git_branch_id": "main",
                "user_id": "test-user",
                "subtask_data": {"subtask_id": "test-subtask-id"}
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_subtask", test_name, args)
            self.results[f"manage_subtask_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_context_management(self):
        """Test manage_context tool"""
        print("\n=== Testing Context Management ===")
        
        tests = [
            # List contexts
            ("list_contexts", {
                "action": "list",
                "user_id": "test-user"
            }),
            
            # Create context
            ("create_context", {
                "action": "create",
                "task_id": "test-task-id",
                "user_id": "test-user",
                "data": {"test": "context"}
            }),
            
            # Get context
            ("get_context", {
                "action": "get",
                "task_id": "test-task-id",
                "user_id": "test-user"
            }),
            
            # Update property (might have type restrictions)
            ("update_property", {
                "action": "update_property",
                "task_id": "test-task-id",
                "user_id": "test-user",
                "property_path": "test_property",
                "value": "test_value"
            }),
            
            # Delete context (might fail)
            ("delete_context", {
                "action": "delete",
                "task_id": "test-task-id",
                "user_id": "test-user"
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_context", test_name, args)
            self.results[f"manage_context_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_project_management(self):
        """Test manage_project tool"""
        print("\n=== Testing Project Management ===")
        
        tests = [
            # List projects
            ("list_projects", {
                "action": "list"
            }),
            
            # Create project
            ("create_project", {
                "action": "create",
                "project_id": "test-project-123",
                "name": "Test Project",
                "description": "Test project description"
            }),
            
            # Get project
            ("get_project", {
                "action": "get",
                "project_id": "test-project-123"
            }),
            
            # Health check
            ("health_check", {
                "action": "project_health_check",
                "project_id": "test-project-123"
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_project", test_name, args)
            self.results[f"manage_project_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_agent_management(self):
        """Test manage_agent tool"""
        print("\n=== Testing Agent Management ===")
        
        tests = [
            # List agents
            ("list_agents", {
                "action": "list",
                "project_id": "test-project"
            }),
            
            # Register agent
            ("register_agent", {
                "action": "register",
                "project_id": "test-project",
                "agent_id": "test-agent",
                "name": "Test Agent"
            }),
            
            # Unassign agent (might be missing method)
            ("unassign_agent", {
                "action": "unassign",
                "project_id": "test-project",
                "agent_id": "test-agent",
                "git_branch_id": "main"
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_agent", test_name, args)
            self.results[f"manage_agent_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_connection_management(self):
        """Test manage_connection tool"""
        print("\n=== Testing Connection Management ===")
        
        tests = [
            # Health check
            ("health_check", {
                "action": "health_check"
            }),
            
            # Server capabilities
            ("server_capabilities", {
                "action": "server_capabilities"
            }),
            
            # Connection health
            ("connection_health", {
                "action": "connection_health"
            }),
            
            # Status
            ("status", {
                "action": "status"
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_connection", test_name, args)
            self.results[f"manage_connection_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def test_compliance_management(self):
        """Test manage_compliance tool"""
        print("\n=== Testing Compliance Management ===")
        
        tests = [
            # Validate compliance
            ("validate_compliance", {
                "action": "validate_compliance",
                "operation": "create_file",
                "file_path": "/tmp/test.txt"
            }),
            
            # Get compliance dashboard
            ("compliance_dashboard", {
                "action": "get_compliance_dashboard"
            }),
            
            # Get audit trail
            ("audit_trail", {
                "action": "get_audit_trail",
                "limit": 10
            })
        ]
        
        for test_name, args in tests:
            success, details = self.test_tool("manage_compliance", test_name, args)
            self.results[f"manage_compliance_{test_name}"] = (success, details)
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {details[:100]}...")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        working_tools = []
        broken_tools = []
        
        for test_name, (success, details) in self.results.items():
            if success:
                working_tools.append(test_name)
            else:
                broken_tools.append((test_name, details))
        
        print(f"\n✅ WORKING TOOLS ({len(working_tools)}):")
        for tool in working_tools:
            print(f"  • {tool}")
        
        print(f"\n❌ BROKEN TOOLS ({len(broken_tools)}):")
        for tool, error in broken_tools:
            print(f"  • {tool}: {error[:100]}...")
        
        print(f"\n📈 SUCCESS RATE: {len(working_tools)}/{len(self.results)} ({len(working_tools)/len(self.results)*100:.1f}%)")
        
        # Group by tool type
        print("\n🔧 BY TOOL TYPE:")
        tool_types = {}
        for test_name, (success, _) in self.results.items():
            tool_type = test_name.split('_')[1]  # Extract tool type
            if tool_type not in tool_types:
                tool_types[tool_type] = {'working': 0, 'broken': 0}
            if success:
                tool_types[tool_type]['working'] += 1
            else:
                tool_types[tool_type]['broken'] += 1
        
        for tool_type, stats in tool_types.items():
            total = stats['working'] + stats['broken']
            rate = stats['working'] / total * 100
            print(f"  • {tool_type}: {stats['working']}/{total} ({rate:.1f}%)")


async def main():
    """Main test runner"""
    print("🚀 Creating FastMCP server...")
    server = FastMCP(
        name="comprehensive_test_server",
        enable_task_management=True
    )
    
    app = server.http_app(path="/mcp", transport="streamable-http")
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1", 
        port=8899,
        log_level="error"
    )
    server_instance = uvicorn.Server(config)
    
    @asynccontextmanager
    async def run_server():
        server_task = asyncio.create_task(server_instance.serve())
        await asyncio.sleep(2)  # Give server time to start
        
        try:
            yield
        finally:
            server_instance.should_exit = True
            try:
                await asyncio.wait_for(server_task, timeout=3.0)
            except asyncio.TimeoutError:
                pass
    
    async with run_server():
        async with httpx.AsyncClient() as client:
            # Initialize session
            print("🔧 Initializing session...")
            try:
                init_response = await client.post(
                    "http://127.0.0.1:8899/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                            "clientInfo": {"name": "comprehensive-test-client", "version": "1.0.0"}
                        }
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    },
                    timeout=15.0
                )
                
                if init_response.status_code != 200:
                    print(f"❌ Init failed: {init_response.status_code}")
                    print(f"Response: {init_response.text}")
                    return
                
                session_id = init_response.headers.get('mcp-session-id')
                print(f"✅ Session initialized: {session_id}")
                
                # Run comprehensive tests
                tester = ToolTester("http://127.0.0.1:8899/mcp", session_id, client)
                await tester.run_test_suite()
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 