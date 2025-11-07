---
description: Architecture design for transforming static agent-library to dynamic per-user agent system with customization capabilities
date: 2025-11-01
status: design-proposal
---

# User-Specific Agent System Architecture

## Executive Summary

| Aspect | Description |
|--------|-------------|
| **Objective** | Transform agenthub from static shared agent-library → dynamic per-user agent system with full customization |
| **Current State** | All users share same agent definitions from `agent-library/` YAML files |
| **Target State** | Each user gets personalized agent instances created from templates, markdown-editable configurations |
| **Architecture** | DDD Phase 8 (Domain/Application/Infrastructure/Interface layers) |
| **Database** | PostgreSQL with 4 tables (templates, instances, markdown configs, usage logs) |
| **Key Features** | Template instantiation \| Markdown editing \| Auto-creation \| Version tracking \| User isolation |

---

## System Transformation

| System | Agent Access | Customization | Data Source | User Experience |
|--------|--------------|---------------|-------------|-----------------|
| **CURRENT** | All users → shared agent-library/*.yaml | ❌ None | YAML files (read-only) | Same config for everyone |
| **NEW** | User → personal agent instances | ✅ Full (markdown editor) | Database (per-user) | Customized agents, template inheritance |

**Flow**: agent-library (templates, read-only) → Agent Template Repository (loaded from YAML, stored in DB) → Instantiate per user → User A's/B's/C's Agent Instances (customized)

**Benefits**: Full customization \| Markdown-based editing \| Template inheritance \| Version tracking \| Usage analytics

---

## Agent-Library Structure (Source)

**YAML Configuration Files**:

| File | Properties Extracted | Purpose |
|------|---------------------|---------|
| **metadata.yaml** | name, description, model, color, migration | Agent metadata |
| **config.yaml** | author, category, version, capabilities.groups, execution_modes, compatibility | Configuration |
| **capabilities.yaml** | file_operations, command_execution, mcp_tools, collaboration | Permissions and tools |
| **contexts/*.yaml** | custom_instructions (complete system prompt with 10+ steps) | Main instructions |
| **rules/*.yaml** | error_handling, continuous_learning, health_check, clean_code_enforcement, implementation_methodology | Behavior rules |
| **output_format/*.yaml** | output_specification | Expected output formats |

**Total**: 6 YAML file types per agent → Consolidated into AgentTemplate entity

---

## Domain-Driven Design Architecture

### Domain Layer (`agent_management/domain/`)

| Entity | Identity | Key Properties | Methods | Notes |
|--------|----------|----------------|---------|-------|
| **AgentTemplate** (Immutable) | id: UUID, slug: str (unique) | name, category, description, version, color, model, default_configuration, metadata | `create_instance(user_id)`, `get_default_configuration()` | Represents default agent from agent-library |
| **UserAgentInstance** (Mutable) | id: UUID, user_id: UUID, template_id: UUID | agent_name, is_customized: bool, configuration, customizations: dict, last_used_at, usage_count | `update_instructions()`, `update_capabilities()`, `reset_to_default()`, `get_effective_configuration()` | User's personalized agent |
| **AgentConfiguration** (Value Object) | N/A (value object) | instructions, capabilities, rules, output_format, metadata | `to_markdown()`, `from_markdown()`, `to_json()`, `validate()` | Complete agent config |
| **AgentCapability** (Value Object) | N/A (value object) | file_operations, command_execution, allowed_commands: list, mcp_tools: list, agent_communication: bool | `validate_against_user_permissions(user)` | Permissions and tools |

**Value Objects**: AgentTemplateId (UUID) \| AgentInstanceId (UUID) \| UserId (UUID) \| AgentInstructions (content: str, max_length: 50K) \| AgentRules (error_handling, continuous_learning, health_check, clean_code_enforcement, implementation_methodology) \| AgentCategory (Enum: 12 types)

**Domain Services**:

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| **AgentInstantiationService** | Creates user instances from templates | `instantiate_from_template()`, `get_or_create_instance()` |
| **AgentCustomizationService** | Handles user modifications with validation | `apply_customization()`, `validate_customization()` |
| **AgentTemplateLoaderService** | Loads templates from YAML files | `load_all_templates()`, `load_template_by_slug()`, `refresh_template()` |

---

### Application Layer (`agent_management/application/`)

**Use Cases** (13 total):

| Category | Use Cases |
|----------|-----------|
| **Instance Management** | InstantiateAgentFromTemplate \| GetUserAgentInstance \| ListUserAgentInstances \| DeleteUserAgentInstance |
| **Customization** | CustomizeAgentConfiguration \| UpdateAgentInstructionsMarkdown \| UpdateAgentCapabilitiesMarkdown \| UpdateAgentRulesMarkdown \| UpdateAgentOutputFormatMarkdown |
| **Reset** | ResetAgentToDefault |
| **Execution** | LoadAgentForExecution |
| **Template Management** | ListAvailableTemplates \| GetTemplateDetails \| RefreshTemplatesFromLibrary |

**Application Services**: AgentInstanceApplicationService \| AgentCustomizationApplicationService \| AgentTemplateApplicationService

**Facade**: `AgentManagementFacade` - Unified interface for all agent operations

**Key Methods**: `get_or_create_agent_instance()` \| `customize_agent()` \| `get_agent_markdown()` \| `update_agent_markdown()` \| `reset_agent_to_default()` \| `list_user_agents()` \| `list_available_templates()`

---

### Infrastructure Layer (`agent_management/infrastructure/`)

**Repositories**:

| Repository | Purpose | Key Methods |
|------------|---------|-------------|
| **AgentTemplateRepository** | YAML + Database for templates | `find_by_slug()`, `find_all()`, `load_from_yaml()`, `sync_all_from_yaml()` |
| **UserAgentInstanceRepository** | SQLAlchemy for user instances | `find_by_id()`, `find_by_user_and_template()`, `find_all_by_user()`, `save()`, `delete()` |
| **AgentConfigurationMarkdownRepository** | Markdown config storage | `find_by_instance_and_type()`, `save_markdown()`, `get_all_for_instance()` |

**External Services**: YAMLAgentTemplateLoader (parse YAML files) \| MarkdownConverter (convert JSON ↔ markdown, validate syntax)

---

## Database Schema

### Table 1: agent_templates

```sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    default_configuration JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_agent_templates_slug ON agent_templates(slug);
CREATE INDEX idx_agent_templates_category ON agent_templates(category);
```

### Table 2: user_agent_instances

```sql
CREATE TABLE user_agent_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    template_id UUID NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    is_customized BOOLEAN DEFAULT FALSE,
    configuration JSONB NOT NULL,
    customizations JSONB DEFAULT '{}'::jsonb,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES agent_templates(id),
    UNIQUE(user_id, template_id)
);
CREATE INDEX idx_user_agent_instances_user_template ON user_agent_instances(user_id, template_id);
CREATE INDEX idx_customized_agents ON user_agent_instances(user_id) WHERE is_customized = true;
```

### Table 3: user_agent_configurations_md

```sql
CREATE TABLE user_agent_configurations_md (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id UUID NOT NULL,
    configuration_type VARCHAR(50) NOT NULL,  -- instructions, capabilities, rules, output_format
    content_markdown TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (instance_id) REFERENCES user_agent_instances(id) ON DELETE CASCADE,
    UNIQUE(instance_id, configuration_type)
);
CREATE INDEX idx_configurations_md_instance ON user_agent_configurations_md(instance_id, configuration_type);
```

### Table 4: agent_usage_logs (Optional)

```sql
CREATE TABLE agent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    instance_id UUID NOT NULL,
    agent_slug VARCHAR(255) NOT NULL,
    execution_context JSONB,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES user_agent_instances(id) ON DELETE SET NULL
);
CREATE INDEX idx_agent_usage_logs_user ON agent_usage_logs(user_id);
CREATE INDEX idx_agent_usage_logs_executed_at ON agent_usage_logs(executed_at);
```

---

## Agent Workflows

### First-Time Agent Call (Auto-Instantiation)

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | User | `call_agent("coding-agent")` | Request |
| 2 | Facade | `get_or_create_agent_instance(user_id, "coding-agent")` | Check instance |
| 3 | InstanceRepo | `find_by_user_and_template()` | None (not found) |
| 4 | TemplateRepo | `find_by_slug("coding-agent")` | AgentTemplate |
| 5 | InstantiationService | `instantiate_from_template(user_id, template)` | UserAgentInstance |
| 6 | InstanceRepo | `save(instance)` | Saved instance |
| 7 | Controller | Return agent config | system_prompt, tools, capabilities |

### Subsequent Agent Calls (Cached)

| Step | Actor | Action | Result |
|------|-------|--------|--------|
| 1 | User | `call_agent("coding-agent")` | Request |
| 2 | CacheLayer | `check_cache(user_id, "coding-agent")` | Cache hit/miss |
| 3a | **Cache Hit** | Return cached AgentInstanceDTO | Fast response (<100ms) |
| 3b | **Cache Miss** | `find_by_user_and_template()` → Return instance | Load from DB (<500ms) |
| 4 | Controller | Return configuration (may be customized) | Agent ready |

### Agent Customization Workflow

| Step | Actor | Action | Notes |
|------|-------|--------|-------|
| 1 | User | Open Agent Editor | Frontend |
| 2 | API | `GET /api/agents/instances/{id}/markdown/instructions` | Retrieve markdown |
| 3 | User | Edit markdown | In-browser editor |
| 4 | API | `PUT /api/agents/instances/{id}/markdown/instructions` | Save changes |
| 5 | CustomizationService | `validate_markdown(content)` | Security check |
| 6 | MarkdownRepo | `save_markdown(id, "instructions", content)` | Persist |
| 7 | InstanceRepo | `update_configuration(id, parsed_config)` \| `set_is_customized(true)` | Update DB |
| 8 | CacheLayer | `invalidate_cache(user_id, agent_slug)` | Clear cache |
| 9 | Frontend | Display success | Updated AgentInstanceDTO |

---

## Markdown Storage Format

**Configuration Types**: instructions \| capabilities \| rules \| output_format

### Example: Instructions Markdown

```markdown
# Agent Instructions: Coding Agent

## Core Purpose
Transform specifications into production-ready, well-tested code.

## Key Capabilities
- Multi-language: JavaScript/TypeScript, Python, Java, C#, Go, Rust, PHP, Ruby
- Frontend: React, Vue, Angular, Svelte, Next.js, Nuxt.js, SolidJS
- Backend: Node.js, Express, FastAPI, Spring, .NET, Flask, Django, Gin, Koa
- Databases: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, SQLite
- APIs: REST, GraphQL, gRPC, WebSockets
- Testing: Unit, integration, E2E test creation

## Implementation Process
1. **Specification Analysis**: Understand requirements
2. **Architecture Planning**: Design code structure
3-10. [Additional steps]

## Edge Cases & Fallback Strategies
- Incomplete spec → Request clarification and pause
- Missing dependency → Use stubs/mocks and document gap

## Quality Standards
- Code coverage ≥90% for critical paths
- All public APIs documented
```

### Example: Capabilities Markdown

```markdown
# Agent Capabilities

## File Operations
- Read: ✅ | Write: ✅ | Create: ✅ | Delete: ✅

## Command Execution
- Enabled: ✅
- Restrictions: sandbox_mode
- Allowed: git, npm, yarn, pnpm, python, node, docker, make, cargo, pytest, jest, mvn, gradle

## MCP Tools
- mcp__ide__getDiagnostics
- mcp__ide__executeCode
- mcp__agenthub_http__manage_task
- mcp__sequential-thinking__sequentialthinking

## Collaboration
- Agent Communication: ✅ | Collaborative Mode: ✅
```

---

## Interface Layer

### Modified call_agent Controller

**Before** (Current):
```python
@mcp_tool
def call_agent(agent_slug: str) -> dict:
    agent_config = load_yaml(f"agent-library/agents/{agent_slug}/")
    return {"system_prompt": agent_config["instructions"], ...}
```

**After** (New):
```python
@mcp_tool
def call_agent(agent_slug: str, user_id: str) -> dict:
    instance = agent_management_facade.get_or_create_agent_instance(user_id, agent_slug)
    instance_repository.update_last_used(instance.id)
    return {
        "system_prompt": instance.configuration.instructions.content,
        "tools": instance.configuration.capabilities.mcp_tools,
        "is_customized": instance.is_customized,
        ...
    }
```

### MCP Controllers

| Controller | Tools | Purpose |
|------------|-------|---------|
| **AgentInstanceMCPController** | `manage_agent_instance(action, user_id, instance_id, agent_slug)` | Actions: create, get, list, delete, reset |
| **AgentMarkdownMCPController** | `get_agent_markdown(user_id, instance_id, type)`, `update_agent_markdown(...)` | Retrieve/save markdown for editing |

### REST API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| **Templates** | GET `/api/agents/templates` | List all available templates |
| | GET `/api/agents/templates/{slug}` | Get template details |
| **Instances** | GET `/api/agents/instances` | List user's agent instances |
| | POST `/api/agents/instances` | Create instance from template |
| | GET `/api/agents/instances/{id}` | Get instance details |
| | PUT `/api/agents/instances/{id}` | Update instance config |
| | DELETE `/api/agents/instances/{id}` | Delete instance |
| | POST `/api/agents/instances/{id}/reset` | Reset to default |
| **Markdown** | GET `/api/agents/instances/{id}/markdown/{type}` | Get markdown |
| | PUT `/api/agents/instances/{id}/markdown/{type}` | Update markdown |
| | POST `/api/agents/instances/{id}/preview` | Preview changes |
| **Usage** | GET `/api/agents/usage` | User's agent usage statistics |

---

## Frontend Integration

**React Components**:

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **AgentLibrary** | Browse available templates | Grid view, template cards, select to instantiate |
| **AgentInstanceList** | User's customized agents | List view, edit/reset actions, usage stats |
| **AgentEditor** | Markdown editor with tabs | 4 tabs (instructions, capabilities, rules, output_format), save/preview |
| **AgentPreview** | Preview configuration | Render markdown before saving |

**Example**: AgentEditor with tabs → MarkdownEditor component → Save → API PUT → Update instance

---

## Migration Strategy

| Phase | Objective | Implementation | Timeline |
|-------|-----------|----------------|----------|
| **1. Backward Compatibility** | Add new infra without breaking existing | Create DB tables, domain entities, repositories \| Keep call_agent with YAML | 1-2 weeks |
| **2. Template Population** | Populate agent_templates from agent-library | AgentTemplateLoaderService \| Migration script to scan YAML \| Insert 60+ agents | 1 week |
| **3. Instance Layer** | Implement auto-instantiation | Modify call_agent to check instances first \| Auto-create from template \| Transparent to users | 2 weeks |
| **4. Customization** | Enable user customization through UI | Markdown storage \| REST API endpoints \| Frontend agent editor \| Save/reset | 3-4 weeks |
| **5. Template Sync** | Handle template updates | Track template version \| Notify users of updates \| Diff view \| Selective merge | 2-3 weeks |

**Template Population Script Example**:
```python
async def populate_agent_templates():
    loader = YAMLAgentTemplateLoader()
    template_repo = AgentTemplateRepository()
    agent_slugs = loader.scan_available_agents()

    for slug in agent_slugs:
        config = loader.load_agent_configuration(slug)
        template = AgentTemplate(slug=slug, name=config['name'], category=config['category'],
            description=config['description'], version=config['version'],
            default_configuration=config, metadata=config.get('metadata', {}))
        template_repo.save(template)

    print(f"🎉 Loaded {len(agent_slugs)} agent templates")
```

---

## Security Considerations

| Concern | Implementation | Enforcement |
|---------|----------------|-------------|
| **1. User Isolation** (CRITICAL) | Always filter by user_id in queries \| Row-level security in PostgreSQL | `POLICY user_agent_instances_isolation USING (user_id = current_user_id)` |
| **2. Capability Restrictions** | Validate all capability changes | Check file_delete permission \| Whitelist commands \| Verify MCP tool authorization |
| **3. Markdown Injection** | Sanitize and validate | `bleach.clean()` with allowed tags only \| Escape special characters |
| **4. Resource Limits** | Hard limits per user | MAX_INSTANCES: 100 \| MAX_MARKDOWN_SIZE: 50KB \| RATE_LIMIT_AGENT_CALLS: 100/hr \| RATE_LIMIT_CUSTOMIZATIONS: 20/hr |
| **5. Audit Trail** | Log all customizations | Timestamp, user_id, instance_id, action, changes, ip_address |

**Validation Example**:
```python
def validate_capability_customization(user: User, new_capabilities: AgentCapability) -> ValidationResult:
    if new_capabilities.file_operations.delete and not user.has_permission('file_delete'):
        return ValidationResult.error("User not authorized for file deletion")
    for cmd in new_capabilities.allowed_commands:
        if cmd not in ALLOWED_COMMAND_WHITELIST:
            return ValidationResult.error(f"Command '{cmd}' not in whitelist")
    return ValidationResult.success()
```

---

## Performance Optimization

| Strategy | Implementation | Impact |
|----------|----------------|--------|
| **1. Caching** | Redis cache for agent instances (1 hour TTL) | <100ms response for cached instances |
| **2. Database Indexing** | idx_user_agent_instances_user_template \| idx_customized_agents (partial) | Fast queries |
| **3. Lazy Loading** | Create instances on-demand (first call), not at signup | Zero initial overhead |
| **4. Batch Template Loading** | Load all templates into memory at startup (AgentTemplateRegistry) | Fast template lookups |

**Cache Implementation**:
```python
class AgentInstanceCache:
    def get_or_load(self, user_id: UserId, agent_slug: str) -> UserAgentInstance:
        cache_key = f"agent_instance:{user_id}:{agent_slug}"
        cached = redis.get(cache_key)
        if cached:
            return UserAgentInstance.from_json(cached)
        instance = instance_repo.find_by_user_and_template(user_id, agent_slug)
        redis.setex(cache_key, 3600, instance.to_json())
        return instance
```

---

## Implementation Roadmap

| Milestone | Timeline | Deliverables |
|-----------|----------|--------------|
| **1. Foundation** | Weeks 1-2 | Database schema \| Domain entities \| Value objects \| Domain services \| Unit tests |
| **2. Infrastructure** | Weeks 3-4 | Repositories \| YAMLAgentTemplateLoader \| MarkdownConverter \| Template population script \| Populate agent_templates |
| **3. Application Layer** | Weeks 5-6 | Use cases \| Application services \| AgentManagementFacade \| Validation \| Integration tests |
| **4. Interface Layer** | Weeks 7-8 | Modified call_agent \| MCP controllers \| REST API endpoints \| Auth/authz |
| **5. Frontend** | Weeks 9-11 | AgentLibrary \| AgentInstanceList \| AgentEditor \| AgentPreview \| Save/reset |
| **6. Testing & Deployment** | Weeks 12-13 | E2E testing \| Performance testing \| Security audit \| Documentation \| Gradual rollout |

---

## Success Metrics

| Category | Metrics |
|----------|---------|
| **Technical** | All 60+ templates loaded \| <100ms cached response \| <500ms first instantiation \| Zero security vulnerabilities \| 99.9% uptime |
| **Business** | % users customizing ≥1 agent \| Avg customized agents per user \| User satisfaction ≥4.5/5 \| Reduced support requests \| Increased agent usage |
| **User Experience** | Time to first customization <5 min \| Markdown save <2 sec \| Reset success rate 100% |

---

## Conclusion

This architecture transforms agenthub from static shared agent-library → dynamic user-specific system with full customization while:

1. **Maintaining Backward Compatibility** - Existing functionality continues
2. **Following DDD Principles** - Clean architecture with proper separation
3. **Ensuring Security** - User isolation, capability validation, audit trails
4. **Optimizing Performance** - Caching, lazy loading, efficient indexing
5. **Enabling Customization** - Markdown-based editing with frontend integration
6. **Supporting Evolution** - Template versioning and migration strategies

**Key Benefits**: Each user creates personalized agent instances from templates → Customize via markdown editor → Maintain customizations while templates evolve

**Next Steps**: Team review → Gather feedback → Proceed with implementation roadmap
