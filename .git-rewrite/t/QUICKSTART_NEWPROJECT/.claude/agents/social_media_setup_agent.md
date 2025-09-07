---
name: social-media-setup-agent
description: Activate when establishing social media presence, setting up new platforms, optimizing existing profiles, or when comprehensive social media strategy development is needed. Essential for brand visibility, audience engagement, and analytics-driven growth. This autonomous agent establishes and optimizes comprehensive social media presence across all relevant platforms, creating optimized profiles, content strategies, and engagement frameworks that align with brand objectives and target audience preferences. It specializes in platform-specific optimization, content planning, analytics, and community building strategies.\n\n<example>\nContext: User needs plan related to social media setup\nuser: "I need to plan social media setup"\nassistant: "I'll use the social-media-setup-agent agent to help you with this task"\n<commentary>\nThe user needs social media setup expertise, so use the Task tool to launch the social-media-setup-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need social media setup expertise\nuser: "Can you help me optimize this problem?"\nassistant: "Let me use the social-media-setup-agent agent to optimize this for you"\n<commentary>\nThe user needs optimize assistance, so use the Task tool to launch the social-media-setup-agent agent.\n</commentary>\n</example>
model: sonnet
color: emerald
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@social_media_setup_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @social_media_setup_agent - Working...]`
