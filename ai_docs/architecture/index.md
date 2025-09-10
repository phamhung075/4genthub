# Architecture Documentation Index

## Overview
This directory contains comprehensive architecture documentation for the DhafnckMCP system, focusing on proper implementation patterns, repository management, and caching strategies.

## 📚 Documentation Structure

### Core Architecture Guides

#### 1. [MCP Server Architecture Guide](MCP_SERVER_ARCHITECTURE_GUIDE.md)
**Purpose**: Complete architecture overview and implementation instructions for agents
- Request flow patterns (Controller → Facade → Use Case → Repository)
- Layer responsibilities and separation of concerns
- Repository Factory pattern implementation
- Cache Strategy with Redis on/off toggle
- Environment configuration management
- Implementation checklist and best practices

#### 2. [Agent Architecture Implementation Guide](AGENT_ARCHITECTURE_PROMPT.md) 🔥 **COMPLETE - ALL-IN-ONE**
**Purpose**: Complete consolidated guide for AI agents with everything needed
- **Executive summary** with mission statement and current violations (61 total)
- **Multi-agent workflow** with visual diagrams and step-by-step process
- **Architecture overview** with complete DDD flow diagrams
- **ACTUAL CODE FIXES** for all violations (Phases 1-4 with exact code)
  - Phase 1: Fix 11 controller files (exact before/after code)
  - Phase 2: Implement repository factory (complete working code)
  - Phase 3: Update 25 facades (specific changes needed)
  - Phase 4: Add cache invalidation (28 methods with implementation)
- **Compliance verification** with test scripts and success criteria
- **Automated tools** including compliance checker script
- **Multi-agent execution checklist** with pre/implementation/post phases
- **Implementation tracking dashboard** with current vs target metrics
- **Critical rules** and anti-patterns to avoid
- **Everything consolidated** - no need to reference multiple files

#### 3. [Repository Switching Strategy Guide](REPOSITORY_SWITCHING_GUIDE.md) ⭐ **NEW**
**Purpose**: Detailed guide on automatic repository selection based on environment
- Repository selection matrix
- Configuration examples for all scenarios
- Repository Factory implementation patterns
- Docker Compose configurations
- Testing strategies for different configurations
- Monitoring and troubleshooting guide

### Working Documents & Agent Scripts

#### 4. [Architecture Issues Report](working/workplace.md) 🚨 **CRITICAL - ACTIVE WORK**
**Purpose**: Live working document for architecture violation analysis and remediation
- Current compliance score tracking
- Active violations being fixed
- Agent task assignments and progress
- Review results and compliance updates
- Controller layer violations (direct infrastructure access)
- Repository factory pattern failures (no environment switching)
- Missing cache invalidation across all repositories

#### Agent Implementation Scripts (working/)
**Location**: `working/` subdirectory contains active agent scripts for multi-agent workflow:
- **[PLANNER_TASK_AGENT_SCRIPT.md](working/PLANNER_TASK_AGENT_SCRIPT.md)** - Task planning and assignment
- **[ANALYZE_AGENT_SCRIPT.md](working/ANALYZE_AGENT_SCRIPT.md)** - Architecture violation analysis
- **[CODE_AGENT_SCRIPT.md](working/CODE_AGENT_SCRIPT.md)** - Code implementation fixes
- **[TEST_AGENT_SCRIPT.md](working/TEST_AGENT_SCRIPT.md)** - Test creation and validation
- **[REVIEW_AGENT_SCRIPT.md](working/REVIEW_AGENT_SCRIPT.md)** - Code and test review

#### 5. [Repository Layer Architecture Analysis](REPOSITORY_LAYER_ARCHITECTURE_ANALYSIS.md)
**Purpose**: Verification that repository layer correctly implements DDD, ORM, and Redis cache
- DDD architecture compliance checklist
- ORM implementation patterns
- Redis cache integration analysis
- Security and isolation features
- Performance optimizations
- Architecture score: 95/100

### Code Analysis & Verification Guides

#### 6. [Code Flow Analysis Prompt](CODE_FLOW_ANALYSIS_PROMPT.md) ⭐ **NEW**
**Purpose**: Systematic prompt for agents to analyze code paths and verify architecture compliance
- Step-by-step analysis checklist for each code path
- Layer compliance verification
- Cache invalidation verification
- Automated analysis script
- Common flow patterns to verify
- Red flags and violation patterns

