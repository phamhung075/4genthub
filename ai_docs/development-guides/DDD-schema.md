# DDD Architecture Schema - Detailed Flow Documentation

**Version**: 2.0.0 | **Last Updated**: 2025-08-29 | **Status**: Production Ready with Enhanced Authentication

---

## System Architecture Overview

### Complete System Flow

| Layer | Components | Responsibilities |
|-------|-----------|------------------|
| **MCP Client** | Claude, VS Code, Other MCP Clients | Initiate requests via MCP protocol |
| **MCP Protocol Transport** | WebSocket, HTTP/2, Keep-Alive, Request ID Tracking | Connection management, protocol handling |
| **FastMCP Server Entry** | Server instance, Environment config, Tool registration, Middleware | Request routing, initial processing |
| **Authentication & Authorization** | JWT validation (RS256/HS256), User context, RBAC, Rate limiting, Audit trail | Security enforcement, multi-tenant isolation |
| **INTERFACE LAYER** | MCP Controllers (Task, Project, Context, Agent, Rule, Compliance) | Parameter validation, DTO construction, error handling |
| **APPLICATION LAYER** | Facades & Use Cases | Transaction management, use case orchestration, cross-cutting concerns |
| **DOMAIN LAYER** | Entities, Value Objects, Business Rules, Domain Services, Events | Core business logic, invariant enforcement |
| **INFRASTRUCTURE LAYER** | Repositories, Database, Cache, External Services, Event Bus | Data persistence, external integrations |

**Flow**: MCP Client → Transport → FastMCP Server → Auth → Interface → Application → Domain → Infrastructure → Response back through layers

### Authentication Pipeline

| Stage | Process | Outputs |
|-------|---------|---------|
| **Token Extraction** | Extract JWT from headers | Raw token |
| **Signature Verification** | Validate RS256/HS256 signature | Verified token |
| **Claims Validation** | Check expiry, issuer, audience | Valid claims |
| **User Context** | Extract user_id, org/tenant_id, session metadata | User context object |
| **MVP Mode** | If AUTH_ENABLED=false: bypass auth, use default context | Development context |
| **Authorization** | Load permissions, check RBAC, validate resources, rate limit | Authorized request |

---

## Detailed Request Flow Sequence

### 1. MCP Tool Request Flow (manage_task example)

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | MCP Client | Send `manage_task(action="create", title="...")` | Request initiated |
| 2 | Transport Layer | Establish WebSocket/HTTP/2, generate request_id | Connection ready |
| 3 | FastMCP Server | Route to TaskController | Controller selected |
| 4 | Auth Middleware | Validate JWT, extract user context | Authorized user |
| 5 | TaskController | Parse parameters, validate types, create TaskCreateDTO | Valid DTO |
| 6 | TaskApplicationFacade | Begin transaction, initialize audit trail | Transaction started |
| 7 | CreateTaskUseCase | Validate business rules, create Task entity | Task entity |
| 8 | Domain Services | Enforce invariants, validate dependencies, emit TaskCreatedEvent | Valid entity + events |
| 9 | TaskRepository | Persist to database, generate UUID | Persisted task |
| 10 | Event Bus | Publish TaskCreatedEvent to subscribers | Event propagated |
| 11 | Facade | Commit transaction, collect events, format response | Response DTO |
| 12 | Controller | Add workflow guidance, serialize to JSON | MCP response |
| 13 | Transport | Send response to client | Complete |

---

## Layer Interaction Flows

### Interface → Application Flow

| Interface Action | Application Response | Data Transformed |
|-----------------|---------------------|------------------|
| **Parameter Parsing** | → Receive structured params | Raw params → Typed params |
| **Type Coercion** | → Accept coerced types | Strings → bool/int/list/UUID |
| **Validation** | → Execute domain validation | Validation errors collected |
| **DTO Construction** | → Receive immutable DTO | Params → Request DTO |
| **Error Handling** | → Map domain exceptions | Domain errors → HTTP errors |

**Pattern**: Controller parses/validates → Creates DTO → Calls Facade → Facade returns Response DTO → Controller serializes to JSON

