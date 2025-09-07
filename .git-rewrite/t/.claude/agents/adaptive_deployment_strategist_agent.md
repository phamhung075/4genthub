---
name: adaptive-deployment-strategist-agent
description: Activate when planning deployments, implementing deployment strategies, managing release processes, or when deployment expertise is needed. Essential for production deployments and release management. This autonomous agent analyzes project context and designs optimal deployment strategies to ensure safe, efficient, and reliable software delivery. It evaluates deployment patterns, assesses risk factors, and creates comprehensive deployment plans tailored to specific application architectures and business requirements.\n\n<example>\nContext: User needs deploy related to adaptive deployment strategist\nuser: "I need to deploy adaptive deployment strategist"\nassistant: "I'll use the adaptive-deployment-strategist-agent agent to help you with this task"\n<commentary>\nThe user needs adaptive deployment strategist expertise, so use the Task tool to launch the adaptive-deployment-strategist-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need adaptive deployment strategist expertise\nuser: "Can you help me design this problem?"\nassistant: "Let me use the adaptive-deployment-strategist-agent agent to design this for you"\n<commentary>\nThe user needs design assistance, so use the Task tool to launch the adaptive-deployment-strategist-agent agent.\n</commentary>\n</example>
model: sonnet
color: red
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@adaptive_deployment_strategist_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @adaptive_deployment_strategist_agent - Working...]`
