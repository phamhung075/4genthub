# Agent Management API Reference

**Version**: 2.0.0
**Base Path**: `/api/v2/agent-management`
**Authentication**: Required (JWT Bearer Token)

## Overview

The Agent Management API provides endpoints for managing user-specific AI agent instances, including customization, sharing, and importing. All endpoints require authentication except public marketplace previews.

**Key Features**:
- User-specific agent instances with customization
- Markdown-based configuration editing
- Secure sharing with cryptographic tokens
- Agent marketplace for discovery and import
- Name collision handling with creator attribution

---

## Authentication

All endpoints (except marketplace preview) require JWT authentication:

```http
Authorization: Bearer <your-jwt-token>
```

---

## Endpoints

### 1. List User's Agent Instances

List all agent instances owned by the authenticated user.

**Endpoint**: `GET /instances`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by agent category |
| `limit` | integer | No | Results per page (default: 50, max: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response**: `200 OK`

```json
{
  "instances": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "template_slug": "coding-agent",
      "custom_name": "My Python Expert",
      "is_customized": true,
      "visibility": "private",
      "created_by": "user@example.com",
      "created_at": "2025-11-01T12:00:00Z",
      "updated_at": "2025-11-01T14:30:00Z",
      "category": "development"
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/instances?category=development&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 2. Get Agent Instance Details

Retrieve complete configuration for a single agent instance, including markdown content for editing.

**Endpoint**: `GET /instances/{instance_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "template_slug": "coding-agent",
  "custom_name": "My Python Expert",
  "custom_description": "Specialized Python developer with Django expertise",
  "is_customized": true,
  "visibility": "private",
  "configuration": {
    "instructions": "You are a Python expert specializing in Django...",
    "rules": ["Follow PEP 8", "Write comprehensive docstrings"],
    "capabilities": ["Python 3.11+", "Django 4.2+", "pytest"],
    "output_format": "markdown"
  },
  "markdown_content": {
    "instructions": "# Python Expert\n\nYou are specialized in...",
    "rules": "## Code Standards\n\n- Follow PEP 8...",
    "capabilities": "## Technical Stack\n\n- Python 3.11+...",
    "output_format": "## Output Format\n\nMarkdown with code blocks..."
  },
  "created_by": "user@example.com",
  "created_at": "2025-11-01T12:00:00Z",
  "updated_at": "2025-11-01T14:30:00Z"
}
```

**Errors**:
- `404 Not Found`: Instance not found
- `403 Forbidden`: Not authorized to access this instance

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 3. Update Agent Configuration

Update agent configuration using markdown content. Automatically converts markdown to structured JSON.

**Endpoint**: `PUT /instances/{instance_id}/configuration`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Request Body**:

```json
{
  "custom_name": "My Python Expert",
  "custom_description": "Specialized Python developer",
  "instructions_markdown": "# Python Expert\n\nYou specialize in Django...",
  "rules_markdown": "## Code Standards\n\n- Follow PEP 8\n- Write tests",
  "capabilities_markdown": "## Stack\n\n- Python 3.11+\n- Django 4.2+",
  "output_format_markdown": "## Format\n\nMarkdown with syntax highlighting"
}
```

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "custom_name": "My Python Expert",
  "is_customized": true,
  "configuration": {
    "instructions": "You specialize in Django...",
    "rules": ["Follow PEP 8", "Write tests"],
    "capabilities": ["Python 3.11+", "Django 4.2+"],
    "output_format": "markdown"
  },
  "updated_at": "2025-11-01T15:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: Invalid markdown or missing required fields
- `403 Forbidden`: Not authorized to update this instance
- `404 Not Found`: Instance not found

**Example**:

```bash
curl -X PUT "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000/configuration" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custom_name": "My Python Expert",
    "instructions_markdown": "# Python Expert\n\nSpecialize in Django development..."
  }'
```

---

### 4. Reset Agent to Template Defaults

Restore agent to original template configuration, clearing all customizations.

**Endpoint**: `POST /instances/{instance_id}/reset`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "template_slug": "coding-agent",
  "custom_name": "Coding Agent",
  "is_customized": false,
  "configuration": {
    "instructions": "Original template instructions...",
    "rules": ["Original template rules..."],
    "capabilities": ["Original capabilities..."],
    "output_format": "markdown"
  },
  "reset_at": "2025-11-01T16:00:00Z"
}
```

