# Claude Document Management System

## Overview

The Claude Document Management System provides comprehensive tools and processes for maintaining high-quality documentation across the entire DhafnckMCP project. This system ensures documentation remains current, well-organized, and synchronized with code changes.

## System Components

### [CLI Commands](cli-commands/)
- [**Documentation Management Tools**](cli-commands/manage-documentation-tools.md) - Comprehensive CLI tools for documentation analysis and maintenance
  - `manage_document_md` - Full-featured documentation manager with JSON indexing
  - `manage_document_md_simple` - Lightweight version without dependencies
  - `manage_document_md_postgresql` - Database-integrated documentation management

### [Architecture](architecture/)
- [**System Architecture**](architecture/claude-document-management-architecture.md) - Technical design and implementation details

### [Implementation](implementation/)
- [**Implementation Guide**](implementation/claude-document-management-implementation.md) - Step-by-step implementation instructions

### [Phases](phases/)
- [**Development Phases**](phases/claude-document-management-phases.md) - Phased rollout and feature development

### [File Specifications](file-specifications/)
- Documentation file format specifications
- Metadata standards
- Naming conventions

## Quick Start

### Basic Usage

```bash
# Navigate to commands directory
cd .claude/commands/

# Make scripts executable
chmod +x manage_document_md manage_document_md_simple

# Run interactive mode
./manage_document_md

# Or run specific analysis
./manage_document_md --full
```

### Common Tasks

#### 1. Check Documentation Health
```bash
./manage_document_md --analyze
```

#### 2. Find Outdated Documents
```bash
./manage_document_md --outdated
```

#### 3. Generate Status Report
```bash
./manage_document_md --report
```

#### 4. Update Navigation Index
```bash
./manage_document_md --update-index
```

## Key Features

### 1. Automated Analysis
- Age-based outdated detection
- Broken link identification
- Orphaned document discovery
- Code-documentation dependency tracking

### 2. Comprehensive Reporting
- JSON metadata indexing
- Markdown status reports
- Category-based organization
- Progress tracking

### 3. Integration Capabilities
- Git history analysis
- CI/CD pipeline integration
- Database synchronization (PostgreSQL version)
- Multi-user support

## Documentation Standards

### File Organization
```
dhafnck_mcp_main/docs/
├── CORE ARCHITECTURE/        # System design
├── DEVELOPMENT GUIDES/        # Developer guides
├── OPERATIONS/               # Deployment docs
├── TROUBLESHOOTING/          # Problem solving
├── vision/                   # Vision System
├── claude-document-management-system/  # This system
└── index.md                  # Main navigation
```

### Categorization Rules
- **API Reference**: Files matching `*api*` or `*API*`
- **Testing**: Files matching `*test*` or `*Test*`
- **Fixes**: Files matching `*fix*` or `*Fix*`
- **Vision System**: Files in `vision/` directory
- **Architecture**: Files matching `*architecture*` or `*design*`

### Quality Metrics
- **Current**: Modified within 30 days
- **Stale**: Not modified in 30-90 days
- **Outdated**: Not modified in >90 days
- **Orphaned**: Not linked from any index
- **Broken**: Contains invalid links

## Workflow Integration

### Daily Maintenance
1. Run health check: `./manage_document_md --analyze`
2. Review any warnings or errors
3. Update stale documentation as needed

### Weekly Review
1. Full analysis: `./manage_document_md --full`
2. Fix broken links
3. Review orphaned documents
4. Update main index

### Pre-Release Checklist
1. Complete documentation audit
2. Generate status report
3. Fix all critical issues
4. Update navigation structure
5. Verify code-doc synchronization

## Best Practices

### 1. Regular Maintenance
- Schedule daily quick checks
- Perform weekly full analysis
- Monthly deep review of old docs

### 2. Documentation Quality
- Keep documents under 30 days old
- Fix broken links immediately
- Maintain clear categorization
- Update docs with code changes

### 3. Organization
- Use consistent naming
- Maintain index.md files
- Follow directory structure
- Apply proper categorization

## Tool Selection Guide

| Tool | Use When | Requirements |
|------|----------|--------------|
| `manage_document_md` | Need full features, JSON indexing | `jq`, `git` |
| `manage_document_md_simple` | Quick analysis, no dependencies | Basic shell |
| `manage_document_md_postgresql` | Database integration needed | PostgreSQL |

## Troubleshooting

### Common Issues

1. **Script Not Executable**
   ```bash
   chmod +x manage_document_md*
   ```

2. **Missing Dependencies**
   ```bash
   # Install jq for full version
   sudo apt-get install jq
   ```

3. **Path Issues**
   - Verify PROJECT_ROOT in scripts
   - Check directory permissions

4. **Performance Problems**
   - Use simple version for large doc sets
   - Limit scope with directory flags

## Future Enhancements

### Planned Features
- Automated documentation generation
- AI-powered content suggestions
- Real-time documentation validation
- Cross-reference verification
- Multi-language support

### Integration Goals
- GitHub Actions workflows
- VS Code extension
- Web-based dashboard
- Slack notifications
- Documentation metrics API

## Related Documentation

- [Main Project Documentation](../index.md)
- [Vision System Documentation](../vision/)
- [Development Guides](../DEVELOPMENT%20GUIDES/)
- [Operations Manual](../OPERATIONS/)

## Support

For issues or questions about the documentation management system:

1. Check [Troubleshooting Guide](../TROUBLESHOOTING/)
2. Review [CLI Commands Documentation](cli-commands/manage-documentation-tools.md)
3. Create issue in project repository
4. Contact development team

---

*Last Updated: 2025-08-14*
*Version: 1.0.0*