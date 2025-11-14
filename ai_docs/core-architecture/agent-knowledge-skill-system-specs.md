# Agent Knowledge & Skill Management System - Technical Specifications

**Version**: 1.0.0
**Date**: 2025-11-13
**Status**: Design Phase
**Scope**: Full System (Phases 1-4)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Database Schema](#3-database-schema)
4. [MCP Tool API Specifications](#4-mcp-tool-api-specifications)
5. [RAG Infrastructure](#5-rag-infrastructure)
6. [Frontend UI Specifications](#6-frontend-ui-specifications)
7. [Private Server Deployment](#7-private-server-deployment)
8. [Integration with Existing System](#8-integration-with-existing-system)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Security & Privacy](#10-security--privacy)

---

## 1. System Overview

### 1.1 Vision

Transform agenthub agents from static entities with fixed instructions into **dynamic, learning agents** that can:
- Access user-specific knowledge bases via RAG (Retrieval-Augmented Generation)
- Load skills on-demand during task execution
- Generate and store new skills when encountering novel domains
- Continuously improve through effectiveness feedback loops

### 1.2 Core Technologies

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **LlamaIndex** | Document ingestion, vector indexing, RAG queries | Open-source, privacy-first, production-ready |
| **sentence-transformers** | Local embedding generation | No API costs, 100% private, fast inference |
| **pgvector** | Vector similarity search in PostgreSQL | Integrated with existing DB, no external dependencies |
| **LangChain** | Agent framework, tool wrappers | Industry standard, extensive ecosystem |
| **Claude Code** | Skill content generation | Subscription-based (no per-request costs) |

### 1.3 Key Features

**For Users:**
- Create custom skills/knowledge in workspace
- Upload documents to private knowledge base
- Query knowledge using natural language
- View agent performance metrics per skill
- Share knowledge across their agents

**For Agents:**
- Receive skill list when called via `call_agent()`
- Search skills semantically during task execution
- Auto-load relevant skills from RAG system
- Request AI to generate missing skills
- Report skill effectiveness for continuous improvement

**For System:**
- Multi-tenant data isolation (per-user vector indexes)
- Horizontal scaling (separate RAG server)
- Simple direct queries (no caching complexity)
- Audit trail (all skill usage logged)

### 1.4 System Boundaries

**In Scope:**
- Agent skill/knowledge CRUD operations
- RAG-powered semantic search
- Frontend UI for skill management
- Integration with existing MCP protocol
- Private server deployment architecture

**Out of Scope (Phase 2+):**
- LoRA fine-tuning (Phase 6)
- LangGraph advanced workflows (Phase 5)
- Cross-user knowledge sharing marketplace
- Mobile app interfaces
- Real-time collaborative editing

---

## 2. Architecture Principles

### 2.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Privacy First** | All data on user's infrastructure, local embeddings, no external API dependencies |
| **DDD Compliance** | Domain entities (Skill, Knowledge), application services, repository pattern |
| **Simplicity** | Direct PostgreSQL queries, lazy loading, batch embeddings, pgvector ivfflat indexes |
| **Extensibility** | Plugin architecture for new embedding models, skill validators, RAG strategies |
| **Observability** | Structured logging, metrics (skill usage, RAG latency, query performance) |

### 2.2 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/TS)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Skill Manager│  │  Knowledge   │  │    Agent     │      │
│  │      UI      │  │   Base UI    │  │  Dashboard   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│             Interface Layer (FastMCP Tools)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │manage_skill  │  │manage_knowledge│ │search_skills │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│           Application Layer (Services/Facades)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SkillService │  │KnowledgeService│ │  RAGService  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              Domain Layer (Entities/Logic)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Skill       │  │  Knowledge   │  │ Embedding    │      │
│  │  Entity      │  │  Entity      │  │  ValueObject │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│         Infrastructure Layer (Persistence/External)          │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ PostgreSQL   │  │  LlamaIndex  │                         │
│  │  (pgvector)  │  │  (RAG Engine)│                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow - Typical Workflow

**Scenario: Agent Needs a Skill**

```
1. User: "Fix the async bug in auth module"
   ↓
2. call_agent("coding-agent")
   → Response includes: {system_prompt, skills: [{title, description}...]}
   ↓
3. Agent analyzes task: "Need async error handling patterns"
   ↓
4. search_skills(query="async error handling Python")
   ↓
5. RAG Service:
   a. Generate embedding for query (sentence-transformers)
   b. Query pgvector with cosine similarity
   c. Retrieve top 3 skills (similarity > 0.75)
   ↓
6. Return: [
     {skill_id, title: "Python Async Exception Patterns", content: "...", score: 0.89},
     ...
   ]
   ↓
7. Agent loads skill content into context
   ↓
8. Agent executes task with enhanced knowledge
   ↓
9. Log skill usage: skill_id, task_id, was_helpful: true
   ↓
10. Update effectiveness_score (running average)
```

---

## 3. Database Schema

### 3.1 New Tables

#### Table: `agent_skills`

**Purpose**: Store reusable skills (code patterns, best practices, procedures)

```sql
CREATE TABLE agent_skills (
    -- Primary identification
    skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(200) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,  -- Full skill content (markdown, code examples)

    -- Classification
    skill_type VARCHAR(50) NOT NULL CHECK (skill_type IN ('system', 'user-created', 'ai-generated')),
    category VARCHAR(100),  -- 'coding', 'debugging', 'testing', 'architecture', etc.
    tags TEXT[],  -- Array for flexible tagging

    -- Versioning
    version VARCHAR(20) DEFAULT '1.0.0',
    parent_skill_id UUID REFERENCES agent_skills(skill_id),  -- For forked/versioned skills

    -- RAG components
    embedding_vector VECTOR(384),  -- sentence-transformers/all-MiniLM-L6-v2

    -- Performance tracking
    is_active BOOLEAN DEFAULT true,
    effectiveness_score FLOAT DEFAULT 0.0,  -- 0-1, updated from agent feedback
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,  -- Tasks completed successfully with this skill

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),  -- 'user', 'ai', 'system'
    metadata JSONB,  -- Flexible field: {prerequisites: [], examples: [], related_skills: []}

    -- Constraints
    CONSTRAINT skill_title_unique_per_user UNIQUE (user_id, title, version)
);

-- Indexes
CREATE INDEX idx_skills_user_category ON agent_skills(user_id, category) WHERE is_active = true;
CREATE INDEX idx_skills_effectiveness ON agent_skills(effectiveness_score DESC) WHERE is_active = true;
CREATE INDEX idx_skills_usage ON agent_skills(usage_count DESC);
CREATE INDEX idx_skills_embedding ON agent_skills USING ivfflat (embedding_vector vector_cosine_ops);
CREATE INDEX idx_skills_tags ON agent_skills USING GIN (tags);
```

**Field Details:**

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `skill_id` | UUID | Unique identifier | `a7f3b2c1-...` |
| `content` | TEXT | Full skill instructions, code examples, best practices | Markdown with code blocks |
| `skill_type` | VARCHAR | Origin of skill | `'user-created'` |
| `category` | VARCHAR | High-level grouping | `'backend-patterns'` |
| `tags` | TEXT[] | Fine-grained search | `{'fastapi', 'async', 'database'}` |
| `embedding_vector` | VECTOR(384) | Semantic search vector | `[0.123, -0.456, ...]` |
| `effectiveness_score` | FLOAT | Agent feedback score (0-1) | `0.87` (87% success rate) |
| `metadata` | JSONB | Extensible data | `{"prerequisites": ["python-basics"], "difficulty": "intermediate"}` |

#### Table: `agent_knowledge`

**Purpose**: User's knowledge base (documents, notes, research, domain expertise)

```sql
CREATE TABLE agent_knowledge (
    -- Primary identification
    knowledge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',  -- 'text', 'markdown', 'code', 'pdf', 'url'

    -- Classification
    category VARCHAR(100),
    source VARCHAR(50) NOT NULL,  -- 'user', 'ai-generated', 'imported', 'web-scraped'
    original_file_path TEXT,  -- If uploaded from file

    -- RAG components
    embedding_vector VECTOR(384),
    chunk_index INTEGER DEFAULT 0,  -- For large documents split into chunks
    parent_knowledge_id UUID REFERENCES agent_knowledge(knowledge_id),  -- Link chunks to parent

    -- Access control
    is_public BOOLEAN DEFAULT false,  -- Future: knowledge marketplace
    access_level VARCHAR(20) DEFAULT 'private' CHECK (access_level IN ('private', 'team', 'public')),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- {summary: "", key_concepts: [], referenced_urls: []}

    -- Constraints
    CONSTRAINT knowledge_title_unique_per_user UNIQUE (user_id, title)
);

-- Indexes
CREATE INDEX idx_knowledge_user ON agent_knowledge(user_id) WHERE access_level = 'private';
CREATE INDEX idx_knowledge_category ON agent_knowledge(user_id, category);
CREATE INDEX idx_knowledge_embedding ON agent_knowledge USING ivfflat (embedding_vector vector_cosine_ops);
CREATE INDEX idx_knowledge_parent ON agent_knowledge(parent_knowledge_id) WHERE parent_knowledge_id IS NOT NULL;
```

**Chunking Strategy for Large Documents:**

```python
# Example: 5000-word document → 5 chunks
parent = Knowledge(title="FastAPI Production Guide", content_type="pdf", ...)
db.add(parent)

for i, chunk_text in enumerate(split_document(content, chunk_size=1000)):
    chunk = Knowledge(
        title=f"{parent.title} (Part {i+1})",
        content=chunk_text,
        chunk_index=i,
        parent_knowledge_id=parent.knowledge_id,
        embedding_vector=embed(chunk_text)
    )
    db.add(chunk)
```

#### Table: `skill_assignments`

**Purpose**: Link skills to specific agents (many-to-many relationship)

```sql
CREATE TABLE skill_assignments (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,  -- References agent_instances.instance_id
    skill_id UUID NOT NULL REFERENCES agent_skills(skill_id) ON DELETE CASCADE,

    -- Assignment metadata
    assigned_by VARCHAR(50) NOT NULL,  -- 'user', 'auto', 'recommendation'
    assignment_reason TEXT,  -- Why this skill was assigned
    priority INTEGER DEFAULT 0,  -- Higher priority skills loaded first (when context limits apply)

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT unique_agent_skill UNIQUE (agent_id, skill_id)
);

-- Indexes
CREATE INDEX idx_assignments_agent ON skill_assignments(agent_id) WHERE is_active = true;
CREATE INDEX idx_assignments_skill ON skill_assignments(skill_id);
CREATE INDEX idx_assignments_priority ON skill_assignments(agent_id, priority DESC);
```

#### Table: `knowledge_access_log`

**Purpose**: Audit trail for knowledge/skill usage (analytics, effectiveness tracking)

```sql
CREATE TABLE knowledge_access_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),

    -- What was accessed
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('skill', 'knowledge')),
    resource_id UUID NOT NULL,  -- skill_id or knowledge_id

    -- Context
    agent_id UUID,
    task_id UUID,  -- References tasks.task_id if accessed during task
    query TEXT,  -- Search query used to find this resource
    similarity_score FLOAT,  -- RAG retrieval score

    -- Outcome
    was_helpful BOOLEAN,  -- Agent reports if resource was useful
    feedback TEXT,  -- Optional agent feedback

    -- Timestamp
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Performance metrics
    retrieval_latency_ms INTEGER  -- How long RAG query took
);

-- Indexes
CREATE INDEX idx_access_log_user ON knowledge_access_log(user_id, accessed_at DESC);
CREATE INDEX idx_access_log_resource ON knowledge_access_log(resource_type, resource_id);
CREATE INDEX idx_access_log_task ON knowledge_access_log(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_access_log_helpful ON knowledge_access_log(was_helpful) WHERE was_helpful IS NOT NULL;
```

### 3.2 Schema Migrations

**Migration Strategy:**

1. **Migration 001**: Create tables (agent_skills, agent_knowledge, skill_assignments, knowledge_access_log)
2. **Migration 002**: Install pgvector extension, add vector columns
3. **Migration 003**: Create indexes (including ivfflat for vector search)
4. **Migration 004**: Add triggers for `updated_at` auto-update
5. **Migration 005**: Seed system skills (Python patterns, Git workflows, etc.)

**Alembic Migration Template:**

```python
# migrations/versions/001_create_skill_knowledge_tables.py
def upgrade():
    # Create tables
    op.execute("""
        CREATE TABLE agent_skills (
            -- See full schema above
        );
    """)

    # Create indexes
    op.create_index('idx_skills_user_category', 'agent_skills', ['user_id', 'category'])

    # Seed system skills
    op.execute("""
        INSERT INTO agent_skills (user_id, title, skill_type, content, category)
        VALUES
            (NULL, 'Python Async Patterns', 'system', '...', 'coding'),
            (NULL, 'Git Best Practices', 'system', '...', 'version-control');
    """)

def downgrade():
    op.drop_table('knowledge_access_log')
    op.drop_table('skill_assignments')
    op.drop_table('agent_knowledge')
    op.drop_table('agent_skills')
```

### 3.3 Data Integrity Constraints

**Business Rules Enforced at DB Level:**

1. **User Isolation**: All queries filtered by `user_id` (row-level security)
2. **Skill Versioning**: Cannot have duplicate (user_id, title, version)
3. **Cascade Deletes**: Deleting user → deletes all their skills/knowledge
4. **Active Skills Only**: Indexes exclude `is_active = false` for performance
5. **Effectiveness Score Bounds**: 0.0 ≤ effectiveness_score ≤ 1.0

**Triggers:**

```sql
-- Auto-update updated_at timestamp
CREATE TRIGGER update_skill_timestamp
BEFORE UPDATE ON agent_skills
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Auto-increment usage_count on access log entry
CREATE TRIGGER increment_skill_usage
AFTER INSERT ON knowledge_access_log
FOR EACH ROW
WHEN (NEW.resource_type = 'skill')
EXECUTE FUNCTION increment_skill_usage_count();
```

---

## 4. MCP Tool API Specifications

### 4.1 Tool: `manage_skill`

**Purpose**: Complete skill lifecycle management (CRUD + assignment)

#### Actions

##### Action: `create`

**Parameters:**

```python
{
    "action": "create",  # REQUIRED
    "user_id": "uuid",   # OPTIONAL (auto from auth context)
    "title": "Python Async Error Handling",  # REQUIRED
    "description": "Patterns for graceful async exception handling",  # OPTIONAL
    "content": "# Async Error Handling\n\n## Pattern 1: Try-Except in Coroutines\n\n```python\nasync def fetch_data():\n    try:\n        result = await api_call()\n    except httpx.TimeoutError:\n        logger.error(\"Timeout\")\n        return default_value\n```",  # REQUIRED
    "skill_type": "user-created",  # OPTIONAL, default: "user-created"
    "category": "backend-patterns",  # OPTIONAL
    "tags": ["python", "async", "error-handling"],  # OPTIONAL (array or comma-separated string)
    "version": "1.0.0",  # OPTIONAL, default: "1.0.0"
    "metadata": {  # OPTIONAL
        "prerequisites": ["python-basics", "async-fundamentals"],
        "difficulty": "intermediate",
        "estimated_reading_time_minutes": 10
    }
}
```

**Response:**

```json
{
    "success": true,
    "skill": {
        "skill_id": "a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
        "title": "Python Async Error Handling",
        "description": "Patterns for graceful async exception handling",
        "skill_type": "user-created",
        "category": "backend-patterns",
        "tags": ["python", "async", "error-handling"],
        "version": "1.0.0",
        "effectiveness_score": 0.0,
        "usage_count": 0,
        "is_active": true,
        "created_at": "2025-11-13T10:30:00Z",
        "embedding_generated": true
    },
    "message": "Skill created successfully. Embedding generated with model: all-MiniLM-L6-v2"
}
```

**Business Logic:**

1. Validate required fields (title, content)
2. Check for duplicate (user_id, title, version) → reject if exists
3. Generate embedding from `title + description + content` using sentence-transformers
4. Insert into `agent_skills` table
5. Publish event: `SkillCreatedEvent` (for cache invalidation, notifications)
6. Return skill object with generated IDs

**Error Responses:**

```json
// Duplicate skill
{
    "success": false,
    "error": "DUPLICATE_SKILL",
    "message": "Skill with title 'Python Async Error Handling' and version '1.0.0' already exists",
    "existing_skill_id": "xyz-123"
}

// Invalid content format
{
    "success": false,
    "error": "INVALID_CONTENT",
    "message": "Content must be valid markdown or plain text"
}
```

##### Action: `update`

**Parameters:**

```python
{
    "action": "update",
    "skill_id": "uuid",  # REQUIRED
    "title": "Updated Title",  # OPTIONAL
    "content": "Updated content...",  # OPTIONAL
    "description": "Updated description",  # OPTIONAL
    "category": "new-category",  # OPTIONAL
    "tags": ["new", "tags"],  # OPTIONAL
    "is_active": false,  # OPTIONAL (soft delete)
    "metadata": {}  # OPTIONAL (merged with existing)
}
```

**Response:**

```json
{
    "success": true,
    "skill": { /* updated skill object */ },
    "embedding_updated": true,  // If content/title/description changed
    "message": "Skill updated successfully. Embedding regenerated."
}
```

**Business Logic:**

1. Verify skill exists and user owns it
2. If content/title/description changed → regenerate embedding
3. Update `updated_at` timestamp (trigger handles this)
4. Invalidate Redis cache for this skill
5. Publish `SkillUpdatedEvent`

##### Action: `get`

**Parameters:**

```python
{
    "action": "get",
    "skill_id": "uuid",  # REQUIRED
    "include_content": true  # OPTIONAL, default: true (set false for list views)
}
```

**Response:**

```json
{
    "success": true,
    "skill": {
        "skill_id": "...",
        "title": "...",
        "description": "...",
        "content": "...",  // Omitted if include_content=false
        "category": "...",
        "tags": [...],
        "effectiveness_score": 0.87,
        "usage_count": 42,
        "success_count": 36,
        "version": "1.2.0",
        "created_at": "...",
        "updated_at": "...",
        "metadata": {...}
    }
}
```

##### Action: `list`

**Parameters:**

```python
{
    "action": "list",
    "user_id": "uuid",  # OPTIONAL (from auth)
    "category": "backend-patterns",  # OPTIONAL filter
    "tags": ["python", "async"],  # OPTIONAL filter (AND logic)
    "skill_type": "user-created",  # OPTIONAL filter
    "is_active": true,  # OPTIONAL filter, default: true
    "sort_by": "effectiveness_score",  # OPTIONAL: effectiveness_score, usage_count, created_at, title
    "sort_order": "desc",  # OPTIONAL: asc, desc
    "limit": 50,  # OPTIONAL, default: 50, max: 100
    "offset": 0  # OPTIONAL for pagination
}
```

**Response:**

```json
{
    "success": true,
    "skills": [
        {
            "skill_id": "...",
            "title": "...",
            "description": "...",
            // content omitted for performance
            "category": "...",
            "effectiveness_score": 0.92,
            "usage_count": 156
        },
        // ... more skills
    ],
    "total_count": 248,
    "limit": 50,
    "offset": 0
}
```

##### Action: `delete`

**Parameters:**

```python
{
    "action": "delete",
    "skill_id": "uuid",  # REQUIRED
    "hard_delete": false  # OPTIONAL, default: false (soft delete: is_active=false)
}
```

**Response:**

```json
{
    "success": true,
    "message": "Skill soft-deleted successfully. Set is_active=false.",
    "deleted_skill_id": "..."
}
```

**Business Logic:**

1. Soft delete (default): Set `is_active = false`
2. Hard delete: Remove from DB (CASCADE removes assignments)
3. Remove from Redis cache
4. Remove embedding from vector index
5. Publish `SkillDeletedEvent`

##### Action: `assign_to_agent`

**Purpose**: Link skill to specific agent instance

**Parameters:**

```python
{
    "action": "assign_to_agent",
    "skill_id": "uuid",  # REQUIRED
    "agent_id": "uuid",  # REQUIRED (agent instance ID)
    "assigned_by": "user",  # OPTIONAL: user, auto, recommendation
    "assignment_reason": "Agent frequently works with async patterns",  # OPTIONAL
    "priority": 10  # OPTIONAL, default: 0 (higher = loaded first)
}
```

**Response:**

```json
{
    "success": true,
    "assignment": {
        "assignment_id": "...",
        "skill_id": "...",
        "agent_id": "...",
        "assigned_by": "user",
        "priority": 10,
        "created_at": "..."
    },
    "message": "Skill assigned to agent successfully"
}
```

##### Action: `unassign_from_agent`

**Parameters:**

```python
{
    "action": "unassign_from_agent",
    "assignment_id": "uuid"  # REQUIRED
    # OR
    "skill_id": "uuid",  # REQUIRED if assignment_id not provided
    "agent_id": "uuid"   # REQUIRED if assignment_id not provided
}
```

##### Action: `search` (Semantic Search)

**Purpose**: Find skills using natural language query

**Parameters:**

```python
{
    "action": "search",
    "query": "how to handle database connection errors in async Python",  # REQUIRED
    "user_id": "uuid",  # OPTIONAL (from auth)
    "category": "backend-patterns",  # OPTIONAL filter
    "min_similarity": 0.7,  # OPTIONAL, default: 0.7 (cosine similarity threshold)
    "limit": 10,  # OPTIONAL, default: 10
    "include_system_skills": true  # OPTIONAL, default: true
}
```

**Response:**

```json
{
    "success": true,
    "results": [
        {
            "skill_id": "...",
            "title": "Python Async Error Handling",
            "description": "...",
            "content": "...",
            "similarity_score": 0.89,  // Cosine similarity
            "category": "backend-patterns",
            "effectiveness_score": 0.87,
            "usage_count": 42
        },
        // ... more results, sorted by similarity_score DESC
    ],
    "query_embedding_time_ms": 12,
    "search_time_ms": 34,
    "total_results": 7
}
```

**Business Logic:**

1. Generate query embedding (sentence-transformers)
2. Check Redis cache (key: `search:{hash(query)}:{filters}`, TTL: 1h)
3. If miss: Query pgvector with cosine similarity
4. Filter by user_id, category, min_similarity
5. Include system skills (user_id = NULL) if requested
6. Sort by similarity_score DESC
7. Cache results
8. Return top N results

---

### 4.2 Tool: `manage_knowledge`

**Purpose**: User's knowledge base management (documents, notes, research)

#### Actions

##### Action: `create`

**Parameters:**

```python
{
    "action": "create",
    "title": "FastAPI Production Deployment Guide",  # REQUIRED
    "content": "# FastAPI Production Deployment\n\n## 1. Use Gunicorn with Uvicorn workers...",  # REQUIRED
    "content_type": "markdown",  # OPTIONAL: text, markdown, code, pdf, url
    "category": "deployment",  # OPTIONAL
    "source": "user",  # OPTIONAL: user, ai-generated, imported, web-scraped
    "original_file_path": "/uploads/fastapi-guide.pdf",  # OPTIONAL
    "chunk_size": 1000,  # OPTIONAL, default: 1000 (words per chunk for large docs)
    "metadata": {
        "author": "John Doe",
        "url": "https://example.com/guide",
        "summary": "Comprehensive guide to deploying FastAPI in production"
    }
}
```

**Response:**

```json
{
    "success": true,
    "knowledge": {
        "knowledge_id": "...",
        "title": "FastAPI Production Deployment Guide",
        "content_type": "markdown",
        "category": "deployment",
        "chunks_created": 5,  // If document was chunked
        "chunk_ids": ["...", "...", ...],  // Array of chunk knowledge_ids
        "created_at": "...",
        "embeddings_generated": true
    },
    "message": "Knowledge created successfully. Document split into 5 chunks for optimal retrieval."
}
```

**Business Logic:**

1. Validate content (check for malicious code, size limits)
2. If content length > chunk_size:
   a. Split into semantic chunks (preserve paragraphs)
   b. Create parent knowledge entry
   c. Create child chunks with `parent_knowledge_id`
3. Generate embeddings for each chunk
4. Insert into `agent_knowledge`
5. Publish `KnowledgeCreatedEvent`

##### Action: `upload_file`

**Purpose**: Upload and process document files (PDF, TXT, MD, DOCX)

**Parameters:**

```python
{
    "action": "upload_file",
    "file": <binary>,  # REQUIRED (multipart/form-data)
    "title": "Custom Title",  # OPTIONAL (defaults to filename)
    "category": "research",  # OPTIONAL
    "extract_metadata": true  # OPTIONAL, default: true (extract author, dates, etc.)
}
```

**Response:**

```json
{
    "success": true,
    "knowledge": {
        "knowledge_id": "...",
        "title": "research-paper.pdf",
        "content_type": "pdf",
        "file_size_bytes": 524288,
        "chunks_created": 12,
        "extracted_metadata": {
            "author": "Jane Smith",
            "creation_date": "2024-06-15",
            "page_count": 23
        }
    },
    "message": "File uploaded and processed. 12 chunks created."
}
```

**Business Logic:**

1. Validate file type (allowed: pdf, txt, md, docx, html)
2. Extract text content:
   - PDF: PyPDF2 or pdfplumber
   - DOCX: python-docx
   - HTML: BeautifulSoup
3. Extract metadata (author, dates, keywords)
4. Chunk large documents
5. Generate embeddings
6. Store original file path for reference

##### Action: `search` (RAG Query)

**Parameters:**

```python
{
    "action": "search",
    "query": "how to configure Gunicorn workers for FastAPI",  # REQUIRED
    "category": "deployment",  # OPTIONAL filter
    "min_similarity": 0.75,  # OPTIONAL
    "limit": 5,  # OPTIONAL, default: 5
    "return_chunks": true  # OPTIONAL: return individual chunks (true) or parent docs (false)
}
```

**Response:**

```json
{
    "success": true,
    "results": [
        {
            "knowledge_id": "...",
            "parent_knowledge_id": "...",  // If this is a chunk
            "title": "FastAPI Production Deployment Guide (Part 3)",
            "content": "## Gunicorn Configuration\n\nUse Uvicorn workers with Gunicorn:\n\n```bash\ngunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app\n```",
            "similarity_score": 0.91,
            "category": "deployment",
            "chunk_index": 2  // If chunked
        },
        // ... more results
    ],
    "total_results": 5,
    "search_time_ms": 28
}
```

##### Action: `list`, `get`, `update`, `delete`

Similar to `manage_skill` (see section 4.1)

---

### 4.3 Tool: `search_skills` (Simplified Semantic Search)

**Purpose**: Lightweight skill search (alias for `manage_skill action=search`)

**Parameters:**

```python
{
    "query": "async error handling",  # REQUIRED
    "limit": 5,  # OPTIONAL
    "category": "backend-patterns"  # OPTIONAL
}
```

**Response:**

```json
{
    "success": true,
    "skills": [
        {
            "skill_id": "...",
            "title": "Python Async Error Handling",
            "description": "...",
            "similarity_score": 0.89
        },
        // ... more skills
    ]
}
```

---

### 4.4 Tool: `call_agent` (Enhanced)

**Current Behavior:**

```json
{
    "name": "coding-agent",
    "system_prompt": "You are a coding agent...",
    "tools": ["Read", "Write", "Edit", "Bash"],
    "capabilities": {...}
}
```

**New Behavior (with Skills):**

```json
{
    "name": "coding-agent",
    "system_prompt": "You are a coding agent...",
    "tools": ["Read", "Write", "Edit", "Bash"],
    "capabilities": {...},
    "skills": [  // NEW
        {
            "skill_id": "a7f3b2c1-...",
            "title": "Python Async Patterns",
            "description": "Best practices for async/await in Python",
            "category": "coding",
            "effectiveness_score": 0.92,
            "load_priority": 10
        },
        {
            "skill_id": "b8g4c3d2-...",
            "title": "FastAPI Error Handling",
            "description": "Exception handling patterns for FastAPI",
            "category": "backend-patterns",
            "effectiveness_score": 0.87,
            "load_priority": 8
        }
        // ... more assigned skills
    ],
    "skill_categories": ["coding", "backend-patterns", "testing"],  // Available categories
    "can_request_skills": true  // Agent can call search_skills during execution
}
```

**Backend Logic:**

```python
def call_agent(name: str, user_id: str) -> AgentResponse:
    # Existing logic
    agent = get_agent_by_slug(name)
    system_prompt = agent.system_prompt
    tools = agent.tools

    # NEW: Fetch assigned skills
    skills = db.query(AgentSkill).join(SkillAssignment).filter(
        SkillAssignment.agent_id == agent.instance_id,
        SkillAssignment.is_active == True,
        AgentSkill.is_active == True
    ).order_by(SkillAssignment.priority.desc()).limit(20).all()

    # Format skill summaries (not full content for performance)
    skill_summaries = [
        {
            "skill_id": s.skill_id,
            "title": s.title,
            "description": s.description,
            "category": s.category,
            "effectiveness_score": s.effectiveness_score,
            "load_priority": assignment.priority
        }
        for s, assignment in skills
    ]

    return {
        "name": agent.name,
        "system_prompt": system_prompt,
        "tools": tools,
        "capabilities": agent.capabilities,
        "skills": skill_summaries,  # NEW
        "skill_categories": list(set([s.category for s in skills])),  # NEW
        "can_request_skills": True  # NEW
    }
```

**Agent Workflow Integration:**

```python
# Agent receives call_agent response
agent_config = call_agent("coding-agent")

# Agent sees assigned skills
print(f"I have {len(agent_config['skills'])} skills available")

# During task execution, agent needs more info
if task_requires("async database patterns"):
    # Agent calls search_skills
    relevant_skills = search_skills(query="async database patterns", limit=3)

    # Agent loads full content of most relevant skill
    skill_content = manage_skill(action="get", skill_id=relevant_skills[0]["skill_id"])

    # Agent uses skill content in system prompt
    enhanced_prompt = f"{system_prompt}\n\nRelevant Skill:\n{skill_content['content']}"

    # Agent executes task with enhanced knowledge
```

---

### 4.5 API Authentication & Authorization

**Authentication:**
- All MCP tools require valid JWT token (existing auth system)
- user_id extracted from token claims

**Authorization Rules:**

| Action | Rule |
|--------|------|
| Create skill/knowledge | User can create for themselves |
| Read skill/knowledge | User can read their own + system skills (user_id=NULL) |
| Update skill/knowledge | User can only update their own |
| Delete skill/knowledge | User can only delete their own |
| Assign skill to agent | User can assign any skill (theirs + system) to their agents |
| Search | User searches across their knowledge + system knowledge |

**Row-Level Security (PostgreSQL):**

```sql
-- Enable RLS on agent_skills
ALTER TABLE agent_skills ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own skills + system skills
CREATE POLICY user_skills_policy ON agent_skills
FOR SELECT
USING (
    user_id = current_setting('app.current_user_id')::UUID
    OR user_id IS NULL  -- System skills
);

-- Policy: Users can only modify their own skills
CREATE POLICY user_skills_modify_policy ON agent_skills
FOR ALL
USING (user_id = current_setting('app.current_user_id')::UUID);
```

**Setting user_id in queries:**

```python
# Set user_id for RLS before each query
db.execute(text("SET app.current_user_id = :user_id"), {"user_id": str(user_id)})

# Now all queries automatically filtered by RLS
skills = db.query(AgentSkill).all()  # Only returns user's skills + system skills
```

---

## 5. RAG Infrastructure

### 5.1 Architecture Overview

**Components:**

```
┌─────────────────────────────────────────────────────┐
│            RAG Service (Python Module)               │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Embedding   │  │  LlamaIndex  │  │  Cache    │ │
│  │  Generator   │  │  QueryEngine │  │  Manager  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│         │                  │                │        │
│         ▼                  ▼                ▼        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ sentence-    │  │  PostgreSQL  │  │   Redis   │ │
│  │ transformers │  │  (pgvector)  │  │           │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### 5.2 Embedding Generation

**Model Choice: sentence-transformers/all-MiniLM-L6-v2**

**Why:**
- Fully local (no API costs)
- Fast inference (~50ms per embedding on CPU)
- Small size (384 dimensions)
- Good quality (performs well on semantic similarity tasks)
- Privacy-first (no data sent externally)

**Alternative: Claude Code for Embeddings (Future)**
- If Anthropic offers embedding API in subscription plans
- Higher quality than sentence-transformers
- Still respects "no pay-per-use" constraint

**Implementation:**

```python
# agenthub_main/src/fastmcp/rag/embedding_service.py

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np

class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # all-MiniLM-L6-v2 output dimension

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batched for efficiency)"""
        embeddings = self.model.encode(texts, convert_to_numpy=True, batch_size=32)
        return embeddings.tolist()

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

**Optimization: Batch Processing**

```python
# When creating multiple skills at once (e.g., seeding system skills)
texts = [f"{skill.title} {skill.description} {skill.content}" for skill in skills]
embeddings = embedding_service.generate_embeddings_batch(texts)

for skill, embedding in zip(skills, embeddings):
    skill.embedding_vector = embedding
    db.add(skill)

db.commit()
```

### 5.3 LlamaIndex Integration

**Setup:**

```python
# agenthub_main/src/fastmcp/rag/llamaindex_service.py

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SimpleNodeParser

class LlamaIndexService:
    def __init__(self, db_connection_string: str):
        # Use our existing PostgreSQL with pgvector
        self.vector_store = PGVectorStore.from_params(
            database=db_name,
            host=db_host,
            password=db_password,
            port=db_port,
            user=db_user,
            table_name="agent_skills",  # Or "agent_knowledge"
            embed_dim=384,
        )

        # Use our embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Storage context
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        # Index
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )

    def query(self, query_text: str, top_k: int = 5, filters: dict = None) -> List[dict]:
        """Query the vector store with semantic search"""
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            filters=filters  # e.g., {"category": "backend-patterns"}
        )

        response = query_engine.query(query_text)

        # Format response
        results = []
        for node in response.source_nodes:
            results.append({
                "skill_id": node.node.metadata.get("skill_id"),
                "title": node.node.metadata.get("title"),
                "content": node.node.text,
                "similarity_score": node.score,
                "metadata": node.node.metadata
            })

        return results

    def add_documents(self, documents: List[dict]):
        """Add new documents to the index"""
        from llama_index.core import Document

        docs = [
            Document(
                text=doc["content"],
                metadata={
                    "skill_id": doc["skill_id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "user_id": doc["user_id"]
                }
            )
            for doc in documents
        ]

        self.index.insert_nodes(docs)
```

**Alternative: Custom pgvector Query (Simpler)**

For more control, query pgvector directly without LlamaIndex:

```python
# agenthub_main/src/fastmcp/rag/vector_search.py

from sqlalchemy import text
from typing import List, Dict

class VectorSearchService:
    def __init__(self, db_session):
        self.db = db_session
        self.embedding_service = EmbeddingService()

    def search_skills(
        self,
        query: str,
        user_id: str,
        category: str = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> List[Dict]:
        """Search skills using pgvector cosine similarity"""

        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)

        # Build SQL query
        sql = text("""
            SELECT
                skill_id,
                title,
                description,
                content,
                category,
                effectiveness_score,
                usage_count,
                1 - (embedding_vector <=> :query_embedding) AS similarity_score
            FROM agent_skills
            WHERE
                (user_id = :user_id OR user_id IS NULL)  -- User's skills + system skills
                AND is_active = true
                AND (:category IS NULL OR category = :category)
                AND (1 - (embedding_vector <=> :query_embedding)) >= :min_similarity
            ORDER BY similarity_score DESC
            LIMIT :limit
        """)

        results = self.db.execute(sql, {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "category": category,
            "min_similarity": min_similarity,
            "limit": limit
        }).fetchall()

        return [
            {
                "skill_id": row.skill_id,
                "title": row.title,
                "description": row.description,
                "content": row.content,
                "category": row.category,
                "similarity_score": float(row.similarity_score),
                "effectiveness_score": float(row.effectiveness_score),
                "usage_count": row.usage_count
            }
            for row in results
        ]
```

**Performance Comparison:**

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **LlamaIndex** | Rich features (chunking, metadata filters, query engines) | Adds complexity, learning curve | Use if need advanced features (hybrid search, reranking) |
| **Direct pgvector** | Simple, full control, performant | More manual work (chunking, metadata) | Use for MVP (simpler, faster) |

**Decision: Start with Direct pgvector for MVP**, migrate to LlamaIndex if need advanced features.

### 5.4 Performance Strategy (MVP: Keep It Simple)

**No Caching Configuration for MVP:**

For the initial release, we use **default PostgreSQL settings** with no custom caching:

**Why No Cache Tuning:**
1. **Prove the concept first**: Measure actual performance before optimizing
2. **Simpler deployment**: No configuration parameters to tune
3. **Easier debugging**: No cache-related issues to troubleshoot
4. **Clear baseline**: Know actual query performance without optimizations
5. **Add later if needed**: Based on real metrics, not guesses

**What PostgreSQL Provides by Default:**
- Basic shared buffers (128MB default)
- OS page cache (automatic)
- Query plan caching (automatic for prepared statements)

**Performance Optimization (Post-MVP):**

If measurements show performance issues, consider in this order:
1. **First**: Verify pgvector indexes are built correctly
2. **Second**: Increase PostgreSQL shared_buffers (256MB-1GB)
3. **Third**: Add application-level caching (Redis) only if needed
4. **Fourth**: Consider GPU for embeddings (10x faster)

**Decision Rule:**
```
If average query time > 500ms → Investigate
If 95th percentile > 1000ms → Optimize
Otherwise → Leave it simple
```

### 5.5 MVP Performance Expectations

**Simple Strategies (MVP):**

1. **Lazy Loading**
   - Only load skill *content* when explicitly requested
   - Default: Return skill metadata (title, description, score)

2. **Batch Embedding Generation**
   - Process multiple skills in one batch (32 at a time)
   - Reduces overhead from model loading

3. **pgvector Index** (Basic)
   - Use ivfflat index with default parameters
   - No tuning required for MVP (<10K skills)

```sql
-- Create basic index (no tuning)
CREATE INDEX idx_skills_embedding_ivfflat
ON agent_skills
USING ivfflat (embedding_vector vector_cosine_ops);
```

4. **Query Result Limiting**
   - Default limit: 10 results (enough for most use cases)
   - Max limit: 100 (prevent massive queries)

**Realistic Performance Expectations (MVP):**

| Operation | Expected Latency | Notes |
|-----------|------------------|-------|
| Generate embedding (1 text) | 50-100ms | CPU inference, no optimization |
| Search skills (RAG query) | 150-300ms | End-to-end, no caching |
| Get skill content | 50-100ms | Direct PostgreSQL query |
| Batch embed (32 texts) | <500ms | Amortized ~15ms per text |

**MVP Philosophy:**
- **Acceptable**: Queries under 500ms for user-facing operations
- **Good enough**: Most operations complete in 200-300ms
- **Optimize later**: Only if real users complain about speed
- **Measure first**: Collect metrics before adding complexity

---

## 6. Frontend UI Specifications

### 6.1 New Pages/Components

#### Page: Skill Manager (`/skills`)

**Layout:**

```
┌────────────────────────────────────────────────┐
│  🎯 My Skills                         [+ New]   │
├────────────────────────────────────────────────┤
│  [Search skills...]  [Filter ▼]  [Sort ▼]     │
├────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │ Python Async Patterns       ⭐ 0.92      │  │
│  │ backend-patterns  •  Used 42 times       │  │
│  │ [View] [Edit] [Assign to Agent] [Delete]│  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ FastAPI Error Handling      ⭐ 0.87      │  │
│  │ backend-patterns  •  Used 28 times       │  │
│  │ [View] [Edit] [Assign to Agent] [Delete]│  │
│  └──────────────────────────────────────────┘  │
│  ...                                            │
└────────────────────────────────────────────────┘
```

**Components:**

1. **SkillCard** (`components/skills/SkillCard.tsx`)
   - Display: title, category, effectiveness score, usage count
   - Actions: View, Edit, Delete, Assign to Agent
   - Visual: Star rating for effectiveness (5 stars = 1.0)

2. **SkillCreateModal** (`components/skills/SkillCreateModal.tsx`)
   - Form fields: title, description, content (markdown editor), category, tags
   - Markdown preview
   - Validation: required fields, duplicate title check

3. **SkillDetailModal** (`components/skills/SkillDetailModal.tsx`)
   - Full skill content display (markdown rendered)
   - Metadata: category, tags, version, created_at, usage stats
   - Actions: Edit, Delete, Assign to Agents

4. **SkillSearchBar** (`components/skills/SkillSearchBar.tsx`)
   - Real-time search (debounced)
   - Filters: category, skill_type, effectiveness_score range
   - Sort: by effectiveness, usage_count, created_at, alphabetical

**State Management:**

```typescript
// hooks/useSkills.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export const useSkills = (filters?: SkillFilters) => {
  return useQuery({
    queryKey: ['skills', filters],
    queryFn: () => api.manageSkill({ action: 'list', ...filters })
  });
};

export const useCreateSkill = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skillData: CreateSkillParams) =>
      api.manageSkill({ action: 'create', ...skillData }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      toast.success('Skill created successfully!');
    }
  });
};

