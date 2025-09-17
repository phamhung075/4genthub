# Keycloak Service Account Setup Guide

## Overview

This guide covers the complete setup and configuration of Keycloak service accounts for MCP hooks authentication. Service accounts enable automated processes and hooks to authenticate with the MCP system without user interaction.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Service Account Configuration](#service-account-configuration)
- [Environment Setup](#environment-setup)
- [Implementation Details](#implementation-details)
- [Security Considerations](#security-considerations)
- [Testing and Validation](#testing-and-validation)
- [Troubleshooting](#troubleshooting)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

1. **Keycloak Instance**: Running Keycloak server with admin access
2. **Realm**: Configured MCP realm (`4genthub`)
3. **Network Access**: Connectivity between MCP application and Keycloak
4. **SSL Certificate**: Valid SSL certificate for production use

## Service Account Configuration

### Step 1: Create Service Account Client

1. Log into Keycloak Admin Console
2. Navigate to your realm (`4genthub`)
3. Go to **Clients** → **Create Client**
4. Configure client settings:
   ```
   Client Type: OpenID Connect
   Client ID: mcp-service-account
   Name: MCP Service Account
   Description: Service account for MCP hooks and automated processes
   ```

### Step 2: Configure Client Authentication

1. In the **Settings** tab:
   ```
   Client authentication: ON (confidential client)
   Authorization: OFF (not needed for service accounts)
   Authentication flow:
     - Standard flow: OFF
     - Implicit flow: OFF  
     - Direct access grants: OFF
     - Service accounts roles: ON
   ```

2. **Save** the configuration

### Step 3: Generate Client Secret

1. Navigate to **Credentials** tab
2. Client secret is automatically generated
3. **Copy** the client secret (you'll need this for configuration)
4. Store securely - this is the only time you'll see the full secret

### Step 4: Configure Service Account Roles

1. Go to **Service account roles** tab
2. Click **Assign role**
3. Add required roles:
   ```
   Realm roles:
   - mcp-admin (for full access)
   - mcp-tools (for tool execution)
   - mcp-user (for basic access)
   ```

### Step 5: Create Custom Client Scopes (Optional)

1. Navigate to **Client scopes**
2. Create new scopes:
   ```
   mcp:read - Read access to MCP resources
   mcp:write - Write access to MCP resources
   mcp:execute - Execute MCP tools and operations
   mcp:admin - Administrative operations
   ```

3. Assign scopes to service account client:
   - **Default client scopes**: `openid`, `profile`, `email`, `mcp:read`
   - **Optional client scopes**: `mcp:write`, `mcp:execute`, `mcp:admin`

## Environment Setup

### Configuration Files

The service account uses environment variables for configuration. Add these to your `.env` file:

```bash
# Keycloak Configuration
KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=4genthub

# Service Account Configuration
KEYCLOAK_SERVICE_CLIENT_ID=mcp-service-account
KEYCLOAK_SERVICE_CLIENT_SECRET=your-generated-client-secret
KEYCLOAK_SERVICE_SCOPES=openid profile email mcp:read mcp:write

# Authentication Settings
AUTH_ENABLED=true
TOKEN_CACHE_TTL=300
PUBLIC_KEY_CACHE_TTL=3600
SSL_VERIFY=true
```

### Sample Configuration

Reference the sample configuration file at:
```
4genthub_main/config/keycloak_service_account.sample
```

## Implementation Details

### Service Account Authentication Module

The service account functionality is implemented in:
```
4genthub_main/src/fastmcp/auth/service_account.py
```

Key components:

1. **ServiceAccountConfig**: Configuration data class
2. **ServiceToken**: Token management with expiry tracking
3. **ServiceAccountAuth**: Main authentication class with:
   - Automatic token refresh
   - Rate limiting
   - Connection pooling
   - Health checking

### Usage Examples

#### Basic Authentication

```python
from fastmcp.auth.service_account import ServiceAccountAuth

# Initialize service account
auth = ServiceAccountAuth()

# Authenticate and get token
token = await auth.authenticate()
if token:
    print(f"Authenticated! Token expires in {token.seconds_until_expiry}s")
```

#### Context Manager Usage

```python
async with ServiceAccountAuth() as auth:
    token = await auth.get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Use headers for authenticated requests
```

#### Singleton Pattern

```python
from fastmcp.auth.service_account import get_service_account_auth

# Get singleton instance
auth = get_service_account_auth()
token = await auth.get_valid_token()
```

### Integration with MCP Controllers

Service account authentication integrates with MCP tools through the authentication middleware. The service account token provides full access to MCP operations without user interaction.

## Security Considerations

### Client Secret Security

1. **Storage**: Store client secrets in secure environment variables only
2. **Access**: Limit access to secrets to necessary personnel and systems
3. **Rotation**: Rotate client secrets monthly in production
4. **Monitoring**: Monitor for unauthorized access attempts

### Network Security

1. **HTTPS Only**: Always use HTTPS for Keycloak communication
2. **Certificate Validation**: Enable SSL certificate verification
3. **Network Isolation**: Restrict network access to Keycloak endpoints
4. **Firewall Rules**: Configure appropriate firewall rules

### Token Security

1. **Short Expiry**: Use reasonable token expiry times (5-15 minutes)
2. **Automatic Refresh**: Implement automatic token refresh before expiry
3. **Secure Storage**: Never store tokens in logs or persistent storage
4. **Transmission**: Only transmit tokens over secure channels

### Audit and Logging

1. **Authentication Events**: Log all authentication attempts
2. **Failed Logins**: Monitor and alert on authentication failures
3. **Token Usage**: Track service account token usage patterns
4. **Access Patterns**: Monitor for unusual access patterns

## Testing and Validation

### Health Check Endpoint

Test service account health:

```python
auth = ServiceAccountAuth()
health = await auth.health_check()
print(json.dumps(health, indent=2))
```

Expected healthy response:
```json
{
  "service_account_configured": true,
  "token_available": true,
  "token_valid": true,
  "token_expires_in": 250,
  "keycloak_reachable": true,
  "last_auth_success": "2025-09-11T16:30:00.000Z",
  "configuration": {
    "keycloak_url": "https://keycloak.example.com",
    "realm": "4genthub",
    "client_id": "mcp-service-account",
    "scopes": ["openid", "profile", "email", "mcp:read", "mcp:write"]
  }
}
```

### Manual Testing

1. **Configuration Test**: Verify environment variables are set
2. **Connectivity Test**: Test connection to Keycloak endpoints
3. **Authentication Test**: Perform service account authentication
4. **Token Validation Test**: Validate generated tokens
5. **Permission Test**: Verify service account has required roles

### Automated Testing

Run the test suite:

```bash
pytest 4genthub_main/src/tests/unit/auth/service_account_test.py -v
```

## Troubleshooting

### Common Issues

#### 1. Client Authentication Failed

**Symptoms**: `401 Unauthorized` responses during authentication

**Solutions**:
- Verify `KEYCLOAK_SERVICE_CLIENT_ID` matches Keycloak configuration
- Check `KEYCLOAK_SERVICE_CLIENT_SECRET` is correct and not truncated
- Ensure client has "Service accounts roles" enabled
- Verify client access type is "confidential"

#### 2. Insufficient Permissions

**Symptoms**: `403 Forbidden` responses when using authenticated requests

**Solutions**:
- Check service account role assignments in Keycloak
- Verify required scopes are assigned to the client
- Review client scope mappings
- Ensure realm roles include required permissions

#### 3. SSL Verification Failed

**Symptoms**: SSL/TLS connection errors

**Solutions**:
- Verify `KEYCLOAK_URL` uses HTTPS
- Check SSL certificate validity and chain
- Ensure certificate is trusted by the system
- Review `SSL_VERIFY` configuration

#### 4. Token Expiration Issues

**Symptoms**: Frequent token expiration errors

**Solutions**:
- Check system time synchronization
- Review `TOKEN_REFRESH_BUFFER` setting
- Monitor token lifetime settings in Keycloak
- Verify automatic refresh is working

#### 5. Connection Timeout

**Symptoms**: Connection timeout or refused errors

**Solutions**:
- Verify `KEYCLOAK_URL` is accessible from application server
- Check firewall and network configuration
- Ensure Keycloak service is running and healthy
- Review DNS resolution

### Debugging Steps

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.getLogger("fastmcp.auth.service_account").setLevel(logging.DEBUG)
   ```

2. **Test Connectivity**:
   ```bash
   curl -k https://your-keycloak-url/realms/4genthub/.well-known/openid-configuration
   ```

3. **Manual Token Request**:
   ```bash
   curl -X POST https://your-keycloak-url/realms/4genthub/protocol/openid-connect/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=mcp-service-account&client_secret=your-secret"
   ```

## Monitoring and Maintenance

### Key Metrics

Monitor these metrics for service account health:

1. **Authentication Success Rate**: Percentage of successful authentications
2. **Token Refresh Rate**: Frequency of token refresh operations
3. **Average Response Time**: Authentication request response times
4. **Error Rate**: Rate of authentication errors
5. **Certificate Expiry**: SSL certificate expiration monitoring

### Alerts

Set up alerts for:

- Authentication failure rate > 5%
- Token refresh failures
- SSL certificate expiry (30 days warning)
- Keycloak service downtime
- Unusual service account activity patterns
- High error rates or response times

### Maintenance Tasks

#### Monthly Tasks
- [ ] Rotate service account client secrets
- [ ] Review service account access logs
- [ ] Update SSL certificates if needed
- [ ] Review and update role assignments

#### Quarterly Tasks  
- [ ] Security review of service account configuration
- [ ] Performance analysis of authentication metrics
- [ ] Update documentation with any configuration changes
- [ ] Review and test disaster recovery procedures

#### Annual Tasks
- [ ] Complete security audit of authentication system
- [ ] Review and update security policies
- [ ] Performance optimization based on usage patterns
- [ ] Update and test backup/restore procedures

### Log Analysis

Important log entries to monitor:

```
✅ Service account authenticated successfully
⚠️  Token expired, refreshing...
❌ Service account authentication failed
🔒 SSL verification failed
🌐 Connection to Keycloak failed
```

Use log aggregation tools to:
- Track authentication patterns
- Identify security incidents
- Monitor performance trends
- Generate compliance reports

## Conclusion

The Keycloak service account setup provides secure, automated authentication for MCP hooks and processes. Following this guide ensures:

- ✅ Secure service account configuration
- ✅ Proper credential management
- ✅ Automatic token refresh
- ✅ Comprehensive monitoring
- ✅ Production-ready security

For additional support or questions, refer to the troubleshooting section or contact the development team.

## Related Documentation

- [Keycloak Authentication Integration](./keycloak-integration.md)
- [MCP Security Guidelines](../security/mcp-security-guidelines.md)
- [Environment Configuration](../setup-guides/environment-setup.md)
- [Monitoring and Alerting](../operations/monitoring-setup.md)