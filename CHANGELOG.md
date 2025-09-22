# Changelog

All notable changes to the agenthub AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed
- **TypeScript Unused Variable Warnings in LazyTaskList.tsx**: Fixed 3 TypeScript compiler warnings about unused parameters
  - Fixed line 332: Changed `page = 1` to `_page = 1` in loadTaskSummaries function parameter
  - Fixed line 761: Changed `subtask` to `_subtask` in onSubtaskSelect callback parameter
  - Fixed line 856: Changed `agentName` to `_agentName` in onAgentClick callback parameter
  - Applied TypeScript convention of underscore prefix for intentionally unused parameters
  - Files modified: `agenthub-frontend/src/components/LazyTaskList.tsx:332,761,856`
  - Impact: Eliminated TypeScript compiler warnings while maintaining interface compliance
- **Frontend WebSocket Unsubscribe Function Error**: Fixed critical TypeError preventing WebSocket DELETE notifications from working
  - Root cause: `unsubscribe()` was being called without checking if it's actually a function, causing "unsubscribe is not a function" crash
  - Solution: Added type safety check `if (typeof unsubscribe === 'function')` before calling unsubscribe
  - Enhanced function with proper TypeScript typing and comprehensive error logging
  - Files modified: `agenthub-frontend/src/services/changePoolService.ts:340-359, 279, 284`
  - Impact: Prevents application crashes on component unmount, allows DELETE notifications to be received properly
  - Testing: Frontend builds successfully without TypeScript errors
- **WebSocket Authorization for Frontend Connections**: Resolved critical issue where WebSocket messages weren't reaching frontend clients
  - Root cause: WebSocket connections weren't being properly maintained in the `connection_users` mapping
  - Solution: Enhanced WebSocket connection establishment and token validation flow
  - Added comprehensive debugging logs for WebSocket authentication and authorization
  - Verified JWT token validation working correctly with Keycloak authentication
  - Confirmed all message types (create, update, delete) are now broadcasting successfully to authorized clients
  - Files modified: `agenthub_main/src/fastmcp/server/routes/websocket_routes.py`
  - Testing: All WebSocket operations verified with 2/2 authorized clients receiving messages
  - Impact: Frontend real-time updates and animations now trigger correctly

