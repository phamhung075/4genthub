"""Agent Metadata Routes - Expose agent information for external clients"""

from typing import Dict, Any, List
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import logging
from .agent_registry import get_agent_registry

logger = logging.getLogger(__name__)

# Legacy predefined agent metadata - kept for backward compatibility
# Now using AgentRegistry for dynamic management
AGENT_METADATA = [
    {
        "id": "@uber_orchestrator_agent",
        "name": "Uber Orchestrator Agent",
        "call_name": "@uber_orchestrator_agent",
        "role": "Master Coordinator and Decision Maker",
        "description": "The highest-level orchestrator that coordinates all other agents and makes strategic decisions",
        "category": "orchestration",
        "type": "orchestrator",
        "priority": "critical",
        "capabilities": [
            "Multi-agent coordination",
            "Strategic planning",
            "Resource allocation",
            "Workflow orchestration",
            "Decision making"
        ],
        "tools": ["All MCP tools"],
        "specializations": [
            "Complex project management",
            "Cross-functional coordination",
            "System-wide optimization",
            "Agent delegation"
        ],
        "guidelines": "Use for high-level coordination and when multiple agents need to work together"
    },
    {
        "id": "@coding_agent",
        "name": "Coding Agent",
        "call_name": "@coding_agent",
        "role": "Software Development Specialist",
        "description": "Specialized in writing, refactoring, and implementing code across various languages and frameworks",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Code implementation",
            "Refactoring",
            "API development",
            "Database design",
            "Algorithm optimization"
        ],
        "tools": ["Code editing tools", "File management", "Git operations"],
        "specializations": [
            "Python development",
            "TypeScript/JavaScript",
            "React components",
            "FastAPI/FastMCP",
            "DDD architecture"
        ],
        "guidelines": "Use for all coding and implementation tasks"
    },
    {
        "id": "@debugger_agent",
        "name": "Debugger Agent",
        "call_name": "@debugger_agent",
        "role": "Bug Detection and Resolution Specialist",
        "description": "Expert in identifying, analyzing, and fixing bugs and errors in code",
        "category": "development",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Error analysis",
            "Stack trace interpretation",
            "Performance debugging",
            "Memory leak detection",
            "Test failure analysis"
        ],
        "tools": ["Debugging tools", "Log analysis", "Test runners"],
        "specializations": [
            "Runtime error resolution",
            "Logic bug fixes",
            "Performance optimization",
            "Test debugging"
        ],
        "guidelines": "Use when encountering errors, test failures, or unexpected behavior"
    },
    {
        "id": "@test_orchestrator_agent",
        "name": "Test Orchestrator Agent",
        "call_name": "@test_orchestrator_agent",
        "role": "Testing Strategy and Execution Coordinator",
        "description": "Manages comprehensive testing strategies and coordinates test execution",
        "category": "quality",
        "type": "orchestrator",
        "priority": "high",
        "capabilities": [
            "Test strategy design",
            "Test suite orchestration",
            "Coverage analysis",
            "Test automation",
            "CI/CD integration"
        ],
        "tools": ["Test frameworks", "Coverage tools", "CI/CD tools"],
        "specializations": [
            "Unit testing",
            "Integration testing",
            "E2E testing",
            "Performance testing",
            "Test automation"
        ],
        "guidelines": "Use for designing and executing comprehensive test strategies"
    },
    {
        "id": "@ui_designer_agent",
        "name": "UI Designer Agent",
        "call_name": "@ui_designer_agent",
        "role": "User Interface and Experience Specialist",
        "description": "Focused on frontend development, UI/UX design, and user interaction",
        "category": "frontend",
        "type": "specialist",
        "priority": "normal",
        "capabilities": [
            "Component design",
            "Responsive layouts",
            "State management",
            "User interaction flows",
            "Accessibility"
        ],
        "tools": ["React tools", "CSS frameworks", "Component libraries"],
        "specializations": [
            "React development",
            "TypeScript components",
            "Tailwind CSS",
            "Material-UI/shadcn",
            "Mobile responsiveness"
        ],
        "guidelines": "Use for frontend development and UI/UX improvements"
    },
    {
        "id": "@documentation_agent",
        "name": "Documentation Agent",
        "call_name": "@documentation_agent",
        "role": "Technical Documentation Specialist",
        "description": "Creates and maintains comprehensive documentation",
        "category": "documentation",
        "type": "specialist",
        "priority": "normal",
        "capabilities": [
            "API documentation",
            "User guides",
            "Technical specifications",
            "README creation",
            "Code comments"
        ],
        "tools": ["Markdown tools", "Documentation generators"],
        "specializations": [
            "API documentation",
            "Architecture docs",
            "User manuals",
            "Migration guides",
            "Best practices"
        ],
        "guidelines": "Use for creating or updating documentation"
    },
    {
        "id": "@task_planning_agent",
        "name": "Task Planning Agent",
        "call_name": "@task_planning_agent",
        "role": "Task Breakdown and Planning Specialist",
        "description": "Breaks down complex tasks into manageable subtasks and creates execution plans",
        "category": "planning",
        "type": "specialist",
        "priority": "high",
        "capabilities": [
            "Task decomposition",
            "Dependency analysis",
            "Timeline estimation",
            "Resource planning",
            "Risk assessment"
        ],
        "tools": ["Task management tools", "Planning tools"],
        "specializations": [
            "Agile planning",
            "Sprint planning",
            "Milestone tracking",
            "Dependency management"
        ],
        "guidelines": "Use at the beginning of complex projects or features"
    },
    {
        "id": "@security_auditor_agent",
        "name": "Security Auditor Agent",
        "call_name": "@security_auditor_agent",
        "role": "Security Analysis and Compliance Specialist",
        "description": "Performs security audits, vulnerability assessments, and ensures compliance",
        "category": "security",
        "type": "specialist",
        "priority": "critical",
        "capabilities": [
            "Vulnerability scanning",
            "Security best practices",
            "Authentication/authorization",
            "Data protection",
            "Compliance checking"
        ],
        "tools": ["Security scanners", "Audit tools"],
        "specializations": [
            "OWASP compliance",
            "JWT security",
            "SQL injection prevention",
            "XSS protection",
            "Security headers"
        ],
        "guidelines": "Use for security reviews and vulnerability assessments"
    }
]

