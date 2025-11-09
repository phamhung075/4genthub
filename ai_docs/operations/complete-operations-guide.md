# Complete Operations Guide - agenthub Platform

## Quick Reference

| Operation | Command | Use Case |
|-----------|---------|----------|
| **Deploy production** | `./scripts/deployment/deploy-production.sh --environment production` | Full production deployment |
| **Health check** | `./scripts/deployment/health-checks/comprehensive-health-check.sh` | Verify system health |
| **Rollback** | `./scripts/deployment/rollback/rollback-production.sh --environment production` | Revert failed deployment |
| **Apply migration** | `python scripts/migrate.py upgrade head` | Update database schema |
| **Database reset** | `python scripts/reset_database.py` | Fresh local development |
| **Monitor metrics** | http://localhost:9090 (Prometheus) | Track system performance |

---

## Production Deployment

### Deployment Checklist

| Category | Requirements |
|----------|-------------|
| **Security** | SSL certificates valid, JWT secrets rotated, rate limiting tested, security headers configured |
| **Infrastructure** | Servers provisioned, Docker installed, firewall configured, backup systems operational |
| **Testing** | Unit tests passing (150+), integration tests complete, security scans done, load tests validated |

### CI/CD Pipeline

**GitHub Actions Workflow**:
1. Security Scanning (Trivy, Bandit, SARIF upload)
2. Code Quality (Black, isort, flake8, mypy)
3. Testing (Unit, integration, migrations)
4. Build & Push (Docker images, multi-architecture)
5. Deployment (Staging auto, production manual)

**Deployment Triggers**:
- Staging: Automatic on `main` branch push
- Production: Manual workflow dispatch or version tag (`v*.*.*`)
- Rollback: Automatic on production deployment failure

### Deployment Execution

```bash
# 1. Pre-deployment validation
./scripts/deployment/security/apply-security-fixes.sh --environment production
./scripts/deployment/deploy-production.sh --dry-run --environment production

# 2. Execute deployment
./scripts/deployment/deploy-production.sh --environment production

# 3. Monitor deployment
docker-compose -f docker-system/docker-compose.production-enhanced.yml logs -f

# 4. Health checks
./scripts/deployment/health-checks/comprehensive-health-check.sh --environment production
```

### Infrastructure Components

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| PostgreSQL | Primary database | 5432 | `pg_isready` |
| Redis | Cache & sessions | 6379 | `redis-cli ping` |
| MCP Backend | API server | 8000 | `/api/v2/health` |
| Frontend | Web interface | 3000 | `/health` |
| Nginx | Reverse proxy | 80/443 | `/health` |
| Prometheus | Metrics collection | 9090 | `/-/healthy` |
| Grafana | Dashboards | 3001 | `/api/health` |

### Rollback Procedures

**Automatic Rollback** (CI/CD triggered):
```bash
./scripts/deployment/rollback/rollback-production.sh \
    --environment production \
    --auto-confirm
```

**Manual Rollback**:
```bash
# Rollback to previous version
./scripts/deployment/rollback/rollback-production.sh --environment production

# Rollback to specific version
./scripts/deployment/rollback/rollback-production.sh \
    --environment production \
    --version v1.2.3
```

**Rollback Validation**: Verify services running → Run health checks → Validate functionality → Monitor stability → Notify stakeholders

---

## Docker Deployment

### SSL Configuration by Deployment Type

| Deployment Type | DATABASE_SSL_MODE | Reason |
|----------------|-------------------|---------|
| **CapRover PostgreSQL** | `disable` | CapRover PostgreSQL doesn't support SSL |
| **AWS RDS** | `require` | Managed service enforces SSL |
| **Google Cloud SQL** | `require` | Managed service enforces SSL |
| **Azure Database** | `require` | Managed service enforces SSL |
| **Supabase** | `require` | Always enforced (automatic) |
| **Local Development** | `disable` or `prefer` | Local PostgreSQL usually no SSL |

### Environment Variables

**Required for all deployments**:
```bash
# Core Settings
ENV=production
NODE_ENV=production
APP_LOG_LEVEL=INFO  # Converted to lowercase automatically

# Database
DATABASE_TYPE=postgresql
DATABASE_HOST=your_database_host
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_password
DATABASE_SSL_MODE=disable  # or 'require' based on deployment type

# Backend
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_chars_long

# Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak.com
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your_keycloak_secret

# CORS
CORS_ORIGINS=https://your-app.com
CORS_ALLOW_CREDENTIALS=true
```

