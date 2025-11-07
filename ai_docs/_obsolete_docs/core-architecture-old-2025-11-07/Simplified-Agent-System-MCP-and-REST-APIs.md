---
description: Simplified Agent System - MCP for Execution, REST APIs for Management
date: 2025-11-01
status: design-proposal-simplified
principle: Separation of Concerns - MCP for agents, REST for users
---

# Simplified Agent System Architecture

## Core Principle: Clear Separation

```
┌─────────────────────────────────────────────────────────┐
│                    MCP LAYER                            │
│                (Agent Execution)                        │
│                                                         │
│  ✅ call_agent(agent_slug, user_id)                    │
│     - Load user's agent instance                       │
│     - Return system prompt + config                    │
│     - Auto-instantiate if needed                       │
│                                                         │
│  ❌ NO agent management tools                          │
│  ❌ NO customization tools                             │
│  ❌ NO sharing tools                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   REST API LAYER                        │
│              (User Management UI)                       │
│                                                         │
│  Agent Management:                                      │
│  - GET    /api/agents/instances                        │
│  - GET    /api/agents/instances/{id}                   │
│  - DELETE /api/agents/instances/{id}                   │
│                                                         │
│  Agent Customization:                                   │
│  - GET    /api/agents/instances/{id}/config            │
│  - PUT    /api/agents/instances/{id}/config            │
│  - POST   /api/agents/instances/{id}/reset             │
│                                                         │
│  Agent Sharing:                                         │
│  - POST   /api/agents/instances/{id}/share             │
│  - DELETE /api/agents/instances/{id}/share             │
│  - GET    /api/agents/shared/{token}                   │
│  - POST   /api/agents/import/{token}                   │
│                                                         │
│  Marketplace:                                           │
│  - GET    /api/agents/marketplace                      │
│  - GET    /api/agents/shared/my                        │
└─────────────────────────────────────────────────────────┘
```

---

## MCP Layer - MINIMAL

### Only One MCP Tool: call_agent

```python
# agenthub_main/src/fastmcp/agent_management/interface/mcp_tools.py

from fastmcp import mcp_tool
from ..application.facades import AgentManagementFacade

@mcp_tool
def call_agent(agent_slug: str, user_id: str) -> dict:
    """
    Load agent configuration for execution

    This is the ONLY MCP tool for agents.
    Everything else is REST API.

    Args:
        agent_slug: Agent identifier (e.g., "coding-agent")
        user_id: User identifier

    Returns:
        Agent configuration with system prompt, tools, capabilities

    Behavior:
        - First call: Auto-creates user instance from template
        - Subsequent calls: Returns user's customized configuration
        - Always returns latest configuration
    """
    facade = AgentManagementFacade()

    # Get or create instance (transparent)
    instance = facade.get_or_create_agent_instance(
        user_id=user_id,
        agent_slug=agent_slug
    )

    # Update usage tracking
    facade.track_agent_usage(instance.id)

    # Return configuration for agent execution
    return {
        "success": True,
        "agent": {
            "name": instance.agent_name,
            "slug": agent_slug,
            "description": instance.template.description,
            "category": instance.template.category,

            # System prompt (main instructions)
            "system_prompt": instance.configuration.instructions.content,

            # Tools available to agent
            "tools": instance.configuration.capabilities.mcp_tools,

            # Capabilities
            "file_operations": instance.configuration.capabilities.file_operations.to_dict(),
            "command_execution": instance.configuration.capabilities.command_execution.to_dict(),
            "allowed_commands": instance.configuration.capabilities.allowed_commands,

            # Metadata
            "is_customized": instance.is_customized,
            "created_by": instance.get_creator_display_name()
        },
        "source": "user-instance" if instance.is_customized else "template"
    }


# Register MCP tool
def register_mcp_tools(server):
    """Register MCP tools - ONLY call_agent"""
    server.register_tool(call_agent)
```

**That's it! No other MCP tools needed.**

---

## REST API Layer - COMPLETE USER MANAGEMENT

### 1. Agent Instance Management

