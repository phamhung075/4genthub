# agenthub Project - Local AI Agent Rules
DATABASE agenthub
rolname = 'agenthub_user'

## About This File
This file (`CLAUDE.local.md`) contains **local, environment-specific rules** for AI agents working on this project. It is NOT checked into version control and complements the main `CLAUDE.md` file.

- **CLAUDE.md**: Main AI agent instructions (checked into repository, shared across team)
- **CLAUDE.local.md**: Local environment rules and overrides (NOT checked in, local only)

Key Points:
- On dev, The system should be using Keycloak for authentication and local PostgreSQL docker for the database
- On dev, for restart after change code Bash(echo "R" | ./docker-system/docker-menu.sh) 
- The server is started with fastmcp.server.mcp_entry_point
- Keycloak is the source of truth for user authentication
- Both frontend and backend trust the same Keycloak user identity
- docker-menu.sh option R for rebuild
- The ORM model should be the source of truth. Update the database table to match the ORM model definition, not the other way
  around
## Core Project Structure
**Source Code Paths:**
- `agenthub-frontend/` - Frontend (React/TypeScript, port 3800)
- `agenthub_main/src/` - Backend (Python/FastMCP/DDD)
- `agenthub_main/src/tests/` - Test files

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
- **Database**: SQLite (dev) / PostgreSQL (prod) (`/data/agenthub.db`)
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
- **Database Path**: `/data/agenthub.db` (Docker volume)
- **Documentation**: `ai_docs/`
- **Tests**: `agenthub_main/src/tests/`
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

### AI Documentation System Overview
The documentation system provides intelligent tracking, automatic indexing, and selective enforcement to help AI agents maintain high-quality documentation while not disrupting workflow.

```
ai_docs/
├── _absolute_docs/           # File-specific documentation (marks importance)
│   ├── scripts/             # Documentation for scripts folder
│   │   ├── f_index.md       # Folder documentation (marks folder as important)
│   │   └── docker-menu.sh.md # Specific file documentation
│   └── claude-hooks-pre-tool-use.py.md  # Hook documentation
├── _obsolete_docs/          # Auto-archived when source files deleted
├── index.json               # Auto-generated documentation index (by hooks)
├── api-integration/         # API documentation
├── authentication/          # Auth system documentation
├── claude-code/             # Claude Code specific docs
├── context-system/          # Context management docs
├── core-architecture/       # System architecture (kebab-case)
├── development-guides/      # Developer resources (kebab-case)
├── issues/                  # Issue tracking and resolution
├── keycloak/                # Keycloak integration docs
├── migration-guides/        # Version migration guides
├── operations/              # Deployment & configuration
├── reports-status/          # Status reports and analysis
├── setup-guides/            # Setup and configuration
├── testing-qa/              # Testing documentation
└── troubleshooting-guides/ # Problem resolution (kebab-case)
```

### Key Features for AI Agents

#### 1. Fast Context Access
- **index.json**: Machine-readable index with all documentation metadata
- **Automatic updates**: Hooks update index.json when docs change
- **Quick lookup**: AI can quickly find relevant documentation via index
- **MD5 hashing**: Track document changes and versions

#### 2. Selective Documentation Enforcement
- **_absolute_docs pattern**: Files with docs here are marked as "important"
- **Smart blocking**: Only blocks modifications if documentation exists
- **Session tracking**: 2-hour sessions prevent workflow disruption
- **f_index.md**: Mark entire folders as important with folder documentation

#### 3. Automatic Documentation Management
- **Post-tool hook**: Updates index.json after any ai_docs changes
- **Obsolete tracking**: Moves docs to _obsolete_docs when source deleted
- **Warning system**: Non-blocking warnings for missing documentation
- **Path mapping**: `ai_docs/_absolute_docs/{path}/file.ext.md` for `/path/file.ext`

