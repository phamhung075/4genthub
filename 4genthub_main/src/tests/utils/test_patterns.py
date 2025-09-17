"""
Standardized Test Patterns for 4genthub

This module provides standardized patterns and utilities for consistent
testing across the 4genthub project. It consolidates best practices
and common patterns into reusable components.
"""

import pytest
from typing import Dict, Any, Callable, List, Optional, Union
from abc import ABC, abstractmethod
from contextlib import contextmanager
from unittest.mock import Mock, patch


class StandardTestCase(ABC):
    """
    Base class for standardized test cases that ensures consistent
    test structure and common setup/teardown patterns.
    """
    
    @abstractmethod
    def setup_test_data(self) -> Dict[str, Any]:
        """Setup test data specific to this test case"""
        pass
    
    @abstractmethod
    def cleanup_test_data(self, test_data: Dict[str, Any]) -> None:
        """Cleanup test data after test completion"""
        pass
    
    def run_test_scenario(self, test_scenario: Callable, test_data: Dict[str, Any]) -> Any:
        """
        Run a test scenario with standardized setup and cleanup.
        
        Args:
            test_scenario: The actual test function to execute
            test_data: Test data to pass to the scenario
            
        Returns:
            Result of the test scenario
        """
        try:
            return test_scenario(test_data)
        finally:
            self.cleanup_test_data(test_data)


class DatabaseTestPattern:
    """
    Standardized pattern for database-related tests.
    Ensures consistent database setup, transaction management, and cleanup.
    """
    
    def __init__(self, use_transaction_rollback: bool = True):
        self.use_transaction_rollback = use_transaction_rollback
        self._test_data_created = []
    
    @contextmanager
    def database_test_context(self):
        """
        Context manager for database tests with automatic cleanup.
        
        Usage:
            with DatabaseTestPattern().database_test_context():
                # Perform database operations
                pass
        """
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        
        db_config = get_db_config()
        
        if self.use_transaction_rollback:
            # Use transaction rollback for isolation
            with db_config.get_session() as session:
                # Start transaction
                transaction = session.begin()
                try:
                    yield session
                finally:
                    # Always rollback to ensure isolation
                    transaction.rollback()
        else:
            # Use explicit cleanup (for integration tests)
            try:
                yield None
            finally:
                self._cleanup_created_data()
    
    def track_created_data(self, table: str, id_field: str, id_value: str):
        """Track data created during test for cleanup"""
        self._test_data_created.append({
            'table': table,
            'id_field': id_field,
            'id_value': id_value
        })
    
    def _cleanup_created_data(self):
        """Clean up tracked test data"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        if not self._test_data_created:
            return
        
        db_config = get_db_config()
        
        with db_config.get_session() as session:
            try:
                # Clean up in reverse order to handle foreign key constraints
                for data in reversed(self._test_data_created):
                    session.execute(
                        text(f"DELETE FROM {data['table']} WHERE {data['id_field']} = :id"),
                        {'id': data['id_value']}
                    )
                session.commit()
            except Exception:
                session.rollback()
            finally:
                self._test_data_created.clear()


class MCPToolTestPattern:
    """
    Standardized pattern for testing MCP tools.
    Provides consistent validation and error handling patterns.
    """
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
    
    def test_successful_call(self, tool_function: Callable, valid_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test successful MCP tool call with standardized validation.
        
        Args:
            tool_function: The MCP tool function to test
            valid_args: Valid arguments for the tool
            
        Returns:
            Tool call result
        """
        from .assertion_helpers import assert_mcp_tool_response
        
        result = tool_function(**valid_args)
        assert_mcp_tool_response(result, expected_success=True)
        
        return result
    
    def test_missing_required_parameter(self, tool_function: Callable, required_param: str) -> Dict[str, Any]:
        """
        Test MCP tool call with missing required parameter.
        
        Args:
            tool_function: The MCP tool function to test
            required_param: Name of the required parameter to omit
            
        Returns:
            Tool call result (should be failure)
        """
        from .assertion_helpers import assert_mcp_tool_response
        
        # Call tool without required parameter
        result = tool_function()
        assert_mcp_tool_response(result, expected_success=False)
        
        # Check that error mentions the missing parameter
        assert required_param in result['error'], \
            f"Error should mention missing parameter '{required_param}': {result['error']}"
        
        return result
    
    def test_invalid_parameter_value(
        self, 
        tool_function: Callable, 
        valid_args: Dict[str, Any],
        invalid_param: str,
        invalid_value: Any
    ) -> Dict[str, Any]:
        """
        Test MCP tool call with invalid parameter value.
        
        Args:
            tool_function: The MCP tool function to test
            valid_args: Valid arguments for the tool
            invalid_param: Name of parameter to make invalid
            invalid_value: Invalid value for the parameter
            
        Returns:
            Tool call result (should be failure)
        """
        from .assertion_helpers import assert_mcp_tool_response
        
        # Create args with invalid value
        test_args = valid_args.copy()
        test_args[invalid_param] = invalid_value
        
        result = tool_function(**test_args)
        assert_mcp_tool_response(result, expected_success=False)
        
        return result


