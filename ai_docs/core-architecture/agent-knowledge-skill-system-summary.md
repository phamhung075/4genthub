# Agent Knowledge & Skill Management System - Executive Summary

**Document**: `agent-knowledge-skill-system-specs.md`
**Date**: 2025-11-13
**Status**: ✅ Planning Complete - Ready for Implementation

---

## 🎯 What You're Building

A **dynamic agent intelligence system** where AI agents can:

1. **Access private knowledge bases** via RAG (Retrieval-Augmented Generation)
2. **Load skills on-demand** during task execution
3. **Generate new skills** when encountering unfamiliar domains
4. **Continuously improve** through effectiveness feedback

---

## 🔑 Key Decisions (Based on Your Preferences)

| Decision | Your Choice | Impact |
|----------|-------------|--------|
| **Scope** | Full System (Phases 1-4) | 14-18 days, includes UI |
| **Embeddings** | Local (sentence-transformers) | 100% private, no API costs |
| **Deployment** | Separate RAG server | Scalable, isolated workload |
| **AI Service** | Claude Code (subscription) | No per-request costs |

---

## 📊 System Architecture

### Core Components

```
User → call_agent("coding-agent")
        ↓
     Returns: {system_prompt, tools, skills: [...]}
        ↓
     Agent works on task
        ↓
     Needs skill: "async patterns"
        ↓
     search_skills(query="async patterns")
        ↓
     RAG System (pgvector + sentence-transformers)
        ↓
     Returns: Top 5 relevant skills with similarity scores
        ↓
     Agent loads skill content → Completes task
```

### Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Local, fast, free |
| **Vector DB** | PostgreSQL + pgvector | Integrated, no external deps |
| **Caching** | None (MVP) | Simplicity over optimization |
| **RAG Framework** | Direct pgvector (MVP) → LlamaIndex (later) | Simple first, advanced later |
| **Backend** | FastAPI | Existing stack |
| **Frontend** | React + TypeScript | Existing stack |

---

## 🗄️ Database Schema (4 New Tables)

### 1. `agent_skills`
- Stores reusable skills (code patterns, best practices)
- **Key fields**: title, content, embedding_vector (384 dims), effectiveness_score, usage_count
- **Indexes**: pgvector ivfflat for semantic search

### 2. `agent_knowledge`
- User's private knowledge base (documents, notes)
- **Key fields**: title, content, content_type, chunk_index, embedding_vector
- **Chunking**: Large docs split into 1000-word chunks

### 3. `skill_assignments`
- Links skills to agents (many-to-many)
- **Key fields**: agent_id, skill_id, priority, assigned_by

### 4. `knowledge_access_log`
- Audit trail for analytics
- **Key fields**: resource_id, task_id, was_helpful, similarity_score

---

## 🔧 New MCP Tools

### 1. `manage_skill`

**Actions**: create, update, delete, get, list, search, assign_to_agent, unassign_from_agent

**Example - Create Skill:**
```python
manage_skill(
    action="create",
    title="Python Async Patterns",
    content="# Async Best Practices\n\n1. Use timeout...",
    category="backend-patterns",
    tags=["python", "async"]
)
```

**Example - Search Skills (RAG):**
```python
manage_skill(
    action="search",
    query="how to handle async errors in Python",
    limit=5
)
# Returns: Top 5 skills with similarity scores > 0.7
```

### 2. `manage_knowledge`

**Actions**: create, upload_file, search, list, get, update, delete

**Example - Upload PDF:**
```python
manage_knowledge(
    action="upload_file",
    file=<pdf_binary>,
    category="deployment"
)
# System: Extracts text, chunks, generates embeddings
```

### 3. `search_skills`

Lightweight wrapper for quick searches.

### 4. Enhanced `call_agent`

**Before:**
```json
{
  "name": "coding-agent",
  "system_prompt": "...",
  "tools": [...]
}
```

**After (with skills):**
```json
{
  "name": "coding-agent",
  "system_prompt": "...",
  "tools": [...],
  "skills": [
    {
      "skill_id": "...",
      "title": "Python Async Patterns",
      "description": "...",
      "effectiveness_score": 0.92
    }
  ]
}
```

---

## 🚀 Deployment: Separate RAG Server

### Architecture

```
Main agenthub Server (Port 8000)
    ↓ HTTP calls
RAG Server (Port 8001)
    • Embedding service
    • Vector search
    ↓
PostgreSQL (Port 5432)
    • pgvector extension
    • skill/knowledge tables
    • Default configuration (no tuning)
```

### Docker Compose Services

1. **rag-api**: FastAPI server for embeddings & search
2. **postgres**: Shared DB with pgvector (default settings)

**Start Command:**
```bash
docker-compose -f docker-compose.rag-server.yml up -d
```

---

## 💻 Frontend UI (3 New Pages)

### 1. Skill Manager (`/skills`)

**Features:**
- Create/edit/delete skills
- Markdown editor with preview
- Semantic search bar
- Filter by category, effectiveness score
- Assign skills to agents

### 2. Knowledge Base (`/knowledge`)

**Features:**
- Upload documents (PDF, TXT, MD, DOCX)
- Natural language query interface
- View chunks with similarity scores
- Organize by category

### 3. Agent Dashboard (Enhanced)

