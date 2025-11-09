# Product & Architecture - Complete Guide

## Quick Reference

| Document | Purpose | Key Sections |
|----------|---------|--------------|
| **Product Vision** | PRD, user personas, feature requirements | Vision, personas, core features, roadmap |
| **Technical Architecture** | DDD layers, bounded contexts, tech stack | System design, DDD layers, deployment tiers |
| **Status** | Production NOT Ready (v0.0.2) | MVP → Enterprise scaling plan |

---

## Executive Summary

### Product Vision

**agenthub** revolutionizes human-AI collaboration through an intuitive web-based platform orchestrating 42+ specialized AI agents via Model Context Protocol (MCP) native architecture.

**Problem Solved**:
- Context loss between AI sessions → Persistent 4-tier context hierarchy
- Tool fragmentation → Unified MCP protocol platform
- Complexity barrier → Web-first visual interface
- Workflow isolation → Multi-agent collaboration
- Progress invisibility → Real-time dashboards

**Success Metrics** (MVP):
- 10-50 concurrent users
- <200ms average response time
- 99.9% uptime for MCP services
- 100% context retention across sessions

### Architecture Overview

**DDD Architecture** with 4 layers (Interface → Application → Domain → Infrastructure) across 5 bounded contexts:
1. Task Management
2. Agent Orchestration
3. Context Management (4-tier hierarchy)
4. Project Management
5. Authentication

**Technology Stack**:
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS
- Backend: Python 3.14 + FastMCP + FastAPI + SQLAlchemy
- Database: PostgreSQL (prod) / SQLite (dev) + Redis cache
- Auth: Keycloak SSO + JWT tokens
- Protocol: MCP 2.1.0 over HTTP

---

## Target Users & Personas

| Persona | Role | Goals | Pain Points | How agenthub Helps |
|---------|------|-------|-------------|-------------------|
| **Solo Developer Sarah** | Full-stack developer | Ship faster, maintain quality | Context loss, tool switching | Persistent context, specialized agents |
| **Tech Lead Thomas** | Team lead (5-10 devs) | Coordinate AI work, consistency | Tracking contributions, quality | Multi-agent coordination, audit trails |
| **Product Manager Patricia** | Non-technical PM | Understand progress | Technical complexity | Web-first interface, visual dashboards |

**Secondary Personas**: DevOps Engineer, Security Auditor, Documentation Writer

---

## Core Features & Requirements

### Feature Matrix

| Feature | Priority | Status | User Story | Key Requirements |
|---------|----------|--------|------------|------------------|
| **Web Dashboard** | P0 | ✅ Implemented | Visual agent management without CLI | Real-time updates, responsive, drag-drop tasks |
| **4-Tier Context** | P0 | ✅ Implemented | AI remembers all context across sessions | Global→Project→Branch→Task, <5ms sync |
| **42+ Agents** | P0 | ✅ Implemented | Expert-level specialized assistance | 12 categories, dynamic tool enforcement |
| **MCP Protocol** | P0 | ✅ Implemented | Industry-standard integration | HTTP transport, 15+ tool categories |
| **Agent Coordination** | P0 | ✅ Implemented | Multi-agent parallel execution | Real-time collaboration, progress tracking |
| **Keycloak Auth** | P0 | ✅ Implemented | Enterprise SSO + multi-tenancy | JWT tokens, RBAC, session management |
| **WebSocket v2** | P1 | ✅ Implemented | Real-time UI updates | Sub-100ms latency, auto-reconnect |

### Agent Categories (42 Total)

| Category | Agents | Responsibilities |
|----------|--------|------------------|
| **Development** (4) | coding-agent, debugger-agent, code-reviewer-agent, prototyping-agent | Code writing, debugging, review |
| **Testing** (3) | test-orchestrator-agent, uat-coordinator-agent, performance-load-tester-agent | QA, UAT, performance |
| **Architecture** (4) | system-architect-agent, design-system-agent, shadcn-ui-expert-agent, core-concept-agent | System design, UI |
| **DevOps** (1) | devops-agent | Infrastructure, deployment |
| **Documentation** (1) | documentation-agent | Technical writing |
| **Project** (4) | project-initiator-agent, task-planning-agent, master-orchestrator-agent, elicitation-agent | Planning, coordination |
| **Security** (3) | security-auditor-agent, compliance-scope-agent, ethical-review-agent | Auditing, compliance |
| **Analytics** (3) | analytics-setup-agent, efficiency-optimization-agent, health-monitor-agent | Metrics, optimization |
| **Marketing** (3) | marketing-strategy-orchestrator, community-strategy-agent, branding-agent | Strategy, branding |
| **Research** (4) | deep-research-agent, llm-ai-agents-research, root-cause-analysis-agent, technology-advisor-agent | Analysis, research |
| **ML** (1) | ml-specialist-agent | Machine learning |
| **Creative** (1) | creative-ideation-agent | Ideation |

