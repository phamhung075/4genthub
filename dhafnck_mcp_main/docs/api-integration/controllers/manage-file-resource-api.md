# manage_file_resource - File Resource Management API Documentation

## Overview

The `manage_file_resource` system provides comprehensive file resource exposure through MCP (Model Context Protocol). This system automatically discovers, registers, and serves files from the project's resources directory as MCP resources, enabling AI agents and clients to access project documentation, configuration files, and other important resources.

## Base Information

- **System**: `FileResourceMCPController` (Resource Exposure System)
- **Module**: `fastmcp.task_management.interface.mcp_controllers.file_resource_mcp_controller`
- **Authentication**: Not required (Read-only access)
- **Resource Discovery**: ✅ Automatic discovery and registration
- **Security**: ✅ Path validation and access control
- **Caching**: ✅ Resource registration with FastMCP

## Architecture Components

### Core Components
- **FileResourceMCPController**: Main controller handling MCP resource registration
- **FileResourceApplicationFacade**: Application layer orchestrating file operations
- **ResourceRegistrationHandler**: Handles MCP resource registration logic
- **FileUtils**: Utility functions for file operations and metadata

### Resource Types Supported
- **Individual Files**: Specific important files registered as resources
- **Directory Listings**: Directory structure as JSON resources
- **Dynamic Access**: Template-based file access for any file in resources directory

## File Discovery and Exposure Rules

### Supported File Types
```json
{
  "text_files": ["*.md", "*.txt", "*.py", "*.js", "*.ts", "*.css", "*.html"],
  "config_files": ["*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg"],
  "documentation": ["*.mdx", "*.jsx", "*.tsx"],
  "scripts": ["*.sh", "*.sql"],
  "special_files": ["*.env", "*.conf", "*.xml", "*.csv"]
}
```

### File Exclusion Rules
```json
{
  "excluded_directories": ["__pycache__", "node_modules", ".git", ".venv", ".pytest_cache"],
  "excluded_extensions": [".pyc", ".pyo", ".pyd", ".so", ".dll", ".lock", ".tmp"],
  "size_limit": "10MB",
  "hidden_files": "excluded (except .gitignore, .env.example)"
}
```

### Resource Directory Paths
The system automatically detects the resources directory in this order:
1. **Docker Environment**: `/data/resources/` (absolute)
2. **Docker Environment**: `{project_root}/data/resources/` (relative)
3. **Local Development**: `{project_root}/00_RESOURCES/`
4. **Parent Directory Search**: Up to 3 levels up for `00_RESOURCES/`

## Resource Registration Process

### 1. Directory Resource Registration
```json
{
  "uri": "resources://directory/resources",
  "name": "resources Directory Listing",
  "description": "Lists all files in the resources directory",
  "mime_type": "application/json",
  "recursive": true,
  "tags": ["directory", "listing", "resource"]
}
```

### 2. Individual File Registration
Each discoverable file is registered as:
```json
{
  "uri": "resources:///path/to/file.md",
  "name": "file.md",
  "description": "File: path/to/file.md",
  "mime_type": "text/markdown",
  "size": 1024,
  "tags": ["file", "resource", "md", "text"]
}
```

### 3. Dynamic Template Registration
A dynamic template enables access to any file:
```
Template: "resources://dynamic/{filepath*}"
Usage: "resources://dynamic/docs/setup-guide.md"
```

## MCP Resource Access Patterns

### Static Resource Access
For files registered during startup:
```json
{
  "method": "resources/read",
  "params": {
    "uri": "resources:///documentation/api-guide.md"
  }
}
```

### Dynamic Resource Access
For any file in the resources directory:
```json
{
  "method": "resources/read", 
  "params": {
    "uri": "resources://dynamic/docs/new-document.md"
  }
}
```

### Directory Listing Access
```json
{
  "method": "resources/read",
  "params": {
    "uri": "resources://directory/resources"
  }
}
```

## Response Formats