### Added
- **Automatic Database Migrations on Server Startup**: Integrated AutoMigrationRunner into server startup process
  - Modified `init_database.py` to automatically run migrations after table creation
  - Creates async engine from existing database configuration for migration support
  - Supports both SQLite (aiosqlite) and PostgreSQL (asyncpg) database types
  - Graceful fallback when async drivers are missing with helpful installation instructions
  - Enhanced migration tracking table creation with database-specific SQL (SERIAL for PostgreSQL, AUTOINCREMENT for SQLite)
  - Comprehensive error handling ensures server continues startup even if migrations fail
  - Automatic execution of materialized view, index, and WebSocket optimization migrations
  - Files modified: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_database.py`, `migration_runner.py`

### Changed
- **Frontend Package Manager Migration**: Migrated agenthub-frontend from npm to pnpm for improved dependency management
  - Removed `package-lock.json` and replaced with `pnpm-lock.yaml`
  - Updated all Docker configurations to use pnpm commands
  - Updated documentation and scripts to use pnpm instead of npm
  - Modified files:
    - `agenthub-frontend/pnpm-lock.yaml` (NEW): pnpm lockfile with all dependencies
    - `agenthub-frontend/package-lock.json` (REMOVED): Old npm lockfile
    - `docker-system/docker-menu.sh`: Updated npm references to pnpm (lines 1223-1228, 1365, 1373, 1458, 1483)
    - `docker-system/docker/Dockerfile.frontend.production`: Added pnpm installation and usage
    - `docker-system/docker/Dockerfile.frontend.dev`: Updated to use pnpm for dependency installation
    - `agenthub-frontend/README.md`: Updated command examples from npm to pnpm
    - `agenthub-frontend/REACT_19_UPGRADE_PLAN.md`: Updated installation commands to use pnpm
  - Benefits: Faster installs, better disk space efficiency, stricter dependency resolution

### Fixed
- **WebSocket Connection Endpoint Mismatch**: Fixed WebSocket connection failure (403 Forbidden) by aligning frontend and backend endpoints
  - Root cause: Frontend was trying to connect to `/ws/{userId}` while backend exposed `/ws/realtime`
  - Solution: Updated frontend WebSocketClient.ts to use correct endpoint `/ws/realtime`
  - Modified files:
    - `agenthub-frontend/src/services/WebSocketClient.ts` (line 71): Changed WebSocket URL from `/ws/${this.userId}` to `/ws/realtime`
  - Impact: WebSocket now connects successfully with JWT authentication, enabling real-time updates
  - Notes: User identification is handled through JWT token payload, eliminating need for user ID in URL path
- **Docker pgAdmin Clean Rebuild**: Enhanced pgAdmin option (G) in docker-menu.sh to completely clean and rebuild with auto-connect configuration
  - Root cause: Old pgAdmin containers may have cached settings that prevent new auto-connect configuration from working properly
  - Solutions implemented:
    - Added volume cleanup: `docker volume rm pgadmin-data 2>/dev/null || true` to clear all cached settings
    - Added image refresh: `docker pull dpage/pgadmin4:latest` to ensure clean start with latest image
    - Both operations include user-friendly console output with colored messaging
    - Operations positioned after container stop/remove and before network creation
  - Modified files:
    - `docker-system/docker-menu.sh` (lines 604-610): Added volume cleanup and image pull to start_postgresql_with_ui() function
  - Impact: pgAdmin now starts completely fresh with no cached settings that could interfere with auto-connect configuration
- **LazySubtaskList Duplicate HTTP Requests**: Fixed performance issue where expanding subtasks made 10+ duplicate API calls
  - Root cause: Race conditions between initial load and real-time subscription, plus lack of request deduplication
  - Solutions implemented:
    - Created request deduplication utility (`agenthub-frontend/src/utils/requestDeduplication.ts`) with 500ms window
    - Enhanced API service layer (`agenthub-frontend/src/services/apiV2.ts`) with automatic request deduplication
    - Fixed subscription timing in LazySubtaskList component with separate `subscriptionEnabled` flag
    - Added debouncing (200ms) to change handlers to batch rapid state changes
    - Added cleanup effects for debounce timers to prevent memory leaks
  - Modified files:
    - `agenthub-frontend/src/utils/requestDeduplication.ts` (NEW): Global request deduplication with debugging tools
    - `agenthub-frontend/src/services/apiV2.ts` (lines 5, 159-179): Added deduplication to fetchWithRetry function
    - `agenthub-frontend/src/components/LazySubtaskList.tsx`:
      - Line 73: Added subscriptionEnabled state flag
      - Lines 235-241: Delayed subscription activation by 250ms after initial load
      - Lines 258-277: Added debouncing to handleSubtaskChanges with 200ms delay
      - Line 392: Updated subscription to use subscriptionEnabled flag
      - Lines 647-653: Added cleanup effect for debounce timers
  - Impact: Reduced API calls from 10+ to just 1 (plus CORS preflight) when expanding subtasks
  - Debug tools: `window.getRequestDeduplicationStats()` and test validation script
  - Performance improvement: Measurable network reduction and faster UI responsiveness
- **Subtask API Endpoint Simplification**: Standardized subtask fetching to use simple authenticated endpoint
  - Root cause: Confusion between two different subtask endpoints (simple vs nested)
  - Solution: Standardized on simple `/api/v2/subtasks/{subtask_id}` endpoint with proper authentication
  - Modified files:
    - `agenthub-frontend/src/services/apiV2.ts` (line 350-366): getSubtask uses simple endpoint with auth headers
    - `agenthub-frontend/src/api.ts` (line 223-227): Passes only subtask_id to apiV2.getSubtask
    - `agenthub_main/src/fastmcp/server/routes/task_user_routes.py` (line 501): Removed nested endpoint to avoid confusion
  - Impact: Clean, consistent API with single subtask endpoint that uses authentication like other endpoints
- **Frontend Task List Real-Time Reactivity**: Fixed task list not updating reactively when changes occur
  - Root cause: WebSocket service was receiving messages but not notifying changePoolService for component updates
  - Solution: Connected websocketService to changePoolService to trigger real-time UI updates
  - Modified files:
    - `agenthub-frontend/src/services/websocketService.ts`:
      - Line 9: Added import for changePoolService
      - Lines 307-320: Added changePoolService.processChange() call in handleMessage method
      - Transforms WebSocket messages to ChangeNotification format for task/subtask entities
  - Impact: All task and subtask operations now trigger immediate UI updates without requiring page refresh
  - Testing: Verified all CRUD operations update in real-time within 1-2 seconds
- **WebSocket Notifications User ID Issues**: Fixed multiple WebSocket broadcast operations using hardcoded `user_id="system"`
  - Root cause: Multiple facade methods were using hardcoded "system" instead of actual user ID for WebSocket broadcasts
  - Solutions implemented:
    1. **Task Deletion**: Updated `delete_task()` to accept and use user_id parameter
    2. **Task Completion**: Updated `complete_task()` to accept and use user_id parameter
    3. **Task Creation**: Fixed to use `derived_user_id` instead of undefined `user_id`
  - Modified files:
    - `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py`:
      - Line 555: Added user_id param to delete_task
      - Line 597: Added user_id param to complete_task
      - Line 264: Fixed create broadcast to use derived_user_id
      - Line 571: Use provided user_id for delete notifications
      - Line 641: Use provided user_id for completion notifications
    - `agenthub_main/src/fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/crud_handler.py` (line 179: pass user_id to delete)
    - `agenthub_main/src/fastmcp/task_management/interface/api_controllers/task_api_controller/handlers/workflow_handler.py` (line 50: pass user_id to complete)
    - `agenthub_main/src/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/crud_handler.py`:
      - Lines 297-302: Extract and pass user_id for delete
      - Lines 316-323: Extract and pass user_id for complete
  - Impact: All task operations now properly broadcast with correct user_id for proper WebSocket notification delivery
- **Subtask API 404 Errors**: Fixed 404 errors on individual subtask endpoints by restarting system with proper table migrations
  - Root cause: Recent table rename from `task_subtasks` to `subtasks` required system restart to apply migrations
  - Solution: Restarted development environment to ensure database schema is up to date
  - API endpoints now working: `GET /api/v2/subtasks/{subtask_id}` returns 200 OK instead of 404
  - Impact: Frontend subtask components can now properly fetch individual subtask details
- **Task Description Character Limit**: Updated task description validation from 1000 to 2000 characters to match domain entity
  - Root cause: Domain entity (Task.py) allows 2000 chars but application layer still validated 1000 chars
  - Solution: Updated validation in application facade and use case to match ORM model (which is source of truth)
  - Modified files:
    - `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py` (lines 908-909, 925-926)
    - `agenthub_main/src/fastmcp/task_management/application/use_cases/create_task.py` (lines 43-44)
    - `agenthub_main/src/tests/unit/task_management/application/use_cases/create_task_test.py` (updated test to match 2000 char limit)
  - Impact: Tasks can now have descriptions up to 2000 characters as intended
- **Supabase Optimized Repository Test**: Fixed test failure in `supabase_optimized_repository_test.py` by removing non-existent `details` parameter from TaskEntity constructor
  - Root cause: `_model_to_entity_minimal` method was passing `details` parameter which doesn't exist in Task entity
  - Solution: Removed `details=task_model.details` from TaskEntity instantiation
  - Modified: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/orm/supabase_optimized_repository.py` (line 186 removed)
  - Impact: Test now passes successfully
