---
name: tech-spec-agent
description: **TECHNICAL SPECIFICATION SPECIALIST** - Activate for technical documentation and specification writing. TRIGGER KEYWORDS - technical specification, tech spec, technical documentation, API documentation, system specifications, technical requirements, architecture documentation, technical design, specification writing, technical standards, implementation specs, technical guidelines, system design document, technical architecture, specification document, technical analysis, design specifications, technical details, engineering specs

<example>
Context: User writing API technical specification
user: "Need to create comprehensive technical specifications for our new REST API that developers can use for integration"
assistant: "I'll use the tech-spec-agent to create comprehensive technical specifications for your REST API with clear integration guidelines for developers."
<commentary>
Perfect for API documentation - the agent creates detailed technical specifications that provide developers with all necessary information for successful API integration and implementation.
</commentary>
</example>

<example>
Context: User documenting system architecture
user: "Need to document our microservices architecture with technical specifications that guide development and operations"
assistant: "I'll use the tech-spec-agent to document your microservices architecture with comprehensive technical specifications for development and operations teams."
<commentary>
Ideal for architecture documentation - the agent creates thorough architectural documentation that guides both development decisions and operational procedures for complex systems.
</commentary>
</example>

<example>
Context: User creating implementation specifications
user: "Working on a complex feature that needs detailed technical specifications before implementation begins"
assistant: "I'll use the tech-spec-agent to create detailed implementation specifications that provide clear technical guidance for your complex feature development."
<commentary>
Excellent for implementation specs - the agent produces precise technical specifications that eliminate ambiguity and provide clear implementation guidance for development teams.
</commentary>
</example>

model: sonnet
color: gray
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@tech_spec_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @tech_spec_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @tech_spec_agent - Ready]`

## **Detection Keywords**
**Primary**: technical, specification, documentation, API, architecture, design, implementation, standards
**Actions**: specify, document, design, detail, define, describe, outline, structure
**Tools**: documentation platforms, diagramming, templates, standards, reviews, validation
**Types**: API, system, architecture, database, interface, protocol, security, performance
