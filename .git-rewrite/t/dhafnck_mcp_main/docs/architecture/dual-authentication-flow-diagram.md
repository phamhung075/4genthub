# Dual Authentication System - Visual Flow Diagrams

## Complete Authentication Flow Architecture

This document provides detailed visual representations of how authentication flows through the DhafnckMCP dual authentication system.

## 1. High-Level System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │   MCP Clients   │    │  Unknown Clients│
│   (Browser)     │    │   (Tools/CLI)   │    │  (Auto-detect)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ Supabase JWT         │ Local JWT            │ Try Both
          │ + Cookies            │ + Custom Headers     │ Methods
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │   DualAuthMiddleware      │
                   │  - Request Type Detection │
                   │  - Auth Method Selection  │
                   │  - User Context Creation  │
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │     DDD Architecture      │
                   │   with User Isolation     │
                   └───────────────────────────┘
```

## 2. Detailed Authentication Decision Tree

```
HTTP Request Received
         │
         ▼
┌─────────────────────┐
│ DualAuthMiddleware  │
│ .dispatch()         │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ _detect_request_    │
│ type(request)       │
└─────────┬───────────┘
          │
          ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │Frontend │      │   MCP   │      │ Unknown │
    │Request  │      │ Request │      │ Request │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│_authenticate│  │_authenticate│  │Try MCP First│
│_frontend_   │  │_mcp_request │  │Then Frontend│
│request()    │  │()           │  │             │
└─────┬───────┘  └─────┬───────┘  └─────┬───────┘
      │                │                │
      ▼                ▼                ▼