**Dynamic Tool Enforcement v2.0**:
- Master orchestrator: Task delegation tools (no file editing)
- Coding agents: File operations (no task delegation)
- Documentation agents: Content creation (limited system access)
- Infrastructure-level enforcement prevents unauthorized tool usage

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────┐
│  Client Layer (Port 3800)                          │
│  • Web Dashboard (React + TypeScript)              │
│  • CLI Tools (MCP Clients)                         │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  API Gateway Layer (Port 8000)                     │
│  • FastAPI Gateway                                 │
│  • WebSocket Server (Real-time Updates)            │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  MCP Protocol Layer                                │
│  • MCP Server (FastMCP Framework)                  │
│  • 15+ Tool Categories                             │
│  • Resource Management                             │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  Business Logic (DDD - 5 Bounded Contexts)         │
│  • Task Management                                 │
│  • Agent Orchestration                             │
│  • Context Management                              │
│  • Project Management                              │
│  • Authentication                                  │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  Data Layer                                        │
│  • PostgreSQL (Primary Database, Port 5432)        │
│  • Redis (Cache & Sessions, Port 6379)             │
│  • File System (Logs & Docs)                       │
└─────────────────────────────────────────────────────┘

External Services:
• Keycloak (Identity Provider)
• AI Models (Claude, GPT, etc.)
```

### DDD Layered Architecture

```
┌─────────────────────────────────────────────────┐
│  INTERFACE LAYER                               │
│  • MCP Controllers                             │
│  • HTTP Endpoints (FastAPI)                    │
│  • WebSocket Handlers                          │
│  • Request/Response DTOs                       │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│  APPLICATION LAYER                             │
│  • Use Cases (Business Workflows)              │
│  • Application Services                        │
│  • Facades (Simplified APIs)                   │
│  • DTOs (Data Transfer Objects)                │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│  DOMAIN LAYER                                  │
│  • Entities (Business Objects)                 │
│  • Value Objects (Immutable Values)            │
│  • Domain Services (Business Logic)            │
│  • Domain Events                               │
│  • Repository Interfaces                       │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│  INFRASTRUCTURE LAYER                          │
│  • Repository Implementations                  │
│  • Database Access (SQLAlchemy)                │
│  • External Service Integrations               │
│  • Caching (Redis)                             │
│  • File System Operations                      │
└─────────────────────────────────────────────────┘
```

### Bounded Contexts

| Context | Purpose | Entities | Location |
|---------|---------|----------|----------|
| **Task Management** | Hierarchical task structures | Task, Subtask, TaskDependency | `task_management/` |
| **Agent Orchestration** | AI agent coordination | Agent, AgentAssignment, AgentCapability | `agent_management/` |
| **Context Management** | 4-tier hierarchy | GlobalContext, ProjectContext, BranchContext, TaskContext | `context_management/` |
| **Project Management** | Projects & git branches | Project, GitBranch, Milestone | `project_management/` |
| **Authentication** | User auth & sessions | User, Session, Role | `auth/` |

---

## Frontend Architecture

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | React | 19.1.0 | UI components |
| Language | TypeScript | 4.9.5 | Type safety |
| Build Tool | Vite | 7.1.3 | Dev server & bundler |
| Styling | Tailwind CSS | 3.4.1 | Utility-first CSS |
| UI Components | shadcn/ui + Material-UI | Latest | Pre-built components |
| State Management | Redux Toolkit | 2.9.0 | Global state |
| Routing | React Router | 7.8.1 | Client-side routing |
| Forms | React Hook Form | 7.62.0 | Form validation |
| Icons | Lucide React + MUI | Latest | Icon libraries |
| Animations | Framer Motion | 12.23.12 | Animations |
| HTTP Client | Fetch API | Native | API communication |

### Component Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # shadcn/ui components
│   ├── features/       # Feature-specific components
│   └── layout/         # Layout components
├── pages/              # Route pages
├── hooks/              # Custom React hooks
├── services/           # API services
├── store/              # Redux store
├── types/              # TypeScript types
└── utils/              # Utility functions
```

### State Management Pattern

- **Global State** (Redux): User auth, agent list, project data
- **Local State** (React hooks): UI state, form state
- **Server State** (React Query): API data caching

---

## Backend Architecture

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastMCP | Custom | MCP server framework |
| Web Framework | FastAPI | 0.104+ | HTTP API |
| ORM | SQLAlchemy | 2.0+ | Database access |
| Migration | Alembic | 1.12+ | Schema migrations |
| Validation | Pydantic | 2.5+ | Data validation |
| Async Runtime | asyncio | Native | Async operations |
| Cache | Redis | 7.0+ | Caching layer |

### MCP Tools (15+ Categories)