```python
# agenthub_main/src/api/routes/agents.py

from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_current_user
from ..schemas import AgentInstanceResponse, AgentListResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/instances", response_model=AgentListResponse)
async def list_user_agents(
    user = Depends(get_current_user)
):
    """
    List all agent instances for current user

    Returns instances with:
    - Default agents (not customized)
    - Customized agents
    - Imported agents (with creator attribution)
    """
    facade = AgentManagementFacade()
    instances = facade.list_user_agents(user.id)

    return {
        "agents": [
            {
                "id": str(inst.id),
                "name": inst.agent_name,
                "slug": inst.template.slug,
                "category": inst.template.category,
                "is_customized": inst.is_customized,
                "is_imported": inst.is_imported,
                "created_by": inst.get_creator_display_name(),
                "last_used_at": inst.last_used_at,
                "usage_count": inst.usage_count
            }
            for inst in instances
        ],
        "total": len(instances)
    }


@router.get("/instances/{instance_id}", response_model=AgentInstanceResponse)
async def get_agent_instance(
    instance_id: str,
    user = Depends(get_current_user)
):
    """Get detailed agent instance information"""
    facade = AgentManagementFacade()
    instance = facade.get_agent_instance(user.id, instance_id)

    if not instance:
        raise HTTPException(404, "Agent instance not found")

    return {
        "id": str(instance.id),
        "name": instance.agent_name,
        "slug": instance.template.slug,
        "category": instance.template.category,
        "is_customized": instance.is_customized,
        "is_imported": instance.is_imported,
        "created_by": instance.get_creator_display_name(),
        "configuration": instance.configuration.to_dict(),
        "last_used_at": instance.last_used_at,
        "usage_count": instance.usage_count,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at
    }


@router.delete("/instances/{instance_id}")
async def delete_agent_instance(
    instance_id: str,
    user = Depends(get_current_user)
):
    """
    Delete agent instance

    Note: Next call_agent will recreate default instance
    """
    facade = AgentManagementFacade()
    facade.delete_agent_instance(user.id, instance_id)

    return {"success": True, "message": "Agent instance deleted"}
```

### 2. Agent Customization

```python
@router.get("/instances/{instance_id}/config")
async def get_agent_configuration(
    instance_id: str,
    user = Depends(get_current_user)
):
    """
    Get agent configuration for editing

    Returns markdown content for each section:
    - instructions
    - capabilities
    - rules
    - output_format
    """
    facade = AgentManagementFacade()
    config = facade.get_agent_configuration_markdown(user.id, instance_id)

    return {
        "instance_id": instance_id,
        "configuration": {
            "instructions": {
                "markdown": config["instructions"],
                "last_updated": config["instructions_updated_at"]
            },
            "capabilities": {
                "markdown": config["capabilities"],
                "last_updated": config["capabilities_updated_at"]
            },
            "rules": {
                "markdown": config["rules"],
                "last_updated": config["rules_updated_at"]
            },
            "output_format": {
                "markdown": config["output_format"],
                "last_updated": config["output_format_updated_at"]
            }
        }
    }


@router.put("/instances/{instance_id}/config")
async def update_agent_configuration(
    instance_id: str,
    config: AgentConfigurationUpdate,
    user = Depends(get_current_user)
):
    """
    Update agent configuration

    Request body:
    {
        "instructions": "markdown content",
        "capabilities": "markdown content",
        "rules": "markdown content",
        "output_format": "markdown content"
    }

    Validates markdown and updates configuration
    """
    facade = AgentManagementFacade()

    # Update configuration
    updated_instance = facade.update_agent_configuration(
        user_id=user.id,
        instance_id=instance_id,
        instructions_md=config.instructions,
        capabilities_md=config.capabilities,
        rules_md=config.rules,
        output_format_md=config.output_format
    )

    return {
        "success": True,
        "instance": {
            "id": str(updated_instance.id),
            "name": updated_instance.agent_name,
            "is_customized": True,
            "updated_at": updated_instance.updated_at
        }
    }


@router.post("/instances/{instance_id}/reset")
async def reset_agent_to_default(
    instance_id: str,
    user = Depends(get_current_user)
):
    """
    Reset agent to default template configuration

    Removes all customizations
    """
    facade = AgentManagementFacade()
    reset_instance = facade.reset_agent_to_default(user.id, instance_id)

    return {
        "success": True,
        "message": "Agent reset to default configuration",
        "instance": {
            "id": str(reset_instance.id),
            "name": reset_instance.agent_name,
            "is_customized": False
        }
    }
```

