# agenthub Backend

> Advanced MCP server framework with integrated AI agent orchestration and task management

## Overview

agenthub Backend is a production-ready Python backend built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) framework, implementing Domain-Driven Design (DDD) principles for AI agent orchestration, task management, and real-time collaboration.

### Key Features

| Feature | Description |
|---------|-------------|
| **MCP Protocol** | Full Model Context Protocol implementation with streamable HTTP transport |
| **DDD Architecture** | 4-layer architecture (Domain, Application, Infrastructure, Interface) |
| **Task Management** | Enterprise-grade task, subtask, and dependency management |
| **Agent Orchestration** | 32+ specialized AI agents with dynamic role switching |
| **Context Hierarchy** | 4-tier context system (Global → Project → Branch → Task) |
| **Real-time Sync** | WebSocket v2.0 protocol with instant UI updates |
| **Authentication** | Keycloak integration with JWT tokens and RBAC |
| **Multi-tenancy** | Complete user data isolation with tenant support |
| **Database Support** | PostgreSQL (production) and SQLite (development) |

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.11+ (3.14 in production) |
| **Framework** | FastMCP | 1.9.4+ |
| **Web Server** | Uvicorn | 0.34.3+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database** | PostgreSQL / SQLite | 15+ / 3.x |
| **Auth** | Keycloak + JWT | - |
| **API Framework** | FastAPI | 0.115.12+ |
| **Testing** | Pytest | 8.3.3+ |
| **Package Manager** | uv | Latest |

## Quick Start

### Prerequisites

```bash
# Required
- Python 3.11+
- PostgreSQL 15+ (or SQLite for dev)
- Git

# Optional
- Docker & docker-compose
- uv (Python package manager)
```

### Installation

```bash
# 1. Navigate to backend directory
cd agenthub_main

# 2. Install dependencies using uv (recommended)
pip install uv
uv pip install -e .

# Or use pip
pip install -e .

# 3. Set up environment variables
cp ../.env.example ../.env
# Edit .env with your database and auth settings

# 4. Initialize database
python init_database.py

# 5. Start the server
python -m fastmcp.server.mcp_entry_point
```

The server will start on `http://localhost:8000`

### Docker Setup (Recommended for Production)

```bash
# From project root
cd docker-system
./docker-menu.sh

# Select option for your environment:
# - Development: PostgreSQL Local (option 3)
# - Production: Full deployment (option 1)
```

## Architecture

### 4-Layer DDD Structure

```
src/fastmcp/
├── domain/                    # Business logic & entities
│   ├── entities/             # Core business objects (Task, Agent, Context)
│   ├── value_objects/        # Immutable value types (TaskId, Priority)
│   ├── services/             # Domain services
│   └── events/               # Domain events
│
├── application/              # Use cases & orchestration
│   ├── facades/              # Application facades (TaskFacade)
│   ├── use_cases/            # Business workflows
│   └── dtos/                 # Data transfer objects
│
├── infrastructure/           # External concerns
│   ├── repositories/         # Data persistence
│   ├── database/             # Database configuration
│   ├── websocket/            # WebSocket protocol
│   ├── cache/                # Caching layer
│   └── ai_services/          # AI integrations
│
└── interface/                # External interface
    ├── controllers/          # MCP controllers
    └── routes/               # REST API routes
```

### Request Flow

```
Client Request
    ↓
MCP Transport (WebSocket/HTTP)
    ↓
Auth Middleware (JWT validation)
    ↓
Interface Layer (Controller)
    ↓
Application Layer (Facade/Use Case)
    ↓
Domain Layer (Entity/Service)
    ↓
Infrastructure Layer (Repository)
    ↓
Database (PostgreSQL/SQLite)
```

## Directory Structure

```
agenthub_main/
├── src/
│   ├── fastmcp/              # Main application code
│   │   ├── task_management/  # Task management module
│   │   ├── connection_management/  # Connection handling
│   │   ├── ai_task_planning/ # AI planning features
│   │   ├── server/           # Server configuration
│   │   └── middleware/       # Request middleware
│   ├── config/               # Configuration files
│   └── tests/                # Test suites
│       ├── unit/             # Unit tests
│       ├── integration/      # Integration tests
│       └── e2e/              # End-to-end tests
│
├── scripts/                  # Utility scripts
│   ├── init_database.py      # Database initialization
│   ├── test-menu.sh          # Test runner menu
│   └── verify_init_schema.py  # Schema verification
│
├── agent-library/            # 32+ specialized agents
│   └── agents/
│       ├── master-orchestrator-agent/
│       ├── coding-agent/
│       ├── test-orchestrator-agent/
│       └── ...
│
├── alembic/                  # Database migrations
├── config/                   # Environment configs
├── logs/                     # Application logs
├── pyproject.toml            # Project dependencies
└── README.md                 # This file
```

## Development

### Environment Variables

Create `.env` file in project root with:

```bash
# Database Configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=agenthub
DATABASE_USER=agenthub_user
DATABASE_PASSWORD=your_password

# Server Configuration
FASTMCP_PORT=8000
FASTMCP_TRANSPORT=streamable-http
ENV=development
APP_DEBUG=true

# Authentication
AUTH_ENABLED=true
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak-server
KEYCLOAK_REALM=agenthub
KEYCLOAK_CLIENT_ID=agenthub-backend
KEYCLOAK_CLIENT_SECRET=your_secret
JWT_SECRET_KEY=your-jwt-secret-min-32-chars

# Feature Flags
FEATURE_HIERARCHICAL_CONTEXT=true
FEATURE_MULTI_AGENT=true
FEATURE_VISION_SYSTEM=true
FEATURE_RATE_LIMITING=false
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests
pytest -m e2e              # End-to-end tests

# Run with coverage
pytest --cov=src --cov-report=html

# Use test menu for interactive selection
./scripts/test-menu.sh
```

### Database Management

```bash
# Initialize database
python init_database.py

# Verify schema
python scripts/verify_init_schema.py

# Generate new migration
alembic revision --autogenerate -m "Description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
ruff format src/

# Lint code
ruff check src/

# Type checking
pyright src/

# Run all checks
ruff check src/ && ruff format src/ --check && pyright src/
```

## Key Modules

### Task Management (`task_management/`)

Enterprise task orchestration with:
- Hierarchical tasks and subtasks
- Dependency management
- Progress tracking
- AI-powered planning
- Real-time WebSocket updates

### Context System (`context_management/`)

4-tier context hierarchy:
1. **Global** - User-level settings and preferences
2. **Project** - Project-specific configuration
3. **Branch** - Git branch context
4. **Task** - Task-specific data

Each level inherits from parent with automatic propagation.

### Agent Orchestration (`agent_management/`)

32+ specialized agents including:
- `master-orchestrator-agent` - Coordination and planning
- `coding-agent` - Code implementation
- `test-orchestrator-agent` - Testing coordination
- `security-auditor-agent` - Security analysis
- `documentation-agent` - Documentation generation
- And 27+ more specialized agents

### Authentication (`server/auth/`)

- Keycloak SSO integration
- JWT token validation (RS256/HS256)
- RBAC (Role-Based Access Control)
- Multi-tenant isolation
- Session management

### WebSocket Protocol v2.0 (`infrastructure/websocket/`)

Real-time updates for:
- Task creation/update/completion/deletion
- Subtask operations
- Context changes
- Agent status updates

## API Endpoints

### Health Check
```http
GET /health
```

### MCP Tools (via MCP protocol)
```
manage_task          # Task CRUD operations
manage_subtask       # Subtask operations
manage_context       # Context management
manage_project       # Project operations
manage_git_branch    # Git branch management
manage_agent         # Agent registration and assignment
call_agent           # Load agent configuration
```

### REST API (Alternative)
```http
POST /api/tasks           # Create task
GET /api/tasks/:id        # Get task
PUT /api/tasks/:id        # Update task
DELETE /api/tasks/:id     # Delete task
```

## Deployment

### Production Dockerfile

Built with multi-stage builds:
- Stage 1: Dependency installation with `uv`
- Stage 2: Production runtime with security hardening
- Non-root user execution
- Health checks enabled
- Minimal image size

```bash
# Build production image
docker build -f docker-system/docker/Dockerfile.backend.production -t agenthub-backend:prod .

# Run production container
docker run -p 8000:8000 --env-file .env agenthub-backend:prod
```

### Environment-Specific Configs

| Environment | Database | Auth | Features |
|------------|----------|------|----------|
| **Development** | SQLite or Local PostgreSQL | Optional | All enabled |
| **Production** | PostgreSQL | Keycloak | Rate limiting, monitoring |
| **Testing** | SQLite in-memory | Disabled | Minimal |

## Performance & Monitoring

### Metrics (Prometheus)

```python
# Exposed at /metrics
- task_operations_total
- task_creation_duration_seconds
- active_websocket_connections
- database_query_duration_seconds
```

### Logging

```python
# Structured JSON logging
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json|text
```

### Caching

- Redis for session persistence
- In-memory cache for frequently accessed data
- Cache invalidation via domain events

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Import errors** | Ensure `PYTHONPATH` includes `src/`: `export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"` |
| **Database connection failed** | Check PostgreSQL is running and credentials in `.env` |
| **Port already in use** | Change `FASTMCP_PORT` in `.env` or kill process on port 8000 |
| **JWT validation fails** | Verify `JWT_SECRET_KEY` matches between backend and Keycloak |
| **Tests fail with DB errors** | Run `python init_database.py` to initialize test database |

### Debug Mode

```bash
# Enable debug logging
export APP_DEBUG=true
export APP_LOG_LEVEL=DEBUG

# Start with verbose output
python -m fastmcp.server.mcp_entry_point --log-level DEBUG
```

## Contributing

1. Follow DDD architecture patterns
2. Write tests for all new features (target 80% coverage)
3. Use type hints (Python 3.11+ typing)
4. Run code quality checks before commit
5. Update CHANGELOG.md for all changes

### Code Style

- Follow PEP 8
- Use `ruff` for linting and formatting
- Type hints required (checked by `pyright`)
- Docstrings for all public APIs

## License

Apache-2.0

## Links

- **Project Homepage**: https://github.com/agenthub/agenthub
- **Documentation**: See `../ai_docs/` directory
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Issue Tracker**: https://github.com/agenthub/agenthub/issues

---

**Version**: 0.0.6 (auto-versioned from git tags)

**Python**: 3.11+ required | 3.14 recommended for production

**Status**: Active Development - Breaking changes may occur
