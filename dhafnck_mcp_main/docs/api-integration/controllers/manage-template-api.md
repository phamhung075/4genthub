# manage_template - Template Management API Documentation

## Overview

The `manage_template` tool provides comprehensive template management for code generation, documentation, configurations, and standardized patterns. It includes intelligent template suggestion, variable substitution, rendering with caching, usage analytics, and validation capabilities.

## Base Information

- **Tool Name**: `manage_template`
- **Controller**: `TemplateController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.template_controller`
- **Authentication**: Required (user context from JWT)
- **Caching**: ✅ Intelligent rendering cache with configurable strategies
- **Analytics**: ✅ Usage tracking and performance metrics

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Template operation to perform"
    },
    "template_id": {
      "type": "string",
      "description": "[OPTIONAL] Template UUID identifier"
    },
    "name": {
      "type": "string",
      "description": "[OPTIONAL] Template name"
    },
    "description": {
      "type": "string",
      "description": "[OPTIONAL] Template description"
    },
    "content": {
      "type": "string",
      "description": "[OPTIONAL] Template content with {{variable}} placeholders"
    },
    "template_type": {
      "type": "string",
      "description": "[OPTIONAL] Template type: 'code', 'config', 'documentation', 'script', 'test', 'other'"
    },
    "category": {
      "type": "string",
      "description": "[OPTIONAL] Domain category for organization"
    },
    "priority": {
      "type": "string",
      "description": "[OPTIONAL] Template priority: 'low', 'medium', 'high'"
    },
    "compatible_agents": {
      "type": "string",
      "description": "[OPTIONAL] List of compatible agent names"
    },
    "file_patterns": {
      "type": "string",
      "description": "[OPTIONAL] Glob patterns for generated files"
    },
    "variables": {
      "type": "string",
      "description": "[OPTIONAL] List of variable names used in template"
    },
    "metadata": {
      "type": "string",
      "description": "[OPTIONAL] Additional template metadata as JSON"
    },
    "task_context": {
      "type": "string",
      "description": "[OPTIONAL] Task context for suggestions and rendering"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core CRUD Operations

#### `create` - Create New Template

Creates a new reusable template with metadata and variable definitions.

**Required Parameters:**
- `action`: "create"
- `name`: Template name
- `description`: Template description
- `content`: Template content with `{{variable}}` placeholders
- `template_type`: Template type ('code', 'config', 'documentation', 'script', 'test', 'other')
- `category`: Domain category for organization

**Optional Parameters:**
- `priority`: Priority level (default: "medium")
- `compatible_agents`: List of agent names (default: ["*"])
- `file_patterns`: Glob patterns for generated files
- `variables`: Variable names used in template
- `metadata`: Additional metadata as JSON object

**Example Request:**
```json
{
  "action": "create",
  "name": "React Functional Component",
  "description": "Standard React functional component with TypeScript and props interface",
  "content": "import React from 'react';\n\ninterface {{name}}Props {\n  {{propsDefinition}}\n}\n\nexport const {{name}}: React.FC<{{name}}Props> = ({{propsDestructuring}}) => {\n  return (\n    <div className=\"{{className}}\">\n      {{content}}\n    </div>\n  );\n};",
  "template_type": "code",
  "category": "react",
  "priority": "high",
  "compatible_agents": ["@coding_agent", "@ui_designer_agent"],
  "file_patterns": ["*.tsx", "*.ts"],
  "variables": ["name", "propsDefinition", "propsDestructuring", "className", "content"]
}
```

**Example Response:**
```json
{
  "success": true,
  "template": {
    "id": "template-123e4567-e89b-12d3-a456-426614174000",
    "name": "React Functional Component",
    "description": "Standard React functional component with TypeScript and props interface",
    "content": "import React from 'react';\n\ninterface {{name}}Props {\n  {{propsDefinition}}\n}\n\nexport const {{name}}: React.FC<{{name}}Props> = ({{propsDestructuring}}) => {\n  return (\n    <div className=\"{{className}}\">\n      {{content}}\n    </div>\n  );\n};",
    "template_type": "code",
    "category": "react",
    "status": "active",
    "priority": "high",
    "compatible_agents": ["@coding_agent", "@ui_designer_agent"],
    "file_patterns": ["*.tsx", "*.ts"],
    "variables": ["name", "propsDefinition", "propsDestructuring", "className", "content"],
    "metadata": {},
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T10:30:00Z",
    "version": 1,
    "is_active": true
  }
}
```

#### `get` - Retrieve Template

Gets a specific template by ID with all metadata and content.

**Required Parameters:**
- `action`: "get"
- `template_id`: Template UUID

**Example Request:**
```json
{
  "action": "get",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "template": {
    "id": "template-123e4567-e89b-12d3-a456-426614174000",
    "name": "React Functional Component",
    "description": "Standard React functional component with TypeScript and props interface",
    "content": "import React from 'react';\n\ninterface {{name}}Props {\n  {{propsDefinition}}\n}\n\nexport const {{name}}: React.FC<{{name}}Props> = ({{propsDestructuring}}) => {\n  return (\n    <div className=\"{{className}}\">\n      {{content}}\n    </div>\n  );\n};",
    "template_type": "code",
    "category": "react",
    "status": "active",
    "priority": "high",
    "compatible_agents": ["@coding_agent", "@ui_designer_agent"],
    "file_patterns": ["*.tsx", "*.ts"],
    "variables": ["name", "propsDefinition", "propsDestructuring", "className", "content"],
    "metadata": {},
    "created_at": "2025-01-27T10:30:00Z",
    "updated_at": "2025-01-27T10:30:00Z",
    "version": 1,
    "is_active": true
  }
}
```

#### `update` - Update Existing Template

Updates template content, metadata, or configuration.

**Required Parameters:**
- `action`: "update"
- `template_id`: Template UUID

**Optional Parameters:**
- Any field that can be updated (name, description, content, etc.)

**Example Request:**
```json
{
  "action": "update",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000",
  "description": "Enhanced React functional component with TypeScript, props interface, and error boundaries",
  "priority": "critical",
  "variables": ["name", "propsDefinition", "propsDestructuring", "className", "content", "errorFallback"]
}
```

#### `delete` - Delete Template

Permanently removes a template from the system.

**Required Parameters:**
- `action`: "delete"
- `template_id`: Template UUID

**Example Request:**
```json
{
  "action": "delete",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "message": "Template deleted successfully"
}
```

### Search and Discovery Operations

#### `list` - List Templates

Lists templates with filtering, pagination, and search capabilities.

**Required Parameters:**
- `action`: "list"

**Optional Parameters:**
- `query`: Search in name, description, and content
- `template_type`: Filter by template type
- `category`: Filter by category
- `agent_compatible`: Filter by agent compatibility
- `is_active`: Filter by active status
- `limit`: Maximum results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)

