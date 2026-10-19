# Complete Operations Guide - agenthub Platform

## Quick Reference

| Operation | Command | Use Case |
|-----------|---------|----------|
| **Deploy production** | *struck 2026-10-09: the script was deleted in commit `1c7b6631` and no in-tree replacement exists* | Full production deployment (`scripts/deployment/deploy-production.sh`) |
| **Deploy frontend** | push to the `frontend` branch -> the CapRover GitHub webhook builds it; a webhook 200 is delivery, not a build - prove the served `/assets/index-<hash>.js` matches HEAD (see *Frontend deploy path*) | Ship the React dashboard (`agenthub-frontend`) to production |
| **Health check** | *struck 2026-10-09: deleted in commit `1c7b6631`, same as above* | Verify system health (`scripts/deployment/health-checks/comprehensive-health-check.sh`) |
| **Rollback** | *struck 2026-10-09: deleted in commit `1c7b6631`, same as above* | Revert failed deployment (`scripts/deployment/rollback/rollback-production.sh`) |
| **Apply migration** | `AUTO_MIGRATE=true ./agenthub` (Go `CreateTables` + startup auto-migrations) | Update database schema |
| **Database reset** | Drop/recreate the database, then boot with `AUTO_MIGRATE=true` | Fresh local development |
| **Monitor metrics** | `curl -sS http://localhost:8000/ws/metrics` — the Go server's own metrics surface, in Prometheus text format from its in-process registry; **no Prometheus or Grafana stack is defined by this repository** | Track system performance |

> **STRUCK 2026-10-09: the deployment scripts this guide names were deleted in commit `1c7b6631` (2026-10-09 22:48:34 +0200), and nothing in the tree replaces them.** That commit removed 33 paths; among them are `scripts/deployment/deploy-production.sh`, `scripts/deployment/health-checks/comprehensive-health-check.sh`, `scripts/deployment/health-checks/smoke-tests.sh`, `scripts/deployment/rollback/rollback-production.sh` and `.github/workflows/production-deployment.yml`. The deletion is **committed**: `git status --porcelain -- scripts/deployment/ .github/workflows/` is empty, and `git show HEAD:scripts/deployment/deploy-production.sh` fails with *does not exist in 'HEAD'*. This guide's invocations of those paths — the three table rows above, the two named in *Deployment Execution*, and the automatic and manual rollback commands — are all struck, and none is runnable. `scripts/deployment/security/apply-security-fixes.sh`, named by the first command under *Deployment Execution*, was deleted earlier in `d1114170`; across both commits `scripts/deployment/` carries exactly two files now, `caprover-env-setup.sh` and `force-caprover-rebuild.sh`. **No replacement is named here, because the tree has none:** `4genteam --help` lists no deploy, rollback or health-check verb, so the client package is not their moved home. The CapRover paths that do exist are named below: `scripts/deploy-frontend.sh`, `docker-system/deployment-manager.sh` and the root `captain-definition.backend` / `captain-definition.frontend`.

---

## Production Deployment

### Deployment Checklist

| Category | Requirements |
|----------|-------------|
| **Security** | SSL certificates valid, JWT secrets rotated, rate limiting tested, security headers configured |
| **Infrastructure** | Servers provisioned, Docker installed, firewall configured, backup systems operational |
| **Testing** | Unit tests passing (150+), integration tests complete, security scans done, load tests validated |

### CI/CD Pipeline

**GitHub Actions workflows, as the repository defines them** (`.github/workflows/`):

- **`production-deployment.yml`** — triggered by a push to `main`, a `v*.*.*` tag, or a manual
  dispatch (with an `environment` choice of `production` or `staging`). Jobs: **Security Scan**
  (Trivy, results uploaded as SARIF to the Security tab) → **Build Images** (backend and
  frontend) → **Deploy to Staging** → **Deploy to Production**. **DATED NOTE 2026-10-09, corrected 2026-10-19: that file was deleted in commit `1c7b6631` and is absent at HEAD (`git show HEAD:.github/workflows/production-deployment.yml` fails with *does not exist in 'HEAD'*; `git status --porcelain -- .github/workflows/` is empty). This paragraph describes the workflow as it stood at `1c7b6631^`, not the tree.**
- **`test_coverage.yml`** — removed with the Python tree: it only ran the archived Python
  suite (`working-directory: agenthub_main`). **CORRECTED 2026-10-10 (writer seat): this read "No workflow now runs Go or frontend tests.", and that is FALSE of this tree — `.github/workflows/ci.yml` runs both, and it is the only workflow left in the directory.** See the next item.

