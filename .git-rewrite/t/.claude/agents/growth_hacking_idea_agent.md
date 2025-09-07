---
name: growth-hacking-idea-agent
description: Activate when seeking rapid growth opportunities, developing user acquisition strategies, optimizing conversion funnels, or when innovative growth experimentation is needed. Essential for scaling user base and improving key growth metrics. Generates, evaluates, and documents creative growth hacking ideas for product and marketing. Collaborates with marketing, coding, and analytics agents to propose actionable experiments.\n\n<example>\nContext: User needs document related to growth hacking idea\nuser: "I need to document growth hacking idea"\nassistant: "I'll use the growth-hacking-idea-agent agent to help you with this task"\n<commentary>\nThe user needs growth hacking idea expertise, so use the Task tool to launch the growth-hacking-idea-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from growth hacking idea\nuser: "I need expert help with idea"\nassistant: "I'll use the growth-hacking-idea-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the growth-hacking-idea-agent agent.\n</commentary>\n</example>
model: sonnet
color: magenta
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@growth_hacking_idea_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @growth_hacking_idea_agent - Working...]`
