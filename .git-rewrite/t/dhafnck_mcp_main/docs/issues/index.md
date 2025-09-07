# Issue Documentation Index

This folder contains detailed documentation of significant issues encountered and resolved in the DhafnckMCP system.

## Critical Issues

### 2025-01-13
- [Database Schema Mismatch - Context Tables](./2025-01-13-database-schema-mismatch.md)
  - **Severity**: CRITICAL
  - **Impact**: Complete Supabase connection failure
  - **Resolution**: Recreated all context tables with UUID types
  - **Key Learning**: ORM models must exactly match database schema
  - **Complete Summary**: [Database Schema Fix Complete](./2025-01-13-database-schema-fix-complete.md)

## Major Issues

### Security
- [Security Fixes Applied](./security-fixes-applied.md) - Comprehensive security vulnerability fixes

### Task Management
- Task count synchronization issues
- Task deletion not updating counters
- Cascade deletion verification

### Docker & Deployment
- Docker container caching preventing code updates
- Frontend build path issues
- Supabase connection configuration

### Database & ORM
- Foreign key type mismatches (VARCHAR vs UUID)
- SQLAlchemy relationship mapping failures
- Context inheritance chain issues

## Issue Documentation Format

Each issue document should include:
1. **Issue Date**: When the issue occurred
2. **Severity**: CRITICAL/MAJOR/MINOR
3. **Summary**: Brief description
4. **Symptoms**: What errors/behaviors were observed
5. **Root Cause Analysis**: Why it happened
6. **Solution Implemented**: How it was fixed
7. **Files Modified**: What was changed
8. **Prevention Measures**: How to avoid in future
9. **Lessons Learned**: Key takeaways
10. **Status**: RESOLVED/ONGOING/INVESTIGATING

## Contributing

When documenting a new issue:
1. Create a file with format: `YYYY-MM-DD-brief-description.md`
2. Follow the template format above
3. Update this index file
4. Link related issues if applicable