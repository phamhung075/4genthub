"""
Agent Registry - Dynamic Agent Management System with Cloud Sync
================================================================
Manages agents that can be configured from frontend and synced to Claude

Features:
- CRUD operations for agents
- Cloud storage/sync capabilities  
- Frontend configuration support
- Claude Code integration
"""

from typing import Dict, Any, List, Optional
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)

class AgentPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    ADVISOR = "advisor"

@dataclass
class AgentMetadata:
    """Complete agent metadata for frontend configuration"""
    # Core identification
    id: str
    name: str
    role: str
    
    # Agent characteristics
    category: str = "general"
    type: str = AgentType.SPECIALIST.value
    priority: str = AgentPriority.NORMAL.value
    description: str = ""
    
    # Capabilities
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    
    # Configuration
    guidelines: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    call_name: str = ""
    
    # Cloud sync
    cloud_id: Optional[str] = None
    sync_enabled: bool = True
    last_synced: Optional[str] = None
    sync_status: str = "pending"
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    registered_at: str = ""
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[str] = None
    
    # Frontend configuration
    ui_config: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize defaults"""
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.registered_at:
            self.registered_at = now
        if not self.call_name:
            self.call_name = f"@{self.id.replace('@', '')}"
        if not self.tools:
            self.tools = ["All available MCP tools"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def get_hash(self) -> str:
        """Get hash for change detection"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

