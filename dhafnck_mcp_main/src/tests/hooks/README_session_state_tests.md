# Session and State Management Tests

## Overview

This directory contains comprehensive tests for the session tracking and state management systems used in the Claude hooks framework. These tests ensure proper functionality of the 2-hour session timeout management, agent role validation, state persistence, and integrated workflow operations.

**Part of subtask:** `a160a5a8-e058-4594-8521-1a14121d2b6c`

## Test Files

### Core Test Suites

1. **`test_session_tracker.py`** (20,282 bytes)
   - Tests for session tracking functionality
   - 2-hour session timeout management
   - File and folder modification tracking
   - Session persistence and recovery
   - Performance testing with large sessions

2. **`test_role_enforcer.py`** (30,617 bytes)
   - Tests for role-based tool permission enforcement
   - Agent role validation and tool restrictions
   - Dynamic tool permission checking
   - Path restrictions for write operations
   - Violation tracking and logging

3. **`test_agent_state_manager.py`** (21,060 bytes)
   - Tests for agent state management system
   - Session-aware agent tracking
   - Persistent state storage
   - State cleanup and maintenance

### Integration and Advanced Tests

4. **`test_session_state_integration.py`** (23,588 bytes)
   - Integration tests between session and state management
   - Cross-component data consistency
   - Session cleanup and state preservation
   - Performance under concurrent access
   - Complete workflow testing

5. **`test_state_persistence.py`** (22,300 bytes)
   - State persistence across application restarts
   - Data recovery after corruption or loss
   - Long-term session management
   - Memory vs disk state consistency
   - Backup and recovery procedures

### Test Infrastructure

6. **`test_session_state_runner.py`** (9,670 bytes)
   - Comprehensive test runner for all test suites
   - Environment setup and teardown
   - Test result reporting and summaries
   - Quick test mode for development

7. **`requirements-test.txt`** (664 bytes)
   - Test dependencies specification
   - Required packages for running the test suite

## Key Features Tested

### Session Tracking
- ✅ 2-hour session timeout management
- ✅ File modification tracking
- ✅ Folder modification tracking
- ✅ Session persistence across restarts
- ✅ Session cleanup and expiration
- ✅ Corrupted session file recovery
- ✅ Large session data handling
- ✅ Concurrent access simulation

### Role Enforcement
- ✅ Agent role validation
- ✅ Tool permission checking
- ✅ Dynamic tool restrictions
- ✅ Path-based write restrictions
- ✅ Violation logging and tracking
- ✅ Role configuration management
- ✅ Default role fallback
- ✅ Delegation suggestions

### State Management
- ✅ Session-aware agent tracking
- ✅ Persistent agent state storage
- ✅ State recovery after corruption
- ✅ Multi-session isolation
- ✅ State cleanup and maintenance
- ✅ Long-term state evolution

### Integration Testing
- ✅ Session tracking with role changes
- ✅ Role enforcement with session tracking
- ✅ State persistence across timeouts
- ✅ Error recovery and consistency
- ✅ Performance under load
- ✅ Complete workflow scenarios

## Running the Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Quick Test

Run a quick subset of tests for development:
```bash
python test_session_state_runner.py --quick
```

### Full Test Suite

Run all tests with comprehensive reporting:
```bash
python test_session_state_runner.py
```

### Specific Test Suites

Run individual test suites:
```bash
# Session tracking tests
python test_session_state_runner.py --suite session

# Role enforcement tests
python test_session_state_runner.py --suite role

# Integration tests
python test_session_state_runner.py --suite integration

# Persistence tests
python test_session_state_runner.py --suite persistence
```

### Individual Test Files

Run specific test files with pytest:
```bash
# Session tracker tests
pytest test_session_tracker.py -v

# Role enforcer tests
pytest test_role_enforcer.py -v

# Integration tests
pytest test_session_state_integration.py -v
```

## Test Structure

### Test Classes

Each test file contains multiple test classes organized by functionality:

- **TestSessionTracker**: Core session tracking functionality
- **TestRoleEnforcer**: Role-based permission enforcement
- **TestSessionStateIntegration**: Cross-component integration
- **TestStatePersistence**: Long-term persistence and recovery
- **TestPerformance**: Performance and scalability testing
- **TestErrorHandling**: Error conditions and recovery

### Test Fixtures

Tests use proper setup and teardown with:
- Temporary directories for test data
- Mocked environment functions
- Clean state between tests
- Resource cleanup after tests

### Test Coverage

The tests cover:
- **Happy path scenarios**: Normal operation flows
- **Error conditions**: Corruption, timeouts, failures
- **Edge cases**: Boundary conditions, large data
- **Performance**: Load testing and scalability
- **Integration**: Cross-component workflows

## Dependencies

### Required Modules
- `pytest>=7.0.0` - Core testing framework
- `freezegun>=1.2.0` - Time mocking for timeout testing
- `PyYAML>=6.0` - Role configuration testing

### Claude Hook Modules
- `session_tracker` - Session tracking functionality
- `role_enforcer` - Role-based permission enforcement
- `agent_state_manager` - Agent state management
- `env_loader` - Environment configuration

## Test Data

Tests use:
- **Temporary directories** for isolation
- **Mock data** for consistent testing
- **Time freezing** for timeout simulation
- **Large datasets** for performance testing

## Expected Results

All tests should pass when:
- Dependencies are properly installed
- Claude hook modules are available
- File system permissions allow temp files
- No conflicting processes interfere

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Python path includes `.claude/hooks/utils`
2. **Permission Errors**: Check write access to temp directories
3. **Timeout Failures**: May indicate performance issues
4. **Mock Failures**: Verify mock patches target correct functions

### Debug Mode

Run tests with verbose output:
```bash
python test_session_state_runner.py --verbose
```

### Dependency Check

Verify all dependencies are available:
```bash
python test_session_state_runner.py --check-deps
```

## Coverage Report

Generate test coverage report:
```bash
pytest --cov=session_tracker --cov=role_enforcer --cov=agent_state_manager test_*.py
```

## Performance Benchmarks

The tests include performance validation:
- Session operations should complete in < 1 second
- 1000 permission checks should complete in < 1 second
- Large session data (1000+ files) should load in < 2 seconds

## Future Enhancements

Potential test improvements:
- [ ] Stress testing with concurrent users
- [ ] Memory leak detection
- [ ] Network failure simulation
- [ ] Configuration hot reloading tests
- [ ] Migration testing between versions

## Contributing

When adding new tests:
1. Follow existing naming conventions
2. Include proper docstrings and comments
3. Add both positive and negative test cases
4. Include performance considerations
5. Update this README with new test descriptions

## Author

Created as part of the comprehensive Claude hooks testing initiative.
Test coverage for subtask: a160a5a8-e058-4594-8521-1a14121d2b6c