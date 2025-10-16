# Core Architecture Documentation

**Last Updated:** 2025-10-16
**File Count:** 26 active documents
**Python Version:** 3.14.0
**Architecture Phase:** DDD Phase 8 Complete

## Overview

This directory contains the **core architectural design documentation** for the agenthub system, focusing on fundamental system design, technical architecture, and foundational patterns.

**Recent Consolidation (2025-10-16)**: Major documentation consolidation completed, reducing from 36 files to 26 files (28% reduction) with elimination of duplicate content:
- ✅ Database timestamp documentation (6 files → 1 unified doc)
- ✅ MCP injection system (4 files → 1 comprehensive doc)
- ✅ Agent system architecture (3 files → 1 complete doc)
- ✅ All updated to Python 3.14.0 and DDD Phase 8

---

## Core Documents (26 Files)

### 📋 Product Requirements & High-Level Architecture (4 files)

**1. [Product Requirements Document (PRD)](./README.md)** ⭐ **FOUNDATIONAL**
   - Complete product vision and requirements
   - 33 specialized AI agents overview
   - 4-tier context hierarchy design (Global → Project → Branch → Task)
   - Technical requirements and roadmap
   - Success metrics and compliance standards

**2. [Technical Architecture](./Architecture_Technique.md)** ⭐ **FOUNDATIONAL**
   - Domain-Driven Design (DDD) Phase 8 implementation
   - FastMCP 2.0 framework integration
   - Complete system layers and components
   - MCP protocol integration (15+ tool categories)
   - Vision System architecture (6 phases)
   - Database schema and performance targets
   - **Updated:** Python 3.14.0, DDD Phase 8

**3. [System Architecture Overview](./system-architecture-overview.md)** ⭐ **FOUNDATIONAL**
   - High-level system design and components
   - Technology stack overview (React 19, Vite 7, Python 3.14)
   - Integration patterns and workflows
   - Service architecture and communication
   - Event System (EventQueue, EventBus, EventWorker)
   - **Updated:** Current architecture standards

**4. [Architecture Thinking](./architecture-thinking.md)**
   - Architectural decision-making process
   - Design principles and trade-offs
   - Pattern selection guidelines
   - System evolution strategy

### 🗄️ Database & Data Architecture (2 files)

**5. [Database Architecture](./database-architecture.md)** ⭐ **CRITICAL**
   - Database design patterns and schemas
   - SQLite (dev) and PostgreSQL (production) configurations
   - Performance optimization strategies
   - Data modeling and relationships
   - Migration patterns
   - **Updated:** Python 3.14.0, Event System integration

**6. [Unified Timestamp Architecture](./unified-timestamp-architecture.md)** ⭐ **NEW - CONSOLIDATED**
   - **Replaces 6 previous documents** (database-timestamp-standardization-summary.md, timestamp-management-architectural-analysis.md, database-schema-timestamp-alignment-verification.md, timestamp-query-optimization-analysis.md, database-initialization-enhancement.md, database-session-handling-optimization.md)
   - Complete timestamp management strategy
   - Application Layer vs Database Triggers decision
   - Schema standardization for PostgreSQL and SQLite
   - Query optimization strategies with benchmarks
   - Session handling and initialization
   - Testing and verification guidelines
   - **Updated:** Python 3.14.0+, DDD Phase 8 Complete

### 🤖 Agent System Architecture (1 file)

**7. [Agent System Architecture](./agent-system-architecture.md)** ⭐ **NEW - CONSOLIDATED**
   - **Replaces 3 previous documents** (agent-delegation-fix.md, agent-orchestration-architecture.md, sub-agent-instructions.md)
   - Complete agent system architecture and hierarchy
   - Master Orchestrator Pattern (supreme conductor)
   - Agent Delegation System (direct agent calling with `call_agent`)
   - Agent Orchestration (multi-agent coordination)
   - Sub-Agent Instructions (specialized agent execution)
   - 33 Specialized Agents directory with decision trees
   - Dynamic Tool Enforcement v2.0 (agent-specific permissions)
   - Task Management Integration (MCP tasks)
   - Best Practices for Python 3.14.0 and DDD Phase 8
   - Troubleshooting guide
   - **Updated:** Python 3.14.0, DDD Phase 8, 95% token savings architecture

