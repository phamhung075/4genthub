"""
Tests for Task Management Application Exceptions
"""

import pytest
from typing import Dict, Any

from fastmcp.task_management.application.exceptions import (
    TaskManagementException,
    TaskNotFoundError,
    SubtaskNotFoundError,
    ValidationError,
    DuplicateError,
    AuthorizationError,
    BusinessRuleViolationError,
    ExternalServiceError
)


class TestTaskManagementException:
    """Test base TaskManagementException"""
    
    def test_basic_exception(self):
        """Test creating basic exception"""
        message = "Something went wrong"
        exception = TaskManagementException(message)
        
        assert str(exception) == message
        assert exception.message == message
        assert exception.code == "TaskManagementException"
        assert exception.details == {}
    
    def test_exception_with_code(self):
        """Test creating exception with custom code"""
        message = "Custom error"
        code = "CUSTOM_ERROR"
        exception = TaskManagementException(message, code)
        
        assert exception.message == message
        assert exception.code == code
        assert exception.details == {}
    
    def test_exception_with_details(self):
        """Test creating exception with details"""
        message = "Error with details"
        details = {"field": "value", "number": 42}
        exception = TaskManagementException(message, details=details)
        
        assert exception.message == message
        assert exception.details == details
    
    def test_exception_with_all_params(self):
        """Test creating exception with all parameters"""
        message = "Complete error"
        code = "COMPLETE_ERROR"
        details = {"context": "test", "severity": "high"}
        
        exception = TaskManagementException(message, code, details)
        
        assert exception.message == message
        assert exception.code == code
        assert exception.details == details
    
    def test_exception_inheritance(self):
        """Test that TaskManagementException inherits from Exception"""
        exception = TaskManagementException("Test")
        
        assert isinstance(exception, Exception)
        assert isinstance(exception, TaskManagementException)


class TestTaskNotFoundError:
    """Test TaskNotFoundError exception"""
    
    def test_task_not_found_string_id(self):
        """Test TaskNotFoundError with string task ID"""
        task_id = "task-123"
        exception = TaskNotFoundError(task_id)
        
        assert exception.task_id == task_id
        assert exception.code == "TASK_NOT_FOUND"
        assert "Task with ID 'task-123' not found" in exception.message
        assert exception.details == {}
    
    def test_task_not_found_int_id(self):
        """Test TaskNotFoundError with integer task ID"""
        task_id = 12345
        exception = TaskNotFoundError(task_id)
        
        assert exception.task_id == task_id
        assert "Task with ID '12345' not found" in exception.message
    
    def test_task_not_found_with_details(self):
        """Test TaskNotFoundError with additional details"""
        task_id = "task-456"
        details = {"attempted_operation": "get", "user_id": "user-789"}
        
        exception = TaskNotFoundError(task_id, details)
        
        assert exception.task_id == task_id
        assert exception.details == details
    
    def test_task_not_found_inheritance(self):
        """Test TaskNotFoundError inheritance"""
        exception = TaskNotFoundError("task-123")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestSubtaskNotFoundError:
    """Test SubtaskNotFoundError exception"""
    
    def test_subtask_not_found_basic(self):
        """Test SubtaskNotFoundError with subtask ID only"""
        subtask_id = "subtask-123"
        exception = SubtaskNotFoundError(subtask_id)
        
        assert exception.subtask_id == subtask_id
        assert exception.task_id is None
        assert exception.code == "SUBTASK_NOT_FOUND"
        assert "Subtask with ID 'subtask-123' not found" in exception.message
        assert "task" not in exception.message  # Should not mention task
    
    def test_subtask_not_found_with_task_id(self):
        """Test SubtaskNotFoundError with both subtask and task ID"""
        subtask_id = "subtask-456"
        task_id = "task-789"
        
        exception = SubtaskNotFoundError(subtask_id, task_id)
        
        assert exception.subtask_id == subtask_id
        assert exception.task_id == task_id
        assert "Subtask with ID 'subtask-456' not found in task 'task-789'" in exception.message
    
    def test_subtask_not_found_with_details(self):
        """Test SubtaskNotFoundError with additional details"""
        subtask_id = "subtask-999"
        task_id = "task-888"
        details = {"search_criteria": "status=active"}
        
        exception = SubtaskNotFoundError(subtask_id, task_id, details)
        
        assert exception.subtask_id == subtask_id
        assert exception.task_id == task_id
        assert exception.details == details
    
    def test_subtask_not_found_inheritance(self):
        """Test SubtaskNotFoundError inheritance"""
        exception = SubtaskNotFoundError("subtask-123")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestValidationError:
    """Test ValidationError exception"""
    
    def test_validation_error_basic(self):
        """Test basic ValidationError"""
        message = "Invalid input data"
        exception = ValidationError(message)
        
        assert exception.message == message
        assert exception.code == "VALIDATION_ERROR"
        assert exception.field is None
        assert exception.value is None
        assert exception.details == {}
    
    def test_validation_error_with_field(self):
        """Test ValidationError with field information"""
        message = "Field must be a positive integer"
        field = "priority"
        value = -5
        
        exception = ValidationError(message, field, value)
        
        assert exception.message == message
        assert exception.field == field
        assert exception.value == value
    
    def test_validation_error_with_details(self):
        """Test ValidationError with additional details"""
        message = "Complex validation failed"
        field = "config"
        value = {"invalid": "config"}
        details = {"expected_schema": "v2.0", "validation_rules": ["required", "format"]}
        
        exception = ValidationError(message, field, value, details)
        
        assert exception.message == message
        assert exception.field == field
        assert exception.value == value
        assert exception.details == details
    
    def test_validation_error_with_none_value(self):
        """Test ValidationError with None value"""
        message = "Field is required"
        field = "name"
        
        exception = ValidationError(message, field, None)
        
        assert exception.field == field
        assert exception.value is None


