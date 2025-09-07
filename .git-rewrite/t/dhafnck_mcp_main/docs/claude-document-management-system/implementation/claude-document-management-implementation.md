# Claude Document Management System - Implementation Guide

## Quick Start

### Prerequisites

1. **PostgreSQL Database**
   ```bash
   # Install PostgreSQL (Ubuntu/Debian)
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # Start PostgreSQL service
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Database Setup**
   ```bash
   # Create database and user
   sudo -u postgres psql
   ```
   ```sql
   CREATE DATABASE claude_docs;
   CREATE USER claude WITH ENCRYPTED PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE claude_docs TO claude;
   \q
   ```

3. **Environment Configuration**
   ```bash
   # Add to ~/.bashrc or project .env
   export CLAUDE_DOC_DB_HOST=localhost
   export CLAUDE_DOC_DB_PORT=5432
   export CLAUDE_DOC_DB_NAME=claude_docs
   export CLAUDE_DOC_DB_USER=claude
   export CLAUDE_DOC_DB_PASSWORD=your_secure_password
   ```

### Installation

1. **Copy the PostgreSQL command**
   ```bash
   cp .claude/commands/manage_document_md_postgresql .claude/commands/manage_document_md_pg
   chmod +x .claude/commands/manage_document_md_pg
   ```

2. **Initialize the database**
   ```bash
   .claude/commands/manage_document_md_pg init
   ```

3. **Initial synchronization**
   ```bash
   .claude/commands/manage_document_md_pg sync
   ```

4. **Generate initial index**
   ```bash
   .claude/commands/manage_document_md_pg index
   ```

## Detailed Usage

### 1. Database Management

#### Initialize Database Schema
```bash
manage_document_md_pg init
```

This creates all necessary tables:
- `documents` - Main document storage
- `document_versions` - Version history
- `document_metadata` - Key-value metadata
- `document_references` - Code/path references
- `document_index` - Generated index snapshots

#### Check Database Status
```bash
# Test connection
psql postgresql://claude@localhost:5432/claude_docs -c "SELECT COUNT(*) FROM documents;"

# View table sizes
psql postgresql://claude@localhost:5432/claude_docs -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    null_frac
FROM pg_stats 
WHERE schemaname = 'public';"
```

### 2. Document Synchronization

#### Full Synchronization
```bash
# Sync all documents
manage_document_md_pg sync

# Dry run to see what would change
manage_document_md_pg sync --dry-run

# Force update all documents
manage_document_md_pg sync --force
```

#### Monitoring Changes
```bash
# Set up file watcher (requires inotify-tools)
sudo apt install inotify-tools

# Watch for changes and auto-sync
while inotifywait -r -e modify,create,delete .claude/commands/; do
    echo "Changes detected, syncing..."
    manage_document_md_pg sync
done
```

### 3. Search and Discovery

#### Full-Text Search
```bash
# Basic search
manage_document_md_pg search "postgresql database"

# Search within category
manage_document_md_pg search "mcp integration" --category api

# Limited results
manage_document_md_pg search "troubleshooting" --limit 5
```

#### Advanced Search Examples
```bash
# Search for MCP tools
manage_document_md_pg search "manage_task manage_context"

# Search for specific patterns
manage_document_md_pg search "CLI command bash script"

# Search for configuration
manage_document_md_pg search "environment variable config" --category configuration
```

### 4. Document Management

#### List Documents
```bash
# List all active documents
manage_document_md_pg list

# List by category
manage_document_md_pg list --category testing

# List recently updated
manage_document_md_pg list --updated-since "2024-07-01"

# List archived documents
manage_document_md_pg list --status archived
```

#### View Document Details
```bash
# Show by path
manage_document_md_pg show "manage-test.md"

# Show by UUID (from list/search results)
manage_document_md_pg show "550e8400-e29b-41d4-a716-446655440000"
```

### 5. Index Generation

#### Generate doc_index.json
```bash
# Generate standard index
manage_document_md_pg index

# Custom output location
manage_document_md_pg index --output /tmp/custom_index.json

# YAML format (future enhancement)
manage_document_md_pg index --format yaml --output docs_index.yaml
```

### 6. MCP Integration

#### Task Integration
```bash
# Create task for document update
manage_document_md_pg mcp create-task "api-reference.md"

# Track document changes
manage_document_md_pg mcp track-change "doc-uuid" "Updated API examples"
```

#### Integration with DhafnckMCP
```bash
# Example workflow with MCP tools
export TASK_ID=$(mcp__dhafnck_mcp_http__manage_task action="create" \
    title="Update CLI documentation" \
    description="Enhance manage_document_md with PostgreSQL backend")