### File Content Response (Text Files)
```json
{
  "contents": [
    {
      "uri": "resources:///example.md",
      "mimeType": "text/markdown",
      "text": "# Example Document\n\nThis is the file content..."
    }
  ]
}
```

### File Content Response (Binary Files)
```json
{
  "contents": [
    {
      "uri": "resources:///image.png",
      "mimeType": "image/png", 
      "blob": "iVBORw0KGgoAAAANSUhEUgAA..." 
    }
  ]
}
```

### Directory Listing Response
```json
{
  "contents": [
    {
      "uri": "resources://directory/resources",
      "mimeType": "application/json",
      "text": "{\"path\":\"\",\"directories\":[{\"name\":\"docs\",\"path\":\"docs\"}],\"files\":[{\"name\":\"README.md\",\"path\":\"README.md\",\"size\":1024,\"mime_type\":\"text/markdown\",\"is_binary\":false}],\"total_files\":1,\"total_directories\":1}"
    }
  ]
}
```

### Error Response Format
```json
{
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "success": false,
      "error": "Resource not found: invalid/path.md",
      "error_code": "NOT_FOUND",
      "field": "filepath", 
      "expected": "A valid file path within resources directory",
      "hint": "Check the file path for typos"
    }
  }
}
```

## Security and Access Control

### Path Security
- **Directory Traversal Protection**: Prevents access outside resources directory
- **Path Validation**: All paths validated against allowed patterns  
- **Absolute Path Prevention**: Blocks absolute path access attempts
- **Symlink Resolution**: Resolves symlinks safely within boundaries

### File Access Control
```python
def validate_file_access(file_path):
    """Security validation for file access"""
    # 1. Must be within resources directory
    # 2. Must not be hidden (except allowed files)
    # 3. Must not be in excluded directories
    # 4. Must not have excluded extensions
    # 5. Must not exceed size limits
```

### Allowed Hidden Files
```json
{
  "allowed_hidden": [".gitignore", ".env.example", ".dockerignore", ".editorconfig"]
}
```

## MIME Type Detection

### Text Files
```json
{
  ".py": "text/x-python",
  ".js": "application/javascript", 
  ".ts": "application/typescript",
  ".md": "text/markdown",
  ".html": "text/html",
  ".css": "text/css",
  ".txt": "text/plain"
}
```

### Configuration Files
```json
{
  ".json": "application/json",
  ".yaml": "application/yaml",
  ".yml": "application/yaml", 
  ".toml": "application/toml",
  ".xml": "application/xml"
}
```

### Binary Files
Automatically detected based on:
- File extension (`.png`, `.jpg`, `.pdf`, `.zip`, etc.)
- Content analysis (presence of null bytes in first 1024 bytes)

## Resource Caching and Optimization

### Registration Caching
- **Startup Registration**: All discoverable files registered once at startup
- **Template Caching**: Dynamic template registered once for runtime access
- **Resource Metadata**: Cached file information for quick access

### Performance Optimizations
- **File Size Limits**: 10MB maximum file size for resources
- **Pattern Matching**: Efficient glob patterns for file discovery
- **Directory Scanning**: Optimized recursive directory traversal
- **Binary Detection**: Fast binary file detection using sampling

### Cache Invalidation
- **Server Restart**: Full resource re-registration on server restart
- **Dynamic Access**: Real-time file access without pre-registration
- **Resource Updates**: No automatic cache invalidation (restart required)

## Usage Examples

### Client Resource Discovery
```javascript
// List all available resources
const resources = await mcp.listResources();

// Filter for file resources
const fileResources = resources.filter(r => 
  r.uri.startsWith('resources://')
);
```

### Reading Documentation
```javascript
// Read API documentation
const apiDocs = await mcp.readResource({
  uri: "resources:///documentation/api-guide.md"
});

console.log(apiDocs.contents[0].text);
```

### Dynamic File Access
```javascript
// Access any file dynamically
const configFile = await mcp.readResource({
  uri: "resources://dynamic/config/database.yml"
});
```

### Directory Browsing
```javascript
// Get directory listing
const dirListing = await mcp.readResource({
  uri: "resources://directory/resources"
});

const listing = JSON.parse(dirListing.contents[0].text);
console.log(`Found ${listing.total_files} files`);
```