**`ci.yml` is the workflow that runs the code's own suites, and it is the only file in `.github/workflows/` (measured 2026-10-19: `ls .github/workflows/` lists `ci.yml` alone).** It has two jobs, each declaring its `working-directory` — `ci.yml:13` (`agenthub_go`) and `ci.yml:36` (`agenthub-frontend`). The **`go`** job (`:9-30`) checks out with `fetch-depth: 0` (`:18-20`, the repoguards witness reads history), then runs `../scripts/gofmt-check.sh` (`:28`), `go vet ./...` (`:29`) and `go test ./...` (`:30`). The **`frontend`** job (`:32-51`) runs `pnpm install --frozen-lockfile` (`:47`), `pnpm typecheck` (`:48`), `pnpm lint` (`:49`), `pnpm test` (`:50`) and `pnpm build` (`:51`). Triggers are a push to `main` or a pull request (`:3-6`). **CORRECTED 2026-10-19 (architect seat): the line numbers above moved when gofmt, typecheck and lint joined the jobs; they are re-measured at `5c254778`.** **CORRECTED 2026-10-10 (writer seat): the paragraph here read "**Two facts about that pipeline worth stating in the operations manual:** neither workflow installs or runs Go, and neither runs the frontend test runner — so a green pipeline says nothing about whether the shipped server passes its tests."** Both halves were true of the two workflows it described and FALSE of the repository, because it did not name `ci.yml` at all. What survives, stated precisely rather than dropped: **the `go` job declares no PostgreSQL service, so the tests gated on `AGENTHUB_TEST_PG_URL` SKIP in CI — and this repository's own rule is that a skip is not a pass (the same reading is recorded for the ledger tests at `NEXT_GEN.md` O1a).** So a green `ci.yml` is evidence that the Go unit tests and the frontend suite pass, and is NOT evidence about the PostgreSQL-backed tests. The de-link of the archived tree from CI is tracked in `agenthub_go/NEXT_GEN.md` (directive 6).

### Deployment Execution

```bash
# 1. Pre-deployment validation
#    STRUCK 2026-10-09: scripts/deployment/security/apply-security-fixes.sh was deleted in
#    d1114170 and nothing replaces it.

# 2. Execute deployment and 4. Health checks: STRUCK 2026-10-09.
#    scripts/deployment/deploy-production.sh and
#    scripts/deployment/health-checks/comprehensive-health-check.sh are absent from the
#    HEAD (deleted in 1c7b6631), and no in-tree replacement
#    exists — see the note under the Quick Reference table.

# 3. Monitor deployment
docker-compose -f docker-system/docker/docker-compose.production.yml logs -f
```

### Infrastructure Components

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| PostgreSQL | Primary database (production container `srv-captain--4genthubdb`) | 5432 | `pg_isready` |
| Go backend (`cmd/agenthub`) | API, WebSocket and MCP server | 8000 (`FASTMCP_PORT`) | `GET /health` |
| Frontend | React dashboard (dev `npm run dev`) | 3800 | — |
| Reverse proxy | CapRover's nginx terminates TLS in production | 80/443 | — |

> Earlier revisions of this guide listed **Redis**, **Prometheus** and **Grafana** rows here, and a `timestamp_health_monitor.py` dashboard elsewhere. **None of those components is defined by this repository**: there is no `monitoring/` directory (`git ls-files monitoring/` → 0), and the Go module carries no Redis client (`fastmcp/server/session_store.go:23` sets `zpSessionRedisAvailable = false`). They are not part of this deployment as the repository describes it. **CORRECTED 2026-10-09 (writer seat): the Quick Reference row above still read `http://localhost:9090 (Prometheus)` while this note said the repository defines no Prometheus — one file contradicting itself, which tells a reader less than a stale path does, because neither half can be trusted. The row now names the surface that exists (`GET /ws/metrics` on the Go server, Prometheus text format from the in-process registry), so the two halves agree.**

### Rollback Procedures

**Automatic Rollback** (CI/CD triggered) and **Manual Rollback** were both `./scripts/deployment/rollback/rollback-production.sh` invocations: `--environment production --auto-confirm` for the first, and `--environment production` with an optional `--version v1.2.3` for the second. **STRUCK 2026-10-09 — that script was deleted in commit `1c7b6631` and no in-tree replacement exists** (see the note under the Quick Reference table). The commands are removed rather than left to be run.

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

### Frontend deploy path (measured 2026-10-19)