export const useSearchSkills = (query: string) => {
  return useQuery({
    queryKey: ['skills', 'search', query],
    queryFn: () => api.searchSkills({ query }),
    enabled: query.length > 2,
    staleTime: 60000 // Cache for 1 minute
  });
};
```

#### Page: Knowledge Base (`/knowledge`)

**Layout:**

```
┌────────────────────────────────────────────────┐
│  📚 Knowledge Base                 [+ Upload]   │
├────────────────────────────────────────────────┤
│  [Search knowledge...]  [Category ▼]           │
├────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │ 📄 FastAPI Production Guide              │  │
│  │ deployment • 5 chunks • PDF              │  │
│  │ [View] [Query] [Edit] [Delete]           │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ 📝 Python Async Notes                    │  │
│  │ coding • 1 chunk • User-created          │  │
│  │ [View] [Query] [Edit] [Delete]           │  │
│  └──────────────────────────────────────────┘  │
│  ...                                            │
└────────────────────────────────────────────────┘
```

**Components:**

1. **KnowledgeCard** (`components/knowledge/KnowledgeCard.tsx`)
   - Display: title, category, source, chunk_count, content_type icon
   - Actions: View, Query (RAG search within doc), Edit, Delete

2. **KnowledgeUploadModal** (`components/knowledge/KnowledgeUploadModal.tsx`)
   - File upload (drag-and-drop)
   - Supported formats: PDF, TXT, MD, DOCX
   - Options: custom title, category, extract_metadata
   - Progress bar during upload/processing

3. **KnowledgeSearchInterface** (`components/knowledge/KnowledgeSearchInterface.tsx`)
   - Natural language query input
   - Results: relevant chunks with similarity scores
   - Highlight matching text
   - "Load Full Document" action

#### Page: Agent Dashboard (`/agents/:agentId`)

**New Section: Assigned Skills**

```
┌────────────────────────────────────────────────┐
│  🤖 coding-agent Dashboard                     │
├────────────────────────────────────────────────┤
│  ...existing dashboard content...              │
├────────────────────────────────────────────────┤
│  📚 Assigned Skills (8)              [+ Assign]│
├────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │ Python Async Patterns            ⭐ 0.92  │  │
│  │ Priority: High • Last used: 2 hours ago   │  │
│  │ [View Skill] [Change Priority] [Unassign] │  │
│  └──────────────────────────────────────────┘  │
│  ...                                            │
├────────────────────────────────────────────────┤
│  📊 Skill Usage Analytics                      │
│  • Most used skill: Python Async Patterns (12x)│
│  • Highest effectiveness: FastAPI Patterns     │
│  • Skill load time avg: 23ms                   │
└────────────────────────────────────────────────┘
```

**Components:**

1. **AgentSkillsTab** (`components/agents/AgentSkillsTab.tsx`)
   - List of assigned skills with metadata
   - Assign new skills (modal with search)
   - Adjust priority (drag-and-drop reordering)
   - Unassign skills

2. **SkillUsageChart** (`components/agents/SkillUsageChart.tsx`)
   - Chart.js bar chart: skill usage frequency
   - Pie chart: skill categories distribution

### 6.2 API Integration

**API Service:**

```typescript
// services/api/skillsApi.ts

