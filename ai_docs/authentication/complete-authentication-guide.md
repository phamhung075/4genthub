# Complete Authentication Guide - agenthub Platform

## Quick Reference

| Component | Status | Port | Purpose |
|-----------|--------|------|---------|
| **Keycloak** | Production Ready | 8080 | Identity provider, SSO |
| **JWT Validation** | Active | - | Token verification, claims |
| **Service Accounts** | Configured | - | Machine-to-machine auth |
| **PostgreSQL** | Integrated | 5432 | Keycloak persistence |
| **Token Security** | Enforced | - | Expiry, refresh, rotation |

**Authentication Flow**: OAuth 2.0 / OpenID Connect via Keycloak

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                                │
│                   (Browser / API Client)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │     KEYCLOAK          │
                │  Identity Provider    │
                │  - Authentication     │
                │  - Token Issuance     │
                │  - User Management    │
                └───────────┬───────────┘
                            │ JWT Token
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   AGENTHUB BACKEND                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ JWT Validator│ -> │  Middleware  │ -> │  Protected   │ │
│  │              │    │   (FastAPI)  │    │   Routes     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  PostgreSQL   │
                    │  (User Data)  │
                    └───────────────┘
```

---

## 1. Keycloak Setup

### Installation

**Docker Deployment**:
```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak_user
      KC_DB_PASSWORD: ${KEYCLOAK_DB_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    command: start-dev  # Use 'start' for production
    ports:
      - "8080:8080"
```

**Start**: `docker-compose up -d keycloak`
**Access**: http://localhost:8080

### Realm Configuration

**Create Realm**:
- Name: `mcp`
- Display Name: "agenthub"
- Enabled: `ON`

**Token Settings**:
```
Access Token Lifespan: 30 minutes
Refresh Token: 7 days
SSO Session Idle: 30 minutes
SSO Session Max: 10 hours
```

**Security Settings**:
- Login Theme: `keycloak` (customize as needed)
- Email Verification: `ON` (production)
- Forgot Password: `ON`
- Remember Me: `ON`
- Login with Email: `ON`

### Client Configuration

**Backend Client** (`mcp-backend`):
```
Client ID: mcp-backend
Protocol: openid-connect
Access Type: confidential
Standard Flow: ON
Direct Access Grants: ON
Service Accounts: ON
Valid Redirect URIs: http://localhost:8000/*
```

**Frontend Client** (`mcp-frontend`):
```
Client ID: mcp-frontend
Protocol: openid-connect
Access Type: public
Standard Flow: ON
Valid Redirect URIs: http://localhost:3800/*
Web Origins: http://localhost:3800
```

**Get Client Secret**:
1. Clients → `mcp-backend` → Credentials
2. Copy `Secret` value
3. Add to `.env`: `KEYCLOAK_CLIENT_SECRET=<secret>`

### Service Account Setup

**Enable Service Accounts**:
1. Clients → `mcp-backend` → Settings
2. Service Accounts Enabled: `ON`
3. Save

**Assign Roles**:
1. Service Account Roles tab
2. Client Roles → `realm-management`
3. Assign: `manage-users`, `view-users`, `view-clients`

**Use Service Account**:
```python
import requests

response = requests.post(
    "http://localhost:8080/realms/mcp/protocol/openid-connect/token",
    data={
        "grant_type": "client_credentials",
        "client_id": "mcp-backend",
        "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET")
    }
)
token = response.json()["access_token"]
```

---

## 2. PostgreSQL Integration

### Database Setup

**Create Keycloak Database**:
```sql
CREATE DATABASE keycloak;
CREATE USER keycloak_user WITH ENCRYPTED PASSWORD '<password>';
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak_user;
```

**Connection String**:
```
jdbc:postgresql://postgres:5432/keycloak
```

### Schema Migration

**Keycloak Auto-Migration**:
- Keycloak automatically creates schema on first start
- ~300 tables created for realms, users, sessions, etc.

**Verify Schema**:
```sql
-- Connect to keycloak database
\c keycloak

-- List tables
\dt

-- Check key tables
SELECT COUNT(*) FROM public.user_entity;
SELECT COUNT(*) FROM public.realm;
```

### Production Configuration

**Performance Tuning**:
```yaml
environment:
  KC_DB_POOL_INITIAL_SIZE: 20
  KC_DB_POOL_MAX_SIZE: 100
  KC_DB_POOL_MIN_SIZE: 10
  KC_TRANSACTION_XA_ENABLED: false
