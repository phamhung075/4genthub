# Complete Setup Guide - agenthub Platform

## Quick Reference

| Component | Setup Time | Prerequisites | Critical Files |
|-----------|-----------|---------------|----------------|
| **PostgreSQL** | 15 min | Docker | `docker-compose.yml`, `.env` |
| **Keycloak** | 30 min | PostgreSQL | Realm config, client credentials |
| **Database UI** | 5 min | PostgreSQL | pgAdmin/DBeaver |
| **Email Verification** | 20 min | SMTP server | Keycloak email settings |
| **Branch Setup** | 5 min | Git | Branch creation, MCP registration |

**Total Estimated Time**: 75 minutes for complete setup

---

## Environment Prerequisites

### Required

| Requirement | Version | Purpose |
|------------|---------|---------|
| Docker | 20.10+ | Container orchestration |
| Docker Compose | 1.29+ | Multi-container apps |
| PostgreSQL | 14+ | Primary database |
| Node.js | 18+ | Frontend development |
| Python | 3.14+ | Backend services |

### Optional

| Tool | Purpose |
|------|---------|
| pgAdmin | Database UI management |
| DBeaver | Alternative database UI |
| SMTP Server | Email verification (MailHog for dev) |

---

## 1. PostgreSQL Setup

### Development (Docker)

**docker-compose.yml**:
```yaml
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: agenthub
      POSTGRES_USER: agenthub_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**Start Database**:
```bash
docker-compose up -d postgres
# Verify: docker-compose ps
# Logs: docker-compose logs postgres
```

### Production Setup

**Configuration** (`postgresql.conf`):
```ini
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
```

**Security**:
- Use strong passwords (min 16 chars, alphanumeric + symbols)
- Enable SSL: `ssl = on` in `postgresql.conf`
- Restrict `pg_hba.conf` to specific IPs
- Regular backups: `pg_dump -Fc agenthub > backup.dump`

---

## 2. Keycloak Authentication Setup

### 2.1 Keycloak Installation

**Docker Deployment**:
```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: agenthub_user
      KC_DB_PASSWORD: ${DB_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    command: start-dev
    ports:
      - "8080:8080"
    depends_on:
      - postgres
```

**Start Keycloak**:
```bash
docker-compose up -d keycloak
# Access: http://localhost:8080
# Login: admin / ${KEYCLOAK_ADMIN_PASSWORD}
```

### 2.2 Realm Configuration

**Create Realm**:
1. Keycloak Admin Console → Create Realm
2. Name: `mcp` (or custom)
3. Display Name: "agenthub"
4. Token Lifespans:
   - Access Token: 30 minutes
   - Refresh Token: 7 days
   - SSO Session Idle: 30 minutes
   - SSO Session Max: 10 hours

**Realm Roles**:
- `admin` - Full system access
- `user` - Standard user access
- `developer` - API/development access

### 2.3 Client Configuration

**Create Client**:
```
Client ID: mcp-backend
Protocol: openid-connect
Root URL: http://localhost:8000
Access Type: confidential
```

**Enable Flows**:
- ✅ Standard Flow (Authorization Code)
- ✅ Direct Access Grants (Password)
- ✅ Service Accounts (Machine-to-Machine)

**Valid Redirect URIs**:
```
http://localhost:8000/*
http://localhost:3800/*
https://yourdomain.com/*  (production)
```

**Credentials**:
1. Go to Credentials tab
2. Copy `Secret` value
3. Add to `.env`:
   ```bash
   KEYCLOAK_CLIENT_SECRET=<secret-value>
   ```

### 2.4 User Setup

**Create Test User**:
1. Users → Add User
2. Username: `testuser`
3. Email: `test@example.com`
4. Email Verified: `ON` (for dev)
5. Set Password (Credentials tab, Temporary: `OFF`)
6. Role Mappings → Assign `user` role

---

## 3. Email Verification Setup

### 3.1 SMTP Configuration

**Development (MailHog)**:
```yaml
services:
  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI
```

**Keycloak Email Settings**:
1. Realm Settings → Email
2. Configure:
   ```
   Host: mailhog (or smtp.gmail.com for production)
   Port: 1025 (or 587 for TLS)
   From: noreply@agenthub.com
   Enable StartTLS: ON (production only)
   Enable Authentication: ON (production)
   Username: <smtp-username>
   Password: <smtp-password>
   ```

**Test Email**:
1. Users → Select user → Send Verify Email
2. Check MailHog UI: http://localhost:8025

### 3.2 Production SMTP

**Gmail** (for small deployments):
```
Host: smtp.gmail.com
Port: 587
From: your-email@gmail.com
Username: your-email@gmail.com
Password: <app-specific-password>
Enable StartTLS: ON
Enable Authentication: ON
```

**SendGrid** (recommended for production):
```
Host: smtp.sendgrid.net
Port: 587
From: noreply@yourdomain.com
Username: apikey
Password: <sendgrid-api-key>
```

### 3.3 Email Templates

**Keycloak → Realm Settings → Themes → Email**:
- Select theme: `keycloak` (default) or custom
- Customize templates in `/themes/<theme>/email/`
- Available templates:
  - `email-verification.ftl` - Verification email
  - `password-reset.ftl` - Password reset
  - `event-login.ftl` - Login notification

---

## 4. Database UI Setup

### Option A: pgAdmin (Web-based)

**Docker Setup**:
```yaml
services:
  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@agenthub.com
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    ports:
      - "5050:80"
    depends_on:
      - postgres
```

**Access**: http://localhost:5050
**Add Server**:
```
Name: agenthub
Host: postgres
Port: 5432
Username: agenthub_user
Password: ${DB_PASSWORD}
```

### Option B: DBeaver (Desktop)

**Install**: https://dbeaver.io/download/

**Connection**:
```
Driver: PostgreSQL
Host: localhost
Port: 5432
Database: agenthub
Username: agenthub_user
Password: ${DB_PASSWORD}
```

**Useful Queries**:
```sql
-- View all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Check table sizes
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size(quote_ident(tablename))) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(quote_ident(tablename)) DESC;

