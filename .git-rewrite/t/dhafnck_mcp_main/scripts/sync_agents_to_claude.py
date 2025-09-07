#!/usr/bin/env python3
"""
Sync MCP Server Agents to Claude Agent Directory
================================================
This script fetches agent configurations from the MCP server
and generates .claude/agents/*.md files for local use.
"""

import requests
from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Default configuration
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_CLAUDE_DIR = ".claude/agents"

# Agent template for Claude
AGENT_TEMPLATE = """# {name}

## Role
{role}

## Description
{description}

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
mcp__dhafnck_mcp_http__call_agent(name_agent="{call_name}")
```

## Metadata
- **Agent ID**: {agent_id}
- **Type**: {agent_type}
- **Category**: {category}
- **Priority**: {priority}
- **Last Updated**: {updated_at}
- **Server Source**: {server_url}

## Additional Notes
{notes}
"""

class AgentSyncClient:
    """Client for syncing agents from MCP server to Claude directory"""
    
    def __init__(self, server_url: str = DEFAULT_SERVER_URL, claude_dir: str = DEFAULT_CLAUDE_DIR):
        self.server_url = server_url.rstrip('/')
        self.claude_dir = Path(claude_dir)
        self.session = requests.Session()
        
    def fetch_agents(self) -> List[Dict[str, Any]]:
        """Fetch all available agents from MCP server"""
        try:
            # Try the new endpoint first
            response = self.session.get(f"{self.server_url}/api/agents/metadata")
            if response.status_code == 404:
                # Fallback to tool-based approach
                return self._fetch_via_mcp_tool()
            response.raise_for_status()
            return response.json().get("agents", [])
        except Exception as e:
            print(f"Error fetching agents: {e}")
            # Try alternative method
            return self._fetch_via_mcp_tool()
    
    def _fetch_via_mcp_tool(self) -> List[Dict[str, Any]]:
        """Fetch agents via MCP tool call"""
        try:
            # Call the MCP tool to list agents
            payload = {
                "tool": "manage_agent",
                "arguments": {
                    "action": "list"
                }
            }
            response = self.session.post(f"{self.server_url}/tools/call", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("agents", [])
            return []
        except Exception as e:
            print(f"Error fetching via MCP tool: {e}")
            return []
    
    def generate_agent_file(self, agent: Dict[str, Any]) -> str:
        """Generate markdown content for an agent"""
        # Extract agent details with defaults
        name = agent.get("name", "Unknown Agent")
        agent_id = agent.get("id", agent.get("agent_id", ""))
        call_name = agent.get("call_name", f"@{agent_id}")
        
        # Format the agent details
        content = AGENT_TEMPLATE.format(
            name=name,
            role=agent.get("role", "Specialized AI Agent"),
            description=agent.get("description", "No description available"),
            capabilities=self._format_list(agent.get("capabilities", [])),
            tools=self._format_list(agent.get("tools", ["All available MCP tools"])),
            specializations=self._format_list(agent.get("specializations", [])),
            guidelines=agent.get("guidelines", "Follow standard agent protocols"),
            call_name=call_name,
            agent_id=agent_id,
            agent_type=agent.get("type", "general"),
            category=agent.get("category", "uncategorized"),
            priority=agent.get("priority", "normal"),
            updated_at=datetime.now().isoformat(),
            server_url=self.server_url,
            notes=agent.get("notes", "Auto-generated from MCP server")
        )
        
        return content
    
    def _format_list(self, items: List[Any]) -> str:
        """Format a list for markdown"""
        if not items:
            return "- None specified"
        return "\n".join(f"- {item}" for item in items)
    
    def save_agent_file(self, agent: Dict[str, Any]) -> Path:
        """Save agent configuration to file"""
        # Create directory if it doesn't exist
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from agent ID or name
        agent_id = agent.get("id", agent.get("agent_id", "unknown"))
        filename = f"{agent_id.replace('@', '').replace(' ', '_').lower()}.md"
        filepath = self.claude_dir / filename
        
        # Generate and save content
        content = self.generate_agent_file(agent)
        filepath.write_text(content)
        
        return filepath
    
    def sync_agents(self, filter_category: str = None) -> Dict[str, Any]:
        """Sync all agents from server to local directory"""
        results = {
            "synced": [],
            "failed": [],
            "total": 0
        }
        
        print(f"Fetching agents from {self.server_url}...")
        agents = self.fetch_agents()
        
        if not agents:
            print("No agents found or unable to fetch agents")
            return results
        
        results["total"] = len(agents)
        print(f"Found {len(agents)} agents")
        
        for agent in agents:
            try:
                # Apply category filter if specified
                if filter_category and agent.get("category") != filter_category:
                    continue
                
                filepath = self.save_agent_file(agent)
                results["synced"].append({
                    "agent_id": agent.get("id"),
                    "name": agent.get("name"),
                    "file": str(filepath)
                })
                print(f"✓ Synced: {agent.get('name', 'Unknown')} -> {filepath}")
            except Exception as e:
                results["failed"].append({
                    "agent_id": agent.get("id"),
                    "error": str(e)
                })
                print(f"✗ Failed: {agent.get('name', 'Unknown')} - {e}")
        
        return results
    
    def fetch_agent_details(self, agent_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific agent"""
        try:
            # Call MCP tool to get agent details
            payload = {
                "tool": "manage_agent",
                "arguments": {
                    "action": "get",
                    "agent_id": agent_id
                }
            }
            response = self.session.post(f"{self.server_url}/tools/call", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching agent details: {e}")
            return {}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sync MCP server agents to Claude agent directory"
    )
    parser.add_argument(
        "--server-url",
        default=DEFAULT_SERVER_URL,
        help="MCP server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--claude-dir",
        default=DEFAULT_CLAUDE_DIR,
        help="Claude agents directory (default: .claude/agents)"
    )
    parser.add_argument(
        "--category",
        help="Filter agents by category"
    )
    parser.add_argument(
        "--agent-id",
        help="Sync specific agent by ID"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing agent files before sync"
    )
    
    args = parser.parse_args()
    
    # Create client
    client = AgentSyncClient(args.server_url, args.claude_dir)
    
    # Clean directory if requested
    if args.clean:
        print(f"Cleaning {args.claude_dir}...")
        for file in Path(args.claude_dir).glob("*.md"):
            file.unlink()
    
    # Sync specific agent or all
    if args.agent_id:
        print(f"Fetching agent: {args.agent_id}")
        agent_data = client.fetch_agent_details(args.agent_id)
        if agent_data.get("success"):
            agent = agent_data.get("agent", {})
            filepath = client.save_agent_file(agent)
            print(f"✓ Saved: {filepath}")
        else:
            print(f"✗ Failed to fetch agent: {agent_data.get('error')}")
    else:
        # Sync all agents
        results = client.sync_agents(filter_category=args.category)
        
        # Print summary
        print("\n" + "="*50)
        print(f"Sync Summary:")
        print(f"  Total agents: {results['total']}")
        print(f"  Successfully synced: {len(results['synced'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        if results['failed']:
            print("\nFailed agents:")
            for failure in results['failed']:
                print(f"  - {failure['agent_id']}: {failure['error']}")

if __name__ == "__main__":
    main()