# Agent Flow Diagrams - Visual Architecture
**Version**: 2.0  
**Date**: 2025-09-09  
**Status**: Active

## System Overview - 31 Agent Architecture

```mermaid
graph TB
    subgraph "Tier 1: Orchestrators"
        MO[🎯 master_orchestrator]
        TP[📋 task_planning]
        PI[🚀 project_initiator]
        EL[📝 elicitation]
    end
    
    subgraph "Tier 2: Implementation"
        CA[💻 coding]
        DB[🐞 debugger]
        TO[🧪 test_orchestrator]
        DO[📄 documentation]
        PA[🔧 prototyping]
    end
    
    subgraph "Tier 3: Specialists"
        SA[🏗️ system_architect]
        DS[🎨 design_system]
        UI[🎨 ui_specialist]
        ML[🤖 ml_specialist]
        DV[⚙️ devops]
        SE[🔒 security_auditor]
    end
    
    MO --> TP
    MO --> PI
    TP --> CA
    TP --> TO
    TP --> DO
    CA <--> DB
    CA --> TO
    SA --> CA
    UI --> CA
```

## Feature Development Flow

```mermaid
sequenceDiagram
    participant U as User
    participant MO as Master Orchestrator
    participant TP as Task Planning
    participant SA as System Architect
    participant CA as Coding Agent
    participant TO as Test Orchestrator
    participant DB as Debugger
    participant DO as Documentation
    participant DV as DevOps
    
    U->>MO: Feature Request
    MO->>TP: Break down feature
    TP->>TP: Create subtasks
    
    par Parallel Design & Implementation
        TP->>SA: Design architecture
        SA-->>TP: Architecture ready
    and
        TP->>CA: Implement backend
        CA-->>TP: Backend complete
    and
        TP->>TO: Create test suite
        TO-->>TP: Tests ready
    end
    
    TO->>TO: Run tests
    alt Tests fail
        TO->>DB: Debug failures
        DB->>CA: Apply fixes
        CA->>TO: Retest
    end
    
    TP->>DO: Update documentation
    TP->>DV: Deploy to production
    DV-->>MO: Deployment complete
    MO-->>U: Feature delivered
```

## Bug Resolution Flow

```mermaid
flowchart LR
    BR[Bug Report] --> DB[🐞 Debugger Agent]
    DB --> |Analyze| RC[Root Cause]
    RC --> |Fix| CA[💻 Coding Agent]
    CA --> |Validate| TO[🧪 Test Orchestrator]
    TO --> |Pass| DO[📄 Documentation]
    TO --> |Fail| DB
    DO --> |Complete| ✅
```

## Research & Decision Flow

```mermaid
graph TD
    RQ[Research Question] --> DR[🔍 Deep Research Agent]
    DR --> |MCP Research| MCP[MCP Platforms]
    DR --> |Tech Research| TECH[Technologies]
    DR --> |Market Research| MKT[Market Analysis]
    
    MCP --> TA[Technology Advisor]
    TECH --> TA
    MKT --> TA
    
    TA --> |Recommendations| MO[Master Orchestrator]
    MO --> |Decision| IMP[Implementation]
```

## Consolidated Agent Capabilities

### Documentation Agent Evolution
```mermaid
graph LR
    subgraph "Before - 3 Agents"
        TSA[tech_spec_agent]
        PRA[prd_architect_agent]
        ADA[api_doc_agent]
    end
    
    subgraph "After - 1 Agent"
        DOC[📄 documentation_agent<br/>• Tech Specs<br/>• PRDs<br/>• API Docs<br/>• User Guides<br/>• Architecture]
    end
    
    TSA -.->|Consolidated| DOC
    PRA -.->|Consolidated| DOC
    ADA -.->|Consolidated| DOC
```