import { apiClient } from './client';

export const skillsApi = {
  // Skill management
  createSkill: (data: CreateSkillParams) =>
    apiClient.post('/mcp/manage_skill', { action: 'create', ...data }),

  updateSkill: (skillId: string, data: Partial<CreateSkillParams>) =>
    apiClient.post('/mcp/manage_skill', { action: 'update', skill_id: skillId, ...data }),

  deleteSkill: (skillId: string, hardDelete = false) =>
    apiClient.post('/mcp/manage_skill', { action: 'delete', skill_id: skillId, hard_delete: hardDelete }),

  getSkill: (skillId: string, includeContent = true) =>
    apiClient.post('/mcp/manage_skill', { action: 'get', skill_id: skillId, include_content: includeContent }),

  listSkills: (filters?: SkillFilters) =>
    apiClient.post('/mcp/manage_skill', { action: 'list', ...filters }),

  searchSkills: (query: string, filters?: SearchFilters) =>
    apiClient.post('/mcp/manage_skill', { action: 'search', query, ...filters }),

  // Skill assignment
  assignSkillToAgent: (skillId: string, agentId: string, priority?: number) =>
    apiClient.post('/mcp/manage_skill', {
      action: 'assign_to_agent',
      skill_id: skillId,
      agent_id: agentId,
      priority,
      assigned_by: 'user'
    }),

  unassignSkillFromAgent: (assignmentId: string) =>
    apiClient.post('/mcp/manage_skill', {
      action: 'unassign_from_agent',
      assignment_id: assignmentId
    }),
};