### Application → Domain Flow

| Application Action | Domain Response | Business Logic |
|-------------------|----------------|----------------|
| **Use Case Invocation** | → Execute business rules | Orchestrate domain operations |
| **Repository Access** | → Load entities | Entity retrieval/persistence |
| **Domain Service Call** | → Apply complex logic | Multi-entity business rules |
| **Event Collection** | → Emit domain events | Track state changes |
| **Transaction Boundary** | → Commit/rollback | Ensure data consistency |

**Pattern**: Facade coordinates use cases → Use cases call domain services → Domain services modify entities → Events emitted → Repositories persist

### Domain → Infrastructure Flow

| Domain Action | Infrastructure Response | Persistence |
|--------------|------------------------|-------------|
| **Entity Save** | → Repository INSERT/UPDATE | Database write |
| **Entity Load** | → Repository SELECT with filters | Database read |
| **Event Publish** | → Event Bus broadcast | Async event delivery |
| **Cache Access** | → Cache hit/miss | Performance optimization |
| **External Call** | → API integration | Third-party services |

**Pattern**: Domain requests persistence → Repository handles DB details → Infrastructure manages connections/transactions

---

## Complete Request/Response Flow

### Detailed Step-by-Step Flow (Task Creation Example)

| # | Layer | Component | Action | Input | Output |
|---|-------|-----------|--------|-------|--------|
| 1 | Transport | WebSocket | Receive request | MCP JSON | Parsed request |
| 2 | Auth | JWTValidator | Validate token | JWT token | User context |
| 3 | Interface | TaskController.create() | Parse parameters | {action, title, ...} | TaskCreateDTO |
| 4 | Application | TaskApplicationFacade.create_task() | Begin transaction | TaskCreateDTO | Transaction started |
| 5 | Application | CreateTaskUseCase.execute() | Load dependencies | Project_id, user_id | Project entity |
| 6 | Domain | Task.create() | Validate + create entity | Title, desc, assignees | Task entity (new) |
| 7 | Domain | TaskStateTransitionService | Initialize status | Task entity | Status=todo |
| 8 | Domain | TaskAssignmentPolicy | Validate assignments | Assignees list | Validated assignments |
| 9 | Domain | Task | Emit TaskCreatedEvent | Task entity | Domain event |
| 10 | Infrastructure | TaskRepository.save() | INSERT to DB | Task entity | Persisted (UUID generated) |
| 11 | Infrastructure | EventBus.publish() | Broadcast event | TaskCreatedEvent | Event queued |
| 12 | Application | TaskApplicationFacade | Commit transaction | All changes | Transaction committed |
| 13 | Application | ResponseSerializer | Format response | Task entity | Response DTO |
| 14 | Interface | WorkflowGuidanceService | Add hints/guidance | Response DTO | Enhanced response |
| 15 | Interface | TaskController | Serialize to JSON | Enhanced response | MCP JSON response |
| 16 | Transport | WebSocket | Send response | MCP JSON | Complete |

**Transaction Span**: Steps 4-12 (begin → commit)
**Event Propagation**: Step 11 (async, after transaction commit)
**Response Time**: Target <100ms for simple operations

---

## Error Flow Sequence

### Error Handling Pipeline

| Error Source | Error Type | Handler | Response | HTTP Status |
|--------------|-----------|---------|----------|-------------|
| **Invalid Parameters** | ValidationError | Interface (Controller) | {error: "Invalid UUID format"} | 400 Bad Request |
| **Auth Failure** | AuthenticationError | Auth Middleware | {error: "Invalid token"} | 401 Unauthorized |
| **Permission Denied** | AuthorizationError | Auth Middleware | {error: "Insufficient permissions"} | 403 Forbidden |
| **Business Rule Violation** | DomainError | Application (Facade) | {error: "Cannot assign inactive agent"} | 422 Unprocessable |
| **Entity Not Found** | NotFoundError | Application (Facade) | {error: "Task not found"} | 404 Not Found |
| **Unique Constraint** | IntegrityError | Infrastructure (Repository) | {error: "Duplicate task title"} | 409 Conflict |
| **Database Error** | DatabaseError | Infrastructure (Repository) | {error: "Database unavailable"} | 503 Service Unavailable |
| **Timeout** | TimeoutError | Application (Facade) | {error: "Operation timeout"} | 504 Gateway Timeout |

