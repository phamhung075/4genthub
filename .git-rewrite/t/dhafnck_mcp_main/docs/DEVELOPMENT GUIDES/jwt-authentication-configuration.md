# JWT Authentication Configuration Guide

## Overview

This guide explains how to properly configure JWT secrets to resolve authentication mismatches between the frontend and backend systems.

## Problem Statement

The DhafnckMCP system uses dual authentication:
- **Frontend**: Generates JWT tokens using `SUPABASE_JWT_SECRET` (88 characters)
- **Backend**: Validates JWT tokens using `JWT_SECRET_KEY` (56 characters)

This mismatch causes 401 Unauthorized errors even with valid tokens.

## Solution: Unified JWT Secret Configuration

### 1. Environment Variables Setup

Create or update your `.env` file in the project root with these unified settings:

```bash
# =============================================================================
# JWT AUTHENTICATION SECRETS - UNIFIED CONFIGURATION
# =============================================================================

# Primary JWT secret - Used by backend for validation
# CRITICAL: Must match frontend token generation secret
JWT_SECRET_KEY=your-unified-jwt-secret-key-here

# Supabase JWT secret - Used by frontend for token generation  
# CRITICAL: Should be the same as JWT_SECRET_KEY for consistency
SUPABASE_JWT_SECRET=your-unified-jwt-secret-key-here

# Alternative: Use Supabase's actual JWT secret if integrating with Supabase Auth
# Get this from: Supabase Dashboard > Project Settings > API > JWT Settings
# SUPABASE_JWT_SECRET=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# =============================================================================
# RECOMMENDED APPROACH: Generate Strong Unified Secret
# =============================================================================
# Use this command to generate a secure secret:
# openssl rand -hex 32
# or
# python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Docker Environment Configuration

If using Docker, ensure environment variables are properly passed:

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: .
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
    env_file:
      - .env

  frontend:
    build: ./dhafnck-frontend
    environment:
      - REACT_APP_SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
    env_file:
      - .env
```

**Dockerfile:**
```dockerfile
# Ensure environment variables are available
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENV SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
```

### 3. Frontend Configuration

Ensure your frontend uses the correct environment variable:

**dhafnck-frontend/.env:**
```bash
# Should match backend JWT_SECRET_KEY
REACT_APP_SUPABASE_JWT_SECRET=your-unified-jwt-secret-key-here

# If using Vite instead of Create React App:
VITE_SUPABASE_JWT_SECRET=your-unified-jwt-secret-key-here
```

**Frontend code (token generation):**
```typescript
// Use consistent environment variable
const jwtSecret = process.env.REACT_APP_SUPABASE_JWT_SECRET || 
                 process.env.VITE_SUPABASE_JWT_SECRET;

if (!jwtSecret) {
  throw new Error('JWT secret not configured');
}

// Generate token with unified secret
const token = jwt.sign(payload, jwtSecret, { 
  algorithm: 'HS256',
  expiresIn: '24h' 
});
```

## Security Best Practices

### 1. Secret Generation
```bash
# Generate cryptographically secure secret (64 characters recommended)
openssl rand -hex 32

# Or using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 2. Secret Management
- **Never commit secrets to version control**
- Use different secrets for development, staging, and production
- Rotate secrets regularly (every 90 days recommended)
- Use environment variables or secure vaults (HashiCorp Vault, AWS Secrets Manager)

### 3. Secret Validation
```bash
# Verify secret length (should be at least 32 characters)
echo ${JWT_SECRET_KEY} | wc -c

# Both secrets should match
if [ "$JWT_SECRET_KEY" = "$SUPABASE_JWT_SECRET" ]; then
  echo "✅ JWT secrets match"
else
  echo "❌ JWT secrets mismatch - authentication will fail"
fi
```

## Configuration Validation

### 1. Environment Check Script
```bash
#!/bin/bash
# check-jwt-config.sh

echo "🔍 JWT Configuration Check"
echo "=========================="

# Check if secrets are defined
if [ -z "$JWT_SECRET_KEY" ]; then
  echo "❌ JWT_SECRET_KEY not defined"
  exit 1
else
  echo "✅ JWT_SECRET_KEY defined (${#JWT_SECRET_KEY} characters)"
fi

if [ -z "$SUPABASE_JWT_SECRET" ]; then
  echo "❌ SUPABASE_JWT_SECRET not defined"
  exit 1
