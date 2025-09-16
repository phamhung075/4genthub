"""
Centralized messages configuration for Claude hooks.
All user-facing messages, errors, warnings, and hints are defined here.
"""

from typing import Dict, Any

# Error messages
ERROR_MESSAGES = {
    # File system protection errors
    "claude_edit_disabled": {
        "message": "BLOCKED: Editing .claude files is disabled",
        "hint": "Set ENABLE_CLAUDE_EDIT=true in .env.claude to allow editing"
    },
    "env_file_subfolder": {
        "message": "BLOCKED: .env* files must be created in project root only",
        "hint": "Place environment files in the project root directory"
    },
    "env_file_access": {
        "message": "BLOCKED: Access to .env* files containing sensitive data is prohibited",
        "hint": "Use .env.sample for template files instead"
    },
    "root_file_creation": {
        "message": "BLOCKED: Creating files in project root is restricted",
        "hint": "Place files in appropriate subdirectories (e.g., ai_docs/, src/, tests/)"
    },
    "root_folder_creation": {
        "message": "BLOCKED: Creating folders in project root is not allowed",
        "hint": "All necessary project folders should already exist"
    },
    "unique_root_file": {
        "message": "BLOCKED: {file} can only exist in project root",
        "hint": "This file already exists in root. Edit the existing file instead of creating a duplicate"
    },
    "subfolder_ai_docs": {
        "message": "BLOCKED: 'ai_docs' folder can only exist in project root",
        "hint": "Use the existing ai_docs folder in the project root for documentation"
    },
    "docs_folder": {
        "message": "BLOCKED: Creating 'docs' folders is prohibited",
        "hint": "Use 'ai_docs' folder in project root for all documentation"
    },
    "md_not_in_ai_docs": {
        "message": "BLOCKED: ALL .md files must be in ai_docs folder",
        "hint": "Place documentation in ai_docs/{category}/*.md",
        "examples": ["ai_docs/api-integration/auth.md", "ai_docs/troubleshooting-guides/setup-issues.md"]
    },
    "invalid_ai_docs_folder": {
        "message": "BLOCKED: Invalid folder name in ai_docs",
        "hint": "Folder names in ai_docs must use kebab-case (lowercase-with-dashes)",
        "valid_examples": ["api-integration", "test-results", "setup-guides"],
        "invalid_examples": ["API_Integration", "Test Results", "SetupGuides"]
    },
    "test_wrong_location": {
        "message": "BLOCKED: Test files must be in designated test directories",
        "hint": "Place test files in approved test directories",
        "valid_paths": ["dhafnck_mcp_main/src/tests", "dhafnck-frontend/src/tests"]
    },
    "venv_wrong_location": {
        "message": "BLOCKED: Virtual environment must be in dhafnck_mcp_main/.venv",
        "hint": "Create .venv only at: dhafnck_mcp_main/.venv"
    },
    "logs_not_in_root": {
        "message": "BLOCKED: 'logs' folder can only exist in project root",
        "hint": "Use the logs folder in project root for all log files"
    },
    "sh_not_in_scripts": {
        "message": "BLOCKED: Shell scripts must be in scripts/ or docker-system/ folders",
        "hint": "Place .sh files in scripts/ or docker-system/ folders"
    },
    "dangerous_rm": {
        "message": "BLOCKED: Dangerous rm -rf command detected",
        "hint": "This command could delete critical system files. Use specific paths and verify before deletion"
    },
    "documentation_required": {
        "message": "BLOCKED: Documentation update required",
        "hint": "This {type} has existing documentation that must be updated before modification",
        "action": "Update documentation at: {doc_path}"
    }
}

# Warning messages
WARNING_MESSAGES = {
    "context_switch_failed": "Warning: Agent context switch failed: {error}",
    "documentation_needed": "📝 Documentation needed: Please {action} {doc_path} for file: {file_path}",
    "hint_display_error": "Warning: Failed to display hints: {error}",
    "context_injection_error": "Warning: Failed to inject context: {error}",
    "session_tracking_error": "Warning: Session tracking error: {error}"
}

