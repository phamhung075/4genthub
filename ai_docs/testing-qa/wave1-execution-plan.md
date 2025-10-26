# 🚀 WAVE 1 EXECUTION PLAN: Infrastructure & Core Services

**Duration:** Weeks 1-2 (10 working days)
**Goal:** +1.5% coverage (~1,000 lines)
**Target:** 0-30% coverage infrastructure files
**Status:** READY TO EXECUTE

---

## 📋 WAVE 1 FILE TARGETS (Top 10)

| # | File | Current Coverage | Missing Lines | Priority | Estimated Tests | Estimated Time |
|---|------|------------------|---------------|----------|----------------|----------------|
| 1 | session_store.py | 0% | 445 | 🔴 CRITICAL | 20-25 | 2 days |
| 2 | openapi.py | 0% | 434 | 🔴 CRITICAL | 20-25 | 2 days |
| 3 | server.py | 24.6% | 413 | 🔴 CRITICAL | 20-25 | 2 days |
| 4 | manage_connection_tool.py | 0% | 375 | 🔴 HIGH | 15-20 | 1.5 days |
| 5 | task_repository.py | 43.3% | 422 | 🔴 HIGH | 15-20 | 1.5 days |
| 6 | auth_endpoints.py | 32.5% | 301 | 🟠 HIGH | 15-20 | 1.5 days |
| 7 | git_branch_application_facade.py | 39.8% | 272 | 🟠 MEDIUM | 12-15 | 1 day |
| 8 | hint_manager.py | 40.7% | 258 | 🟠 MEDIUM | 12-15 | 1 day |
| 9 | context_delegation_service.py | 43.7% | 215 | 🟠 MEDIUM | 10-12 | 1 day |
| 10 | context_resolution_service.py | TBD | ~200 | 🟡 MEDIUM | 10-12 | 1 day |

**Total Estimated:**
- Lines to Cover: ~1,000-1,200
- Tests to Write: 150-180
- Time Required: 14-16 days (2 developers @ 80% capacity = 10 days)

---

## 🎯 DAILY EXECUTION SCHEDULE

### Week 1

**Monday (Day 1): Setup & File #1**
- Morning (2h): Generate coverage report, analyze files
- Afternoon (6h): session_store.py - Write 10-12 tests

**Tuesday (Day 2): File #1 Completion**
- All day (8h): session_store.py - Complete remaining 10-12 tests
- Target: 0% → 60%+ coverage

**Wednesday (Day 3): File #2**
- All day (8h): openapi.py - Write 20-25 tests
- Target: 0% → 50%+ coverage

**Thursday (Day 4): File #3**
- Morning (4h): server.py - Write 12-15 tests
- Afternoon (4h): Continue server.py tests
- Target: 24.6% → 60%+ coverage

**Friday (Day 5): File #3 & Review**
- Morning (4h): Complete server.py tests
- Afternoon (4h): Week 1 review, coverage report, documentation

**Expected Week 1 Results:**
- 3 files improved
- ~60-75 tests added
- ~600-700 lines covered
- Coverage: 56.08% → ~57.1% (+1%)

### Week 2

**Monday (Day 6): File #4 & #5**
- Morning (4h): manage_connection_tool.py - Write 8-10 tests
- Afternoon (4h): task_repository.py - Write 8-10 tests

**Tuesday (Day 7): File #5 & #6**
- Morning (4h): Complete task_repository.py
- Afternoon (4h): auth_endpoints.py - Write 10-12 tests

**Wednesday (Day 8): File #6 & #7**
- Morning (4h): Complete auth_endpoints.py
- Afternoon (4h): git_branch_application_facade.py - Write 12-15 tests

**Thursday (Day 9): File #8, #9, #10**
- Morning (4h): hint_manager.py - Write 12-15 tests
- Afternoon (4h): context_delegation_service.py - Write 10-12 tests

**Friday (Day 10): Completion & Wave 1 Report**
- Morning (4h): context_resolution_service.py - Write 10-12 tests
- Afternoon (4h): Wave 1 final report, documentation

**Expected Week 2 Results:**
- 7 files improved
- ~80-100 tests added
- ~400-500 lines covered
- Coverage: ~57.1% → 57.6%+ (+0.5%)

