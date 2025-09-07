# Phase 2: pgvector Semantic Search Implementation Guide

## Overview

This guide provides detailed implementation steps for Phase 2 of the Claude Document Management System, focusing on adding semantic search capabilities using PostgreSQL's pgvector extension.

## Prerequisites

- [x] Phase 1 PostgreSQL baseline completed
- [ ] PostgreSQL 15+ with pgvector extension support
- [ ] Python environment with required ML libraries
- [ ] OpenAI API key or local embedding model setup

## Implementation Checklist

## 📁 Phase 2 File Creation Locations & Specifications

### Python Services Directory
**Location**: `dhafnck_mcp_main/services/`

1. **`embedding_service.py`** (~300 lines)
   - **Purpose**: Generate and manage document embeddings using OpenAI API
   - **Key Classes**: `EmbeddingService`, `EmbeddingQueue`
   - **Dependencies**: OpenAI API, PostgreSQL, pgvector
   - **Features**: Batch processing, rate limiting, error handling

2. **`requirements_phase2.txt`** 
   - **Location**: `dhafnck_mcp_main/requirements_phase2.txt`
   - **Contents**: openai>=1.0.0, psycopg2-binary>=2.9.0, python-dotenv>=0.19.0, numpy>=1.21.0

### Database Scripts Directory
**Location**: `dhafnck_mcp_main/database/`

3. **`phase2_pgvector.sql`** (~50 lines)
   - **Purpose**: Add pgvector extension and vector columns to existing schema
   - **Contents**: Extension creation, vector columns, indexes

4. **`migrations/migration_001_add_vectors.sql`** (~30 lines)
   - **Purpose**: Safe migration script for existing databases
   - **Features**: Rollback support, data preservation

### Configuration Directory
**Location**: `dhafnck_mcp_main/config/`

5. **`.pgvector_config`**
   - **Purpose**: pgvector-specific configuration
   - **Contents**: Index parameters, embedding dimensions, optimization settings

### Test Files Structure
**Location**: `dhafnck_mcp_main/tests/`

6. **`phase2/test_phase2.sh`**
   - **Purpose**: Comprehensive Phase 2 integration testing
   - **Tests**: pgvector installation, embedding generation, semantic search

7. **`unit/test_embedding_service.py`**
   - **Purpose**: Unit tests for embedding service
   - **Coverage**: API calls, database operations, error handling, rate limiting

8. **`integration/test_semantic_search.py`**
   - **Purpose**: Integration tests for semantic search functionality
   - **Coverage**: Query processing, result ranking, performance benchmarks

### Enhanced CLI Updates
**Location**: `.claude/commands/manage_document_md_postgresql`

9. **Updated CLI Script** (+200 lines)
   - **New Actions**: `semantic-search`, `generate-embeddings`
   - **New Options**: `--hybrid`, `--threshold`, `--batch-size`
   - **Features**: Hybrid search, similarity thresholds, batch processing

## Test Strategy for Phase 2

### Unit Tests (Fast, Isolated)
- `test_embedding_service.py`: Test embedding generation, API integration, error handling
- `test_vector_operations.py`: Test vector similarity calculations and indexing
- `test_pgvector_integration.py`: Test database vector operations

### Integration Tests (Component Interaction)
- `test_semantic_search.py`: End-to-end semantic search functionality
- `test_hybrid_search.py`: Combined keyword + semantic search
- `test_cli_semantic_commands.py`: CLI semantic search commands

### Performance Tests (Benchmarks)
- `test_embedding_performance.py`: Embedding generation speed benchmarks
- `test_vector_search_performance.py`: Vector search response time tests
- `test_index_optimization.py`: Vector index performance validation

### Phase 2 File Creation Checklist
- [ ] Create `services/embedding_service.py` with OpenAI integration
- [ ] Create `requirements_phase2.txt` with Python dependencies
- [ ] Create `database/phase2_pgvector.sql` schema additions
- [ ] Create `database/migrations/migration_001_add_vectors.sql`
- [ ] Update CLI script with semantic search functions
- [ ] Create `config/.pgvector_config` configuration file
- [ ] Create `tests/phase2/test_phase2.sh` integration test script
- [ ] Create `tests/unit/test_embedding_service.py` unit tests
- [ ] Create `tests/integration/test_semantic_search.py` integration tests

### Step 1: pgvector Extension Setup

#### 1.1 Install pgvector Extension
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15-pgvector

# From source (if package not available)
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Checklist:**
- [ ] pgvector extension installed on system
- [ ] PostgreSQL service restarted
- [ ] Extension available in PostgreSQL

