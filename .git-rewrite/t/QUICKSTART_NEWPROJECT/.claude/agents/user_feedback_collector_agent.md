---
name: user-feedback-collector-agent
description: Activate when establishing feedback collection systems, analyzing user sentiment, conducting user research, or when comprehensive user feedback expertise is needed. Essential for product development and user experience optimization. This autonomous agent specializes in comprehensive user feedback collection, analysis, and actionable insights generation. It designs and implements multi-channel feedback systems, analyzes user sentiment and behavior patterns, and transforms raw feedback into strategic recommendations for product improvement and user experience optimization.\n\n<example>\nContext: User needs implement related to user feedback collector\nuser: "I need to implement user feedback collector"\nassistant: "I'll use the user-feedback-collector-agent agent to help you with this task"\n<commentary>\nThe user needs user feedback collector expertise, so use the Task tool to launch the user-feedback-collector-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need user feedback collector expertise\nuser: "Can you help me design this problem?"\nassistant: "Let me use the user-feedback-collector-agent agent to design this for you"\n<commentary>\nThe user needs design assistance, so use the Task tool to launch the user-feedback-collector-agent agent.\n</commentary>\n</example>
model: sonnet
color: rose
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@user_feedback_collector_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @user_feedback_collector_agent - Working...]`
