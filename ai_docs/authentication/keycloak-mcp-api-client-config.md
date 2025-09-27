# Keycloak MCP-API Client Configuration Guide

## Client Basic Settings

### General Settings
- **Client ID**: `mcp-api`
- **Name**: MCP Backend Services
- **Description**: Backend API services client
- **Always display in UI**: On

### Access Settings
- **Root URL**: `https://api.4genthub.com`
- **Home URL**: `https://api.4genthub.com`
- **Admin URL**: `https://api.4genthub.com`

### Valid Redirect URIs
```
http://localhost:8000/*
http://localhost:8000/auth/callback
http://localhost:8000/api/auth/callback
http://localhost:3800/*
https://api.4genthub.com/*
https://api.4genthub.com/auth/callback
https://api.4genthub.com/api/auth/callback
http://92.5.226.7:8000/*
https://92.5.226.7:8000/*
http://captain.4genthub.com/*
https://captain.4genthub.com/*
http://www.4genthub.com/*
https://www.4genthub.com/*
```

### Valid Post Logout Redirect URIs
```
http://localhost:8000
http://localhost:3800
https://api.4genthub.com
https://www.4genthub.com
```

### Web Origins (CORS)
```
http://localhost:8000
http://localhost:3800
https://api.4genthub.com
https://www.4genthub.com
http://92.5.226.7:8000
https://92.5.226.7:8000
```

## Capability Configuration

### Required Settings
- **Client authentication**: On ✓
- **Authorization**: On ✓

### Authentication Flows
- **Standard flow**: Enabled ✓
- **Direct access grants**: Enabled ✓
- **Implicit flow**: Disabled
- **Service accounts roles**: Enabled ✓
- **Standard Token Exchange**: Disabled
- **OAuth 2.0 Device Authorization Grant**: Disabled
- **OIDC CIBA Grant**: Disabled

### PKCE Method
- Not required for backend service (leave as "Choose...")

## Login Settings
- **Login theme**: Default (leave as "Choose...")
- **Consent required**: Off ✓
- **Display client on screen**: Off ✓
- **Consent screen text**: (leave empty)

## Logout Settings
- **Front channel logout**: On ✓
- **Front-channel logout URL**: (leave empty)
- **Front-channel logout session required**: On ✓

## Advanced Settings (if needed)

### Access Token Lifespan
- Default: 5 minutes (300 seconds)
- Recommended: 15 minutes (900 seconds) for development

### Refresh Token Settings
- **Refresh Token Max Reuse**: 0 (no reuse)
- **Refresh Token Rotation**: On

## Environment Variables (.env)

Ensure your `.env` file has these settings:

```bash
# Keycloak Configuration
KEYCLOAK_URL=https://keycloak.92.5.226.7.nip.io
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-api
KEYCLOAK_CLIENT_SECRET=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P

# Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
EMAIL_VERIFIED_AUTO=true

# JWT Configuration
JWT_SECRET_KEY=18ergzNQajOEtdEK8ZBiKf7WgZojgXN32YLmK1VPqRDJNWtIEhP02tqbj016p999
HOOK_JWT_ALGORITHM=HS256
HOOK_JWT_SECRET=agenthub-mcp-hook-secret-2025
```

## Testing the Configuration

1. **Test Direct Grant (Password Flow)**:
```bash
curl -X POST https://keycloak.92.5.226.7.nip.io/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=mcp-api" \
  -d "client_secret=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P" \
  -d "username=YOUR_USERNAME" \
  -d "password=YOUR_PASSWORD"
```

2. **Test Service Account**:
```bash
curl -X POST https://keycloak.92.5.226.7.nip.io/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=mcp-api" \
  -d "client_secret=AuJ07QpbXdSdHxfIhyjnNI6VVRx1sd7P"
```

## Common Issues and Solutions

### Issue: CORS Errors
- Ensure Web Origins includes all frontend URLs
- Check that CORS_ORIGINS in .env matches Keycloak settings

### Issue: Redirect URI Mismatch
- Add all possible redirect variations including with/without trailing slashes
- Include both http and https variants for development

### Issue: Token Validation Failures
- Verify KEYCLOAK_URL doesn't have trailing slash
- Check that JWT_SECRET_KEY matches between backend and Keycloak
- Ensure KEYCLOAK_CLIENT_SECRET is correct

## Security Notes

1. **Production Deployment**:
   - Use HTTPS only for all URLs
   - Remove localhost URLs from production
   - Rotate client secret regularly
   - Enable PKCE for public clients

2. **Development**:
   - Keep localhost URLs for local testing
   - Use longer token lifespans for convenience
   - Enable debug logging for troubleshooting

## Related Documentation
- [Keycloak Setup Guide](./keycloak-setup-guide.md)
- [Frontend Client Configuration](./keycloak-mcp-webapp-client-config.md)
- [JWT Token Flow](./jwt-token-flow.md)