#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///

"""
Pre-tool use hook for Claude AI to enforce file system protection rules.

This hook runs before any tool execution and validates:
1. File/folder creation restrictions in project root
2. Environment file access protection
3. Documentation folder structure enforcement
4. Dangerous command prevention (rm -rf, etc.)
5. File naming uniqueness across the project

The hook blocks operations that violate project structure rules and
provides clear error messages to guide the AI toward correct behavior.
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path

# Import the AI_DATA path loader for logging
sys.path.insert(0, str(Path(__file__).parent))
from utils.env_loader import get_ai_data_path, is_claude_edit_enabled
try:
    from utils.docs_indexer import check_documentation_requirement
except ImportError:
    check_documentation_requirement = None
try:
    from utils.session_tracker import is_file_in_session, is_folder_in_session, add_modified_file, add_modified_folder
except ImportError:
    is_file_in_session = None
    is_folder_in_session = None
    add_modified_file = None
    add_modified_folder = None

# Import the new context injection system
try:
    from utils.context_injector import inject_context_sync
    CONTEXT_INJECTION_ENABLED = True
except ImportError:
    inject_context_sync = None
    CONTEXT_INJECTION_ENABLED = False

# Import MCP task validator for lifecycle hints
try:
    from utils.mcp_task_validator import inject_mcp_hints
    MCP_VALIDATION_ENABLED = True
except ImportError:
    inject_mcp_hints = None
    MCP_VALIDATION_ENABLED = False

# Import MCP hint matrix for comprehensive validation
try:
    from utils.mcp_hint_matrix import inject_matrix_hints
    MCP_MATRIX_ENABLED = True
except ImportError:
    inject_matrix_hints = None
    MCP_MATRIX_ENABLED = False

# Import hint bridge to display pending hints from post_tool_use
try:
    from utils.hint_bridge import get_pending_hints
    HINT_BRIDGE_ENABLED = True
except ImportError:
    get_pending_hints = None
    HINT_BRIDGE_ENABLED = False

def load_allowed_root_files():
    """
    Load allowed root files from .claude/hooks/config/__claude_hook__allowed_root_files config file.
    Falls back to default list if file doesn't exist.

    Returns:
        list: List of filenames that are allowed in the project root.
              These names should be unique across the entire project.
    """
    project_root = Path.cwd()
    allowed_files_path = project_root / '.claude' / 'hooks' / 'config' / '__claude_hook__allowed_root_files'
    
    # Default allowed files - only essential config and documentation files
    # These files should ONLY exist in the project root, nowhere else
    default_allowed = [
        'README.md', 'CHANGELOG.md', 'TEST-CHANGELOG.md', 
        'CLAUDE.md', 'CLAUDE.local.md', '.gitignore',
        'package.json', 'package-lock.json', 'requirements.txt',
        'pyproject.toml', 'poetry.lock', 'Pipfile', 'Pipfile.lock',
        'docker-compose.yml', 'Dockerfile', '.dockerignore',
        'Makefile', 'setup.py', 'setup.cfg', '__claude_hook__allowed_root_files',
        '__claude_hook__valid_test_paths', '__claude_hook__hint_message.yaml'
    ]
    
    if allowed_files_path.exists():
        try:
            with open(allowed_files_path, 'r') as f:
                lines = f.readlines()
                # Parse non-empty, non-comment lines
                allowed_files = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        allowed_files.append(line)
                
                # Always include __claude_hook__allowed_root_files itself
                if '__claude_hook__allowed_root_files' not in allowed_files:
                    allowed_files.append('__claude_hook__allowed_root_files')
                
                return allowed_files if allowed_files else default_allowed
        except Exception:
            return default_allowed
    
    return default_allowed

def load_valid_test_paths():
    """
    Load valid test paths from .claude/hooks/config/__claude_hook__valid_test_paths config file.
    Falls back to default list if file doesn't exist.

    Returns:
        list: List of directory paths where test files are allowed.
    """
    project_root = Path.cwd()
    test_paths_file = project_root / '.claude' / 'hooks' / 'config' / '__claude_hook__valid_test_paths'
    
    # Default test paths
    default_paths = [
        'dhafnck_mcp_main/src/tests',
        'dhafnck-frontend/src/tests'
    ]
    
    if test_paths_file.exists():
        try:
            with open(test_paths_file, 'r') as f:
                lines = f.readlines()
                # Parse non-empty, non-comment lines
                test_paths = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        test_paths.append(line)
                
                return test_paths if test_paths else default_paths
        except Exception:
            return default_paths
    
    return default_paths

def check_documentation_enforcement(file_path):
    """
    Check if a file has existing documentation that must be updated.
    Only blocks if:
    1. Documentation exists in _absolute_docs
    2. File is not already in current session
    
    Returns:
        tuple (should_block, doc_path, is_folder)
    """
    if not file_path:
        return (False, None, False)
    
    path_obj = Path(file_path)
    ai_docs_path = Path.cwd() / 'ai_docs' / '_absolute_docs'
    
    # Skip if in ai_docs itself
    if 'ai_docs' in path_obj.parts:
        return (False, None, False)
    
    # Check for folder documentation (f_index.md)
    if path_obj.is_dir():
        try:
            folder_doc = ai_docs_path / path_obj.relative_to(Path.cwd()) / 'f_index.md'
        except ValueError:
            # If path is not relative to cwd, use the path as is
            folder_doc = ai_docs_path / Path(*path_obj.parts[1:]) / 'f_index.md' if path_obj.is_absolute() else ai_docs_path / path_obj / 'f_index.md'
        if folder_doc.exists():
            # Check if folder is in current session
            if is_folder_in_session and is_folder_in_session(path_obj):
                return (False, str(folder_doc), True)  # Don't block, already working on it
            return (True, str(folder_doc), True)  # Block, documentation exists
    else:
        # Check for file documentation
        doc_name = f"{path_obj.name}.md"
        try:
            doc_path = ai_docs_path / path_obj.relative_to(Path.cwd()).parent / doc_name
        except ValueError:
            # If path is not relative to cwd, handle absolute paths
            if path_obj.is_absolute():
                doc_path = ai_docs_path / Path(*path_obj.parts[1:]).parent / doc_name
            else:
                doc_path = ai_docs_path / path_obj.parent / doc_name
        
        if doc_path.exists():
            # Check if file is in current session
            if is_file_in_session and is_file_in_session(path_obj):
                return (False, str(doc_path), False)  # Don't block, already working on it
            return (True, str(doc_path), False)  # Block, documentation exists
    
    return (False, None, False)

def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    
    Blocks commands like:
    - rm -rf /
    - rm -fr ~
    - rm --recursive --force
    - Any recursive rm targeting critical paths
    
    Args:
        command (str): The bash command to validate
        
    Returns:
        bool: True if the command is dangerous and should be blocked
    """
    # Normalize command by removing extra spaces and converting to lowercase
    normalized = ' '.join(command.lower().split())
    
    # Pattern 1: Standard rm -rf variations
    patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, rm -Rf, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',  # rm --recursive --force
        r'\brm\s+--force\s+--recursive',  # rm --force --recursive
        r'\brm\s+-r\s+.*-f',  # rm -r ... -f
        r'\brm\s+-f\s+.*-r',  # rm -f ... -r
    ]
    
    # Check for dangerous patterns
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    
    # Pattern 2: Check for rm with recursive flag targeting dangerous paths
    dangerous_paths = [
        r'/',           # Root directory
        r'/\*',         # Root with wildcard
        r'~',           # Home directory
        r'~/',          # Home directory path
        r'\$HOME',      # Home environment variable
        r'\.\.',        # Parent directory references
        r'\*',          # Wildcards in general rm -rf context
        r'\.',          # Current directory
        r'\.\s*$',      # Current directory at end of command
    ]
    
    if re.search(r'\brm\s+.*-[a-z]*r', normalized):  # If rm has recursive flag
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True
    
    return False