**Wave 1 Total Expected:**
- Coverage: 56.08% → **57.6%+** (+1.5%)
- Tests: 8,829 → **9,000+** (+171)
- 10 files from 0-43% → 50-70%

---

## 📝 MCP TASK TEMPLATES

### Master Task Template

```
Action: create
Title: Wave 1: Infrastructure & Core Services Coverage (10 files, +1.5%)
git_branch_id: [INSERT_BRANCH_ID]
assignees: test-orchestrator-agent
priority: critical
estimated_effort: 10 days

Details:
=== WAVE 1: INFRASTRUCTURE & CORE SERVICES ===

**Objective:** Improve 10 critical infrastructure files from 0-43% to 50-70% coverage

**Target Files (Priority Order):**
1. session_store.py - 0% (445 missing) → 60%+ [CRITICAL]
2. openapi.py - 0% (434 missing) → 50%+ [CRITICAL]
3. server.py - 24.6% (413 missing) → 60%+ [CRITICAL]
4. manage_connection_tool.py - 0% (375 missing) → 55%+ [HIGH]
5. task_repository.py - 43.3% (422 missing) → 65%+ [HIGH]
6. auth_endpoints.py - 32.5% (301 missing) → 60%+ [HIGH]
7. git_branch_application_facade.py - 39.8% (272 missing) → 65%+ [MEDIUM]
8. hint_manager.py - 40.7% (258 missing) → 65%+ [MEDIUM]
9. context_delegation_service.py - 43.7% (215 missing) → 70%+ [MEDIUM]
10. context_resolution_service.py - TBD (~200 missing) → 60%+ [MEDIUM]

**Success Criteria:**
- Total coverage gain: +1.5% project-wide (56.08% → 57.6%+)
- Tests added: 150-180 comprehensive tests
- Lines covered: 1,000-1,200 lines
- Zero regressions: All 8,829 existing tests still passing
- Quality: All tests production-ready, no flaky tests
- Timeline: 10 working days (2 weeks)

**Testing Strategy:**
- **Infrastructure files (server, openapi, session_store):**
  - Integration tests with real dependencies where possible
  - Mock external services (databases, APIs)
  - Focus on initialization, lifecycle, error handling
  - Test configuration loading and validation

- **Repository files (task_repository):**
  - Unit tests for CRUD operations
  - Mock database connections
  - Test query building and execution
  - Focus on data validation and transformation

- **Service files (auth, facades, delegation):**
  - Unit tests with mocked dependencies
  - Test business logic paths
  - Focus on happy paths first, then error paths
  - Test async operations if present

- **Tool files (manage_connection_tool):**
  - Integration tests for MCP tool interface
  - Mock underlying services
  - Test parameter validation
  - Test response formatting

**Coverage Focus:**
- **Primary:** Happy path coverage (70% of effort)
- **Secondary:** Error handling (20% of effort)
- **Tertiary:** Edge cases (10% of effort)

**Quality Standards:**
- Every test must cover minimum 5 lines
- Use existing test patterns from project
- Follow pytest conventions
- Proper fixtures and mocking
- Clear test names and documentation
- No flaky tests (must pass 3x consistently)

**Reporting Requirements:**
- Daily: Coverage % progress on each file
- Weekly: Wave 1 progress report with metrics
- End of Wave: Complete summary with lessons learned
```

---

### Individual File Task Template (Example: session_store.py)

