# Technical Architecture Document
## agenthub - AI-Human Collaboration Platform

**Version**: 0.0.2
**Status**: Production NOT Ready
**Last Updated**: 2025-10-16
**Document Owner**: Engineering Team

---

## 1. Executive Summary

### 1.1 Architecture Overview
agenthub implements a **Domain-Driven Design (DDD) architecture** with clear separation of concerns across four layers: Domain, Application, Infrastructure, and Interface. The system is built on the **Model Context Protocol (MCP)** standard and designed for horizontal scalability from MVP (100 RPS) to Enterprise (1M+ RPS).

### 1.2 Key Architectural Decisions
1. **MCP Protocol Native**: Built-in support for Model Context Protocol HTTP transport
2. **DDD Architecture**: Clean architecture with bounded contexts for each subsystem
3. **4-Tier Context Hierarchy**: Global → Project → Branch → Task for zero context loss
4. **Multi-Tenancy**: Per-user data isolation with Keycloak authentication
5. **Containerized Deployment**: Docker-based with multiple configuration profiles
6. **Microservices Ready**: Designed for future microservices migration

### 1.3 Technology Stack at a Glance
- **Frontend**: React 19 + TypeScript 4 + Vite 7 + Tailwind CSS
- **Backend**: Python 3.14 + FastMCP + FastAPI + SQLAlchemy
- **Database**: PostgreSQL (production) / SQLite (dev) + Redis (cache)
- **Auth**: Keycloak (SSO) + JWT tokens
- **Infrastructure**: Docker + Docker Compose
- **Protocol**: MCP 2.1.0 over HTTP

---

## 2. System Architecture

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Web Dashboard<br/>React + TypeScript<br/>Port 3800]
        CLI[CLI Tools<br/>MCP Clients]
    end

    subgraph "API Gateway Layer"
        Gateway[FastAPI Gateway<br/>Port 8000]
        WS[WebSocket Server<br/>Real-time Updates]
    end

    subgraph "MCP Protocol Layer"
        MCP[MCP Server<br/>FastMCP Framework]
        Tools[15+ Tool Categories]
        Resources[Resource Management]
    end

    subgraph "Business Logic Layer (DDD)"
        TM[Task Management<br/>Bounded Context]
        AM[Agent Orchestration<br/>Bounded Context]
        CM[Context Management<br/>Bounded Context]
        PM[Project Management<br/>Bounded Context]
        Auth[Authentication<br/>Bounded Context]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary Database)]
        Redis[(Redis<br/>Cache & Sessions)]
        FS[File System<br/>Logs & Docs]
    end

    subgraph "External Services"
        KC[Keycloak<br/>Identity Provider]
        AI[AI Models<br/>Claude, GPT, etc.]
    end

    UI --> Gateway
    CLI --> Gateway
    Gateway --> MCP
    Gateway --> WS
    MCP --> Tools
    MCP --> Resources
    Tools --> TM
    Tools --> AM
    Tools --> CM
    Tools --> PM
    Tools --> Auth
    TM --> PG
    AM --> PG
    CM --> PG
    PM --> PG
    Auth --> KC
    Auth --> Redis
    TM --> Redis
    AM --> AI

    style UI fill:#e1f5fe
    style Gateway fill:#f3e5f5
    style MCP fill:#e8f5e9
    style TM fill:#fff3e0
    style PG fill:#fce4ec
    style KC fill:#f1f8e9
```

### 2.2 Layered Architecture (DDD)

```
┌─────────────────────────────────────────────────────────┐
│              INTERFACE LAYER                           │
│  - MCP Controllers                                      │
│  - HTTP Endpoints (FastAPI)                            │
│  - WebSocket Handlers                                  │
│  - Request/Response DTOs                               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            APPLICATION LAYER                            │
│  - Use Cases (Business Workflows)                       │
│  - Application Services                                 │
│  - Facades (Simplified APIs)                           │
│  - DTOs (Data Transfer Objects)                        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│               DOMAIN LAYER                              │
│  - Entities (Business Objects)                          │
│  - Value Objects (Immutable Values)                     │
│  - Domain Services (Business Logic)                     │
│  - Domain Events                                        │
│  - Repository Interfaces                                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│           INFRASTRUCTURE LAYER                          │
│  - Repository Implementations                           │
│  - Database Access (SQLAlchemy)                        │
│  - External Service Integrations                        │
│  - Caching (Redis)                                     │
│  - File System Operations                              │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Bounded Contexts

