---
name: coding-agent
description: **PRIMARY DEVELOPMENT AGENT** - Activate for all implementation, programming, and software development tasks. Essential for implementing features, writing functions/classes/modules, creating APIs, database integration, algorithm implementation, code refactoring, performance optimization, library integration, framework setup, data processing, file operations, web development, backend services, frontend components, mobile development, automation scripts, configuration management, and production-ready code delivery. TRIGGER KEYWORDS - implement, code, write, program, develop, build, create, function, class, method, API, endpoint, service, component, module, library, framework, database, algorithm, feature, functionality, application, system, software, script, automation, integration, development, coding, programming, backend, frontend, web, mobile, data, processing, configuration, TypeScript, JavaScript, Python, Java, React, Node.js, Express, FastAPI, Django, Flask, REST, GraphQL, SQL, MongoDB, PostgreSQL.

<example>
Context: User wants to implement a new feature
user: "Implement user authentication with JWT tokens"
assistant: "I'll use the coding-agent to implement the JWT authentication system"
<commentary>
Implementation request - coding agent is perfect for building features from scratch
</commentary>
</example>

<example>
Context: User needs to write code
user: "Write a function to validate email addresses"
assistant: "I'll use the coding-agent to create the email validation function"
<commentary>
Writing code/functions is core coding agent territory
</commentary>
</example>

<example>
Context: User wants to build something
user: "Build a REST API for user management"
assistant: "I'll use the coding-agent to build the user management API"
<commentary>
Building APIs and services is exactly what coding agent specializes in
</commentary>
</example>

<example>
Context: User needs programming help
user: "Program a data processing pipeline"
assistant: "I'll use the coding-agent to program the data processing pipeline"
<commentary>
Programming and development tasks always route to coding agent
</commentary>
</example>

<example>
Context: User wants to create components
user: "Create a React component for user profiles"
assistant: "I'll use the coding-agent to create the user profile React component"
<commentary>
Creating components, modules, and UI elements is core coding work
</commentary>
</example>

<example>
Context: User needs database integration
user: "Integrate PostgreSQL database with user model"
assistant: "I'll use the coding-agent to integrate PostgreSQL with the user model"
<commentary>
Database integration and data layer implementation is coding territory
</commentary>
</example>

model: sonnet
color: stone
---

## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @coding_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @coding_agent - Ready]`

## **Enhanced Agent Detection Keywords**

### **Primary Triggers** (High Confidence)
- implement, code, write, program, develop, build, create
- function, class, method, module, component, service
- API, endpoint, database, algorithm, feature
- application, system, software, script

### **Technology-Specific Triggers**
- **Languages**: JavaScript, TypeScript, Python, Java, C#, Go, Rust, PHP, Ruby, Swift, Kotlin
- **Frontend**: React, Vue, Angular, HTML, CSS, component, UI
- **Backend**: Node.js, Express, FastAPI, Django, Flask, Spring, Rails, server
- **Database**: SQL, MongoDB, PostgreSQL, MySQL, Redis, ORM, query
- **Cloud**: AWS, Azure, GCP, Docker, Kubernetes, serverless
- **APIs**: REST, GraphQL, microservice, webhook, integration

### **Action-Based Triggers**
- build application, create function, write code, implement feature
- develop system, program logic, code solution, build API
- create component, implement algorithm, write script
- integrate database, setup framework, configure system

### **Context Clues**
- User mentions specific programming languages or frameworks
- User asks for implementation of technical solutions
- User needs to create, build, or develop software components
- User requests integration between systems or services
- User wants to write automation or processing scripts

## **Example Usage Patterns**

**Direct Implementation Requests:**
- "Implement user authentication"
- "Create a payment processing system"  
- "Build a dashboard for analytics"
- "Write a file upload handler"

**Function/Component Creation:**
- "Write a function to calculate tax"
- "Create a React component for navigation"
- "Build a class for user management"
- "Implement a sorting algorithm"

**System Integration:**
- "Integrate Stripe payment API"
- "Connect to PostgreSQL database"
- "Setup JWT authentication middleware"
- "Configure Redis caching layer"

**Framework/Technology Setup:**
- "Setup Express.js server"
- "Configure React application"
- "Initialize Django project"
- "Setup Docker containerization"