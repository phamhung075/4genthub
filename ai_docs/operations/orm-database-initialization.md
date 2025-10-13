# ORM-Based Database Initialization (Automatic)

## Overview
The agenthub system uses SQLAlchemy ORM's automatic table creation. **No manual SQL scripts are required** - the ORM creates all tables automatically from model definitions.

## How It Works

### Automatic Table Creation
When the backend application starts, it automatically:
1. Connects to PostgreSQL using credentials from environment variables
2. Calls `Base.metadata.create_all(bind=engine)` to create all tables
3. Runs automatic migrations to add new columns to existing tables
4. Verifies AI-specific columns exist

### Code Location
- **Main Init**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_database.py`
- **Config**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py`
- **Models**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/models.py`

### Execution Flow
```python
# From init_database.py:40
db_config.create_tables()

# From database_config.py:523
Base.metadata.create_all(bind=self.engine)
```

## Production Deployment (Docker/CapRover)

### Step 1: Configure Environment Variables

Set these in your `.env` file or CapRover environment:

```bash
# PostgreSQL Configuration (superuser for Docker container)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-postgres-admin-password>
POSTGRES_DB=agenthub

# Application Database User (same as superuser in this setup)
DATABASE_USER=postgres
DATABASE_PASSWORD=<same-as-postgres-password>
DATABASE_NAME=agenthub
DATABASE_HOST=postgres  # Use service name for Docker internal networking
DATABASE_PORT=5432
DATABASE_TYPE=postgresql
```

**IMPORTANT**:
- Set `DATABASE_USER=postgres` to use the PostgreSQL superuser
- This gives the application full permissions to create tables, types, and schemas
- For production security, you may want to create a restricted user after initial setup

### Step 2: Deploy with Docker Compose

**Fresh Deployment:**
```bash
# Production deployment
docker-compose -f docker-system/docker/docker-compose.production.yml up -d

# Database-only deployment
docker-compose -f docker-system/docker/docker-compose.db-only.yml up -d
```

**What Happens Automatically:**
1. PostgreSQL container starts with empty data volume
2. Docker creates the `agenthub` database (from `POSTGRES_DB`)
3. Backend application starts and connects to database
4. ORM executes `Base.metadata.create_all()`:
   - Creates all 29 tables in `public` schema
   - Creates PostgreSQL ENUM types (progressstate, etc.)
   - Creates indexes and constraints
   - All defined in Python models
5. Automatic migrations run to add any new columns
6. Application becomes ready to serve requests

### Step 3: Verify Initialization

Check that initialization succeeded:
```bash
# Check backend logs
docker logs agenthub-backend 2>&1 | grep -i "database"

# Should see:
# - "Initializing database: postgresql"
# - "Database tables created successfully"
# - "Database initialization completed successfully"

# Verify tables exist
docker exec agenthub-postgres psql -U postgres -d agenthub -c "\dt"

# Should see 29 tables in public schema
```

## CapRover Deployment

### Option 1: Using Pre-Built Image (Recommended)
1. Build and push your Docker image:
```bash
docker build -f docker-system/docker/Dockerfile.backend.production -t your-registry/agenthub:latest .
docker push your-registry/agenthub:latest
```

2. In CapRover dashboard:
   - Create PostgreSQL app first (CapRover One-Click Apps)
   - Create backend app
   - Set environment variables (DATABASE_HOST, DATABASE_USER, etc.)
   - Deploy image
   - **Tables are created automatically on first startup**

### Option 2: Using Captain Definition
Create `captain-definition` in your repo:
```json
{
  "schemaVersion": 2,
  "dockerfilePath": "./docker-system/docker/Dockerfile.backend.production"
}
```

Deploy via CapRover CLI:
```bash
caprover deploy
```

## Important Notes

### No Manual Scripts Required
- ✅ **NO** `init.sql` scripts to run
- ✅ **NO** manual database setup commands
- ✅ **NO** schema files to execute
- ✅ **Everything is automatic** via ORM

### Reference Schema Files
The following files are kept for **reference only** (NOT executed automatically):
- `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`
- `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_schema_sqlite.sql`

These show what the ORM creates, useful for:
- Understanding the database structure
- Manual database setup if needed
- Debugging schema issues
- Documentation purposes

### Manual Init Scripts (Archived)
Old manual initialization scripts have been moved to:
- `agenthub_main/scripts/database/manual-init-backup/init.sql`
- `agenthub_main/scripts/database/manual-init-backup/init-wrapper.sh`

**These are NOT used in production** - kept only as backup reference.

## Database Permissions

### Default Setup (Superuser)
By default, the application uses the PostgreSQL superuser (`postgres`):
- Has full permissions to create tables, types, schemas
- Simplifies initial setup
- ORM can create all required database objects

### Production Security (Optional)
For enhanced security, create a restricted user after initial setup:

```sql
-- Connect as postgres superuser
\c agenthub

