# Core Architecture Documentation

## Overview

This directory contains the **core architectural design documentation** for the agenthub system, focusing on fundamental system design, technical architecture, and foundational patterns.

**📁 Reorganization Complete (2025-09-11)**: This folder has been cleaned and reorganized from 48 files to 6 core files. Specialized documentation has been moved to appropriate folders:
- **Authentication**: [ai_docs/authentication/](../authentication/)
- **Context System**: [ai_docs/context-system/](../context-system/)
- **Agent Architecture**: [ai_docs/development-guides/](../development-guides/) (agent-*.md files)
- **DDD Patterns**: [ai_docs/development-guides/](../development-guides/) (DDD-*.md files)
- **MCP Integration**: [ai_docs/api-integration/](../api-integration/) (MCP-*.md files)
- **Controller Architecture**: [ai_docs/development-guides/](../development-guides/) (controller-*.md files)
- **Repository Patterns**: [ai_docs/development-guides/](../development-guides/) (repository-*.md files)
- **Issues & Reports**: [ai_docs/issues/](../issues/) and [ai_docs/reports-status/](../reports-status/)

## Core Documents

### 📋 Product Requirements & Architecture

1. **[Product Requirements Document (PRD)](./PRD.md)** ⭐ **CORE**
   - Complete product vision and requirements
   - 60+ specialized AI agents overview
   - 4-tier context hierarchy design
   - Technical requirements and roadmap
   - Success metrics and compliance standards

2. **[Technical Architecture](./Architecture_Technique.md)** ⭐ **CORE**
   - Domain-Driven Design (DDD) implementation
   - FastMCP 2.0 framework integration
   - Complete system layers and components
   - MCP protocol integration (15+ categories)
   - Vision System architecture (6 phases)
   - Database schema and performance targets

3. **[System Architecture Overview](./architecture.md)** ⭐ **CORE**
   - High-level system design and components
   - Technology stack overview
   - Integration patterns and workflows
   - Service architecture and communication

4. **[Database Architecture](./database-architecture.md)** ⭐ **CORE**
   - Database design patterns and schemas
   - SQLite and PostgreSQL configurations
   - Performance optimization strategies
   - Data modeling and relationships

## Related Documentation

### Specialized Architecture Documentation

**Authentication System**:
- See [ai_docs/authentication/](../authentication/) for authentication architecture, token security, and Keycloak integration

**Context Management**:
- See [ai_docs/context-system/](../context-system/) for hierarchical context implementation, inheritance patterns, and context update strategies

**Agent Architecture**:
- See [ai_docs/development-guides/](../development-guides/) for agent interaction patterns, capability matrices, optimization analysis, and role-based assignments

**Domain-Driven Design**:
- See [ai_docs/development-guides/](../development-guides/) for DDD compliance analysis, domain services, and implementation patterns

**MCP Integration**:
- See [ai_docs/api-integration/](../api-integration/) for MCP server architecture, parameter resolution, and controller implementation guides

**Controller & Repository Patterns**:
- See [ai_docs/development-guides/](../development-guides/) for modular controller architecture, repository switching guides, and refactoring plans

### Cross-Reference Guide

**For Implementation Details**:
- **Agent Development**: [Agent guides in development-guides/](../development-guides/)
- **API Integration**: [MCP integration in api-integration/](../api-integration/)
- **Authentication**: [Auth system in authentication/](../authentication/)
- **Context Management**: [Context system in context-system/](../context-system/)
- **Testing**: [Testing guides in testing-qa/](../testing-qa/)
- **Setup & Operations**: [Setup guides](../setup-guides/) and [Operations](../operations/)
- **Troubleshooting**: [Issue resolution in troubleshooting-guides/](../troubleshooting-guides/)
- **Migration**: [Migration guides in migration-guides/](../migration-guides/)

## Key Architectural Decisions

### Domain-Driven Design (DDD)

**Decision**: Strict layer separation with clear boundaries and rich domain models.

**Layers**:
- **Domain**: Business logic, entities, value objects, domain services
- **Application**: Use cases, facades, DTOs, event handlers
- **Infrastructure**: Database, external services, repositories
- **Interface**: MCP controllers, HTTP endpoints, UI components

**Benefits**: Maintainable code, clear separation of concerns, testable architecture

### 4-Tier Context Hierarchy

**Decision**: Hierarchical context system with automatic inheritance.