```

**Backup Strategy**:
```bash
# Backup keycloak database
pg_dump -Fc keycloak > keycloak_backup.dump

# Restore
pg_restore -d keycloak keycloak_backup.dump
```

---

## 3. Token Flow

### Authorization Code Flow (Standard)

**Step 1: Redirect to Keycloak**:
```
GET http://localhost:8080/realms/mcp/protocol/openid-connect/auth
  ?client_id=mcp-frontend
  &redirect_uri=http://localhost:3800/callback
  &response_type=code
  &scope=openid
```

**Step 2: User Authenticates**:
- User enters credentials
- Keycloak validates
- Returns authorization code

**Step 3: Exchange Code for Token**:
```python
response = requests.post(
    "http://localhost:8080/realms/mcp/protocol/openid-connect/token",
    data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": "mcp-frontend",
        "redirect_uri": "http://localhost:3800/callback"
    }
)
tokens = response.json()
# {
#   "access_token": "...",
#   "refresh_token": "...",
#   "expires_in": 1800,
#   "token_type": "Bearer"
# }
```

### Direct Access Flow (Password)

**For Testing Only** (not recommended for production):
```python
response = requests.post(
    "http://localhost:8080/realms/mcp/protocol/openid-connect/token",
    data={
        "grant_type": "password",
        "client_id": "mcp-backend",
        "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET"),
        "username": "testuser",
        "password": "password"
    }
)
```

### Token Refresh Flow

**Refresh Access Token**:
```python
response = requests.post(
    "http://localhost:8080/realms/mcp/protocol/openid-connect/token",
    data={
        "grant_type": "refresh_token",
        "client_id": "mcp-backend",
        "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET"),
        "refresh_token": refresh_token
    }
)
new_tokens = response.json()
```

**Auto-Refresh Strategy**:
```python
def get_valid_token():
    if token_expired():
        refresh_access_token()
    return current_token
```

---

## 4. JWT Validation

### Token Structure

**JWT Components**:
```
Header.Payload.Signature
```

**Decoded JWT**:
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-id"
  },
  "payload": {
    "exp": 1699999999,
    "iat": 1699996399,
    "jti": "uuid",
    "iss": "http://localhost:8080/realms/mcp",
    "sub": "user-uuid",
    "typ": "Bearer",
    "azp": "mcp-backend",
    "scope": "openid email profile",
    "email": "user@example.com",
    "preferred_username": "testuser"
  }
}
```

### Validation Process

**Backend JWT Validation**:
```python
from jose import jwt, JWTError
import requests

# 1. Fetch JWKS (JSON Web Key Set)
jwks_url = "http://localhost:8080/realms/mcp/protocol/openid-connect/certs"
jwks = requests.get(jwks_url).json()

# 2. Validate token
try:
    payload = jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        audience="mcp-backend",
        issuer="http://localhost:8080/realms/mcp"
    )
    user_id = payload["sub"]
    email = payload["email"]
except JWTError as e:
    # Invalid token
    raise HTTPException(status_code=401, detail="Invalid token")
```

### Validation Checks

| Check | Purpose | Validation |
|-------|---------|------------|
| **Signature** | Authenticity | Verify with public key from JWKS |
| **Expiry** | Freshness | `exp` claim > current time |
| **Issuer** | Source | `iss` matches Keycloak URL |
| **Audience** | Intended recipient | `aud` matches client ID |
| **Not Before** | Early use | `nbf` claim ≤ current time |

---

## 5. Token Security

### Security Best Practices

**Access Token**:
- ✅ Short lifespan (30 min)
- ✅ Store in memory only (not localStorage)
- ✅ Include in Authorization header
- ✅ Validate on every request
- ❌ Never log or expose

**Refresh Token**:
- ✅ Longer lifespan (7 days)
- ✅ Store in httpOnly cookie
- ✅ Rotate on use
- ✅ Revoke on logout
- ❌ Never send to third parties

**Storage Comparison**:

| Storage | Access Token | Refresh Token | Security |
|---------|--------------|---------------|----------|
| Memory | ✅ Recommended | ❌ Lost on reload | High |
| httpOnly Cookie | ⚠️ CSRF risk | ✅ Recommended | High |
| localStorage | ❌ XSS vulnerable | ❌ XSS vulnerable | Low |
| sessionStorage | ⚠️ Acceptable | ❌ Lost on close | Medium |

