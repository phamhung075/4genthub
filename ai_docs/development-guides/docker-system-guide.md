# 4genthub Docker Development System Guide

## Overview

The 4genthub project includes a sophisticated Docker-based development system designed to streamline the development workflow with multiple deployment configurations and advanced features. The system is managed through `docker-system/docker-menu.sh`, a comprehensive interactive menu system.

## Docker Menu System (`docker-system/docker-menu.sh`)

### Core Features

The Docker menu system provides a unified interface for managing all aspects of the development environment:

**Build Configurations:**
1. **PostgreSQL Local** - Backend + Frontend with local PostgreSQL database
2. **Supabase Cloud** - Uses remote Supabase database (no Redis)
3. **Supabase Cloud + Redis** - Full stack with Supabase and Redis caching

**Development Modes:**
- **Development Mode (Non-Docker)** - Local development with hot reload
- **Performance Mode** - Optimized for low-resource PCs
- **Force Complete Rebuild** - Fresh rebuild removing all cached data

**Management Operations:**
- Service status monitoring
- Log viewing and analysis
- Database shell access
- Docker system cleanup
- Performance monitoring

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Docker Menu System v3.0                     │
├─────────────────────────────────────────────────────────────┤
│  Build Optimization:                                       │
│  • --no-cache builds (ensures fresh code changes)         │
│  • BuildKit optimization (provenance disabled)            │
│  • Automatic port conflict resolution                     │
│  • Python cache clearing                                  │
└─────────────────────────────────────────────────────────────┘
         │
         ├─── PostgreSQL Local ──── Port 5432 (PostgreSQL)
         │                      └── Port 8000 (Backend)
         │                      └── Port 3800 (Frontend)
         │
         ├─── Supabase Cloud ────── Supabase Remote DB
         │                      └── Port 8000 (Backend) 
         │                      └── Port 3800 (Frontend)
         │
         ├─── Redis + Supabase ──── Supabase Remote DB
         │                      └── Port 6379 (Redis)
         │                      └── Port 8000 (Backend)
         │                      └── Port 3800 (Frontend)
         │
         └─── Development Mode ──── Native Python/Node processes
                               └── Hot reload enabled
                               └── Direct filesystem access
```

### Key Scripts and Functions

#### Build Optimization
```bash
set_build_optimization() {
    # Disable slow provenance and SBOM features
    export DOCKER_BUILDKIT_PROVENANCE=false
    export DOCKER_BUILDKIT_SBOM=false  
    export BUILDX_NO_DEFAULT_ATTESTATIONS=true
    
    # Enable BuildKit for better performance
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
}
```

#### Port Management
```bash
check_and_free_ports() {
    # Automatically stops containers using ports 8000 and 3800
    # Ensures clean startup without port conflicts
}
```

#### Build Cleanup
```bash
clean_existing_builds() {
    # Removes existing 4genthub images
    # Clears Python cache files
    # Ensures fresh --no-cache builds
}
```

## Backend MCP Architecture

### Core MCP Server Structure

The backend is built around the FastMCP framework with a comprehensive MCP (Model Context Protocol) server implementation:

```
4genthub_main/src/fastmcp/server/
├── mcp_entry_point.py          # Main entry point with dual auth
├── server.py                   # FastMCP server core
├── connection_manager.py       # Connection state management
├── middleware.py               # Authentication and request middleware
├── http_server.py             # HTTP transport layer
└── dependencies.py            # Dependency injection
```

### Key Components

#### 1. MCP Entry Point (`mcp_entry_point.py`)
- **Dual Authentication**: Supports both JWT tokens and MCP session-based auth
- **Environment Configuration**: Automatically loads .env files and configures logging
- **Database Initialization**: Sets up and validates database schema on startup
- **Middleware Stack**: Configures DualAuthMiddleware and RequestContextMiddleware
- **Transport Selection**: Supports both `stdio` (MCP standard) and `streamable-http` modes

#### 2. DDD-Compliant Tool Registration
```python
# Register DDD-compliant task management tools
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
ddd_tools = DDDCompliantMCPTools()
ddd_tools.register_tools(server)
```

#### 3. Authentication Integration
The system supports dual authentication modes:
- **JWT Authentication**: For web frontend access
- **MCP Session Authentication**: For MCP client access

```python
# Authentication middleware configuration
auth_middleware = AuthMiddleware(secret_key=jwt_secret_key)
middleware_stack = [
    Middleware(DualAuthMiddleware),      # JWT token processing
    Middleware(RequestContextMiddleware), # Context propagation
    Middleware(DebugLoggingMiddleware)   # Request/response logging
]
```

#### 4. Health Check Endpoint
```python
@server.custom_route("/health", methods=["GET"])
async def health_endpoint(request) -> JSONResponse:
    # Provides comprehensive health status
    # Includes connection stats, auth status, and system metrics
