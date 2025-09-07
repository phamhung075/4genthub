# JWT Authentication Testing Instructions

## Overview

This guide provides comprehensive testing procedures to validate the JWT authentication fix and ensure proper token validation across the DhafnckMCP system.

## Quick Test (Immediate Verification)

### 1. Run the Verification Script
```bash
# Navigate to project root
cd /path/to/agentic-project

# Run basic verification
python dhafnck_mcp_main/scripts/jwt-authentication-verification.py

# Run with verbose output
python dhafnck_mcp_main/scripts/jwt-authentication-verification.py --verbose

# Test with actual endpoints (requires running server)
python dhafnck_mcp_main/scripts/jwt-authentication-verification.py --test-endpoints
```

### 2. Expected Output (Success)
```
🚀 Starting JWT Authentication Verification
============================================================
🔍 Testing JWT Configuration
✅ JWT_SECRET_KEY defined (64 characters)
✅ SUPABASE_JWT_SECRET defined (64 characters)  
✅ JWT secrets match - authentication should work
✅ Configuration validation passed

🔍 Testing JWT Token Generation
✅ Token generated with JWT_SECRET_KEY (XXX chars)
✅ Manual JWT token generated (XXX chars)

🔍 Testing JWT Token Validation
✅ Token validated with JWT_SECRET_KEY (user: test-user-123)
✅ Direct PyJWT validation with JWT_SECRET_KEY succeeded

🔍 Testing Middleware Dual Secret Support
✅ Middleware simulation: SUPABASE_JWT_SECRET + api_token type = SUCCESS
✅ Middleware compatibility test passed (1 successful attempts)

============================================================
📊 Test Summary
============================================================
✅ Passed: 4
❌ Failed: 0
⚠️ Warnings: 0
📊 Total: 4
🎉 All tests passed! JWT authentication should be working correctly.

📄 Detailed results exported to: jwt_verification_results.json
```

## Manual Testing Procedures

### 1. Environment Configuration Test

```bash
# Check environment variables
echo "JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
echo "SUPABASE_JWT_SECRET length: ${#SUPABASE_JWT_SECRET}"

# Quick validation script
cat << 'EOF' > check_jwt_config.sh
#!/bin/bash
if [ "$JWT_SECRET_KEY" = "$SUPABASE_JWT_SECRET" ]; then
  echo "✅ JWT secrets match"
else
  echo "❌ JWT secrets mismatch"
  echo "Backend: ${#JWT_SECRET_KEY} chars"
  echo "Frontend: ${#SUPABASE_JWT_SECRET} chars"
fi
EOF

chmod +x check_jwt_config.sh
./check_jwt_config.sh
```

### 2. Token Generation Test

```python
# test_token_generation.py
import os
import sys
sys.path.append('dhafnck_mcp_main/src')

from fastmcp.auth.domain.services.jwt_service import JWTService

# Test with both secrets
jwt_secret = os.getenv("JWT_SECRET_KEY")
supabase_secret = os.getenv("SUPABASE_JWT_SECRET")

print("Testing token generation...")

# Generate tokens with both secrets
for secret_name, secret_value in [("JWT_SECRET_KEY", jwt_secret), ("SUPABASE_JWT_SECRET", supabase_secret)]:
    if secret_value:
        try:
            service = JWTService(secret_key=secret_value)
            token = service.create_access_token(
                user_id="test-user",
                email="test@example.com", 
                roles=["user"]
            )
            print(f"✅ {secret_name}: Token generated ({len(token)} chars)")
        except Exception as e:
            print(f"❌ {secret_name}: {e}")
```

### 3. Middleware Testing

```bash
# Start the development server
cd dhafnck_mcp_main
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, test authentication
export TEST_TOKEN="your-generated-jwt-token-here"

# Test API endpoints
curl -H "Authorization: Bearer $TEST_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v2/projects

# Check server logs for authentication details:
# Look for lines like:
# ✅ MCP AUTH: JWT token validated with SUPABASE_JWT_SECRET as api_token type
# ✅ DUAL AUTH: Authenticated user test-user via mcp
```