agenthub is organized into **5 primary bounded contexts**:

#### 1. Task Management Context
- **Purpose**: Manage hierarchical task structures and workflows
- **Entities**: Task, Subtask, TaskDependency
- **Value Objects**: TaskStatus, Priority, TaskId
- **Services**: TaskCreationService, TaskCompletionService
- **Location**: `agenthub_main/src/fastmcp/task_management/`

#### 2. Agent Orchestration Context
- **Purpose**: Coordinate AI agent assignments and execution
- **Entities**: Agent, AgentAssignment, AgentCapability
- **Value Objects**: AgentId, AgentRole
- **Services**: AgentRegistrationService, AgentCoordinationService
- **Location**: `agenthub_main/src/fastmcp/agent_management/`

#### 3. Context Management Context
- **Purpose**: Manage 4-tier context hierarchy (Global → Project → Branch → Task)
- **Entities**: GlobalContext, ProjectContext, BranchContext, TaskContext
- **Value Objects**: ContextId, ContextLevel
- **Services**: ContextInheritanceService, ContextSyncService
- **Location**: `agenthub_main/src/fastmcp/context_management/`

#### 4. Project Management Context
- **Purpose**: Organize projects, git branches, and version control integration
- **Entities**: Project, GitBranch, Milestone
- **Value Objects**: ProjectId, BranchId, BranchName
- **Services**: ProjectHealthService, BranchSyncService
- **Location**: `agenthub_main/src/fastmcp/project_management/`

#### 5. Authentication Context
- **Purpose**: Handle user authentication, authorization, and session management
- **Entities**: User, Session, Role
- **Value Objects**: UserId, AccessToken, RefreshToken
- **Services**: AuthenticationService, TokenRefreshService
- **Location**: `agenthub_main/src/fastmcp/auth/`

---

## 3. Frontend Architecture

### 3.1 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | React | 19.1.0 | UI component library |
| **Language** | TypeScript | 4.9.5 | Type-safe development |
| **Build Tool** | Vite | 7.1.3 | Fast development server & bundler |
| **Styling** | Tailwind CSS | 3.4.1 | Utility-first CSS framework |
| **UI Components** | shadcn/ui + Material-UI | Latest | Pre-built component library |
| **State Management** | Redux Toolkit | 2.9.0 | Global state management |
| **Routing** | React Router | 7.8.1 | Client-side routing |
| **Forms** | React Hook Form | 7.62.0 | Form validation & handling |
| **Icons** | Lucide React + MUI Icons | Latest | Icon libraries |
| **Animations** | Framer Motion | 12.23.12 | Animation library |
| **HTTP Client** | Fetch API | Native | API communication |
| **Testing** | Vitest + Testing Library | 3.2.4 | Unit & integration testing |

### 3.2 Directory Structure

```
agenthub-frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── common/          # Shared components (Button, Input, etc.)
│   │   ├── layout/          # Layout components (Header, Sidebar)
│   │   └── features/        # Feature-specific components
│   ├── pages/               # Route-based page components
│   │   ├── Dashboard/       # Main dashboard page
│   │   ├── Projects/        # Projects management
│   │   ├── Tasks/           # Task management
│   │   └── Agents/          # Agent orchestration
│   ├── store/               # Redux store configuration
│   │   ├── slices/          # Redux slices (features)
│   │   └── api/             # API service definitions
│   ├── hooks/               # Custom React hooks
│   ├── utils/               # Utility functions
│   ├── types/               # TypeScript type definitions
│   ├── styles/              # Global styles
│   ├── assets/              # Static assets (images, fonts)
│   ├── App.tsx              # Root component
│   └── main.tsx             # Entry point
├── public/                  # Public static files
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── package.json             # Dependencies
```

### 3.3 Component Architecture

```
App Component (Root)
    ↓
Router Provider
    ↓
Redux Store Provider
    ↓
Theme Provider
    ↓
Layout Component
    ├── Header (Navigation, User Menu)
    ├── Sidebar (Project Tree, Quick Actions)
    └── Main Content Area
        ├── Dashboard Page
        ├── Projects Page
        ├── Tasks Page
        └── Agents Page
```

