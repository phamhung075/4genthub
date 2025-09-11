---
description: Technical Architecture for DhafnckMCP AI Agent Orchestration Platform
globs: 
alwaysApply: false
---
# DhafnckMCP AI Agent Orchestration Platform - Technical Architecture

## SYSTEM_ARCHITECTURE_OVERVIEW
### Architecture_Type
Domain-Driven Design (DDD) with Clean Architecture Principles

### Architecture_Description
Sophisticated enterprise-grade architecture implementing Domain-Driven Design principles with clear separation of concerns. Built on FastMCP 2.0 framework with MCP (Model Context Protocol) integration, providing advanced multi-agent coordination, hierarchical context management, and autonomous workflow execution through a comprehensive agent orchestration platform.

### Architecture_Layers
1. **Domain Layer** - Rich entities, value objects, and business logic
2. **Application Layer** - Use cases, facades, DTOs, and event handlers
3. **Infrastructure Layer** - SQLite repositories, caching, database management
4. **Interface Layer** - MCP controllers and tool registration
5. **Frontend Layer** - React + TypeScript + Tailwind CSS application

## DOMAIN_DRIVEN_DESIGN_IMPLEMENTATION

### Domain_Layer
**Location**: `dhafnck_mcp_main/src/fastmcp/task_management/domain/`

#### Entities
- **Task**: Core entity with business logic, validation, and lifecycle management
- **Subtask**: Hierarchical task decomposition with progress tracking
- **Project**: Project entity with metadata, health monitoring, and relationships
- **GitBranch**: Branch-based task organization with agent assignments
- **Agent**: AI agent entity with capabilities, assignments, and coordination
- **Context**: Rich context preservation with hierarchical inheritance

#### Value_Objects
- **TaskId, ProjectId, AgentId**: Strong-typed UUID identifiers
- **TaskStatus**: Enumerated status with transition rules (todo, in_progress, blocked, review, testing, done)
- **Priority**: Priority levels with numeric scoring (low, medium, high, urgent, critical)
- **ProgressPercentage**: Progress tracking with automatic status mapping

#### Domain_Services
- **TaskOrchestrationService**: Advanced task workflow coordination and intelligence
- **AgentCoordinationService**: Multi-agent workflow orchestration and load balancing
- **WorkDistributionService**: Intelligent task assignment based on agent capabilities
- **ProgressTrackingService**: Multi-dimensional progress analytics and forecasting
- **ContextEnrichmentService**: Context enhancement and knowledge building

#### Domain_Events
- **TaskCreated, TaskUpdated, TaskCompleted**: Task lifecycle events
- **SubtaskCreated, SubtaskUpdated, SubtaskCompleted**: Subtask management events
- **ProjectCreated, ProjectUpdated, ProjectHealthCheck**: Project lifecycle events
- **AgentRegistered, AgentAssigned, AgentUnassigned**: Agent coordination events
- **ContextCreated, ContextUpdated, InsightAdded**: Context management events

### Application_Layer
**Location**: `dhafnck_mcp_main/src/fastmcp/task_management/application/`

#### Use_Cases
- **Task Management**: CreateTask, UpdateTask, CompleteTask, DeleteTask, ListTasks, SearchTasks, GetNextTask
- **Subtask Management**: CreateSubtask, UpdateSubtask, CompleteSubtask, ListSubtasks
- **Project Management**: CreateProject, UpdateProject, GetProjectHealth, CleanupObsolete, ValidateIntegrity
- **Agent Management**: RegisterAgent, AssignAgent, UnassignAgent, RebalanceAgents, CallAgent
- **Context Management**: CreateContext, UpdateContext, AddProgress, AddInsight, ResolveHierarchy

#### Application_Services
- **TaskApplicationService**: Coordinates task operations with vision enhancement
- **SubtaskApplicationService**: Manages hierarchical task decomposition
- **ProjectApplicationService**: Project lifecycle and health management
- **AgentApplicationService**: Agent registration and coordination
- **ContextApplicationService**: Context preservation and enrichment

#### DTOs_and_Facades
- **TaskDTO**: Data transfer objects for API boundaries
- **TaskApplicationFacade**: Unified interface for task operations
- **AgentApplicationFacade**: Agent coordination and management facade
- **ProjectApplicationFacade**: Project management operations facade

### Infrastructure_Layer
**Location**: `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/`

#### Repositories
- **JsonTaskRepository**: JSON-based task storage with atomic operations
- **SqliteTaskRepository**: SQLite integration with performance optimization
- **FileSystemRepository**: File-based storage for configurations and caching
- **CacheRepository**: Redis-based caching for session persistence

