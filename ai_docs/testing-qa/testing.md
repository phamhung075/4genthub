# Testing Guide

## Overview

Comprehensive testing strategies for the agenthub platform using Test-Driven Development (TDD) patterns with strict authentication requirements.

## Quick Start

### Authentication Testing (MANDATORY)
All tests must enforce strict authentication following the 2025-08-25 modernization:

```python
@patch('module.get_current_user_id')
def test_operation_with_auth(self, mock_get_user_id):
    """Test operation with proper authentication."""
    mock_get_user_id.return_value = "test-user-123"
    result = controller.operation()
    assert result["success"] is True

def test_operation_without_auth_raises_error(self):
    """Test operation without authentication raises error."""
    with pytest.raises(UserAuthenticationRequiredError):
        controller.operation()
```

### Test Categories

#### Unit Tests
- **Location**: `agenthub_main/src/tests/unit/`
- **Target Coverage**: 90%+
- **Focus**: Individual components, business logic, value objects

#### Integration Tests  
- **Location**: `agenthub_main/src/tests/integration/`
- **Target Coverage**: All API endpoints
- **Focus**: Component interaction, database operations, MCP tools

#### End-to-End Tests
- **Location**: `agenthub_main/src/tests/e2e/`
- **Target Coverage**: Critical user journeys  
- **Focus**: Complete workflows, user scenarios

### Running Tests

```bash
# All tests
pytest agenthub_main/src/tests/

# Unit tests only
pytest agenthub_main/src/tests/unit/

# With coverage
pytest --cov=agenthub_main/src --cov-report=html

# Specific test file
pytest agenthub_main/src/tests/unit/test_task_management.py
```

## Test Structure

### Standard Test Class
```python
class TestComponent:
    """Test cases for Component."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Initialize mocks and test data
    
    @patch('module.get_current_user_id')
    def test_successful_operation(self, mock_get_user_id):
        """Test successful operation with authentication."""
        mock_get_user_id.return_value = "test-user"
        # Test logic here
    
    def test_operation_validation_error(self):
        """Test validation error scenarios."""
        # Error case testing
```

### TDD Workflow

1. **Write Test First**
   ```python
   def test_new_feature_should_work():
       """Test new feature functionality."""
       # Arrange
       input_data = {"key": "value"}
       
       # Act  
       result = new_feature(input_data)
       
       # Assert
       assert result.success is True
       assert result.data == expected_data
   ```

2. **Run Test (Should Fail)**
   ```bash
   pytest tests/test_new_feature.py::test_new_feature_should_work
   ```

3. **Implement Feature**
   ```python
   def new_feature(input_data):
       """Implement new feature."""
       # Implementation here
       pass
   ```

4. **Run Test (Should Pass)**
   ```bash  
   pytest tests/test_new_feature.py::test_new_feature_should_work
   ```

5. **Refactor**
   - Improve code quality
   - Run tests to ensure no regression

## Best Practices

### Authentication Requirements
- ✅ Mock `get_current_user_id()` in all authenticated operations
- ✅ Test `UserAuthenticationRequiredError` scenarios  
- ✅ No default user patterns allowed
- ✅ Explicit authentication contexts required

### Import Guidelines
```python
# ✅ Correct imports (post-2025-08-25)
from fastmcp.task_management.domain.value_objects.status import Status
from fastmcp.task_management.domain.value_objects.priority import Priority

# ❌ Deprecated imports (will fail)
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
```

### Test Naming
- Use descriptive test names
- Follow pattern: `test_<what>_<condition>_<expected_result>`
- Examples:
  - `test_create_task_with_valid_data_returns_success`
  - `test_update_task_without_auth_raises_error`

### Assertions
- Use specific assertions
- Include meaningful error messages
- Examples:
  ```python
  assert result.status == "success", f"Expected success, got {result.status}"
  assert len(result.tasks) > 0, "Expected tasks to be returned"
  ```

## Testing Tools

### Pytest Fixtures
```python
@pytest.fixture
def mock_database():
    """Mock database session."""
    with patch('sqlalchemy.create_engine') as mock_engine:
        yield mock_engine

@pytest.fixture  
def authenticated_user():
    """Mock authenticated user."""
    with patch('module.get_current_user_id') as mock_user:
        mock_user.return_value = "test-user-123"
        yield mock_user
```

### Mock Patterns
```python
# Database mocking
@patch('repository.get_db_session')
def test_database_operation(self, mock_session):
    mock_session.return_value.__enter__ = Mock()
    mock_session.return_value.__exit__ = Mock()

# Service mocking
@patch('service.external_api_call')  
def test_external_dependency(self, mock_api):
    mock_api.return_value = {"data": "test"}
```

## Coverage Goals

### Minimum Requirements
- **Unit Tests**: 90% code coverage
- **Integration Tests**: 100% endpoint coverage  
- **E2E Tests**: 100% critical path coverage
- **Security Tests**: 100% authentication path coverage

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=agenthub_main/src --cov-report=html

# View coverage report  
open htmlcov/index.html

# Terminal coverage report
pytest --cov=agenthub_main/src --cov-report=term-missing
```

## Common Patterns

### Testing API Endpoints
```python
@patch('controller.get_current_user_id')
def test_api_endpoint(self, mock_user_id):
    """Test API endpoint with authentication.""" 
    mock_user_id.return_value = "user-123"
    
    response = client.post("/api/endpoint", json={"data": "test"})
    
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### Testing Database Operations  
```python
@patch('repository.get_db_session')
@patch('repository.get_current_user_id')
def test_database_create(self, mock_user_id, mock_session):
    """Test database create operation."""
    mock_user_id.return_value = "user-123"
    mock_db = Mock()
    mock_session.return_value.__enter__.return_value = mock_db
    
    result = repository.create(entity_data)
    
    assert result.success is True
    mock_db.add.assert_called_once()
```

### Testing Error Conditions
```python  
def test_invalid_input_raises_validation_error(self):
    """Test invalid input raises validation error."""
    invalid_data = {"invalid": "data"}
    
    with pytest.raises(ValidationError) as exc_info:
        service.validate_input(invalid_data)
    
    assert "invalid" in str(exc_info.value)
```

## Migration from Legacy Tests

### Update Authentication
```python
# OLD (pre-2025-08-25)
def test_operation(self):
    result = service.operation(user_id="default")

# NEW (post-2025-08-25)  
@patch('service.get_current_user_id')
def test_operation(self, mock_user_id):
    mock_user_id.return_value = "test-user"
    result = service.operation()
```

### Update Imports
```python
# OLD
from domain.value_objects.task_status import TaskStatus

# NEW
from domain.value_objects.status import Status  
```

### Add Error Testing
```python
# Add these tests for all operations
def test_operation_requires_authentication(self):
    """Test operation requires authentication."""
    with pytest.raises(UserAuthenticationRequiredError):
        service.operation()
```

## Related Documentation

- [Test Modernization Guide](test-modernization-guide.md) - Comprehensive modernization guide
- [E2E Testing Guidelines](e2e/End_to_End_Testing_Guidelines.md) - End-to-end testing best practices
- [Authentication System Architecture](../CORE ARCHITECTURE/authentication-system.md) - Authentication system details

---

*Last Updated: 2025-09-08 - Created comprehensive testing guide with authentication requirements*