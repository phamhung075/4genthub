"""
Unit Tests for MCP Controllers

This package contains comprehensive unit tests for all MCP controllers in the system.
Each controller has its own test file with proper mocking of all dependencies.

Test Files:
- test_task_mcp_controller.py: Tests for TaskMCPController
- test_project_mcp_controller.py: Tests for ProjectMCPController  
- test_subtask_mcp_controller.py: Tests for SubtaskMCPController
- test_git_branch_mcp_controller.py: Tests for GitBranchMCPController
- test_context_mcp_controller.py: Tests for ContextMCPController
- test_agent_mcp_controller.py: Tests for AgentMCPController

Testing Framework:
- pytest: Primary testing framework
- unittest.mock: Comprehensive mocking of dependencies
- asyncio: Async test support
- parametrize: Data-driven testing

Key Testing Patterns:
1. Fixture-based setup for common test data
2. Proper mocking of facades, authentication, and permissions
3. Comprehensive error handling tests
4. Edge case validation
5. Parametrized tests for multiple scenarios
6. Async/await support for async operations

Usage:
    # Run all controller tests
    pytest dhafnck_mcp_main/src/tests/unit/mcp_controllers/

    # Run specific controller tests
    pytest dhafnck_mcp_main/src/tests/unit/mcp_controllers/test_task_mcp_controller.py

    # Run with coverage
    pytest dhafnck_mcp_main/src/tests/unit/mcp_controllers/ --cov --cov-report=html
"""