#### External_Services
- **VisionSystemService**: 6-phase AI enhancement platform
- **ComplianceOrchestrator**: Audit trails and policy validation
- **ConnectionHealthMonitor**: Real-time health monitoring and diagnostics
- **NotificationService**: Real-time status broadcasting and updates

#### Database_Integration
- **SQLite**: Primary database with atomic operations and performance optimization
- **Redis**: Session persistence and caching layer
- **Database Management**: Automated migrations, backups, and health monitoring

### Interface_Layer
**Location**: `dhafnck_mcp_main/src/fastmcp/task_management/interface/`

#### MCP_Controllers (Modular Factory Architecture - August 2025)
**Architecture Pattern**: All controllers refactored using factory-based modular design with 93% code size reduction

- **TaskMCPController**: Modular task management (2377→324 lines) with specialized CRUD, search, workflow handlers
- **SubtaskMCPController**: Modular subtask management (1407→23 lines) with automatic parent progress tracking
- **WorkflowHintEnhancer**: Modular AI enhancement (1068→23 lines) with AI-powered guidance services
- **GitBranchMCPController**: Modular branch management (834→23 lines) with agent assignment and advanced operations
- **ProjectMCPController**: Modular project management (435→23 lines) with health checks and maintenance operations
- **AgentMCPController**: Modular agent coordination (402→23 lines) with assignment and rebalancing handlers
- **ProgressToolsController**: Modular progress tracking (376→23 lines) with Vision System Phase 2 integration
- **UnifiedContextController**: Modular context management (362→23 lines) with hierarchical operations and parameter normalization
- **CallAgentMCPController**: Dynamic agent invocation and execution
- **ConnectionMCPController**: Connection management and diagnostics
- **ComplianceMCPController**: Compliance and audit tools
- **RuleOrchestrationController**: Rule management and synchronization

**Modular Components**: 35+ specialized handlers, factories, validators, and services created across all controllers
**Benefits**: Enhanced maintainability, testability, and scalability with zero breaking changes

## MCP_PROTOCOL_INTEGRATION

### MCP_Tool_Ecosystem
**Total Tools**: 15+ categories with comprehensive workflow automation

#### Tool_Categories
1. **Task Management Tools**
   - Full CRUD operations with context integration
   - Workflow guidance and AI recommendations
   - Progress tracking and analytics

2. **Subtask Management Tools**
   - Hierarchical task decomposition
   - Progress tracking with percentage mapping
   - Parent-child relationship management

3. **Context Management Tools**
   - Advanced context preservation
   - AI insights and recommendations
   - Progress tracking and analytics

4. **Hierarchical Context Tools**
   - Global → Project → Task inheritance
   - Context delegation and approval workflows
   - Inheritance validation and debugging

5. **Project Management Tools**
   - Project lifecycle management
   - Health monitoring and cleanup
   - Multi-project coordination

6. **Git Branch Management Tools**
   - Branch-based task organization
   - Agent assignment and coordination
   - Statistics and progress monitoring

7. **Agent Management Tools**
   - Agent registration and coordination
   - Capability-based assignment
   - Load balancing and rebalancing

8. **Agent Invocation Tools**
   - Dynamic agent loading (60+ agents)
   - Capability-based execution
   - Multi-agent coordination

9. **Connection Management Tools**
   - Real-time health monitoring
   - Advanced diagnostics and troubleshooting
   - Performance metrics and analytics

10. **Compliance Tools**
    - Audit trails and policy validation
    - Security monitoring and compliance
    - Governance and risk management

11. **Rule Management Tools**
    - Rule orchestration and hierarchy
    - Client synchronization and conflicts
    - Cache management and optimization

12. **File Resource Tools**
    - File system integration
    - Resource management and optimization
    - Configuration management

13. **Cursor Rules Tools**
    - IDE integration and rule generation
    - Development workflow optimization
    - Code standards enforcement

14. **Delegation Queue Tools**
    - Manual review and approval workflows
    - Context delegation management
    - Governance and oversight

15. **Context Validation Tools**
    - Inheritance chain validation
    - Debugging and troubleshooting
    - Performance optimization

### MCP_Protocol_Features
- **Tool Registration**: Dynamic tool discovery and registration
- **Parameter Validation**: Comprehensive parameter validation with error handling
- **Response Formatting**: Structured responses with workflow guidance
- **Error Handling**: Comprehensive error handling with recovery strategies
- **Performance Optimization**: Caching, batching, and async processing

