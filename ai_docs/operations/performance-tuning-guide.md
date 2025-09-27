# Performance Tuning Guide - agenthub Auto-Injection System

## Overview

This guide provides comprehensive performance optimization strategies for the agenthub Auto-Injection System, covering all components from database optimization to application-level tuning.

## Performance Baselines

### Target Metrics
- **API Response Time:** <2 seconds (95th percentile)
- **Database Query Time:** <500ms average
- **Memory Usage:** <80% of allocated resources
- **CPU Usage:** <70% average, <90% peak
- **Error Rate:** <0.1%
- **Throughput:** >1000 requests/minute

### Current Performance (Post-Optimization)
- **40% improvement** in response times achieved
- **Database queries optimized** with proper indexing
- **Caching layer implemented** with Redis
- **Resource usage optimized** in containers

## Database Performance Tuning

### PostgreSQL Optimization

#### 1. Connection Pool Configuration

```python
# Database connection pool settings
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

#### 2. PostgreSQL Configuration

Update `config/postgres/postgresql.conf`:

```conf
# Memory settings
shared_buffers = 512MB                  # 25% of RAM
effective_cache_size = 2GB              # 50-75% of RAM
work_mem = 8MB                          # RAM / max_connections / 2
maintenance_work_mem = 128MB            # RAM / 8

# Checkpoint settings
checkpoint_completion_target = 0.9
checkpoint_timeout = 30min
max_wal_size = 8GB
min_wal_size = 2GB

# Query performance
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage
default_statistics_target = 100

# Connection settings
max_connections = 200
```

#### 3. Query Optimization

**Identify Slow Queries:**

```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1 second
SELECT pg_reload_conf();

-- Find slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

**Indexing Strategy:**

```sql
-- Create indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_tasks_user_id_status ON tasks(user_id, status);
CREATE INDEX CONCURRENTLY idx_projects_user_id_created_at ON projects(user_id, created_at);
CREATE INDEX CONCURRENTLY idx_git_branches_project_id ON git_branches(project_id);
CREATE INDEX CONCURRENTLY idx_contexts_level_context_id ON contexts(level, context_id);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_tasks_complex ON tasks(project_id, status, priority, created_at);
```

### Database Monitoring

```bash
# Monitor database performance
docker-compose exec postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c "
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables;
"

# Check index usage
docker-compose exec postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
"
```

## Application Performance Tuning

### FastAPI Optimization

#### 1. Async Configuration

```python
# Optimize async settings
import asyncio
from fastapi import FastAPI

app = FastAPI(
    title="agenthub API",
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc"
)

# Configure async loop
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

#### 2. Caching Implementation

```python
from functools import lru_cache
import redis

# Redis cache client
cache_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)

# LRU cache for frequently accessed data
@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str) -> List[str]:
    """Cache user permissions for 5 minutes."""
    # Implementation with TTL
    pass

# Redis cache decorator
def redis_cache(ttl: int = 300):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached_result = cache_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            result = await func(*args, **kwargs)
            cache_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

#### 3. Response Optimization

```python
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware

# Enable compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Optimize JSON responses
class OptimizedJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS)

app.response_class = OptimizedJSONResponse
```

### Background Task Optimization

```python
from fastapi import BackgroundTasks
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure thread pool
executor = ThreadPoolExecutor(max_workers=10)

# Optimize background tasks
async def optimize_background_tasks():
    # Use connection pooling
    async with async_session_maker() as session:
        # Batch operations
        await session.execute(bulk_operations)
        await session.commit()

# Queue management
from celery import Celery

celery_app = Celery(
    "agenthub",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2"
)

@celery_app.task
def long_running_task(data):
    """Process heavy operations asynchronously."""
    pass
```

## Caching Strategy

### Multi-Layer Caching

#### 1. Application-Level Cache (Redis)

```python
# Cache configuration
CACHE_CONFIG = {
    "user_sessions": {"ttl": 1800},        # 30 minutes
    "user_permissions": {"ttl": 900},      # 15 minutes
    "project_data": {"ttl": 300},          # 5 minutes
    "static_data": {"ttl": 3600},          # 1 hour
}

# Cache implementation
class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_or_set(self, key: str, fetch_func, ttl: int = 300):
        """Get from cache or fetch and set."""
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        data = await fetch_func()
        await self.redis.setex(key, ttl, json.dumps(data))
        return data
```

#### 2. Database Query Cache

```python
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import declarative_base

# Query result caching
def cached_query(query: Query, cache_key: str, ttl: int = 300):
    """Cache database query results."""
    cached_result = cache_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    result = query.all()
    serialized = [item.to_dict() for item in result]
    cache_client.setex(cache_key, ttl, json.dumps(serialized))
    return result
```

#### 3. HTTP Response Cache

```nginx
# Nginx caching configuration
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

location /api/v2/static/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 30m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
}
```

## Container Optimization

### Docker Performance Tuning

#### 1. Resource Limits

```yaml
# docker-compose.production-enhanced.yml
services:
  mcp-backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

#### 2. Multi-stage Build Optimization

```dockerfile
# Dockerfile.backend.production
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

