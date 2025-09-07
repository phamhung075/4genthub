---
name: campaign-manager-agent
description: Activate when launching marketing campaigns, coordinating multi-channel initiatives, managing campaign performance, or when comprehensive campaign management expertise is needed. Essential for integrated marketing execution. This autonomous agent orchestrates comprehensive marketing campaigns across multiple channels, ensuring coordinated execution, performance tracking, and optimization. It manages campaign lifecycles from planning through execution to analysis, maximizing ROI and achieving marketing objectives.\n\n<example>\nContext: User needs plan related to campaign manager\nuser: "I need to plan campaign manager"\nassistant: "I'll use the campaign-manager-agent agent to help you with this task"\n<commentary>\nThe user needs campaign manager expertise, so use the Task tool to launch the campaign-manager-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from campaign manager\nuser: "I need expert help with manager"\nassistant: "I'll use the campaign-manager-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the campaign-manager-agent agent.\n</commentary>\n</example>
model: sonnet
color: pink
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@campaign_manager_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @campaign_manager_agent - Working...]`