def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access ANY .env* files containing sensitive data.
    Blocks reading all .env files and creation of .env files in subfolders.
    
    Protection rules:
    1. Blocks reading ANY file starting with .env (except .env.sample)
    2. Blocks creation of .env* files in subfolders (must be in root)
    3. Blocks bash commands that try to access .env files
    
    Args:
        tool_name (str): Name of the tool being used (Read, Write, Bash, etc.)
        tool_input (dict): Parameters passed to the tool
        
    Returns:
        bool or str: True if access should be blocked, 
                    'subfolder_env' if trying to create .env in subfolder,
                    False otherwise
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            path_obj = Path(file_path)
            
            # Block ANY file that starts with .env (except .env.sample and .env.claude)
            if path_obj.name.startswith('.env') and not path_obj.name.endswith('.sample') and not path_obj.name == '.env.claude':
                return True
            
            # Block creation of .env* files in subfolders (only allow in root)
            if tool_name == 'Write' and path_obj.name.startswith('.env'):
                # Get project root (where .git exists)
                project_root = Path.cwd()
                if path_obj.parent.resolve() != project_root:
                    return 'subfolder_env'
        
        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect ANY .env* file access (but allow .env.sample and .env.claude)
            # Skip check if command contains .env.claude
            if '.env.claude' not in command:
                env_patterns = [
                    r'\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # Any .env* file but not .env.sample or .env.claude
                    r'cat\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # cat .env*
                    r'echo\s+.*>\s*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # echo > .env*
                    r'touch\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # touch .env*
                    r'cp\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # cp .env*
                    r'mv\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # mv .env*
                    r'vim\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # vim .env*
                    r'nano\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # nano .env*
                    r'less\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # less .env*
                    r'more\s+.*\.env[^\s]*(?<!\.sample)(?<!\.claude)',  # more .env*
                ]
                
                for pattern in env_patterns:
                    if re.search(pattern, command):
                        return True
    
    return False