### 🔗 MCP Integration & Injection System (1 file)

**8. [MCP Injection Architecture](./mcp-injection-architecture.md)** ⭐ **NEW - CONSOLIDATED**
   - **Replaces 4 previous documents** (mcp-auto-injection-architecture.md, real-time-context-injection-system.md, real-time-injection-system.md, mcp-injection-task-dependencies.md)
   - Complete MCP injection system architecture
   - Authentication and HTTP communication
   - Auto-injection mechanisms (session start)
   - Real-time context injection (during execution)
   - Post-tool context updates (synchronization)
   - Task dependency integration
   - Performance optimization and caching
   - Implementation guide for Python 3.14.0 and DDD Phase 8
   - Error handling and resilience
   - Monitoring and observability
   - Security considerations
   - References to CLAUDE.md for Dynamic Tool Enforcement v2.0
   - **Updated:** Python 3.14.0+, DDD Phase 8 Complete

### 🏛️ Domain-Driven Design (DDD) (3 files)

**9. [Domain-Driven Design Layers](./domain-driven-design-layers.md)** ⭐ **CRITICAL**
   - Complete DDD Phase 8 implementation
   - Strict layer separation (Domain, Application, Infrastructure, Interface)
   - Domain entities, value objects, and domain services
   - Application use cases and facades
   - Infrastructure repositories and external services
   - Interface layer (MCP controllers, HTTP endpoints)
   - Best practices and patterns
   - **Status:** Phase 8 Complete

**10. [Domain Events Catalog](./domain-events-catalog.md)**
   - Complete domain events reference
   - Event definitions and payloads
   - Event handlers and subscribers
   - Event sourcing patterns
   - Integration with Event System (EventQueue, EventBus)

**11. [Cascade Calculator DDD Refactoring](./cascade-calculator-ddd-refactoring.md)**
   - Real-world DDD refactoring example
   - Before/after architecture comparison
   - Implementation patterns and lessons learned
   - Migration guide
   - **Updated:** DDD Phase 8 patterns

### 📦 Context & Dependency Management (3 files)

**12. [Context Hierarchy System](./context-hierarchy-system.md)** ⭐ **CRITICAL**
   - 4-tier context hierarchy (Global → Project → Branch → Task)
   - Context inheritance and propagation
   - Context resolution patterns
   - User-scoped global contexts (multi-tenant)
   - Context delegation and updates
   - Best practices and optimization
   - **Updated:** Python 3.14.0, DDD Phase 8

**13. [Dependency Management Engine Architecture](./dependency-management-engine-architecture.md)**
   - Task dependency resolution
   - Dependency graph calculation
   - Circular dependency detection
   - Priority-based scheduling
   - Performance optimization

**14. [Task Versioning Analysis](./task-versioning-analysis.md)**
   - Task versioning strategy
   - Version history tracking
   - Rollback mechanisms
   - Audit trail implementation

### 🎨 Design Patterns & Best Practices (4 files)

**15. [Design Patterns in Architecture](./design-patterns-in-architecture.md)**
   - Common design patterns used
   - Pattern selection guidelines
   - Implementation examples
   - Anti-patterns to avoid

**16. [Implementation Methodology Pattern](./implementation-methodology-pattern.md)**
   - Standardized implementation approach
   - Step-by-step methodology
   - Quality checkpoints
   - Documentation requirements

**17. [Clean Code Enforcement](./clean-code-enforcement.md)**
   - Code quality standards
   - Clean code principles (DRY, SOLID)
   - Enforcement mechanisms
   - Pre-commit hooks and validation