```

### MCP Tools Architecture

The system implements 15+ categories of MCP tools:

**Core Tools:**
- `manage_task` - Task CRUD operations
- `manage_subtask` - Subtask management
- `manage_context` - Hierarchical context management
- `manage_project` - Project lifecycle management

**Advanced Tools:**
- `call_agent` - Dynamic agent invocation
- `manage_connection` - Connection health monitoring
- `manage_compliance` - Security and audit compliance
- `manage_rule` - Rule system management

**Specialized Tools:**
- `manage_git_branch` - Git branch operations
- `manage_agent` - Agent registration and assignment
- `manage_delegation_queue` - Task delegation management

## Frontend-Backend Communication

### Communication Architecture

```
Frontend (React/TypeScript)
├── api.ts                     # Main API abstraction layer
├── apiV2.ts                   # Authenticated user-isolated API
├── mcpTokenService.ts         # MCP token management
└── authContext.tsx            # Authentication state management
     │
     │ HTTP/REST
     ▼
Backend (Python/FastMCP)
├── HTTP Server (Port 8000)    # RESTful API endpoints
├── MCP Server (stdio/http)    # MCP protocol communication
└── Dual Authentication        # JWT + MCP session support
```

### API Layers

#### 1. V1 API (Legacy/Anonymous)
```typescript
const API_BASE = "http://localhost:8000/mcp/";
// Direct MCP tool invocation
// No user isolation
// Used for anonymous or fallback access
```

#### 2. V2 API (Authenticated/User-Isolated)
```typescript
const API_BASE_URL = 'http://localhost:8000';
// RESTful endpoints: /api/v2/tasks/, /api/v2/projects/
// JWT authentication required
// User-scoped data isolation
// Automatic token refresh handling
```

### Authentication Flow

```
Frontend Request
├── Check for JWT token in cookies
├── If authenticated → Use V2 API (user-isolated)
├── If not authenticated → Fallback to V1 API (anonymous)
└── Auto-retry on 401 errors with token refresh
     │
     ▼
Backend Processing
├── DualAuthMiddleware processes JWT tokens
├── RequestContextMiddleware propagates user context
├── Route to appropriate handler based on API version
└── Return user-scoped or anonymous data
```

### Data Flow Example

```typescript
// Frontend - Task Creation
const createTask = async (taskData) => {
  if (isAuthenticated()) {
    // Use V2 API - user-isolated
    return taskApiV2.createTask(taskData);
  } else {
    // Use V1 API - anonymous access
    return mcpRequest('manage_task', { action: 'create', ...taskData });
  }
};
```

```python
# Backend - Request Processing
@app.post("/api/v2/tasks/")
async def create_task_v2(request: Request, task_data: TaskCreate):
    # User context automatically available from middleware
    user_id = request.state.user_id
    
    # Create user-scoped task
    return await task_service.create_task(task_data, user_id=user_id)
