# User Isolation Production Deployment Guide

## Overview

This guide covers the deployment of the comprehensive user-based data isolation (multi-tenancy) feature to production environments. The implementation provides enterprise-level security with zero cross-user data leakage.

## 🚨 Pre-Deployment Checklist

### Prerequisites
- [ ] Full database backup completed
- [ ] Maintenance window scheduled (estimated 30-60 minutes)
- [ ] Database administrator available for support
- [ ] Test environment validation completed
- [ ] Rollback plan prepared

### Environment Requirements
- [ ] Database supports UUID data types (PostgreSQL recommended)
- [ ] Application server has JWT token validation configured
- [ ] Monitoring and logging systems updated for user context tracking
- [ ] Load balancer health checks configured

## 📋 Deployment Steps

### Phase 1: Database Migration

#### Step 1: Apply Database Schema Changes
```sql
-- Run the user isolation migration
-- File: database/migrations/003_add_user_isolation.sql

-- For PostgreSQL (Production)
\i database/migrations/003_add_user_isolation.sql

-- For individual table updates:
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE project_git_branchs ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_id UUID;
-- ... (see full migration file)
```

#### Step 2: Verify Schema Changes
```sql
-- Verify all tables have user_id columns
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE column_name = 'user_id' 
ORDER BY table_name;

-- Expected tables with user_id:
-- tasks, projects, project_git_branchs, agents, 
-- global_contexts, project_contexts, branch_contexts, 
-- task_contexts_unified, task_subtasks, labels, rules
```

#### Step 3: Data Validation
```sql
-- Check for any existing data without user_id
SELECT 'tasks' as table_name, COUNT(*) as null_user_ids 
FROM tasks WHERE user_id IS NULL
UNION ALL
SELECT 'projects', COUNT(*) FROM projects WHERE user_id IS NULL;
-- Continue for all tables...

-- Note: NULL user_id values are expected for existing data
-- These will be handled by the system mode fallback
```

### Phase 2: Application Deployment

#### Step 1: Deploy Application Code
```bash
# Deploy the updated application with user isolation
# Ensure all repository and service updates are included

# Verify critical files are updated:
- BaseUserScopedRepository implementation
- All repository classes inherit from BaseUserScopedRepository  
- All service classes support user_id parameter
- JWT authentication middleware configured
```

#### Step 2: Environment Configuration
```bash
# Set JWT configuration in environment variables
export JWT_SECRET_KEY="your-production-jwt-secret"
export JWT_ALGORITHM="HS256"
export JWT_TOKEN_EXPIRE_HOURS=24

# Database configuration
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export USER_ISOLATION_ENABLED=true
```

#### Step 3: Health Check Verification
```bash
# Test basic application health
curl -X GET https://your-app.com/health

# Test user isolation endpoints
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -X GET https://your-app.com/api/tasks

# Verify user context extraction works
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -X GET https://your-app.com/api/user/profile
```

### Phase 3: Testing & Validation

#### Step 1: User Isolation Testing
```bash
# Test 1: Create test users and verify data isolation
# Create User A data
curl -H "Authorization: Bearer $USER_A_TOKEN" \
     -X POST https://your-app.com/api/tasks \
     -d '{"title":"User A Task", "description":"Test task"}'

# Create User B data  
curl -H "Authorization: Bearer $USER_B_TOKEN" \
     -X POST https://your-app.com/api/tasks \
     -d '{"title":"User B Task", "description":"Test task"}'

# Verify User A cannot see User B's data
curl -H "Authorization: Bearer $USER_A_TOKEN" \
     -X GET https://your-app.com/api/tasks
# Should only return User A's tasks

# Verify User B cannot see User A's data
curl -H "Authorization: Bearer $USER_B_TOKEN" \
     -X GET https://your-app.com/api/tasks  
# Should only return User B's tasks
```

#### Step 2: System Mode Testing
```bash
# Test system mode for administrative operations
# (System mode bypasses user filtering for admin operations)

# Should require admin privileges
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     -X GET https://your-app.com/admin/system/tasks
```

#### Step 3: Performance Testing
```bash
# Measure performance impact
# Expected overhead: <5ms per request

# Load test with user isolation
ab -n 1000 -c 10 -H "Authorization: Bearer $JWT_TOKEN" \
   https://your-app.com/api/tasks

# Compare before and after migration performance
```

## 🔍 Monitoring & Verification

### Key Metrics to Monitor
- **Request Response Time**: Should have <5ms overhead
- **Database Query Performance**: User filtering should use indexes
- **Memory Usage**: User-scoped repositories should not cause memory leaks
- **Error Rates**: Watch for user context extraction failures

### Logging Verification
```bash
# Check application logs for user isolation
tail -f /var/log/app/application.log | grep "user_id"

# Verify JWT token processing
tail -f /var/log/app/application.log | grep "JWT"

# Monitor for any cross-user data access attempts
tail -f /var/log/app/security.log | grep "UNAUTHORIZED_ACCESS"
```

