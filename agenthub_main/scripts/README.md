# Scripts Directory

This directory contains essential utility scripts for the agenthub project, organized for clarity and maintainability.

## Directory Structure

### Core Database Scripts
- `init_database.py` - **PRIMARY** database initialization script (replaces all migration scripts)
- `init.sql` - SQL initialization commands

### Database Utilities (`/database/`)
- `check_table_schema.py` - Validate database table schemas

### Authentication & Security
- `check-jwt-env.py` - JWT environment validation
- `jwt-authentication-verification.py` - Comprehensive JWT verification
- `quick-jwt-check.py` - Quick JWT token validation
- `fix-jwt-secrets.sh` - Fix JWT secret configuration
- `generate-secure-tokens.py` - Generate secure authentication tokens
- `generate_secure_secrets.py` - Generate secure secrets

### Docker & Deployment
- `docker-entrypoint.sh` - Main Docker container entrypoint
- `docker-entrypoint-optimized.sh` - Optimized Docker entrypoint
- `dev-entrypoint.sh` - Development environment entrypoint
- `deploy-frontend.sh` - Frontend deployment
- `deploy-mvp.sh` - MVP deployment script
- `publish-docker.sh` - Docker image publishing
- `manage_container.sh` - Container management utilities
- `unified-docker.sh` - Unified Docker operations

### MCP Server Management
- `run_mcp_server.sh` - Start MCP server
- `run_mcp_server_with_logging.sh` - Start MCP server with detailed logging
- `restart_mcp.sh` - Restart MCP server
- `wsl_mcp_bridge.sh` - WSL-specific MCP bridge

### Testing & Validation
- `test_runner.py` - Main test execution framework
- `test_schema_validation.py` - Database schema validation tests
- `test_keycloak_integration.py` - Keycloak integration tests
- `test_keycloak_mcp_integration.py` - Keycloak-MCP integration tests
- `validate_schema.py` - Schema validation utilities
- `validate_service_account.py` - Service account validation
- `run_tests_enhanced.sh` - Enhanced test runner
- `test-single-file.sh` - Single file test execution

### Development Tools
- `ddd_layer_tracer.py` - Domain-Driven Design layer analysis
- `enhanced_test_coverage_analyzer.py` - Test coverage analysis
- `cleanup_test_labels.py` - Test label cleanup utility
- `generate-claude-agents.py` - Claude agent generation
- `sync_agents_complete.py` - Complete agent synchronization
- `sync_agents_standalone.py` - Standalone agent sync
- `sync_agents_to_claude.py` - Claude agent synchronization

### System Administration
- `quick_start_postgres_keycloak.sh` - Quick PostgreSQL + Keycloak setup
- `quick_start_production.sh` - Production environment quick start
- `setup_pgadmin.sh` - pgAdmin setup
- `setup_session_persistence.sh` - Session persistence configuration
- `start-test-db.sh` - Start test database
- `start_inspector.sh` - Start system inspector
- `switch_database.sh` - Database switching utility
- `security-audit.sh` - Security audit script

### Diagnostic Tools
- `diagnose_mcp_connection.sh` - MCP connection diagnostics
- `diagnostic_connect.sh` - Connection diagnostics
- `check_cursor_logs.sh` - Cursor logs verification

### Test Support (`/test/` and `/test_templates/`)
- `test/test-keycloak-mcp-integration.py` - Keycloak-MCP integration tests
- `test/test_mcp_integration.py` - MCP integration tests
- `test_templates/` - Test template files for code generation

## Usage Guidelines

### Environment Setup
```bash
# Required environment variables
export DATABASE_TYPE=postgresql
export DATABASE_URL=postgresql://user:password@localhost:5432/agenthub
export KEYCLOAK_SERVER_URL=http://localhost:8080
export JWT_SECRET_KEY=your-secret-key
```

### Database Initialization
```bash
# Initialize database (recommended method)
python agenthub_main/scripts/init_database.py

# Verify schema
python agenthub_main/scripts/validate_schema.py
```

### Development Workflow
```bash
# Start development environment
./agenthub_main/scripts/quick_start_postgres_keycloak.sh

# Run tests
python agenthub_main/scripts/test_runner.py

# Deploy
./agenthub_main/scripts/deploy-mvp.sh
```

### Production Deployment
```bash
# Quick production setup
./agenthub_main/scripts/quick_start_production.sh

# Publish Docker images
./agenthub_main/scripts/publish-docker.sh
```

## Important Notes

### Clean Code Principles Applied
- **No backward compatibility scripts** - All legacy/migration scripts removed
- **No duplicate functionality** - Consolidated similar scripts
- **Essential scripts only** - Removed obsolete debugging and one-off scripts
- **Single source of truth** - `init_database.py` is the authoritative database setup

### Removed During Cleanup (2025-09-25)
- All Supabase-related scripts (89 files removed)
- All migration scripts (replaced by `init_database.py`)
- All backward compatibility scripts
- Duplicate authentication test scripts
- Obsolete debugging and development scripts
- **Total reduction**: 143 → 54 files (62% reduction)

### Safety & Security
- Always backup database before running schema scripts
- Validate environment variables before execution
- Run diagnostic scripts to verify system health
- Use test scripts to validate functionality before production deployment

### Support
- Scripts are self-documenting with `--help` flags where applicable
- Check individual script headers for specific usage instructions
- All scripts support both local and Docker container execution