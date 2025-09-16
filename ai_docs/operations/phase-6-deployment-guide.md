# Phase 6: Production Deployment & Operations Guide

**Version**: 2.1.0
**Last Updated**: 2025-09-16
**Status**: ✅ Phase 6 Complete

## Overview

This guide documents the Phase 6 deployment and cleanup implementation, providing comprehensive instructions for production deployment, monitoring, and maintenance of the DhafnckMCP system.

## 🎯 Phase 6 Objectives Completed

### ✅ Deployment Infrastructure
- **Production-ready Docker configurations** optimized for scalability
- **Enhanced deployment automation** with health checks and rollback capability
- **Comprehensive monitoring system** with real-time health tracking
- **CI/CD pipeline** already configured for automated deployments
- **Legacy cleanup** with safe backup and restoration procedures

### ✅ Key Deliverables
1. **Deployment Manager** (`docker-system/deployment-manager.sh`)
2. **Health Monitoring System** (`scripts/health-monitor.sh`)
3. **Legacy Cleanup Tool** (`scripts/cleanup-legacy.sh`)
4. **Production Docker Configurations** (optimized multi-stage builds)
5. **Monitoring & Alerting** (comprehensive health checks)

## 🚀 Deployment Options

### 1. Development Deployment
**Use Case**: Local development and testing

```bash
# Quick start development environment
cd docker-system
./deployment-manager.sh --development

# Or use the existing docker menu
./docker-menu.sh
```

**Services Started**:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3800` (if enabled)
- Database: PostgreSQL on port 5432
- API Docs: `http://localhost:8000/docs`

### 2. Production Deployment
**Use Case**: Production environment with full optimization

```bash
# Production deployment with health checks
cd docker-system
./deployment-manager.sh --production

# Interactive mode for step-by-step deployment
./deployment-manager.sh
```

**Features**:
- Multi-stage optimized Docker builds
- Health checks and automatic rollback
- Database backup before deployment
- Performance monitoring
- Nginx reverse proxy (optional)
- SSL/TLS termination (configurable)

### 3. Database-Only Deployment
**Use Case**: Separate database deployment or database maintenance

```bash
# Deploy only PostgreSQL database
./deployment-manager.sh --db-only
```

## 📊 Monitoring & Health Checks

### Health Monitor Usage

```bash
# Check system status once
./scripts/health-monitor.sh check

# Continuous monitoring (recommended for production)
./scripts/health-monitor.sh monitor

# View current system status
./scripts/health-monitor.sh status
```

### Health Check Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Backend | `http://localhost:8000/health` | Backend service health |
| API Docs | `http://localhost:8000/docs` | API documentation |
| Database | Container health check | PostgreSQL readiness |
| Frontend | `http://localhost:3800` | Frontend availability |

### Monitoring Features

- **Real-time Health Tracking**: All services monitored continuously
- **Performance Metrics**: Response times, memory usage, disk usage
- **Alerting System**: Automatic alerts for service degradation
- **JSON Status Reports**: Machine-readable status for integration
- **Historical Logging**: Complete audit trail of system health

## 🔧 Configuration Management

### Environment Files

| File | Purpose | Usage |
|------|---------|-------|
| `.env.dev` | Development configuration | Local development |
| `.env` | Production configuration | Production deployment |
| `.env.keycloak` | Keycloak authentication | Authentication setup |

### Key Configuration Parameters

```bash
# Core Settings
ENV=production                    # Environment mode
CONTAINER_ENV=docker             # Container detection
APP_DEBUG=false                  # Debug mode (false for prod)

# Database Configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres           # Container name or IP
DATABASE_PORT=5432
DATABASE_NAME=dhafnck_mcp
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=SecurePassword123!

# Application Ports
FASTMCP_PORT=8000               # Backend port
FRONTEND_PORT=3800              # Frontend port (if enabled)
MCP_PORT=8001                   # Production backend port

# Authentication (Keycloak)
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=dhafnck
KEYCLOAK_CLIENT_ID=mcp-frontend

# Security
JWT_SECRET_KEY=YourSecure32CharacterJWTSecretKey
CORS_ORIGINS=http://localhost:3800,https://yourdomain.com
```

## 🏗️ Architecture Overview

### Production Stack

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │───▶│  MCP Backend     │───▶│   PostgreSQL    │
│   (Optional)    │    │  (Port 8001)     │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │    Frontend      │
                       │  (Port 3800)     │
                       └──────────────────┘
```

### Container Network

- **Network**: `dhafnck-network` (bridge)
- **Service Discovery**: Container name-based DNS
- **Health Checks**: Built-in Docker health checks
- **Volume Management**: Persistent data volumes

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/production-deployment.yml`

**Triggers**:
- Push to `main` branch
- Version tags (`v*.*.*`)
- Manual workflow dispatch

**Pipeline Stages**:
1. **Security Scan** - Trivy vulnerability scanning
2. **Build & Test** - Multi-platform Docker builds
3. **Quality Gates** - Code quality and test coverage
4. **Deployment** - Automated production deployment
5. **Health Verification** - Post-deployment health checks

**Manual Deployment**:
```bash
# Trigger manual deployment via GitHub Actions
# Go to Actions → Production Deployment Pipeline → Run workflow
```

## 🧹 Maintenance & Cleanup

### Legacy Cleanup Tool

