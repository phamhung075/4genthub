# 🚀 DhafnckMCP Complete Setup Guide

## 📋 Overview

This comprehensive guide will walk you through setting up DhafnckMCP from scratch, including all dependencies, configurations, and first-time usage. Whether you're a complete beginner or an experienced developer, this guide has you covered.

---

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ A fully functional DhafnckMCP platform running locally
- ✅ 43 specialized AI agents ready for collaboration
- ✅ Web dashboard accessible at http://localhost:3800
- ✅ MCP server running at http://localhost:8000
- ✅ Proper Claude Code integration with .mcp.json configuration
- ✅ Understanding of the 4-tier context system
- ✅ Your first AI-human collaborative project

---

## 📋 Prerequisites

### 🔧 Required Software

#### **Docker & Docker Compose** (Essential)
```bash
# Verify Docker installation
docker --version
docker-compose --version

# Should return version numbers like:
# Docker version 24.0.0
# Docker Compose version 2.20.0
```

**Installation Links:**
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)

#### **Git** (Essential)
```bash
# Verify Git installation
git --version
# Should return: git version 2.30.0 or higher
```

#### **WSL2** (Windows Only)
For Windows users, ensure WSL2 is installed and set as default:
```bash
# In PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

### 💻 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8GB | 16GB+ |
| **CPU** | 4 cores | 8 cores+ |
| **Storage** | 20GB free | 50GB+ free |
| **Network** | Broadband | High-speed |

### 🌐 Network Requirements

Ensure these ports are available:
- **3800**: Frontend React dashboard
- **8000**: Backend MCP server
- **5432**: PostgreSQL database (Docker)
- **6379**: Redis cache (Docker)

---

## 🏗️ Step 1: Repository Setup

### 📥 Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd agentic-project

# Verify repository structure
ls -la
# You should see: CLAUDE.md, CLAUDE.local.md, .mcp.json, docker-system/
```

### 🔍 Verify Project Structure

```bash
# Check essential directories
ls -la .claude/
ls -la docker-system/
ls -la dhafnck-frontend/
ls -la dhafnck_mcp_main/

# Verify configuration files
cat .mcp.json | head -10
cat CLAUDE.md | head -20
```

---

## 🐳 Step 2: Docker Environment Setup

### 🚀 Launch Docker Menu

```bash
# Make the script executable (if needed)
chmod +x docker-system/docker-menu.sh

# Launch the interactive Docker menu
./docker-system/docker-menu.sh
```

### 🎛️ Choose Your Configuration

The Docker menu presents several options:

```
╔════════════════════════════════════════════════════════╗
║             DhafnckMCP Docker Management               ║
║                  Build System v3.0                    ║
╚════════════════════════════════════════════════════════╝

🚀 Quick Start Options
────────────────────────────────────────────────────────
  1) 🐘 PostgreSQL Local (Recommended for beginners)
  2) ☁️  Supabase Cloud (Best for teams)
  3) ☁️🔴 Supabase + Redis (Enterprise mode)
  P) ⚡ Performance Mode (Low-resource PCs)
```

**For most users, choose Option 1: PostgreSQL Local**

### 📊 Configuration Details

#### **Option 1: PostgreSQL Local** (Recommended)
- **Best for**: Individual developers, local development
- **Database**: Local PostgreSQL in Docker
- **Cache**: Local Redis in Docker
- **Resources**: Moderate (8GB RAM minimum)

#### **Option 2: Supabase Cloud**
- **Best for**: Teams, shared development
- **Database**: Supabase managed PostgreSQL
- **Cache**: Local Redis in Docker
- **Setup**: Requires Supabase account

#### **Option 3: Supabase + Redis**
- **Best for**: Enterprise, production-like testing
- **Database**: Supabase managed PostgreSQL
- **Cache**: Redis Cloud or managed Redis
- **Setup**: Requires both Supabase and Redis cloud accounts

#### **Option P: Performance Mode**
- **Best for**: Low-resource systems, older computers
- **Database**: SQLite (local file)
- **Cache**: In-memory (no Redis)
- **Resources**: Minimal (4GB RAM)

---

## ⚙️ Step 3: Environment Configuration