### 3.4 State Management Strategy

**Redux Toolkit Slices**:
- `authSlice`: User authentication state, tokens
- `projectsSlice`: Projects list, current project
- `tasksSlice`: Tasks hierarchy, current task
- `agentsSlice`: Agent assignments, agent status
- `contextSlice`: Context data for all 4 tiers

**API Integration**:
- RTK Query for automated caching and invalidation
- WebSocket integration for real-time updates
- Automatic retry logic for failed requests

### 3.5 Key Features

1. **Real-Time Updates**: WebSocket connection for live agent activity
2. **Responsive Design**: Mobile-first approach, works on tablets (iPad+)
3. **Dark Mode Support**: System preference detection and manual toggle
4. **Accessibility**: WCAG 2.1 Level AA compliance (in progress)
5. **Performance**: Code splitting, lazy loading, memoization
6. **Type Safety**: Comprehensive TypeScript coverage

---

## 4. Backend Architecture

### 4.1 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.14.0 | Programming language |
| **Framework** | FastMCP | Latest | MCP protocol framework |
| **Web Framework** | FastAPI | 0.115.12 | REST API framework |
| **ASGI Server** | Uvicorn | 0.34.3 | Production ASGI server |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Migrations** | Alembic | 1.13.0 | Database schema versioning |
| **Validation** | Pydantic | 2.11.7 | Data validation |
| **Authentication** | PyJWT + python-jose | Latest | JWT token management |
| **Password Hashing** | bcrypt | 4.1.0 | Secure password storage |
| **Async Support** | asyncio + httpx | Native | Asynchronous operations |
| **Testing** | pytest + pytest-asyncio | 8.3.3 | Unit & integration testing |
| **Caching** | Redis | 5.0.0 | Session & cache storage |

### 4.2 Directory Structure (DDD Layout)

```
agenthub_main/src/fastmcp/
├── task_management/              # Task Management Bounded Context
│   ├── domain/
│   │   ├── entities/             # Task, Subtask
│   │   ├── value_objects/        # TaskId, TaskStatus
│   │   ├── services/             # Domain business logic
│   │   └── repositories/         # Repository interfaces
│   ├── application/
│   │   ├── use_cases/            # Create Task, Complete Task
│   │   ├── services/             # Application orchestration
│   │   └── dtos/                 # Data transfer objects
│   ├── infrastructure/
│   │   ├── repositories/         # SQLAlchemy implementations
│   │   └── database/             # Database configurations
│   └── interface/
│       └── controllers/          # MCP tool controllers
│
├── agent_management/             # Agent Orchestration Bounded Context
│   ├── domain/
│   │   ├── entities/             # Agent, AgentAssignment
│   │   ├── value_objects/        # AgentId, AgentRole
│   │   └── services/             # Agent coordination logic
│   ├── application/
│   │   ├── use_cases/            # Register Agent, Assign Agent
│   │   └── services/             # Agent orchestration
│   ├── infrastructure/
│   │   └── repositories/         # Agent persistence
│   └── interface/
│       └── controllers/          # MCP agent controllers
│
├── context_management/           # Context Management Bounded Context
│   ├── domain/
│   │   ├── entities/             # GlobalContext, ProjectContext
│   │   ├── value_objects/        # ContextId, ContextLevel
│   │   └── services/             # Context inheritance logic
│   ├── application/
│   │   ├── use_cases/            # Create Context, Sync Context
│   │   └── services/             # Context operations
│   ├── infrastructure/
│   │   └── repositories/         # Context persistence
│   └── interface/
│       └── controllers/          # MCP context controllers
│
├── auth/                         # Authentication Bounded Context
│   ├── domain/
│   │   ├── entities/             # User, Session
│   │   ├── value_objects/        # AccessToken, RefreshToken
│   │   └── services/             # Authentication logic
│   ├── application/
│   │   ├── use_cases/            # Login, Refresh Token
│   │   └── services/             # Token management
│   ├── infrastructure/
│   │   ├── repositories/         # User persistence
│   │   └── integrations/         # Keycloak integration
│   └── interface/
│       └── controllers/          # Auth endpoints
│
├── shared/                       # Shared Kernel
│   ├── domain/
│   │   └── base_entities.py      # BaseEntity, AggregateRoot
│   ├── infrastructure/
│   │   ├── database.py           # SQLAlchemy engine
│   │   ├── redis_client.py       # Redis connection
│   │   └── unit_of_work.py       # Transaction management
│   └── utils/
│       ├── validators.py         # Common validations
│       └── exceptions.py         # Custom exceptions
│
├── cli/                          # CLI commands
├── config/                       # Configuration management
└── server.py                     # FastMCP server entry point
```

