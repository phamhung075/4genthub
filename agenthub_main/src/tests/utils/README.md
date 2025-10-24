# Test Infrastructure - Utilities and Fixtures

This directory contains comprehensive test infrastructure including fixtures, mocks, and test data builders to support authentication, database, and MCP protocol testing.

## Table of Contents

- [Overview](#overview)
- [Auth Token Builder](#auth-token-builder)
- [Test Data Builders](#test-data-builders)
- [Mock External Services](#mock-external-services)
- [MCP Message Fixtures](#mcp-message-fixtures)
- [Database Fixtures](#database-fixtures)
- [Best Practices](#best-practices)

## Overview

The test infrastructure provides:

1. **Auth Token Builder**: Generate JWT/Keycloak tokens with configurable properties
2. **Test Data Builders**: Builder pattern for creating test entities (User, Project, Task, Context)
3. **Mock Services**: Mock implementations of Keycloak, Redis, and SMTP
4. **MCP Message Fixtures**: Sample requests/responses for MCP protocol testing
5. **Database Fixtures**: Pre-populated test databases with proper isolation

## Auth Token Builder

Located in `auth_token_builder.py`. Generates JWT tokens for authentication testing.

### Basic Usage

```python
from tests.utils.auth_token_builder import AuthTokenBuilder

# Generate a basic valid token
token = AuthTokenBuilder().build()

# Generate an admin token
admin_token = (AuthTokenBuilder()
    .with_admin_role()
    .build())

# Generate an expired token
expired_token = (AuthTokenBuilder()
    .with_expired_token(hours_ago=2)
    .build())

# Generate an invalid token for security testing
invalid_token = AuthTokenBuilder.generate_invalid_token(reason="bad_signature")
```

### Available Methods

- `.with_user_id(user_id)`: Set user ID
- `.with_email(email)`: Set email address
- `.with_role(role)`: Add a role
- `.with_roles(roles)`: Set multiple roles
- `.with_admin_role()`: Add admin role and permissions
- `.with_permission(permission)`: Add a permission
- `.with_permissions(permissions)`: Set multiple permissions
- `.with_expired_token(hours_ago)`: Create expired token
- `.with_not_yet_valid_token(hours_future)`: Create token not yet valid
- `.build()`: Build and return signed JWT

### JWKS Support

```python
from tests.utils.auth_token_builder import MockKeycloakJWKS

# Get JWKS for token validation testing
jwks = MockKeycloakJWKS()
jwks_json = jwks.get_jwks()
```

## Test Data Builders

Located in `builders/` directory. Builder pattern for creating test data.

### User Builder

```python
from tests.utils.builders import UserBuilder

user = (UserBuilder()
    .with_email("admin@test.com")
    .with_admin_role()
    .with_email_verified(True)
    .build())
```

### Project Builder

```python
from tests.utils.builders import ProjectBuilder

project = (ProjectBuilder()
    .with_name("Test Project")
    .with_description("Project for testing")
    .with_status("active")
    .build())
```

### Task Builder

```python
from tests.utils.builders import TaskBuilder

task = (TaskBuilder()
    .with_title("Implement feature")
    .with_assignee("coding-agent")
    .with_priority("high")
    .with_progress(50)
    .build())
```

### Context Builder

```python
from tests.utils.builders import ContextBuilder

context = (ContextBuilder()
    .with_level("task")
    .with_objective("Test Objective", "Description")
    .with_progress(75)
    .build())
```

## Mock External Services

### Mock Keycloak

Located in `../mocks/keycloak_mock.py`.

```python
from tests.mocks import MockKeycloakServer, MockKeycloakClient

# Create and start mock server
server = MockKeycloakServer()
server.start()

# Add test user
server.add_user("test@example.com", "password123", roles=["user"])

# Use client to authenticate
client = MockKeycloakClient(server)
token = client.login("test@example.com", "password123")

# Validate token
assert client.validate_current_token()

# Cleanup
server.stop()
```

### Mock Redis

Located in `../mocks/redis_mock.py`.

```python
from tests.mocks import MockRedisClient

# Create mock Redis client
redis = MockRedisClient()

# Use like real Redis
redis.set("key", "value", ex=60)
assert redis.get("key") == "value"

# Supports common Redis operations
redis.incr("counter")
redis.hset("hash", "field", "value")
redis.expire("key", 30)

# Cleanup
redis.flushdb()
```

### Mock SMTP

Located in `../mocks/smtp_mock.py`.

```python
from tests.mocks import MockSMTPServer

# Create and start mock SMTP server
smtp = MockSMTPServer()
smtp.start()

# Get email capture
capture = smtp.get_capture()

# Send email (captured, not actually sent)
capture.send_email(
    "from@test.com",
    "to@test.com",
    "Test Subject",
    "Test Body"
)

# Verify emails in tests
emails = capture.get_sent_emails()
assert len(emails) == 1
assert emails[0]["subject"] == "Test Subject"

# Cleanup
smtp.stop()
```

## MCP Message Fixtures

Located in `../fixtures/mcp_message_fixtures.py`.

```python
from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures

# Get valid task creation request
request = MCPMessageFixtures.get_task_create_request()

# Get matching response
response = MCPMessageFixtures.get_task_create_response()

# Get request/response pair for integration tests
req, resp = MCPMessageFixtures.get_request_response_pair("task_create")

# Get invalid request for error testing
invalid = MCPMessageFixtures.get_invalid_request("missing_required")

# Get error response
error = MCPMessageFixtures.get_error_response("unauthorized")
```

### Available Message Types

**Task Management:**
- `get_task_create_request()`
- `get_task_update_request()`
- `get_task_complete_request()`
- `get_task_list_request()`

**Subtask Management:**
- `get_subtask_create_request()`
- `get_subtask_update_request()`

**Context Management:**
- `get_context_create_request()`
- `get_context_get_request()`
- `get_context_update_request()`

**Project/Branch Management:**
- `get_project_create_request()`
- `get_branch_create_request()`

**Invalid Messages:**
- `get_invalid_request(error_type)`
- `get_error_response(error_type)`

## Database Fixtures

Located in `../fixtures/database_fixtures.py`.

```python
def test_something(test_project_data):
    """Test with pre-created project and branch."""
    project_id = test_project_data['project_id']
    git_branch_id = test_project_data['git_branch_id']

    # Use in your test
    # ...


def test_with_valid_branch(valid_git_branch_id):
    """Test with a valid branch ID."""
    # Branch exists in database
    # ...
```

## Best Practices

### 1. Use Builders for Complex Test Data

```python
# Good: Use builder pattern
user = (UserBuilder()
    .with_email("test@example.com")
    .with_admin_role()
    .build())

# Avoid: Manual dictionary creation
user = {
    "email": "test@example.com",
    "roles": ["admin"],
    # ... many fields
}
```

### 2. Use Mock Services for Integration Tests

```python
def test_authentication_flow():
    # Use mock Keycloak instead of real server
    server = MockKeycloakServer()
    server.start()

    try:
        # Test authentication
        client = MockKeycloakClient(server)
        token = client.login("test@example.com", "password")
        assert token is not None
    finally:
        server.stop()
```

### 3. Use Fixtures for Common Test Data

```python
from tests.fixtures.mcp_message_fixtures import get_sample_task_request

def test_task_creation():
    # Use pre-built fixtures
    request = get_sample_task_request()
    # Modify as needed
    request["title"] = "Custom Title"
    # Test with request
```

### 4. Clean Up Resources

```python
def test_with_resources():
    server = MockKeycloakServer()
    server.start()

    try:
        # Test code
        pass
    finally:
        # Always cleanup
        server.stop()
```

### 5. Use Descriptive Test Data

```python
# Good: Descriptive test data
user = (UserBuilder()
    .with_email("admin_with_all_permissions@test.com")
    .with_admin_role()
    .build())

# Avoid: Generic test data
user = UserBuilder().build()
```

## Testing the Test Infrastructure

All utilities should have their own tests to ensure reliability.

```bash
# Run tests for test infrastructure
pytest agenthub_main/src/tests/utils/test_auth_token_builder.py
pytest agenthub_main/src/tests/mocks/test_keycloak_mock.py
pytest agenthub_main/src/tests/mocks/test_redis_mock.py
```

## Contributing

When adding new test utilities:

1. Follow the builder pattern for data creation
2. Include comprehensive docstrings with usage examples
3. Write tests for your test utilities
4. Update this README with usage examples
5. Ensure thread-safety for parallel test execution

## References

- [Builder Pattern](https://refactoring.guru/design-patterns/builder)
- [Test Data Builders](https://www.martinfowler.com/bliki/ObjectMother.html)
- [JWT Testing Best Practices](https://jwt.io/)
- [Strategic Test Plan](../../ai_docs/testing-qa/strategic-test-plan-2025-10-24.md)