class TestDuplicateError:
    """Test DuplicateError exception"""
    
    def test_duplicate_error_basic(self):
        """Test basic DuplicateError"""
        resource = "task"
        identifier = "task-123"
        
        exception = DuplicateError(resource, identifier)
        
        assert exception.resource == resource
        assert exception.identifier == identifier
        assert exception.code == "DUPLICATE_ERROR"
        assert "Duplicate task with identifier 'task-123'" in exception.message
    
    def test_duplicate_error_with_int_identifier(self):
        """Test DuplicateError with integer identifier"""
        resource = "project"
        identifier = 12345
        
        exception = DuplicateError(resource, identifier)
        
        assert exception.identifier == identifier
        assert "Duplicate project with identifier '12345'" in exception.message
    
    def test_duplicate_error_with_details(self):
        """Test DuplicateError with additional details"""
        resource = "user"
        identifier = "user@example.com"
        details = {"conflict_field": "email", "existing_id": "user-456"}
        
        exception = DuplicateError(resource, identifier, details)
        
        assert exception.resource == resource
        assert exception.identifier == identifier
        assert exception.details == details
    
    def test_duplicate_error_inheritance(self):
        """Test DuplicateError inheritance"""
        exception = DuplicateError("task", "task-123")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestAuthorizationError:
    """Test AuthorizationError exception"""
    
    def test_authorization_error_operation_only(self):
        """Test AuthorizationError with operation only"""
        operation = "delete"
        exception = AuthorizationError(operation)
        
        assert exception.operation == operation
        assert exception.resource is None
        assert exception.code == "AUTHORIZATION_ERROR"
        assert "Not authorized to delete" in exception.message
        assert exception.message == "Not authorized to delete"
    
    def test_authorization_error_with_resource(self):
        """Test AuthorizationError with operation and resource"""
        operation = "update"
        resource = "task-123"
        
        exception = AuthorizationError(operation, resource)
        
        assert exception.operation == operation
        assert exception.resource == resource
        assert "Not authorized to update task-123" in exception.message
    
    def test_authorization_error_with_details(self):
        """Test AuthorizationError with additional details"""
        operation = "create"
        resource = "project"
        details = {"required_role": "admin", "user_role": "viewer"}
        
        exception = AuthorizationError(operation, resource, details)
        
        assert exception.operation == operation
        assert exception.resource == resource
        assert exception.details == details
    
    def test_authorization_error_inheritance(self):
        """Test AuthorizationError inheritance"""
        exception = AuthorizationError("read", "task")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestBusinessRuleViolationError:
    """Test BusinessRuleViolationError exception"""
    
    def test_business_rule_violation_basic(self):
        """Test basic BusinessRuleViolationError"""
        rule = "max_subtasks_per_task"
        message = "Cannot exceed 10 subtasks per task"
        
        exception = BusinessRuleViolationError(rule, message)
        
        assert exception.rule == rule
        assert exception.message == message
        assert exception.code == "BUSINESS_RULE_VIOLATION"
        assert exception.details == {}
    
    def test_business_rule_violation_with_details(self):
        """Test BusinessRuleViolationError with additional details"""
        rule = "task_priority_escalation"
        message = "Cannot escalate task priority without supervisor approval"
        details = {
            "current_priority": "medium",
            "requested_priority": "critical",
            "required_approval": "supervisor"
        }
        
        exception = BusinessRuleViolationError(rule, message, details)
        
        assert exception.rule == rule
        assert exception.message == message
        assert exception.details == details
    
    def test_business_rule_violation_inheritance(self):
        """Test BusinessRuleViolationError inheritance"""
        exception = BusinessRuleViolationError("test_rule", "Test message")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestExternalServiceError:
    """Test ExternalServiceError exception"""
    
    def test_external_service_error_basic(self):
        """Test basic ExternalServiceError"""
        service = "keycloak"
        operation = "authenticate"
        message = "Connection timeout"
        
        exception = ExternalServiceError(service, operation, message)
        
        assert exception.service == service
        assert exception.operation == operation
        assert exception.code == "EXTERNAL_SERVICE_ERROR"
        assert "External service 'keycloak' failed during 'authenticate': Connection timeout" in exception.message
    
    def test_external_service_error_with_details(self):
        """Test ExternalServiceError with additional details"""
        service = "database"
        operation = "query"
        message = "Query execution timeout"
        details = {
            "query": "SELECT * FROM tasks WHERE ...",
            "timeout_seconds": 30,
            "retry_count": 3
        }
        
        exception = ExternalServiceError(service, operation, message, details)
        
        assert exception.service == service
        assert exception.operation == operation
        assert exception.details == details
        assert "External service 'database' failed during 'query': Query execution timeout" in exception.message
    
    def test_external_service_error_inheritance(self):
        """Test ExternalServiceError inheritance"""
        exception = ExternalServiceError("service", "operation", "error")
        
        assert isinstance(exception, TaskManagementException)
        assert isinstance(exception, Exception)