export const knowledgeApi = {
  // Knowledge management
  createKnowledge: (data: CreateKnowledgeParams) =>
    apiClient.post('/mcp/manage_knowledge', { action: 'create', ...data }),

  uploadFile: (file: File, metadata?: { title?: string; category?: string }) =>
    apiClient.postFormData('/mcp/manage_knowledge', {
      action: 'upload_file',
      file,
      ...metadata
    }),

  searchKnowledge: (query: string, filters?: SearchFilters) =>
    apiClient.post('/mcp/manage_knowledge', { action: 'search', query, ...filters }),

  listKnowledge: (filters?: KnowledgeFilters) =>
    apiClient.post('/mcp/manage_knowledge', { action: 'list', ...filters }),

  deleteKnowledge: (knowledgeId: string) =>
    apiClient.post('/mcp/manage_knowledge', { action: 'delete', knowledge_id: knowledgeId }),
};
```

### 6.3 UI/UX Guidelines

**Design Principles:**

1. **Consistency**: Use existing agenthub design system (shadcn/ui components)
2. **Performance**: Lazy load components, virtualize long lists
3. **Feedback**: Loading states, success/error toasts, optimistic updates
4. **Accessibility**: ARIA labels, keyboard navigation, screen reader support

**Reusable Components:**

- `MarkdownEditor`: Rich markdown editor with preview (use `react-markdown` + `react-simplemde-editor`)
- `TagInput`: Chip input for tags (use `react-tag-input`)
- `EffectivenessIndicator`: Star rating + percentage display
- `SimilarityBadge`: Color-coded badge for similarity scores (>0.9 green, 0.7-0.9 yellow, <0.7 red)

---

## 7. Private Server Deployment

### 7.1 Separate Server Architecture

**Deployment Option: Dedicated RAG Server**

```
┌─────────────────────────────────────────────────┐
│         User's Private Infrastructure           │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Main agenthub Server (Existing)         │  │
│  │  • FastMCP API                           │  │
│  │  • WebSocket                             │  │
│  │  • Frontend serving                      │  │
│  │  Port: 8000                              │  │
│  └────────────┬─────────────────────────────┘  │
│               │ HTTP calls                      │
│               ▼                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  RAG Server (New)                        │  │
│  │  • Embedding service                     │  │
│  │  • Vector search                         │  │
│  │  • Redis cache                           │  │
│  │  Port: 8001                              │  │
│  └────────────┬─────────────────────────────┘  │
│               │                                 │
│               ▼                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  PostgreSQL (Shared)                     │  │
│  │  • pgvector extension                    │  │
│  │  • skill/knowledge tables                │  │
│  │  Port: 5432                              │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Why Separate Server?**
- **Isolation**: RAG workload doesn't impact main API
- **Scalability**: Scale embedding/search independently
- **GPU Support**: RAG server can have GPU for faster embeddings (optional)
- **Simplified Architecture**: Single database, no cache complexity

