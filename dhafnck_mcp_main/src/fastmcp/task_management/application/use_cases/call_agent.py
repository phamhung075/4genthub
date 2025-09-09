"""Enhanced Call Agent Use Case for Agent Library Architecture"""

import os
import yaml
import logging
import traceback
from pathlib import Path
try:
    from .agent_mappings import resolve_agent_name, is_deprecated_agent
except ImportError:
    # Fallback if mappings not available
    def resolve_agent_name(name): return name
    def is_deprecated_agent(name): return False
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

from ...domain.interfaces.utility_service import IAgentDocGenerator

# Configure logger
logger = logging.getLogger(__name__)


def _find_project_root() -> Path:
    """Find project root by looking for dhafnck_mcp_main directory"""
    current_path = Path(__file__).resolve()
    
    # Walk up the directory tree looking for dhafnck_mcp_main
    while current_path.parent != current_path:
        if (current_path / "dhafnck_mcp_main").exists():
            return current_path
        current_path = current_path.parent
    
    # If not found, use current working directory as fallback
    cwd = Path.cwd()
    if (cwd / "dhafnck_mcp_main").exists():
        return cwd
        
    # Last resort - use the directory containing dhafnck_mcp_main
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:
        if current_path.name == "dhafnck_mcp_main":
            return current_path.parent
        current_path = current_path.parent
    
    # Absolute fallback
    # Use environment variable or default data path
    data_path = os.environ.get('DHAFNCK_DATA_PATH', '/data')
    # If running in development, try to find project root
    if not os.path.exists(data_path):
        # Try current working directory
        cwd = Path.cwd()
        if (cwd / "dhafnck_mcp_main").exists():
            return cwd
        # Try parent directories
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "dhafnck_mcp_main").exists():
                return current
            current = current.parent
        # Fall back to temp directory for safety
        return Path("/tmp/dhafnck_project")
    return Path(data_path)


class AgentCapabilities:
    """Manages agent capability checking and validation"""
    
    def __init__(self, capabilities_config: Dict[str, Any]):
        self.capabilities = capabilities_config
        
    def has_file_read(self) -> bool:
        """Check if agent can read files"""
        return self.capabilities.get('file_operations', {}).get('read', False)
    
    def has_file_write(self) -> bool:
        """Check if agent can write/edit files"""
        return self.capabilities.get('file_operations', {}).get('write', False)
    
    def has_mcp_tools(self) -> bool:
        """Check if agent has MCP tools available"""
        return len(self.get_mcp_tools()) > 0
    
    def get_mcp_tools(self) -> List[str]:
        """Get list of available MCP tools"""
        # Try multiple possible locations for MCP tools
        mcp_tools = []
        
        # Check direct mcp_tools field
        if 'mcp_tools' in self.capabilities:
            mcp_tools = self.capabilities['mcp_tools']
        
        # Check if tools are in a nested structure like {'enabled': True, 'tools': [...]}
        elif isinstance(self.capabilities, dict):
            for key, value in self.capabilities.items():
                if isinstance(value, dict) and 'tools' in value:
                    potential_tools = value['tools']
                    if isinstance(potential_tools, list):
                        # Filter for MCP tools (those starting with 'mcp__')
                        mcp_tools.extend([tool for tool in potential_tools if tool.startswith('mcp__')])
        
        return mcp_tools if isinstance(mcp_tools, list) else []
    
    def can_execute_commands(self) -> bool:
        """Check if agent can execute system commands"""
        return self.capabilities.get('system_commands', {}).get('execute', False)


