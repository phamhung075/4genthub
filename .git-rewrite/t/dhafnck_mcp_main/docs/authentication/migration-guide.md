# Authentication Migration Guide

## Overview

This guide helps you migrate your existing DhafnckMCP system to use the new JWT-based authentication system. The migration includes database schema updates, user data migration, and client application updates.

## Pre-Migration Checklist

### System Requirements

- [ ] Python 3.8+ with all dependencies installed
- [ ] Database backup completed
- [ ] Test environment set up and validated
- [ ] All client applications identified
- [ ] Maintenance window scheduled

### Backup Procedures

**Critical: Always backup before migration**

```bash
# Backup SQLite database
cp dhafnck_mcp.db dhafnck_mcp_backup_$(date +%Y%m%d).db

# Backup PostgreSQL database (if using)
pg_dump dhafnck_mcp > dhafnck_mcp_backup_$(date +%Y%m%d).sql

# Backup configuration files
cp -r config/ config_backup_$(date +%Y%m%d)/
```

### Environment Preparation

```bash
# Set migration environment variables
export MIGRATION_ENV=production
export BACKUP_LOCATION=/path/to/backups
export MIGRATION_LOG=/path/to/migration.log

# Test database connectivity
python -c "from fastmcp.database import get_db_session; next(get_db_session())"
```

## Migration Steps

### Step 1: Database Schema Migration

#### Automatic Migration (Recommended)

```bash
# Run the migration script
cd dhafnck_mcp_main
python scripts/migrate_to_auth.py --dry-run

# If dry-run looks good, run actual migration
python scripts/migrate_to_auth.py --execute
```

#### Manual Migration (Advanced Users)

```sql
-- Create new authentication tables
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending_verification',
    roles TEXT[] DEFAULT ARRAY['user'],
    is_locked BOOLEAN DEFAULT FALSE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_at TIMESTAMP,
    lock_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_auth_users_email ON auth_users(email);
CREATE INDEX idx_auth_users_username ON auth_users(username);
CREATE INDEX idx_auth_users_status ON auth_users(status);

-- Create refresh token table
CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    token_family UUID NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user_id ON auth_refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family ON auth_refresh_tokens(token_family);
```

### Step 2: Data Migration

#### Migrate Existing Users

Create migration script (`scripts/migrate_to_auth.py`):

```python
import bcrypt
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastmcp.database import get_db_session
from fastmcp.auth.domain.entities.user import User, UserStatus, UserRole

def migrate_existing_users():
    """Migrate existing users to new auth system"""
    session = next(get_db_session())
    
    try:
        # Query existing users from old system
        old_users = session.execute("""
            SELECT id, email, username, password_hash, created_at, is_active
            FROM legacy_users
        """).fetchall()
        
        migrated_count = 0
        
        for old_user in old_users:
            # Create new auth user
            new_user = User(
                email=old_user.email,
                username=old_user.username,
                password_hash=old_user.password_hash or generate_temp_password()
            )
            
            # Set appropriate status
            new_user.status = UserStatus.ACTIVE if old_user.is_active else UserStatus.PENDING_VERIFICATION
            new_user.roles = [UserRole.USER]
            new_user.created_at = old_user.created_at or datetime.utcnow()
            
            # If user was active, mark as verified
            if old_user.is_active:
                new_user.verified_at = new_user.created_at
            
            session.add(new_user)
            migrated_count += 1
            
            print(f"Migrated user: {old_user.email}")
        
        session.commit()
        print(f"Successfully migrated {migrated_count} users")
        
    except Exception as e:
        session.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        session.close()

def generate_temp_password():
    """Generate temporary password for users without passwords"""
    temp_password = str(uuid.uuid4())[:12] + "!"
    return bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()

if __name__ == "__main__":
    migrate_existing_users()
```

#### Run Data Migration

```bash
# Test migration
python scripts/migrate_to_auth.py --test

# Run actual migration
python scripts/migrate_to_auth.py

# Verify migration
python scripts/verify_migration.py
```

### Step 3: Update Environment Configuration

#### JWT Configuration

