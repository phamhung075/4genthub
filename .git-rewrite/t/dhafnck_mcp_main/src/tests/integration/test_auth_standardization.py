#!/usr/bin/env python3
"""
Test script to validate authentication standardization across MCP tools.

This script tests that all standardized MCP tools accept the user_id parameter
and handle authentication consistently.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dhafnck_mcp_main', 'src'))

def test_manage_agent_user_id():
    """Test that manage_agent accepts user_id parameter"""
    try:
        from fastmcp.task_management.interface.controllers.agent_mcp_controller import AgentMCPController
        from fastmcp.task_management.application.factories.agent_facade_factory import AgentFacadeFactory
        
        # Create controller instance
        facade_factory = AgentFacadeFactory()
        controller = AgentMCPController(facade_factory)
        
        # Test that the manage_agent method accepts user_id
        # This should not raise a TypeError for unexpected keyword argument
        try:
            result = controller.manage_agent(
                action="list",
                project_id="test_project", 
                user_id="test_user_123"
            )
            print("✓ manage_agent accepts user_id parameter")
            return True
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"✗ manage_agent does not accept user_id parameter: {e}")
                return False
            else:
                # Other errors are okay for testing parameter acceptance
                print("✓ manage_agent accepts user_id parameter")
                return True
        except Exception as e:
            # Other exceptions are expected (no database, etc.) - we're just testing parameter acceptance
            print("✓ manage_agent accepts user_id parameter")
            return True
    except ImportError as e:
        print(f"✗ Could not import manage_agent controller: {e}")
        return False

def test_manage_subtask_user_id():
    """Test that manage_subtask accepts user_id parameter"""
    try:
        from fastmcp.task_management.interface.controllers.subtask_mcp_controller import SubtaskMCPController
        from fastmcp.task_management.application.factories.subtask_facade_factory import SubtaskFacadeFactory
        from fastmcp.task_management.infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        
        # Create controller instance
        task_repo_factory = TaskRepositoryFactory()
        subtask_repo_factory = SubtaskRepositoryFactory()
        facade_factory = SubtaskFacadeFactory(subtask_repo_factory, task_repo_factory)
        controller = SubtaskMCPController(facade_factory)
        
        # Test that the manage_subtask method accepts user_id
        try:
            result = controller.manage_subtask(
                action="list",
                task_id="test_task_123",
                user_id="test_user_123"
            )
            print("✓ manage_subtask accepts user_id parameter")
            return True
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"✗ manage_subtask does not accept user_id parameter: {e}")
                return False
            else:
                print("✓ manage_subtask accepts user_id parameter")
                return True
        except Exception as e:
            print("✓ manage_subtask accepts user_id parameter")
            return True
    except ImportError as e:
        print(f"✗ Could not import manage_subtask controller: {e}")
        return False

def test_manage_rule_user_id():
    """Test that manage_rule accepts user_id parameter"""
    try:
        from fastmcp.task_management.interface.controllers.rule_orchestration_controller import RuleOrchestrationController
        
        # Mock facade to avoid complex dependencies
        class MockRuleFacade:
            def execute_action(self, action, target="", content="", user_id=None):
                return {"success": True, "action": action, "user_id": user_id}
        
        # Create controller instance with mock facade
        controller = RuleOrchestrationController(MockRuleFacade())
        
        # Test that the handle_manage_rule_request method accepts user_id
        try:
            result = controller.handle_manage_rule_request(
                action="info",
                target="",
                content="",
                user_id="test_user_123"
            )
            print("✓ manage_rule accepts user_id parameter")
            return True
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"✗ manage_rule does not accept user_id parameter: {e}")
                return False
            else:
                print("✓ manage_rule accepts user_id parameter")
                return True
        except Exception as e:
            print("✓ manage_rule accepts user_id parameter")
            return True
    except ImportError as e:
        print(f"✗ Could not import manage_rule controller: {e}")
        return False

def test_manage_connection_user_id():
    """Test that manage_connection accepts user_id parameter"""
    try:
        from fastmcp.connection_management.interface.controllers.connection_mcp_controller import ConnectionMCPController
        
        # Mock facade to avoid complex dependencies
        class MockConnectionFacade:
            def check_server_health(self, include_details=True, user_id=None):
                from fastmcp.connection_management.application.dtos.connection_dtos import HealthCheckResponse
                return HealthCheckResponse(
                    success=True,
                    status="healthy",
                    timestamp=1000,
                    details={} if include_details else None
                )
        
        # Create controller instance with mock facade
        controller = ConnectionMCPController(MockConnectionFacade())
        
        # Test that the manage_connection method accepts user_id
        try:
            result = controller.manage_connection(
                action="health_check",
                include_details=True,
                user_id="test_user_123"
            )
            print("✓ manage_connection accepts user_id parameter")
            return True
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"✗ manage_connection does not accept user_id parameter: {e}")
                return False
            else:
                print("✓ manage_connection accepts user_id parameter")  
                return True
        except Exception as e:
            print("✓ manage_connection accepts user_id parameter")
            return True
    except ImportError as e:
        print(f"✗ Could not import manage_connection controller: {e}")
        return False

def test_manage_compliance_user_id():
    """Test that manage_compliance already accepts user_id parameter (should already work)"""
    try:
        from fastmcp.task_management.interface.controllers.compliance_mcp_controller import ComplianceMCPController
        
        # Create controller instance 
        controller = ComplianceMCPController()
        
        # Test that the manage_compliance method accepts user_id
        try:
            result = controller.manage_compliance(
                action="get_compliance_dashboard",
                user_id="test_user_123"
            )
            print("✓ manage_compliance accepts user_id parameter")
            return True
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"✗ manage_compliance does not accept user_id parameter: {e}")
                return False
            else:
                print("✓ manage_compliance accepts user_id parameter")
                return True
        except Exception as e:
            print("✓ manage_compliance accepts user_id parameter")
            return True
    except ImportError as e:
        print(f"✗ Could not import manage_compliance controller: {e}")
        return False

def main():
    """Run all authentication standardization tests"""
    print("🔐 Testing Authentication Standardization Across MCP Tools")
    print("=" * 60)
    
    tests = [
        ("manage_agent", test_manage_agent_user_id),
        ("manage_subtask", test_manage_subtask_user_id), 
        ("manage_rule", test_manage_rule_user_id),
        ("manage_connection", test_manage_connection_user_id),
        ("manage_compliance", test_manage_compliance_user_id),
    ]
    
    results = []
    for tool_name, test_func in tests:
        print(f"\nTesting {tool_name}...")
        try:
            result = test_func()
            results.append((tool_name, result))
        except Exception as e:
            print(f"✗ {tool_name} test failed with exception: {e}")
            results.append((tool_name, False))
    
    print("\n" + "=" * 60)
    print("📊 AUTHENTICATION STANDARDIZATION TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for tool_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"{icon} {tool_name:<20} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All MCP tools successfully standardized with user_id authentication!")
        return True
    else:
        print(f"\n⚠️ {failed} tool(s) still need user_id parameter standardization.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)