┌─────────┐      ┌─────────┐      ┌─────────┐
│Supabase │      │Local JWT│      │Best Fit │
│ + Cookie│      │+ Token  │      │Auth     │
│Validation│     │Validator│      │Method   │
└─────────┘      └─────────┘      └─────────┘
```

## 3. Frontend Authentication Flow Detail

```
Frontend Request (/api/v2/*)
         │
         ▼
┌─────────────────────┐
│Request Type:        │
│"frontend"           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│Extract Token From:  │
│1. Authorization:    │
│   Bearer <token>    │
│2. Cookie:           │
│   access_token      │
└─────────┬───────────┘
          │
          ▼
    ┌─────────┐
    │ Token   │
    │ Found?  │
    └────┬────┘
         │
    ┌────▼────┐
    │   YES   │
    └────┬────┘
         │
         ▼
┌─────────────────────┐
│SupabaseAuthService │
│.verify_token()      │
│                     │
│→ Remote call to     │
│  Supabase API       │
│→ Validate JWT       │
│→ Get user profile   │
└─────────┬───────────┘
          │
     ┌────▼────┐
     │ Valid?  │
     └────┬────┘
          │
    ┌─────▼─────┐         ┌─────────────┐
    │   YES     │         │     NO      │
    └─────┬─────┘         └─────┬───────┘
          │                     │
          ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│request.state:   │    │Return 401       │
│- user_id        │    │WWW-Authenticate:│
│- email          │    │Bearer           │
│- auth_type      │    │                 │
│- auth_method    │    │JSON: {          │
│                 │    │ "detail": "...", │
│Continue to      │    │ "auth_type":    │
│next middleware  │    │ "bearer_or_     │
│                 │    │  cookie_req"    │
└─────────────────┘    │}                │
                       └─────────────────┘
```

## 4. MCP Authentication Flow Detail

```
MCP Request (/mcp/* or MCP headers)
         │
         ▼
┌─────────────────────┐
│Request Type:        │
│"mcp"                │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│Extract Token From:  │
│1. Authorization:    │
│   Bearer <token>    │
│   Token <token>     │
│2. Custom Headers:   │
│   x-mcp-token       │
│   mcp-token         │
│3. Query Params:     │
│   ?token=<token>    │
└─────────┬───────────┘
          │
          ▼
    ┌─────────┐
    │ Token   │
    │ Found?  │
    └────┬────┘
         │
    ┌────▼────┐
    │   YES   │
    └────┬────┘
         │
         ▼
┌─────────────────────┐
│Token Type Detection:│
│                     │
│JWT (starts "eyJ")   │
│  ↓                  │
│JWTService.verify_   │
│token()              │
│                     │
│MCP (starts "mcp_")  │
│  ↓                  │
│TokenValidator.      │
│validate_token()     │
└─────────┬───────────┘
          │
     ┌────▼────┐
     │ Valid?  │
     └────┬────┘
          │
    ┌─────▼─────┐         ┌─────────────┐
    │   YES     │         │     NO      │
    └─────┬─────┘         └─────┬───────┘
          │                     │
          ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│request.state:   │    │Return 401       │
│- user_id        │    │JSON-RPC Format: │
│- auth_type      │    │{                │
│- auth_method    │    │ "jsonrpc":"2.0",│
│- token_info     │    │ "error": {      │
│                 │    │   "code": -32001│
│Continue to      │    │   "message":    │
│next middleware  │    │   "Auth failed" │
│                 │    │   "data": {...} │
└─────────────────┘    │ }               │
                       │ "id": null      │
                       │}                │
                       └─────────────────┘
```

## 5. Request Type Detection Logic

```
┌─────────────────────┐
│ Incoming Request    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Extract Request     │
│ Characteristics:    │
│ - Path              │
│ - User-Agent        │
│ - Content-Type      │
│ - Custom Headers    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Path Analysis       │
│                     │
│ /mcp/* → MCP        │
│ /api/v2/* → Frontend│
│ /api/* → Frontend   │
│ /* → Continue...    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Header Analysis     │
│                     │
│ mcp-protocol-version│
│ → MCP               │
│                     │
│ application/json +  │
│ jsonrpc → MCP       │
│                     │
│ Mozilla/Chrome/etc  │
│ → Frontend          │
└─────────┬───────────┘
          │
          ▼
    ┌─────────┐
    │Result:  │
    └────┬────┘
         │
  ┌──────┼──────┐
  │      │      │
  ▼      ▼      ▼
┌────┐ ┌───┐ ┌───────┐
│MCP │ │Web│ │Unknown│
└────┘ └───┘ └───────┘
```

## 6. DDD Layer Authentication Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌─────────────────┐                │
│  │DualAuthMiddleware│    │  Route Handlers │                │
│  │                  │    │                 │                │
│  │ • Request Type   │    │ • Extract       │                │
│  │   Detection      │───▶│  user_id from  │                 │
│  │ • Auth Strategy  │    │   request.state │                │
│  │   Selection      │    │ • Create user-  │                │
│  │ • User Context   │    │   scoped deps   │                │
│  │   Injection      │    │                 │                │
│  └──────────────────┘    └─────────────────┘                │
│           │                        │                        │
└───────────┼────────────────────────┼────────────────────────┘
            │                        │
            ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Auth Services  │    │   Use Cases     │                 │
│  │                 │    │                 │                 │
│  │ • Supabase      │    │ • CreateTask(   │                 │
│  │   AuthService   │    │    user_id)     │                 │
│  │ • JWT Service   │    │ • ListTasks(    │                 │
│  │ • Token         │───▶│    user_id)   │                  │
│  │   Validator     │    │ • UpdateProject(│                 │
│  │                 │    │    user_id)     │                 │
│  │ User Context    │    │                 │                 │
│  │ Propagation     │    │ User-Scoped     │                 │
│  └─────────────────┘    │ Operations      │                 │
│           │             └─────────────────┘                 │
└───────────┼─────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   Entities      │    │ Domain Services │                 │
│  │                 │    │                 │                 │
│  │ • Task(user_id) │    │ • Validation    │                 │
│  │ • Project(      │    │   Rules         │                 │
│  │    user_id)     │───▶│ • Business     │                 │
│  │ • User Context  │    │   Logic         │                 │
│  │                 │    │ • Security      │                 │
│  │ User Ownership  │    │   Policies      │                 │
│  │ Built-in        │    │                 │                 │
│  └─────────────────┘    └─────────────────┘                 │
│           │                        │                        │
└───────────┼────────────────────────┼────────────────────────┘
            │                        │
            ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│               INFRASTRUCTURE LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────┐                │
│  │ User-Scoped     │     │ Auth Providers  │                │
│  │ Repositories    │     │                 │                │
│  │                 │     │ • Supabase      │                │
│  │ • TaskRepo.     │     │   Client        │                │
│  │   with_user(id) │     │ • JWT Service   │                │
│  │ • ProjectRepo.  │────▶│ • Rate Limiter  │                │
│  │   with_user(id) │     │ • Token Cache   │                │
│  │                 │     │                 │                │
│  │ WHERE user_id   │     │ External        │                │
│  │ = :user_id      │     │ Integration     │                │
│  └─────────────────┘     └─────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 7. Error Handling Flow

```
Authentication Error Occurred
         │
         ▼
┌─────────────────────┐
│ Determine Request   │
│ Type for Error      │
│ Response Format     │
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│Frontend │ │   MCP   │
│Request  │ │ Request │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────────┐ ┌─────────────┐
│HTTP 401     │ │JSON-RPC     │
│             │ │Error        │
│Headers:     │ │             │
│WWW-Authenti-│ │{            │
│cate: Bearer │ │"jsonrpc":   │
│             │ │ "2.0",      │
│Body:        │ │"error": {   │
│{            │ │  "code":    │
│ "detail":   │ │  -32001,    │
│  "...",     │ │  "message": │
│ "auth_type":│ │  "Auth      │
│  "bearer_or │ │   failed",  │
│  _cookie_   │ │  "data": {  │
│  required"  │ │   "detail": │
│}            │ │   "...",    │
│             │ │   "auth_    │
│             │ │    type":   │
│             │ │   "mcp_     │
│             │ │    token_   │
│             │ │    req"     │
│             │ │  }          │
│             │ │ },          │
│             │ │ "id": null  │
│             │ │}            │
└─────────────┘ └─────────────┘
```

## 8. Performance Considerations

```
┌─────────────────────────────────────────────────────────────┐
│                   PERFORMANCE OPTIMIZATIONS                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Token Caching:                                             │
│  ┌─────────────────┐                                        │
│  │ TokenValidator  │──▶ In-Memory Cache (5 min TTL)        │
│  └─────────────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ Cache Miss      │──▶ Validate with Provider             │
│  └─────────────────┘                                        │
│                                                             │
│  Rate Limiting:                                             │
│  ┌─────────────────┐                                        │
│  │ Per-Token       │──▶ 100 req/min, 1000 req/hour         │
│  │ Limits          │                                        │
│  └─────────────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ Burst Protection│──▶ 20 requests per 10 seconds         │
│  └─────────────────┘                                        │
│                                                             │
│  Connection Pooling:                                        │
│  ┌─────────────────┐                                        │
│  │ Supabase Client │──▶ HTTP connection reuse              │
│  └─────────────────┘                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 9. Security Monitoring Flow

```
Authentication Event
         │
         ▼
┌─────────────────────┐
│ Log Security Event  │
│                     │
│ • Timestamp         │
│ • User/Token Hash   │
│ • Event Type        │
│ • Request Context   │
│ • Success/Failure   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Event Analysis      │
│                     │
│ • Rate Limiting     │
│ • Failure Patterns  │
│ • Suspicious Tokens │
│ • Audit Trails      │
└─────────┬───────────┘
          │
          ▼
    ┌─────────┐
    │ Alert   │
    │ Needed? │
    └────┬────┘
         │
    ┌────▼────┐
    │   YES   │
    └────┬────┘
         │
         ▼
┌─────────────────────┐
│ Security Response   │
│                     │
│ • Log Warning       │
│ • Rate Limit Token  │
│ • Block Suspicious  │
│ • Notify Admin      │
└─────────────────────┘
```

---

*These diagrams illustrate the complete flow of authentication requests through the DhafnckMCP dual authentication system, showing how different request types are detected, authenticated, and processed through the DDD architecture layers.*