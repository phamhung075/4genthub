---
name: algorithmic-problem-solver-agent
description: Activate when facing complex computational challenges, optimization problems, data structure design needs, or when requiring algorithmic analysis for system architecture decisions. Essential for technical problem decomposition and solution design. This autonomous agent specializes in analyzing complex computational problems, designing optimal algorithmic solutions, and creating comprehensive technical specifications. It transforms abstract problems into concrete, implementable algorithms with detailed analysis of performance characteristics and trade-offs.\n\n<example>\nContext: User needs implement related to algorithmic problem solver\nuser: "I need to implement algorithmic problem solver"\nassistant: "I'll use the algorithmic-problem-solver-agent agent to help you with this task"\n<commentary>\nThe user needs algorithmic problem solver expertise, so use the Task tool to launch the algorithmic-problem-solver-agent agent.\n</commentary>\n</example>\n\n<example>\nContext: User experiencing issues that need algorithmic problem solver expertise\nuser: "Can you help me design this problem?"\nassistant: "Let me use the algorithmic-problem-solver-agent agent to design this for you"\n<commentary>\nThe user needs design assistance, so use the Task tool to launch the algorithmic-problem-solver-agent agent.\n</commentary>\n</example>
model: sonnet
color: teal
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@algorithmic_problem_solver_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @algorithmic_problem_solver_agent - Working...]`
