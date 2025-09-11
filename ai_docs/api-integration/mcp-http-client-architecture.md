# MCP HTTP Client Module Architecture

## Overview

The MCP HTTP Client Module provides a comprehensive HTTP client infrastructure for communicating with the MCP (Model Context Protocol) server. It implements a hierarchical architecture with three specialized client classes that build upon each other to provide authentication, resilience, and performance optimization.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Session Start Hook                           │
│                         (.claude/hooks/)                               │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MCP HTTP Client Stack                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                OptimizedMCPClient                               │    │
│  │  • Connection Pooling     • Rate Limiting                      │    │
│  │  • HTTP Retry Strategy    • Pool Management                    │    │
│  └─────────────────┬───────────────────────────────────────────────┘    │
│                    │ inherits from                                      │
│  ┌─────────────────▼───────────────────────────────────────────────┐    │
│  │                ResilientMCPClient                               │    │
│  │  • Fallback Strategies   • Cache Integration                   │    │
│  │  • Error Recovery        • Strategy Configuration              │    │
│  └─────────────────┬───────────────────────────────────────────────┘    │
│                    │ inherits from                                      │
│  ┌─────────────────▼───────────────────────────────────────────────┐    │
│  │                  MCPHTTPClient                                  │    │
│  │  • Basic HTTP Methods    • Token Management                    │    │
│  │  • Session Management    • Authentication                      │    │
│  └─────────────────┬───────────────────────────────────────────────┘    │
│                    │                                                    │
│  ┌─────────────────▼───────────────────────────────────────────────┐    │
│  │                   TokenManager                                  │    │
│  │  • JWT Token Lifecycle   • Cache Management                    │    │
│  │  • Automatic Refresh     • Keycloak Integration               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cache Manager                                  │
│               (.claude/hooks/utils/)                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              SessionContextCache                                │    │
│  │  • Task-specific caching    • Git status cache                 │    │
│  │  • Context optimization     • TTL management                   │    │
│  └─────────────────┬───────────────────────────────────────────────┘    │
│                    │ inherits from                                      │
│  ┌─────────────────▼───────────────────────────────────────────────┐    │
│  │                 CacheManager                                    │    │
│  │  • Generic caching          • File-based storage               │    │
│  │  • Expiration handling      • Thread safety                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MCP Server                                      │
│                    (Port 8000)                                         │
│                                                                         │
│  • Task Management API      • Context Management                       │
│  • Project Management       • Agent Coordination                       │
│  • Authentication           • Git Branch Management                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. MCPHTTPClient (Base Layer)

The foundational HTTP client that provides:
- **Session Management**: Persistent HTTP sessions with proper headers
- **Token Management**: Integration with TokenManager for authentication
- **Basic HTTP Methods**: Core request/response handling
- **Timeout Handling**: Configurable request timeouts

```python
class MCPHTTPClient:
    def __init__(self):
        self.base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.token_manager = TokenManager()
        self.session = requests.Session()
        self.timeout = int(os.getenv("MCP_SERVER_TIMEOUT", "10"))
```

### 2. ResilientMCPClient (Resilience Layer)

Adds fault tolerance and fallback strategies:
- **3-Level Fallback Strategy**: Primary server → Cache → Skip/Error
- **Intelligent Caching**: Automatic cache population and validation
- **Error Recovery**: Graceful handling of server unavailability
- **Strategy Configuration**: Configurable fallback behaviors

```python
class ResilientMCPClient(MCPHTTPClient):
    def query_with_fallback(self, query_func, *args, **kwargs):
        # Strategy 1: Try primary MCP server
        # Strategy 2: Use cached data if recent
        # Strategy 3: Handle based on strategy
```

### 3. OptimizedMCPClient (Performance Layer)

Provides performance optimizations:
- **Connection Pooling**: HTTP connection reuse for efficiency
- **Rate Limiting**: Prevents server overload with request throttling
- **Retry Strategy**: Automatic retries with exponential backoff
- **Pool Management**: Configurable connection pool sizes

```python
class OptimizedMCPClient(ResilientMCPClient):
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=100, time_window=60)
        # HTTPAdapter with retry strategy and connection pooling
```

## Token Management Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client App    │────▶│  TokenManager   │────▶│   Keycloak      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Request Token  │     │  Check Cache    │     │ Client Creds    │
│                 │     │  Validate TTL   │     │ Grant Flow      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  HTTP Headers   │     │  Cache Token    │     │  Return JWT     │
│  Authorization  │     │  File Storage   │     │  + Metadata     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Fallback Strategies

