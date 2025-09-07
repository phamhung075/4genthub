# Claude Document Management System

A comprehensive PostgreSQL-based document management system designed for `.claude/commands` with full-text search, semantic search, versioning, and MCP integration.

## 📁 Documentation Structure

### 🏗️ Architecture
- **[System Architecture](architecture/claude-document-management-architecture.md)** - Complete system design, database schema, and component relationships

### 🚀 Implementation
- **[Implementation Guide](implementation/claude-document-management-implementation.md)** - Step-by-step setup, configuration, and deployment instructions

### 📋 Phases
- **[Multi-Phase Implementation Plan](phases/claude-document-management-phases.md)** - 5-phase roadmap from PostgreSQL baseline to enterprise features
- **[Phase 2: pgvector Integration](phases/phase2-pgvector-implementation.md)** - Semantic search with vector embeddings
- **[Phase 3: Advanced Search](phases/phase3-advanced-search-implementation.md)** - Analytics, recommendations, faceted search

### 📄 File Specifications
- **[Complete File Structure & Tests](file-specifications/complete-file-structure-and-tests.md)** - Comprehensive file listings, locations, and test requirements for all phases

### 🔧 CLI Commands
- **[manage_document_md_postgresql](cli-commands/manage_document_md_postgresql)** - Main CLI tool for document management
- **[setup_doc_database.sh](cli-commands/setup_doc_database.sh)** - Database setup and configuration script

## 🎯 Quick Start

1. **Database Setup**:
   ```bash
   ./cli-commands/setup_doc_database.sh
   ```

2. **Initialize System**:
   ```bash
   ./cli-commands/manage_document_md_postgresql init
   ```

3. **Sync Documents**:
   ```bash
   ./cli-commands/manage_document_md_postgresql sync
   ```

4. **Search Documents**:
   ```bash
   ./cli-commands/manage_document_md_postgresql search "query"
   ```

## 🔍 Features

### Phase 1 (Completed) ✅
- PostgreSQL database with full-text search
- CLI command interface
- MCP integration
- Version control
- Metadata extraction

### Phase 2 (Planned)
- pgvector semantic search
- OpenAI embedding integration
- Hybrid search (keyword + semantic)
- Vector similarity matching

### Phase 3 (Planned)
- Advanced query language
- Search analytics
- Content recommendations
- Faceted search

### Phase 4 (Planned)
- AI-powered content analysis
- Claude AI integration
- Natural language queries
- Content generation

### Phase 5 (Planned)
- Multi-tenant architecture
- Enterprise security
- Scalability optimization
- Monitoring & alerting

## 🗂️ File Organization

```
claude-document-management-system/
├── architecture/           # System design and schemas
├── implementation/         # Setup and deployment guides
├── phases/                # Implementation phases and roadmaps
├── file-specifications/   # Complete file listings and tests
├── cli-commands/          # Executable scripts and tools
└── README.md             # This file
```

## 🔗 Related Documentation

- **Main Docs Index**: [../index.md](../index.md)
- **Architecture Guide**: [../architecture.md](../architecture.md)
- **API Reference**: [../api-reference.md](../api-reference.md)
- **Testing Guide**: [../testing.md](../testing.md)

## 📝 Implementation Status

- **Phase 1**: ✅ Completed - PostgreSQL baseline with CLI and MCP integration
- **Phase 2**: 📋 Planned - pgvector semantic search
- **Phase 3**: 📋 Planned - Advanced search and analytics
- **Phase 4**: 📋 Planned - AI-powered features
- **Phase 5**: 📋 Planned - Enterprise features

## 🤝 Contributing

See the [implementation guide](implementation/claude-document-management-implementation.md) for development setup and the [file specifications](file-specifications/complete-file-structure-and-tests.md) for complete file structure requirements.