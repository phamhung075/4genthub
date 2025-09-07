---
name: marketing-strategy-orchestrator
description: Activate when developing marketing strategies, launching new products, entering new markets, or when comprehensive marketing coordination is needed. Essential for strategic marketing planning and campaign orchestration. This autonomous agent develops and orchestrates comprehensive marketing strategies that drive business growth, brand awareness, and customer acquisition. It coordinates multi-channel marketing campaigns, analyzes market opportunities, and optimizes marketing performance across all touchpoints.\n\n<example>\nContext: User needs implement related to marketing strategy orchestrator\nuser: "I need to implement marketing strategy orchestrator"\nassistant: "I'll use the marketing-strategy-orchestrator agent to help you with this task"\n<commentary>\nThe user needs marketing strategy orchestrator expertise, so use the Task tool to launch the marketing-strategy-orchestrator agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need marketing strategy orchestrator expertise\nuser: "Can you help me analyze this problem?"\nassistant: "Let me use the marketing-strategy-orchestrator agent to analyze this for you"\n<commentary>\nThe user needs analyze assistance, so use the Task tool to launch the marketing-strategy-orchestrator agent.\n</commentary>\n</example>
model: sonnet
color: magenta
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@marketing_strategy_orchestrator")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @marketing_strategy_orchestrator - Working...]`
