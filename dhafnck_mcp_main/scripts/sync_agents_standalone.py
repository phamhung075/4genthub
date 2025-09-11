#!/usr/bin/env python3
"""
Standalone Agent Sync Script
============================
This script generates .claude/agents/*.md files from predefined agent configurations.
Works without server dependency.
"""

from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Default configuration
DEFAULT_CLAUDE_DIR = ".claude/agents"

# Predefined agent configurations
AGENT_DEFINITIONS = {
    "master-orchestrator-agent": {
        "name": "Uber Orchestrator Agent",
        "role": "Master Coordinator and Decision Maker",
        "description": "The highest-level orchestrator that coordinates all other agents and makes strategic decisions about task delegation, resource allocation, and workflow optimization.",
        "category": "orchestration",
        "type": "orchestrator",
        "priority": "critical",
        "capabilities": [
            "Multi-agent coordination across all domains",
            "Strategic planning and decision making",
            "Resource allocation and optimization",
            "Complex workflow orchestration",
            "Cross-functional team management"
        ],
        "tools": ["All MCP tools available"],
        "specializations": [
            "Complex project management",
            "Cross-functional coordination",
            "System-wide optimization",
            "Agent delegation and task distribution",
            "Conflict resolution between agents"
        ],
        "guidelines": "Use as the primary entry point for complex tasks requiring multiple specialists. This agent will analyze requirements and delegate to appropriate specialist agents."
    },
    "coding-agent": {
        "name": "Coding Agent",
        "role": "Software Development Specialist",
        "description": "Specialized in writing, refactoring, and implementing code across various languages and frameworks. Expert in DDD architecture, clean code principles, and modern development practices.",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Code implementation in Python, TypeScript, JavaScript",
            "API development with FastAPI/FastMCP",
            "Frontend development with React",
            "Database design and optimization",
            "Algorithm design and optimization"
        ],
        "tools": ["Edit", "Write", "Read", "MultiEdit", "Bash", "Grep", "Glob"],
        "specializations": [
            "Domain-Driven Design (DDD) architecture",
            "React component development",
            "FastAPI/FastMCP backend development",
            "TypeScript/JavaScript implementation",
            "Python development with type hints"
        ],
        "guidelines": "Use for all coding tasks including new feature implementation, refactoring, and code optimization. Follows project conventions and patterns."
    },
    "debugger-agent": {
        "name": "Debugger Agent",
        "role": "Bug Detection and Resolution Specialist",
        "description": "Expert in identifying, analyzing, and fixing bugs and errors in code. Specializes in root cause analysis, performance debugging, and test failure resolution.",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Error analysis and stack trace interpretation",
            "Performance profiling and optimization",
            "Memory leak detection and resolution",
            "Test failure investigation",
            "Runtime error debugging"
        ],
        "tools": ["Read", "Grep", "Bash", "Edit", "mcp__ide__getDiagnostics"],
        "specializations": [
            "Python exception handling",
            "TypeScript/JavaScript debugging",
            "Async/await issues resolution",
            "Database query optimization",
            "API endpoint debugging"
        ],
        "guidelines": "Deploy when encountering errors, test failures, performance issues, or unexpected behavior. Provides detailed root cause analysis."
    },
    "test-orchestrator-agent": {
        "name": "Test Orchestrator Agent",
        "role": "Testing Strategy and Execution Coordinator",
        "description": "Manages comprehensive testing strategies, coordinates test execution, and ensures code quality through automated testing.",
        "category": "quality",
        "type": "orchestrator",
        "priority": "high",
        "capabilities": [
            "Test strategy design and planning",
            "Test suite orchestration",
            "Code coverage analysis",
            "Test automation implementation",
            "CI/CD pipeline integration"
        ],
        "tools": ["Bash", "Write", "Read", "Edit", "TodoWrite"],
        "specializations": [
            "Pytest test framework",
            "Jest/React Testing Library",
            "Integration testing strategies",
            "E2E testing with Playwright/Cypress",
            "Performance testing frameworks"
        ],
        "guidelines": "Use for designing test strategies, writing test cases, and ensuring comprehensive test coverage. Coordinates with other agents for test implementation."
    },
    "@ui_designer_agent": {
        "name": "UI Designer Agent",
        "role": "User Interface and Experience Specialist",
        "description": "Focused on frontend development, UI/UX design, and creating intuitive user interactions. Expert in modern frontend frameworks and responsive design.",
        "category": "frontend",
        "type": "specialist",
        "priority": "normal",
        "capabilities": [
            "React component architecture",
            "Responsive design implementation",
            "State management with Redux/Context",
            "User interaction flow design",
            "Accessibility compliance (WCAG)"
        ],
        "tools": ["Edit", "Write", "Read", "WebFetch", "mcp__shadcn-ui-server__*"],
        "specializations": [
            "React hooks and functional components",
            "TypeScript for React",
            "Tailwind CSS styling",
            "shadcn/ui component integration",
            "Mobile-first responsive design"
        ],
        "guidelines": "Deploy for all frontend tasks including component creation, UI improvements, and user experience enhancements."
    },
    "documentation-agent": {
        "name": "Documentation Agent",
        "role": "Technical Documentation Specialist",
        "description": "Creates and maintains comprehensive documentation including API specs, user guides, and technical documentation.",
        "category": "documentation",
        "type": "specialist",
        "priority": "normal",
        "capabilities": [
            "API documentation with OpenAPI/Swagger",
            "User guide creation",
            "Technical specification writing",
            "README and setup guide creation",
            "Code documentation and comments"
        ],
        "tools": ["Write", "Read", "Edit", "Glob"],
        "specializations": [
            "Markdown documentation",
            "API endpoint documentation",
            "Architecture documentation",
            "Migration and upgrade guides",
            "Best practices documentation"
        ],
        "guidelines": "Use for creating or updating any form of documentation. Ensures consistency with existing documentation structure."
    },
    "task-planning-agent": {
        "name": "Task Planning Agent",
        "role": "Task Breakdown and Planning Specialist",
        "description": "Breaks down complex tasks into manageable subtasks, creates execution plans, and manages task dependencies.",
        "category": "planning",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Task decomposition and analysis",
            "Dependency mapping and management",
            "Timeline and milestone estimation",
            "Resource planning and allocation",
            "Risk assessment and mitigation"
        ],
        "tools": ["TodoWrite", "mcp__dhafnck_mcp_http__manage_task", "mcp__dhafnck_mcp_http__manage_subtask"],
        "specializations": [
            "Agile methodology planning",
            "Sprint planning and management",
            "Milestone tracking",
            "Critical path analysis",
            "Dependency resolution"
        ],
        "guidelines": "Deploy at the beginning of complex projects or when tasks need to be broken down into manageable pieces."
    },
    "security-auditor-agent": {
        "name": "Security Auditor Agent",
        "role": "Security Analysis and Compliance Specialist",
        "description": "Performs security audits, vulnerability assessments, and ensures compliance with security best practices.",
        "category": "security",
        "type": "specialist",
        "priority": "critical",
        "capabilities": [
            "Security vulnerability scanning",
            "Authentication/authorization review",
            "Data protection assessment",
            "OWASP compliance checking",
            "Security best practices enforcement"
        ],
        "tools": ["Read", "Grep", "Bash", "mcp__dhafnck_mcp_http__manage_compliance"],
        "specializations": [
            "JWT token security",
            "SQL injection prevention",
            "XSS and CSRF protection",
            "Security headers configuration",
            "Secrets management"
        ],
        "guidelines": "Deploy for security reviews, vulnerability assessments, and when implementing authentication/authorization features."
    },
    "@database_architect_agent": {
        "name": "Database Architect Agent",
        "role": "Database Design and Optimization Specialist",
        "description": "Expert in database design, query optimization, and data modeling. Handles both SQL and NoSQL databases.",
        "category": "database",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Database schema design",
            "Query optimization",
            "Index strategy planning",
            "Data migration planning",
            "Performance tuning"
        ],
        "tools": ["Bash", "Read", "Write", "Edit"],
        "specializations": [
            "PostgreSQL optimization",
            "SQLite configuration",
            "Supabase integration",
            "Redis caching strategies",
            "Database migration scripts"
        ],
        "guidelines": "Use for database-related tasks including schema changes, query optimization, and data migration planning."
    },
    "@devops_engineer_agent": {
        "name": "DevOps Engineer Agent",
        "role": "Infrastructure and Deployment Specialist",
        "description": "Manages Docker containers, CI/CD pipelines, and deployment configurations. Expert in containerization and orchestration.",
        "category": "infrastructure",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Docker container management",
            "CI/CD pipeline configuration",
            "Kubernetes orchestration",
            "Infrastructure as Code",
            "Monitoring and logging setup"
        ],
        "tools": ["Bash", "Write", "Read", "Edit"],
        "specializations": [
            "Docker and Docker Compose",
            "GitHub Actions workflows",
            "Environment configuration",
            "Service monitoring",
            "Log aggregation"
        ],
        "guidelines": "Deploy for infrastructure tasks, deployment issues, and containerization requirements."
    }
}

