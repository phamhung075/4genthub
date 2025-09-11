# 🗄️ Database UI Guide for PostgreSQL in Docker

## Quick Start

Your Docker setup already includes **pgAdmin** - the most popular PostgreSQL management tool. Here's how to use it:

### 🚀 Start pgAdmin with Docker

```bash
# Start with pgAdmin included (using the tools profile)
docker-compose --profile tools up -d

# Or start only the database and pgAdmin
docker-compose up -d postgres pgadmin
```

### 🌐 Access pgAdmin

1. Open your browser and navigate to:
   ```
   http://localhost:5050
   ```

2. Login with default credentials:
   - **Email**: `admin@dhafnck.com`
   - **Password**: `AdminPassword2025!`

3. Connect to your PostgreSQL database:
   - Click "Add New Server"
   - **General Tab**:
     - Name: `DhafnckMCP Database`
   - **Connection Tab**:
     - Host: `postgres` (Docker service name)
     - Port: `5432`
     - Database: `dhafnck_mcp_prod`
     - Username: `dhafnck_user`
     - Password: `ChangeThisSecurePassword2025!`
   - Click "Save"

## 🎯 Alternative Database UI Options

### Option 1: DBeaver (Desktop Application)

**Best for**: Advanced users, complex queries, multiple database types

```bash
# Install DBeaver
# macOS
brew install --cask dbeaver-community

# Ubuntu/Debian
sudo snap install dbeaver-ce

# Windows - Download from https://dbeaver.io/download/
```

**Connection Settings**:
- Host: `localhost`
- Port: `5432`
- Database: `dhafnck_mcp_prod`
- Username: `dhafnck_user`
- Password: `ChangeThisSecurePassword2025!`

### Option 2: Adminer (Lightweight Web UI)

Add to your `docker-compose.yml`:

```yaml
  adminer:
    image: adminer:latest
    container_name: dhafnck-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    networks:
      - dhafnck_network
    depends_on:
      - postgres
    environment:
      ADMINER_DEFAULT_SERVER: postgres
    profiles:
      - tools
```

Access at: `http://localhost:8080`
- System: `PostgreSQL`
- Server: `postgres`
- Username: `dhafnck_user`
- Password: `ChangeThisSecurePassword2025!`
- Database: `dhafnck_mcp_prod`

### Option 3: TablePlus (Premium Desktop App)

**Best for**: Beautiful UI, fast performance, multi-tab interface

Download from: https://tableplus.com/

**Connection**:
- Create new PostgreSQL connection
- Host: `localhost`
- Port: `5432`
- User: `dhafnck_user`
- Password: `ChangeThisSecurePassword2025!`
- Database: `dhafnck_mcp_prod`

### Option 4: Beekeeper Studio (Free & Open Source)

**Best for**: Modern UI, cross-platform, beginner-friendly

```bash
# Install Beekeeper Studio
# macOS
brew install --cask beekeeper-studio

# Linux/Windows - Download from https://www.beekeeperstudio.io/
```

## 📊 Viewing Your Database Tables

Once connected through any UI tool, you can explore:

### Core Tables Structure

```sql
-- View all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Common tables in DhafnckMCP:
-- • projects
-- • git_branches  
-- • tasks
-- • subtasks
-- • contexts (hierarchical)
-- • agents
-- • users (if Keycloak integrated)
```

### Useful Queries

```sql
-- View recent tasks
SELECT t.*, p.name as project_name, gb.name as git_branch_name
FROM tasks t
JOIN git_branches gb ON t.git_branch_id = gb.id
JOIN projects p ON gb.project_id = p.id
ORDER BY t.created_at DESC
LIMIT 20;

-- Check context hierarchy
SELECT 
  level,
  context_id,
  parent_context_id,
  data,
  created_at
FROM contexts
ORDER BY created_at DESC;

-- View project activity
SELECT 
  p.name,
  COUNT(DISTINCT gb.id) as branch_count,
  COUNT(DISTINCT t.id) as task_count,
  MAX(t.updated_at) as last_activity
FROM projects p
LEFT JOIN git_branches gb ON gb.project_id = p.id
LEFT JOIN tasks t ON t.git_branch_id = gb.id
GROUP BY p.id, p.name
ORDER BY last_activity DESC;
```