### 3. Agent Sharing

```python
@router.post("/instances/{instance_id}/share")
async def share_agent(
    instance_id: str,
    user = Depends(get_current_user)
):
    """
    Make agent publicly shareable

    Generates share token and returns shareable link
    """
    facade = AgentManagementFacade()

    share_result = facade.share_agent(
        user_id=user.id,
        instance_id=instance_id,
        base_url=request.base_url
    )

    return {
        "success": True,
        "share_token": share_result.share_token,
        "shareable_link": share_result.shareable_link,
        "agent_name": share_result.agent_name
    }


@router.delete("/instances/{instance_id}/share")
async def revoke_agent_sharing(
    instance_id: str,
    user = Depends(get_current_user)
):
    """
    Revoke agent sharing (make private)
    """
    facade = AgentManagementFacade()
    facade.revoke_agent_sharing(user.id, instance_id)

    return {
        "success": True,
        "message": "Agent sharing revoked"
    }


@router.get("/shared/{share_token}")
async def get_shared_agent_preview(share_token: str):
    """
    Get shared agent details for preview

    No authentication required (public link)
    """
    facade = AgentManagementFacade()

    agent_details = facade.get_shared_agent_details(share_token)

    if not agent_details:
        raise HTTPException(404, "Shared agent not found or no longer public")

    return {
        "agent_name": agent_details.agent_name,
        "template_slug": agent_details.template_slug,
        "template_category": agent_details.template_category,
        "description": agent_details.description,
        "creator_name": agent_details.creator_name,
        "share_count": agent_details.share_count,
        "import_count": agent_details.import_count,
        "is_customized": agent_details.is_customized,
        "configuration_preview": agent_details.configuration_preview
    }


@router.post("/import/{share_token}")
async def import_shared_agent(
    share_token: str,
    user = Depends(get_current_user)
):
    """
    Import shared agent into user's workspace

    Handles name collision automatically by appending creator name
    """
    facade = AgentManagementFacade()

    import_result = facade.import_agent(
        importer_user_id=user.id,
        share_token=share_token
    )

    return {
        "success": True,
        "imported_instance": {
            "id": str(import_result.imported_instance.id),
            "name": import_result.imported_instance.agent_name,
            "slug": import_result.imported_instance.template.slug,
            "created_by": import_result.creator_name,
            "was_renamed": import_result.was_renamed
        },
        "message": "Agent imported successfully" + (
            f". Renamed to avoid collision." if import_result.was_renamed else ""
        )
    }
```

### 4. Agent Marketplace

```python
@router.get("/marketplace")
async def browse_agent_marketplace(
    category: Optional[str] = None,
    sort: str = "popular",
    page: int = 1,
    page_size: int = 20
):
    """
    Browse public shared agents (marketplace)

    Query params:
    - category: Filter by category (development, testing, etc.)
    - sort: popular (by import_count) or recent (by created_at)
    - page: Page number
    - page_size: Results per page
    """
    facade = AgentManagementFacade()

    marketplace_result = facade.browse_marketplace(
        category=category,
        sort_by=sort,
        page=page,
        page_size=page_size
    )

    return {
        "agents": [
            {
                "instance_id": str(agent.instance_id),
                "agent_name": agent.agent_name,
                "template_slug": agent.template_slug,
                "template_category": agent.template_category,
                "description_preview": agent.description_preview,
                "creator_name": agent.creator_name,
                "import_count": agent.import_count,
                "share_token": agent.share_token,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
            for agent in marketplace_result.agents
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": marketplace_result.total,
            "total_pages": (marketplace_result.total + page_size - 1) // page_size
        }
    }


@router.get("/shared/my")
async def get_my_shared_agents(
    user = Depends(get_current_user)
):
    """
    Get user's shared agents with statistics
    """
    facade = AgentManagementFacade()

    shared_agents = facade.get_user_shared_agents(user.id)

    return {
        "shared_agents": [
            {
                "instance_id": str(agent.id),
                "agent_name": agent.agent_name,
                "share_token": agent.share_token,
                "shareable_link": f"{request.base_url}/agents/import/{agent.share_token}",
                "import_count": agent.import_count,
                "share_count": agent.share_count,
                "created_at": agent.created_at,
                "updated_at": agent.updated_at
            }
            for agent in shared_agents
        ],
        "total": len(shared_agents)
    }
```