- **TaskResponse DTO Progress History**: Fixed backend TaskResponse DTO to properly return progress_history instead of details field
  - Root cause: TaskResponse DTO was trying to access non-existent 'details' field from task entity's to_dict() method
  - Solution: Added progress_history and progress_count fields to TaskResponse, mapped task.get_progress_history_text() to details for backward compatibility
  - Impact: Frontend timeline visualization now receives proper progress_history data structure
  - Modified: `agenthub_main/src/fastmcp/task_management/application/dtos/task/task_response.py`
  - Testing: Added comprehensive tests verifying progress_history mapping and backward compatibility
- **Dependency Validation Service Test**: Fixed missing ID validator in test setup causing test failures
  - Root cause: DependencyValidationService requires IDValidator instance but tests weren't providing it
  - Solution: Added mock ID validator to both TestDependencyValidationService and TestDependencyValidationServiceIntegration setup methods
  - Modified: `agenthub_main/src/tests/unit/task_management/domain/services/test_dependency_validation_service.py`
  - Impact: Fixed 26 tests (24 previously passing, 2 integration tests failing)
- **WebSocket Integration Test**: Fixed incorrect patch path for get_session mock
  - Root cause: get_session is imported from database_config, not exported by websocket_routes
  - Solution: Changed patch path from 'fastmcp.server.routes.websocket_routes.get_session' to 'fastmcp.task_management.infrastructure.database.database_config.get_session'
  - Modified: `agenthub_main/src/tests/security/websocket/test_websocket_integration.py` (lines 209, 260, 401, 437)
