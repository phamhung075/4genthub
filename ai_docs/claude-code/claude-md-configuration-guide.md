# 📋 CLAUDE.md & CLAUDE.local.md Configuration Guide

## 📋 Overview

This comprehensive guide covers the configuration and customization of CLAUDE.md and CLAUDE.local.md files - the core instruction files that define how AI agents behave within the DhafnckMCP system. These files implement the revolutionary DhafnckMCP Agent System that transforms Claude into a professional enterprise employee.

---

## 🏗️ File Structure & Purpose

### 📁 File Locations

```
/home/daihungpham/__projects__/agentic-project/CLAUDE.md          # Global AI instructions (checked into git)
/home/daihungpham/__projects__/agentic-project/CLAUDE.local.md    # Local environment rules (not checked in)
```

### 🎯 File Purposes

| File | Purpose | Version Control | Scope |
|------|---------|----------------|-------|
| **CLAUDE.md** | Global AI agent instructions | ✅ Checked in | All environments |
| **CLAUDE.local.md** | Local environment rules | ❌ Not checked in | Local development only |

---

## 📄 CLAUDE.md - Global AI Instructions

### 🎭 Core Concept: Enterprise Employee Model

CLAUDE.md implements a revolutionary approach where Claude operates as a **professional enterprise employee** rather than an independent AI. This creates:

- **Accountability**: All work tracked in MCP tasks
- **Professionalism**: Structured workflows and reporting
- **Collaboration**: Team-based approach with 43 specialized agents
- **Transparency**: Complete visibility into AI work processes

### 🏢 Key Sections Breakdown

#### **1. Professional Identity Section**
```markdown
## 🏢 YOU ARE AN ENTERPRISE EMPLOYEE - NOT A FREELANCER

### YOUR PROFESSIONAL IDENTITY:
**You are Claude, a PROFESSIONAL EMPLOYEE in the DhafnckMCP Enterprise System**
- **NOT** an independent AI working alone
- **NOT** making decisions in isolation
- **NOT** working without documentation
- **YOU ARE** part of a structured organization with rules, workflows, and reporting requirements
```

**Purpose**: Establishes Claude's role as a team member, not a solo operator.

#### **2. Clock-In System**
```markdown
## 🚨 ABSOLUTE FIRST PRIORITY - CLOCK IN TO WORK! 🚨

**Like any employee starting their shift, you MUST clock in:**
```typescript
mcp__dhafnck_mcp_http__call_agent("master-orchestrator-agent")
```
```

**Purpose**: Ensures proper initialization and role assignment for every session.

#### **3. Dynamic Tool Enforcement v2.0**
```markdown
## 🔒 DYNAMIC TOOL ENFORCEMENT v2.0 - CRITICAL SECURITY UPDATE

### Revolutionary Change: From Static to Dynamic Tool Permissions
**BREAKING CHANGE**: Tool permissions are NO LONGER static configurations.
```

**Purpose**: Implements security through role-based tool access control.

#### **4. Enterprise Task Management**
```markdown
## 📊 ENTERPRISE TASK MANAGEMENT SYSTEM - YOUR WORK TRACKER

### WHY `mcp__dhafnck_mcp_http__manage_task` IS YOUR PROFESSIONAL DUTY

**ENTERPRISE FUNDAMENTAL TRUTH:**
> **Like any employee, you MUST report your work status regularly**
```

**Purpose**: Enforces professional work tracking and transparency.

### 🔧 Configuration Principles

#### **Scope & Environment Rules**
```markdown
---
scope: global
- Only uses environment variables and remove any hardcoded secrets
- No backward, no legacy, no compatibility code
- debug addressing the root cause, do not fixing symptoms only
```

**Key Principles:**
1. **Clean Architecture**: No legacy code, current standards only
2. **Security First**: Environment variables, no hardcoded secrets
3. **Root Cause Focus**: Address problems at their source
4. **DDD Compliance**: Domain-Driven Design patterns

#### **Environment Variables Enforcement**
```markdown
Environment Variables
- All configuration values must come from environment variables—no hardcoded values allowed.
- If any required environment variable is missing, the system must raise an error.
- Shared repository configuration logic is centralized in utils.py to follow DRY principles.
```

