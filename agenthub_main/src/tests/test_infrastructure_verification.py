"""Test Infrastructure Verification

This module verifies that all test infrastructure components are working correctly.
Run this test to ensure the test infrastructure is properly set up.

Run with: pytest agenthub_main/src/tests/test_infrastructure_verification.py -v
"""

import pytest


class TestAuthTokenBuilder:
    """Verify Auth Token Builder functionality."""

    def test_import_auth_token_builder(self):
        """Verify AuthTokenBuilder can be imported."""
        from tests.utils.auth_token_builder import AuthTokenBuilder
        assert AuthTokenBuilder is not None

    def test_create_basic_token(self):
        """Verify basic token generation."""
        from tests.utils.auth_token_builder import AuthTokenBuilder

        builder = AuthTokenBuilder()
        token = builder.build()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_admin_token(self):
        """Verify admin token generation."""
        from tests.utils.auth_token_builder import AuthTokenBuilder

        token = AuthTokenBuilder().with_admin_role().build()
        payload = AuthTokenBuilder.decode_token(token)

        assert "admin" in payload["realm_access"]["roles"]

    def test_create_expired_token(self):
        """Verify expired token generation."""
        from tests.utils.auth_token_builder import AuthTokenBuilder

        token = AuthTokenBuilder().with_expired_token(hours_ago=2).build()
        assert token is not None

    def test_generate_invalid_token(self):
        """Verify invalid token generation."""
        from tests.utils.auth_token_builder import AuthTokenBuilder

        invalid = AuthTokenBuilder.generate_invalid_token("bad_signature")
        assert invalid is not None


class TestTestDataBuilders:
    """Verify Test Data Builders functionality."""

    def test_import_user_builder(self):
        """Verify UserBuilder can be imported."""
        from tests.utils.builders import UserBuilder
        assert UserBuilder is not None

    def test_user_builder_basic(self):
        """Verify basic user creation."""
        from tests.utils.builders import UserBuilder

        user = UserBuilder().build()

        assert user["email"] == "test@example.com"
        assert "user" in user["roles"]

    def test_user_builder_with_admin(self):
        """Verify admin user creation."""
        from tests.utils.builders import UserBuilder

        user = UserBuilder().with_admin_role().build()

        assert "admin" in user["roles"]
        assert "mcp:*" in user["permissions"]

    def test_project_builder(self):
        """Verify project builder."""
        from tests.utils.builders import ProjectBuilder

        project = ProjectBuilder().with_name("Test Project").build()

        assert project["name"] == "Test Project"
        assert project["status"] == "active"

    def test_task_builder(self):
        """Verify task builder."""
        from tests.utils.builders import TaskBuilder

        task = (TaskBuilder()
            .with_title("Test Task")
            .with_priority("high")
            .with_progress(50)
            .build())

        assert task["title"] == "Test Task"
        assert task["priority"] == "high"
        assert task["progress_percentage"] == 50

    def test_context_builder(self):
        """Verify context builder."""
        from tests.utils.builders import ContextBuilder

        context = (ContextBuilder()
            .with_level("task")
            .with_progress(75)
            .build())

        assert context["level"] == "task"
        assert context["data"]["progress"]["completion_percentage"] == 75


