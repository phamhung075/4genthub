# Production Deployment Guide - 4genthub Auto-Injection System

## Overview

This comprehensive guide covers the complete production deployment process for the 4genthub Auto-Injection System, including security hardening, monitoring setup, and operational procedures.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Security Hardening](#security-hardening)
3. [Infrastructure Setup](#infrastructure-setup)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Monitoring & Observability](#monitoring--observability)
6. [Deployment Execution](#deployment-execution)
7. [Post-Deployment Validation](#post-deployment-validation)
8. [Rollback Procedures](#rollback-procedures)
9. [Operational Procedures](#operational-procedures)
10. [Troubleshooting](#troubleshooting)

## Pre-Deployment Checklist

### Security Requirements
- [ ] All HIGH security vulnerabilities from audit SA-2025-09-11-001 addressed
- [ ] SSL/TLS certificates configured and valid
- [ ] JWT secrets rotated from default values
- [ ] Database credentials secured
- [ ] Rate limiting implemented and tested
- [ ] Security headers configured

### Infrastructure Requirements
- [ ] Production server(s) provisioned and configured
- [ ] Docker and Docker Compose installed
- [ ] Required environment variables configured
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Backup systems operational
- [ ] Monitoring systems prepared

### Testing Requirements
- [ ] All unit tests passing (150+ tests)
- [ ] Integration tests completed successfully
- [ ] Performance tests validated (40% improvement confirmed)
- [ ] Security scans completed
- [ ] Load testing performed
- [ ] Disaster recovery tested

## Security Hardening

### 1. Apply Security Fixes

The security audit identified 5 HIGH vulnerabilities that must be addressed:

```bash
# Apply all security fixes
./scripts/deployment/security/apply-security-fixes.sh --environment production

# Validate security fixes
./scripts/deployment/security/validate-security-fixes.sh
```

### 2. SSL/TLS Configuration

**Critical:** All SSL verification must be enabled and TLS 1.2+ enforced.

```bash
# Verify SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### 3. Environment Variable Security

Ensure all sensitive values are properly configured:

```bash
# Required secure environment variables
JWT_SECRET_KEY=<64-character-random-string>
DATABASE_PASSWORD=<strong-database-password>
KEYCLOAK_CLIENT_SECRET=<keycloak-client-secret>
REDIS_PASSWORD=<redis-password>
```

### 4. Rate Limiting

Enhanced rate limiting is implemented:
- User-based: 60 requests per 5 minutes
- Authentication: 10 attempts per 5 minutes
- Global: 100 requests per second

## Infrastructure Setup

### Docker Compose Configurations

Three Docker Compose configurations are available:

1. **Basic Production** (`docker-compose.production.yml`)
   - Core services only
   - Suitable for small deployments

2. **Enhanced Production** (`docker-compose.production-enhanced.yml`)
   - Full monitoring stack
   - Security hardening
   - Recommended for production

3. **Development** (`docker-compose.yml`)
   - Development and testing only

### Production Infrastructure Components

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| PostgreSQL | Primary database | 5432 | `pg_isready` |
| Redis | Cache & sessions | 6379 | `redis-cli ping` |
| MCP Backend | API server | 8000 | `/api/v2/health` |
| Frontend | Web interface | 3000 | `/health` |
| Nginx | Reverse proxy | 80/443 | `/health` |
| Prometheus | Metrics collection | 9090 | `/-/healthy` |
| Grafana | Dashboards | 3001 | `/api/health` |

### Network Architecture

```
Internet
    ↓
[Nginx Reverse Proxy] (Port 80/443)
    ↓
[External Network] (172.22.0.0/16)
    ↓
[Frontend] (Port 3000) ←→ [MCP Backend] (Port 8000)
    ↓
[Internal Network] (172.21.0.0/16)
    ↓
[PostgreSQL] (Port 5432) ←→ [Redis] (Port 6379)
    ↓
[Monitoring Stack]
```

## CI/CD Pipeline

### GitHub Actions Workflow

The production deployment pipeline includes:

1. **Security Scanning**
   - Trivy vulnerability scanning
   - Bandit security linting
   - SARIF upload to GitHub Security

2. **Code Quality**
   - Black code formatting
   - isort import sorting
   - flake8 linting
   - mypy type checking

3. **Testing**
   - Unit tests with coverage
   - Integration tests
   - Database migration tests

4. **Build & Push**
   - Docker image builds
   - Container registry push
   - Multi-architecture support

5. **Deployment**
   - Staging deployment (automatic)
   - Production deployment (manual/tagged)
   - Rollback capability

### Deployment Triggers

- **Staging:** Automatic on `main` branch push
- **Production:** Manual workflow dispatch or version tag (`v*.*.*`)
- **Rollback:** Automatic on production deployment failure

### Required Secrets

Configure these GitHub repository secrets:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=<aws-access-key>
AWS_SECRET_ACCESS_KEY=<aws-secret-key>
AWS_ACCESS_KEY_ID_PROD=<prod-aws-access-key>
AWS_SECRET_ACCESS_KEY_PROD=<prod-aws-secret-key>
AWS_REGION=<aws-region>

# Notifications
SLACK_WEBHOOK=<slack-webhook-url>
WEBHOOK_URL=<monitoring-webhook-url>

# Production Environment
PRODUCTION_BACKEND_URL=<prod-backend-url>
PRODUCTION_FRONTEND_URL=<prod-frontend-url>
PRODUCTION_KEYCLOAK_URL=<prod-keycloak-url>
```

## Monitoring & Observability

### Metrics Collection

**Prometheus Metrics:**
- System metrics (CPU, memory, disk)
- Container metrics (cAdvisor)
- Application metrics (custom)
- Database metrics (PostgreSQL)
- Cache metrics (Redis)

**Key Metrics Tracked:**
- Request latency and throughput
- Error rates by endpoint
- Authentication success/failure rates
- MCP operation metrics
- Resource utilization

### Alerting Rules

Critical alerts configured:
- Service downtime (1 minute)
- High error rates (>10% for 2 minutes)
- Database connectivity issues
- SSL certificate expiration (30 days)
- High resource usage (>85%)

### Log Aggregation

**Loki + Promtail** for centralized logging:
- Application logs
- System logs
- Container logs
- Audit logs

### Dashboards

**Grafana Dashboards:**
- System overview
- Application performance
- Database metrics
- Security monitoring
- Business metrics

## Deployment Execution

### Manual Deployment Process

1. **Pre-deployment Validation**
```bash
# Run security fixes
./scripts/deployment/security/apply-security-fixes.sh --environment production

# Validate environment
./scripts/deployment/deploy-production.sh --dry-run --environment production
```

2. **Execute Deployment**
```bash
# Full production deployment
./scripts/deployment/deploy-production.sh --environment production

# With specific options
./scripts/deployment/deploy-production.sh \
    --environment production \
    --force \
    --skip-security
```

3. **Monitor Deployment**
```bash
# Real-time monitoring
docker-compose -f docker-system/docker-compose.production-enhanced.yml logs -f

# Health checks
./scripts/deployment/health-checks/comprehensive-health-check.sh --environment production
```

### Automated Deployment (CI/CD)

Trigger via GitHub Actions:

1. **Tag-based Deployment**
```bash
git tag v1.0.0
git push origin v1.0.0
```

2. **Manual Workflow Dispatch**
   - Go to GitHub Actions
   - Select "Production Deployment Pipeline"
   - Click "Run workflow"
   - Select production environment

## Post-Deployment Validation

### Health Checks

Comprehensive health validation:

```bash
# Full health check suite
./scripts/deployment/health-checks/comprehensive-health-check.sh \
    --environment production \
    --verbose \
    --timeout 60

# Quick smoke tests
./scripts/deployment/health-checks/smoke-tests.sh \
    --environment production
```

### Validation Checklist

- [ ] All services are running and healthy
- [ ] Database migrations completed
- [ ] Authentication system functional
- [ ] MCP endpoints responding correctly
- [ ] SSL certificates valid and secure
- [ ] Monitoring systems operational
- [ ] Performance benchmarks met
- [ ] Security scans passed

### Performance Validation

Expected performance metrics:
- API response time: <2 seconds (95th percentile)
- Database query time: <500ms average
- Error rate: <0.1%
- Uptime: >99.9%

## Rollback Procedures

### Automatic Rollback

The CI/CD pipeline automatically triggers rollback on deployment failure:

```bash
# Automatic rollback (triggered by CI/CD)
./scripts/deployment/rollback/rollback-production.sh \
    --environment production \
    --auto-confirm
```

### Manual Rollback

For manual rollback execution:

```bash
# Rollback to previous version
./scripts/deployment/rollback/rollback-production.sh \
    --environment production

# Rollback to specific version
./scripts/deployment/rollback/rollback-production.sh \
    --environment production \
    --version v1.2.3

# Dry run rollback
./scripts/deployment/rollback/rollback-production.sh \
    --dry-run \
    --environment production
```

### Rollback Validation

After rollback:

1. Verify services are running
2. Run health checks
3. Validate critical functionality
4. Monitor for stability
5. Notify stakeholders

## Operational Procedures

### Regular Maintenance

**Daily:**
- Monitor dashboard alerts
- Review error logs
- Check system resource usage
- Validate backup completion

**Weekly:**
- Review performance metrics
- Update security patches
- Test backup restoration
- Review access logs

**Monthly:**
- Security audit review
- Performance optimization
- Capacity planning review
- Documentation updates

### Backup Procedures

**Database Backups:**
```bash
# Create production backup
./scripts/backup-production.sh

# Verify backup integrity
./scripts/verify-backup.sh
```

**Configuration Backups:**
- Environment variables
- SSL certificates
- Docker configurations
- Monitoring configurations

### Scaling Procedures

**Horizontal Scaling:**
```bash
# Scale MCP backend
docker-compose -f docker-system/docker-compose.production-enhanced.yml \
    up -d --scale mcp-backend=3
```

**Vertical Scaling:**
- Update resource limits in Docker Compose
- Adjust database configuration
- Monitor performance impact

## Troubleshooting

### Common Issues

**1. SSL Certificate Issues**
```bash
# Check certificate validity
openssl x509 -in /path/to/cert.pem -text -noout

# Verify certificate chain
openssl verify -CAfile /path/to/ca.pem /path/to/cert.pem
```

**2. Database Connection Issues**
```bash
# Test database connectivity
docker-compose exec postgres pg_isready -U ${DATABASE_USER}

# Check database logs
docker-compose logs postgres
```

**3. High Memory Usage**
```bash
# Check container memory usage
docker stats

# Identify memory leaks
docker-compose exec mcp-backend top
```

**4. Authentication Failures**
```bash
# Check Keycloak connectivity
curl -f ${KEYCLOAK_URL}/auth/realms/4genthub/.well-known/openid_configuration

# Verify JWT configuration
grep JWT_SECRET_KEY .env
```

### Emergency Procedures

**1. Critical Service Down**
1. Check service logs
2. Restart affected service
3. If restart fails, rollback
4. Notify stakeholders
5. Investigate root cause

**2. Database Issues**
1. Check database connectivity
2. Review database logs
3. Verify disk space
4. Restore from backup if needed
5. Document incident

**3. Security Breach**
1. Isolate affected systems
2. Change all credentials
3. Review access logs
4. Notify security team
5. Document incident

### Log Locations

- **Application Logs:** `logs/`
- **Docker Logs:** `docker-compose logs [service]`
- **System Logs:** `/var/log/`
- **Nginx Logs:** `/var/log/nginx/`
- **Database Logs:** Docker volume `postgres_logs`

### Monitoring URLs

- **Grafana:** `http://your-domain:3001`
- **Prometheus:** `http://your-domain:9090`
- **Application:** `http://your-domain:8000/api/v2/health`

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

## Compliance & Auditing

### Audit Trail
- All deployment activities logged
- Configuration changes tracked
- Access logs maintained
- Performance metrics recorded

### Compliance Requirements
- Data encryption standards
- Access control policies
- Backup and recovery procedures
- Incident response plans

---

## Quick Reference

### Essential Commands

```bash
# Deploy to production
./scripts/deployment/deploy-production.sh --environment production

# Health check
./scripts/deployment/health-checks/comprehensive-health-check.sh --environment production

# Rollback
./scripts/deployment/rollback/rollback-production.sh --environment production

# View logs
docker-compose -f docker-system/docker-compose.production-enhanced.yml logs -f

# Monitor services
docker-compose -f docker-system/docker-compose.production-enhanced.yml ps
```

### Emergency Contacts

- **DevOps Team:** devops@4genthub.dev
- **Security Team:** security@4genthub.dev
- **On-Call Engineer:** +1-XXX-XXX-XXXX

### Support Resources

- **Documentation:** `/ai_docs/operations/`
- **Runbooks:** `/scripts/deployment/`
- **Monitoring:** Grafana dashboards
- **Logs:** Centralized logging in Loki

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-09-11  
**Next Review:** 2025-10-11