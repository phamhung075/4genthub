# Agent System Architecture

**Version:** 2.0 | **Updated:** 2025-10-16 | **Status:** Active | **Python:** 3.14.0 | **DDD Phase:** 8

## Executive Summary

agenthub employs multi-agent orchestration with Master Orchestrator coordinating 33 specialized agents via token-efficient delegation (95% savings), transparent MCP task management, and intelligent assignment patterns.

| Component | Description |
|-----------|-------------|
| **Master Orchestrator** | Supreme conductor coordinating workflows |
| **33 Specialized Agents** | Domain experts (dev, test, arch, security, etc.) |
| **MCP Tasks** | 95% token savings via task_id reference |
| **Context Hierarchy** | Global → Project → Branch → Task (4 tiers) |
| **Tool Enforcement** | Dynamic permissions per agent type |
| **Enterprise Model** | Accountability-focused documentation |

---

## System Overview

### Architecture Hierarchy

| Layer | Components | Purpose |
|-------|------------|---------|
| **Human Interface** | User, Claude Code CLI | User interaction entry point |
| **Master Orchestration** | Master Agent, MCP Tasks, Context System, Tool Enforcement | Coordination and delegation |
| **Specialized Agents** | 33 agents across 12 categories | Domain expertise execution |

**Agent Categories** (33 total):
- Development & Coding: 4 | Testing & QA: 3 | Architecture & Design: 4
- Project & Planning: 4 | Security & Compliance: 3 | Research & Analysis: 4
- DevOps: 1 | Documentation: 1 | Analytics & Optimization: 3
- Marketing & Branding: 3 | AI & ML: 1 | Creative & Ideation: 1

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Single Orchestrator** | One master coordinates all specialized agents |
| **Token Efficiency** | Store context once, reference by ID (95% savings) |
| **Enterprise Accountability** | All work documented in MCP tasks |
| **Tool Boundaries** | Dynamic enforcement prevents inappropriate tool access |
| **Context Inheritance** | 4-tier hierarchy (Global→Project→Branch→Task) |
| **Specialization** | 33 agents with distinct, non-overlapping responsibilities |

---

## Master Orchestrator Pattern

### Role Definition

Master Orchestrator (`master-orchestrator-agent`) = Supreme conductor | Enterprise professional employee | NOT independent AI | PART of structured organization with rules, workflows, reporting

**Critical First Action:**
```python
# FIRST COMMAND - NO EXCEPTIONS
mcp__agenthub_http__call_agent("master-orchestrator-agent")
# Returns: {agent: {system_prompt, tools, capabilities}}
# READ system_prompt | FOLLOW rules | USE ONLY listed tools | CONFIRM loaded
```

### Core Responsibilities

| Responsibility | Implementation |
|----------------|----------------|
| **Task Complexity** | Simple (<1%): handle directly \| Complex (>99%): delegate |
| **Agent Selection** | Match work type to optimal specialist via decision matrix |
| **Workflow Coordination** | Sequential (dependent tasks) \| Parallel (independent tasks) |
| **Quality Assurance** | Verify subtasks complete before parent completion |
| **Progress Monitoring** | Updates every 25% \| Blocker escalation \| Completion reports |

**Simple Tasks** (<1%): Single-line mechanical changes, no logic (fix typo, check status)
**Complex Tasks** (>99%): ANY code writing, bug fixes, features, config changes

### Workflow Pattern

```
User Request → call_agent("master-orchestrator") → Evaluate Complexity
  ↓ Simple: Handle directly → Report
  ↓ Complex: Create MCP task → Store context → Select specialist → Delegate (task_id only)
    → Monitor progress → Verify subtasks → Quality check → Complete → Report
```

### Enterprise Professional Model

**Professional Duties**: Report everything | Update regularly | Follow workflows | Communicate constantly | Maintain context | Escalate blockers

**Enterprise Rules**: No YOLO mode | No silent work | No assumptions | No shortcuts | No freelancing

---

## Agent Delegation System

