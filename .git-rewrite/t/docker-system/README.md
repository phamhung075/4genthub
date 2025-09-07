# DhafnckMCP Docker Management System

A streamlined Docker management interface for the DhafnckMCP project with unified Docker configuration and multiple deployment modes.

## Quick Start

```bash
# From project root (recommended)
./docker-menu.sh

# OR from docker-system directory
cd docker-system && ./docker-menu.sh
```

## Build Configurations

### 1. PostgreSQL Local (Option 1)
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- **Use for**: Standard local development with local database

### 2. Supabase Cloud (Option 2) ⭐ RECOMMENDED
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Database: Supabase Cloud (remote)
- **Requirements**: .env file with Supabase credentials
- **Use for**: Development with cloud database (no local DB required)

### 3. Supabase Cloud + Redis (Option 3)
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Database: Supabase Cloud
- Redis: localhost:6379 (for caching)
- **Requirements**: .env file with Supabase credentials
- **Use for**: Full stack with caching and performance optimization

### P. Performance Mode (Option P)
- Optimized for low-resource PCs
- Reduced memory and CPU usage
- **Use for**: Systems with limited resources

## Key Features

- ✅ All builds use `--no-cache` (no hot reload)
- ✅ **Automatic cleanup of existing builds** (saves disk space since --no-cache doesn't need old versions)
- ✅ **Automatic port conflict resolution** (stops conflicting containers before starting)
- ✅ Consistent port mapping: Backend 8000, Frontend 3000
- ✅ Interactive menu interface
- ✅ Service status monitoring
- ✅ Log viewing and database shell access
- ✅ Comprehensive Docker system cleanup tools

## Management Options

- **Show Status**: View all running containers
- **Stop All Services**: Stop all Docker containers
- **View Logs**: Access logs for specific services
- **Database Shell**: Direct access to PostgreSQL/Redis
- **Clean Docker System**: Remove unused Docker resources

## Environment Requirements

Make sure your `.env` file contains:
```bash
# For Supabase configurations
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_DATABASE_URL=your_database_url

# For Redis configurations
REDIS_PASSWORD=dev_redis_password_123
```

## Usage Examples

### Start PostgreSQL Local Configuration
```bash
cd docker-system
./docker-menu.sh
# Select option 1
```

### Stop All Services
```bash
cd docker-system
./docker-menu.sh
# Select option 6
```

## Troubleshooting

### Port Already Allocated Error
If you see "Bind for 0.0.0.0:8000 failed: port is already allocated":

```bash
# Stop existing containers
docker stop $(docker ps -q --filter "publish=8000") $(docker ps -q --filter "publish=3800")

# Remove stopped containers  
docker container prune -f

# Try starting again
./docker-menu.sh
```

**Root Cause**: Previous Docker containers are still running on ports 8000 or 3800
**Prevention**: The system now automatically handles this - it stops conflicting containers before starting new ones

### Automatic Build Cleanup
The system automatically cleans up existing Docker images before each build because:
- All builds use `--no-cache` flag (fresh builds every time)
- Old image versions are unnecessary and waste disk space
- Each configuration build removes previous dhafnck project images

**What gets cleaned automatically**:
- Previous dhafnck project images (`*dhafnck*`, `docker-*`)
- Dangling images and build cache
- Stopped containers using ports 8000/3800

**Manual cleanup**: Use menu option 9 "Clean Docker System" for comprehensive cleanup

### View Backend Logs
```bash
cd docker-system
./docker-menu.sh
# Select option 7, then option 1
```

## File Structure

```
docker-system/
├── docker-menu.sh                          # Main interface script
├── docker/
│   ├── docker-compose.postgresql-local.yml # PostgreSQL + Redis local
│   ├── docker-compose.supabase.yml         # Supabase cloud only
│   ├── docker-compose.redis-postgresql.yml # Redis + PostgreSQL local
│   └── docker-compose.redis-supabase.yml   # Redis + Supabase cloud
└── README.md                               # This file
```

## Notes

- All configurations build without cache to ensure latest code changes
- Hot reload is disabled for consistent production-like builds
- Frontend always runs on port 3800
- Backend always runs on port 8000
- Services automatically restart unless stopped manually