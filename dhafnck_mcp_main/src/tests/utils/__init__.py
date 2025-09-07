"""
Centralized Test Utilities Package

This package provides standardized utilities for testing across the DhafnckMCP project:

Modules:
- database_utils: Standardized database testing utilities and fixtures
- mcp_client_utils: MCP protocol testing utilities (relocated from utilities/)
- test_isolation_utils: Test isolation and cleanup utilities (relocated)
- assertion_helpers: Custom assertion helpers for domain-specific testing
- test_patterns: Standardized test patterns and base classes
- coverage_analysis: Test coverage analysis and gap identification
"""

from .database_utils import (
    create_test_project_data,
    create_valid_git_branch,
    cleanup_test_data,
    TestDataBuilder,
    TestProjectData,
    create_database_records
)

from .mcp_client_utils import (
    MCPTestClient,
    MCPProtocolValidator
)

from .test_isolation_utils import (
    isolated_test_environment,
    cleanup_test_data_files_only,
    is_test_data_file
)

from .assertion_helpers import (
    assert_task_structure,
    assert_context_inheritance,
    assert_domain_event_structure,
    assert_mcp_tool_response,
    assert_pagination_structure,
    assert_test_isolation
)

from .test_patterns import (
    StandardTestCase,
    DatabaseTestPattern,
    MCPToolTestPattern,
    IntegrationTestPattern,
    PerformanceTestPattern
)

from .coverage_analysis import (
    CoverageAnalyzer,
    CoverageReport,
    CoverageGap
)

__all__ = [
    # Database utilities
    'create_test_project_data',
    'create_valid_git_branch', 
    'cleanup_test_data',
    'TestDataBuilder',
    'TestProjectData',
    'create_database_records',
    
    # MCP client utilities
    'MCPTestClient',
    'MCPProtocolValidator',
    
    # Test isolation
    'isolated_test_environment',
    'cleanup_test_data_files_only',
    'is_test_data_file',
    
    # Assertion helpers
    'assert_task_structure',
    'assert_context_inheritance',
    'assert_domain_event_structure',
    'assert_mcp_tool_response',
    'assert_pagination_structure',
    'assert_test_isolation',
    
    # Test patterns
    'StandardTestCase',
    'DatabaseTestPattern',
    'MCPToolTestPattern',
    'IntegrationTestPattern',
    'PerformanceTestPattern',
    
    # Coverage analysis
    'CoverageAnalyzer',
    'CoverageReport',
    'CoverageGap'
]