### Direct Agent Calling (Recommended)

**CRITICAL**: Claude Code's `Task` tool hardcoded to route through master-orchestrator. Use `call_agent` for direct access.

```python
# ✅ CORRECT: Direct loading
mcp__agenthub_http__call_agent("debugger-agent")

# ❌ WRONG: Always routes through master orchestrator
Task(subagent_type="debugger-agent", prompt="Fix bug")
```

### Token-Efficient Delegation

**95% Token Savings Pattern:**

```python
# ❌ Traditional (token-heavy): 5,000-15,000 tokens per delegation
Task(subagent_type="agent", prompt=f"Full context: {db_schema}…{api_spec}…{security}…")

# ✅ agenthub (token-efficient): 20-30 tokens per delegation
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="uuid",
    title="Implement JWT authentication",
    assignees="coding-agent",
    details="""
    Requirements: JWT with RS256, 2hr expiry, refresh tokens
    Files with LINE NUMBERS:
      - /src/auth/jwt.py:45-67 (token generation function)
      - /src/models/user.py:23-35 (User model)
    Dependencies: Complete database schema first
    Acceptance: All auth tests pass
    """  # Stored ONCE
)
mcp__agenthub_http__call_agent("coding-agent")  # Retrieves via task_id
```

| Approach | Tokens | Efficiency Gain |
|----------|--------|-----------------|
| Traditional full context | 5,000-15,000 | Baseline |
| agenthub task_id reference | 20-30 | **95% savings** |
| Context inheritance | 100-500 | 90% savings |

---

## Sub-Agent Instructions

### Role Definition

When loaded via `call_agent("agent-name")`, you ARE that agent with specialized capabilities.

**✅ DO**: Focus on specialized work | Use loaded capabilities | Complete assigned task | Update MCP progress | Report completion with summary

**❌ DON'T**: Call master-orchestrator | Delegate to others | Use Task tool | Follow orchestrator instructions | Confuse role

### Workflow

```
call_agent loads you → Read task context (task_id) → Retrieve from MCP → Use specialized tools
  → Update progress (every 25%) → Complete work → Report completion
```

### Task Context Retrieval

```python
# Receive: task_id
# Retrieve complete context with 4-tier inheritance
context = mcp__agenthub_http__manage_task(
    action="get",
    task_id=task_id,
    include_context=True  # Gets Global→Project→Branch→Task
)
# Now have: task details, branch config, project settings, global preferences
```

### Available Tools by Type

| Agent Type | Tools |
|------------|-------|
| **All Agents** | Read, Write, Edit, Bash, Grep, Glob, manage_task, manage_subtask |
| **Master Orchestrator** | +Task, +call_agent, +manage_context, +TodoWrite (NO Write/Edit/Bash) |
| **Coding Agents** | Full file ops (NO Task delegation) |
| **Documentation** | +WebFetch (NO Bash) |

### Completion Protocol

```python
# 1. Complete ALL subtasks first
subtasks = mcp__agenthub_http__manage_subtask(action="list", task_id=task_id)
for st in subtasks:
    if st.status != "done":
        mcp__agenthub_http__manage_subtask(action="complete", task_id=task_id, subtask_id=st.id, ...)

# 2. Complete main task
mcp__agenthub_http__manage_task(
    action="complete",
    task_id=task_id,
    completion_summary="Detailed accomplishments",
    testing_notes="Tests performed and results",
    insights_found="Important discoveries"
)
```

---

## 33 Specialized Agents

### Complete Agent Directory

