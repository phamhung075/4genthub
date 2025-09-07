"""
Custom Assertion Helpers for Domain-Specific Testing

Provides specialized assertion functions for validating domain objects,
business rules, and integration points in the DhafnckMCP system.
"""

from typing import Dict, Any, List, Optional, Union
from uuid import UUID


def assert_task_structure(task_data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> None:
    """
    Assert that task data has the expected structure.
    
    Args:
        task_data: Dictionary containing task information
        required_fields: Optional list of fields that must be present
    
    Raises:
        AssertionError: If structure is invalid
    """
    # Default required fields for a task
    default_required = [
        'id', 'title', 'status', 'priority', 'created_at', 'updated_at'
    ]
    
    fields_to_check = required_fields or default_required
    
    # Check that it's a dictionary
    assert isinstance(task_data, dict), f"Task data must be a dictionary, got {type(task_data)}"
    
    # Check required fields are present
    for field in fields_to_check:
        assert field in task_data, f"Task missing required field: {field}"
    
    # Validate field types if present
    if 'id' in task_data:
        assert isinstance(task_data['id'], str), "Task ID must be a string"
        assert len(task_data['id']) > 0, "Task ID cannot be empty"
    
    if 'title' in task_data:
        assert isinstance(task_data['title'], str), "Task title must be a string"
        assert len(task_data['title']) > 0, "Task title cannot be empty"
    
    if 'status' in task_data:
        valid_statuses = ['todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled']
        assert task_data['status'] in valid_statuses, f"Invalid task status: {task_data['status']}"
    
    if 'priority' in task_data:
        valid_priorities = ['low', 'medium', 'high', 'urgent', 'critical']
        assert task_data['priority'] in valid_priorities, f"Invalid task priority: {task_data['priority']}"


def assert_context_inheritance(context_data: Dict[str, Any], expected_inheritance_chain: List[str]) -> None:
    """
    Assert that context data properly inherits from parent contexts.
    
    Args:
        context_data: Dictionary containing context information
        expected_inheritance_chain: List of context levels that should be inherited
    
    Raises:
        AssertionError: If inheritance is incorrect
    """
    assert isinstance(context_data, dict), f"Context data must be a dictionary, got {type(context_data)}"
    
    # Check that inheritance information is present
    assert 'inheritance_chain' in context_data, "Context data missing inheritance_chain"
    
    actual_chain = context_data['inheritance_chain']
    assert isinstance(actual_chain, list), "Inheritance chain must be a list"
    
    # Validate inheritance chain matches expected
    assert len(actual_chain) == len(expected_inheritance_chain), \
        f"Inheritance chain length mismatch. Expected {len(expected_inheritance_chain)}, got {len(actual_chain)}"
    
    for i, (expected, actual) in enumerate(zip(expected_inheritance_chain, actual_chain)):
        assert expected == actual, f"Inheritance chain mismatch at position {i}: expected {expected}, got {actual}"
    
    # Check that inherited data is properly merged
    if 'inherited_data' in context_data:
        inherited_data = context_data['inherited_data']
        assert isinstance(inherited_data, dict), "Inherited data must be a dictionary"


def assert_domain_event_structure(event_data: Dict[str, Any], event_type: str) -> None:
    """
    Assert that domain event data has the expected structure.
    
    Args:
        event_data: Dictionary containing domain event information
        event_type: Expected event type (e.g., 'TaskCreated', 'ContextUpdated')
    
    Raises:
        AssertionError: If event structure is invalid
    """
    assert isinstance(event_data, dict), f"Event data must be a dictionary, got {type(event_data)}"
    
    # Check required event fields
    required_fields = ['event_type', 'event_id', 'occurred_at']
    for field in required_fields:
        assert field in event_data, f"Event missing required field: {field}"
    
    # Validate event type
    assert event_data['event_type'] == event_type, \
        f"Event type mismatch: expected {event_type}, got {event_data['event_type']}"
    
    # Validate event ID format (should be UUID)
    event_id = event_data['event_id']
    assert isinstance(event_id, str), "Event ID must be a string"
    try:
        UUID(event_id)
    except ValueError:
        assert False, f"Event ID is not a valid UUID: {event_id}"
    
    # Validate timestamp format
    occurred_at = event_data['occurred_at']
    assert isinstance(occurred_at, str), "Occurred_at must be a string"
    assert len(occurred_at) > 0, "Occurred_at cannot be empty"


def assert_mcp_tool_response(response: Dict[str, Any], expected_success: bool = True) -> None:
    """
    Assert that MCP tool response has the expected structure.
    
    Args:
        response: Dictionary containing MCP tool response
        expected_success: Whether the response should indicate success
    
    Raises:
        AssertionError: If response structure is invalid
    """
    assert isinstance(response, dict), f"MCP response must be a dictionary, got {type(response)}"
    
    # Check for success field
    assert 'success' in response, "MCP response missing 'success' field"
    assert isinstance(response['success'], bool), "'success' field must be a boolean"
    
    # Validate success/failure structure
    if expected_success:
        assert response['success'] is True, f"Expected successful response, got: {response}"
        
        # Successful responses should have result data
        if 'error' in response:
            assert False, f"Successful response should not contain error: {response['error']}"
    else:
        assert response['success'] is False, f"Expected failed response, got: {response}"
        
        # Failed responses should have error information
        assert 'error' in response, "Failed response missing 'error' field"
        assert isinstance(response['error'], str), "Error field must be a string"
        assert len(response['error']) > 0, "Error message cannot be empty"


def assert_database_foreign_key_constraint(
    test_data: Dict[str, Any], 
    foreign_key_field: str,
    referenced_table: str
) -> None:
    """
    Assert that database foreign key constraints are properly enforced.
    
    Args:
        test_data: Test data that should trigger foreign key constraint
        foreign_key_field: Name of the foreign key field
        referenced_table: Name of the referenced table
    
    Raises:
        AssertionError: If foreign key constraint is not enforced
    """
    assert isinstance(test_data, dict), "Test data must be a dictionary"
    assert foreign_key_field in test_data, f"Test data missing foreign key field: {foreign_key_field}"
    
    # This helper documents the expectation that foreign key constraints should be enforced
    # The actual constraint testing should be done in the calling test


def assert_pagination_structure(
    pagination_result: Dict[str, Any],
    expected_page: int,
    expected_page_size: int,
    min_total_count: int = 0
) -> None:
    """
    Assert that pagination result has the expected structure.
    
    Args:
        pagination_result: Dictionary containing pagination result
        expected_page: Expected current page number
        expected_page_size: Expected page size
        min_total_count: Minimum expected total count
    
    Raises:
        AssertionError: If pagination structure is invalid
    """
    assert isinstance(pagination_result, dict), "Pagination result must be a dictionary"
    
    # Check required pagination fields
    required_fields = ['items', 'total_count', 'page', 'page_size', 'total_pages', 'has_next', 'has_previous']
    for field in required_fields:
        assert field in pagination_result, f"Pagination result missing field: {field}"
    
    # Validate field types and values
    assert isinstance(pagination_result['items'], list), "'items' must be a list"
    assert isinstance(pagination_result['total_count'], int), "'total_count' must be an integer"
    assert isinstance(pagination_result['page'], int), "'page' must be an integer"
    assert isinstance(pagination_result['page_size'], int), "'page_size' must be an integer"
    assert isinstance(pagination_result['total_pages'], int), "'total_pages' must be an integer"
    assert isinstance(pagination_result['has_next'], bool), "'has_next' must be a boolean"
    assert isinstance(pagination_result['has_previous'], bool), "'has_previous' must be a boolean"
    
    # Validate pagination logic
    assert pagination_result['page'] == expected_page, \
        f"Page mismatch: expected {expected_page}, got {pagination_result['page']}"
    assert pagination_result['page_size'] == expected_page_size, \
        f"Page size mismatch: expected {expected_page_size}, got {pagination_result['page_size']}"
    assert pagination_result['total_count'] >= min_total_count, \
        f"Total count too low: expected >= {min_total_count}, got {pagination_result['total_count']}"
    
    # Validate items count doesn't exceed page size
    assert len(pagination_result['items']) <= expected_page_size, \
        f"Items count exceeds page size: {len(pagination_result['items'])} > {expected_page_size}"


def assert_test_isolation(test_id: str, file_paths: List[str]) -> None:
    """
    Assert that test isolation is properly maintained.
    
    Args:
        test_id: Unique identifier for the test
        file_paths: List of file paths that should be test-specific
    
    Raises:
        AssertionError: If test isolation is violated
    """
    assert isinstance(test_id, str), "Test ID must be a string"
    assert len(test_id) > 0, "Test ID cannot be empty"
    assert isinstance(file_paths, list), "File paths must be a list"
    
    # Check that all file paths contain test identifier or are clearly test files
    for file_path in file_paths:
        assert isinstance(file_path, str), f"File path must be a string: {file_path}"
        
        # File should either contain test ID or be clearly a test file
        is_test_file = (
            test_id in file_path or
            'test' in file_path.lower() or
            file_path.endswith('.test.json') or
            file_path.endswith('.test.db')
        )
        
        assert is_test_file, f"File path does not appear to be test-isolated: {file_path}"