- **WebSocket Performance Security Test**: Fixed User entity instantiation missing password_hash parameter
  - Root cause: User domain entity requires password_hash as mandatory field for security
  - Solution: Added `password_hash="hashed_password_123"` to all User instantiations in test
  - Fixed incorrect patch path for database session (from websocket_routes to database_config)
  - Modified: `agenthub_main/src/tests/security/websocket/test_performance_security.py`
- **Context Processor Test**: Fixed test_context_processor in test_hook_system_comprehensive.py
  - Root cause: Module import path issue when patching utils.context_injector
  - Solution: Mock utils.context_injector module in sys.modules before ContextProcessor imports it
  - Modified: `agenthub_main/src/tests/hooks/test_hook_system_comprehensive.py` (lines 244-277)

- **Hook E2E Test Fix**: Fixed dangerous bash command blocking test
  - Root cause: Test expected exit code 1 but hook returns exit code 2 for blocked operations
  - Updated test to expect exit code 2 for blocked commands instead of exit code 1
  - Enhanced CommandValidator to detect more dangerous commands (mkfs, dd, chmod on system files)
  - Modified: `agenthub_main/src/tests/hooks/test_hook_e2e.py` (lines 104-124)
  - Modified: `.claude/hooks/pre_tool_use.py` (CommandValidator class, lines 242-289)

- **Hook Integration Test**: Fixed test_env_file_protection_integration to handle SystemExit properly
  - Root cause: Hook calls sys.exit(2) for .env file blocking but test expected return value
  - Solution: Updated test to use pytest.raises(SystemExit) and check exit code is 2
  - Modified: `agenthub_main/src/tests/hooks/test_hook_integration.py` (lines 134-137)

- **Critical Test Parsing Bug**: Fixed missing FAILED and ERROR entries in test result parsing
  - Root cause: Bash subshell issue in pipeline preventing temp file population
  - Solution: Separated pytest execution from result parsing to avoid subshell scope issues
  - Impact: All FAILED tests now properly captured and cached in test-menu.sh
  - Modified: `scripts/test-menu.sh` (lines 260-277)

- **WebSocket Token Validation Test**: Fixed JWT decode error in auth websocket integration test
  - Added proper JWT decode mock to handle token validation flow
  - Mocked jwt.decode to return valid payload structure for test tokens
  - Modified: `agenthub_main/src/tests/integration/test_auth_websocket_integration.py`

- **Template Pattern Matching**: Fixed wildcard pattern matching in Template domain entity
  - Added fnmatch module for proper wildcard pattern support (e.g., `*.py` matches `test.py`)
  - Updated `_pattern_matches()` method to use `fnmatch.fnmatch()` instead of string contains logic
  - Fixed test to use valid wildcard patterns instead of reversed pattern/filename arguments
  - Modified: `agenthub_main/src/fastmcp/task_management/domain/entities/template.py`

- **Test Failures in HintGenerationService**: Fixed `test_generate_hints_success` test by correcting mock strategy
  - Changed mocking approach to use `self.service.strategy` instead of `self.service` for internal method patches
  - Aligned with other working tests in the same file that use strategy-based mocking
  - Modified: `agenthub_main/src/tests/unit/task_management/application/services/hint_generation_service_test.py`

- **SQLite Datetime Adapter Deprecation Warnings**: Fixed Python 3.12+ deprecation warnings
  - Resolved 164 deprecation warnings in SQLite datetime handling
  - Added explicit datetime adapters and converters using ISO format
  - Implemented Python version detection (only affects Python 3.12+)
  - Maintains backward compatibility with older Python versions
  - Modified: `agenthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py`

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