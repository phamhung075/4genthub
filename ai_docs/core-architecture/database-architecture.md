# Database Architecture Guide

## Overview

DhafnckMCP implements a **dual PostgreSQL architecture** designed for optimal development-production parity while leveraging cloud-managed services for production scale.

## Architecture Design

### Dual PostgreSQL Setup

```
┌─────────────────────────────────────────────────────────────┐
│                DhafnckMCP Database Architecture             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Production Environment          Development Environment    │
│  ┌─────────────────────────┐      ┌────────────────────────┐│
│  │  Supabase Cloud         │      │ PostgreSQL Docker      ││
│  │  PostgreSQL             │      │ Container              ││
│  │                         │      │                        ││
│  │  • Fully managed        │ <──> │ • Local development    ││
│  │  • Global distribution  │      │ • Full feature parity  ││
│  │  • Auto backups         │      │ • Same PostgreSQL ver. ││
│  │  • Real-time features   │      │ • Isolated environment ││
│  │  • Built-in auth        │      │ • Fast iteration       ││
│  └─────────────────────────┘      └────────────────────────┘│
│                                                             │
│  Configuration:                   Configuration:            │
│  DATABASE_TYPE=supabase           DATABASE_TYPE=postgresql  │
│  SUPABASE_URL=...                 DATABASE_URL=postgresql://│
│  SUPABASE_ANON_KEY=...            ...@localhost:5432/...    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

#### Production (Supabase)
```bash
# Database type selection
DATABASE_TYPE=supabase

# Supabase project configuration
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=eyJ[your-anon-key]
SUPABASE_DB_PASSWORD=your-secure-database-password

# Optional: Direct database URL (alternative to Supabase config)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require

# Region optimization
SUPABASE_REGION=us-west-1  # Choose closest to your users
```

#### Development (Docker PostgreSQL)
```bash
# Database type selection
DATABASE_TYPE=postgresql

# Local development database
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/dhafnck_mcp_dev

# Docker container database
DATABASE_URL=postgresql://dhafnck_user:dhafnck_password@postgres:5432/dhafnck_mcp

# Connection pool settings (optional)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
```

#### Testing
```bash
# Test database (PostgreSQL for consistency)
DATABASE_TYPE=postgresql
TEST_DATABASE_URL=postgresql://postgres:test@localhost:5432/dhafnck_mcp_test
```

## Implementation Details

### Database Selection Logic

```python
# In database_config.py
class DatabaseConfig:
    def _get_database_url(self) -> str:
        if self.database_type == "supabase":
            # Production: Use Supabase managed PostgreSQL
            from .supabase_config import get_supabase_config
            supabase_config = get_supabase_config()
            return supabase_config.database_url
            
        elif self.database_type == "postgresql":
            # Development: Use local PostgreSQL
            return self.database_url
            
        else:
            # Invalid database type
            raise ValueError(f"Unsupported database type: {self.database_type}. Use 'postgresql' or 'supabase'.")
```

### Connection Optimization

#### Supabase Optimizations
```python
# Connection pool optimized for cloud database
engine = create_engine(
    database_url,
    pool_size=10,           # Smaller for cloud
    max_overflow=20,
    pool_pre_ping=True,     # Health checks
    pool_recycle=300,       # 5-minute recycle
    connect_args={
        "connect_timeout": 10,
        "application_name": "dhafnck_mcp",
        "keepalives": 1,
        "keepalives_idle": 30,
    }
)
```

#### Local PostgreSQL Optimizations
```python
# Connection pool optimized for local development
engine = create_engine(
    database_url,
    pool_size=20,           # Larger local pool
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,      # 1-hour recycle
    echo=True,              # SQL logging for dev
)
```

## Schema Management

### Migration Strategy

Both environments use identical schemas managed by Alembic:

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply to development
DATABASE_TYPE=postgresql alembic upgrade head

# Apply to production
DATABASE_TYPE=supabase alembic upgrade head
```

### Schema Synchronization

1. **Single Source of Truth**: All schema changes defined in SQLAlchemy models
2. **Automated Migrations**: Alembic generates migrations from model changes
3. **Environment Consistency**: Same PostgreSQL features in both environments
4. **Version Control**: Migration files tracked in git

## Operational Considerations

### Backup Strategy

#### Production (Supabase)
- **Automatic Backups**: Managed by Supabase (point-in-time recovery)
- **Export Options**: pg_dump available through Supabase dashboard
- **Retention**: Configurable retention period

#### Development
- **Docker Volumes**: Persistent storage via named volumes
- **Manual Backups**: pg_dump for local snapshots
- **Reset Capability**: Easy container recreation for clean state

### Monitoring

#### Health Checks
```python
# Database health check endpoint
@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database_type": database_type}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

#### Metrics
- Connection pool utilization
- Query performance
- Error rates
- Database size (Supabase dashboard)

### Security

#### Production Security
- **SSL/TLS**: Required for Supabase connections
- **Connection Pooling**: Supabase pooler for connection management
- **Access Control**: Supabase RLS (Row Level Security) available
- **Audit Logging**: Built-in audit capabilities

#### Development Security
- **Network Isolation**: Docker network isolation
- **Credentials**: Development-only credentials
- **Local Access**: Restricted to development environment

## Migration from Legacy SQLite

### Migration Steps

1. **Backup Existing Data**:
   ```bash
   # Export SQLite data
   sqlite3 dhafnck_mcp.db .dump > backup.sql
   ```

2. **Setup PostgreSQL Environment**:
   ```bash
   # Start PostgreSQL container
   docker-compose up -d postgres
   ```

3. **Run Migration Script**:
   ```bash
   # Use migration script
   python scripts/migrate_to_postgresql.py
   ```

4. **Update Configuration**:
   ```bash
   # Switch to PostgreSQL
   export DATABASE_TYPE=postgresql
   export DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/dhafnck_mcp_dev
   ```

### Data Migration

The migration preserves:
- All task data and relationships
- Project and branch structures  
- Agent assignments and configurations
- Hierarchical context data
- User preferences and settings

## Troubleshooting

### Common Issues

#### Connection Issues
```bash
# Test Supabase connection
psql "postgresql://postgres.[project]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require"

# Test local PostgreSQL
psql -h localhost -p 5432 -U dev_user -d dhafnck_mcp_dev
```

#### Performance Issues
- Monitor connection pool utilization
- Check query execution plans
- Review Supabase performance insights
- Optimize frequently-used queries

#### Migration Issues
- Verify schema compatibility
- Check foreign key constraints
- Validate data types
- Review index configurations

## Future Enhancements

### Planned Features

1. **Multi-Region Support**: Supabase multi-region deployment
2. **Read Replicas**: Read-only replicas for scale
3. **Connection Pooling**: Advanced pooling strategies
4. **Caching Layer**: Redis integration for frequently-accessed data
5. **Analytics**: Advanced database analytics and insights

This dual PostgreSQL architecture provides the foundation for scalable, reliable, and maintainable database operations while ensuring development-production parity.