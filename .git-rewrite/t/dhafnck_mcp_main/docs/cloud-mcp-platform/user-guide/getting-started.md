# Getting Started with Cloud MCP Platform

Welcome to the Cloud MCP Platform! This guide will help you get up and running quickly with task management, agent orchestration, and file generation capabilities.

## Prerequisites

Before you begin, ensure you have:
- A Cloud MCP account (sign up at [cloud-mcp.example.com](https://cloud-mcp.example.com))
- Node.js 18+ or Python 3.9+ installed locally
- Basic familiarity with command-line tools

## Quick Start in 5 Minutes

### Step 1: Install the CLI

Choose your preferred language:

**Node.js/npm:**
```bash
npm install -g @cloud-mcp/cli
```

**Python/pip:**
```bash
pip install cloud-mcp-cli
```

### Step 2: Authenticate

```bash
cloud-mcp auth login
# Enter your email and password when prompted
```

This will save your credentials securely in `~/.cloud-mcp/config.json`

### Step 3: Create Your First Task

```bash
# Create a simple task
cloud-mcp task create \
  --title "Build a landing page" \
  --description "Create a responsive landing page with hero section" \
  --priority high
```

### Step 4: List Available Agents

```bash
# See what agents are available
cloud-mcp agent list

# Example output:
# ID              NAME                    CAPABILITIES
# agent_web_001   Web Developer          [html, css, javascript, react]
# agent_py_002    Python Developer       [python, fastapi, django]
# agent_test_003  Test Automation        [unit_testing, integration_testing]
```

### Step 5: Assign an Agent and Execute

```bash
# Assign agent to your task
cloud-mcp task assign task_123 --agent agent_web_001

# Execute the task
cloud-mcp task execute task_123

# Check status
cloud-mcp task status task_123
```

## Understanding Core Concepts

### Tasks
Tasks are units of work that can be assigned to agents. Each task has:
- **Title & Description**: What needs to be done
- **Priority**: Low, Medium, High, or Critical
- **Status**: Pending → In Progress → Completed
- **Agent Assignment**: Which agent will handle it
- **Generated Files**: Output from task execution

### Agents
Agents are AI-powered workers with specific capabilities:
- **Pre-built Agents**: Ready-to-use for common tasks
- **Custom Agents**: Create your own with specific skills
- **Shared Agents**: Use community-created agents

### Templates
Templates are reusable patterns for file generation:
- **File Templates**: Structure for generating code files
- **Project Templates**: Complete project scaffolding
- **Variable Substitution**: Dynamic content generation

## Common Workflows

### Workflow 1: Generate a React Component

```bash
# Use a template to generate files
cloud-mcp template use react-component \
  --var componentName=Button \
  --var hasTests=true \
  --output ./src/components/

# This generates:
# - src/components/Button/Button.tsx
# - src/components/Button/Button.test.tsx
# - src/components/Button/Button.module.css
# - src/components/Button/index.ts
```

### Workflow 2: Create a Full Project

```bash
# Create project with multiple agents
cloud-mcp project create "E-commerce Site" \
  --template fullstack-web \
  --agents 3

# Project creates:
# - 15 tasks automatically
# - Assigns specialized agents
# - Generates project structure
```

### Workflow 3: Custom Agent Creation

```python
# Python example for creating custom agent
from cloud_mcp import Client

client = Client()

# Create a specialized agent
agent = client.agents.create(
    name="API Documentation Generator",
    capabilities=["api_docs", "openapi", "markdown"],
    tools=["swagger", "redoc"],
    base_template="documentation_writer"
)

# Use the agent
task = client.tasks.create(
    title="Generate API docs",
    description="Create OpenAPI specification for REST API"
)

result = agent.execute(task)
print(f"Documentation generated: {result.files}")
```

## Working with Files

Since the Cloud MCP runs in the cloud, file generation works differently:

### Option 1: Download Generated Files

```bash
# Generate files and download as ZIP
cloud-mcp task execute task_123 --output zip

# Download and extract
cloud-mcp download task_123 --to ./my-project/
```

### Option 2: Get File Instructions

```bash
# Get files as JSON with instructions
cloud-mcp task execute task_123 --output json > files.json

# Use the included file writer
cloud-mcp write-files files.json --to ./my-project/
```

### Option 3: Git Integration

```bash
# Push generated files to Git repository
cloud-mcp task execute task_123 \
  --output git \
  --repo https://github.com/user/project \
  --branch generated-files
```

## Using the Web Interface

Access the web dashboard at [app.cloud-mcp.example.com](https://app.cloud-mcp.example.com)

### Dashboard Features
1. **Task Board**: Kanban-style task management
2. **Agent Monitor**: Real-time agent status
3. **Template Library**: Browse and use templates
4. **File Explorer**: View generated files
5. **Analytics**: Track productivity metrics

### Creating Tasks via UI

1. Click "New Task" button
2. Fill in task details:
   - Title and description
   - Select priority
   - Choose template (optional)
   - Add tags for organization
3. Click "Create Task"
4. Assign agent from dropdown
5. Click "Execute" to start

## API Integration

For programmatic access, use the REST API:

```javascript
// JavaScript example
const CloudMCP = require('@cloud-mcp/sdk');

const client = new CloudMCP({
  apiKey: process.env.CLOUD_MCP_API_KEY
});

async function createAndExecuteTask() {
  // Create task
  const task = await client.tasks.create({
    title: 'Generate REST API',
    description: 'Create CRUD endpoints for users',
    template: 'rest-api',
    priority: 'high'
  });

  // Find suitable agent
  const agents = await client.agents.list({
    capabilities: ['python', 'fastapi']
  });

  // Assign and execute
  await client.tasks.assign(task.id, agents[0].id);
  const result = await client.tasks.execute(task.id);

  // Download files
  const files = await client.files.download(result.fileSetId);
  console.log(`Generated ${files.length} files`);
}

createAndExecuteTask();
```

## Environment Configuration

### Local Development

Create `.env` file:
```bash
CLOUD_MCP_API_KEY=your_api_key_here
CLOUD_MCP_API_URL=https://api.cloud-mcp.example.com
CLOUD_MCP_OUTPUT_DIR=./generated
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Generate Code
on: [push]

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install Cloud MCP CLI
        run: npm install -g @cloud-mcp/cli
      
      - name: Generate Files
        env:
          CLOUD_MCP_API_KEY: ${{ secrets.CLOUD_MCP_API_KEY }}
        run: |
          cloud-mcp task execute ${{ vars.TASK_ID }}
          cloud-mcp download ${{ vars.TASK_ID }} --to ./src/
      
      - name: Commit Generated Files
        run: |
          git add .
          git commit -m "Generated files from Cloud MCP"
          git push
```

## Best Practices

### 1. Task Organization

- Use descriptive titles and detailed descriptions
- Tag tasks for easy filtering
- Group related tasks in projects
- Set realistic priorities

### 2. Agent Selection

- Match agent capabilities to task requirements
- Use specialized agents for better results
- Monitor agent performance metrics
- Create custom agents for repeated tasks

### 3. Template Management

- Create templates for common patterns
- Version control your templates
- Share useful templates with team
- Use variables for flexibility

### 4. File Handling

- Always verify generated files before use
- Use version control for generated code
- Review files for security issues
- Test generated code thoroughly

## Troubleshooting

### Common Issues

**Authentication Failed**
```bash
# Clear cached credentials
cloud-mcp auth logout
cloud-mcp auth login
```

**Task Execution Timeout**
```bash
# Increase timeout for long-running tasks
cloud-mcp task execute task_123 --timeout 600
```

**Agent Not Available**
```bash
# Check agent status
cloud-mcp agent status agent_123

# Use different agent
cloud-mcp agent list --available
```

**File Download Issues**
```bash
# Retry download
cloud-mcp download task_123 --retry 3

# Use alternative format
cloud-mcp task execute task_123 --output json
```

### Getting Help

- **Documentation**: [docs.cloud-mcp.example.com](https://docs.cloud-mcp.example.com)
- **Support Email**: support@cloud-mcp.example.com
- **Discord Community**: [discord.gg/cloudmcp](https://discord.gg/cloudmcp)
- **GitHub Issues**: [github.com/cloud-mcp/issues](https://github.com/cloud-mcp/issues)

## Next Steps

Now that you're familiar with the basics:

1. **Explore Templates**: Browse the [Template Marketplace](../advanced/marketplace.md)
2. **Create Custom Agents**: Learn about [Custom Agent Development](../advanced/custom-agents.md)
3. **Team Collaboration**: Set up [Team Workspaces](../tutorials/team-collaboration.md)
4. **Advanced Workflows**: Build [Automation Pipelines](../tutorials/task-pipeline.md)

## Useful Commands Reference

```bash
# Task Management
cloud-mcp task create --title "Task" --priority high
cloud-mcp task list --status pending
cloud-mcp task assign task_123 --agent agent_456
cloud-mcp task execute task_123
cloud-mcp task status task_123
cloud-mcp task delete task_123

# Agent Management
cloud-mcp agent list
cloud-mcp agent create --name "Custom Agent" --capabilities "python,testing"
cloud-mcp agent status agent_123
cloud-mcp agent delete agent_123

# Template Management
cloud-mcp template list
cloud-mcp template use template_name --var key=value
cloud-mcp template create --from ./template.json

# File Operations
cloud-mcp download task_123 --to ./output/
cloud-mcp write-files files.json
cloud-mcp preview task_123

# Project Management
cloud-mcp project create "Project Name" --template web
cloud-mcp project status proj_123
cloud-mcp project execute proj_123
```

## Example: Building a Complete Web App

Here's a complete example of using Cloud MCP to build a web application:

```bash
#!/bin/bash

# 1. Create project
PROJECT_ID=$(cloud-mcp project create "Todo App" \
  --template fullstack-web \
  --framework react \
  --backend nodejs \
  --database postgresql \
  --format json | jq -r '.project.id')

echo "Created project: $PROJECT_ID"

# 2. Execute project tasks
cloud-mcp project execute $PROJECT_ID --mode parallel

# 3. Wait for completion
while true; do
  STATUS=$(cloud-mcp project status $PROJECT_ID --format json | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  echo "Waiting for project completion..."
  sleep 10
done

# 4. Download generated files
cloud-mcp project download $PROJECT_ID --to ./todo-app/

# 5. Install dependencies and run
cd todo-app
npm install
npm run dev

echo "Todo app is running at http://localhost:3000"
```

Congratulations! You're now ready to leverage the full power of the Cloud MCP Platform for your development workflows.