**Error Handling Pattern**:
1. Error occurs in any layer
2. Raise specific exception type
3. Bubble up through layers (no catching except at boundaries)
4. Facade catches, logs, rolls back transaction
5. Controller maps to HTTP status + user-friendly message
6. Response includes: error message, error code, trace_id (for debugging)

---

## Event Flow Architecture

### Domain Event Flow

| Stage | Component | Action | Timing |
|-------|-----------|--------|--------|
| **1. Event Creation** | Domain Entity | `self._events.append(TaskCreatedEvent(...))` | During entity modification |
| **2. Event Collection** | Use Case | `events = task.collect_events()` | After domain operations |
| **3. Event Propagation** | Facade | `for event in events: event_bus.publish(event)` | After transaction commit |
| **4. Event Delivery** | Event Bus | Route to registered handlers | Async (non-blocking) |
| **5. Event Handling** | Event Handlers | Execute side effects (notifications, metrics, etc.) | Background processing |

**Event Types**: TaskCreated, TaskUpdated, TaskCompleted, TaskAssigned, AgentRegistered, ProjectCreated, etc.

**Why After Transaction Commit**: Ensures events only published if operation succeeded (no rollback scenarios)

---

## Data Flow Through Layers

### Request Data Transformation

| Stage | Format | Example | Validation Level |
|-------|--------|---------|------------------|
| **MCP Request** | JSON | `{"action":"create","title":"Build auth"}` | None (raw) |
| **Controller Input** | dict | `{action: "create", title: "Build auth"}` | Type checking |
| **Request DTO** | Dataclass | `TaskCreateDTO(action=TaskAction.CREATE, title="Build auth")` | Business validation |
| **Domain Entity** | Entity object | `Task(id=UUID, title="Build auth", status=TaskStatus.TODO)` | Invariant enforcement |
| **DB Record** | SQL row | `INSERT INTO tasks (id, title, status) VALUES (uuid, 'Build auth', 'todo')` | Constraint enforcement |
| **Repository Output** | Entity object | `Task(id=UUID, title="Build auth", status=TaskStatus.TODO)` | Rehydrated entity |
| **Response DTO** | Dataclass | `TaskResponseDTO(task={id, title, status}, workflow_guidance={...})` | None (trusted) |
| **MCP Response** | JSON | `{"task":{"id":"uuid","title":"Build auth"}, "status":"success"}` | Serialization only |

**Key Transformations**:
- JSON → dict: Deserialization
- dict → DTO: Type coercion + validation
- DTO → Entity: Business rule enforcement + UUID generation
- Entity → SQL: ORM mapping
- SQL → Entity: Rehydration
- Entity → DTO: Projection (select fields)
- DTO → JSON: Serialization

---

## Enhanced Security & Authentication Flow

### Multi-Mode Authentication Pipeline

| Mode | Configuration | Auth Method | Use Case |
|------|--------------|-------------|----------|
| **Production** | AUTH_ENABLED=true, KEYCLOAK_URL set | JWT from Keycloak | Multi-tenant production |
| **Development** | AUTH_ENABLED=false | Default user context | Local development |
| **Testing** | AUTH_ENABLED=false | Mock user context | Automated tests |

**JWT Validation Steps**:
1. Extract `Authorization: Bearer <token>` header
2. Decode JWT header (algorithm: RS256 or HS256)
3. Fetch public key from Keycloak (or use secret for HS256)
4. Verify signature
5. Check expiry (`exp` claim)
6. Validate issuer (`iss` claim matches KEYCLOAK_URL)
7. Validate audience (`aud` claim matches client_id)
8. Extract user claims (user_id, email, roles, tenant_id)
9. Create user context object
10. Inject into request processing