**Errors**:
- `403 Forbidden`: Not authorized to reset this instance
- `404 Not Found`: Instance not found

**Example**:

```bash
curl -X POST "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000/reset" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 5. Delete Agent Instance

Soft delete a user's agent instance.

**Endpoint**: `DELETE /instances/{instance_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Response**: `204 No Content`

**Errors**:
- `403 Forbidden`: Not authorized to delete this instance
- `404 Not Found`: Instance not found
- `409 Conflict`: Instance is currently in use

**Example**:

```bash
curl -X DELETE "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 6. Share Agent (Generate Share Token)

Generate a secure share token for public agent sharing. Creates a shareable URL.

**Endpoint**: `POST /instances/{instance_id}/share`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Request Body**:

```json
{
  "share_publicly": true
}
```

**Response**: `200 OK`

```json
{
  "share_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "share_url": "https://example.com/marketplace/agents/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "visibility": "public",
  "shared_at": "2025-11-01T17:00:00Z"
}
```

**Notes**:
- Share tokens are cryptographically secure (32 characters, 128-bit entropy)
- Only the owner can share an agent
- Sharing sets visibility to `public`

**Errors**:
- `403 Forbidden`: Not authorized to share this instance
- `404 Not Found`: Instance not found

**Example**:

```bash
curl -X POST "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"share_publicly": true}'
```

---

### 7. Unshare Agent (Revoke Share Token)

Revoke share token and make agent private. Existing imports remain unaffected.

**Endpoint**: `POST /instances/{instance_id}/unshare`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instance_id` | UUID | Yes | Agent instance identifier |

**Response**: `200 OK`

```json
{
  "visibility": "private",
  "share_token": null,
  "unshared_at": "2025-11-01T18:00:00Z"
}
```

**Notes**:
- Only the owner can unshare
- Revokes access to future imports
- Existing imports (copies) remain intact

**Errors**:
- `403 Forbidden`: Not authorized to unshare this instance
- `404 Not Found`: Instance not found

**Example**:

```bash
curl -X POST "https://api.example.com/api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000/unshare" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 8. Import Shared Agent

Import a shared agent using its share token. Creates a copy in the importing user's account.

**Endpoint**: `POST /import`

**Request Body**:

```json
{
  "share_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "custom_name": "Imported Python Expert"
}
```

**Response**: `201 Created`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "template_slug": "coding-agent",
  "custom_name": "Imported Python Expert",
  "is_customized": true,
  "visibility": "private",
  "original_creator": "creator@example.com",
  "imported_from": "550e8400-e29b-41d4-a716-446655440000",
  "configuration": {
    "instructions": "Copied configuration...",
    "rules": ["Copied rules..."],
    "capabilities": ["Copied capabilities..."],
    "output_format": "markdown"
  },
  "imported_at": "2025-11-01T19:00:00Z"
}
```

**Name Collision Handling**:
If an agent with the same name exists, automatically appends ` - created by [creator]`:
- Original: "Python Expert"
- Collision result: "Python Expert - created by creator@example.com"

**Errors**:
- `400 Bad Request`: Invalid share token
- `404 Not Found`: Share token not found or agent is private
- `409 Conflict`: Agent already imported by this user

**Example**:

```bash
curl -X POST "https://api.example.com/api/v2/agent-management/import" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "share_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "custom_name": "Imported Python Expert"
  }'
```

---

### 9. Browse Agent Marketplace

List all publicly shared agents available for import.

**Endpoint**: `GET /marketplace/agents`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category |
| `search` | string | No | Search agent names and descriptions |
| `sort_by` | string | No | Sort field: `popular`, `recent` (default: `recent`) |
| `limit` | integer | No | Results per page (default: 20, max: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response**: `200 OK`

```json
{
  "agents": [
    {
      "share_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "template_slug": "coding-agent",
      "custom_name": "Python Django Expert",
      "custom_description": "Specialized Django developer",
      "creator_display_name": "creator@example.com",
      "category": "development",
      "import_count": 245,
      "shared_at": "2025-10-15T10:00:00Z",
      "customizations_summary": {
        "has_custom_instructions": true,
        "has_custom_rules": true,
        "has_custom_capabilities": false
      }
    }
  ],
  "total": 1523,
  "limit": 20,
  "offset": 0
}
```

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/marketplace/agents?category=development&search=python&sort_by=popular&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 10. Get Shared Agent Preview

Public preview of a shared agent before importing. No authentication required.

**Endpoint**: `GET /marketplace/agents/{share_token}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `share_token` | string | Yes | 32-character share token |

**Response**: `200 OK`

```json
{
  "share_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "template_slug": "coding-agent",
  "custom_name": "Python Django Expert",
  "custom_description": "Specialized Django developer",
  "creator_display_name": "creator@example.com",
  "configuration_preview": {
    "instructions_excerpt": "You are a Python expert specializing in Django...",
    "rules_count": 5,
    "capabilities_count": 8,
    "output_format": "markdown"
  },
  "import_count": 245,
  "shared_at": "2025-10-15T10:00:00Z",
  "can_import": true
}
```

**Notes**:
- No authentication required (public endpoint)
- Configuration excerpts limited for security
- Use `/import` endpoint to import after preview

**Errors**:
- `404 Not Found`: Invalid share token or agent is private

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/marketplace/agents/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

---

### 11. List Available Agent Templates

List all system agent templates available for instantiation.

**Endpoint**: `GET /templates`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category |
| `limit` | integer | No | Results per page (default: 50, max: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response**: `200 OK`

```json
{
  "templates": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "slug": "coding-agent",
      "name": "Coding Agent",
      "description": "General-purpose coding agent for software development",
      "category": "development",
      "version": "2.0.0",
      "default_capabilities": [
        "Python",
        "JavaScript",
        "Code review",
        "Testing"
      ],
      "metadata": {
        "tags": ["coding", "development", "general"],
        "popularity": 8.5
      }
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Notes**:
- Templates are system-defined (read-only)
- Calling `/api/mcp` with `call_agent` tool auto-creates instances from templates

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/templates?category=development" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 12. Get Template Details

Retrieve complete details for a specific agent template.

**Endpoint**: `GET /templates/{template_slug}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `template_slug` | string | Yes | Template identifier (e.g., `coding-agent`) |

**Response**: `200 OK`

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "slug": "coding-agent",
  "name": "Coding Agent",
  "description": "General-purpose coding agent for software development",
  "category": "development",
  "version": "2.0.0",
  "default_configuration": {
    "instructions": "You are a professional software developer...",
    "rules": ["Write clean code", "Follow best practices"],
    "capabilities": ["Python", "JavaScript", "Git"],
    "output_format": "markdown"
  },
  "metadata": {
    "tags": ["coding", "development"],
    "popularity": 8.5,
    "use_cases": ["Feature development", "Bug fixes", "Code review"]
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Errors**:
- `404 Not Found`: Template not found

**Example**:

```bash
curl -X GET "https://api.example.com/api/v2/agent-management/templates/coding-agent" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Agent instance not found",
    "details": {
      "instance_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "timestamp": "2025-11-01T20:00:00Z"
  }
}
```

**Common Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | User not authorized for this resource |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `CONFLICT` | 409 | Resource conflict (duplicate, in use) |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limits

**Current Limits** (production will have stricter limits):
- List operations: 100 requests/minute
- Create/Update operations: 20 requests/minute
- Import operations: 10 requests/minute

**Response Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699920000
```

---

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `limit`: Results per page (default varies by endpoint, max 100)
- `offset`: Number of results to skip

**Response**:
```json
{
  "items": [...],
  "total": 1523,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

---

## Versioning

**Current Version**: v2.0.0

The API uses URL-based versioning (`/api/v2/...`). Breaking changes will increment the major version.

**Deprecation Policy**:
- 6 months notice for breaking changes
- Deprecated endpoints return `X-API-Deprecated` header
- Migration guides provided in documentation

---

## Support

**Documentation**: https://docs.example.com/agent-management
**Issues**: https://github.com/example/agenthub/issues
**API Status**: https://status.example.com
