#!/usr/bin/env python3
"""Test the agent sync functionality"""

import sys
import os
import json
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_server_endpoints():
    """Test that server endpoints are working"""
    base_url = "http://localhost:8000"
    
    print("Testing Agent Metadata Endpoints...")
    print("="*50)
    
    # Test 1: Get all agents
    print("\n1. Testing GET /api/agents/metadata")
    try:
        response = requests.get(f"{base_url}/api/agents/metadata")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Found {data.get('total', 0)} agents")
            print(f"  Source: {data.get('source', 'unknown')}")
            
            # Show first agent as example
            if data.get('agents'):
                first_agent = data['agents'][0]
                print(f"  Example agent: {first_agent.get('name')} ({first_agent.get('id')})")
        else:
            print(f"✗ Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 2: Get categories
    print("\n2. Testing GET /api/agents/categories")
    try:
        response = requests.get(f"{base_url}/api/agents/categories")
        if response.status_code == 200:
            data = response.json()
            categories = data.get('categories', [])
            print(f"✓ Found {len(categories)} categories: {', '.join(categories)}")
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Get specific agent
    print("\n3. Testing GET /api/agents/metadata/coding-agent")
    try:
        response = requests.get(f"{base_url}/api/agents/metadata/coding-agent")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                agent = data.get('agent', {})
                print(f"✓ Found agent: {agent.get('name')}")
                print(f"  Role: {agent.get('role')}")
                print(f"  Category: {agent.get('category')}")
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Get agents by category
    print("\n4. Testing GET /api/agents/category/development")
    try:
        response = requests.get(f"{base_url}/api/agents/category/development")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data.get('total', 0)} development agents")
            for agent in data.get('agents', [])[:3]:  # Show first 3
                print(f"  - {agent.get('name')}")
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

def test_sync_client():
    """Test the sync client"""
    print("\n\nTesting Agent Sync Client...")
    print("="*50)
    
    # Import the sync client
    try:
        from sync_agents_to_claude import AgentSyncClient
        
        # Create client
        client = AgentSyncClient()
        
        # Test fetching agents
        print("\n1. Fetching agents from server...")
        agents = client.fetch_agents()
        
        if agents:
            print(f"✓ Successfully fetched {len(agents)} agents")
            
            # Test generating agent file content
            print("\n2. Generating agent file content...")
            if agents:
                sample_agent = agents[0]
                content = client.generate_agent_file(sample_agent)
                print(f"✓ Generated content for {sample_agent.get('name')}")
                print(f"  Content length: {len(content)} characters")
                
                # Show first few lines
                lines = content.split('\n')[:5]
                for line in lines:
                    print(f"  {line}")
            
            # Test saving to file (in temp directory)
            print("\n3. Testing file save...")
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                client.claude_dir = Path(tmpdir) / ".claude" / "agents"
                
                if agents:
                    filepath = client.save_agent_file(agents[0])
                    print(f"✓ Saved to: {filepath}")
                    
                    # Verify file exists
                    if filepath.exists():
                        print(f"✓ File exists and is {filepath.stat().st_size} bytes")
                    else:
                        print("✗ File was not created")
        else:
            print("✗ No agents fetched from server")
            print("  Make sure the MCP server is running on port 8000")
            
    except ImportError as e:
        print(f"✗ Could not import sync client: {e}")
    except Exception as e:
        print(f"✗ Error during testing: {e}")

def main():
    """Main test runner"""
    print("Agent Sync System Test")
    print("="*70)
    
    # Check if server is running
    print("\nChecking server availability...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server is running")
        else:
            print(f"⚠ Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running. Please start the MCP server first.")
        print("  Run: cd agenthub_main && python -m fastmcp.server")
        return
    except Exception as e:
        print(f"⚠ Unexpected error checking server: {e}")
    
    # Run tests
    test_server_endpoints()
    test_sync_client()
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("\nTo sync agents to .claude/agents/, run:")
    print("  python agenthub_main/scripts/sync_agents_to_claude.py")

if __name__ == "__main__":
    main()