#### 7. [Visual Flow Verification Prompt](VISUAL_FLOW_VERIFICATION_PROMPT.md) ⭐ **NEW**
**Purpose**: Visual approach to verify each code path follows correct architecture
- Mermaid flow diagrams for verification
- Specific code paths to analyze
- Visual violation detection
- Verification checklist matrix
- Complete flow examples
- Automated flow verification script

## 🎯 Quick Reference

### For AI Agents Starting New Work
1. **PRIMARY REFERENCE**: [Architecture Issues Report](working/workplace.md) - **LIVE WORKING DOCUMENT**
2. **AGENT SCRIPTS**: See `working/` directory for specific agent implementation guides
3. **ALL-IN-ONE GUIDE**: [Agent Architecture Implementation Guide](AGENT_ARCHITECTURE_PROMPT.md) - **COMPLETE REFERENCE**
4. **MUST FIX FIRST**: Follow the specific tasks in working/workplace.md organized by priority
5. **Architecture flow**: Controller → Facade → Use Case → Repository Factory → Repository
6. **Never hardcode** repository implementations - always use factory

### For Understanding Repository Selection
1. Check [Repository Switching Strategy Guide](REPOSITORY_SWITCHING_GUIDE.md)
2. See the selection matrix for different environments
3. Understand factory pattern implementation
4. Configure environment variables correctly

### For Architecture Verification
1. Review [Repository Layer Architecture Analysis](REPOSITORY_LAYER_ARCHITECTURE_ANALYSIS.md)
2. Verify DDD compliance
3. Check cache invalidation implementation
4. Ensure proper layer separation

### For Analyzing Code Paths (Chemins)
1. Use [Code Flow Analysis Prompt](CODE_FLOW_ANALYSIS_PROMPT.md) for systematic analysis
2. Apply [Visual Flow Verification Prompt](VISUAL_FLOW_VERIFICATION_PROMPT.md) for visual verification
3. Run automated analysis scripts to detect violations
4. Create flow diagrams for each MCP endpoint
5. Verify each path follows: Controller → Facade → Factory → Repository

## 🔑 Key Concepts

### Repository Factory Pattern
```python
# Central decision point for repository selection
RepositoryFactory.get_task_repository()
  ├── if ENVIRONMENT=test → SQLiteRepository
  └── if ENVIRONMENT=production
      ├── if DATABASE_TYPE=supabase → SupabaseRepository
      └── if REDIS_ENABLED=true → Wrap with CachedRepository
```

### Environment Variables Control Everything
```bash
ENVIRONMENT=test|production  # Determines SQLite vs Production DB
DATABASE_TYPE=supabase|postgresql  # Production database type
REDIS_ENABLED=true|false  # Cache layer on/off
```

### Cache Invalidation Pattern
```python
# Always invalidate after data changes
def update_entity(entity):
    result = repository.update(entity)
    cache.invalidate(f"entity:{entity.id}")
    return result
```

## ⚠️ Critical Rules

### NEVER DO:
- ❌ Hardcode repository implementations
- ❌ Skip architectural layers
- ❌ Assume cache is always available
- ❌ Forget cache invalidation on updates/deletes
- ❌ Mix test and production databases

### ALWAYS DO:
- ✅ Use RepositoryFactory for all repository creation
- ✅ Follow layer hierarchy strictly
- ✅ Check cache availability before using
- ✅ Invalidate cache after data changes
- ✅ Handle cache failures gracefully

## 📊 Architecture Compliance Status (Latest Analysis: 2025-08-28 V7 - COMPLETE CODE FLOW PATH ANALYSIS)

| Component | Status | Score | Notes |
|-----------|--------|-------|-------|
| DDD Implementation | ❌ Violated | 0% | 16 controllers with direct database/repository access |
| Repository Pattern | ❌ Broken | 0% | Pattern exists but completely bypassed |
| Factory Pattern | ❌ Non-functional | 0% | **27 factory files exist but ALL BROKEN - 0 check environment variables** |
| ORM Abstraction | ✅ Complete | 95% | SQLAlchemy properly abstracted |
| Redis Cache | ❌ Not Implemented | 0% | No cache wrapping, no Redis integration |
| Cache Invalidation | ❌ Missing | 0% | 0/32 code paths have cache invalidation |
| **Overall Compliance** | **❌ CRITICAL FAILURE** | **20/100** | **90 violations (ALL HIGH SEVERITY) - SYSTEM NOT FOLLOWING DDD** |

## 🚀 Recent Updates (2025-08-28 - VERSION 7 COMPLETE CODE PATH ANALYSIS)

