# Claude Commands
directory to check : $ARGUMENTS 
This directory contains custom commands for managing the DhafnckMCP project.

## Test File Management Commands

### manage-test-files

Move individual test files to their correct location in the project structure.

**Usage:**
```bash
manage-test-files <test_file_path>
```

**Features:**
- Analyzes test file content to determine type (unit, integration, e2e, performance)
- Detects outdated test files based on markers and patterns
- Suggests correct location based on project structure
- Updates imports after moving (requires manual review)

**Example:**
```bash
manage-test-files test_dependency_debug.py
```

### manage-test-files-bulk

Bulk operations for test file management across the entire project.

**Usage:**
```bash
manage-test-files-bulk [OPTIONS]
```

**Options:**
- `--scan-all`: Scan entire project for test files
- `--dry-run`: Show what would be done without making changes
- `--auto-move`: Automatically move misplaced files without prompting
- `--help`: Show help message

**Example:**
```bash
# Scan and report on all test files
manage-test-files-bulk --scan-all

# Automatically move all misplaced files
manage-test-files-bulk --scan-all --auto-move
```

### manage-test-files-smart

Intelligent test file management that reads project documentation to make informed decisions.

**Usage:**
```bash
manage-test-files-smart <test_file>
```

**Features:**
- Reads testing.md to understand test organization patterns
- Reads domain-driven-design.md for DDD patterns
- Provides detailed analysis and recommendations
- Validates against documented project standards
- Offers multiple action choices for each file

**Example:**
```bash
manage-test-files-smart test_task_completion.py
```

## Test Organization Structure

According to the project documentation, tests should be organized as follows:

```
dhafnck_mcp_main/src/tests/
├── unit/                    # Unit tests for individual components
│   ├── domain/             # Domain logic tests
│   ├── application/        # Application service tests
│   └── infrastructure/     # Infrastructure layer tests
├── integration/            # Integration tests
│   ├── database/          # Database integration tests
│   ├── mcp_tools/         # MCP tool integration tests
│   └── facades/           # Facade integration tests
├── e2e/                   # End-to-end workflow tests
│   ├── task_workflows/    # Complete task workflows
│   ├── project_workflows/ # Project management workflows
│   └── agent_workflows/   # Agent orchestration workflows
├── performance/           # Performance and load tests
└── fixtures/             # Test data and utilities
```

## Identifying Outdated Tests

The commands identify outdated tests based on:
- Deprecation markers (DEPRECATED, OUTDATED, OLD, DO NOT USE)
- Filename patterns (debug, temp, backup, old, copy)
- File age (not modified in 90+ days)
- Missing test functions
- Multiple missing imports/references
- High number of TODO/FIXME markers

## Current Status

Based on the scan performed on 2025-07-31:
- **Misplaced Test Files:** 14 files found in project root and dhafnck_mcp_main root
- **Potentially Outdated Files:** 19 files identified as potentially outdated
- **Correctly Placed Files:** 137 files already in correct locations

## Recommendations

1. Run `manage-test-files-bulk --scan-all --auto-move` to move all misplaced files
2. Review the 19 potentially outdated files and remove if no longer needed
3. Use `git rm` to remove files to maintain version history
4. After cleanup, run tests to ensure nothing is broken