class TestMockServices:
    """Verify Mock Services functionality."""

    def test_import_keycloak_mock(self):
        """Verify KeycloakMock can be imported."""
        from tests.mocks import MockKeycloakClient, MockKeycloakServer
        assert MockKeycloakServer is not None
        assert MockKeycloakClient is not None

    def test_keycloak_authentication(self):
        """Verify Keycloak mock authentication."""
        from tests.mocks import MockKeycloakClient, MockKeycloakServer

        server = MockKeycloakServer()
        server.start()

        try:
            client = MockKeycloakClient(server)
            token = client.login("test@example.com", "password123")

            assert token is not None
            assert client.validate_current_token()
        finally:
            server.stop()

    def test_redis_mock_basic_operations(self):
        """Verify Redis mock basic operations."""
        from tests.mocks import MockRedisClient

        redis = MockRedisClient()

        # Set and get
        redis.set("key", "value")
        assert redis.get("key") == "value"

        # Expiry
        redis.set("temp", "data", ex=60)
        assert redis.ttl("temp") > 0

        # Delete
        redis.delete("key")
        assert redis.get("key") is None

    def test_redis_mock_hash_operations(self):
        """Verify Redis mock hash operations."""
        from tests.mocks import MockRedisClient

        redis = MockRedisClient()

        redis.hset("user:1", "name", "John")
        redis.hset("user:1", "email", "john@test.com")

        assert redis.hget("user:1", "name") == "John"

        all_data = redis.hgetall("user:1")
        assert len(all_data) == 2

    def test_smtp_mock_email_capture(self):
        """Verify SMTP mock email capture."""
        from tests.mocks import MockSMTPServer

        smtp = MockSMTPServer()
        smtp.start()

        try:
            capture = smtp.get_capture()
            capture.send_email(
                "from@test.com",
                "to@test.com",
                "Test Subject",
                "Test Body"
            )

            emails = capture.get_sent_emails()
            assert len(emails) == 1
            assert emails[0]["subject"] == "Test Subject"
            assert emails[0]["from"] == "from@test.com"
        finally:
            smtp.stop()


class TestMCPMessageFixtures:
    """Verify MCP Message Fixtures functionality."""

    def test_import_mcp_fixtures(self):
        """Verify MCPMessageFixtures can be imported."""
        from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures
        assert MCPMessageFixtures is not None

    def test_task_create_request(self):
        """Verify task creation request fixture."""
        from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures

        request = MCPMessageFixtures.get_task_create_request()

        assert request["action"] == "create"
        assert "title" in request
        assert "assignees" in request

    def test_invalid_request_fixtures(self):
        """Verify invalid request fixtures."""
        from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures

        invalid = MCPMessageFixtures.get_invalid_request("missing_action")

        assert "action" not in invalid

    def test_request_response_pair(self):
        """Verify request/response pairs."""
        from tests.fixtures.mcp_message_fixtures import MCPMessageFixtures

        req, resp = MCPMessageFixtures.get_request_response_pair("task_create")

        assert req["action"] == "create"
        assert resp["success"] is True
        assert "task" in resp["data"]


class TestDocumentation:
    """Verify documentation exists."""

    def test_readme_exists(self):
        """Verify README.md exists."""
        from pathlib import Path

        readme_path = Path(__file__).parent / "utils" / "README.md"
        assert readme_path.exists(), "README.md should exist"

    def test_conftest_fixtures_doc_exists(self):
        """Verify CONFTEST_FIXTURES.md exists."""
        from pathlib import Path

        doc_path = Path(__file__).parent / "utils" / "CONFTEST_FIXTURES.md"
        assert doc_path.exists(), "CONFTEST_FIXTURES.md should exist"


def test_integration_all_components():
    """Integration test using multiple components together."""
    from tests.mocks import MockKeycloakClient, MockKeycloakServer, MockRedisClient
    from tests.utils.auth_token_builder import AuthTokenBuilder
    from tests.utils.builders import TaskBuilder, UserBuilder

    # Create test user
    user = UserBuilder().with_email("integration@test.com").build()

    # Generate token
    token = (AuthTokenBuilder()
        .with_user_id(user["id"])
        .with_email(user["email"])
        .build())

    # Mock authentication
    server = MockKeycloakServer()
    server.start()

    try:
        # Verify authentication
        client = MockKeycloakClient(server)
        auth_token = client.login("test@example.com", "password123")
        assert auth_token is not None

        # Cache session
        redis = MockRedisClient()
        redis.set(f"session:{user['id']}", token, ex=3600)
        cached = redis.get(f"session:{user['id']}")
        assert cached == token

        # Create task
        task = (TaskBuilder()
            .with_title("Integration Test Task")
            .with_assignee("coding-agent")
            .build())

        assert task["title"] == "Integration Test Task"

    finally:
        server.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