```

### Connection Management

The system includes sophisticated connection management:

**Connection Health Monitoring:**
- Real-time connection status tracking
- Automatic reconnection handling
- Server restart detection and recovery

**Status Broadcasting:**
- WebSocket-like real-time updates
- Client registration and notification system
- Connection statistics and metrics

## Development Workflows

### 1. Docker Development
```bash
# Interactive menu
./docker-system/docker-menu.sh

# Direct commands
./docker-system/docker-menu.sh start-dev    # Start development mode
./docker-system/docker-menu.sh restart-dev  # Restart with changes
./docker-system/docker-menu.sh stop-dev     # Stop development mode
```

### 2. Configuration Selection

**For Local Development:**
- Use "PostgreSQL Local" for full local database
- Use "Development Mode" for fastest iteration with hot reload

**For Cloud Integration:**
- Use "Supabase Cloud" for remote database testing
- Use "Redis + Supabase" for full production-like stack

**For Low-Resource PCs:**
- Use "Optimized Mode" with resource limits
- Monitor with "Performance Monitor"

### 3. Environment Configuration

The system automatically detects and validates environment variables:

**.env File Requirements:**
```bash
# Database Configuration
DATABASE_TYPE=postgresql|supabase
DATABASE_URL=postgresql://user:pass@host:port/db

# Supabase Configuration (if using Supabase)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Authentication
AUTH_ENABLED=true|false
JWT_SECRET_KEY=your-secret-key

# Development
FASTMCP_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
ENV=development|production
```

### 4. Hot Reload Capabilities

**Backend Hot Reload:**
- Python files automatically reload on change
- FastAPI development server with `--reload`
- Docker volume mounts for real-time code changes

**Frontend Hot Reload:**
- Vite HMR (Hot Module Replacement)
- React Fast Refresh
- TypeScript incremental compilation

## Performance Optimizations

### Docker Build Optimization
- **--no-cache builds** ensure fresh code changes
- **BuildKit optimization** with provenance disabled
- **Parallel layer building** for faster builds
- **Multi-stage builds** for smaller image sizes

### Resource Management
- **Memory limits** on containers (256M-512M)
- **CPU limits** for balanced resource usage
- **Health checks** with appropriate timeouts
- **Automatic cleanup** of dangling images and cache

### Development Mode Benefits
- **Native performance** without Docker overhead
- **Direct filesystem access** for faster file operations
- **Simplified debugging** with direct process access
- **Faster dependency installation** with uv/pip

## Troubleshooting

### Common Issues

**Port Conflicts:**
- System automatically detects and stops conflicting containers
- Clean up with `docker container prune -f`

**Build Cache Issues:**
- Use "Force Complete Rebuild" option
- Clear Python cache: `find . -name "__pycache__" -exec rm -rf {} +`

**Database Connection Issues:**
- Verify .env configuration
- Check database service health status
- Use database shell access for direct debugging

**Authentication Problems:**
- Clear browser cookies and tokens
- Check JWT_SECRET_KEY configuration
- Verify Supabase credentials if using cloud database

### Monitoring and Debugging

**Performance Monitor:**
- Real-time container resource usage
- System memory and disk utilization
- Connection statistics and health metrics

**Log Viewing:**
- Separate logs for backend, frontend, database, and Redis
- Tail logs with `docker logs -f <container>`
- Debug logging with `FASTMCP_LOG_LEVEL=DEBUG`

**Health Checks:**
- Built-in HTTP health endpoint at `/health`
- Container health checks with automatic restart
- Connection manager health validation

## Conclusion

The 4genthub Docker development system provides a comprehensive, production-ready development environment with:

- **Multiple deployment configurations** for different use cases
- **Sophisticated MCP server architecture** with dual authentication
- **Seamless frontend-backend communication** with automatic fallbacks
- **Advanced monitoring and debugging capabilities**
- **Performance optimizations** for both development and production

This system enables rapid development iteration while maintaining production-like capabilities and robust error handling.