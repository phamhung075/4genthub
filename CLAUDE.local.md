# DhafnckMCP Project - Local AI Agent Rules

## About This File
This file (`CLAUDE.local.md`) contains **local, environment-specific rules** for AI agents working on this project. It is NOT checked into version control and complements the main `CLAUDE.md` file.

- **CLAUDE.md**: Main AI agent instructions (checked into repository, shared across team)
- **CLAUDE.local.md**: Local environment rules and overrides (NOT checked in, local only)

Key Points:
- On dev, The system should be using Keycloak for authentication and local PostgreSQL docker for the database
- Keycloak is the source of truth for user authentication
- Both frontend and backend trust the same Keycloak user identity
- docker-menu.sh option R for rebuild
- The ORM model should be the source of truth. Update the database table to match the ORM model definition, not the other way
  around
## Core Project Structure
**Source Code Paths:**
- `dhafnck-frontend/` - Frontend (React/TypeScript, port 3800)
- `dhafnck_mcp_main/src/` - Backend (Python/FastMCP/DDD)
- `dhafnck_mcp_main/src/tests/` - Test files

**Important Paths to Ignore:**
- `00_RESOURCES/*` - Reference materials only
- `00_RULES/*` - Legacy rules (use CLAUDE.md instead)

## System Architecture
**4-Tier Context Hierarchy:**
```
GLOBAL → PROJECT → BRANCH → TASK
```
- Inheritance flows downward
- UUID-based identification
- Auto-creation on demand

**Tech Stack:**
- **Backend**: Python, FastMCP, SQLAlchemy, DDD patterns
- **Frontend**: React, TypeScript, Tailwind CSS
- **Database**: SQLite (dev) / PostgreSQL (prod) (`/data/dhafnck_mcp.db`)
- **Auth**: Keycloak (source of truth) with JWT tokens
- **Container**: Docker with docker-compose orchestration
- **Ports**: 8000 (backend), 3800 (frontend)
- **MCP Tools**: 15+ categories, 43+ specialized agents
- **Vision System**: AI enrichment, workflow guidance, progress tracking

**Docker Configurations:**
- PostgreSQL Local (recommended for dev)
- Supabase Cloud
- Redis + PostgreSQL
- Redis + Supabase
- Menu system: `docker-system/docker-menu.sh` (option R for rebuild)

## 🏗️ System Architecture (Local Environment Details)

### Domain-Driven Design (DDD) Structure
The system follows strict DDD patterns with clear separation of concerns:
- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases and application services
- **Infrastructure Layer**: Database, external services, and repositories
- **Interface Layer**: MCP controllers, HTTP endpoints, and UI

### 4-Tier Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
- Each level inherits from the parent level
- Global context is user-scoped (multi-tenant isolation)
- Automatic context creation on demand
- UUID-based identification throughout

### Local System Information
- **Backend URL**: http://localhost:8000
- **Frontend URL**: http://localhost:3800
- **Database Path**: `/data/dhafnck_mcp.db` (Docker volume)
- **Documentation**: `dhafnck_mcp_main/docs/`
- **Tests**: `dhafnck_mcp_main/src/tests/`
- **Docker Menu**: `docker-system/docker-menu.sh`
- **Environment Config**: `.env` file in project root

### Security Guidelines (Local Environment)
- **Authentication**: Keycloak is source of truth for all user identity
- **Credentials**: NEVER expose passwords - all stored in `.env` file only
- **Environment Variables**: Access secrets via environment variables only
- **Token Handling**: JWT tokens expire and refresh automatically
- **Multi-tenant Isolation**: Each user's data is completely isolated
- **Audit Trails**: All operations logged for security compliance

## Documentation Architecture
```
dhafnck_mcp_main/docs/
├── CORE ARCHITECTURE/        # System understanding
├── DEVELOPMENT GUIDES/        # Developer resources
├── OPERATIONS/               # Deployment & config
├── TROUBLESHOOTING/          # Problem resolution
├── api-integration/          # API documentation
├── architecture-design/      # DDD and system design
├── context-system/           # Context management docs
├── issues/                   # Issue tracking and resolution
├── migration-guides/         # Version migration guides
├── reports-status/           # Status reports and analysis
├── setup-guides/             # Setup and configuration
└── testing-qa/               # Testing documentation
```