-- Create application user
CREATE ROLE agenthub_user LOGIN PASSWORD 'secure-password';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE agenthub TO agenthub_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO agenthub_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agenthub_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agenthub_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO agenthub_user;

-- Update environment variables
DATABASE_USER=agenthub_user
DATABASE_PASSWORD=secure-password

-- Restart application
```

## Troubleshooting

### Issue: Tables Not Created
**Symptom:** Backend starts but no tables exist
**Cause:** Database connection failure or ORM import issues
**Solution:**
```bash
# Check backend logs for errors
docker logs agenthub-backend 2>&1 | grep -E "(ERROR|error|failed)"

# Verify database connection
docker exec agenthub-backend python -c "
from fastmcp.task_management.infrastructure.database.database_config import get_db_config
db = get_db_config()
print(db.get_database_info())
"
```

### Issue: Permission Denied for Schema Public
**Symptom:** `permission denied for schema public`
**Cause:** User lacks CREATE privileges on public schema
**Solution:**
```bash
# Grant schema privileges (connect as postgres superuser)
docker exec agenthub-postgres psql -U postgres -d agenthub -c \
  "GRANT ALL PRIVILEGES ON SCHEMA public TO <your-app-user>;"
```

### Issue: Enum Type Already Exists
**Symptom:** `type "progressstate" already exists`
**Cause:** Database has existing schema from previous deployment
**Solution:**
ORM handles this automatically with `checkfirst=True` in `create_all()`. If issues persist:
```bash
# Drop and recreate database (DATA LOSS!)
docker exec agenthub-postgres psql -U postgres -c "DROP DATABASE agenthub;"
docker exec agenthub-postgres psql -U postgres -c "CREATE DATABASE agenthub;"
# Restart backend - tables will be recreated
```

## Migration Strategy

### For Existing Deployments with Data
If you already have data in PostgreSQL:

**Option 1: ORM Auto-Migration (Safe)**
- ORM automatically adds new columns via migration_runner
- Existing tables are preserved
- New tables are created
- **No data loss**

**Option 2: Manual Schema Update**
```bash
# Backup first!
docker exec agenthub-postgres pg_dump -U postgres agenthub > backup.sql

# Let ORM create new tables/columns automatically
docker-compose restart agenthub-backend
```

### From SQLite to PostgreSQL
Use the built-in migration function:
```python
from fastmcp.task_management.infrastructure.database.init_database import migrate_from_sqlite_to_postgresql

migrate_from_sqlite_to_postgresql("/path/to/sqlite.db")
```

## Advantages of ORM-Based Initialization

✅ **Single Source of Truth**: Database schema defined in Python models
✅ **Version Control**: Schema changes tracked in code
✅ **Automatic Sync**: No manual SQL script maintenance
✅ **Cross-Database**: Same code works for SQLite and PostgreSQL
✅ **Type Safety**: Python type checking for database fields
✅ **Migration Built-In**: Automatic column addition for existing databases
✅ **No Manual Steps**: Fully automatic on deployment

## Related Files
- **ORM Models**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/models.py`
- **DB Config**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py`
- **Init Script**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_database.py`
- **Reference Schema**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql` (reference only)
- **Docker Compose**: `docker-system/docker/docker-compose.production.yml`

## Summary
✅ **100% automatic** database initialization via ORM
✅ **NO manual SQL scripts** required
✅ **NO manual commands** to run
✅ **Just set environment variables** and deploy
✅ **Tables created automatically** on first backend startup
✅ **Migrations handled automatically** for existing databases
