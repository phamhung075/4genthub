# Frontend Development Quick Start Guide

## 🚀 Getting Started

This guide helps you quickly start frontend development for agenthub with the newly fixed development environment.

## ✅ Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ (for local development) 
- Git repository cloned

## 🔧 Setup Steps

### 1. Test Your Environment
```bash
# Validate your development environment
./docker-system/test-frontend-dev.sh
```

### 2. Start Development Environment
```bash
cd docker-system

# Build the development container (first time only)
docker-compose build frontend

# Start frontend development server
docker-compose up frontend
```

### 3. Access Your Application
- **Frontend**: http://localhost:3800
- **API Proxy**: http://localhost:3800/api
- **Backend**: http://localhost:8000

## 🔥 Development Features

### Hot Reload
Changes to these files will automatically trigger browser updates:
- `agenthub-frontend/src/**` - All source code
- `agenthub-frontend/public/**` - Static assets
- `agenthub-frontend/vite.config.ts` - Vite configuration

### Environment Variables
Development environment automatically loads:
- `VITE_API_URL=http://localhost:8000`
- `NODE_ENV=development`
- Supabase configuration from `.env`

### Debugging
```bash
# View logs
docker-compose logs frontend

# Interactive shell
docker-compose exec frontend sh

# Check Node.js version
docker-compose exec frontend node --version

# Check installed packages
docker-compose exec frontend npm list
```

## 🛠 Common Tasks

### Install New Dependencies
```bash
# Stop container
docker-compose stop frontend

# Add dependency to package.json manually, then:
docker-compose build --no-cache frontend
docker-compose up frontend
```

### Reset Development Environment
```bash
# Complete reset
docker-compose down
docker system prune -f
docker-compose build --no-cache frontend
docker-compose up frontend
```

### Production Build Test
```bash
# Test production build locally
cd agenthub-frontend
npm run build
npm run preview
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| ESM import errors | Run `docker-compose build --no-cache frontend` |
| Port 3800 not accessible | Check `.env` has `FRONTEND_PORT=3800` |
| Hot reload not working | Verify volume mounts in docker-compose.yml |
| Permission errors | Check container runs as non-root user |
| Build failures | Check Node.js version is 20+ |

### Debug Commands
```bash
# Check container health
docker-compose ps

# View all logs
docker-compose logs

# Restart just frontend
docker-compose restart frontend

# Force rebuild everything
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `docker-system/docker/Dockerfile.frontend.dev` | Development container |
| `agenthub-frontend/vite.config.ts` | Vite configuration |
| `docker-system/docker-compose.yml` | Service orchestration |
| `.env` | Environment variables |
| `agenthub-frontend/package.json` | Dependencies |

## 🎯 Development Workflow

1. **Start**: `docker-compose up frontend`
2. **Code**: Edit files in `agenthub-frontend/src/`
3. **Test**: Browser auto-refreshes at http://localhost:3800
4. **Debug**: Use browser DevTools + container logs
5. **Commit**: Changes persist automatically

## 🚀 What's Fixed

✅ **Node.js 20**: Compatible with Vite 7.1.3  
✅ **Port 3800**: Consistent across all configurations  
✅ **Hot Reload**: Volume mounts for instant updates  
✅ **Security**: Non-root user in container  
✅ **Performance**: Optimized development builds  

---

**Need Help?** Check `ai_docs/troubleshooting-guides/frontend-development-environment-fix.md` for detailed troubleshooting.