**New Section:**
- View assigned skills (8 skills)
- Skill usage analytics (most used, highest effectiveness)
- Adjust skill priority (drag-and-drop)
- Performance metrics (avg load time)

---

## 📅 Implementation Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1: Database** | 3 days | Tables, pgvector, ORM models, migrations |
| **Phase 2: RAG Infrastructure** | 3 days | Embedding service, vector search, RAG server (no cache complexity) |
| **Phase 3: MCP Tools** | 3 days | manage_skill, manage_knowledge, enhanced call_agent |
| **Phase 4: Frontend UI** | 4 days | Skill Manager, Knowledge Base, Agent Dashboard |
| **Buffer** | 4 days | Contingency |
| **TOTAL** | **17 days** | **~ 3 weeks** |

---

## 🔐 Security & Privacy

### Data Privacy Guarantees

✅ **100% Private**: All data on your infrastructure
✅ **Local Embeddings**: No API calls (sentence-transformers)
✅ **Multi-Tenant Isolation**: Row-level security (RLS)
✅ **Encryption**: At rest (PostgreSQL) + in transit (HTTPS)

### Authorization

- Users can only access **their own skills** + **system skills**
- Row-level security enforced at PostgreSQL level
- JWT authentication (existing system)

---

## 📈 Performance Expectations (MVP)

| Operation | Expected | Notes |
|-----------|----------|-------|
| Generate embedding | 50-100ms | CPU inference, no optimization |
| Search skills (RAG) | 150-300ms | End-to-end, no caching |
| Get skill content | 50-100ms | Direct PostgreSQL query |
| Overall UX | <500ms | Acceptable for MVP user experience |

**MVP Philosophy**: Measure first, optimize later. If users complain about speed, then add caching.

---

## 🎓 Example Use Cases

### Use Case 1: Agent Auto-Discovers Skill

1. User: "Fix async bug in auth module"
2. Agent analyzes: "Need async error handling patterns"
3. Agent calls: `search_skills(query="async error handling")`
4. RAG returns: "Python Async Error Handling" (similarity: 0.89)
5. Agent loads skill content, applies pattern
6. Bug fixed! ✅
7. System logs: skill_usage++, effectiveness_score updated

### Use Case 2: User Creates Custom Skill

1. User opens Skill Manager UI
2. Creates skill: "Company-Specific AWS Deployment Process"
3. Content: Step-by-step instructions with code snippets
4. System generates embedding, stores in pgvector
5. Skill assigned to devops-agent
6. Next deployment task: Agent uses custom skill automatically

### Use Case 3: Knowledge Base Upload

1. User uploads: "FastAPI Production Guide.pdf" (23 pages)
2. System:
   - Extracts text (PyPDF2)
   - Splits into 12 chunks (1000 words each)
   - Generates embeddings for each chunk
   - Stores in agent_knowledge table
3. Later, agent queries: "How to configure Gunicorn workers?"
4. RAG retrieves relevant chunk (Part 3, similarity: 0.91)
5. Agent uses knowledge to configure deployment

---

## 🔄 Next Steps

### Immediate Actions (This Week)

1. **Review Specifications** (ai_docs/core-architecture/agent-knowledge-skill-system-specs.md)
   - 10 sections, 50,000+ words, comprehensive coverage
   - Review database schema (Section 3)
   - Review API specifications (Section 4)

2. **Stakeholder Approval**
   - Architecture decisions
   - Timeline (14-18 days)
   - Resource allocation (5-6 people)

3. **Environment Setup**
   - Provision separate server for RAG (if not using existing)
   - Install Docker + docker-compose
   - PostgreSQL with pgvector extension

### Implementation Start (Next Week)

**Phase 1: Database Foundation** (Days 1-3)

**Day 1 Tasks:**
- Create Alembic migration for 4 new tables
- Design SQLAlchemy ORM models (Skill, Knowledge entities)
- Install pgvector extension in PostgreSQL

**First Code to Write:**
```python
# agenthub_main/src/fastmcp/task_management/domain/entities/skill.py

from sqlalchemy import Column, String, Text, Float, Integer, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

class Skill(Base):
    __tablename__ = "agent_skills"

    skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    embedding_vector = Column(Vector(384))  # pgvector column
    effectiveness_score = Column(Float, default=0.0)
    # ... more fields (see spec Section 3.1)
```

**Ready to Start?**
- ✅ Specifications complete
- ✅ Architecture validated
- ✅ Timeline defined
- ✅ Technology stack chosen
- ⏳ Awaiting your approval to begin implementation

---

## 📚 Documentation Location

All specs located in: `ai_docs/core-architecture/`

| File | Purpose | Size |
|------|---------|------|
| **agent-knowledge-skill-system-specs.md** | Complete technical specs | 50,000+ words |
| **agent-knowledge-skill-system-summary.md** | This executive summary | 2,000 words |

---

## ❓ Questions Before Starting?

- Database schema concerns?
- RAG architecture clarifications?
- Timeline adjustments needed?
- Resource constraints?
- Integration risks?

**Contact:** Ready to begin implementation when you give the green light! 🚀

---

**Prepared by**: Master Orchestrator Agent
**Date**: 2025-11-13
**Status**: ✅ Planning Phase Complete