| Category | Tools | Purpose |
|----------|-------|---------|
| **Task Management** | manage_task, manage_subtask | CRUD operations, progress tracking |
| **Project** | manage_project, manage_git_branch | Project lifecycle, branch ops |
| **Context** | manage_context | 4-tier context hierarchy |
| **Agent** | manage_agent, call_agent | Agent registration, invocation |
| **Delegation** | manage_delegation_queue | Task delegation |
| **Compliance** | manage_compliance | Security & audit |
| **Rules** | manage_rule | Rule system |
| **Health** | manage_connection | System health |

### Database Schema

**Core Tables**:
- `tasks` - Task entities with hierarchical structure
- `subtasks` - Granular task decomposition
- `projects` - Project definitions
- `git_branches` - Git branch tracking
- `agents` - Agent registry
- `contexts` - 4-tier context storage (global, project, branch, task)
- `users` - User accounts (Keycloak sync)
- `sessions` - Active user sessions

**Relationships**:
- Task → Subtasks (1:many)
- Project → GitBranches (1:many)
- GitBranch → Tasks (1:many)
- Task → Context (1:1)
- Agent → Tasks (many:many via assignments)

---

## Deployment Architecture

### Scaling Tiers

| Tier | RPS | Users | Architecture | Timeline |
|------|-----|-------|--------------|----------|
| **MVP** | 100 | 10-50 | Monolith + Docker | Current |
| **Tier 1** | 1K | 100-500 | Microservices | Q2 2025 |
| **Tier 2** | 10K | 500-5K | Service mesh + CDN | Q3 2025 |
| **Enterprise** | 1M+ | 5K+ | Multi-region + edge | Q4 2025 |

### Docker Deployment

**Configurations**:
1. **PostgreSQL Local**: Full local development (ports 5432, 8000, 3800)
2. **Supabase Cloud**: Remote database integration (ports 8000, 3800)
3. **Supabase + Redis**: Production-like stack (ports 6379, 8000, 3800)

**Environment Variables**:
```bash
# Database
DATABASE_TYPE=postgresql|supabase
DATABASE_URL=postgresql://user:pass@host:port/db

# Authentication
AUTH_ENABLED=true
JWT_SECRET_KEY=your-secret-key

# MCP
FASTMCP_LOG_LEVEL=INFO
ENV=development|production
```

### Performance Targets

| Metric | MVP | Tier 1 | Enterprise |
|--------|-----|--------|-----------|
| API Response | <200ms | <100ms | <50ms |
| WebSocket Latency | <100ms | <50ms | <20ms |
| Context Sync | <5ms | <2ms | <1ms |
| Concurrent Users | 50 | 500 | 5,000+ |
| Database Connections | 20 | 100 | 1,000+ |

---

## Security Architecture

### Authentication Flow

```
User → Keycloak SSO → JWT Token → API Gateway → Validation → MCP Server
```

**Components**:
- **Keycloak**: Identity provider (SSO, user management)
- **JWT Tokens**: Access (1 hour) + Refresh (7 days)
- **Token Validation**: Every API request
- **Session Management**: Redis-backed sessions
- **RBAC**: Role-based access control

### Security Best Practices

| Layer | Implementation |
|-------|---------------|
| **Transport** | HTTPS only (TLS 1.3) |
| **Authentication** | Keycloak SSO + JWT |
| **Authorization** | RBAC + dynamic tool enforcement |
| **Data** | Per-user isolation, encrypted at rest |
| **API** | Rate limiting, input validation |
| **Audit** | Complete operation logging |

---

## Release Roadmap

### Milestones

**MVP (Current - v0.0.2)**:
- ✅ Web dashboard with real-time updates
- ✅ 42+ specialized agents
- ✅ 4-tier context hierarchy
- ✅ Keycloak authentication
- ✅ Docker deployment
- ⏳ Production hardening

**Tier 1 (Q2 2025 - v1.0.0)**:
- Microservices architecture
- Enhanced security (audit logs, GDPR compliance)
- Advanced monitoring (Prometheus, Grafana)
- API rate limiting
- Horizontal scaling (load balancing)

**Tier 2 (Q3 2025 - v2.0.0)**:
- Service mesh (Istio)
- Global CDN
- Multi-region database replication
- Advanced caching strategies
- GraphQL API

**Enterprise (Q4 2025 - v3.0.0)**:
- Multi-region deployment
- Edge computing integration
- Advanced ML features
- Custom agent marketplace
- Enterprise SLA guarantees

---

## Related Documentation
- [Complete Setup Guide](../setup-guides/complete-setup-guide.md)
- [Complete Authentication Guide](../authentication/complete-authentication-guide.md)
- [Development Infrastructure Complete](../development-guides/development-infrastructure-complete.md)
- [Primary System Architecture](../core-architecture/agenthub-system-architecture.md)