else
  echo "✅ SUPABASE_JWT_SECRET defined (${#SUPABASE_JWT_SECRET} characters)"
fi

# Check if secrets match
if [ "$JWT_SECRET_KEY" = "$SUPABASE_JWT_SECRET" ]; then
  echo "✅ JWT secrets match - authentication should work"
else
  echo "⚠️  JWT secrets differ - may cause authentication issues"
  echo "   Backend uses: JWT_SECRET_KEY (${#JWT_SECRET_KEY} chars)"
  echo "   Frontend uses: SUPABASE_JWT_SECRET (${#SUPABASE_JWT_SECRET} chars)"
fi

# Check minimum length
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
  echo "⚠️  JWT_SECRET_KEY is shorter than recommended (32+ characters)"
fi

echo "=========================="
```

### 2. Python Validation Script
```python
#!/usr/bin/env python3
import os
import sys

def check_jwt_config():
    print("🔍 JWT Configuration Validation")
    print("=" * 40)
    
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    supabase_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    issues = []
    
    # Check existence
    if not jwt_secret:
        issues.append("❌ JWT_SECRET_KEY not defined")
    else:
        print(f"✅ JWT_SECRET_KEY defined ({len(jwt_secret)} characters)")
    
    if not supabase_secret:
        issues.append("❌ SUPABASE_JWT_SECRET not defined")  
    else:
        print(f"✅ SUPABASE_JWT_SECRET defined ({len(supabase_secret)} characters)")
    
    # Check consistency
    if jwt_secret and supabase_secret:
        if jwt_secret == supabase_secret:
            print("✅ JWT secrets match - authentication should work")
        else:
            issues.append("⚠️  JWT secrets mismatch - authentication may fail")
    
    # Check strength
    if jwt_secret and len(jwt_secret) < 32:
        issues.append(f"⚠️  JWT_SECRET_KEY too short ({len(jwt_secret)} chars, recommend 32+)")
    
    if issues:
        print("\n🚨 Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("\n✅ JWT configuration looks good!")
        return True

if __name__ == "__main__":
    success = check_jwt_config()
    sys.exit(0 if success else 1)
```

## Development vs Production

### Development Setup
```bash
# Development - Use simple but secure secret
JWT_SECRET_KEY=dev-jwt-secret-32-chars-minimum-required-here
SUPABASE_JWT_SECRET=dev-jwt-secret-32-chars-minimum-required-here
```

### Production Setup
```bash
# Production - Use strong generated secrets
JWT_SECRET_KEY=$(openssl rand -hex 32)
SUPABASE_JWT_SECRET=${JWT_SECRET_KEY}

# Or use external secret management
JWT_SECRET_KEY=${VAULT_JWT_SECRET}
SUPABASE_JWT_SECRET=${VAULT_JWT_SECRET}
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized despite valid tokens**
   - Check if `JWT_SECRET_KEY` and `SUPABASE_JWT_SECRET` match
   - Verify environment variables are loaded correctly
   - Check token generation uses same secret as validation

2. **"Invalid token" errors in logs**
   - Ensure secrets are properly base64 encoded if required
   - Check token format (should start with `eyJ` for JWT)
   - Verify algorithm consistency (HS256 recommended)

3. **Environment variables not loading**
   - Check `.env` file location and format
   - Ensure no trailing spaces or quotes in values
   - Verify Docker/container environment variable passing

### Debug Commands
```bash
# Check current environment
env | grep JWT

# Test token generation/validation
python3 -c "
import jwt
import os
secret = os.getenv('JWT_SECRET_KEY')
token = jwt.encode({'test': True}, secret, algorithm='HS256')
decoded = jwt.decode(token, secret, algorithms=['HS256'])
print('✅ JWT test successful:', decoded)
"

# Check Docker environment
docker exec -it container_name env | grep JWT
```

## Integration Testing

After configuration changes, test the complete authentication flow:

1. **Generate token in frontend**
2. **Send authenticated request to backend**  
3. **Verify successful authentication in logs**
4. **Check user context is properly set**

See `jwt-authentication-verification.py` for automated testing script.

---

## Summary

The key to resolving JWT authentication issues is ensuring both `JWT_SECRET_KEY` and `SUPABASE_JWT_SECRET` use the same value. The updated DualAuthMiddleware now supports both secrets for backward compatibility, but unified configuration is the recommended long-term solution.