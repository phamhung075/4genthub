# Changelog

All notable changes to the DhafnckMCP AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed
- **Hook System Message Loading**: Fixed critical issues with session start and configuration loading
  - Fixed session_start.py hook to properly load and display agent-specific initialization messages from session_start_messages.yaml
  - Integrated ConfigurationLoader class to manage YAML configuration files in hooks
  - Added AgentMessageProvider to detect session type and provide appropriate agent messages
  - Files: MODIFIED `.claude/hooks/session_start.py` (700 lines)
- **Last Prompt Storage for Status Line**: Fixed issue where last prompt was not being stored for status line display
  - Updated SessionTracker processor to properly store prompts when `store_last_prompt` flag is enabled
  - Modified ComponentFactory to pass `store_last_prompt` parameter to SessionTracker
  - Ensured prompts are saved to session JSON files for status line retrieval
  - Files: MODIFIED `.claude/hooks/user_prompt_submit.py`

### Added
- **MCP Hint Matrix System**: Comprehensive contextual hint system for MCP operations
  - Implemented MCP hint matrix providing validation hints for all MCP tool operations
  - Added mcp_hint_matrix.py module with tool/action mappings and contextual hint generation
  - Integrated hint matrix into pre_tool_use.py for pre-action validation hints
  - Integrated hint matrix into post_tool_use.py for post-action contextual hints
  - Created documentation: `ai_docs/claude-code/hook-message-flow-analysis.md`
  - Files: NEW `.claude/hooks/utils/mcp_hint_matrix.py` (505 lines), MODIFIED `.claude/hooks/pre_tool_use.py`, `.claude/hooks/post_tool_use.py`
- **Hook Configuration Files**: Essential YAML configurations for message display
  - Added pre_tool_messages.yaml, post_tool_messages.yaml for tool use messages
  - Added mcp_post_action_hints.yaml for post-action contextual hints
  - Files: NEW `.claude/hooks/config/*.yaml` (multiple configuration files)
- **Phase 6 Complete**: Production Deployment & Operations Infrastructure
  - Created comprehensive deployment manager (`docker-system/deployment-manager.sh`) with production, development, and database-only modes
  - Implemented real-time health monitoring system (`scripts/health-monitor.sh`) with performance metrics and alerting
  - Added legacy cleanup tool (`scripts/cleanup-legacy.sh`) with safe backup and restoration procedures
  - Enhanced Docker configurations with multi-stage optimized builds and security hardening
  - Comprehensive deployment documentation (`ai_docs/operations/phase-6-deployment-guide.md`)
  - Production-ready CI/CD pipeline validation and documentation
  - Enterprise-grade monitoring with JSON status reports and continuous health checks
  - Automated rollback capability with database backup integration
  - System resource monitoring (memory, disk, load average) with degradation alerts
  - Complete production deployment checklist and troubleshooting guides
- **Phase 3.1 Complete**: Consolidated Hint System with Factory Pattern
  - Created unified HintManager consolidating 3 hint services (HintGenerationService, WorkflowHintsSimplifier, HintOptimizer)
  - Implemented factory pattern with 4 strategies: domain, simplified, optimized, auto
  - Environment-driven configuration (HINT_STRATEGY, ENABLE_ULTRA_HINTS, HINT_MAX_HINTS)
  - 100% backward compatibility maintained through inheritance
  - Added AutoHintStrategy for automatic strategy selection based on environment
  - Integrated with domain service factory for dependency injection
  - Reduced code complexity while preserving all functionality
  - Files: NEW hint_manager.py (1,274 lines), MODIFIED hint_generation_service.py, workflow_hints_simplifier.py, domain_service_factory.py

### Changed
- **Refactored MCP Hint Matrix to Factory Pattern**: Improved hint system architecture
  - Created mcp_hint_matrix_factory.py with factory pattern loading from YAML configuration
  - Created comprehensive mcp_hint_matrix_config.yaml with all hint definitions
  - Separated configuration from logic for better maintainability
  - Updated pre_tool_use.py to use the new factory-based hint system
  - Files: NEW `.claude/hooks/utils/mcp_hint_matrix_factory.py` (349 lines), NEW `.claude/hooks/config/mcp_hint_matrix_config.yaml` (281 lines)