-- Active connections
SELECT * FROM pg_stat_activity;
```

---

## 5. Git Branch Setup

### 5.1 Create Development Branch

```bash
# Create feature branch
git checkout -b feature/my-feature

# Push to remote
git push -u origin feature/my-feature
```

### 5.2 Register Branch in MCP

**Using MCP Tool**:
```python
from utils.mcp_client import get_default_client

client = get_default_client()

# Create project (if not exists)
project = client.query_project_create(
    name="My Project",
    description="Project description"
)

# Create branch
branch = client.query_branch_create(
    project_id=project["id"],
    git_branch_name="feature/my-feature",
    git_branch_description="Feature description"
)

print(f"Branch ID: {branch['id']}")
```

**Using API**:
```bash
curl -X POST http://localhost:8000/api/git-branch \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid",
    "git_branch_name": "feature/my-feature",
    "git_branch_description": "Description"
  }'
```

### 5.3 Assign Agents to Branch

```python
# Register agent (if not exists)
agent = client.query_agent_register(
    project_id=project["id"],
    name="coding-agent",
    description="Primary coding agent"
)

# Assign to branch
client.query_branch_assign_agent(
    git_branch_id=branch["id"],
    agent_id=agent["id"]
)
```

---

## 6. Environment Variables

### Required Variables

**.env** (create in project root):
```bash
# Database
DATABASE_URL=postgresql://agenthub_user:${DB_PASSWORD}@localhost:5432/agenthub
DB_PASSWORD=<strong-password>

# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=mcp
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=<from-keycloak-credentials>
KEYCLOAK_ADMIN_PASSWORD=<admin-password>

# Email
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=noreply@agenthub.com
SMTP_USERNAME=
SMTP_PASSWORD=

