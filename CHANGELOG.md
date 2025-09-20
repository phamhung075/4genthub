# Changelog

All notable changes to the agenthub AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed
- **Subtask API Endpoint 404 Errors**: Fixed routing patterns for fetching individual subtasks
  - Updated frontend to use proper parent task routing (`/api/v2/tasks/{taskId}/subtasks/{subtaskId}`)
  - Added new backend endpoint with parent task validation
  - Modified: `agenthub-frontend/src/services/apiV2.ts`, `agenthub_main/src/fastmcp/server/routes/task_user_routes.py`

- **Duplicate Task Completion Notifications**: Eliminated duplicate "Task completed" notifications
  - Modified CompleteTaskUseCase to return `was_already_completed` flag
  - TaskApplicationFacade now only broadcasts notifications for new completions

## [2025-09-19] - Test Suite Excellence Achieved

### Added
- **Complete Test Suite Victory**: 541 tests passing with 100% success rate
- **Comprehensive Test Coverage**: Full coverage across all critical components
  - Unit tests: Complete coverage for all domain entities
  - Integration tests: Full API and database integration testing
  - End-to-end tests: User workflow validation
  - Performance tests: System performance benchmarking

### Fixed
- **Test Infrastructure Improvements**:
  - Resolved timezone issues in test fixtures
  - Fixed DatabaseSourceManager patches for async operations
  - Corrected AsyncMock assertion methods
  - Eliminated all import errors and module conflicts
  - Stabilized mock configurations for consistent testing

## [2025-09-18] - Authentication & Security Enhancements

### Added
- **Keycloak Integration**: Complete OAuth2/OIDC authentication system
  - JWT token validation for all API endpoints
  - Automatic token refresh mechanism
  - Role-based access control (RBAC)
  - Multi-tenant user isolation
  - Created comprehensive setup guide: `ai_docs/authentication/keycloak-setup-guide.md`

- **Developer Tools**:
  - Added `toggle_auth.py` script for easy authentication enable/disable
  - Environment-specific configuration with `.env.dev` priority
  - SSL warning suppression for development environment

### Fixed
- **Authentication Configuration**:
  - Fixed `auth_enabled` to properly load from `AUTH_ENABLED` environment variable
  - Updated `/health` endpoint to correctly read auth status
  - Login endpoint now returns proper 401 for invalid credentials
  - Frontend correctly stores tokens and sends Authorization headers

### Changed
- **Environment Configuration Priority**:
  - `.env.dev` (development) now takes precedence over `.env` (production)
  - Database configuration respects environment priority
  - Proper type conversion for all environment variables

## [2025-09-17] - Infrastructure & Deployment Improvements

### Added
- **Docker Production Configuration**:
  - Multi-stage Docker builds for optimized images
  - CapRover deployment configuration
  - Environment-specific build arguments
  - Automated container orchestration with docker-compose

- **Documentation System**:
  - Comprehensive video tutorial documentation system
  - AI documentation with automatic indexing (`ai_docs/index.json`)
  - Structured documentation categories:
    - API integration guides
    - Authentication documentation
    - Context system documentation
    - Development guides
    - Migration guides
    - Operations documentation
    - Testing & QA documentation
    - Troubleshooting guides

### Fixed
- **Production Docker Configuration**:
  - Fixed `__RUNTIME_INJECTED__` placeholder in MCP configuration
  - Updated Dockerfile for proper frontend production builds
  - Fixed MCP URL configuration for production environments
  - MCPConfigProfile now correctly hides ports for production domains

### Changed
- **Major Rebranding**: Complete transition from "agenthub" to "agenthub"
  - Updated all references across codebase
  - Renamed database tables and schemas
  - Updated Docker images and configurations
  - Migrated all documentation

## [2025-09-16] - Core Platform Features

### Added
- **MCP Task Management System**:
  - Complete CRUD operations for tasks
  - Hierarchical subtask management
  - Task dependencies and workflow orchestration
  - Progress tracking and status management
  - AI-enhanced task planning and breakdown

- **4-Tier Context Hierarchy**:
  - Global → Project → Branch → Task context inheritance
  - UUID-based identification system
  - Automatic context creation on demand
  - Multi-tenant data isolation

- **Agent Orchestration**:
  - 43+ specialized AI agents
  - Dynamic agent assignment and coordination
  - Tool permission enforcement
  - Agent capability management
  - Master orchestrator pattern implementation

- **Vision System Integration**:
  - AI enrichment for tasks and contexts
  - Workflow guidance and hints
  - Progress tracking and analytics
  - Blocker identification and resolution
  - Impact analysis and recommendations

### Technical Stack
- **Backend**: Python 3.12, FastMCP, SQLAlchemy, Domain-Driven Design (DDD)
- **Frontend**: React 18, TypeScript 5, Tailwind CSS, Vite
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: Keycloak with JWT tokens
- **Infrastructure**: Docker, docker-compose, CapRover
- **API**: RESTful API v2 with comprehensive endpoints
- **Testing**: Pytest, Jest, React Testing Library

### Architecture
- **Domain-Driven Design (DDD)** with clear separation of concerns:
  - Domain Layer: Business logic and entities
  - Application Layer: Use cases and application services
  - Infrastructure Layer: Database, external services, repositories
  - Interface Layer: MCP controllers, HTTP endpoints, UI
- **Event-driven architecture** with WebSocket support
- **Microservices-ready** with modular design
- **Clean Architecture** principles throughout

## Project Information

**Repository**: agenthub AI Agent Orchestration Platform
**License**: MIT
**Documentation**: `ai_docs/` with comprehensive guides and references
**Support**: GitHub Issues