### 5. Agent Templates (Browse Available)

```python
@router.get("/templates")
async def list_agent_templates(
    category: Optional[str] = None
):
    """
    List all available agent templates

    These are the base templates from agent-library
    Users can create instances from these
    """
    facade = AgentManagementFacade()

    templates = facade.list_agent_templates(category=category)

    return {
        "templates": [
            {
                "id": str(template.id),
                "slug": template.slug,
                "name": template.name,
                "category": template.category,
                "description": template.description,
                "version": template.version,
                "color": template.metadata.get("color"),
                "model": template.metadata.get("model")
            }
            for template in templates
        ],
        "total": len(templates)
    }


@router.get("/templates/{slug}")
async def get_agent_template_details(slug: str):
    """
    Get detailed template information

    Shows default configuration that will be used for new instances
    """
    facade = AgentManagementFacade()

    template = facade.get_agent_template(slug)

    if not template:
        raise HTTPException(404, "Template not found")

    return {
        "id": str(template.id),
        "slug": template.slug,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "version": template.version,
        "default_configuration": template.default_configuration,
        "metadata": template.metadata
    }
```

---

## Frontend Integration

### Simple User Flow

```typescript
// 1. User calls an agent (via MCP) - Transparent instantiation
const callAgent = async (agentSlug: string) => {
  // MCP call - auto-creates instance if needed
  const result = await mcp.call('call_agent', {
    agent_slug: agentSlug,
    user_id: currentUser.id
  });

  // Execute agent with returned configuration
  executeAgent(result.agent);
};

// 2. User wants to customize agent - Use REST API
const customizeAgent = async (instanceId: string) => {
  // Fetch current configuration
  const config = await fetch(`/api/agents/instances/${instanceId}/config`);

  // Show editor
  openAgentEditor(config);
};

// 3. User saves customization - Use REST API
const saveCustomization = async (instanceId: string, newConfig: Config) => {
  await fetch(`/api/agents/instances/${instanceId}/config`, {
    method: 'PUT',
    body: JSON.stringify(newConfig)
  });

  // Next call_agent will use customized version
};

// 4. User shares agent - Use REST API
const shareAgent = async (instanceId: string) => {
  const result = await fetch(`/api/agents/instances/${instanceId}/share`, {
    method: 'POST'
  });

  // Show shareable link
  showShareModal(result.shareable_link);
};

// 5. User imports agent - Use REST API
const importAgent = async (shareToken: string) => {
  // Preview first
  const preview = await fetch(`/api/agents/shared/${shareToken}`);
  showImportModal(preview);

  // Import
  const result = await fetch(`/api/agents/import/${shareToken}`, {
    method: 'POST'
  });

  // Agent now available for use
};
```

---

## Architecture Benefits

### 1. Clear Separation of Concerns

```
MCP Layer:
  - ONLY for agent execution
  - Minimal API surface (1 tool)
  - High performance, cached
  - Transparent to users

REST API Layer:
  - ONLY for user management
  - Full CRUD operations
  - Rich UI interactions
  - Clear HTTP semantics
```

### 2. Security Boundaries

```
MCP:
  - Requires authentication (user_id)
  - Returns agent config for execution
  - No modification operations

REST API:
  - Full authentication/authorization
  - User isolation enforced
  - Rate limiting per endpoint
  - Input validation per route
```

### 3. Scalability

