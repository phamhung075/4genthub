# Test Organization Guide

## Overview

This guide describes the standardized test architecture and patterns for the agenthub project. It consolidates best practices and provides clear guidelines for writing maintainable, consistent tests.

## Test Architecture Structure

### Directory Organization

```
src/tests/
├── utils/                          # Centralized test utilities
│   ├── __init__.py                 # Main utilities exports
│   ├── database_utils.py           # Database testing utilities
│   ├── mcp_client_utils.py         # MCP protocol testing
│   ├── test_isolation_utils.py     # Test isolation & cleanup
│   ├── assertion_helpers.py        # Domain-specific assertions
│   ├── test_patterns.py           # Standardized test patterns
│   └── coverage_analysis.py       # Coverage analysis tools
├── unit/                          # Unit tests (isolated components)
├── integration/                   # Integration tests (multiple components)
├── e2e/                          # End-to-end tests (full workflows)
├── performance/                  # Performance and load tests
├── task_management/              # Domain-specific tests
├── fixtures/                     # Legacy fixtures (being migrated)
├── conftest.py                   # Global pytest configuration
└── README.md                     # Test documentation
```

### Test Categories

1. **Unit Tests** (`unit/`): Test individual components in isolation
2. **Integration Tests** (`integration/`): Test component interactions
3. **End-to-End Tests** (`e2e/`): Test complete user workflows
4. **Performance Tests** (`performance/`): Test performance characteristics
5. **Domain Tests** (`task_management/`): Domain-specific business logic tests

## Standardized Test Utilities

### Database Testing

Use the centralized database utilities for consistent test data:

```python
from tests.utils import create_test_project_data, TestDataBuilder, create_database_records

# Simple test data
def test_with_basic_data():
    test_data = create_test_project_data()
    create_database_records(test_data)
    # ... test logic ...
    cleanup_test_data(test_data)

# Custom test data with builder pattern
def test_with_custom_data():
    test_data = (TestDataBuilder()
                .with_project_name("Custom Project")
                .with_branch_name("feature-branch")
                .with_user_id("custom_user")
                .build())
    create_database_records(test_data)
    # ... test logic ...
    cleanup_test_data(test_data)
```

### MCP Tool Testing

Use standardized MCP tool testing patterns:

```python
from tests.utils import MCPToolTestPattern

def test_manage_task_tool():
    pattern = MCPToolTestPattern("manage_task")
    
    # Test successful call
    result = pattern.test_successful_call(
        manage_task,
        {"action": "list", "git_branch_id": "test-branch"}
    )
    
    # Test missing parameter
    pattern.test_missing_required_parameter(manage_task, "action")
    
    # Test invalid parameter
    pattern.test_invalid_parameter_value(
        manage_task,
        {"action": "list", "git_branch_id": "test-branch"},
        "action",
        "invalid_action"
    )
```

### Assertion Helpers

Use domain-specific assertion helpers:

```python
from tests.utils import (
    assert_task_structure,
    assert_context_inheritance,
    assert_domain_event_structure,
    assert_mcp_tool_response,
    assert_pagination_structure
)

def test_task_creation():
    result = create_task({"title": "Test Task"})
    
    # Validate MCP response structure
    assert_mcp_tool_response(result, expected_success=True)
    
    # Validate task data structure
    task_data = result["task"]
    assert_task_structure(task_data, required_fields=["id", "title", "status"])
    
    # Validate domain event
    event = result.get("event")
    if event:
        assert_domain_event_structure(event, "TaskCreated")
```

## Test Patterns

### Database Test Pattern

For tests that require database access:

```python
from tests.utils import DatabaseTestPattern

def test_with_database():
    db_pattern = DatabaseTestPattern(use_transaction_rollback=True)
    
    with db_pattern.database_test_context() as session:
        # Perform database operations
        # Transaction will be rolled back automatically
        pass
```

### Integration Test Pattern

For complex multi-step tests:

```python
from tests.utils import IntegrationTestPattern

def test_project_workflow():
    pattern = IntegrationTestPattern("project_workflow")
    
    # Add test steps
    pattern.add_test_step("create_project", lambda: create_project("Test"))
    pattern.add_test_step("create_branch", lambda: create_branch("main"))
    pattern.add_test_step("create_task", lambda: create_task("Task 1"))
    
    # Add cleanup
    pattern.add_cleanup_function(lambda: cleanup_test_data())
    
    # Execute test scenario
    results = pattern.execute_test_scenario()
    assert results["overall_success"]
```

### Performance Test Pattern

For performance-sensitive tests:

```python
from tests.utils import PerformanceTestPattern

def test_task_creation_performance():
    pattern = PerformanceTestPattern("task_creation", max_duration_seconds=0.1)
    
    with pattern.performance_monitoring() as monitor:
        # Perform operations to monitor
        create_task({"title": "Performance Test"})
        monitor.checkpoint("task_created")
        
        # Check memory usage
        monitor.check_memory_usage(max_memory_mb=50.0)
        
        # Results automatically validated against max_duration
```

## Test Fixtures and Marks

### Pytest Fixtures

Use standardized fixtures from `tests.utils`:

```python
import pytest
from tests.utils import test_project_data, valid_git_branch_id

def test_with_project_data(test_project_data):
    """Uses standardized test project data with automatic cleanup"""
    project_id = test_project_data.project_id
    branch_id = test_project_data.git_branch_id
    # ... test logic ...

def test_with_valid_branch(valid_git_branch_id):
    """Uses a valid git branch ID with automatic cleanup"""
    # ... test logic using valid_git_branch_id ...
```

### Pytest Marks

