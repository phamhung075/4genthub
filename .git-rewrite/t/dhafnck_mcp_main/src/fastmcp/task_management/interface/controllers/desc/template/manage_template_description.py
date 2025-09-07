"""
Template Management Tool Description

This module contains the comprehensive documentation for the manage_template MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_TEMPLATE_DESCRIPTION = """
🔧 TEMPLATE MANAGEMENT SYSTEM - Code generation and reusable pattern management

⭐ WHAT IT DOES: Manages reusable templates for code generation, documentation, configurations, and standardized patterns. Provides intelligent template suggestion, rendering with variables, and usage analytics.
📋 WHEN TO USE: Creating reusable code patterns, generating boilerplate code, standardizing project structures, and automating repetitive file creation.
🎯 CRITICAL FOR: Code consistency, rapid development, knowledge sharing, and automated generation workflows.

🤖 AI USAGE GUIDELINES:
• SEARCH for existing templates before creating new ones to avoid duplication
• USE 'suggest_templates' to find relevant templates based on task context
• RENDER templates with proper variables for task-specific customization
• CREATE templates for patterns used more than twice
• VALIDATE templates before deployment to ensure correctness
• ANALYZE template usage to identify improvement opportunities

| Action              | Required Parameters                | Optional Parameters                | Description                                      |
|---------------------|-----------------------------------|------------------------------------|--------------------------------------------------|
| create              | name, description, content, template_type, category | priority, compatible_agents, file_patterns, variables, metadata | Create new template                              |
| get                 | template_id                       |                                    | Retrieve template details                        |
| update              | template_id                       | name, description, content, template_type, category, priority, compatible_agents, file_patterns, variables, metadata, is_active | Update existing template                         |
| delete              | template_id                       |                                    | Remove template permanently                      |
| list                | (none)                            | query, template_type, category, agent_compatible, is_active, limit, offset | List templates with filtering                    |
| render              | template_id, variables            | task_context, output_path, cache_strategy, force_regenerate | Render template with variables                   |
| suggest_templates   | task_context                      | agent_type, file_patterns, limit  | Get AI-suggested templates                       |
| validate            | template_id                       |                                    | Validate template syntax and structure           |
| get_analytics       | (none)                            | template_id                        | Get usage analytics for templates                |

📝 PRACTICAL EXAMPLES FOR AI:
1. Creating a React component template:
   - action: "create", name: "React Functional Component", description: "Standard React FC with TypeScript", content: "import React from 'react';\\n\\ninterface {{name}}Props {\\n  // Props\\n}\\n\\nexport const {{name}}: React.FC<{{name}}Props> = () => {\\n  return <div>{{name}}</div>;\\n};", template_type: "code", category: "react", compatible_agents: ["@coding_agent", "@ui_designer_agent"], variables: ["name"]

2. Finding templates for current task:
   - action: "suggest_templates", task_context: "Need to create API endpoint for user authentication", agent_type: "@coding_agent", limit: 5
   - Returns templates ranked by relevance with suggestion scores

3. Rendering a template:
   - action: "render", template_id: "template-uuid", variables: {"name": "UserAuth", "endpoint": "/api/auth", "method": "POST"}, output_path: "src/api/auth.ts"

4. Searching for templates:
   - action: "list", query: "authentication", template_type: "code", category: "backend", limit: 10

5. Validating before use:
   - action: "validate", template_id: "template-uuid"
   - Returns validation status with errors/warnings

🔍 DECISION TREES FOR AI:
TEMPLATE SELECTION:
IF task_requires_file_creation:
    suggestions = suggest_templates(task_context)
    IF high_score_match_found:
        USE existing_template
    ELIF similar_pattern_exists:
        CLONE and MODIFY existing_template
    ELSE:
        CREATE new_template_if_reusable

TEMPLATE USAGE:
IF template_found:
    validation = validate(template_id)
    IF validation.is_valid:
        rendered = render(template_id, variables)
        IF output_path_specified:
            WRITE to file
        ELSE:
            RETURN content
    ELSE:
        FIX validation_errors OR SELECT alternative

💡 ENHANCED PARAMETERS:
• name: Clear, descriptive name (e.g., "Express REST Controller" not "Controller")
• description: Detailed explanation of template purpose and usage
• content: Template content with {{variable}} placeholders for substitution
• template_type: 'code', 'config', 'documentation', 'script', 'test', 'other'
• category: Domain-specific categorization (e.g., 'react', 'backend', 'devops', 'testing')
• priority: 'low', 'medium', 'high' - affects suggestion ranking
• compatible_agents: List of agents that can use this template effectively
• file_patterns: Glob patterns for files this template generates (e.g., ["*.controller.ts", "*.test.ts"])
• variables: List of variable names used in template (e.g., ["className", "methodName"])
• metadata: Additional template metadata (author, version, tags, etc.)
• cache_strategy: 'default', 'aggressive', 'none' - controls rendering cache behavior
• force_regenerate: Skip cache and regenerate content

