"""
WebSocket Security Test Configuration

Provides shared fixtures and configuration for WebSocket security tests.

FEATURES:
- Security test environment setup
- Mock authentication and authorization
- Test data generation
- Performance monitoring
- Attack simulation utilities
"""

import pytest
import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import jwt
import os

# Set up test environment
os.environ['AUTH_ENABLED'] = 'true'
os.environ['JWT_SECRET_KEY'] = 'websocket-security-test-secret-key'
os.environ['KEYCLOAK_URL'] = 'http://localhost:8080'
os.environ['AUTH_PROVIDER'] = 'keycloak'

from fastmcp.auth.domain.entities.user import User
from fastmcp.server.routes.websocket_routes import (
    active_connections,
    connection_subscriptions,
    connection_users
)

logger = logging.getLogger(__name__)


class SecurityTestConfig:
    """Configuration for security testing"""

    # Test secrets and keys
    TEST_JWT_SECRET = "websocket-security-test-secret-key"
    TEST_ALGORITHM = "HS256"

    # Test users
    LEGITIMATE_USER_ID = "legitimate_user_123"
    ADMIN_USER_ID = "admin_user_456"
    ATTACKER_USER_ID = "attacker_user_789"

    # Test tokens
    VALID_TOKEN_DURATION = 30  # minutes
    EXPIRED_TOKEN_DURATION = -30  # minutes (expired)

    # Security thresholds
    MAX_CONNECTIONS_PER_USER = 5
    MAX_MESSAGE_RATE = 100  # messages per second
    MAX_TOTAL_CONNECTIONS = 1000

    # Test data
    SENSITIVE_DATA = {
        "classified": "top_secret_data",
        "personal": "user_private_information",
        "financial": "payment_details"
    }


@pytest.fixture(scope="function")
def security_config():
    """Provide security test configuration"""
    return SecurityTestConfig()


@pytest.fixture(scope="function", autouse=True)
def cleanup_websocket_state():
    """Clean up WebSocket state before and after each test"""
    # Clean up before test
    active_connections.clear()
    connection_subscriptions.clear()
    connection_users.clear()

    yield

    # Clean up after test
    active_connections.clear()
    connection_subscriptions.clear()
    connection_users.clear()


