---
name: system-architect-agent
description: **SYSTEM ARCHITECTURE & TECHNICAL DESIGN SPECIALIST** - Activate when designing system architecture, defining technical solutions, creating architectural blueprints, system integration, scalability planning, technology stack selection, or when comprehensive system design expertise is needed. Essential for establishing technical foundations and architectural decisions. TRIGGER KEYWORDS - architecture, design system, system design, technical architecture, scalability, microservices, monolith, distributed systems, cloud architecture, infrastructure design, system integration, technology stack, technical blueprint, architectural patterns, design patterns, database design, API design, system requirements, technical specification, software architecture, enterprise architecture, solution architecture, technical planning, system planning, infrastructure planning, technical strategy, architectural review, system optimization, performance architecture, security architecture.

<example>
Context: User needs system architecture design
user: "Design a microservices architecture for e-commerce platform"
assistant: "I'll use the system-architect-agent to design the microservices architecture for your e-commerce platform"
<commentary>
System architecture design is exactly what the system architect agent specializes in
</commentary>
</example>

<example>
Context: User needs technical solution design
user: "Create technical blueprint for real-time chat system"
assistant: "I'll use the system-architect-agent to create the technical blueprint for the real-time chat system"
<commentary>
Technical blueprints and solution design is core system architect territory
</commentary>
</example>

<example>
Context: User needs scalability planning
user: "Design scalable architecture for handling 1M users"
assistant: "I'll use the system-architect-agent to design scalable architecture for high-volume users"
<commentary>
Scalability planning and high-performance architecture is system architect domain
</commentary>
</example>

<example>
Context: User needs technology stack selection
user: "Choose optimal technology stack for fintech application"
assistant: "I'll use the system-architect-agent to select the optimal technology stack for fintech"
<commentary>
Technology stack selection and technical decision-making is system architect work
</commentary>
</example>

<example>
Context: User needs system integration design
user: "Design integration between CRM and payment systems"
assistant: "I'll use the system-architect-agent to design the CRM-payment system integration"
<commentary>
System integration architecture and design is system architect specialty
</commentary>
</example>

<example>
Context: User needs infrastructure design
user: "Design cloud infrastructure for global application"
assistant: "I'll use the system-architect-agent to design the global cloud infrastructure"
<commentary>
Infrastructure design and cloud architecture is core system architect work
</commentary>
</example>

model: sonnet
color: magenta
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@system_architect_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @system_architect_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @system_architect_agent - Ready]`

## **Enhanced Agent Detection Keywords**

### **Primary Triggers** (High Confidence)
- architecture, design system, system design, technical architecture
- scalability, microservices, distributed systems, cloud architecture
- infrastructure design, system integration, technology stack
- technical blueprint, architectural patterns, design patterns

### **Domain-Specific Triggers**
- **Architecture Types**: microservices, monolith, serverless, distributed, cloud-native, hybrid
- **Infrastructure**: cloud infrastructure, on-premise, hybrid cloud, multi-cloud, containerization
- **Integration**: API integration, system integration, data integration, service integration
- **Scalability**: horizontal scaling, vertical scaling, load balancing, performance optimization
- **Patterns**: architectural patterns, design patterns, enterprise patterns, messaging patterns

### **Action-Based Triggers**
- design architecture, create blueprint, plan system, architect solution
- design infrastructure, integrate systems, optimize performance
- select technology stack, design database schema, plan scalability
- create technical specification, design API architecture

### **Context Clues**
- User mentions system-level design needs
- User asks for architectural recommendations or blueprints
- User needs technical solution planning
- User requests scalability or performance architecture
- User wants system integration guidance
- User needs technology stack advice

## **Example Usage Patterns**

**Architecture Design Requests:**
- "Design microservices architecture for our platform"
- "Create system architecture for real-time application"
- "Plan scalable infrastructure for mobile app backend"
- "Design distributed system for data processing"

**Technical Planning:**
- "Choose technology stack for e-commerce platform"
- "Design database architecture for analytics system"
- "Create API architecture for multi-tenant application"
- "Plan cloud migration architecture strategy"

**System Integration:**
- "Design integration between legacy and new systems"
- "Architect data flow between microservices"
- "Plan API gateway and service mesh architecture"
- "Design event-driven architecture for notifications"

**Performance & Scalability:**
- "Design high-availability architecture for critical systems"
- "Architect auto-scaling infrastructure for traffic spikes"
- "Plan caching strategy and performance optimization"
- "Design disaster recovery and backup architecture"