class ExecutableAgent:
    """Represents a fully executable agent with all capabilities"""
    
    def __init__(self, name: str, config: Dict[str, Any], capabilities: AgentCapabilities, 
                 contexts: List[Dict], rules: List[Dict], output_formats: List[Dict], 
                 mcp_tools: List[Dict], metadata: Dict[str, Any]):
        self.name = name
        self.config = config
        self.capabilities = capabilities
        self.contexts = contexts
        self.rules = rules
        self.output_formats = output_formats
        self.mcp_tools = mcp_tools
        self.metadata = metadata
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get comprehensive agent information"""
        return {
            "name": self.name,
            "role": self.config.get('role', ''),
            "context": self.config.get('context', ''),
            "rules": self.config.get('rules', []),
            "tools": self.capabilities.get_mcp_tools(),
            "capabilities_summary": {
                "file_read": self.capabilities.has_file_read(),
                "file_write": self.capabilities.has_file_write(),
                "mcp_tools": self.capabilities.has_mcp_tools(),
                "system_commands": self.capabilities.can_execute_commands(),
                "total_mcp_tools": len(self.capabilities.get_mcp_tools()),
                "total_contexts": len(self.contexts),
                "total_rules": len(self.rules)
            }
        }
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions based on capabilities"""
        actions = []
        if self.capabilities.has_file_read():
            actions.append("read_files")
        if self.capabilities.has_file_write():
            actions.append("write_files")
        if self.capabilities.has_mcp_tools():
            actions.append("use_mcp_tools")
        if self.capabilities.can_execute_commands():
            actions.append("execute_commands")
        return actions
    
    def execute_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute an action based on agent capabilities"""
        if action not in self.get_available_actions():
            return {"success": False, "error": f"Action '{action}' not available for this agent"}
        
        # This would be implemented based on specific action requirements
        return {"success": True, "message": f"Action '{action}' executed successfully"}


class AgentFactory:
    """Factory class for creating ExecutableAgent instances"""
    
    def __init__(self, agent_library_path: Path):
        self.agent_library_path = agent_library_path
        self.agents_path = agent_library_path / "agents"
    
    def create_agent(self, agent_name: str) -> Optional[ExecutableAgent]:
        """Create an ExecutableAgent from agent-library structure"""
        agent_dir = self.agents_path / agent_name
        
        if not agent_dir.exists():
            return None
        
        try:
            # Load configuration files
            config = self._load_config(agent_dir)
            capabilities_config = self._load_capabilities(agent_dir)
            contexts = self._load_contexts(agent_dir)
            rules = self._load_rules(agent_dir)
            output_formats = self._load_output_formats(agent_dir)
            mcp_tools = self._load_mcp_tools(agent_dir)
            metadata = self._load_metadata(agent_dir)
            
            # Create capabilities manager
            capabilities = AgentCapabilities(capabilities_config)
            
            # Create executable agent
            return ExecutableAgent(
                name=agent_name,
                config=config,
                capabilities=capabilities,
                contexts=contexts,
                rules=rules,
                output_formats=output_formats,
                mcp_tools=mcp_tools,
                metadata=metadata
            )
        except Exception as e:
            logging.error(f"Error creating agent {agent_name}: {str(e)}")
            return None
    
    def _load_config(self, agent_dir: Path) -> Dict[str, Any]:
        """Load agent configuration"""
        config_file = agent_dir / "config.yaml"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _load_capabilities(self, agent_dir: Path) -> Dict[str, Any]:
        """Load agent capabilities"""
        capabilities_file = agent_dir / "capabilities.yaml"
        if capabilities_file.exists():
            with open(capabilities_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _load_contexts(self, agent_dir: Path) -> List[Dict]:
        """Load agent contexts"""
        contexts = []
        contexts_dir = agent_dir / "contexts"
        if contexts_dir.exists():
            for context_file in contexts_dir.glob("*.yaml"):
                try:
                    with open(context_file, 'r', encoding='utf-8') as f:
                        context_data = yaml.safe_load(f)
                        if context_data:
                            contexts.append(context_data)
                except Exception as e:
                    logging.warning(f"Error loading context {context_file}: {str(e)}")
        return contexts
    
    def _load_rules(self, agent_dir: Path) -> List[Dict]:
        """Load agent rules"""
        rules = []
        rules_dir = agent_dir / "rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.yaml"):
                try:
                    with open(rule_file, 'r', encoding='utf-8') as f:
                        rule_data = yaml.safe_load(f)
                        if rule_data:
                            rules.append(rule_data)
                except Exception as e:
                    logging.warning(f"Error loading rule {rule_file}: {str(e)}")
        return rules
    
    def _load_output_formats(self, agent_dir: Path) -> List[Dict]:
        """Load agent output formats"""
        output_formats = []
        output_dir = agent_dir / "output_format"
        if output_dir.exists():
            for output_file in output_dir.glob("*.yaml"):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        output_data = yaml.safe_load(f)
                        if output_data:
                            output_formats.append(output_data)
                except Exception as e:
                    logging.warning(f"Error loading output format {output_file}: {str(e)}")
        return output_formats
    
    def _load_mcp_tools(self, agent_dir: Path) -> List[Dict]:
        """Load agent MCP tools"""
        mcp_tools = []
        tools_dir = agent_dir / "tools"
        if tools_dir.exists():
            for tool_file in tools_dir.glob("*.yaml"):
                try:
                    with open(tool_file, 'r', encoding='utf-8') as f:
                        tool_data = yaml.safe_load(f)
                        if tool_data:
                            mcp_tools.append(tool_data)
                except Exception as e:
                    logging.warning(f"Error loading MCP tool {tool_file}: {str(e)}")
        return mcp_tools
    
    def _load_metadata(self, agent_dir: Path) -> Dict[str, Any]:
        """Load agent metadata"""
        metadata_file = agent_dir / "metadata.yaml"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    # Handle multiple YAML documents
                    docs = list(yaml.safe_load_all(f))
                    # Return the first non-empty document
                    for doc in docs:
                        if doc and isinstance(doc, dict):
                            return doc
                    return {}
            except Exception as e:
                logging.warning(f"Error loading metadata {metadata_file}: {str(e)}")
        return {}


class CallAgentUseCase:
    """Enhanced use case for calling agents with executable capabilities"""
    
    def __init__(self, agent_library_dir: Optional[str] = None):
        # Set up agent library path
        if agent_library_dir:
            self.agent_library_path = Path(agent_library_dir)
        else:
            # Auto-detect project structure
            project_root = self._find_project_root()
            self.agent_library_path = project_root / "agent-library"
        
        # Initialize agent factory if agent-library exists
        if self.agent_library_path.exists():
            self._agent_factory = AgentFactory(self.agent_library_path)
            logging.info(f"Agent factory initialized with path: {self.agent_library_path}")
        else:
            self._agent_factory = None
            logging.error(f"Agent library not found at: {self.agent_library_path}")
    
    def _find_project_root(self) -> Path:
        """Find the project root directory"""
        current_path = Path(__file__).resolve()
        
        # Look for project markers
        while current_path.parent != current_path:
            if (current_path / "agent-library").exists():
                return current_path
            if (current_path / "dhafnck_mcp_main").exists():
                return current_path / "dhafnck_mcp_main"
            current_path = current_path.parent
        
        # Default fallback
        return Path.cwd()
    
    def _agent_exists(self, agent_name: str) -> bool:
        """Check if an agent directory exists in the agent-library."""
        try:
            if self._agent_factory:
                agent_path = self._agent_factory.agent_library_path / "agents" / agent_name
                return agent_path.exists() and agent_path.is_dir()
            return False
        except Exception:
            return False
    
    def _normalize_agent_name(self, name_agent: str) -> str:
        """Generic normalization for any agent name to canonical agent-library directory name."""
        # Remove leading @ if present
        name = name_agent.lstrip('@')
        # Remove common file extensions if present
        for ext in ('.json', '.md', '.mdc', '.txt', '.yaml'):
            if name.endswith(ext):
                name = name[:-len(ext)]
        
        # Check if the original name (with underscores) matches an existing directory
        original_name = name.lower()
        if self._agent_exists(original_name):
            return original_name
        
        # Replace underscores, spaces, and multiple hyphens with a single hyphen
        name = re.sub(r'[ _]+', '_', name)
        name = re.sub(r'-+', '_', name)
        # Lowercase for matching
        name = name.lower()
        # Optionally, map common suffixes (e.g., -agent) to canonical form if needed
        # (If you want to enforce -agent suffix, uncomment below)
        # if not name.endswith('-agent'):
        #     name = f"{name}-agent"
        return name
    
    def execute(self, name_agent: str, format: str = "default") -> Dict[str, Any]:
        """Execute agent call with enhanced capabilities"""
        if not self._agent_factory:
            return {
                "success": False,
                "error": f"Agent library not available. Please ensure agent-library directory exists.",
                "agent_info": None,
                "yaml_content": None,
                "available_agents": []
            }
        # Normalize agent name
        normalized_name = self._normalize_agent_name(name_agent)
        
        # Resolve deprecated agent names
        resolved_name = resolve_agent_name(normalized_name)
        
        # Log if using deprecated name
        if is_deprecated_agent(normalized_name):
            logger.info(f"Deprecated agent '{normalized_name}' mapped to '{resolved_name}'")
        
        # Try to create executable agent from agent-library
        executable_agent = self._agent_factory.create_agent(resolved_name)
        if executable_agent:
            # Streamlined Claude Code compatible format
            config = executable_agent.config
            agent_info = config.get('agent_info', {})
            
            # Extract frontmatter data
            frontmatter = {
                "name": agent_info.get('slug', executable_agent.name),
                "description": agent_info.get('description', 'Agent from DhafnckMCP agent-library')
            }
            
            # Add tools if available
            tools = self._extract_tools_from_capabilities(executable_agent.capabilities.capabilities, executable_agent)
            if tools:
                frontmatter["tools"] = tools
            
            # Extract system prompt
            system_prompt = self._extract_system_prompt(executable_agent.contexts)
            
            # Extract actual MCP tools from capabilities
            mcp_tools = self._extract_mcp_tools_from_capabilities(executable_agent.capabilities.capabilities)
            
            # Generate the different formats
            agent_json = self._convert_to_claude_json(executable_agent)
            agent_markdown = self._convert_to_claude_format(executable_agent)
            
            # Return based on requested format
            if format == "json":
                return {
                    "success": True,
                    "json": agent_json,
                    "source": "agent-library"
                }
            elif format == "markdown":
                return {
                    "success": True,
                    "markdown": agent_markdown,
                    "source": "agent-library"
                }
            else:  # default format
                return {
                    "success": True,
                    "agent": agent_json,
                    "source": "agent-library"
                }
        # Agent not found
        available_agents = self._get_available_agents()
        return {
            "success": False,
            "error": f"Agent '{name_agent}' not found in agent-library (normalized as '{normalized_name}')",
            "agent_info": None,
            "yaml_content": None,
            "available_agents": available_agents
        }
    
    def _get_available_agents(self) -> List[str]:
        """Get list of available agents"""
        if not self._agent_factory:
            return []
        
        available_agents = []
        try:
            if self._agent_factory.agents_path.exists():
                for agent_dir in self._agent_factory.agents_path.iterdir():
                    if agent_dir.is_dir() and not agent_dir.name.startswith('.'):
                        available_agents.append(agent_dir.name)
        except Exception as e:
            logging.error(f"Error scanning agent-library directory: {str(e)}")
        
        return sorted(available_agents)
    
    def _extract_system_prompt(self, contexts: List[Dict]) -> str:
        """Extract system prompt from agent contexts"""
        system_prompt_parts = []
        
        for context in contexts:
            # Look for custom_instructions or system_prompt fields
            if 'custom_instructions' in context:
                system_prompt_parts.append(str(context['custom_instructions']))
            elif 'system_prompt' in context:
                system_prompt_parts.append(str(context['system_prompt']))
            elif 'content' in context:
                system_prompt_parts.append(str(context['content']))
        
        return "\n\n".join(system_prompt_parts) if system_prompt_parts else "You are a helpful AI assistant."
    
    def _get_role_based_tools(self, agent_info: Dict[str, Any], capabilities_config: Dict[str, Any]) -> List[str]:
        """Get tools based on YAML configuration permissions"""
        tools = []
        
        # Always include basic file reading tools for all agents
        tools.extend(['Read', 'Grep', 'Glob'])
        
        # File operations based on YAML permissions
        file_ops = capabilities_config.get('file_operations', {})
        if file_ops.get('enabled', False):
            permissions = file_ops.get('permissions', {})
            
            # Add file modification tools based on permissions
            if permissions.get('write', False):
                tools.append('Edit')
            if permissions.get('create', False):
                tools.extend(['Write', 'MultiEdit'])
            if permissions.get('delete', False):
                # Delete is typically part of file system operations
                pass  # No specific tool for delete in current tool set
        
        # Command execution based on YAML configuration
        cmd_exec = capabilities_config.get('command_execution', {})
        if cmd_exec.get('enabled', False):
            tools.append('Bash')
            
            # Add specific command-based tools if allowed
            allowed_commands = cmd_exec.get('allowed_commands', [])
            if any('npm' in cmd or 'yarn' in cmd or 'pnpm' in cmd for cmd in allowed_commands):
                # Package management commands already covered by Bash
                pass
            if any('git' in cmd for cmd in allowed_commands):
                # Git commands already covered by Bash
                pass
        
        # MCP Tools from YAML configuration
        mcp_config = capabilities_config.get('mcp_tools', {})
        if mcp_config.get('enabled', False) and 'tools' in mcp_config:
            mcp_tools = mcp_config['tools']
            if isinstance(mcp_tools, list):
                tools.extend(mcp_tools)
        
        # Additional tools based on collaboration settings
        collaboration = capabilities_config.get('collaboration', {})
        if collaboration.get('enabled', False):
            # Already included task management tools in MCP tools
            pass
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(tools))

    def _extract_tools_from_capabilities(self, capabilities_config: Dict[str, Any], executable_agent: ExecutableAgent = None) -> str:
        """Extract tool list from capabilities configuration with role-based restrictions"""
        
        if executable_agent and hasattr(executable_agent, 'config'):
            agent_info = executable_agent.config.get('agent_info', {})
            role_tools = self._get_role_based_tools(agent_info, capabilities_config)
            return ', '.join(role_tools)
        
        # Fallback to original logic if no agent info
        tools = []
        has_defined_tools = False
        
        # Check for file operations capabilities
        if 'file_operations' in capabilities_config:
            file_ops = capabilities_config['file_operations']
            if file_ops.get('enabled') and file_ops.get('permissions', {}).get('read'):
                tools.extend(['Read', 'Grep', 'Glob'])
                has_defined_tools = True
            if file_ops.get('enabled') and file_ops.get('permissions', {}).get('write'):
                tools.extend(['Edit', 'Write', 'MultiEdit'])
                has_defined_tools = True
        
        # Check for command execution capabilities  
        if 'command_execution' in capabilities_config:
            cmd_exec = capabilities_config['command_execution']
            if cmd_exec.get('enabled'):
                tools.append('Bash')
                has_defined_tools = True
        
        # Check for MCP tools
        if 'mcp_tools' in capabilities_config:
            mcp_config = capabilities_config['mcp_tools']
            if mcp_config.get('enabled'):
                if 'tools' in mcp_config and mcp_config['tools']:
                    tools.extend(mcp_config['tools'])
                    has_defined_tools = True
                else:
                    tools.append('*')
                    has_defined_tools = True
        
        if not has_defined_tools:
            return '*'
        
        unique_tools = list(dict.fromkeys(tools))
        return ', '.join(unique_tools)
    
    def _extract_mcp_tools_from_capabilities(self, capabilities_config: Dict[str, Any]) -> List[str]:
        """Extract MCP tools list from capabilities configuration"""
        mcp_tools = []
        
        # Check for MCP tools in capabilities
        if 'mcp_tools' in capabilities_config:
            mcp_config = capabilities_config['mcp_tools']
            if mcp_config.get('enabled') and 'tools' in mcp_config:
                mcp_tools = mcp_config['tools']
        
        return mcp_tools
    
    def _convert_to_claude_format(self, executable_agent: ExecutableAgent) -> str:
        """Convert dhafnck_mcp agent-library structure to Claude Code .claude/agents format"""
        
        # Extract basic info from config
        config = executable_agent.config
        agent_info = config.get('agent_info', {})
        
        # Build frontmatter
        frontmatter_data = {
            'name': agent_info.get('slug', executable_agent.name),
            'description': agent_info.get('description', 'Agent from DhafnckMCP agent-library')
        }
        
        # Add tools if available
        tools = self._extract_tools_from_capabilities(executable_agent.capabilities.capabilities, executable_agent)
        if tools:
            frontmatter_data['tools'] = tools
        
        # Build frontmatter
        frontmatter_lines = ['---']
        for key, value in frontmatter_data.items():
            frontmatter_lines.append(f'{key}: {value}')
        frontmatter_lines.append('---')
        
        # Extract system prompt
        system_prompt = self._extract_system_prompt(executable_agent.contexts)
        
        # Build final markdown content
        claude_agent_content = '\n'.join(frontmatter_lines) + '\n\n' + system_prompt
        
        return claude_agent_content
    
    def _convert_to_claude_json(self, executable_agent: ExecutableAgent) -> Dict[str, Any]:
        """Convert agent to JSON structure respecting .claude/agents format"""
        
        config = executable_agent.config
        agent_info = config.get('agent_info', {})
        
        # Build the JSON structure following the markdown format
        agent_json = {
            "name": agent_info.get('slug', executable_agent.name),
            "description": agent_info.get('description', 'Agent from DhafnckMCP agent-library'),
            "system_prompt": self._extract_system_prompt(executable_agent.contexts)
        }
        
        # Add tools if available
        tools = self._extract_tools_from_capabilities(executable_agent.capabilities.capabilities, executable_agent)
        if tools:
            # Convert comma-separated string to list
            if isinstance(tools, str):
                agent_json["tools"] = [t.strip() for t in tools.split(',') if t.strip()]
            else:
                agent_json["tools"] = tools
            
        # Add optional metadata
        if agent_info.get('category'):
            agent_json["category"] = agent_info['category']
        if agent_info.get('version'):
            agent_json["version"] = agent_info['version']
            
        return agent_json


# Set up project root and path resolution
def resolve_path(path, base=None):
    p = Path(path)
    if p.is_absolute():
        return p
    base = base or _find_project_root()
    return (base / p).resolve()

# Configure paths for agent-library structure only
if "AGENT_LIBRARY_DIR_PATH" in os.environ:
    AGENT_LIBRARY_DIR = resolve_path(os.environ["AGENT_LIBRARY_DIR_PATH"])
else:
    # find_project_root() returns the dhafnck_mcp_main directory
    project_root = _find_project_root()
    if project_root.name == "dhafnck_mcp_main":
        AGENT_LIBRARY_DIR = project_root / "agent-library"
    else:
        AGENT_LIBRARY_DIR = project_root / "dhafnck_mcp_main/agent-library"

# Convenience function for backward compatibility
def call_agent(name_agent: str, format: str = "default", agent_library_dir: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to call an agent (with normalization)
    
    Args:
        name_agent: Name of the agent to call
        format: Response format - "default", "json", or "markdown"
        agent_library_dir: Optional custom agent library directory
        
    Returns:
        Dict with success status and formatted agent data
    """
    use_case = CallAgentUseCase(agent_library_dir)
    return use_case.execute(name_agent, format) 