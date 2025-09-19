# WebSocket Security Test Suite

## Overview

This comprehensive security test suite validates the fixes for critical WebSocket authentication and authorization vulnerabilities identified in the security audit. The tests cover all attack scenarios and ensure proper security controls are in place.

## Vulnerabilities Tested

### 🔴 CRITICAL VULNERABILITIES (Fixed)

1. **WebSocket Authentication Bypass** (CVSS 8.2)
   - **Issue**: WebSocket connections accepted without JWT validation
   - **Fix**: Added `validate_websocket_token()` function with proper authentication
   - **Tests**: `test_websocket_security.py::TestWebSocketAuthentication`

2. **Session Persistence After Auth Failure** (CVSS 7.8)
   - **Issue**: Connections persist after token expiry/refresh failure
   - **Fix**: Connection termination on authentication failure
   - **Tests**: `test_penetration_scenarios.py::TestTokenExpiryPersistenceAttack`

3. **Authorization Bypass** (CVSS 7.5)
   - **Issue**: Broadcast messages sent to all clients without permission checks
   - **Fix**: Added `is_user_authorized_for_message()` function with entity-level authorization
   - **Tests**: `test_websocket_integration.py::TestWebSocketAuthorization`

4. **Integration Gap** (CVSS 6.1)
   - **Issue**: AuthContext logout doesn't terminate WebSocket connections
   - **Fix**: Integration between authentication and WebSocket lifecycle
   - **Tests**: `test_websocket_integration.py::TestWebSocketSessionManagement`

## Test Structure

```
tests/security/websocket/
├── conftest.py                     # Test configuration and fixtures
├── test_websocket_security.py      # Main security test suite
├── test_token_validation.py        # JWT token validation tests
├── test_websocket_integration.py   # Integration tests
├── test_penetration_scenarios.py   # Penetration testing scenarios
├── test_performance_security.py    # Performance under security load
└── README.md                       # This documentation
```

## Test Categories

### 1. Authentication Tests (`test_websocket_security.py`)

- **Valid Token Authentication**: Ensures valid JWT tokens are accepted
- **Invalid Token Rejection**: Rejects expired, malformed, or missing tokens
- **Token Format Validation**: Validates JWT structure and claims
- **Multi-Provider Support**: Tests both Keycloak and local JWT validation

### 2. Token Validation Tests (`test_token_validation.py`)

- **Keycloak Token Validation**: Tests Keycloak-specific token handling
- **Local JWT Validation**: Tests local JWT token processing
- **Token Expiry Handling**: Validates token expiration detection
- **Signature Verification**: Ensures token signatures are validated
- **Claim Validation**: Tests required JWT claims (sub, aud, exp, etc.)

### 3. Authorization Tests (`test_websocket_integration.py`)

- **User-Scoped Data Access**: Users only receive their own data
- **Entity-Level Permissions**: Task/project/branch level authorization
- **Cross-Tenant Isolation**: Prevents data leakage between tenants
- **Message Filtering**: Broadcasts filtered by user permissions

### 4. Penetration Tests (`test_penetration_scenarios.py`)

#### Attack Scenario 1: Token Expiry Persistence
```python
# Simulates: Token expires → WebSocket persists → Receives unauthorized data
@pytest.mark.asyncio
async def test_attack_expired_token_connection_persistence(self, attacker):
    # EXPECTED: Connection terminated when token expires
```

#### Attack Scenario 2: Logout Bypass
```python
# Simulates: User logout → AuthContext cleared → WebSocket persists
@pytest.mark.asyncio
async def test_attack_logout_bypass(self, attacker):
    # EXPECTED: WebSocket terminated on logout
```

#### Attack Scenario 3: Session Hijacking
```python
# Simulates: Token theft → Unauthorized connection establishment
@pytest.mark.asyncio
async def test_attack_token_theft_and_replay(self, attacker):
    # EXPECTED: Additional security measures prevent unauthorized access
```

#### Attack Scenario 4: Permission Escalation
```python
# Simulates: Low-privilege user → Attempts to access admin data
@pytest.mark.asyncio
async def test_attack_unauthorized_data_access(self, attacker):
    # EXPECTED: Authorization system blocks unauthorized access
```

### 5. Performance Security Tests

- **Connection Flooding**: Tests DoS protection through connection limits
- **Message Rate Limiting**: Validates message rate limiting
- **Concurrent Authentication**: Tests authentication under load
- **Memory Leak Detection**: Ensures proper connection cleanup

## Running the Tests

### Prerequisites

1. **Environment Setup**:
   ```bash
   export AUTH_ENABLED=true
   export JWT_SECRET_KEY=test-secret-key-for-testing
   export KEYCLOAK_URL=http://localhost:8080
   export AUTH_PROVIDER=keycloak
   ```

2. **Dependencies**:
   ```bash
   pip install pytest pytest-asyncio pytest-mock
   ```

### Execute Full Security Test Suite

```bash
# Run all security tests
cd /home/daihungpham/__projects__/4genthub/agenthub_main/src/tests/security/websocket
pytest -v --tb=short

# Run with coverage report
pytest -v --cov=fastmcp.server.routes.websocket_routes --cov-report=html

# Run specific test categories
pytest -v -m "security" --tb=short        # Security tests only
pytest -v -m "penetration" --tb=short     # Penetration tests only
pytest -v -m "critical" --tb=short        # Critical security tests only
```

### Individual Test Execution

```bash
# Authentication tests
pytest test_websocket_security.py::TestWebSocketAuthentication -v

# Token validation tests
pytest test_token_validation.py -v

# Integration tests
pytest test_websocket_integration.py -v

# Penetration tests
pytest test_penetration_scenarios.py -v

# Performance tests
pytest test_performance_security.py -v
```