# Application
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENVIRONMENT=development
DEBUG=true

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3800
```

### Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate strong password
openssl rand -base64 24
```

---

## 7. Verification Checklist

### Database

- [ ] PostgreSQL running: `docker-compose ps postgres`
- [ ] Can connect: `psql -h localhost -U agenthub_user -d agenthub`
- [ ] Tables created: `\dt` in psql
- [ ] Database UI accessible

### Keycloak

- [ ] Keycloak running: http://localhost:8080
- [ ] Realm created: `mcp`
- [ ] Client created: `mcp-backend`
- [ ] Client secret configured in `.env`
- [ ] Test user created and can login
- [ ] Roles assigned

### Email

- [ ] SMTP configured in Keycloak
- [ ] Test email sent successfully
- [ ] Email received (check MailHog UI)
- [ ] Email templates rendering correctly

### Application

- [ ] Backend starts: `python -m fastmcp.server.mcp_entry_point`
- [ ] Frontend starts: `npm run dev`
- [ ] Health check: `curl http://localhost:8000/health`
- [ ] Can authenticate via Keycloak
- [ ] Can access protected endpoints with JWT

### Git & MCP

- [ ] Feature branch created
- [ ] Project registered in MCP
- [ ] Branch registered in MCP
- [ ] Agent assigned to branch
- [ ] Can create tasks on branch

---

## 8. Troubleshooting

### Database Connection Issues

**Error**: `FATAL: password authentication failed`
**Solution**: Verify `DB_PASSWORD` in `.env` matches database password

**Error**: `could not connect to server`
**Solution**:
```bash
docker-compose ps postgres  # Check if running
docker-compose logs postgres  # Check logs
docker-compose restart postgres  # Restart if needed
```

### Keycloak Issues

**Error**: `Unable to connect to Keycloak`
**Solution**: Verify `KEYCLOAK_URL` and ensure Keycloak is running

**Error**: `Invalid client credentials`
**Solution**: Regenerate client secret in Keycloak → Clients → mcp-backend → Credentials → Regenerate Secret

### Email Not Sending

**Check SMTP Settings**:
1. Keycloak → Realm Settings → Email
2. Click "Test connection"
3. Check MailHog logs: `docker-compose logs mailhog`

**Common Issues**:
- Wrong port (use 1025 for MailHog, 587 for production SMTP)
- Authentication enabled but no credentials
- Firewall blocking SMTP port

---

## 9. Production Deployment

### Security Hardening

**PostgreSQL**:
- Change default passwords
- Enable SSL/TLS
- Restrict `pg_hba.conf` to application IPs only
- Regular backups

**Keycloak**:
- Use production database (not H2)
- Enable HTTPS
- Configure proper token lifespans
- Enable brute force detection
- Regular security updates

**Application**:
- Set `DEBUG=false`
- Use strong `SECRET_KEY`
- Enable HTTPS
- Configure CORS properly
- Rate limiting
- Input validation

### Monitoring

**Health Checks**:
```bash
# Database
curl http://localhost:8000/health/db

# Keycloak
curl http://localhost:8080/health

# Application
curl http://localhost:8000/health
```

**Logging**:
- Application logs: `logs/claude-hooks/`
- Database logs: `docker-compose logs postgres`
- Keycloak logs: `docker-compose logs keycloak`

---

## 10. Quick Start Commands

```bash
# Complete setup from scratch
docker-compose up -d
python scripts/init_database.py
npm install && npm run dev

# Verify setup
curl http://localhost:8000/health
curl http://localhost:8080

# Create first project
python scripts/create_project.py --name "My Project"

# Run application
python -m fastmcp.server.mcp_entry_point  # Backend
npm run dev  # Frontend
```

---

## Related Documentation
- [Database Configuration](../operations/database-configuration-guide.md)
- [Authentication System](../authentication/complete-authentication-system.md)
- [Docker Deployment](../operations/docker-deployment-guide.md)
- [Production Guide](../operations/production-deployment-guide.md)
