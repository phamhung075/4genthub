# Complete Troubleshooting Guide - agenthub Platform

## Quick Diagnostic Reference

| Symptom | Likely Cause | Quick Fix | Section |
|---------|--------------|-----------|---------|
| **Cannot connect to database** | PostgreSQL not running | `docker-compose up -d postgres` | [Database](#database-issues) |
| **Infinite loop on startup** | Database lock | Clear locks, restart | [Database Locks](#database-lock-infinite-loop) |
| **MCP tools not responding** | Server not running | Check `curl localhost:8000/health` | [MCP Connection](#mcp-connection-issues) |
| **Docker volume data lost** | Wrong volume path | Check `docker-compose.yml` volumes | [Docker Volumes](#docker-volume-persistence) |
| **Subtasks not loading** | WebSocket disconnect | Check browser console, reconnect | [WebSocket](#websocket-issues) |
| **Label timestamps invalid** | Timezone mismatch | Use UTC timestamps | [Timestamps](#label-timestamp-errors) |
| **Production deployment fails** | Missing env vars | Verify `.env` file | [Production](#production-deployment) |

---

## Database Issues

### Cannot Connect to Database

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server
FATAL: password authentication failed for user "agenthub_user"
```

**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
psql -h localhost -U agenthub_user -d agenthub
```

**Solutions**:

| Issue | Fix |
|-------|-----|
| Container not running | `docker-compose up -d postgres` |
| Wrong password | Verify `DB_PASSWORD` in `.env` |
| Port conflict | Change port in `docker-compose.yml` |
| Network issues | `docker network ls` and reconnect |

### Database Lock Infinite Loop

**Symptoms**:
- Application hangs on startup
- Logs show repeated "waiting for lock" messages
- Database queries timeout

**Root Cause**: Nested transactions or abandoned locks

**Diagnosis**:
```sql
-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Find blocking queries
SELECT
  blocked_locks.pid AS blocked_pid,
  blocking_locks.pid AS blocking_pid,
  blocked_activity.usename AS blocked_user,
  blocking_activity.usename AS blocking_user,
  blocked_activity.query AS blocked_statement,
  blocking_activity.query AS current_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Solutions**:

**1. Clear Active Locks**:
```sql
-- Terminate blocking queries
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND query_start < NOW() - INTERVAL '5 minutes';
```

**2. Fix Application Code**:
```python
# ❌ WRONG - Nested transactions cause deadlocks
def bad_example():
    with session.begin():
        # Outer transaction
        with session.begin():  # Nested - BAD!
            session.add(obj)

# ✅ CORRECT - Single transaction
def good_example():
    with session.begin():
        session.add(obj)
        session.commit()
```

**3. Restart Database**:
```bash
docker-compose restart postgres
# Wait 10 seconds
docker-compose ps postgres
```

---

## Docker Issues

### Docker Volume Persistence

**Symptoms**:
- Data disappears after container restart
- Database reset on `docker-compose down`
- "No such file or directory" errors

**Root Cause**: Volume not properly mounted or wrong path

**Diagnosis**:
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect agenthub_postgres_data

# Check mount point
docker inspect <container_id> | grep Mounts -A 20
```

**Solutions**:

**Verify docker-compose.yml**:
```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Named volume

volumes:
  postgres_data:  # Volume definition
```

**Common Mistakes**:
```yaml
# ❌ WRONG - Relative path creates volume wherever executed
volumes:
  - ./data:/var/lib/postgresql/data

# ✅ CORRECT - Named volume persists across restarts
volumes:
  - postgres_data:/var/lib/postgresql/data
```

**Recovery**:
```bash
# Stop containers
docker-compose down

# DON'T use -v flag (deletes volumes)
# Restart with existing volumes
docker-compose up -d
```

### Docker Menu Clean Volume Fix

**Issue**: `docker-menu.sh` option "C" (Clean) was deleting volumes

**Fixed**: Clean now only removes containers/images, preserves volumes

**Safe Clean**:
```bash
# Remove containers and images
docker-compose down --rmi all

# Keep volumes
docker volume ls  # Verify volumes still exist
```

---

## MCP Connection Issues

### MCP Server Not Responding

**Symptoms**:
```
ConnectionError: Cannot connect to MCP server
timeout: MCP request timed out after 30s
```

**Diagnosis**:
```bash
# Check if MCP server is running
curl http://localhost:8000/health

# Check server logs
docker-compose logs backend

# Check port binding
netstat -an | grep 8000
```

**Solutions**:

| Issue | Solution |
|-------|----------|
| Server not started | `python -m fastmcp.server.mcp_entry_point` |
| Port conflict | Change `BACKEND_PORT` in `.env` |
| Firewall blocking | Allow port 8000 |
| Authentication failed | Check JWT token validity |

### MCP Tool Timeout

**Symptoms**: Long-running operations timeout

**Configuration**:
```bash
# .env
MCP_REQUEST_TIMEOUT=30  # Increase for long operations
MCP_MAX_RETRIES=3
```

**Code Solution**:
```python
# Use async operations for long tasks
from utils.mcp_client import get_default_client

client = get_default_client()
# Set custom timeout
result = await client.query_with_timeout(
    operation="long_operation",
    timeout=60  # 60 seconds
)
```

---

## WebSocket Issues

### Subtasks Not Loading/Updating

**Symptoms**:
- Subtask list empty
- Subtask count shows N but list is empty
- Real-time updates not appearing

**Root Causes**:
1. WebSocket disconnected
2. Frontend cache stale
3. Backend sync event not triggered

**Diagnosis**:
```javascript
// Browser console
// Check WebSocket status
console.log(websocketService.isConnected());

// Check cache
console.log(queryClient.getQueryData(['subtasks', taskId]));

// Force refetch
queryClient.invalidateQueries(['subtasks', taskId]);
```

**Solutions**:

**1. Reconnect WebSocket**:
```javascript
// Frontend
websocketService.disconnect();
websocketService.connect();
```

**2. Force Cache Refresh**:
```javascript
queryClient.invalidateQueries(['tasks']);
queryClient.invalidateQueries(['subtasks']);
```

**3. Backend Fix** (ensure sync events):
```python
# After subtask create/update
await sync_broadcast_project_event(
    project_id=project_id,
    event_type="SUBTASK_CREATE",
    payload=subtask_data
)
```

### WebSocket Component Rendering

**Issue**: Subtask component not rendering despite data present

**Diagnosis**:
```javascript
// Check component props
console.log('taskId:', taskId);
console.log('subtasks:', subtasks);
console.log('isLoading:', isLoading);

// Check React DevTools
// Verify component receiving props
```

**Solutions**:
- Ensure `taskId` is valid UUID
- Check `useSubtasks` hook returns data
- Verify component key is unique
- Check for React errors in console

---

## Label/Timestamp Issues

### Label Timestamp Errors

**Symptoms**:
```
ValidationError: Invalid timestamp format
TypeError: Cannot read property 'toISOString' of undefined
```

**Root Cause**: Frontend expects ISO 8601, backend sends different format

**Correct Format**:
```javascript
// ✅ CORRECT - ISO 8601 with UTC
"2025-11-09T12:00:00.000Z"

// ❌ WRONG - Missing timezone
"2025-11-09 12:00:00"

// ❌ WRONG - Local timezone
"2025-11-09T12:00:00+08:00"
```

**Backend Fix**:
```python
from datetime import datetime, timezone

# Always use UTC
timestamp = datetime.now(timezone.utc)
# Serialize to ISO 8601
iso_string = timestamp.isoformat()
```

**Frontend Validation**:
```typescript
// Validate timestamp
function isValidTimestamp(ts: string): boolean {
  const date = new Date(ts);
  return !isNaN(date.getTime()) && ts.includes('Z');
}
```

---

## Production Deployment Issues

### Missing Environment Variables

**Symptoms**:
```
KeyError: 'DATABASE_URL'
ConfigurationError: Required environment variable not set
```

**Required Variables**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Keycloak
KEYCLOAK_URL=https://auth.yourdomain.com
KEYCLOAK_CLIENT_SECRET=<secret>

# Application
SECRET_KEY=<32-char-hex>
ENVIRONMENT=production
DEBUG=false
```

**Validation Script**:
```bash
#!/bin/bash
required_vars=(
  "DATABASE_URL"
  "KEYCLOAK_URL"
  "KEYCLOAK_CLIENT_SECRET"
  "SECRET_KEY"
)

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var not set"
    exit 1
  fi
done
echo "All required variables set"
```

### SSL/HTTPS Issues

**Symptoms**:
```
SSL: CERTIFICATE_VERIFY_FAILED
Mixed content warning
```

**Solutions**:

**1. Enable HTTPS**:
```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

**2. Update URLs**:
```bash
# .env
KEYCLOAK_URL=https://auth.yourdomain.com  # Not http://
FRONTEND_URL=https://app.yourdomain.com
```

**3. Force HTTPS**:
```nginx
# nginx.conf
server {
  listen 80;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl;
  ssl_certificate /etc/nginx/certs/cert.pem;
  ssl_certificate_key /etc/nginx/certs/key.pem;
}
```

### Database Migration Failures

**Symptoms**:
```
alembic.util.exc.CommandError: Target database is not up to date
IntegrityError: duplicate key value violates unique constraint
```

**Solutions**:

**1. Check Migration Status**:
```bash
alembic current
alembic history
```

**2. Manual Migration**:
```bash
# Upgrade to latest
alembic upgrade head

# Downgrade if needed
alembic downgrade -1
```

**3. Fix Conflicts**:
```python
# If duplicate data issue
# Option 1: Clean database
docker-compose down -v
docker-compose up -d

# Option 2: Manual fix
# Connect to database and resolve conflicts
```

---

## Common Error Messages

### "Task not found"

**Cause**: Invalid UUID or task deleted

**Solution**:
```python
# Verify task exists
from utils.mcp_client import get_default_client
client = get_default_client()

try:
    task = client.query_task_get(task_id=uuid)
except ResourceNotFoundError:
    print("Task does not exist")
```

### "Permission denied"

**Cause**: User lacks required role

**Solution**:
```python
# Check user roles
payload = verify_token(token)
roles = payload.get("realm_access", {}).get("roles", [])

# Assign required role in Keycloak
# Users → Select user → Role Mappings → Assign role
```

### "Connection pool exhausted"

**Cause**: Too many database connections

**Solution**:
```python
# Increase pool size
# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=40
)
```

---

## Diagnostic Commands

### Health Checks
```bash
# All services
curl http://localhost:8000/health
curl http://localhost:8080/health  # Keycloak
curl http://localhost:3800  # Frontend

# Database
psql -h localhost -U agenthub_user -d agenthub -c "SELECT 1;"
```

### Log Analysis
```bash
# Application logs
tail -f logs/claude-hooks/pre_tool_use.json
tail -f logs/claude-hooks/post_tool_use.json

# Container logs
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs --tail=100 keycloak
```

### System Resources
```bash
# Docker resource usage
docker stats

# Database connections
SELECT count(*) FROM pg_stat_activity;

# Database size
SELECT pg_size_pretty(pg_database_size('agenthub'));
```

---

## Emergency Procedures

### Complete System Reset

**WARNING**: Destroys all data

```bash
# Stop all containers
docker-compose down -v

# Remove all volumes
docker volume prune -f

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Initialize database
python scripts/init_database.py
```

### Database Backup/Restore

**Backup**:
```bash
# Backup database
docker exec postgres pg_dump -U agenthub_user agenthub > backup.sql

# Or compressed
docker exec postgres pg_dump -Fc -U agenthub_user agenthub > backup.dump
```

**Restore**:
```bash
# From SQL
docker exec -i postgres psql -U agenthub_user agenthub < backup.sql

# From dump
docker exec -i postgres pg_restore -U agenthub_user -d agenthub backup.dump
```

### Rollback Deployment

**Steps**:
```bash
# 1. Stop current version
docker-compose down

# 2. Checkout previous version
git checkout <previous-tag>

# 3. Restore database backup
docker exec -i postgres psql -U agenthub_user agenthub < backup_before_deploy.sql

# 4. Restart services
docker-compose up -d

# 5. Verify
curl http://localhost:8000/health
```

---

## Related Documentation
- [Setup Guide](../setup-guides/complete-setup-guide.md)
- [Production Deployment](../operations/production-deployment-guide.md)
- [Database Configuration](../operations/database-configuration-guide.md)
