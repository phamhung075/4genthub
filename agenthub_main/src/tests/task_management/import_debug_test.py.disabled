#!/usr/bin/env python3
"""
Debug Test: Import Error Investigation
Test the exact import sequence that occurs during task creation to identify where the issue originates.
"""

import sys
import os
import traceback

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

def test_import_sequence():
    """Test the exact import sequence used during task creation"""
    print("=== Import Debug Test ===")
    
    # Test 1: Direct domain imports
    print("\n1. Testing domain layer imports:")
    try:
        from fastmcp.task_management.domain.entities.task import Task
        print("   ✅ Task entity import: SUCCESS")
    except ImportError as e:
        print(f"   ❌ Task entity import: FAILED - {e}")
        traceback.print_exc()
    
    try:
        from fastmcp.task_management.domain.constants import validate_user_id
        print("   ✅ Domain constants import: SUCCESS")
    except ImportError as e:
        print(f"   ❌ Domain constants import: FAILED - {e}")
        traceback.print_exc()
    
    # Test 2: Application layer imports
    print("\n2. Testing application layer imports:")
    try:
        from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
        print("   ✅ Task facade import: SUCCESS")
    except ImportError as e:
        print(f"   ❌ Task facade import: FAILED - {e}")
        traceback.print_exc()
    
    try:
        from fastmcp.task_management.application.services.facade_service import FacadeService
        print("   ✅ Facade service import: SUCCESS")
    except ImportError as e:
        print(f"   ❌ Facade service import: FAILED - {e}")
        traceback.print_exc()
    
    # Test 3: Interface layer imports
    print("\n3. Testing interface layer imports:")
    try:
        from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController
        print("   ✅ TaskMCPController import: SUCCESS")
    except ImportError as e:
        print(f"   ❌ TaskMCPController import: FAILED - {e}")
        traceback.print_exc()
    
    # Test 4: Check for non-existent interface.domain
    print("\n4. Checking for problematic interface.domain import:")
    try:
        import fastmcp.task_management.interface.domain
        print("   ❌ ERROR: interface.domain import SHOULD NOT WORK")
    except ImportError:
        print("   ✅ Confirmed: interface.domain does NOT exist (correct)")
    
    # Test 5: Full controller initialization
    print("\n5. Testing full controller initialization:")
    try:
        controller = TaskMCPController()
        print("   ✅ TaskMCPController initialization: SUCCESS")
        
        # Test method access
        if hasattr(controller, 'manage_task'):
            print("   ✅ manage_task method exists")
        else:
            print("   ❌ manage_task method missing")
            
    except Exception as e:
        print(f"   ❌ Controller initialization: FAILED - {e}")
        traceback.print_exc()
    
    # Test 6: Simulate the create task path
    print("\n6. Testing task creation path simulation:")
    try:
        from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.handlers.crud_handler import CRUDHandler
        from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.validators.parameter_validator import ParameterValidator
        print("   ✅ Handler and validator imports: SUCCESS")
        
        # Check if the Task import in CRUD handler works
        from fastmcp.task_management.domain.entities.task import Task
        dummy_task = Task(title="test", description="test")
        print("   ✅ Task entity creation: SUCCESS")
        
    except Exception as e:
        print(f"   ❌ Task creation path: FAILED - {e}")
        traceback.print_exc()
    
    print("\n=== Import Debug Test Complete ===")

if __name__ == "__main__":
    test_import_sequence()