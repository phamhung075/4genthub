# Claude Hooks Docker Configuration Guide

## Overview

This document provides complete Docker configuration examples for deploying the Claude hooks system as a containerized service, including Dockerfiles, docker-compose configurations, and deployment scripts.

## Dockerfile Configurations

### 1. Production Dockerfile

```dockerfile
# Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r claude && \
    useradd -r -g claude -d /app -s /sbin/nologin claude

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=claude:claude src/ ./src/
COPY --chown=claude:claude config/ ./config/
COPY --chown=claude:claude scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R claude:claude /app

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HOOKS_ENV=production

# Switch to non-root user
USER claude

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9000/health/status || exit 1

# Expose port
EXPOSE 9000

# Run application
CMD ["python", "-m", "uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "9000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--access-log", \
     "--log-config", "/app/config/logging.yaml"]
```

### 2. Development Dockerfile

```dockerfile
# Dockerfile.dev
# Development image with hot-reload and debugging capabilities

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt -r requirements-dev.txt

# Install development tools
RUN pip install \
    ipython \
    ipdb \
    black \
    flake8 \
    mypy \
    pytest-watch

# Set environment variables
ENV PYTHONPATH=/app \
    HOOKS_ENV=development \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create directories
RUN mkdir -p /app/data /app/logs

# Expose ports (API + debugger)
EXPOSE 9000 5678

# Volume mounts for development
VOLUME ["/app/src", "/app/tests", "/app/config"]

# Run with hot-reload
CMD ["python", "-m", "uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "9000", \
     "--reload", \
     "--reload-dir", "/app/src", \
     "--log-level", "debug"]
```

### 3. Testing Dockerfile

```dockerfile
# Dockerfile.test
# Image for running tests in CI/CD

FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# Copy application and tests
COPY src/ ./src/
COPY tests/ ./tests/
COPY config/ ./config/
COPY pytest.ini ./

# Set environment
ENV PYTHONPATH=/app \
    HOOKS_ENV=testing

# Run tests
CMD ["pytest", "-v", "--cov=src", "--cov-report=term-missing", "--cov-report=xml"]
```

## Docker Compose Configurations

### 1. Production Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

x-common-variables: &common-variables
  TZ: UTC
  LOG_LEVEL: INFO

