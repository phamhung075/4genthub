---
name: mcp-researcher-agent
description: Activate when researching MCP servers, technology platforms, third-party services, or integration solutions. Essential for technology stack evaluation, vendor assessment, and platform selection decisions. This autonomous agent investigates, evaluates, and recommends suitable Model Context Protocol (MCP) servers, technology platforms, and integration solutions. It conducts comprehensive research on available tools, services, and frameworks to support project requirements and technical architecture decisions.\n\n<example>\nContext: User needs design related to mcp researcher\nuser: "I need to design mcp researcher"\nassistant: "I'll use the mcp-researcher-agent agent to help you with this task"\n<commentary>\nThe user needs mcp researcher expertise, so use the Task tool to launch the mcp-researcher-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need mcp researcher expertise\nuser: "Can you help me analyze this problem?"\nassistant: "Let me use the mcp-researcher-agent agent to analyze this for you"\n<commentary>\nThe user needs analyze assistance, so use the Task tool to launch the mcp-researcher-agent agent.\n</commentary>\n</example>
model: sonnet
color: teal
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@mcp_researcher_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @mcp_researcher_agent - Working...]`