**18. [Prompt Analyze](./prompt-analyze.md)**
   - Prompt engineering patterns
   - Analysis methodology
   - Optimization techniques
   - Best practices for AI interactions

### 🔧 System Components & Utilities (4 files)

**19. [Claude Hooks Refactoring Architecture](./claude-hooks-refactoring-architecture.md)**
   - Hook system architecture
   - Pre-tool and post-tool hooks
   - Hook execution lifecycle
   - Custom hook development
   - File: `.claude/hooks/pre_tool_use.py`, `.claude/hooks/post_tool_use.py`

**20. [Session Type Detection](./session-type-detection.md)**
   - Principal vs Sub-agent session detection
   - Session initialization patterns
   - Context loading strategies
   - Agent role identification

**21. [Toast Notification Architecture](./toast-notification-architecture.md)**
   - UI notification system design
   - Real-time notification delivery
   - Priority and categorization
   - Frontend integration patterns

**22. [Architecture (Legacy)](./architecture.md)**
   - Historical architecture documentation
   - System evolution reference
   - Migration history
   - **Note:** Consider consolidating with system-architecture-overview.md

### 📚 Migration & Repository Patterns (2 files)

**23. [Repository Pagination Migration Guide](./repository-pagination-migration-guide.md)**
   - Pagination implementation patterns
   - Migration from offset to cursor-based
   - Performance optimization
   - Clean architecture notes
   - **Updated:** DDD Phase 8 patterns

**24. [Deprecated Agent Mappings](./deprecated-agent-mappings.md)**
   - Historical agent assignments
   - Migration from old to new agents
   - Breaking changes documentation
   - **Note:** Consider moving to `migration-guides/`

### 🐛 Issues & Problem Analysis (2 files)

**25. [Initial Problem](./initial-problem.md)**
   - Project genesis and problem statement
   - Original requirements and challenges
   - Solution architecture overview
   - **Note:** Consider moving to `issues/`

**26. [Index (This File)](./index.md)**
   - Complete documentation index
   - Navigation and cross-references
   - Recent updates and changelog

---

## Consolidated Documents Summary

### Phase 1: Database Timestamp Consolidation ✅
**Replaced 6 files with 1:**
- ❌ `database-timestamp-standardization-summary.md` → `.obsolete`
- ❌ `timestamp-management-architectural-analysis.md` → `.obsolete`
- ❌ `database-schema-timestamp-alignment-verification.md` → `.obsolete`
- ❌ `timestamp-query-optimization-analysis.md` → `.obsolete`
- ❌ `database-initialization-enhancement.md` → `.obsolete`
- ❌ `database-session-handling-optimization.md` → `.obsolete`
- ✅ **NEW:** `unified-timestamp-architecture.md` (750 lines, 46% content reduction)

### Phase 2: MCP Injection Consolidation ✅
**Replaced 4 files with 1:**
- ❌ `mcp-auto-injection-architecture.md` (1,688 lines) → `.obsolete`
- ❌ `real-time-context-injection-system.md` → `.obsolete`
- ❌ `real-time-injection-system.md` → `.obsolete`
- ❌ `mcp-injection-task-dependencies.md` → `.obsolete`
- ✅ **NEW:** `mcp-injection-architecture.md` (1,308 lines, 50% content reduction)

### Phase 3: Agent System Consolidation ✅
**Replaced 3 files with 1:**
- ❌ `agent-delegation-fix.md` → `.obsolete`
- ❌ `agent-orchestration-architecture.md` → `.obsolete`
- ❌ `sub-agent-instructions.md` → `.obsolete`
- ✅ **NEW:** `agent-system-architecture.md` (comprehensive, 55% duplicate elimination)

**Total Consolidation:** 36 files → 26 files (28% reduction, zero content loss)

---

## Related Documentation

### Specialized Architecture Documentation

**Authentication System:**
- [ai_docs/authentication/](../authentication/) - Authentication architecture, token security, Keycloak integration

