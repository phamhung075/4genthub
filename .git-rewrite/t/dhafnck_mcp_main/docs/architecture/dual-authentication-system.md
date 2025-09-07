# Dual Authentication System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Components](#architecture-components)
3. [Authentication Flow Diagrams](#authentication-flow-diagrams)
4. [DDD Architecture Layers](#ddd-architecture-layers)
5. [Request Type Detection](#request-type-detection)
6. [Authentication Methods](#authentication-methods)
7. [Code Examples](#code-examples)
8. [File Locations](#file-locations)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

## Overview

### Purpose and Design Rationale

The DhafnckMCP server implements a **dual authentication system** designed to handle two distinct types of clients:

1. **Frontend Authentication (API v2)**: Browser-based requests from the React frontend using Supabase JWT tokens
2. **MCP Authentication**: Machine-to-machine communication from MCP clients using local JWT tokens

This dual approach allows the system to:
- Support both human users (via web interface) and programmatic access (via MCP protocol)
- Maintain secure token-based authentication for both contexts
- Provide seamless integration with Supabase for user management
- Enable local JWT validation for high-performance MCP operations

### Two Authentication Modes

#### Frontend Mode (Supabase JWT)
- **Target**: React frontend application
- **Token Source**: Supabase authentication service
- **Validation**: Remote validation via Supabase API
- **Transport**: HTTP Bearer tokens or cookies
- **User Context**: Full Supabase user profile with email verification

#### MCP Mode (Local JWT)
- **Target**: MCP clients and tools
- **Token Source**: Local JWT service in the application
- **Validation**: Local validation using secret key
- **Transport**: HTTP Bearer/Token headers or custom headers
- **User Context**: Lightweight user context with scopes and permissions

## Architecture Components

### Core Authentication Components

```
DualAuthMiddleware
├── SupabaseAuthService     (Frontend authentication)
├── TokenValidator          (MCP token validation)
├── JWTService             (Local JWT operations)
└── Request Detection      (Route and type identification)
```

## Authentication Flow Diagrams

### Frontend Authentication Flow

```
Browser Request → DualAuthMiddleware → Request Type Detection
     ↓
"frontend" type detected
     ↓
Extract token from:
├── Authorization: Bearer <token>
└── Cookie: access_token=<token>
     ↓
SupabaseAuthService.verify_token()
     ↓
Remote validation with Supabase
     ↓
Success: Add user_id to request.state
Failure: Return 401 with WWW-Authenticate header
```

### MCP Authentication Flow

```
MCP Client Request → DualAuthMiddleware → Request Type Detection
     ↓
"mcp" type detected
     ↓
Extract token from:
├── Authorization: Bearer <token>
├── Authorization: Token <token>
├── x-mcp-token: <token>
├── mcp-token: <token>
└── ?token=<token> (query param)
     ↓
Token Type Detection:
├── JWT (starts with "eyJ") → JWTService.verify_token()
└── MCP Token (starts with "mcp_") → TokenValidator.validate_token()
     ↓
Local validation or Supabase validation
     ↓
Success: Add user_id to request.state
Failure: Return 401 with JSON-RPC error format
```

### Complete Request Flow Through DDD Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
├─────────────────────────────────────────────────────────────┤
│  HTTP Request → DualAuthMiddleware                          │
│       ↓                                                     │
│  Request Type Detection:                                    │
│  ├── /api/v2/* → Frontend                                  │
│  ├── /mcp/* → MCP                                          │
│  ├── User-Agent analysis                                   │
│  └── Content-Type analysis                                 │
│       ↓                                                     │
│  Authentication Strategy:                                   │
│  ├── Frontend → Supabase JWT                              │
│  └── MCP → Local JWT + TokenValidator                     │
│       ↓                                                     │
│  Route to Controllers:                                      │
│  ├── /api/v2/tasks → UserScopedTaskRoutes                │
│  └── /mcp/tools → MCP Tool Endpoints                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
├─────────────────────────────────────────────────────────────┤
│  Controllers extract user_id from request.state            │
│       ↓                                                     │
│  Create User-Scoped Services:                              │
│  ├── TaskApplicationFacade(user_id)                       │
│  ├── ProjectApplicationFacade(user_id)                    │
│  └── ContextService(user_id)                              │
│       ↓                                                     │
│  Execute Use Cases:                                         │
│  ├── CreateTask(request, user_id)                         │
│  ├── ListTasks(user_id)                                   │
│  └── UpdateSubtask(request, user_id)                      │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Domain Layer                              │
├─────────────────────────────────────────────────────────────┤
│  Business Logic with User Context:                         │
│  ├── Task Entities with user_id                           │
│  ├── Project Aggregates with user_id                      │
│  └── Domain Services (validation, business rules)          │
│       ↓                                                     │
│  Domain Events:                                             │
│  ├── TaskCreated(task_id, user_id)                        │
│  └── ProjectUpdated(project_id, user_id)                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
├─────────────────────────────────────────────────────────────┤
│  User-Scoped Repositories:                                 │
│  ├── TaskRepository.with_user(user_id)                    │
│  ├── ProjectRepository.with_user(user_id)                 │
│  └── ContextRepository.with_user(user_id)                 │
│       ↓                                                     │
│  Database Queries with WHERE user_id = :user_id           │
│  Authentication Services:                                   │
│  ├── SupabaseAuthService → Remote validation               │
│  └── JWTService → Local validation                         │
└─────────────────────────────────────────────────────────────┘
```

## DDD Architecture Layers

### Interface Layer

**Responsibilities:**
- HTTP request handling and routing
- Authentication middleware application  
- Request/response serialization
- API versioning (v2 for frontend, MCP endpoints for tools)

**Key Components:**
- `DualAuthMiddleware`: Routes authentication based on request type
- `UserScopedTaskRoutes`: Frontend API routes with Supabase auth
- `MCP Tool Endpoints`: MCP protocol routes with local JWT auth
- Route decorators and dependency injection

### Application Layer

**Responsibilities:**
- Orchestration of domain operations
- Use case implementation
- User context propagation
- Cross-cutting concerns (logging, caching)

**Key Components:**
- `TaskApplicationFacade`: User-scoped task operations
- `ProjectApplicationFacade`: User-scoped project management
- `ContextService`: Hierarchical context management
- User-scoped service factories

### Domain Layer

**Responsibilities:**
- Core business logic
- Entity definitions and relationships
- Domain services and business rules
- Domain events

**Key Components:**
- Task, Project, Context entities with user ownership
- Domain services for validation and business rules
- User entity and authentication context
- Domain events for audit trails

### Infrastructure Layer

**Responsibilities:**
- Data persistence with user isolation
- External service integration
- Authentication provider implementations
- Caching and performance optimizations

**Key Components:**
- User-scoped ORM repositories
- Supabase authentication integration
- Local JWT service implementation
- Database connection and session management

## Request Type Detection

The `DualAuthMiddleware._detect_request_type()` method uses multiple heuristics to identify request types:

### Frontend Request Indicators
```python
# Path-based detection
if path.startswith('/api/v2/'):
    return 'frontend'

# User-Agent analysis
browser_indicators = ['mozilla', 'chrome', 'safari', 'firefox', 'edge']
if any(indicator in user_agent for indicator in browser_indicators):
    return 'frontend'

# Default for API requests
if path.startswith('/api/'):
    return 'frontend'
```

### MCP Request Indicators
```python
# MCP-specific paths
if path.startswith('/mcp'):
    return 'mcp'

# MCP protocol headers
if 'mcp-protocol-version' in request.headers:
    return 'mcp'

# JSON-RPC content type
if 'application/json' in content_type and 'jsonrpc' in accept_header:
    return 'mcp'
```

### Unknown Request Handling
For unknown request types, the middleware attempts both authentication methods:
1. Try MCP authentication first (Bearer token validation)
2. Fallback to Frontend authentication (cookies or Supabase tokens)

## Authentication Methods

### Frontend Authentication Methods

#### Bearer Token (API Calls)
```http
Authorization: Bearer <supabase_jwt_token>
```
- Used for programmatic frontend API calls
- Validated against Supabase service
- Returns full user profile

#### Cookie Authentication (Browser Requests)
```http
Cookie: access_token=<supabase_jwt_token>
```
- Used for browser-based requests
- Automatically set by frontend authentication
- Provides seamless user experience

### MCP Authentication Methods

#### Bearer Token
```http
Authorization: Bearer <local_jwt_token>
```
- Standard OAuth 2.0 format
- Local validation for performance
- Supports scopes and permissions

#### Token Header
```http
Authorization: Token <local_jwt_token>
```
- Alternative token format
- Compatible with various MCP clients

#### Custom Headers
```http
x-mcp-token: <token>
mcp-token: <token>
```
- MCP-specific headers
- Useful for clients that can't modify Authorization header

#### Query Parameters (Development Only)
```http
GET /mcp/endpoint?token=<token>
```
- **Security Warning**: Only for development/testing
- Logs security warning when used
- Tokens may be logged in access logs

## Code Examples

### Frontend API Call with Authentication

```javascript
// Frontend React component
const createTask = async (taskData) => {
  const response = await fetch('/api/v2/tasks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'Content-Type': 'application/json'
    },
    credentials: 'include', // Include cookies
    body: JSON.stringify(taskData)
  });
  
  if (!response.ok) {
    throw new Error('Authentication failed');
  }
  
  return response.json();
};
```

### MCP Tool Call with Authentication

```python
# MCP client tool call
import httpx

async def call_mcp_tool(tool_name, params, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-mcp-token': token  # Backup header
    }
    
    payload = {
        'jsonrpc': '2.0',
        'method': f'mcp_tool_{tool_name}',
        'params': params,
        'id': 1
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8000/mcp/tools',
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"MCP call failed: {response.text}")
            
        return response.json()
```

### Dual Auth Middleware Configuration

```python
# FastAPI application setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.auth.middleware.dual_auth_middleware import DualAuthMiddleware

app = FastAPI(title="DhafnckMCP Server")

# Add CORS middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3800"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add dual authentication middleware
app.add_middleware(DualAuthMiddleware)

# Include routers
app.include_router(
    user_scoped_task_routes.router,
    prefix="/api/v2"
)
app.include_router(
    mcp_tool_routes.router,
    prefix="/mcp"
)
```

### Creating User-Scoped Services

```python
# Application layer service creation
async def get_user_scoped_task_service(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TaskApplicationFacade:
    """Create a task service scoped to the current user"""
    
    # Create user-scoped repositories
    task_repo = TaskRepository(db).with_user(current_user.id)
    project_repo = ProjectRepository(db).with_user(current_user.id)
    context_service = ContextService().with_user(current_user.id)
    
    return TaskApplicationFacade(
        task_repository=task_repo,
        project_repository=project_repo,
        context_service=context_service
    )
```

## File Locations

### Authentication Core Files

| Component | File Path | Responsibilities |
|-----------|-----------|-----------------|
| **DualAuthMiddleware** | `/src/fastmcp/auth/middleware/dual_auth_middleware.py` | Request routing and authentication orchestration |
| **SupabaseAuthService** | `/src/fastmcp/auth/infrastructure/supabase_auth.py` | Frontend JWT validation via Supabase |
| **TokenValidator** | `/src/fastmcp/auth/token_validator.py` | MCP token validation and rate limiting |
| **JWTService** | `/src/fastmcp/auth/domain/services/jwt_service.py` | Local JWT token operations |

### Route Implementation Files

| Route Type | File Path | Purpose |
|------------|-----------|---------|
| **Frontend API** | `/src/fastmcp/server/routes/user_scoped_task_routes.py` | User-scoped task operations for frontend |
| **MCP Tools** | `/src/fastmcp/server/routes/mcp_token_routes.py` | MCP tool authentication endpoints |
| **Token Management** | `/src/fastmcp/server/routes/token_routes.py` | Token generation and management |

### Configuration Files

| Type | File Path | Description |
|------|-----------|-------------|
| **Environment** | `/.env` | Authentication secrets and configuration |
| **FastAPI Integration** | `/src/fastmcp/auth/interface/fastapi_auth.py` | FastAPI dependency injection |
| **Supabase Integration** | `/src/fastmcp/auth/interface/supabase_fastapi_auth.py` | Supabase-specific FastAPI helpers |

### Test Files

| Component | File Path | Coverage |
|-----------|-----------|----------|
| **Middleware Tests** | `/src/tests/auth/middleware/dual_auth_middleware_test.py` | Dual auth middleware functionality |
| **Service Tests** | `/src/tests/auth/infrastructure/supabase_auth_test.py` | Supabase authentication service |
| **Token Tests** | `/src/tests/auth/token_validator_test.py` | Token validation and rate limiting |
| **Integration Tests** | `/src/tests/auth/test_auth_bridge_integration.py` | End-to-end authentication flows |

## Configuration

### Environment Variables

```bash
# Supabase Configuration (Frontend Auth)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Local JWT Configuration (MCP Auth)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Frontend Configuration
FRONTEND_URL=http://localhost:3800

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_REQUESTS_PER_HOUR=1000
RATE_LIMIT_BURST_LIMIT=20
```

### Authentication Middleware Settings

```python
# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 100,
    "requests_per_hour": 1000,
    "burst_limit": 20,
    "window_size": 60
}

# Skip authentication for these paths
SKIP_AUTH_PATHS = [
    "/health",
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/favicon.ico",
    "/static/"
]

# Token cache configuration
TOKEN_CACHE_TTL = 300  # 5 minutes
```

## Troubleshooting

### Common Authentication Issues

#### 1. Frontend Authentication Failing

**Symptoms:**
- 401 errors on `/api/v2/` endpoints
- Users redirected to login repeatedly

**Debug Steps:**
```bash
# Check Supabase configuration
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Verify token in browser
# Open browser dev tools → Application → Cookies
# Look for access_token cookie

# Check server logs
tail -f /logs/dhafnck_mcp_errors.log | grep "FRONTEND AUTH"
```

**Common Solutions:**
- Verify Supabase credentials in `.env`
- Check cookie domain settings
- Ensure CORS is properly configured
- Verify token expiration times

#### 2. MCP Authentication Failing

**Symptoms:**
- MCP tools return authentication errors
- Token validation failures in logs

**Debug Steps:**
```bash
# Check JWT secret configuration
echo $JWT_SECRET_KEY

# Test token generation
curl -X POST http://localhost:8000/api/v2/auth/generate-token \
  -H "Authorization: Bearer <frontend-token>"

# Check MCP tool logs
tail -f /logs/dhafnck_mcp_errors.log | grep "MCP AUTH"
```

**Common Solutions:**
- Verify JWT secret key is set
- Check token format (should start with 'eyJ' for JWT)
- Ensure proper token headers are sent
- Verify rate limiting isn't blocking requests

#### 3. Request Type Detection Issues

**Symptoms:**
- Wrong authentication method applied
- Unexpected authentication failures

**Debug Steps:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check request detection logs
tail -f /logs/dhafnck_mcp.log | grep "Request type detected"
```

**Common Solutions:**
- Verify User-Agent strings for browser requests
- Check path prefixes (`/api/v2/` vs `/mcp/`)
- Ensure proper Content-Type headers
- Add MCP protocol headers if needed

#### 4. Database User Isolation Issues

**Symptoms:**
- Users seeing other users' data
- Authorization errors in application layer

**Debug Steps:**
```python
# Check user context in request
@app.middleware("http")
async def debug_user_context(request: Request, call_next):
    if hasattr(request.state, 'user_id'):
        logger.debug(f"Request user_id: {request.state.user_id}")
    response = await call_next(request)
    return response
```

**Common Solutions:**
- Verify user_id is properly set in request.state
- Check repository user scoping is applied
- Ensure database queries include user_id filters
- Verify middleware order (auth middleware before route handlers)

### Performance Monitoring

#### Authentication Performance Metrics

```python
# Add to monitoring dashboard
auth_metrics = {
    "supabase_auth_latency": "avg(supabase_verify_duration)",
    "local_jwt_validation_latency": "avg(jwt_verify_duration)", 
    "token_cache_hit_rate": "cache_hits / (cache_hits + cache_misses)",
    "authentication_success_rate": "successful_auths / total_auth_attempts"
}
```

#### Rate Limiting Monitoring

```python
# Monitor rate limiting effectiveness
rate_limit_metrics = {
    "requests_blocked": "count(rate_limit_exceeded)",
    "top_rate_limited_tokens": "top_k(rate_limited_tokens, 10)",
    "burst_limit_violations": "count(burst_limit_exceeded)"
}
```

### Security Considerations

#### Token Security Best Practices

1. **Frontend Tokens (Supabase JWT):**
   - Use HTTPS only in production
   - Set secure cookie flags
   - Implement proper token refresh flows
   - Monitor for suspicious login patterns

2. **MCP Tokens (Local JWT):**
   - Use strong secret keys (256-bit minimum)
   - Implement token rotation
   - Set appropriate expiration times
   - Log all token usage for audit trails

3. **General Security:**
   - Enable rate limiting on all endpoints
   - Monitor authentication failure patterns
   - Implement account lockout policies
   - Regular security audits of authentication flows

---

*This documentation covers the complete dual authentication system implementation in DhafnckMCP. For additional technical details, refer to the source code files listed in the File Locations section.*