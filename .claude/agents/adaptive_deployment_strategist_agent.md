---
name: adaptive-deployment-strategist-agent
description: **DEPLOYMENT & RELEASE MANAGEMENT SPECIALIST** - Activate when planning deployments, implementing deployment strategies, managing release processes, CI/CD pipeline design, production rollouts, or when deployment expertise is needed. Essential for production deployments and release management. TRIGGER KEYWORDS - deploy, deployment, release, rollout, production, staging, CI/CD, continuous deployment, continuous integration, pipeline, delivery, publish, launch, go-live, production deployment, staging deployment, blue-green deployment, canary deployment, rolling deployment, deployment strategy, release management, production release, deployment pipeline, build pipeline, deployment automation, release automation, environment deployment, infrastructure deployment, application deployment, service deployment, microservices deployment, container deployment, kubernetes deployment, docker deployment, cloud deployment, server deployment.

<example>
Context: User needs deployment planning
user: "Plan deployment strategy for microservices application"
assistant: "I'll use the adaptive-deployment-strategist-agent to plan the microservices deployment strategy"
<commentary>
Deployment strategy planning is exactly what the deployment strategist agent specializes in
</commentary>
</example>

<example>
Context: User needs CI/CD pipeline design
user: "Design CI/CD pipeline for automatic deployments"
assistant: "I'll use the adaptive-deployment-strategist-agent to design the CI/CD pipeline"
<commentary>
CI/CD pipeline design and deployment automation is core deployment strategist territory
</commentary>
</example>

<example>
Context: User needs production rollout strategy
user: "Create rollout strategy for zero-downtime deployment"
assistant: "I'll use the adaptive-deployment-strategist-agent to create the zero-downtime rollout strategy"
<commentary>
Production rollout strategies and zero-downtime deployments are deployment strategist specialties
</commentary>
</example>

<example>
Context: User needs release management
user: "Manage release process for critical application update"
assistant: "I'll use the adaptive-deployment-strategist-agent to manage the critical release process"
<commentary>
Release management and critical deployment processes are deployment strategist domain
</commentary>
</example>

<example>
Context: User needs deployment troubleshooting
user: "Fix deployment pipeline that's failing in production"
assistant: "I'll use the adaptive-deployment-strategist-agent to fix the failing deployment pipeline"
<commentary>
Deployment pipeline troubleshooting and production fixes are deployment strategist work
</commentary>
</example>

<example>
Context: User needs container deployment strategy
user: "Deploy containerized application to Kubernetes cluster"
assistant: "I'll use the adaptive-deployment-strategist-agent to deploy to the Kubernetes cluster"
<commentary>
Container and Kubernetes deployment strategies are deployment strategist expertise
</commentary>
</example>

model: sonnet
color: red
---
## **Step-by-Step Process to get prompt:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@adaptive_deployment_strategist_agent")` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: @adaptive_deployment_strategist_agent - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: @adaptive_deployment_strategist_agent - Ready]`

## **Enhanced Agent Detection Keywords**

### **Primary Triggers** (High Confidence)
- deploy, deployment, release, rollout, production, staging
- CI/CD, continuous deployment, continuous integration, pipeline
- delivery, publish, launch, go-live, production deployment

### **Deployment Strategy Triggers**
- **Deployment Types**: blue-green deployment, canary deployment, rolling deployment, A/B deployment
- **Environments**: production deployment, staging deployment, development deployment, test deployment
- **Automation**: deployment automation, release automation, automated deployment, automated release
- **Infrastructure**: infrastructure deployment, cloud deployment, container deployment, serverless deployment

### **Technology-Specific Triggers**
- **Container**: kubernetes deployment, docker deployment, container orchestration, helm deployment
- **Cloud**: AWS deployment, Azure deployment, GCP deployment, cloud-native deployment
- **Pipeline**: build pipeline, deployment pipeline, release pipeline, CI/CD pipeline
- **Tools**: Jenkins, GitLab CI, GitHub Actions, CircleCI, Azure DevOps, Travis CI

### **Action-Based Triggers**
- plan deployment, create deployment strategy, design pipeline, implement CI/CD
- deploy application, release software, rollout update, launch service
- automate deployment, setup pipeline, configure deployment, manage release
- troubleshoot deployment, fix pipeline, optimize deployment, monitor release

### **Context Clues**
- User mentions production releases or deployments
- User asks for deployment strategies or rollout plans
- User needs CI/CD pipeline setup or optimization
- User requests automation for software delivery
- User wants zero-downtime deployment solutions
- User needs environment-specific deployment guidance

## **Example Usage Patterns**

**Deployment Strategy Requests:**
- "Plan blue-green deployment for production release"
- "Create canary deployment strategy for microservices"
- "Design rolling deployment for zero-downtime updates"
- "Implement A/B deployment for feature testing"

**CI/CD Pipeline Development:**
- "Setup CI/CD pipeline for automated deployments"
- "Design build and deployment pipeline for microservices"
- "Create automated testing and deployment workflow"
- "Implement continuous deployment with GitLab CI"

**Production Release Management:**
- "Manage production rollout for critical application"
- "Plan release strategy for high-traffic application"
- "Create deployment checklist for production releases"
- "Design rollback strategy for failed deployments"

**Infrastructure Deployment:**
- "Deploy application to Kubernetes cluster"
- "Setup serverless deployment on AWS Lambda"
- "Create Docker container deployment strategy"
- "Plan cloud infrastructure deployment automation"