```
Action: create (subtask)
parent_task_id: [MASTER_TASK_ID]
Title: Test coverage: session_store.py (0% → 60%+)
assignees: test-orchestrator-agent
priority: critical
estimated_effort: 2 days

Description:
Improve test coverage for session_store.py from 0% to 60%+ coverage.

**File Location:**
src/fastmcp/[FIND_EXACT_PATH]/session_store.py

**Current Coverage:** 0%
**Missing Lines:** 445
**Target Coverage:** 60%+ (cover ~270 lines)
**Estimated Tests:** 20-25 comprehensive tests

**Test Focus Areas (Priority Order):**

1. **Session Creation (5-7 tests):**
   - Create session with valid data
   - Create session with minimal data
   - Create session with all optional fields
   - Validate session ID generation
   - Test session expiration setting
   - Test session metadata storage
   - Test concurrent session creation

2. **Session Retrieval (4-6 tests):**
   - Get session by valid ID
   - Get session by invalid ID (returns None)
   - Get session after expiration
   - Get session with metadata
   - List all sessions
   - Filter sessions by criteria

3. **Session Updates (4-5 tests):**
   - Update session expiration
   - Update session metadata
   - Update session state
   - Extend session lifetime
   - Update non-existent session (error handling)

4. **Session Deletion (3-4 tests):**
   - Delete session by ID
   - Delete expired sessions (cleanup)
   - Delete all sessions
   - Delete non-existent session (idempotent)

5. **Session Expiration (3-4 tests):**
   - Check if session expired
   - Auto-cleanup expired sessions
   - Extend session before expiration
   - Handle timezone-aware expiration

**Testing Strategy:**
- Use in-memory storage for fast tests
- Mock time/datetime for expiration tests
- Test both sync and async operations if applicable
- Focus on data integrity and consistency
- Test edge cases: empty strings, None values, special characters

**Expected Coverage Improvement:**
- Lines: 0/445 → 270/445 (60%+)
- Branches: Improve branch coverage where present
- Test execution: All tests complete in <5 seconds total

**Success Criteria:**
- 20-25 tests written and passing
- Coverage reaches 60%+
- Zero flaky tests (3x execution confirms)
- No regressions in existing test suite
- Tests follow project conventions
```

---

## 🛠️ EXECUTION COMMANDS

### Step 1: Create Master Task

```bash
# Find git branch ID
git_branch_id=$(python3 -c "from fastmcp.task_management.infrastructure.repositories.orm import * ; print('GET_FROM_MCP')")

# Create master task via MCP
mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="[INSERT_BRANCH_ID]",
    title="Wave 1: Infrastructure & Core Services Coverage (10 files, +1.5%)",
    assignees="test-orchestrator-agent",
    priority="critical",
    details="[USE TEMPLATE ABOVE]",
    estimated_effort="10 days"
)
```

### Step 2: Create Subtasks for Each File

```python
# Repeat for all 10 files
mcp__agenthub_http__manage_subtask(
    action="create",
    task_id="[MASTER_TASK_ID]",
    title="Test coverage: session_store.py (0% → 60%+)",
    description="[USE INDIVIDUAL TEMPLATE ABOVE]",
    priority="critical",
    assignees="test-orchestrator-agent"
)
```

### Step 3: Delegate to test-orchestrator-agent

```python
Task(
    subagent_type="test-orchestrator-agent",
    prompt="task_id: [MASTER_TASK_ID]

EXECUTE WAVE 1 - Start with File 1 (session_store.py)

Work through all 10 subtasks systematically:
1. session_store.py (Day 1-2)
2. openapi.py (Day 3)
3. server.py (Day 4-5)
4. manage_connection_tool.py (Day 6)
5. task_repository.py (Day 6-7)
6. auth_endpoints.py (Day 7-8)
7. git_branch_application_facade.py (Day 8)
8. hint_manager.py (Day 9)
9. context_delegation_service.py (Day 9)
10. context_resolution_service.py (Day 10)

For each file:
1. Read file to understand structure
2. Analyze existing tests (if any)
3. Write comprehensive tests following strategy
4. Run tests to verify coverage improvement
5. Update subtask status and progress
6. Continue to next file automatically

Target: +1.5% project coverage (56.08% → 57.6%+)
Timeline: 10 days
Quality: Zero regressions, production-ready tests

EXECUTE NOW starting with session_store.py."
)
```

---

## 📊 PROGRESS TRACKING

### Daily Checklist

- [ ] Morning: Review yesterday's progress
- [ ] Generate coverage report for current files
- [ ] Update subtask status with progress %
- [ ] Write tests following file strategy
- [ ] Run tests locally (all passing)
- [ ] Commit tests with clear message
- [ ] Update task progress notes
- [ ] Evening: Run full test suite (no regressions)

### Weekly Checklist

- [ ] Generate comprehensive coverage report
- [ ] Update Wave 1 master task with progress
- [ ] Document lessons learned
- [ ] Identify any blockers or issues
- [ ] Adjust next week's plan if needed
- [ ] Celebrate wins with team