## AGENT_ORCHESTRATION_SYSTEM

### Agent_Architecture
**Total Agents**: 60+ specialized AI agents with dynamic loading

#### Agent_Categories
- **Development Agents**: coding_agent, debugger_agent, system_architect_agent, tech_spec_agent
- **Design Agents**: ui_designer_agent, design_system_agent, ux_researcher_agent
- **DevOps Agents**: devops_agent, security_auditor_agent, performance_load_tester_agent
- **Analytics Agents**: analytics_setup_agent, market_research_agent, user_feedback_collector_agent
- **Management Agents**: project_initiator_agent, task_planning_agent, master_orchestrator_agent
- **Marketing Agents**: campaign_manager_agent, content_strategy_agent, seo_sem_agent
- **Specialized Agents**: compliance_scope_agent, ethical_review_agent, documentation_agent

#### Agent_Features
- **YAML Configuration**: Metadata-driven agent definitions
- **Dynamic Loading**: Runtime agent discovery and execution
- **Capability-Based Assignment**: Intelligent work distribution
- **Multi-Agent Coordination**: Structured handoffs and collaboration
- **Performance Monitoring**: Agent utilization and efficiency tracking

#### Agent_Coordination
- **Work Distribution**: Intelligent task assignment based on capabilities
- **Load Balancing**: Automatic agent workload distribution
- **Collaboration**: Multi-agent workflow patterns
- **Monitoring**: Real-time agent performance and health tracking

## VISION_SYSTEM_ARCHITECTURE

### Vision_System_Implementation
**Phases**: 6-phase AI enhancement with hierarchical context inheritance

#### Phase_1_Context_Enforcement
- Mandatory context validation for task completion
- Hierarchical context inheritance (Global → Project → Task)
- Context completeness scoring and validation

#### Phase_2_Progress_Tracking
- Multi-dimensional progress analytics
- Predictive completion forecasting
- Performance benchmarking and optimization

#### Phase_3_Workflow_Hints
- AI-powered workflow optimization
- Intelligent suggestions and recommendations
- Pattern detection and process improvement

#### Phase_4_Multi_Agent_Coordination
- Structured agent handoffs and collaboration
- Capability-based work assignment
- Real-time coordination and monitoring

#### Phase_5_Vision_Enrichment
- Strategic objective alignment
- Goal tracking and metrics
- Context enhancement and knowledge building

#### Phase_6_Integration_Testing
- Performance benchmarks and analytics
- System integration validation
- Continuous improvement and optimization

### Context_Hierarchy
```
GLOBAL CONTEXT (Singleton: 'global_singleton')
   ↓ inherits to
PROJECT CONTEXT (ID: project_id)  
   ↓ inherits to
TASK CONTEXT (ID: task_id)
```

## DATABASE_ARCHITECTURE

### Database_Technology
- **Primary Database**: SQLite with atomic operations
- **Caching Layer**: Redis for session persistence
- **Performance Optimization**: Indexing strategy and query optimization

### Database_Schema

#### Task_Storage_Structure
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    git_branch_id TEXT NOT NULL,
    context_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    estimated_effort TEXT,
    assignees TEXT,
    labels TEXT,
    dependencies TEXT,
    due_date TEXT
);
```

#### Subtask_Storage_Structure
```sql
CREATE TABLE subtasks (
    id TEXT PRIMARY KEY,
    parent_task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assignees TEXT,
    progress_percentage INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
);
```

#### Project_Storage_Structure
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Agent_Storage_Structure
```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    call_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

