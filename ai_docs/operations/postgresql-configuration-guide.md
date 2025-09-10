# PostgreSQL Configuration Guide

## System Configuration

This system uses **PostgreSQL** exclusively for database operations.

## Supported Database Types

- **Supabase** (Recommended for production)
- **PostgreSQL** (Local development)

## Configuration Requirements

### 1. **Environment Variables**

Required environment variables in your `.env` file:

```bash
# Database Type (required)
DATABASE_TYPE=supabase  # or 'postgresql' for local

# For Supabase:
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DATABASE_URL=postgresql://...

# For Local PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 2. **Docker Configuration**

The system includes Docker Compose configurations for both development and production:

- `docker-compose.yml` - Main configuration
- `docker-compose.postgresql.yml` - PostgreSQL specific setup
- `docker-compose.supabase.yml` - Supabase integration

### 3. **Database Schema**

All tables are automatically created via SQLAlchemy ORM on first run.

### 4. **Connection Pooling**

PostgreSQL connections are managed efficiently with:
- Pool size: 15 connections
- Max overflow: 25 connections
- Pool timeout: 30 seconds
- Echo: Disabled in production

## Migration from Legacy Systems

If migrating from other database systems, use:
```bash
python scripts/migrate_to_postgresql.py
```

## Development Setup

1. Set up environment variables
2. Start Docker containers:
   ```bash
   docker-compose up -d
   ```
3. Initialize database:
   ```bash
   python scripts/init_database.py
   ```

## Production Setup

1. Configure Supabase credentials
2. Set `DATABASE_TYPE=supabase`
3. Deploy with Docker:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.supabase.yml up -d
   ```

## Benefits of PostgreSQL

- **Performance**: Superior query performance and indexing
- **Concurrency**: Better concurrent access handling
- **Data Integrity**: ACID compliance and foreign key constraints
- **Scalability**: Horizontal and vertical scaling options
- **JSON Support**: Native JSONB data type for flexible schemas
- **Full-text Search**: Built-in text search capabilities
- **Replication**: Master-slave replication support

## Troubleshooting

### Connection Issues
- Verify DATABASE_TYPE is set correctly
- Check PostgreSQL service is running
- Confirm network connectivity to database

### Performance Optimization
- Monitor connection pool usage
- Optimize queries with EXPLAIN ANALYZE
- Use appropriate indexes for frequent queries

## Support

For database-related issues, check:
- `/ai_docs/architecture-design/database-architecture.md`
- `/ai_docs/troubleshooting-guides/COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md`