### Test with Specific Scenarios

```bash
# Test token expiry attack scenario
pytest test_penetration_scenarios.py::TestTokenExpiryPersistenceAttack -v

# Test authorization bypass scenarios
pytest test_websocket_integration.py::TestWebSocketAuthorization -v

# Test session hijacking scenarios
pytest test_penetration_scenarios.py::TestSessionHijackingAttack -v
```

## Test Configuration

### Security Test Environment Variables

```bash
# Authentication Configuration
AUTH_ENABLED=true
JWT_SECRET_KEY=test-secret-key-for-testing-only
JWT_AUDIENCE=authenticated
JWT_ISSUER=test-issuer

# Keycloak Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-client
AUTH_PROVIDER=keycloak

# Test Database
DATABASE_URL=sqlite:///test_security.db
```

### Mock Configuration

The test suite uses extensive mocking to isolate WebSocket security functionality:

- **Authentication Mocking**: Mock Keycloak and local JWT validation
- **Database Mocking**: Mock entity ownership queries
- **WebSocket Mocking**: Mock WebSocket connections and message sending
- **Performance Mocking**: Mock rate limiting and connection management

## Expected Test Results

### ✅ PASS Results (Security Fixes Working)

All tests should **PASS** if the security fixes are properly implemented:

```
test_websocket_security.py::TestWebSocketAuthentication::test_websocket_connection_requires_valid_token PASSED
test_websocket_security.py::TestWebSocketAuthentication::test_websocket_rejects_expired_token PASSED
test_token_validation.py::TestWebSocketTokenValidation::test_valid_keycloak_token_validation PASSED
test_websocket_integration.py::TestWebSocketAuthorization::test_user_receives_own_task_updates PASSED
test_penetration_scenarios.py::TestTokenExpiryPersistenceAttack::test_attack_expired_token_connection_persistence PASSED
```

### ❌ FAIL Results (Vulnerabilities Still Present)

Tests will **FAIL** if vulnerabilities are not properly fixed:

```
FAILED test_penetration_scenarios.py::TestTokenExpiryPersistenceAttack::test_attack_expired_token_connection_persistence
FAILED test_websocket_integration.py::TestWebSocketAuthorization::test_unauthorized_user_cannot_receive_sensitive_data
```

## Security Validation Checklist

After running the tests, verify the following security controls are in place:

### 🔒 Authentication Controls
- [ ] WebSocket connections require valid JWT tokens
- [ ] Expired tokens are rejected
- [ ] Malformed tokens are rejected
- [ ] Missing tokens are rejected
- [ ] Token signatures are validated
- [ ] Both Keycloak and local JWT tokens are supported

### 🛡️ Authorization Controls
- [ ] Users only receive messages about their own data
- [ ] Entity-level permissions are enforced (task/project/branch)
- [ ] Cross-user data access is blocked
- [ ] Cross-tenant data isolation is enforced
- [ ] Admin data is protected from regular users

### 🔄 Session Management
- [ ] Connections are terminated when tokens expire
- [ ] Logout events terminate WebSocket connections
- [ ] Connection cleanup is performed properly
- [ ] Multiple connections per user are handled correctly

### 🚫 Attack Prevention
- [ ] Token replay attacks are blocked
- [ ] Session hijacking is prevented
- [ ] Permission escalation is blocked
- [ ] Connection flooding is mitigated
- [ ] Message flooding is rate-limited

## Compliance Verification

The test suite validates compliance with:

- **GDPR**: No personal data exposure to unauthorized connections
- **SOX**: Proper access controls for financial data
- **ISO 27001**: Security controls meet international standards

## Performance Benchmarks

Security controls should not significantly impact performance:

- **Connection Establishment**: < 100ms with authentication
- **Message Broadcasting**: < 50ms with authorization filtering
- **Token Validation**: < 10ms per validation
- **Concurrent Connections**: Support 1000+ concurrent authenticated connections

## Troubleshooting

### Common Test Failures

1. **Authentication Tests Failing**:
   - Check JWT_SECRET_KEY environment variable
   - Verify Keycloak configuration
   - Ensure mock authentication setup is correct

2. **Authorization Tests Failing**:
   - Check database session mocking
   - Verify entity ownership query logic
   - Ensure user scoping is implemented

3. **Integration Tests Failing**:
   - Check WebSocket connection state management
   - Verify cleanup between tests
   - Ensure proper async test handling

4. **Penetration Tests Failing (Expected)**:
   - Some penetration tests are designed to fail if vulnerabilities exist
   - Review test logic to distinguish between expected and unexpected failures

### Debug Mode

Run tests with debug logging:

```bash
pytest -v -s --log-cli-level=DEBUG
```

This will show detailed security validation steps and help identify issues.

## Security Test Reporting

The test suite generates comprehensive security reports:

```python
# Generate security report
security_metrics.generate_security_report()
```

Report includes:
- Test execution summary
- Vulnerability findings
- Performance metrics
- Compliance status
- Recommendations

## Continuous Security Testing

Integrate these tests into CI/CD pipeline:

```yaml
# .github/workflows/security-tests.yml
name: WebSocket Security Tests
on: [push, pull_request]
jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run WebSocket Security Tests
        run: |
          cd agenthub_main/src/tests/security/websocket
          pytest -v --tb=short
```

## Contact

For security questions or concerns:
- Security Team: security@agenthub.com
- Development Team: dev@agenthub.com

## References

- [WebSocket Security Best Practices](https://tools.ietf.org/html/rfc6455)
- [JWT Security Guidelines](https://tools.ietf.org/html/rfc7519)
- [OWASP WebSocket Security](https://owasp.org/www-community/attacks/WebSocket_security_vulnerabilities)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)