### 📝 Environment Variables Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit environment file (use your preferred editor)
nano .env
# or
code .env
```

### 🔧 Essential Environment Variables

```bash
# Database Configuration (PostgreSQL Local)
DATABASE_URL=postgresql://dhafnck:password@localhost:5432/dhafnck_mcp
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dhafnck_mcp
DB_USER=dhafnck
DB_PASSWORD=password

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:3800

# MCP Configuration
MCP_ENABLED=true
MCP_LOG_LEVEL=INFO
```

### 🔑 Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file with generated keys
```

---

## 🏃‍♂️ Step 4: Initial Startup

### 🚀 Start the Platform

After choosing your Docker configuration, the system will:

1. **Pull Docker images** (first time only, ~5-10 minutes)
2. **Build custom containers** (~3-5 minutes)
3. **Initialize databases** (~1-2 minutes)
4. **Start all services** (~30 seconds)

### 📊 Monitor Startup Process

```bash
# Watch the logs during startup
docker-compose logs -f

# Check service status
docker-compose ps

# Verify all services are running
curl http://localhost:8000/health
curl http://localhost:3800
```

### ✅ Startup Verification

**Expected Output:**
```bash
# Health check should return:
{
  "status": "healthy",
  "timestamp": "2024-XX-XX",
  "services": {
    "database": "connected",
    "redis": "connected",
    "mcp_server": "running",
    "agents": "43 available"
  }
}
```

---

## 🌐 Step 5: First Access

### 📱 Web Dashboard

1. **Open your browser** to: http://localhost:3800
2. **You should see**: DhafnckMCP dashboard login/welcome screen
3. **Create your first account** (if required)

### 🔧 MCP Server

1. **Open your browser** to: http://localhost:8000
2. **You should see**: MCP server status page
3. **API documentation**: http://localhost:8000/docs

### 🛠️ API Testing

```bash
# Test basic API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/agents
curl http://localhost:8000/projects

# Expected responses should be JSON with appropriate data
```

---

## 🎯 Step 6: Claude Code Integration

### 📄 Verify .mcp.json Configuration

```bash
# Check MCP configuration
cat .mcp.json

# Verify server endpoints
curl -H "Accept: application/json" http://localhost:8000/mcp
```

### 🔗 Claude Code Setup

1. **Install Claude Code** (if not already installed)
2. **Configure MCP connection**:
   - Open Claude Code settings
   - Add MCP server configuration
   - Point to: http://localhost:8000/mcp

3. **Verify integration**:
   ```bash
   # Test MCP call from Claude Code
   mcp__dhafnck_mcp_http__call_agent(name_agent="master-orchestrator-agent")
   ```

### 📋 CLAUDE.md and CLAUDE.local.md

These files should already be configured correctly. Verify:

```bash
# Check global AI instructions
head -50 CLAUDE.md

# Check local environment rules
head -30 CLAUDE.local.md
```

---

## 🧪 Step 7: First Project Creation

### 🎬 Create Your First Project

1. **Access the dashboard**: http://localhost:3800
2. **Click "New Project"**
3. **Enter project details**:
   - **Name**: "My First AI Collaboration"
   - **Description**: "Learning DhafnckMCP basics"
   - **Type**: "Development"

### 🌿 Create a Branch

1. **Go to your project**
2. **Click "New Branch"**
3. **Enter branch details**:
   - **Name**: "feature/hello-world"
   - **Description**: "First feature implementation"

### 🎯 Create Your First Task

1. **Navigate to your branch**
2. **Click "New Task"**
3. **Enter task details**:
   - **Title**: "Create a simple Hello World application"
   - **Description**: "Build a basic app to test the platform"
   - **Assign to**: "@coding_agent"

### 🤖 Watch AI Agents Work

1. **Monitor task progress** in real-time
2. **View agent responses** and code generation
3. **See context flow** between agents
4. **Review completed work**

---

## 🔧 Step 8: Troubleshooting Common Issues

### 🐳 Docker Issues

#### Port Conflicts
```bash
# Check which process is using a port
lsof -i :3800
lsof -i :8000

# Kill conflicting processes
sudo kill -9 <PID>

# Or use different ports in docker-compose.yml
```

#### Container Startup Problems
```bash
# Check container logs
docker-compose logs dhafnck-backend
docker-compose logs dhafnck-frontend

# Restart specific service
docker-compose restart dhafnck-backend

# Full restart
docker-compose down && docker-compose up -d
```