### CapRover Deployment

**Setup Steps**:
1. Create PostgreSQL service in CapRover dashboard
2. Configure backend app with environment variables
3. Set `DATABASE_HOST=srv-captain--postgres` and `DATABASE_SSL_MODE=disable`
4. Configure frontend app with Vite environment variables

**Key Settings**:
```bash
DATABASE_HOST=srv-captain--postgres  # CapRover internal hostname
DATABASE_SSL_MODE=disable  # CRITICAL: Must be disabled for CapRover
APP_LOG_LEVEL=INFO
CORS_ORIGINS=https://app.captain.yourdomain.com
```

### Managed PostgreSQL Deployment

**AWS RDS Configuration**:
```bash
DATABASE_TYPE=postgresql
DATABASE_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
DATABASE_PORT=5432
DATABASE_SSL_MODE=require  # AWS RDS enforces SSL
```

**Google Cloud SQL / Azure**: Same pattern with `DATABASE_SSL_MODE=require`

### Environment Validation

**Docker Entrypoint Process**:
1. Required variable check (DATABASE_TYPE, HOST, PORT, NAME, USER, PASSWORD, FASTMCP_PORT, JWT_SECRET_KEY)
2. Security validation (JWT secret ≥32 chars)
3. Database connection test (`pg_isready`)
4. Log level conversion (uppercase → lowercase)

**Validation Script**:
```bash
#!/bin/bash
# validate-docker-env.sh
REQUIRED_VARS="DATABASE_TYPE DATABASE_HOST DATABASE_SSL_MODE APP_LOG_LEVEL JWT_SECRET_KEY"

for VAR in $REQUIRED_VARS; do
    if [ -z "${!VAR}" ]; then
        echo "❌ Missing: $VAR"
        exit 1
    fi
done

# Validate JWT secret length
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "❌ JWT_SECRET_KEY too short (need 32+ chars)"
    exit 1
fi
```

---

## Database Migrations

### Migration Strategies

| Strategy | Use When | Advantages |
|----------|----------|------------|
| **Alembic Migrations** ⭐ | Production, staging, team collaboration | Version controlled, rollback support, auto-detection, industry standard |
| **Raw SQL Migrations** | Quick local fixes, testing | Simple, fast, direct SQL control |
| **Database Reset** | Fresh local development, schema redesign | Guaranteed clean state, ORM = truth, fastest approach |

### Alembic Workflow

**Quick Reference**:
```bash
# Create manual migration
python scripts/migrate.py create "remove subtask_count column"

# Auto-generate migration (recommended)
python scripts/migrate.py auto "detected changes"

# Apply all pending
python scripts/migrate.py upgrade head

# Rollback one
python scripts/migrate.py downgrade -1

# View history
python scripts/migrate.py history
```

**Auto-Generate Workflow**:
```bash
# 1. Update ORM models first (e.g., remove field from models.py)
# 2. Auto-generate migration
python scripts/migrate.py auto "remove subtask_count column"

# 3. Review generated file in alembic/versions/
# 4. Apply migration
python scripts/migrate.py upgrade head
```

**Migration File Example**:
```python
def upgrade() -> None:
    op.drop_column('tasks', 'subtask_count')

def downgrade() -> None:
    op.add_column('tasks',
        sa.Column('subtask_count', sa.Integer(), nullable=False, server_default='0')
    )
```

### Raw SQL Migration

```bash
# Create SQL file
nano migrations/remove_subtask_count_column.sql

# Apply migration (tracks in schema_migrations table)
python scripts/apply_migration.py migrations/remove_subtask_count_column.sql

# List applied migrations
python scripts/apply_migration.py --list
```

### Database Reset (Development Only)

```bash
# Complete fresh start (ALL DATA LOST)
python scripts/reset_database.py
# Type RESET to confirm
```

**When to Reset vs Migrate**:
- Local development solo: Reset ✅
- Shared development: Migrate ✅
- Staging/Production: Migrate ✅ Required
- Need preserve data: Migrate ✅

### Best Practices

**✅ DO**:
1. Review auto-generated migrations before applying
2. Test migrations locally first (upgrade + downgrade + re-upgrade)
3. Write descriptive messages: `"add user_preferences table with jsonb column"`
4. Always include downgrade logic
5. Commit migrations to git

