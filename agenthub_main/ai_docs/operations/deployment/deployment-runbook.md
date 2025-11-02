# Agent Management System - Deployment Runbook

**Version**: 2.0.0
**Last Updated**: 2025-11-02
**System**: User-Specific Agent Management with Sharing Features

## Overview

This runbook provides step-by-step deployment procedures for the agent management system including database migrations, template population, and system verification.

**Deployment Scope**:
- 4 new database tables (agent_templates, user_agent_instances, user_agent_configurations_md, agent_import_history)
- 42+ agent templates from agent-library
- 12 new REST API endpoints
- New MCP tool (`call_agent` v2.0)
- Frontend components (agent management UI)

**Estimated Deployment Time**: 30-45 minutes
**Downtime**: Zero (rolling deployment)

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Database Migration](#database-migration)
3. [Template Population](#template-population)
4. [Application Deployment](#application-deployment)
5. [Verification](#verification)
6. [Rollback Procedure](#rollback-procedure)
7. [Post-Deployment Tasks](#post-deployment-tasks)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Prerequisites

**Environment Verification**:
- [ ] Production database backup completed (within last 24 hours)
- [ ] Staging deployment successful
- [ ] All tests passing (unit, integration, E2E, security)
- [ ] Performance tests validated (<500ms P95 first call, <100ms cached)
- [ ] Security audit reviewed (no critical issues)
- [ ] Documentation updated

**Access Requirements**:
- [ ] Database admin credentials
- [ ] Application server SSH access
- [ ] Container registry access (Docker Hub / AWS ECR)
- [ ] Environment variable management access (AWS Secrets Manager / Vault)
- [ ] Monitoring dashboard access (Grafana / DataDog)

**Team Coordination**:
- [ ] Deployment window scheduled (off-peak hours recommended)
- [ ] Team notified (engineering, support, QA)
- [ ] On-call engineer available for rollback
- [ ] Communication channel open (Slack #deployments)

### Pre-Deployment Commands

```bash
# 1. Verify current system health
curl https://api.production.com/health
# Expected: {"status": "healthy", "version": "1.x.x"}

# 2. Check database connectivity
psql -h production-db.example.com -U agenthub_user -d agenthub -c "SELECT version();"

# 3. Verify application version
docker ps | grep agenthub
# Note current image tag for rollback

# 4. Check disk space (need 5GB+ free)
df -h /var/lib/postgresql

# 5. Verify backup exists
aws s3 ls s3://agenthub-backups/postgres/ --recursive | tail -5
```

---

## Database Migration

### Step 1: Backup Current Database

```bash
# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -h production-db.example.com \
        -U agenthub_user \
        -d agenthub \
        -F c \
        -f "backup_pre_agent_mgmt_${TIMESTAMP}.dump"

# Verify backup size (should be >100MB)
ls -lh backup_pre_agent_mgmt_${TIMESTAMP}.dump

# Upload to S3
aws s3 cp backup_pre_agent_mgmt_${TIMESTAMP}.dump \
         s3://agenthub-backups/postgres/pre-deployment/
```

**Verification**:
```bash
# Download and verify backup
aws s3 cp s3://agenthub-backups/postgres/pre-deployment/backup_pre_agent_mgmt_${TIMESTAMP}.dump \
         /tmp/verify_backup.dump
pg_restore --list /tmp/verify_backup.dump | head -20
```

### Step 2: Run Database Migrations

```bash
# SSH to application server
ssh production-app-01

# Navigate to application directory
cd /opt/agenthub/agenthub_main

# Activate virtual environment
source .venv/bin/activate

# Check current migration version
alembic current
# Expected: previous migration hash (e.g., abc123def456)

# Show pending migrations
alembic history
# Should show new agent management migration

# Run migration (DRY RUN first)
alembic upgrade head --sql > /tmp/migration_preview.sql
cat /tmp/migration_preview.sql
# Review SQL before actual execution

# Execute migration
alembic upgrade head

# Verify migration success
alembic current
# Expected: new migration hash (e.g., xyz789abc012)

# Check tables created
psql -h production-db.example.com -U agenthub_user -d agenthub -c "\dt agent*"
# Expected: agent_templates, user_agent_instances, user_agent_configurations_md, agent_import_history
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade abc123def456 -> xyz789abc012, add agent management tables
```

**Rollback Point**: If migration fails, see [Rollback Procedure](#rollback-procedure)

### Step 3: Verify Database Schema

```bash
# Check table structure
psql -h production-db.example.com -U agenthub_user -d agenthub << 'EOF'
-- Verify agent_templates table
\d agent_templates

-- Verify indexes
\di agent_templates*

-- Verify foreign keys
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f' AND conrelid::regclass::text LIKE '%agent%';

-- Check constraints
SELECT conname, contype, consrc
FROM pg_constraint
WHERE conrelid = 'user_agent_instances'::regclass;
EOF
```

---

## Template Population

### Step 1: Verify Agent Library

```bash
# Check agent-library directory exists
ls -la /opt/agenthub/agenthub_main/agent-library/agents/
# Expected: 42+ agent directories

# Count agents
ls -l /opt/agenthub/agenthub_main/agent-library/agents/ | grep ^d | wc -l
# Expected: 42 (or current count)

# Verify YAML structure for sample agent
cat agent-library/agents/coding-agent/metadata.yaml
cat agent-library/agents/coding-agent/contexts/instructions.yaml
```

### Step 2: Run Population Script

```bash
# Navigate to scripts directory
cd /opt/agenthub/agenthub_main

# Run population script (idempotent - safe to re-run)
python scripts/populate_agent_templates.py --dry-run

# Review output
# Expected: "Would create/update X templates"

# Execute for real
python scripts/populate_agent_templates.py

# Monitor output
# Expected: "✓ Loaded coding-agent (version 2.0.0)"
#           "✓ Loaded test-orchestrator-agent (version 2.0.0)"
#           ...
#           "Successfully loaded 42 agent templates"
```

**Script Output Example**:
```
🚀 Agent Template Population Script
📁 Loading from: /opt/agenthub/agenthub_main/agent-library/agents

Processing agents...
  ✓ coding-agent (v2.0.0) - Created
  ✓ test-orchestrator-agent (v2.0.0) - Created
  ✓ debugger-agent (v2.0.0) - Created
  ...
  ↻ documentation-agent (v2.0.0) - Updated (already exists)

📊 Summary:
  - Created: 40 templates
  - Updated: 2 templates
  - Failed: 0
  - Total: 42 templates

✅ Population completed successfully!
```

### Step 3: Verify Template Data

```bash
# Check template count
psql -h production-db.example.com -U agenthub_user -d agenthub -c \
  "SELECT COUNT(*) FROM agent_templates;"
# Expected: 42 (or current count)

# List all templates
psql -h production-db.example.com -U agenthub_user -d agenthub -c \
  "SELECT slug, name, category, version FROM agent_templates ORDER BY category, slug;"

# Verify sample template configuration
psql -h production-db.example.com -U agenthub_user -d agenthub -c \
  "SELECT slug, default_configuration->>'instructions'
   FROM agent_templates
   WHERE slug='coding-agent';"

# Check for missing templates
python -c "
import json
from pathlib import Path

agent_dir = Path('agent-library/agents')
agent_slugs = {d.name for d in agent_dir.iterdir() if d.is_dir()}
print(f'Agent library count: {len(agent_slugs)}')
"

psql -h production-db.example.com -U agenthub_user -d agenthub -t -c \
  "SELECT COUNT(*) FROM agent_templates;" | xargs echo "Database count:"
```

---

## Application Deployment

### Step 1: Build New Docker Image

```bash
# On build server or CI/CD
cd /path/to/agenthub

# Build backend image
docker build -t agenthub-backend:2.0.0-agent-mgmt \
             -f agenthub_main/Dockerfile \
             agenthub_main/

# Build frontend image
docker build -t agenthub-frontend:2.0.0-agent-mgmt \
             -f agenthub-frontend/Dockerfile \
             agenthub-frontend/

# Tag for registry
docker tag agenthub-backend:2.0.0-agent-mgmt \
           your-registry.com/agenthub-backend:2.0.0-agent-mgmt

docker tag agenthub-frontend:2.0.0-agent-mgmt \
           your-registry.com/agenthub-frontend:2.0.0-agent-mgmt

# Push to registry
docker push your-registry.com/agenthub-backend:2.0.0-agent-mgmt
docker push your-registry.com/agenthub-frontend:2.0.0-agent-mgmt
```

### Step 2: Update Environment Variables

```bash
# Add new environment variables (if any)
# Using AWS Secrets Manager example

aws secretsmanager update-secret \
  --secret-id agenthub/production/env \
  --secret-string '{
    "DATABASE_URL": "postgresql://user:pass@host:5432/agenthub",
    "AGENT_LIBRARY_PATH": "/app/agent-library",
    "ENABLE_AGENT_MARKETPLACE": "true",
    "MAX_AGENT_IMPORT_PER_MINUTE": "10"
  }'
```

**Required Environment Variables**:
```bash
# Core application
DATABASE_URL=postgresql://user:pass@host:5432/agenthub
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key

# Agent management specific
AGENT_LIBRARY_PATH=/app/agent-library
ENABLE_AGENT_MARKETPLACE=true
MAX_AGENT_IMPORT_PER_MINUTE=10
SHARE_TOKEN_EXPIRY_DAYS=365
```

### Step 3: Rolling Deployment

**For Docker Swarm**:
```bash
# Update service with new image
docker service update \
  --image your-registry.com/agenthub-backend:2.0.0-agent-mgmt \
  --update-parallelism 1 \
  --update-delay 30s \
  --update-failure-action rollback \
  agenthub-backend

# Monitor deployment
docker service ps agenthub-backend --no-trunc

# Verify all replicas updated
docker service ls
```

**For Kubernetes**:
```bash
# Apply new deployment
kubectl set image deployment/agenthub-backend \
  agenthub-backend=your-registry.com/agenthub-backend:2.0.0-agent-mgmt

# Monitor rollout
kubectl rollout status deployment/agenthub-backend

# Verify pods running
kubectl get pods -l app=agenthub-backend
```

**For Plain Docker Compose**:
```bash
# Update docker-compose.yml with new image tags
sed -i 's/image: agenthub-backend:.*/image: agenthub-backend:2.0.0-agent-mgmt/' docker-compose.yml

# Rolling update (one container at a time)
docker-compose up -d --scale backend=2
sleep 30
docker-compose up -d --scale backend=1
```

---

## Verification

### Step 1: Health Check

```bash
# Check application health
curl https://api.production.com/health
# Expected: {"status": "healthy", "version": "2.0.0"}

# Check database connectivity
curl https://api.production.com/health/db
# Expected: {"database": "connected", "migrations": "up-to-date"}
```

### Step 2: API Endpoint Verification

```bash
# Test new agent management endpoints
# Replace YOUR_TOKEN with valid JWT

# List templates
curl -X GET "https://api.production.com/api/v2/agent-management/templates" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: {"templates": [...], "total": 42}

# Test call_agent MCP tool
curl -X POST "https://api.production.com/api/mcp" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "call_agent",
      "arguments": {"name_agent": "coding-agent"}
    }
  }'
# Expected: {"result": {"agent": {"system_prompt": "..."}}}

# Test marketplace
curl -X GET "https://api.production.com/api/v2/agent-management/marketplace/agents?limit=5"
# Expected: {"agents": [], "total": 0} (initially empty)
```

### Step 3: Frontend Verification

```bash
# Open browser to production URL
# Manual verification checklist:

1. Navigate to https://app.production.com/agents
   - [ ] Agent list loads without errors
   - [ ] "Browse Templates" button visible

2. Click "Browse Templates"
   - [ ] All 42 templates displayed
   - [ ] Categories filter working
   - [ ] Search functional

3. Select an agent (e.g., coding-agent)
   - [ ] Configuration editor loads
   - [ ] 4 tabs visible (Instructions, Rules, Capabilities, Output Format)
   - [ ] Markdown content displays correctly

4. Edit and save
   - [ ] Make a small change
   - [ ] Click "Save Configuration"
   - [ ] Success message appears
   - [ ] "Customized" badge shows on agent card

5. Share agent
   - [ ] Click "Share" button
   - [ ] Toggle "Make Public" ON
   - [ ] Share URL generated
   - [ ] Copy to clipboard works

6. Marketplace
   - [ ] Navigate to Marketplace
   - [ ] Shared agent appears in list
   - [ ] Preview modal works
   - [ ] Import button enabled

7. Import test
   - [ ] Click "Import"
   - [ ] Name collision handling (if applicable)
   - [ ] Agent imported successfully
   - [ ] Creator attribution visible
```

### Step 4: Performance Verification

```bash
# Run quick performance check (100 users, 1 minute)
cd /path/to/tests/performance/agent_management

k6 run --vus 100 --duration 1m k6_call_agent_load_test.js

# Expected results:
# - P95 first call < 500ms
# - P95 cached call < 100ms
# - Error rate < 1%
```

### Step 5: Monitoring Dashboard

**Check Metrics** (Grafana / DataDog):
- [ ] API request rate increased (new endpoints)
- [ ] Database query count increased (agent queries)
- [ ] No error spikes
- [ ] Response times within SLA (<500ms P95)
- [ ] Memory usage stable

**Sample Prometheus Queries**:
```promql
# Request rate for new endpoints
rate(http_requests_total{path=~"/api/v2/agent-management/.*"}[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

---

## Rollback Procedure

### When to Rollback

Rollback immediately if:
- ❌ Critical errors in application logs (>10 errors/minute)
- ❌ Database queries failing (connection timeouts)
- ❌ P95 latency >2000ms (4x normal)
- ❌ Error rate >5%
- ❌ Users reporting data loss or corruption

### Rollback Steps

#### 1. Stop New Deployments

```bash
# Docker Swarm
docker service rollback agenthub-backend

# Kubernetes
kubectl rollout undo deployment/agenthub-backend

# Docker Compose
docker-compose down
# Edit docker-compose.yml to previous image tags
docker-compose up -d
```

#### 2. Revert Database Migration

```bash
# Connect to database
psql -h production-db.example.com -U agenthub_user -d agenthub

# Check current migration
SELECT * FROM alembic_version;
# Note current version: xyz789abc012

# Downgrade migration
cd /opt/agenthub/agenthub_main
alembic downgrade -1

# Verify rollback
alembic current
# Expected: previous version (abc123def456)

# Verify tables removed
\dt agent*
# Expected: No tables (or previous state)
```

#### 3. Restore Database from Backup (if needed)

```bash
# Download backup
aws s3 cp s3://agenthub-backups/postgres/pre-deployment/backup_pre_agent_mgmt_${TIMESTAMP}.dump \
         /tmp/restore.dump

# Stop application
docker service scale agenthub-backend=0

# Restore database
pg_restore -h production-db.example.com \
           -U agenthub_user \
           -d agenthub \
           -c \  # Clean existing objects
           /tmp/restore.dump

# Restart application with old version
docker service update \
  --image your-registry.com/agenthub-backend:1.x.x \
  agenthub-backend

docker service scale agenthub-backend=3
```

#### 4. Verify Rollback Success

```bash
# Check health
curl https://api.production.com/health
# Expected: {"status": "healthy", "version": "1.x.x"}

# Verify old functionality works
curl -X GET "https://api.production.com/api/v1/tasks"
# Expected: Normal response

# Check error logs cleared
tail -f /var/log/agenthub/app.log | grep ERROR
# Expected: No critical errors
```

#### 5. Post-Rollback Communication

**Notify Team**:
- [ ] Update #deployments Slack channel
- [ ] Document rollback reason
- [ ] Schedule post-mortem meeting
- [ ] Create incident report

**Template Message**:
```
🔴 ROLLBACK COMPLETED

Deployment: Agent Management v2.0.0
Rollback time: [timestamp]
Reason: [brief description]
Impact: [user impact summary]
Current status: System stable on v1.x.x

Next steps:
- Root cause analysis scheduled for [date/time]
- Fix being prepared
- Retry deployment: TBD
```

---

## Post-Deployment Tasks

### Immediate (Within 1 hour)

- [ ] Monitor error logs for 30 minutes
- [ ] Check user feedback channels (support tickets, Slack)
- [ ] Verify background jobs running (if any)
- [ ] Update deployment log/wiki

### Short-term (Within 24 hours)

- [ ] Review monitoring dashboards
- [ ] Analyze performance metrics
- [ ] Check database growth (disk space)
- [ ] Send deployment summary to stakeholders

### Long-term (Within 1 week)

- [ ] Schedule post-deployment retrospective
- [ ] Update runbook with lessons learned
- [ ] Review and optimize slow queries
- [ ] Plan next iteration improvements

---

## Troubleshooting

### Issue: Migration Fails with "relation already exists"

**Cause**: Database in inconsistent state from previous failed migration

**Solution**:
```bash
# Check alembic version table
psql -h host -U user -d db -c "SELECT * FROM alembic_version;"

# If version is wrong, manually set correct version
psql -h host -U user -d db -c \
  "UPDATE alembic_version SET version_num='abc123def456';"

# Retry migration
alembic upgrade head
```

### Issue: Template Population Fails

**Cause**: YAML parsing error or missing files

**Solution**:
```bash
# Check YAML validity
python -c "
import yaml
from pathlib import Path

agent_dir = Path('agent-library/agents')
for agent_path in agent_dir.iterdir():
    if agent_path.is_dir():
        metadata_file = agent_path / 'metadata.yaml'
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    yaml.safe_load(f)
                print(f'✓ {agent_path.name}')
            except Exception as e:
                print(f'✗ {agent_path.name}: {e}')
"

# Fix invalid YAML files
# Re-run population script
python scripts/populate_agent_templates.py
```

### Issue: High Latency After Deployment

**Cause**: Missing indexes or query optimization needed

**Solution**:
```bash
# Check slow queries
psql -h host -U user -d db -c \
  "SELECT query, calls, mean_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;"

# Add missing indexes
psql -h host -U user -d db << 'EOF'
CREATE INDEX CONCURRENTLY idx_user_agent_instances_user_template
ON user_agent_instances(user_id, template_id);

CREATE INDEX CONCURRENTLY idx_marketplace_public
ON user_agent_instances(visibility, created_at DESC)
WHERE visibility = 'public';
EOF

# Analyze tables
psql -h host -U user -d db -c "ANALYZE agent_templates;"
psql -h host -U user -d db -c "ANALYZE user_agent_instances;"
```

### Issue: Frontend Not Loading Agent List

**Cause**: API endpoint misconfiguration or CORS issues

**Solution**:
```bash
# Check API endpoint
curl -v https://api.production.com/api/v2/agent-management/templates

# Check CORS headers
curl -H "Origin: https://app.production.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Authorization" \
     -X OPTIONS \
     https://api.production.com/api/v2/agent-management/templates

# Expected: Access-Control-Allow-Origin header present

# Verify frontend environment variables
docker exec agenthub-frontend-container env | grep API_URL
# Expected: API_URL=https://api.production.com
```

---

## Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Lead Engineer | [Name] | [Phone/Slack] |
| DevOps Lead | [Name] | [Phone/Slack] |
| DBA | [Name] | [Phone/Slack] |
| On-Call Engineer | Check PagerDuty | #on-call |
| Product Manager | [Name] | [Slack] |

---

## Appendix: Environment Variables Reference

See [environment-variables.md](./environment-variables.md) for complete list.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2025-11-02 | DevOps Team | Initial agent management deployment |
| 1.0.0 | 2025-01-15 | DevOps Team | Initial deployment runbook |