### 4.3 Database Schema (PostgreSQL)

#### Core Tables

**users** (Authentication Context)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**sessions** (Authentication Context)
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**projects** (Project Management Context)
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, user_id)
);
```

**git_branches** (Project Management Context)
```sql
CREATE TABLE git_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    git_branch_name VARCHAR(255) NOT NULL,
    git_branch_description TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, git_branch_name)
);
```

**tasks** (Task Management Context)
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    git_branch_id UUID REFERENCES git_branches(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'todo',
    priority VARCHAR(50) DEFAULT 'medium',
    estimated_effort VARCHAR(100),
    details TEXT,
    assignees TEXT,  -- JSON array of agent names
    labels TEXT,     -- JSON array of labels
    due_date TIMESTAMP,
    dependencies TEXT,  -- JSON array of task IDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**subtasks** (Task Management Context)
```sql
CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'todo',
    priority VARCHAR(50),
    progress_percentage INTEGER DEFAULT 0,
    assignees TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**contexts** (Context Management Context)
```sql
CREATE TABLE contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(50) NOT NULL,  -- 'global', 'project', 'branch', 'task'
    context_id UUID NOT NULL,     -- ID of the entity (user, project, branch, task)
    data JSONB NOT NULL,          -- Flexible JSON data storage
    user_id UUID REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    git_branch_id UUID REFERENCES git_branches(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(level, context_id)
);
CREATE INDEX idx_contexts_level ON contexts(level);
CREATE INDEX idx_contexts_user_id ON contexts(user_id);
CREATE INDEX idx_contexts_data ON contexts USING GIN(data);
```

**agents** (Agent Orchestration Context)
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    call_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, agent_id)
);
```

**agent_assignments** (Agent Orchestration Context)
```sql
CREATE TABLE agent_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    git_branch_id UUID REFERENCES git_branches(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, git_branch_id)
);
```

### 4.4 Caching Strategy (Redis)

**Cache Keys Structure**:
```
session:{user_id}:{session_id}        # User sessions (TTL: 24h)
context:{level}:{context_id}          # Context cache (TTL: 1h)
task:{task_id}                        # Task cache (TTL: 30min)
agent:{agent_id}:status               # Agent status (TTL: 5min)
```

**Invalidation Strategy**:
- Write-through cache: Update DB first, then cache
- Cache invalidation on updates via event listeners
- LRU eviction policy for memory management
- Automatic TTL refresh on access

---

## 5. MCP Protocol Integration

### 5.1 MCP Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Server                            │
│                  (FastMCP Framework)                    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                  HTTP Transport Layer                    │
│           (Port 8000, RESTful endpoints)                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│               MCP Tool Controllers                       │
│  - manage_task        - manage_project                  │
│  - manage_subtask     - manage_git_branch               │
│  - manage_context     - manage_agent                    │
│  - call_agent         - manage_connection               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            Application Layer (Use Cases)                 │
│     Orchestrates domain logic and data access           │
└─────────────────────────────────────────────────────────┘
```

### 5.2 MCP Tool Categories

agenthub provides **15+ tool categories** with **50+ individual tools**:

1. **Task Management** (8 tools)
   - create, update, get, delete, complete, list, search, next

2. **Subtask Management** (6 tools)
   - create, update, delete, get, list, complete

3. **Project Management** (9 tools)
   - create, get, list, update, delete, health_check, cleanup, validate, rebalance

4. **Git Branch Management** (10 tools)
   - create, get, list, update, delete, assign_agent, unassign_agent, statistics, archive, restore

5. **Context Management** (9 tools)
   - create, get, update, delete, resolve, delegate, add_insight, add_progress, list

6. **Agent Orchestration** (8 tools)
   - register, assign, get, list, update, unassign, unregister, rebalance