# Track progress
mcp__dhafnck_mcp_http__manage_context action="update" \
    level="task" context_id="$TASK_ID" \
    data='{"document_operation": "sync", "documents_processed": 42}'

# Complete task
mcp__dhafnck_mcp_http__manage_task action="complete" \
    task_id="$TASK_ID" \
    completion_summary="PostgreSQL document management system implemented"
```

## Advanced Features

### 1. Version Management

#### SQL Queries for Version History
```sql
-- Get version history for a document
SELECT 
    dv.version_number,
    dv.change_summary,
    dv.created_at,
    dv.created_by,
    LENGTH(dv.content) as content_length
FROM document_versions dv
JOIN documents d ON dv.document_id = d.id
WHERE d.path = 'manage-test.md'
ORDER BY dv.version_number DESC;

-- Compare two versions
SELECT 
    v1.version_number as version_1,
    v2.version_number as version_2,
    LENGTH(v1.content) as v1_length,
    LENGTH(v2.content) as v2_length,
    v1.created_at as v1_date,
    v2.created_at as v2_date
FROM document_versions v1, document_versions v2
WHERE v1.document_id = v2.document_id
    AND v1.version_number = 1
    AND v2.version_number = 2;
```

### 2. Advanced Search

#### Complex Search Queries
```sql
-- Search with ranking and highlighting
SELECT 
    d.path,
    d.title,
    ts_rank_cd(d.search_vector, query) AS rank,
    ts_headline('english', d.content, query, 'MaxWords=20, MinWords=5') AS snippet
FROM documents d, 
     plainto_tsquery('english', 'postgresql cli integration') query
WHERE d.search_vector @@ query
    AND d.status = 'active'
ORDER BY rank DESC
LIMIT 10;

-- Search by category and content
SELECT 
    d.path,
    d.title,
    d.category,
    d.updated_at
FROM documents d
WHERE d.category IN ('api', 'testing')
    AND d.search_vector @@ to_tsquery('english', 'mcp & tool')
ORDER BY d.updated_at DESC;
```

### 3. Analytics and Reporting

#### Document Statistics
```sql
-- Category distribution
SELECT 
    category,
    COUNT(*) as doc_count,
    AVG(LENGTH(content)) as avg_length,
    MIN(updated_at) as oldest_update,
    MAX(updated_at) as newest_update
FROM documents
WHERE status = 'active'
GROUP BY category
ORDER BY doc_count DESC;

-- Update frequency
SELECT 
    DATE_TRUNC('week', updated_at) as week,
    COUNT(*) as updates
FROM documents
WHERE updated_at >= NOW() - INTERVAL '3 months'
GROUP BY week
ORDER BY week;

-- Most referenced documents
SELECT 
    d.path,
    d.title,
    COUNT(dr.id) as reference_count
FROM documents d
LEFT JOIN document_references dr ON d.id = dr.document_id
WHERE d.status = 'active'
GROUP BY d.id, d.path, d.title
ORDER BY reference_count DESC
LIMIT 10;
```

### 4. Maintenance Operations

#### Database Maintenance
```bash
# Vacuum and analyze tables
psql "$DB_CONN" -c "VACUUM ANALYZE documents;"
psql "$DB_CONN" -c "VACUUM ANALYZE document_versions;"

# Reindex search vectors
psql "$DB_CONN" -c "REINDEX INDEX idx_documents_search;"

# Update statistics
psql "$DB_CONN" -c "ANALYZE documents;"
```

#### Cleanup Operations
```sql
-- Archive old versions (keep last 5)
WITH versions_to_keep AS (
    SELECT id
    FROM (
        SELECT id, 
               ROW_NUMBER() OVER (PARTITION BY document_id ORDER BY version_number DESC) as rn
        FROM document_versions
    ) ranked
    WHERE rn <= 5
)
DELETE FROM document_versions 
WHERE id NOT IN (SELECT id FROM versions_to_keep);

-- Clean up orphaned metadata
DELETE FROM document_metadata dm
WHERE NOT EXISTS (
    SELECT 1 FROM documents d WHERE d.id = dm.document_id AND d.status != 'archived'
);
```

## Performance Optimization

### 1. Database Tuning

#### PostgreSQL Configuration
```sql
-- Optimize for text search
ALTER SYSTEM SET default_text_search_config = 'pg_catalog.english';

-- Increase work memory for search operations
ALTER SYSTEM SET work_mem = '256MB';

-- Optimize for read-heavy workload
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_cache_size = '1GB';

-- Reload configuration
SELECT pg_reload_conf();
```

#### Index Optimization
```sql
-- Create partial indexes for common queries
CREATE INDEX idx_documents_active_category 
ON documents(category) 
WHERE status = 'active';

CREATE INDEX idx_documents_recent 
ON documents(updated_at) 
WHERE updated_at >= NOW() - INTERVAL '1 month';

