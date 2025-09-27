#!/usr/bin/env python3
"""
Example: Convert agenthub agents to .claude/agents files using the new JSON format
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def json_to_claude_agent_file(agent_json: Dict[str, Any], output_dir: str = ".claude/agents") -> str:
    """
    Convert agent JSON to .claude/agents/*.md file format
    
    Args:
        agent_json: Agent definition in JSON format from call_agent response
        output_dir: Directory to save the agent file
    
    Returns:
        Path to the created file
    """
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Build frontmatter
    frontmatter_lines = ["---"]
    frontmatter_lines.append(f"name: {agent_json['name']}")
    frontmatter_lines.append(f"description: {agent_json['description']}")
    
    # Add optional fields
    if 'tools' in agent_json:
        frontmatter_lines.append(f"tools: {agent_json['tools']}")
    if 'category' in agent_json:
        frontmatter_lines.append(f"# category: {agent_json['category']}")
    if 'version' in agent_json:
        frontmatter_lines.append(f"# version: {agent_json['version']}")
    
    frontmatter_lines.append("---")
    
    # Build complete content
    content = "\n".join(frontmatter_lines) + "\n\n" + agent_json['system_prompt']
    
    # Write to file
    filename = f"{agent_json['name']}.md"
    filepath = Path(output_dir) / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(filepath)

def create_agent_from_agenthub(agent_name: str, output_dir: str = ".claude/agents") -> str:
    """
    Complete workflow: Get agent from agenthub and create .claude/agents file
    
    Args:
        agent_name: Name of the agent (with or without @ prefix)
        output_dir: Directory to save the agent file
    
    Returns:
        Path to the created file
    """
    
    # Mock call_agent function for demonstration
    # In real usage, this would be: mcp__agenthub_http__call_agent(name_agent=f"@{agent_name}")
    
    # Example response structure (this would come from actual MCP call)
    mock_response = {
        "success": True,
        "agent": {
            "name": "test-orchestrator-agent",
            "description": "**TESTING & QA SPECIALIST** - Activate for ALL testing activities, quality assurance, and test-related tasks. Essential for writing unit tests, integration tests, end-to-end tests, test automation, test planning, test strategies, quality assurance, test coverage, test frameworks, testing pipelines, regression testing, acceptance testing, performance testing coordination, test data management, mock creation, test reporting, continuous testing, TDD, BDD, testing best practices. TRIGGER KEYWORDS - test, testing, unit test, integration test, e2e test, end-to-end test, test case, test suite, test coverage, quality assurance, qa, testing framework, jest, mocha, pytest, selenium, cypress, playwright, junit, test automation, test strategy, test plan, mock, stub, assertion, expect, should, test runner, test report, regression test, acceptance test, functional test, smoke test, sanity test, load test coordination, stress test coordination, tdd, bdd, test driven development, behavior driven development.",
            "system_prompt": """You are a comprehensive testing specialist responsible for all aspects of software quality assurance.

## Core Purpose
Orchestrate comprehensive testing strategies and coordinate all testing activities across development lifecycles. Design testing frameworks, manage test execution workflows, and ensure thorough quality validation.

## Key Responsibilities
1. **Test Strategy Design**: Create comprehensive testing plans
2. **Framework Setup**: Establish testing infrastructure
3. **Quality Assurance**: Ensure high standards across all deliverables
4. **Test Coordination**: Manage multiple testing activities
5. **Risk Assessment**: Identify and mitigate quality risks

## Testing Specializations
- Unit Testing: Component-level validation
- Integration Testing: System integration verification  
- End-to-End Testing: Complete workflow validation
- Performance Testing: Load and stress testing coordination
- Security Testing: Vulnerability and compliance testing
- User Acceptance Testing: Stakeholder validation facilitation

## Tools & Technologies
- Test Frameworks: Jest, Mocha, Pytest, JUnit, NUnit, TestNG
- E2E Tools: Playwright, Cypress, Selenium, Puppeteer
- Performance Tools: JMeter, K6, Gatling, LoadRunner
- CI/CD Integration: Jenkins, GitHub Actions, GitLab CI

## Quality Standards
- Maintain >80% test coverage for critical paths
- Ensure <30min test execution for CI/CD
- Zero critical defects in production releases
- Comprehensive documentation for all tests

Always prioritize quality and thoroughness in all testing activities.""",
            "tools": "Read, Grep, Glob, Edit, Write, MultiEdit, Bash, *",
            "category": "testing",
            "version": "1.0.0"
        },
        "formats": {
            "json": "...",  # The agent object above
            "markdown": "..."  # Pre-formatted markdown
        },
        "capabilities": [
            "mcp__browsermcp__browser_navigate",
            "mcp__agenthub_http__manage_task",
            "mcp__sequential-thinking__sequentialthinking"
        ],
        "source": "agent-library"
    }
    
    if not mock_response['success']:
        raise Exception(f"Failed to get agent: {mock_response.get('error')}")
    
    # Create .claude/agents file from JSON
    return json_to_claude_agent_file(mock_response['agent'], output_dir)

def batch_create_agents(agent_names: list, output_dir: str = ".claude/agents") -> Dict[str, str]:
    """
    Create multiple .claude/agents files from agenthub agents
    
    Args:
        agent_names: List of agent names to create
        output_dir: Directory to save the agent files
    
    Returns:
        Dictionary mapping agent names to created file paths
    """
    
    results = {}
    
    for name in agent_names:
        try:
            filepath = create_agent_from_agenthub(name, output_dir)
            results[name] = filepath
            print(f"✅ Created {name}: {filepath}")
        except Exception as e:
            results[name] = f"ERROR: {str(e)}"
            print(f"❌ Failed {name}: {str(e)}")
    
    return results

def main():
    """Demonstration of the JSON to .claude/agents workflow"""
    
    print("=== agenthub to Claude Code Agent Conversion ===\n")
    
    # Example 1: Single agent conversion
    print("1. Creating single agent...")
    try:
        filepath = create_agent_from_agenthub("test-orchestrator-agent", "/tmp/claude-agents-demo")
        print(f"✅ Agent created: {filepath}\n")
        
        # Show the created file
        with open(filepath, 'r') as f:
            content = f.read()
        
        print("Generated .claude/agents file preview:")
        print("-" * 50)
        lines = content.split('\n')
        # Show first 20 lines
        for i, line in enumerate(lines[:20]):
            print(f"{i+1:2d}| {line}")
        if len(lines) > 20:
            print("...  [content continues]...")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 2: Batch conversion
    print(f"\n2. Batch creating multiple agents...")
    agent_names = [
        "coding-agent",
        "debugger-agent", 
        "security-auditor-agent",
        "test-orchestrator-agent"
    ]
    
    results = batch_create_agents(agent_names, "/tmp/claude-agents-demo")
    
    print(f"\nSummary:")
    successful = sum(1 for v in results.values() if not v.startswith("ERROR"))
    print(f"✅ Successfully created: {successful}/{len(agent_names)} agents")
    
    if successful > 0:
        print(f"\nAgent files ready for Claude Code:")
        for name, path in results.items():
            if not path.startswith("ERROR"):
                print(f"  - {name}: {path}")

if __name__ == "__main__":
    main()