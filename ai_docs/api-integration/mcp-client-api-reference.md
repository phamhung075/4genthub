# MCP HTTP Client API Reference

## Overview

This document provides a complete API reference for the MCP HTTP Client Module, including all public methods, parameters, return types, and usage examples.

## Table of Contents

- [TokenManager](#tokenmanager)
- [RateLimiter](#ratelimiter)
- [MCPHTTPClient](#mcphttpclient)
- [ResilientMCPClient](#resilientmcpclient)
- [OptimizedMCPClient](#optimizedmcpclient)
- [Factory Functions](#factory-functions)
- [Testing Functions](#testing-functions)

---

## TokenManager

Manages JWT tokens for hook-to-MCP communication with automatic refresh.

### Constructor

```python
def __init__(self)
```

Creates a TokenManager instance with configuration from environment variables.

**Environment Variables:**
- `TOKEN_REFRESH_BEFORE_EXPIRY`: Seconds before expiry to refresh (default: 60)
- `KEYCLOAK_URL`: Keycloak server URL (default: "http://localhost:8080")
- `KEYCLOAK_REALM`: Keycloak realm (default: "dhafnck")
- `KEYCLOAK_CLIENT_ID`: Client ID (default: "claude-hooks")
- `KEYCLOAK_CLIENT_SECRET`: Client secret (required)

### Methods

#### get_valid_token()

```python
def get_valid_token(self) -> Optional[str]
```

Get a valid JWT token, refreshing if needed.

**Returns:**
- `str`: Valid JWT token
- `None`: If authentication fails

**Example:**
```python
token_manager = TokenManager()
token = token_manager.get_valid_token()
if token:
    headers = {"Authorization": f"Bearer {token}"}
```

#### _should_refresh()

```python
def _should_refresh(self) -> bool
```

Check if token should be refreshed.

**Returns:**
- `bool`: True if token needs refresh, False otherwise

#### _refresh_token()

```python
def _refresh_token(self)
```

Refresh token using client credentials flow.

**Raises:**
- Network errors if Keycloak is unreachable
- Authentication errors if credentials are invalid

#### _load_cached_token()

```python
def _load_cached_token(self) -> bool
```

Load token from cache file if valid.

**Returns:**
- `bool`: True if cached token loaded successfully, False otherwise

#### _request_new_token()

```python
def _request_new_token(self) -> bool
```

Request new token from Keycloak.

**Returns:**
- `bool`: True if token obtained successfully, False otherwise

**Example:**
```python
token_manager = TokenManager()
if token_manager._request_new_token():
    print("Token obtained successfully")
```

---

## RateLimiter

Simple rate limiter for HTTP requests using token bucket algorithm.

### Constructor

```python
def __init__(self, max_requests: int = 100, time_window: int = 60)
```

**Parameters:**
- `max_requests` (int): Maximum requests allowed in time window (default: 100)
- `time_window` (int): Time window in seconds (default: 60)

### Methods

#### allow_request()

```python
def allow_request(self) -> bool
```

Check if request is allowed under rate limit.

**Returns:**
- `bool`: True if request allowed, False if rate limited

**Example:**
```python
rate_limiter = RateLimiter(max_requests=50, time_window=60)
if rate_limiter.allow_request():
    # Make HTTP request
    pass
else:
    print("Rate limited - wait before making request")
```

---

## MCPHTTPClient

Base HTTP client for communicating with MCP server.

### Constructor

```python
def __init__(self)
```

Creates an MCPHTTPClient instance with configuration from environment variables.

**Environment Variables:**
- `MCP_SERVER_URL`: MCP server base URL (default: "http://localhost:8000")
- `MCP_SERVER_TIMEOUT`: Request timeout in seconds (default: "10")

### Methods

#### authenticate()

```python
def authenticate(self) -> bool
```

Authenticate with Keycloak and get JWT token.

**Returns:**
- `bool`: True if authentication successful, False otherwise

**Example:**
```python
client = MCPHTTPClient()
if client.authenticate():
    print("Authentication successful")
else:
    print("Authentication failed")
```

#### query_pending_tasks()

```python
def query_pending_tasks(self, limit: int = 5, user_id: Optional[str] = None) -> Optional[List[Dict]]
```

Query MCP server for pending tasks via HTTP.

**Parameters:**
- `limit` (int): Maximum number of tasks to return (default: 5)
- `user_id` (str, optional): Filter tasks by user ID

**Returns:**
- `List[Dict]`: List of task dictionaries
- `None`: If query fails or authentication fails

**Example:**
```python
client = MCPHTTPClient()
tasks = client.query_pending_tasks(limit=10)
if tasks:
    for task in tasks:
        print(f"Task: {task.get('title')} - Status: {task.get('status')}")
```

**Task Dictionary Structure:**
```python
{
    "id": "task-uuid",
    "title": "Task title",
    "description": "Task description",
    "status": "todo|in_progress|blocked|review|testing|done|cancelled",
    "priority": "low|medium|high|urgent|critical",
    "assignees": "agent1,agent2",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### get_next_recommended_task()

```python
def get_next_recommended_task(self, git_branch_id: str, user_id: Optional[str] = None) -> Optional[Dict]
```

Get next recommended task via HTTP.

**Parameters:**
- `git_branch_id` (str): Git branch UUID identifier
- `user_id` (str, optional): Filter by user ID

**Returns:**
- `Dict`: Task dictionary with context
- `None`: If no task available or query fails

**Example:**
```python
client = MCPHTTPClient()
task = client.get_next_recommended_task("550e8400-e29b-41d4-a716-446655440000")
if task:
    print(f"Next task: {task.get('title')}")
    print(f"Description: {task.get('description')}")
```

#### make_request()

```python
def make_request(self, endpoint: str, payload: dict) -> Optional[dict]
```

Make authenticated HTTP request to MCP server.

**Parameters:**
- `endpoint` (str): API endpoint path (e.g., "/mcp/manage_task")
- `payload` (dict): Request payload

**Returns:**
- `dict`: Response data
- `None`: If request fails

**Features:**
- Automatic token refresh on 401 responses
- Retry logic for authentication failures
- Error logging and handling

**Example:**
```python
client = MCPHTTPClient()
payload = {
    "action": "list",
    "status": "todo",
    "limit": 5
}
response = client.make_request("/mcp/manage_task", payload)
if response and response.get("success"):
    tasks = response.get("data", {}).get("tasks", [])
```

---

## ResilientMCPClient

HTTP client with fallback strategies for MCP server issues. Inherits from MCPHTTPClient.

### Constructor

```python
def __init__(self)
```

**Environment Variables:**
- All MCPHTTPClient environment variables
- `FALLBACK_CACHE_TTL`: Cache TTL in seconds (default: "3600")
- `FALLBACK_STRATEGY`: Fallback behavior (default: "cache_then_skip")

### Methods

#### query_with_fallback()

```python
def query_with_fallback(self, query_func, *args, **kwargs) -> Optional[Any]
```

Query MCP with multiple fallback strategies.

**Parameters:**
- `query_func`: Function to execute (e.g., `super().query_pending_tasks`)
- `*args, **kwargs`: Arguments to pass to query function

**Returns:**
- `Any`: Result from successful query or cached data
- `None`: If all strategies fail and strategy allows

**Fallback Strategies:**
1. **Primary Server**: Try direct MCP server communication
2. **Cache Fallback**: Use cached data if recent and valid
3. **Strategy Handling**: Based on `FALLBACK_STRATEGY` setting:
   - `cache_then_skip`: Return None, continue without MCP
   - `cache_then_error`: Raise ConnectionError
   - `skip`: Always return None on failure

**Example:**
```python
client = ResilientMCPClient()
tasks = client.query_with_fallback(
    client.query_pending_tasks,
    limit=5,
    user_id="user123"
)
```

#### query_pending_tasks()

```python
def query_pending_tasks(self, limit: int = 5, user_id: Optional[str] = None) -> Optional[List[Dict]]
```

Query pending tasks with fallback strategies. Same signature as MCPHTTPClient but with resilience.

#### get_next_recommended_task()

```python
def get_next_recommended_task(self, git_branch_id: str, user_id: Optional[str] = None) -> Optional[Dict]
```

Get next recommended task with fallback strategies. Same signature as MCPHTTPClient but with resilience.

### Private Methods

#### _cache_fallback_data()

```python
def _cache_fallback_data(self, data: Any)
```

Cache data for fallback use.

**Parameters:**
- `data` (Any): Data to cache

#### _get_cached_fallback()

```python
def _get_cached_fallback(self) -> Optional[Dict]
```

Get cached fallback data.

**Returns:**
- `Dict`: Cached data with metadata
- `None`: If no cache available

#### _is_cache_valid()

```python
def _is_cache_valid(self, cache_data: Dict) -> bool
```

Check if cached data is recent enough.

**Parameters:**
- `cache_data` (Dict): Cache data with timestamp

**Returns:**
- `bool`: True if cache is valid, False if expired

---

## OptimizedMCPClient

HTTP client with connection pooling and rate limiting. Inherits from ResilientMCPClient.

### Constructor

```python
def __init__(self)
```

**Environment Variables:**
- All ResilientMCPClient environment variables
- `RATE_LIMIT_REQUESTS_PER_MINUTE`: Rate limit (default: "100")
- `HTTP_MAX_RETRIES`: Maximum retry attempts (default: "3")
- `HTTP_POOL_CONNECTIONS`: Connection pool size (default: "10")
- `HTTP_POOL_MAXSIZE`: Maximum pool size (default: "10")

**Features:**
- HTTP connection pooling with configurable pool sizes
- Automatic retry strategy with exponential backoff
- Rate limiting to prevent server overload
- Enhanced error handling and recovery

### Methods

#### make_request()

```python
def make_request(self, endpoint: str, payload: dict) -> Optional[dict]
```

Make rate-limited request with connection pooling. Overrides parent method.

**Parameters:**
- `endpoint` (str): API endpoint path
- `payload` (dict): Request payload

**Returns:**
- `dict`: Response data
- `None`: If rate limited or request fails

**Features:**
- Rate limiting check before request
- Connection pool reuse for efficiency
- Automatic retry with backoff
- Enhanced error recovery

**Example:**
```python
client = OptimizedMCPClient()

# This request will be rate limited and use connection pooling
response = client.make_request("/mcp/manage_task", {
    "action": "get",
    "task_id": "550e8400-e29b-41d4-a716-446655440001"
})
```

---

## Factory Functions

### create_mcp_client()

```python
def create_mcp_client(client_type: str = "optimized") -> MCPHTTPClient
```

Factory function to create MCP client instances.

**Parameters:**
- `client_type` (str): Type of client to create
  - `"basic"`: MCPHTTPClient
  - `"resilient"`: ResilientMCPClient  
  - `"optimized"`: OptimizedMCPClient (default)

**Returns:**
- `MCPHTTPClient`: Client instance of specified type

**Raises:**
- `ValueError`: If client_type is unknown

**Example:**
```python
# Create optimized client (default)
client = create_mcp_client()

# Create basic client
basic_client = create_mcp_client("basic")

# Create resilient client
resilient_client = create_mcp_client("resilient")
```

### get_default_client()

```python
def get_default_client() -> OptimizedMCPClient
```

Get default optimized MCP client.

**Returns:**
- `OptimizedMCPClient`: Ready-to-use optimized client instance

**Example:**
```python
# Quick way to get a fully-featured client
client = get_default_client()
tasks = client.query_pending_tasks()
```

---

## Testing Functions

### test_mcp_connection()

```python
def test_mcp_connection() -> bool
```

Test MCP server connection.

**Returns:**
- `bool`: True if connection successful, False otherwise

**Features:**
- Tests authentication
- Tests basic server connectivity
- Provides detailed feedback via print statements

**Example:**
```python
if test_mcp_connection():
    print("MCP server is ready")
else:
    print("MCP server connection failed")
```

**Output Example:**
```
✅ Authentication successful
✅ MCP server connection successful
```

---

## Error Handling

### Common Exceptions

#### Authentication Errors
- **Cause**: Invalid credentials, expired tokens, Keycloak unavailable
- **Handling**: Automatic token refresh, graceful degradation
- **Recovery**: Retry with new token, fallback to cached data

#### Connection Errors
- **Cause**: Network issues, server downtime, timeout
- **Handling**: Automatic retries, fallback strategies
- **Recovery**: Use cached data, continue without MCP functionality

#### Rate Limit Errors
- **Cause**: Too many requests in time window
- **Handling**: Request throttling, automatic delay
- **Recovery**: Queue requests, respect rate limits

### Error Response Format

```python
{
    "success": false,
    "error": "error_code",
    "message": "Human readable error message",
    "details": {
        "timestamp": "2024-01-01T00:00:00Z",
        "endpoint": "/mcp/manage_task",
        "status_code": 401
    }
}
```

### Logging Levels

- **DEBUG**: Request/response details, cache hits/misses
- **INFO**: Successful operations, authentication events
- **WARNING**: Non-critical errors, fallback usage
- **ERROR**: Request failures, authentication failures

---

## Best Practices

### Client Usage

1. **Use OptimizedMCPClient** for production environments
2. **Handle None returns** gracefully for all query methods
3. **Configure environment variables** for your environment
4. **Monitor rate limits** in high-traffic scenarios

### Error Handling

```python
client = get_default_client()

try:
    tasks = client.query_pending_tasks()
    if tasks:
        # Process tasks
        for task in tasks:
            print(f"Processing task: {task['title']}")
    else:
        print("No tasks available or server unavailable")
except Exception as e:
    logger.error(f"Failed to query tasks: {e}")
    # Handle gracefully
```

### Authentication Management

```python
# Check authentication before critical operations
client = get_default_client()
if client.authenticate():
    # Proceed with authenticated requests
    result = client.make_request("/mcp/critical_operation", payload)
else:
    # Handle authentication failure
    logger.error("Authentication required for this operation")
```

### Performance Optimization

```python
# Reuse client instances
client = get_default_client()

# Batch related requests
tasks = client.query_pending_tasks(limit=20)
for task in tasks[:5]:  # Process subset
    # Process task details
    pass
```

This API reference provides comprehensive documentation for all public methods and classes in the MCP HTTP Client Module, enabling developers to effectively integrate and use the client in their applications.