services:
  claude-hooks:
    image: claude-hooks:${VERSION:-latest}
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_DATE=${BUILD_DATE:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}
        - VERSION=${VERSION:-latest}
    container_name: claude-hooks-service

    ports:
      - "${API_PORT:-9000}:9000"

    volumes:
      # Mount project directory (read-only)
      - ${PROJECT_PATH:-./project}:/project:ro

      # Persistent volumes
      - hooks-data:/app/data
      - hooks-logs:/app/logs

      # Configuration
      - ./config/production.yaml:/app/config/production.yaml:ro

      # SSL certificates (if needed)
      - ./certs:/app/certs:ro

    environment:
      <<: *common-variables
      HOOKS_ENV: production
      API_PORT: 9000

      # Database URLs
      POSTGRES_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0

      # MCP Server
      MCP_SERVER_URL: ${MCP_SERVER_URL:-http://mcp-server:8000}
      MCP_API_KEY: ${MCP_API_KEY}

      # Authentication
      JWT_SECRET: ${JWT_SECRET}
      KEYCLOAK_URL: ${KEYCLOAK_URL:-http://keycloak:8080}
      KEYCLOAK_REALM: ${KEYCLOAK_REALM:-dhafnck}
      KEYCLOAK_CLIENT_ID: ${KEYCLOAK_CLIENT_ID:-claude-hooks}
      KEYCLOAK_CLIENT_SECRET: ${KEYCLOAK_CLIENT_SECRET}

      # Project paths
      PROJECT_PATH: /project
      AI_DOCS_PATH: /project/ai_docs
      AI_DATA_PATH: /app/data

    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

    networks:
      - claude-network

    restart: unless-stopped

    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        labels: "service=claude-hooks"

  postgres:
    image: postgres:15-alpine
    container_name: claude-postgres

    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d:ro

    environment:
      POSTGRES_DB: ${DB_NAME:-claude_hooks}
      POSTGRES_USER: ${DB_USER:-claude}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"

    ports:
      - "${DB_PORT:-5432}:5432"

    networks:
      - claude-network

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-claude} -d ${DB_NAME:-claude_hooks}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: claude-redis

    volumes:
      - redis-data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro

    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}

    ports:
      - "${REDIS_PORT:-6379}:6379"

    networks:
      - claude-network

    command: >
      redis-server /usr/local/etc/redis/redis.conf
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --appendfsync everysec

    healthcheck:
      test: ["CMD", "redis-cli", "--auth", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: claude-nginx

    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
      - nginx-cache:/var/cache/nginx

    ports:
      - "80:80"
      - "443:443"

    networks:
      - claude-network

    depends_on:
      - claude-hooks

    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: claude-prometheus

    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus

    ports:
      - "${PROMETHEUS_PORT:-9090}:9090"

    networks:
      - claude-network

    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'

    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: claude-grafana

    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro

    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: redis-datasource

    ports:
      - "${GRAFANA_PORT:-3000}:3000"

    networks:
      - claude-network

    depends_on:
      - prometheus

    restart: unless-stopped

volumes:
  hooks-data:
    driver: local
  hooks-logs:
    driver: local
  postgres-data:
    driver: local
  redis-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
  nginx-cache:
    driver: local

networks:
  claude-network:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.28.0.0/16
```

### 2. Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  claude-hooks-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: claude-hooks-dev

    ports:
      - "9000:9000"    # API
      - "5678:5678"    # Python debugger

    volumes:
      # Mount source code for hot-reload
      - ./src:/app/src
      - ./tests:/app/tests
      - ./config:/app/config

      # Mount project for testing
      - ${PROJECT_PATH:-../project}:/project

      # Persistent data
      - ./data:/app/data
      - ./logs:/app/logs

    environment:
      HOOKS_ENV: development
      DEBUG: "true"
      LOG_LEVEL: DEBUG

      # Use local services
      POSTGRES_URL: postgresql://dev:dev@postgres-dev:5432/claude_hooks_dev
      REDIS_URL: redis://redis-dev:6379/0

      # Mock MCP server for development
      MCP_SERVER_URL: http://mock-mcp:8000

      # Development JWT secret
      JWT_SECRET: dev-secret-key-change-in-production

      # Project paths
      PROJECT_PATH: /project
      AI_DOCS_PATH: /project/ai_docs
      AI_DATA_PATH: /app/data

      # Python debugging
      PYTHONBREAKPOINT: ipdb.set_trace

    depends_on:
      - postgres-dev
      - redis-dev
      - mock-mcp

    networks:
      - claude-dev-network

    stdin_open: true
    tty: true

  postgres-dev:
    image: postgres:15-alpine
    container_name: claude-postgres-dev

    environment:
      POSTGRES_DB: claude_hooks_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev

    ports:
      - "5433:5432"

    volumes:
      - postgres-dev-data:/var/lib/postgresql/data

    networks:
      - claude-dev-network

  redis-dev:
    image: redis:7-alpine
    container_name: claude-redis-dev

    ports:
      - "6380:6379"

    networks:
      - claude-dev-network

  mock-mcp:
    build:
      context: ./tests/mocks
      dockerfile: Dockerfile.mock-mcp
    container_name: mock-mcp-server

    ports:
      - "8001:8000"

    networks:
      - claude-dev-network

    environment:
      MOCK_MODE: "true"
      RESPONSE_DELAY: 0

  mailhog:
    image: mailhog/mailhog
    container_name: claude-mailhog

    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

    networks:
      - claude-dev-network

  adminer:
    image: adminer
    container_name: claude-adminer

    ports:
      - "8080:8080"

    networks:
      - claude-dev-network

    environment:
      ADMINER_DEFAULT_SERVER: postgres-dev

volumes:
  postgres-dev-data:
    driver: local

networks:
  claude-dev-network:
    driver: bridge
```

## Supporting Configuration Files

### 1. Redis Configuration

```conf
# redis.conf
# Redis configuration for Claude hooks

# Network
bind 0.0.0.0
protected-mode yes
port 6379

# General
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""

# Persistence
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data

# Append only mode
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Limits
maxclients 10000
maxmemory 256mb
maxmemory-policy allkeys-lru

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Advanced
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
```

### 2. Nginx Configuration

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml application/atom+xml image/svg+xml
               text/x-js text/x-cross-domain-policy application/x-font-ttf
               application/x-font-opentype application/vnd.ms-fontobject
               image/x-icon;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Upstream
    upstream claude_hooks {
        least_conn;
        server claude-hooks:9000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Include server configurations
    include /etc/nginx/conf.d/*.conf;
}
```

```nginx
# nginx/conf.d/claude-hooks.conf
server {
    listen 80;
    server_name _;

    # Redirect to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    # SSL Configuration
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API endpoints
    location /api/ {
        proxy_pass http://claude_hooks;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering off;
        proxy_request_buffering off;

        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        limit_conn addr 10;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://claude_hooks;
        proxy_http_version 1.1;

        # WebSocket headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts for WebSocket
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://claude_hooks/health;
        access_log off;
    }

    # Metrics endpoint (internal only)
    location /metrics {
        proxy_pass http://claude_hooks/metrics;
        allow 172.28.0.0/16;  # Internal network only
        deny all;
    }
}
```

### 3. Environment Configuration

```bash
# .env.example
# Claude Hooks Docker Environment Configuration

# Service Configuration
API_PORT=9000
LOG_LEVEL=INFO
DEBUG=false

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=claude_hooks
DB_USER=claude
DB_PASSWORD=your-secure-password-here

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password-here

# MCP Server Configuration
MCP_SERVER_URL=http://mcp-server:8000
MCP_API_KEY=your-mcp-api-key-here
MCP_TIMEOUT=30

# Authentication
JWT_SECRET=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Keycloak Configuration (optional)
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=dhafnck
KEYCLOAK_CLIENT_ID=claude-hooks
KEYCLOAK_CLIENT_SECRET=your-keycloak-secret-here

# Project Paths
PROJECT_PATH=/path/to/your/project
AI_DOCS_PATH=/path/to/your/project/ai_docs
AI_DATA_PATH=/app/data

# Performance
MAX_WORKERS=4
REQUEST_TIMEOUT=60
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin

# Security
ALLOWED_ORIGINS=http://localhost:*,https://yourdomain.com
API_KEY=optional-api-key-for-additional-security

# Version
VERSION=1.0.0
BUILD_DATE=2024-01-15T00:00:00Z
```

## Deployment Scripts

### 1. Build Script

```bash
#!/bin/bash
# scripts/build.sh

set -e

# Configuration
REGISTRY=${DOCKER_REGISTRY:-"docker.io"}
NAMESPACE=${DOCKER_NAMESPACE:-"claude-hooks"}
IMAGE_NAME="claude-hooks"
VERSION=${VERSION:-$(git describe --tags --always --dirty)}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Claude Hooks Docker Image${NC}"
echo "Version: ${VERSION}"

# Build production image
echo -e "${YELLOW}Building production image...${NC}"
docker build \
    --build-arg VERSION=${VERSION} \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --tag ${IMAGE_NAME}:${VERSION} \
    --tag ${IMAGE_NAME}:latest \
    --file Dockerfile \
    .

# Build development image
echo -e "${YELLOW}Building development image...${NC}"
docker build \
    --tag ${IMAGE_NAME}:dev \
    --file Dockerfile.dev \
    .

# Build test image
echo -e "${YELLOW}Building test image...${NC}"
docker build \
    --tag ${IMAGE_NAME}:test \
    --file Dockerfile.test \
    .

# Tag for registry
if [ ! -z "${DOCKER_REGISTRY}" ]; then
    echo -e "${YELLOW}Tagging for registry...${NC}"
    docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${VERSION}
    docker tag ${IMAGE_NAME}:latest ${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:latest
fi

echo -e "${GREEN}Build complete!${NC}"

# Display image sizes
echo -e "${YELLOW}Image sizes:${NC}"
docker images | grep ${IMAGE_NAME}
```

### 2. Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.${ENVIRONMENT}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Deploying Claude Hooks - Environment: ${ENVIRONMENT}${NC}"

# Check environment file
if [ ! -f "${ENV_FILE}" ]; then
    echo -e "${RED}Error: Environment file ${ENV_FILE} not found${NC}"
    exit 1
fi

# Select compose file based on environment
if [ "${ENVIRONMENT}" = "development" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
elif [ "${ENVIRONMENT}" = "testing" ]; then
    COMPOSE_FILE="docker-compose.test.yml"
fi

echo -e "${YELLOW}Using compose file: ${COMPOSE_FILE}${NC}"

# Load environment variables
export $(cat ${ENV_FILE} | grep -v '^#' | xargs)

# Pull latest images
echo -e "${YELLOW}Pulling latest images...${NC}"
docker-compose -f ${COMPOSE_FILE} pull

# Stop existing services
echo -e "${YELLOW}Stopping existing services...${NC}"
docker-compose -f ${COMPOSE_FILE} down

# Start services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f ${COMPOSE_FILE} up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
./scripts/health-check.sh

# Run database migrations
if [ "${ENVIRONMENT}" != "testing" ]; then
    echo -e "${YELLOW}Running database migrations...${NC}"
    docker-compose -f ${COMPOSE_FILE} exec claude-hooks python scripts/migrate.py
fi

echo -e "${GREEN}Deployment complete!${NC}"

# Show service status
docker-compose -f ${COMPOSE_FILE} ps
```

### 3. Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

set -e

# Configuration
MAX_RETRIES=30
RETRY_INTERVAL=2
API_URL=${API_URL:-"http://localhost:9000"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Checking service health...${NC}"

# Check Claude Hooks API
echo -n "Checking Claude Hooks API..."
for i in $(seq 1 ${MAX_RETRIES}); do
    if curl -sf ${API_URL}/health/status > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi

    if [ $i -eq ${MAX_RETRIES} ]; then
        echo -e " ${RED}✗${NC}"
        echo -e "${RED}Error: API health check failed${NC}"
        exit 1
    fi

    echo -n "."
    sleep ${RETRY_INTERVAL}
done

# Check PostgreSQL
echo -n "Checking PostgreSQL..."
for i in $(seq 1 ${MAX_RETRIES}); do
    if docker-compose exec -T postgres pg_isready > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi

    if [ $i -eq ${MAX_RETRIES} ]; then
        echo -e " ${RED}✗${NC}"
        echo -e "${RED}Error: PostgreSQL health check failed${NC}"
        exit 1
    fi

    echo -n "."
    sleep ${RETRY_INTERVAL}
done

# Check Redis
echo -n "Checking Redis..."
for i in $(seq 1 ${MAX_RETRIES}); do
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi

    if [ $i -eq ${MAX_RETRIES} ]; then
        echo -e " ${RED}✗${NC}"
        echo -e "${RED}Error: Redis health check failed${NC}"
        exit 1
    fi

    echo -n "."
    sleep ${RETRY_INTERVAL}
done

echo -e "${GREEN}All services are healthy!${NC}"
```

## Makefile

```makefile
# Makefile
.PHONY: help build deploy test clean logs status

# Variables
ENVIRONMENT ?= production
VERSION ?= $(shell git describe --tags --always --dirty)
COMPOSE_FILE = docker-compose.yml
COMPOSE_DEV_FILE = docker-compose.dev.yml

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	@./scripts/build.sh

deploy: ## Deploy services
	@./scripts/deploy.sh $(ENVIRONMENT)

dev: ## Start development environment
	@docker-compose -f $(COMPOSE_DEV_FILE) up

test: ## Run tests
	@docker-compose -f docker-compose.test.yml up --abort-on-container-exit
	@docker-compose -f docker-compose.test.yml down

clean: ## Clean up containers and volumes
	@docker-compose -f $(COMPOSE_FILE) down -v
	@docker-compose -f $(COMPOSE_DEV_FILE) down -v
	@docker system prune -f

logs: ## Show logs
	@docker-compose -f $(COMPOSE_FILE) logs -f

status: ## Show service status
	@docker-compose -f $(COMPOSE_FILE) ps

shell: ## Open shell in running container
	@docker-compose -f $(COMPOSE_FILE) exec claude-hooks /bin/bash

db-shell: ## Open PostgreSQL shell
	@docker-compose -f $(COMPOSE_FILE) exec postgres psql -U claude claude_hooks

redis-cli: ## Open Redis CLI
	@docker-compose -f $(COMPOSE_FILE) exec redis redis-cli

migrate: ## Run database migrations
	@docker-compose -f $(COMPOSE_FILE) exec claude-hooks python scripts/migrate.py

backup: ## Backup database
	@docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U claude claude_hooks > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database from backup
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U claude claude_hooks < $(BACKUP_FILE)

monitor: ## Open monitoring dashboard
	@open http://localhost:3000

lint: ## Run linters
	@docker-compose -f $(COMPOSE_DEV_FILE) exec claude-hooks-dev black src/ tests/
	@docker-compose -f $(COMPOSE_DEV_FILE) exec claude-hooks-dev flake8 src/ tests/
	@docker-compose -f $(COMPOSE_DEV_FILE) exec claude-hooks-dev mypy src/

format: ## Format code
	@docker-compose -f $(COMPOSE_DEV_FILE) exec claude-hooks-dev black src/ tests/

security-scan: ## Run security scan
	@docker run --rm -v $(PWD):/src aquasec/trivy fs /src
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image claude-hooks:latest
```

## Conclusion

This comprehensive Docker configuration guide provides everything needed to containerize and deploy the Claude hooks system:

1. **Production-ready Dockerfiles** with multi-stage builds and security best practices
2. **Complete docker-compose configurations** for different environments
3. **Supporting configuration files** for all services
4. **Deployment automation scripts** for easy management
5. **Makefile** for common operations

The configuration supports:
- Horizontal scaling
- High availability
- Security best practices
- Monitoring and observability
- Development workflow
- Automated testing
- Easy deployment

This setup can be deployed to any Docker-compatible environment including local development, cloud providers, or Kubernetes clusters.