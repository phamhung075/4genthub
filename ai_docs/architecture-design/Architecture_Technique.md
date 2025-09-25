# Technical Architecture Document
# 4genthub - AI-Human Collaboration Platform

## 1. System Overview

### 1.1 Architecture Philosophy
4genthub follows a **Domain-Driven Design (DDD)** approach with clean architecture principles, ensuring separation of concerns, maintainability, and scalability. The system is built as a distributed, event-driven architecture with microservices capabilities.

### 1.2 High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Dashboard<br/>React + TypeScript]
        CLI[CLI Tools<br/>MCP Clients]
    end

    subgraph "API Gateway"
        NGINX[Nginx<br/>Reverse Proxy]
        WS[WebSocket<br/>Server]
    end

    subgraph "Application Layer"
        MCP[MCP Server<br/>FastMCP]
        API[REST API<br/>FastAPI]
        AGENT[Agent Orchestra<br/>32 Agents]
    end

    subgraph "Domain Layer"
        TASK[Task Domain]
        CONTEXT[Context Domain]
        PROJECT[Project Domain]
        AUTH[Auth Domain]
    end

    subgraph "Infrastructure Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        KC[Keycloak]
        DOCKER[Docker]
    end

    WEB --> NGINX
    CLI --> MCP
    NGINX --> API
    NGINX --> WS
    WS --> MCP
    API --> AGENT
    MCP --> AGENT
    AGENT --> TASK
    AGENT --> CONTEXT
    AGENT --> PROJECT
    API --> AUTH
    AUTH --> KC
    TASK --> PG
    CONTEXT --> PG
    PROJECT --> PG
    CONTEXT --> REDIS
```

## 2. Domain-Driven Design Structure

### 2.1 Layered Architecture

```
agenthub_main/src/
├── domain/                 # Enterprise Business Rules
│   ├── entities/          # Core business objects
│   ├── value_objects/     # Immutable value types
│   ├── aggregates/        # Aggregate roots
│   └── services/          # Domain services
├── application/           # Application Business Rules
│   ├── use_cases/        # Application services
│   ├── facades/          # Application facades
│   └── dto/              # Data transfer objects
├── infrastructure/        # Frameworks & Drivers
│   ├── persistence/      # Database implementations
│   ├── external/         # External service clients
│   └── config/           # Configuration management
└── interfaces/           # Interface Adapters
    ├── mcp/             # MCP controllers
    ├── http/            # HTTP endpoints
    └── websocket/       # WebSocket handlers
```

### 2.2 Domain Boundaries

#### Core Domains
1. **Task Management Domain**
   - Entities: Task, Subtask
   - Value Objects: TaskId, TaskStatus, Priority
   - Aggregates: TaskTree
   - Services: TaskOrchestrator

2. **Context Management Domain**
   - Entities: GlobalContext, ProjectContext, BranchContext, TaskContext
   - Value Objects: ContextId, ContextLevel
   - Aggregates: ContextHierarchy
   - Services: ContextResolver

3. **Project Management Domain**
   - Entities: Project, GitBranch
   - Value Objects: ProjectId, BranchId
   - Aggregates: ProjectWorkspace
   - Services: ProjectCoordinator

4. **Agent Management Domain**
   - Entities: Agent, AgentAssignment
   - Value Objects: AgentId, AgentCapability
   - Aggregates: AgentPool
   - Services: AgentDispatcher

## 3. Component Architecture

### 3.1 Frontend Architecture (React + TypeScript)

```typescript
// Component Structure
src/
├── components/           // Reusable UI components
│   ├── common/          // Shared components
│   ├── dashboard/       // Dashboard widgets
│   └── agents/          // Agent-specific components
├── contexts/            // React contexts
├── hooks/              // Custom hooks
├── services/           // API services
│   ├── api/           // REST API clients
│   └── websocket/     // WebSocket clients
├── store/             // State management
│   ├── slices/        // Redux slices
│   └── middleware/    // Custom middleware
└── utils/             // Utility functions
```

#### Key Frontend Technologies
- **Build Tool**: Vite 6.0
- **Framework**: React 18.3
- **Language**: TypeScript 5.7
- **Styling**: Tailwind CSS 3.4
- **State Management**: Redux Toolkit
- **Routing**: React Router 7.1
- **UI Components**: Radix UI, shadcn/ui
- **WebSocket**: native WebSocket API
- **HTTP Client**: Axios

### 3.2 Backend Architecture (Python + FastMCP)

```python
# Service Layer Architecture
class ApplicationFacade:
    """Orchestrates domain services and use cases"""

    def __init__(self):
        self.task_service = TaskDomainService()
        self.context_service = ContextDomainService()
        self.agent_service = AgentDomainService()

    async def execute_workflow(self, workflow: Workflow):
        """Coordinates multi-domain operations"""
        pass
