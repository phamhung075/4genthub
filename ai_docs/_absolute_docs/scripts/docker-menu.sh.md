# Documentation for docker-menu.sh

## Purpose
Comprehensive Docker menu system for managing all aspects of the Docker-based development environment.

## Important File
**This file has documentation, indicating it's important and requires documentation updates when modified.**

## Access Methods

### 1. Convenience Wrapper (Recommended)
```bash
# From project root - uses build-menu.sh wrapper
./build-menu.sh
```

### 2. Direct Access
```bash
# From project root
./docker-system/docker-menu.sh
```

**Note:** `build-menu.sh` in the project root is a convenience wrapper that automatically redirects to `docker-system/docker-menu.sh`. Both provide identical functionality.

## Description
The docker-menu.sh script provides a sophisticated interactive menu system for Docker operations with multiple deployment configurations:

### Build Configurations
1. **PostgreSQL Local** - Backend + Frontend with local PostgreSQL database
2. **Supabase Cloud** - Uses remote Supabase database (no Redis)
3. **Supabase Cloud + Redis** - Full stack with Supabase and Redis caching

### Development Modes
- **Development Mode (Non-Docker)** - Local development with hot reload
- **Performance Mode** - Optimized for low-resource PCs
- **Force Complete Rebuild** - Fresh rebuild removing all cached data

### Management Operations
- Service status monitoring
- Log viewing and analysis
- Database shell access
- Docker system cleanup
- Performance monitoring

## Quick Start Examples

```bash
# Interactive menu
./build-menu.sh

# Direct commands
./build-menu.sh start-dev    # Start development mode
./build-menu.sh restart-dev  # Restart with changes
./build-menu.sh stop-dev     # Stop development mode
```

## Key Features

### Build Optimization
- `--no-cache` builds ensure fresh code changes
- BuildKit optimization with provenance disabled
- Automatic port conflict resolution (8000, 3800)
- Python cache clearing

### Port Management
- Automatically stops containers using required ports
- Ensures clean startup without conflicts

### Environment Configuration
- Automatic .env file detection and validation
- Support for multiple database backends
- JWT authentication configuration

## Location
- Main Script: `docker-system/docker-menu.sh`
- Convenience Wrapper: `build-menu.sh` (project root)
- Comprehensive Documentation: `ai_docs/development-guides/docker-system-guide.md`
- This File: `ai_docs/_absolute_docs/scripts/docker-menu.sh.md`

## Dependencies
- Docker (with BuildKit support)
- Docker Compose
- Bash shell

## Related Documentation
See `ai_docs/development-guides/docker-system-guide.md` for comprehensive documentation including:
- Complete system architecture
- Backend MCP server details
- Frontend-backend communication
- Authentication flows
- Troubleshooting guides

## Last Updated
2025-10-16 - Updated to include build-menu.sh wrapper and comprehensive feature list