# Info messages
INFO_MESSAGES = {
    "role_violation": "Tool '{tool}' is not available for agent '{agent}'",
    "available_tools": "Available tools: {tools}",
    "solution": "Solution: {solution}",
    "documentation_updated": "✅ Documentation successfully updated",
    "session_started": "Session {session_id} started",
    "context_injected": "Context injected for {tool}: {size} bytes"
}

# System prompts and instructions
SYSTEM_PROMPTS = {
    "documentation_reminder": """
The file you're modifying has existing documentation that should be kept in sync.
Please ensure the documentation accurately reflects your changes.
Documentation location: {doc_path}
""",
    "role_enforcement": """
You are currently operating as {agent_type}.
Your available tools are restricted to: {tools}
Please use only the tools appropriate for your role.
""",
    "context_injection": """
Relevant context has been loaded for your current operation.
Context type: {context_type}
Context size: {context_size} bytes
"""
}

# Function to get formatted error message
def get_error_message(error_key: str, **kwargs) -> str:
    """
    Get a formatted error message with optional parameters.

    Args:
        error_key: Key identifying the error type
        **kwargs: Parameters to format into the message

    Returns:
        Formatted error message string
    """
    if error_key not in ERROR_MESSAGES:
        return f"Unknown error: {error_key}"

    error_config = ERROR_MESSAGES[error_key]
    message = error_config["message"].format(**kwargs) if kwargs else error_config["message"]

    # Build complete error message with hint
    result = [message]

    if "hint" in error_config:
        hint = error_config["hint"].format(**kwargs) if kwargs else error_config["hint"]
        result.append(hint)

    if "examples" in error_config:
        result.append("Examples: " + ", ".join(error_config["examples"]))

    if "valid_examples" in error_config:
        result.append("Valid: " + ", ".join(error_config["valid_examples"]))

    if "invalid_examples" in error_config:
        result.append("Invalid: " + ", ".join(error_config["invalid_examples"]))

    if "valid_paths" in error_config:
        result.append("Valid paths: " + ", ".join(error_config["valid_paths"]))

    if "action" in error_config:
        action = error_config["action"].format(**kwargs) if kwargs else error_config["action"]
        result.append(action)

    return "\n".join(result)

# Function to get formatted warning message
def get_warning_message(warning_key: str, **kwargs) -> str:
    """
    Get a formatted warning message with optional parameters.

    Args:
        warning_key: Key identifying the warning type
        **kwargs: Parameters to format into the message

    Returns:
        Formatted warning message string
    """
    if warning_key not in WARNING_MESSAGES:
        return f"Unknown warning: {warning_key}"

    message = WARNING_MESSAGES[warning_key]
    return message.format(**kwargs) if kwargs else message

# Function to get formatted info message
def get_info_message(info_key: str, **kwargs) -> str:
    """
    Get a formatted info message with optional parameters.

    Args:
        info_key: Key identifying the info type
        **kwargs: Parameters to format into the message

    Returns:
        Formatted info message string
    """
    if info_key not in INFO_MESSAGES:
        return f"Unknown info: {info_key}"

    message = INFO_MESSAGES[info_key]
    return message.format(**kwargs) if kwargs else message

# Function to get system prompt
def get_system_prompt(prompt_key: str, **kwargs) -> str:
    """
    Get a formatted system prompt with optional parameters.

    Args:
        prompt_key: Key identifying the prompt type
        **kwargs: Parameters to format into the prompt

    Returns:
        Formatted system prompt string
    """
    if prompt_key not in SYSTEM_PROMPTS:
        return f"Unknown prompt: {prompt_key}"

    prompt = SYSTEM_PROMPTS[prompt_key]
    return prompt.format(**kwargs) if kwargs else prompt