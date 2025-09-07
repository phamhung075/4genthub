#!/bin/bash

echo "==================================================================="
echo "Cleaning up duplicate configuration files and scripts"
echo "==================================================================="

# Remove duplicate environment files (keeping only .env.production and .env.example)
echo "Removing duplicate .env files..."
rm -f .env.backup-*
rm -f .env.clean-template
rm -f .env.final
rm -f .env.postgres-keycloak*
rm -f .env.production-clean
rm -f .env.production-final
rm -f .env.production-postgres-keycloak*
rm -f .env.production-unified

# Remove duplicate docker-compose files (keeping only docker-compose.yml and docker-compose.production.yml)
echo "Removing duplicate docker-compose files..."
rm -f docker-compose.final.yml
rm -f docker-compose.postgres*.yml
rm -f docker-compose.production-clean.yml
rm -f docker-compose.production-final.yml
rm -f docker-compose.production-postgres-keycloak.yml
rm -f docker-compose.unified.yml

# Remove duplicate startup scripts (keeping only start-production.sh)
echo "Removing duplicate startup scripts..."
rm -f start-clean*.sh
rm -f start-final.sh
rm -f start-postgres*.sh
rm -f start-production-clean*.sh
rm -f start-production-final.sh
rm -f start-production-postgres*.sh
rm -f start-unified*.sh
rm -f start_*.sh  # Remove underscore variants
rm -f start_mcp*.sh
rm -f stop-*.sh
rm -f stop_*.sh

# Remove duplicate authentication files
echo "Removing duplicate authentication files..."
rm -f dhafnck_mcp_main/src/fastmcp/auth/keycloak_auth_clean.py
rm -f dhafnck_mcp_main/src/fastmcp/auth/keycloak_auth_final.py
rm -f dhafnck_mcp_main/src/fastmcp/auth/keycloak_auth_production.py
rm -f dhafnck_mcp_main/src/fastmcp/auth/keycloak_auth_unified.py

# Remove duplicate MCP server files
echo "Removing duplicate MCP server files..."
rm -f dhafnck_mcp_main/src/mcp_http_server_clean.py
rm -f dhafnck_mcp_main/src/mcp_http_server_final.py
rm -f dhafnck_mcp_main/src/mcp_http_server_postgres_keycloak.py
rm -f dhafnck_mcp_main/src/mcp_http_server_production*.py
rm -f dhafnck_mcp_main/src/mcp_http_server_unified.py
rm -f dhafnck_mcp_main/src/mcp_server_*.py
rm -f mcp_http_server_clean.py

# Remove duplicate database config files
echo "Removing duplicate database config files..."
rm -f dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/database/database_config_clean.py
rm -f dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/database/database_config_postgres.py
rm -f dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/database/database_config_production.py

# Remove duplicate test files
echo "Removing duplicate test files..."
rm -f test-clean*.py
rm -f test-final*.py
rm -f test-keycloak*.py
rm -f test-production*.py
rm -f test-unified*.py
rm -f test_clean*.py
rm -f test_keycloak*.py
rm -f test_mcp*.py
rm -f test_postgres*.py
rm -f test_production*.py
rm -f test_unified*.py
rm -f dhafnck_mcp_main/test_keycloak_mcp.py

# Remove duplicate setup guides
echo "Removing duplicate setup documentation..."
rm -rf dhafnck_mcp_main/docs/setup-guides/
rm -f CLEAN_SETUP_GUIDE.md
rm -f KEYCLOAK_CLOUD_SETUP_GUIDE.md
rm -f SETUP_SUMMARY.md
rm -f UNIFIED_SETUP.md

# Remove other cleanup scripts
echo "Removing other cleanup scripts..."
rm -f cleanup-all-duplicates.sh
rm -f cleanup-old-configs.sh
rm -f cleanup-old-files.sh
rm -f cleanup-production.sh
rm -f setup_keycloak_postgres.sh
rm -f setup_postgres_keycloak*.sh

# Remove Dockerfile duplicates
echo "Removing duplicate Dockerfiles..."
rm -f Dockerfile.final
rm -f Dockerfile.production

echo "==================================================================="
echo "Cleanup complete! Remaining files:"
echo "==================================================================="
echo "Environment files:"
ls -la .env* 2>/dev/null | grep -v "/"
echo ""
echo "Docker Compose files:"
ls -la docker-compose*.yml 2>/dev/null
echo ""
echo "Startup scripts:"
ls -la start*.sh 2>/dev/null
echo ""
echo "==================================================================="