def is_prohibited_file_creation(tool_name, tool_input):
    """
    Check if tool is trying to create prohibited files or folders.
    
    Validation rules:
    1. NO folders can be created in project root by AI
    2. Only files listed in __claude_hook__allowed_root_files can be created in root
    3. Files with names from __claude_hook__allowed_root_files cannot exist in subfolders (unique names)
    4. ai_docs folder can only exist in project root
    5. 'docs' folders are prohibited - must use 'ai_docs' instead
    6. ALL .md files must be in ai_docs folder (except root allowed ones)
    7. Test files must be in dhafnck_mcp_main/src/tests or dhafnck-frontend/src/tests
    8. Only one .venv allowed in dhafnck_mcp_main/.venv
    9. Only one logs folder allowed in project root
    
    Args:
        tool_name (str): Name of the tool being used (Write, Bash, etc.)
        tool_input (dict): Parameters passed to the tool
        
    Returns:
        str or False: Type of violation or False if allowed
    """
    if tool_name in ['Write', 'Bash']:
        if tool_name == 'Write':
            file_path = tool_input.get('file_path', '')
            if not file_path:
                return False
            
            path_obj = Path(file_path)
            project_root = Path.cwd()
            
            # Load allowed root files
            allowed_root_files = load_allowed_root_files()
            
            # Check if creating file in root directory
            if path_obj.parent.resolve() == project_root:
                if path_obj.name not in allowed_root_files:
                    return 'root_file'
            else:
                # Check if trying to create a file with same name as allowed root files in subfolders
                # These names should be unique to root
                if path_obj.name in allowed_root_files:
                    return 'unique_root_file'
            
            # Check if creating ai_docs in subfolder (only allow in root)
            if 'ai_docs' in path_obj.parts[:-1]:  # ai_docs in path but not the file name
                pass  # This is OK - files inside ai_docs
            elif path_obj.name == 'ai_docs' or '/ai_docs/' in str(path_obj):
                if path_obj.parent != project_root:
                    return 'subfolder_ai_docs'
            
            # Check if creating docs folder (should use ai_docs instead)
            # Exception: Allow _absolute_docs and _obsolete_docs within ai_docs
            if ('_absolute_docs' not in str(path_obj) and '_obsolete_docs' not in str(path_obj)):
                if path_obj.name == 'docs' or '/docs/' in str(path_obj):
                    return 'docs_folder'
            
            # Check for .md files - must be in ai_docs (except root allowed)
            if path_obj.suffix == '.md':
                # Check if it's in root and allowed
                if path_obj.parent.resolve() == project_root:
                    if path_obj.name not in allowed_root_files:
                        return 'md_not_in_ai_docs'
                # Check if it's in ai_docs
                elif 'ai_docs' not in path_obj.parts:
                    return 'md_not_in_ai_docs'
            
            # Check for subdirectory naming convention in ai_docs - must be kebab-case (lowercase-with-dashes)
            # Exception: Allow _absolute_docs and _obsolete_docs special folders
            if 'ai_docs' in path_obj.parts:
                # Get the index of ai_docs in the path
                ai_docs_index = path_obj.parts.index('ai_docs')
                # Check all subdirectories after ai_docs
                for i in range(ai_docs_index + 1, len(path_obj.parts) - 1):  # -1 to exclude the filename
                    part = path_obj.parts[i]
                    # Allow special underscore folders
                    if part in ['_absolute_docs', '_obsolete_docs']:
                        continue
                    # Check if subdirectory follows kebab-case pattern: lowercase letters and hyphens only
                    # Valid: "api-integration", "test-results", "documentation"
                    # Invalid: "API_Integration", "Test Results", "Documentation123"
                    if not re.match(r'^[a-z]+(-[a-z]+)*$', part):
                        return 'invalid_ai_docs_folder_name'
            
            # Check for test files - must be in specific test directories
            if ('test_' in path_obj.name or '_test.' in path_obj.name or 
                path_obj.name.endswith('.test.py') or path_obj.name.endswith('.test.js') or
                path_obj.name.endswith('.test.ts') or path_obj.name.endswith('.spec.js') or
                path_obj.name.endswith('.spec.ts')):
                # Load valid test paths from config
                valid_test_paths = load_valid_test_paths()
                if not any(test_path in str(path_obj) for test_path in valid_test_paths):
                    return 'test_wrong_location'
            
            # Check for .venv - only allowed in dhafnck_mcp_main/.venv
            if '.venv' in str(path_obj) or path_obj.name == '.venv':
                if str(path_obj) != str(project_root / 'dhafnck_mcp_main' / '.venv'):
                    return 'venv_wrong_location'
            
            # Check for logs folder - only allowed in root
            if path_obj.name == 'logs' and path_obj.parent != project_root:
                return 'logs_not_in_root'
            
            # Check for .sh files - must be in scripts folder
            if path_obj.suffix == '.sh':
                if 'scripts' not in path_obj.parts and 'docker-system' not in path_obj.parts:
                    return 'sh_not_in_scripts'
        
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            
            # Check for mkdir commands
            if 'mkdir' in command:
                # Block ANY folder creation in root directory
                # Pattern: mkdir [options] folder_name (where folder_name has no /)
                # Matches: mkdir test, mkdir -p test, but NOT mkdir test/sub
                if re.search(r'mkdir\s+(?:-[pm]\s+)?(?!.*/)[^/\s]+(?:\s|$)', command):
                    return 'root_folder'
                
                # Block docs folder creation anywhere (except _absolute_docs and _obsolete_docs)
                if re.search(r'mkdir\s+.*docs', command):
                    # Allow special documentation folders
                    if '_absolute_docs' not in command and '_obsolete_docs' not in command:
                        return 'docs_folder'
                
                # Block ai_docs in subfolders (must be in root only)
                if re.search(r'mkdir\s+.*/ai_docs', command):
                    return 'subfolder_ai_docs'
            
            # Check for file creation in root via bash
            # Patterns: touch file.txt (no path), echo > file.txt (redirect to root file)
            if re.search(r'touch\s+[^/]+$', command) or re.search(r'>\s*[^/]+$', command):
                return 'root_file'
            
            # Check for .md file creation outside ai_docs
            if re.search(r'(touch|>|echo.*>).*\.md', command):
                if 'ai_docs' not in command and not any(f in command for f in ['README.md', 'CHANGELOG.md', 'CLAUDE.md']):
                    return 'md_not_in_ai_docs'
            
            # Check for test file creation in wrong location
            if re.search(r'(touch|>).*test[_\-].*\.(py|js|ts)', command):
                valid_test_paths = load_valid_test_paths()
                if not any(test_path in command for test_path in valid_test_paths):
                    return 'test_wrong_location'
            
            # Check for .venv creation in wrong location
            if 'python -m venv' in command or 'virtualenv' in command:
                if 'dhafnck_mcp_main/.venv' not in command:
                    return 'venv_wrong_location'
            
            # Check for logs folder creation outside root
            if re.search(r'mkdir\s+.*/logs', command):
                return 'logs_not_in_root'
            
            # Check for .sh file creation outside scripts folder
            if re.search(r'(touch|>|echo.*>).*\.sh', command):
                if 'scripts' not in command and 'docker-system' not in command:
                    return 'sh_not_in_scripts'
    
    return False