### Documentation Structure Rules
- **Test files**: Must write in correct location (`agenthub_main/src/tests/`)
- **Document files**: Must write in correct location (`ai_docs/`)
- **Kebab-case folders**: All ai_docs subfolders must use lowercase-with-dashes
- **Organization**: Create subfolders for easy management
- **Index files**: Auto-generated index.json (not index.md anymore)
- **NO LOOSE DOCUMENTATION IN ROOT**: All documentation MUST be in appropriate folders:
  - Troubleshooting guides → `ai_docs/troubleshooting-guides/`
  - Migration guides → `ai_docs/migration-guides/`
  - Issue documentation → `ai_docs/issues/`
  - Reports & status → `ai_docs/reports-status/`
  - Operations guides → `ai_docs/operations/`
  - **ONLY 5 .md FILES ALLOWED IN PROJECT ROOT**: 
    - README.md (project overview)
    - CHANGELOG.md (project-wide changes)
    - TEST-CHANGELOG.md (tests changes)
    - CLAUDE.md (AI agent instructions - checked in)
    - CLAUDE.local.md (local AI rules - not checked in)

### How AI Should Use Documentation System

1. **Check index.json for existing docs**:
   - Located at `ai_docs/index.json`
   - Contains all documentation with metadata
   - Use to quickly find relevant documentation

2. **Create absolute documentation for important files**:
   - Place in `ai_docs/_absolute_docs/` with path structure
   - This marks the file as important and requires doc updates
   - Example: For `scripts/test.sh` → `ai_docs/_absolute_docs/scripts/test.sh.md`

3. **Follow kebab-case for all folders**:
   - Valid: `api-integration`, `test-results`, `setup-guides`
   - Invalid: `API_Integration`, `Test Results`, `SetupGuides`

4. **Respect session tracking**:
   - First modification might trigger warning
   - Subsequent modifications in same session won't be blocked
   - Sessions last 2 hours for uninterrupted work

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
- Docker/Local Dev: Use Docker database (`/data/agenthub.db`)
- Test Mode: Isolated test database (`agenthub_test.db`)
- Rebuild Docker to view code changes

### Documentation & Changelog Rules
- Check `ai_docs/index.md` first for structure
- **MANDATORY**: Update CHANGELOG.md for ALL project changes
- **CHANGELOG LOCATION RULES**:
  - **Use ONLY ONE CHANGELOG.md in project root** (`/home/daihungpham/agentic-project/CHANGELOG.md`)
  - **NEVER create CHANGELOG.md in subdirectories** (except frontend has its own for frontend-specific changes)
  - All project-wide changes go in root CHANGELOG.md
  - Frontend maintains separate `agenthub-frontend/CHANGELOG.md` for frontend-only changes
  - CHANGELOG.md is the official project changelog (checked into repository)
  - CLAUDE.local.md is for local AI agent rules and instructions only
  - Never add version history or change logs to CLAUDE.local.md

### Recent Changes
**Note**: All changelog entries have been moved to the main CHANGELOG.md file where they belong.
See CHANGELOG.md for version history and recent changes.

### Testing
- Location: `agenthub_main/src/tests/`
- Categories: unit/, integration/, e2e/, performance/
- Run tests before committing changes
- Write tests for new features

