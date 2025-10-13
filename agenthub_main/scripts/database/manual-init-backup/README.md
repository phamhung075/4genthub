# Manual Database Initialization Scripts (ARCHIVED)

## ⚠️ THESE SCRIPTS ARE NOT USED IN PRODUCTION

These files are kept for **historical reference only**. They are **NOT automatically executed** during deployment.

## Why These Exist

These were the original manual database initialization scripts that required:
1. Mounting SQL files into PostgreSQL container
2. Running bash scripts on first startup
3. Managing password synchronization between scripts and environment variables

## Current Approach (ORM-Based)

The system now uses **100% automatic ORM-based initialization**:
- No manual scripts required
- SQLAlchemy creates all tables from Python models
- Fully automatic on first backend startup
- See: `ai_docs/operations/orm-database-initialization.md`

## Files in This Directory

### init.sql
- Original PostgreSQL initialization script
- Created tables in `mcp` schema
- Set up basic permissions
- **Not used anymore** - ORM creates tables in `public` schema

### init-wrapper.sh
- Bash script to create user with environment-based password
- Granted schema permissions
- **Not used anymore** - Use superuser or grant permissions manually

## When You Might Need These

### Scenario 1: Manual Database Setup
If you want to set up the database manually (not recommended):
```bash
# Connect to PostgreSQL
psql -U postgres -d agenthub

# Run the SQL manually
\i init.sql

# Or run the wrapper script
./init-wrapper.sh
```

### Scenario 2: Understanding Database Structure
These files show what the original database structure looked like before ORM took over.

### Scenario 3: Debugging
If you need to compare ORM-generated schema with original manual schema.

## Recommended Approach

**For Production:** Let the ORM handle everything automatically
- Set environment variables
- Deploy application
- ORM creates all tables on first startup

**For Development:** Same as production - ORM handles it

**For Manual Setup:** Only if you absolutely must:
1. Create database manually
2. Grant superuser permissions to application user
3. Let ORM create tables

## See Also
- Current documentation: `ai_docs/operations/orm-database-initialization.md`
- ORM models: `agenthub_main/src/fastmcp/task_management/infrastructure/database/models.py`
- Init code: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_database.py`
