# Cloud MCP Platform - Deployment Guide

## Overview

This guide covers deploying the Cloud MCP Platform to various cloud providers and on-premises infrastructure.

## Deployment Options

### Cloud Providers
- **AWS**: ECS, EKS, or EC2
- **Google Cloud**: GKE, Cloud Run, or Compute Engine
- **Azure**: AKS, Container Instances, or VMs
- **DigitalOcean**: Kubernetes, App Platform
- **Self-Hosted**: Docker, Kubernetes, or bare metal

## Prerequisites

### Required Tools
```bash
# Check required tools
docker --version          # Docker 20.10+
docker-compose --version   # Docker Compose 2.0+
kubectl version           # Kubernetes CLI 1.25+
terraform --version       # Terraform 1.5+ (optional)
helm version             # Helm 3.10+ (optional)
```

### Required Resources
- **Minimum**: 2 vCPUs, 4GB RAM, 20GB storage
- **Recommended**: 4 vCPUs, 8GB RAM, 100GB storage
- **Production**: 8+ vCPUs, 16GB+ RAM, 500GB+ storage

## Quick Deploy with Docker Compose

### 1. Clone Repository
```bash
git clone https://github.com/your-org/cloud-mcp-platform.git
cd cloud-mcp-platform
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` file:
```env
# Application
APP_ENV=production
APP_PORT=8000
APP_SECRET_KEY=generate-strong-secret-key

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/cloudmcp
REDIS_URL=redis://redis:6379

# Storage
S3_BUCKET=cloud-mcp-storage
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=us-east-1

# Authentication
JWT_SECRET=generate-jwt-secret
JWT_EXPIRY=3600

# External Services
OPENAI_API_KEY=your-openai-key  # Optional
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=smtp-password
```

### 3. Deploy with Docker Compose
```bash
# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Kubernetes Deployment

### 1. Prepare Kubernetes Cluster

**Local Development (Minikube)**:
```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
```

**Production (EKS Example)**:
```bash
eksctl create cluster \
  --name cloud-mcp-cluster \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed
```

### 2. Create Namespace and Secrets
```bash
# Create namespace
kubectl create namespace cloud-mcp

# Create secrets
kubectl create secret generic cloud-mcp-secrets \
  --from-literal=database-url='postgresql://user:pass@host:5432/db' \
  --from-literal=jwt-secret='your-jwt-secret' \
  --from-literal=s3-access-key='your-s3-key' \
  --from-literal=s3-secret-key='your-s3-secret' \
  -n cloud-mcp
```

### 3. Deploy with Helm

```bash
# Add Helm repository
helm repo add cloud-mcp https://charts.cloud-mcp.example.com
helm repo update

# Install chart
helm install cloud-mcp cloud-mcp/platform \
  --namespace cloud-mcp \
  --values values.yaml \
  --set image.tag=latest \
  --set ingress.enabled=true \
  --set ingress.host=api.cloud-mcp.example.com
```

**Custom values.yaml**:
```yaml
replicaCount: 3

image:
  repository: cloud-mcp/platform
  tag: v1.0.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.cloud-mcp.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: cloud-mcp-tls
      hosts:
        - api.cloud-mcp.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1024Mi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true
  auth:
    database: cloudmcp
    username: cloudmcp
    password: changeme

redis:
  enabled: true
  auth:
    enabled: true
    password: changeme
```

### 4. Deploy with Raw Kubernetes Manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-mcp-platform
  namespace: cloud-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloud-mcp
  template:
    metadata:
      labels:
        app: cloud-mcp
    spec:
      containers:
      - name: cloud-mcp
        image: cloud-mcp/platform:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: cloud-mcp-secrets
              key: database-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: cloud-mcp-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: cloud-mcp-service
  namespace: cloud-mcp
spec:
  selector:
    app: cloud-mcp
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply manifests:
```bash
kubectl apply -f deployment.yaml
kubectl get pods -n cloud-mcp
kubectl get svc -n cloud-mcp
```

## AWS Deployment

### Using AWS ECS with Fargate

```terraform
# main.tf
provider "aws" {
  region = "us-east-1"
}

resource "aws_ecs_cluster" "cloud_mcp" {
  name = "cloud-mcp-cluster"
}

resource "aws_ecs_task_definition" "cloud_mcp" {
  family                   = "cloud-mcp-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"

  container_definitions = jsonencode([
    {
      name  = "cloud-mcp"
      image = "cloud-mcp/platform:latest"
      
      environment = [
        {
          name  = "APP_ENV"
          value = "production"
        }
      ]
      
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.db_url.arn
        }
      ]
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/cloud-mcp"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "cloud_mcp" {
  name            = "cloud-mcp-service"
  cluster         = aws_ecs_cluster.cloud_mcp.id
  task_definition = aws_ecs_task_definition.cloud_mcp.arn
  desired_count   = 3
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.cloud_mcp.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cloud_mcp.arn
    container_name   = "cloud-mcp"
    container_port   = 8000
  }
}
```

Deploy with Terraform:
```bash
terraform init
terraform plan
terraform apply
```

### Using AWS Lambda (Serverless)

```yaml
# serverless.yml
service: cloud-mcp-platform

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  environment:
    DATABASE_URL: ${env:DATABASE_URL}
    JWT_SECRET: ${env:JWT_SECRET}

functions:
  api:
    handler: src.main.handler
    events:
      - httpApi:
          path: /{proxy+}
          method: ANY
    timeout: 30
    memorySize: 1024

plugins:
  - serverless-python-requirements
  - serverless-offline

custom:
  pythonRequirements:
    dockerizePip: true