**Authorization Checks**:
- Role-based: Check user.roles contains required role
- Resource-level: Check user.tenant_id matches resource.tenant_id
- Operation-level: Check user has permission for operation (create/read/update/delete)

### User-Scoped Repository Pattern

| Aspect | Implementation | Benefit |
|--------|---------------|---------|
| **Tenant Isolation** | `WHERE tenant_id = user.tenant_id` added to ALL queries | Complete data isolation |
| **Automatic Filtering** | Repository constructor receives user context | No manual filtering needed |
| **Query Safety** | Cross-tenant access impossible (filtered at repo level) | Security by design |
| **Performance** | Tenant_id indexed | Fast queries |

**Pattern**:
```python
class UserScopedTaskRepository:
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
    
    def find_all(self) -> list[Task]:
        return db.query(Task).filter(
            Task.tenant_id == self.user_context.tenant_id
        ).all()
```

---

## Performance Optimization Flows

### Caching Strategy Flow

| Resource | Cache Type | TTL | Invalidation | Hit Rate Target |
|----------|-----------|-----|--------------|-----------------|
| **Project Metadata** | In-memory (LRU) | 5 minutes | On project update | 95% |
| **User Permissions** | Redis | 15 minutes | On role change | 90% |
| **Task Lists** | Application-level | 30 seconds | On task create/update | 80% |
| **Agent Definitions** | In-memory | No expiry | On agent register/update | 99% |

**Cache Flow**:
1. Request arrives
2. Check cache key
3. If hit: Return cached value (fast path)
4. If miss: Load from database → Store in cache → Return value

### Database Query Optimization Flow

| Optimization | Technique | Impact |
|-------------|----------|--------|
| **Eager Loading** | `joinedload(Task.assignees)` | Avoid N+1 queries |
| **Batch Loading** | Load multiple entities in single query | Reduce round-trips |
| **Index Strategy** | Index on tenant_id, user_id, created_at | 10-100x faster queries |
| **Query Projection** | SELECT only needed columns | Reduce data transfer |
| **Connection Pooling** | Reuse DB connections | Eliminate connection overhead |

---

## Transaction Management Flow

### Distributed Transaction Coordination

| Phase | Action | Rollback Trigger |
|-------|--------|------------------|
| **1. Begin** | Start DB transaction | N/A |
| **2. Domain Operations** | Execute business logic | Domain rule violation |
| **3. Repository Writes** | INSERT/UPDATE/DELETE | Database constraint violation |
| **4. Pre-commit Validation** | Final consistency checks | Validation failure |
| **5. Commit** | Persist all changes | Commit error |
| **6. Post-commit Events** | Publish domain events | Event publish failure (logged, not rolled back) |

**Transaction Span**: Application layer (Facade) controls boundaries
**Isolation Level**: READ COMMITTED (default)
**Timeout**: 30 seconds (configurable)

---

## Monitoring & Observability Flow

### Request Tracing Pipeline

| Metric | Collection Point | Storage | Visualization |
|--------|-----------------|---------|---------------|
| **Request Duration** | Middleware (start/end time) | Prometheus | Grafana dashboard |
| **Error Rate** | Exception handler | Logs + Metrics | Alert on >5% |
| **DB Query Time** | Repository | APM (Application Performance Monitoring) | Query optimization insights |
| **Cache Hit Rate** | Cache layer | Metrics | Cache effectiveness |
| **Event Processing Time** | Event handlers | Metrics | Async performance |

**Trace ID**: Generated at transport layer, propagated through all layers, included in logs/responses

---

## DDD Component Architecture

### Core DDD Components

| Component | Examples | Responsibilities |
|-----------|----------|------------------|
| **Entities** | Task, Project, Agent, GitBranch, Context | Identity, state, invariants |
| **Value Objects** | TaskStatus, Priority, UUID, Email, Progress | Immutable values, no identity |
| **Aggregates** | Task (root), Subtasks (children) | Transaction boundary, consistency |
| **Domain Services** | TaskStateTransitionService, AgentAssignmentPolicy, ProgressCalculationService | Multi-entity business logic |
| **Repositories** | TaskRepository, ProjectRepository, AgentRepository | Entity persistence |
| **Domain Events** | TaskCreated, TaskCompleted, AgentAssigned | State change notifications |
| **Factories** | TaskFactory, ProjectFactory | Complex entity creation |
| **Specifications** | TaskAssignmentSpecification | Reusable business rules |