```

#### Key Backend Technologies
- **Language**: Python 3.12+
- **MCP Framework**: FastMCP 0.6+
- **Web Framework**: FastAPI 0.115+
- **ORM**: SQLAlchemy 2.0
- **Async**: asyncio, uvicorn
- **Validation**: Pydantic 2.11
- **Authentication**: python-jose, PyJWT
- **Testing**: pytest, pytest-asyncio

### 3.3 Database Architecture

#### PostgreSQL Schema Design

```sql
-- Context Hierarchy
CREATE TABLE contexts (
    id UUID PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    parent_id UUID REFERENCES contexts(id),
    data JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Task Management
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    git_branch_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20),
    priority VARCHAR(20),
    assignees JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Indexes for Performance
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_branch ON tasks(git_branch_id);
CREATE INDEX idx_contexts_level ON contexts(level);
```

#### Timestamp Management Architecture

The system implements application-layer timestamp management for clean architecture compliance:

```python
# Application Layer Timestamp Management
from sqlalchemy import event
from datetime import datetime, timezone

@event.listens_for(BaseModel, 'before_insert', propagate=True)
def receive_before_insert(mapper, connection, target):
    """Set timestamps for new entities"""
    now = datetime.now(timezone.utc)
    target.created_at = now
    target.updated_at = now