```

Deploy:
```bash
npm install -g serverless
serverless deploy --stage production
```

## Google Cloud Deployment

### Using Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/cloud-mcp

# Deploy to Cloud Run
gcloud run deploy cloud-mcp \
  --image gcr.io/PROJECT_ID/cloud-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="APP_ENV=production" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --min-instances=1 \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=2
```

### Using GKE

```bash
# Create GKE cluster
gcloud container clusters create cloud-mcp-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2

# Get credentials
gcloud container clusters get-credentials cloud-mcp-cluster \
  --zone us-central1-a

# Deploy application
kubectl apply -f k8s/
```

## Azure Deployment

### Using Azure Container Instances

```bash
# Create resource group
az group create --name cloud-mcp-rg --location eastus

# Create container instance
az container create \
  --resource-group cloud-mcp-rg \
  --name cloud-mcp \
  --image cloud-mcp/platform:latest \
  --dns-name-label cloud-mcp \
  --ports 8000 \
  --environment-variables \
    APP_ENV=production \
  --secure-environment-variables \
    DATABASE_URL=$DATABASE_URL \
    JWT_SECRET=$JWT_SECRET \
  --cpu 2 \
  --memory 4
```

### Using AKS

```bash
# Create AKS cluster
az aks create \
  --resource-group cloud-mcp-rg \
  --name cloud-mcp-cluster \
  --node-count 3 \
  --node-vm-size Standard_DS2_v2 \
  --enable-addons monitoring

# Get credentials
az aks get-credentials \
  --resource-group cloud-mcp-rg \
  --name cloud-mcp-cluster

# Deploy application
kubectl apply -f k8s/
```

## Database Setup

### PostgreSQL

```sql
-- Create database and user
CREATE DATABASE cloudmcp;
CREATE USER cloudmcp WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE cloudmcp TO cloudmcp;

-- Run migrations
python manage.py migrate
```

### MongoDB (Alternative)

```javascript
// Create database and collection
use cloudmcp
db.createCollection("tasks")
db.createCollection("agents")
db.createCollection("templates")

// Create indexes
db.tasks.createIndex({ "status": 1, "priority": -1 })
db.agents.createIndex({ "capabilities": 1 })
```

## SSL/TLS Configuration

### Using Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.cloud-mcp.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Using Cloudflare

1. Add domain to Cloudflare
2. Enable "Full (strict)" SSL mode
3. Create origin certificate
4. Configure nginx with origin certificate

## Monitoring Setup

### Prometheus + Grafana

```yaml
# prometheus.yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cloud-mcp'
    static_configs:
      - targets: ['cloud-mcp:8000']
```

```bash
# Deploy monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

### Application Metrics

```python
# src/metrics.py
from prometheus_client import Counter, Histogram, Gauge

task_created = Counter('tasks_created_total', 'Total tasks created')
task_duration = Histogram('task_duration_seconds', 'Task execution duration')
active_agents = Gauge('active_agents', 'Number of active agents')
```

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DB_NAME="cloudmcp"
DATE=$(date +%Y%m%d_%H%M%S)

pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

### File Storage Backup

```bash
# S3 sync
aws s3 sync s3://cloud-mcp-storage s3://cloud-mcp-backup --delete

# Google Cloud Storage
gsutil -m rsync -r gs://cloud-mcp-storage gs://cloud-mcp-backup
```

## Health Checks

### Endpoints

```python
# Health check endpoints
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    # Check database connection
    # Check Redis connection
    # Check S3 access
    return {"status": "ready"}
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Security Hardening

### Network Security

```yaml
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cloud-mcp-network-policy
spec:
  podSelector:
    matchLabels:
      app: cloud-mcp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
```

### Secret Management

```bash
# Using HashiCorp Vault
vault kv put secret/cloud-mcp \
  database_url="postgresql://..." \
  jwt_secret="..." \
  s3_access_key="..."

# Using AWS Secrets Manager
aws secretsmanager create-secret \
  --name cloud-mcp/production \
  --secret-string file://secrets.json
```

## Performance Tuning

### Application Optimization

```python
# Async connection pooling
from databases import Database

database = Database(
    DATABASE_URL,
    min_size=10,
    max_size=20,
    command_timeout=60
)

# Redis connection pooling
import redis

redis_pool = redis.ConnectionPool(
    host='redis',
    port=6379,
    max_connections=50
)
```

### Infrastructure Optimization

```yaml
# HPA Configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cloud-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cloud-mcp
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check network connectivity
nc -zv postgres-host 5432
```

**Memory Issues**
```bash
# Check memory usage
kubectl top pods -n cloud-mcp

# Increase memory limits
kubectl set resources deployment cloud-mcp \
  --limits=memory=2Gi \
  --requests=memory=1Gi
```

**Performance Issues**
```bash
# Enable debug logging
kubectl set env deployment/cloud-mcp LOG_LEVEL=DEBUG

# Check slow queries
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

## Production Checklist

- [ ] SSL/TLS certificates configured
- [ ] Database backups automated
- [ ] Monitoring and alerting setup
- [ ] Logging aggregation configured
- [ ] Security scanning enabled
- [ ] Rate limiting configured
- [ ] CORS settings reviewed
- [ ] Environment variables secured
- [ ] Health checks implemented
- [ ] Auto-scaling configured
- [ ] Disaster recovery tested
- [ ] Documentation updated

## Support

For deployment assistance:
- **Documentation**: [docs.cloud-mcp.example.com](https://docs.cloud-mcp.example.com)
- **Support**: support@cloud-mcp.example.com
- **Enterprise Support**: enterprise@cloud-mcp.example.com