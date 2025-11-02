# Agent Management Developer Guide

**Version**: 2.0.0
**Last Updated**: 2025-11-02
**Architecture**: Domain-Driven Design (DDD)

## Overview

This guide provides technical documentation for developers working on the agent management system, extending it with new features, or adding custom agent templates.

**Target Audience**:
- Backend developers
- DevOps engineers
- System architects
- Contributors

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Domain Model](#domain-model)
3. [Database Schema](#database-schema)
4. [Adding New Agent Templates](#adding-new-agent-templates)
5. [Extending the System](#extending-the-system)
6. [Testing Strategy](#testing-strategy)
7. [Deployment](#deployment)
8. [Performance Optimization](#performance-optimization)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
├─────────────────────────────────────────────────────────────┤
│  MCP Interface     │     REST API        │   Frontend (React)│
│  (call_agent)      │  (12 endpoints)     │   (Agent Manager) │
└────────┬───────────┴──────────┬──────────┴─────────┬─────────┘
         │                      │                    │
         └──────────────────────┼────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  AgentManagementFacade  │  Use Cases  │  DTOs & Mappers     │
└────────────────────────┬─────────────────────────┬──────────┘
                         │                         │
┌─────────────────────────────────────────────────────────────┐
│                       Domain Layer                           │
├─────────────────────────────────────────────────────────────┤
│  Entities:              │  Services:             │  Value    │
│  - AgentTemplate        │  - AgentInstantiation  │  Objects  │
│  - UserAgentInstance    │  - AgentCustomization  │           │
│                         │  - AgentSharing        │           │
└────────────────────────┬─────────────────────────┴──────────┘
                         │
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
├─────────────────────────────────────────────────────────────┤
│  ORM Repositories  │  SQLAlchemy Models  │  External APIs    │
└────────────────────┴─────────────────────┴───────────────────┘
```

### Layer Responsibilities

**Presentation Layer**:
- MCP tool (`call_agent`) - Agent inst antiation for MCP clients
- REST API - Full CRUD operations for web clients
- Frontend - React components with markdown editor

**Application Layer**:
- `AgentManagementFacade` - Orchestrates domain services
- Use cases - Encapsulate business workflows
- DTOs - Data transfer between layers

**Domain Layer**:
- Entities - Core business objects with behavior
- Services - Complex business logic
- Value objects - Immutable domain concepts

**Infrastructure Layer**:
- Repositories - Data persistence abstraction
- ORM models - SQLAlchemy database mappings
- External integrations - YAML loaders, etc.

---

## Domain Model

### Core Entities

#### AgentTemplate

**Purpose**: System-defined agent configurations (immutable)

**File**: `src/fastmcp/task_management/domain/entities/agent_template.py`

**Attributes**:
```python
class AgentTemplate:
    id: AgentTemplateId              # UUID
    slug: str                         # URL-friendly identifier (e.g., "coding-agent")
    name: str                         # Display name
    category: str                     # Category (development, testing, etc.)
    version: str                      # Semantic version
    default_configuration: dict       # Instructions, rules, capabilities
    metadata: dict                    # Tags, popularity, use cases
    created_at: datetime
    updated_at: datetime
```

**Key Methods**:
- `from_yaml(yaml_path: str) -> AgentTemplate` - Load from YAML
- `to_dict() -> dict` - Serialize to dictionary
- `validate() -> None` - Validate configuration

**Invariants**:
- Slug must be unique
- Configuration must have required fields: instructions, rules, capabilities
- Templates are immutable after creation

#### UserAgentInstance

**Purpose**: User-specific copy of a template with customizations

**File**: `src/fastmcp/task_management/domain/entities/user_agent_instance.py`

**Attributes**:
```python
class UserAgentInstance:
    id: UserAgentInstanceId          # UUID
    user_id: UserId                  # Owner
    template_id: AgentTemplateId     # Source template
    custom_name: str                 # User-defined name
    custom_description: str | None   # User description
    custom_instructions: str | None  # Markdown instructions
    custom_rules: str | None         # Markdown rules
    custom_capabilities: str | None  # Markdown capabilities
    custom_output_format: str | None # Markdown output format
    is_customized: bool              # True if any customization exists
    visibility: str                  # "private" or "public"
    share_token: str | None          # Cryptographic share token (32 chars)
    original_creator_id: UserId | None  # If imported
    last_used_at: datetime | None    # Usage tracking
    created_at: datetime
    updated_at: datetime
```

**Key Methods**:
- `customize_configuration(**kwargs) -> None` - Update customizations
- `track_usage() -> None` - Update last_used_at
- `get_creator_display_name() -> str` - Get creator attribution
- `to_dict() -> dict` - Serialize

**Invariants**:
- UNIQUE constraint on (user_id, template_id)
- Share token must be 32 characters if visibility is public
- Cannot share if not customized

### Domain Services

**File**: `src/fastmcp/task_management/domain/services/agent_management/`

#### AgentInstantiationService

**Responsibility**: Create or retrieve agent instances

```python
class AgentInstantiationService:
    def get_or_create_instance(
        self,
        user_id: UserId,
        template_id: AgentTemplateId
    ) -> UserAgentInstance:
        """
        Get existing instance or create new one.
        Ensures one instance per (user, template) pair.
        """
```

#### AgentCustomizationService

**Responsibility**: Update agent configurations

```python
class AgentCustomizationService:
    def update_configuration(
        self,
        instance: UserAgentInstance,
        instructions_md: str | None = None,
        rules_md: str | None = None,
        capabilities_md: str | None = None,
        output_format_md: str | None = None
    ) -> UserAgentInstance:
        """
        Update instance configuration from markdown.
        Converts markdown to structured JSON.
        Marks instance as customized.
        """
```

#### AgentSharingService

**Responsibility**: Share and import logic

```python
class AgentSharingService:
    def generate_share_token(
        self,
        instance: UserAgentInstance
    ) -> str:
        """
        Generate cryptographically secure 32-char token.
        Uses secrets.token_urlsafe() for 128-bit entropy.
        """

    def import_agent(
        self,
        share_token: str,
        importing_user_id: UserId,
        custom_name: str | None = None
    ) -> UserAgentInstance:
        """
        Create copy of shared agent for importing user.
        Handles name collision with " - created by [creator]".
        Records in agent_import_history.
        """
```

---

## Database Schema

### Tables

#### agent_templates

```sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    default_configuration JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_templates_slug ON agent_templates(slug);
CREATE INDEX idx_agent_templates_category ON agent_templates(category);
```

#### user_agent_instances

```sql
CREATE TABLE user_agent_instances (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    template_id UUID REFERENCES agent_templates(id) ON DELETE CASCADE,
    custom_name VARCHAR(255) NOT NULL,
    custom_description TEXT,
    custom_instructions TEXT,
    custom_rules TEXT,
    custom_capabilities TEXT,
    custom_output_format TEXT,
    is_customized BOOLEAN DEFAULT FALSE,
    visibility VARCHAR(20) DEFAULT 'private',
    share_token VARCHAR(32) UNIQUE,
    original_creator_id UUID,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, template_id)
);

CREATE INDEX idx_user_agent_instances_user_id ON user_agent_instances(user_id);
CREATE INDEX idx_user_agent_instances_template_id ON user_agent_instances(template_id);
CREATE INDEX idx_user_agent_instances_share_token ON user_agent_instances(share_token);
CREATE INDEX idx_user_agent_instances_visibility ON user_agent_instances(visibility);
```

#### user_agent_configurations_md

```sql
CREATE TABLE user_agent_configurations_md (
    id UUID PRIMARY KEY,
    instance_id UUID REFERENCES user_agent_instances(id) ON DELETE CASCADE,
    configuration_type VARCHAR(50) NOT NULL,
    content_markdown TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(instance_id, configuration_type)
);

CREATE INDEX idx_user_agent_config_md_instance ON user_agent_configurations_md(instance_id);
```

#### agent_import_history

```sql
CREATE TABLE agent_import_history (
    id UUID PRIMARY KEY,
    importer_user_id UUID NOT NULL,
    source_instance_id UUID REFERENCES user_agent_instances(id) ON DELETE SET NULL,
    imported_instance_id UUID REFERENCES user_agent_instances(id) ON DELETE CASCADE,
    imported_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_agent_import_history_importer ON agent_import_history(importer_user_id);
CREATE INDEX idx_agent_import_history_source ON agent_import_history(source_instance_id);
```

### Migrations

**Location**: `agenthub_main/alembic/versions/`

**Create Migration**:
```bash
cd agenthub_main
alembic revision --autogenerate -m "Add agent management tables"
alembic upgrade head
```

---

## Adding New Agent Templates

### Step 1: Create YAML Definition

**Location**: `agenthub_main/agent-library/agents/{agent-slug}/`

**File Structure**:
```
agent-library/agents/my-new-agent/
├── contexts/
│   ├── instructions.yaml
│   ├── rules.yaml
│   ├── capabilities.yaml
│   └── output_format.yaml
└── metadata.yaml
```

**metadata.yaml**:
```yaml
name: My New Agent
slug: my-new-agent
category: custom
version: 1.0.0
description: Brief description of what this agent does
tags:
  - custom
  - specialized
popularity: 5.0
use_cases:
  - Use case 1
  - Use case 2
```

**contexts/instructions.yaml**:
```yaml
# Agent Instructions

You are a specialized agent for [specific purpose].

## Your Role
- Responsibility 1
- Responsibility 2

## Your Expertise
- Skill 1
- Skill 2
```

**contexts/rules.yaml**:
```yaml
## Standards

- Rule 1
- Rule 2

## Quality Requirements

- Requirement 1
- Requirement 2
```

**contexts/capabilities.yaml**:
```yaml
## Technical Skills

- Capability 1
- Capability 2

## Tools & Frameworks

- Tool 1
- Tool 2
```

**contexts/output_format.yaml**:
```yaml
## Response Format

Use clear, structured output.

## Code Examples

- Include complete examples
- Add inline comments
```

### Step 2: Populate Database

**Run Population Script**:
```bash
cd agenthub_main
python scripts/populate_agent_templates.py
```

**Script Logic**:
```python
# scripts/populate_agent_templates.py
from fastmcp.task_management.domain.services.yaml_agent_template_loader import YAMLAgentTemplateLoader
from fastmcp.task_management.infrastructure.repositories.orm_agent_template_repository import ORMAgentTemplateRepository

loader = YAMLAgentTemplateLoader()
repository = ORMAgentTemplateRepository(db_session)

# Load all agents from agent-library
agent_dir = Path("agent-library/agents")
for agent_path in agent_dir.iterdir():
    if agent_path.is_dir():
        template = loader.load_from_directory(agent_path)

        # Idempotent: update if exists, create if new
        existing = repository.find_by_slug(template.slug)
        if existing:
            repository.update(template)
        else:
            repository.save(template)
```

### Step 3: Verify

```bash
# Check database
psql -d agenthub -c "SELECT slug, name, version FROM agent_templates WHERE slug='my-new-agent';"

# Test via API
curl -X GET "http://localhost:8000/api/v2/agent-management/templates/my-new-agent" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test via MCP
# Use call_agent with new slug
```

---

## Extending the System

### Adding a New Sharing Feature

**Example**: Add expiring share links

**Step 1: Update Domain Entity**

```python
# src/fastmcp/task_management/domain/entities/user_agent_instance.py

class UserAgentInstance:
    # ... existing fields ...
    share_expires_at: datetime | None = None

    def is_share_expired(self) -> bool:
        if self.share_expires_at is None:
            return False
        return datetime.utcnow() > self.share_expires_at
```

**Step 2: Update Database**

```bash
alembic revision -m "Add share expiration"
```

```python
# alembic/versions/xxx_add_share_expiration.py

def upgrade():
    op.add_column('user_agent_instances', sa.Column('share_expires_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('user_agent_instances', 'share_expires_at')
```

**Step 3: Update Service**

```python
# src/fastmcp/task_management/domain/services/agent_management/agent_sharing_service.py

class AgentSharingService:
    def generate_share_token(
        self,
        instance: UserAgentInstance,
        expires_in_hours: int | None = None
    ) -> str:
        token = secrets.token_urlsafe(24)

        if expires_in_hours:
            instance.share_expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        return token
```

**Step 4: Update API**

```python
# src/fastmcp/task_management/interface/http/routes/agent_management_routes.py

@router.post("/instances/{instance_id}/share")
async def share_agent(
    instance_id: UUID,
    request: ShareAgentRequest,  # Add expires_in_hours field
    current_user: User = Depends(get_current_user)
):
    result = facade.share_agent(
        instance_id=instance_id,
        user_id=current_user.id,
        share_publicly=request.share_publicly,
        expires_in_hours=request.expires_in_hours
    )
    return result
```

**Step 5: Add Tests**

```python
# src/tests/unit/domain/services/test_agent_sharing_service.py

def test_share_token_expiration():
    service = AgentSharingService(repository)
    instance = create_test_instance()

    # Share with 24-hour expiration
    token = service.generate_share_token(instance, expires_in_hours=24)

    assert instance.share_expires_at is not None
    assert instance.share_expires_at > datetime.utcnow()

    # Simulate time passage
    instance.share_expires_at = datetime.utcnow() - timedelta(hours=1)
    assert instance.is_share_expired() is True
```

---

## Testing Strategy

### Test Hierarchy

```
tests/
├── unit/                      # Fast, isolated tests
│   ├── domain/
│   │   ├── entities/
│   │   └── services/
│   └── application/
├── integration/               # Multi-component tests
│   ├── agent_management/
│   └── api/
├── e2e/                       # End-to-end user flows
│   └── agent_management/
├── security/                  # Security vulnerability tests
│   └── agent_management/
└── performance/               # Load and stress tests
    └── agent_management/
```

### Running Tests

```bash
# Unit tests (fastest)
pytest src/tests/unit/

# Integration tests
pytest src/tests/integration/

# E2E tests
pytest src/tests/e2e/

# Security tests
pytest src/tests/security/

# Performance tests (K6)
cd src/tests/performance/agent_management
k6 run k6_call_agent_load_test.js

# All tests with coverage
pytest src/tests/ --cov=fastmcp.task_management --cov-report=html
```

### Test Coverage Goals

| Layer | Target Coverage |
|-------|----------------|
| Domain entities | 95%+ |
| Domain services | 90%+ |
| Application use cases | 85%+ |
| API endpoints | 85%+ |
| Overall | 85%+ |

---

## Deployment

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/agenthub
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret

# Agent Management Specific
AGENT_LIBRARY_PATH=/path/to/agent-library
MAX_SHARE_TOKEN_AGE_DAYS=365
ENABLE_PUBLIC_MARKETPLACE=true
```

### Deployment Checklist

**Pre-Deployment**:
- [ ] Run all tests (`pytest src/tests/`)
- [ ] Check security audit (`pytest src/tests/security/`)
- [ ] Verify migrations (`alembic upgrade head`)
- [ ] Populate agent templates (`python scripts/populate_agent_templates.py`)
- [ ] Review environment variables
- [ ] Check database backups

**Deployment**:
- [ ] Apply database migrations
- [ ] Restart application servers
- [ ] Verify health endpoints
- [ ] Monitor error logs
- [ ] Test critical user flows

**Post-Deployment**:
- [ ] Smoke test marketplace
- [ ] Verify agent instantiation
- [ ] Check import/share flows
- [ ] Monitor performance metrics
- [ ] Review user feedback

### Rollback Plan

```bash
# Rollback database
alembic downgrade -1

# Rollback application
git revert <commit-hash>
docker-compose up -d --force-recreate

# Verify
curl http://localhost:8000/health
```

---

## Performance Optimization

### Database Optimization

**Indexes**:
- Add indexes on frequently queried columns
- Use partial indexes for filtered queries
- Composite indexes for multi-column queries

```sql
-- Marketplace query optimization
CREATE INDEX idx_marketplace_agents
ON user_agent_instances(visibility, created_at DESC)
WHERE visibility = 'public';

-- User instance lookup
CREATE INDEX idx_user_instances
ON user_agent_instances(user_id, template_id);
```

**Query Optimization**:
```python
# Use eager loading to prevent N+1 queries
instances = session.query(UserAgentInstance)\
    .options(joinedload(UserAgentInstance.template))\
    .filter_by(user_id=user_id)\
    .all()
```

### Caching Strategy

**Redis Caching**:
```python
from redis import Redis

redis_client = Redis.from_url(os.getenv("REDIS_URL"))

def get_template(slug: str) -> AgentTemplate:
    # Check cache first
    cached = redis_client.get(f"template:{slug}")
    if cached:
        return AgentTemplate.from_dict(json.loads(cached))

    # Load from database
    template = repository.find_by_slug(slug)

    # Cache for 1 hour
    redis_client.setex(
        f"template:{slug}",
        3600,
        json.dumps(template.to_dict())
    )

    return template
```

**Cache Invalidation**:
- Template updates: Clear template cache
- Instance updates: Clear user instance cache
- Share/unshare: Clear marketplace cache

### Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/import")
@limiter.limit("10/minute")
async def import_agent(request: Request):
    # Rate limit: 10 imports per minute per IP
    ...
```

---

## Architecture Decisions

### Why Domain-Driven Design?

**Benefits**:
- Clear separation of concerns
- Business logic centralized in domain
- Easy to test and modify
- Scalable architecture

**Trade-offs**:
- More boilerplate code
- Steeper learning curve
- Overkill for simple CRUD

### Why Markdown for Configuration?

**Benefits**:
- User-friendly editing
- Version control friendly
- Supports rich formatting
- Easy to preview

**Trade-offs**:
- Requires markdown-to-JSON conversion
- Potential for parsing errors
- Storage overhead (dual format)

### Why Cryptographic Share Tokens?

**Benefits**:
- 128-bit entropy (practically unguessable)
- URL-safe characters
- No user information leakage
- Revocable

**Trade-offs**:
- Cannot reverse-engineer source from token
- Requires database lookup
- Storage requirement (32 chars per share)

---

## Contributing

### Code Style

**Python**:
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Docstrings for all public methods

**Example**:
```python
def generate_share_token(
    self,
    instance: UserAgentInstance,
    expires_in_hours: int | None = None
) -> str:
    """
    Generate cryptographically secure share token.

    Args:
        instance: Agent instance to share
        expires_in_hours: Optional expiration time

    Returns:
        32-character URL-safe token

    Raises:
        ValueError: If instance is not customized
    """
    if not instance.is_customized:
        raise ValueError("Cannot share non-customized agent")

    return secrets.token_urlsafe(24)
```

### Pull Request Guidelines

1. Create feature branch: `feature/agent-expiring-shares`
2. Write tests first (TDD)
3. Implement feature
4. Update documentation
5. Run full test suite
6. Submit PR with clear description
7. Address review feedback

---

## Resources

**Documentation**:
- [API Reference](./api-reference.md)
- [User Guide](./user-guide.md)
- [Security Audit](../../testing-qa/security-audit-agent-management.md)

**External Resources**:
- [Domain-Driven Design](https://martinfowler.com/tags/domain%20driven%20design.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

**Support**:
- GitHub: https://github.com/example/agenthub
- Discussions: https://github.com/example/agenthub/discussions
- Issues: https://github.com/example/agenthub/issues
