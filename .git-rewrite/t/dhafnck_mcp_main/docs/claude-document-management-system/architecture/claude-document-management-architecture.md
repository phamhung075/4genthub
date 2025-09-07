# Claude Document Management System Architecture

## Overview

The Claude Document Management System is a PostgreSQL-based solution for managing `.claude/commands` markdown documentation with full CLI+MCP integration. It provides versioning, full-text search, indexing, and seamless synchronization with the file system.

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface                              │
│  manage_document_md [action] [options]                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   MCP Integration Layer                           │
│  - Task Management Integration                                   │
│  - Context Synchronization                                       │
│  - Compliance Tracking                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               Document Management Service                         │
│  - Document CRUD Operations                                      │
│  - Version Control                                               │
│  - Full-Text Search                                             │
│  - Index Management                                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  PostgreSQL Database                              │
│  - Documents Table                                               │
│  - Versions Table                                                │
│  - Search Index                                                  │
│  - Metadata Tables                                               │
└──────────────────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables

#### 1. documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path TEXT UNIQUE NOT NULL,  -- Relative path from .claude/commands/
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'draft',  -- draft, active, deprecated, archived
    file_hash VARCHAR(64),  -- SHA256 hash for change detection
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED
);

CREATE INDEX idx_documents_search ON documents USING GIN (search_vector);
CREATE INDEX idx_documents_path ON documents(path);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
```

#### 2. document_versions
```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    change_summary TEXT,
    file_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    
    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_versions_document ON document_versions(document_id);
CREATE INDEX idx_versions_created ON document_versions(created_at);
```

#### 3. document_metadata
```sql
CREATE TABLE document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(document_id, key)
);

CREATE INDEX idx_metadata_document ON document_metadata(document_id);
CREATE INDEX idx_metadata_key ON document_metadata(key);
CREATE INDEX idx_metadata_value ON document_metadata USING GIN (value);
```

#### 4. document_references
```sql
CREATE TABLE document_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reference_type VARCHAR(20) NOT NULL,  -- mcp, code, path, import
    reference_value TEXT NOT NULL,
    line_number INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_references_document ON document_references(document_id);
CREATE INDEX idx_references_type_value ON document_references(reference_type, reference_value);
```

#### 5. document_index
```sql
CREATE TABLE document_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_documents INTEGER NOT NULL DEFAULT 0,
    index_data JSONB NOT NULL,  -- Stores the complete doc_index.json structure
    file_hash VARCHAR(64)  -- Hash of doc_index.json for change detection
);
```

## CLI Command Interface

### Usage
```bash
manage_document_md [action] [options]
```

### Actions

#### 1. sync
Synchronize file system with database
```bash
manage_document_md sync [--force] [--dry-run]
```

#### 2. search
Full-text search across documents
```bash
manage_document_md search "query" [--category CATEGORY] [--limit N]
```

#### 3. list
List documents with filters
```bash
manage_document_md list [--category CATEGORY] [--status STATUS] [--updated-since DATE]
```

#### 4. show
Display document details
```bash
manage_document_md show <path|id>
```

#### 5. create
Create new document
```bash
manage_document_md create <path> [--title TITLE] [--category CATEGORY]
```

#### 6. update
Update existing document
```bash
manage_document_md update <path|id> [--content FILE] [--title TITLE]
```

#### 7. version
Manage document versions
```bash
manage_document_md version <path|id> [--list] [--diff V1 V2] [--restore VERSION]
```

#### 8. index
Generate/update doc_index.json
```bash
manage_document_md index [--output FILE] [--format json|yaml]
```

#### 9. validate
Validate documents against standards
```bash
manage_document_md validate [<path|id>] [--fix]
```

#### 10. export
Export documents
```bash
manage_document_md export [--format md|pdf|html] [--output DIR]
```

## MCP Integration

### Task Integration
```python
# Create task for document update
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title=f"Update documentation: {document_path}",
    description="Update command documentation with latest changes",
    labels=["documentation", "cli-commands"]
)