- Started hooks refactoring project Phase 1: Assessment & Cleanup
  - Completed Phase 1.1: Archived 4 clean architecture directories to archive_clean_attempt_20250116
  - Completed Phase 1.2: Created comprehensive backup in backup_20250116_refactor (14 hooks, 23 utils, configs)
  - Completed Phase 1.3: Created dependency map documenting all imports and dependencies
    - No circular dependencies found
    - Identified 2 core dependencies (env_loader, config_factory)
    - Documented consolidation opportunities for 23 utils modules

### Fixed
- Clarified post-tool-use hook architecture - keeping post_tool_use.py as the working version
- Test Iteration 36: Fixed failing integration tests (2025-09-16)
  - **test_mcp_authentication_fixes.py**: Fixed API calls from deprecated `manage_unified_context` to current `manage_context`
  - **create_project_test.py**: Fixed tests expecting branch name "main" as key instead of UUID in git_branchs dictionary
  - Updated tests to match current implementation where git_branchs uses UUID keys, not branch names
  - 91 tests remain to be fixed
  - post_tool_use.py (345 lines): Active, working hook with all features
  - post_tool_use_clean.py (172 lines): Incomplete refactor attempt with missing core module
  - Action taken: Removed post_tool_use_clean.py to avoid confusion

### Added
- Created comprehensive hooks architecture analysis documenting system complexity
  - Documented in ai_docs/claude-code/hooks-architecture-analysis.md
  - Identified 45+ Python files, 24 YAML configs, ~5000 lines of code
  - Found ~40% duplicate functionality across modules
- Implemented factory pattern refactoring for post_tool_use hook
  - Created post_tool_use_refactored.py with clean architecture
  - Reduced from 345 to 280 lines with better organization
  - Implemented ComponentFactory for dependency injection
  - Applied Single Responsibility Principle to components
- Created detailed 20-day refactoring plan with 6 phases
  - Documented in ai_docs/claude-code/hooks-refactoring-plan.md
  - Phase 1: Assessment & Cleanup (Day 1-2)
  - Phase 2: Core Infrastructure (Day 3-5)
  - Phase 3: Component Implementation (Day 6-10)
  - Phase 4: Hook Refactoring (Day 11-15)
  - Phase 5: Testing & Validation (Day 16-18)
  - Phase 6: Deployment (Day 19-20)
  - Expected outcomes: 50% code reduction, 87% duplication reduction, <10ms execution time
- Created comprehensive MCP tasks for hooks refactoring project
  - Task eb79363f: Phase 1.1 - Remove Incomplete Clean Architecture
  - Task b9a66b2b: Phase 1.2 - Backup Current Working System
  - Task 3f4420c8: Phase 1.3 - Create Dependency Map
  - Task dc9cf172: Phase 2.1 - Create Core Factory System
  - Task 6e17aced: Phase 3.1 - Consolidate Hint System
  - Task df216cc7: Phase 4 - Refactor Main Hooks (5 days)
  - Task d9fae890: Phase 5 - Testing & Validation (3 days)
  - Task 105fa334: Phase 6 - Deployment & Cleanup (2 days)
  - All tasks include complete implementation context and code examples

### Added - 2025-09-16
- Status Line v4: Real-time MCP connection status monitoring with intelligent caching
  - **Feature**: Live connection status display showing server connectivity, response times, and error states
  - **Format**: `🔗 MCP: ✅ Connected (http://localhost:8000) 2ms` (green) or `🔗 MCP: ❌ Connection Refused (http://localhost:9999)` (red)
  - **Caching**: 45-second cache duration to prevent excessive network calls (configurable via MCP_STATUS_CACHE_DURATION)
  - **Configuration**: MCP_SERVER_URL, MCP_CONNECTION_TIMEOUT (2.0s), MCP_STATUS_CACHE_DURATION (45s)
  - **Resilience**: Timeout handling, retry strategy, graceful fallback when requests library unavailable
  - **Authentication**: Detects auth-enabled vs auth-disabled servers, shows auth-specific errors
  - **Performance**: Uses fast /health endpoint (~2ms response time), intelligent error handling
  - **Files**: `.claude/status_lines/status_line_v4.py` (enhanced with MCP connection testing functions)
  - **Testing**: Comprehensive testing with connected/disconnected scenarios, cache validation, error handling