The frontend ships on its own line, the `frontend` branch (`main` and `frontend` are separate branches
that merge periodically), and not from a script: a push to `frontend` fires the GitHub push webhook
that CapRover's app `4genthub-frontend` builds, and nothing in this repository runs the build.
Measured 2026-10-19 (the lead's deploy walk, re-read here): the push of `408a304c` (authored 17:01:36Z)
at 17:11Z returned **200 Delivered** on the webhook and built nothing; the re-trigger at 17:56Z produced
the build that began serving at 18:03:24Z (`/assets/index-BAhshU-p.js`). A build runs about 4-11
minutes (04:35Z trigger -> live 04:46Z; 17:56Z -> 18:03Z), and a trigger can be lost silently while the
webhook still answers 200.

**A webhook 200 is delivery, not a build.** It says CapRover accepted the event; it says nothing about
whether an image was built, was deployed, or is serving. Two surfaces answer that: the frontend app's
build log in the CapRover dashboard (a build has a start line and an end line), and the served entry -
its `Last-Modified` must move past the push, and the entry chunk's hash is the one Vite wrote into the
build's own `index.html`.

```bash
# Did the deploy you pushed actually serve? The served entry's Last-Modified moves past the push time.
curl -sI https://www.4genthub.com/ | grep -i last-modified
# Which build is live? The entry chunk is the script the page loads.
curl -s https://www.4genthub.com | grep -o '<script[^>]*src="/assets/index-[A-Za-z0-9_-]*\.js"'
# The same hash in a local build of HEAD proves the live app IS that build (exit 0 = identity):
python3 scripts/check_served_frontend.py --base-url https://www.4genthub.com \
    --expect-dist agenthub-frontend/build
```

When the 200 is followed by no build, re-trigger from the CapRover app's deployment tab, wait for the
build log's end line, and re-run the checks. A 200 on its own is not a deploy report.

**The build definition is a suffixed file, and the app's choice of it is not in the repository.**
CapRover reads `captain-definition` from the branch root, and `origin/frontend` carries no such file -
only three suffixed variants, `captain-definition.backend`, `captain-definition.backend.go` and
`captain-definition.frontend`; which of them the app reads is a CapRover app setting. The frontend one
names `docker-system/docker/Dockerfile.frontend.production` - a multi-stage node:20-alpine build that
exists at HEAD and on `origin/frontend`. `agenthub-frontend/captain-definition` is a second, stale
definition: it names `./Dockerfile.production`, absent at HEAD and on `origin/frontend` (`9787bce2`
introduced it), and `scripts/deploy-frontend.sh`, the image-push variant of this path, stops at that
same missing file (`:110`). Until a root `captain-definition` exists, the repository cannot say which
definition a given build used; the CapRover app configuration holds the answer.

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

The live backend is the Go service (`agenthub_go`), which is PostgreSQL-only and creates
its schema from Go table metadata (`database.Tables`,
`fastmcp/task_management/infrastructure/database/models.go`). There is **no Alembic, no
SQLAlchemy and no `scripts/migrate.py`**; the Python migration tooling described in earlier
revisions of this guide was retired with the Python backend.

### Schema Creation and Startup Migrations

All DDL is opt-in via `AUTO_MIGRATE=true`. On startup the Go binary (`cmd/agenthub`) calls
`database.InitDatabase`, which:

- without `AUTO_MIGRATE=true` validates the connection, leaves the existing schema
  untouched, and logs the tables it is missing;
- with `AUTO_MIGRATE=true` calls `CreateTables` (creates the registered tables) and runs
  the automatic startup migrations in `auto_migration.go`.

```bash
# Create/update the schema at startup
AUTO_MIGRATE=true ./agenthub

# Normal boot (no DDL; missing tables are logged)
./agenthub
```

### Adding a Table or Column

1. Update the Go model/TableDef metadata (`models.go`, `models_prod.go`,
   `seat_tables.go`) or the seat DDL
   (`fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql`).
2. Add any backfill/rename step to the Go auto-migration runner (`auto_migration.go`).
3. Boot once with `AUTO_MIGRATE=true` and verify with `\dt` or the verification queries.

### Raw SQL

One-off changes can be applied directly with `psql`, but they live outside the Go metadata
and must be reflected in the models afterwards so `CreateTables` and the runtime agree.

```bash
psql "$DATABASE_URL" -f migrations/your_change.sql
```

### Database Reset (Development Only)

```bash
# Drop and recreate the database, then let the Go server create the schema
dropdb agenthub && createdb agenthub
AUTO_MIGRATE=true ./agenthub
```

**When to Reset vs Migrate**:
- Local development solo: Reset ✅
- Shared development: `AUTO_MIGRATE=true` boot ✅
- Staging/Production: `AUTO_MIGRATE=true` boot ✅ Required
- Need preserve data: apply DDL with a backup in place ✅

### Best Practices

**✅ DO**:
1. Keep Go table metadata and any raw SQL change in sync
2. Test a fresh `AUTO_MIGRATE=true` boot and a boot against an existing database
3. Back up production before applying DDL: `pg_dump agenthub > backup_before_migration.sql`
4. Commit schema changes together with the Go metadata that defines them

**❌ DON'T**:
1. Run DDL in production without a tested backup
2. Assume a default boot changes the schema — it does not without `AUTO_MIGRATE=true`
3. Leave raw SQL changes that the Go metadata does not know about
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

**Monitoring, as this repository actually provides it**:
- **`GET /health`** — liveness plus the deployed version (the deploy-confirmation signal).
- **`GET /ws/metrics`** — WebSocket connection metrics (`fastmcp/server/httpapp/misc_mount.go:73`).
- **Performance metrics** — `GET /api/v1/performance/metrics/overview`, `/timeseries` and `/alerts`.
- **PostgreSQL** — the `pg_stat_statements` queries below.

> The Prometheus/Grafana/Loki stack and the `timestamp_health_monitor.py` dashboard described
> in earlier revisions **are not in this repository**: there is no `monitoring/` directory
> (`git ls-files monitoring/ | wc -l` → 0), so those instructions describe tooling that ships
> elsewhere or not at all.

**Quick Start Monitoring**:
```bash
# Liveness and the deployed version
curl -sS http://localhost:8000/health

# WebSocket metrics
curl -sS http://localhost:8000/ws/metrics

# Performance metrics
curl -sS http://localhost:8000/api/v1/performance/metrics/overview
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
The Go server manages its PostgreSQL pool through `database/sql`; the Supabase pool defaults
are `pool_size=3`, `max_overflow=7`, `pool_recycle=300s`, `pool_timeout=10s`
(`fastmcp/task_management/infrastructure/database/connection_pool.go`). Tune the pool in use
and restart the backend; there is no SQLAlchemy engine to configure.

**Indexing Strategy**:
```sql
-- Create indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_tasks_user_id_status ON tasks(user_id, status);
CREATE INDEX CONCURRENTLY idx_projects_user_id_created_at ON projects(user_id, created_at);
CREATE INDEX CONCURRENTLY idx_project_git_branchs_project_id ON project_git_branchs(project_id);

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

**Caching**: the Go server's performance cache is **in-process**; `POST /api/v1/performance/metrics/clear-cache`
(`routes.ClearPerformanceCache`, `fastmcp/server/routes/performance_metrics_routes.go:438`) clears it,
and the module has **no Redis client** (`go.mod` lists no redis dependency; `fastmcp/task_management/infrastructure/repositories/cached/cache_client.go:7-8`
says the same and injects `CacheClient` with `MemoryCache` as the in-process implementation). Earlier revisions of this guide showed a Python
`redis.Redis` client for the retired Python backend — it is not part of the live stack.

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
docker-compose -f docker-system/docker/docker-compose.production.yml \
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
# Was DDL enabled? The schema is only created/altered with AUTO_MIGRATE=true
grep AUTO_MIGRATE .env

# A normal boot logs the tables the schema is missing
./agenthub | grep -i "missing table"

# Re-run schema creation/migrations at startup
AUTO_MIGRATE=true ./agenthub
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
# Create the Postgres schema, then serve (from agenthub_go/)
AUTO_MIGRATE=true ./agenthub
```

### Log Locations

- **Application Logs**: `logs/`
- **Docker Logs**: `docker-compose logs [service]`
- **System Logs**: `/var/log/`
- **Nginx Logs**: `/var/log/nginx/`
- **Database Logs**: Docker volume `postgres_logs`
- **Server Logs**: the Go server's stdout/stderr (the container log, e.g. `docker logs <container>`)

### Health Check Commands

```bash
# Backend (the deployed version is what /health reports)
curl http://localhost:8000/health

# Frontend
curl http://localhost:3800

# Database (local defaults from .env.sample: database agenthub, role postgres;
# production is database postgresdb in container srv-captain--4genthubdb)
psql -h localhost -U postgres -d agenthub -c "SELECT 1;"

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