## Error Handling

### Common Error Codes

#### NOT_FOUND
```json
{
  "error_code": "NOT_FOUND",
  "error": "Resource not found: path/to/file.md",
  "field": "filepath",
  "expected": "A valid file path within resources directory",
  "hint": "Check the file path for typos"
}
```

#### FORBIDDEN
```json
{
  "error_code": "FORBIDDEN", 
  "error": "Access denied: Path outside resources directory",
  "field": "filepath",
  "expected": "A path within the resources directory",
  "hint": "Do not use .. or absolute paths"
}
```

#### INTERNAL_ERROR
```json
{
  "error_code": "INTERNAL_ERROR",
  "error": "Error reading resource: Permission denied",
  "details": "Permission denied: /data/resources/private/file.txt"
}
```

### Error Recovery
- **Path Validation**: Clear error messages for invalid paths
- **Permission Issues**: Graceful handling of permission denied errors
- **File Not Found**: Helpful hints for correcting file paths
- **Binary File Handling**: Automatic base64 encoding for binary content

## Integration Patterns

### With Task Management
```python
# Access task templates from resources
task_template = await read_resource("resources://dynamic/templates/task-template.md")
```

### With Documentation Systems
```python
# Serve documentation through MCP resources
docs = await read_resource("resources:///docs/user-guide.md")
```

### With Configuration Management
```python
# Access configuration files
config = await read_resource("resources://dynamic/config/app-config.yml")
```

## Monitoring and Logging

### Initialization Logs
```
INFO: FileResourceMCPController initialized with project root: /path/to/project
INFO: Discovering files for resource exposure from 00_RESOURCES...
INFO: Discovered 45 files for resource exposure from /path/to/00_RESOURCES
INFO: File resources registered successfully
```

### Access Logs
```
DEBUG: Registered file resource: docs/api-guide.md
DEBUG: Registered directory resource: /path/to/resources
WARNING: Skipping large file: large-file.zip (15728640 bytes)
```

### Error Logs
```
ERROR: Error reading resource path/file.md: Permission denied
WARNING: Resources directory not found (tried data/resources and 00_RESOURCES)
```

## Best Practices

### Resource Organization
1. **Structured Layout**: Organize resources in logical directory structure
2. **Clear Naming**: Use descriptive file and directory names  
3. **Size Management**: Keep files under 10MB limit
4. **Documentation**: Include README files in resource directories

### Security Considerations
1. **No Sensitive Data**: Never place credentials or secrets in resources
2. **Public Access**: Assume all resources are publicly accessible
3. **Path Validation**: Always validate paths in client applications
4. **Content Review**: Regularly review exposed resource content

### Performance Optimization
1. **File Size**: Keep resource files reasonably sized
2. **Directory Structure**: Avoid deeply nested directory structures
3. **Binary Files**: Minimize binary file exposure
4. **Resource Cleanup**: Remove unused resources to reduce discovery time

## Troubleshooting

### Common Issues

#### Resources Not Found
- **Check Directory**: Ensure `00_RESOURCES/` or `data/resources/` exists
- **File Permissions**: Verify files are readable
- **Path Validation**: Check file paths for typos

#### Access Denied Errors  
- **Directory Traversal**: Avoid using `..` in paths
- **Hidden Files**: Most hidden files are blocked by default
- **File Extensions**: Some extensions are automatically excluded

#### Large File Issues
- **Size Limit**: Files over 10MB are automatically excluded
- **Binary Files**: Large binary files should be hosted separately
- **Resource Split**: Split large resources into smaller files

### Debug Steps
1. **Check Logs**: Review initialization and access logs
2. **List Resources**: Use MCP resource listing to see available resources
3. **Test Paths**: Try directory listing to verify structure
4. **Validate Access**: Test file access with dynamic template

This comprehensive API documentation covers all aspects of the file resource management system, providing developers with the information needed to effectively integrate and use the MCP file resource capabilities.