-- Analyze index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### 2. Query Optimization

#### Efficient Search Patterns
```bash
# Use specific categories to narrow results
manage_document_md_pg search "api" --category api --limit 10

# Combine with other filters
manage_document_md_pg list --category testing --updated-since "2024-07-01"
```

#### Batch Operations
```sql
-- Batch update documents
UPDATE documents 
SET status = 'active', updated_at = NOW()
WHERE status = 'draft' 
    AND created_at <= NOW() - INTERVAL '1 day';

-- Batch insert versions
INSERT INTO document_versions (document_id, version_number, content, file_hash)
SELECT 
    d.id,
    COALESCE(MAX(dv.version_number), 0) + 1,
    d.content,
    d.file_hash
FROM documents d
LEFT JOIN document_versions dv ON d.id = dv.document_id
WHERE d.updated_at >= NOW() - INTERVAL '1 hour'
GROUP BY d.id, d.content, d.file_hash;
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Problems
```bash
# Test connection
psql "postgresql://claude@localhost:5432/claude_docs" -c "SELECT version();"

# Check if database exists
psql -l | grep claude_docs

# Check user permissions
psql -c "SELECT * FROM pg_user WHERE usename = 'claude';"
```

#### 2. Permission Issues
```sql
-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO claude;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claude;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claude;
```

#### 3. Search Not Working
```sql
-- Check search configuration
SELECT * FROM pg_ts_config WHERE cfgname = 'english';

-- Verify search vectors
SELECT path, search_vector FROM documents LIMIT 1;

-- Rebuild search vectors if needed
UPDATE documents SET content = content;
```

#### 4. Performance Issues
```sql
-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE query LIKE '%documents%'
ORDER BY total_time DESC
LIMIT 10;

-- Analyze table statistics
SELECT 
    attname,
    n_distinct,
    null_frac,
    avg_width
FROM pg_stats
WHERE tablename = 'documents';
```

### Recovery Procedures

#### Database Recovery
```bash
# Create backup
pg_dump "$DB_CONN" > claude_docs_backup.sql

# Restore from backup
psql "$DB_CONN" < claude_docs_backup.sql

# Re-sync after recovery
manage_document_md_pg sync --force
```

#### Index Corruption
```sql
-- Drop and recreate search index
DROP INDEX idx_documents_search;
CREATE INDEX idx_documents_search ON documents USING GIN (search_vector);

-- Refresh all search vectors
UPDATE documents SET updated_at = NOW();
```

## Security Considerations

### 1. Database Security
```sql
-- Create read-only user for reporting
CREATE USER claude_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE claude_docs TO claude_readonly;
GRANT USAGE ON SCHEMA public TO claude_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
```

### 2. Access Control
```bash
# Set proper file permissions
chmod 600 ~/.pgpass  # PostgreSQL password file
chmod 700 ~/.claude/  # Claude configuration directory
```

### 3. Audit Trail
```sql
-- Create audit table
CREATE TABLE document_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID,
    action VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_name VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create audit trigger
CREATE OR REPLACE FUNCTION audit_documents()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO document_audit (document_id, action, old_values, new_values, user_name)
    VALUES (
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        to_jsonb(OLD),
        to_jsonb(NEW),
        current_user
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON documents
FOR EACH ROW EXECUTE FUNCTION audit_documents();
```

## Integration Examples

### 1. CI/CD Integration
```yaml
# .github/workflows/docs.yml
name: Documentation Sync
on:
  push:
    paths: ['.claude/commands/**']

jobs:
  sync-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup PostgreSQL
        # ... setup steps
      - name: Sync documents
        run: |
          .claude/commands/manage_document_md_pg sync
          .claude/commands/manage_document_md_pg index
```

### 2. Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check if any .md files in .claude/commands changed
if git diff --cached --name-only | grep -q '.claude/commands/.*\.md$'; then
    echo "Syncing documentation changes..."
    .claude/commands/manage_document_md_pg sync --dry-run
    
    if [ $? -ne 0 ]; then
        echo "Documentation sync check failed!"
        exit 1
    fi
fi
```

### 3. API Integration
```bash
# REST API wrapper (future enhancement)
#!/bin/bash
# api_server.sh

case "$REQUEST_METHOD" in
    GET)
        case "$PATH_INFO" in
            /docs) manage_document_md_pg list --format json ;;
            /docs/search) manage_document_md_pg search "$QUERY_STRING" --format json ;;
            *) echo "404 Not Found" ;;
        esac
        ;;
    POST)
        # Handle document updates
        ;;
esac
```

This implementation provides a robust, scalable document management system with full PostgreSQL backend, CLI interface, and MCP integration for the Claude commands ecosystem.