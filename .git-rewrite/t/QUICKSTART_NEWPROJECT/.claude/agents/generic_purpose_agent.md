---
name: generic-purpose-agent
description: Activate when [scenario 1, e.g., needing quick insights, automating repetitive tasks], [scenario 2, e.g., brainstorming new ideas], or when requiring [specific expertise]. Essential for [core function or use case]. This autonomous agent specializes in [concise role description, e.g., analyzing complex data, generating creative content, optimizing workflows]. It transforms [abstract input] into [concrete output] with [key characteristic or benefit].\n\n<example>\nContext: User needs help with related to generic purpose\nuser: "I need to help with generic purpose"\nassistant: "I'll use the generic-purpose-agent agent to help you with this task"\n<commentary>\nThe user needs generic purpose expertise, so use the Task tool to launch the generic-purpose-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from generic purpose\nuser: "I need expert help with purpose"\nassistant: "I'll use the generic-purpose-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the generic-purpose-agent agent.\n</commentary>\n</example>
model: sonnet
color: sky
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@generic_purpose_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @generic_purpose_agent - Working...]`
