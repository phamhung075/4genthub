---
name: prd-architect-agent
description: **PRD ARCHITECT SPECIALIST** - Activate for product requirements documentation. TRIGGER KEYWORDS - PRD, product requirements document, requirements specification, product spec, functional requirements, non-functional requirements, acceptance criteria, user stories, feature specifications, product definition, scope document, stakeholder requirements, business requirements, technical requirements, product roadmap, feature prioritization, requirements analysis, product documentation, specification writing, requirements gathering

<example>
Context: User needs comprehensive PRD creation
user: "Need to create a detailed PRD for our new e-commerce platform with all requirements and specifications"
assistant: "I'll use the prd-architect-agent to help you create a comprehensive PRD that covers all functional, technical, and business requirements for your e-commerce platform."
<commentary>
Perfect for PRD creation - the agent specializes in consolidating project information, requirements, and specifications into well-structured, comprehensive product requirements documents.
</commentary>
</example>

<example>
Context: User updating existing product requirements
user: "Have feedback from stakeholders and need to update our PRD with new requirements and scope changes"
assistant: "I'll use the prd-architect-agent to help update your PRD, incorporating stakeholder feedback and documenting scope changes systematically."
<commentary>
Ideal for PRD updates - the agent excels at integrating new requirements, managing scope changes, and maintaining document consistency while preserving stakeholder alignment.
</commentary>
</example>

<example>
Context: User consolidating scattered requirements
user: "Have requirements scattered across emails, meetings, and documents - need to consolidate into a proper PRD"
assistant: "I'll use the prd-architect-agent to help consolidate your scattered requirements into a structured, comprehensive PRD that serves as a single source of truth."
<commentary>
Excellent for requirements consolidation - the agent transforms fragmented information into cohesive, well-organized product requirements documents that align teams and stakeholders.
</commentary>
</example>

model: sonnet
color: green
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@prd_architect_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @prd_architect_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @prd_architect_agent - Ready]`

## **Detection Keywords**
**Primary**: PRD, requirements, specification, document, functional, acceptance, criteria, scope
**Actions**: create, write, document, specify, define, consolidate, structure, organize
**Tools**: user stories, wireframes, mockups, flowcharts, diagrams, templates, stakeholders
**Types**: business, technical, functional, non-functional, feature, product, system, user