Use standardized marks for test categorization:

```python
import pytest

@pytest.mark.unit
def test_unit_functionality():
    """Unit test - isolated component testing"""
    pass

@pytest.mark.integration
def test_integration_workflow():
    """Integration test - multiple components"""
    pass

@pytest.mark.e2e
def test_end_to_end_workflow():
    """End-to-end test - complete user workflow"""
    pass

@pytest.mark.performance
def test_performance_characteristics():
    """Performance test - timing and resource usage"""
    pass

@pytest.mark.database
def test_database_operations():
    """Database test - requires database setup"""
    pass

@pytest.mark.mcp
def test_mcp_protocol():
    """MCP protocol test - tests MCP tool interactions"""
    pass
```

## Test Naming Conventions

### File Naming

- Unit tests: `test_<component_name>.py`
- Integration tests: `test_<feature_name>_integration.py`
- End-to-end tests: `test_<workflow_name>_e2e.py`
- Performance tests: `test_<feature_name>_performance.py`

### Function Naming

- Descriptive names: `test_create_task_with_valid_data()`
- Error cases: `test_create_task_with_missing_title_fails()`
- Edge cases: `test_create_task_with_empty_description_succeeds()`

### Class Naming

- Test classes: `TestTaskManagement`
- Test patterns: `TaskManagementTestPattern`

## Coverage Analysis

Use the coverage analysis tools to identify gaps:

```python
from tests.utils import CoverageAnalyzer

# Analyze coverage
analyzer = CoverageAnalyzer(project_root)
report = analyzer.analyze_coverage()

print(f"Coverage: {report.coverage_percentage:.1f}%")
print(f"Gaps found: {len(report.gaps)}")

# Generate detailed report
report_text = analyzer.generate_coverage_report()
print(report_text)
```

## Migration Guidelines

### From Legacy Fixtures

When migrating from legacy fixtures:

1. **Replace fixture imports**:
   ```python
   # Old
   from tests.fixtures.database_fixtures import test_project_data
   
   # New
   from tests.utils import test_project_data
   ```

2. **Use builder pattern for custom data**:
   ```python
   # Old
   def create_custom_project_data():
       # Custom implementation
       pass
   
   # New
   from tests.utils import TestDataBuilder
   test_data = TestDataBuilder().with_project_name("Custom").build()
   ```

3. **Standardize assertion patterns**:
   ```python
   # Old
   assert result["success"] == True
   assert "task" in result
   
   # New
   from tests.utils import assert_mcp_tool_response, assert_task_structure
   assert_mcp_tool_response(result, expected_success=True)
   assert_task_structure(result["task"])
   ```

### From Scattered Utilities

When consolidating utilities:

1. **Move utility functions** to appropriate modules in `tests/utils/`
2. **Update imports** to use centralized utilities
3. **Remove duplicate implementations**
4. **Add to `__all__` exports** in `tests/utils/__init__.py`

## Best Practices

### Test Organization

1. **Group related tests** in classes or modules
2. **Use descriptive names** that explain the test purpose
3. **Keep tests focused** on single behaviors
4. **Separate setup/teardown** using fixtures or patterns

### Test Data Management

1. **Use builders** for complex test data creation
2. **Ensure isolation** between tests
3. **Clean up resources** automatically
4. **Use meaningful test data** that aids debugging

### Error Testing

1. **Test both success and failure paths**
2. **Validate error messages** and status codes
3. **Test edge cases** and boundary conditions
4. **Use assertion helpers** for consistent validation

### Performance Testing

1. **Set realistic time limits** for performance tests
2. **Monitor memory usage** in addition to timing
3. **Use performance patterns** for consistency
4. **Document performance expectations**

## Tools and Commands

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest -m unit
pytest -m integration
pytest -m e2e

# With coverage
pytest --cov=src --cov-report=html

# Performance tests only
pytest -m performance -v
```

### Coverage Analysis

```bash
# Generate coverage report
python -m tests.utils.coverage_analysis . -o coverage_report.md

# View in browser
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Discovery

```bash
# List all tests
pytest --collect-only

# List tests by marker
pytest --collect-only -m unit
```

## Integration with CI/CD

### Test Stages

1. **Unit Tests**: Fast, isolated tests (< 5 minutes)
2. **Integration Tests**: Component interaction tests (< 15 minutes)
3. **End-to-End Tests**: Full workflow tests (< 30 minutes)
4. **Performance Tests**: Optional, on-demand or nightly

### Quality Gates

- Minimum 80% code coverage
- All tests must pass
- No deprecation warnings from our code
- Performance tests within acceptable limits

## Troubleshooting

### Common Issues

1. **Import errors**: Check `PYTHONPATH` and package structure
2. **Database errors**: Ensure test database is properly configured
3. **Fixture conflicts**: Use scoped fixtures appropriately
4. **Test isolation**: Verify cleanup is working correctly

### Debugging Tips

1. **Use verbose output**: `pytest -v`
2. **Print debugging**: Use `pytest -s` to see print statements
3. **Run single tests**: `pytest path/to/test.py::test_function`
4. **Use debugger**: `pytest --pdb` to drop into debugger on failure

## Contributing

When adding new tests:

1. **Follow the established patterns** in this guide
2. **Use centralized utilities** from `tests.utils`
3. **Add appropriate pytest marks**
4. **Include both success and failure scenarios**
5. **Update documentation** if adding new patterns

## Resources

- [Pytest Documentation](https://ai_docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://ai_docs.python-guide.org/writing/tests/)
- [agenthub Architecture Guide](../CORE ARCHITECTURE/system-architecture.md)