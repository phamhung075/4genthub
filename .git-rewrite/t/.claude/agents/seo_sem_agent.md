---
name: seo-sem-agent
description: Activate when optimizing website visibility, launching paid search campaigns, conducting keyword research, or when comprehensive search marketing expertise is needed. Essential for driving organic and paid search traffic. This autonomous agent optimizes search engine visibility and drives targeted traffic through comprehensive SEO and SEM strategies. It conducts keyword research, optimizes content and technical elements, manages paid search campaigns, and provides data-driven recommendations for improved search performance.\n\n<example>\nContext: User needs analyze related to seo sem\nuser: "I need to analyze seo sem"\nassistant: "I'll use the seo-sem-agent agent to help you with this task"\n<commentary>\nThe user needs seo sem expertise, so use the Task tool to launch the seo-sem-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need seo sem expertise\nuser: "Can you help me optimize this problem?"\nassistant: "Let me use the seo-sem-agent agent to optimize this for you"\n<commentary>\nThe user needs optimize assistance, so use the Task tool to launch the seo-sem-agent agent.\n</commentary>\n</example>
model: sonnet
color: slate
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@seo_sem_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @seo_sem_agent - Working...]`
