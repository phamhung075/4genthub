# Changelog

All notable changes to the DhafnckMCP AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v1.0.0.html)

## [Unreleased]

### Fixed
- **🔧 Subtask JSON View Button Consolidation** - 2025-09-07
  - Removed duplicate JSON button from subtask row actions in LazySubtaskList
  - Consolidated JSON view functionality in SubtaskDetailsDialog using proper tab interface
  - Fixed RawJSONDisplay prop mismatch (`data` vs `jsonData`) that was causing crashes
  - Enhanced JSON display in dialog with proper title and filename for subtasks  
  - JSON view is now only accessible through the details dialog, providing a cleaner and more consistent UI
  - Files modified:
    - `dhafnck-frontend/src/components/LazySubtaskList.tsx` - Removed JSON button and inline display
    - `dhafnck-frontend/src/components/SubtaskDetailsDialog.tsx` - Fixed RawJSONDisplay props
- **🔧 Subtask Completion Progress Percentage Auto-Setting** - 2025-09-07
  - Fixed issue where `progress_percentage` was not automatically set to 100% when subtasks were completed
  - Updated `Subtask.complete()` method to automatically set `progress_percentage = 100`
  - Updated `Subtask.update_status()` method to automatically set `progress_percentage = 100` when status changes to 'done'  
  - Updated `Subtask.update_status()` method to reset `progress_percentage = 0` when status changes to 'todo' from completed state
  - Updated MCP `complete_subtask` handler to include `progress_percentage = 100` in completion data
  - Ensures consistent behavior across all completion methods (MCP, API, direct domain calls)
  - Backend now handles this automatically without relying on frontend to send correct values
  - Files modified:
    - `dhafnck_mcp_main/src/fastmcp/task_management/domain/entities/subtask.py`
    - `dhafnck_mcp_main/src/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers/crud_handler.py`

- **🔧 LazySubtaskList Critical Syntax & Display Issues** - 2025-09-07
  - Fixed critical try-catch block syntax error that was causing frontend crashes around line 179
  - Fixed `getSubtask()` function to use dedicated `/api/v2/subtasks/{subtask_id}` endpoint instead of filtering list results  
  - Fixed `deleteSubtask()` function signature to use correct parameter (only `subtask_id`, not `task_id, subtask_id`)
  - Updated `Subtask` interface to include missing fields (`progress_percentage`, `progress_notes`, `created_at`, `updated_at`, `completed_at`)
  - "View details" button now correctly displays subtask information instead of showing "nothing"
  - All detailed fields (description, progress notes, assignees) now display properly in SubtaskDetailsDialog
  - Updated test cases to match corrected API signatures
  - **Added Raw JSON Display**: Implemented consistent JSON view functionality for subtasks like other components
  - Added new JSON button in subtask actions with expandable Raw JSON display using RawJSONDisplay component
  - JSON data displays in expandable table rows with copy-to-clipboard functionality
  - Consistent with BranchDetailsDialog and SubtaskDetailsDialog JSON display patterns

### Added
- **✨ Modern Token Management UI** - 2025-09-07
  - Complete redesign with shadcn/ui components and grid layouts
  - Enhanced scope selection with visual feedback and presets
  - MCP configuration code profile with VS Code-style display
  - Responsive design with gradient effects and animations

- **🎬 VideoText & FallingGlitch Components** - 2025-09-07
  - Dynamic text effects with multiple variants (gradient, animated, holographic)
  - Animated binary background effect for login page
  - Theme-aware and performance optimized

- **🔐 Complete Keycloak Authentication System** - 2025-09-07
  - Full integration with token validation and user management
  - Multi-realm support with role-based access control
  - Automated user account setup and email verification

- **📧 Environment Variable Controls** - 2025-09-07
  - EMAIL_VERIFIED_AUTO for automatic email verification
  - Improved Docker environment validation and configuration

- **🔐 Resource-Specific CRUD Authorization** - 2025-09-07
  - Granular permission system with role-based access
  - Context-aware authorization for all MCP operations
  - Enhanced security across all endpoints