### DevOps Agent Evolution
```mermaid
graph LR
    subgraph "Before - 4 Agents"
        SSA[swarm_scaler_agent]
        ADS[adaptive_deployment_strategist]
        MCA[mcp_configuration_agent]
        INF[infrastructure_agent]
    end
    
    subgraph "After - 1 Agent"
        DVO[⚙️ devops_agent<br/>• Swarm Scaling<br/>• Deployment Strategies<br/>• MCP Configuration<br/>• Infrastructure<br/>• CI/CD]
    end
    
    SSA -.->|Merged| DVO
    ADS -.->|Merged| DVO
    MCA -.->|Merged| DVO
    INF -.->|Merged| DVO
```

## Parallel Execution Pattern

```mermaid
graph TD
    MO[Master Orchestrator] --> |Spawns Parallel Agents| PAR{Parallel Execution}
    
    PAR --> A1[Agent 1: Backend API]
    PAR --> A2[Agent 2: Frontend UI]
    PAR --> A3[Agent 3: Database]
    PAR --> A4[Agent 4: Testing]
    PAR --> A5[Agent 5: Documentation]
    PAR --> A6[Agent 6: Security]
    
    A1 --> SYNC[Synchronization Point]
    A2 --> SYNC
    A3 --> SYNC
    A4 --> SYNC
    A5 --> SYNC
    A6 --> SYNC
    
    SYNC --> COMPLETE[✅ Task Complete]
```

## Marketing Strategy Flow

```mermaid
graph TB
    MKT[Marketing Request] --> MSO[📈 Marketing Strategy Orchestrator]
    
    MSO --> |SEO/SEM| SEO[Search Optimization]
    MSO --> |Growth| GRO[Growth Strategies]
    MSO --> |Content| CON[Content Planning]
    
    MSO --> BA[🎨 Branding Agent]
    MSO --> CS[👥 Community Strategy]
    MSO --> CI[💡 Creative Ideation]
    
    BA --> |Brand Guidelines| OUT[Campaign Output]
    CS --> |Community Plan| OUT
    CI --> |Creative Assets| OUT
```

## Creative Workflow

```mermaid
stateDiagram-v2
    [*] --> Ideation
    
    state creative_ideation_agent {
        Ideation --> Generation
        Generation --> Refinement
        Refinement --> Validation
        Validation --> Iteration
        Iteration --> Generation: Improve
        Validation --> Final: Approved
    }
    
    Final --> Implementation
    Implementation --> [*]
```

## Security & Compliance Flow

```mermaid
flowchart TD
    CODE[Code Changes] --> SA[🔒 Security Auditor]
    SA --> |Scan| VUL{Vulnerabilities?}
    
    VUL -->|Yes| DB[🐞 Debugger]
    DB --> FIX[Apply Fixes]
    FIX --> SA
    
    VUL -->|No| CS[Compliance Scope]
    CS --> |Check| REG{Compliant?}
    
    REG -->|Yes| ETH[Ethical Review]
    REG -->|No| REM[Remediation]
    REM --> CS
    
    ETH --> |Approved| ✅
```

## Testing Pyramid

```mermaid
graph TB
    subgraph "Test Orchestrator Agent"
        E2E[E2E Tests<br/>5%]
        INT[Integration Tests<br/>20%]
        UNIT[Unit Tests<br/>75%]
    end
    
    E2E --> UAT[UAT Coordinator]
    INT --> PERF[Performance Tester]
    
    style E2E fill:#f9f,stroke:#333,stroke-width:2px
    style INT fill:#bbf,stroke:#333,stroke-width:2px
    style UNIT fill:#bfb,stroke:#333,stroke-width:2px
```

## Context Hierarchy Flow

```mermaid
graph TD
    G[🌍 GLOBAL Context] --> P[📁 PROJECT Context]
    P --> B[🌿 BRANCH Context]
    B --> T[✅ TASK Context]
    
    T --> |Updates| AG[Agent Work]
    AG --> |Insights| T
    T --> |Bubbles Up| B
    B --> |Aggregates| P
    P --> |Summarizes| G
```

