# 3-Phase Professional Development Workflow

**Date**: 2025-10-31
**Purpose**: Demonstrates the optimal workflow for complex feature development using MCP tasks and specialized agents
**Pattern**: Plan → Execute → Review

---

## Overview

This workflow pattern maximizes efficiency by:
1. **Phase 1**: Creating complete work structure upfront (tasks + subtasks + assignments)
2. **Phase 2**: Parallel execution by specialized agents
3. **Phase 3**: Quality assurance through code review

**Benefits**:
- Clear visibility into all work before execution starts
- Parallel agent execution for faster completion
- Quality gates catch issues before deployment
- Complete audit trail for compliance

---

## Phase 1: Create All Tasks, Split to Subtasks, and Assign to Agents

### Step 1.1: Create Parent Task with Complete Context

```python
# Create high-level feature task
parent_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Build complete JWT authentication system",
    description="End-to-end authentication with JWT tokens, secure password handling, middleware, testing, and documentation",
    assignees="master-orchestrator-agent",  # Orchestrator owns parent
    priority="critical",
    details="""
    COMPLETE REQUIREMENTS:
    - JWT token generation and validation (RS256 signing algorithm)
    - Secure password hashing with bcrypt (12+ salt rounds)
    - Authentication middleware for route protection
    - REST endpoints: /auth/login, /auth/register, /auth/refresh, /auth/logout
    - Security audit for OWASP Top 10 compliance
    - Comprehensive test suite (unit, integration, e2e) - 95%+ coverage
    - API documentation with request/response examples

    ACCEPTANCE CRITERIA:
    - All endpoints functional and tested
    - Security audit passed with no critical issues
    - Documentation complete with integration guide
    - Code reviewed and approved
    """
)

# Capture parent task ID
parent_task_id = parent_task["task"]["id"]
print(f"✅ Parent task created: {parent_task_id}")
```

### Step 1.2: Create Specialized Subtasks with Agent Assignments