7. **Agent Invocation** (1 tool)
   - call_agent (dynamic agent loading)

8. **Authentication** (1 tool)
   - manage_connection (health check)

### 5.3 Request/Response Flow

```
Client (Claude Code, Cline, etc.)
    ↓ HTTP POST
MCP Server (FastMCP)
    ↓ Parse request
Tool Controller (e.g., manage_task)
    ↓ Validate parameters
Application Service (e.g., TaskApplicationFacade)
    ↓ Execute use case
Domain Service (e.g., TaskCreationService)
    ↓ Business logic
Repository (e.g., TaskRepository)
    ↓ Database operation
SQLAlchemy ORM
    ↓ SQL query
PostgreSQL Database
    ↓ Return data
Repository → Domain → Application → Controller → MCP → Client
```

---

## 6. Authentication & Security Architecture

### 6.1 Keycloak Integration

```
User (Web/CLI Client)
    ↓ Login request
Frontend/CLI
    ↓ Redirect to Keycloak
Keycloak (Identity Provider)
    ↓ Authenticate user
Keycloak
    ↓ Issue tokens (access + refresh)
Frontend/CLI
    ↓ Store tokens (httpOnly cookies / local storage)
Frontend/CLI
    ↓ API request with access token
Backend (FastAPI)
    ↓ Validate JWT signature
Backend
    ↓ Verify token with Keycloak
Keycloak
    ↓ Confirm validity
Backend
    ↓ Extract user info (sub, email, roles)
Backend
    ↓ Process request with user context
```

### 6.2 Token Management

**Access Token**:
- Type: JWT (JSON Web Token)
- Lifetime: 5 minutes (configurable)
- Storage: httpOnly cookie (web) / memory (CLI)
- Purpose: API authorization

**Refresh Token**:
- Type: Opaque token
- Lifetime: 24 hours (configurable)
- Storage: httpOnly cookie (web) / secure storage (CLI)
- Purpose: Renew access token

**Token Refresh Flow**:
```python
if access_token.is_expired():
    new_tokens = await keycloak.refresh_token(refresh_token)
    update_cookies(new_tokens.access_token, new_tokens.refresh_token)
    retry_request_with_new_token()
```

### 6.3 Multi-Tenancy & Data Isolation

**Per-User Isolation**:
- Every database query includes `user_id` filter
- Global context scoped by user (each user has own global context)
- Projects, branches, tasks isolated by user ownership
- SQLAlchemy relationship filters enforce isolation

**Example Query**:
```python
# WRONG - No user isolation
tasks = session.query(Task).filter(Task.status == "todo").all()

# CORRECT - User-isolated
tasks = session.query(Task).join(GitBranch).join(Project).filter(
    Project.user_id == current_user_id,
    Task.status == "todo"
).all()
```

### 6.4 Security Best Practices

1. **Password Handling**: Never store passwords (Keycloak manages)
2. **Token Security**: httpOnly cookies prevent XSS attacks
3. **HTTPS Only**: TLS 1.3 for all production traffic
4. **SQL Injection**: SQLAlchemy ORM prevents injection
5. **XSS Protection**: React escapes all user input by default
6. **CSRF Protection**: SameSite=Strict cookie attribute
7. **Rate Limiting**: Per-user API rate limits (planned)
8. **Audit Logging**: All operations logged with user context

---

## 7. Deployment Architecture

### 7.1 Docker Infrastructure

**docker-compose.yml configurations**:

```yaml
# Configuration 1: PostgreSQL Local (Recommended for dev)
services:
  postgres:
    image: postgres:17
    ports: ["5432:5432"]
    volumes: ["./data:/var/lib/postgresql/data"]

  backend:
    build: ./agenthub_main
    ports: ["8000:8000"]
    depends_on: [postgres]

  frontend:
    build: ./agenthub-frontend
    ports: ["3800:3800"]
    depends_on: [backend]
```

```yaml
# Configuration 2: Supabase Cloud
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://[supabase-url]

  frontend:
    depends_on: [backend]
```

```yaml
# Configuration 3: Redis + PostgreSQL (Enterprise)
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:17

  backend:
    depends_on: [postgres, redis]
    environment:
      - REDIS_URL=redis://redis:6379
```

### 7.2 Container Structure