class TestExceptionHierarchy:
    """Test exception hierarchy and common behaviors"""
    
    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from TaskManagementException"""
        exceptions = [
            TaskNotFoundError("task-1"),
            SubtaskNotFoundError("subtask-1"),
            ValidationError("validation failed"),
            DuplicateError("resource", "id"),
            AuthorizationError("operation"),
            BusinessRuleViolationError("rule", "message"),
            ExternalServiceError("service", "operation", "error")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, TaskManagementException)
            assert isinstance(exc, Exception)
    
    def test_all_exceptions_have_code(self):
        """Test that all exceptions have a code attribute"""
        exceptions = [
            TaskManagementException("base"),
            TaskNotFoundError("task-1"),
            SubtaskNotFoundError("subtask-1"),
            ValidationError("validation failed"),
            DuplicateError("resource", "id"),
            AuthorizationError("operation"),
            BusinessRuleViolationError("rule", "message"),
            ExternalServiceError("service", "operation", "error")
        ]
        
        for exc in exceptions:
            assert hasattr(exc, 'code')
            assert exc.code is not None
            assert isinstance(exc.code, str)
    
    def test_all_exceptions_have_details(self):
        """Test that all exceptions have a details attribute"""
        exceptions = [
            TaskManagementException("base"),
            TaskNotFoundError("task-1"),
            SubtaskNotFoundError("subtask-1"),
            ValidationError("validation failed"),
            DuplicateError("resource", "id"),
            AuthorizationError("operation"),
            BusinessRuleViolationError("rule", "message"),
            ExternalServiceError("service", "operation", "error")
        ]
        
        for exc in exceptions:
            assert hasattr(exc, 'details')
            assert isinstance(exc.details, dict)
    
    def test_exception_str_representation(self):
        """Test string representation of exceptions"""
        message = "Test error message"
        exception = TaskManagementException(message)
        
        assert str(exception) == message
        
        # Test with specific exception
        task_error = TaskNotFoundError("task-123")
        assert "Task with ID 'task-123' not found" in str(task_error)


class TestExceptionEdgeCases:
    """Test edge cases and special scenarios for exceptions"""
    
    def test_empty_details_dict(self):
        """Test exceptions with empty details dictionary"""
        exception = TaskManagementException("test", details={})
        assert exception.details == {}
    
    def test_none_details_becomes_empty_dict(self):
        """Test that None details becomes empty dictionary"""
        exception = TaskManagementException("test", details=None)
        assert exception.details == {}
    
    def test_complex_details_structure(self):
        """Test exception with complex details structure"""
        complex_details = {
            "nested": {
                "level1": {
                    "level2": "deep_value"
                }
            },
            "array": [1, 2, 3],
            "mixed": {
                "string": "value",
                "number": 42,
                "boolean": True,
                "null": None
            }
        }
        
        exception = TaskManagementException("test", details=complex_details)
        assert exception.details == complex_details
        assert exception.details["nested"]["level1"]["level2"] == "deep_value"
        assert exception.details["array"] == [1, 2, 3]
    
    def test_unicode_in_messages(self):
        """Test exceptions with Unicode characters in messages"""
        unicode_message = "Tâche non trouvée 🔍 ID: 'тест-123'"
        exception = TaskManagementException(unicode_message)
        
        assert exception.message == unicode_message
        assert str(exception) == unicode_message
    
    def test_very_long_identifiers(self):
        """Test exceptions with very long identifiers"""
        long_id = "a" * 1000  # Very long ID
        exception = TaskNotFoundError(long_id)
        
        assert exception.task_id == long_id
        assert long_id in exception.message