# Track document operations
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "document_operation": "update",
        "document_path": document_path,
        "changes": change_summary
    }
)
```

### Compliance Tracking
```python
# Validate document operations
mcp__dhafnck_mcp_http__manage_compliance(
    action="validate_compliance",
    operation="update_documentation",
    file_path=document_path,
    content=new_content,
    security_level="internal"
)
```

## Implementation Features

### 1. File System Synchronization
- Monitor `.claude/commands/` directory for changes
- Detect new, modified, and deleted files
- Calculate file hashes for change detection
- Batch synchronization for efficiency

### 2. Version Control
- Automatic versioning on content changes
- Diff generation between versions
- Version restoration capability
- Change history tracking

### 3. Full-Text Search
- PostgreSQL full-text search with ranking
- Search across title, description, and content
- Category and status filtering
- Code reference search

### 4. Document Validation
- Markdown syntax validation
- Link checking
- Code reference validation
- Structure compliance

### 5. Index Generation
- Generate doc_index.json from database
- Support for multiple output formats
- Incremental updates
- Change detection

## Configuration

### Environment Variables
```bash
# Database connection
CLAUDE_DOC_DB_HOST=localhost
CLAUDE_DOC_DB_PORT=5432
CLAUDE_DOC_DB_NAME=claude_docs
CLAUDE_DOC_DB_USER=claude
CLAUDE_DOC_DB_PASSWORD=secure_password

# Document management
CLAUDE_DOC_ROOT=/home/user/project/.claude/commands
CLAUDE_DOC_INDEX_PATH=/home/user/project/.claude/doc_index.json
CLAUDE_DOC_SYNC_INTERVAL=300  # seconds

# Search configuration
CLAUDE_DOC_SEARCH_LANGUAGE=english
CLAUDE_DOC_SEARCH_MIN_LENGTH=3
```

### Configuration File
```yaml
# .claude/doc_config.yaml
database:
  host: localhost
  port: 5432
  name: claude_docs
  
documents:
  root_path: .claude/commands
  index_path: .claude/doc_index.json
  watch_enabled: true
  sync_interval: 300
  
categories:
  - api
  - architecture
  - testing
  - troubleshooting
  - migration
  
validation:
  check_links: true
  check_code_refs: true
  max_line_length: 120
```

## Security Considerations

1. **Access Control**
   - Role-based access for document operations
   - Audit trail for all modifications
   - Secure credential storage

2. **Data Protection**
   - Encrypted database connections
   - Backup and recovery procedures
   - Version retention policies

3. **Compliance**
   - Document access logging
   - Change tracking
   - Retention policies

## Performance Optimization

1. **Indexing**
   - GIN indexes for full-text search
   - B-tree indexes for lookups
   - Partial indexes for common queries

2. **Caching**
   - Query result caching
   - Document content caching
   - Index data caching

3. **Batch Operations**
   - Bulk synchronization
   - Batch updates
   - Efficient diff algorithms

## Migration Strategy

### Phase 1: Database Setup
1. Create PostgreSQL database and schema
2. Set up connection pooling
3. Configure backup procedures

### Phase 2: Initial Import
1. Scan existing .claude/commands directory
2. Import all documents with metadata
3. Generate initial index

### Phase 3: Integration
1. Update manage_document_md script
2. Add MCP integration hooks
3. Set up file watchers

### Phase 4: Validation
1. Verify data integrity
2. Test search functionality
3. Validate synchronization

## Future Enhancements

1. **AI-Powered Features**
   - Auto-categorization
   - Content suggestions
   - Duplicate detection

2. **Collaboration**
   - Multi-user editing
   - Review workflows
   - Comment system

3. **Analytics**
   - Usage statistics
   - Search analytics
   - Quality metrics

4. **Integration**
   - IDE plugins
   - CI/CD integration
   - API endpoints