### Documentation Structure Rules
- **Test files**: Must write in correct location (`dhafnck_mcp_main/src/tests/`)
- **Document files**: Must write in correct location (`dhafnck_mcp_main/docs/`)
- **Organization**: Create subfolders for easy management
- **Index files**: Create/update `index.md` for all document folders
- **NO LOOSE DOCUMENTATION IN ROOT**: All documentation MUST be in appropriate folders:
  - Troubleshooting guides → `dhafnck_mcp_main/docs/troubleshooting-guides/`
  - Migration guides → `dhafnck_mcp_main/docs/migration-guides/`
  - Issue documentation → `dhafnck_mcp_main/docs/issues/`
  - Reports & status → `dhafnck_mcp_main/docs/reports-status/`
  - Operations guides → `dhafnck_mcp_main/docs/operations/`
  - **ONLY 5 .md FILES ALLOWED IN PROJECT ROOT**: 
    - README.md (project overview)
    - CHANGELOG.md (project-wide changes)
    - TEST-CHANGELOG.md (tests changes)
    - CLAUDE.md (AI agent instructions - checked in)
    - CLAUDE.local.md (local AI rules - not checked in)

## Essential Rules

### 🚨 CRITICAL: Changelog Updates
**MANDATORY**: AI agents MUST update CHANGELOG.md when making ANY project changes:
- Add new features under `### Added`
- Document fixes under `### Fixed`
- Note breaking changes under `### Changed`
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Include file paths modified/created
- Describe impact and testing performed

### Context Management
- `manage_context` - Unified context operations (includes delegation, inheritance)
- Note: `manage_hierarchical_context` has been deprecated, use `manage_context` instead
- Always use `git_branch_id` (UUID), not branch names

### Database Modes
- Docker/Local Dev: Use Docker database (`/data/dhafnck_mcp.db`)
- Test Mode: Isolated test database (`dhafnck_mcp_test.db`)
- Rebuild Docker to view code changes

### Documentation & Changelog Rules
- Check `docs/index.md` first for structure
- **MANDATORY**: Update CHANGELOG.md for ALL project changes
- **CHANGELOG LOCATION RULES**:
  - **Use ONLY ONE CHANGELOG.md in project root** (`/home/daihungpham/agentic-project/CHANGELOG.md`)
  - **NEVER create CHANGELOG.md in subdirectories** (except frontend has its own for frontend-specific changes)
  - All project-wide changes go in root CHANGELOG.md
  - Frontend maintains separate `dhafnck-frontend/CHANGELOG.md` for frontend-only changes
  - CHANGELOG.md is the official project changelog (checked into repository)
  - CLAUDE.local.md is for local AI agent rules and instructions only
  - Never add version history or change logs to CLAUDE.local.md

### Recent Changes
**Note**: All changelog entries have been moved to the main CHANGELOG.md file where they belong.
See CHANGELOG.md for version history and recent changes.

### Testing
- Location: `dhafnck_mcp_main/src/tests/`
- Categories: unit/, integration/, e2e/, performance/
- Run tests before committing changes
- Write tests for new features

### AI Workflow Rules
1. **ALWAYS update CHANGELOG.md for project changes, NEVER CLAUDE.local.md**
2. Check `docs/index.md` first for documentation structure
3. Test all code examples before including in documentation
4. Follow Domain-Driven Design (DDD) patterns in codebase
5. Use existing libraries and utilities - check package.json/requirements
6. Follow existing code conventions and patterns

## System Behaviors
- Boolean parameters accept multiple formats: "true", "1", "yes", "on"
- Array parameters accept JSON strings, comma-separated, or arrays
- Task completion auto-creates context if missing (working as designed)

## Quick Reference
1. **UPDATE CHANGELOG.md for ALL project changes (NOT CLAUDE.local.md)**
2. Check existing docs structure before creating files
3. Follow DDD patterns in codebase
4. Test code examples before documentation
5. Use Docker menu: `docker-system/docker-menu.sh`
6. CLAUDE.local.md is for AI rules only, not for changelog entries
7. Refer to CLAUDE.md for comprehensive Vision System documentation

## Important Notes
- **ALWAYS** remove backward or legacy code on working, update to last version code -> CLEAN code
- **NEVER** create files unless absolutely necessary
- **NEVER** create test files, scripts for test or debug, document on root project
- **ALWAYS** prefer editing existing files over creating new ones
- **NEVER** proactively create documentation unless explicitly requested
- Do what has been asked; nothing more, nothing less
- Rebuild Docker to view code changes in container mode
- **TEST-CHANGELOG.md Updates**: AI agents MUST update TEST-CHANGELOG.md when making changes to test files. Document all test additions, modifications, or fixes in TEST-CHANGELOG.md (located in project root). This rule belongs in CLAUDE.local.md, NOT in CLAUDE.md.
- Use the Task tool to launch the Claude Code troubleshooter agent

## Git Commit Guidelines

Follow [Conventional Commits 1.0.0](https://conventionalcommits.org/) specification:

**Format**: `<type>[optional scope]: <description>`

**Common Types**:
- `feat:` - New feature
- `fix:` - Bug fix  
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

**Examples**:
- `feat(auth): add JWT token validation`
- `fix(ui): resolve login form validation error`
- `docs: update API documentation`
- `test: add unit tests for context management`