**Context Management:**
- [ai_docs/context-system/](../context-system/) - Hierarchical context implementation, inheritance patterns, context update strategies

**Development Guides:**
- [ai_docs/development-guides/](../development-guides/) - Agent interaction patterns, capability matrices, optimization analysis, role-based assignments, DDD compliance

**API Integration:**
- [ai_docs/api-integration/](../api-integration/) - MCP server architecture, parameter resolution, controller implementation guides

**Testing & QA:**
- [ai_docs/testing-qa/](../testing-qa/) - Testing strategies, frameworks, test organization

**Setup & Configuration:**
- [ai_docs/setup-guides/](../setup-guides/) - Installation guides, environment setup, configuration

**Operations:**
- [ai_docs/operations/](../operations/) - Deployment, maintenance, Python 3.14.0 installation guide

**Troubleshooting:**
- [ai_docs/troubleshooting-guides/](../troubleshooting-guides/) - Issue resolution, debugging guides

**Migration:**
- [ai_docs/migration-guides/](../migration-guides/) - Version upgrade guides, breaking changes

**Issues:**
- [ai_docs/issues/](../issues/) - Known issues, bug reports, resolutions

**Reports & Status:**
- [ai_docs/reports-status/](../reports-status/) - Status reports, analysis documents, reviews

---

## Key Architectural Decisions

### Domain-Driven Design (DDD) Phase 8 Complete

**Decision:** Strict layer separation with clear boundaries and rich domain models.

**Layers:**
- **Domain Layer:** Business logic, entities, value objects, domain services
- **Application Layer:** Use cases, facades, DTOs, event handlers
- **Infrastructure Layer:** Database, external services, repositories, event system
- **Interface Layer:** MCP controllers, HTTP endpoints, UI components

**Benefits:**
- Maintainable and testable code
- Clear separation of concerns
- Rich domain models with business logic
- Flexible infrastructure swapping

**Status:** Phase 8 Complete (2025-10-16)

### 4-Tier Context Hierarchy

**Decision:** Hierarchical context system with automatic inheritance.

