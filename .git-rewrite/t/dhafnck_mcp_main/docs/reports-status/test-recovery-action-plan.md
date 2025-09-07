# Test Recovery Action Plan

## Immediate Actions Required (Day 1)

### 1. Fix Critical Import Errors

#### Issue: Module 'tests.fixtures.domain' Not Found
**File**: `src/tests/unit/test_mock_repository_completeness.py`
```python
# Current (broken):
from tests.fixtures.mocks.repositories import (...)

# Fix:
from fastmcp.task_management.infrastructure.mocks.repositories import (...)
```

#### Issue: Missing TaskApplicationFacadeFactory
**File**: `src/tests/integration/test_next_task_controller_fix.py`
```python
# Current (broken):
from fastmcp.task_management.application.factories.task_application_facade_factory import TaskApplicationFacadeFactory

# Fix:
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
```

#### Issue: Missing test_helpers Module
**File**: `src/tests/integration/test_task_label_persistence_fix.py`
```python
# Current (broken):
from fastmcp.task_management.infrastructure.database.test_helpers import (...)

# Fix: Create test_helpers.py or update import to correct location
```

### 2. Fix Database Configuration

#### Create Test Database Helper
**Location**: `src/fastmcp/task_management/infrastructure/database/test_helpers.py`
```python
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

@contextmanager
def get_test_db_session() -> Session:
    """Get a test database session with automatic cleanup."""
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_db_session():
    """Compatibility function for tests expecting get_db_session."""
    with get_test_db_session() as session:
        return session
```

### 3. Update Test Runner Script

**File**: `run_tests_fast.sh`
```bash
# Remove --no-cov flag
# OLD: pytest $TEST_PATH --no-cov -x --tb=short
# NEW:
pytest $TEST_PATH -x --tb=short
```

### 4. Fix PYTHONPATH Configuration

**Create**: `.env.test`
```bash
export PYTHONPATH=/home/daihungpham/agentic-project/dhafnck_mcp_main/src
export TEST_DATABASE_URL=sqlite:///./test.db
export MCP_TEST_MODE=true
```

## Day 2-3: Stabilization

### 1. Audit All Test Imports
- Run import checker script
- Fix all relative imports
- Standardize import paths

### 2. Create Test Fixtures Registry
```python
# src/tests/fixtures/__init__.py
from .database import test_db_session
from .mocks import MockRepositoryFactory
from .data import TestDataFactory

__all__ = [
    'test_db_session',
    'MockRepositoryFactory', 
    'TestDataFactory'
]
```

### 3. Implement Test Isolation
```python
# src/tests/conftest.py
import pytest
from fastmcp.task_management.infrastructure.database import Base, engine

@pytest.fixture(autouse=True)
def reset_db():
    """Reset database before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
```

## Week 2: Recovery

### 1. Fix All Deprecation Warnings
Update server initialization in all tests:
```python
# OLD
server = Server(log_level="INFO", debug=True)

# NEW
server = Server()
# Pass settings to run() method instead
```

### 2. Create Test Documentation
- Document all test categories
- Create test execution guide
- Document test data requirements

### 3. Setup CI Pipeline
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest src/tests/ --tb=short
```

## Testing Checklist

### Before Each Test Run
- [ ] Verify PYTHONPATH is set
- [ ] Check database configuration
- [ ] Ensure test isolation is enabled
- [ ] Verify all imports resolve

### After Fixing Issues
- [ ] Run unit tests successfully
- [ ] Run integration tests successfully
- [ ] Run E2E tests successfully
- [ ] Generate coverage report
- [ ] Update test documentation

## Test Execution Commands

### Recommended Workflow
```bash
# 1. Setup environment
source .env.test

# 2. Run specific test category
pytest src/tests/unit/ -v              # Unit tests only
pytest src/tests/integration/ -v       # Integration tests
pytest src/tests/e2e/ -v               # E2E tests

# 3. Run with coverage
pytest src/tests/ --cov=fastmcp --cov-report=html

# 4. Run failed tests only
pytest --lf

# 5. Run tests in parallel
pytest -n auto src/tests/
```

## Success Criteria

### Phase 1 Complete When:
- [ ] All import errors resolved
- [ ] Basic test execution working
- [ ] At least 50% of tests passing

### Phase 2 Complete When:
- [ ] Database tests working
- [ ] No deprecation warnings
- [ ] 80% of tests passing

### Phase 3 Complete When:
- [ ] All tests passing
- [ ] CI pipeline working
- [ ] Coverage > 80%

## Risk Mitigation

### High Risk Areas
1. **Database Migration**: Backup all data before changes
2. **Import Changes**: Test incrementally
3. **Configuration Updates**: Keep rollback plan

### Rollback Strategy
1. Git tag current state before changes
2. Create branch for test recovery work
3. Test all changes in isolation first

## Monitoring Progress

### Daily Metrics
- Tests fixed today: ___
- Tests remaining: ___
- Blockers identified: ___
- Blockers resolved: ___

### Weekly Goals
- Week 1: Basic execution restored
- Week 2: 50% tests passing
- Week 3: 80% tests passing
- Week 4: 100% tests passing + CI

## Support Resources

### Documentation
- pytest documentation: https://docs.pytest.org/
- SQLAlchemy testing: https://docs.sqlalchemy.org/testing
- Python testing best practices

### Team Contacts
- Test Lead: @test_orchestrator_agent
- Database Expert: @debugger_agent
- CI/CD Support: @devops_agent

---

*Plan Created: August 14, 2025*
*Target Completion: September 14, 2025*
*Status: In Progress*