### 4. Frontend Integration Test

```javascript
// frontend-auth-test.js (run in browser console)
const testAuthentication = async () => {
  // Generate JWT token using frontend logic
  const payload = {
    user_id: 'test-user-123',
    email: 'test@example.com',
    type: 'api_token',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
  };
  
  // Use the same secret that frontend uses
  const secret = process.env.REACT_APP_SUPABASE_JWT_SECRET;
  const token = jwt.sign(payload, secret, { algorithm: 'HS256' });
  
  console.log('Generated token:', token.substring(0, 50) + '...');
  
  // Test with backend API
  try {
    const response = await fetch('/api/v2/projects', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Backend response status:', response.status);
    if (response.status === 200) {
      console.log('✅ Authentication successful');
    } else {
      console.log('❌ Authentication failed');
    }
  } catch (error) {
    console.error('Request error:', error);
  }
};

testAuthentication();
```

## Comprehensive End-to-End Testing

### 1. Docker Environment Testing

```bash
# Test with Docker setup
docker-compose up -d

# Wait for services to start
sleep 10

# Run verification against Docker
python dhafnck_mcp_main/scripts/jwt-authentication-verification.py \
  --base-url http://localhost:8000 \
  --test-endpoints \
  --verbose

# Check Docker logs
docker-compose logs backend | grep -E "(AUTH|JWT)"
```

### 2. Production-like Testing

```bash
# Set production-like environment
export NODE_ENV=production
export APP_ENV=production
export DHAFNCK_AUTH_ENABLED=true
export DHAFNCK_MVP_MODE=false

# Generate strong secrets
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export SUPABASE_JWT_SECRET=$JWT_SECRET_KEY

# Restart services
docker-compose restart

# Run full test suite
python dhafnck_mcp_main/scripts/jwt-authentication-verification.py \
  --test-endpoints \
  --verbose
```

### 3. Load Testing (Optional)

```python
# load_test_jwt.py
import concurrent.futures
import requests
import time
from dhafnck_mcp_main.src.fastmcp.auth.domain.services.jwt_service import JWTService
import os

jwt_service = JWTService(secret_key=os.getenv("JWT_SECRET_KEY"))

def test_auth_request():
    token = jwt_service.create_access_token(
        user_id=f"user-{time.time()}",
        email="test@example.com",
        roles=["user"]
    )
    
    response = requests.get(
        "http://localhost:8000/api/v2/projects",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.status_code == 200

# Run 100 concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(test_auth_request) for _ in range(100)]
    results = [f.result() for f in futures]
    
success_rate = sum(results) / len(results)
print(f"Success rate: {success_rate:.2%}")
```

## Troubleshooting Failed Tests

### 1. Configuration Issues

**Error**: `JWT_SECRET_KEY not defined`
```bash
# Solution: Set environment variable
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export SUPABASE_JWT_SECRET=$JWT_SECRET_KEY

# Or add to .env file
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "SUPABASE_JWT_SECRET=$JWT_SECRET_KEY" >> .env
```

**Error**: `JWT secrets mismatch`
```bash
# Solution: Ensure both secrets match
export UNIFIED_SECRET=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$UNIFIED_SECRET
export SUPABASE_JWT_SECRET=$UNIFIED_SECRET
```

### 2. Token Generation Issues

**Error**: `Token generation failed`
```python
# Debug token generation
import os
from dhafnck_mcp_main.src.fastmcp.auth.domain.services.jwt_service import JWTService

secret = os.getenv("JWT_SECRET_KEY")
print(f"Secret length: {len(secret) if secret else 'None'}")
print(f"Secret type: {type(secret)}")

# Try manual generation
import jwt
payload = {"test": True}
token = jwt.encode(payload, secret, algorithm="HS256")
print(f"Manual token: {token[:50]}...")
```