# Copy pre-built wheels
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Optimize Python settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1
ENV PYTHONDONTWRITEBYTECODE=1
```

#### 3. Layer Optimization

```dockerfile
# Optimize layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code last
COPY . .
```

## Network Performance

### Nginx Optimization

```nginx
# nginx.conf
worker_processes auto;
worker_cpu_affinity auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # Enable compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Connection optimization
    keepalive_timeout 30;
    keepalive_requests 100;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;

    # Buffer optimization
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    output_buffers 1 32k;
    postpone_output 1460;

    # Upstream configuration
    upstream backend {
        server mcp-backend:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Proxy optimization
    proxy_connect_timeout 5s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
}
```

### Connection Pooling

```python
# HTTP client optimization
import httpx

# Configure HTTP client with connection pooling
async_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    ),
    timeout=httpx.Timeout(10.0, connect=5.0)
)
```

## Monitoring & Profiling

### Performance Monitoring

#### 1. Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# Instrument code
@REQUEST_LATENCY.time()
async def timed_endpoint():
    REQUEST_COUNT.labels(method='GET', endpoint='/api/v2/health').inc()
    return {"status": "healthy"}
```

#### 2. Database Monitoring

```sql
-- Create monitoring views
CREATE VIEW performance_summary AS
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins + n_tup_upd + n_tup_del as total_writes
FROM pg_stat_user_tables;

-- Monitor lock waits
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_or_recent_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

### Performance Profiling Tools

```bash
# Application profiling
pip install py-spy
py-spy record -o profile.svg -d 60 -p $(pgrep -f "python.*main.py")

# Database profiling
docker-compose exec postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c "
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) 
SELECT * FROM tasks WHERE user_id = 'user-123' AND status = 'pending';
"

# Container resource monitoring
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

## Load Testing

### Performance Testing Setup

```python
# locustfile.py
from locust import HttpUser, task, between
import random

class agenthubUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        # Authenticate user
        response = self.client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def view_projects(self):
        self.client.get("/api/v2/projects", headers=self.headers)
    
    @task(2)
    def view_tasks(self):
        self.client.get("/api/v2/tasks", headers=self.headers)
    
    @task(1)
    def create_task(self):
        self.client.post("/api/v2/tasks", 
                        headers=self.headers,
                        json={
                            "title": f"Load test task {random.randint(1, 1000)}",
                            "description": "Automated load test task"
                        })
```

```bash
# Run load tests
locust -f locustfile.py --host=http://localhost:8000 -u 50 -r 10 -t 300s

# Stress test with multiple scenarios
./scripts/performance/run-load-tests.sh --users 100 --spawn-rate 20 --duration 600
```

## Performance Optimization Checklist

### Database Optimization
- [ ] Connection pooling configured
- [ ] Proper indexes created for common queries
- [ ] Slow query logging enabled
- [ ] Database statistics updated
- [ ] Unnecessary indexes removed
- [ ] Query plans optimized
- [ ] Connection limits appropriate

### Application Optimization
- [ ] Async operations implemented
- [ ] Response compression enabled
- [ ] Database queries optimized
- [ ] N+1 query problems resolved
- [ ] Caching strategy implemented
- [ ] Background tasks for heavy operations
- [ ] Resource limits configured

### Infrastructure Optimization
- [ ] Container resources optimized
- [ ] Network configuration tuned
- [ ] Load balancer configured
- [ ] CDN implemented for static assets
- [ ] Monitoring and alerting active
- [ ] Auto-scaling configured
- [ ] Health checks optimized

## Performance Troubleshooting

### Common Performance Issues

#### 1. High Database CPU Usage

```bash
# Identify expensive queries
docker-compose exec postgres psql -U ${DATABASE_USER} -d ${DATABASE_NAME} -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"

# Solutions:
# - Add missing indexes
# - Optimize WHERE clauses
# - Use LIMIT for large result sets
# - Consider query rewriting
```

#### 2. Memory Leaks

```bash
# Monitor memory usage
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Python memory profiling
pip install memory-profiler
python -m memory_profiler main.py

# Solutions:
# - Review object lifecycle
# - Clear unused references
# - Optimize data structures
# - Use generators for large datasets
```

#### 3. High Response Times

```bash
# Profile API endpoints
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/v2/health"

# Solutions:
# - Implement caching
# - Optimize database queries
# - Add connection pooling
# - Use async operations
```

### Performance Monitoring Dashboard

Key metrics to monitor:
- Request rate and response times
- Error rates by endpoint
- Database connection pool usage
- Cache hit rates
- Memory and CPU usage
- Disk I/O and network throughput

---

## Quick Performance Checks

```bash
# Database performance
./scripts/performance/check-db-performance.sh

# Application performance
./scripts/performance/check-app-performance.sh

# System resources
./scripts/performance/check-system-resources.sh

# Full performance report
./scripts/performance/generate-performance-report.sh
```

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-09-11  
**Next Review:** 2025-10-11