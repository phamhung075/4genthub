# Troubleshooting Guides

This folder contains comprehensive troubleshooting documentation to help diagnose and resolve common issues with the agenthub platform.

## 📋 Contents

### Core Guides
- **[Comprehensive Troubleshooting Guide](COMPREHENSIVE_TROUBLESHOOTING_GUIDE.md)** - Systematic problem diagnosis with detailed solutions
- **[Quick Troubleshooting Reference](TROUBLESHOOTING.md)** - Common issues and quick fixes

### Database & Connection Issues
- **[Legacy Database Columns Analysis](legacy-database-columns.md)** - Analysis of 19 extra database columns not in models, migration strategy, and risk assessment
- **[Supabase Connection Fix Guide](supabase-connection-fix-guide.md)** - Fix for Supabase data not showing after Docker rebuild
- **[Fix Supabase Connection](fix-supabase-connection.md)** - Detailed Supabase connection troubleshooting steps
- **[Frontend Supabase Fix Summary](frontend-supabase-fix-summary.md)** - Frontend-specific Supabase connection solutions

### Docker Configuration Issues
- **Unified Docker Setup**: All Docker configurations consolidated to single `docker-compose.yml` with profiles
- **Port Conflicts**: Backend runs on 8000, Frontend on 3000 (changed from 3800)
- **Environment Variables**: Single `.env` file at project root instead of scattered config files
- **Memory Issues**: Frontend memory crashes resolved with increased NODE_OPTIONS (1536MB)

## 🔍 Troubleshooting Approach

Our troubleshooting guides follow a systematic approach:

1. **Problem Identification** - Clear symptoms and error descriptions
2. **Root Cause Analysis** - Step-by-step diagnostic procedures
3. **Solution Implementation** - Detailed resolution steps
4. **Prevention Measures** - How to avoid future occurrences
5. **Escalation Paths** - When to seek additional help

## 🎯 Common Issues Covered

- Database connection problems (PostgreSQL, Supabase)
- Database schema inconsistencies and legacy column issues
- MCP tool integration issues
- Context system errors
- Agent orchestration failures
- Performance bottlenecks
- Docker configuration problems
- Frontend memory crashes
- Port conflicts and networking
- Environment variable issues

## 👥 Audience

- **Developers**: Technical troubleshooting and debugging
- **System Administrators**: Operational issue resolution
- **Support Teams**: User assistance and problem resolution
- **End Users**: Self-service troubleshooting