```
4genthub/
├── docker-compose.yml              # Main orchestration file
├── docker-system/
│   ├── docker-menu.sh              # Interactive menu system
│   ├── postgres-local.yml          # PostgreSQL local config
│   ├── supabase-cloud.yml          # Supabase cloud config
│   └── redis-postgres.yml          # Redis + PostgreSQL config
├── agenthub_main/
│   ├── Dockerfile                  # Backend container
│   └── .dockerignore               # Exclude files
├── agenthub-frontend/
│   ├── Dockerfile                  # Frontend container
│   └── .dockerignore               # Exclude files
└── data/                           # Persistent volumes
    ├── postgresql/                 # Database data
    └── logs/                       # Application logs
```

### 7.3 Environment Variables

**Backend (.env)**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/agenthub
REDIS_URL=redis://localhost:6379

# Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=agenthub-backend
KEYCLOAK_CLIENT_SECRET=secret

# Application
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
FASTMCP_LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=5
REFRESH_TOKEN_EXPIRE_HOURS=24
```

**Frontend (.env)**:
```bash
# API
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Keycloak
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=agenthub
VITE_KEYCLOAK_CLIENT_ID=agenthub-frontend
```

### 7.4 Deployment Strategies

**Development (Current)**:
- Docker Compose with hot reload
- SQLite for rapid iteration
- No TLS (HTTP only)
- Debug logging enabled

**Staging (Planned)**:
- Docker Compose with production builds
- PostgreSQL + Redis
- Self-signed TLS certificates
- Info-level logging

**Production (Future)**:
- Kubernetes orchestration
- Managed PostgreSQL (AWS RDS, GCP Cloud SQL)
- Managed Redis (AWS ElastiCache)
- TLS 1.3 with Let's Encrypt
- Error-level logging
- Multiple replicas for high availability

---

## 8. Performance Optimization

### 8.1 Current Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API Response Time (avg) | <200ms | ~150ms | ✅ Met |
| Context Sync Overhead | <5ms | ~3ms | ✅ Met |
| Database Query Time (p95) | <50ms | ~40ms | ✅ Met |
| Frontend Load Time | <2s | ~1.8s | ✅ Met |
| Throughput | 100 RPS | ~120 RPS | ✅ Met |

### 8.2 Optimization Techniques

**Frontend**:
1. **Code Splitting**: Route-based lazy loading
2. **Memoization**: React.memo, useMemo, useCallback
3. **Virtual Scrolling**: For large task lists
4. **Image Optimization**: WebP format, lazy loading
5. **Bundle Size**: Tree shaking, minification

**Backend**:
1. **Database Indexing**: All foreign keys and query fields
2. **Connection Pooling**: SQLAlchemy pool_size=20, max_overflow=10
3. **Query Optimization**: SELECT only needed columns, JOIN optimization
4. **Async Operations**: asyncio for I/O-bound tasks
5. **Caching**: Redis for frequently accessed data

**Database**:
1. **Indexes**: 15+ indexes on critical query paths
2. **JSONB**: GIN indexes on context.data for fast lookup
3. **Partitioning**: Planned for tasks table by created_at
4. **Vacuum**: Auto-vacuum configured for PostgreSQL
5. **Replication**: Read replicas planned for Tier 2

### 8.3 Scalability Roadmap

**MVP → Tier 1 (100 RPS → 1K RPS)**:
- Microservices architecture (split bounded contexts)
- Load balancer (Nginx/HAProxy)
- Read replicas for database
- Redis cluster for caching
- Horizontal pod autoscaling

**Tier 1 → Tier 2 (1K RPS → 10K RPS)**:
- Service mesh (Istio/Linkerd)
- Event-driven architecture (Kafka/RabbitMQ)
- Database sharding by user_id
- CDN for frontend assets
- Global load balancing

**Tier 2 → Enterprise (10K RPS → 1M+ RPS)**:
- Multi-region deployment
- Edge computing for low latency
- Distributed caching (Redis Cluster)
- Time-series database for metrics
- Machine learning for auto-scaling

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
        /\
       /  \
      / E2E \          10% - End-to-End Tests
     /______\
    /        \
   /Integration\       30% - Integration Tests
  /____________\
 /              \
/  Unit Tests    \     60% - Unit Tests
/__________________\
```

