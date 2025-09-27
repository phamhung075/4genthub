# agenthub System Architecture

## Overview

agenthub is a multi-project AI orchestration platform built using Domain-Driven Design (DDD) principles with a 4-tier hierarchical context system. The platform enables autonomous AI agents to manage complex software development workflows across multiple projects and team contexts.

## Core Architecture Principles

### 1. Domain-Driven Design (DDD)
- **Bounded Contexts**: Clear separation between task management, agent orchestration, and context management domains
- **Aggregates**: Task, Project, GitBranch, and Context as primary aggregates
- **Domain Services**: Business logic encapsulated in domain services
- **Application Services**: Orchestrate domain operations and external integrations

### 2. 4-Tier Hierarchical Context System
```
GLOBAL (Organization-wide patterns)
   ↓ inherits to
PROJECT (Business domain context)  
   ↓ inherits to
BRANCH (Feature/work branch context)
   ↓ inherits to
TASK (Specific work unit context)
```

### 3. MCP (Model Context Protocol) Integration
- FastMCP framework for tool definitions
- Type-safe parameter validation
- Async/await support for performance
- Comprehensive error handling

## System Components

### Core Domains

#### Task Management Domain
- **Entities**: Task, Subtask, TaskContext
- **Value Objects**: TaskStatus, Priority, CompletionSummary
- **Services**: TaskCompletionService, TaskWorkflowGuidance
- **Repositories**: TaskRepository, SubtaskRepository

#### Project Management Domain
- **Entities**: Project, GitBranch
- **Value Objects**: ProjectMetadata, BranchConfiguration
- **Services**: ProjectHealthService, BranchStatisticsService
- **Repositories**: ProjectRepository, GitBranchRepository

#### Agent Orchestration Domain
- **Entities**: Agent, AgentAssignment
- **Value Objects**: AgentCapabilities, AssignmentConfiguration
- **Services**: AgentLoadBalancer, AgentSelectionService
- **Repositories**: AgentRepository

#### Context Management Domain
- **Entities**: HierarchicalContext, ContextDelegation
- **Value Objects**: ContextData, DelegationRequest
- **Services**: ContextInheritanceService, ContextDelegationService, ContextCacheService
- **Repositories**: HierarchicalContextRepository

### Application Layer

#### Facades
- **TaskApplicationFacade**: Orchestrates task operations
- **ProjectApplicationFacade**: Manages project lifecycle
- **AgentApplicationFacade**: Handles agent assignments
- **HierarchicalContextFacade**: Manages context hierarchy

#### MCP Controllers (Modular Architecture)
- **TaskMCPController**: Modular task management with CRUD handlers, workflow guidance, and validation (2377→324 lines)
- **SubtaskMCPController**: Modular subtask management with automatic parent progress tracking (1407→23 lines)
- **ProjectMCPController**: Modular project management with health checks and maintenance operations (435→23 lines)
- **GitBranchMCPController**: Modular branch management with agent assignment and advanced operations (834→23 lines)
- **AgentMCPController**: Modular agent orchestration with assignment and rebalancing handlers (402→23 lines)
- **ProgressToolsController**: Modular progress tracking with Vision System Phase 2 integration (376→23 lines)
- **UnifiedContextController**: Modular context management with hierarchical operations (362→23 lines)
- **WorkflowHintEnhancer**: Modular workflow enhancement with AI-powered guidance services (1068→23 lines)

**Modular Pattern**: All controllers use factory-based architecture with specialized handlers, validators, and services for 93% code size reduction while maintaining 100% backward compatibility.

### Infrastructure Layer

#### Persistence - Dual PostgreSQL Architecture
- **SQLAlchemy ORM**: Object-relational mapping with dual database support
- **Production Database**: Supabase cloud PostgreSQL (managed, globally distributed)
- **Development Database**: PostgreSQL Docker container (full feature parity)
- **Database Adapters**: PostgreSQL optimized for both local and cloud deployment
- **Migration Management**: Alembic for schema versioning across both environments

#### Caching
- **ContextCacheService**: LRU cache with dependency tracking
- **Cache Invalidation**: Automatic invalidation on context changes
- **Performance Monitoring**: Cache hit/miss metrics

#### External Integrations
- **MCP Protocol**: Tool registration and execution
- **Authentication**: Bearer token validation
- **Compliance**: Operation validation and audit trails

## Data Flow Architecture

### Request Processing Flow
```
AI Agent → MCP Tool → Controller → Facade → Domain Service → Repository → Database
                                      ↓
                              Context Resolution
                                      ↓
                              Business Logic
                                      ↓
                              Response Enrichment
```

### Context Resolution Flow
```
Task Context Request → Branch Context → Project Context → Global Context
                           ↓
                    Inheritance Chain
                           ↓
                    Merged Context Data
                           ↓
                    Cached for Performance
```

## Database Architecture

### Dual PostgreSQL Setup

agenthub uses a dual PostgreSQL architecture designed for optimal development-production parity:

