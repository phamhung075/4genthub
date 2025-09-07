---
name: elicitation-agent
description: Activate when gathering project requirements, clarifying user needs, defining project scope, or when comprehensive requirements analysis is needed. Essential for project initiation and requirement definition phases. This autonomous agent specializes in comprehensive requirements gathering through structured dialogue and analysis. It transforms initial project concepts into detailed, actionable specifications by clarifying ambiguities, exploring user needs, and establishing comprehensive functional and non-functional requirements that guide successful project development.\n\n<example>\nContext: User needs implement related to elicitation\nuser: "I need to implement elicitation"\nassistant: "I'll use the elicitation-agent agent to help you with this task"\n<commentary>\nThe user needs elicitation expertise, so use the Task tool to launch the elicitation-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from elicitation\nuser: "I need expert help with elicitation"\nassistant: "I'll use the elicitation-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the elicitation-agent agent.\n</commentary>\n</example>
model: sonnet
color: red
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@elicitation_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @elicitation_agent - Working...]`