#### Context_Storage_Structure
```sql
CREATE TABLE contexts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    git_branch_id TEXT NOT NULL, -- UUID identifier for branch
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

## PERFORMANCE_ARCHITECTURE

### Performance_Optimization
- **Database**: SQLite with indexing and query optimization
- **Caching**: Redis for session persistence and performance
- **Async Processing**: FastMCP async/await architecture
- **Connection Pooling**: Efficient resource management

### Caching_Strategy
- **Session Persistence**: Redis-based session storage
- **Query Caching**: Database query result caching
- **Agent Caching**: Agent configuration and state caching
- **Context Caching**: Hierarchical context inheritance caching

### Performance_Targets
- **Task Operations**: < 100ms for complex operations
- **Agent Coordination**: < 500ms for multi-agent workflows
- **Database Operations**: < 200ms for SQLite transactions
- **Health Monitoring**: < 50ms for connection checks
- **Vision Analytics**: < 1 second for AI insight generation

## SECURITY_ARCHITECTURE

### Security_Layers
1. **Authentication & Authorization**: Multi-provider OAuth with JWT
2. **Data Protection**: Encryption at rest and in transit
3. **Audit & Compliance**: Comprehensive operation logging
4. **Threat Protection**: Input validation and security monitoring

### Compliance_Framework
- **Operation Validation**: Real-time policy enforcement
- **Audit Trail Management**: Comprehensive activity logging
- **Governance Controls**: Policy configuration and management
- **Risk Management**: Automated risk assessment and mitigation

### Security_Features
- **Authlib Integration**: Multi-provider authentication support
- **JWT Tokens**: Secure token-based authentication
- **Policy Validation**: Real-time compliance checking
- **Audit Trails**: Complete operation logging and tracking

## FRONTEND_ARCHITECTURE

### Frontend_Technology
- **Framework**: React 19.1.0 with TypeScript
- **Styling**: Tailwind CSS with Radix UI components
- **State Management**: React hooks and context
- **Build System**: Vite with modern tooling

### Frontend_Components
- **Task Management**: Basic CRUD operations with forms
- **Project Dashboard**: Project overview and statistics
- **Agent Coordination**: Basic agent assignment interface
- **Real-time Updates**: WebSocket integration (planned)

### Frontend_Limitations
- **Current State**: Basic MVP functionality
- **Missing Features**: Advanced visualization, real-time updates, complex workflows
- **Enhancement Opportunities**: Agent orchestration visualization, performance monitoring dashboard

## DEPLOYMENT_ARCHITECTURE

### Production_Configuration
- **Environment**: Production-ready deployment
- **Server**: FastMCP 2.0 with Python 3.10+
- **Database**: SQLite with Redis caching
- **Frontend**: React build with static hosting
- **Agent System**: 60+ agents with dynamic loading

### System_Requirements
- **Performance**: Sub-second response times
- **Reliability**: 99.9% uptime with error recovery
- **Scalability**: 100+ concurrent agents supported
- **Security**: Comprehensive security and compliance

### Deployment_Components
- **Core Server**: dhafnck_mcp_main/ (Python + FastMCP + DDD)
- **Frontend**: dhafnck-frontend/ (React + TypeScript + Tailwind)
- **Agent Library**: agent-library/ (60+ specialized agents)
- **Configuration**: .cursor/rules/ (Platform rules and settings)

## INTEGRATION_POINTS

### External_Integrations
- **Cursor IDE**: MCP server integration for development workflow
- **Git Systems**: Branch-based task management and organization
- **Authentication**: Multi-provider OAuth with enterprise support
- **Monitoring**: Real-time health monitoring and diagnostics

### API_Endpoints
- **MCP Protocol**: Standard MCP tool invocation and communication
- **WebSocket**: Real-time status updates and notifications
- **HTTP**: RESTful API for frontend communication
- **Authentication**: OAuth and JWT token management

## CURRENT_TECHNICAL_STATUS

### Implemented_Features
- **Domain-Driven Design**: Complete implementation with clean architecture
- **MCP Protocol Integration**: 15+ tool categories with comprehensive functionality
- **Agent Orchestration**: 60+ specialized agents with dynamic loading
- **Database Integration**: SQLite with Redis caching and performance optimization
- **Vision System**: 6-phase AI enhancement with hierarchical context inheritance
- **Security & Compliance**: Comprehensive audit trails and policy validation

### Technical_Debt_and_Improvements
- **Frontend Enhancement**: Advanced visualization and real-time updates needed
- **Database Migration**: Optional PostgreSQL integration for enterprise scaling
- **Performance Optimization**: Multi-layer caching and async processing improvements
- **API Expansion**: REST and GraphQL APIs for external integrations
- **Cloud Deployment**: Kubernetes configuration and cloud-native features

### Future_Architecture_Evolution
- **Microservices**: Potential migration to microservices architecture
- **Event Sourcing**: Enhanced event-driven architecture
- **CQRS**: Command Query Responsibility Segregation implementation
- **Distributed Systems**: Multi-node deployment and coordination
- **Machine Learning**: Advanced ML integration and predictive analytics

## CONCLUSION

The DhafnckMCP AI Agent Orchestration Platform represents a sophisticated enterprise-grade implementation of Domain-Driven Design principles with comprehensive MCP protocol integration. The architecture provides a solid foundation for advanced multi-agent coordination, hierarchical context management, and autonomous workflow execution, supporting 60+ specialized agents and 15+ MCP tool categories with enterprise-level performance, security, and compliance capabilities.