@event.listens_for(BaseModel, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Update timestamp for modified entities"""
    target.updated_at = datetime.now(timezone.utc)
```

**Benefits:**
- Database portability (works across SQLite, PostgreSQL, cloud databases)
- Explicit control and visibility in application code
- Easy testing with mocked time
- No database trigger complexity
- Clean separation of concerns per DDD principles

#### Database Initialization

The system uses direct SQL schema initialization instead of migrations:
- `init_schema_postgresql.sql` for PostgreSQL deployments
- `init_schema_sqlite.sql` for development environments
- No migration history or version tracking needed
- Clean slate approach for development phase
- **Pure Domain Logic**: No SQL triggers, CASCADE constraints, or database business logic
- **Clean Architecture**: All business rules in domain layer, database is just storage

#### Redis Caching Strategy

```python
# Cache Patterns
CACHE_PATTERNS = {
    "session": "session:{user_id}",
    "context": "context:{level}:{id}",
    "task": "task:{task_id}",
    "agent": "agent:{agent_id}"
}

# TTL Strategy
TTL_STRATEGY = {
    "session": 3600,      # 1 hour
    "context": 300,       # 5 minutes
    "task": 60,          # 1 minute
    "agent": 1800        # 30 minutes
}
```

## 4. Integration Architecture

### 4.1 MCP Protocol Implementation

```python
# MCP Tool Registration
@mcp_tool(
    name="manage_task",
    description="Task management operations"
)
async def manage_task(
    action: str,
    **kwargs
) -> Dict:
    """MCP tool for task management"""
    facade = TaskApplicationFacade()
    return await facade.handle_action(action, **kwargs)
```

### 4.2 Authentication Flow (Keycloak)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Keycloak

    User->>Frontend: Login Request
    Frontend->>Keycloak: Redirect to Auth
    Keycloak->>User: Login Form
    User->>Keycloak: Credentials
    Keycloak->>Frontend: Auth Code
    Frontend->>Backend: Exchange Code
    Backend->>Keycloak: Validate Token
    Keycloak->>Backend: User Info
    Backend->>Frontend: JWT Token
    Frontend->>User: Authenticated
```

### 4.3 WebSocket Architecture

```typescript
// WebSocket Connection Management
class WebSocketClient {
    private socket: WebSocket;
    private reconnectAttempts = 0;

    connect(): void {
        this.socket = new WebSocket('ws://localhost:8000/ws');
        this.setupEventHandlers();
    }

    private setupEventHandlers(): void {
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = () => {
            this.handleReconnect();
        };
    }
}
```

## 5. Agent Architecture

### 5.1 Agent Hierarchy

```yaml
Agent Categories:
  Development:
    - coding-agent
    - debugger-agent
    - code-reviewer-agent
    - prototyping-agent

  Testing:
    - test-orchestrator-agent
    - uat-coordinator-agent
    - performance-load-tester-agent

  Design:
    - system-architect-agent
    - design-system-agent
    - shadcn-ui-expert-agent
    - core-concept-agent

  Operations:
    - devops-agent
    - health-monitor-agent
    - analytics-setup-agent
    - efficiency-optimization-agent
```

### 5.2 Agent Communication Pattern

```python
# Agent Delegation Pattern
class MasterOrchestratorAgent:
    async def delegate_task(self, task: Task) -> Result:
        # 1. Analyze task requirements
        requirements = self.analyze_requirements(task)

        # 2. Select appropriate agent
        agent = self.select_agent(requirements)

        # 3. Create MCP task with context
        mcp_task = await self.create_mcp_task(task)

        # 4. Delegate with ID only
        result = await agent.execute(task_id=mcp_task.id)

        # 5. Process results
        return self.process_results(result)
```

## 6. Deployment Architecture

### 6.1 Docker Configuration

```yaml
# docker-compose.yml structure
version: '3.9'

services:
  frontend:
    build: ./agenthub-frontend
    ports:
      - "3800:3800"
    environment:
      - VITE_API_URL=http://backend:8000

  backend:
    build: ./agenthub_main
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/agenthub
      - REDIS_URL=redis://redis:6379

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  keycloak:
    image: quay.io/keycloak/keycloak:25.0
    environment:
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_PASSWORD}
```

### 6.2 Scalability Strategy

```mermaid
graph LR
    LB[Load Balancer] --> W1[Web Server 1]
    LB --> W2[Web Server 2]
    LB --> W3[Web Server N]

    W1 --> API1[API Server 1]
    W2 --> API2[API Server 2]
    W3 --> API3[API Server N]

    API1 --> PG[(PostgreSQL<br/>Primary)]
    API2 --> PG
    API3 --> PG

    PG --> PGR[(PostgreSQL<br/>Read Replica)]

    API1 --> REDIS[(Redis Cluster)]
    API2 --> REDIS
    API3 --> REDIS
```

## 7. Security Architecture

### 7.1 Security Layers

1. **Network Security**
   - HTTPS/TLS encryption
   - Firewall rules
   - DDoS protection

2. **Application Security**
   - JWT token validation
   - CORS configuration
   - Rate limiting
   - Input validation

3. **Data Security**
   - Encryption at rest
   - Encryption in transit
   - Secure key management
   - Database access control

### 7.2 Authentication & Authorization

```python
# RBAC Implementation
class RoleBasedAccessControl:
    PERMISSIONS = {
        "admin": ["*"],
        "developer": ["task:*", "context:read", "agent:execute"],
        "viewer": ["task:read", "context:read", "project:read"]
    }

    def check_permission(self, user_role: str, action: str) -> bool:
        """Verify user has permission for action"""
        permissions = self.PERMISSIONS.get(user_role, [])
        return self.matches_permission(permissions, action)
```

## 8. Performance Optimization

### 8.1 Caching Strategy

- **L1 Cache**: Application memory (Python dict)
- **L2 Cache**: Redis for distributed caching
- **L3 Cache**: PostgreSQL query caching
- **CDN**: Static assets caching

### 8.2 Database Optimization

- Connection pooling (max 100 connections)
- Query optimization with indexes
- Materialized views for complex queries
- Partitioning for large tables

### 8.3 Async Processing

```python
# Async Task Queue Pattern
async def process_task_queue():
    while True:
        task = await queue.get()
        asyncio.create_task(process_task(task))
        await asyncio.sleep(0.1)
```

## 9. Monitoring & Observability

### 9.1 Logging Architecture

```python
# Structured Logging
import structlog

logger = structlog.get_logger()

logger.info(
    "task_created",
    task_id=task.id,
    user_id=user.id,
    duration_ms=elapsed_time
)
```

### 9.2 Metrics Collection

- **Application Metrics**: Response time, throughput, error rate
- **Business Metrics**: Task completion rate, agent utilization
- **Infrastructure Metrics**: CPU, memory, disk, network

### 9.3 Health Checks

```python
# Health Check Endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.0.5",
        "services": {
            "database": check_database(),
            "redis": check_redis(),
            "keycloak": check_keycloak()
        }
    }
```

## 10. Development Practices

### 10.1 CI/CD Pipeline

```yaml
# GitHub Actions Workflow
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: |
          pytest agenthub_main/src/tests/
          npm test --prefix agenthub-frontend

  build:
    needs: test
    steps:
      - name: Build Docker Images
        run: docker-compose build

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Production
        run: ./scripts/deploy.sh
```

### 10.2 Testing Strategy

- **Unit Tests**: 80% code coverage target
- **Integration Tests**: API endpoint testing
- **E2E Tests**: Critical user flows
- **Performance Tests**: Load and stress testing

## 11. Technology Stack Summary

### Frontend Stack
- React 18.3 + TypeScript 5.7
- Vite 6.0 build tool
- Tailwind CSS 3.4
- Redux Toolkit for state
- Radix UI components

### Backend Stack
- Python 3.12+
- FastMCP 0.6+ framework
- FastAPI 0.115+
- SQLAlchemy 2.0 ORM
- Pydantic 2.11 validation

### Infrastructure Stack
- PostgreSQL 16 database
- Redis 7 caching
- Docker containerization
- Keycloak 25.0 auth
- Nginx reverse proxy

### Development Stack
- Git version control
- GitHub Actions CI/CD
- pytest testing
- ESLint/Prettier
- Black/Ruff formatting

## 12. Future Architecture Considerations

### 12.1 Microservices Migration Path
- Extract agent service
- Separate task service
- Independent context service
- API gateway implementation

### 12.2 Event-Driven Architecture
- Event sourcing for audit
- CQRS pattern adoption
- Message queue integration
- Event streaming platform

### 12.3 Cloud-Native Evolution
- Kubernetes orchestration
- Service mesh adoption
- Serverless functions
- Cloud-native databases

---

*This architecture document represents the current state of the 4genthub platform and will evolve as the system grows.*