#### 1.2 Enable Extension in Database
```sql
-- Connect to claude_docs database
\c claude_docs

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test basic vector operations
SELECT '[1,2,3]'::vector;
SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector;
```

**Checklist:**
- [ ] Extension created successfully
- [ ] Vector operations work correctly
- [ ] Distance calculations functional

#### 1.3 Configure PostgreSQL for Vectors
```sql
-- Increase max_connections if needed
ALTER SYSTEM SET max_connections = 200;

-- Increase shared_buffers for better vector performance
ALTER SYSTEM SET shared_buffers = '256MB';

-- Optimize for vector operations
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration
SELECT pg_reload_conf();
```

**Checklist:**
- [ ] PostgreSQL configuration optimized
- [ ] Settings applied and reloaded
- [ ] Performance baseline established

### Step 2: Database Schema Enhancement

#### 2.1 Add Embedding Column
```sql
-- Add embedding column to documents table
ALTER TABLE documents ADD COLUMN embedding vector(1536);

-- Add embedding metadata
ALTER TABLE documents ADD COLUMN embedding_model VARCHAR(100);
ALTER TABLE documents ADD COLUMN embedding_generated_at TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN embedding_status VARCHAR(20) DEFAULT 'pending';

-- Create embedding processing queue table
CREATE TABLE embedding_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'queued',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_embedding_queue_status ON embedding_queue(status, priority DESC);
```

**Checklist:**
- [ ] Embedding column added successfully
- [ ] Metadata columns created
- [ ] Processing queue table created
- [ ] Indexes created for performance

#### 2.2 Create Vector Indexes
```sql
-- Create IVFFlat index for vector similarity search
-- Note: You need some data with embeddings before creating the index
-- This will be done after embedding generation

-- For now, create a placeholder
-- CREATE INDEX idx_documents_embedding ON documents 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Checklist:**
- [ ] Index strategy planned
- [ ] Index creation deferred until data available
- [ ] Index parameters researched

### Step 3: Embedding Generation Service

#### 3.1 Create Embedding Service Script
```python
#!/usr/bin/env python3
# embedding_service.py

