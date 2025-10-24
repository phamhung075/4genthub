"""Mock External Services for Test Infrastructure

This package provides mock implementations of external services for testing:
- Keycloak (authentication and authorization)
- Redis (caching)
- SMTP (email delivery)

These mocks allow tests to run without external dependencies while maintaining
realistic behavior for integration testing.
"""

from .keycloak_mock import MockKeycloakServer, MockKeycloakClient
from .redis_mock import MockRedisClient
from .smtp_mock import MockSMTPServer, MockEmailCapture

__all__ = [
    'MockKeycloakServer',
    'MockKeycloakClient',
    'MockRedisClient',
    'MockSMTPServer',
    'MockEmailCapture'
]