### 7.2 Docker Compose Configuration

**File: `docker-compose.rag-server.yml`**

```yaml
version: '3.8'

services:
  # RAG API Server
  rag-api:
    build:
      context: ./agenthub_rag_server
      dockerfile: Dockerfile
    container_name: agenthub-rag-api
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://agenthub_user:${DB_PASSWORD}@postgres:5432/agenthub
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      - MODEL_CACHE_DIR=/models
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/models  # Cache downloaded models
      - ./logs/rag:/logs
    networks:
      - agenthub-network
    depends_on:
      - postgres
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 3G
        reservations:
          cpus: '1.0'
          memory: 1.5G

  # PostgreSQL (shared with main system)
  postgres:
    image: pgvector/pgvector:pg15
    container_name: agenthub-postgres
    environment:
      POSTGRES_USER: agenthub_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: agenthub
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init_pgvector.sql:/docker-entrypoint-initdb.d/01_init_pgvector.sql
    networks:
      - agenthub-network
    restart: unless-stopped

networks:
  agenthub-network:
    driver: bridge

volumes:
  postgres-data:
```

**File: `scripts/init_pgvector.sql`**

```sql
-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 7.3 RAG Server Implementation

**File Structure:**

```
agenthub_rag_server/
├── Dockerfile
├── requirements.txt
├── main.py  # FastAPI app
├── services/
│   ├── embedding_service.py
│   └── vector_search_service.py
├── models/  # Downloaded sentence-transformers models
└── config.py
```

**File: `agenthub_rag_server/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download embedding model on build (cache for faster startup)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