### Added - 2025-09-16
- **Status Line Project & Branch Display**: Enhanced status line with project name and git branch context
  - **Project Name Display**: Added `get_project_name()` function that extracts project name from git remote origin URL
  - **Fallback Logic**: Falls back to current directory name if git remote not available
  - **Enhanced Branch Display**: Updated `get_git_branch()` to use `git branch --show-current`
  - **Detached HEAD Support**: Handles detached HEAD state with commit hash display
  - **Color Coding**: Branch types color coded (main=bold green, feature=blue, hotfix=red, develop=yellow, detached=magenta)
  - **Status Indicators**: Shows git status with ±N format for modified files
  - **Configuration Options**: Environment variables for customizing display:
    * `STATUS_SHOW_PROJECT=true/false` - Show/hide project name (default: true)
    * `STATUS_SHOW_BRANCH=true/false` - Show/hide git branch (default: true)
    * `STATUS_SHORT_PROJECT_NAME=true/false` - Truncate long project names (default: false)
  - **Format**: `◆ Claude • 📁 project-name • 🌿 main ±5 • 🎯 Active: coding-agent • 📊 data 📚 ai_docs`
  - **Performance**: 2-second timeout on git commands, no impact on status line speed
  - **Error Handling**: Graceful fallbacks for non-git directories and command failures
  - **Files**: Modified `.claude/status_lines/status_line.py` with comprehensive documentation

### Fixed - 2025-09-16
- **Project API 422 Errors**: Fixed FastAPI form data handling in project creation and update endpoints
  - **Issue**: Frontend sending `application/x-www-form-urlencoded` data was causing 422 validation errors
  - **Root Cause**: FastAPI route parameters not configured to accept form data using `Form()` dependencies
  - **Solution**: Updated `/dhafnck_mcp_main/src/fastmcp/server/routes/project_routes.py` to use proper Form dependencies
  - **Changes**:
    - Create: `name: str` → `name: str = Form(...)`, `description: str = ""` → `description: str = Form("")`
    - Update: `name: Optional[str] = None` → `name: Optional[str] = Form(None)`, `description: Optional[str] = None` → `description: Optional[str] = Form(None)`
  - **Impact**: Project creation and update from frontend now work correctly, no more 422 errors on form submissions
- Database schema: Renamed 'data' column to 'unified_context_data' for clarity
- Docker environment: Added CONTAINER_ENV for proper runtime detection
- Session messages: Dynamic agent detection for all 33 agents
- Logging system: Environment-aware file/console logging with rotation
- CLAUDE.md: Corrected system instructions, removed non-existent tool references
- Task completion: Fixed "Cannot transition from done to done" error when updating completed tasks
  - Modified `dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers/crud_handler.py`
  - Now uses `facade.complete_task` directly instead of `facade.update_task` with status="done"
  - Allows updating context and summaries for already-completed tasks
- Frontend global context editor: Fixed non-functional raw JSON editing capability
  - **Issue**: Edit button was functional but showed "coming soon" placeholder instead of actual editing
  - **Solution**: Implemented complete raw JSON editor with validation, formatting, and error handling
  - **Files**: `dhafnck-frontend/src/components/GlobalContextDialog.tsx`, `dhafnck-frontend/src/tests/components/GlobalContextDialog.test.tsx`
  - **Features**: 400px textarea with monospace font, live JSON validation, Format JSON button, character/line count, comprehensive error states
  - **Testing**: All 15 component tests pass, frontend builds successfully
- Task status transitions: Fixed invalid "in_progress to in_progress" transition error blocking task updates
  - **Issue**: Business validator incorrectly prevented updating in_progress tasks with new details/context
  - **Root Cause**: Missing "in_progress" in valid transitions list for "in_progress" status
  - **Solution**: Added "in_progress" as valid transition from "in_progress" in both validation methods
  - **Files**: `dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators/business_validator.py:155,174`
  - **Testing**: Created comprehensive test suite with 6 test cases covering all transition scenarios
  - **Impact**: Users can now update task details and context while task remains in_progress without status errors
