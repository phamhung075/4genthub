# DhafnckMCP Test Suite

## Test Organization

The test suite is organized following best practices for Python testing with clear separation of concerns:

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── domain/             # Domain entity tests
│   ├── services/           # Service layer tests
│   └── test_mock_repository_completeness.py  # Mock validation
│
├── integration/            # Integration tests
│   ├── test_tool_registration.py
│   ├── test_task_completion_*.py
│   └── test_context_*.py
│
├── e2e/                    # End-to-end tests
│   └── test_full_workflow.py
│
├── fixtures/               # Test fixtures and mocks
│   ├── mocks/             # Mock implementations
│   │   ├── repositories/  # Mock repositories
│   │   │   ├── mock_repository_factory.py
│   │   │   └── mock_task_context_repository.py
│   │   └── services/      # Mock services
│   │       └── mock_unified_context_service.py
│   └── data/              # Test data fixtures
│
├── utilities/              # Test utilities and helpers
│   ├── test_layer_by_layer_diagnostic.py  # Diagnostic tool
│   ├── docker_test_utils.py
│   └── mcp_client_utils.py
│
├── core/                   # Core functionality tests
├── infrastructure/         # Infrastructure layer tests
└── task_management/        # Task management specific tests
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/
```

### Run Diagnostic Tests
```bash
# Run layer-by-layer diagnostic
python tests/utilities/test_layer_by_layer_diagnostic.py

# Test mock completeness
pytest tests/unit/test_mock_repository_completeness.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src/fastmcp --cov-report=html
```

## Mock Implementations

Mock implementations are located in `tests/fixtures/mocks/` and are used when:
1. Database is not available
2. Running unit tests in isolation
3. Testing error conditions

### Using Mocks in Tests

```python
from tests.fixtures.mocks import (
    MockProjectRepository,
    MockTaskRepository,
    MockUnifiedContextService
)

# Create mock repository
mock_repo = MockProjectRepository()

# Use in tests
project = await mock_repo.find_by_id("test-id")
```

### Using Mocks in Production (Database Unavailable)

The production code can fall back to mocks when database is unavailable:

```python
try:
    from fastmcp.task_management.infrastructure.database.database_config import get_db_config
    db_config = get_db_config()
    # Use real repository
except Exception:
    from tests.fixtures.mocks import MockProjectRepository
    # Use mock repository
```

## Diagnostic Tools

### Layer-by-Layer Diagnostic

The diagnostic tool tests each architectural layer independently:

```python
from tests.utilities import run_diagnostic

# Run full diagnostic
success, results, failure_point = run_diagnostic()

# Test individual layers
from tests.utilities import (
    test_domain_layer,
    test_infrastructure_repositories,
    test_application_facades,
    test_interface_controllers
)

# Test specific layer
success, result = test_domain_layer()
```

### Mock Completeness Testing

Ensures all mock implementations have required methods:

```bash
pytest tests/unit/test_mock_repository_completeness.py -v
```

This test automatically:
1. Checks all abstract methods are implemented
2. Verifies method signatures match interfaces
3. Tests basic CRUD operations work
4. Validates return types are correct

## Test Data

Test data fixtures are located in `tests/fixtures/data/`:
- `sample_projects.json` - Sample project data
- `sample_tasks.json` - Sample task data
- `sample_contexts.json` - Sample context hierarchies

## Writing New Tests

### Unit Test Template
```python
import pytest
from tests.fixtures.mocks import MockProjectRepository

class TestProjectService:
    def setup_method(self):
        """Setup before each test"""
        self.repository = MockProjectRepository()
        
    def test_create_project(self):
        """Test project creation"""
        # Arrange
        project_data = {...}
        
        # Act
        result = self.service.create_project(project_data)
        
        # Assert
        assert result is not None
        assert result.name == project_data['name']
```

### Integration Test Template
```python
import pytest
from tests.utilities import setup_test_environment

@pytest.mark.integration
class TestTaskWorkflow:
    def setup_method(self):
        """Setup test environment"""
        self.env = setup_test_environment()
        
    def test_complete_workflow(self):
        """Test complete task workflow"""
        # Create project
        project = self.env.create_project(...)
        
        # Create task
        task = self.env.create_task(...)
        
        # Complete task
        result = self.env.complete_task(task.id)
        
        # Verify
        assert result.status == 'completed'
```

## CI/CD Integration

Tests are automatically run in CI/CD pipeline:
1. Unit tests run on every commit
2. Integration tests run on PR creation
3. E2E tests run before deployment

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes src directory
   ```bash
   export PYTHONPATH=/path/to/dhafnck_mcp_main/src:$PYTHONPATH
   ```

2. **Mock Not Found**: Check fixtures are properly installed
   ```bash
   ls tests/fixtures/mocks/
   ```

3. **Database Connection**: Set DATABASE_TYPE for testing
   ```bash
   export DATABASE_TYPE=mock
   ```

### Debug Mode

Run tests with verbose output:
```bash
pytest tests/ -vvs --log-cli-level=DEBUG
```

## Contributing

When adding new tests:
1. Place in appropriate category (unit/integration/e2e)
2. Use mocks for external dependencies
3. Add docstrings explaining test purpose
4. Ensure tests are idempotent
5. Update this README if adding new test categories

## Related Documentation

- [Architecture Overview](../ai_docs/architecture-design/architecture.md)
- [Testing Guide](../ai_docs/testing/testing.md)
- [Mock Implementation Guide](../ai_docs/fixes/DATABASE_UNAVAILABLE_MOCK_IMPLEMENTATION_FIX.md)
- [Troubleshooting Guide](../ai_docs/troubleshooting/index.md)