**Structure**:
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```

**Benefits**:
- Clear scope boundaries and data isolation
- Automatic context inheritance and delegation
- Efficient data sharing across hierarchy levels
- Multi-tenant support with user-scoped global contexts

### Agent Orchestration Architecture

**Decision**: 60+ specialized agents with dynamic loading and capability-based assignment.

**Benefits**:
- Specialized expertise for different tasks
- Parallel execution and workflow optimization
- Intelligent work distribution and load balancing
- Modular and extensible agent system

## Implementation Guidelines

### Adding New Features

1. **Start with Domain Model**: Define entities, value objects, and domain services
2. **Define Use Cases**: Create application services and use case handlers
3. **Implement Infrastructure**: Add repositories, external service integrations
4. **Create Interface Layer**: Build MCP controllers and API endpoints
5. **Add Comprehensive Tests**: Unit, integration, and E2E tests
6. **Update Documentation**: Keep architecture documentation current

### Modifying Existing Components

1. **Maintain DDD Boundaries**: Respect layer separation and domain integrity
2. **Follow Established Patterns**: Use existing architectural patterns consistently
3. **Update Related Documentation**: Keep all documentation synchronized
4. **Create Migration Guides**: Document breaking changes and upgrade paths
5. **Test Thoroughly**: Ensure changes don't break existing functionality

### MCP Controller Development

For MCP controller patterns and implementation guidelines, see:
- [MCP Integration Documentation](../api-integration/)
- [Controller Architecture Guides](../development-guides/)
- [Parameter Resolution Patterns](../api-integration/)

## Best Practices

### Code Organization
- **One class per file** with clear responsibility
- **Clear module structure** following DDD layers
- **Descriptive naming** that reflects domain concepts
- **Comprehensive docstrings** with examples and context

### Testing Strategy
- **Unit tests per layer** with appropriate mocking
- **Integration tests for workflows** and cross-layer interactions
- **E2E tests for critical paths** and user journeys
- **Performance benchmarks** for optimization validation

### Documentation
- **Keep documentation current** with code changes
- **Include practical examples** and usage patterns
- **Explain architectural decisions** and trade-offs
- **Cross-reference related documents** for comprehensive understanding

## Recent Updates

- **2025-09-11**: 🧹 **MAJOR REORGANIZATION** - Cleaned and reorganized core-architecture folder
  - **Reduced from 48 files to 6 core files** (87% reduction)
  - **Moved specialized docs to appropriate folders**:
    - Authentication → [ai_docs/authentication/](../authentication/)
    - Context System → [ai_docs/context-system/](../context-system/)
    - Agent Architecture → [ai_docs/development-guides/](../development-guides/)
    - DDD Patterns → [ai_docs/development-guides/](../development-guides/)
    - MCP Integration → [ai_docs/api-integration/](../api-integration/)
    - Controller/Repository Patterns → [ai_docs/development-guides/](../development-guides/)
  - **Updated cross-references** and navigation
  - **Maintained all content** while improving organization
- **2025-09-09**: Major agent architecture consolidation (60+ agents)
- **2025-09-03**: Context Update Implementation Technical Specification
- **2025-09-03**: MCP parameter type resolution and controller fixes
- **2025-09-02**: Updated context hierarchy documentation

## Quick Links

### Core Documentation
- [Project README](../../README.md) - Main project overview
- [CHANGELOG](../../CHANGELOG.md) - Project change history
- [CLAUDE.md](../../CLAUDE.md) - AI agent instructions

### Specialized Architecture
- [Authentication System](../authentication/) - Auth architecture and security
- [Context Management](../context-system/) - Hierarchical context implementation
- [Development Guides](../development-guides/) - Agent, DDD, controller patterns
- [API Integration](../api-integration/) - MCP framework and API design
- [Testing Guide](../testing-qa/) - Testing strategies and frameworks
- [Setup Guides](../setup-guides/) - Installation and configuration
- [Operations](../operations/) - Deployment and maintenance
- [Troubleshooting](../troubleshooting-guides/) - Issue resolution

### Project Management
- [Issues](../issues/) - Known issues and resolutions
- [Migration Guides](../migration-guides/) - Version upgrade guides
- [Reports & Status](../reports-status/) - Status reports and analysis

---

*This core architecture documentation provides the foundation for understanding the agenthub system. For specific implementation details, refer to the specialized documentation folders listed above.*