**❌ DON'T**:
1. Edit applied migrations (create new one instead)
2. Skip migration testing
3. Trust auto-generate blindly
4. Forget backups in production: `pg_dump agenthub > backup_before_migration.sql`

---

## Monitoring & Performance

### Monitoring System

**Key Metrics Tracked**:

| Metric | Warning | Critical | Purpose |
|--------|---------|----------|---------|
| `api_response_time` | >500ms | >1000ms | API health endpoint response |
| `timestamp_task_creation_avg` | >500ms | >1000ms | Task creation performance |
| `system_cpu_utilization` | >75% | >90% | CPU usage |
| `system_memory_utilization` | >80% | >90% | Memory usage |
| `api_availability` | <100% | 0% | Service uptime |

**Monitoring Stack**:
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards (port 3001)
- **Loki + Promtail**: Centralized logging
- **Custom Monitor**: `timestamp_health_monitor.py` (port 8080 dashboard)

**Quick Start Monitoring**:
```bash
# Navigate to monitoring directory
cd monitoring

# Automated setup
./setup_monitoring.sh

# Start monitoring
./start_monitoring.sh

# Start dashboard
./start_dashboard.sh

# Access dashboard: http://localhost:8080
```

### Performance Tuning

**PostgreSQL Configuration**:
```conf
# Memory settings
shared_buffers = 512MB                  # 25% of RAM
effective_cache_size = 2GB              # 50-75% of RAM
work_mem = 8MB                          # RAM / max_connections / 2
maintenance_work_mem = 128MB            # RAM / 8

# Checkpoint settings
checkpoint_completion_target = 0.9
checkpoint_timeout = 30min
max_wal_size = 8GB

# Query performance
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage
max_connections = 200
```

**Connection Pool Optimization**:
```python
# Database connection pool settings
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

**Indexing Strategy**:
```sql
-- Create indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_tasks_user_id_status ON tasks(user_id, status);
CREATE INDEX CONCURRENTLY idx_projects_user_id_created_at ON projects(user_id, created_at);
CREATE INDEX CONCURRENTLY idx_git_branches_project_id ON git_branches(project_id);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_tasks_complex ON tasks(project_id, status, priority, created_at);
```

**Identify Slow Queries**:
```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1 second
SELECT pg_reload_conf();

-- Find slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Caching Implementation**:
```python
import redis
from functools import lru_cache

# Redis cache client
cache_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_connect_timeout=5
)

# LRU cache for frequently accessed data
@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str) -> List[str]:
    """Cache user permissions for 5 minutes."""
    pass
```

**Performance Baselines**:
- API Response Time: <2 seconds (95th percentile)
- Database Query Time: <500ms average
- Memory Usage: <80% of allocated
- CPU Usage: <70% average, <90% peak
- Error Rate: <0.1%
- Throughput: >1000 requests/minute

---

## Keycloak & Authentication

### Keycloak Setup

**PostgreSQL Integration**:
```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: agenthub_user
      KC_DB_PASSWORD: ${KEYCLOAK_DB_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    command: start-dev  # Use 'start' for production
    ports:
      - "8080:8080"
```

**Realm Configuration**:
- Name: `mcp` (or custom)
- Display Name: "agenthub"
- Token Lifespans:
  - Access Token: 30 minutes
  - Refresh Token: 7 days
  - SSO Session Idle: 30 minutes
  - SSO Session Max: 10 hours

**Client Configuration**:
```
Client ID: mcp-backend
Protocol: openid-connect
Access Type: confidential
Standard Flow: ON
Direct Access Grants: ON
Service Accounts: ON
Valid Redirect URIs: http://localhost:8000/*
```

**Environment Variables**:
```bash
KEYCLOAK_URL=https://your-keycloak-instance.cloud.com
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
KEYCLOAK_VERIFY_TOKEN_AUDIENCE=true
KEYCLOAK_TOKEN_CACHE_TTL=300
KEYCLOAK_SSL_VERIFY=true
```

---

## Maintenance Procedures

### Regular Maintenance Schedule

**Daily**:
- Monitor dashboard alerts
- Review error logs
- Check system resource usage
- Validate backup completion

**Weekly**:
- Review performance metrics
- Update security patches
- Test backup restoration
- Review access logs

**Monthly**:
- Security audit review
- Performance optimization
- Capacity planning review
- Documentation updates