```
MCP:
  - Simple caching strategy
  - Fast lookups (< 100ms)
  - Minimal database queries

REST API:
  - Standard HTTP caching
  - Pagination for lists
  - Async operations where needed
  - Independent scaling
```

### 4. Development Simplicity

```
MCP:
  - 1 file, 1 function
  - Easy to test
  - Minimal dependencies

REST API:
  - Standard FastAPI patterns
  - OpenAPI documentation automatic
  - Easy to extend
  - Familiar to developers
```

---

## Complete API Reference

### MCP Tools (1 tool)

```
call_agent(agent_slug: str, user_id: str) -> dict
  - Load agent configuration for execution
```

### REST API Endpoints (15 endpoints)

```
# Instance Management (3)
GET    /api/agents/instances                 # List user's agents
GET    /api/agents/instances/{id}            # Get agent details
DELETE /api/agents/instances/{id}            # Delete agent

# Customization (3)
GET    /api/agents/instances/{id}/config     # Get config for editing
PUT    /api/agents/instances/{id}/config     # Save customization
POST   /api/agents/instances/{id}/reset      # Reset to default

# Sharing (4)
POST   /api/agents/instances/{id}/share      # Share agent
DELETE /api/agents/instances/{id}/share      # Revoke sharing
GET    /api/agents/shared/{token}            # Preview shared agent
POST   /api/agents/import/{token}            # Import agent

# Marketplace (3)
GET    /api/agents/marketplace                # Browse public agents
GET    /api/agents/shared/my                  # My shared agents
GET    /api/agents/templates                  # List templates

# Templates (2)
GET    /api/agents/templates                  # List all templates
GET    /api/agents/templates/{slug}           # Template details
```

---

## File Structure

```
agenthub_main/
└── src/
    ├── fastmcp/
    │   └── agent_management/
    │       ├── domain/              # Entities, value objects, services
    │       ├── application/         # Use cases, facades
    │       ├── infrastructure/      # Repositories, external services
    │       └── interface/
    │           └── mcp_tools.py     # ONLY call_agent
    │
    └── api/
        └── routes/
            └── agents.py            # ALL REST endpoints

agenthub-frontend/
└── src/
    ├── services/
    │   ├── mcp.ts                  # MCP client (call_agent)
    │   └── agentAPI.ts             # REST API client (all management)
    ├── components/
    │   ├── AgentList/
    │   ├── AgentEditor/
    │   ├── AgentMarketplace/
    │   └── ShareImportModals/
    └── pages/
        ├── MyAgents.tsx
        ├── AgentEditor.tsx
        └── Marketplace.tsx
```

---

## Implementation Checklist

### Backend

- [ ] **MCP Layer (Minimal)**
  - [ ] Implement `call_agent` function
  - [ ] Register MCP tool
  - [ ] Add caching layer
  - [ ] Test auto-instantiation

- [ ] **REST API Layer (Complete)**
  - [ ] Instance management endpoints (3)
  - [ ] Customization endpoints (3)
  - [ ] Sharing endpoints (4)
  - [ ] Marketplace endpoints (3)
  - [ ] Template endpoints (2)
  - [ ] Authentication middleware
  - [ ] Rate limiting
  - [ ] Input validation

### Frontend

- [ ] **MCP Integration**
  - [ ] MCP client for call_agent
  - [ ] Agent execution logic

- [ ] **REST API Integration**
  - [ ] API client service
  - [ ] Agent list component
  - [ ] Agent editor component
  - [ ] Share/Import modals
  - [ ] Marketplace component

---

## Summary

**MCP = Execution Only (1 tool)**
- `call_agent` - Load agent configuration

**REST API = Everything Else (15 endpoints)**
- Instance management
- Customization
- Sharing
- Importing
- Marketplace
- Templates

This creates a clean separation where:
- Agents use MCP (simple, fast, cached)
- Users use REST API (rich, flexible, full-featured)
- No overlap, no confusion
- Easy to maintain and extend

**Next Steps**: Implement `call_agent` MCP tool and REST API endpoints according to this simplified architecture.
