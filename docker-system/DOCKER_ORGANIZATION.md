# Docker System Organization

## Overview
The DhafnckMCP Docker infrastructure is managed through a centralized menu system that provides multiple deployment configurations.

## Entry Point
```bash
./docker-system/docker-menu.sh
```

## Active Docker Compose Configurations

### Production Configurations (in `dhafnck_mcp_main/docker/`)
1. **docker-compose.postgresql.yml**
   - Local PostgreSQL database
   - Backend + Frontend services
   - Port 5432 for PostgreSQL
   - Used via menu option 1

2. **docker-compose.supabase.yml**
   - Supabase Cloud database connection
   - No local database container
   - Requires .env configuration
   - Used via menu option 2

3. **docker-compose.redis.yml**
   - Redis cache layer
   - Used in combination with Supabase
   - Port 6379 for Redis
   - Used via menu option 3 (with Supabase)

### Auto-Generated Configurations (in `docker-system/docker/`)
1. **docker-compose.optimized.yml**
   - Created dynamically by docker-menu.sh
   - Optimized for low-resource PCs
   - Resource limits applied
   - Alpine-based images
   - Used via menu option P

## Menu Options

### Build Configurations
- **1)** 🐘 PostgreSQL Local (Backend + Frontend)
- **2)** ☁️ Supabase Cloud (No Redis)
- **3)** ☁️🔴 Supabase Cloud + Redis (Full Stack)

### Performance Mode
- **P)** 🚀 Start Optimized Mode (Low-resource PC support)
- **M)** 📊 Monitor Performance (Live stats)

### Management Options
- **4)** 📊 Show Status
- **5)** 🛑 Stop All Services
- **6)** 📜 View Logs
- **7)** 🗄️ Database Shell
- **8)** 🧹 Clean Docker System
- **9)** 🔄 Force Complete Rebuild
- **0)** 🚪 Exit

## Key Features

### All Builds Use `--no-cache`
- Ensures latest code changes are included
- No hot reload in production mode
- Complete rebuild for code updates

### Port Configuration
- Backend: Port 8000
- Frontend: Port 3800
- PostgreSQL: Port 5432 (when local)
- Redis: Port 6379 (when enabled)

### Environment Variables
- Supabase configurations read from `.env`
- DATABASE_TYPE automatically set based on configuration
- Support for multiple database backends

### Performance Optimizations
- Automatic port conflict resolution
- Container cleanup before builds
- Python cache clearing
- Docker build cache management
- Resource limits for low-spec machines

## Obsolete Files
All unused docker-compose files have been moved to backup directories:
- `dhafnck_mcp_main/docker/obsolete_docker_compose_backup/`
- `docker-system/docker/obsolete_docker_compose_backup/`

These can be safely deleted once confirmed they are no longer needed.

## Best Practices
1. Always use `docker-menu.sh` for Docker operations
2. Choose configuration based on your environment:
   - Local development: PostgreSQL Local
   - Cloud development: Supabase Cloud
   - Production: Supabase + Redis
   - Low-spec PC: Performance Mode
3. Use Force Rebuild (option 9) when switching between configurations
4. Monitor performance (option M) to track resource usage