**File: `agenthub_rag_server/requirements.txt`**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pgvector==0.2.4
sentence-transformers==2.3.1
torch==2.1.2
numpy==1.26.3
pydantic==2.5.3
python-multipart==0.0.6
```

**File: `agenthub_rag_server/main.py`**

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.embedding_service import EmbeddingService
from services.vector_search_service import VectorSearchService
import logging

# Initialize FastAPI
app = FastAPI(title="agenthub RAG Server", version="1.0.0")

# Initialize services
embedding_service = EmbeddingService()
vector_search_service = VectorSearchService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingBatchRequest(BaseModel):
    texts: List[str]

class SearchRequest(BaseModel):
    query: str
    user_id: str
    category: Optional[str] = None
    min_similarity: float = 0.7
    limit: int = 10

class SearchResponse(BaseModel):
    results: List[dict]
    search_time_ms: int

# Endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "embedding_model": embedding_service.model_name,
        "database_connected": True  # Check DB connection if needed
    }

@app.post("/embed")
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for single text"""
    try:
        embedding = embedding_service.generate_embedding(request.text)
        return {
            "embedding": embedding,
            "dimension": len(embedding)
        }
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed/batch")
async def generate_embeddings_batch(request: EmbeddingBatchRequest):
    """Generate embeddings for multiple texts"""
    try:
        embeddings = embedding_service.generate_embeddings_batch(request.texts)
        return {
            "embeddings": embeddings,
            "count": len(embeddings)
        }
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/skills", response_model=SearchResponse)
async def search_skills(request: SearchRequest):
    """Search skills using semantic similarity"""
    import time
    start_time = time.time()

    try:
        # Perform semantic search (PostgreSQL handles query caching automatically)
        results = vector_search_service.search_skills(
            query=request.query,
            user_id=request.user_id,
            category=request.category,
            min_similarity=request.min_similarity,
            limit=request.limit
        )

        search_time_ms = int((time.time() - start_time) * 1000)

        return SearchResponse(
            results=results,
            search_time_ms=search_time_ms
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get RAG server statistics"""
    # Placeholder - implement metrics collection
    return {
        "total_embeddings_generated": 0,
        "total_searches": 0,
        "avg_search_time_ms": 0,
        "avg_embedding_time_ms": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### 7.4 Integration with Main System

**Main System Calls RAG Server:**

```python
# agenthub_main/src/fastmcp/task_management/application/services/skill_service.py

import httpx
from typing import List, Dict
from config import settings