Add to your environment file (`.env`):

```env
# JWT Configuration
JWT_SECRET_KEY=your_super_secret_jwt_key_change_this_in_production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_ALGORITHM=HS256

# Email Configuration (for verification/reset)
SMTP_HOST=your_smtp_host
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=noreply@yourapp.com

# Security Settings
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
```

#### Update Configuration File

Update `config/settings.py`:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dhafnck_mcp.db"
    
    # JWT Settings
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"
    
    # Email Settings
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from_email: str
    
    # Security Settings
    password_min_length: int = 8
    max_login_attempts: int = 5
    account_lockout_duration_minutes: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 4: Update Server Code

#### Add Authentication Routes

Update `main.py` or your FastAPI app:

```python
from fastapi import FastAPI
from fastmcp.auth.api.endpoints import router as auth_router

app = FastAPI()

# Add authentication routes
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])

# Add middleware for authentication
from fastmcp.auth.infrastructure.middleware import AuthenticationMiddleware
app.add_middleware(AuthenticationMiddleware)
```

#### Update Protected Endpoints

Update existing endpoints to use authentication:

```python
from fastapi import Depends
from fastmcp.auth.application.dependencies import get_current_user
from fastmcp.auth.domain.entities.user import User

@app.get("/api/protected-endpoint")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    # Your protected logic here
    return {"message": f"Hello {current_user.email}"}
```

### Step 5: Update Client Applications

#### Frontend Applications

Update React/JavaScript clients:

```javascript
// Install required packages
npm install js-cookie jwt-decode react-hook-form

// Update API client
import { AuthProvider } from './components/auth/AuthProvider';
import { LoginForm, SignupForm, ProtectedRoute } from './components/auth';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route path="/signup" element={<SignupForm />} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

#### Update API Calls

Replace old authentication with JWT:

```javascript
// Old way
const response = await fetch('/api/data', {
  headers: {
    'X-API-Key': oldApiKey
  }
});

// New way
const response = await fetch('/api/data', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});
```

#### Python Clients

Update Python clients:

```python
# Old way
import requests

response = requests.get(
    'http://localhost:8000/api/data',
    headers={'X-API-Key': old_api_key}
)

# New way
import requests

# Login to get token
auth_response = requests.post(
    'http://localhost:8000/api/auth/login',
    json={
        'email': 'user@example.com',
        'password': 'password'
    }
)
token = auth_response.json()['access_token']

# Use token for requests
response = requests.get(
    'http://localhost:8000/api/data',
    headers={'Authorization': f'Bearer {token}'}
)
```

### Step 6: Testing Migration

#### Automated Tests

```bash
# Run migration tests
python -m pytest tests/migration/ -v

# Run authentication tests
python -m pytest tests/auth/ -v

# Run integration tests
python -m pytest tests/integration/test_auth_endpoints.py -v
```

#### Manual Testing

1. **User Registration**
   - Register new user
   - Verify email workflow
   - Test password requirements

2. **User Login**
   - Login with migrated user
   - Test "remember me" functionality
   - Verify token refresh

3. **Protected Routes**
   - Access protected endpoints
   - Test token expiration
   - Verify role-based access

4. **Password Reset**
   - Request password reset
   - Complete reset process
   - Login with new password

#### Load Testing

```bash
# Test concurrent logins
python tests/load/test_concurrent_auth.py

# Test token refresh under load
python tests/load/test_token_refresh_load.py
```

## Post-Migration Tasks

### Step 1: Update Documentation

- [ ] Update API documentation
- [ ] Update user guides
- [ ] Update integration examples
- [ ] Update troubleshooting guides

### Step 2: User Communication

#### Email Template for Existing Users

```
Subject: Important: Authentication System Update

Dear [Username],

We've upgraded our authentication system to provide better security and features. Here's what you need to know:

What's New:
- More secure JWT-based authentication
- Email verification for new accounts
- Enhanced password reset functionality
- Better session management

What You Need to Do:
1. Your existing login credentials still work
2. You may be asked to verify your email on first login
3. Update any saved API integrations (see guide below)