### Strategy 1: Primary Server
- Direct HTTP communication with MCP server
- Full functionality and real-time data
- Automatic token refresh and retry logic

### Strategy 2: Cache Fallback
- File-based cache with TTL validation
- Serves recent data when server unavailable
- Graceful degradation of functionality

### Strategy 3: Skip/Error Handling
- **cache_then_skip**: Continue without MCP functionality
- **cache_then_error**: Raise exception for critical operations
- **skip**: Return None for all failed requests

## Cache Integration

The client integrates seamlessly with the Cache Manager:

```python
# Automatic cache population
def query_with_fallback(self, query_func, *args, **kwargs):
    result = query_func(*args, **kwargs)
    if result is not None:
        self._cache_fallback_data(result)  # Cache successful results
        return result
```

### Cache Hierarchy
- **Session-level caching**: Task lists, git status, project context
- **Fallback caching**: Server response caching for resilience
- **Token caching**: JWT token persistence across sessions

## Service Account Authentication

Integration with Keycloak service account authentication:

```python
class TokenManager:
    def __init__(self):
        self.keycloak_config = {
            "url": os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
            "realm": os.getenv("KEYCLOAK_REALM", "dhafnck"),
            "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "claude-hooks"),
            "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET")
        }
```

## Performance Optimizations

### Connection Pooling
- **Pool Connections**: Reuse HTTP connections for efficiency
- **Pool Max Size**: Configurable maximum pool size
- **Keep-Alive**: Persistent connections for reduced latency

### Rate Limiting
- **Token Bucket Algorithm**: Smooth rate limiting implementation
- **Configurable Limits**: Environment-based rate configuration
- **Request Throttling**: Automatic delay for rate-limited requests

### Retry Strategy
- **Exponential Backoff**: Progressive delay between retries
- **Status-based Retries**: Retry on specific HTTP status codes
- **Circuit Breaker Pattern**: Fail fast after consecutive failures

## Error Handling

### Hierarchical Error Recovery
1. **HTTP-level errors**: Connection timeouts, network issues
2. **Authentication errors**: Token refresh, re-authentication
3. **Rate limit errors**: Automatic throttling and retry
4. **Server errors**: Fallback to cached data

### Logging and Monitoring
- **Structured logging**: Consistent log format across components
- **Performance metrics**: Request timing and success rates
- **Error tracking**: Detailed error reporting and recovery actions

## Integration Points

### Session Hook Integration
- **Automatic initialization**: Client ready at session start
- **Context injection**: MCP data injected into Claude sessions
- **Background updates**: Continuous context synchronization

### Cache Manager Integration
- **Transparent caching**: Automatic cache population and retrieval
- **Cache invalidation**: Smart cache expiration and cleanup
- **Multi-level caching**: Task, context, and fallback caches

### MCP Server Integration
- **RESTful API**: Standard HTTP/JSON communication
- **Authentication**: JWT bearer token authentication
- **Error responses**: Structured error handling and reporting

## Security Considerations

### Token Security
- **Secure storage**: Token files with restricted permissions (0o600)
- **Automatic refresh**: Proactive token renewal before expiration
- **Environment isolation**: Sensitive credentials from environment only

### Network Security
- **TLS verification**: HTTPS certificate validation enabled
- **Request signing**: JWT tokens for request authentication
- **Rate limiting**: Protection against abuse and DoS

### Error Information
- **Sanitized logging**: No sensitive data in logs
- **Error boundaries**: Graceful degradation without data exposure
- **Audit trails**: Request tracking for security analysis

## Configuration Management

All client behavior is configurable through environment variables:

```bash
# Server Configuration
MCP_SERVER_URL=http://localhost:8000
MCP_SERVER_TIMEOUT=10

# Authentication
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=dhafnck
KEYCLOAK_CLIENT_ID=claude-hooks
KEYCLOAK_CLIENT_SECRET=<secret>

# Caching
FALLBACK_CACHE_TTL=3600
FALLBACK_STRATEGY=cache_then_skip

# Performance
RATE_LIMIT_REQUESTS_PER_MINUTE=100
HTTP_MAX_RETRIES=3
HTTP_POOL_CONNECTIONS=10
HTTP_POOL_MAXSIZE=10
```

This architecture provides a robust, scalable, and maintainable solution for MCP server communication with comprehensive error handling, performance optimization, and security features.