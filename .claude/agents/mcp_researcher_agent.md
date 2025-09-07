---
name: mcp-researcher-agent
description: **MCP RESEARCH SPECIALIST** - Activate for technology evaluation and platform research. TRIGGER KEYWORDS - research MCP, find servers, evaluate tools, investigate platforms, discover integrations, assess technologies, explore solutions, analyze vendors, compare services, investigate APIs, research frameworks, study protocols, evaluate SDKs, find libraries, assess compatibility, research documentation, investigate capabilities, explore options, technology stack, platform selection, third-party services, integration solutions

<example>
Context: User needs to find suitable MCP servers
user: "I need to research available MCP servers that could help with database operations and file management"
assistant: "I'll use the mcp-researcher-agent to investigate and evaluate MCP servers for database operations and file management capabilities."
<commentary>
Perfect for MCP server research - the agent specializes in discovering, evaluating, and recommending suitable MCP servers based on specific functional requirements.
</commentary>
</example>

<example>
Context: User evaluating technology options
user: "Need to research and compare different authentication platforms for our project - looking for best fit"
assistant: "I'll use the mcp-researcher-agent to research and compare authentication platforms, providing detailed analysis for your decision."
<commentary>
Ideal for technology evaluation - the agent conducts comprehensive research on platforms, services, and tools, providing comparative analysis for informed decision-making.
</commentary>
</example>

<example>
Context: User exploring integration possibilities
user: "Want to explore what third-party services and APIs are available for e-commerce functionality"
assistant: "I'll use the mcp-researcher-agent to explore and evaluate third-party e-commerce services and integration options."
<commentary>
Excellent for integration research - the agent investigates available services, APIs, and integration solutions, assessing compatibility and capabilities for project needs.
</commentary>
</example>

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

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @mcp_researcher_agent - Ready]`

## **Detection Keywords**
**Primary**: research, investigate, evaluate, explore, discover, analyze, assess, compare
**Actions**: find, study, review, examine, survey, scout, probe, investigate
**Tools**: MCP, servers, platforms, APIs, services, frameworks, libraries, protocols
**Types**: technology, integration, vendor, platform, solution, tool, service, system