## 🔒 Security Best Practices

### 1. Change Default Passwords

Update in your `.env` file:
```env
# Database
DATABASE_PASSWORD=YourSecurePasswordHere!

# pgAdmin
PGADMIN_PASSWORD=YourAdminPasswordHere!
```

### 2. Restrict Access in Production

```yaml
# docker-compose.prod.yml
services:
  pgadmin:
    # Remove ports mapping for production
    # ports:
    #   - "5050:80"
    networks:
      - internal_network  # Internal only
```

### 3. Use Read-Only Users for Viewing

```sql
-- Create read-only user
CREATE USER readonly_viewer WITH PASSWORD 'ViewOnlyPass2025!';
GRANT CONNECT ON DATABASE dhafnck_mcp_prod TO readonly_viewer;
GRANT USAGE ON SCHEMA public TO readonly_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_viewer;
```

## 🛠️ Troubleshooting

### Cannot Connect to Database

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs dhafnck-postgres

# Test connection from within Docker network
docker exec -it dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_prod
```

### pgAdmin Connection Failed

```bash
# Ensure you're using 'postgres' as hostname (not localhost) when connecting from pgAdmin container
# The hostname should be the Docker service name

# Test network connectivity
docker exec -it dhafnck-pgadmin ping postgres
```

### Permission Denied Errors

```bash
# Reset pgAdmin data volume if corrupted
docker-compose down
docker volume rm dhafnck_pgadmin_data
docker-compose --profile tools up -d
```

## 📈 Database Monitoring

### Add pg_stat_statements for Query Analysis

```sql
-- Enable in PostgreSQL
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slowest queries
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Database Size Monitoring

```sql
-- Check database size
SELECT 
  pg_database.datname,
  pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'dhafnck_mcp_prod';

-- Check table sizes
SELECT
  schemaname AS table_schema,
  tablename AS table_name,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 🚀 Quick Commands

```bash
# Start everything including pgAdmin
docker-compose --profile tools up -d

# Stop pgAdmin but keep database running
docker-compose stop pgadmin

# View database logs
docker logs -f dhafnck-postgres

# Backup database
docker exec dhafnck-postgres pg_dump -U dhafnck_user dhafnck_mcp_prod > backup.sql

# Restore database
docker exec -i dhafnck-postgres psql -U dhafnck_user dhafnck_mcp_prod < backup.sql

# Access PostgreSQL CLI
docker exec -it dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_prod
```

## 📝 Environment Variables

Add to your `.env` file for customization:

```env
# pgAdmin Configuration
PGADMIN_EMAIL=admin@yourcompany.com
PGADMIN_PASSWORD=YourSecureAdminPassword!

# Database Configuration
DATABASE_NAME=dhafnck_mcp_prod
DATABASE_USER=dhafnck_user
DATABASE_PASSWORD=YourSecureDatabasePassword!
DATABASE_SSL_MODE=prefer
```

## 🎨 pgAdmin Tips

### Save Connection Password
1. Right-click on your server in pgAdmin
2. Select "Properties"
3. Go to "Connection" tab
4. Check "Save password?"

### Create Custom Dashboards
1. Right-click on server
2. Select "Create" → "Dashboard"
3. Add charts for:
   - Database size
   - Active connections
   - Query performance
   - Table statistics

### Export Query Results
1. Run your query
2. Click "Download" button in results panel
3. Choose format: CSV, JSON, or XML

## 📚 Additional Resources

- [pgAdmin Documentation](https://www.pgadmin.org/ai_docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/ai_docs/)
- [DBeaver Documentation](https://dbeaver.com/ai_docs/wiki/)
- [Docker PostgreSQL Image](https://hub.docker.com/_/postgres)

---

**Quick Start Summary**:
1. Run: `docker-compose --profile tools up -d`
2. Open: http://localhost:5050
3. Login: admin@dhafnck.com / AdminPassword2025!
4. Connect to database with provided credentials
5. Start exploring your data!