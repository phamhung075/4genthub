# Database Initialization System

This replaces the complex migration system with a simple, reliable approach using complete SQL schema files.

## Quick Start

### For SQLite (Development)
```bash
cd agenthub_main
python init_database.py --database-type sqlite --confirm
```

### For PostgreSQL (Production/Docker)
```bash
cd agenthub_main
python init_database.py --database-type postgresql --confirm
```

### Auto-detect Database Type
```bash
cd agenthub_main
python init_database.py --confirm
```

## What This Does

1. **Drops all existing tables** - Clean slate approach
2. **Recreates complete schema** - From single SQL files containing ALL requirements
3. **Includes all modern features**:
   - AI Agent fields for task automation
   - User isolation (user_id fields) for security
   - Task count triggers for WebSocket real-time updates
   - Complete index structure for performance
   - All constraints and relationships

## SQL Schema Files

- **`init_schema_postgresql.sql`** - Complete PostgreSQL schema with JSONB fields and triggers
- **`init_schema_sqlite.sql`** - Complete SQLite schema with TEXT fields and compatibility views

## Migration from Old System

The old migration system in `infrastructure/migrations/` is now obsolete. This new approach:

✅ **Simpler** - Single SQL file vs 20+ migration files
✅ **Faster** - Direct schema creation vs incremental migrations
✅ **Reliable** - No migration dependency issues
✅ **Complete** - Includes ALL current ORM model requirements
✅ **Clean** - No legacy artifacts or compatibility code

## Safety Features

- **Confirmation required** - Won't run without `--confirm` flag
- **Auto-detection** - Reads your environment configuration
- **Error handling** - Clear error messages with troubleshooting steps
- **Backup reminder** - Always backup production data before running

## Environment Configuration

The script reads your database configuration from:
- Environment variables (`.env` file)
- FastMCP configuration system
- Auto-detects PostgreSQL vs SQLite from `DATABASE_URL`

## Troubleshooting

### SQLite Issues
```bash
# Check if database file exists
ls -la /data/agenthub.db

# Check permissions
chmod 666 /data/agenthub.db
```

### PostgreSQL Issues
```bash
# Check connection
psql postgresql://user:pass@localhost:5432/dbname

# Check if psycopg2 is installed
pip install psycopg2-binary
```

### Configuration Issues
```bash
# Check environment variables
echo $DATABASE_URL

# Verify config loading
cd agenthub_main/src
python -c "from fastmcp.core.config import get_db_config; print(get_db_config())"
```

## Integration with Application

After initialization, start your application normally:
```bash
# The application will use the newly initialized database
python -m fastmcp.server.mcp_entry_point
```

## Development Workflow

1. Make ORM model changes in `domain/entities/`
2. Update the SQL schema files to match
3. Run `python init_database.py --confirm` to apply changes
4. Test your application

This approach is ideal for the development phase where you can break anything to achieve clean architecture.