| # | Agent | Specialization | Use When | Decision Criteria |
|---|-------|----------------|----------|-------------------|
| **Development & Coding (4)** |
| 1 | `coding-agent` | Implementation, features | New features, code improvements | `implement\|code\|build\|develop\|create` |
| 2 | `debugger-agent` | Bug fixing, troubleshooting | Bug investigation, error resolution | `debug\|fix\|error\|bug\|troubleshoot` |
| 3 | `code-reviewer-agent` | Code quality, review | Quality gates, PR reviews, security | Post-implementation verification |
| 4 | `prototyping-agent` | Rapid prototyping, POCs | Proof of concepts, spikes | `prototype\|poc\|proof of concept` |
| **Testing & QA (3)** |
| 5 | `test-orchestrator-agent` | Comprehensive testing | Test planning, automation, QA | `test\|verify\|validate\|qa` |
| 6 | `uat-coordinator-agent` | User acceptance testing | UAT planning, story validation | `uat\|acceptance testing\|user testing` |
| 7 | `performance-load-tester-agent` | Performance, load testing | Performance optimization, bottlenecks | `performance\|load\|stress\|benchmark` |
| **Architecture & Design (4)** |
| 8 | `system-architect-agent` | System design, architecture | Architecture planning, tech decisions | `architecture\|system\|design patterns` |
| 9 | `design-system-agent` | Design systems, UI patterns | Component libraries, UI standardization | `design system\|component library\|ui patterns` |
| 10 | `shadcn-ui-expert-agent` | UI/UX, frontend | UI development, UX improvements | `design\|ui\|interface\|ux\|frontend` |
| 11 | `core-concept-agent` | Core concepts, fundamentals | Foundational architecture, principles | `core concept\|fundamental\|foundation` |
| **DevOps & Infrastructure (1)** |
| 12 | `devops-agent` | CI/CD, infrastructure | Deployment automation, infrastructure | `deploy\|infrastructure\|devops\|ci/cd` |
| **Documentation (1)** |
| 13 | `documentation-agent` | Technical documentation | API docs, guides, specifications | `document\|guide\|manual\|readme` |
| **Project & Planning (4)** |
| 14 | `project-initiator-agent` | Project setup, kickoff | New project setup, team onboarding | `project\|initiative\|kickoff` |
| 15 | `task-planning-agent` | Task breakdown, planning | Project planning, workflow design | `plan\|analyze\|breakdown\|organize` |
| 16 | `master-orchestrator-agent` | Complex workflow orchestration | Multi-agent coordination, workflows | `orchestrate\|coordinate\|multi-step\|complex` |
| 17 | `elicitation-agent` | Requirements gathering | Stakeholder communication, scope | `elicit\|requirements\|gathering` |
| **Security & Compliance (3)** |
| 18 | `security-auditor-agent` | Security audits, reviews | Security assessment, vulnerabilities | `security\|audit\|vulnerability\|penetration` |
| 19 | `compliance-scope-agent` | Regulatory compliance | Compliance analysis, audit prep | `compliance\|regulatory\|legal` |
| 20 | `ethical-review-agent` | Ethical considerations | Ethical review, bias analysis | `ethics\|ethical\|responsible` |
| **Analytics & Optimization (3)** |
| 21 | `analytics-setup-agent` | Analytics, tracking | Analytics setup, data collection | `analytics\|tracking\|metrics` |
| 22 | `efficiency-optimization-agent` | Process optimization | Process analysis, efficiency | `efficiency\|optimize\|process` |
| 23 | `health-monitor-agent` | System health monitoring | System monitoring, health checks | `health\|monitor\|monitoring\|status` |
| **Marketing & Branding (3)** |
| 24 | `marketing-strategy-orchestrator-agent` | Marketing strategy | Marketing planning, campaigns | `marketing\|campaign\|growth\|seo` |
| 25 | `community-strategy-agent` | Community building | Community management, engagement | `community\|social\|engagement` |
| 26 | `branding-agent` | Brand identity | Brand development, identity | `brand\|branding\|identity` |
| **Research & Analysis (4)** |
| 27 | `deep-research-agent` | In-depth research | Market research, competitive analysis | `research\|investigate\|explore\|study` |
| 28 | `llm-ai-agents-research` | AI/ML research | AI research, ML strategy | AI/ML focused research |
| 29 | `root-cause-analysis-agent` | Problem analysis | Incident analysis, troubleshooting | `incident\|postmortem\|root cause` |
| 30 | `technology-advisor-agent` | Technology recommendations | Technology selection, stack evaluation | `technology\|tech stack\|framework` |
| **AI & Machine Learning (1)** |
| 31 | `ml-specialist-agent` | Machine learning | ML models, data science, AI features | `ml\|machine learning\|ai\|neural` |
| **Creative & Ideation (1)** |
| 32 | `creative-ideation-agent` | Creative idea generation | Brainstorming, innovative solutions | `creative\|idea\|ideation\|brainstorm` |

