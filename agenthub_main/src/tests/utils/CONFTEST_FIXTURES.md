# Global Fixtures for conftest.py

This document provides pytest fixture definitions to add to `conftest.py` for the new test infrastructure.

## How to Add These Fixtures

Add these fixtures to `/home/daihungpham/__projects__/4genthub/agenthub_main/src/tests/conftest.py` after the existing fixtures (around line 1400+).

## Fixtures to Add

```python
# =============================================
# TEST INFRASTRUCTURE FIXTURES (Added 2025-10-24)
# =============================================

@pytest.fixture
def auth_token_builder():
    """Provide AuthTokenBuilder for generating test tokens.

    Usage:
        def test_auth(auth_token_builder):
            token = auth_token_builder().with_admin_role().build()
            assert token is not None
    """
    from tests.utils.auth_token_builder import AuthTokenBuilder
    return AuthTokenBuilder


@pytest.fixture
def user_builder():
    """Provide UserBuilder for creating test users.

    Usage:
        def test_user(user_builder):
            user = user_builder().with_email("test@example.com").build()
            assert user["email"] == "test@example.com"
    """
    from tests.utils.builders import UserBuilder
    return UserBuilder


@pytest.fixture
def project_builder():
    """Provide ProjectBuilder for creating test projects.

    Usage:
        def test_project(project_builder):
            project = project_builder().with_name("Test").build()
            assert project["name"] == "Test"
    """
    from tests.utils.builders import ProjectBuilder
    return ProjectBuilder


@pytest.fixture
def task_builder():
    """Provide TaskBuilder for creating test tasks.

    Usage:
        def test_task(task_builder):
            task = task_builder().with_priority("high").build()
            assert task["priority"] == "high"
    """
    from tests.utils.builders import TaskBuilder
    return TaskBuilder


@pytest.fixture
def context_builder():
    """Provide ContextBuilder for creating test contexts.

    Usage:
        def test_context(context_builder):
            ctx = context_builder().with_progress(50).build()
            assert ctx["data"]["progress"]["completion_percentage"] == 50
    """
    from tests.utils.builders import ContextBuilder
    return ContextBuilder


@pytest.fixture
def mcp_message_fixtures():
    """Provide MCPMessageFixtures for protocol testing.

    Usage:
        def test_mcp(mcp_message_fixtures):
            request = mcp_message_fixtures.get_task_create_request()
            assert request["action"] == "create"
    """
    from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures
    return MCPMessageFixtures


@pytest.fixture
def mock_keycloak_server():
    """Provide a mock Keycloak server for auth testing.

    Usage:
        def test_auth(mock_keycloak_server):
            mock_keycloak_server.start()
            try:
                # Use server
                client = MockKeycloakClient(mock_keycloak_server)
                token = client.login("test@example.com", "password123")
                assert token is not None
            finally:
                mock_keycloak_server.stop()
    """
    from tests.mocks import MockKeycloakServer

    server = MockKeycloakServer()
    yield server

    # Cleanup
    if server._running:
        server.stop()


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client for caching tests.

    Usage:
        def test_cache(mock_redis):
            mock_redis.set("key", "value")
            assert mock_redis.get("key") == "value"
    """
    from tests.mocks import MockRedisClient

    redis = MockRedisClient()
    yield redis

    # Cleanup
    redis.flushdb()


@pytest.fixture
def mock_smtp_server():
    """Provide a mock SMTP server for email testing.

    Usage:
        def test_email(mock_smtp_server):
            mock_smtp_server.start()
            try:
                capture = mock_smtp_server.get_capture()
                capture.send_email("from@test.com", "to@test.com", "Subject", "Body")
                emails = capture.get_sent_emails()
                assert len(emails) == 1
            finally:
                mock_smtp_server.stop()
    """
    from tests.mocks import MockSMTPServer

    server = MockSMTPServer()
    yield server

    # Cleanup
    if server.is_running():
        server.stop()


# =============================================
# CONVENIENCE FIXTURES FOR QUICK TESTING
# =============================================

@pytest.fixture
def sample_user(user_builder):
    """Provide a pre-built sample user for quick testing.

    Usage:
        def test_with_user(sample_user):
            assert sample_user["email"] == "test@example.com"
    """
    return user_builder().build()


@pytest.fixture
def sample_admin_user(user_builder):
    """Provide a pre-built admin user for quick testing.

    Usage:
        def test_admin(sample_admin_user):
            assert "admin" in sample_admin_user["roles"]
    """
    return user_builder().with_admin_role().build()


@pytest.fixture
def sample_project(project_builder):
    """Provide a pre-built project for quick testing.

    Usage:
        def test_project(sample_project):
            assert sample_project["name"] == "Test Project"
    """
    return project_builder().build()


@pytest.fixture
def sample_task(task_builder):
    """Provide a pre-built task for quick testing.

    Usage:
        def test_task(sample_task):
            assert sample_task["status"] == "todo"
    """
    return task_builder().build()


@pytest.fixture
def sample_valid_token(auth_token_builder):
    """Provide a pre-built valid JWT token for quick testing.

    Usage:
        def test_auth(sample_valid_token):
            assert sample_valid_token is not None
            assert len(sample_valid_token) > 50
    """
    return auth_token_builder().build()


@pytest.fixture
def sample_admin_token(auth_token_builder):
    """Provide a pre-built admin JWT token for quick testing.

    Usage:
        def test_admin_auth(sample_admin_token):
            from tests.utils.auth_token_builder import AuthTokenBuilder
            payload = AuthTokenBuilder.decode_token(sample_admin_token)
            assert "admin" in payload["realm_access"]["roles"]
    """
    return auth_token_builder().with_admin_role().build()
```

