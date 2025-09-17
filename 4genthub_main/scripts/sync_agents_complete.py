#!/usr/bin/env python3
"""
Complete Agent Sync Script - All 60+ Agents
============================================
This script generates .claude/agents/*.md files for ALL agents in the 4genthub system.
Works without server dependency.
"""

from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Default configuration
DEFAULT_CLAUDE_DIR = ".claude/agents"

# Complete agent definitions - 60+ specialized agents
AGENT_DEFINITIONS = {
    # Orchestrators and Coordinators
    "master-orchestrator-agent": {
        "name": "Uber Orchestrator Agent",
        "role": "Master Coordinator and Decision Maker",
        "description": "The highest-level orchestrator that coordinates all other agents and makes strategic decisions",
        "category": "orchestration",
        "type": "orchestrator",
        "priority": "critical",
        "capabilities": ["Multi-agent coordination", "Strategic planning", "Resource allocation", "Workflow orchestration"],
        "tools": ["All MCP tools available"],
        "specializations": ["Complex project management", "Cross-functional coordination", "Agent delegation"]
    },
    "@development_orchestrator_agent": {
        "name": "Development Orchestrator Agent",
        "role": "Development Team Coordinator",
        "description": "Coordinates all development-related agents and activities",
        "category": "orchestration",
        "type": "orchestrator",
        "priority": "high",
        "capabilities": ["Development workflow management", "Code review coordination", "Sprint planning"],
        "tools": ["All development tools"],
        "specializations": ["Agile development", "CI/CD coordination", "Development best practices"]
    },
    "test-orchestrator-agent": {
        "name": "Test Orchestrator Agent",
        "role": "Testing Strategy and Execution Coordinator",
        "description": "Manages comprehensive testing strategies and coordinates test execution",
        "category": "quality",
        "type": "orchestrator",
        "priority": "high",
        "capabilities": ["Test strategy design", "Test suite orchestration", "Coverage analysis"],
        "tools": ["Bash", "Write", "Read", "Edit", "TodoWrite"],
        "specializations": ["Pytest", "Jest", "E2E testing", "Performance testing"]
    },
    "marketing-strategy-orchestrator-agent": {
        "name": "Marketing Strategy Orchestrator Agent",
        "role": "Marketing Campaign Coordinator",
        "description": "Orchestrates marketing strategies and campaign execution",
        "category": "business",
        "type": "orchestrator",
        "priority": "normal",
        "capabilities": ["Campaign planning", "Content strategy", "Market analysis"],
        "tools": ["Documentation tools", "Analytics tools"],
        "specializations": ["Digital marketing", "Content marketing", "Growth strategies"]
    },
    
    # Core Development Agents
    "coding-agent": {
        "name": "Coding Agent",
        "role": "Software Development Specialist",
        "description": "Specialized in writing, refactoring, and implementing code across various languages",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Code implementation", "API development", "Algorithm optimization"],
        "tools": ["Edit", "Write", "Read", "MultiEdit", "Bash", "Grep", "Glob"],
        "specializations": ["Python", "TypeScript", "React", "FastAPI", "DDD architecture"]
    },
    "debugger-agent": {
        "name": "Debugger Agent",
        "role": "Bug Detection and Resolution Specialist",
        "description": "Expert in identifying, analyzing, and fixing bugs and errors",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Error analysis", "Performance debugging", "Memory leak detection"],
        "tools": ["Read", "Grep", "Bash", "Edit", "mcp__ide__getDiagnostics"],
        "specializations": ["Runtime errors", "Logic bugs", "Performance optimization"]
    },
    "code-reviewer-agent": {
        "name": "Code Reviewer Agent",
        "role": "Code Quality Specialist",
        "description": "Reviews code for quality, standards compliance, and best practices",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Code review", "Standards enforcement", "Best practices validation"],
        "tools": ["Read", "Grep", "Edit"],
        "specializations": ["Clean code", "SOLID principles", "Design patterns"]
    },
    "@backend_agent": {
        "name": "Backend Agent",
        "role": "Backend Development Specialist",
        "description": "Focused on server-side development and API design",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["API development", "Database integration", "Server optimization"],
        "tools": ["Edit", "Write", "Read", "Bash"],
        "specializations": ["FastAPI", "Node.js", "Database design", "Microservices"]
    },
    "@frontend_agent": {
        "name": "Frontend Agent",
        "role": "Frontend Development Specialist",
        "description": "Specializes in client-side development and user interfaces",
        "category": "frontend",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Component development", "State management", "UI optimization"],
        "tools": ["Edit", "Write", "Read", "WebFetch"],
        "specializations": ["React", "Vue", "Angular", "TypeScript"]
    },
    
    # Architecture and Design Agents
    "system-architect-agent": {
        "name": "System Architect Agent",
        "role": "System Architecture Specialist",
        "description": "Designs system architecture and high-level technical solutions",
        "category": "architecture",
        "type": "specialist",
        "priority": "critical",
        "capabilities": ["Architecture design", "System modeling", "Technology selection"],
        "tools": ["Documentation tools", "Diagramming tools"],
        "specializations": ["Microservices", "Cloud architecture", "Scalability patterns"]
    },
    "@code_architect_agent": {
        "name": "Code Architect Agent",
        "role": "Code Architecture Specialist",
        "description": "Designs code structure and architectural patterns",
        "category": "architecture",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Code structure design", "Pattern implementation", "Refactoring strategies"],
        "tools": ["Read", "Write", "Edit"],
        "specializations": ["DDD", "Clean architecture", "Design patterns"]
    },
    "@database_architect_agent": {
        "name": "Database Architect Agent",
        "role": "Database Design and Optimization Specialist",
        "description": "Expert in database design, query optimization, and data modeling",
        "category": "database",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Schema design", "Query optimization", "Data migration"],
        "tools": ["Bash", "Read", "Write", "Edit"],
        "specializations": ["PostgreSQL", "MongoDB", "Redis", "Database migrations"]
    },
    "@workflow_architect_agent": {
        "name": "Workflow Architect Agent",
        "role": "Workflow Design Specialist",
        "description": "Designs and optimizes business and technical workflows",
        "category": "architecture",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Workflow design", "Process optimization", "Automation planning"],
        "tools": ["Documentation tools", "TodoWrite"],
        "specializations": ["BPMN", "Workflow automation", "Process improvement"]
    },
    "@prd_architect_agent": {
        "name": "PRD Architect Agent",
        "role": "Product Requirements Specialist",
        "description": "Creates detailed product requirement documents and specifications",
        "category": "product",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Requirements gathering", "Specification writing", "User story creation"],
        "tools": ["Write", "Read", "Documentation tools"],
        "specializations": ["Product planning", "Feature specification", "Acceptance criteria"]
    },
    
    # UI/UX and Design Agents
    "@ui_designer_agent": {
        "name": "UI Designer Agent",
        "role": "User Interface and Experience Specialist",
        "description": "Focused on frontend development, UI/UX design, and user interaction",
        "category": "frontend",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Component design", "Responsive layouts", "Accessibility"],
        "tools": ["Edit", "Write", "Read", "WebFetch", "mcp__shadcn-ui-server__*"],
        "specializations": ["React", "Tailwind CSS", "Material-UI", "Mobile responsiveness"]
    },
    "@ui_designer_expert_shadcn_agent": {
        "name": "UI Designer Expert Shadcn Agent",
        "role": "Shadcn/UI Component Specialist",
        "description": "Expert in shadcn/ui component library and modern React patterns",
        "category": "frontend",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Shadcn component integration", "Theme customization", "Component composition"],
        "tools": ["mcp__shadcn-ui-server__*", "Edit", "Write"],
        "specializations": ["shadcn/ui", "Radix UI", "Tailwind CSS", "React hooks"]
    },
    "@ux_researcher_agent": {
        "name": "UX Researcher Agent",
        "role": "User Experience Research Specialist",
        "description": "Conducts user research and provides UX insights",
        "category": "design",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["User research", "Usability testing", "Persona development"],
        "tools": ["Documentation tools", "Analytics tools"],
        "specializations": ["User interviews", "A/B testing", "User journey mapping"]
    },
    "@design_qa_analyst_agent": {
        "name": "Design QA Analyst Agent",
        "role": "Design Quality Assurance Specialist",
        "description": "Ensures design consistency and quality across the application",
        "category": "design",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Design review", "Consistency checking", "Accessibility validation"],
        "tools": ["Read", "WebFetch"],
        "specializations": ["Design systems", "WCAG compliance", "Visual regression testing"]
    },
    
    # Testing and QA Agents
    "@qa_engineer": {
        "name": "QA Engineer Agent",
        "role": "Quality Assurance Specialist",
        "description": "Ensures software quality through comprehensive testing",
        "category": "quality",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Test planning", "Bug tracking", "Quality metrics"],
        "tools": ["Bash", "Read", "Write"],
        "specializations": ["Test automation", "Manual testing", "Test documentation"]
    },
    "@functional_tester_agent": {
        "name": "Functional Tester Agent",
        "role": "Functional Testing Specialist",
        "description": "Performs functional testing of features and workflows",
        "category": "quality",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Functional testing", "Feature validation", "Regression testing"],
        "tools": ["Bash", "Read", "Test tools"],
        "specializations": ["Black-box testing", "User acceptance testing", "Smoke testing"]
    },
    "@exploratory_tester_agent": {
        "name": "Exploratory Tester Agent",
        "role": "Exploratory Testing Specialist",
        "description": "Discovers issues through exploratory and ad-hoc testing",
        "category": "quality",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Exploratory testing", "Edge case discovery", "Usability testing"],
        "tools": ["Bash", "Read", "WebFetch"],
        "specializations": ["Ad-hoc testing", "Scenario-based testing", "Risk-based testing"]
    },
    "@integration_specialist_agent": {
        "name": "Integration Specialist Agent",
        "role": "Integration Testing Specialist",
        "description": "Tests system integrations and API interactions",
        "category": "quality",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Integration testing", "API testing", "Contract testing"],
        "tools": ["Bash", "Read", "API testing tools"],
        "specializations": ["REST APIs", "GraphQL", "Microservices testing"]
    },
    "performance-load-tester-agent": {
        "name": "Performance Load Tester Agent",
        "role": "Performance Testing Specialist",
        "description": "Conducts performance and load testing to ensure scalability",
        "category": "quality",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Load testing", "Stress testing", "Performance profiling"],
        "tools": ["Bash", "Performance tools"],
        "specializations": ["JMeter", "Locust", "Performance optimization"]
    },
    "@security_penetration_tester_agent": {
        "name": "Security Penetration Tester Agent",
        "role": "Penetration Testing Specialist",
        "description": "Performs security penetration testing and vulnerability assessment",
        "category": "security",
        "type": "specialist",
        "priority": "critical",
        "capabilities": ["Penetration testing", "Vulnerability scanning", "Security assessment"],
        "tools": ["Security tools", "Bash"],
        "specializations": ["OWASP testing", "Network security", "Application security"]
    },
    "uat-coordinator-agent": {
        "name": "UAT Coordinator Agent",
        "role": "User Acceptance Testing Coordinator",
        "description": "Coordinates user acceptance testing with stakeholders",
        "category": "quality",
        "type": "coordinator",
        "priority": "normal",
        "capabilities": ["UAT planning", "Stakeholder coordination", "Test scenario creation"],
        "tools": ["Documentation tools", "Communication tools"],
        "specializations": ["UAT processes", "Stakeholder management", "Test documentation"]
    },
    
    # Security and Compliance Agents
    "security-auditor-agent": {
        "name": "Security Auditor Agent",
        "role": "Security Analysis and Compliance Specialist",
        "description": "Performs security audits and ensures compliance",
        "category": "security",
        "type": "specialist",
        "priority": "critical",
        "capabilities": ["Security auditing", "Compliance checking", "Risk assessment"],
        "tools": ["Read", "Grep", "Bash", "mcp__4genthub_http__manage_compliance"],
        "specializations": ["OWASP", "GDPR", "Security best practices"]
    },
    "@security_agent": {
        "name": "Security Agent",
        "role": "General Security Specialist",
        "description": "Handles general security concerns and implementations",
        "category": "security",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Security implementation", "Authentication", "Authorization"],
        "tools": ["Read", "Write", "Edit"],
        "specializations": ["JWT", "OAuth", "Encryption"]
    },
    
    # DevOps and Infrastructure Agents
    "devops-agent": {
        "name": "DevOps Agent",
        "role": "DevOps and Infrastructure Specialist",
        "description": "Manages infrastructure, deployment, and CI/CD pipelines",
        "category": "infrastructure",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["CI/CD setup", "Container management", "Infrastructure automation"],
        "tools": ["Bash", "Docker tools", "Kubernetes tools"],
        "specializations": ["Docker", "Kubernetes", "GitHub Actions", "Terraform"]
    },
    "@devops_engineer_agent": {
        "name": "DevOps Engineer Agent",
        "role": "DevOps Engineering Specialist",
        "description": "Focuses on engineering aspects of DevOps practices",
        "category": "infrastructure",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Pipeline engineering", "Infrastructure as Code", "Monitoring setup"],
        "tools": ["Bash", "Write", "Read", "Edit"],
        "specializations": ["Jenkins", "GitLab CI", "AWS", "Azure"]
    },
    "health-monitor-agent": {
        "name": "Health Monitor Agent",
        "role": "System Health Monitoring Specialist",
        "description": "Monitors system health and performance metrics",
        "category": "monitoring",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Health monitoring", "Alert configuration", "Performance tracking"],
        "tools": ["Monitoring tools", "Bash"],
        "specializations": ["Prometheus", "Grafana", "ELK stack", "APM tools"]
    },
    "@system_health_agent": {
        "name": "System Health Agent",
        "role": "System Health Check Specialist",
        "description": "Performs system health checks and diagnostics",
        "category": "monitoring",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Health checks", "Diagnostics", "System analysis"],
        "tools": ["Bash", "Read"],
        "specializations": ["System diagnostics", "Resource monitoring", "Log analysis"]
    },
    
    # Planning and Management Agents
    "task-planning-agent": {
        "name": "Task Planning Agent",
        "role": "Task Breakdown and Planning Specialist",
        "description": "Breaks down complex tasks into manageable subtasks",
        "category": "planning",
        "type": "specialist",
        "priority": "high",
        "capabilities": ["Task decomposition", "Timeline estimation", "Dependency analysis"],
        "tools": ["TodoWrite", "mcp__4genthub_http__manage_task"],
        "specializations": ["Agile planning", "Sprint planning", "Milestone tracking"]
    },
    "@task_deep_manager_agent": {
        "name": "Task Deep Manager Agent",
        "role": "Deep Task Analysis Specialist",
        "description": "Performs deep analysis and management of complex tasks",
        "category": "planning",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Deep task analysis", "Complexity assessment", "Risk identification"],
        "tools": ["TodoWrite", "Analysis tools"],
        "specializations": ["Complex project management", "Risk management", "Resource planning"]
    },
    "@campaign_manager_agent": {
        "name": "Campaign Manager Agent",
        "role": "Campaign Management Specialist",
        "description": "Manages and coordinates campaigns and initiatives",
        "category": "business",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Campaign management", "Timeline coordination", "Resource allocation"],
        "tools": ["TodoWrite", "Documentation tools"],
        "specializations": ["Marketing campaigns", "Product launches", "Event management"]
    },
    
    # Documentation and Research Agents
    "documentation-agent": {
        "name": "Documentation Agent",
        "role": "Technical Documentation Specialist",
        "description": "Creates and maintains comprehensive documentation",
        "category": "documentation",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["API documentation", "User guides", "Technical specs"],
        "tools": ["Write", "Read", "Edit", "Glob"],
        "specializations": ["Markdown", "API docs", "Architecture docs"]
    },
    "deep-research-agent": {
        "name": "Deep Research Agent",
        "role": "Technology Research Specialist",
        "description": "Conducts deep research on technologies and solutions",
        "category": "research",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Technology research", "Solution analysis", "Best practices research"],
        "tools": ["WebFetch", "Read", "Documentation tools"],
        "specializations": ["Technology evaluation", "Market research", "Competitive analysis"]
    },
    "@mcp_researcher_agent": {
        "name": "MCP Researcher Agent",
        "role": "MCP System Research Specialist",
        "description": "Specializes in researching MCP-related technologies and patterns",
        "category": "research",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["MCP research", "Tool analysis", "Integration patterns"],
        "tools": ["Read", "WebFetch", "Documentation tools"],
        "specializations": ["MCP tools", "Agent systems", "Integration patterns"]
    },
    "technology-advisor-agent": {
        "name": "Technology Advisor Agent",
        "role": "Technology Advisory Specialist",
        "description": "Provides technology recommendations and guidance",
        "category": "advisory",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Technology selection", "Architecture advice", "Best practices guidance"],
        "tools": ["Documentation tools", "Research tools"],
        "specializations": ["Technology trends", "Architecture patterns", "Tool selection"]
    },
    
    # Specialized Testing Agents
    "@test_agent": {
        "name": "Test Agent",
        "role": "General Testing Specialist",
        "description": "General purpose testing agent for various testing needs",
        "category": "quality",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["General testing", "Test execution", "Result validation"],
        "tools": ["Bash", "Read", "Test tools"],
        "specializations": ["Unit testing", "Integration testing", "Test automation"]
    },
    "@testing_agent": {
        "name": "Testing Agent",
        "role": "Testing Execution Specialist",
        "description": "Executes various types of tests and validates results",
        "category": "quality",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Test execution", "Result analysis", "Test reporting"],
        "tools": ["Bash", "Read", "Write"],
        "specializations": ["Test frameworks", "Test reporting", "Test metrics"]
    },
    
    # Plugin and Extension Agents
    "@plugin_manager": {
        "name": "Plugin Manager Agent",
        "role": "Plugin Management Specialist",
        "description": "Manages plugins, extensions, and integrations",
        "category": "integration",
        "type": "specialist",
        "priority": "normal",
        "capabilities": ["Plugin management", "Integration setup", "Extension configuration"],
        "tools": ["Bash", "Read", "Write", "Edit"],
        "specializations": ["Plugin architecture", "API integrations", "Extension development"]
    },
    
    # Enhanced Orchestrators
    "@enhanced_orchestrator": {
        "name": "Enhanced Orchestrator Agent",
        "role": "Enhanced Multi-Domain Orchestrator",
        "description": "Advanced orchestrator with enhanced capabilities across multiple domains",
        "category": "orchestration",
        "type": "orchestrator",
        "priority": "high",
        "capabilities": ["Advanced coordination", "Cross-domain orchestration", "Complex workflow management"],
        "tools": ["All MCP tools"],
        "specializations": ["Multi-domain coordination", "Advanced workflows", "System optimization"]
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

## Type
{agent_type}

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
mcp__4genthub_http__call_agent(name_agent="{agent_id}")

# The agent will then handle tasks in its domain of expertise
```

## Integration Notes
This agent integrates with the 4genthub system and can be called via the MCP tools interface. 
It has access to the specified tools and follows the project's established patterns and conventions.

## Collaboration
This agent can work with other specialized agents for complex tasks. Common collaborations:
- Works with master-orchestrator-agent for coordination
- Can delegate to more specialized agents when needed
- Participates in multi-agent workflows

## Metadata
- **Agent ID**: `{agent_id}`
- **Type**: {agent_type}
- **Category**: {category}
- **Priority**: {priority}
- **Total Agents in System**: 60+
- **Last Updated**: {updated_at}

---
*Auto-generated from 4genthub complete agent registry*
"""

class AgentGenerator:
    """Generate Claude agent files from definitions"""
    
    def __init__(self, claude_dir: str = DEFAULT_CLAUDE_DIR):
        self.claude_dir = Path(claude_dir)
        
    def generate_agent_file(self, agent_id: str, agent_data: Dict[str, Any]) -> str:
        """Generate markdown content for an agent"""
        # Default guidelines based on category
        default_guidelines = {
            "orchestration": "Use for coordinating multiple agents and complex workflows",
            "development": "Deploy for coding, implementation, and development tasks",
            "architecture": "Use for system design and architectural decisions",
            "frontend": "Deploy for UI/UX and frontend development tasks",
            "quality": "Use for testing, QA, and quality assurance tasks",
            "security": "Deploy for security reviews and vulnerability assessments",
            "infrastructure": "Use for DevOps, deployment, and infrastructure tasks",
            "planning": "Deploy for task planning and project management",
            "documentation": "Use for creating and maintaining documentation",
            "research": "Deploy for research and technology evaluation",
            "business": "Use for business-related tasks and strategies",
            "monitoring": "Deploy for system monitoring and health checks",
            "database": "Use for database design and optimization",
            "design": "Deploy for design and UX tasks",
            "product": "Use for product planning and requirements",
            "integration": "Deploy for integrations and plugin management",
            "advisory": "Use for technology advice and recommendations"
        }
        
        category = agent_data.get("category", "general")
        guidelines = agent_data.get("guidelines", default_guidelines.get(category, "Follow standard agent protocols"))
        
        # Format the agent details
        content = AGENT_TEMPLATE.format(
            name=agent_data.get("name", "Unknown Agent"),
            role=agent_data.get("role", "Specialized AI Agent"),
            description=agent_data.get("description", "No description available"),
            category=category,
            agent_type=agent_data.get("type", "specialist"),
            priority=agent_data.get("priority", "normal"),
            capabilities=self._format_list(agent_data.get("capabilities", [])),
            tools=self._format_list(agent_data.get("tools", ["All available MCP tools"])),
            specializations=self._format_list(agent_data.get("specializations", [])),
            guidelines=guidelines,
            agent_id=agent_id,
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
            "total": 0,
            "categories": {}
        }
        
        # Count agents by category
        for agent_id, agent_data in AGENT_DEFINITIONS.items():
            category = agent_data.get("category", "general")
            if category not in results["categories"]:
                results["categories"][category] = 0
            results["categories"][category] += 1
        
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
                    "category": agent_data.get("category"),
                    "file": str(filepath)
                })
                print(f"✓ Generated: {agent_data.get('name', 'Unknown')} [{agent_data.get('category')}]")
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
        description="Generate Claude agent files for ALL 60+ 4genthub agents"
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
    parser.add_argument(
        "--categories",
        action="store_true",
        help="List all categories and agent counts"
    )
    
    args = parser.parse_args()
    
    # List categories if requested
    if args.categories:
        print("Agent Categories:")
        print("="*60)
        categories = {}
        for agent_id, agent_data in AGENT_DEFINITIONS.items():
            category = agent_data.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(agent_data.get("name"))
        
        for category in sorted(categories.keys()):
            print(f"\n{category.upper()} ({len(categories[category])} agents):")
            for agent_name in sorted(categories[category]):
                print(f"  - {agent_name}")
        
        print(f"\nTotal: {len(AGENT_DEFINITIONS)} agents across {len(categories)} categories")
        return
    
    # List agents if requested
    if args.list:
        print("Available Agents (60+ Total):")
        print("="*60)
        
        # Group by category for better readability
        by_category = {}
        for agent_id, agent_data in AGENT_DEFINITIONS.items():
            category = agent_data.get("category", "general")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((agent_id, agent_data))
        
        for category in sorted(by_category.keys()):
            print(f"\n{category.upper()} AGENTS:")
            for agent_id, agent_data in sorted(by_category[category], key=lambda x: x[0]):
                print(f"  {agent_id:<40} {agent_data.get('name', 'Unknown')}")
                print(f"    Role: {agent_data.get('role', 'N/A')}")
        
        print(f"\nTotal: {len(AGENT_DEFINITIONS)} agents")
        return
    
    # Create generator
    generator = AgentGenerator(args.claude_dir)
    
    # Clean directory if requested
    if args.clean:
        print(f"Cleaning {args.claude_dir}...")
        for file in Path(args.claude_dir).glob("*.md"):
            # Preserve specific existing agents if needed
            if file.name not in ["claude-code-troubleshooter.md"]:
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
        print(f"Generating ALL {len(AGENT_DEFINITIONS)} agent files in {args.claude_dir}")
        print("="*60)
        results = generator.generate_all_agents(filter_category=args.category)
        
        # Print summary
        print("\n" + "="*60)
        print(f"Generation Summary:")
        print(f"  Total agents defined: {len(AGENT_DEFINITIONS)}")
        print(f"  Successfully generated: {len(results['generated'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        print(f"\nAgents by Category:")
        for category, count in sorted(results['categories'].items()):
            print(f"  {category}: {count} agents")
        
        if results['failed']:
            print("\nFailed agents:")
            for failure in results['failed']:
                print(f"  - {failure['agent_id']}: {failure['error']}")
        
        print(f"\nAll {len(results['generated'])} agent files are ready in: {Path(args.claude_dir).absolute()}")

if __name__ == "__main__":
    main()