**Agent Files**: All agents in `.claude/agents/{agent-name}/` (system.md, tools.yml)

---

## Dynamic Tool Enforcement

### Overview

**v2.0 Evolution**: Tools NO LONGER static configs. Dynamic enforcement based on `call_agent` response.

**SOURCE OF TRUTH**: Only `tools` array returned by `call_agent` determines permissions.

```
Generic Claude → call_agent("agent") → Response: {tools: ["Read", "Edit", "Bash"]}
  → Dynamic Enforcement: ONLY these tools available → All others BLOCKED
```

### Agent-Specific Permissions

| Agent Type | Can Use | Cannot Use |
|------------|---------|------------|
| **Master Orchestrator** | Task, Read, manage_task, manage_subtask, call_agent, manage_context, TodoWrite | Write, Edit, Bash (coordination only) |
| **Coding Agent** | Read, Write, Edit, Bash, Grep, Glob | Task (no delegation) |
| **Documentation Agent** | Read, Write, Edit, Grep, WebFetch | Bash, Task |

### Enforcement Examples

**Scenario 1**: Master orchestrator tries Edit → BLOCKED ❌ | Error: "Edit not available for master-orchestrator" | Solution: Delegate to coding-agent

**Scenario 2**: Coding agent tries Task → BLOCKED ❌ | Error: "Task not available for coding-agent" | Solution: Coding agents implement only, cannot delegate

**Scenario 3**: Documentation agent tries Bash → BLOCKED ❌ | Error: "Bash not available for documentation-agent" | Solution: Documentation agents cannot run system commands

### Benefits

Clear boundaries | Security (prevents inappropriate tool access) | Workflow integrity | Error prevention | Role clarity

---

## Task Management Integration

### MCP Task System

**MCP** = Enterprise communication and accountability system

**Capabilities**: Permanent work record | Manager visibility | Audit trail | Status tracking | Knowledge retention

### Task Hierarchy

```
Project → Git Branch → Task → Subtask (granular breakdown)
```

### Task Creation Pattern

```python
# MANDATORY for complex work (>99% of cases)

# Step 1: Check existing (prevent duplicates!)
existing = mcp__agenthub_http__manage_task(action="list", git_branch_id="uuid")
for task in existing:
    if "authentication" in task.title.lower():
        task_id = task.id  # Use existing
        break
else:
    # Step 2: Create ONLY if none exists
    task = mcp__agenthub_http__manage_task(
        action="create",
        git_branch_id="uuid",
        title="Implement JWT authentication",  # Clear, specific
        assignees="coding-agent",  # At least one required
        details="""
        Requirements: JWT with RS256, 2hr expiry, refresh tokens
        Files with LINE NUMBERS:
          - /src/auth/jwt.py:45-67 (token generation)
          - /src/models/user.py:23-35 (User model)
          - /tests/auth/test_jwt.py:12-25 (add JWT tests)
        Dependencies: Complete database schema first
        Acceptance: All auth tests pass, tokens expire correctly
        """,
        priority="high",
        estimated_effort="3 days"
    )
    task_id = task["task"]["id"]

# Step 3: Delegate with task_id only (95% token savings!)
mcp__agenthub_http__call_agent("coding-agent")
```

### Critical: Line Numbers

**WHY**: Sub-agents go directly to locations | No searching | Clear instructions | Professional standard

**Formats**: `/file.js:23` (single) | `/file.js:23-35` (range) | `/file.js:23-35,45-52` (multiple) | `/file.js:23-35 (functionName)` (with context)