async def get_agent_metadata(request):
    """Get metadata for all available agents"""
    try:
        # Use the agent registry for dynamic agent management
        registry = get_agent_registry()
        agents = registry.list_agents()
        
        # Fallback to static metadata if registry is empty
        if not agents:
            agents = AGENT_METADATA
            
        return JSONResponse({
            "success": True,
            "agents": agents,
            "total": len(agents),
            "source": "registry" if agents else "static"
        })
    except Exception as e:
        logger.error(f"Error fetching agent metadata: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

async def get_agent_by_id(request):
    """Get metadata for a specific agent"""
    agent_id = request.path_params.get("agent_id")
    
    try:
        # Find agent by ID
        agent = next((a for a in AGENT_METADATA if a["id"] == agent_id), None)
        
        if agent:
            return JSONResponse({
                "success": True,
                "agent": agent
            })
        else:
            return JSONResponse({
                "success": False,
                "error": f"Agent '{agent_id}' not found"
            }, status_code=404)
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

async def get_agents_by_category(request):
    """Get agents filtered by category"""
    category = request.path_params.get("category")
    
    try:
        # Filter agents by category
        agents = [a for a in AGENT_METADATA if a.get("category") == category]
        
        return JSONResponse({
            "success": True,
            "category": category,
            "agents": agents,
            "total": len(agents)
        })
    except Exception as e:
        logger.error(f"Error fetching agents by category {category}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

def get_agent_categories():
    """Get all unique agent categories"""
    categories = list(set(agent.get("category", "uncategorized") for agent in AGENT_METADATA))
    return sorted(categories)

async def list_agent_categories(request):
    """List all available agent categories"""
    try:
        categories = get_agent_categories()
        return JSONResponse({
            "success": True,
            "categories": categories,
            "total": len(categories)
        })
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Routes to be added to the main application
agent_metadata_routes = [
    Route("/api/agents/metadata", get_agent_metadata, methods=["GET"]),
    Route("/api/agents/metadata/{agent_id}", get_agent_by_id, methods=["GET"]),
    Route("/api/agents/category/{category}", get_agents_by_category, methods=["GET"]),
    Route("/api/agents/categories", list_agent_categories, methods=["GET"]),
]

def register_agent_metadata_routes(app: Starlette):
    """Register agent metadata routes with the application"""
    for route in agent_metadata_routes:
        app.routes.append(route)
    logger.info("Agent metadata routes registered")