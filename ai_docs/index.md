# DhafnckMCP Documentation

Welcome to the DhafnckMCP Multi-Project AI Orchestration Platform documentation.

## 📚 Documentation Hub

### 🚀 Getting Started
- [README](../README.md) - Project overview and quick start
- [Database Setup](../DATABASE_SETUP.md) - Database configuration guide
- [Environment Setup](../ENV_SETUP_README.md) - Environment setup instructions
- [Docker Quick Start](../docker/README_DOCKER.md) - Docker deployment guide
- [Configuration Guide](configuration.md) - Environment variables and settings

### 🏗️ Architecture & Design
Foundational design principles, architectural patterns, and technical decisions for the DhafnckMCP platform.

- [**Architecture & Design Overview**](architecture-design/README.md) - Complete architectural documentation hub
- [System Architecture](architecture-design/architecture.md) - Overall system architecture and components
- [Technical Architecture](architecture-design/Architecture_Technique.md) - Detailed technical architecture with DDD
- [**Agent Library Cleanup Recommendations**](architecture-design/agent-library-cleanup-recommendations.md) - **NEW 2025-09-06** - Analysis and recommendations to optimize agent library from 69 to 43 core agents
- [**Authentication System Architecture (Current)**](CORE ARCHITECTURE/authentication-system-current.md) - **UPDATED 2025-09-05** - Complete current authentication implementation with Keycloak
- [**Authentication System Architecture (Legacy)**](CORE ARCHITECTURE/authentication-system.md) - Previous JWT-based authentication documentation
- [**Keycloak Authentication Setup**](setup-guides/keycloak-authentication-setup.md) - **NEW** - Step-by-step Keycloak configuration guide
- [**Authentication Configuration**](api-integration/configuration.md#authentication-configuration) - **UPDATED** - Uses `AUTH_ENABLED` and `AUTH_PROVIDER` (deprecated `MCP_AUTH_ENABLED` removed)
- [**Dual Authentication System**](architecture/dual-authentication-system.md) - Complete dual auth system supporting multiple providers
- [**Dual Authentication Flow Diagrams**](architecture/dual-authentication-flow-diagram.md) - Visual authentication flow diagrams through DDD layers
- [Domain-Driven Design](architecture-design/domain-driven-design.md) - DDD implementation patterns
- [AI Context Realistic Approach](architecture-design/AI-CONTEXT-REALISTIC-APPROACH.md) - Practical AI context strategies
- [**User Isolation Architecture**](architecture/user-isolation-architecture.md) - Multi-tenant data isolation architecture

### 🔄 Migration & Updates
System migration guides for upgrading and transitioning between versions and configurations.

- [**Migration Guides Overview**](migration-guides/README.md) - Complete migration documentation hub
- [**User Isolation Migration Guide**](migration-guides/user-isolation-migration-guide.md) - Complete guide for multi-tenant migration
- [Hierarchical Context Migration](migration-guides/HIERARCHICAL_CONTEXT_MIGRATION.md) - Basic to hierarchical context migration
- [Unified Context Migration Guide](migration-guides/unified_context_migration_guide.md) - Unified context system migration
- [Context Auto-Detection Fix](migration-guides/CONTEXT_AUTO_DETECTION_FIX.md) - Enhanced auto-detection with error handling

### 📖 API & Integration
Comprehensive API documentation, integration guides, and configuration references.

- [**API & Integration Overview**](api-integration/README.md) - Complete API documentation hub
- [API Reference](api-integration/api-reference.md) - Complete MCP tools and HTTP API documentation
- [Configuration Guide](api-integration/configuration.md) - Environment variables and settings
- [Parameter Type Validation](api-behavior/parameter-type-validation.md) - Strict type validation for MCP tool parameters
- [Parameter Type Conversion](api-behavior/parameter-type-conversion-verification.md) - Automatic parameter type conversion
- [JSON Parameter Parsing](api-behavior/json-parameter-parsing.md) - JSON string parameter handling


### 🔗 Context System
Comprehensive documentation for the DhafnckMCP hierarchical context management system.

- [**Context System Overview**](context-system/index.md) - ⭐ **START HERE** - Complete context system documentation index
- [**Complete Database Schema**](context-system/context-database-schema-complete.md) - ⭐ **CRITICAL** - Exact field mappings for all context levels
- [**Context Data Models**](context-system/CONTEXT_DATA_MODELS.md) - ⭐ **NEW** - Comprehensive data structures and update patterns for each hierarchy level
- [Understanding MCP Context](context-system/00-understanding-mcp-context.md) - What the context system actually is
- [Architecture](context-system/01-architecture.md) - System design and components
- [API Reference](context-system/03-api-reference.md) - Complete API documentation
- [Implementation Guide](context-system/04-implementation-guide.md) - How to implement context
- [Workflow Patterns](context-system/05-workflow-patterns.md) - Common usage patterns

### 🧪 Testing & Quality
Comprehensive testing documentation, QA procedures, and test results.

- [**Testing & QA Overview**](testing-qa/README.md) - Complete testing documentation hub
- [Testing Guide](testing-qa/testing.md) - Unit and integration testing strategies with TDD patterns
- [Test Results and Issues](testing-qa/test-results-and-issues.md) - Comprehensive test execution results
- [MCP Tools Test Issues](testing-qa/mcp-tools-test-issues.md) - Known MCP tool integration test issues
- [MCP Testing Report](testing-qa/MCP_TESTING_REPORT.md) - Detailed MCP tools testing results
- [PostgreSQL TDD Fixes](testing-qa/POSTGRESQL_TDD_FIXES_SUMMARY.md) - Test-driven development fixes
- [PostgreSQL Test Migration](testing-qa/POSTGRESQL_TEST_MIGRATION_SUMMARY.md) - Database test migration results
- [End-to-End Testing Guidelines](testing-qa/e2e/End_to_End_Testing_Guidelines.md) - E2E testing best practices
- [Context Resolution Tests Summary](testing-qa/context_resolution_tests_summary.md) - Context resolution test results
- [Context Resolution TDD Tests](testing-qa/context_resolution_tdd_tests.md) - TDD approach for context tests

### 🛠️ Development Guides
Technical development guides, implementation patterns, and best practices.

- [**Development Guides Overview**](development-guides/README.md) - Complete development documentation hub
- [**MCP Integration Guide**](DEVELOPMENT GUIDES/mcp-integration-guide.md) - Complete MCP client integration patterns and examples
- [Error Handling and Logging](development-guides/error-handling-and-logging.md) - Error handling patterns and logging strategies
- [ORM Agent Repository](development-guides/orm-agent-repository-implementation.md) - ORM-based repository patterns
- [Docker Deployment](development-guides/docker-deployment.md) - Production-ready Docker configurations

### 📋 Product Requirements
Product requirements, specifications, and strategic planning documents.

- [**Product Requirements Overview**](product-requirements/README.md) - Complete product requirements hub
- [Product Requirements Document (PRD)](product-requirements/PRD.md) - Complete product requirements and strategic objectives



### 🚨 Troubleshooting & Issues
Comprehensive troubleshooting documentation for diagnosing and resolving issues.

- [**Troubleshooting Overview**](troubleshooting-guides/README.md) - Complete troubleshooting documentation hub
- [**MCP Connection Issues Guide**](troubleshooting-guides/mcp-connection-issues.md) - Diagnose and fix MCP connection problems
- [Comprehensive Troubleshooting Guide](troubleshooting-guides/COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md) - Systematic problem diagnosis and solutions
- [Quick Troubleshooting Reference](troubleshooting-guides/TROUBLESHOOTING.md) - Common issues and quick fixes
- [**Issue Documentation**](issues/index.md) - Detailed documentation of significant issues and resolutions
  - [Database Schema Mismatch (2025-01-13)](issues/2025-01-13-database-schema-mismatch.md) - Critical context table schema fix

### 📊 Reports & Status
System status reports, documentation health checks, and implementation status updates.

- [**Reports & Status Overview**](reports-status/README.md) - Complete reports and status documentation hub
- [**Final Cleanup Report (2025-09-08)**](reports-status/final-cleanup-report-2025-09-08.md) - ⭐ **LATEST** - Comprehensive final cleanup operations summary with system integrity validation
- [Documentation Status Report](reports-status/DOCUMENTATION_STATUS_REPORT.md) - Latest documentation health check and coverage
- [Insights Found Parameter Fix](reports-status/INSIGHTS_FOUND_PARAMETER_FIX_SOLUTION.md) - Parameter validation solution implementation

### 🐳 Deployment & Operations
- **[Operations Overview](operations/index.md)** - Complete operations documentation hub
- [**MCP Registration System**](OPERATIONS/mcp-registration-system.md) - MCP client registration and session management
- [PostgreSQL Configuration Guide](operations/postgresql-configuration-guide.md) - Database setup and configuration
- [Docker Deployment](development-guides/docker-deployment.md) - Production Docker deployment
- [Docker Configuration](docker/config/README.md) - Docker configuration details
- [Scripts Documentation](operations/scripts-documentation.md) - Utility scripts guide

### 📂 Examples & Templates
- [Smart Home Example](../examples/smart_home/README.md) - Smart home integration example

## 🔗 Quick Links

- **🔒 User Isolation**: See [User Isolation Quick Reference](quick-guides/user-isolation-quick-reference.md) for multi-tenant patterns
- **🚨 Error Handling**: See [Error Handling and Logging](development-guides/error-handling-and-logging.md) for comprehensive error management
- **💾 Database Setup**: See [Database Setup Guide](../DATABASE_SETUP.md) for PostgreSQL configuration
- **📡 API Documentation**: See [API Reference](api-integration/api-reference.md) for MCP tools documentation
- **🐛 Troubleshooting**: See [Comprehensive Troubleshooting Guide](troubleshooting-guides/COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md)

## 📅 Recent Updates

### 2025-09-06
- **Agent Library Optimization**: Comprehensive analysis and recommendations to streamline agent library from 69 to 43 core agents (38% reduction)
  - **Identified Overlaps**: Analyzed functional overlaps across 8 major agent groups (Testing, Design, Strategy, Research, Security, Marketing, Documentation, Generic)
  - **Recommended Consolidations**: Detailed recommendations to remove 26 redundant agents while preserving all functionality
  - **Migration Strategy**: 3-phase implementation plan with low to high risk phases
  - **Maintainability Benefits**: Simplified maintenance, clearer agent selection, better system performance
  - **Documentation**: Created [Agent Library Cleanup Recommendations](architecture-design/agent-library-cleanup-recommendations.md) with complete analysis

### 2025-08-29
- **DDD Architecture Compliance Achieved**: Complete refactoring to implement proper Domain-Driven Design
  - **Controller Layer Separation**: Separated MCP controllers from frontend API controllers
  - **Route Reorganization**: Standardized naming convention for all route files
  - **API Controllers**: Created 6 new API controllers for proper DDD delegation
  - **Code Cleanup**: Removed obsolete components and unused functionality
  - **Documentation**: Updated DDD compliance documentation with current status
- **Modular Controller Architecture Implementation**: Refactored large monolithic controllers using factory pattern
  - **Task MCP Controller**: Decomposed 1800+ line controller into modular structure
  - **Subtask MCP Controller**: Decomposed 1407 line controller into specialized handlers
  - **Factory Pattern**: Implemented operation factories for centralized coordination
  - **Backward Compatibility**: Preserved all existing interfaces and import paths
  - **Maintainability**: Improved code organization and separation of concerns
- **Route File Standardization**: All route files now follow consistent "name + routes" naming pattern
- **Subtask Routes**: Added dedicated subtask management endpoints with full CRUD operations
- **Architecture Documentation**: Created comprehensive DDD compliance update report and modular controller architecture guide

### 2025-08-20
- **MCP Registration System**: Implemented proper `/register` endpoint for Claude MCP client compatibility
  - Created dedicated registration routes with session management
  - Added support for multiple registration paths
  - Returns MCP protocol-compliant responses
- **Authentication System Fixes**: Resolved JWT token validation issues
  - Fixed token type compatibility (accepts both `access` and `api_token`)
  - Fixed user ID field flexibility (checks both `sub` and `user_id`)
  - Fixed metadata validation errors with SQLAlchemy
- **Documentation Updates**: Comprehensive documentation for new systems
  - MCP Registration System documentation
  - Authentication System Architecture guide
  - MCP Integration Guide with examples
  - Troubleshooting guide for connection issues

### 2025-01-31
- **Major Documentation Reorganization**: Complete restructuring of documentation into logical categories
  - Created 9 new categorized subfolders: architecture-design, context-system, troubleshooting-guides, migration-guides, testing-qa, reports-status, development-guides, api-integration, product-requirements
  - Moved 28 loose markdown files into appropriate categories with dedicated README files
  - Updated all cross-references and maintained proper documentation hierarchy
- **Enhanced Navigation**: Added comprehensive README files for each category with clear descriptions
- **Better Discoverability**: Organized ai_docs into logical categories with consistent formatting and icons

### 2025-01-20
- **Boolean Parameter Fix**: Resolved validation issues for boolean string parameters
- **Auto-Context Creation**: Implemented automatic context creation for all entities
- **Context Synchronization**: Manual context updates sync to cloud automatically

### 2025-01-19
- **Task Completion Fix**: Tasks can now be completed without manual context creation
- **Unified Context Fix**: Resolved async/sync architecture issues in context system
- **Parameter Flexibility**: Added JSON string support for context data parameters

### 2025-01-18
- **4-Tier Context System**: Global→Project→Branch→Task hierarchy implemented
- **Database Enforcement**: Strict Docker DB usage for consistency
- **Documentation Cleanup**: Removed 45% of obsolete ai_docs while improving coverage

### Previous Updates
- Enhanced hierarchical context system with custom data fields
- PostgreSQL support with JSONB for better performance
- ORM-based agent repository implementation with comprehensive test suite
- Complete migration to 4-tier hierarchical context system
- Enhanced context auto-detection with comprehensive error handling
- Comprehensive testing guide with TDD patterns and performance testing
- Docker deployment guide with production-ready configurations

## 🤝 Contributing

Please see the project repository for guidelines on contributing to this project. Contact the maintainers for contribution guidelines.

## 📝 Documentation Standards

When adding new documentation:
1. Place files in appropriate category directories
2. Update this index with proper categorization
3. Follow existing naming conventions
4. Include clear descriptions and examples
5. Cross-reference related documentation
6. Test all code examples before inclusion

---
*Last Updated: 2025-01-31 - Major Documentation Reorganization & Category Structure Implementation*