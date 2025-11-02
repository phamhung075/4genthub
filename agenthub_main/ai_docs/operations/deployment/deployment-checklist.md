# Deployment Checklist - Agent Management System v2.0

**Quick reference checklist for agent management system deployment**

## Pre-Deployment ☐

### Preparation
- [ ] All tests passing (unit, integration, E2E, security, performance)
- [ ] Security audit reviewed (no critical vulnerabilities)
- [ ] Code review completed and approved
- [ ] Staging deployment successful
- [ ] Performance benchmarks met (P95 <500ms first call, <100ms cached)

### Backups
- [ ] Database backup completed and verified (within 24 hours)
- [ ] Backup uploaded to S3/remote storage
- [ ] Backup restoration tested on staging

### Team Coordination
- [ ] Deployment window scheduled and communicated
- [ ] Engineering team notified
- [ ] Support team briefed on new features
- [ ] On-call engineer identified and available
- [ ] Communication channel open (#deployments)

### Access Verification
- [ ] Database admin credentials available
- [ ] Application server SSH access verified
- [ ] Container registry access confirmed
- [ ] Secrets manager access verified (AWS Secrets Manager / Vault)
- [ ] Monitoring dashboard access confirmed

---

## Database Migration ☐

### Pre-Migration
- [ ] Current database version noted: `________________`
- [ ] Disk space verified (>5GB free)
- [ ] Database backup timestamp: `________________`

### Migration Execution
- [ ] Migration SQL reviewed (dry run)
- [ ] Migration executed: `alembic upgrade head`
- [ ] New migration version verified: `________________`
- [ ] Tables created successfully:
  - [ ] `agent_templates`
  - [ ] `user_agent_instances`
  - [ ] `user_agent_configurations_md`
  - [ ] `agent_import_history`
- [ ] Indexes created (11 indexes total)
- [ ] Foreign keys validated

---

## Template Population ☐

### Agent Library
- [ ] Agent library path exists: `/opt/agenthub/agenthub_main/agent-library`
- [ ] Agent count verified: `______ agents` (expected: 42)
- [ ] YAML files validated (no parsing errors)

### Population Script
- [ ] Dry run executed: `python scripts/populate_agent_templates.py --dry-run`
- [ ] Dry run output reviewed: `______ templates to create/update`
- [ ] Script executed: `python scripts/populate_agent_templates.py`
- [ ] Success count: `______ templates loaded`
- [ ] Database count matches: `SELECT COUNT(*) FROM agent_templates;`

---

## Application Deployment ☐

### Docker Images
- [ ] Backend image built: `agenthub-backend:2.0.0-agent-mgmt`
- [ ] Frontend image built: `agenthub-frontend:2.0.0-agent-mgmt`
- [ ] Images pushed to registry
- [ ] Image tags verified in registry

### Environment Variables
- [ ] New variables added to secrets manager:
  - [ ] `AGENT_LIBRARY_PATH`
  - [ ] `ENABLE_AGENT_MARKETPLACE`
  - [ ] `MAX_AGENT_IMPORT_PER_MINUTE`
  - [ ] `SHARE_TOKEN_EXPIRY_DAYS`
- [ ] Environment validated: `python scripts/validate_env.py`

### Rolling Deployment
- [ ] Old version noted for rollback: `________________`
- [ ] Service updated with new image
- [ ] Deployment monitored (zero downtime)
- [ ] All replicas updated successfully
- [ ] Pod/container status: All running

---

## Verification ☐

### Health Checks
- [ ] Application health: `curl /health` → status: healthy
- [ ] Database health: `curl /health/db` → connected
- [ ] Application version: `______ ` (expected: 2.0.0)

### API Endpoints (Manual Testing)
- [ ] List templates: `GET /api/v2/agent-management/templates` → 42 templates
- [ ] Get template: `GET /api/v2/agent-management/templates/coding-agent` → OK
- [ ] List instances: `GET /api/v2/agent-management/instances` → []
- [ ] MCP call_agent: `POST /api/mcp` (call_agent tool) → system_prompt returned
- [ ] Marketplace: `GET /api/v2/agent-management/marketplace/agents` → []

### Frontend Verification
- [ ] Agent list page loads without errors
- [ ] Browse templates displays 42 agents
- [ ] Template selection and instantiation works
- [ ] Configuration editor opens (4 tabs visible)
- [ ] Markdown editing and saving works
- [ ] Share functionality generates token
- [ ] Marketplace page accessible
- [ ] Import flow functional

### Performance Testing
- [ ] Quick load test executed (100 users, 1 min)
- [ ] P95 first call latency: `______ ms` (target: <500ms)
- [ ] P95 cached call latency: `______ ms` (target: <100ms)
- [ ] Error rate: `______ %` (target: <1%)

### Monitoring
- [ ] API request rate increased (new endpoints visible)
- [ ] Database query metrics normal
- [ ] No error spikes in logs
- [ ] Response times within SLA
- [ ] Memory usage stable
- [ ] CPU usage normal

---

## Post-Deployment ☐

### Immediate (Within 1 Hour)
- [ ] Monitor error logs for 30 minutes
- [ ] Check user feedback channels
- [ ] Verify background jobs (if any)
- [ ] Update deployment log

### Short-Term (Within 24 Hours)
- [ ] Review monitoring dashboards
- [ ] Analyze performance metrics
- [ ] Check database growth
- [ ] Send deployment summary to stakeholders

### Communication
- [ ] Deployment announcement sent
- [ ] Documentation updated with new features
- [ ] Support team briefed on common issues
- [ ] Changelog updated

---

## Rollback Criteria ☐

**Rollback immediately if any of the following occur**:

- [ ] Critical errors in logs (>10 errors/minute)
- [ ] Database queries failing consistently
- [ ] P95 latency >2000ms (4x normal)
- [ ] Error rate >5%
- [ ] Users reporting data loss or corruption
- [ ] Application crashes or becomes unresponsive

---

## Rollback Procedure ☐

**Only complete if rollback is necessary**

### Application Rollback
- [ ] Stop new deployments
- [ ] Rollback to previous version: `________________`
- [ ] Service rollback command executed
- [ ] All replicas reverted successfully

### Database Rollback
- [ ] Migration downgraded: `alembic downgrade -1`
- [ ] Current version verified: `________________`
- [ ] OR Database restored from backup: `________________`

### Verification After Rollback
- [ ] Health check: `curl /health` → old version
- [ ] Old functionality working
- [ ] Error logs cleared
- [ ] Users notified

### Post-Rollback
- [ ] Incident report created
- [ ] Root cause analysis scheduled
- [ ] Fix planned
- [ ] Retry deployment: `________________` (date/time)

---

## Sign-Off

| Role | Name | Signature | Date/Time |
|------|------|-----------|-----------|
| **Lead Engineer** | _____________ | _____________ | _____________ |
| **DevOps Lead** | _____________ | _____________ | _____________ |
| **QA Lead** | _____________ | _____________ | _____________ |
| **Product Manager** | _____________ | _____________ | _____________ |

---

## Notes

**Deployment Issues**:
```
(Record any issues encountered during deployment)





```

**Performance Observations**:
```
(Note any performance anomalies or improvements)





```

**Action Items**:
```
(List any follow-up tasks or improvements needed)





```

---

## Related Documents

- [Deployment Runbook](./deployment-runbook.md) - Detailed step-by-step procedures
- [Environment Variables](./environment-variables.md) - Complete variable reference
- [Rollback Plan](./deployment-runbook.md#rollback-procedure) - Emergency rollback guide
- [API Reference](../../api-integration/agent-system/api-reference.md) - API documentation