❌ **VAGUE**: "Update user validation logic" (agent must search)
✅ **PRECISE**: "Update user validation in src/models/User.js:23-35 (validateEmail method), focus lines 28-30 for email regex"

### Subtask Management

```python
# Parent task created
parent_id = "..."

# Break down for transparency
subtask = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_id,
    title="Design database schema",
    description="Create user table with auth fields",
    assignees="system-architect-agent"  # Inherits from parent if not specified
)

# Update progress
mcp__agenthub_http__manage_subtask(
    action="update",
    task_id=parent_id,
    subtask_id=subtask.id,
    progress_percentage=50,
    progress_notes="Schema designed, creating migrations"
)

# Complete with insights
mcp__agenthub_http__manage_subtask(
    action="complete",
    task_id=parent_id,
    subtask_id=subtask.id,
    completion_summary="Database schema created with proper indexes",
    insights_found="Used compound index on (email, status) for faster queries"
)
```

### Progress Reporting

**Frequency**: Initial (in_progress) | Every 25% | Blockers (immediate) | Completion (detailed)

```python
# Every 25%
mcp__agenthub_http__manage_task(
    action="update",
    task_id=task_id,
    progress_percentage=50,
    details="Completed JWT generation, working on refresh tokens",
    insights_found="Discovered existing utility for token signing"
)
```

### Completion Protocol

```python
# MANDATORY: Verify ALL subtasks complete BEFORE parent
subtasks = mcp__agenthub_http__manage_subtask(action="list", task_id=parent_id)
incomplete = [st for st in subtasks if st.status != "done"]

if incomplete:
    # ❌ CANNOT complete parent - subtasks pending
    print(f"Must complete {len(incomplete)} subtasks first")
else:
    # ✅ All done - complete parent
    mcp__agenthub_http__manage_task(
        action="complete",
        task_id=parent_id,
        completion_summary="""
        JWT authentication fully implemented:
        - RS256 with 2-hour expiry
        - Refresh tokens (7-day expiry)
        - httpOnly cookie storage
        - Database migrations
        - Complete test coverage
        """,
        testing_notes="""
        - Unit tests: 47 tests passing
        - Integration: Login/logout flows validated
        - Security: Token expiry verified
        - Performance: <100ms token generation
        """,
        insights_found="""
        - Used Redis for refresh token storage (faster)
        - Implemented token blacklist for logout
        - Added rate limiting on refresh endpoint
        """
    )
```

### TodoWrite vs MCP Tasks

| Feature | TodoWrite | MCP Tasks |
|---------|-----------|-----------|
| **Purpose** | Track parallel coordination ONLY | Store work context permanently |
| **When** | Planning simultaneous agent calls | ALWAYS for complex work before delegation |
| **Stores** | Agent assignment planning | Full implementation details, files, requirements |
| **Persistence** | Session only | Survives sessions |

```python
# ✅ TodoWrite: Planning parallel work
TodoWrite(todos=[
    {"content": "Delegate auth to coding-agent", "status": "pending", ...},
    {"content": "Delegate UI to shadcn-ui-expert-agent", "status": "pending", ...}
])

# ✅ MCP Task: Actual work context
task = mcp__agenthub_http__manage_task(
    action="create",
    title="Implement JWT authentication",
    assignees="coding-agent",
    details="Complete context, files with line numbers, requirements..."
)
```

---

## Best Practices

### Master Orchestrator

**Session Startup**:
1. ALWAYS: `mcp__agenthub_http__call_agent("master-orchestrator-agent")`
2. Confirm: "Master orchestrator capabilities loaded successfully"
3. Check tools array in response

**Task Creation**:
1. Check existing tasks FIRST
2. Create ONLY if doesn't exist
3. Include LINE NUMBERS in file references
4. Store complete context
5. Assign at least one agent

**Delegation**:
1. Create MCP task with full context
2. Delegate with task_id ONLY (95% token savings)
3. Monitor progress through MCP updates
4. Verify ALL subtasks before completing parent