### Token Rotation

**Automatic Rotation**:
```python
# Keycloak automatically rotates refresh token on use
response = refresh_token(old_refresh_token)
new_access_token = response["access_token"]
new_refresh_token = response["refresh_token"]  # New token issued

# Old refresh token is now invalid
```

**Manual Revocation**:
```python
requests.post(
    "http://localhost:8080/realms/mcp/protocol/openid-connect/logout",
    data={
        "client_id": "mcp-backend",
        "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET"),
        "refresh_token": refresh_token
    }
)
```

### Attack Prevention

| Attack | Prevention | Implementation |
|--------|-----------|----------------|
| **XSS** | Content Security Policy | `helmet` middleware, sanitize inputs |
| **CSRF** | SameSite cookies | `Set-Cookie: SameSite=Strict` |
| **Token Theft** | Short expiry, rotation | 30 min access, rotate refresh |
| **Replay** | JTI validation | Track used tokens, reject duplicates |
| **MITM** | HTTPS only | Enforce TLS, HSTS headers |

---

## 6. Backend Integration

### FastAPI Middleware

**JWT Dependency**:
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, jwks, algorithms=["RS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use in routes
@app.get("/protected")
async def protected_route(payload: dict = Depends(verify_token)):
    user_id = payload["sub"]
    return {"user_id": user_id}
```

### Role-Based Access Control

**Check Roles**:
```python
def require_role(required_role: str):
    async def role_checker(payload: dict = Depends(verify_token)):
        roles = payload.get("realm_access", {}).get("roles", [])
        if required_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return payload
    return role_checker

# Use in routes
@app.get("/admin")
async def admin_route(payload: dict = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

---

## 7. Environment Configuration

**.env**:
```bash
# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=<from-credentials-tab>
KEYCLOAK_ADMIN_PASSWORD=<admin-password>

# Database
KEYCLOAK_DB_PASSWORD=<db-password>

# Token Settings
TOKEN_EXPIRY_MINUTES=30
REFRESH_TOKEN_DAYS=7
```

---

## 8. Troubleshooting

### Common Issues

**Invalid Client Credentials**:
```
Error: "invalid_client"
Solution: Verify KEYCLOAK_CLIENT_SECRET in .env matches Keycloak
```

**Token Expired**:
```
Error: "Token has expired"
Solution: Implement auto-refresh or re-authenticate
```

**JWKS Fetch Failed**:
```
Error: "Unable to fetch JWKS"
Solution: Check KEYCLOAK_URL, ensure Keycloak is running
```

**User Not Found**:
```
Error: "User does not exist"
Solution: Create user in Keycloak admin console
```

### Debug Commands

```bash
# Check Keycloak health
curl http://localhost:8080/health

# Test token generation
curl -X POST http://localhost:8080/realms/mcp/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=mcp-backend" \
  -d "client_secret=${SECRET}" \
  -d "username=testuser" \
  -d "password=password"

# Decode JWT (using jwt.io or jwt CLI)
echo $TOKEN | jwt decode -

# Check JWKS endpoint
curl http://localhost:8080/realms/mcp/protocol/openid-connect/certs
```

---

## 9. Production Deployment

### Security Hardening

**Keycloak**:
- Enable HTTPS (TLS certificates)
- Use production database (PostgreSQL)
- Set strong admin password
- Enable brute force detection
- Configure email verification
- Set up backup/restore

**Application**:
- Validate all tokens server-side
- Use HTTPS only
- Implement rate limiting
- Enable CORS properly
- Sanitize all inputs
- Monitor failed auth attempts

**Database**:
- Enable SSL connections
- Restrict access to Keycloak only
- Regular backups
- Encrypt sensitive data

---

## 10. Monitoring

**Health Checks**:
```bash
curl http://localhost:8080/health  # Keycloak
curl http://localhost:8000/health  # Application
```

**Metrics to Track**:
- Active sessions
- Failed login attempts
- Token refresh rate
- Average token lifespan
- Authentication errors

**Logs**:
- Keycloak: `docker-compose logs keycloak`
- Application: `logs/auth.log`
- Failed auth: `logs/auth_failures.log`

---

## Related Documentation
- [Setup Guide](../setup-guides/complete-setup-guide.md)
- [API Integration](../api-integration/)
- [Security Best Practices](../operations/production-deployment-guide.md)