**Example Request:**
```json
{
  "action": "list",
  "query": "react component",
  "template_type": "code",
  "category": "react",
  "agent_compatible": "@coding_agent",
  "limit": 10,
  "offset": 0
}
```

**Example Response:**
```json
{
  "success": true,
  "templates": [
    {
      "id": "template-123e4567-e89b-12d3-a456-426614174000",
      "name": "React Functional Component",
      "description": "Standard React functional component with TypeScript and props interface",
      "template_type": "code",
      "category": "react",
      "priority": "high",
      "compatible_agents": ["@coding_agent", "@ui_designer_agent"],
      "file_patterns": ["*.tsx", "*.ts"],
      "variables": ["name", "propsDefinition", "propsDestructuring", "className", "content"],
      "created_at": "2025-01-27T10:30:00Z",
      "is_active": true
    }
  ],
  "pagination": {
    "total_count": 15,
    "page": 1,
    "page_size": 10,
    "has_next": true,
    "has_previous": false
  }
}
```

#### `suggest_templates` - AI-Powered Template Suggestions

Gets AI-suggested templates based on current task context and agent type.

**Required Parameters:**
- `action`: "suggest_templates"
- `task_context`: Current task description or context

**Optional Parameters:**
- `agent_type`: Current agent for better suggestions
- `file_patterns`: File patterns being worked with
- `limit`: Maximum suggestions (default: 10)

**Example Request:**
```json
{
  "action": "suggest_templates",
  "task_context": "Need to create a REST API endpoint for user authentication with JWT tokens",
  "agent_type": "@coding_agent",
  "file_patterns": ["*.ts", "*.js"],
  "limit": 5
}
```

