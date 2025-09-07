# Architecture Design Documentation

## Overview

This directory contains architectural design documentation for the DhafnckMCP system, covering design patterns, implementation guidelines, and technical architecture decisions.

## Documents

### Core Architecture

1. **[Domain-Driven Design Implementation](./ddd-architecture.md)**
   - DDD patterns and principles
   - Layer separation and boundaries
   - Entity and value object design

2. **[System Architecture Overview](./system-architecture.md)**
   - High-level system design
   - Component interactions
   - Technology stack

### MCP Framework

3. **[MCP Parameter Type Resolution Guide](./mcp-parameter-type-resolution-guide.md)** ⭐ NEW
   - Complete guide for handling MCP parameter type display issues
   - Standardized pattern for MCP tool controllers
   - Type conversion strategies and best practices
   - Generic implementation template

4. **[MCP Controller Implementation Changes](./mcp-controller-implementation-changes.md)** ⭐ NEW
   - Detailed documentation of fixes applied to task, compliance, and context controllers
   - Before/after comparisons
   - Migration guide for other controllers
   - Testing and verification procedures

### Design Patterns

5. **[Factory Pattern Implementation](./factory-pattern.md)**
   - Factory pattern usage across the system
   - Repository factories
   - Service factories

6. **[Repository Pattern](./repository-pattern.md)**
   - Repository abstraction design
   - ORM integration
   - Mock implementations

### Context Management

7. **[Hierarchical Context System](./hierarchical-context.md)**
   - 4-tier context hierarchy (Global → Project → Branch → Task)
   - Context inheritance and delegation
   - Vision system integration

8. **[Context Update Implementation Technical Specification](./CONTEXT_UPDATE_IMPLEMENTATION.md)** ⭐ NEW
   - Comprehensive technical specification for safe, atomic, and intelligent context update patterns
   - Context Update API Design with 5 distinct update operation types (REPLACE, MERGE, APPEND, PREPEND, ATOMIC)
   - 7-step Agent Context Update Workflow for safe updates without data loss
   - Field-specific merge strategies with conflict resolution for each context level
   - Implementation examples in Python (backend) and TypeScript (frontend)
   - MCP tool usage examples for AI agents with proper error handling
   - Concurrency handling with optimistic locking and retry strategies
   - Performance optimization with batch processing and intelligent caching
   - Complete error handling with recovery strategies and audit trail

9. **[Context Synchronization](./context-synchronization.md)**
   - Cross-level context updates
   - Propagation strategies
   - Conflict resolution

### API Design

10. **[RESTful API Design](./restful-api.md)**
    - API endpoint structure
    - Request/response formats
    - Error handling patterns

11. **[MCP Tool Interface Design](./mcp-tool-interface.md)**
    - Tool registration patterns
    - Parameter handling
    - Response standardization

## Key Architectural Decisions

### MCP Parameter Handling (2025-09-03)

**Problem:** MCP framework shows Union and Optional types as "unknown" in tool interfaces.

**Solution:** Use simple base types in signatures with type conversion in function body.

**Pattern:**
```python
# Signature: Simple types
param: Annotated[str, Field(description="[OPTIONAL] ...")] = None

# Body: Handle flexible inputs
if param and ',' in param:
    param = param.split(',')
```

### Domain-Driven Design

**Decision:** Strict layer separation with clear boundaries.

**Layers:**
- Domain: Business logic and entities
- Application: Use cases and orchestration
- Infrastructure: External concerns
- Interface: User/system interaction

### Context Hierarchy

**Decision:** 4-tier hierarchical context system with inheritance.

**Benefits:**
- Clear scope boundaries
- Automatic inheritance
- Efficient data sharing
- Multi-tenant support

## Implementation Guidelines

### Creating New MCP Controllers

Follow the pattern documented in [MCP Parameter Type Resolution Guide](./mcp-parameter-type-resolution-guide.md):

1. Create separate description module
2. Use simple types in signatures
3. Add "[OPTIONAL]" to descriptions
4. Implement type conversion in body
5. Test parameter display

### Adding New Features

1. Start with domain model
2. Define application use cases
3. Implement infrastructure
4. Create interface layer
5. Add comprehensive tests

### Modifying Existing Components

1. Maintain layer boundaries
2. Follow existing patterns
3. Update documentation
4. Add migration guides
5. Test thoroughly

## Best Practices

### Code Organization
- One class per file
- Clear module structure
- Descriptive naming
- Comprehensive docstrings

### Testing Strategy
- Unit tests per layer
- Integration tests for workflows
- E2E tests for critical paths
- Performance benchmarks

### Documentation
- Keep docs next to code
- Update with changes
- Include examples
- Explain decisions

## Recent Updates

- **2025-09-03**: Added Context Update Implementation Technical Specification with comprehensive update patterns and strategies
- **2025-09-03**: Added MCP parameter type resolution documentation
- **2025-09-03**: Documented controller implementation fixes
- **2025-09-02**: Updated context hierarchy documentation
- **2025-09-01**: Added factory pattern documentation

## Quick Links

- [Project README](../../README.md)
- [API Documentation](../api-integration/index.md)
- [Testing Guide](../testing-qa/index.md)
- [Setup Guide](../setup-guides/index.md)

---

*For questions or updates to these documents, please follow the contribution guidelines in the main README.*