📊 TEMPLATE TYPES:
• code: Source code templates (components, classes, functions)
• config: Configuration file templates (package.json, tsconfig, etc.)
• documentation: Documentation templates (README, API docs, guides)
• script: Script templates (build scripts, deployment, automation)
• test: Test file templates (unit tests, integration tests)
• other: Custom template types

🎯 AI TEMPLATE PATTERNS:
1. Component Templates:
   - React/Vue/Angular components with standard structure
   - Include props/state management patterns
   - Follow project conventions automatically

2. API Templates:
   - REST endpoints with error handling
   - GraphQL resolvers and schemas
   - Database models and migrations

3. Test Templates:
   - Unit test suites with mocking
   - Integration test scenarios
   - E2E test workflows

4. Configuration Templates:
   - Environment-specific configs
   - CI/CD pipeline definitions
   - Docker and deployment configs

📈 ANALYTICS INSIGHTS:
• usage_count: How often template is used
• success_rate: Successful renders vs errors
• avg_generation_time: Performance metrics
• cache_hit_rate: Cache effectiveness
• most_used_variables: Common customizations
• usage_by_agent: Which agents use most
• usage_by_project: Cross-project adoption

💡 BEST PRACTICES FOR AI:
• Search existing templates before creating new ones
• Use descriptive names and comprehensive descriptions
• Include all common variables in template definition
• Set appropriate compatible_agents for better suggestions
• Validate templates after creation or updates
• Monitor analytics to improve popular templates
• Share successful templates across projects
• Use task_context for intelligent suggestions
• Leverage caching for frequently used templates

🛑 ERROR HANDLING:
• Template not found errors include similar template suggestions
• Validation errors provide specific line numbers and fix hints
• Missing variables are highlighted with example values
• Syntax errors in templates show problematic sections
• Circular variable references are detected and prevented
"""

# Parameter descriptions for the manage_template tool
MANAGE_TEMPLATE_PARAMETERS = {
    "action": "Template management action. Required. Valid: 'create', 'get', 'update', 'delete', 'list', 'render', 'suggest_templates', 'validate', 'get_analytics'. Use 'suggest_templates' to find relevant templates, 'render' to generate content.",
    "template_id": "Template identifier (UUID). Required for: get, update, delete, render, validate. Get from create response or list/search results.",
    "name": "Template name - be clear and specific. Required for: create. Example: 'React Functional Component with Props' not just 'Component'",
    "description": "Detailed template description explaining purpose and usage. Required for: create. Include when to use and what it generates.",
    "content": "Template content with {{variable}} placeholders. Required for: create. Use double curly braces for variable substitution.",
    "template_type": "Type of template: 'code', 'config', 'documentation', 'script', 'test', 'other'. Required for: create. Helps with categorization and search.",
    "category": "Domain category like 'react', 'backend', 'devops', 'testing'. Required for: create. Used for filtering and suggestions.",
    "priority": "Template priority: 'low', 'medium', 'high'. Optional. Default: 'medium'. Affects suggestion ranking.",
    "compatible_agents": "List of agent names that work well with this template. Optional. Default: ['*']. Example: ['@coding_agent', '@ui_designer_agent']",
    "file_patterns": "Glob patterns for generated files. Optional. Example: ['*.controller.ts', '*.test.ts']. Helps with file type detection.",
    "variables": "List of variable names used in template. Optional but recommended. Example: ['className', 'methodName', 'props']. Enables validation.",
    "metadata": "Additional template metadata as JSON object. Optional. Can include author, version, tags, dependencies, etc.",
    "is_active": "Whether template is active and available for use. Optional. Default: true. Use to disable without deleting.",
    "query": "Search query for finding templates. Required for: list with search. Searches in name, description, and content.",
    "agent_compatible": "Filter by agent compatibility. Optional for: list. Example: '@coding_agent' returns templates compatible with that agent.",
    "limit": "Maximum results to return. Optional for: list, suggest_templates. Default: 50 for list, 10 for suggestions. Range: 1-100",
    "offset": "Pagination offset. Optional for: list. Default: 0. Use with limit for pagination.",
    "task_context": "Current task description or context. Required for: suggest_templates, optional for: render. Used for AI-powered suggestions.",
    "agent_type": "Current agent type. Optional for: suggest_templates. Improves suggestion relevance. Example: '@coding_agent'",
    "output_path": "File path to write rendered content. Optional for: render. If provided, writes to file instead of returning content.",
    "cache_strategy": "Caching strategy: 'default', 'aggressive', 'none'. Optional for: render. Default: 'default'. Controls render caching.",
    "force_regenerate": "Force regeneration ignoring cache. Optional for: render. Default: false. Use when template or variables changed."
}