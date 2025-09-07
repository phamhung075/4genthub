"""File Resource MCP Controller Description

This module provides comprehensive documentation for the file resource management controller,
including all operations, parameters, and AI optimization guidelines.
"""

description = '''
📁 FILE RESOURCE MANAGEMENT SYSTEM - Secure file exposure and access control

⭐ WHAT IT DOES: Manages file resource exposure from the project's resources directory, providing secure access to documentation, templates, and configuration files through MCP protocol
📋 WHEN TO USE: When AI agents need to access project documentation, templates, configuration files, or any resources stored in the designated resources directory (00_RESOURCES or data/resources)
🎯 CRITICAL FOR: Resource discovery, documentation access, template retrieval, configuration management, and secure file exposure within project boundaries

🔍 RESOURCE DISCOVERY PATTERNS:
The system automatically discovers and exposes files from:
• Local development: project_root/00_RESOURCES/
• Docker deployment: /data/resources/ or project_root/data/resources/
• Parent directories: Searches up to 3 levels for 00_RESOURCES

📂 EXPOSED RESOURCE TYPES:
• Documentation: *.md, *.mdx (Markdown files)
• Code templates: *.py, *.js, *.ts, *.jsx, *.tsx
• Configuration: *.json, *.yaml, *.yml, *.toml, *.ini, *.cfg, *.conf
• Scripts: *.sh (Shell scripts)
• Web resources: *.html, *.css
• Data files: *.csv, *.xml, *.sql
• Environment examples: *.env, .env.example
• Other text files: *.txt, *.log, *.mdc

🛡️ SECURITY FEATURES:
• Path traversal protection (no access outside resources directory)
• File size limits (max 10MB per file)
• Binary file detection and base64 encoding
• Hidden file filtering (with exceptions for .gitignore, .env.example)
• Excluded directories: __pycache__, node_modules, .git, venv, dist, build

🔗 RESOURCE ACCESS METHODS:
1. Static resource listing: resources://directory/resources
2. Individual file resources: resources:///path/to/file
3. Dynamic file access: resources://dynamic/{filepath*}

💡 USAGE GUIDELINES:
• Resources are read-only - no modification operations available
• All file paths are relative to the resources directory
• Binary files are automatically base64 encoded
• Text files use UTF-8 encoding with error replacement
• Resource discovery happens automatically on startup

🔍 AI DECISION TREES:

RESOURCE ACCESS PATTERN:
IF need_project_documentation:
    ACCESS resources:///README.md or resources:///docs/
ELIF need_configuration_template:
    ACCESS resources:///templates/config/
ELIF need_code_examples:
    ACCESS resources:///examples/
ELIF need_specific_file:
    USE resources://dynamic/{relative/path/to/file}

FILE TYPE HANDLING:
IF file.is_binary:
    RETURN base64_encoded_content
ELIF file.is_text:
    RETURN utf8_decoded_content
ELSE:
    RETURN error("Unsupported file type")

📊 COMMON WORKFLOWS:

1. Discovering Available Resources:
   - System automatically registers all eligible files on startup
   - Use resource listing to see available directories
   - Access individual files through their resource URIs

2. Accessing Documentation:
   - Navigate to resources:///docs/ for project documentation
   - Use resources:///README.md for main project info
   - Access API docs at resources:///docs/api/

3. Using Templates:
   - Find templates at resources:///templates/
   - Copy template content for new implementations
   - Reference examples at resources:///examples/

4. Configuration Management:
   - Access config templates at resources:///config/
   - Review .env.example for environment setup
   - Check resources:///settings/ for app configurations

⚠️ IMPORTANT NOTES:
• Resources directory must exist for the system to function
• Files outside the resources directory cannot be accessed
• Large files (>10MB) are automatically excluded
• Certain file types (.pyc, .dll, .so) are always excluded
• Hidden directories and files are excluded (except specific allowed ones)
• Path traversal attempts (../, absolute paths) are blocked
• All access is read-only - no write operations available

🚫 RESTRICTED OPERATIONS:
• Cannot modify or delete resource files
• Cannot access files outside resources directory
• Cannot access system files or sensitive areas
• Cannot bypass size or type restrictions

🎯 BEST PRACTICES:
• Organize resources in logical directory structure
• Keep documentation in docs/ subdirectory
• Store templates in templates/ subdirectory
• Place examples in examples/ subdirectory
• Use clear, descriptive file names
• Maintain reasonable file sizes (<10MB)
• Avoid storing sensitive data in resources

📈 PERFORMANCE CONSIDERATIONS:
• File discovery runs once at startup
• Large directories may slow initial registration
• Binary files require base64 encoding overhead
• Recursive directory scanning for all patterns
• Caching not implemented - files read on each access

🔄 ERROR HANDLING:
• NOT_FOUND: Resource file or directory doesn't exist
• FORBIDDEN: Access denied (outside resources, restricted file)
• INTERNAL_ERROR: Read errors, encoding issues
• Clear error messages with field names and hints

🌐 ENVIRONMENT SUPPORT:
• Local development: Uses 00_RESOURCES directory
• Docker deployment: Uses /data/resources or data/resources
• Parent directory search: Looks up to 3 levels for resources
• Automatic environment detection and path resolution
'''