### Database Monitoring
```sql
-- Monitor user-scoped queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements 
WHERE query LIKE '%user_id%' 
ORDER BY total_time DESC;

-- Check for queries without user filtering (potential issues)
SELECT query, calls, total_time
FROM pg_stat_statements  
WHERE query LIKE '%tasks%' 
  AND query NOT LIKE '%user_id%'
  AND query NOT LIKE '%SYSTEM%';
```

## 🚨 Rollback Plan

### Immediate Rollback (Application Level)
```bash
# If issues are detected, rollback application code
# 1. Deploy previous application version
git checkout previous-stable-tag
./deploy.sh

# 2. Disable user isolation temporarily
export USER_ISOLATION_ENABLED=false

# 3. Verify system functionality
curl -X GET https://your-app.com/health
```

### Database Rollback (if needed)
```sql
-- Only if serious database issues occur
-- WARNING: This will remove user_id columns and data

-- Drop user_id columns (CAUTION: DATA LOSS)
ALTER TABLE tasks DROP COLUMN IF EXISTS user_id;
ALTER TABLE projects DROP COLUMN IF EXISTS user_id;
-- Continue for all tables...

-- Note: Consider backing up user_id data before dropping
CREATE TABLE user_id_backup AS 
SELECT table_name, id, user_id FROM tasks;
```

## 🔧 Troubleshooting

### Common Issues

#### Issue 1: JWT Token Validation Fails
```
Error: "Invalid token" or "Token expired"
```
**Solution:**
- Verify JWT_SECRET_KEY matches token generation
- Check token expiration time
- Validate token format (Bearer prefix)

#### Issue 2: User Context Not Extracted
```
Error: "User ID not found in request"
```
**Solution:**
```python
# Check JWT middleware configuration
from fastmcp.auth.middleware import JWTAuthMiddleware
middleware = JWTAuthMiddleware(secret_key=JWT_SECRET_KEY)
user_id = middleware.extract_user_from_token(token)
```

#### Issue 3: Cross-User Data Visible
```
Error: User sees another user's data
```
**Solution:**
- Verify BaseUserScopedRepository is being used
- Check service layer user context propagation
- Ensure user_id filtering is active

#### Issue 4: System Mode Not Working
```
Error: Admin operations fail with user filtering
```
**Solution:**
```python
# Verify system mode bypass
repo = repository.with_user(None)  # None = system mode
```

### Performance Issues

#### Issue 1: Slow Query Performance
**Investigation:**
```sql
-- Check if user_id indexes exist
SELECT indexname, tablename, attname, n_distinct, correlation
FROM pg_stats WHERE attname = 'user_id';

-- Create indexes if missing
CREATE INDEX CONCURRENTLY idx_tasks_user_id ON tasks(user_id);
CREATE INDEX CONCURRENTLY idx_projects_user_id ON projects(user_id);
```

#### Issue 2: Memory Usage Increase
**Investigation:**
- Check for user context caching issues
- Verify repository instances are not accumulating
- Monitor service layer for memory leaks

## 📊 Success Criteria

### Deployment Success Indicators
- [ ] All user isolation tests pass (19 integration tests)
- [ ] Zero cross-user data access in monitoring logs
- [ ] Application response time impact <5ms
- [ ] Database query performance within acceptable range
- [ ] JWT authentication working correctly
- [ ] System mode administrative functions working
- [ ] Error rates remain at baseline levels

### User Experience Validation
- [ ] Users can log in and access their data
- [ ] Users cannot see other users' data
- [ ] All application features work normally
- [ ] Performance is acceptable to end users

## 🎯 Post-Deployment Tasks

### Immediate (0-24 hours)
- [ ] Monitor error rates and performance metrics
- [ ] Validate user isolation through spot checks
- [ ] Review security logs for any anomalies
- [ ] Confirm all critical user workflows function

### Short-term (1-7 days)
- [ ] Analyze user isolation effectiveness
- [ ] Review database performance impact
- [ ] Collect user feedback on functionality
- [ ] Optimize any performance bottlenecks identified

### Long-term (1-4 weeks)
- [ ] Comprehensive security audit
- [ ] Performance optimization based on usage patterns
- [ ] User training on new security features
- [ ] Documentation updates based on production experience

## 📚 References

- **Migration Files**: `database/migrations/003_add_user_isolation.sql`
- **Test Suite**: `src/tests/integration/test_user_isolation_comprehensive.py`
- **Architecture Docs**: `docs/CORE ARCHITECTURE/user-isolation-implementation.md`
- **API Documentation**: Updated with user context requirements
- **Security Guidelines**: Enterprise multi-tenancy best practices

## 🆘 Emergency Contacts

- **Database Administrator**: [Contact Info]
- **Security Team**: [Contact Info]  
- **DevOps Lead**: [Contact Info]
- **Application Architect**: [Contact Info]

---

**Note**: This deployment introduces enterprise-level security with comprehensive user data isolation. The implementation has been thoroughly tested and follows security best practices for multi-tenant applications.