```python
# SUBTASK 1: JWT Service (Backend Development)
subtask_jwt = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Implement JWT token generation service",
    description="""
    Create JWT service with complete token lifecycle management.

    FILES TO CREATE:
    - src/services/jwt.service.js (or .py for Python backend)

    REQUIREMENTS:
    - Token generation with RS256 signing
    - 1-hour access token expiry
    - 7-day refresh token expiry
    - Token validation and verification
    - Token refresh mechanism
    - Proper error handling

    DEPENDENCIES: None (can start immediately)
    """,
    assignees="coding-agent",
    priority="critical"
)

# SUBTASK 2: Password Security (Security Implementation)
subtask_password = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Implement password hashing and validation service",
    description="""
    Create secure password handling with industry best practices.

    FILES TO CREATE:
    - src/services/password.service.js (or .py)

    REQUIREMENTS:
    - Bcrypt hashing with 12+ salt rounds
    - Password strength validation (min 8 chars, special chars, numbers, uppercase)
    - Secure comparison to prevent timing attacks
    - Password history tracking (prevent reuse)

    DEPENDENCIES: None (can start immediately)
    """,
    assignees="security-auditor-agent",
    priority="critical"
)

# SUBTASK 3: Authentication Middleware (Backend Development)
subtask_middleware = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Build authentication middleware",
    description="""
    Create middleware to protect routes with JWT validation.

    FILES TO CREATE:
    - src/middleware/auth.middleware.js (or .py)

    REQUIREMENTS:
    - Extract JWT from Authorization header
    - Validate token signature and expiry
    - Inject user context into request object
    - Handle refresh token flow
    - Proper error responses (401, 403)

    DEPENDENCIES: Requires subtask_jwt completion (JWT service must exist)
    """,
    assignees="coding-agent",
    priority="high"
)

# SUBTASK 4: REST Endpoints (API Development)
subtask_endpoints = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Create login, register, refresh, and logout endpoints",
    description="""
    Implement complete authentication REST API.

    FILES TO CREATE:
    - src/routes/auth.routes.js (or .py)
    - src/controllers/auth.controller.js (or .py)

    ENDPOINTS:
    - POST /auth/register (email, username, password)
    - POST /auth/login (email/username, password)
    - POST /auth/refresh (refresh_token)
    - POST /auth/logout (invalidate refresh token)

    REQUIREMENTS:
    - Request validation (email format, password strength)
    - Proper HTTP status codes
    - Standardized error responses
    - Rate limiting consideration

    DEPENDENCIES: Requires subtask_jwt and subtask_password completion
    """,
    assignees="coding-agent",
    priority="high"
)

# SUBTASK 5: Security Audit (Security Review)
subtask_audit = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Conduct OWASP security audit",
    description="""
    Comprehensive security review against OWASP Top 10.

    AUDIT CHECKLIST:
    - SQL Injection protection (parameterized queries)
    - XSS prevention (input sanitization)
    - CSRF protection (token validation)
    - Authentication bypass attempts
    - Session fixation vulnerabilities
    - Brute force protection (rate limiting)
    - Secure token storage (httpOnly cookies)
    - Password policy enforcement
    - Error message information disclosure
    - Security headers (HSTS, CSP, X-Frame-Options)

    DELIVERABLE: Security audit report with findings and remediation steps

    DEPENDENCIES: Requires all implementation subtasks complete
    """,
    assignees="security-auditor-agent",
    priority="critical"
)

# SUBTASK 6: Comprehensive Testing (QA)
subtask_tests = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Create comprehensive test suite",
    description="""
    Write unit, integration, and e2e tests for complete coverage.

    FILES TO CREATE:
    - tests/unit/jwt.service.test.js
    - tests/unit/password.service.test.js
    - tests/integration/auth.routes.test.js
    - tests/e2e/auth.flow.test.js

    TEST COVERAGE:
    - Unit tests for JWT service (token generation, validation, refresh)
    - Unit tests for password service (hashing, comparison, validation)
    - Integration tests for all endpoints (success and error cases)
    - E2E tests for complete user journeys
    - Edge cases: expired tokens, invalid credentials, concurrent requests

    TARGET: 95%+ code coverage

    DEPENDENCIES: Requires all implementation subtasks complete
    """,
    assignees="test-orchestrator-agent",
    priority="high"
)

# SUBTASK 7: API Documentation (Documentation)
subtask_docs = mcp__agenthub_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Write authentication API documentation",
    description="""
    Create comprehensive API documentation for frontend integration.

    FILES TO CREATE:
    - docs/api/authentication.md
    - docs/guides/authentication-integration.md

    DOCUMENTATION SECTIONS:
    - Authentication flow diagram
    - Endpoint specifications (request/response with examples)
    - Error codes and handling
    - Token management best practices
    - Integration guide for frontend developers
    - Code examples (JavaScript, Python, cURL)

    DEPENDENCIES: Requires all implementation subtasks complete
    """,
    assignees="documentation-agent",
    priority="medium"
)

print("✅ Phase 1 Complete: 7 subtasks created with specialized agent assignments")
print(f"""
SUBTASK SUMMARY:
1. JWT Service → coding-agent (CRITICAL) - No dependencies
2. Password Service → security-auditor-agent (CRITICAL) - No dependencies
3. Auth Middleware → coding-agent (HIGH) - Depends on #1
4. REST Endpoints → coding-agent (HIGH) - Depends on #1, #2
5. Security Audit → security-auditor-agent (CRITICAL) - Depends on #1-4
6. Test Suite → test-orchestrator-agent (HIGH) - Depends on #1-4
7. API Docs → documentation-agent (MEDIUM) - Depends on #1-4

PARALLEL EXECUTION POSSIBLE:
- Wave 1: #1 (JWT) and #2 (Password) can run in parallel
- Wave 2: #3 (Middleware) and #4 (Endpoints) can run in parallel after Wave 1
- Wave 3: #5 (Audit), #6 (Tests), #7 (Docs) can run in parallel after Wave 2
""")
```

---

## Phase 2: Call Agents to Execute All Tasks

### Step 2.1: Execute Wave 1 (No Dependencies - Parallel Execution)