If You Have Issues:
- Try the password reset feature if you can't log in
- Contact support at support@dhafnck-mcp.com
- Check our updated user guide: [link]

Integration Guide: [link to migration guide]

Thank you for your patience during this upgrade.

Best regards,
The DhafnckMCP Team
```

### Step 3: Monitor and Support

#### Monitoring Setup

```python
# Add logging for migration issues
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

# Monitor authentication metrics
def monitor_auth_metrics():
    """Monitor key authentication metrics"""
    session = next(get_db_session())
    
    metrics = {
        'total_users': session.query(User).count(),
        'active_users': session.query(User).filter(User.status == UserStatus.ACTIVE).count(),
        'locked_accounts': session.query(User).filter(User.is_locked == True).count(),
        'unverified_users': session.query(User).filter(User.status == UserStatus.PENDING_VERIFICATION).count()
    }
    
    logging.info(f"Auth metrics: {metrics}")
    return metrics
```

#### Support Preparation

- [ ] Train support team on new authentication features
- [ ] Update support documentation
- [ ] Prepare FAQ for common migration issues
- [ ] Set up monitoring alerts

## Rollback Plan

If migration fails and rollback is needed:

### Step 1: Stop Services

```bash
# Stop application servers
sudo systemctl stop dhafnck-mcp

# Stop background processes
pkill -f "dhafnck"
```

### Step 2: Restore Database

```bash
# Restore from backup
cp dhafnck_mcp_backup_YYYYMMDD.db dhafnck_mcp.db

# Or for PostgreSQL
psql dhafnck_mcp < dhafnck_mcp_backup_YYYYMMDD.sql
```

### Step 3: Restore Configuration

```bash
# Restore config files
cp -r config_backup_YYYYMMDD/* config/

# Restore environment
cp .env.backup .env
```

### Step 4: Restart with Old Version

```bash
# Checkout previous version
git checkout previous-stable-tag

# Restart services
sudo systemctl start dhafnck-mcp
```

## Troubleshooting

### Common Migration Issues

#### Database Connection Errors

```bash
# Check database connectivity
python -c "from fastmcp.database import get_db_session; print('DB OK')"

# Check permissions
ls -la dhafnck_mcp.db
```

#### User Migration Failures

```bash
# Check for duplicate emails
SELECT email, COUNT(*) FROM auth_users GROUP BY email HAVING COUNT(*) > 1;

# Check for missing data
SELECT * FROM auth_users WHERE email IS NULL OR username IS NULL;
```

#### JWT Token Issues

```python
# Test JWT token generation
from fastmcp.auth.domain.services.jwt_service import JWTService

jwt_service = JWTService(secret_key="test-key")
token = jwt_service.create_access_token(
    user_id="test-user",
    email="test@example.com",
    roles=["user"]
)
print(f"Token: {token}")
```

### Performance Issues

#### Slow Authentication

- Check database indexes
- Monitor JWT token size
- Optimize database queries
- Consider connection pooling

#### Memory Usage

- Monitor application memory
- Check for token storage leaks
- Optimize session management

### Getting Help

If you encounter issues during migration:

1. **Check the logs**: `tail -f migration.log`
2. **Review this guide**: Ensure all steps were followed
3. **Run verification scripts**: Check data integrity
4. **Contact support**: Include logs and error messages

**Support Contact:**
- Email: dev-support@dhafnck-mcp.com
- Subject: "Migration Support - [Issue Summary]"
- Include: Migration logs, error messages, system info

## Conclusion

This migration guide provides a comprehensive approach to upgrading your DhafnckMCP system to use JWT-based authentication. The process includes:

- Database schema and data migration
- Configuration updates
- Client application updates
- Testing and validation
- Monitoring and support

Following this guide carefully will ensure a smooth transition to the new authentication system while maintaining data integrity and user access.

Remember to:
- Always backup before migration
- Test thoroughly in a staging environment
- Communicate changes to users
- Monitor the system after migration
- Have a rollback plan ready

---

*Last updated: August 17, 2025*

For technical support during migration, contact: dev-support@dhafnck-mcp.com