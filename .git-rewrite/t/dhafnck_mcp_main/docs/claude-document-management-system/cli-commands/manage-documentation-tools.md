# Documentation Management CLI Tools

## Overview

The documentation management system provides powerful command-line tools for maintaining, analyzing, and organizing markdown documentation across the entire project. These tools help ensure documentation quality, identify outdated content, and maintain comprehensive documentation coverage.

## Available Tools

### 1. manage_document_md

**Location**: `.claude/commands/manage_document_md`

A comprehensive documentation management system with advanced features requiring `jq` for JSON processing.

#### Features
- **Document Health Analysis**: Analyzes age, status, and quality of documentation
- **JSON Index Generation**: Creates searchable index with metadata extraction
- **Code-Documentation Dependency Tracking**: Maps relationships between code and docs
- **Broken Link Detection**: Identifies invalid internal references
- **Orphaned Document Detection**: Finds unlinked documentation
- **Automatic Report Generation**: Creates detailed status reports
- **Main Index Updates**: Maintains navigation structure

#### Usage Examples

```bash
# Interactive mode - displays menu
./manage_document_md

# Analyze documentation health
./manage_document_md --analyze

# Generate JSON index
./manage_document_md --index

# Find outdated documents
./manage_document_md --outdated

# Find orphaned documents
./manage_document_md --orphaned

# Check code-documentation dependencies
./manage_document_md --deps

# Generate comprehensive report
./manage_document_md --report

# Update main index.md
./manage_document_md --update-index

# Run full analysis
./manage_document_md --full
```

#### Output Files
- **JSON Index**: `$PROJECT_ROOT/.claude/doc_index.json` - Searchable metadata index
- **Status Report**: `$DOCS_ROOT/DOCUMENTATION_STATUS.md` - Health and status report
- **Main Index**: `$DOCS_ROOT/index.md` - Navigation structure

### 2. manage_document_md_simple

**Location**: `.claude/commands/manage_document_md_simple`

A lightweight version without external dependencies, ideal for basic documentation management.

#### Features
- Document scanning and categorization
- Age-based outdated detection (>30 days stale, >90 days old)
- Orphaned document detection
- Broken link checking
- Status report generation
- Individual document analysis

#### Usage Examples

```bash
# Interactive mode
./manage_document_md_simple

# Scan all documentation
./manage_document_md_simple --scan

# Find outdated documents
./manage_document_md_simple --outdated

# Find orphaned documents
./manage_document_md_simple --orphaned

# Check for broken links
./manage_document_md_simple --broken-links

# Generate status report
./manage_document_md_simple --report

# Analyze specific document
./manage_document_md_simple --analyze path/to/doc.md

# Run full analysis
./manage_document_md_simple --full
```

### 3. manage_document_md_postgresql

**Location**: `.claude/commands/manage_document_md_postgresql`

PostgreSQL-integrated version for projects using database-backed documentation systems.

#### Additional Features
- Database synchronization
- Version history tracking
- Multi-user documentation management
- Query-based document retrieval
- Database-backed metadata storage

## Document Organization System

### Automatic Categorization

Documents are automatically categorized based on patterns:

| Category | Pattern Matching | Examples |
|----------|-----------------|----------|
| **API Reference** | `*api*`, `*API*` | `api-reference.md`, `REST-API.md` |
| **Testing** | `*test*`, `*Test*` | `testing-guide.md`, `TestStrategy.md` |
| **Fixes** | `*fix*`, `*Fix*` | `bugfix-guide.md`, `Fix-Authentication.md` |
| **Vision System** | `vision/` directory | `vision/architecture.md` |
| **Architecture** | `*architecture*`, `*design*` | `system-architecture.md` |
| **Troubleshooting** | `*troubleshoot*` | `troubleshooting-guide.md` |
| **Configuration** | `*config*`, `*setup*` | `configuration.md`, `setup-guide.md` |
| **Migration** | `*migration*` | `migration-v2.md` |
| **Changelog** | `*CHANGELOG*`, `*changelog*` | `CHANGELOG.md` |

### Directory Structure

```
dhafnck_mcp_main/docs/
├── CORE ARCHITECTURE/        # System design and architecture
├── DEVELOPMENT GUIDES/        # Developer resources
├── OPERATIONS/               # Deployment and configuration
├── TROUBLESHOOTING/          # Problem resolution guides
├── vision/                   # Vision System documentation
├── fixes/                    # Bug fix documentation
├── migration-guides/         # Version migration guides
├── api-reference/            # API documentation
└── index.md                  # Main navigation index
```

## Detection Criteria

### Outdated Document Detection

Documents are flagged as outdated based on:

1. **Age-Based Criteria**:
   - **Very Old**: Not modified in >90 days
   - **Stale**: Not modified in >30 days

2. **Content Markers**:
   - Contains `DEPRECATED` tags
   - Contains `OUTDATED` markers
   - Contains unresolved `TODO` items
   - Contains `FIXME` annotations

