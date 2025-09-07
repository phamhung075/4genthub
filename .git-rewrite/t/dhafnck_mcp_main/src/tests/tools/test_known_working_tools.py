#!/usr/bin/env python3
"""
Test known working tools more thoroughly
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
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastmcp.server.server import FastMCP


class WorkingToolsTester:
    def __init__(self, base_url: str, session_id: str, client: httpx.AsyncClient):
        self.base_url = base_url
        self.session_id = session_id
        self.client = client
        self.results = {}
        self.created_resources = []  # Track created resources for cleanup
        
    async def call_tool(self, tool_name: str, arguments: dict, timeout: float = 10.0):
        """Make a tool call and return the response"""
        response = await self.client.post(
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
            timeout=timeout
        )
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.text}"
        
        if not response.text.strip():
            return None, "Empty response"
        
        try:
            data = response.json()
            if 'error' in data:
                return None, data['error'].get('message', str(data['error']))
            elif 'result' in data:
                return data['result'], None
            else:
                return None, f"Unexpected format: {str(data)[:200]}..."
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e}"
    
    def test_manage_connection(self):
        """Test manage_connection tool thoroughly"""
        print("\n=== Testing manage_connection (should work) ===")
        
        tests = [
            ("health_check", {"action": "health_check"}),
            ("health_check_detailed", {"action": "health_check", "include_details": True}),
            ("server_capabilities", {"action": "server_capabilities"}),
            ("server_capabilities_detailed", {"action": "server_capabilities", "include_details": True}),
            ("connection_health", {"action": "connection_health"}),
            ("status", {"action": "status"}),
            ("status_detailed", {"action": "status", "include_details": True}),
        ]
        
        for test_name, args in tests:
            result, error = self.call_tool("manage_connection", args)
            success = result is not None
            self.results[f"manage_connection.{test_name}"] = (success, error or "Success")
            status = "✅" if success else "❌"
            print(f"  {status} {test_name}: {error or 'Success'}")
    
    def test_manage_project(self):
        """Test manage_project tool thoroughly"""
        print("\n=== Testing manage_project ===")
        
        # Test list first
        result, error = self.call_tool("manage_project", {"action": "list"})
        success = result is not None
        self.results["manage_project.list"] = (success, error or "Success")
        print(f"  {'✅' if success else '❌'} list: {error or 'Success'}")
        
        if success:
            # Create a test project
            project_id = f"test-project-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            result, error = self.call_tool("manage_project", {
                "action": "create",
                "project_id": project_id,
                "name": "Test Project",
                "description": "Created by test suite"
            })
            success = result is not None
            self.results["manage_project.create"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} create: {error or 'Success'}")
            
            if success:
                self.created_resources.append(("project", project_id))
                
                # Test get project
                result, error = self.call_tool("manage_project", {
                    "action": "get",
                    "project_id": project_id
                })
                success = result is not None
                self.results["manage_project.get"] = (success, error or "Success")
                print(f"  {'✅' if success else '❌'} get: {error or 'Success'}")
                
                # Test update project
                result, error = self.call_tool("manage_project", {
                    "action": "update",
                    "project_id": project_id,
                    "name": "Updated Test Project",
                    "description": "Updated by test suite"
                })
                success = result is not None
                self.results["manage_project.update"] = (success, error or "Success")
                print(f"  {'✅' if success else '❌'} update: {error or 'Success'}")
    
    def test_manage_task(self):
        """Test manage_task tool thoroughly"""
        print("\n=== Testing manage_task ===")
        
        # Test basic operations first
        basic_tests = [
            ("list", {"action": "list"}),
            ("next", {"action": "next"}),
            ("search", {"action": "search", "query": "test"}),
        ]
        
        for test_name, args in basic_tests:
            result, error = self.call_tool("manage_task", args)
            success = result is not None
            self.results[f"manage_task.{test_name}"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} {test_name}: {error or 'Success'}")
        
        # Create a test task
        task_title = f"Test Task {datetime.now().strftime('%Y%m%d%H%M%S')}"
        result, error = self.call_tool("manage_task", {
            "action": "create",
            "title": task_title,
            "description": "Created by test suite",
            "priority": "medium",
            "status": "todo"
        })
        success = result is not None
        self.results["manage_task.create"] = (success, error or "Success")
        print(f"  {'✅' if success else '❌'} create: {error or 'Success'}")
        
        if success and isinstance(result, dict) and 'task_id' in result:
            task_id = result['task_id']
            self.created_resources.append(("task", task_id))
            
            # Test get task
            result, error = self.call_tool("manage_task", {
                "action": "get",
                "task_id": task_id
            })
            success = result is not None
            self.results["manage_task.get"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} get: {error or 'Success'}")
            
            # Test update task
            result, error = self.call_tool("manage_task", {
                "action": "update",
                "task_id": task_id,
                "title": f"Updated {task_title}",
                "status": "in_progress"
            })
            success = result is not None
            self.results["manage_task.update"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} update: {error or 'Success'}")
            
            # Test complete task
            result, error = self.call_tool("manage_task", {
                "action": "complete",
                "task_id": task_id
            })
            success = result is not None
            self.results["manage_task.complete"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} complete: {error or 'Success'}")
    
    def test_manage_context(self):
        """Test manage_context tool thoroughly"""
        print("\n=== Testing manage_context ===")
        
        # Test list first
        result, error = self.call_tool("manage_context", {
            "action": "list",
            "user_id": "test-user"
        })
        success = result is not None
        self.results["manage_context.list"] = (success, error or "Success")
        print(f"  {'✅' if success else '❌'} list: {error or 'Success'}")
        
        # Create a test context
        test_task_id = f"test-task-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result, error = self.call_tool("manage_context", {
            "action": "create",
            "task_id": test_task_id,
            "user_id": "test-user",
            "data": {
                "test_property": "test_value",
                "created_at": datetime.now().isoformat()
            }
        })
        success = result is not None
        self.results["manage_context.create"] = (success, error or "Success")
        print(f"  {'✅' if success else '❌'} create: {error or 'Success'}")
        
        if success:
            self.created_resources.append(("context", test_task_id))
            
            # Test get context
            result, error = self.call_tool("manage_context", {
                "action": "get",
                "task_id": test_task_id,
                "user_id": "test-user"
            })
            success = result is not None
            self.results["manage_context.get"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} get: {error or 'Success'}")
            
            # Test update context
            result, error = self.call_tool("manage_context", {
                "action": "update",
                "task_id": test_task_id,
                "user_id": "test-user",
                "data": {
                    "test_property": "updated_value",
                    "updated_at": datetime.now().isoformat()
                }
            })
            success = result is not None
            self.results["manage_context.update"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} update: {error or 'Success'}")
            
            # Test update_property with simple value
            result, error = self.call_tool("manage_context", {
                "action": "update_property",
                "task_id": test_task_id,
                "user_id": "test-user",
                "property_path": "simple_property",
                "value": "simple_value"
            })
            success = result is not None
            self.results["manage_context.update_property"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} update_property: {error or 'Success'}")
    
    def test_manage_compliance(self):
        """Test manage_compliance tool thoroughly"""
        print("\n=== Testing manage_compliance ===")
        
        tests = [
            ("validate_compliance", {
                "action": "validate_compliance",
                "operation": "create_file",
                "file_path": "/tmp/test.txt",
                "content": "test content"
            }),
            ("compliance_dashboard", {
                "action": "get_compliance_dashboard"
            }),
            ("audit_trail", {
                "action": "get_audit_trail",
                "limit": 10
            }),
        ]
        
        for test_name, args in tests:
            result, error = self.call_tool("manage_compliance", args)
            success = result is not None
            self.results[f"manage_compliance.{test_name}"] = (success, error or "Success")
            print(f"  {'✅' if success else '❌'} {test_name}: {error or 'Success'}")
    
    async def cleanup_resources(self):
        """Clean up created resources"""
        print("\n=== Cleaning up test resources ===")
        
        for resource_type, resource_id in self.created_resources:
            try:
                if resource_type == "context":
                    result, error = await self.call_tool("manage_context", {
                        "action": "delete",
                        "task_id": resource_id,
                        "user_id": "test-user"
                    })
                    print(f"  {'✅' if result else '❌'} Deleted context {resource_id}: {error or 'Success'}")
                elif resource_type == "task":
                    result, error = await self.call_tool("manage_task", {
                        "action": "delete",
                        "task_id": resource_id
                    })
                    print(f"  {'✅' if result else '❌'} Deleted task {resource_id}: {error or 'Success'}")
                # Note: Not deleting projects as they might be needed for other tests
            except Exception as e:
                print(f"  ❌ Failed to delete {resource_type} {resource_id}: {e}")
    
    async def run_tests(self):
        """Run all tests"""
        print("🧪 Running comprehensive tests on known working tools...")
        
        await self.test_manage_connection()
        await self.test_manage_project()
        await self.test_manage_task()
        await self.test_manage_context()
        await self.test_manage_compliance()
        
        await self.cleanup_resources()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("📊 WORKING TOOLS TEST RESULTS")
        print("="*80)
        
        working = []
        broken = []
        
        for test_name, (success, details) in self.results.items():
            if success:
                working.append(test_name)
            else:
                broken.append((test_name, details))
        
        print(f"\n✅ WORKING TESTS ({len(working)}):")
        for test in working:
            print(f"  • {test}")
        
        print(f"\n❌ BROKEN TESTS ({len(broken)}):")
        for test, error in broken:
            print(f"  • {test}: {error[:100]}...")
        
        print(f"\n📈 SUCCESS RATE: {len(working)}/{len(self.results)} ({len(working)/len(self.results)*100:.1f}%)")
        
        # Group by tool
        print("\n🔧 BY TOOL:")
        tool_stats = {}
        for test_name, (success, _) in self.results.items():
            tool = test_name.split('.')[0]
            if tool not in tool_stats:
                tool_stats[tool] = {'working': 0, 'broken': 0}
            if success:
                tool_stats[tool]['working'] += 1
            else:
                tool_stats[tool]['broken'] += 1
        
        for tool, stats in tool_stats.items():
            total = stats['working'] + stats['broken']
            rate = stats['working'] / total * 100
            status = "✅" if rate >= 50 else "❌"
            print(f"  {status} {tool}: {stats['working']}/{total} ({rate:.1f}%)")


async def main():
    """Main test runner"""
    print("🚀 Creating FastMCP server...")
    server = FastMCP(
        name="working_tools_test_server",
        enable_task_management=True
    )
    
    app = server.http_app(path="/mcp", transport="streamable-http")
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1", 
        port=8896,
        log_level="error"
    )
    server_instance = uvicorn.Server(config)
    
    @asynccontextmanager
    async def run_server():
        server_task = asyncio.create_task(server_instance.serve())
        await asyncio.sleep(2)
        
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
                    "http://127.0.0.1:8896/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                            "clientInfo": {"name": "working-tools-test-client", "version": "1.0.0"}
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
                tester = WorkingToolsTester("http://127.0.0.1:8896/mcp", session_id, client)
                await tester.run_tests()
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 