import os
import json
import hashlib
import psycopg2
import openai
from typing import List, Optional
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.db_conn = self._get_db_connection()
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.embedding_model = 'text-embedding-ada-002'
        self.batch_size = 10
        self.rate_limit_delay = 1  # seconds between API calls
    
    def _get_db_connection(self):
        return psycopg2.connect(
            host=os.getenv('CLAUDE_DOC_DB_HOST', 'localhost'),
            port=os.getenv('CLAUDE_DOC_DB_PORT', '5432'),
            database=os.getenv('CLAUDE_DOC_DB_NAME', 'claude_docs'),
            user=os.getenv('CLAUDE_DOC_DB_USER', 'claude'),
            password=os.getenv('CLAUDE_DOC_DB_PASSWORD')
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def process_embedding_queue(self):
        """Process pending embeddings in queue"""
        cursor = self.db_conn.cursor()
        
        # Get queued items
        cursor.execute("""
            SELECT eq.id, eq.document_id, d.title, d.content
            FROM embedding_queue eq
            JOIN documents d ON eq.document_id = d.id
            WHERE eq.status = 'queued'
            ORDER BY eq.priority DESC, eq.created_at ASC
            LIMIT %s
        """, (self.batch_size,))
        
        queue_items = cursor.fetchall()
        
        for queue_id, doc_id, title, content in queue_items:
            try:
                # Mark as processing
                cursor.execute("""
                    UPDATE embedding_queue SET status = 'processing' 
                    WHERE id = %s
                """, (queue_id,))
                self.db_conn.commit()
                
                # Generate embedding
                text = f"{title}\n\n{content}"
                embedding = self.generate_embedding(text)
                
                # Update document with embedding
                cursor.execute("""
                    UPDATE documents SET 
                        embedding = %s,
                        embedding_model = %s,
                        embedding_generated_at = NOW(),
                        embedding_status = 'completed'
                    WHERE id = %s
                """, (embedding, self.embedding_model, doc_id))
                
                # Mark queue item as completed
                cursor.execute("""
                    UPDATE embedding_queue SET 
                        status = 'completed',
                        processed_at = NOW()
                    WHERE id = %s
                """, (queue_id,))
                
                self.db_conn.commit()
                logger.info(f"Generated embedding for document {doc_id}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                # Mark as failed
                cursor.execute("""
                    UPDATE embedding_queue SET 
                        status = 'failed',
                        error_message = %s,
                        processed_at = NOW()
                    WHERE id = %s
                """, (str(e), queue_id))
                self.db_conn.commit()
                logger.error(f"Failed to generate embedding for document {doc_id}: {e}")
        
        cursor.close()
    
    def queue_all_documents(self):
        """Queue all documents without embeddings"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO embedding_queue (document_id, priority)
            SELECT id, 1 FROM documents 
            WHERE embedding IS NULL 
            AND status = 'active'
            ON CONFLICT (document_id) DO NOTHING
        """)
        self.db_conn.commit()
        cursor.close()
        logger.info("Queued all documents for embedding generation")

if __name__ == "__main__":
    service = EmbeddingService()
    
    # Queue all existing documents
    service.queue_all_documents()
    
    # Process queue
    while True:
        service.process_embedding_queue()
        
        # Check if there are more items
        cursor = service.db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embedding_queue WHERE status = 'queued'")
        remaining = cursor.fetchone()[0]
        cursor.close()
        
        if remaining == 0:
            logger.info("All embeddings processed")
            break
        
        logger.info(f"{remaining} embeddings remaining")
        time.sleep(5)
```

**Checklist:**
- [ ] Embedding service script created
- [ ] OpenAI API integration configured
- [ ] Database connection established
- [ ] Error handling implemented
- [ ] Rate limiting configured

#### 3.2 Create Requirements File
```txt
# requirements_phase2.txt
openai>=1.0.0
psycopg2-binary>=2.9.0
python-dotenv>=0.19.0
numpy>=1.21.0
```

**Checklist:**
- [ ] Requirements file created
- [ ] Dependencies listed
- [ ] Version constraints specified

#### 3.3 Environment Configuration
```bash
# Add to ~/.claude_doc_env
export OPENAI_API_KEY="your-api-key-here"
export EMBEDDING_MODEL="text-embedding-ada-002"
export EMBEDDING_BATCH_SIZE=10
export EMBEDDING_RATE_LIMIT=1
```

**Checklist:**
- [ ] Environment variables configured
- [ ] API key secured
- [ ] Configuration parameters set

### Step 4: CLI Enhancement for Semantic Search

#### 4.1 Update manage_document_md_postgresql
```bash
# Add new functions to the CLI script

# Function to generate embeddings
action_generate_embeddings() {
    print_header "Generating Document Embeddings"
    
    if ! check_db_connection; then
        return 1
    fi
    
    local force=false
    local batch_size=10
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force) force=true; shift ;;
            --batch-size) batch_size="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    print_info "Starting embedding generation service..."
    
    # Check if embedding service is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required for embedding generation"
        return 1
    fi
    
    # Run embedding service
    python3 "$(dirname "$0")/embedding_service.py"
    
    if [ $? -eq 0 ]; then
        print_success "Embedding generation completed"
        
        # Create vector index if not exists
        print_info "Creating vector index..."
        psql "$DB_CONN" -c "
            DO \$\$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_embedding') THEN
                    CREATE INDEX idx_documents_embedding ON documents 
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                END IF;
            END
            \$\$;
        "
        print_success "Vector index created"
    else
        print_error "Embedding generation failed"
        return 1
    fi
}

# Function for semantic search
action_semantic_search() {
    local query="$1"
    shift
    
    if [ -z "$query" ]; then
        print_error "Search query required"
        return 1
    fi
    
    if ! check_db_connection; then
        return 1
    fi
    
    local limit=10
    local similarity_threshold=0.8
    local hybrid=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --limit) limit="$2"; shift 2 ;;
            --threshold) similarity_threshold="$2"; shift 2 ;;
            --hybrid) hybrid=true; shift ;;
            *) shift ;;
        esac
    done
    
    print_header "Semantic Search Results for: $query"
    
    # Generate embedding for query (simplified - in practice, use embedding service)
    print_info "Generating query embedding..."
    
    # For now, show SQL template that would be used
    local search_query
    if [ "$hybrid" = true ]; then
        search_query="
        WITH semantic_search AS (
            SELECT 
                id, path, title, description, category,
                1 - (embedding <=> query_embedding) AS similarity_score,
                ts_rank(search_vector, plainto_tsquery('english', '$query')) AS text_score
            FROM documents
            WHERE embedding IS NOT NULL
                AND status = 'active'
            ORDER BY similarity_score DESC
            LIMIT $limit
        ),
        text_search AS (
            SELECT 
                id, path, title, description, category,
                ts_rank(search_vector, plainto_tsquery('english', '$query')) AS text_score,
                0.0 AS similarity_score
            FROM documents
            WHERE search_vector @@ plainto_tsquery('english', '$query')
                AND status = 'active'
            LIMIT $limit
        )
        SELECT DISTINCT
            path, title, description, category,
            GREATEST(similarity_score, text_score * 0.5) AS combined_score
        FROM (
            SELECT * FROM semantic_search
            UNION ALL
            SELECT * FROM text_search
        ) combined
        ORDER BY combined_score DESC
        LIMIT $limit"
    else
        search_query="
        SELECT 
            path, title, description, category,
            1 - (embedding <=> %query_embedding%) AS similarity
        FROM documents
        WHERE embedding IS NOT NULL
            AND status = 'active'
            AND 1 - (embedding <=> %query_embedding%) > $similarity_threshold
        ORDER BY similarity DESC
        LIMIT $limit"
    fi
    
    print_info "Search query prepared (embedding generation required)"
    print_info "Use 'generate-embeddings' action first to enable semantic search"
}

