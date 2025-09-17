#!/usr/bin/env python3
"""
Test script for dynamic agent role display functionality.
Tests the agent state manager and status line role mapping.
"""

import json
import sys
import uuid
from pathlib import Path

# Add hooks to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / ".claude" / "hooks"))
from utils.agent_state_manager import set_current_agent, get_current_agent, get_agent_role_from_session

def test_agent_role_mapping():
    """Test the role mapping functionality."""
    print("Testing agent role mapping...")

    # Create a test session
    test_session = str(uuid.uuid4())
    print(f"Test session ID: {test_session}")

    # Test different agent types
    test_cases = [
        ('coding-agent', 'Coding'),
        ('debugger-agent', 'Debugging'),
        ('test-orchestrator-agent', 'Testing'),
        ('master-orchestrator-agent', 'Orchestrating'),
        ('ui-specialist-agent', 'UI/UX'),
        ('security-auditor-agent', 'Security'),
        ('documentation-agent', 'Documentation'),
        ('unknown-agent', 'Assistant')  # Should default to Assistant
    ]

    for agent_name, expected_role in test_cases:
        print(f"\n--- Testing {agent_name} ---")

        # Set the agent
        set_current_agent(test_session, agent_name)

        # Verify agent was set
        current_agent = get_current_agent(test_session)
        print(f"Current agent: {current_agent}")

        # Get the role
        role = get_agent_role_from_session(test_session)
        print(f"Mapped role: {role}")
        print(f"Expected role: {expected_role}")

        # Check if mapping is correct
        if role == expected_role:
            print(f"✅ PASS: {agent_name} correctly mapped to {role}")
        else:
            print(f"❌ FAIL: {agent_name} expected {expected_role}, got {role}")

def test_status_line_integration():
    """Test the status line integration."""
    print("\n\nTesting status line integration...")

    # Import status line module
    sys.path.insert(0, str(project_root / ".claude" / "status_lines"))
    from status_line_mcp import generate_status_line

    # Create test input data
    test_session = str(uuid.uuid4())
    set_current_agent(test_session, 'coding-agent')

    input_data = {
        'session_id': test_session,
        'model': {
            'display_name': 'Claude'
        }
    }

    # Generate status line
    status_line = generate_status_line(input_data)
    print(f"Generated status line: {status_line}")

    # Check if it contains the expected role display
    if '[Agent] [Coding]' in status_line:
        print("✅ PASS: Status line contains dynamic agent role display")
    else:
        print("❌ FAIL: Status line missing dynamic agent role display")

    # Check if it contains the active agent display
    if '🎯 Active: coding-agent' in status_line:
        print("✅ PASS: Status line contains active agent display")
    else:
        print("❌ FAIL: Status line missing active agent display")

if __name__ == '__main__':
    print("=== Testing Dynamic Agent Role Display ===\n")

    try:
        project_root = Path(__file__).parent.parent.parent.parent
        test_agent_role_mapping()
        test_status_line_integration()
        print("\n=== Test Complete ===")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()