- **🚀 CapRover CI/CD Deployment System** - 2025-09-06
  - Automated deployment pipeline with health checks
  - Multi-environment support (dev, staging, production)
  - Docker-based deployment with monitoring integration

- **🏗️ Global Context Nested Categorization** - 2025-09-05
  - Hierarchical context organization with inheritance
  - Enhanced data structure for multi-tenant operations
  - Improved context resolution and caching

- **🧪 Comprehensive MCP Testing Protocol** - 2025-09-05/06
  - 45 iterations of comprehensive testing (iterations 32-45 achieved 100% success)
  - 7-phase testing covering all system components
  - Production-certified stability with zero critical failures

- **⚡ Performance & UI Enhancements** - 2025-09-05
  - HolographicPriorityBadge with shimmer animations
  - Enhanced progress bars and visual indicators
  - RawJSONDisplay components for debugging
  - Improved task and subtask management interfaces

### Security
- **🔒 Credential Security Hardening** - 2025-09-07
  - Removed all hardcoded credentials from Keycloak scripts
  - Environment variable-based credential management
  - Enhanced .gitignore and security documentation

- **🔒 Critical JWT Security Fix** - 2025-09-03
  - Fixed user ID extraction vulnerability in JWT processing
  - Eliminated potential cross-user data access
  - Comprehensive security testing across all endpoints

- **🔒 Backend Authentication Integration** - 2025-09-03
  - Integrated Keycloak authentication for all MCP endpoints
  - Multi-tenant security enforcement
  - Production-ready secure backend implementation

### Fixed
- **🐛 Authentication & Setup Issues** - 2025-09-07
  - Resolved account setup problems with automated fixes
  - Fixed CORS configuration for multi-origin support
  - Improved Docker environment validation

- **🐛 Critical Data Consistency Issues** - 2025-09-06
  - Fixed branch deletion system data inconsistency
  - Resolved orphaned task dependencies
  - Enhanced database integrity checks

- **🔧 Configuration & Environment Fixes** - 2025-09-06/07
  - Aligned environment files across all deployment modes
  - Fixed port configuration conflicts
  - Improved Docker container health checks
  - Resolved V2 API routing import errors

- **🗄️ Database & Connection Improvements** - 2025-09-04
  - Enhanced connection pool optimization
  - Fixed timeout handling for long operations
  - Improved error recovery mechanisms

### Changed
- **🏗️ DDD Architecture Verification** - 2025-09-05
  - Complete Domain-Driven Design compliance audit
  - Enhanced separation of concerns across layers
  - Improved code organization and maintainability

- **🔧 Unified Authentication System** - 2025-09-03
  - Consolidated authentication approach using Keycloak exclusively
  - Streamlined token validation and user management
  - Enhanced multi-tenant support

### Removed
- **🧹 Documentation & Code Cleanup** - 2025-09-03
  - Removed 47+ obsolete troubleshooting files
  - Eliminated duplicate configuration guides
  - Deprecated MVP mode functionality
  - Cleaned legacy authentication code

- **🗑️ Cache & Temporary File Cleanup** - 2025-09-07
  - Removed Python `__pycache__` directories
  - Cleaned `.pytest_cache` directories
  - Eliminated potential sensitive data from cache files

## Key System Features

### Authentication & Authorization
- Role hierarchy: mcp-admin → mcp-developer → mcp-tools → mcp-user
- JWT-based authentication with Keycloak integration
- Multi-tenant security with complete user isolation
- Resource-specific CRUD permissions

### Architecture
- Domain-Driven Design (DDD) implementation
- 4-tier context hierarchy (Global → Project → Branch → Task)
- Vision System AI enrichment and workflow guidance
- MCP tool orchestration with 60+ specialized agents

### Infrastructure
- Docker-based deployment with comprehensive monitoring
- Multi-environment support (development, staging, production)
- Automated CI/CD pipeline with CapRover integration
- Database optimization with connection pooling

### Testing & Quality Assurance
- 7-phase comprehensive testing protocol
- Production-certified stability (100% success rate maintained)
- Automated quality checks and performance monitoring
- Security validation and compliance testing