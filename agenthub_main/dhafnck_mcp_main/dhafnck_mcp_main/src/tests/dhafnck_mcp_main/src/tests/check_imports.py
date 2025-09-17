#!/usr/bin/env python
"""Check imports for test failures."""
import sys
import os
os.chdir('./agenthub_main')
sys.path.insert(0, 'src')

# Try to import test modules
test_modules = [
    'tests.unit.mcp_controllers.test_task_mcp_controller',
    'tests.unit.mcp_controllers.test_task_mcp_controller_complete',
]

for module_name in test_modules:
    try:
        __import__(module_name)
        print(f"✅ {module_name}: Import successful")
    except Exception as e:
        print(f"❌ {module_name}: {e}")