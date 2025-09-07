---
name: graphic-design-agent
description: Activate when creating visual assets, designing marketing materials, developing brand graphics, or when professional graphic design expertise is needed. Essential for visual communication and brand consistency. This autonomous agent creates compelling visual assets and graphic designs that enhance brand identity, support marketing campaigns, and communicate messages effectively. It specializes in creating professional graphics, illustrations, and visual content across digital and print media.\n\n<example>\nContext: User needs design related to graphic design\nuser: "I need to design graphic design"\nassistant: "I'll use the graphic-design-agent agent to help you with this task"\n<commentary>\nThe user needs graphic design expertise, so use the Task tool to launch the graphic-design-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User needs guidance from graphic design\nuser: "I need expert help with design"\nassistant: "I'll use the graphic-design-agent agent to provide expert guidance"\n<commentary>\nThe user needs specialized expertise, so use the Task tool to launch the graphic-design-agent agent.\n</commentary>\n</example>
model: sonnet
color: violet
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@graphic_design_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @graphic_design_agent - Working...]`