```python
# Wave 1: JWT Service and Password Service (parallel)
from TodoWrite import TodoWrite

TodoWrite(todos=[
    {"content": "Execute JWT service implementation", "status": "in_progress", "activeForm": "Executing JWT service implementation"},
    {"content": "Execute password service implementation", "status": "in_progress", "activeForm": "Executing password service implementation"},
    {"content": "Execute middleware implementation", "status": "pending", "activeForm": "Executing middleware implementation"},
    {"content": "Execute REST endpoints implementation", "status": "pending", "activeForm": "Executing REST endpoints implementation"},
    {"content": "Execute security audit", "status": "pending", "activeForm": "Executing security audit"},
    {"content": "Execute test suite creation", "status": "pending", "activeForm": "Executing test suite creation"},
    {"content": "Execute API documentation", "status": "pending", "activeForm": "Executing API documentation"}
])

# Delegate JWT service to coding-agent
Task(
    subagent_type="coding-agent",
    prompt=f"task_id: {subtask_jwt['subtask']['id']}"
)

# Delegate password service to security-auditor-agent (parallel)
Task(
    subagent_type="security-auditor-agent",
    prompt=f"task_id: {subtask_password['subtask']['id']}"
)

# Wait for both agents to complete...
# Result: JWT service and password service both implemented
```

### Step 2.2: Execute Wave 2 (Depends on Wave 1 - Parallel Execution)

```python
# Update TodoWrite
TodoWrite(todos=[
    {"content": "Execute JWT service implementation", "status": "completed", "activeForm": "Executing JWT service implementation"},
    {"content": "Execute password service implementation", "status": "completed", "activeForm": "Executing password service implementation"},
    {"content": "Execute middleware implementation", "status": "in_progress", "activeForm": "Executing middleware implementation"},
    {"content": "Execute REST endpoints implementation", "status": "in_progress", "activeForm": "Executing REST endpoints implementation"},
    {"content": "Execute security audit", "status": "pending", "activeForm": "Executing security audit"},
    {"content": "Execute test suite creation", "status": "pending", "activeForm": "Executing test suite creation"},
    {"content": "Execute API documentation", "status": "pending", "activeForm": "Executing API documentation"}
])

# Wave 2: Middleware and Endpoints (parallel, both need Wave 1 complete)
Task(
    subagent_type="coding-agent",
    prompt=f"task_id: {subtask_middleware['subtask']['id']}"
)

Task(
    subagent_type="coding-agent",
    prompt=f"task_id: {subtask_endpoints['subtask']['id']}"
)

# Wait for both agents to complete...
# Result: Middleware and endpoints both implemented
```

### Step 2.3: Execute Wave 3 (Final Phase - Parallel Execution)

```python
# Update TodoWrite
TodoWrite(todos=[
    {"content": "Execute JWT service implementation", "status": "completed", "activeForm": "Executing JWT service implementation"},
    {"content": "Execute password service implementation", "status": "completed", "activeForm": "Executing password service implementation"},
    {"content": "Execute middleware implementation", "status": "completed", "activeForm": "Executing middleware implementation"},
    {"content": "Execute REST endpoints implementation", "status": "completed", "activeForm": "Executing REST endpoints implementation"},
    {"content": "Execute security audit", "status": "in_progress", "activeForm": "Executing security audit"},
    {"content": "Execute test suite creation", "status": "in_progress", "activeForm": "Executing test suite creation"},
    {"content": "Execute API documentation", "status": "in_progress", "activeForm": "Executing API documentation"}
])

# Wave 3: Security audit, tests, and docs (all parallel)
Task(
    subagent_type="security-auditor-agent",
    prompt=f"task_id: {subtask_audit['subtask']['id']}"
)

Task(
    subagent_type="test-orchestrator-agent",
    prompt=f"task_id: {subtask_tests['subtask']['id']}"
)

Task(
    subagent_type="documentation-agent",
    prompt=f"task_id: {subtask_docs['subtask']['id']}"
)

# Wait for all three agents to complete...
# Result: Security audit report, test suite with 95%+ coverage, complete API documentation

print("✅ Phase 2 Complete: All 7 subtasks executed by specialized agents")
```

---

## Phase 3: Call Code Review Agent to Review All Changes

### Step 3.1: Create Code Review Task

