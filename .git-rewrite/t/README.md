# DhafnckMCP - Agentic Project Platform

[![Architecture Status](https://img.shields.io/badge/Architecture-Production%20NOT%20Ready-brightgreen)](https://github.com/dhafnck/dhafnck_mcp)
[![MCP Version](https://img.shields.io/badge/MCP-2.1.0-blue)](https://github.com/dhafnck/dhafnck_mcp)
[![Docker Support](https://img.shields.io/badge/Docker-Multi%20Mode-orange)](https://github.com/dhafnck/dhafnck_mcp)

## 🎯 **Project Overview**

DhafnckMCP is an enterprise-grade Model Context Protocol (MCP) platform designed for agentic project management and multi-agent orchestration. The platform provides comprehensive task management, project coordination, and AI agent collaboration capabilities with cloud-scale architecture.

### 🏗️ **Core Architecture**

- **MCP Server**: FastMCP-based server with streamable HTTP transport
- **Task Management**: Comprehensive DDD-compliant task lifecycle management
- **Agent Orchestration**: Multi-agent coordination with role-based switching
- **Project Management**: Hierarchical project organization with context inheritance
- **Frontend Dashboard**: React-based monitoring and control interface
- **Docker Infrastructure**: Multi-mode containerized deployment

## 🚀 **Quick Start**

### Prerequisites

- **Python 3.8+** with virtual environment support
- **Docker & Docker Compose** for containerized deployment
- **Node.js 18+** for frontend development (optional)
- **WSL2** (Windows users) or **Linux/macOS**

### 🐳 **Docker Setup (Recommended)**

The project includes a sophisticated Docker management system with multiple operational modes:

```bash
# Clone the repository
git clone <repository-url>
cd agentic-project

# Quick start with Docker (interactive menu)
./docker-menu.sh  # Can run from project root
# OR
cd docker-system && ./docker-menu.sh

# The menu provides multiple configuration options:
# - PostgreSQL Local (Backend + Frontend) 
# - Supabase Cloud (No Redis) - RECOMMENDED
# - Supabase Cloud + Redis (Full Stack)
# - Performance Mode for low-resource PCs
```

### 🎯 **MCP Usage Examples**

#### First Steps with MCP Tools:
```python
# 1. Switch to appropriate agent for your task
mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")

# 2. Check system health
mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# 3. Create or get a project
project = mcp__dhafnck_mcp_http__manage_project(
    action="create",
    name="my-new-feature",
    description="Implementing user authentication"
)

# 4. Create a git branch (task tree)
branch = mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id=project["project"]["id"],
    git_branch_name="feature/auth",
    git_branch_description="JWT authentication implementation"
)

# 5. Create a task
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch["git_branch"]["id"],
    title="Implement login endpoint",
    description="Create POST /auth/login with JWT",
    priority="high"
)

# 6. Update context for knowledge sharing
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task["task"]["id"],
    git_branch_id=branch["git_branch"]["id"],
    data={
        "technical_approach": "Using JWT with refresh tokens",
        "dependencies": ["bcrypt", "jsonwebtoken"],
        "api_design": {"endpoint": "/auth/login", "method": "POST"}
    }
)
```

#### Available Docker Configurations

| Configuration | Menu Option | Description | Requirements |
|---------------|-------------|-------------|--------------|
| **PostgreSQL Local** | Option 1 | Local PostgreSQL database | No external dependencies |
| **Supabase Cloud** | Option 2 ⭐ | Cloud database (Supabase) - RECOMMENDED | Requires .env with Supabase credentials |
| **Supabase + Redis** | Option 3 | Cloud DB with Redis cache | Requires .env + Redis setup |
| **Performance Mode** | Option P | Optimized for low-resource PCs | For systems with limited RAM/CPU |

### 📊 **Frontend Dashboard**

The project includes a comprehensive React-based dashboard:

- **Access via Docker**: http://localhost:3000 (automatic when using Docker)
- **Backend API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## 🛠️ **MCP Tools & Capabilities**

### Core MCP Tools

The platform provides 50+ MCP tools organized into functional categories:

#### 🎯 **Task Management**
- `mcp__dhafnck_mcp_http__manage_task`: Complete task lifecycle management
- `mcp__dhafnck_mcp_http__manage_subtask`: Subtask creation and tracking
- `mcp__dhafnck_mcp_http__manage_dependencies`: Task dependency management
- `mcp__dhafnck_mcp_http__manage_git_branch`: Hierarchical task organization

#### 🤖 **Agent Orchestration**
- `mcp__dhafnck_mcp_http__call_agent`: Dynamic agent role switching
- `mcp__dhafnck_mcp_http__manage_agent`: Agent registration and management
- `mcp__dhafnck_mcp_http__agent_coordination`: Multi-agent collaboration

#### 📋 **Project Management**
- `mcp__dhafnck_mcp_http__manage_project`: Project creation and management
- `mcp__dhafnck_mcp_http__manage_git_branch`: Git branch coordination

#### 🔄 **Context Management**
- `mcp__dhafnck_mcp_http__manage_context`: Unified context management with inheritance
- `mcp__dhafnck_mcp_http__manage_delegation_queue`: Context delegation
- `mcp__dhafnck_mcp_http__validate_context_inheritance`: Context validation

#### 🛡️ **Security & Compliance**
- `mcp__dhafnck_mcp_http__manage_compliance`: Compliance tracking
- `mcp__dhafnck_mcp_http__validate_token`: Authentication validation
- `mcp__dhafnck_mcp_http__manage_connection`: Connection management

### 🎨 **Agent Roles & Specializations**

The platform supports 20+ specialized AI agents:

| Agent | Role | Specialization |
|-------|------|----------------|
| `@uber_orchestrator_agent` | System Orchestrator | Complex task coordination |
| `@coding_agent` | Development | Code implementation |
| `@debugger_agent` | Debugging | Error resolution |
| `@test_orchestrator_agent` | Testing | QA and validation |
| `@ui_designer_agent` | Design | UI/UX development |
| `@security_auditor_agent` | Security | Security assessment |
| `@devops_agent` | DevOps | Infrastructure management |
| `@documentation_agent` | Documentation | Technical writing |
| `@deep_research_agent` | Research | Analysis and investigation |
| `@task_planning_agent` | Planning | Project planning |

## 🐳 **Docker Management**

### ⚠️ **IMPORTANT: Use Docker System Menu Only**

**Always use the Docker system menu (`docker-system/docker-menu.sh`) for ALL Docker operations.**  
**DO NOT use direct docker or docker-compose commands.**

```bash
# ✅ CORRECT - Use the interactive menu
./docker-system/docker-menu.sh

# ❌ WRONG - Never use these directly:
# docker-compose up
# docker build
# docker-compose -f docker-compose.yml up
```

### 📋 **Docker System Menu Guide**

When you run `./docker-system/docker-menu.sh`, you'll see this interactive menu:

```
╔════════════════════════════════════════════════╗
║        DhafnckMCP Docker Management            ║
║           Build System v3.0                    ║
╚════════════════════════════════════════════════╝

Build Configurations
────────────────────────────────────────────────
  1) 🐘 PostgreSQL Local (Backend + Frontend)
  2) ☁️  Supabase Cloud (No Redis)
  3) ☁️🔴 Supabase Cloud + Redis (Full Stack)

⚡ Performance Mode (Low-Resource PC)
────────────────────────────────────────────────
  P) 🚀 Start Optimized Mode (Uses less RAM/CPU)
  M) 📊 Monitor Performance (Live stats)

Management Options
────────────────────────────────────────────────
  4) 📊 Show Status
  5) 🛑 Stop All Services
  6) 📜 View Logs
  7) 🗄️  Database Shell
  8) 🧹 Clean Docker System
  9) 🔄 Force Complete Rebuild (removes all images)
  0) 🚪 Exit
```

### 🚀 **Step-by-Step Docker Setup**

#### First Time Setup:
1. Run `./docker-system/docker-menu.sh`
2. Choose your configuration:
   - **Option 1**: PostgreSQL Local (most common)
   - **Option 2**: Supabase Cloud (requires .env setup)
   - **Option 3**: Supabase + Redis (full stack)

#### Daily Development:
1. Run `./docker-system/docker-menu.sh`
2. Select your preferred configuration (1, 2, or 3)
3. **Note**: All builds use `--no-cache` to ensure latest code changes

#### After Code Changes:
1. Run `./docker-system/docker-menu.sh`
2. Select **Option 9** (Force Complete Rebuild) to remove all images
3. Then select your configuration (1, 2, or 3) to rebuild and start

#### Low-Resource PC:
1. Run `./docker-system/docker-menu.sh`
2. Select **P** for Performance Mode (uses less RAM/CPU)
3. Select **M** to monitor performance

### 📊 **Menu Options Explained**

| Option | Purpose | When to Use |
|--------|---------|-------------|
| **1** | PostgreSQL Local | Standard local development |
| **2** | Supabase Cloud | Cloud database (needs .env) |
| **3** | Supabase + Redis | Full stack with caching |
| **P** | Performance Mode | Low-resource computers |
| **M** | Monitor Performance | Check resource usage |
| **4** | Show Status | Check running services |
| **5** | Stop All Services | End work session |
| **6** | View Logs | Debug issues |
| **7** | Database Shell | Direct DB access |
| **8** | Clean Docker System | Free up space |
| **9** | Force Complete Rebuild | After major changes |
| **0** | Exit | Leave menu |

### ⚠️ **Common Mistakes to Avoid**

```bash
# ❌ DON'T use these commands:
docker-compose up -d
docker build -t dhafnck-mcp .
docker-compose down
docker ps
docker exec -it container-name bash

# ✅ ALWAYS use the menu:
./docker-system/docker-menu.sh
# Then select the appropriate option
```

### 🆘 **Troubleshooting Guide**

**If containers won't start:**
```bash
./docker-system/docker-menu.sh
# Select 5 (Stop all)
# Select 7 (Rebuild)
# Select 1-4 (Start in desired mode)
```

**For database issues:**
```bash
./docker-system/docker-menu.sh
# Select 10 (Database operations)
# Choose "Fix database permissions"
```

**To view logs:**
```bash
./docker-system/docker-menu.sh
# Select 8 (View logs)
```

### Docker Architecture (Managed by Menu)

The menu system manages these Docker configurations:

#### Configuration Files:
- **PostgreSQL Local**: `docker-compose.postgresql.yml`
- **Supabase Cloud**: `docker-compose.supabase.yml`
- **Redis Extension**: `docker-compose.redis.yml`

#### Key Features:
- **Automatic Port Management**: Frees ports 8000 and 3800 before starting
- **--no-cache Builds**: Ensures latest code changes are always included
- **Clean Build System**: Option 9 removes all images for fresh rebuild
- **Performance Mode**: Special optimization for low-resource PCs
- **Python Cache Cleanup**: Automatically clears `__pycache__` files

## 🏗️ **Architecture Overview**

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Dashboard                        │
│                 (React + TypeScript)                        │
│                  Port: 3800                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                  MCP Server                                 │
│              (FastMCP + Python)                             │
│                  Port: 8000                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Task Mgmt   │ │ Agent Orch  │ │ Project Mgmt│          │
│  │             │ │             │ │             │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────┬───────────────────────────────────────┘
                      │ PostgreSQL
┌─────────────────────▼───────────────────────────────────────┐
│                  Database Layer                             │
│          (PostgreSQL + Redis Cache)                        │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Tasks       │ │ Projects    │ │ Agents      │          │
│  │ Context     │ │ Rules       │ │ Sessions    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### DDD Architecture

The platform follows Domain-Driven Design principles:

```
Interface Layer (MCP Controllers)
    ↓
Application Layer (Facades & Use Cases)
    ↓
Domain Layer (Entities & Business Logic)
    ↓
Infrastructure Layer (Repositories & Services)
```

## 📊 **Performance & Scaling**

### Current Performance Metrics

- **Scale**: 50-100 RPS (Python monolith)
- **Response Time**: <200ms average
- **Concurrent Users**: 10-50 users
- **Database**: PostgreSQL with Redis cache (primary), Supabase cloud option
- **Availability**: 95%+

### Scaling Roadmap

| Tier | Target RPS | Architecture | Timeline | Investment |
|------|------------|--------------|----------|------------|
| **MVP** | 100 | Docker + PostgreSQL | Current | $0 |
| **Tier 1** | 1K | Microservices | 3 months | $210K |
| **Tier 2** | 10K | Service Mesh | 6 months | $580K |
| **Tier 4** | 1M+ | Global Edge | 12 months | $2.24M |

## 🔒 **Security & Authentication**

### Security Features

- **Token-based Authentication**: JWT with Supabase integration
- **Rate Limiting**: Per-user and per-endpoint limits
- **Access Control**: Role-based permissions
- **Audit Logging**: Comprehensive security event tracking
- **Connection Security**: TLS/SSL encryption

### Authentication Flow

```bash
# Generate authentication token
curl -X POST http://localhost:8000/auth/token

# Use token in MCP calls
mcp__dhafnck_mcp_http__validate_token(token="your-token-here")

# Check authentication status
mcp__dhafnck_mcp_http__get_auth_status()
```

## 🧪 **Testing & Quality Assurance**

### Test Categories

- **Unit Tests**: Domain logic and business rules
- **Integration Tests**: MCP tool integration
- **E2E Tests**: Full workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Penetration testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run E2E tests in Docker
docker exec -it dhafnck-mcp-server pytest /app/tests/e2e

# Performance testing
python tests/performance/mcp_performance_tests.py
```

## 📈 **Monitoring & Observability**

### Health Monitoring

```bash
# Server health check
curl http://localhost:8000/health

```

## 🛠️ **Development Guide**

### Project Structure

```
agentic-project/
├── dhafnck_mcp_main/           # MCP server implementation
│   ├── src/fastmcp/            # FastMCP framework
│   │   ├── task_management/    # Task management domain
│   │   ├── server/             # MCP server core
│   │   └── auth/               # Authentication system
│   ├── docker/                 # Docker configuration
│   ├── tests/                  # Test suites
│   └── scripts/                # Utility scripts
├── dhafnck-frontend/           # React dashboard
│   ├── src/                    # Frontend source
│   ├── public/                 # Static assets
│   └── docker/                 # Frontend Docker config
├── docker-system/              # Docker management system
│   ├── docker-menu.sh          # Main Docker menu script
│   └── docker/                 # Docker configurations
└── README.md                   # This file
```

### Development Workflow

1. **Setup Environment**
   ```bash
   ./docker-system/docker-menu.sh
   # Select Option 1, 2, or 3 based on your needs
   ```

2. **Make Changes**
   - Backend: Edit files in `dhafnck_mcp_main/src/`
   - Frontend: Edit files in `dhafnck-frontend/src/`
   - Note: All builds use `--no-cache`, no hot reload

3. **Rebuild After Changes**
   ```bash
   ./docker-system/docker-menu.sh
   # Select Option 9 (Force Complete Rebuild)
   # Then select your configuration (1, 2, or 3)
   ```

4. **Debug Issues**
   - View logs: Option 6 in Docker menu
   - Database shell: Option 7 in Docker menu
   - Check container status: Option 4 in Docker menu

### Contributing Guidelines

1. **Code Style**: Follow PEP 8 for Python, ESLint for TypeScript
2. **Testing**: Maintain 80%+ test coverage
3. **Documentation**: Update README and inline docs
4. **Security**: Follow security best practices
5. **Performance**: Consider performance impact of changes

## 🚀 **Deployment**

### Production Deployment

```bash
# Use Docker menu for production
./docker-system/docker-menu.sh
# Select Option 1 (PostgreSQL Local) for standard deployment
# Or Option 2/3 for cloud-based deployment
```

### Environment Configuration

```bash
# Key environment variables
FASTMCP_TRANSPORT=streamable-http
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
DHAFNCK_AUTH_ENABLED=true
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### Health Checks

The platform includes comprehensive health monitoring:

```bash
# Use Docker menu for all health checks
./docker-system/docker-menu.sh

# Option 4: Show Status (container health)
# Option 6: View Logs (application logs)
# Option 7: Database Shell (direct DB access)

# Quick health check via API
curl http://localhost:8000/health
```

## 📞 **Support & Troubleshooting**

### Common Issues

1. **Port Conflicts**: Change ports in docker-compose files
2. **Database Permissions**: Use "Fix Database Permissions" in Docker menu
3. **Memory Issues**: Increase Docker memory allocation
4. **SSL Errors**: Check network configuration and certificates

### Troubleshooting Tools

- **MCP Inspector**: Debug MCP server communication
- **Container Logs**: Real-time log monitoring
- **Health Endpoints**: System status validation
- **Database Tools**: Direct database access and repair

### Getting Help

- **Documentation**: Check `/docs` directory for detailed guides
- **Logs**: Use Docker menu to view real-time logs
- **Community**: Join our Discord/Slack channels
- **Issues**: Report bugs on GitHub issues

## 🎯 **Roadmap**

### Current Phase: Production NOT Ready MVP

- ✅ **Core MCP Tools**: 50+ tools implemented
- ✅ **Docker Infrastructure**: Multi-mode deployment
- ✅ **Agent Orchestration**: 20+ specialized agents
- ✅ **Frontend Dashboard**: React-based monitoring
- ❌ **Security Framework**: Authentication and authorization

### Next Phase: Scaling (Q2 2025)

- 🎯 **Microservices**: Break monolith into services
- 🎯 **Kubernetes**: Container orchestration
- 🎯 **API Gateway**: Centralized API management
- 🎯 **Monitoring**: Prometheus + Grafana
- 🎯 **CI/CD**: Automated deployment pipelines

### Future Phase: Enterprise (Q3-Q4 2025)

- 🔮 **Global CDN**: Edge deployment
- 🔮 **Auto-scaling**: Dynamic resource allocation
- 🔮 **AI Enhancement**: ML-powered optimization
- 🔮 **Enterprise Integration**: SSO and compliance
- 🔮 **Multi-tenant**: SaaS deployment model

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

---

**Last Updated**: 2025-01-15  
**Version**: 0.0.1beta  
**Status**: Production Not Ready MVP  
**Next Milestone**: Microservices Architecture (Q2 2025)

---

### 🔗 **Quick Links**

- **Frontend Dashboard**: http://localhost:3800
- **MCP Server**: http://localhost:8000
- **Health Check**: http://localhost:8000/health  
- **Docker Management**: `./docker-system/docker-menu.sh`

### 📊 **Key Metrics**

- **MCP Tools**: 50+ implemented
- **Agent Roles**: 20+ specialized agents
- **Docker Modes**: 4 operational modes
- **Test Coverage**: 80%+ across all components
- **Performance**: 100 RPS current, 1M+ RPS target