### Architecture Compliance Analysis - Latest Reports Available
**COMPLETE Code Flow Path (Chemin) Analysis V7** (Latest execution: 16:09:00) 🔥 **LATEST WITH SYSTEMATIC PATH TRACING**:
- **Latest V7 Report**: [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V7.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V7.md) ← **CURRENT V7**
- **V7 Compliance Report**: [compliance_reports/compliance_report_20250828_160901.md](compliance_reports/compliance_report_20250828_160901.md)
- **V7 JSON Report**: [compliance_reports/compliance_report_20250828_160901.json](compliance_reports/compliance_report_20250828_160901.json)
- **Enhanced Script V7**: `scripts/analyze_architecture_compliance_v7.py` ✅ **V7 WITH COMPLETE CODE PATH ANALYSIS**

**Previous V6 Analysis**:
- **V6 Report**: [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V6.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V6.md)
- **V6 Script**: `scripts/analyze_architecture_compliance_enhanced.py`

**Previous V4 Analysis**:
- **V4 Report**: [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V4.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V4.md)
- Previous Reports:
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V3.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V3.md)
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V2.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V2.md)
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_FINAL.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_FINAL.md)
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_AUTOMATED.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_AUTOMATED.md)
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_UPDATED.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_UPDATED.md)
  - [ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_COMPLETE.md](ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_COMPLETE.md)
- Script: `scripts/analyze_architecture_compliance.py` ✅ **EXECUTED WITH ENHANCED ANALYSIS**
- **Compliance Score: 0/100 (Grade F - Critical Failure)**
- Total Violations: 39 (6 HIGH, 33 MEDIUM)
- V4 analysis provides complete remediation plan with code templates

### Critical Findings Summary (V5 ENHANCED - WITH LINE NUMBERS)
1. **Repository Factory**: ⚠️ **7 FACTORIES EXIST but ALL BROKEN**
   - ✅ Factory files found: TaskRepositoryFactory, ProjectRepositoryFactory, GitBranchRepositoryFactory, etc.
   - ❌ ZERO environment variable checking across ALL factories
   - ❌ No DATABASE_TYPE checking (always uses ORM)
   - ❌ No REDIS_ENABLED checking (cache never wrapped)
   - ❌ No test/production switching logic
   - ❌ Facades don't properly use factories

2. **Controller Violations**: 11 controllers directly violate DDD (14 HIGH severity violations)
   - `git_branch_mcp_controller.py` - Direct repository imports (lines 491, 579, 612)
   - `task_mcp_controller.py` - Direct database access (lines 1550, 1578)
   - `context_id_detector_orm.py` - Direct database imports (lines 9-10)
   - `subtask_mcp_controller.py` - Direct database access
   - Plus 7 more controller violations with line-level detail

3. **Facade Violations**: 25 facades missing factory pattern (47 MEDIUM severity violations)
   - `task_application_facade.py` - Hardcoded `MockTaskContextRepository()` (line 82)
   - 24 other services/facades not using factory pattern
   - Missing imports of RepositoryFactory across all application layer

4. **Cache Invalidation**: 25 repository methods missing invalidation
   - 10 repository files with mutation methods lacking invalidation
   - Methods affected: create, update, delete, save across context repositories
   - Base repository classes not implementing cache invalidation mixin

### New Documentation
1. **Architecture Compliance Report**: Detailed violation analysis and fixes
2. **Agent Architecture Prompt**: Comprehensive guide for AI agents
3. **Repository Switching Guide**: Detailed environment-based selection documentation
4. **Architecture Index**: This index file for easy navigation

## 📝 Next Steps

For developers and AI agents working on this system:

1. **Always consult these guides** before implementing new features
2. **Follow the factory pattern** for repository creation
3. **Test with different configurations** (cache on/off, different databases)
4. **Monitor repository selection** using logging and health checks
5. **Update documentation** when making architectural changes

## 🔗 Related Documentation

- [Main Documentation Index](/ai_docs/index.md)
- [Vision System Documentation](/ai_docs/vision/)
- [Development Guides](/ai_docs/DEVELOPMENT GUIDES/)
- [Troubleshooting Guides](/ai_docs/troubleshooting-guides/)

---

*Last Updated: 2025-08-28 15:50*
*Architecture Version: 2.0*
*Compliance Status: 0/100 - Critical Failure (V5 Enhanced Analysis)*
*Total Violations: 61 (14 HIGH, 47 MEDIUM)*
*Cache Strategy: Redis with Optional Toggle (Not Implemented)*
*Repository Pattern: Factory-based Selection (Non-functional - 7 factories all broken)*