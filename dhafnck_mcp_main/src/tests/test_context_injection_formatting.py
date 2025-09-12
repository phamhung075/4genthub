#!/usr/bin/env python3
"""
Test context injection formatting with simulated data
"""

import sys
import os
import asyncio
import json

# Add paths for imports
project_root = '/home/daihungpham/__projects__/agentic-project'
sys.path.insert(0, os.path.join(project_root, '.claude/hooks/utils'))

# Import the context injector
try:
    from context_injector import ContextInjector
    MODULE_AVAILABLE = True
except ImportError:
    MODULE_AVAILABLE = False
    print("Warning: context_injector module not available")

async def test_formatting():
    """Test the context formatting with sample data"""
    
    print("=" * 60)
    print("Testing Context Injection Formatting")
    print("=" * 60)
    
    if not MODULE_AVAILABLE:
        print('\n⚠️  WARNING: context_injector module not available')
        print('   This test file needs to be updated for the new architecture')
        return False
    
    # Create a context injector
    injector = ContextInjector()
    
    # Sample context data that would come from MCP
    sample_context_data = {
        'task': {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'title': 'Implement user authentication',
            'status': 'in_progress',
            'priority': 'high',
            'assignees': ['coding-agent', '@security-auditor-agent'],
            'details': 'Implement JWT-based authentication with refresh tokens. Requirements: 1) Login endpoint 2) Logout endpoint 3) Token refresh mechanism 4) Secure cookie storage 5) Rate limiting on auth endpoints'
        },
        'git_branch': {
            'id': '456e7890-e89b-12d3-a456-426614174111',
            'git_branch_name': 'feature/user-auth',
            'git_branch_description': 'Implementation of JWT authentication system'
        },
        'related_tasks': [
            {'title': 'Add password validation', 'status': 'completed'},
            {'title': 'Create login UI', 'status': 'in_progress'},
            {'title': 'Add session management', 'status': 'todo'}
        ],
        'documentation': {
            'exists': True,
            'path': '/home/daihungpham/__projects__/agentic-project/ai_docs/authentication/jwt-implementation.md',
            'last_modified': '2025-09-11T15:30:00'
        }
    }
    
    # Test formatting with different priority levels
    for priority in ['high', 'medium', 'low']:
        print(f"\n--- Testing with priority: {priority} ---")
        formatted = injector._format_context_injection(sample_context_data, priority)
        print(formatted)
        print(f"\nFormatted context size: {len(formatted)} bytes")
    
    # Test with minimal data
    minimal_data = {
        'mcp_operation': {
            'tool': 'mcp__dhafnck_mcp_http__manage_task',
            'action': 'list'
        }
    }
    
    print("\n--- Testing with minimal data ---")
    formatted_minimal = injector._format_context_injection(minimal_data, 'low')
    print(formatted_minimal)
    print(f"\nMinimal context size: {len(formatted_minimal)} bytes")
    
    print("\n" + "=" * 60)
    print("✅ Context formatting test complete")
    print("=" * 60)
    
    # Show what meaningful context should look like
    print("\n📊 EXPECTED MEANINGFUL CONTEXT:")
    print("- Should be > 500 bytes for task operations")
    print("- Should include task details, status, assignees")
    print("- Should include related tasks if available")
    print("- Should include documentation status")
    print("- Should include git branch context")
    
    return len(formatted) > 500  # Return True if meaningful data

if __name__ == "__main__":
    result = asyncio.run(test_formatting())
    if result:
        print("\n✅ System would return MEANINGFUL context if MCP data retrieval worked")
    else:
        print("\n⚠️ Context formatting needs improvement")