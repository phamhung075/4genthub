# Documentation for .claude/hooks/pre_tool_use.py

## Purpose
Pre-tool validation hook that enforces file system protection rules and documentation requirements before any file operation is executed by Claude Code.

## Key Features

### 1. Claude File Edit Protection
- Checks `ENABLE_CLAUDE_EDIT` environment variable from `.env.claude`
- Blocks editing of `.claude` files when flag is disabled
- Provides clear error messages for permission denied scenarios

### 2. File System Protection Rules

#### Root Directory Restrictions
- **Blocks creation of files in project root** (except those in `.allowed_root_files`)
- **Blocks creation of folders in project root** (except specific allowed folders)
- Configurable via `.allowed_root_files` configuration file

#### Environment File Protection
- **Blocks creation of `.env*` files in subdirectories** (security measure)
- **Blocks reading of `.env*` files** (except `.env.claude` which is allowed)
- Prevents accidental exposure of sensitive configuration

#### Documentation Directory Rules
- **Enforces single `ai_docs` folder** - blocks creation of `docs` folders
- **Kebab-case enforcement** for ai_docs subdirectories (lowercase-with-dashes)
- **Pattern validation**: Only allows letters and dashes in folder names

#### File Type Restrictions
- **`.md` files**: Only allowed in `ai_docs/` directory
- **`.sh` scripts**: Must be placed in `scripts/` directory  
- **Test files**: Must follow paths defined in `.valid_test_paths`
- **`.venv` folder**: Only one allowed at `dhafnck_mcp_main/.venv`
- **`logs` folder**: Only one allowed in project root

### 3. Selective Documentation Enforcement
- Checks if documentation exists in `ai_docs/_absolute_docs/`
- Only blocks modifications to files that have existing documentation
- Uses session tracking (2-hour windows) to avoid disrupting active work
- Folder documentation support via `f_index.md` files

### 4. Bash Command Validation
- Validates bash commands for compliance with file system rules
- Checks for forbidden operations (mkdir in root, creating .env files, etc.)
- Provides detailed error messages for auto-correction

## Configuration Files

### `.allowed_root_files`
Lists files that are allowed to be created/modified in the project root:
- Core project files (README.md, CHANGELOG.md, etc.)
- Configuration files (.gitignore, .env.claude, etc.)
- Package management files (package.json, requirements.txt, etc.)

### `.valid_test_paths`
Defines allowed paths for test file creation:
- `dhafnck_mcp_main/src/tests/`
- `dhafnck-frontend/src/tests/`
- `dhafnck-frontend/src/__tests__/`
- Other test directories as configured

## Error Messages

The hook provides detailed error messages to help AI auto-correct:

1. **Root file creation blocked**:
   ```
   BLOCKED: Cannot create files in project root
   Allowed files: [list from .allowed_root_files]
   Suggested locations: ai_docs/, scripts/, src/
   ```

2. **Invalid folder name pattern**:
   ```
   BLOCKED: Folder name must use kebab-case pattern
   Invalid: 'FolderName'
   Valid: 'folder-name'
   ```

3. **Wrong file location**:
   ```
   BLOCKED: .md files must be in ai_docs/
   Current: /wrong/path/file.md
   Correct: ai_docs/appropriate-folder/file.md
   ```

4. **Documentation required**:
   ```
   WARNING: File has documentation that should be updated
   Documentation: ai_docs/_absolute_docs/path/to/file.md
   Consider updating documentation when modifying this file
   ```

## Session Tracking

- Tracks modified files/folders in 2-hour sessions
- Prevents repeated blocking during active work
- Session data stored in: `{AI_DATA}/hook_sessions/current_session.json`
- Automatic session expiry after 2 hours of inactivity

## Dependencies

- `utils/env_loader.py` - Environment variable loading from `.env.claude`
- `utils/docs_indexer.py` - Documentation tracking and requirements
- `utils/session_tracker.py` - Session management for workflow continuity

## Exit Codes

- `0` - Validation passed, operation allowed
- `1` - General validation failure
- `2` - Permission denied (e.g., ENABLE_CLAUDE_EDIT=false)

## Important Notes

1. **Order of Validation**:
   - First checks ENABLE_CLAUDE_EDIT for .claude files
   - Then validates file paths and names
   - Finally checks documentation requirements

2. **Special Exceptions**:
   - `_absolute_docs` and `_obsolete_docs` folders are exempt from kebab-case rule
   - `.env.claude` is allowed while other `.env*` files are blocked
   - Files in active session bypass documentation checks

3. **Purpose**: 
   - Maintains clean project structure
   - Prevents accidental security issues
   - Ensures documentation stays synchronized with code
   - Guides AI to follow project conventions automatically

## Last Updated
2025-09-10 - Complete documentation of all validation rules and features