# Update show_usage function to include new actions
show_usage() {
    cat << EOF
${BOLD}Claude Document Management System (PostgreSQL + pgvector)${NC}

${CYAN}Usage:${NC}
  manage_document_md [action] [options]

${CYAN}Actions:${NC}
  ${GREEN}init${NC}                     Initialize database schema
  ${GREEN}sync${NC}                     Synchronize files with database
  ${GREEN}search${NC} <query>           Full-text search documents
  ${GREEN}semantic-search${NC} <query>  Semantic similarity search
                             Options: --limit N, --threshold 0.8, --hybrid
  ${GREEN}generate-embeddings${NC}      Generate embeddings for all documents
                             Options: --force, --batch-size N
  ${GREEN}list${NC}                     List documents
  ${GREEN}show${NC} <path|id>           Show document details
  ${GREEN}index${NC}                    Generate doc_index.json
  ${GREEN}mcp${NC} <action>             MCP integration commands

${CYAN}New Semantic Search Features:${NC}
  ${GREEN}semantic-search${NC} "authentication issues"  # Find conceptually similar docs
  ${GREEN}semantic-search${NC} "login problems" --hybrid  # Combine with keyword search
  ${GREEN}generate-embeddings${NC} --batch-size 5        # Generate all embeddings

${CYAN}Examples:${NC}
  # Generate embeddings for semantic search
  manage_document_md generate-embeddings

  # Semantic search
  manage_document_md semantic-search "database connection problems"

  # Hybrid search (semantic + keyword)
  manage_document_md semantic-search "api integration" --hybrid --limit 15
EOF
}

# Update main function to include new actions
main() {
    local action="${1:-help}"
    shift || true
    
    case "$action" in
        init)
            action_init "$@"
            ;;
        sync)
            action_sync "$@"
            ;;
        search)
            action_search "$@"
            ;;
        semantic-search)
            action_semantic_search "$@"
            ;;
        generate-embeddings)
            action_generate_embeddings "$@"
            ;;
        list)
            action_list "$@"
            ;;
        show)
            action_show "$@"
            ;;
        index)
            action_index "$@"
            ;;
        mcp)
            action_mcp_integrate "$@"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac
}
```

**Checklist:**
- [ ] Semantic search action implemented
- [ ] Embedding generation action added
- [ ] Hybrid search capability included
- [ ] Help documentation updated
- [ ] Error handling for new features

### Step 5: Testing & Validation

#### 5.1 Functional Testing Script
```bash
#!/bin/bash
# test_phase2.sh

set -e

print_test() {
    echo "🧪 Testing: $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
}

# Test pgvector installation
print_test "pgvector extension"
if psql "$DB_CONN" -c "SELECT '[1,2,3]'::vector;" > /dev/null 2>&1; then
    print_success "pgvector extension working"
else
    print_error "pgvector extension failed"
    exit 1
fi

# Test embedding generation
print_test "Embedding generation"
./manage_document_md_postgresql generate-embeddings --batch-size 2

# Check if embeddings were generated
count=$(psql -t -A "$DB_CONN" -c "SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;")
if [ "$count" -gt 0 ]; then
    print_success "Embeddings generated ($count documents)"
else
    print_error "No embeddings generated"
    exit 1
fi

# Test semantic search
print_test "Semantic search"
./manage_document_md_postgresql semantic-search "database connection" --limit 3

print_success "Phase 2 testing completed successfully"
```

**Checklist:**
- [ ] Testing script created
- [ ] pgvector functionality tested
- [ ] Embedding generation tested
- [ ] Semantic search tested
- [ ] All tests passing

#### 5.2 Performance Benchmarking
```sql
-- Performance testing queries
-- Test vector search performance
EXPLAIN ANALYZE
SELECT path, title, 1 - (embedding <=> '[0.1,0.2,0.3,...]'::vector) AS similarity
FROM documents
WHERE embedding IS NOT NULL
ORDER BY similarity DESC
LIMIT 10;