## Usage Examples

After adding these fixtures to `conftest.py`, you can use them in any test file:

```python
# tests/test_example.py

def test_user_creation(user_builder):
    """Test creating a user with builder."""
    user = (user_builder()
        .with_email("john@example.com")
        .with_role("developer")
        .build())

    assert user["email"] == "john@example.com"
    assert "developer" in user["roles"]


def test_token_generation(auth_token_builder):
    """Test generating an auth token."""
    token = auth_token_builder().with_admin_role().build()

    # Decode and verify
    from tests.utils.auth_token_builder import AuthTokenBuilder
    payload = AuthTokenBuilder.decode_token(token)

    assert "admin" in payload["realm_access"]["roles"]


def test_keycloak_authentication(mock_keycloak_server):
    """Test authentication flow with mock Keycloak."""
    from tests.mocks import MockKeycloakClient

    mock_keycloak_server.start()

    try:
        client = MockKeycloakClient(mock_keycloak_server)
        token = client.login("test@example.com", "password123")

        assert token is not None
        assert client.validate_current_token()
    finally:
        mock_keycloak_server.stop()


def test_redis_caching(mock_redis):
    """Test caching with mock Redis."""
    # Set value with expiry
    mock_redis.set("session:123", "user_data", ex=60)

    # Verify
    assert mock_redis.get("session:123") == "user_data"
    assert mock_redis.ttl("session:123") > 0


def test_email_sending(mock_smtp_server):
    """Test email capture with mock SMTP."""
    mock_smtp_server.start()

    try:
        capture = mock_smtp_server.get_capture()
        capture.send_email(
            "no-reply@test.com",
            "user@test.com",
            "Welcome",
            "Welcome to our service!"
        )

        emails = capture.get_sent_emails()
        assert len(emails) == 1
        assert emails[0]["subject"] == "Welcome"
    finally:
        mock_smtp_server.stop()
```

## Integration Testing Pattern

For complex integration tests, combine multiple fixtures:

```python
def test_complete_auth_flow(
    mock_keycloak_server,
    mock_redis,
    user_builder
):
    """Test complete authentication flow with session caching."""
    from tests.mocks import MockKeycloakClient

    # Setup
    mock_keycloak_server.start()
    user = user_builder().with_email("test@example.com").build()

    try:
        # Authenticate
        client = MockKeycloakClient(mock_keycloak_server)
        token = client.login(user["email"], "password123")
        assert token is not None

        # Cache session
        mock_redis.set(f"session:{user['id']}", token, ex=3600)

        # Verify cached session
        cached_token = mock_redis.get(f"session:{user['id']}")
        assert cached_token == token

    finally:
        mock_keycloak_server.stop()
```

## Notes

1. All fixtures include automatic cleanup via `yield` statements
2. Builders return dictionaries, not ORM objects, for flexibility
3. Mock services start on demand and cleanup automatically
4. Use builder fixtures for parameterized test data
5. Use pre-built fixtures (sample_*) for quick simple tests