# Agent template for Claude
AGENT_TEMPLATE = """# {name}

## Role
{role}

## Description
{description}

## Category
{category}

## Priority
{priority}

## Capabilities
{capabilities}

## Tools Access
{tools}

## Specializations
{specializations}

## Usage Guidelines
{guidelines}

## Example Usage
```python
# To activate this agent:
mcp__dhafnck_mcp_http__call_agent(name_agent="{agent_id}")

# The agent will then handle tasks in its domain of expertise
```

## Integration Notes
This agent integrates with the DhafnckMCP system and can be called via the MCP tools interface. It has access to the specified tools and follows the project's established patterns and conventions.

## Metadata
- **Agent ID**: `{agent_id}`
- **Type**: {agent_type}
- **Category**: {category}
- **Priority**: {priority}
- **Last Updated**: {updated_at}

---
*Auto-generated from DhafnckMCP agent definitions*
"""

class AgentGenerator:
    """Generate Claude agent files from definitions"""
    
    def __init__(self, claude_dir: str = DEFAULT_CLAUDE_DIR):
        self.claude_dir = Path(claude_dir)
        
    def generate_agent_file(self, agent_id: str, agent_data: Dict[str, Any]) -> str:
        """Generate markdown content for an agent"""
        # Format the agent details
        content = AGENT_TEMPLATE.format(
            name=agent_data.get("name", "Unknown Agent"),
            role=agent_data.get("role", "Specialized AI Agent"),
            description=agent_data.get("description", "No description available"),
            category=agent_data.get("category", "general"),
            priority=agent_data.get("priority", "normal"),
            capabilities=self._format_list(agent_data.get("capabilities", [])),
            tools=self._format_list(agent_data.get("tools", ["All available MCP tools"])),
            specializations=self._format_list(agent_data.get("specializations", [])),
            guidelines=agent_data.get("guidelines", "Follow standard agent protocols"),
            agent_id=agent_id,
            agent_type=agent_data.get("type", "specialist"),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return content
    
    def _format_list(self, items: List[Any]) -> str:
        """Format a list for markdown"""
        if not items:
            return "- None specified"
        return "\n".join(f"- {item}" for item in items)
    
    def save_agent_file(self, agent_id: str, agent_data: Dict[str, Any]) -> Path:
        """Save agent configuration to file"""
        # Create directory if it doesn't exist
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from agent ID
        filename = f"{agent_id.replace('@', '').replace(' ', '_').lower()}.md"
        filepath = self.claude_dir / filename
        
        # Generate and save content
        content = self.generate_agent_file(agent_id, agent_data)
        filepath.write_text(content)
        
        return filepath
    
    def generate_all_agents(self, filter_category: str = None) -> Dict[str, Any]:
        """Generate all agent files"""
        results = {
            "generated": [],
            "failed": [],
            "total": 0
        }
        
        agents_to_generate = AGENT_DEFINITIONS.items()
        if filter_category:
            agents_to_generate = [
                (id, data) for id, data in agents_to_generate 
                if data.get("category") == filter_category
            ]
        
        results["total"] = len(list(agents_to_generate))
        
        for agent_id, agent_data in AGENT_DEFINITIONS.items():
            try:
                # Apply category filter if specified
                if filter_category and agent_data.get("category") != filter_category:
                    continue
                
                filepath = self.save_agent_file(agent_id, agent_data)
                results["generated"].append({
                    "agent_id": agent_id,
                    "name": agent_data.get("name"),
                    "file": str(filepath)
                })
                print(f"✓ Generated: {agent_data.get('name', 'Unknown')} -> {filepath}")
            except Exception as e:
                results["failed"].append({
                    "agent_id": agent_id,
                    "error": str(e)
                })
                print(f"✗ Failed: {agent_data.get('name', 'Unknown')} - {e}")
        
        return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate Claude agent files from predefined configurations"
    )
    parser.add_argument(
        "--claude-dir",
        default=DEFAULT_CLAUDE_DIR,
        help="Claude agents directory (default: .claude/agents)"
    )
    parser.add_argument(
        "--category",
        help="Filter agents by category (e.g., development, frontend, security)"
    )
    parser.add_argument(
        "--agent-id",
        help="Generate specific agent by ID (e.g., coding-agent)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing agent files before generating"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available agents without generating files"
    )
    
    args = parser.parse_args()
    
    # List agents if requested
    if args.list:
        print("Available Agents:")
        print("="*60)
        for agent_id, agent_data in AGENT_DEFINITIONS.items():
            print(f"{agent_id:<30} {agent_data.get('name', 'Unknown')}")
            print(f"  Category: {agent_data.get('category', 'N/A')}")
            print(f"  Role: {agent_data.get('role', 'N/A')}")
            print()
        return
    
    # Create generator
    generator = AgentGenerator(args.claude_dir)
    
    # Clean directory if requested
    if args.clean:
        print(f"Cleaning {args.claude_dir}...")
        for file in Path(args.claude_dir).glob("*.md"):
            if file.name not in ["claude-code-troubleshooter.md", "coding-agent.md"]:  # Preserve existing special agents
                file.unlink()
                print(f"  Removed: {file.name}")
    
    # Generate specific agent or all
    if args.agent_id:
        if args.agent_id not in AGENT_DEFINITIONS:
            print(f"Error: Agent '{args.agent_id}' not found")
            print("Use --list to see available agents")
            return
        
        print(f"Generating agent: {args.agent_id}")
        agent_data = AGENT_DEFINITIONS[args.agent_id]
        filepath = generator.save_agent_file(args.agent_id, agent_data)
        print(f"✓ Saved: {filepath}")
    else:
        # Generate all agents
        print(f"Generating agent files in {args.claude_dir}")
        print("="*60)
        results = generator.generate_all_agents(filter_category=args.category)
        
        # Print summary
        print("\n" + "="*60)
        print(f"Generation Summary:")
        print(f"  Total agents: {len(AGENT_DEFINITIONS)}")
        print(f"  Successfully generated: {len(results['generated'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        if results['failed']:
            print("\nFailed agents:")
            for failure in results['failed']:
                print(f"  - {failure['agent_id']}: {failure['error']}")
        
        print(f"\nAgent files are ready in: {Path(args.claude_dir).absolute()}")

if __name__ == "__main__":
    main()