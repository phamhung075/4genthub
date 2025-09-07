# Documentation Management Commands

This directory contains commands for managing project documentation.

## manage_document_md

A comprehensive documentation management system for markdown files in the project.

**Features:**
- Document health analysis (age, status, outdated detection)
- Document indexing with metadata extraction
- Code-documentation dependency tracking
- Broken link detection
- Orphaned document detection
- Automatic report generation
- Main index.md updates

**Usage:**
```bash
# Interactive mode
manage_document_md

# Command line options
manage_document_md --analyze      # Analyze documentation health
manage_document_md --index        # Generate document index (JSON)
manage_document_md --outdated     # Find outdated documents
manage_document_md --orphaned     # Find orphaned documents
manage_document_md --deps         # Check code-documentation dependencies
manage_document_md --report       # Generate documentation report
manage_document_md --update-index # Update main index.md
manage_document_md --full         # Run full analysis
```

**Requirements:**
- `jq` for JSON processing
- `git` for version history
- `tree` (optional) for directory visualization

## manage_document_md_simple

A simplified version without jq dependency, providing core functionality.

**Features:**
- Document scanning and categorization
- Age-based outdated detection (>30 days stale, >90 days old)
- Orphaned document detection
- Broken link checking
- Status report generation
- Individual document analysis

**Usage:**
```bash
# Interactive mode
manage_document_md_simple

# Command line options
manage_document_md_simple --scan          # Scan all documentation
manage_document_md_simple --outdated      # Find outdated documents
manage_document_md_simple --orphaned      # Find orphaned documents
manage_document_md_simple --broken-links  # Check for broken links
manage_document_md_simple --report        # Generate status report
manage_document_md_simple --analyze PATH  # Analyze specific document
manage_document_md_simple --full          # Run full analysis
```

## Document Organization

The system recognizes these document categories:
- **API Reference**: Files matching `*api*` or `*API*`
- **Testing**: Files matching `*test*` or `*Test*`
- **Fixes**: Files matching `*fix*` or `*Fix*`
- **Vision System**: Files in `vision/` directory
- **Architecture**: Files matching `*architecture*` or `*design*`
- **Troubleshooting**: Files matching `*troubleshoot*`
- **Configuration**: Files matching `*config*` or `*setup*`
- **Migration**: Files matching `*migration*`
- **Changelog**: Files matching `*CHANGELOG*` or `*changelog*`

## Detection Criteria

### Outdated Documents
- **Very Old**: Not modified in >90 days
- **Stale**: Not modified in >30 days
- Contains markers: `DEPRECATED`, `OUTDATED`, `TODO`, `FIXME`
- References outdated technology (e.g., SQLite when project uses PostgreSQL)

### Orphaned Documents
- Not linked from `index.md` or `README.md` files
- Not referenced by other documents
- Excludes index files themselves

### Code-Documentation Dependencies
- Tracks Python imports and file references
- Identifies MCP tool references (`manage_*`)
- Maps class/function references
- Detects undocumented major components

## Output Files

### JSON Index (manage_document_md)
Location: `$PROJECT_ROOT/.claude/doc_index.json`

Contains:
- Document metadata (title, description, type)
- Age and last update information
- Code references
- Status (current/outdated)

### Status Report
Location: `$DOCS_ROOT/DOCUMENTATION_STATUS.md`

Contains:
- Summary statistics
- List of outdated documents by age
- Orphaned documents
- Recommendations
- Category breakdown

### Main Index
Location: `$DOCS_ROOT/index.md`

Auto-generated navigation structure for all documentation.

## Best Practices

1. **Regular Scans**: Run `--full` analysis weekly
2. **Update Stale Docs**: Review documents >30 days old
3. **Fix Broken Links**: Run `--broken-links` after moving files
4. **Remove Orphans**: Either link or remove orphaned documents
5. **Maintain Index**: Keep main index.md updated

## Integration with Development Workflow

1. **Before Release**: Run full analysis to ensure docs are current
2. **After Major Changes**: Update related documentation
3. **During Code Review**: Check if docs need updates
4. **Sprint Planning**: Review outdated docs for update tasks

## Troubleshooting

### Command Hangs
- Large number of files may take time to process
- Check git repository status
- Ensure proper permissions on doc files

### JSON Parse Errors
- Use `manage_document_md_simple` if jq issues occur
- Check for special characters in document titles

### Missing Documents
- Ensure documents are in tracked directories
- Check `.gitignore` for excluded patterns
- Verify file extensions are `.md`