class IntegrationTestPattern:
    """
    Standardized pattern for integration tests that span multiple components.
    Provides orchestration and validation for complex test scenarios.
    """
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.test_steps = []
        self.cleanup_functions = []
    
    def add_test_step(self, step_name: str, step_function: Callable, expected_result: Any = None):
        """Add a test step to the integration test"""
        self.test_steps.append({
            'name': step_name,
            'function': step_function,
            'expected': expected_result
        })
    
    def add_cleanup_function(self, cleanup_function: Callable):
        """Add a cleanup function to run after test completion"""
        self.cleanup_functions.append(cleanup_function)
    
    def execute_test_scenario(self) -> Dict[str, Any]:
        """
        Execute the full integration test scenario.
        
        Returns:
            Dictionary containing results of all test steps
        """
        results = {
            'test_name': self.test_name,
            'steps': {},
            'overall_success': True,
            'errors': []
        }
        
        try:
            for step in self.test_steps:
                step_name = step['name']
                step_function = step['function']
                expected_result = step['expected']
                
                try:
                    step_result = step_function()
                    results['steps'][step_name] = {
                        'success': True,
                        'result': step_result
                    }
                    
                    # Validate expected result if provided
                    if expected_result is not None:
                        assert step_result == expected_result, \
                            f"Step '{step_name}' result mismatch: expected {expected_result}, got {step_result}"
                
                except Exception as e:
                    results['steps'][step_name] = {
                        'success': False,
                        'error': str(e)
                    }
                    results['overall_success'] = False
                    results['errors'].append(f"Step '{step_name}': {e}")
        
        finally:
            # Run cleanup functions
            for cleanup_func in self.cleanup_functions:
                try:
                    cleanup_func()
                except Exception as e:
                    results['errors'].append(f"Cleanup error: {e}")
        
        return results


class PerformanceTestPattern:
    """
    Standardized pattern for performance tests with timing and resource monitoring.
    """
    
    def __init__(self, test_name: str, max_duration_seconds: float = 1.0):
        self.test_name = test_name
        self.max_duration_seconds = max_duration_seconds
    
    @contextmanager
    def performance_monitoring(self):
        """
        Context manager for performance monitoring during tests.
        
        Usage:
            with PerformanceTestPattern("test").performance_monitoring() as monitor:
                # Perform operations to monitor
                monitor.check_memory_usage()
        """
        import time
        import psutil
        
        class PerformanceMonitor:
            def __init__(self):
                self.start_time = time.time()
                self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                self.checkpoints = []
            
            def checkpoint(self, name: str):
                """Add a performance checkpoint"""
                current_time = time.time()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                self.checkpoints.append({
                    'name': name,
                    'elapsed_time': current_time - self.start_time,
                    'memory_usage': current_memory,
                    'memory_delta': current_memory - self.start_memory
                })
            
            def check_memory_usage(self, max_memory_mb: float = 100.0):
                """Check current memory usage against limit"""
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                memory_delta = current_memory - self.start_memory
                
                assert memory_delta <= max_memory_mb, \
                    f"Memory usage exceeded limit: {memory_delta:.2f}MB > {max_memory_mb}MB"
            
            def get_results(self) -> Dict[str, Any]:
                """Get performance monitoring results"""
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                return {
                    'test_name': self.test_name,
                    'total_duration': end_time - self.start_time,
                    'memory_start': self.start_memory,
                    'memory_end': end_memory,
                    'memory_delta': end_memory - self.start_memory,
                    'checkpoints': self.checkpoints
                }
        
        monitor = PerformanceMonitor()
        
        try:
            yield monitor
        finally:
            results = monitor.get_results()
            
            # Assert performance constraints
            assert results['total_duration'] <= self.max_duration_seconds, \
                f"Test '{self.test_name}' exceeded time limit: {results['total_duration']:.3f}s > {self.max_duration_seconds}s"


# =============================================
# PYTEST FIXTURES FOR STANDARDIZED PATTERNS
# =============================================

@pytest.fixture
def database_test_pattern():
    """Pytest fixture providing DatabaseTestPattern"""
    return DatabaseTestPattern()


@pytest.fixture
def mcp_tool_test_pattern():
    """Pytest fixture providing MCPToolTestPattern factory"""
    def _create_pattern(tool_name: str):
        return MCPToolTestPattern(tool_name)
    return _create_pattern


@pytest.fixture
def integration_test_pattern():
    """Pytest fixture providing IntegrationTestPattern factory"""
    def _create_pattern(test_name: str):
        return IntegrationTestPattern(test_name)
    return _create_pattern


@pytest.fixture
def performance_test_pattern():
    """Pytest fixture providing PerformanceTestPattern factory"""
    def _create_pattern(test_name: str, max_duration_seconds: float = 1.0):
        return PerformanceTestPattern(test_name, max_duration_seconds)
    return _create_pattern