### Authentication Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **JWTValidator** | Token signature verification | auth/validators.py |
| **KeycloakClient** | Public key fetching, user info | auth/keycloak_client.py |
| **UserContextExtractor** | Extract user claims from token | auth/context.py |
| **PermissionChecker** | Role/resource authorization | auth/permissions.py |
| **AuthMiddleware** | Request interception, auth enforcement | middleware/auth.py |

---

## Dependency Resolution Flow

### Module Dependency Rules

| Layer | Can Depend On | Cannot Depend On |
|-------|--------------|------------------|
| **Domain** | Nothing (pure business logic) | Application, Interface, Infrastructure |
| **Application** | Domain | Interface, Infrastructure |
| **Interface** | Application, Domain | Infrastructure (except via injection) |
| **Infrastructure** | Domain (for entity persistence) | Application, Interface |

**Why**: Ensures domain logic stays pure, portable, and testable

### Dependency Injection Flow

**Pattern**: Constructor injection at all layers

| Layer | Injects | Receives |
|-------|---------|----------|
| **Interface** | Application Facades | Instantiated by FastMCP framework |
| **Application** | Domain Services, Repositories | Facade constructor |
| **Domain** | Domain Services (optional) | Entity methods/factories |
| **Infrastructure** | Database connections, External clients | Repository constructor |

---

## Architecture Summary

### Key Architectural Patterns

| Pattern | Purpose | Implementation |
|---------|---------|----------------|
| **DDD Layering** | Separate concerns, testability | Domain/Application/Interface/Infrastructure |
| **CQRS (Partial)** | Read/write optimization | Separate query methods from commands |
| **Event Sourcing (Partial)** | Audit trail, decoupling | Domain events for state changes |
| **Repository Pattern** | Data access abstraction | User-scoped repositories |
| **DTO Pattern** | Layer boundary data transfer | Request/Response DTOs |

### Security Features

- Multi-tenant isolation (tenant_id filtering)
- JWT-based authentication (RS256/HS256)
- Role-based access control (RBAC)
- Resource-level authorization
- Rate limiting and throttling
- Audit trail (all operations logged)
- Development mode (AUTH_ENABLED=false)

### Performance Optimizations

- Multi-level caching (in-memory, Redis)
- Database connection pooling
- Eager loading (N+1 query prevention)
- Query optimization (indexes, projections)
- Async event processing

### Scalability Considerations

- Stateless application layer (horizontal scaling)
- Database connection pooling (resource efficiency)
- Event-driven architecture (async processing)
- Tenant isolation (no cross-tenant queries)
- Cache invalidation strategies (consistency at scale)

### Development Features

- MVP mode for local development (no auth)
- Comprehensive logging and tracing
- Test isolation (separate DB contexts)
- Transaction management (automatic rollback)
- Error handling with clear messages

---

## Implementation Status

### ✅ Completed Components

- All 4 DDD layers implemented and operational
- JWT authentication with Keycloak integration
- User-scoped repositories with tenant isolation
- Domain event system with async event bus
- Transaction management with automatic rollback
- Multi-level caching (in-memory + Redis)
- Comprehensive error handling pipeline
- Request tracing and observability
- All MCP tools (Task, Project, Context, Agent, GitBranch)

### 🚧 In Progress

- Advanced caching strategies (cache warming, predictive invalidation)
- Query performance optimization (additional indexes)
- Event replay mechanisms (event sourcing enhancements)
- Distributed tracing integration (OpenTelemetry)

### 📅 Planned Features

- CQRS read models (optimized query paths)
- Saga pattern for long-running transactions
- Event store persistence (full event sourcing)
- API rate limiting per tenant
- Advanced monitoring dashboards
