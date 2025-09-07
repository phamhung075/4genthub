"""Claude Agent Generation Facade

This facade handles the generation of Claude Code agent configuration files
following DDD principles.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class ClaudeAgentFacade:
    """Facade for generating Claude Code agent configuration files."""
    
    # Agent templates for different types
    AGENT_TEMPLATES = {
        "code-reviewer": {
            "name": "{name}",
            "description": "Expert code reviewer for {language} projects",
            "expertise": [
                "Code quality analysis",
                "Performance optimization",
                "Security vulnerability detection",
                "Best practices enforcement"
            ],
            "tools": ["Read", "Grep", "Task"],
            "prompts": {
                "initial": "You are an expert code reviewer specializing in {language}. Focus on code quality, performance, and security.",
                "review_checklist": [
                    "Check for code style consistency",
                    "Identify potential bugs",
                    "Suggest performance improvements",
                    "Look for security vulnerabilities"
                ]
            }
        },
        "test-writer": {
            "name": "{name}",
            "description": "Automated test writer for comprehensive test coverage",
            "expertise": [
                "Unit test creation",
                "Integration test design",
                "Test coverage analysis",
                "Test-driven development"
            ],
            "tools": ["Read", "Write", "Edit", "Bash"],
            "prompts": {
                "initial": "You are a test automation expert. Create comprehensive tests with high coverage.",
                "test_types": ["unit", "integration", "e2e"]
            }
        },
        "documentation-writer": {
            "name": "{name}",
            "description": "Technical documentation specialist",
            "expertise": [
                "API documentation",
                "User guides",
                "Architecture documentation",
                "Code comments"
            ],
            "tools": ["Read", "Write", "Grep"],
            "prompts": {
                "initial": "You are a technical documentation expert. Create clear, comprehensive documentation.",
                "doc_sections": ["Overview", "Installation", "Usage", "API Reference", "Examples"]
            }
        },
        "debugger": {
            "name": "{name}",
            "description": "Expert debugger and problem solver",
            "expertise": [
                "Bug diagnosis",
                "Root cause analysis",
                "Performance profiling",
                "Error pattern recognition"
            ],
            "tools": ["Read", "Edit", "Bash", "Grep"],
            "prompts": {
                "initial": "You are an expert debugger. Systematically identify and fix issues.",
                "debug_process": [
                    "Reproduce the issue",
                    "Identify root cause",
                    "Implement fix",
                    "Verify solution"
                ]
            }
        },
        "architect": {
            "name": "{name}",
            "description": "System architecture and design expert",
            "expertise": [
                "System design",
                "Design patterns",
                "Architecture decisions",
                "Scalability planning"
            ],
            "tools": ["Read", "Write", "Task"],
            "prompts": {
                "initial": "You are a system architect. Design scalable, maintainable solutions.",
                "design_principles": ["SOLID", "DRY", "KISS", "YAGNI"]
            }
        },
        "custom": {
            "name": "{name}",
            "description": "{description}",
            "expertise": [],
            "tools": ["Read", "Write", "Edit", "Bash"],
            "prompts": {
                "initial": "{initial_prompt}"
            }
        }
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize the Claude Agent Facade.
        
        Args:
            project_root: Optional project root path. If not provided, uses current working directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.agents_dir = self.project_root / ".claude" / "agents"
        
    def create_agent(
        self,
        name: str,
        agent_type: str = "custom",
        description: Optional[str] = None,
        expertise: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        initial_prompt: Optional[str] = None,
        language: Optional[str] = "Python",
        additional_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new Claude Code agent configuration file.
        
        Args:
            name: Name of the agent (will be used as filename)
            agent_type: Type of agent template to use
            description: Custom description for the agent
            expertise: List of expertise areas
            tools: List of tools the agent should use
            initial_prompt: Custom initial prompt
            language: Programming language for code-related agents
            additional_config: Additional configuration options
            
        Returns:
            Dict containing the result of the operation
        """
        try:
            # Ensure agents directory exists
            self.agents_dir.mkdir(parents=True, exist_ok=True)
            
            # Get template
            if agent_type not in self.AGENT_TEMPLATES:
                return {
                    "success": False,
                    "error": f"Unknown agent type: {agent_type}. Available types: {list(self.AGENT_TEMPLATES.keys())}"
                }
            
            template = self.AGENT_TEMPLATES[agent_type].copy()
            
            # Format template with provided values
            agent_config = {
                "name": template["name"].format(name=name),
                "description": description or template["description"].format(
                    name=name, 
                    language=language, 
                    description=description or f"Custom {agent_type} agent"
                ),
                "expertise": expertise or template.get("expertise", []),
                "tools": tools or template.get("tools", []),
                "prompts": template.get("prompts", {}),
                "created_at": datetime.now().isoformat(),
                "agent_type": agent_type,
                "language": language if agent_type in ["code-reviewer"] else None
            }
            
            # Update prompts with custom values
            if initial_prompt and "initial" in agent_config["prompts"]:
                agent_config["prompts"]["initial"] = initial_prompt.format(
                    language=language,
                    name=name,
                    initial_prompt=initial_prompt
                )
            elif "initial" in agent_config["prompts"] and "{" in str(agent_config["prompts"]["initial"]):
                agent_config["prompts"]["initial"] = agent_config["prompts"]["initial"].format(
                    language=language,
                    name=name,
                    initial_prompt=initial_prompt or ""
                )
            
            # Add additional configuration
            if additional_config:
                agent_config.update(additional_config)
            
            # Generate markdown content
            md_content = self._generate_markdown(agent_config)
            
            # Write to file
            agent_file = self.agents_dir / f"{name}.md"
            agent_file.write_text(md_content)
            
            return {
                "success": True,
                "message": f"Agent '{name}' created successfully",
                "path": str(agent_file),
                "config": agent_config
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create agent: {str(e)}"
            }
    
    def list_agents(self) -> Dict[str, Any]:
        """List all available Claude Code agents.
        
        Returns:
            Dict containing list of agents
        """
        try:
            if not self.agents_dir.exists():
                return {
                    "success": True,
                    "agents": [],
                    "message": "No agents directory found"
                }
            
            agents = []
            for agent_file in self.agents_dir.glob("*.md"):
                agents.append({
                    "name": agent_file.stem,
                    "path": str(agent_file),
                    "modified": datetime.fromtimestamp(agent_file.stat().st_mtime).isoformat()
                })
            
            return {
                "success": True,
                "agents": agents,
                "count": len(agents)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list agents: {str(e)}"
            }
    
    def get_agent(self, name: str) -> Dict[str, Any]:
        """Get a specific agent configuration.
        
        Args:
            name: Name of the agent
            
        Returns:
            Dict containing agent configuration
        """
        try:
            agent_file = self.agents_dir / f"{name}.md"
            
            if not agent_file.exists():
                return {
                    "success": False,
                    "error": f"Agent '{name}' not found"
                }
            
            content = agent_file.read_text()
            
            return {
                "success": True,
                "name": name,
                "path": str(agent_file),
                "content": content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get agent: {str(e)}"
            }
    
    def delete_agent(self, name: str) -> Dict[str, Any]:
        """Delete an agent configuration.
        
        Args:
            name: Name of the agent to delete
            
        Returns:
            Dict containing result of operation
        """
        try:
            agent_file = self.agents_dir / f"{name}.md"
            
            if not agent_file.exists():
                return {
                    "success": False,
                    "error": f"Agent '{name}' not found"
                }
            
            agent_file.unlink()
            
            return {
                "success": True,
                "message": f"Agent '{name}' deleted successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete agent: {str(e)}"
            }
    
    def _generate_markdown(self, config: Dict[str, Any]) -> str:
        """Generate markdown content for agent configuration.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            Markdown formatted string
        """
        lines = []
        
        # Header
        lines.append(f"# {config['name']}")
        lines.append("")
        lines.append(f"**Type**: {config['agent_type']}")
        lines.append(f"**Created**: {config['created_at']}")
        if config.get('language'):
            lines.append(f"**Language**: {config['language']}")
        lines.append("")
        
        # Description
        lines.append("## Description")
        lines.append(config['description'])
        lines.append("")
        
        # Expertise
        if config.get('expertise'):
            lines.append("## Expertise")
            for item in config['expertise']:
                lines.append(f"- {item}")
            lines.append("")
        
        # Tools
        if config.get('tools'):
            lines.append("## Required Tools")
            lines.append(f"Tools: {', '.join(config['tools'])}")
            lines.append("")
        
        # Prompts
        if config.get('prompts'):
            lines.append("## System Prompts")
            prompts = config['prompts']
            
            if isinstance(prompts.get('initial'), str):
                lines.append("### Initial Prompt")
                lines.append(prompts['initial'])
                lines.append("")
            
            # Add other prompt sections
            for key, value in prompts.items():
                if key != 'initial' and value:
                    lines.append(f"### {key.replace('_', ' ').title()}")
                    if isinstance(value, list):
                        for item in value:
                            lines.append(f"- {item}")
                    else:
                        lines.append(str(value))
                    lines.append("")
        
        # Custom configuration
        excluded_keys = {'name', 'description', 'expertise', 'tools', 'prompts', 'created_at', 'agent_type', 'language'}
        custom_config = {k: v for k, v in config.items() if k not in excluded_keys}
        
        if custom_config:
            lines.append("## Additional Configuration")
            lines.append("```json")
            lines.append(json.dumps(custom_config, indent=2))
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)