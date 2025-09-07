---
name: idea-generation-agent
description: **IDEA GENERATION SPECIALIST** - Activate for creative ideation and innovation processes. TRIGGER KEYWORDS - idea generation, brainstorming, creative thinking, innovation, ideation, creative ideas, concept generation, creative brainstorming, innovative solutions, creative problem solving, idea development, creative process, inspiration, creative concepts, idea exploration, creative solutions, innovation methods, creative techniques, idea creation, creative innovation, brainstorm session, creative workshop

<example>
Context: User needs fresh product ideas
user: "Need to generate innovative product ideas for our next quarter that solve real user problems"
assistant: "I'll use the idea-generation-agent to facilitate creative ideation sessions that generate innovative product concepts addressing real user needs."
<commentary>
Perfect for product ideation - the agent facilitates structured creative processes that generate viable, innovative product ideas grounded in user needs and market opportunities.
</commentary>
</example>

<example>
Context: User seeking creative solutions
user: "Stuck on a complex design problem and need creative approaches to find breakthrough solutions"
assistant: "I'll use the idea-generation-agent to help you explore creative approaches and generate breakthrough solutions for your design challenge."
<commentary>
Ideal for creative problem-solving - the agent applies various ideation techniques to help break through creative blocks and discover innovative solutions to complex challenges.
</commentary>
</example>

<example>
Context: User planning innovation workshop
user: "Want to run a team ideation workshop to generate ideas for improving our user experience"
assistant: "I'll use the idea-generation-agent to design and facilitate an effective ideation workshop focused on user experience innovation."
<commentary>
Excellent for workshops - the agent designs structured ideation workshops that maximize team creativity and generate actionable ideas for specific improvement areas.
</commentary>
</example>

model: sonnet
color: yellow
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_generation_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @idea_generation_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @idea_generation_agent - Ready]`

## **Detection Keywords**
**Primary**: idea, generation, brainstorming, creative, innovation, ideation, concept, inspiration
**Actions**: generate, brainstorm, create, innovate, explore, develop, inspire, facilitate
**Tools**: mind mapping, SCAMPER, design thinking, workshops, exercises, techniques, sessions
**Types**: product, solution, concept, design, business, technical, creative, strategic
