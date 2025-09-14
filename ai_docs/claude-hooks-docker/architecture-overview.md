# Claude Hooks Docker Client Architecture

## Executive Summary

This document outlines the architecture and technical implementation for containerizing the Claude hooks system as a Docker client service. The solution transforms the existing file-based hook system into a scalable, network-accessible microservice while maintaining compatibility with Claude Code's workflow.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Component Architecture](#component-architecture)
4. [Communication Patterns](#communication-patterns)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Performance Considerations](#performance-considerations)

## System Overview

### Current State Architecture

The Claude hooks system currently operates as a set of Python scripts that:
- Execute locally on the developer's machine
- Intercept tool calls from Claude Code
- Validate file operations and enforce project rules
- Communicate with MCP server via HTTP
- Maintain session state in local files

### Proposed Docker Architecture

The containerized solution transforms this into:
- A standalone microservice running in Docker
- REST/WebSocket API for Claude Code integration
- Centralized state management
- Scalable and portable deployment
- Network-based communication

## Architecture Design

### High-Level Architecture

```mermaid
graph TB
    subgraph "Developer Machine"
        CC[Claude Code]
        PF[Project Files]
    end

    subgraph "Docker Environment"
        subgraph "Claude Hooks Container"
            API[API Gateway]
            HE[Hook Engine]
            VM[Validation Manager]
            SM[Session Manager]
            Cache[Redis Cache]
        end

        subgraph "Supporting Services"
            MCP[MCP Server]
            KC[Keycloak]
            PG[PostgreSQL]
        end
    end

    CC -->|WebSocket/REST| API
    API --> HE
    HE --> VM
    HE --> SM
    SM --> Cache
    HE -->|HTTP| MCP
    HE -->|Auth| KC
    SM --> PG
    API -->|Volume Mount| PF
```

### Microservices Architecture

```yaml
services:
  claude-hooks-api:
    purpose: "API gateway for hook requests"
    technology: "FastAPI/Python"
    port: 9000

  claude-hooks-engine:
    purpose: "Core hook processing logic"
    technology: "Python"

  claude-hooks-validator:
    purpose: "File system validation"
    technology: "Python"

  claude-hooks-session:
    purpose: "Session management"
    technology: "Python/Redis"
```

## Component Architecture

### 1. API Gateway Layer

```python
# API Structure
/api/v1/
  /hooks/
    POST /pre-tool-use      # Pre-tool validation
    POST /post-tool-use     # Post-tool processing
    POST /session-start     # Initialize session
    POST /session-end       # Cleanup session

  /validation/
    POST /file-operation    # Validate file operations
    POST /command           # Validate commands

  /context/
    GET  /session/{id}      # Get session context
    POST /inject            # Inject context

  /health/
    GET  /status            # Health check
    GET  /metrics           # Performance metrics
```

### 2. Hook Engine Architecture

```python
class HookEngine:
    """Core engine for processing hook requests"""

    def __init__(self):
        self.validators = ValidatorRegistry()
        self.processors = ProcessorRegistry()
        self.session_manager = SessionManager()
        self.mcp_client = MCPClient()

    async def process_pre_tool_use(self, request: ToolRequest) -> HookResponse:
        """Process pre-tool-use hook"""
        # 1. Load session context
        session = await self.session_manager.get_session(request.session_id)

        # 2. Run validators
        validation_results = await self.validators.validate(request, session)

        # 3. Apply business rules
        if not validation_results.passed:
            return HookResponse(blocked=True, errors=validation_results.errors)

        # 4. Update session
        await self.session_manager.update(session, request)

        # 5. Return response
        return HookResponse(blocked=False, hints=validation_results.hints)
```

### 3. Validation Architecture

```python
class ValidationManager:
    """Manages all validation rules"""

    validators = {
        'file_system': FileSystemValidator(),
        'documentation': DocumentationValidator(),
        'command': CommandValidator(),
        'mcp_task': MCPTaskValidator(),
        'naming': NamingValidator()
    }

    async def validate(self, operation: Operation) -> ValidationResult:
        """Run all applicable validators"""
        results = []

        for validator in self.get_applicable_validators(operation):
            result = await validator.validate(operation)
            results.append(result)

        return ValidationResult.merge(results)
```

### 4. Session Management Architecture

```python
class SessionManager:
    """Manages hook sessions with Redis backend"""

    def __init__(self):
        self.redis = Redis(host='redis', port=6379)
        self.postgres = PostgreSQL(connection_string)

    async def create_session(self, user_id: str, project_id: str) -> Session:
        """Create new session"""
        session = Session(
            id=generate_uuid(),
            user_id=user_id,
            project_id=project_id,
            started_at=datetime.now(),
            context={}
        )

        # Store in Redis for fast access
        await self.redis.set(f"session:{session.id}", session.to_json(), ex=7200)

        # Persist to PostgreSQL
        await self.postgres.insert_session(session)

        return session
```

## Communication Patterns

### 1. WebSocket Communication (Real-time)

```python
# WebSocket for real-time hook processing
@app.websocket("/ws/hooks/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    try:
        while True:
            # Receive hook request
            data = await websocket.receive_json()

            # Process hook
            result = await hook_engine.process(data)

            # Send response
            await websocket.send_json(result)

    except WebSocketDisconnect:
        await session_manager.cleanup(client_id)
```

### 2. REST API Communication

```python
# REST endpoint for hook processing
@app.post("/api/v1/hooks/pre-tool-use")
async def pre_tool_use(request: ToolRequest) -> HookResponse:
    """Process pre-tool-use hook via REST"""

    # Validate request
    if not await validate_client(request.client_id, request.token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Process hook
    result = await hook_engine.process_pre_tool_use(request)

    # Return response
    return result
```

### 3. Event-Driven Pattern

```python
# Event bus for asynchronous processing
class EventBus:
    """Publish-subscribe event system"""

    async def publish(self, event: HookEvent):
        """Publish hook event"""
        await self.redis.publish(f"hook:{event.type}", event.to_json())

    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to hook events"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"hook:{event_type}")

        async for message in pubsub.listen():
            event = HookEvent.from_json(message['data'])
            await handler(event)
```

## Data Flow

### 1. Request Flow

```mermaid
sequenceDiagram
    participant CC as Claude Code
    participant API as API Gateway
    participant HE as Hook Engine
    participant Val as Validators
    participant MCP as MCP Server
    participant Cache as Redis Cache

    CC->>API: Tool Request
    API->>HE: Process Request
    HE->>Cache: Get Session
    HE->>Val: Validate Operation
    Val-->>HE: Validation Result

    alt Validation Passed
        HE->>MCP: Update Context
        MCP-->>HE: Confirmation
        HE->>Cache: Update Session
        HE-->>API: Allow Operation
    else Validation Failed
        HE-->>API: Block Operation
    end

    API-->>CC: Response
```

### 2. State Management Flow

```python
# State synchronization across components
class StateManager:
    """Manages distributed state"""

    async def sync_state(self, operation: Operation):
        """Synchronize state across all components"""

        # 1. Update local cache
        await self.redis.set(f"state:{operation.id}", operation.state)

        # 2. Persist to database
        await self.postgres.update_state(operation)

        # 3. Notify subscribers
        await self.event_bus.publish(StateChangeEvent(operation))

        # 4. Update MCP context
        await self.mcp_client.update_context(operation.context)
```

## Security Architecture

### 1. Authentication & Authorization

```python
class SecurityManager:
    """Handles authentication and authorization"""

    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.keycloak = KeycloakClient()

    async def authenticate(self, token: str) -> User:
        """Authenticate user via JWT"""
        try:
            # Verify JWT signature
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Validate with Keycloak
            user = await self.keycloak.validate_user(payload['sub'])

            return user

        except JWTError:
            raise AuthenticationError("Invalid token")

    async def authorize(self, user: User, resource: str, action: str) -> bool:
        """Check user authorization"""
        return await self.keycloak.check_permission(user, resource, action)
```

### 2. Network Security

```yaml
# Network isolation configuration
networks:
  claude-internal:
    driver: bridge
    internal: true

  claude-external:
    driver: bridge

services:
  claude-hooks:
    networks:
      - claude-internal  # Internal only

  api-gateway:
    networks:
      - claude-internal
      - claude-external  # External access
```

### 3. Data Encryption

```python
class EncryptionManager:
    """Handles data encryption"""

    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt_sensitive_data(self, data: dict) -> str:
        """Encrypt sensitive data"""
        json_data = json.dumps(data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_sensitive_data(self, encrypted: str) -> dict:
        """Decrypt sensitive data"""
        decoded = base64.b64decode(encrypted.encode())
        decrypted = self.cipher.decrypt(decoded)
        return json.loads(decrypted.decode())
```

## Deployment Architecture

### 1. Container Structure

```dockerfile
# Multi-stage Dockerfile for optimized image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY claude_hooks/ ./claude_hooks/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 claude && \
    chown -R claude:claude /app

USER claude

# Environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV HOOKS_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9000/health/status')"

# Expose API port
EXPOSE 9000

# Run application
CMD ["uvicorn", "claude_hooks.api:app", "--host", "0.0.0.0", "--port", "9000"]
```

### 2. Docker Compose Configuration

```yaml
version: '3.8'

services:
  claude-hooks:
    build:
      context: .
      dockerfile: Dockerfile.hooks
    image: claude-hooks:latest
    container_name: claude-hooks-service

    ports:
      - "9000:9000"

    volumes:
      # Mount project directory (read-only for validation)
      - ${PROJECT_PATH}:/project:ro

      # Persistent data volumes
      - claude-hooks-data:/app/data
      - claude-hooks-logs:/app/logs

      # Configuration
      - ./config:/app/config:ro

    environment:
      # Service configuration
      - HOOKS_ENV=production
      - API_PORT=9000
      - LOG_LEVEL=INFO

      # MCP Server connection
      - MCP_SERVER_URL=http://mcp-server:8000
      - MCP_API_KEY=${MCP_API_KEY}

      # Database connections
      - POSTGRES_URL=postgresql://user:pass@postgres:5432/claude_hooks
      - REDIS_URL=redis://redis:6379/0

      # Authentication
      - KEYCLOAK_URL=http://keycloak:8080
      - KEYCLOAK_REALM=dhafnck
      - JWT_SECRET=${JWT_SECRET}

      # Project configuration
      - PROJECT_PATH=/project
      - AI_DOCS_PATH=/project/ai_docs
      - AI_DATA_PATH=/app/data

    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mcp-server:
        condition: service_healthy

    networks:
      - claude-network

    restart: unless-stopped

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  postgres:
    image: postgres:15-alpine
    container_name: claude-postgres

    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d

    environment:
      - POSTGRES_DB=claude_hooks
      - POSTGRES_USER=claude
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

    ports:
      - "5432:5432"

    networks:
      - claude-network

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U claude"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: claude-redis

    volumes:
      - redis-data:/data

    ports:
      - "6379:6379"

    networks:
      - claude-network

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    container_name: claude-nginx

    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro

    ports:
      - "443:443"
      - "80:80"

    networks:
      - claude-network

    depends_on:
      - claude-hooks

volumes:
  claude-hooks-data:
    driver: local
  claude-hooks-logs:
    driver: local
  postgres-data:
    driver: local
  redis-data:
    driver: local

networks:
  claude-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### 3. Kubernetes Deployment (Optional)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claude-hooks
  namespace: claude-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: claude-hooks
  template:
    metadata:
      labels:
        app: claude-hooks
    spec:
      containers:
      - name: claude-hooks
        image: claude-hooks:latest
        ports:
        - containerPort: 9000
        env:
        - name: HOOKS_ENV
          value: "production"
        - name: MCP_SERVER_URL
          value: "http://mcp-server:8000"
        volumeMounts:
        - name: project
          mountPath: /project
          readOnly: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/status
            port: 9000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 9000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: project
        persistentVolumeClaim:
          claimName: project-pvc
```

## Performance Considerations

### 1. Caching Strategy

```python
class CacheManager:
    """Multi-layer caching strategy"""

    def __init__(self):
        self.memory_cache = {}  # L1: In-memory cache
        self.redis = Redis()    # L2: Redis cache
        self.postgres = PostgreSQL()  # L3: Database

    async def get(self, key: str) -> Any:
        """Get with cache hierarchy"""

        # Check L1 cache
        if key in self.memory_cache:
            return self.memory_cache[key]

        # Check L2 cache
        value = await self.redis.get(key)
        if value:
            self.memory_cache[key] = value
            return value

        # Fetch from L3
        value = await self.postgres.get(key)
        if value:
            await self.redis.set(key, value, ex=3600)
            self.memory_cache[key] = value
            return value

        return None
```

### 2. Connection Pooling

```python
# Connection pool configuration
class ConnectionPool:
    """Manages database and HTTP connections"""

    def __init__(self):
        # PostgreSQL connection pool
        self.pg_pool = asyncpg.create_pool(
            min_size=10,
            max_size=50,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )

        # HTTP connection pool
        self.http_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300
            )
        )
```

### 3. Async Processing

```python
# Asynchronous task processing
class AsyncProcessor:
    """Handles async processing of hooks"""

    async def process_batch(self, requests: List[HookRequest]):
        """Process multiple requests concurrently"""

        tasks = []
        for request in requests:
            task = asyncio.create_task(self.process_single(request))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            result if not isinstance(result, Exception) else ErrorResponse(str(result))
            for result in results
        ]
```

### 4. Performance Metrics

```python
# Performance monitoring
class MetricsCollector:
    """Collects performance metrics"""

    def __init__(self):
        self.prometheus = PrometheusClient()

    async def record_request(self, endpoint: str, duration: float, status: int):
        """Record request metrics"""

        # Record to Prometheus
        self.prometheus.histogram(
            'hook_request_duration_seconds',
            duration,
            labels={'endpoint': endpoint, 'status': status}
        )

        # Log slow requests
        if duration > 1.0:
            logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")
```

## Conclusion

This architecture provides a robust, scalable, and maintainable solution for containerizing the Claude hooks system. The design ensures:

1. **Scalability** - Horizontal scaling through container orchestration
2. **Reliability** - Health checks, retries, and circuit breakers
3. **Performance** - Caching, connection pooling, and async processing
4. **Security** - Authentication, authorization, and encryption
5. **Maintainability** - Clean architecture and separation of concerns
6. **Observability** - Logging, metrics, and tracing

The solution maintains backward compatibility while providing a modern, cloud-native architecture suitable for production deployment.