### AI Workflow Rules
1. **ALWAYS update CHANGELOG.md for project changes, NEVER CLAUDE.local.md**
2. Check `ai_docs/index.md` first for documentation structure
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
2. Check existing ai_docs structure before creating files
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
- `ai_docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

**Examples**:
- `feat(auth): add JWT token validation`
- `fix(ui): resolve login form validation error`
- `ai_docs: update API documentation`
- `test: add unit tests for context management`

## 🔒 File System Protection Rules (Enhanced 2025-09-10)

### Root Directory Restrictions
- **NO file creation in root** except files listed in `.allowed_root_files`
- **NO folder creation in root** - all folders should already exist
- **Allowed root files only**: README.md, CHANGELOG.md, TEST-CHANGELOG.md, CLAUDE.md, CLAUDE.local.md
- **Configuration files**: `.allowed_root_files` and `.valid_test_paths` control restrictions

### File Type Restrictions
- **ALL .md files** must be in `ai_docs/` (except allowed root files)
- **ALL test files** must be in directories listed in `.valid_test_paths`
- **ALL .sh scripts** must be in `scripts/` or `docker-system/`
- **Only ONE .venv** allowed at `agenthub_main/.venv`
- **Only ONE logs folder** allowed in project root
- **NO .env* files** can be read or created (security protection)

### ai_docs Folder Rules
- **Subdirectories must use kebab-case**: lowercase-with-dashes (e.g., `api-integration`, `setup-guides`)
- **Special folders allowed**: `_absolute_docs` and `_obsolete_docs` (exempt from kebab-case)
- **NO uppercase folders** except legacy that are being migrated
- **17 standard folders** maintained in ai_docs:
  - api-behavior, api-integration, assets, authentication, claude-code, context-system,
  - core-architecture, development-guides, integration-guides, issues, migration-guides,
  - operations, product-requirements, reports-status, setup-guides, testing-qa, troubleshooting-guides

## 📚 Documentation System (Automatic)

### Documentation Structure
- **index.json**: Automatically generated index of all documentation (replaces index.md)
  - Generated by: `python .claude/hooks/utils/docs_indexer.py`
  - Contains: file count, directory structure, hashes, timestamps
  - Updates: Automatically via post-tool hook when ai_docs changes
- **_absolute_docs/**: File-specific documentation following project structure
  - Pattern: `ai_docs/_absolute_docs/path/to/file.ext.md` documents `path/to/file.ext`
  - Example: `scripts/test.sh` → `ai_docs/_absolute_docs/scripts/test.sh.md`
- **_obsolete_docs/**: Automatic archival when source files are deleted
- **f_index.md**: Folder documentation marking important directories

### Selective Documentation Enforcement
- **Smart Blocking**: Only blocks modifications to files/folders WITH existing documentation
- **Session Tracking**: 2-hour sessions prevent repeated blocking during active work
- **User-Controlled**: Files are marked important by creating documentation for them
- **Non-Disruptive**: Files without docs can be modified freely

### How Documentation Enforcement Works
1. **Important Files**: If `ai_docs/_absolute_docs/path/to/file.md` exists, the file is important
2. **Important Folders**: If `ai_docs/_absolute_docs/path/f_index.md` exists, the folder is important
3. **First Access**: Blocks on first modification in new session, requires doc update
4. **Continued Work**: After first access in session, allows continued modifications
5. **Auto-Indexing**: Changes to ai_docs automatically update index.json

### Environment Paths (Loaded from .env)
- **AI_DATA**: Directory for AI-generated data and logs (default: `logs`)
- **AI_DOCS**: Documentation directory (default: `ai_docs`)
- **Status Line**: Always displays these paths for AI memory/context

### Hook System Files
Located in `.claude/hooks/`:
- **pre_tool_use.py**: Enforces all file system protection rules
- **post_tool_use.py**: Updates documentation index and tracks changes
- **utils/session_tracker.py**: Manages 2-hour work sessions
- **utils/docs_indexer.py**: Generates and maintains index.json
- **utils/env_loader.py**: Loads environment variables safely
- **status_lines/status_line.py**: Displays environment paths in status

### Configuration Files
- **.allowed_root_files**: Lists files allowed in project root
- **.valid_test_paths**: Lists directories where test files can be created

### Error Messages
All blocking operations provide:
- Clear error description
- Specific file/folder path that violated rules
- Suggestions for correction
- Examples of valid patterns

### Quick Reference Commands
```bash
# Update documentation index manually
python .claude/hooks/utils/docs_indexer.py

# Check allowed root files
cat .allowed_root_files

# Check valid test paths
cat .valid_test_paths

# View current documentation structure
ls -la ai_docs/_absolute_docs/
ls -la ai_docs/_obsolete_docs/
```

## Important Instruction Reminders
- Do what has been asked; nothing more, nothing less
- **NEVER** create files unless absolutely necessary
- **ALWAYS** prefer editing existing files over creating new ones  
- **NEVER** proactively create documentation unless explicitly requested
- **NEVER** create test files, scripts for test or debug, document on root project
- **ALWAYS** remove backward or legacy code when working, update to latest version code → CLEAN code
- docker-menu.sh option R for rebuild to view code changes in dev mode, need start docker posgresql for have data dev
- Use the Task tool to launch specialized agents when appropriate