```python
# Update TodoWrite for Phase 3
TodoWrite(todos=[
    {"content": "All subtasks completed - starting code review", "status": "in_progress", "activeForm": "Starting code review"},
    {"content": "Review implementation quality", "status": "pending", "activeForm": "Reviewing implementation quality"},
    {"content": "Verify security findings addressed", "status": "pending", "activeForm": "Verifying security findings addressed"},
    {"content": "Confirm test coverage meets standards", "status": "pending", "activeForm": "Confirming test coverage meets standards"},
    {"content": "Finalize and mark parent task complete", "status": "pending", "activeForm": "Finalizing and marking parent task complete"}
])

# Create comprehensive code review task
review_task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Code review: JWT authentication system",
    description="Comprehensive code review of complete authentication implementation",
    assignees="code-reviewer-agent",
    priority="critical",
    details=f"""
    REVIEW SCOPE: Parent task {parent_task_id} and all 7 subtasks

    CODE REVIEW CHECKLIST:

    1. CODE QUALITY:
       - Clean code principles (DRY, SOLID)
       - Proper error handling
       - Consistent code style
       - Meaningful variable/function names
       - Adequate comments for complex logic

    2. ARCHITECTURE:
       - Separation of concerns
       - Proper service layer abstraction
       - Middleware implementation patterns
       - Route organization

    3. SECURITY:
       - Verify security audit findings addressed
       - Check for hardcoded secrets
       - Validate input sanitization
       - Confirm secure token storage
       - Review error messages (no information disclosure)

    4. TESTING:
       - Verify 95%+ code coverage achieved
       - Check edge case handling
       - Validate test quality (not just coverage)
       - Confirm integration tests comprehensive

    5. DOCUMENTATION:
       - API docs complete and accurate
       - Code comments adequate
       - Integration guide clear
       - Error handling documented

    6. PERFORMANCE:
       - Check for N+1 queries
       - Validate caching strategy
       - Review database indexes
       - Assess scalability considerations

    FILES TO REVIEW:
    - All files created in subtasks #1-4
    - Test files from subtask #6
    - Documentation from subtask #7
    - Security audit report from subtask #5

    DELIVERABLE: Comprehensive code review report with:
    - Approval status (Approved / Needs Changes)
    - Issues found (Critical, High, Medium, Low)
    - Recommendations for improvement
    - Sign-off for deployment
    """
)

review_task_id = review_task["task"]["id"]
print(f"✅ Code review task created: {review_task_id}")
```

### Step 3.2: Execute Code Review

```python
# Delegate to code-reviewer-agent
Task(
    subagent_type="code-reviewer-agent",
    prompt=f"task_id: {review_task_id}"
)

# Wait for code review to complete...
# Expected result: Code review report with findings
```

### Step 3.3: Handle Code Review Results

```python
# SCENARIO A: Code Review Approved (Happy Path)
if review_approved:
    # Mark all subtasks as complete
    for subtask_id in [subtask_jwt, subtask_password, subtask_middleware,
                       subtask_endpoints, subtask_audit, subtask_tests, subtask_docs]:
        mcp__agenthub_http__manage_subtask(
            action="complete",
            task_id=parent_task_id,
            subtask_id=subtask_id["subtask"]["id"],
            completion_summary="Implementation complete and code review approved"
        )

    # Mark parent task as complete
    mcp__agenthub_http__manage_task(
        action="complete",
        task_id=parent_task_id,
        completion_summary="""
        JWT authentication system fully implemented and approved:
        - JWT token generation and validation ✓
        - Secure password hashing with bcrypt ✓
        - Authentication middleware for route protection ✓
        - Complete REST API (login, register, refresh, logout) ✓
        - Security audit passed with no critical issues ✓
        - Test suite with 97% coverage ✓
        - Comprehensive API documentation ✓
        - Code review approved for deployment ✓
        """,
        testing_notes="All unit tests, integration tests, and e2e tests passing. Security audit completed with no critical or high issues found.",
        insights_found="""
        - RS256 signing provides better security than HS256 for JWT
        - Bcrypt with 12 salt rounds provides optimal security/performance balance
        - HttpOnly cookies prevent XSS token theft
        - Refresh token rotation prevents token replay attacks
        """
    )

    TodoWrite(todos=[
        {"content": "All subtasks completed - starting code review", "status": "completed", "activeForm": "Starting code review"},
        {"content": "Review implementation quality", "status": "completed", "activeForm": "Reviewing implementation quality"},
        {"content": "Verify security findings addressed", "status": "completed", "activeForm": "Verifying security findings addressed"},
        {"content": "Confirm test coverage meets standards", "status": "completed", "activeForm": "Confirming test coverage meets standards"},
        {"content": "Finalize and mark parent task complete", "status": "completed", "activeForm": "Finalizing and marking parent task complete"}
    ])

    print("✅ Phase 3 Complete: Code review approved, all tasks marked complete")
    print("🎉 WORKFLOW COMPLETE: Authentication system ready for deployment")

# SCENARIO B: Code Review Needs Changes
else:
    # Create fix tasks for identified issues
    for issue in code_review_issues:
        fix_task = mcp__agenthub_http__manage_subtask(
            action="create",
            task_id=parent_task_id,
            title=f"Fix: {issue.title}",
            description=issue.description,
            assignees=issue.assigned_agent,
            priority=issue.priority
        )

        # Delegate fix to appropriate agent
        Task(
            subagent_type=issue.assigned_agent,
            prompt=f"task_id: {fix_task['subtask']['id']}"
        )

    print(f"⚠️ Code review found {len(code_review_issues)} issues - created fix tasks")
    print("🔄 Rerunning Phase 2 for fix tasks, then Phase 3 for re-review")
```

