# Database Configuration Guide

## Overview

DhafnckMCP uses PostgreSQL as the primary database with Keycloak for authentication. This guide consolidates all database configuration information.

## Current Architecture (as of 2025-09-02)

### Default Configuration
- **Database Type**: PostgreSQL (local Docker container)
- **Authentication**: Keycloak (no hardcoded users)
- **Connection**: Through SQLAlchemy ORM
- **Migration System**: Alembic

### Key Changes from Previous Versions
- ✅ **Default**: PostgreSQL instead of SQLite
- ✅ **Removed**: MVP mode and fallback users
- ✅ **Fixed**: Environment variable loading order
- ✅ **Simplified**: Single database configuration approach

## Environment Configuration

### Required Environment Variables
```env
# Database Configuration
DATABASE_TYPE=postgresql  # Default for local development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dhafnck_db

# Alternative for Supabase (if using cloud)
SUPABASE_DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=prefer

# Connection Pool Settings
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=60
DB_CONNECT_TIMEOUT=30
```

### Database Type Priority
1. `DATABASE_TYPE` environment variable
2. Falls back to PostgreSQL if not specified
3. Never defaults to SQLite in production

## Docker Configuration

### PostgreSQL Container
```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: dhafnck_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Starting the Database
```bash
# Using docker-menu.sh
./docker-system/docker-menu.sh
# Select option: P (PostgreSQL Local)

# Or directly with docker-compose
docker-compose up -d postgres
```

## Database Configuration Module

Located at: `src/fastmcp/task_management/infrastructure/database/database_config.py`

### Key Features
- Automatic .env loading at module import
- Proper environment variable resolution
- Connection pooling and retry logic
- Support for multiple database types

### Configuration Loading
```python
# Loads .env file automatically
from dotenv import load_dotenv
load_dotenv()

# Determines database type
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'postgresql').lower()
```

## Connection Management

### Connection Pool Settings
```python
engine_config = {
    "pool_size": 5,          # Reduced for stability
    "max_overflow": 10,      # Conservative overflow
    "pool_timeout": 60,      # Increased for cloud latency
    "pool_pre_ping": True,   # Verify connections
    "echo": False            # Disable SQL logging in production
}
```

### Retry Logic
- Exponential backoff for connection failures
- Automatic reconnection on transient errors
- Connection validation with SELECT 1 query

## Database Migrations

### Running Migrations
```bash
# Initialize migrations (first time only)
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Migration Files Location
```
dhafnck_mcp_main/
└── alembic/
    ├── versions/       # Migration files
    └── alembic.ini     # Configuration
```

## Testing Configuration

### Test Database
```python
# Separate test database
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/dhafnck_test_db"
```

### Running Tests
```bash
# Set test environment
export DATABASE_TYPE=postgresql
export DATABASE_URL=$TEST_DATABASE_URL

# Run tests
pytest dhafnck_mcp_main/src/tests/
```

## Troubleshooting

### Common Issues

#### Issue: "DATABASE_TYPE not being read from .env"
**Solution**: Fixed in latest version - .env is loaded at module import

#### Issue: Connection timeout to PostgreSQL
**Solution**: Check Docker container is running:
```bash
docker ps | grep postgres
```

#### Issue: "null value in column user_id violates not-null constraint"
**Solution**: System now requires authentication - no MVP fallback

### Debug Commands
```bash
# Check database connection
psql -h localhost -U postgres -d dhafnck_db -c "SELECT 1"

# View current connections
psql -h localhost -U postgres -d dhafnck_db -c "SELECT * FROM pg_stat_activity"

# Check environment variables
python -c "import os; print(os.getenv('DATABASE_TYPE'))"
```

## Production Deployment

### Recommended Settings
```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@host:5432/database
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
```

### Security Considerations
1. Use strong passwords
2. Enable SSL for connections
3. Restrict database access by IP
4. Regular backups
5. Monitor connection pool usage

## Backup and Restore

### Backup Database
```bash
pg_dump -h localhost -U postgres dhafnck_db > backup.sql
```

### Restore Database
```bash
psql -h localhost -U postgres dhafnck_db < backup.sql
```

## Performance Tuning

### PostgreSQL Configuration
```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '256MB';

-- Optimize for SSD
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration
SELECT pg_reload_conf();
```

### Connection Pool Optimization
- Monitor active connections
- Adjust pool_size based on load
- Use connection pooler (pgBouncer) for high traffic

---

**Last Updated**: 2025-09-02
**Status**: Current and Accurate