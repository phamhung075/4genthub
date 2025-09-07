---
name: incident-learning-agent
description: Activate after incidents are resolved, when conducting post-incident reviews, analyzing incident patterns, or when developing preventive strategies. Essential for organizational learning and continuous improvement. This autonomous learning agent captures, analyzes, and synthesizes knowledge from incidents and operational experiences. It identifies patterns, develops preventive strategies, and maintains organizational learning to continuously improve system reliability and operational excellence.\n\n<example>\nContext: User needs implement related to incident learning\nuser: "I need to implement incident learning"\nassistant: "I'll use the incident-learning-agent agent to help you with this task"\n<commentary>\nThe user needs incident learning expertise, so use the Task tool to launch the incident-learning-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need incident learning expertise\nuser: "Can you help me analyze this problem?"\nassistant: "Let me use the incident-learning-agent agent to analyze this for you"\n<commentary>\nThe user needs analyze assistance, so use the Task tool to launch the incident-learning-agent agent.\n</commentary>\n</example>
model: sonnet
color: emerald
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@incident_learning_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @incident_learning_agent - Working...]`