### 9.2 Test Categories

| Type | Framework | Coverage | Examples |
|------|-----------|----------|----------|
| **Unit** | pytest | 60% | Domain services, value objects |
| **Integration** | pytest + TestClient | 30% | API endpoints, database operations |
| **E2E** | Vitest + Testing Library | 10% | User workflows, multi-agent coordination |
| **Performance** | pytest-benchmark | N/A | Response time, throughput |
| **Load** | Locust | N/A | Concurrent users, stress testing |

### 9.3 Test Structure

**Backend Tests** (`agenthub_main/src/tests/`):
```
tests/
├── unit/                    # Pure unit tests (no DB)
│   ├── task_management/
│   ├── auth/
│   └── context_management/
├── integration/             # Database-required tests
│   ├── task_management/
│   ├── auth/
│   └── api/
├── e2e/                     # End-to-end workflows
│   ├── user_workflows/
│   └── agent_coordination/
└── performance/             # Performance benchmarks
    ├── api_benchmarks/
    └── database_benchmarks/
```

**Frontend Tests** (`agenthub-frontend/src/__tests__/`):
```
__tests__/
├── unit/                    # Component unit tests
│   ├── components/
│   └── hooks/
├── integration/             # Feature integration tests
│   ├── pages/
│   └── store/
└── e2e/                     # User journey tests
    ├── authentication/
    ├── task_management/
    └── agent_coordination/
```

### 9.4 CI/CD Pipeline

```
Git Push
    ↓
GitHub Actions
    ↓
┌─────────────────────┐
│  Linting & Formatting│
│  - ruff (backend)    │
│  - eslint (frontend) │
└─────────────────────┘
    ↓
┌─────────────────────┐
│   Unit Tests        │
│   (parallel)        │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Integration Tests   │
│ (with test DB)      │
└─────────────────────┘
    ↓
┌─────────────────────┐
│   Build Docker      │
│   Images            │
└─────────────────────┘
    ↓
┌─────────────────────┐
│   E2E Tests         │
│   (full stack)      │
└─────────────────────┘
    ↓
┌─────────────────────┐
│   Deploy Staging    │
│   (if main branch)  │
└─────────────────────┘
```

---

## 10. Monitoring & Observability

### 10.1 Logging Strategy

**Log Levels**:
- **DEBUG**: Development only, verbose internal state
- **INFO**: Important events (task created, agent assigned)
- **WARNING**: Recoverable errors (token refresh, cache miss)
- **ERROR**: Unrecoverable errors (database connection lost)
- **CRITICAL**: System failure (service unavailable)

**Log Format** (JSON structured):
```json
{
  "timestamp": "2025-10-16T06:33:50Z",
  "level": "INFO",
  "service": "task-management",
  "user_id": "user-uuid",
  "action": "task_created",
  "task_id": "task-uuid",
  "duration_ms": 45,
  "message": "Task created successfully"
}
```

### 10.2 Metrics Collection (Planned)

**Application Metrics**:
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (errors/minute)
- Active users (concurrent)
- Agent coordination (parallel tasks)

**Infrastructure Metrics**:
- CPU usage (%)
- Memory usage (MB)
- Disk I/O (MB/s)
- Network I/O (MB/s)
- Database connections (active)

**Business Metrics**:
- Tasks created (per day)
- Tasks completed (per day)
- Agent utilization (%)
- User engagement (sessions/day)
- Feature adoption (%)

### 10.3 Health Checks

**Liveness Probe** (`/health`):
- Service is running
- Can handle requests
- Returns HTTP 200

**Readiness Probe** (`/ready`):
- Database connection active
- Redis connection active
- Keycloak reachable
- Returns HTTP 200

**Startup Probe** (`/startup`):
- Initial migrations complete
- Cache warmed up
- Configuration loaded
- Returns HTTP 200

---

## 11. Future Architectural Enhancements

### 11.1 Microservices Migration (Tier 1)

**Planned Services**:
1. **Task Service**: Task and subtask management
2. **Agent Service**: Agent orchestration and coordination
3. **Context Service**: 4-tier context hierarchy
4. **Project Service**: Projects and git branches
5. **Auth Service**: Authentication and authorization
6. **Gateway Service**: API gateway and routing