3. **Technology Mismatches**:
   - References outdated dependencies
   - Mentions deprecated APIs
   - Uses obsolete code patterns

### Orphaned Document Detection

Documents are considered orphaned when:
- Not linked from any `index.md` or `README.md`
- Not referenced by other documents
- Not included in navigation structure
- Excludes index files themselves

### Code-Documentation Dependencies

The system tracks:
- Python imports and module references
- File path references in documentation
- Class and function documentation coverage
- MCP tool references (`manage_*` patterns)
- Undocumented major components

## Metadata Extraction

Each document is analyzed for:

```json
{
  "title": "Document Title",
  "description": "Brief description extracted from content",
  "type": "category",
  "sections": 5,
  "tags": "tag1, tag2",
  "age_days": 15,
  "last_updated": "2024-07-20",
  "status": "current|outdated",
  "code_refs": ["py:module", "path:/src/file", "mcp:manage_task"],
  "links": ["internal", "external"],
  "word_count": 1500
}
```

## Workflow Integration

### Daily Maintenance
```bash
# Quick health check
./manage_document_md --analyze

# Update stale docs
./manage_document_md --outdated
```

### Weekly Review
```bash
# Full analysis
./manage_document_md --full

# Fix broken links
./manage_document_md --broken-links

# Clean orphaned docs
./manage_document_md --orphaned
```

### Before Release
```bash
# Complete documentation audit
./manage_document_md --full
./manage_document_md --report
./manage_document_md --update-index
```

### After Major Changes
```bash
# Check documentation coverage
./manage_document_md --deps

# Update related docs
./manage_document_md --analyze
```

## Best Practices

### 1. Regular Maintenance
- Run `--analyze` daily for quick health checks
- Perform `--full` analysis weekly
- Review `--report` before releases

### 2. Documentation Quality
- Update documents flagged as stale (>30 days)
- Remove or update very old documents (>90 days)
- Fix broken links immediately
- Link or remove orphaned documents

### 3. Code-Doc Synchronization
- Update docs when code changes significantly
- Ensure new features are documented
- Keep API documentation current
- Document breaking changes

### 4. Organization
- Use consistent categorization
- Maintain clear directory structure
- Keep index.md files updated
- Use descriptive file names

## Troubleshooting

### Common Issues

#### 1. Command Hangs
**Cause**: Large number of files or slow git operations
**Solution**: 
- Use `--limit` flag if available
- Check git repository status
- Use `manage_document_md_simple` for faster processing

#### 2. JSON Parse Errors
**Cause**: Missing `jq` or special characters in content
**Solution**:
- Install `jq`: `sudo apt-get install jq`
- Use `manage_document_md_simple` as alternative
- Check for special characters in titles

#### 3. Missing Documents
**Cause**: Incorrect paths or gitignore patterns
**Solution**:
- Verify documents are in tracked directories
- Check `.gitignore` for exclusions
- Ensure `.md` file extensions

#### 4. Permission Errors
**Cause**: Insufficient file permissions
**Solution**:
- Check file ownership
- Ensure execute permissions: `chmod +x manage_document_md`
- Run with appropriate user privileges

### Performance Optimization

For large documentation sets:

1. **Use Incremental Updates**:
   ```bash
   # Analyze only changed files
   ./manage_document_md --changed
   ```

2. **Limit Scope**:
   ```bash
   # Analyze specific directory
   ./manage_document_md --dir docs/api-reference
   ```

3. **Use Simple Version**:
   ```bash
   # Faster processing without JSON
   ./manage_document_md_simple --scan
   ```

## Advanced Features

### Custom Categories

Add custom categories by modifying the script:

```bash
declare -A DOC_CATEGORIES=(
    ["api"]="API Reference"
    ["custom"]="Custom Category"  # Add your category
)
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Check Documentation
  run: |
    ./manage_document_md --full
    if [ -f docs/DOCUMENTATION_STATUS.md ]; then
      cat docs/DOCUMENTATION_STATUS.md >> $GITHUB_STEP_SUMMARY
    fi
```

### Automated Alerts

Set up cron job for regular checks:

```bash
# Add to crontab
0 9 * * 1 /path/to/manage_document_md --report --email admin@example.com
```

## Summary

The documentation management tools provide comprehensive capabilities for maintaining high-quality documentation. Regular use ensures:

- Documentation remains current and accurate
- Broken links are identified and fixed
- Orphaned documents are discovered
- Code and documentation stay synchronized
- Documentation coverage is comprehensive

Choose the appropriate tool based on your needs:
- **manage_document_md**: Full-featured with JSON support
- **manage_document_md_simple**: Lightweight, no dependencies
- **manage_document_md_postgresql**: Database-integrated version

Regular maintenance using these tools ensures documentation quality and helps maintain a well-organized, accessible knowledge base for the entire development team.