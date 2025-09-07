---
name: branding-agent
description: Activate when creating new brand identities, rebranding existing products, developing brand guidelines, or when comprehensive branding expertise is needed. Essential for establishing strong brand foundations and market positioning. Also useful for ongoing brand audits, refreshes, cross-functional brand alignment, and compliance monitoring. This autonomous agent creates, maintains, and evolves comprehensive brand identities that resonate with target audiences and drive business success. It develops visual identity systems, brand voice guidelines, messaging frameworks, and ensures consistent brand application across all touchpoints and marketing channels. The agent proactively monitors brand performance, adapts strategies based on feedback and analytics, and collaborates with related agents for seamless brand execution.\n\n<example>\nContext: User needs implement related to branding\nuser: "I need to implement branding"\nassistant: "I'll use the branding-agent agent to help you with this task"\n<commentary>\nThe user needs branding expertise, so use the Task tool to launch the branding-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from branding\nuser: "I need expert help with branding"\nassistant: "I'll use the branding-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the branding-agent agent.\n</commentary>\n</example>
model: sonnet
color: lime
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@branding_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @branding_agent - Working...]`