**Example Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "template_id": "template-auth-endpoint-uuid",
      "name": "Express JWT Authentication Endpoint",
      "description": "Express.js endpoint with JWT authentication and validation",
      "template_type": "code",
      "category": "backend",
      "priority": "high",
      "suggestion_score": 0.95,
      "suggestion_reason": "Perfect match for JWT authentication API endpoint",
      "compatible_agents": ["@coding_agent", "@security_auditor_agent"],
      "file_patterns": ["*.ts", "*.js"],
      "variables": ["routePath", "validationSchema", "jwtSecret", "tokenExpiry"]
    },
    {
      "template_id": "template-auth-middleware-uuid",
      "name": "JWT Authentication Middleware",
      "description": "Express middleware for JWT token verification",
      "template_type": "code",
      "category": "backend",
      "priority": "medium",
      "suggestion_score": 0.87,
      "suggestion_reason": "Commonly used with authentication endpoints",
      "compatible_agents": ["@coding_agent"],
      "file_patterns": ["*.ts", "*.js"],
      "variables": ["jwtSecret", "errorHandling"]
    }
  ]
}
```

### Template Processing Operations

#### `render` - Render Template with Variables

Renders template content with variable substitution and caching.

**Required Parameters:**
- `action`: "render"
- `template_id`: Template UUID
- `variables`: JSON object with variable values

**Optional Parameters:**
- `task_context`: Additional context for rendering
- `output_path`: File path to write rendered content
- `cache_strategy`: 'default', 'aggressive', 'none'
- `force_regenerate`: Skip cache and regenerate

**Example Request:**
```json
{
  "action": "render",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000",
  "variables": {
    "name": "UserProfile",
    "propsDefinition": "user: User;\n  onUpdate: (user: User) => void;",
    "propsDestructuring": "{ user, onUpdate }",
    "className": "user-profile-container",
    "content": "<h1>{user.name}</h1>\n      <UserForm user={user} onSubmit={onUpdate} />"
  },
  "task_context": "Creating user profile component for dashboard",
  "output_path": "src/components/UserProfile.tsx"
}
```

**Example Response:**
```json
{
  "success": true,
  "result": {
    "content": "import React from 'react';\n\ninterface UserProfileProps {\n  user: User;\n  onUpdate: (user: User) => void;\n}\n\nexport const UserProfile: React.FC<UserProfileProps> = ({ user, onUpdate }) => {\n  return (\n    <div className=\"user-profile-container\">\n      <h1>{user.name}</h1>\n      <UserForm user={user} onSubmit={onUpdate} />\n    </div>\n  );\n};",
    "template_id": "template-123e4567-e89b-12d3-a456-426614174000",
    "variables_used": ["name", "propsDefinition", "propsDestructuring", "className", "content"],
    "generated_at": "2025-01-27T11:15:00Z",
    "generation_time_ms": 45,
    "cache_hit": false,
    "output_path": "src/components/UserProfile.tsx"
  }
}
```

### Quality Assurance Operations

#### `validate` - Validate Template

Validates template syntax, variables, and structure.

**Required Parameters:**
- `action`: "validate"
- `template_id`: Template UUID

**Example Request:**
```json
{
  "action": "validate",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Variable 'className' is optional but commonly used"
    ],
    "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
  }
}
```

**Validation Error Response:**
```json
{
  "success": true,
  "validation": {
    "is_valid": false,
    "errors": [
      "Unclosed variable placeholder at line 5: {{unclosedVar",
      "Undefined variable 'unknownVar' used at line 8"
    ],
    "warnings": [
      "Consider adding default values for optional variables"
    ],
    "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
  }
}
```

#### `get_analytics` - Template Usage Analytics

Retrieves usage statistics and performance metrics for templates.

**Required Parameters:**
- `action`: "get_analytics"

**Optional Parameters:**
- `template_id`: Specific template UUID (if not provided, returns system-wide analytics)

**Example Request:**
```json
{
  "action": "get_analytics",
  "template_id": "template-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "analytics": {
    "template_id": "template-123e4567-e89b-12d3-a456-426614174000",
    "usage_count": 156,
    "success_rate": 0.94,
    "avg_generation_time": 67.5,
    "total_generation_time": 10530,
    "cache_hit_rate": 0.73,
    "most_used_variables": [
      {"name": "name", "usage_count": 156},
      {"name": "className", "usage_count": 142},
      {"name": "content", "usage_count": 156}
    ],
    "usage_by_agent": {
      "@coding_agent": 89,
      "@ui_designer_agent": 45,
      "@test_orchestrator_agent": 22
    },
    "usage_by_project": {
      "ecommerce-frontend": 78,
      "admin-dashboard": 45,
      "mobile-app": 33
    },
    "usage_over_time": [
      {"date": "2025-01-20", "count": 12},
      {"date": "2025-01-21", "count": 18},
      {"date": "2025-01-22", "count": 25}
    ]
  }
}
```

## Template Variable Substitution

### Variable Syntax

Templates use `{{variableName}}` syntax for variable placeholders:

```javascript
// Template content example
const {{className}} = {
  name: '{{componentName}}',
  type: '{{componentType}}',
  props: {{propsJSON}}
};
```

### Variable Types

1. **Simple Variables**: `{{name}}` - Direct string substitution
2. **JSON Variables**: `{{propsJSON}}` - JSON object/array substitution
3. **Conditional Variables**: Planned for future implementation
4. **Loop Variables**: Planned for future implementation

### Variable Validation

- All variables used in template content should be listed in the `variables` array
- Undefined variables will cause validation errors
- Missing variables during rendering will cause render errors

## Template Types and Categories

### Template Types

- **`code`**: Source code templates (components, classes, functions)
- **`config`**: Configuration file templates (package.json, tsconfig, etc.)
- **`documentation`**: Documentation templates (README, API docs, guides)
- **`script`**: Script templates (build scripts, deployment, automation)
- **`test`**: Test file templates (unit tests, integration tests)
- **`other`**: Custom template types

### Common Categories

- **Frontend**: `react`, `vue`, `angular`, `html`, `css`
- **Backend**: `express`, `fastapi`, `django`, `spring`, `nodejs`
- **Testing**: `jest`, `cypress`, `selenium`, `unittest`
- **DevOps**: `docker`, `kubernetes`, `terraform`, `ci-cd`
- **Database**: `sql`, `mongodb`, `redis`, `migrations`

## Template Inheritance and Composition

### Future Features (Planned)

1. **Template Inheritance**: Templates can extend base templates
2. **Template Composition**: Combine multiple templates
3. **Nested Templates**: Templates within templates
4. **Template Libraries**: Shared template collections

### Current Limitations

- No template inheritance (flat structure only)
- No template composition (single template rendering)
- No nested template support

## Caching Strategy

### Cache Strategies

1. **`default`**: Smart caching based on template version and variables
2. **`aggressive`**: Cache aggressively, refresh only on explicit changes
3. **`none`**: No caching, always regenerate content

### Cache Invalidation

- Template content changes invalidate cache
- Template metadata changes may invalidate cache
- Force regeneration bypasses all caching

## Error Handling

### Common Errors

```json
{
  "success": false,
  "error": "Template not found: template-invalid-uuid"
}
```

```json
{
  "success": false,
  "error": "Required parameter missing: content is required for create action"
}
```

```json
{
  "success": false,
  "error": "Variable substitution failed: undefined variable 'missingVar' in template"
}
```

### Validation Errors

```json
{
  "success": true,
  "validation": {
    "is_valid": false,
    "errors": [
      "Syntax error: Unclosed variable placeholder at line 5",
      "Reference error: Variable 'undefined_var' not declared in variables list"
    ],
    "warnings": [
      "Performance: Consider using fewer nested variables",
      "Best practice: Add description for complex variables"
    ]
  }
}
```

## Best Practices

### Template Creation

1. **Descriptive Names**: Use clear, specific template names
2. **Comprehensive Descriptions**: Explain purpose, usage, and benefits
3. **Variable Documentation**: List all variables with descriptions
4. **Agent Compatibility**: Specify which agents work best with template
5. **File Patterns**: Define expected output file patterns

### Template Usage

1. **Search First**: Check existing templates before creating new ones
2. **Use Suggestions**: Leverage AI-powered template suggestions
3. **Validate Before Use**: Run validation on templates before rendering
4. **Monitor Analytics**: Track usage to identify improvement opportunities
5. **Proper Variables**: Provide all required variables with appropriate values

### Performance Optimization

1. **Use Caching**: Leverage default caching strategy for repeated renders
2. **Optimize Variables**: Minimize complex variable substitutions
3. **Batch Operations**: Group multiple renders when possible
4. **Monitor Metrics**: Use analytics to identify slow templates

## JSON-RPC Format Examples

### Complete JSON-RPC Create Request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "manage_template",
    "arguments": {
      "action": "create",
      "name": "Express API Endpoint",
      "description": "Standard Express.js API endpoint with validation and error handling",
      "content": "import { Request, Response } from 'express';\nimport { validateSchema } from '../utils/validation';\n\nexport const {{handlerName}} = async (req: Request, res: Response) => {\n  try {\n    const validatedData = validateSchema(req.body, {{validationSchema}});\n    \n    // {{businessLogic}}\n    \n    res.status(200).json({\n      success: true,\n      data: result\n    });\n  } catch (error) {\n    res.status({{errorCode}}).json({\n      success: false,\n      error: error.message\n    });\n  }\n};",
      "template_type": "code",
      "category": "backend",
      "priority": "high",
      "compatible_agents": ["@coding_agent"],
      "file_patterns": ["*.controller.ts", "*.route.ts"],
      "variables": ["handlerName", "validationSchema", "businessLogic", "errorCode"]
    }
  }
}
```

### Complete JSON-RPC Render Request
```json
{
  "jsonrpc": "2.0", 
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "manage_template",
    "arguments": {
      "action": "render",
      "template_id": "template-express-endpoint-uuid",
      "variables": {
        "handlerName": "createUserHandler",
        "validationSchema": "userCreateSchema",
        "businessLogic": "const user = await userService.createUser(validatedData);\\nconst result = { user: user.toJSON() };",
        "errorCode": "400"
      },
      "output_path": "src/controllers/user.controller.ts"
    }
  }
}
```

This comprehensive documentation covers all aspects of the `manage_template` API, including detailed examples, error handling, best practices, and future roadmap items.