```
Production Environment:
  ┌─────────────────────────────────┐
  │     Supabase Cloud PostgreSQL   │
  │  • Fully managed service        │
  │  • Global distribution          │
  │  • Automatic backups           │
  │  • Real-time capabilities       │
  │  • Built-in auth integration    │
  └─────────────────────────────────┘

Development Environment:
  ┌─────────────────────────────────┐
  │   PostgreSQL Docker Container   │
  │  • Full feature parity          │
  │  • Local development speed      │
  │  • Isolated environment        │
  │  • Same PostgreSQL version      │
  │  • Consistent schema           │
  └─────────────────────────────────┘
```

### Database Configuration Logic

```python
if DATABASE_TYPE == "supabase":
    # Production: Use Supabase managed PostgreSQL
    # Optimized for global scale, real-time features
    connection = supabase_postgresql_connection
elif DATABASE_TYPE == "postgresql":
    # Development: Use Docker PostgreSQL
    # Full feature parity with production
    connection = docker_postgresql_connection
else:
    # PostgreSQL configuration
    connection = sqlite_connection
```

### Schema Synchronization

- **Single Schema**: Both environments use identical PostgreSQL schema
- **Migration Consistency**: Alembic migrations work across both databases
- **Feature Parity**: All PostgreSQL features available in both environments
- **Testing**: Tests use PostgreSQL to match production behavior

## Key Design Patterns

### 1. Facade Pattern
- Simplified interfaces for complex domain operations
- Coordination of multiple domain services
- Transaction boundary management

### 2. Repository Pattern
- Abstraction over data persistence
- Domain-focused query interfaces
- Testability through interface abstractions

### 3. Strategy Pattern
- Agent selection strategies
- Context delegation strategies
- Workflow guidance strategies

### 4. Observer Pattern
- Context change propagation
- Cache invalidation events
- Audit trail generation

### 5. Factory Pattern
- Facade creation with proper dependencies
- Context creation based on hierarchy level
- Agent instantiation with capabilities

## Performance Considerations

### Caching Strategy
- **Context Cache**: LRU cache with dependency tracking
- **Agent Assignment Cache**: Cached agent-branch relationships
- **Workflow Guidance Cache**: Cached decision trees

### Database Optimization
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Selective loading with SQLAlchemy relationships
- **Index Strategy**: Optimized indexes for common query patterns

### Async Processing
- **Non-blocking Operations**: Async/await throughout the stack
- **Background Tasks**: Deferred processing for expensive operations
- **Resource Management**: Proper cleanup of async resources

## Security Architecture

### Authentication & Authorization
- **Bearer Token Authentication**: Stateless token validation
- **Role-based Access Control**: Project and task-level permissions
- **Audit Trails**: Comprehensive operation logging

### Data Protection
- **Input Validation**: Type-safe parameter validation
- **SQL Injection Prevention**: Parameterized queries with SQLAlchemy
- **Secrets Management**: Environment-based configuration

### Compliance
- **Operation Validation**: Pre-execution compliance checks
- **Audit Logging**: Immutable audit trail
- **Data Retention**: Configurable retention policies

## Deployment Architecture

### Container Strategy
- **Docker Containerization**: Consistent deployment environments
- **Multi-stage Builds**: Optimized container images
- **Health Checks**: Container health monitoring

### Database Configuration
- **Primary**: PostgreSQL with JSONB for all environments (development, production)
- **PostgreSQL**: Full support for local and cloud deployments
- **Testing**: Isolated PostgreSQL test databases

### Monitoring & Observability
- **Health Endpoints**: System health monitoring
- **Metrics Collection**: Performance and usage metrics
- **Error Tracking**: Comprehensive error logging

## Scalability Considerations

### Horizontal Scaling
- **Stateless Design**: No server-side session state
- **Database Scaling**: Read replicas and connection pooling
- **Cache Distribution**: Distributed caching strategies

### Vertical Scaling
- **Resource Optimization**: Efficient memory and CPU usage
- **Database Tuning**: Query optimization and indexing
- **Caching Efficiency**: Intelligent cache eviction policies

## Future Architecture Evolution

### Planned Enhancements
- **Event Sourcing**: Complete audit trail with event replay
- **CQRS Pattern**: Separated read/write models for performance
- **Microservices**: Domain-based service decomposition
- **Real-time Updates**: WebSocket-based real-time notifications

### Extension Points
- **Plugin Architecture**: Dynamic tool registration
- **Custom Workflows**: User-defined workflow patterns
- **Third-party Integrations**: External system connectors
- **AI Model Integration**: Direct LLM integration capabilities

## Conclusion

The agenthub architecture provides a robust, scalable foundation for AI-driven project management. The combination of DDD principles, hierarchical context management, and MCP integration enables sophisticated autonomous workflows while maintaining clean separation of concerns and high testability.

The architecture is designed to evolve with changing requirements while maintaining backward compatibility and system stability.