### Wave Completion Checklist

- [ ] All 10 files improved to target coverage
- [ ] 150-180 tests added and passing
- [ ] Zero regressions confirmed
- [ ] Coverage goal achieved (57.6%+)
- [ ] All tasks marked complete with summaries
- [ ] Wave 1 report generated
- [ ] Lessons documented for Wave 2

---

## 🎯 SUCCESS METRICS

### Target Metrics (End of Wave 1)

| Metric | Start | Target | Measurement |
|--------|-------|--------|-------------|
| Project Coverage | 56.08% | 57.6%+ | pytest --cov |
| Files Improved | 0 | 10 | Coverage report |
| Tests Added | 8,829 | 9,000+ | pytest collect |
| Lines Covered | - | 1,000-1,200 | Coverage diff |
| Regressions | 0 | 0 | CI/CD pipeline |
| Test Execution Time | ~7 min | <8 min | pytest duration |
| Flaky Tests | 0 | 0 | 3x test runs |

### Quality Metrics

- **Test Quality Score:** 95%+
  - Proper mocking: Yes/No
  - Clear test names: Yes/No
  - Good documentation: Yes/No
  - Follows conventions: Yes/No
  - No flakiness: Yes/No

- **Code Review Checklist:**
  - [ ] Tests cover happy paths
  - [ ] Error handling tested
  - [ ] Edge cases considered
  - [ ] Fixtures properly used
  - [ ] Mocks correctly implemented
  - [ ] Test names descriptive
  - [ ] No hardcoded values
  - [ ] Cleanup handled properly

---

## 🚨 RISK MITIGATION

### Common Issues & Solutions

**Issue 1: File Not Found**
- Solution: Use `find` command to locate file
- Update task with correct path
- Continue execution

**Issue 2: Complex Dependencies**
- Solution: Start with simple tests first
- Mock complex dependencies
- Add integration tests later if needed

**Issue 3: Slow Test Execution**
- Solution: Use in-memory databases
- Mock slow operations
- Parallelize test execution

**Issue 4: Coverage Not Improving**
- Solution: Check for unreachable code
- Review branch coverage separately
- Focus on partial branches
- Add edge case tests

---

## 📝 REPORTING TEMPLATE

### Daily Status Update

```
Date: [DATE]
Wave: 1
Day: [X]/10

**Files Worked On:**
- [filename]: [start%] → [current%] ([tests added])

**Progress:**
- Tests Added: [count]
- Lines Covered: [estimated]
- Current Project Coverage: [%]

**Blockers:**
- [None / List any issues]

**Tomorrow:**
- [Next file to work on]
```

### Week 1 Report

```
Week 1 Wave 1 Progress Report
Date: [END_OF_WEEK]

**Coverage Progress:**
- Start: 56.08%
- Current: [%]
- Gain: [%]
- Target: 57.6%

**Files Completed:**
1. [file1]: [0%] → [60%] ✅
2. [file2]: [0%] → [50%] ✅
3. [file3]: [24.6%] → [65%] ✅

**Metrics:**
- Tests Added: [count]/150
- Lines Covered: [count]/1000
- Regressions: 0
- Test Time: [duration]

**Insights:**
- [Key learnings]
- [Challenges faced]
- [Solutions implemented]

**Next Week Plan:**
- Complete remaining 7 files
- Focus on [specific areas]
- Adjust strategy if needed
```

---

## ✅ WAVE 1 COMPLETION CRITERIA

Wave 1 is considered complete when:

1. ✅ All 10 target files improved to goal coverage
2. ✅ Project coverage reaches 57.6%+ (minimum 57.5%)
3. ✅ 150+ tests added (minimum 140)
4. ✅ Zero regressions in existing test suite
5. ✅ All tests pass 3x consistently (no flakiness)
6. ✅ Test execution time <8 minutes
7. ✅ Code review completed and approved
8. ✅ Documentation updated
9. ✅ Wave 1 report generated
10. ✅ Lessons documented for Wave 2

**Upon completion, proceed to Wave 2 planning and execution.**

---

**Document Version:** 1.0
**Last Updated:** 2025-10-25
**Status:** READY TO EXECUTE
**Dependencies:** Coverage report (coverage_final.json), Git branch with MCP setup