@pytest.fixture
def mock_database_session():
    """Mock database session for testing authorization"""
    with patch('fastmcp.server.routes.websocket_routes.get_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_authentication():
    """Mock authentication functions for testing"""
    with patch('fastmcp.server.routes.websocket_routes.validate_keycloak_token') as mock_keycloak, \
         patch('fastmcp.server.routes.websocket_routes.validate_local_token') as mock_local:
        yield {
            'keycloak': mock_keycloak,
            'local': mock_local
        }


class TestUserFactory:
    """Factory for creating test users and tokens"""

    def __init__(self, config: SecurityTestConfig):
        self.config = config

    def create_user(self, user_id: str, email: str = None, role: str = "user") -> User:
        """Create a test user"""
        return User(
            id=user_id,
            email=email or f"{user_id}@test.com",
            username=user_id,
            role=role
        )

    def create_token(self, user_id: str, expires_in_minutes: int = None, **claims) -> str:
        """Create JWT token for testing"""
        if expires_in_minutes is None:
            expires_in_minutes = self.config.VALID_TOKEN_DURATION

        payload = {
            "sub": user_id,
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "aud": "authenticated",
            "iss": "test-issuer",
            "exp": datetime.now(timezone.utc).timestamp() + (expires_in_minutes * 60),
            "iat": datetime.now(timezone.utc).timestamp(),
            "role": "authenticated",
            **claims
        }
        return jwt.encode(payload, self.config.TEST_JWT_SECRET, algorithm=self.config.TEST_ALGORITHM)

    def create_admin_user(self) -> tuple[User, str]:
        """Create admin user and token"""
        user = self.create_user(self.config.ADMIN_USER_ID, role="admin")
        token = self.create_token(self.config.ADMIN_USER_ID, role="admin", admin=True)
        return user, token

    def create_legitimate_user(self) -> tuple[User, str]:
        """Create legitimate user and token"""
        user = self.create_user(self.config.LEGITIMATE_USER_ID)
        token = self.create_token(self.config.LEGITIMATE_USER_ID)
        return user, token

    def create_attacker_user(self) -> tuple[User, str]:
        """Create attacker user and token"""
        user = self.create_user(self.config.ATTACKER_USER_ID)
        token = self.create_token(self.config.ATTACKER_USER_ID)
        return user, token

    def create_expired_token(self, user_id: str) -> str:
        """Create expired token"""
        return self.create_token(user_id, expires_in_minutes=self.config.EXPIRED_TOKEN_DURATION)

    def create_malformed_token(self) -> str:
        """Create malformed token"""
        return "not.a.valid.jwt.token"


@pytest.fixture
def user_factory(security_config):
    """Provide user factory for tests"""
    return TestUserFactory(security_config)


class MockWebSocketFactory:
    """Factory for creating mock WebSocket connections"""

    @staticmethod
    def create_websocket(token: str = None, user_id: str = None) -> AsyncMock:
        """Create mock WebSocket connection"""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.receive_json = AsyncMock()
        mock_ws.close = AsyncMock()

        # Set up query params
        mock_ws.query_params = {}
        if token:
            mock_ws.query_params["token"] = token

        return mock_ws

    @staticmethod
    def setup_authenticated_connection(websocket: AsyncMock, user: User, client_id: str = None):
        """Set up authenticated WebSocket connection state"""
        if not client_id:
            client_id = f"{user.id}_test_conn"

        # Add to active connections
        active_connections[client_id] = {websocket}

        # Add subscription data
        connection_subscriptions[websocket] = {
            "client_id": client_id,
            "user_id": user.id,
            "user_email": user.email,
            "scope": "branch",
            "filters": {}
        }

        # Add user data
        connection_users[websocket] = user

        return client_id


@pytest.fixture
def websocket_factory():
    """Provide WebSocket factory for tests"""
    return MockWebSocketFactory()


class SecurityTestMetrics:
    """Collect and analyze security test metrics"""

    def __init__(self):
        self.test_results = []
        self.performance_metrics = []
        self.vulnerability_reports = []

    def record_test_result(self, test_name: str, passed: bool, duration: float, details: dict = None):
        """Record test execution result"""
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "duration": duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        })

    def record_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Record performance metric"""
        self.performance_metrics.append({
            "metric": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_vulnerability(self, vulnerability_type: str, severity: str, description: str, exploitable: bool):
        """Record vulnerability finding"""
        self.vulnerability_reports.append({
            "type": vulnerability_type,
            "severity": severity,
            "description": description,
            "exploitable": exploitable,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def generate_security_report(self) -> dict:
        """Generate comprehensive security test report"""
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        total_tests = len(self.test_results)

        critical_vulnerabilities = sum(1 for vuln in self.vulnerability_reports
                                     if vuln["severity"] == "critical" and vuln["exploitable"])

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "critical_vulnerabilities": critical_vulnerabilities
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "vulnerability_reports": self.vulnerability_reports,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


@pytest.fixture(scope="session")
def security_metrics():
    """Provide security metrics collector"""
    return SecurityTestMetrics()


@pytest.fixture(autouse=True)
def record_test_metrics(request, security_metrics):
    """Automatically record test metrics"""
    start_time = time.time()
    yield
    duration = time.time() - start_time

    # Record test result
    test_passed = not hasattr(request.node, 'rep_failed') or not request.node.rep_failed
    security_metrics.record_test_result(
        test_name=request.node.name,
        passed=test_passed,
        duration=duration
    )


# Performance testing utilities
class PerformanceTestUtils:
    """Utilities for performance testing"""

    @staticmethod
    async def measure_async_function(func, *args, **kwargs):
        """Measure execution time of async function"""
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration

    @staticmethod
    async def test_concurrent_load(func, concurrent_count: int, *args, **kwargs):
        """Test function under concurrent load"""
        start_time = time.time()

        tasks = [func(*args, **kwargs) for _ in range(concurrent_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start_time

        successful = sum(1 for result in results if not isinstance(result, Exception))
        failed = len(results) - successful

        return {
            "total_requests": len(results),
            "successful": successful,
            "failed": failed,
            "duration": duration,
            "requests_per_second": len(results) / duration if duration > 0 else 0,
            "errors": [str(result) for result in results if isinstance(result, Exception)]
        }


@pytest.fixture
def performance_utils():
    """Provide performance testing utilities"""
    return PerformanceTestUtils()


# Logging configuration for security tests
def configure_security_test_logging():
    """Configure logging for security tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set specific log levels for security testing
    logging.getLogger('fastmcp.server.routes.websocket_routes').setLevel(logging.DEBUG)
    logging.getLogger('fastmcp.auth').setLevel(logging.DEBUG)


# Configure logging when module is imported
configure_security_test_logging()


# Test markers for categorizing security tests
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "penetration: mark test as penetration test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "critical: mark test as critical security test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


# Test data generators
class TestDataGenerator:
    """Generate test data for security tests"""

    @staticmethod
    def generate_sensitive_task_data(user_id: str) -> dict:
        """Generate sensitive task data for testing"""
        return {
            "id": f"task_{user_id}_{int(time.time())}",
            "title": f"Confidential Task for {user_id}",
            "description": "This task contains sensitive information",
            "data": {
                "classification": "confidential",
                "owner": user_id,
                "sensitive_fields": ["ssn", "credit_card", "api_key"]
            }
        }

    @staticmethod
    def generate_attack_payloads() -> list:
        """Generate common attack payloads for testing"""
        return [
            {"type": "xss", "payload": "<script>alert('xss')</script>"},
            {"type": "sql_injection", "payload": "'; DROP TABLE users; --"},
            {"type": "command_injection", "payload": "; rm -rf /"},
            {"type": "path_traversal", "payload": "../../etc/passwd"},
            {"type": "json_injection", "payload": '{"admin": true}'},
        ]


@pytest.fixture
def test_data_generator():
    """Provide test data generator"""
    return TestDataGenerator()