## Agent Communication Matrix

```mermaid
graph LR
    subgraph "High Communication"
        CA[Coding] <--> TO[Testing]
        CA <--> DB[Debugger]
        TO <--> DB
    end
    
    subgraph "Medium Communication"
        MO[Orchestrator] --> TP[Planning]
        TP --> CA
        CA --> DO[Documentation]
    end
    
    subgraph "Low Communication"
        SE[Security] -.-> CA
        ML[ML Specialist] -.-> CA
        CS[Community] -.-> MKT[Marketing]
    end
```

## Deployment Pipeline

```mermaid
flowchart LR
    DEV[Development] --> TEST[Testing]
    TEST --> |Pass| STG[Staging]
    TEST --> |Fail| DEV
    
    STG --> SEC[Security Scan]
    SEC --> |Pass| PERF[Performance Test]
    SEC --> |Fail| DEV
    
    PERF --> |Pass| PROD[Production]
    PERF --> |Fail| OPT[Optimization]
    OPT --> DEV
    
    subgraph "DevOps Agent Manages"
        STG
        SEC
        PERF
        PROD
    end
```

## Agent Selection Decision Tree

```mermaid
graph TD
    START[Task Request] --> TYPE{Task Type?}
    
    TYPE -->|Complex Project| MO[Master Orchestrator]
    TYPE -->|Task Planning| TP[Task Planning]
    TYPE -->|Implementation| IMP{Implementation Type?}
    TYPE -->|Research| RES{Research Type?}
    TYPE -->|Testing| TEST{Test Type?}
    
    IMP -->|Backend/Frontend| CA[Coding Agent]
    IMP -->|Bug Fix| DB[Debugger Agent]
    IMP -->|Documentation| DO[Documentation Agent]
    IMP -->|UI/UX| UI[UI Specialist]
    
    RES -->|General/MCP| DR[Deep Research]
    RES -->|Technology| TA[Tech Advisor]
    RES -->|Root Cause| RC[Root Cause Analysis]
    
    TEST -->|Unit/Integration| TO[Test Orchestrator]
    TEST -->|UAT| UAT[UAT Coordinator]
    TEST -->|Performance| PL[Performance Load Tester]
```

## Performance Optimization Flow

```mermaid
sequenceDiagram
    participant APP as Application
    participant HM as Health Monitor
    participant PL as Performance Tester
    participant EO as Efficiency Optimizer
    participant CA as Coding Agent
    participant DV as DevOps
    
    APP->>HM: Monitor Metrics
    HM->>HM: Detect Issues
    HM->>PL: Run Load Tests
    PL->>PL: Identify Bottlenecks
    PL->>EO: Optimization Request
    EO->>EO: Analyze & Plan
    EO->>CA: Implement Optimizations
    CA->>PL: Validate Improvements
    PL->>DV: Deploy Optimizations
    DV->>APP: Updated Application
```

## Summary Statistics

```mermaid
pie title Agent Distribution by Category
    "Orchestration" : 4
    "Development" : 5
    "Testing" : 3
    "Architecture" : 4
    "DevOps" : 1
    "Documentation" : 1
    "Security" : 3
    "Analytics" : 3
    "Marketing" : 3
    "Research" : 3
    "AI/ML" : 1
    "Creative" : 1
```

## Conclusion
These flow diagrams illustrate the streamlined architecture after consolidating from 42 to 31 agents. The key improvements include:

1. **Clearer delegation paths** - Direct flows from orchestrators to implementers
2. **Reduced handoffs** - Consolidated agents handle related tasks
3. **Better parallelization** - Independent agents work simultaneously
4. **Simplified communication** - Fewer agents mean fewer interactions
5. **Enhanced capabilities** - Each agent has broader, integrated skills

The visual flows demonstrate how the system maintains full functionality while operating more efficiently with 26% fewer agents.