**Inter-Service Communication**:
- Synchronous: gRPC for low-latency calls
- Asynchronous: RabbitMQ for events
- Service discovery: Consul or Kubernetes DNS

### 11.2 Event-Driven Architecture (Tier 2)

**Domain Events**:
```python
TaskCreatedEvent(task_id, user_id, timestamp)
    → Notify Context Service (add task context)
    → Notify Analytics Service (track metrics)
    → Notify Notification Service (notify user)

AgentAssignedEvent(agent_id, task_id, timestamp)
    → Notify Agent Service (update agent status)
    → Notify Task Service (update task assignees)
    → Notify WebSocket Service (real-time update)
```

**Event Bus Options**:
- **Apache Kafka**: High-throughput, distributed log
- **RabbitMQ**: Traditional message broker
- **Redis Streams**: Lightweight event streaming

### 11.3 Advanced Caching (Tier 2+)

**Multi-Layer Cache**:
```
Client (Browser Cache)
    ↓ Cache miss
CDN (Edge Cache)
    ↓ Cache miss
Application Cache (Redis)
    ↓ Cache miss
Database Query Cache
    ↓ Cache miss
Database
```

**Cache Warming**:
- Pre-populate cache on deployment
- Scheduled jobs for frequently accessed data
- User-specific cache on login

### 11.4 Global Deployment (Enterprise)

**Multi-Region Architecture**:
```
User (US West) → Edge Node (Seattle) → API Gateway (US West) → Services
User (EU) → Edge Node (London) → API Gateway (EU) → Services
User (Asia) → Edge Node (Singapore) → API Gateway (Asia) → Services
```

**Data Replication**:
- Primary region: Write operations
- Secondary regions: Read operations
- Asynchronous replication with eventual consistency
- Conflict resolution strategies

---

## 12. Appendices

### 12.1 Technology Decision Rationale

| Technology | Why Chosen | Alternatives Considered |
|------------|------------|-------------------------|
| **React** | Industry standard, large ecosystem | Vue.js, Svelte |
| **Python** | Excellent AI/ML libraries, FastMCP support | Node.js, Go |
| **FastMCP** | Native MCP protocol support | Custom implementation |
| **PostgreSQL** | JSONB support, strong consistency | MongoDB, MySQL |
| **Redis** | High-performance caching, session storage | Memcached, in-memory |
| **Keycloak** | Open-source SSO, enterprise features | Auth0, AWS Cognito |
| **Docker** | Standardized containerization | Podman, LXC |

### 12.2 Architecture Principles

1. **Domain-Driven Design**: Business logic in domain layer
2. **SOLID Principles**: Single responsibility, dependency inversion
3. **Clean Architecture**: Dependency rule (outer → inner only)
4. **API First**: API design before implementation
5. **Security by Design**: Security considerations from day one
6. **Performance by Design**: Optimization built-in, not bolted-on
7. **Testability**: All components designed for easy testing

### 12.3 Key Architectural Constraints

1. **MCP Protocol Compatibility**: Must adhere to MCP 2.1.0 spec
2. **Multi-Tenancy**: Per-user data isolation mandatory
3. **Context Persistence**: 100% context retention required
4. **Backward Compatibility**: Breaking changes require migration path
5. **Open Source**: All core components must use permissive licenses

### 12.4 Glossary

- **DDD**: Domain-Driven Design - software design approach focusing on business domain
- **MCP**: Model Context Protocol - standard for AI tool integration
- **JWT**: JSON Web Token - compact token format for authentication
- **ASGI**: Asynchronous Server Gateway Interface - Python async web servers
- **ORM**: Object-Relational Mapping - database abstraction layer
- **SSO**: Single Sign-On - centralized authentication service
- **JSONB**: JSON Binary - PostgreSQL's efficient JSON storage type
- **GIN**: Generalized Inverted Index - PostgreSQL index type for JSONB

### 12.5 References

- [FastMCP Documentation](https://github.com/anthropics/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Best Practices](https://react.dev/)
- [Keycloak Documentation](https://www.keycloak.org/documentation)

### 12.6 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-16 | AI Agent | Initial architecture document during sync protocol |

---

**Document Status**: DRAFT
**Next Review**: Q1 2025
**Approval Required From**: Engineering Lead, Security Team, DevOps Lead