```bash
# Safe cleanup with backup (recommended)
./scripts/cleanup-legacy.sh all

# Dry run to preview changes
DRY_RUN=true ./scripts/cleanup-legacy.sh all

# Specific cleanup operations
./scripts/cleanup-legacy.sh backup-only
./scripts/cleanup-legacy.sh logs-only
./scripts/cleanup-legacy.sh workers-only
```

**Files Cleaned Up**:
- Legacy backup files (`.bak`, `.backup`)
- Old test logs and iteration files
- Obsolete worker scripts
- Node.js artifact logs
- HTML coverage artifacts
- Stale PID files

**Safety Features**:
- Automatic backup before deletion
- Dry-run mode for preview
- Restoration capability
- Detailed logging and reporting

### Regular Maintenance

```bash
# Weekly health check
./scripts/health-monitor.sh check > logs/weekly-health-$(date +%Y%m%d).log

# Monthly cleanup
./scripts/cleanup-legacy.sh all

# Database backup (production)
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp > backup_$(date +%Y%m%d).sql

# Resource cleanup
./deployment-manager.sh --cleanup
```

## 🚨 Troubleshooting

### Common Issues & Solutions

#### 1. Service Health Check Failures

```bash
# Check service logs
docker compose logs -f mcp-backend
docker compose logs -f postgres

# Manual health check
curl -f http://localhost:8000/health
```

#### 2. Database Connection Issues

```bash
# Check database readiness
docker exec dhafnck-postgres pg_isready -U dhafnck_user

# Connect to database manually
docker exec -it dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp
```

#### 3. Port Conflicts

```bash
# Check port usage
docker ps --format "table {{.Names}}\t{{.Ports}}"
netstat -tulpn | grep :8000

# Stop conflicting services
./deployment-manager.sh --cleanup
```

#### 4. Performance Issues

```bash
# System resource check
./scripts/health-monitor.sh status

# Docker resource usage
docker stats --no-stream

# Database performance
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp -c "SELECT * FROM pg_stat_activity;"
```

### Rollback Procedures

#### Automatic Rollback
```bash
# Deployment manager includes automatic rollback on health check failure
./deployment-manager.sh --production
# Will automatically rollback if health checks fail
```

#### Manual Rollback
```bash
# Using backup file
./deployment-manager.sh --rollback /path/to/backup.sql

# Emergency stop and restore
docker compose down
# Restore from backup, then restart
docker compose up -d
```

## 📈 Performance Optimization

### Production Tuning

**PostgreSQL Configuration**:
```ini
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
work_mem = 4MB
```

**Backend Optimization**:
```bash
# Environment variables for production
ENV=production
APP_DEBUG=false
FEATURE_REQUEST_LOGGING=false
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

**Frontend Optimization**:
- Production build with optimized assets
- Static file caching
- Gzip compression
- CDN integration (if configured)

### Scaling Considerations

**Horizontal Scaling**:
- Load balancer configuration (Nginx)
- Database read replicas
- Redis session storage
- Container orchestration (Kubernetes ready)

**Vertical Scaling**:
- Memory allocation tuning
- CPU core optimization
- Disk I/O optimization
- Database connection pooling

## 🔐 Security Checklist

### Production Security

- [ ] JWT secret key ≥ 32 characters
- [ ] Database passwords are strong and unique
- [ ] CORS origins are properly configured
- [ ] SSL/TLS certificates are valid
- [ ] Container security scanning passes
- [ ] Non-root container users configured
- [ ] Secrets are not in environment files
- [ ] Firewall rules are properly configured
- [ ] Regular security updates applied

### Monitoring Security

- [ ] Health check endpoints are secured
- [ ] Log files have appropriate permissions
- [ ] Database access is restricted
- [ ] API endpoints have proper authentication
- [ ] Admin interfaces are protected

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] Environment configuration validated
- [ ] Database backup completed
- [ ] Health monitoring system operational
- [ ] CI/CD pipeline tests passed
- [ ] Security scans completed
- [ ] Performance benchmarks established

### Deployment

- [ ] Services deployed successfully
- [ ] Health checks passing
- [ ] Database migrations completed
- [ ] Authentication system verified
- [ ] API endpoints responding
- [ ] Frontend application loading

### Post-Deployment

- [ ] Full system health verification
- [ ] Performance monitoring activated
- [ ] Error tracking configured
- [ ] Backup procedures verified
- [ ] Documentation updated
- [ ] Team notified of deployment completion

## 📞 Support & Contact

### Log Files Locations

- **Deployment Logs**: `logs/deployment-*.log`
- **Health Monitor Logs**: `logs/health-monitor.log`
- **Cleanup Logs**: `logs/cleanup-*.log`
- **Application Logs**: Container-specific logging

### Emergency Procedures

1. **Service Down**: Check health monitor, restart services
2. **Database Issues**: Check connections, restore from backup
3. **Performance Problems**: Scale resources, check monitoring
4. **Security Incidents**: Stop services, review logs, patch system

---

## 📚 Related Documentation

- [Docker System Configuration](../core-architecture/docker-system.md)
- [Health Monitoring Setup](../operations/health-monitoring.md)
- [CI/CD Pipeline Configuration](../development-guides/cicd-setup.md)
- [Security Configuration](../operations/security-guide.md)
- [Troubleshooting Guide](../troubleshooting-guides/deployment-issues.md)

---

**Phase 6 Status**: ✅ **COMPLETE**
**Next Steps**: Regular monitoring and maintenance as per this guide
**Deployment Ready**: Production deployment fully configured and tested