class SkillService:
    def __init__(self):
        self.rag_server_url = settings.RAG_SERVER_URL  # http://rag-api:8001
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search_skills_semantic(
        self,
        query: str,
        user_id: str,
        category: str = None,
        min_similarity: float = 0.7,
        limit: int = 10
    ) -> List[Dict]:
        """Call RAG server for semantic search"""
        try:
            response = await self.client.post(
                f"{self.rag_server_url}/search/skills",
                json={
                    "query": query,
                    "user_id": user_id,
                    "category": category,
                    "min_similarity": min_similarity,
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["results"]

        except httpx.HTTPError as e:
            logger.error(f"RAG server request failed: {e}")
            # Fallback: use basic keyword search or return empty
            return []

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via RAG server"""
        try:
            response = await self.client.post(
                f"{self.rag_server_url}/embed",
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

        except httpx.HTTPError as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
```

**Configuration:**

```python
# agenthub_main/src/config.py

class Settings(BaseSettings):
    # Existing settings...

    # RAG Server
    RAG_SERVER_URL: str = Field(
        default="http://localhost:8001",
        env="RAG_SERVER_URL"
    )

    class Config:
        env_file = ".env"
```

**Environment Variables (`.env`):**

```env
# Existing variables...

# RAG Server
RAG_SERVER_URL=http://rag-api:8001  # Use service name in Docker network
```

### 7.5 Deployment Instructions

**Steps:**

1. **Build and Start RAG Server:**

```bash
# Navigate to project root
cd /home/daihu/__projects__/4genthub

# Create RAG server directory
mkdir -p agenthub_rag_server

# Copy files (see section 7.3 for file contents)
# ... copy Dockerfile, requirements.txt, main.py, services/, etc.

# Start RAG server
docker-compose -f docker-compose.rag-server.yml up -d

# Verify services are running
docker-compose -f docker-compose.rag-server.yml ps

# Check logs
docker logs agenthub-rag-api
docker logs agenthub-redis-rag

# Test health endpoint
curl http://localhost:8001/health
```

2. **Verify pgvector Extension:**

```bash
# Connect to PostgreSQL
docker exec -it agenthub-postgres psql -U agenthub_user -d agenthub

# Check extension
\dx

# Should see:
# vector | 0.5.1 | public | vector data type and ivfflat access method
```

3. **Run Database Migrations:**

```bash
# In main agenthub container
cd agenthub_main
alembic upgrade head  # Applies migrations for skill/knowledge tables
```

4. **Seed System Skills (Optional):**

```bash
python scripts/seed_system_skills.py
```

5. **Update Main System Environment:**

```bash
# Edit .env
echo "RAG_SERVER_URL=http://rag-api:8001" >> .env

# Restart main system to load new config
docker-compose restart
```

6. **Test End-to-End:**

```bash
# Test skill creation with embedding generation
curl -X POST http://localhost:8000/mcp/manage_skill \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "title": "Test Skill",
    "content": "This is a test skill content",
    "category": "testing"
  }'

# Test semantic search
curl -X POST http://localhost:8000/mcp/manage_skill \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "search",
    "query": "test skill content",
    "limit": 5
  }'
```

### 7.6 Monitoring & Maintenance

**Monitoring:**

```bash
# Monitor RAG server performance
docker stats agenthub-rag-api

# Monitor Redis cache
docker exec -it agenthub-redis-rag redis-cli INFO stats

# Monitor PostgreSQL pgvector usage
docker exec -it agenthub-postgres psql -U agenthub_user -d agenthub -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('agent_skills', 'agent_knowledge')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**Backup Strategy:**

```bash
# Backup skills/knowledge data
docker exec agenthub-postgres pg_dump -U agenthub_user -d agenthub \
  --table=agent_skills --table=agent_knowledge --table=skill_assignments \
  --table=knowledge_access_log > backup_rag_data_$(date +%Y%m%d).sql

# Backup embeddings (included in pg_dump, but vector columns are large)
# Consider separate backup for just metadata if space is concern
```

**Scaling Considerations:**

- **Horizontal Scaling**: Add more RAG server replicas behind load balancer
- **Vertical Scaling**: Increase memory for larger embedding models (e.g., BGE-large)
- **GPU Acceleration**: Use CUDA-enabled Docker image for 10x faster embeddings
- **Distributed Cache**: Use Redis Cluster for larger cache capacity

---

## 8. Integration with Existing System

### 8.1 Integration Points

**Touchpoints with Existing agenthub System:**

| Component | Integration Point | Changes Required |
|-----------|------------------|------------------|
| **Agent Management** | `call_agent()` endpoint | Add skills to response payload |
| **MCP Tools** | Add 3 new tools | `manage_skill`, `manage_knowledge`, `search_skills` |
| **Database** | PostgreSQL | Add 4 new tables, install pgvector extension |
| **Frontend** | React app | Add 2 new pages, update Agent Dashboard |
| **Authentication** | JWT tokens | Reuse existing auth (no changes) |
| **WebSocket** | Real-time updates | Optional: broadcast skill updates |

### 8.2 Backward Compatibility

**Principle: No Breaking Changes**

1. **API Endpoints**:
   - All new endpoints (manage_skill, etc.) are additions
   - Existing endpoints unchanged
   - `call_agent()` adds optional `skills` field (clients can ignore)

2. **Database**:
   - New tables don't affect existing tables
   - No foreign key constraints from existing tables to new tables
   - Migrations are additive only

3. **Frontend**:
   - New pages/routes don't interfere with existing routes
   - Existing components untouched
   - Feature flag for skill system (optional)

**Migration Strategy:**

```python
# Phase 1: Add tables (no FK dependencies)
def upgrade():
    op.create_table('agent_skills', ...)
    op.create_table('agent_knowledge', ...)
    # No foreign keys to existing tables yet

# Phase 2: Add indexes
def upgrade():
    op.create_index('idx_skills_user_category', ...)

# Phase 3: Enable pgvector
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Phase 4: Seed system skills (optional)
def upgrade():
    op.execute("INSERT INTO agent_skills (...) VALUES (...);")
```

**Rollback Plan:**

```python
def downgrade():
    op.drop_table('knowledge_access_log')
    op.drop_table('skill_assignments')
    op.drop_table('agent_knowledge')
    op.drop_table('agent_skills')
    op.execute("DROP EXTENSION IF EXISTS vector;")
```

### 8.3 Data Migration

**Scenario: Existing Agents Need Skills**

**Option 1: Manual Assignment**
- Admin manually assigns system skills to agents via UI
- Users gradually build their skill libraries

**Option 2: Auto-Assignment Based on Agent Type**

```python
# scripts/auto_assign_skills_to_agents.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mapping: agent slug → skill titles
AGENT_SKILL_MAPPING = {
    "coding-agent": [
        "Python Async Patterns",
        "FastAPI Best Practices",
        "Git Workflow Patterns",
        "Error Handling Strategies"
    ],
    "test-orchestrator-agent": [
        "pytest Best Practices",
        "Test Coverage Strategies",
        "CI/CD Integration"
    ],
    "debugging-agent": [
        "Python Debugging Techniques",
        "Log Analysis Patterns",
        "Root Cause Analysis"
    ],
    # ... more mappings
}

def assign_skills_to_agents():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    for agent_slug, skill_titles in AGENT_SKILL_MAPPING.items():
        # Get all agent instances of this type
        agents = session.query(AgentInstance).filter_by(slug=agent_slug).all()

        for agent in agents:
            for skill_title in skill_titles:
                # Find skill
                skill = session.query(AgentSkill).filter(
                    AgentSkill.title == skill_title,
                    AgentSkill.skill_type == 'system'
                ).first()

                if skill:
                    # Create assignment
                    assignment = SkillAssignment(
                        agent_id=agent.instance_id,
                        skill_id=skill.skill_id,
                        assigned_by='auto',
                        assignment_reason='Initial system skill assignment'
                    )
                    session.add(assignment)

    session.commit()
    print("Auto-assignment completed!")

if __name__ == "__main__":
    assign_skills_to_agents()
```

**Run After Deployment:**

```bash
python scripts/auto_assign_skills_to_agents.py
```

### 8.4 Testing Integration

**Integration Tests:**

```python
# agenthub_main/src/tests/integration/test_skill_integration.py

import pytest
from fastapi.testclient import TestClient

def test_call_agent_includes_skills(client: TestClient, auth_headers):
    """Verify call_agent returns skills in response"""
    # Assign a skill to coding-agent
    skill = create_test_skill(title="Test Skill")
    assign_skill_to_agent(skill_id=skill.skill_id, agent_id="coding-agent")

    # Call agent
    response = client.post(
        "/mcp/call_agent",
        json={"name_agent": "coding-agent"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify skills field exists
    assert "skills" in data
    assert len(data["skills"]) > 0

    # Verify skill structure
    skill_data = data["skills"][0]
    assert "skill_id" in skill_data
    assert "title" in skill_data
    assert "description" in skill_data
    assert "effectiveness_score" in skill_data

def test_skill_search_integration(client: TestClient, auth_headers):
    """Test semantic search integration with RAG server"""
    # Create test skills
    create_test_skill(
        title="Python Async Patterns",
        content="Async/await patterns for Python...",
        category="coding"
    )

    # Search
    response = client.post(
        "/mcp/manage_skill",
        json={
            "action": "search",
            "query": "async python patterns",
            "limit": 5
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] == True
    assert len(data["results"]) > 0
    assert data["results"][0]["similarity_score"] > 0.7
```

**End-to-End Test Scenarios:**

1. **New User Onboarding**:
   - User signs up → Gets access to system skills
   - User creates first custom skill
   - User assigns skills to their agents
   - User tests agent with skill via task execution

2. **Agent Task Execution with Skills**:
   - User calls `call_agent("coding-agent")`
   - Agent receives skills in response
   - Agent executes task, searches for skill mid-execution
   - Agent loads skill content, completes task
   - System logs skill usage and updates effectiveness_score

3. **Knowledge Base Upload**:
   - User uploads PDF document
   - System processes, chunks, generates embeddings
   - User queries knowledge base with natural language
   - System returns relevant chunks
   - User assigns knowledge to agent for future use

---

## 9. Implementation Roadmap

### 9.1 Phase Breakdown

#### **Phase 1: Database Foundation** (Days 1-3)

**Deliverables:**
- ✅ PostgreSQL tables created (agent_skills, agent_knowledge, skill_assignments, knowledge_access_log)
- ✅ pgvector extension installed and configured
- ✅ SQLAlchemy ORM models (DDD-compliant entities)
- ✅ Alembic migrations (upgrade/downgrade)
- ✅ Seed system skills (10-15 common skills)

**Tasks:**

| Day | Task | Owner | Hours |
|-----|------|-------|-------|
| 1 | Design schema, create migration scripts | Backend Dev | 6 |
| 1-2 | Implement ORM models (Skill, Knowledge entities) | Backend Dev | 4 |
| 2 | Install pgvector, configure indexes | DevOps | 3 |
| 2-3 | Write seed scripts for system skills | Backend Dev | 4 |
| 3 | Test migrations (up/down), verify data integrity | QA | 3 |

**Success Criteria:**
- All tables created without errors
- pgvector extension active (`SELECT * FROM pg_extension WHERE extname='vector';`)
- 10+ system skills seeded with embeddings
- Unit tests pass for all ORM models

---

#### **Phase 2: RAG Infrastructure** (Days 4-7)

**Deliverables:**
- ✅ Embedding service (sentence-transformers)
- ✅ Vector search service (pgvector queries)
- ✅ Redis caching layer
- ✅ RAG server (FastAPI) deployed
- ✅ Integration tests for RAG pipeline

**Tasks:**

| Day | Task | Owner | Hours |
|-----|------|-------|-------|
| 4 | Implement EmbeddingService class | Backend Dev | 4 |
| 4-5 | Implement VectorSearchService with pgvector | Backend Dev | 6 |
| 5 | Implement RAGCacheService (Redis) | Backend Dev | 4 |
| 5-6 | Build RAG server (FastAPI endpoints) | Backend Dev | 6 |
| 6 | Dockerize RAG server, create docker-compose config | DevOps | 4 |
| 6-7 | Integration tests (embedding → search → cache) | QA | 6 |
| 7 | Performance tuning (batch embeddings, index optimization) | Backend Dev | 4 |

**Success Criteria:**
- Embedding generation < 50ms per text
- Semantic search < 100ms
- Cache hit rate > 60% in tests
- RAG server passes health checks
- 95% test coverage on RAG services

---

#### **Phase 3: MCP Tools Layer** (Days 8-10)

**Deliverables:**
- ✅ `manage_skill` tool (all 8 actions)
- ✅ `manage_knowledge` tool (all actions)
- ✅ `search_skills` tool
- ✅ Enhanced `call_agent` (includes skills)
- ✅ API documentation

**Tasks:**

| Day | Task | Owner | Hours |
|-----|------|-------|-------|
| 8 | Implement manage_skill (create, get, list, update, delete) | Backend Dev | 6 |
| 8-9 | Implement manage_skill (search, assign, unassign) | Backend Dev | 4 |
| 9 | Implement manage_knowledge (create, upload, search) | Backend Dev | 6 |
| 9 | Implement search_skills (lightweight wrapper) | Backend Dev | 2 |
| 10 | Modify call_agent to include skills in response | Backend Dev | 3 |
| 10 | Write API docs (OpenAPI spec) | Tech Writer | 3 |
| 10 | Integration tests for all tools | QA | 4 |

**Success Criteria:**
- All 3 tools functional via MCP protocol
- `call_agent` returns skills field
- API docs published (Swagger UI)
- Postman collection created for testing
- 100% endpoint coverage in tests

---

#### **Phase 4: Frontend UI** (Days 11-14)

**Deliverables:**
- ✅ Skill Manager page (`/skills`)
- ✅ Knowledge Base page (`/knowledge`)
- ✅ Agent Dashboard skills section
- ✅ Search/filter/sort functionality
- ✅ Markdown editor for skill content

**Tasks:**

| Day | Task | Owner | Hours |
|-----|------|-------|-------|
| 11 | Design UI mockups (Figma) | Designer | 4 |
| 11-12 | Implement Skill Manager page (SkillCard, SkillCreateModal) | Frontend Dev | 8 |
| 12 | Implement skill search bar with filters | Frontend Dev | 4 |
| 12-13 | Implement Knowledge Base page (upload, list, query) | Frontend Dev | 8 |
| 13 | Integrate markdown editor (react-simplemde) | Frontend Dev | 4 |
| 13-14 | Add skills section to Agent Dashboard | Frontend Dev | 6 |
| 14 | UI polish, responsive design, accessibility | Frontend Dev | 4 |
| 14 | E2E tests (Cypress) | QA | 4 |

**Success Criteria:**
- Users can create/edit/delete skills via UI
- Users can upload documents to knowledge base
- Markdown editor renders correctly
- Search/filter works across all lists
- Mobile-responsive design
- E2E tests pass (skill creation → assignment → agent call)

---

### 9.2 Timeline Summary

| Phase | Duration | Dependencies | Risk |
|-------|----------|--------------|------|
| Phase 1: Database | 3 days | None | Low |
| Phase 2: RAG Infrastructure | 4 days | Phase 1 | Medium (embedding model setup) |
| Phase 3: MCP Tools | 3 days | Phase 1, Phase 2 | Low |
| Phase 4: Frontend UI | 4 days | Phase 3 | Low |
| **Total** | **14 days** | Sequential | **Low-Medium** |

**Buffer:** +4 days (contingency for unexpected issues)

**Total with Buffer:** **18 days** (~ 3.5 weeks)

### 9.3 Resource Allocation

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Total Hours |
|------|---------|---------|---------|---------|-------------|
| Backend Developer | 17 | 24 | 21 | 0 | 62 |
| Frontend Developer | 0 | 0 | 0 | 38 | 38 |
| DevOps Engineer | 3 | 4 | 0 | 0 | 7 |
| QA Engineer | 3 | 6 | 4 | 4 | 17 |
| Designer | 0 | 0 | 0 | 4 | 4 |
| Tech Writer | 0 | 0 | 3 | 0 | 3 |

**Team Size:** 5-6 people (1 backend, 1 frontend, 1 QA, 1 DevOps part-time, 1 designer part-time, 1 tech writer part-time)

### 9.4 Risk Management

**Potential Risks:**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| pgvector installation issues | Medium | High | Pre-test on staging, use Docker image with pgvector pre-installed |
| Embedding model download slow | Medium | Medium | Cache model in Docker image, use CDN mirror |
| Performance issues with large datasets | Low | High | Implement pagination, lazy loading, query optimization early |
| Integration conflicts with existing code | Low | Medium | Thorough testing, feature flags for rollback |
| User confusion with new UI | Medium | Low | User testing, onboarding tooltips, documentation |

**Contingency Plans:**

- **pgvector issues**: Fallback to keyword search (less accurate but functional)
- **Performance issues**: Add aggressive caching, implement query limits
- **Integration issues**: Use feature flags to disable skill system if critical bug found

---

## 10. Security & Privacy

### 10.1 Data Privacy Guarantees

**Core Principles:**

1. **Data Sovereignty**: All user data stored on user's private infrastructure
2. **No External Calls**: Embeddings generated locally (sentence-transformers)
3. **Multi-Tenancy Isolation**: Row-level security (RLS) ensures users only see their data
4. **Encryption**: Data at rest (PostgreSQL encryption), data in transit (HTTPS/TLS)

### 10.2 Authentication & Authorization

**Authentication:**
- Reuse existing JWT-based auth system
- user_id extracted from token claims
- All MCP tools require valid authentication

**Authorization Matrix:**

| Resource | Create | Read | Update | Delete | Search |
|----------|--------|------|--------|--------|--------|
| **Own Skills** | ✅ User | ✅ User | ✅ User | ✅ User | ✅ User |
| **System Skills** | ❌ Admin only | ✅ All users | ❌ Admin only | ❌ Admin only | ✅ All users |
| **Other User's Skills** | N/A | ❌ Blocked | ❌ Blocked | ❌ Blocked | ❌ Blocked |
| **Own Knowledge** | ✅ User | ✅ User | ✅ User | ✅ User | ✅ User |
| **Other User's Knowledge** | N/A | ❌ Blocked | ❌ Blocked | ❌ Blocked | ❌ Blocked |

**Row-Level Security (PostgreSQL):**

```sql
-- Enable RLS
ALTER TABLE agent_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge ENABLE ROW LEVEL SECURITY;

-- Policy: Users see their own + system skills
CREATE POLICY user_skills_read_policy ON agent_skills
FOR SELECT
USING (
    user_id = current_setting('app.current_user_id')::UUID
    OR user_id IS NULL  -- System skills
);

-- Policy: Users can only modify their own skills
CREATE POLICY user_skills_write_policy ON agent_skills
FOR ALL
USING (user_id = current_setting('app.current_user_id')::UUID);

-- Similar policies for agent_knowledge
CREATE POLICY user_knowledge_read_policy ON agent_knowledge
FOR SELECT
USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY user_knowledge_write_policy ON agent_knowledge
FOR ALL
USING (user_id = current_setting('app.current_user_id')::UUID);
```

### 10.3 Input Validation & Sanitization

**Validation Rules:**

| Field | Validation |
|-------|------------|
| `title` | 1-200 chars, alphanumeric + spaces, no special chars except `-_` |
| `content` | Max 50,000 chars, sanitize HTML/JS if markdown contains code |
| `category` | Max 100 chars, lowercase, kebab-case |
| `tags` | Max 20 tags, each 1-50 chars |
| `query` | Max 500 chars, SQL injection prevention |

**Sanitization:**

```python
import bleach
from html import escape

def sanitize_content(content: str) -> str:
    """Sanitize user-provided content"""
    # Allow markdown, but strip dangerous HTML
    allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre', 'h1', 'h2', 'h3']
    return bleach.clean(content, tags=allowed_tags, strip=True)

def sanitize_query(query: str) -> str:
    """Sanitize search queries"""
    # Remove SQL injection attempts
    query = escape(query)
    # Remove special characters that could break vector search
    query = query.replace("'", "").replace(";", "").replace("--", "")
    return query.strip()
```

### 10.4 Rate Limiting

**Rate Limits (per user):**

| Endpoint | Limit | Window |
|----------|-------|--------|
| `manage_skill` (create) | 20 | 1 minute |
| `manage_skill` (search) | 100 | 1 minute |
| `manage_knowledge` (upload) | 10 | 1 minute |
| `search_skills` | 200 | 1 minute |

**Implementation:**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/mcp/manage_skill")
@limiter.limit("20/minute")
async def manage_skill(request: Request, ...):
    # ... implementation
```

### 10.5 Audit Logging

**Log All Operations:**

```python
# agenthub_main/src/fastmcp/task_management/infrastructure/logging/audit_logger.py

import logging
from datetime import datetime

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")

    def log_skill_operation(
        self,
        user_id: str,
        action: str,
        skill_id: str = None,
        details: dict = None
    ):
        self.logger.info({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource_type": "skill",
            "action": action,
            "skill_id": skill_id,
            "details": details,
            "ip_address": request.client.host
        })
```

**Log Examples:**

```json
// Skill creation
{
  "timestamp": "2025-11-13T10:30:00Z",
  "user_id": "user-123",
  "resource_type": "skill",
  "action": "create",
  "skill_id": "skill-456",
  "details": {"title": "Python Async Patterns", "category": "coding"},
  "ip_address": "192.168.1.100"
}

// Unauthorized access attempt
{
  "timestamp": "2025-11-13T10:31:00Z",
  "user_id": "user-789",
  "resource_type": "skill",
  "action": "read_attempt_denied",
  "skill_id": "skill-456",
  "details": {"reason": "user_id mismatch"},
  "ip_address": "192.168.1.200"
}
```

### 10.6 Compliance Considerations

**GDPR Compliance:**

- **Right to Access**: Users can export all their skills/knowledge (add export endpoint)
- **Right to Deletion**: Hard delete removes all user data including embeddings
- **Data Portability**: Export format: JSON (skills + knowledge + metadata)

**Implementation:**

```python
@app.post("/mcp/user/export_data")
async def export_user_data(user_id: str):
    """Export all user's skills and knowledge (GDPR compliance)"""
    skills = db.query(AgentSkill).filter_by(user_id=user_id).all()
    knowledge = db.query(AgentKnowledge).filter_by(user_id=user_id).all()

    return {
        "export_date": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "skills": [skill.to_dict() for skill in skills],
        "knowledge": [k.to_dict() for k in knowledge]
    }

@app.post("/mcp/user/delete_all_data")
async def delete_all_user_data(user_id: str):
    """Delete all user data (GDPR Right to be Forgotten)"""
    # Hard delete all skills
    db.query(AgentSkill).filter_by(user_id=user_id).delete()
    # Hard delete all knowledge
    db.query(AgentKnowledge).filter_by(user_id=user_id).delete()
    # Delete from vector store
    cache_service.redis.delete(f"user:{user_id}:*")

    db.commit()
    return {"message": "All user data deleted permanently"}
```

---

## Appendix A: Example System Skills

**Skill 1: Python Async Error Handling**

```markdown
# Python Async Error Handling Patterns

## Overview
Best practices for gracefully handling errors in asynchronous Python code.

## Pattern 1: Try-Except in Coroutines

```python
async def fetch_data(url: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutError:
        logger.error(f"Timeout fetching {url}")
        return {"error": "timeout"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code}")
        return {"error": "http_error", "status": e.response.status_code}
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"error": "unknown"}
```

## Pattern 2: Gather with Return Exceptions

```python
import asyncio

async def fetch_all(urls: list[str]) -> list[dict]:
    tasks = [fetch_data(url) for url in urls]
    # return_exceptions=True prevents one failure from canceling all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    successful_results = [
        r for r in results
        if not isinstance(r, Exception)
    ]
    return successful_results
```

## Pattern 3: Timeout Context Manager

```python
async def fetch_with_timeout(url: str, timeout: float = 5.0) -> dict:
    try:
        async with asyncio.timeout(timeout):
            return await fetch_data(url)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout}s")
        return {"error": "timeout"}
```

## Best Practices

1. **Always specify timeouts**: Prevent hanging indefinitely
2. **Use `return_exceptions=True` in gather**: Fail gracefully
3. **Log exceptions**: Include context (URL, params, timestamp)
4. **Return error objects**: Don't raise exceptions in async code unless fatal
5. **Use asyncio.TimeoutError**: More specific than generic Exception

## When to Use Each Pattern

- **Pattern 1**: Single async operation with known failure modes
- **Pattern 2**: Multiple independent async operations (fan-out)
- **Pattern 3**: Time-critical operations with strict deadlines
```

**Metadata:**
- Category: `backend-patterns`
- Tags: `python`, `async`, `error-handling`, `best-practices`
- Effectiveness Score: 0.92 (based on agent feedback)
- Usage Count: 156

---

**Skill 2: FastAPI Dependency Injection**

```markdown
# FastAPI Dependency Injection Patterns

## Overview
Leverage FastAPI's dependency injection system for clean, testable code.

## Pattern 1: Database Session Dependency

```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Pattern 2: Authentication Dependency

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("sub")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user)
):
    return {"message": f"Hello {current_user.username}"}
```

## Pattern 3: Nested Dependencies

```python
async def get_db() -> AsyncSession:
    # ... database session

async def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    return UserService(db)

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.create(user_data)
```

## Benefits

1. **Testability**: Easy to mock dependencies in tests
2. **Separation of Concerns**: Business logic separate from HTTP layer
3. **Reusability**: Share dependencies across routes
4. **Type Safety**: Full IDE autocomplete and type checking

## Testing with Dependencies

```python
import pytest
from fastapi.testclient import TestClient

def override_get_db():
    # Return test database session
    return test_db

app.dependency_overrides[get_db] = override_get_db

def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
```
```

**Metadata:**
- Category: `backend-patterns`
- Tags: `fastapi`, `dependency-injection`, `python`, `api-design`
- Effectiveness Score: 0.89
- Usage Count: 98

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - AI technique combining information retrieval with generation |
| **Embedding** | Vector representation of text (numbers) that captures semantic meaning |
| **pgvector** | PostgreSQL extension for storing and searching vector embeddings |
| **Cosine Similarity** | Metric for measuring similarity between two vectors (range: -1 to 1) |
| **LlamaIndex** | Framework for building RAG applications with LLMs |
| **LangChain** | Framework for developing applications powered by language models |
| **LangGraph** | Extension of LangChain for building stateful multi-agent systems |
| **LoRA** | Low-Rank Adaptation - Efficient fine-tuning technique for large models |
| **sentence-transformers** | Python library for generating semantic embeddings |
| **ivfflat** | Inverted File with Flat compression - pgvector index type for fast approximate search |
| **DDD** | Domain-Driven Design - Software design approach focusing on domain model |
| **MCP** | Model Context Protocol - Protocol for AI agent tool usage |

---

## Appendix C: References

**Documentation:**
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [LangChain Docs](https://python.langchain.com/docs/)
- [sentence-transformers](https://www.sbert.net/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

**Research Papers:**
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "LoRA: Low-Rank Adaptation of Large Language Models" (Hu et al., 2021)
- "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks" (Reimers & Gurevych, 2019)

---

**End of Technical Specifications**

---

**Next Steps:**
1. Review this document with stakeholders
2. Get approval on architecture decisions
3. Finalize resource allocation
4. Begin Phase 1: Database Foundation
5. Schedule weekly progress reviews

**Questions? Contact:**
- Architecture: [Architect Email]
- Implementation: [Dev Team Lead]
- Timeline: [Project Manager]
