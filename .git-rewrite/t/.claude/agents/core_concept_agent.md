---
name: core-concept-agent
description: Activate when defining product concepts, developing value propositions, synthesizing market research into actionable insights, or when strategic concept development expertise is needed. Essential for product strategy and market positioning. This autonomous agent synthesizes insights from ideation, market research, and competitive analysis to define and articulate compelling core concepts for products and services. It crystallizes Unique Value Propositions (UVPs), identifies key differentiators, and defines essential features that create market-fit solutions with clear competitive advantages.\n\n<example>\nContext: User needs analyze related to core concept\nuser: "I need to analyze core concept"\nassistant: "I'll use the core-concept-agent agent to help you with this task"\n<commentary>\nThe user needs core concept expertise, so use the Task tool to launch the core-concept-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from core concept\nuser: "I need expert help with concept"\nassistant: "I'll use the core-concept-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the core-concept-agent agent.\n</commentary>\n</example>
model: sonnet
color: purple
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@core_concept_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @core_concept_agent - Working...]`