- MCP Authentication: Simplified authentication by removing Keycloak fallback and displaying clear errors
  - **Issue**: Complex authentication flow with Keycloak fallback was unnecessary and confusing
  - **Solution**: Simplified to .mcp.json-only authentication with prominent status line error display
  - **Files**: `.claude/hooks/utils/mcp_client.py`, `.claude/hooks/core_clean_arch/exceptions.py`, `.claude/status_lines/status_line_v4.py`
  - **Changes**: Removed all Keycloak configuration and logic, added MCPAuthenticationError exception, enhanced status line to show authentication errors
  - **Testing**: Verified authentication works with .mcp.json token, error messages display correctly when token is missing or invalid
  - **Impact**: Users get clear visual feedback when MCP authentication is misconfigured, simplified codebase with single authentication method

### Added - 2025-09-16
- Complete agent library: 33 specialized agents with unique configurations
- Centralized message system for all user-facing hooks
- Environment detection utility for Docker vs local
- Comprehensive test suites for logging and database
- Hook configuration factory pattern: Complete refactoring to centralized YAML-based configuration
  - **NEW**: Created `utils/config_factory.py` - Centralized factory for all hook configuration with caching and fallbacks
  - **NEW**: Created 10 comprehensive YAML configuration files:
    - `error_messages.yaml` - All error messages with hints and examples
    - `warning_messages.yaml` - Non-blocking warning messages
    - `info_messages.yaml` - Informational messages and status updates
    - `hint_messages.yaml` - Contextual hints for AI agents
    - `session_messages.yaml` - Session lifecycle messages
    - `system_config.yaml` - System-wide settings and defaults
    - `pre_tool_messages.yaml` - Pre-tool execution messages
    - `post_tool_messages.yaml` - Post-tool completion messages
    - `docs_messages.yaml` - Documentation indexer messages
    - `status_line_messages.yaml` - Status line indicators
  - **REFACTORED**: Updated ALL hook files to use ConfigFactory pattern:
    - `pre_tool_use.py` - Updated imports to use ConfigFactory
    - `post_tool_use.py` - Updated imports to use ConfigFactory
    - `utils/hint_bridge.py` - Refactored to use ConfigFactory for messages
    - `utils/role_enforcer.py` - Updated to use ConfigFactory
    - `utils/mcp_post_action_hints.py` - Refactored to use ConfigFactory
  - **BACKWARDS COMPATIBLE**: Made `config/messages.py` a compatibility wrapper with deprecation warnings
  - **BENEFITS**: Centralized configuration, intelligent caching, fallback mechanisms, consistent message formatting

## [2.0.0] - 2025-09-15

### Major Features
- **Dynamic Tool Enforcement v2.0**: Permission system based on agent responses (replaces YAML configs)
- **Vision System**: AI enrichment with workflow guidance and progress tracking
- **Token Economy**: 95% token savings through ID-based delegation
- **Complete Agent Library**: 33 agents across 12 categories (Development, Testing, Design, Security, etc.)

### Breaking Changes
- Removed all backward compatibility and legacy code
- SQLite only for pytest, PostgreSQL required for dev/production
- CLAUDE.md is single source of truth for AI instructions

## [1.5.0] - 2025-09-14

### Core Systems
- **MCP Task Management**: Full CRUD with subtasks and progress tracking
- **4-Tier Context Hierarchy**: GLOBAL → PROJECT → BRANCH → TASK with inheritance
- **Unified Context API**: Single interface for all hierarchy levels
- **Documentation System**: Auto-indexing with selective enforcement

### Infrastructure
- Keycloak authentication with JWT tokens
- Docker menu system for container management
- Multi-tenant data isolation per user
- Frontend (React/TypeScript:3800) and Backend (FastMCP:8000)

## [1.0.0] - 2025-09-13

### Foundation
- Domain-Driven Design architecture
- PostgreSQL database with migrations
- Initial 10 agents for core functionality
- Docker containerization
- Basic authentication system

## Key Statistics
- **Iterations**: 105+ documented improvements
- **Agents**: 33 specialized agents
- **Token Savings**: 95% through optimizations
- **Architecture**: 4-tier context hierarchy
- **Categories**: 12 agent categories, 15+ tool types

## Quick Setup
```bash
cp .env.sample .env
./docker-system/docker-menu.sh  # Option R for rebuild
# Backend: http://localhost:8000
# Frontend: http://localhost:3800
```

---
*For detailed history, see git commits or CHANGELOG.md.backup. Major releases and breaking changes only.*