### Sub-Agents

**Session**: Already loaded via call_agent | Don't call master-orchestrator | Focus on specialized work

**Execution**:
1. Retrieve context from task_id: `mcp__agenthub_http__manage_task(action="get", task_id=task_id, include_context=True)`
2. Use specialized tools
3. Update progress every 25%
4. Report blockers immediately
5. Complete with detailed summary

**Completion**:
1. Complete all YOUR subtasks first
2. Update parent with completion
3. Include insights learned
4. Document testing performed

### Environment

| Component | Details |
|-----------|---------|
| **Python** | 3.14.0 (scripts/install-python-3.14.sh) |
| **Architecture** | DDD Phase 8 (strict layer separation) |
| **Database** | PostgreSQL (dev), isolated test DB, SQLAlchemy ORM |
| **Backend** | agenthub_main/src/ |
| **Frontend** | agenthub-frontend/ |
| **Tests** | agenthub_main/src/tests/ |
| **Agents** | .claude/agents/ |
| **Docs** | ai_docs/ |

### Code Quality

**Clean Code Principles** (CLAUDE.md:9-47):
- ❌ NO backward compatibility - break cleanly
- ❌ NO legacy code - remove immediately
- ❌ NO fallback mechanisms - one way only
- ❌ NO migration helpers - clean breaks allowed in dev
- ✅ Clean code - eliminate duplication
- ✅ DRY - reuse code
- ✅ SOLID - follow all 5 principles
- ✅ Single source of truth - define entities once

**Test Fixing Hierarchy**: Prompt Input → ORM Model → Database → Tests → Code

---

## Troubleshooting

### Common Issues

| Issue | Problem | Solution |
|-------|---------|----------|
| **Task tool routing** | `Task(subagent_type="debugger")` always calls master-orchestrator | Use `mcp__agenthub_http__call_agent("debugger-agent")` directly |
| **Unavailable tools** | Master orchestrator tries `Edit("file")` → Error | Check tools array from call_agent | Delegate to agent with Edit (coding-agent) |
| **Cannot complete parent** | "Cannot complete task - subtasks pending" | List subtasks | Complete all with status != "done" | Then complete parent |
| **Duplicate tasks** | Multiple tasks for same work | ALWAYS check existing first: `manage_task(action="list")` | Search for similar | Reuse if found |
| **Role confusion** | Sub-agent tries delegating | Sub-agents DON'T delegate | Focus on specialized work only |

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Edit tool not available for master-orchestrator-agent" | Master trying file edits | Delegate to coding-agent |
| "Task tool not available for coding-agent" | Coding agent trying delegation | Coding agents implement only, cannot delegate |
| "Cannot complete task - subtasks pending" | Parent completion before subtasks | Complete all subtasks first |
| "No agent loaded - call call_agent first" | Work without loading capabilities | Call `mcp__agenthub_http__call_agent` first |

### Documentation References

- System Architecture: `/ai_docs/core-architecture/system-architecture-overview.md`
- DDD Layers: `/ai_docs/core-architecture/domain-driven-design-layers.md`
- Context System: `/ai_docs/core-architecture/context-hierarchy-system.md`
- CLAUDE.md: Project root (complete AI agent instructions)
- MCP Tools: See tool descriptions in tools array

---

**Related**: [System Architecture Overview](/ai_docs/core-architecture/system-architecture-overview.md) | [Domain-Driven Design Layers](/ai_docs/core-architecture/domain-driven-design-layers.md) | [Context Hierarchy System](/ai_docs/core-architecture/context-hierarchy-system.md) | [Design Patterns](/ai_docs/core-architecture/design-patterns-in-architecture.md) | [Python 3.14.0 Guide](/ai_docs/operations/python-3.14-installation-guide.md)

**Updated:** 2025-10-16 | **Owner:** agenthub Architecture Team | **Review:** Monthly | **Status:** Living Document | **Version:** 2.0
