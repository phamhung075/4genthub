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

**agenthub** revolutionizes human-AI collaboration through an intuitive web-based platform orchestrating human and AI work through a Model Context Protocol (MCP) native architecture. The Python agent library's 42+ specialized agent roles were retired; agents are now registry rows managed through the `manage_agent` MCP tool.

**Problem Solved**:
- Context loss between AI sessions → Context records at four levels behind `/api/v2/contexts/{level}`, plus per-seat composition from company → room → seat overlays
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
3. Context Management (four mounted levels)
4. Project Management
5. Authentication

**Technology Stack**:
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS
- Backend: Go (`agenthub_go`, `cmd/agenthub`), net/http + FastMCP-compatible MCP layer
- Database: PostgreSQL (Postgres-only) + Redis cache
- Auth: Keycloak SSO + JWT tokens
- Protocol: MCP over HTTP (`POST /mcp`, `GET /mcp` SSE)

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
| **Context API** | P0 | ✅ Implemented | Four-level context records with inheritance | `/api/v2/contexts/{level}` (`resolve`, `delegate`, `insights`, `progress`); the live composition model is the seat overlay chain |
| **Agent registry** | P0 | ✅ Implemented | Register and assign agents via MCP | `manage_agent` tool + `agents` table; the 42-role Python agent library was retired |
| **MCP Protocol** | P0 | ✅ Implemented | Industry-standard integration | `POST /mcp` (JSON-RPC) + `GET /mcp` (SSE), 9 published tools |
| **Agent Coordination** | P0 | ✅ Implemented | Multi-agent parallel execution | Real-time collaboration, progress tracking |
| **Keycloak Auth** | P0 | ✅ Implemented | Enterprise SSO + multi-tenancy | JWT tokens, RBAC, session management |
| **WebSocket v2** | P1 | ✅ Implemented | Real-time UI updates | Sub-100ms latency, auto-reconnect |

### Agent Library — retired

The Python agent library (42 role templates across 12 categories: `coding-agent`, `debugger-agent`, `master-orchestrator-agent`, …) and its `call_agent` MCP tool were removed. The Go server keeps only the `agents` registry table and the `manage_agent` MCP tool (register, assign, get, list, update, unassign, unregister, rebalance); `call_agent` survives only as an optional field of `manage_agent`. The "Dynamic Tool Enforcement v2.0" doctrine, which derived tool permissions from the `call_agent` response, went with the tool — tool scope is now per seat.

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
│  • Go HTTP API (net/http)                          │
│  • WebSocket Server (Real-time Updates)            │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  MCP Protocol Layer                                │
│  • MCP Server (Go)                                 │
│  • 9 published MCP tools                           │
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
│  • HTTP Endpoints (net/http)                   │
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
│  • Database Access (Postgres, TableDef)        │
│  • External Service Integrations               │
│  • Caching (Redis)                             │
│  • File System Operations                      │
└─────────────────────────────────────────────────┘
```

### Bounded Contexts

| Context | Purpose | Entities | Location |
|---------|---------|----------|----------|
| **Task Management** | Hierarchical task structures | Task, Subtask, TaskDependency | `task_management/` |
| **Agent Orchestration** | Agent registry coordination | Agent | `task_management/interface/mcp_controllers/agent_mcp_controller/` |
| **Context Management** | Context records at four levels | GlobalContext, ProjectContext, BranchContext, TaskContext | `context_management/` |
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

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language / runtime | Go (`agenthub_go`, `cmd/agenthub`) | HTTP server, MCP layer |
| Web framework | `net/http` (`fastmcp/server/httpapp`) | HTTP API |
| DB access | generated `TableDef` metadata (`database.Tables`), Postgres driver | Database access |
| Schema creation | `DatabaseConfig.CreateTables`, gated by `AUTO_MIGRATE=true` | Schema creation |
| Cache | Redis decorators + in-process cache | Caching layer |
| MCP transport | `POST /mcp` (JSON-RPC), `GET /mcp` (SSE) | MCP protocol |

### MCP Tools (9 published)

| Tool | Purpose |
|------|---------|
| **manage_task** | Task CRUD, search, dependencies, AI planning |
| **manage_subtask** | Subtask CRUD, progress tracking, completion |
| **manage_project** | Project lifecycle, health checks, validation |
| **manage_git_branch** | Branch CRUD, agent assignment, statistics |
| **manage_context** | 4-tier context hierarchy, inheritance, delegation |
| **manage_agent** | Agent registry: register, assign, update |
| **manage_seat** | Seat list/get/set_occupant (Go-only) |
| **call_seat** | Resolve one seat and its rendered context files (Go-only) |
| **manage_connection** | System health |

`initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list` and `notifications/initialized` are JSON-RPC protocol methods, not tools. The retired `call_agent` tool and the never-published `manage_delegation_queue`, `manage_compliance` and `manage_rule` names are not part of the surface (`ai_docs/api-integration/surface-inventory.md` §2).

### Database Schema

**Core Tables** (full list: `ai_docs/api-integration/surface-inventory.md` §3):
- `tasks` - Task entities with hierarchical structure
- `subtasks` - Granular task decomposition
- `projects` - Project definitions
- `project_git_branchs` - Git branch tracking
- `agents` - Agent registry
- `global_contexts`, `project_contexts`, `branch_contexts`, `task_contexts` - Context records at the four levels (`/api/v2/contexts/{level}`)
- `users` - User accounts (Keycloak sync)
- `agent_sessions`, `agent_session_events` - Session records

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
| **Authorization** | RBAC + per-seat tool scope (the `call_agent`-based dynamic enforcement was retired) |
| **Data** | Per-user isolation, encrypted at rest |
| **API** | Rate limiting, input validation |
| **Audit** | Complete operation logging |

---

## Release Roadmap

### Milestones

**MVP (Current - v0.0.2)**:
- ✅ Web dashboard with real-time updates
- ✅ Agent registry (`manage_agent`) — the 42-role Python agent library was retired
- ✅ Context API at four levels (`/api/v2/contexts/{level}`)
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