### Backup Procedures

**Database Backups**:
```bash
# Create production backup
./scripts/backup-production.sh

# Verify backup integrity
./scripts/verify-backup.sh

# Manual backup
pg_dump -Fc agenthub > backup.dump

# Restore
pg_restore -d agenthub backup.dump
```

**Configuration Backups**:
- Environment variables (`.env` files)
- SSL certificates
- Docker configurations
- Monitoring configurations

### Scaling Procedures

**Horizontal Scaling**:
```bash
# Scale MCP backend
docker-compose -f docker-system/docker-compose.production-enhanced.yml \
    up -d --scale mcp-backend=3
```

**Vertical Scaling**:
- Update resource limits in Docker Compose
- Adjust database configuration
- Monitor performance impact

---

## Troubleshooting

### Common Issues

**SSL Connection Issues**:
```bash
# CapRover: Set SSL mode to disable
DATABASE_SSL_MODE=disable

# Managed Services: Ensure SSL is required
DATABASE_SSL_MODE=require

# Certificate verification failed: Use require instead of verify-ca
DATABASE_SSL_MODE=require
```

**Database Connection Issues**:
```bash
# Test connectivity
pg_isready -h ${DATABASE_HOST} -p ${DATABASE_PORT} -U ${DATABASE_USER}

# Check logs
docker-compose logs postgres

# CapRover: Verify service name
DATABASE_HOST=srv-captain--postgres
```

**Migration Issues**:
```bash
# Check current version
python scripts/migrate.py current

# Apply pending migrations
python scripts/migrate.py upgrade head

# Migration failed mid-way
python scripts/migrate.py downgrade -1
# Fix migration file
python scripts/migrate.py upgrade head
```

**High Memory Usage**:
```bash
# Check container memory usage
docker stats

# Identify memory leaks
docker-compose exec mcp-backend top

# Check database size
SELECT pg_size_pretty(pg_database_size('agenthub'));
```

**Authentication Failures**:
```bash
# Check Keycloak connectivity
curl -f ${KEYCLOAK_URL}/auth/realms/agenthub/.well-known/openid-configuration

# Verify JWT configuration
grep JWT_SECRET_KEY .env

# Check JWT secret length (must be ≥32 chars)
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
    echo "JWT_SECRET_KEY too short"
fi
```

### Emergency Procedures

**1. Critical Service Down**:
1. Check service logs
2. Restart affected service
3. If restart fails, rollback
4. Notify stakeholders
5. Investigate root cause

**2. Database Issues**:
1. Check database connectivity
2. Review database logs
3. Verify disk space
4. Restore from backup if needed
5. Document incident

**3. Complete System Reset** (Development Only):
```bash
# WARNING: Destroys all data
docker-compose down -v
docker volume prune -f
docker-compose build --no-cache
docker-compose up -d
python scripts/init_database.py
```

### Log Locations

- **Application Logs**: `logs/`
- **Docker Logs**: `docker-compose logs [service]`
- **System Logs**: `/var/log/`
- **Nginx Logs**: `/var/log/nginx/`
- **Database Logs**: Docker volume `postgres_logs`
- **Monitoring Logs**: `monitoring/timestamp_monitor.log`

### Health Check Commands

```bash
# All services
curl http://localhost:8000/health
curl http://localhost:8080/health  # Keycloak
curl http://localhost:3800  # Frontend

# Database
psql -h localhost -U agenthub_user -d agenthub -c "SELECT 1;"

# System resources
docker stats
SELECT count(*) FROM pg_stat_activity;  # Database connections
```

---

## Security Considerations

### Access Control
- Production access limited to authorized personnel
- Multi-factor authentication required
- Regular access review and revocation

### Data Protection
- All data encrypted at rest and in transit
- Regular security scans and updates
- Compliance with data protection regulations

### Network Security
- Firewall rules restricting access
- VPN access for administrative functions
- Regular security audits

### Rate Limiting
Enhanced rate limiting implemented:
- User-based: 60 requests per 5 minutes
- Authentication: 10 attempts per 5 minutes
- Global: 100 requests per second

---

## Related Documentation
- [Complete Setup Guide](../setup-guides/complete-setup-guide.md)
- [Complete Authentication Guide](../authentication/complete-authentication-guide.md)
- [Complete Troubleshooting Guide](../troubleshooting-guides/complete-troubleshooting-guide.md)