#### Volume Permission Issues (Linux)
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./data
sudo chmod -R 755 ./data
```

### 🗄️ Database Issues

#### Connection Problems
```bash
# Test database connection
docker-compose exec postgres psql -U dhafnck -d dhafnck_mcp -c "SELECT 1;"

# Check database logs
docker-compose logs postgres

# Reset database (WARNING: destroys data)
docker-compose down -v
docker-compose up -d
```

#### Migration Issues
```bash
# Manual migration
docker-compose exec dhafnck-backend python -m alembic upgrade head

# Check migration status
docker-compose exec dhafnck-backend python -m alembic current
```

### 🌐 Network Issues

#### Frontend Not Loading
```bash
# Check frontend logs
docker-compose logs dhafnck-frontend

# Rebuild frontend
docker-compose down
docker-compose build dhafnck-frontend
docker-compose up -d
```

#### API Connection Issues
```bash
# Test API connectivity
curl -v http://localhost:8000/health

# Check backend logs
docker-compose logs dhafnck-backend

# Verify environment variables
docker-compose exec dhafnck-backend env | grep -E "(DB_|API_|MCP_)"
```

---

## 🎓 Step 9: Next Steps

### 📚 Learning Path

1. **Complete the Video Tutorial Series** (Episodes 1-12)
2. **Explore Agent Capabilities**: Try different agents for various tasks
3. **Learn Advanced Features**: Context management, workflows, customization
4. **Join the Community**: Share experiences and get help

### 🛠️ Customization Options

1. **Add Custom Agents**: Extend the agent library
2. **Configure Hooks**: Customize the .claude/hooks system
3. **Create Commands**: Add custom .claude/commands
4. **Modify UI**: Customize the React dashboard

### 🚀 Production Deployment

1. **Security Hardening**: Update secrets, enable HTTPS
2. **Scalability**: Configure load balancing, database clustering
3. **Monitoring**: Set up logging, metrics, alerting
4. **Backup**: Implement data backup and recovery

---

## 📊 Verification Checklist

Use this checklist to ensure everything is working correctly:

### ✅ System Health
- [ ] Docker containers are running (`docker-compose ps`)
- [ ] Health endpoint returns 200 (`curl http://localhost:8000/health`)
- [ ] Frontend loads (`http://localhost:3800`)
- [ ] Database connection works
- [ ] Redis connection works

### ✅ Basic Functionality
- [ ] Can create a project
- [ ] Can create a branch
- [ ] Can create a task
- [ ] Can assign agents to tasks
- [ ] Can view agent responses
- [ ] Context flows correctly between levels

### ✅ Claude Code Integration
- [ ] .mcp.json is properly configured
- [ ] Can call MCP agents from Claude Code
- [ ] CLAUDE.md and CLAUDE.local.md are loaded
- [ ] Hooks system is functioning

### ✅ Agent System
- [ ] All 43 agents are available
- [ ] Agents respond to assignments
- [ ] Context sharing works between agents
- [ ] Task completion workflows function

---

## 🆘 Getting Help

### 📞 Support Channels

1. **Documentation**: Check `ai_docs/` for detailed guides
2. **GitHub Issues**: Report bugs and request features
3. **Community Discord**: Real-time help and discussions
4. **Video Tutorials**: Watch setup and usage demonstrations

### 🐛 Reporting Issues

When reporting issues, include:
- **System information**: OS, Docker version, hardware specs
- **Error messages**: Full error logs and stack traces
- **Steps to reproduce**: Detailed reproduction instructions
- **Configuration**: Relevant parts of .env, .mcp.json, etc.

### 💡 Feature Requests

For feature requests:
- **Use case description**: Why you need the feature
- **Proposed solution**: How it should work
- **Alternatives considered**: Other approaches you've thought about
- **Additional context**: Any other relevant information

---

## 🎉 Congratulations!

You've successfully set up DhafnckMCP! You now have a powerful AI-human collaboration platform with:

- 🤖 **43 specialized AI agents** ready to help
- 🌐 **Beautiful web dashboard** for managing projects
- 🔗 **MCP protocol integration** for advanced AI workflows
- 📊 **4-tier context system** for intelligent collaboration
- 🛠️ **Extensible architecture** for customization

**What's Next?**
1. Explore the video tutorial series for in-depth learning
2. Create your first real project with multiple agents
3. Join the community to share your experiences
4. Contribute to the platform development

**Happy collaborating with AI! 🚀**