---

## 📄 CLAUDE.local.md - Local Environment Configuration

### 🏠 Local-Specific Rules

CLAUDE.local.md contains environment-specific configurations that complement the global CLAUDE.md instructions.

#### **1. Project Structure Definition**
```markdown
## Core Project Structure
**Source Code Paths:**
- `dhafnck-frontend/` - Frontend (React/TypeScript, port 3800)
- `dhafnck_mcp_main/src/` - Backend (Python/FastMCP/DDD)
- `dhafnck_mcp_main/src/tests/` - Test files

**Important Paths to Ignore:**
- `00_RESOURCES/*` - Reference materials only
- `00_RULES/*` - Legacy rules (use CLAUDE.md instead)
```

#### **2. System Architecture Details**
```markdown
## System Architecture
**4-Tier Context Hierarchy:**
```
GLOBAL → PROJECT → BRANCH → TASK
```
- Inheritance flows downward
- UUID-based identification
- Auto-creation on demand
```

#### **3. Local Environment Configuration**
```markdown
### Local System Information
- **Backend URL**: http://localhost:8000
- **Frontend URL**: http://localhost:3800
- **Database Path**: `/data/dhafnck_mcp.db` (Docker volume)
- **Documentation**: `ai_docs/`
- **Tests**: `dhafnck_mcp_main/src/tests/`
- **Docker Menu**: `docker-system/docker-menu.sh`
```

### 📚 Documentation System Integration

#### **AI Documentation Architecture**
```markdown
### AI Documentation System Overview
The documentation system provides intelligent tracking, automatic indexing, and selective enforcement.

```
ai_docs/
├── _absolute_docs/           # File-specific documentation (marks importance)
├── _obsolete_docs/          # Auto-archived when source files deleted
├── index.json               # Auto-generated documentation index (by hooks)
├── api-integration/         # API documentation
├── authentication/          # Auth system documentation
└── ...                     # 17 standard folders
```
```

---

## ⚙️ Configuration Strategies

### 🎯 Environment-Specific Overrides

#### **Development Environment**
```markdown
## Development Configuration (CLAUDE.local.md)
- On dev, The system should be using Keycloak for authentication and local PostgreSQL docker for the database
- Keycloak is the source of truth for user authentication
- docker-menu.sh option R for rebuild
- The ORM model should be the source of truth
```

#### **Production Environment**
```markdown
## Production Configuration (CLAUDE.local.md)
- Use managed PostgreSQL service
- Enable HTTPS and security headers
- Implement rate limiting and monitoring
- Use production Keycloak instance
```

### 🔒 File System Protection

#### **Root Directory Restrictions**
```markdown
### Root Directory Restrictions
- **NO file creation in root** except files listed in `.allowed_root_files`
- **NO folder creation in root** - all folders should already exist
- **Allowed root files only**: README.md, CHANGELOG.md, TEST-CHANGELOG.md, CLAUDE.md, CLAUDE.local.md
```

#### **Documentation Enforcement**
```markdown
### Selective Documentation Enforcement
- **Smart Blocking**: Only blocks modifications to files/folders WITH existing documentation
- **Session Tracking**: 2-hour sessions prevent repeated blocking during active work
- **User-Controlled**: Files are marked important by creating documentation for them
```

---

## 🔧 Customization Guide

### 📝 Adding Custom Instructions

#### **Global Instructions (CLAUDE.md)**
Add new sections to CLAUDE.md for project-wide rules:

```markdown
## Custom Global Rule: Code Quality Standards

### Mandatory Code Practices
- All functions must have type hints (Python) or TypeScript definitions
- Maximum function length: 50 lines
- All public methods require docstrings
- Unit test coverage minimum: 80%

### Code Review Requirements
- All code changes require peer review
- Security-sensitive changes require security team approval
- Performance changes require performance testing
```

#### **Local Instructions (CLAUDE.local.md)**
Add environment-specific rules to CLAUDE.local.md:

```markdown
## Custom Local Rule: Development Workflow

### Local Development Practices
- Use Docker for all dependencies
- Run tests before committing
- Use feature branches for all changes
- Local database: PostgreSQL in Docker container

### IDE Configuration
- VSCode with Python extension
- ESLint and Prettier for frontend
- Black formatter for Python
- Pre-commit hooks enabled
```

### 🎛️ Agent Behavior Customization

#### **Custom Agent Instructions**
```markdown
## Custom Agent Behaviors

### Coding Agent Enhancements
- Always use dependency injection patterns
- Implement logging for all public methods
- Follow Domain-Driven Design principles
- Generate comprehensive error handling

### Documentation Agent Enhancements
- Include code examples in all documentation
- Generate API documentation automatically
- Create user-friendly setup guides
- Maintain changelog for all updates
```

#### **Workflow Customizations**
```markdown
## Custom Workflow Patterns

### Feature Development Workflow
1. Create branch from main
2. Implement feature with tests
3. Update documentation
4. Run quality checks
5. Submit for review
6. Deploy to staging
7. Validate in staging
8. Deploy to production

### Bug Fix Workflow
1. Reproduce issue in tests
2. Implement fix
3. Verify fix resolves issue
4. Check for regression
5. Update documentation if needed
6. Deploy with monitoring
```

---

## 🧪 Testing & Validation

### ✅ Configuration Validation

#### **CLAUDE.md Validation Script**
```python
#!/usr/bin/env python3
"""Validate CLAUDE.md configuration."""

import re
from pathlib import Path

def validate_claude_md():
    """Validate CLAUDE.md structure and content."""
    claude_file = Path("CLAUDE.md")

    if not claude_file.exists():
        print("❌ CLAUDE.md not found")
        return False

    content = claude_file.read_text()

    # Check for required sections
    required_sections = [
        "DhafnckMCP Agent System",
        "ENTERPRISE EMPLOYEE",
        "CLOCK IN TO WORK",
        "DYNAMIC TOOL ENFORCEMENT",
        "ENTERPRISE TASK MANAGEMENT"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        print(f"❌ Missing required sections: {missing_sections}")
        return False

    print("✅ CLAUDE.md validation passed")
    return True

if __name__ == "__main__":
    validate_claude_md()
```

#### **CLAUDE.local.md Validation Script**
```python
#!/usr/bin/env python3
"""Validate CLAUDE.local.md configuration."""

import re
from pathlib import Path

def validate_claude_local_md():
    """Validate CLAUDE.local.md structure and content."""
    claude_file = Path("CLAUDE.local.md")

    if not claude_file.exists():
        print("❌ CLAUDE.local.md not found")
        return False

    content = claude_file.read_text()

    # Check for required local sections
    required_sections = [
        "Core Project Structure",
        "System Architecture",
        "Local System Information",
        "Documentation Architecture"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        print(f"❌ Missing required sections: {missing_sections}")
        return False

    # Check for development-specific configurations
    if "localhost:3800" not in content:
        print("❌ Missing frontend URL configuration")
        return False

    if "localhost:8000" not in content:
        print("❌ Missing backend URL configuration")
        return False

    print("✅ CLAUDE.local.md validation passed")
    return True

if __name__ == "__main__":
    validate_claude_local_md()
```

### 🔍 Behavioral Testing

#### **Agent Initialization Test**
```python
def test_agent_initialization():
    """Test that agents properly initialize with CLAUDE.md instructions."""

    # This would be implemented as an integration test
    # to verify that Claude properly loads and follows instructions

    # Test checklist:
    # 1. Agent calls clock-in function first
    # 2. Agent follows enterprise employee model
    # 3. Agent creates MCP tasks for complex work
    # 4. Agent uses appropriate tools for role
    # 5. Agent reports progress regularly

    pass
```

#### **Configuration Override Test**
```python
def test_configuration_overrides():
    """Test that CLAUDE.local.md properly overrides CLAUDE.md."""

    # Test checklist:
    # 1. Local database settings override global
    # 2. Development URLs used instead of production
    # 3. Local file paths recognized
    # 4. Environment-specific rules applied

    pass
```

---

## 🛠️ Troubleshooting

### 🔍 Common Issues

#### **Issue 1: Agent Not Following Instructions**
```markdown
**Symptoms:**
- Agent makes direct changes without creating MCP tasks
- Agent doesn't report progress
- Agent uses tools not appropriate for role

**Diagnosis:**
1. Check if CLAUDE.md is being loaded
2. Verify call_agent function is called first
3. Check for syntax errors in CLAUDE.md

**Solution:**
1. Ensure CLAUDE.md is in project root
2. Verify file encoding is UTF-8
3. Check for markdown syntax errors
4. Test with minimal CLAUDE.md configuration
```

#### **Issue 2: Local Overrides Not Working**
```markdown
**Symptoms:**
- Production URLs used in development
- Wrong database configurations
- Local paths not recognized

**Diagnosis:**
1. Check if CLAUDE.local.md exists
2. Verify file is not in .gitignore
3. Check section headers match CLAUDE.md format

**Solution:**
1. Create CLAUDE.local.md in project root
2. Ensure proper markdown formatting
3. Verify local configurations override global
4. Test with simple override example
```

#### **Issue 3: Hook System Not Working**
```markdown
**Symptoms:**
- File system protection not working
- Documentation not auto-updating
- Status lines not showing

**Diagnosis:**
1. Check .claude/hooks directory exists
2. Verify hook scripts are executable
3. Check for Python errors in hooks

**Solution:**
1. Ensure hooks are properly configured
2. Check hook script permissions
3. Verify Python dependencies installed
4. Test hooks individually
```

### 🚨 Emergency Fixes

#### **Minimal Working CLAUDE.md**
If your CLAUDE.md is corrupted, use this minimal version:

```markdown
# DhafnckMCP Agent System - Minimal Configuration

## Professional Identity
You are Claude, a professional AI agent in the DhafnckMCP system.

## Required First Action
Always call: `mcp__dhafnck_mcp_http__call_agent("master-orchestrator-agent")`

## Core Rules
1. Create MCP tasks for complex work
2. Report progress regularly
3. Use appropriate tools for your role
4. Follow professional workflows

## Environment Variables
Use environment variables for all configuration.
Never hardcode secrets or URLs.
```

#### **Minimal Working CLAUDE.local.md**
```markdown
# DhafnckMCP Local Configuration

## Project Structure
- Frontend: http://localhost:3800
- Backend: http://localhost:8000
- Database: Local PostgreSQL Docker

## Development Rules
- Use Docker for all services
- Run tests before commits
- Follow local development practices
```

---

## 📊 Performance Optimization

### ⚡ Configuration Loading

#### **Optimize File Size**
```markdown
# Keep CLAUDE.md focused and concise
# Use links to external documentation for detailed guides
# Avoid repetitive content
# Use clear, scannable formatting

## Example: Instead of duplicating content
See [Complete Agent Guide](ai_docs/agents/complete-guide.md) for full details.

## Example: Instead of long lists
Core agents: coding, debugging, testing, documentation
[View full agent list](ai_docs/agents/agent-directory.md)
```

#### **Efficient Processing**
```markdown
# Use clear section headers for fast parsing
# Group related rules together
# Use bullet points for scannable content
# Include quick reference sections

## Quick Reference
- Clock in: call_agent("master-orchestrator-agent")
- Complex work: Create MCP task first
- Progress: Update tasks regularly
- Tools: Use role-appropriate tools only
```

### 📈 Monitoring & Analytics

#### **Usage Tracking**
```python
# Track which sections of CLAUDE.md are most referenced
# Monitor compliance with configuration rules
# Analyze agent behavior patterns
# Identify optimization opportunities

def track_configuration_usage():
    """Track how often different configuration sections are referenced."""
    # Implementation would log which sections are accessed
    # during agent operations for optimization insights
    pass
```

---

## 📋 Best Practices

### ✅ Configuration Management

#### **Version Control Strategy**
```bash
# CLAUDE.md - Always commit
git add CLAUDE.md
git commit -m "Update global AI instructions"

# CLAUDE.local.md - Never commit
echo "CLAUDE.local.md" >> .gitignore

# Create template for team members
cp CLAUDE.local.md CLAUDE.local.md.example
git add CLAUDE.local.md.example
```

#### **Documentation Strategy**
```markdown
# Keep CLAUDE.md focused on behavior and rules
# Use ai_docs/ for detailed implementation guides
# Link between CLAUDE.md and supporting documentation
# Maintain clear separation between global and local rules
```

#### **Testing Strategy**
```python
# Test configuration changes before deploying
# Validate markdown syntax and structure
# Test agent behavior with new configurations
# Monitor performance impact of changes

def test_configuration_change():
    """Test that configuration changes work as expected."""
    # 1. Validate syntax
    # 2. Test agent initialization
    # 3. Verify behavioral changes
    # 4. Check performance impact
    pass
```

### 🔒 Security Practices

#### **Sensitive Information Handling**
```markdown
# Never put secrets in CLAUDE.md (it's version controlled)
# Use environment variables for all sensitive data
# Keep local credentials in CLAUDE.local.md only
# Regular audit of configuration files for sensitive data

## Example: Correct approach
Database URL: ${DATABASE_URL}  # From environment
API Key: ${API_KEY}           # From environment

## Example: Incorrect approach
Database URL: postgresql://user:password@localhost/db  # Hardcoded
API Key: sk_1234567890abcdef                          # Exposed
```

#### **Access Control**
```bash
# Set appropriate file permissions
chmod 600 CLAUDE.local.md     # Only owner can read/write
chmod 644 CLAUDE.md            # World-readable (safe for git)

# Verify no sensitive data in git history
git log --all --grep="password"
git log --all -S "api_key"
```

---

## 📚 Advanced Configuration

### 🎛️ Conditional Logic

#### **Environment-Based Behavior**
```markdown
## Development vs Production Behavior

### Development Environment
- Use detailed logging
- Enable debugging features
- Allow experimental agents
- Relaxed error handling

### Production Environment
- Minimal logging (performance)
- Disable debug features
- Use only stable agents
- Strict error handling
```

#### **Feature Flags**
```markdown
## Feature Flag Configuration

### Experimental Features
- ENABLE_ADVANCED_REASONING: ${ENABLE_ADVANCED_REASONING:-false}
- ENABLE_MULTI_AGENT_PARALLEL: ${ENABLE_MULTI_AGENT_PARALLEL:-false}
- ENABLE_PERFORMANCE_MONITORING: ${ENABLE_PERFORMANCE_MONITORING:-true}

### Agent Behavior Flags
- STRICT_TASK_TRACKING: ${STRICT_TASK_TRACKING:-true}
- AUTO_DOCUMENTATION: ${AUTO_DOCUMENTATION:-true}
- CONTEXT_VALIDATION: ${CONTEXT_VALIDATION:-true}
```

### 🔄 Dynamic Configuration

#### **Runtime Configuration Updates**
```python
# Support for updating configuration without restart
# Hot-reload capabilities for development
# Graceful configuration migration

def reload_configuration():
    """Reload CLAUDE.md and CLAUDE.local.md without restart."""
    # Implementation would:
    # 1. Validate new configuration
    # 2. Apply changes safely
    # 3. Update agent behaviors
    # 4. Log configuration changes
    pass
```

---

## 🚀 Future Enhancements

### 📈 Roadmap

#### **Planned Features**
- **Configuration UI**: Web interface for editing configurations
- **Template System**: Reusable configuration templates
- **Validation API**: Real-time configuration validation
- **Migration Tools**: Automated configuration updates
- **Analytics Dashboard**: Configuration usage insights

#### **Advanced Features**
- **Multi-tenant Configuration**: Different configs per organization
- **Role-based Configuration**: Different rules per user role
- **A/B Testing**: Test different configurations simultaneously
- **Machine Learning**: AI-optimized configuration suggestions

---

## 📖 References

### 🔗 Related Documentation
- [.mcp.json Configuration Guide](mcp-json-configuration-guide.md)
- [Hook System Documentation](hooks-system-guide.md)
- [Agent Library Reference](../core-architecture/agent-library-reference.md)
- [Context Management Guide](../context-system/context-management-guide.md)

### 🛠️ Tools and Utilities
- [Markdown Validator](https://remarkjs.github.io/remark-lint/)
- [Configuration Validator](../development-guides/configuration-validator.py)
- [Claude Code Documentation](https://docs.anthropic.com/claude/docs)

---

**Next Steps**: [Configure the Hook System →](hooks-system-guide.md)