-- Test hybrid search performance
EXPLAIN ANALYZE
WITH semantic_results AS (
    SELECT id, path, title, 1 - (embedding <=> '[0.1,0.2,0.3,...]'::vector) AS score
    FROM documents
    WHERE embedding IS NOT NULL
    ORDER BY score DESC
    LIMIT 20
),
text_results AS (
    SELECT id, path, title, ts_rank(search_vector, plainto_tsquery('test')) AS score
    FROM documents
    WHERE search_vector @@ plainto_tsquery('test')
    ORDER BY score DESC
    LIMIT 20
)
SELECT * FROM semantic_results
UNION ALL
SELECT * FROM text_results
ORDER BY score DESC
LIMIT 10;
```

**Checklist:**
- [ ] Performance queries created
- [ ] Query execution times measured
- [ ] Index usage verified
- [ ] Performance baselines established

### Step 6: Documentation & Training

#### 6.1 Update Implementation Guide
```markdown
# Phase 2 Completed Features

## Semantic Search Capabilities
- pgvector extension integration
- OpenAI embedding generation
- Vector similarity search
- Hybrid search (semantic + keyword)

## New Commands
- `generate-embeddings`: Generate embeddings for all documents
- `semantic-search`: Search using semantic similarity
- `semantic-search --hybrid`: Combined semantic and keyword search

## Configuration
- OpenAI API key required
- Embedding model: text-embedding-ada-002
- Vector dimension: 1536
- Index type: IVFFlat with cosine distance

## Performance
- Embedding generation: ~1 second per document
- Semantic search: <200ms for 1000 documents
- Index size: ~6MB per 1000 documents
```

**Checklist:**
- [ ] Documentation updated
- [ ] New features documented
- [ ] Configuration guide updated
- [ ] Performance metrics documented

## Phase 2 Completion Criteria

### Technical Completion
- [ ] pgvector extension installed and configured
- [ ] All existing documents have embeddings
- [ ] Vector indexes created and optimized
- [ ] Semantic search functionality working
- [ ] Hybrid search implemented
- [ ] Performance meets requirements (<200ms search)

### Quality Assurance
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Error handling tested
- [ ] Documentation complete
- [ ] Code review completed

### User Acceptance
- [ ] Semantic search accuracy > 85%
- [ ] User interface intuitive
- [ ] Backward compatibility maintained
- [ ] Help documentation clear

## Rollback Plan

If Phase 2 needs to be rolled back:

```sql
-- Remove vector columns and indexes
ALTER TABLE documents DROP COLUMN IF EXISTS embedding;
ALTER TABLE documents DROP COLUMN IF EXISTS embedding_model;
ALTER TABLE documents DROP COLUMN IF EXISTS embedding_generated_at;
ALTER TABLE documents DROP COLUMN IF EXISTS embedding_status;

-- Drop embedding queue table
DROP TABLE IF EXISTS embedding_queue;

-- Drop vector extension (optional)
-- DROP EXTENSION IF EXISTS vector;
```

```bash
# Revert CLI to Phase 1 version
git checkout phase1 -- .claude/commands/manage_document_md_postgresql
```

**Checklist:**
- [ ] Rollback procedures tested
- [ ] Data backup verified
- [ ] Rollback time < 5 minutes
- [ ] No data loss in rollback

## Next Steps

After Phase 2 completion:
1. Monitor semantic search usage and accuracy
2. Collect user feedback on search relevance
3. Optimize vector index parameters
4. Prepare for Phase 3 advanced search features
5. Plan embedding model updates/improvements

## Troubleshooting Guide

### Common Issues

#### pgvector Installation Issues
```bash
# Check if extension is available
SELECT name, default_version, installed_version 
FROM pg_available_extensions 
WHERE name = 'vector';

# If not available, reinstall
sudo apt remove postgresql-15-pgvector
sudo apt install postgresql-15-pgvector
sudo systemctl restart postgresql
```

#### Embedding Generation Fails
```bash
# Check API key
echo $OPENAI_API_KEY

# Test API connection
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": "test", "model": "text-embedding-ada-002"}' \
     https://api.openai.com/v1/embeddings
```

#### Poor Search Results
```sql
-- Check embedding distribution
SELECT 
    COUNT(*) as total_docs,
    COUNT(embedding) as docs_with_embeddings,
    AVG(array_length(embedding, 1)) as avg_embedding_dim
FROM documents;

-- Analyze vector index
\d+ idx_documents_embedding
```

This completes the detailed Phase 2 implementation guide with comprehensive checklists and troubleshooting information.