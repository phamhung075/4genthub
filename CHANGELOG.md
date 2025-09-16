# Changelog

All notable changes to the DhafnckMCP AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed - 2025-09-16
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