---

## Workflow Summary

### Execution Timeline

```
Phase 1: Planning (5-10 minutes)
├─ Create parent task
└─ Create 7 specialized subtasks with dependencies

Phase 2: Parallel Execution (30-60 minutes)
├─ Wave 1: JWT + Password (parallel) → 15 min
├─ Wave 2: Middleware + Endpoints (parallel) → 20 min
└─ Wave 3: Audit + Tests + Docs (parallel) → 25 min

Phase 3: Quality Review (10-20 minutes)
├─ Create review task
├─ Execute code review
└─ Handle results (approve or create fix tasks)

Total: ~45-90 minutes (vs 2-3 hours sequential)
```

### Success Metrics

✅ **Phase 1 Success Indicators:**
- All subtasks have clear requirements
- Agent assignments match expertise
- Dependencies properly identified
- Parallel execution opportunities identified

✅ **Phase 2 Success Indicators:**
- All subtasks completed without blockers
- Implementation meets acceptance criteria
- Tests passing with target coverage
- Security audit completed

✅ **Phase 3 Success Indicators:**
- Code review approved or issues clearly identified
- All critical/high issues addressed
- Parent task marked complete with summary
- Feature ready for deployment

### Key Advantages

1. **Visibility**: Complete work structure visible before execution starts
2. **Efficiency**: Parallel execution reduces total time by 40-60%
3. **Quality**: Built-in security audit and code review gates
4. **Accountability**: Clear ownership and progress tracking per subtask
5. **Scalability**: Pattern works for features of any size

---

## Real-World Application

This workflow pattern was successfully used in the comprehensive MCP tools testing (2025-10-31):

**Test Execution:**
- Created 2 projects, 4 branches, 7 tasks, 4 subtasks
- Tested 20+ MCP tool actions systematically
- Achieved 90% success rate (18/20 actions working)
- Documented 3 issues with detailed fix prompts
- Completed in ~15 minutes with proper task management

**Key Learnings:**
- Systematic task creation prevents missed requirements
- Agent specialization improves code quality
- Subtask validation catches issues early
- Documentation in MCP tasks provides complete audit trail

---

## Best Practices

### DO:
✅ Create parent task with complete requirements upfront
✅ Break into specialized subtasks with clear acceptance criteria
✅ Assign agents based on expertise (coding, security, testing, docs)
✅ Identify dependencies to enable parallel execution
✅ Include line numbers when referencing existing code
✅ Run security audit and code review before completion
✅ Update task progress at key milestones (25%, 50%, 75%, 100%)

### DON'T:
❌ Start implementation before planning complete
❌ Assign generic "coding-agent" to security-critical subtasks
❌ Skip dependency analysis (causes blocking and delays)
❌ Forget to include file paths and line numbers in context
❌ Mark tasks complete without verification
❌ Skip code review for "small" changes
❌ Create tasks without clear acceptance criteria

---

## Conclusion

The 3-phase workflow provides a structured, efficient approach to complex feature development:

1. **Phase 1 (Planning)**: Creates complete visibility and enables parallelism
2. **Phase 2 (Execution)**: Leverages specialized agents for optimal quality
3. **Phase 3 (Review)**: Ensures production-ready code through systematic review

**Result**: Faster delivery, higher quality, complete audit trail, and better team coordination.