def main():
    """
    Main entry point for the pre-tool use hook.
    
    This function:
    1. Receives tool call data from Claude via stdin
    2. Validates the tool operation against all protection rules
    3. Blocks prohibited operations with specific error messages
    4. Logs allowed operations to AI_DATA directory
    5. Exits with code 0 (allow) or 2 (block with error message)
    """
    try:
        # Read JSON input from stdin containing tool name and parameters
        input_data = json.load(sys.stdin)
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        
        # HINT BRIDGE: Display any pending hints from previous operations
        if HINT_BRIDGE_ENABLED and get_pending_hints:
            try:
                pending_hints = get_pending_hints()
                if pending_hints:
                    # Display hints that were generated after the last tool use
                    print(pending_hints, file=sys.stderr)
            except Exception:
                pass  # Don't block on hint display errors
        
        # NOTE: MCP hints moved to post_tool_use.py for better timing
        # Pre-tool validation focuses on blocking dangerous operations
        # Post-tool hints provide reminders about what to do next
        
        # CONTEXT INJECTION: Inject relevant context for MCP tools
        if CONTEXT_INJECTION_ENABLED and inject_context_sync and tool_name.startswith('mcp__'):
            try:
                # Inject context synchronously (uses cached or fresh data)
                context = inject_context_sync(tool_name, tool_input)
                if context:
                    # Log that context was injected (for debugging)
                    log_dir = get_ai_data_path()
                    context_log_path = log_dir / 'context_injection.log'
                    with open(context_log_path, 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - Injected context for {tool_name}: {len(str(context))} bytes\n")
            except Exception as e:
                # Log error but don't block the operation
                log_dir = get_ai_data_path()
                error_log_path = log_dir / 'context_injection_errors.log'
                with open(error_log_path, 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Error injecting context for {tool_name}: {e}\n")
        
        # VALIDATION STEP 0: Check if editing .claude files is allowed
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            if file_path and '.claude' in file_path:
                if not is_claude_edit_enabled():
                    print("BLOCKED: Editing .claude files is disabled", file=sys.stderr)
                    print("Set ENABLE_CLAUDE_EDIT=true in .env.claude to allow editing", file=sys.stderr)
                    sys.exit(2)
        
        # VALIDATION STEP 1: Check for .env file access (security protection)
        env_check = is_env_file_access(tool_name, tool_input)
        if env_check == 'subfolder_env':
            print("BLOCKED: .env* files must be created in project root only", file=sys.stderr)
            print("Place environment files in the project root directory", file=sys.stderr)
            sys.exit(2)
        elif env_check:
            print("BLOCKED: Access to .env* files containing sensitive data is prohibited", file=sys.stderr)
            print("Use .env.sample for template files instead", file=sys.stderr)
            sys.exit(2)
        
        # VALIDATION STEP 2: Check for prohibited file/folder creation
        creation_check = is_prohibited_file_creation(tool_name, tool_input)
        if creation_check == 'root_file':
            print("BLOCKED: Creating files in project root is restricted", file=sys.stderr)
            print("Place files in appropriate subdirectories (e.g., ai_docs/, src/, tests/)", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'root_folder':
            print("BLOCKED: Creating folders in project root is not allowed", file=sys.stderr)
            print("All folders should already exist. Use existing folders like ai_docs/, dhafnck_mcp_main/, etc.", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'unique_root_file':
            print("BLOCKED: This filename is reserved for project root only", file=sys.stderr)
            print("Files like README.md, CHANGELOG.md, etc. must be unique to the root directory", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'subfolder_ai_docs':
            print("BLOCKED: ai_docs folder must exist only in project root", file=sys.stderr)
            print("Use the root ai_docs/ folder for all documentation", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'docs_folder':
            print("BLOCKED: Use 'ai_docs' folder instead of 'docs'", file=sys.stderr)
            print("All documentation should go in ai_docs/ folder", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'md_not_in_ai_docs':
            file_path = tool_input.get('file_path', '')
            print(f"BLOCKED: Markdown file '{file_path}' must be in ai_docs/ folder", file=sys.stderr)
            print("SUGGESTION: Move to ai_docs/ folder (e.g., ai_docs/your_file.md)", file=sys.stderr)
            print("EXCEPTION: Only README.md, CHANGELOG.md, CLAUDE.md allowed in root", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'test_wrong_location':
            file_path = tool_input.get('file_path', '')
            valid_paths = load_valid_test_paths()
            print(f"BLOCKED: Test file '{file_path}' in wrong location", file=sys.stderr)
            print(f"ALLOWED LOCATIONS: {', '.join(valid_paths)}", file=sys.stderr)
            print("SUGGESTION: Move test file to one of the allowed test directories", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'venv_wrong_location':
            print("BLOCKED: Virtual environment must be in dhafnck_mcp_main/.venv", file=sys.stderr)
            print("Only one .venv is allowed at: dhafnck_mcp_main/.venv", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'logs_not_in_root':
            print("BLOCKED: 'logs' folder must be in project root only", file=sys.stderr)
            print("Use the root logs/ folder for all log files", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'sh_not_in_scripts':
            print("BLOCKED: Shell scripts (.sh) must be in scripts/ folder", file=sys.stderr)
            print("Create shell scripts in: scripts/ or docker-system/ folders", file=sys.stderr)
            sys.exit(2)
        elif creation_check == 'invalid_ai_docs_folder_name':
            file_path = tool_input.get('file_path', '')
            print(f"BLOCKED: Invalid folder name in ai_docs: '{file_path}'", file=sys.stderr)
            print("REQUIRED: Use kebab-case pattern (lowercase-with-dashes)", file=sys.stderr)
            print("VALID: 'api-integration', 'test-results', 'setup-guides'", file=sys.stderr)
            print("INVALID: 'API_Integration', 'Test Results', 'SetupGuides', 'setup123'", file=sys.stderr)
            sys.exit(2)
        
        # VALIDATION STEP 3: Check documentation enforcement for files with existing docs
        # Block ONLY if documentation already exists (indicating it's important)
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            if file_path:
                should_block, doc_path, is_folder = check_documentation_enforcement(file_path)
                
                if should_block:
                    if is_folder:
                        print(f"BLOCKED: Folder has documentation that must be updated first", file=sys.stderr)
                        print(f"Documentation: {doc_path}", file=sys.stderr)
                        print(f"Please update the folder documentation before modifying files in: {file_path}", file=sys.stderr)
                    else:
                        print(f"BLOCKED: File has documentation that must be updated", file=sys.stderr)
                        print(f"Documentation: {doc_path}", file=sys.stderr)
                        print(f"Please update the documentation before modifying: {file_path}", file=sys.stderr)
                    print("HINT: Documentation exists, indicating this is an important file/folder", file=sys.stderr)
                    sys.exit(2)
                else:
                    # Add to session if not blocking
                    if add_modified_file and not is_folder:
                        try:
                            add_modified_file(file_path)
                        except:
                            pass
                    elif add_modified_folder and is_folder:
                        try:
                            add_modified_folder(file_path)
                        except:
                            pass
        
        # VALIDATION STEP 4: Check for dangerous bash commands (rm -rf, etc.)
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            
            # Block rm -rf commands with comprehensive pattern matching
            if is_dangerous_rm_command(command):
                print("BLOCKED: Dangerous rm command detected and prevented", file=sys.stderr)
                sys.exit(2)
        
        # CONTEXT INJECTION: Inject relevant context if system supports it
        if CONTEXT_INJECTION_ENABLED and inject_context_sync:
            try:
                # Attempt context injection with timeout protection
                injected_context = inject_context_sync(tool_name, tool_input)
                
                if injected_context:
                    # Output context to stderr for Claude to see as system reminder
                    print(f"\n{injected_context}\n", file=sys.stderr)
                    
                    # Log successful context injection
                    log_dir = get_ai_data_path()
                    context_log_path = log_dir / 'context_injection.json'
                    
                    context_log_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'tool_name': tool_name,
                        'injection_successful': True,
                        'context_size': len(injected_context)
                    }
                    
                    # Append to context injection log
                    if context_log_path.exists():
                        with open(context_log_path, 'r') as f:
                            try:
                                context_log_data = json.load(f)
                            except (json.JSONDecodeError, ValueError):
                                context_log_data = []
                    else:
                        context_log_data = []
                    
                    context_log_data.append(context_log_entry)
                    
                    # Keep only last 100 entries to prevent log bloat
                    if len(context_log_data) > 100:
                        context_log_data = context_log_data[-100:]
                    
                    with open(context_log_path, 'w') as f:
                        json.dump(context_log_data, f, indent=2)
                        
            except Exception as e:
                # Context injection failure should not block tool execution
                # Log the error but continue with tool execution
                error_msg = f"Context injection failed: {str(e)}"
                print(f"WARNING: {error_msg}", file=sys.stderr)
                
                # Log the error
                log_dir = get_ai_data_path()
                error_log_path = log_dir / 'context_injection_errors.json'
                
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'tool_name': tool_name,
                    'error': str(e),
                    'injection_successful': False
                }
                
                if error_log_path.exists():
                    with open(error_log_path, 'r') as f:
                        try:
                            error_log_data = json.load(f)
                        except (json.JSONDecodeError, ValueError):
                            error_log_data = []
                else:
                    error_log_data = []
                
                error_log_data.append(error_entry)
                
                # Keep only last 50 error entries
                if len(error_log_data) > 50:
                    error_log_data = error_log_data[-50:]
                
                with open(error_log_path, 'w') as f:
                    json.dump(error_log_data, f, indent=2)

        # LOGGING: If all validations pass, log the tool use for auditing
        # Get AI_DATA path from environment (configured in .env)
        log_dir = get_ai_data_path()
        log_path = log_dir / 'pre_tool_use.json'
        
        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []
        
        # Append new data to the log for auditing
        log_data.append(input_data)
        
        # Write back to file with formatting for readability
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Exit with success - tool operation is allowed
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors - allow operation to proceed
        # This prevents the hook from blocking operations due to parsing issues
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully - allow operation to proceed
        # Better to allow operations than to block everything on error
        sys.exit(0)

# Entry point when run as a hook script
if __name__ == '__main__':
    main()