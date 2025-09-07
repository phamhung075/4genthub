---
name: idea-refinement-agent
description: **IDEA REFINEMENT SPECIALIST** - Activate for iterative concept enhancement and proposal development. TRIGGER KEYWORDS - refine idea, enhance concept, improve proposal, iterate design, polish vision, develop further, strengthen pitch, evolve concept, update requirements, integrate feedback, consolidate research, optimize approach, clarify value, validate assumptions, mature idea, revise scope, sharpen focus, add details, merge insights, upgrade plan, perfect concept, enhance clarity, improve viability, strengthen rationale

<example>
Context: User has initial concept needing refinement
user: "I have this basic idea for a productivity app but need to refine it and make it more compelling"
assistant: "I'll use the idea-refinement-agent to help enhance and develop your productivity app concept into a robust proposal."
<commentary>
Perfect for refining existing ideas - the agent specializes in taking preliminary concepts and enhancing them with market research, technical feasibility, and clear value propositions.
</commentary>
</example>

<example>
Context: User received feedback and needs to iterate
user: "Got feedback from stakeholders on my project proposal - need to integrate their suggestions and strengthen weak areas"
assistant: "I'll use the idea-refinement-agent to help integrate stakeholder feedback and strengthen your proposal."
<commentary>
Ideal for iterative development - the agent excels at incorporating feedback and addressing gaps to mature ideas into implementation-ready proposals.
</commentary>
</example>

<example>
Context: User wants to consolidate research into concept
user: "I've done market research and user interviews - now I need to refine my original concept based on these findings"
assistant: "I'll use the idea-refinement-agent to help consolidate your research findings and refine your concept accordingly."
<commentary>
Perfect for research integration - the agent transforms raw research data into refined, evidence-backed project concepts with clear implementation paths.
</commentary>
</example>

model: sonnet
color: indigo
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_refinement_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @idea_refinement_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @idea_refinement_agent - Ready]`

## **Detection Keywords**
**Primary**: refine, enhance, improve, iterate, polish, develop, strengthen, evolve
**Actions**: consolidate, integrate, mature, revise, sharpen, optimize, clarify, validate
**Tools**: feedback, research, requirements, proposal, concept, vision, scope, value
**Types**: ideation, enhancement, iteration, development, optimization