**Structure:**
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```

**Key Features:**
- User-scoped global contexts (multi-tenant isolation)
- Automatic context inheritance down the hierarchy
- Context delegation and propagation
- Efficient data sharing across levels

**Benefits:**
- Clear scope boundaries and data isolation
- Reduced duplication through inheritance
- Multi-tenant support with complete isolation
- Efficient context resolution with caching

### Agent Orchestration Architecture

**Decision:** 33 specialized agents with dynamic loading and token-efficient delegation.

**Key Components:**
- Master Orchestrator Agent (supreme conductor)
- 33 Specialized Agents (domain experts)
- MCP Task Management System (95% token savings)
- Dynamic Tool Enforcement v2.0 (security)

**Benefits:**
- 95% token savings through MCP task delegation
- Specialized expertise for different tasks
- Dynamic tool permissions (security)
- Parallel execution capabilities
- Intelligent work distribution

### MCP Injection System

**Decision:** Comprehensive auto-injection and real-time context system.

**Key Features:**
- Auto-injection at session start
- Real-time context updates during execution
- Post-tool context synchronization
- Task dependency integration
- 98% confidence, production-ready

**Benefits:**
- Automatic context loading (no manual work)
- Real-time synchronization
- Performance optimization through caching
- Error resilience with fallback strategies

---

## Technology Stack (Current)

### Backend
- **Language:** Python 3.14.0+
- **Framework:** FastMCP 2.0, FastAPI
- **ORM:** SQLAlchemy with DDD entities
- **Database:** PostgreSQL (production), SQLite (dev)
- **Architecture:** DDD Phase 8 Complete
- **Event System:** EventQueue, EventBus, EventWorker

### Frontend
- **Framework:** React 19.x
- **Build Tool:** Vite 7.x
- **Language:** TypeScript
- **State Management:** React Context, custom hooks
- **UI Components:** shadcn/ui components

### Infrastructure
- **Containerization:** Docker, docker-compose
- **Authentication:** Keycloak (source of truth)
- **API Protocol:** MCP (Model Context Protocol)
- **Caching:** Redis (optional)

---

## Implementation Guidelines

### Adding New Features

1. **Start with Domain Model**
   - Define entities, value objects, domain services
   - Implement business logic in domain layer
   - Follow DDD Phase 8 patterns

2. **Define Use Cases**
   - Create application services and use case handlers
   - Implement DTOs and facades
   - Add event handlers if needed

3. **Implement Infrastructure**
   - Add repositories for data access
   - Integrate external services
   - Configure Event System integration

4. **Create Interface Layer**
   - Build MCP controllers with proper parameter handling
   - Create HTTP endpoints if needed
   - Add UI components

5. **Add Comprehensive Tests**
   - Unit tests per layer (domain, application, infrastructure)
   - Integration tests for workflows
   - E2E tests for critical paths

6. **Update Documentation**
   - Add to appropriate documentation folder
   - Update cross-references
   - Include code examples with line numbers

### Modifying Existing Components

1. **Maintain DDD Boundaries**
   - Respect layer separation
   - Keep domain logic in domain layer
   - Use dependency injection

2. **Follow Established Patterns**
   - Use existing architectural patterns consistently
   - Reference design-patterns-in-architecture.md
   - Apply clean code principles

3. **Update Related Documentation**
   - Keep all documentation synchronized
   - Update cross-references
   - Add to CHANGELOG.md

4. **Create Migration Guides**
   - Document breaking changes
   - Provide upgrade paths
   - Include migration scripts if needed

5. **Test Thoroughly**
   - Ensure no regressions
   - Add new tests for changes
   - Verify E2E workflows

### MCP Controller Development

**See:**
- [MCP Integration Documentation](../api-integration/)
- [MCP Injection Architecture](./mcp-injection-architecture.md)
- [System Architecture Overview](./system-architecture-overview.md)

**Best Practices:**
- Use proper parameter type conversion
- Implement error handling and validation
- Follow DDD patterns in controller layer
- Add comprehensive logging

---

## Best Practices

### Code Organization
- **One class per file** with clear single responsibility
- **Clear module structure** following DDD layers
- **Descriptive naming** that reflects domain concepts
- **Comprehensive docstrings** with examples and usage

### Testing Strategy
- **Unit tests per layer** with appropriate mocking (pytest)
- **Integration tests for workflows** and cross-layer interactions
- **E2E tests for critical paths** and user journeys
- **Performance benchmarks** for optimization validation
- **Test location:** `/home/daihungpham/__projects__/4genthub/agenthub_main/src/tests/`

### Documentation Standards
- **Keep documentation current** with code changes
- **Include practical examples** with file references and line numbers
- **Explain architectural decisions** and trade-offs
- **Cross-reference related documents** for comprehensive understanding
- **Update CHANGELOG.md** for all project changes
- **Update TEST-CHANGELOG.md** for all test changes

### File References
- **Always use specific line numbers:** `file.py:23-35` not just `file.py`
- **Include function/method names:** `file.py:23-35 (functionName method)`
- **Provide context:** Explain what the referenced code does
- **Update when code changes:** Keep line numbers accurate

---

## Recent Updates

### 2025-10-16: MAJOR CONSOLIDATION ⭐
- 🧹 **File Count Reduction:** 36 → 26 files (28% reduction, zero content loss)
- ✅ **Phase 1 Complete:** Unified Timestamp Architecture (6 → 1 file)
  - Consolidated all database timestamp documentation
  - Updated to Python 3.14.0+ and DDD Phase 8 Complete
  - Single source of truth for timestamp management
- ✅ **Phase 2 Complete:** MCP Injection Architecture (4 → 1 file)
  - Consolidated all MCP injection system documentation
  - Eliminated 50% duplicate content
  - Updated to Python 3.14.0+ and DDD Phase 8
  - References CLAUDE.md for Dynamic Tool Enforcement v2.0
- ✅ **Phase 3 Complete:** Agent System Architecture (3 → 1 file)
  - Consolidated agent delegation, orchestration, and instructions
  - Complete 33 specialized agents directory
  - Updated to Python 3.14.0 and DDD Phase 8
  - Dynamic Tool Enforcement v2.0 fully documented
- ✅ **Updated index.md** for accurate file count and organization
- ✅ **All content preserved** while eliminating duplication

### 2025-09-12: Agent Architecture Updates
- Major agent architecture consolidation
- 33 specialized agents (updated from 60+ count)
- Enhanced agent assignment decision trees

### 2025-09-11: Previous Reorganization
- Moved specialized docs to appropriate folders
- Improved navigation and cross-references
- Authentication, Context System, Development Guides separation

### 2025-09-09: DDD Phase 8 Completion
- Completed Domain-Driven Design Phase 8
- Full layer separation implemented
- Rich domain models with business logic

---

## Quick Links

### Core Documentation
- [Project README](../../README.md) - Main project overview
- [CHANGELOG](../../CHANGELOG.md) - Project change history
- [TEST-CHANGELOG](../../TEST-CHANGELOG.md) - Test changes history
- [CLAUDE.md](../../CLAUDE.md) - AI agent instructions (authoritative)
- [CLAUDE.local.md](../../CLAUDE.local.md) - Local AI agent rules

### Consolidated Core Architecture (This Folder)
- [Unified Timestamp Architecture](./unified-timestamp-architecture.md) - Complete timestamp management
- [MCP Injection Architecture](./mcp-injection-architecture.md) - Complete injection system
- [Agent System Architecture](./agent-system-architecture.md) - Complete agent architecture
- [System Architecture Overview](./system-architecture-overview.md) - High-level design
- [Domain-Driven Design Layers](./domain-driven-design-layers.md) - DDD Phase 8
- [Context Hierarchy System](./context-hierarchy-system.md) - 4-tier context

### Specialized Architecture
- [Authentication System](../authentication/) - Auth architecture and security
- [Context Management](../context-system/) - Hierarchical context implementation
- [Development Guides](../development-guides/) - Implementation patterns and guides
- [API Integration](../api-integration/) - MCP framework and API design
- [Testing Guide](../testing-qa/) - Testing strategies and frameworks
- [Setup Guides](../setup-guides/) - Installation and configuration
- [Operations](../operations/) - Deployment, maintenance, Python 3.14.0 guide
- [Troubleshooting](../troubleshooting-guides/) - Issue resolution

### Project Management
- [Issues](../issues/) - Known issues and resolutions
- [Migration Guides](../migration-guides/) - Version upgrade guides
- [Reports & Status](../reports-status/) - Status reports and analysis

---

## Document Maintenance

### Updating This Index
When adding/removing files in core-architecture/:
1. Update the file count in the header
2. Add/remove the document in the appropriate category
3. Update the consolidation summary if merging files
4. Add update note in "Recent Updates" section
5. Update cross-references if needed
6. Run: `python .claude/hooks/utils/docs_indexer.py` to regenerate `index.json`

### Documentation Standards for This Folder
- **All documents must be updated** to Python 3.14.0 and DDD Phase 8
- **Include specific file references** with line numbers
- **Cross-reference related documents** for comprehensive understanding
- **Mark obsolete files** with `.obsolete` extension (never delete)
- **Update CHANGELOG.md** for all architecture changes

---

*This core architecture documentation provides the foundation for understanding the agenthub system. All documents have been consolidated to eliminate duplication while preserving all unique content. For specific implementation details, refer to the specialized documentation folders listed above.*

**Current Status:** 26 active documents, all updated to Python 3.14.0 and DDD Phase 8 Complete.