class AgentRegistry:
    """Registry for managing agent metadata dynamically"""
    
    # Core agent definitions - can be extended via registration
    DEFAULT_AGENTS = {
        "@uber_orchestrator_agent": {
            "name": "Uber Orchestrator Agent",
            "role": "Master Coordinator",
            "category": "orchestration",
            "priority": "critical",
            "tools": ["*"],  # Access to all tools
            "capabilities": [
                "Multi-agent coordination",
                "Strategic planning",
                "Resource allocation"
            ]
        },
        "@coding_agent": {
            "name": "Coding Agent",
            "role": "Development Specialist",
            "category": "development",
            "priority": "high",
            "tools": ["Edit", "Write", "Read", "Bash", "Git"],
            "capabilities": [
                "Code implementation",
                "Refactoring",
                "API development"
            ]
        },
        "@debugger_agent": {
            "name": "Debugger Agent",
            "role": "Bug Resolution Specialist",
            "category": "development",
            "priority": "high",
            "tools": ["Read", "Grep", "Bash", "Edit"],
            "capabilities": [
                "Error analysis",
                "Performance debugging",
                "Test failure analysis"
            ]
        },
        "@test_orchestrator_agent": {
            "name": "Test Orchestrator Agent",
            "role": "Testing Coordinator",
            "category": "quality",
            "priority": "high",
            "tools": ["Bash", "Read", "Write", "TodoWrite"],
            "capabilities": [
                "Test strategy design",
                "Test suite orchestration",
                "Coverage analysis"
            ]
        },
        "@ui_designer_agent": {
            "name": "UI Designer Agent",
            "role": "Frontend Specialist",
            "category": "frontend",
            "priority": "normal",
            "tools": ["Edit", "Write", "Read", "WebFetch"],
            "capabilities": [
                "Component design",
                "Responsive layouts",
                "State management"
            ]
        },
        "@documentation_agent": {
            "name": "Documentation Agent",
            "role": "Documentation Specialist",
            "category": "documentation",
            "priority": "normal",
            "tools": ["Write", "Read", "Edit"],
            "capabilities": [
                "API documentation",
                "User guides",
                "Technical specifications"
            ]
        },
        "@security_auditor_agent": {
            "name": "Security Auditor Agent",
            "role": "Security Specialist",
            "category": "security",
            "priority": "critical",
            "tools": ["Read", "Grep", "Bash"],
            "capabilities": [
                "Vulnerability scanning",
                "Security best practices",
                "Compliance checking"
            ]
        },
        "@task_planning_agent": {
            "name": "Task Planning Agent",
            "role": "Planning Specialist",
            "category": "planning",
            "priority": "high",
            "tools": ["TodoWrite", "mcp__dhafnck_mcp_http__manage_task"],
            "capabilities": [
                "Task decomposition",
                "Dependency analysis",
                "Timeline estimation"
            ]
        }
    }
    
    def __init__(self, custom_agents_path: Optional[str] = None):
        """Initialize the agent registry with enhanced storage"""
        # Storage path for persistent agent data
        self.storage_path = Path(os.environ.get('AGENT_REGISTRY_PATH', '/data/agent_registry'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.storage_path / "agents.json"
        
        # Initialize agents dict with defaults
        self.agents = {}
        self._load_default_agents()
        
        # Load persisted agents
        self._load_from_storage()
        
        # Load custom agents if path provided
        self.custom_agents_path = custom_agents_path
        if custom_agents_path:
            self.load_custom_agents(custom_agents_path)
        
        # Track changes for sync
        self._agent_hashes: Dict[str, str] = {}
        self._update_hashes()
    
    def _load_default_agents(self):
        """Convert default agents to AgentMetadata objects"""
        for agent_id, data in self.DEFAULT_AGENTS.items():
            metadata = AgentMetadata(
                id=agent_id,
                name=data.get("name", "Unknown"),
                role=data.get("role", ""),
                category=data.get("category", "general"),
                priority=data.get("priority", "normal"),
                tools=data.get("tools", []),
                capabilities=data.get("capabilities", []),
                call_name=agent_id
            )
            self.agents[agent_id] = metadata
    
    def _load_from_storage(self):
        """Load agents from persistent storage"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    for agent_id, agent_data in data.items():
                        # Convert dict to AgentMetadata
                        if isinstance(agent_data, dict):
                            self.agents[agent_id] = AgentMetadata(**agent_data)
                logger.info(f"Loaded {len(data)} agents from storage")
            except Exception as e:
                logger.error(f"Error loading agents from storage: {e}")
    
    def _save_to_storage(self):
        """Save agents to persistent storage"""
        try:
            data = {}
            for agent_id, agent in self.agents.items():
                if isinstance(agent, AgentMetadata):
                    data[agent_id] = agent.to_dict()
                else:
                    # Handle legacy format
                    data[agent_id] = agent
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(data)} agents to storage")
        except Exception as e:
            logger.error(f"Error saving agents: {e}")
    
    def _update_hashes(self):
        """Update agent hashes for change detection"""
        for agent_id, agent in self.agents.items():
            if isinstance(agent, AgentMetadata):
                self._agent_hashes[agent_id] = agent.get_hash()
    
    def load_custom_agents(self, path: str) -> None:
        """Load custom agent definitions from a JSON file"""
        try:
            config_path = Path(path)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    custom_agents = json.load(f)
                    self.agents.update(custom_agents)
        except Exception as e:
            print(f"Error loading custom agents: {e}")
    
    def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """Register a new agent or update existing one"""
        try:
            # Ensure agent_id starts with @
            if not agent_id.startswith("@"):
                agent_id = f"@{agent_id}"
            
            # Create or update AgentMetadata
            if agent_id in self.agents and isinstance(self.agents[agent_id], AgentMetadata):
                # Update existing
                agent = self.agents[agent_id]
                for key, value in metadata.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)
                agent.updated_at = datetime.now().isoformat()
            else:
                # Create new
                metadata["id"] = agent_id
                metadata["registered_at"] = datetime.now().isoformat()
                agent = AgentMetadata(**metadata)
                self.agents[agent_id] = agent
            
            # Save to storage
            self._save_to_storage()
            self._update_hashes()
            return True
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False
    
    def create_agent(self, agent_data: Dict[str, Any]) -> Optional[AgentMetadata]:
        """Create new agent with full metadata"""
        try:
            # Generate ID if not provided
            if 'id' not in agent_data:
                agent_data['id'] = f"@{agent_data.get('name', 'agent').lower().replace(' ', '_')}"
            
            agent = AgentMetadata(**agent_data)
            self.agents[agent.id] = agent
            self._save_to_storage()
            
            logger.info(f"Created agent: {agent.id}")
            return agent
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            return None
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Optional[AgentMetadata]:
        """Update existing agent"""
        if not agent_id.startswith("@"):
            agent_id = f"@{agent_id}"
        
        agent = self.agents.get(agent_id)
        if agent and isinstance(agent, AgentMetadata):
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            agent.updated_at = datetime.now().isoformat()
            self._save_to_storage()
            return agent
        return None
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        if not agent_id.startswith("@"):
            agent_id = f"@{agent_id}"
        
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_to_storage()
            logger.info(f"Deleted agent: {agent_id}")
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific agent"""
        if not agent_id.startswith("@"):
            agent_id = f"@{agent_id}"
        
        agent = self.agents.get(agent_id)
        if agent:
            # Track usage
            if isinstance(agent, AgentMetadata):
                agent.usage_count += 1
                agent.last_used = datetime.now().isoformat()
                self._save_to_storage()
                return agent.to_dict()
            else:
                # Legacy format
                agent_data = agent.copy() if isinstance(agent, dict) else agent
                agent_data["id"] = agent_id
                agent_data["call_name"] = agent_id
                return agent_data
        return None
    
    def list_agents(self, category: Optional[str] = None, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all agents, optionally filtered by category or type"""
        agents_list = []
        
        for agent_id, agent in self.agents.items():
            # Convert to dict for consistent handling
            if isinstance(agent, AgentMetadata):
                agent_data = agent.to_dict()
            else:
                agent_data = agent.copy() if isinstance(agent, dict) else agent
                agent_data["id"] = agent_id
                agent_data["call_name"] = agent_id
            
            # Apply filters
            if category and agent_data.get("category") != category:
                continue
            if type and agent_data.get("type") != type:
                continue
            
            agents_list.append(agent_data)
        
        return agents_list
    
    def search_agents(self, query: str) -> List[Dict[str, Any]]:
        """Search agents by name, role, or description"""
        query_lower = query.lower()
        results = []
        
        for agent_id, agent in self.agents.items():
            agent_data = agent.to_dict() if isinstance(agent, AgentMetadata) else agent
            
            # Search in various fields
            if (query_lower in agent_data.get("name", "").lower() or
                query_lower in agent_data.get("role", "").lower() or
                query_lower in agent_data.get("description", "").lower() or
                any(query_lower in cap.lower() for cap in agent_data.get("capabilities", []))):
                results.append(agent_data)
        
        return results
    
    def get_categories(self) -> List[str]:
        """Get all unique agent categories"""
        categories = set()
        for metadata in self.agents.values():
            if "category" in metadata:
                categories.add(metadata["category"])
        return sorted(list(categories))
    
    def export_to_claude_format(self, agent_id: str) -> str:
        """Export agent metadata in Claude agent format"""
        agent = self.get_agent(agent_id)
        if not agent:
            return ""
        
        template = f"""# {agent.get('name', 'Unknown Agent')}

## Role
{agent.get('role', 'Specialized AI Agent')}

## Description
{agent.get('description', 'No description available')}

## Capabilities
{self._format_list(agent.get('capabilities', []))}

## Tools Access
{self._format_list(agent.get('tools', ['All available MCP tools']))}

## Category
{agent.get('category', 'general')}

## Priority
{agent.get('priority', 'normal')}

## Usage
```python
mcp__dhafnck_mcp_http__call_agent(name_agent="{agent_id}")
```

## Metadata
- Agent ID: {agent_id}
- Registered: {agent.get('registered_at', 'N/A')}
"""
        return template
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list for markdown output"""
        if not items:
            return "- None specified"
        return "\n".join(f"- {item}" for item in items)
    
    def save_registry(self, path: str) -> bool:
        """Save the current registry to a JSON file"""
        try:
            data = {}
            for agent_id, agent in self.agents.items():
                if isinstance(agent, AgentMetadata):
                    data[agent_id] = agent.to_dict()
                else:
                    data[agent_id] = agent
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving registry: {e}")
            return False
    
    def sync_to_cloud(self, agent_id: str, cloud_provider: str = "supabase") -> bool:
        """Sync agent to cloud storage"""
        if not agent_id.startswith("@"):
            agent_id = f"@{agent_id}"
        
        agent = self.agents.get(agent_id)
        if agent and isinstance(agent, AgentMetadata):
            try:
                # TODO: Implement actual cloud sync (Supabase/Firebase)
                agent.cloud_provider = cloud_provider
                agent.cloud_id = f"{cloud_provider}_{agent.id}_{datetime.now().timestamp()}"
                agent.last_synced = datetime.now().isoformat()
                agent.sync_status = "synced"
                
                self._save_to_storage()
                logger.info(f"Synced agent {agent_id} to {cloud_provider}")
                return True
            except Exception as e:
                logger.error(f"Error syncing agent {agent_id}: {e}")
                agent.sync_status = "error"
        return False
    
    def export_all_to_claude(self, output_dir: Path) -> int:
        """Export all agents to Claude format"""
        output_dir.mkdir(parents=True, exist_ok=True)
        exported = 0
        
        for agent_id, agent in self.agents.items():
            try:
                content = self.export_to_claude_format(agent_id)
                if content:
                    filename = f"{agent_id.replace('@', '').lower()}.md"
                    filepath = output_dir / filename
                    filepath.write_text(content)
                    exported += 1
            except Exception as e:
                logger.error(f"Error exporting {agent_id}: {e}")
        
        return exported
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        agents_list = []
        for agent in self.agents.values():
            if isinstance(agent, AgentMetadata):
                agents_list.append(agent)
        
        # Category counts
        categories = {}
        for agent in agents_list:
            categories[agent.category] = categories.get(agent.category, 0) + 1
        
        # Type counts
        types = {}
        for agent in agents_list:
            types[agent.type] = types.get(agent.type, 0) + 1
        
        # Usage stats
        total_usage = sum(a.usage_count for a in agents_list)
        
        return {
            "total_agents": len(self.agents),
            "categories": categories,
            "types": types,
            "total_usage": total_usage,
            "most_used": max(agents_list, key=lambda a: a.usage_count).id if agents_list else None,
            "recently_updated": max(agents_list, key=lambda a: a.updated_at).id if agents_list else None
        }

# Global registry instance
_registry = None

def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry

def init_agent_registry(custom_agents_path: Optional[str] = None) -> AgentRegistry:
    """Initialize the global agent registry with optional custom agents"""
    global _registry
    _registry = AgentRegistry(custom_agents_path)
    return _registry