### 3. Validation Issues

**Error**: `Token validation failed`
```python
# Test validation with debug info
import jwt
import os

token = "your-token-here"
secret = os.getenv("JWT_SECRET_KEY")

try:
    # Decode without verification to see payload
    unverified = jwt.decode(token, options={"verify_signature": False})
    print(f"Token payload: {unverified}")
    
    # Try verification
    verified = jwt.decode(token, secret, algorithms=["HS256"])
    print(f"Verification successful: {verified}")
    
except jwt.ExpiredSignatureError:
    print("Token expired")
except jwt.InvalidSignatureError:
    print("Invalid signature - check secret")
except Exception as e:
    print(f"Validation error: {e}")
```

### 4. Middleware Issues

**Error**: `401 Unauthorized despite valid token`

Check middleware logs:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart server and check logs
docker-compose logs backend | grep -E "(DUAL AUTH|MCP AUTH)" | tail -20

# Look for:
# ✅ MCP AUTH: JWT token validated with SUPABASE_JWT_SECRET
# ✅ DUAL AUTH: Authenticated user {user_id} via mcp
```

Test middleware directly:
```python
# test_middleware_direct.py
import os
from dhafnck_mcp_main.src.fastmcp.auth.middleware.dual_auth_middleware import DualAuthMiddleware
from starlette.requests import Request
from starlette.applications import Starlette

# Create test request with JWT token
app = Starlette()
middleware = DualAuthMiddleware(app)

# This requires more complex setup - see the verification script instead
```

## Validation Checklist

Before considering the fix complete, ensure:

### ✅ Configuration
- [ ] `JWT_SECRET_KEY` is defined and secure (32+ chars)
- [ ] `SUPABASE_JWT_SECRET` is defined
- [ ] Both secrets match (recommended) OR dual secret support is working
- [ ] No default/placeholder values are being used

### ✅ Token Generation
- [ ] Frontend can generate tokens using `SUPABASE_JWT_SECRET`
- [ ] Backend services can generate tokens using `JWT_SECRET_KEY`
- [ ] Tokens have correct format (start with `eyJ`)
- [ ] Tokens contain required payload fields (`user_id`, `type`, etc.)

### ✅ Token Validation
- [ ] Backend can validate frontend-generated tokens
- [ ] Middleware tries both secrets when needed
- [ ] Validation returns correct user information
- [ ] Token expiration is handled properly

### ✅ Integration
- [ ] Frontend → Backend API calls work with JWT tokens
- [ ] User context is properly set in request state
- [ ] Authentication errors are handled gracefully
- [ ] Logs show successful authentication events

### ✅ Security
- [ ] Secrets are not logged or exposed
- [ ] Default secrets are replaced with secure values
- [ ] Token expiration times are appropriate
- [ ] Error messages don't leak sensitive information

## Continuous Monitoring

Set up monitoring to catch authentication issues:

```bash
# Monitor authentication success/failure rates
grep -E "(✅|❌).*AUTH" /var/log/dhafnck-mcp.log | \
  awk '{print $1 " " $4}' | \
  sort | uniq -c

# Alert on high authentication failure rates
tail -f /var/log/dhafnck-mcp.log | \
  grep "❌.*AUTH" | \
  while read line; do
    echo "AUTH FAILURE: $line"
    # Send alert notification
  done
```

## Next Steps

After successful testing:

1. **Update Documentation**: Record any configuration changes
2. **Deploy Gradually**: Test in staging before production
3. **Monitor Metrics**: Track authentication success rates
4. **Plan Secret Rotation**: Set up regular secret rotation schedule
5. **Update Tests**: Add authentication tests to CI/CD pipeline

---

## Summary

The JWT authentication fix introduces dual secret support to resolve frontend/backend token mismatches. The verification script and manual tests ensure the fix works correctly across all authentication scenarios. Follow the testing procedures to validate your specific environment and configuration.